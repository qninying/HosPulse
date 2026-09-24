# ADR-011: Reconcile dual story-numbering by auditing overlap, not rebuilding

**Status:** Accepted

## Context

This project has two parallel, non-corresponding story-numbering systems — `.colaberry/` and
`.hospulse/` — that don't share story IDs for the same underlying work, and sometimes reuse the
same ID for two genuinely different stories. This surfaced repeatedly (a dozen-plus documented
instances) as work was built under one system's numbering.

## Decision

Before building anything a story asks for, check whether the other numbering system's plan
already specifies the same real capability, and whether it's already built. When it is, credit
both systems' progress files honestly against what's actually true in the code — never assume a
match without re-reading both stories' literal acceptance criteria, and never tick a criterion
that doesn't genuinely hold just because a same-named story elsewhere is marked done.

## Consequences

- Real, substantial rework has been avoided repeatedly (e.g. `.hospulse` STORY-008's
  normalization requirement was already satisfied by `.colaberry` STORY-011's `export_normalizer.py`
  — confirmed by re-reading both acceptance-criteria lists side by side, not assumed).
- Some crediting attempts found a genuine partial gap instead of a full match (`.hospulse`
  STORY-008's "days in A/R" criterion, `.colaberry` STORY-002's "monthly metrics" wording) and were
  left honestly unticked rather than rounded up — the audit is a check, not a rubber stamp.
- This is real, recurring overhead — every new story now needs a deliberate cross-numbering check
  before work starts, which a single unified plan would not require. Accepted as a workaround for
  a numbering split this project doesn't control the source of.
