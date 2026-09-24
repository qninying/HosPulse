# ADR-004: Idempotency via natural-key UPSERT + a shared execution-state log

**Status:** Accepted

## Context

REQ-015 requires every import, upload, normalization, and email to be idempotent — re-running
must not duplicate data or double-send. A job queue with delivery-once semantics, or an
application-level lock table, were both possible mechanisms.

## Decision

Every side-effecting write uses `INSERT ... ON CONFLICT (natural key) DO UPDATE` (or `DO NOTHING`
where the correct behavior is "reserve a slot before the external call," as in
`weekly_briefing_email.reserve_send_slot()`), keyed on the real-world identity of the thing being
written — `(provider_ccn, fiscal_year)`, `(company_id, week_of, recipient_email)`,
`source_file_hash`, `(provider_ccn, fiscal_year, metric_name)`. No queue, no separate lock table.
On top of that, `pipeline/pipeline_run_log.py` (built for STORY-009) gives `hcris_import.py` and
`early_warning.py` — the two processes with no natural per-run audit trail of their own — an
explicit `pipeline_runs` row per execution (`status`, `rows_affected`, `error_message`), reused
by the Cost Report Co-pilot rather than building a second logging mechanism.

## Consequences

- Idempotency is provable by inspection of the schema (a `UNIQUE` constraint) rather than by
  trusting application logic to check-then-act correctly under concurrency.
- Live-proven repeatedly, not just asserted: every idempotent process in this system has been run
  twice back-to-back against production at least once, with before/after row counts compared.
- `export_conversions`/`weekly_briefing_emails` already are execution-state logs in their own
  right (one row per unit of work); `pipeline_runs` was deliberately not layered on top of them
  too, to avoid two logs claiming to be the source of truth for the same event.
- `pipeline_runs` is an audit trail, not a lock — two concurrent invocations of the same process
  are not prevented from both running (each still ends up in a consistent state via the natural
  key), and a process killed mid-run leaves a permanently `'running'` row with nothing yet
  surfacing that to a human. Documented, not solved, on the Next list.
