# STORY-004: Build the public Health Snapshot search and hospital page

As a Rural Hospital CEO, I want to look up my hospital and see its financial health and trends, so that I know how it compares without asking anyone.

**Release:** r0 · Walking Skeleton: Public Data to Grounded Briefing (weeks 0 to 1)
**Owner:** Snapshot Site
**Blocked by:** STORY-002
**Due:** 2026-10-06 (baseline 2026-10-06)

## The requirements this satisfies

- **REQ-002** (Functional, must): The system must provide a public Health Snapshot where anyone can search for a rural hospital and see its metrics and three-year trend without an account.
- **REQ-003** (Safety, must): The system must make every displayed or briefed number traceable to the public cost report line or uploaded file row it came from.

## How to build it

Next.js app in web/ reading from Supabase, with the data year shown next to every figure. Run locally until STORY-005 checks the numbers.

## Failure paths you must handle

- Search finds nothing because of spelling differences in hospital names
- The database is unreachable when a page renders
- An old fiscal year is shown as if it were current

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given a visitor on the snapshot page, When they search by hospital name or city, Then matching Oklahoma and Texas rural hospitals are listed.
- [ ] Given a hospital page, When it loads, Then it shows three years of operating margin, days cash on hand and days in A/R with any flags in plain words.
- [ ] Given a hospital with missing metrics, When its page loads, Then the missing values read 'not reported' rather than zero.
- [ ] Trust: Every figure on the page shows which cost report year it came from, and the page states that public data lags one to two years.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-004: Build the public Health Snapshot search and hospital page.

As a Rural Hospital CEO, I want to look up my hospital and see its financial health and trends, so that I know how it compares without asking anyone.

Before writing any code, confirm STORY-002 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given a visitor on the snapshot page, When they search by hospital name or city, Then matching Oklahoma and Texas rural hospitals are listed.
- Given a hospital page, When it loads, Then it shows three years of operating margin, days cash on hand and days in A/R with any flags in plain words.
- Given a hospital with missing metrics, When its page loads, Then the missing values read 'not reported' rather than zero.
- Trust: Every figure on the page shows which cost report year it came from, and the page states that public data lags one to two years.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- Search finds nothing because of spelling differences in hospital names
- The database is unreachable when a page renders
- An old fiscal year is shown as if it were current

Next.js app in web/ reading from Supabase, with the data year shown next to every figure. Run locally until STORY-005 checks the numbers.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-004 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-004` on its own line in the message, and add a PROGRESS.md entry.
```
