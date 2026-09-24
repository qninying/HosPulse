# ADR-015: Column-level GRANT for the Cost Report Finding decision, not RLS alone

**Status:** Accepted

## Context

STORY-011 deliberately shipped the Cost Report Co-pilot with no specialist sign-off workflow --
`cost_report_findings.status` only ever gets set to `'open'`, by the trusted pipeline, which
connects as table owner and bypasses RLS entirely. A specialist confirming or rejecting a finding
needs a real write path for an authenticated company member, the first one this table has ever
needed from an untrusted (RLS-bound) client.

`authenticated` already holds a blanket `UPDATE` grant on every table in this schema (Supabase's
schema-level default, the same fact the STORY-006 comment on this file documents for `SELECT`). A
row-level `FOR UPDATE` policy only controls *which rows* a company member can touch, not *which
columns*. Adding a `FOR UPDATE` policy scoped by company membership, without more, would let any
member of a company managing a hospital rewrite that finding's `cost_report_value`,
`ledger_value`, or `explanation` via a direct PostgREST call, not just decide it.

## Decision

Revoke the blanket `UPDATE` grant on `cost_report_findings` and re-grant `UPDATE` on exactly the
four decision columns (`status`, `reviewed_by`, `reviewed_at`, `decision_note`) to `authenticated`.
This is a standard, Supabase-documented pattern for "let a client edit some columns, not others,"
independent of and layered underneath the row-level policy, not a replacement for it.

The row-level policy adds the transition rules a column grant can't express: `USING (status =
'open' ...)` so only an undecided finding can be touched at all (a company member can't reopen a
decided one), and `WITH CHECK (status IN ('confirmed', 'rejected') AND reviewed_by = auth.uid()
...)` so a member can only move a finding forward, and only ever attribute the decision to their
own `auth.uid()`, never someone else's.

A `status` `CHECK` constraint was added at the same time -- it had none before, `'open'` was only
ever a default, never an enforced value. There are now real transitions worth constraining.

## Consequences

- Closes the AI Employee Charter's largest named gap: a specialist can now confirm or reject a
  finding for real, through `frontend/src/app/dashboard/actions.ts`'s `decideCostReportFinding`,
  which calls the authenticated (cookie-session, RLS-bound) Supabase client -- never the
  service-role key, keeping the same trust boundary distinction ADR-014 already drew between the
  trusted pipeline and every other caller.
- A decided finding disappears from `getOpenCostReportFindings`'s open-only query once it is
  confirmed or rejected -- by design for this pass, matching how the rest of this dashboard treats
  a resolved item. A "decided findings" history view is real, separate future work, not built here.
- This is the first column-level `GRANT` in this schema. Every other table's write protection
  comes from RLS row scoping alone (STORY-006's own documented model), because no other table has
  needed per-column protection for an untrusted client yet. If a future table needs the same
  pattern, this ADR is the reference.
