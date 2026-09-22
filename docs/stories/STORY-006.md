# STORY-006: Sign operators in and isolate each company's hospitals

As a Management Company COO, I want to sign in and see only the hospitals my company manages, so that our data never leaks to another company.

**Release:** r2 · Trust Spine for Customer Data (weeks 3 to 4)
**Owner:** Operator Portal
**Blocked by:** STORY-004
**Due:** 2026-10-20 (baseline 2026-10-20)

## The requirements this satisfies

- **REQ-008** (Safety, must): The system must require operators to sign in and must only ever show a management company the hospitals it manages.
- **REQ-019** (Constraint, must): The system must run on Supabase, Vercel, the Anthropic Claude API and Resend.

## How to build it

Supabase Auth with companies and company_members tables, row-level security on every customer table, and a test that signs in as two companies.

## Failure paths you must handle

- A new table ships without a row-level security policy
- The session expires in the middle of an upload
- An operator is assigned to the wrong company

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given an operator from company A, When they sign in, Then they see only company A's hospitals.
- [ ] Given an operator from company A, When they request a company B hospital by ID or URL, Then the request is refused and nothing from company B is returned.
- [ ] Given a signed-out visitor, When they open any portal page, Then they are sent to sign in.
- [ ] Trust: Company isolation is enforced by database row-level security, and a test proves a cross-company query returns zero rows.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-006: Sign operators in and isolate each company's hospitals.

As a Management Company COO, I want to sign in and see only the hospitals my company manages, so that our data never leaks to another company.

Before writing any code, confirm STORY-004 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given an operator from company A, When they sign in, Then they see only company A's hospitals.
- Given an operator from company A, When they request a company B hospital by ID or URL, Then the request is refused and nothing from company B is returned.
- Given a signed-out visitor, When they open any portal page, Then they are sent to sign in.
- Trust: Company isolation is enforced by database row-level security, and a test proves a cross-company query returns zero rows.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- A new table ships without a row-level security policy
- The session expires in the middle of an upload
- An operator is assigned to the wrong company

Supabase Auth with companies and company_members tables, row-level security on every customer table, and a test that signs in as two companies.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-006 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-006` on its own line in the message, and add a PROGRESS.md entry.
```
