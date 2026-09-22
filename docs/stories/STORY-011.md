# STORY-011: Find possible missed reimbursement in a cost report

As a Reimbursement Specialist, I want likely missed reimbursement items listed with the lines that support them, so that I review the right places first.

**Release:** r4 · Cost Report Co-pilot (weeks 7 to 8)
**Owner:** Cost Report Co-pilot
**Blocked by:** STORY-008
**Due:** 2026-11-18 (baseline 2026-11-18)

## The requirements this satisfies

- **REQ-015** (Functional, should): The system must compare a hospital's cost report with its ledger totals and list possible missed reimbursement with the lines that support each item.

## How to build it

Claude Opus 5.5 with structured output. Check every cited line against the parsed cost report before a finding is shown, then call pipeline/grounding_guardrail.validate_ai_output_is_grounded on the finding text against the same parsed facts before it is saved or displayed.

## Failure paths you must handle

- The model cites a worksheet line that does not exist
- Ledger categories do not map to cost report lines
- A long cost report exceeds the context budget

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given a hospital's cost report and ledger totals for the same year, When the co-pilot runs, Then it lists possible missed items, each with the cost report line and ledger total it compared.
- [ ] Given a cost report and ledger for different years, When the co-pilot is asked to compare them, Then it refuses and says why.
- [ ] Given a finding that cites a cost report line that does not exist, When the result is checked, Then that finding is dropped.
- [ ] Given a finding whose dollar amount, percentage or day-count does not match a value in the parsed cost report and ledger facts within tolerance, When pipeline/grounding_guardrail.validate_ai_output_is_grounded runs against it, Then the finding is rejected before it reaches the specialist, per the passing tests in pipeline/test_grounding_guardrail.py.
- [ ] Trust: Every finding cites real cost report lines and ledger totals present in the input.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-011: Find possible missed reimbursement in a cost report.

As a Reimbursement Specialist, I want likely missed reimbursement items listed with the lines that support them, so that I review the right places first.

Before writing any code, confirm STORY-008 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given a hospital's cost report and ledger totals for the same year, When the co-pilot runs, Then it lists possible missed items, each with the cost report line and ledger total it compared.
- Given a cost report and ledger for different years, When the co-pilot is asked to compare them, Then it refuses and says why.
- Given a finding that cites a cost report line that does not exist, When the result is checked, Then that finding is dropped.
- Given a finding whose dollar amount, percentage or day-count does not match a value in the parsed cost report and ledger facts within tolerance, When pipeline/grounding_guardrail.validate_ai_output_is_grounded runs against it, Then the finding is rejected before it reaches the specialist, per the passing tests in pipeline/test_grounding_guardrail.py.
- Trust: Every finding cites real cost report lines and ledger totals present in the input.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- The model cites a worksheet line that does not exist
- Ledger categories do not map to cost report lines
- A long cost report exceeds the context budget

Claude Opus 5.5 with structured output. Check every cited line against the parsed cost report before a finding is shown, then call pipeline/grounding_guardrail.validate_ai_output_is_grounded on the finding text against the same parsed facts before it is saved or displayed.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-011 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-011` on its own line in the message, and add a PROGRESS.md entry.
```
