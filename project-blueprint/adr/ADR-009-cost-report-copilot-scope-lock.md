# ADR-009: Cost Report Co-pilot scoped to cash + A/R only

**Status:** Accepted

## Context

`.hospulse` STORY-011 asks the Cost Report Co-pilot to "find possible missed reimbursement" by
comparing a hospital's annual cost report against its own ledger. The operator-uploaded monthly
ledger (`hospital_monthly_metrics`) only ever captures four metrics: `cash_on_hand`,
`ar_balance`, `denial_rate_pct`, `open_positions`. The cost report captures five annual figures,
including revenue and operating expense, which have no monthly-ledger counterpart at all.

## Decision

The co-pilot compares only `cash_on_hand` and A/R balance — the two metrics that genuinely exist
on both sides of the data — flagged with a human-confirmed 15% relative-difference threshold.
Revenue, expense, and margin reconciliation are explicitly out of scope, not silently attempted
with a fabricated proxy.

## Consequences

- Every finding this agent can produce is grounded in a real, literal comparison a reader can
  verify by hand — a narrower but fully defensible claim, rather than a "reimbursement audit"
  the underlying data can't actually support.
- Denial rate and open positions, despite being real ledger metrics, are never used by this agent
  at all — there is no cost-report line to compare them against. A future story that wants to use
  them needs a different comparison target, not an extension of this one.
- If the product ever needs the broader claim implied by "cost report co-pilot," the real
  prerequisite is extending `export_normalizer.py`'s captured metric set (revenue, expense) before
  extending this agent's comparison logic — documented as a real dependency, not a code change to
  make here.
