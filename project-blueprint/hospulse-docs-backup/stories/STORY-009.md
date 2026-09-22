# STORY-009: Show each managed hospital's dashboard with flags and briefings

As a Management Company COO, I want one screen showing every hospital I manage with its trends, flags and past briefings, so that I can see trouble at a glance.

**Release:** r3 · Early Warning on Customer Data (weeks 5 to 6)
**Owner:** Operator Portal
**Blocked by:** STORY-008, STORY-003
**Due:** 2026-11-06 (baseline 2026-11-06)

## The requirements this satisfies

- **REQ-012** (Functional, must): The system must show operators a dashboard of every managed hospital with its metrics, trends, flags and past briefings.
- **REQ-005** (Functional, must): The system must flag hospitals using fixed, tested rules and store the metric values that triggered each flag.

## How to build it

Extend the Next.js portal, read metrics and flags through Supabase with row-level security, and follow the layout in project-blueprint/mockup.html.

## Failure paths you must handle

- An old month is shown as current
- A chart draws zero for missing months
- The page is slow to load with many hospitals

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given monthly metrics for a company's hospitals, When the operator opens the portal, Then every hospital is listed with status, days cash, days in A/R, margin and a 12-week trend.
- [ ] Given a flagged hospital, When the operator opens it, Then the flag, the rule and the triggering numbers are shown.
- [ ] Given a hospital with no uploads yet, When the dashboard loads, Then it shows 'no data yet' rather than a stable status.
- [ ] Trust: Status colors come only from engine flags, never from the page's own calculations.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-009: Show each managed hospital's dashboard with flags and briefings.

As a Management Company COO, I want one screen showing every hospital I manage with its trends, flags and past briefings, so that I can see trouble at a glance.

Before writing any code, confirm STORY-008, STORY-003 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given monthly metrics for a company's hospitals, When the operator opens the portal, Then every hospital is listed with status, days cash, days in A/R, margin and a 12-week trend.
- Given a flagged hospital, When the operator opens it, Then the flag, the rule and the triggering numbers are shown.
- Given a hospital with no uploads yet, When the dashboard loads, Then it shows 'no data yet' rather than a stable status.
- Trust: Status colors come only from engine flags, never from the page's own calculations.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- An old month is shown as current
- A chart draws zero for missing months
- The page is slow to load with many hospitals

Extend the Next.js portal, read metrics and flags through Supabase with row-level security, and follow the layout in project-blueprint/mockup.html.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-009 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-009` on its own line in the message, and add a PROGRESS.md entry.
```
