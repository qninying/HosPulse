# ADR-010: No value that could be mistaken for real

**Status:** Accepted

## Context

Several places in this project could show either a real number or a placeholder: the Command
Center's Sample/Real toggle, a KPI card with zero real runs yet, a dashboard metric with no
underlying data. The easy failure mode is a "0" or a plausible-looking sample number that a
reader mistakes for a real, checked fact.

## Decision

A missing or not-yet-produced value is never rendered as zero, a dash standing in for zero, or a
believable-but-synthetic number without an explicit, visible label. Concretely: the Command
Center's Sample mode carries a visible "Sample data" badge on every card that uses it; a KPI with
no real runs reads the literal string "No runs recorded" or "No data yet," never "0"; the
dashboard's Slipping KPI specifically avoids "0" because a real 0 would wrongly imply "checked,
none slipping" when the true state is "never checked, no monthly data exists yet."

## Consequences

- Two stale Command Center sample-data maps were found and fixed specifically because they
  silently fell back to real production data when a sample override was missing — the bug this
  ADR's rule is meant to prevent, caught by an explicit audit rather than by chance.
- Every "empty" state in this codebase (`EmptyState.tsx`, `no_briefing`, `no_data`,
  `not_assessable`) is a distinct, named case in code — not a shared fallback that papers over why
  something is empty.
- This is more states to design and test than a single "N/A" catch-all — accepted as the cost of
  a product whose entire value proposition is that operators can trust every number they see.
