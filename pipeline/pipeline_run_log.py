"""STORY-009 (REQ-015): a shared execution-state log for processes that
otherwise leave no audit trail of their own runs.

Not an idempotency key by itself. hcris_import.py and early_warning.py are
already safe to run twice via natural-key upserts on their own data
tables -- this module only records that a run happened, when, and how it
ended, which is the separate Trust criterion ("each process logs its
execution state to prevent duplication") on top of that. export_conversions
and weekly_briefing_emails already give normalization/upload and email
this same guarantee at a finer grain (one row per file / per send), so
they are not routed through this table too.

A failed run also triggers a best-effort founder alert (founder_alert.py)
-- closes the "no active paging" gap every process routed through this
module used to have. The DB write is the real record either way; the
alert is a secondary notification that never affects it.
"""
from __future__ import annotations

import psycopg2

from founder_alert import send_founder_alert


def start_pipeline_run(process_name: str, database_url: str, run_key: str | None = None) -> int:
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pipeline_runs (process_name, run_key) VALUES (%s, %s) RETURNING id",
                (process_name, run_key),
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def finish_pipeline_run(
    run_id: int,
    status: str,
    database_url: str,
    rows_affected: int | None = None,
    error_message: str | None = None,
) -> None:
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_runs
                SET status = %s, rows_affected = %s, error_message = %s, completed_at = now()
                WHERE id = %s
                RETURNING process_name, run_key
                """,
                (status, rows_affected, error_message, run_id),
            )
            process_name, run_key = cur.fetchone()
    finally:
        conn.close()

    if status == "failed":
        subject = f"HosPulse pipeline failed: {process_name}"
        run_desc = f"{process_name}" + (f" ({run_key})" if run_key else "")
        send_founder_alert(subject, f"Run {run_id} of {run_desc} failed: {error_message}")
