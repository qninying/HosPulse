# STORY-012: Require specialist sign-off on every co-pilot finding

As a Reimbursement Specialist, I want every finding to wait for my confirm or reject decision, so that nothing is filed on an AI suggestion alone.

**Release:** r4 · Cost Report Co-pilot (weeks 7 to 8)
**Owner:** Cost Report Co-pilot
**Blocked by:** STORY-011
**Due:** 2026-11-24 (baseline 2026-11-24)

## The requirements this satisfies

- **REQ-014** (Safety, must): The system must hold every cost report co-pilot finding as unconfirmed until a human reimbursement specialist confirms or rejects it.

## How to build it

A findings table with a status column, a separate insert-only finding_decisions table, and a database constraint so only one decision per finding can exist.

## Failure paths you must handle

- An unconfirmed finding is exported by mistake
- Two specialists decide the same finding at the same time
- The audit record write fails

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [x] Given a new co-pilot finding, When it is shown, Then it is marked 'unconfirmed' and cannot be exported as confirmed.
- [ ] Given a specialist confirms or rejects a finding, When they submit, Then the decision, their name and the time are recorded.
- [ ] Given a finding that has already been decided, When someone tries to decide it again, Then the original decision stands and the attempt is recorded.
- [ ] Trust: Every decision on a finding is kept in an append-only audit record.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-012: Require specialist sign-off on every co-pilot finding.

As a Reimbursement Specialist, I want every finding to wait for my confirm or reject decision, so that nothing is filed on an AI suggestion alone.

Before writing any code, confirm STORY-011 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given a new co-pilot finding, When it is shown, Then it is marked 'unconfirmed' and cannot be exported as confirmed.
- Given a specialist confirms or rejects a finding, When they submit, Then the decision, their name and the time are recorded.
- Given a finding that has already been decided, When someone tries to decide it again, Then the original decision stands and the attempt is recorded.
- Trust: Every decision on a finding is kept in an append-only audit record.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- An unconfirmed finding is exported by mistake
- Two specialists decide the same finding at the same time
- The audit record write fails

A findings table with a status column, a separate insert-only finding_decisions table, and a database constraint so only one decision per finding can exist.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-012 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-012` on its own line in the message, and add a PROGRESS.md entry.
```
