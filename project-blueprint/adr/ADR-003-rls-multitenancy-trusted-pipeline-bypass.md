# ADR-003: Multi-tenancy via Postgres RLS, pipeline as a trusted bypass role

**Status:** Accepted

## Context

REQ-008 requires that each management company only sees its own hospitals' private data
(uploaded ledgers, briefings, cost-report findings). This could be enforced in application code
(every query manually filtered by `company_id`) or at the database layer.

## Decision

Every private table (`hospital_monthly_metrics`, `briefings`, `cost_report_findings`,
`weekly_briefing_emails`, `export_conversions`) has Postgres Row-Level Security enabled with a
`FOR SELECT` policy joining `company_hospitals`/`company_members` on `auth.uid()`. The Python
pipeline connects to Postgres as the table owner (`postgres`, confirmed live to have
`rolbypassrls=true`) and is the only write path — it bypasses RLS entirely, by design, since it
is the trusted process, not a stand-in for any one company. Every future browser-based read (the
STORY-009 dashboard, this project's first) goes through a real signed-in session so `auth.uid()`
resolves for real, rather than any per-request `company_id` filter written in TypeScript.

## Consequences

- Access control has one real enforcement point (Postgres), not N call sites across a growing
  frontend that could each independently forget a `.eq("company_id", ...)` filter.
- Verified against the real running database, not assumed: `pipeline/test_row_level_security.py`
  simulates a real JWT claim (`SET LOCAL request.jwt.claim.sub`) against live RLS policies, opt-in
  only (never runs in the default `pytest pipeline/` suite, per this project's rule that
  integration tests never touch production automatically).
- New private tables must remember to enable RLS from day one — `export_conversions`/
  `hospital_monthly_metrics`/`slipping_hospital_alerts` were deliberately shipped with RLS
  enabled and zero policies (fails closed) before any per-company policy existed, rather than
  left open in the gap.
- The trusted pipeline having unrestricted write access is a real concentration of trust — a bug
  in pipeline code has no RLS backstop. Accepted because there is no other legitimate write path
  in this system today.
