# HosPulse: Requirements

Early-warning intelligence for companies that manage rural hospitals: one view across every managed hospital, fixed and tested warning rules, and a plain-English weekly briefing, built without patient data.

Generated from `.hospulse/plan.json` by `scripts/build_plan.py`. Edit the plan, not this file.

| Kind | Meaning |
|---|---|
| Functional | something the system does |
| Safety | a guardrail, with a check that enforces it |
| Reliability | how it behaves when something fails |
| Measure | a number the system has to move |
| Constraint | a platform or data source we must use, context rather than a task |

## Public Data

### REQ-001: Functional · must

The system must import CMS HCRIS cost reports for rural and Critical Access Hospitals in Oklahoma and Texas and compute operating margin, days cash on hand and days in A/R per hospital per year.

Fulfilled by: STORY-001

### REQ-002: Functional · must

The system must provide a public Health Snapshot where anyone can search for a rural hospital and see its metrics and three-year trend without an account.

Fulfilled by: STORY-004, STORY-005

## Trust

### REQ-003: Safety · must

The system must make every displayed or briefed number traceable to the public cost report line or uploaded file row it came from.

Fulfilled by: STORY-001, STORY-002, STORY-004, STORY-007

### REQ-004: Safety · must

The system must reject any AI-written briefing that contains a number not present in the early-warning engine's output.

Fulfilled by: STORY-003

## Early Warning

### REQ-005: Functional · must

The system must flag hospitals using fixed, tested rules and store the metric values that triggered each flag.

Fulfilled by: STORY-002, STORY-009

## Briefing

### REQ-006: Functional · must

The system must produce a one-page plain-English hospitals-at-risk briefing for a chosen set of hospitals.

Fulfilled by: STORY-003, STORY-010

### REQ-013: Functional · must

The system must run the analysis weekly and email each company's briefing to its operators.

Fulfilled by: STORY-010

## Data Pipeline

### REQ-007: Reliability · must

The system must make every import, load and normalization run idempotent, so re-running it leaves the same data with no duplicates.

Fulfilled by: STORY-001, STORY-007, STORY-008

## Access Control

### REQ-008: Safety · must

The system must require operators to sign in and must only ever show a management company the hospitals it manages.

Fulfilled by: STORY-006

### REQ-009: Safety · must

The system must reject any upload that contains patient-identifying data before it is stored or logged.

Fulfilled by: STORY-007

## Customer Data

### REQ-010: Functional · must

The system must let operators upload monthly GL, A/R aging, denials summary and staffing exports for each managed hospital.

Fulfilled by: STORY-007

### REQ-011: Functional · must

The system must convert exports from different hospital systems into one standard set of monthly metrics per hospital.

Fulfilled by: STORY-008

## Operator Portal

### REQ-012: Functional · must

The system must show operators a dashboard of every managed hospital with its metrics, trends, flags and past briefings.

Fulfilled by: STORY-009

## Cost Report Co-pilot

### REQ-014: Safety · must

The system must hold every cost report co-pilot finding as unconfirmed until a human reimbursement specialist confirms or rejects it.

Fulfilled by: STORY-012

### REQ-015: Functional · should

The system must compare a hospital's cost report with its ledger totals and list possible missed reimbursement with the lines that support each item.

Fulfilled by: STORY-011

## Outcomes

### REQ-016: Measure · should

The system must surface a slipping hospital at least 4 weeks earlier than the operator's current monthly reporting.

Fulfilled by: STORY-010

### REQ-017: Measure · should

The system must run for under $200 a month until it has 10 paying customers.

Fulfilled by: no story yet (a measure tracked over time, not a build task)

## Platforms

### REQ-018: Constraint · must

The system must use the public CMS HCRIS cost report files as its Phase 0 data source.

Fulfilled by: STORY-001

### REQ-019: Constraint · must

The system must run on Supabase, Vercel, the Anthropic Claude API and Resend.

Fulfilled by: STORY-003, STORY-005, STORY-006
