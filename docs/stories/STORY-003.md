# STORY-003: Write a grounded hospitals-at-risk briefing

As a Management Company CEO, I want a one-page plain-English briefing on which hospitals need attention and why, so that I can act without reading spreadsheets.

**Release:** r0 · Walking Skeleton: Public Data to Grounded Briefing (weeks 0 to 1)
**Owner:** Briefing Agent
**Blocked by:** STORY-002
**Due:** 2026-10-03 (baseline 2026-10-03)

## The requirements this satisfies

- **REQ-006** (Functional, must): The system must produce a one-page plain-English hospitals-at-risk briefing for a chosen set of hospitals.
- **REQ-004** (Safety, must): The system must reject any AI-written briefing that contains a number not present in the early-warning engine's output.
- **REQ-019** (Constraint, must): The system must run on Supabase, Vercel, the Anthropic Claude API and Resend.

## How to build it

Pass only engine output (metrics and flags) as structured input, extract every number from the response and check it against the input before saving. 30 second timeout, at most 3 retries with backoff.

## Failure paths you must handle

- The model invents a figure or rounds one differently from the data
- Claude API timeout or rate limit
- The briefing leaves out a flagged hospital

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given a list of hospitals, When the briefing script runs, Then Claude Sonnet 5 produces a one-page briefing covering every flagged hospital in the list.
- [ ] Given a briefing that contains a number not present in the engine's output, When the grounding check runs, Then the briefing is rejected and not saved.
- [ ] Given the Claude API times out or errors, When the script runs, Then it retries a capped number of times and then fails with a clear message, saving nothing partial.
- [ ] Trust: Every number in a saved briefing matches a stored metric or flag value.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-003: Write a grounded hospitals-at-risk briefing.

As a Management Company CEO, I want a one-page plain-English briefing on which hospitals need attention and why, so that I can act without reading spreadsheets.

Before writing any code, confirm STORY-002 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given a list of hospitals, When the briefing script runs, Then Claude Sonnet 5 produces a one-page briefing covering every flagged hospital in the list.
- Given a briefing that contains a number not present in the engine's output, When the grounding check runs, Then the briefing is rejected and not saved.
- Given the Claude API times out or errors, When the script runs, Then it retries a capped number of times and then fails with a clear message, saving nothing partial.
- Trust: Every number in a saved briefing matches a stored metric or flag value.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- The model invents a figure or rounds one differently from the data
- Claude API timeout or rate limit
- The briefing leaves out a flagged hospital

Pass only engine output (metrics and flags) as structured input, extract every number from the response and check it against the input before saving. 30 second timeout, at most 3 retries with backoff.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-003 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-003` on its own line in the message, and add a PROGRESS.md entry.
```
