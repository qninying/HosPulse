# STORY-010: Email the weekly hospitals-at-risk briefing on a schedule

As a Management Company CEO, I want the briefing in my inbox every Monday morning, so that I start the week knowing where to look.

**Release:** r3 · Early Warning on Customer Data (weeks 5 to 6)
**Owner:** Briefing Agent
**Blocked by:** STORY-009
**Due:** 2026-11-10 (baseline 2026-11-10)

## The requirements this satisfies

- **REQ-013** (Functional, must): The system must run the analysis weekly and email each company's briefing to its operators.
- **REQ-006** (Functional, must): The system must produce a one-page plain-English hospitals-at-risk briefing for a chosen set of hospitals.
- **REQ-016** (Measure, should): The system must surface a slipping hospital at least 4 weeks earlier than the operator's current monthly reporting.

## How to build it

GitHub Actions cron, an idempotency key of (company, week) stored before sending, and Resend with a 10 second timeout and 3 retries.

## Failure paths you must handle

- The GitHub Actions run is delayed or skipped
- Resend rate limit or outage
- An operator's email bounces

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given it is Monday 6:00 AM Central, When the scheduled run starts, Then the engine runs on the latest data and each company's operators receive their briefing by email.
- [ ] Given the run is triggered twice for the same week, When the second run happens, Then no operator receives a second email.
- [ ] Given the email service fails, When the run finishes, Then the briefing is still saved in the portal and the failure is logged with a retry.
- [ ] Trust: A company's briefing only ever goes to that company's operators.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-010: Email the weekly hospitals-at-risk briefing on a schedule.

As a Management Company CEO, I want the briefing in my inbox every Monday morning, so that I start the week knowing where to look.

Before writing any code, confirm STORY-009 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given it is Monday 6:00 AM Central, When the scheduled run starts, Then the engine runs on the latest data and each company's operators receive their briefing by email.
- Given the run is triggered twice for the same week, When the second run happens, Then no operator receives a second email.
- Given the email service fails, When the run finishes, Then the briefing is still saved in the portal and the failure is logged with a retry.
- Trust: A company's briefing only ever goes to that company's operators.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- The GitHub Actions run is delayed or skipped
- Resend rate limit or outage
- An operator's email bounces

GitHub Actions cron, an idempotency key of (company, week) stored before sending, and Resend with a 10 second timeout and 3 retries.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-010 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-010` on its own line in the message, and add a PROGRESS.md entry.
```
