# STORY-005: Publish the snapshot after checking numbers against published financials

As a HosPulse Founder, I want the public snapshot live only after its numbers match published hospital financials, so that the first thing prospects see is correct.

**Release:** r1 · Public Health Snapshot Launch (week 2)
**Owner:** Snapshot Site
**Blocked by:** STORY-004
**Due:** 2026-10-13 (baseline 2026-10-13)

## The requirements this satisfies

- **REQ-002** (Functional, must): The system must provide a public Health Snapshot where anyone can search for a rural hospital and see its metrics and three-year trend without an account.
- **REQ-019** (Constraint, must): The system must run on Supabase, Vercel, the Anthropic Claude API and Resend.

## How to build it

Keep checks/published_financials.csv and a pytest that compares against it. Deploy with Vercel, with environment variables set only in the Vercel dashboard.

## Failure paths you must handle

- Our days cash formula differs from how auditors compute it
- Vercel build fails on a missing environment variable
- The Supabase free tier pauses the database for inactivity

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given five hospitals with published audited financials, When their snapshot metrics are compared, Then each metric is within 2 percentage points or 5 days of the published figure, or the difference is explained in writing.
- [ ] Given the check passes, When the site is deployed to Vercel, Then the public URL serves every hospital page.
- [ ] Given a deploy fails, When a previous version exists, Then the previous version stays live.
- [ ] Trust: No page shows a metric from a formula that failed the comparison check.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-005: Publish the snapshot after checking numbers against published financials.

As a HosPulse Founder, I want the public snapshot live only after its numbers match published hospital financials, so that the first thing prospects see is correct.

Before writing any code, confirm STORY-004 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given five hospitals with published audited financials, When their snapshot metrics are compared, Then each metric is within 2 percentage points or 5 days of the published figure, or the difference is explained in writing.
- Given the check passes, When the site is deployed to Vercel, Then the public URL serves every hospital page.
- Given a deploy fails, When a previous version exists, Then the previous version stays live.
- Trust: No page shows a metric from a formula that failed the comparison check.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- Our days cash formula differs from how auditors compute it
- Vercel build fails on a missing environment variable
- The Supabase free tier pauses the database for inactivity

Keep checks/published_financials.csv and a pytest that compares against it. Deploy with Vercel, with environment variables set only in the Vercel dashboard.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-005 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-005` on its own line in the message, and add a PROGRESS.md entry.
```
