# STORY-002: Flag at-risk hospitals with fixed warning rules

As a Management Company COO, I want hospitals flagged by clear, fixed rules, so that I can trust why a hospital is on the at-risk list.

**Release:** r0 · Walking Skeleton: Public Data to Grounded Briefing (weeks 0 to 1)
**Owner:** Early-Warning Engine
**Blocked by:** STORY-001
**Due:** 2026-09-30 (baseline 2026-09-30)

## The requirements this satisfies

- **REQ-005** (Functional, must): The system must flag hospitals using fixed, tested rules and store the metric values that triggered each flag.
- **REQ-003** (Safety, must): The system must make every displayed or briefed number traceable to the public cost report line or uploaded file row it came from.

## How to build it

Write each rule as a small pure Python function with pytest tests at, just above and just below each threshold. Store flags in a warning_flags table keyed on (hospital, rule, period).

## Failure paths you must handle

- A missing metric is silently treated as passing a rule
- A rule threshold changes without a test catching it
- A re-run creates duplicate flags

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given a hospital with operating margin below 0%, days cash on hand below 30, or days in A/R rising two years in a row, When the engine runs, Then that hospital receives a flag naming the rule it tripped.
- [ ] Given a hospital whose metrics are missing, When the engine runs, Then it is marked as not assessable rather than stable.
- [ ] Given the engine has already run on the same data, When it runs again, Then no duplicate flags are created.
- [ ] Trust: Every flag stores the exact metric values and years that triggered it.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-002: Flag at-risk hospitals with fixed warning rules.

As a Management Company COO, I want hospitals flagged by clear, fixed rules, so that I can trust why a hospital is on the at-risk list.

Before writing any code, confirm STORY-001 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given a hospital with operating margin below 0%, days cash on hand below 30, or days in A/R rising two years in a row, When the engine runs, Then that hospital receives a flag naming the rule it tripped.
- Given a hospital whose metrics are missing, When the engine runs, Then it is marked as not assessable rather than stable.
- Given the engine has already run on the same data, When it runs again, Then no duplicate flags are created.
- Trust: Every flag stores the exact metric values and years that triggered it.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- A missing metric is silently treated as passing a rule
- A rule threshold changes without a test catching it
- A re-run creates duplicate flags

Write each rule as a small pure Python function with pytest tests at, just above and just below each threshold. Store flags in a warning_flags table keyed on (hospital, rule, period).

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-002 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-002` on its own line in the message, and add a PROGRESS.md entry.
```
