# STORY-007: Accept monthly exports and reject anything with patient data

As a Management Company CFO, I want to upload each hospital's monthly financial exports safely, so that HosPulse can track them without ever holding patient data.

**Release:** r2 · Trust Spine for Customer Data (weeks 3 to 4)
**Owner:** Operator Portal
**Blocked by:** STORY-006
**Due:** 2026-10-27 (baseline 2026-10-27)

## The requirements this satisfies

- **REQ-009** (Safety, must): The system must reject any upload that contains patient-identifying data before it is stored or logged.
- **REQ-010** (Functional, must): The system must let operators upload monthly GL, A/R aging, denials summary and staffing exports for each managed hospital.
- **REQ-003** (Safety, must): The system must make every displayed or briefed number traceable to the public cost report line or uploaded file row it came from.
- **REQ-007** (Reliability, must): The system must make every import, load and normalization run idempotent, so re-running it leaves the same data with no duplicates.

## How to build it

Check each file against a strict allowed-column list per export type first, then run Microsoft Presidio on text columns. Store accepted files in a private Supabase Storage bucket keyed on the file's SHA-256.

## Failure paths you must handle

- Patient names hidden in a free-text memo column
- Upload of a large Excel file times out
- The wrong hospital is selected for a file

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given a GL, A/R aging, denials summary or staffing export with only allowed columns, When an operator uploads it, Then the original file is stored privately and linked to the hospital and month.
- [ ] Given a file containing a column or value that looks like patient data (names, birth dates, record numbers), When it is uploaded, Then it is rejected before storage with a message saying why.
- [ ] Given the same file is uploaded twice, When the second upload arrives, Then it is recognized as a duplicate and not stored again.
- [ ] Trust: No rejected file, or any part of it, is ever written to storage or logs.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-007: Accept monthly exports and reject anything with patient data.

As a Management Company CFO, I want to upload each hospital's monthly financial exports safely, so that HosPulse can track them without ever holding patient data.

Before writing any code, confirm STORY-006 is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given a GL, A/R aging, denials summary or staffing export with only allowed columns, When an operator uploads it, Then the original file is stored privately and linked to the hospital and month.
- Given a file containing a column or value that looks like patient data (names, birth dates, record numbers), When it is uploaded, Then it is rejected before storage with a message saying why.
- Given the same file is uploaded twice, When the second upload arrives, Then it is recognized as a duplicate and not stored again.
- Trust: No rejected file, or any part of it, is ever written to storage or logs.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- Patient names hidden in a free-text memo column
- Upload of a large Excel file times out
- The wrong hospital is selected for a file

Check each file against a strict allowed-column list per export type first, then run Microsoft Presidio on text columns. Store accepted files in a private Supabase Storage bucket keyed on the file's SHA-256.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-007 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-007` on its own line in the message, and add a PROGRESS.md entry.
```
