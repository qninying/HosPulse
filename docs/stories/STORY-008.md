# STORY-008: Normalize exports into standard monthly metrics

As a Management Company CFO, I want exports from different hospital systems turned into the same monthly numbers, so that I can compare hospitals that run different software.

**Release:** r3 · Early Warning on Customer Data (weeks 5 to 6)
**Owner:** Data Pipeline
**Blocked by:** STORY-007
**Due:** 2026-11-02 (baseline 2026-11-02)

## The requirements this satisfies

- **REQ-011** (Functional, must): The system must convert exports from different hospital systems into one standard set of monthly metrics per hospital.
- **REQ-007** (Reliability, must): The system must make every import, load and normalization run idempotent, so re-running it leaves the same data with no duplicates.

## How to build it

pandas mapping per source system in a versioned mappings/ folder, with a test fixture file for each. Upsert on (hospital, month, metric).

## Failure paths you must handle

- A vendor renames a column in an export update
- A totals row is counted as a data row
- Fiscal months are offset between systems

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given exports from two different hospital systems for the same month, When they are normalized, Then both produce the same standard monthly metrics (cash, days in A/R, denial rate, open positions).
- [ ] Given an export in a format with no known mapping, When normalization runs, Then the file is marked 'needs mapping' and no metrics are guessed.
- [ ] Given normalization has already run for a file, When it runs again, Then the monthly metrics are unchanged and not duplicated.
- [ ] Trust: Every monthly metric links back to the stored file and row it came from.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-008: Normalize exports into standard monthly metrics.

As a Management Company CFO, I want exports from different hospital systems turned into the same monthly numbers, so that I can compare hospitals that run different software.

Before writing any code, confirm STORY-007 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given exports from two different hospital systems for the same month, When they are normalized, Then both produce the same standard monthly metrics (cash, days in A/R, denial rate, open positions).
- Given an export in a format with no known mapping, When normalization runs, Then the file is marked 'needs mapping' and no metrics are guessed.
- Given normalization has already run for a file, When it runs again, Then the monthly metrics are unchanged and not duplicated.
- Trust: Every monthly metric links back to the stored file and row it came from.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- A vendor renames a column in an export update
- A totals row is counted as a data row
- Fiscal months are offset between systems

pandas mapping per source system in a versioned mappings/ folder, with a test fixture file for each. Upsert on (hospital, month, metric).

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-008 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-008` on its own line in the message, and add a PROGRESS.md entry.
```
