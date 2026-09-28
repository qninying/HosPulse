# STORY-002 — Compute Financial Metrics and Ensure Trust Spine

As a system operator, I want to compute financial metrics from imported data, so that I can ensure accurate and trustworthy reporting.

**Release:** r0 · Initial Setup and Data Import (weeks 1–2)
**Owner:** system
**Blocked by:** nothing — you can start this now

## The requirement this satisfies

- **REQ-002** (Functional, must) — The system must compute operating margin, days cash on hand, and days in A/R per hospital per year from the imported data.
- **REQ-013** (Safety, must) — The system must link every computed metric back to the file and row it came from.

## How to build it

Implement computation logic to process imported data and generate metrics. Ensure each metric is linked to its source file and row in the audit trail.

## Failure paths you must handle

- Data import fails
- Metric computation error
- Audit trail linkage failure

## Acceptance — your stop condition

Tick each box as it genuinely passes. This file is yours — the platform reads
the same criteria out of `.colaberry/progress.json`, which Claude Code keeps in
step (see the managed block in CLAUDE.md). Ticking something you have not
actually met only misleads you.

- [ ] Given a set of imported data, when the system computes financial metrics, then it should produce a standard set of metrics per hospital per year.
- [ ] Given a computed metric, when traced, then it should link back to the original file and row it came from.
- [ ] Trust: Given any computation, when logged, then it should include an audit trail linking metrics to source data.

When every box above is ticked, stop and show the demo.
