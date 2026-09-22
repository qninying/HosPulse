# STORY-001: Import public cost reports and compute hospital metrics

As a Management Company COO, I want every Oklahoma and Texas rural hospital's margin, days cash on hand and days in A/R computed from public cost reports, so that I can compare my hospitals against their peers.

**Release:** r0 · Walking Skeleton: Public Data to Grounded Briefing (weeks 0 to 1)
**Owner:** Data Pipeline
**Blocked by:** nothing, you can start this now
**Due:** 2026-09-27 (baseline 2026-09-27)

## The requirements this satisfies

- **REQ-001** (Functional, must): The system must import CMS HCRIS cost reports for rural and Critical Access Hospitals in Oklahoma and Texas and compute operating margin, days cash on hand and days in A/R per hospital per year.
- **REQ-003** (Safety, must): The system must make every displayed or briefed number traceable to the public cost report line or uploaded file row it came from.
- **REQ-007** (Reliability, must): The system must make every import, load and normalization run idempotent, so re-running it leaves the same data with no duplicates.
- **REQ-018** (Constraint, must): The system must use the public CMS HCRIS cost report files as its Phase 0 data source.

## How to build it

Use Python with DuckDB to read the HCRIS report, numeric and alpha files, then upsert into Supabase Postgres keyed on (provider number, fiscal year). Select rural and Critical Access Hospitals by CMS provider type and state code.

## Failure paths you must handle

- CMS download times out or returns a partial file
- HCRIS column layout changes between years
- A hospital's cost report is missing worksheet lines a metric needs

## Acceptance: your stop condition

Ticks mirror `.hospulse/progress.json`, which is the source of truth. Set `passed` there,
then run `python3 scripts/build_plan.py` to refresh this file.

- [ ] Given the latest three years of CMS HCRIS files, When the importer runs, Then every rural and Critical Access Hospital in Oklahoma and Texas has a yearly row with operating margin, days cash on hand and days in A/R.
- [ ] Given the importer has already run, When it runs again on the same files, Then the database holds exactly the same rows with no duplicates.
- [ ] Given a cost report missing a field a metric needs, When the importer runs, Then that metric is stored as missing with a reason, never as zero.
- [ ] Trust: Every stored metric records the cost report ID, worksheet and line it was computed from.

---

## Build prompt

Copy everything below this line into Claude Code to build this story.

```
Implement STORY-001: Import public cost reports and compute hospital metrics.

As a Management Company COO, I want every Oklahoma and Texas rural hospital's margin, days cash on hand and days in A/R computed from public cost reports, so that I can compare my hospitals against their peers.

Before writing any code, confirm nothing (this story has no dependencies) is already built and working.
If it isn't, stop and say so rather than building on top of something that doesn't exist yet.

Build only what this story needs. Don't build ahead into another story's scope.

Acceptance criteria. All of these must genuinely pass, not just the happy path:
- Given the latest three years of CMS HCRIS files, When the importer runs, Then every rural and Critical Access Hospital in Oklahoma and Texas has a yearly row with operating margin, days cash on hand and days in A/R.
- Given the importer has already run, When it runs again on the same files, Then the database holds exactly the same rows with no duplicates.
- Given a cost report missing a field a metric needs, When the importer runs, Then that metric is stored as missing with a reason, never as zero.
- Trust: Every stored metric records the cost report ID, worksheet and line it was computed from.

Handle these failure paths explicitly; none may surface as an unhandled exception or a silent no-op:
- CMS download times out or returns a partial file
- HCRIS column layout changes between years
- A hospital's cost report is missing worksheet lines a metric needs

Use Python with DuckDB to read the HCRIS report, numeric and alpha files, then upsert into Supabase Postgres keyed on (provider number, fiscal year). Select rural and Critical Access Hospitals by CMS provider type and state code.

When you believe the story is done:
1. Tests cover the happy path and at least one failure path above.
2. Re-check every criterion against what the code actually does.
3. No secrets or patient data in code, commits, or logs. Every side effect is idempotent.
4. In .hospulse/progress.json set `passed` on each criterion of STORY-001 that is truly met, fill
   files_touched and tests_added, then run `python3 scripts/build_plan.py`.
5. Commit with `Story: STORY-001` on its own line in the message, and add a PROGRESS.md entry.
```
