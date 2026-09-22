# HosPulse: Stories

12 stories across 5 releases, walking skeleton first: the
earliest release proves the thinnest end-to-end path including the trust guarantees,
and later releases stack features on top of something already working.

Generated from `.hospulse/plan.json` by `scripts/build_plan.py`. Edit the plan, not this file.

## Before the releases: start here

- **[STORY-000](stories/STORY-000.md)**: Build the Command Center

## r0 · Walking Skeleton: Public Data to Grounded Briefing (weeks 0 to 1, 2026-09-23 to 2026-10-06)

**Goal:** Prove the full chain from raw public data to a correct, traceable hospitals-at-risk briefing.
**Done when you can show:** Look up an Oklahoma rural hospital, see three years of flagged metrics with their source lines, and hand prospect #1 a briefing where every number matches the data.

- **[STORY-001](stories/STORY-001.md)**: Import public cost reports and compute hospital metrics
- **[STORY-002](stories/STORY-002.md)**: Flag at-risk hospitals with fixed warning rules _(waits on STORY-001)_
- **[STORY-003](stories/STORY-003.md)**: Write a grounded hospitals-at-risk briefing _(waits on STORY-002)_
- **[STORY-004](stories/STORY-004.md)**: Build the public Health Snapshot search and hospital page _(waits on STORY-002)_

## r1 · Public Health Snapshot Launch (week 2, 2026-10-07 to 2026-10-13)

**Goal:** Publish the free snapshot only after its numbers are checked against published financials.
**Done when you can show:** Share a public link to any Oklahoma or Texas rural hospital's snapshot in a LinkedIn post.

- **[STORY-005](stories/STORY-005.md)**: Publish the snapshot after checking numbers against published financials _(waits on STORY-004)_

## r2 · Trust Spine for Customer Data (weeks 3 to 4, 2026-10-14 to 2026-10-27)

**Goal:** Put sign-in, company isolation and the patient-data guard in place before any customer file is processed.
**Done when you can show:** Sign in as two companies and show neither can see the other, then show a file with patient names rejected before storage.

- **[STORY-006](stories/STORY-006.md)**: Sign operators in and isolate each company's hospitals _(waits on STORY-004)_
- **[STORY-007](stories/STORY-007.md)**: Accept monthly exports and reject anything with patient data _(waits on STORY-006)_

## r3 · Early Warning on Customer Data (weeks 5 to 6, 2026-10-28 to 2026-11-10)

**Goal:** Turn monthly customer exports into a live dashboard and a Monday briefing email.
**Done when you can show:** Upload a month of exports for two hospitals on different systems and receive the Monday briefing flagging the one that is slipping.

- **[STORY-008](stories/STORY-008.md)**: Normalize exports into standard monthly metrics _(waits on STORY-007)_
- **[STORY-009](stories/STORY-009.md)**: Show each managed hospital's dashboard with flags and briefings _(waits on STORY-008, STORY-003)_
- **[STORY-010](stories/STORY-010.md)**: Email the weekly hospitals-at-risk briefing on a schedule _(waits on STORY-009)_

## r4 · Cost Report Co-pilot (weeks 7 to 8, 2026-11-11 to 2026-11-24)

**Goal:** Find possible missed reimbursement, with a specialist confirming every finding.
**Done when you can show:** Run the co-pilot on one hospital's cost report and have a reimbursement specialist confirm or reject each finding on screen.

- **[STORY-011](stories/STORY-011.md)**: Find possible missed reimbursement in a cost report _(waits on STORY-008)_
- **[STORY-012](stories/STORY-012.md)**: Require specialist sign-off on every co-pilot finding _(waits on STORY-011)_
