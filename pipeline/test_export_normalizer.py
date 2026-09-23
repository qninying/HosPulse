"""Tests for pipeline/export_normalizer.py's pure logic (no network, no
database) -- normalize_rows(), parse_csv(), and compute_file_hash().

The DB-wiring functions (fetch_existing_conversion, persist_conversion,
upsert_metrics, run) are exercised manually against the live Supabase
instance -- see PROGRESS.md's STORY-011 entry for that verification
record, matching this project's own rule that integration tests must
never run automatically against production.

Run: cd HosPulse && ./.venv/bin/python -m pytest pipeline/test_export_normalizer.py -v
"""

import json

from export_normalizer import _log_phi_audit, compute_file_hash, normalize_rows, parse_csv
from phi_guardrail import scan_file_for_phi

EPIC_COLUMNS = [
    "hospital_ccn", "report_month", "line_type", "cash_balance",
    "net_ar_balance", "denied_claims", "total_claims", "open_fte_positions",
]

CERNER_COLUMNS = [
    "provider_ccn", "period_end", "row_category", "unrestricted_cash",
    "net_patient_ar", "claims_denied_count", "claims_total_count", "vacant_positions",
]


def epic_row(ccn="370178", month="2026-08-01", line_type="DATA", **overrides):
    row = {
        "hospital_ccn": ccn, "report_month": month, "line_type": line_type,
        "cash_balance": "150000", "net_ar_balance": "320000",
        "denied_claims": "12", "total_claims": "200", "open_fte_positions": "3",
    }
    row.update(overrides)
    return row


def cerner_row(ccn="370178", month="2026-08-01", row_category="DATA", **overrides):
    row = {
        "provider_ccn": ccn, "period_end": month, "row_category": row_category,
        "unrestricted_cash": "150000", "net_patient_ar": "320000",
        "claims_denied_count": "12", "claims_total_count": "200", "vacant_positions": "3",
    }
    row.update(overrides)
    return row


# -- Happy path: two different vendors, same hospital+month, must land
# on the same standard metric names and values -- this is REQ-011 itself.

def test_epic_and_cerner_exports_produce_the_same_standard_metrics():
    epic_outcome = normalize_rows(EPIC_COLUMNS, [epic_row()])
    cerner_outcome = normalize_rows(CERNER_COLUMNS, [cerner_row()])

    assert epic_outcome.status == "ok"
    assert cerner_outcome.status == "ok"
    epic_metrics = {m.metric_name: m.metric_value for m in epic_outcome.metric_rows}
    cerner_metrics = {m.metric_name: m.metric_value for m in cerner_outcome.metric_rows}
    assert epic_metrics == cerner_metrics == {
        "cash_on_hand": 150000.0,
        "ar_balance": 320000.0,
        "denial_rate_pct": 6.0,
        "open_positions": 3.0,
    }


def test_metric_rows_carry_provider_and_month():
    outcome = normalize_rows(EPIC_COLUMNS, [epic_row(ccn="450099", month="2026-01-01")])
    assert all(m.provider_ccn == "450099" for m in outcome.metric_rows)
    assert all(m.month == "2026-01-01" for m in outcome.metric_rows)


def test_month_with_day_component_is_normalized_to_first_of_month():
    outcome = normalize_rows(EPIC_COLUMNS, [epic_row(month="2026-08-15")])
    assert all(m.month == "2026-08-01" for m in outcome.metric_rows)


# -- Unknown format: REQ-012, never guess.

def test_unknown_columns_are_marked_needs_mapping_not_guessed():
    outcome = normalize_rows(["some_col", "other_col"], [{"some_col": "1", "other_col": "2"}])
    assert outcome.status == "needs_mapping"
    assert outcome.source_system is None
    assert outcome.metric_rows == []


def test_epic_export_missing_one_fingerprint_column_is_needs_mapping():
    columns = [c for c in EPIC_COLUMNS if c != "open_fte_positions"]
    outcome = normalize_rows(columns, [{}])
    assert outcome.status == "needs_mapping"


# -- Totals rows: must be dropped, and dropping them must not corrupt
# source_row provenance for the rows that follow.

def test_totals_row_is_dropped_and_does_not_produce_metrics():
    rows = [epic_row(), epic_row(line_type="TOTAL")]
    outcome = normalize_rows(EPIC_COLUMNS, rows)
    assert outcome.status == "ok"
    # 4 standard metrics from the one real data row, none from TOTAL
    assert len(outcome.metric_rows) == 4


def test_source_row_reflects_position_in_the_original_file_including_the_dropped_totals_row():
    rows = [epic_row(line_type="TOTAL"), epic_row(ccn="450099")]
    outcome = normalize_rows(EPIC_COLUMNS, rows)
    assert outcome.status == "ok"
    # the real data row is index 1 in the original file (index 0 was TOTAL)
    assert all(m.source_row == 1 for m in outcome.metric_rows)
    assert all(m.provider_ccn == "450099" for m in outcome.metric_rows)


# -- Failure path: "export conversion fails" -- a malformed value must
# produce a 'failed' outcome, not an unhandled exception or a silent
# partial result.

def test_unparseable_month_produces_a_failed_outcome_not_a_crash():
    outcome = normalize_rows(EPIC_COLUMNS, [epic_row(month="not-a-date")])
    assert outcome.status == "failed"
    assert outcome.source_system == "epic"
    assert "not-a-date" in outcome.error_message
    assert outcome.metric_rows == []


def test_missing_hospital_id_column_at_row_level_produces_failed_not_a_crash():
    row = epic_row()
    del row["hospital_ccn"]
    outcome = normalize_rows(EPIC_COLUMNS, [row])
    assert outcome.status == "failed"
    assert "hospital_ccn" in outcome.error_message


# -- Trust: denial rate must not be fabricated when there's nothing to
# divide -- an idle/unreported month is None, never a fake 0%.

def test_zero_total_claims_gives_none_denial_rate_not_a_fake_zero():
    outcome = normalize_rows(EPIC_COLUMNS, [epic_row(total_claims="0", denied_claims="0")])
    metrics = {m.metric_name: m.metric_value for m in outcome.metric_rows}
    assert metrics["denial_rate_pct"] is None


# -- compute_file_hash / parse_csv: the idempotency key and the CSV entry point.

def test_identical_content_hashes_identically():
    a = b"col1,col2\n1,2\n"
    b = b"col1,col2\n1,2\n"
    assert compute_file_hash(a) == compute_file_hash(b)


def test_different_content_hashes_differently():
    a = b"col1,col2\n1,2\n"
    b = b"col1,col2\n1,3\n"
    assert compute_file_hash(a) != compute_file_hash(b)


def test_parse_csv_round_trips_columns_and_rows():
    content = b"hospital_ccn,report_month\n370178,2026-08-01\n"
    columns, rows = parse_csv(content)
    assert columns == ["hospital_ccn", "report_month"]
    assert rows == [{"hospital_ccn": "370178", "report_month": "2026-08-01"}]


# -- PHI audit logging: the log line must be valid JSON and must never
# carry the offending cell value, only the column name/category/reason
# PhiAuditEntry already restricts itself to.

def test_phi_audit_log_line_is_valid_json_and_never_contains_the_flagged_value(capsys):
    rows = [{"Patient Name": "Jane Q. Doe", "cash_balance": "150000"}]
    result = scan_file_for_phi(rows)
    entry = result.to_audit_entry(file_name="epic_export.csv")

    _log_phi_audit(entry, "epic_export.csv")

    line = capsys.readouterr().out.strip()
    payload = json.loads(line)  # raises if not valid JSON
    assert payload["outcome"] == "rejected"
    assert payload["context"]["source_file"] == "epic_export.csv"
    assert payload["context"]["categories"] == ["patient_name"]
    assert "Jane Q. Doe" not in line
