"""STORY-011: convert operator-uploaded hospital-system exports (Epic,
Cerner, etc.) into HosPulse's standard monthly metrics, per the mapping
registry in mappings/.

REQ-011: convert exports from different hospital systems into one
standard set of monthly metrics per hospital.
REQ-012: mark unknown formats as 'needs mapping' rather than guessing --
enforced entirely inside mappings.detect_format(), not here.

Every run writes exactly one export_conversions row (the Trust
criterion's audit entry), on every branch -- ok, needs_mapping, or
failed -- so "audit entry missing for conversion" can't happen by
construction. Idempotent: the same file content run twice returns the
first run's outcome without a second audit row or duplicate metrics,
keyed on a SHA-256 of the raw file bytes.

Every export is scanned for PHI before anything below is stored or
logged (REQ-009's whole-project guardrail, not just STORY-010's own
scope) via phi_guardrail.ingest_file_with_phi_gate() -- reused rather
than rebuilt, since it was already built for exactly this reuse and
this repo already learned once (this same STORY-011, in the portal's
other numbering) that a guardrail nothing calls doesn't count. A PHI
hit raises PhiRejectedError; export_conversions and
hospital_monthly_metrics are never touched for a rejected file.

STORY-005 (operator upload) invokes this module as a subprocess from a
Next.js API route rather than reimplementing any of this in TypeScript
-- `--json` makes the CLI print one machine-readable JSON line instead
of the human-readable text below, so that bridge doesn't have to
string-sniff stdout.

Usage: python3 export_normalizer.py [--json] <path-to-export.csv>
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras

from env import load_env
from mappings import detect_format
from phi_guardrail import PhiAuditEntry, PhiRejectedError, ingest_file_with_phi_gate

ROOT = Path(__file__).resolve().parent.parent

_MONTH_FORMATS = ("%Y-%m-%d", "%Y-%m")


@dataclass
class MetricRow:
    provider_ccn: str
    month: str  # ISO date, first-of-month
    metric_name: str
    metric_value: float | None
    source_row: int  # 0-based index into the data rows (header excluded)


@dataclass
class ConversionOutcome:
    status: str  # "ok" | "needs_mapping" | "failed"
    source_system: str | None
    metric_rows: list[MetricRow] = field(default_factory=list)
    error_message: str | None = None
    is_duplicate: bool = False  # STORY-005: this exact file was already processed


def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_csv(content: bytes) -> tuple[list[str], list[dict]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return list(reader.fieldnames or []), rows


def _normalize_month(value: str) -> str:
    value = str(value).strip()
    for fmt in _MONTH_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(day=1).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unrecognized month format: {value!r}")


def normalize_rows(columns: list[str], rows: list[dict]) -> ConversionOutcome:
    """Pure: no I/O. Detects the source system from `columns`, drops totals
    rows, and maps each remaining row to standard metric names. Any error
    while mapping (a malformed month, a vendor-renamed column that's
    missing at row-access time, etc.) is caught and reported as a
    'failed' outcome rather than raising out of the pipeline -- this is
    the "export conversion fails" failure path handled explicitly."""
    mapping = detect_format(columns)
    if mapping is None:
        return ConversionOutcome(status="needs_mapping", source_system=None)

    try:
        metric_rows: list[MetricRow] = []
        for i, row in enumerate(rows):
            if mapping.is_totals_row(row):
                continue
            provider_ccn = row[mapping.HOSPITAL_ID_COLUMN]
            month = _normalize_month(row[mapping.MONTH_COLUMN])
            for metric_name, value in mapping.compute_metrics(row).items():
                metric_rows.append(
                    MetricRow(provider_ccn, month, metric_name, value, i)
                )
        return ConversionOutcome(
            status="ok", source_system=mapping.SOURCE_SYSTEM_NAME, metric_rows=metric_rows
        )
    except (KeyError, ValueError) as exc:
        return ConversionOutcome(
            status="failed",
            source_system=mapping.SOURCE_SYSTEM_NAME,
            error_message=f"{type(exc).__name__}: {exc}",
        )


def _outcome_from_existing(existing: dict) -> ConversionOutcome:
    """Pure: builds the outcome for a file whose hash was already
    processed. is_duplicate=True lets a caller (STORY-005's upload route)
    report 'duplicate' as a message distinct from a fresh outcome, without
    re-deriving anything from the stored record."""
    return ConversionOutcome(
        status=existing["status"],
        source_system=existing["source_system"],
        error_message=existing["error_message"],
        is_duplicate=True,
    )


def fetch_existing_conversion(source_file_hash: str, database_url: str) -> dict | None:
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, source_system, metrics_count, error_message "
                "FROM export_conversions WHERE source_file_hash = %s",
                (source_file_hash,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    status, source_system, metrics_count, error_message = row
    return {
        "status": status,
        "source_system": source_system,
        "metrics_count": metrics_count,
        "error_message": error_message,
    }


def _provider_ccn_for(outcome: ConversionOutcome) -> str | None:
    """Pure: STORY-006 needs export_conversions attributed to a hospital
    so RLS can scope it by company. A 'needs_mapping' or 'failed' outcome
    genuinely has no reliably-known hospital (the format was never
    identified, or the row-level error happened before we'd trust any
    single row's data) -- None here is honest, not a gap to paper over."""
    if not outcome.metric_rows:
        return None
    return outcome.metric_rows[0].provider_ccn


def persist_conversion(
    outcome: ConversionOutcome, source_file: str, source_file_hash: str, database_url: str
) -> int:
    """Writes the single audit row for this conversion attempt. Not
    idempotent on its own -- callers must check fetch_existing_conversion()
    first, which run() does."""
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO export_conversions (
                    source_file, source_file_hash, source_system, status,
                    metrics_count, error_message, provider_ccn
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    source_file,
                    source_file_hash,
                    outcome.source_system,
                    outcome.status,
                    len(outcome.metric_rows),
                    outcome.error_message,
                    _provider_ccn_for(outcome),
                ),
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def upsert_metrics(
    metric_rows: list[MetricRow],
    source_file: str,
    source_system: str,
    conversion_id: int,
    database_url: str,
) -> None:
    """Idempotent: ON CONFLICT (provider_ccn, month, metric_name) DO
    UPDATE, so re-normalizing the same export upserts the same values
    instead of accumulating duplicate rows."""
    if not metric_rows:
        return
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO hospital_monthly_metrics (
                    provider_ccn, month, metric_name, metric_value,
                    source_file, source_row, source_system, conversion_id
                ) VALUES %s
                ON CONFLICT (provider_ccn, month, metric_name) DO UPDATE SET
                    metric_value = EXCLUDED.metric_value,
                    source_file = EXCLUDED.source_file,
                    source_row = EXCLUDED.source_row,
                    source_system = EXCLUDED.source_system,
                    conversion_id = EXCLUDED.conversion_id,
                    created_at = now()
                """,
                [
                    (
                        r.provider_ccn,
                        r.month,
                        r.metric_name,
                        r.metric_value,
                        source_file,
                        r.source_row,
                        source_system,
                        conversion_id,
                    )
                    for r in metric_rows
                ],
            )
    finally:
        conn.close()


def _log_phi_audit(entry: PhiAuditEntry, source_file: str) -> None:
    """Structured stdout log line per this project's Observability
    Framework. No dedicated PHI audit table exists yet -- REQ-009 only
    requires the entry never carry row content, which PhiAuditEntry
    already guarantees by construction (column names and categories
    only)."""
    print(json.dumps({
        "timestamp": entry.timestamp,
        "level": "warn" if entry.decision == "rejected" else "info",
        "service": "export-normalizer",
        "event": "phi_scan",
        "outcome": entry.decision,
        "context": {
            "source_file": source_file,
            "categories": entry.categories,
            "reason": entry.reason,
        },
    }))


def run(content: bytes, source_file: str, database_url: str) -> ConversionOutcome:
    """Idempotent entry point. The same file content processed twice
    returns the first run's outcome and touches neither table a second
    time, keyed on a hash of the raw bytes rather than the filename
    (a re-uploaded file with a different name is still the same file;
    a corrected file with the same name is not).

    Raises PhiRejectedError if the export contains a patient name, birth
    date, or record number field -- by that point the PHI audit entry has
    already been logged, and neither export_conversions nor
    hospital_monthly_metrics has been touched. This deliberately does not
    fold into ConversionOutcome.status: a PHI rejection is a security
    gate, not a normal/retryable conversion outcome, and a caller
    branching only on .status must not be able to mistake one for the
    other."""
    source_file_hash = compute_file_hash(content)
    existing = fetch_existing_conversion(source_file_hash, database_url)
    if existing is not None:
        return _outcome_from_existing(existing)

    columns, rows = parse_csv(content)
    outcomes: list[ConversionOutcome] = []

    def _store(clean_rows: list[dict]) -> None:
        outcome = normalize_rows(columns, clean_rows)
        conversion_id = persist_conversion(outcome, source_file, source_file_hash, database_url)
        if outcome.status == "ok":
            upsert_metrics(
                outcome.metric_rows, source_file, outcome.source_system, conversion_id, database_url
            )
        outcomes.append(outcome)

    ingest_file_with_phi_gate(
        source_file,
        rows,
        store=_store,
        log_audit=lambda entry: _log_phi_audit(entry, source_file),
    )
    return outcomes[0]


if __name__ == "__main__":
    json_mode = "--json" in sys.argv[1:]
    positional = [a for a in sys.argv[1:] if a != "--json"]
    if len(positional) != 1:
        print("usage: python3 export_normalizer.py [--json] <path-to-export.csv>", file=sys.stderr)
        sys.exit(1)

    load_env(ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set -- check .env")

    file_path = Path(positional[0])
    try:
        outcome = run(file_path.read_bytes(), file_path.name, database_url)
    except PhiRejectedError as exc:
        if json_mode:
            print(json.dumps({"status": "phi_rejected", "message": exc.audit_entry.reason}))
        else:
            print(f"rejected: {exc.audit_entry.reason}", file=sys.stderr)
        sys.exit(1)

    if json_mode:
        print(json.dumps({
            "status": outcome.status,
            "is_duplicate": outcome.is_duplicate,
            "source_system": outcome.source_system,
            "metrics_count": len(outcome.metric_rows),
            "error_message": outcome.error_message,
        }))
        sys.exit(0 if outcome.status in ("ok", "needs_mapping") else 1)

    if outcome.is_duplicate:
        print(f"duplicate: {file_path.name} was already processed (status: {outcome.status})")
    elif outcome.status == "ok":
        print(f"{outcome.source_system}: {len(outcome.metric_rows)} metrics normalized")
    elif outcome.status == "needs_mapping":
        print(f"needs_mapping: no known source system matched {file_path.name}")
    else:
        print(f"failed: {outcome.error_message}", file=sys.stderr)
        sys.exit(1)
