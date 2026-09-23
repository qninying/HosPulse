"""Tests for the PHI guardrail (pipeline/phi_guardrail.py).

Run: cd HosPulse && ./.venv/bin/python -m pytest pipeline/ -v
"""

import pytest

from phi_guardrail import PhiRejectedError, ingest_file_with_phi_gate, scan_file_for_phi


CLEAN_LEDGER_ROWS = [
    {"account": "4000", "description": "Patient service revenue", "amount": "184200.00"},
    {"account": "5000", "description": "Salaries and wages", "amount": "92100.00"},
]


def test_happy_path_a_clean_ledger_export_is_accepted():
    result = scan_file_for_phi(CLEAN_LEDGER_ROWS)
    assert result.ok
    assert result.findings == []
    assert "no patient name" in result.reason()


def test_rejects_a_file_with_a_patient_name_column():
    rows = [{"Patient Name": "Jane Doe", "amount": "100.00"}]
    result = scan_file_for_phi(rows)
    assert not result.ok
    assert result.findings[0].category == "patient_name"
    assert result.findings[0].column == "Patient Name"
    assert result.findings[0].basis == "header"


def test_rejects_a_file_with_a_birth_date_column():
    rows = [{"DOB": "1980-01-01", "amount": "100.00"}]
    result = scan_file_for_phi(rows)
    assert not result.ok
    assert result.findings[0].category == "birth_date"


def test_rejects_a_file_with_a_record_number_column():
    rows = [{"MRN": "00019284", "amount": "100.00"}]
    result = scan_file_for_phi(rows)
    assert not result.ok
    assert result.findings[0].category == "record_number"
    assert result.findings[0].basis == "header"


def test_header_matching_is_case_and_punctuation_insensitive():
    rows = [{"  patient_name  ": "Jane Doe"}]
    result = scan_file_for_phi(rows)
    assert not result.ok
    assert result.findings[0].category == "patient_name"


def test_ssn_shaped_content_is_caught_even_under_an_innocuous_header():
    # Header says "identifier", not "SSN" -- content-based fallback catches
    # what the header check alone would miss.
    rows = [{"identifier": "123-45-6789", "amount": "100.00"}]
    result = scan_file_for_phi(rows)
    assert not result.ok
    assert result.findings[0].category == "record_number"
    assert result.findings[0].basis == "content"


def test_a_column_already_flagged_by_header_is_not_double_flagged_by_content():
    rows = [{"SSN": "123-45-6789"}]
    result = scan_file_for_phi(rows)
    assert not result.ok
    assert len(result.findings) == 1
    assert result.findings[0].basis == "header"


def test_reports_every_flagged_column_not_just_the_first():
    rows = [{"Patient Name": "Jane Doe", "DOB": "1980-01-01", "MRN": "00019284"}]
    result = scan_file_for_phi(rows)
    assert not result.ok
    assert {f.category for f in result.findings} == {"patient_name", "birth_date", "record_number"}


def test_ordinary_business_dates_do_not_trigger_a_false_rejection():
    # "report_date" and "posting_date" are legitimate ledger fields, not
    # birth dates -- only the specific DOB-style headers are flagged.
    rows = [{"report_date": "2026-09-22", "posting_date": "2026-09-21", "amount": "100.00"}]
    result = scan_file_for_phi(rows)
    assert result.ok


def test_a_nine_digit_number_that_is_not_ssn_shaped_is_not_flagged():
    # No dashes, so it does not match the SSN pattern -- an ordinary
    # account or invoice number under a generic header stays clean.
    rows = [{"invoice_number": "123456789", "amount": "100.00"}]
    result = scan_file_for_phi(rows)
    assert result.ok


def test_empty_rows_is_trivially_clean():
    assert scan_file_for_phi([]).ok


def test_null_cell_values_do_not_crash_the_content_scan():
    rows = [{"notes": None, "amount": "100.00"}]
    result = scan_file_for_phi(rows)
    assert result.ok


def test_reason_names_every_offending_column_and_category():
    rows = [{"Patient Name": "Jane Doe", "DOB": "1980-01-01"}]
    reason = scan_file_for_phi(rows).reason()
    assert "Patient Name" in reason
    assert "DOB" in reason
    assert "patient_name" in reason
    assert "birth_date" in reason


def test_rejected_file_audit_entry_states_the_reason_without_the_phi_value():
    rows = [{"Patient Name": "Jane Doe"}]
    result = scan_file_for_phi(rows)
    entry = result.to_audit_entry(file_name="monthly_export.csv")
    assert entry.decision == "rejected"
    assert entry.file_name == "monthly_export.csv"
    assert "patient_name" in entry.categories
    assert "Patient Name" in entry.reason  # column name, not the value
    assert "Jane Doe" not in entry.reason
    assert "Jane Doe" not in str(entry.as_dict())


def test_accepted_file_audit_entry_says_accepted():
    entry = scan_file_for_phi(CLEAN_LEDGER_ROWS).to_audit_entry(file_name="ledger.csv")
    assert entry.decision == "accepted"
    assert entry.categories == []


def test_audit_entry_timestamp_is_deterministic_when_now_is_supplied():
    from datetime import datetime, timezone

    fixed = datetime(2026, 9, 22, 6, 0, 0, tzinfo=timezone.utc)
    rows = [{"Patient Name": "Jane Doe"}]
    entry = scan_file_for_phi(rows).to_audit_entry(file_name="f.csv", now=fixed)
    assert entry.timestamp == "2026-09-22T06:00:00+00:00"


class _Recorder:
    """Stand-in for the real Supabase write / logger, not built yet (STORY-005)."""

    def __init__(self):
        self.calls: list = []

    def __call__(self, arg):
        self.calls.append(arg)


def test_gate_stores_a_clean_file_and_logs_an_accepted_entry():
    store, log_audit = _Recorder(), _Recorder()
    entry = ingest_file_with_phi_gate(
        "ledger.csv", CLEAN_LEDGER_ROWS, store=store, log_audit=log_audit
    )
    assert entry.decision == "accepted"
    assert store.calls == [CLEAN_LEDGER_ROWS]
    assert log_audit.calls == [entry]


def test_gate_rejects_a_file_with_patient_names_before_storage():
    store, log_audit = _Recorder(), _Recorder()
    rows = [{"Patient Name": "Jane Doe", "amount": "100.00"}]
    with pytest.raises(PhiRejectedError) as exc_info:
        ingest_file_with_phi_gate("upload.csv", rows, store=store, log_audit=log_audit)
    assert store.calls == []  # never stored
    assert exc_info.value.audit_entry.decision == "rejected"
    assert "patient_name" in exc_info.value.audit_entry.categories


def test_gate_rejects_a_file_with_birth_dates_before_storage():
    store, log_audit = _Recorder(), _Recorder()
    rows = [{"DOB": "1980-01-01", "amount": "100.00"}]
    with pytest.raises(PhiRejectedError):
        ingest_file_with_phi_gate("upload.csv", rows, store=store, log_audit=log_audit)
    assert store.calls == []


def test_gate_logs_the_rejection_audit_entry_exactly_once_before_raising():
    store, log_audit = _Recorder(), _Recorder()
    rows = [{"MRN": "00019284"}]
    with pytest.raises(PhiRejectedError):
        ingest_file_with_phi_gate("upload.csv", rows, store=store, log_audit=log_audit)
    assert len(log_audit.calls) == 1
    assert log_audit.calls[0].decision == "rejected"


def test_gate_audit_log_never_contains_the_raw_row_content():
    store, log_audit = _Recorder(), _Recorder()
    rows = [{"Patient Name": "Jane Doe", "SSN": "123-45-6789"}]
    with pytest.raises(PhiRejectedError):
        ingest_file_with_phi_gate("upload.csv", rows, store=store, log_audit=log_audit)
    logged = str(log_audit.calls[0].as_dict())
    assert "Jane Doe" not in logged
    assert "123-45-6789" not in logged


def test_gate_birth_date_value_never_reaches_the_audit_log():
    # Direct mapping to STORY-010's second criterion: a birth date must be
    # rejected before its actual value is ever written to a log, even
    # though the rejection itself is logged.
    store, log_audit = _Recorder(), _Recorder()
    rows = [{"DOB": "1980-01-01"}]
    with pytest.raises(PhiRejectedError):
        ingest_file_with_phi_gate("upload.csv", rows, store=store, log_audit=log_audit)
    assert "1980-01-01" not in str(log_audit.calls[0].as_dict())
    assert log_audit.calls[0].categories == ["birth_date"]
