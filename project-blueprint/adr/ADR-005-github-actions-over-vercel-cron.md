# ADR-005: GitHub Actions cron over Vercel Cron

**Status:** Superseded by [ADR-013](ADR-013-deploy-to-vercel-fulfill-req018.md)

## Context

REQ-014 requires a weekly email briefing every Monday 6:00 AM Central. STORY-008's own
`task_guidance` suggested Vercel Cron. At the time this was built, the Next.js frontend had never
been deployed anywhere — no Vercel project existed — and REQ-018 (the system must use Vercel for
hosting) was not yet being actively worked toward.

## Decision (as originally made)

Used GitHub Actions cron instead, scheduled at both 11:00 and 12:00 UTC to cover the DST
transition, with a `should_run_now()` gate in Python doing the actual Central-time check. This
needed no new infrastructure beyond the repo that already existed.

## Why this is being superseded

This decision quietly deferred REQ-018 rather than resolving it, and REQ-018 is an explicit
`must`-priority constraint, not a suggestion. The user flagged this directly: avoiding a Vercel
deployment to sidestep the requirement is not an acceptable resolution. ADR-013 records the
actual plan to deploy to Vercel and fulfill REQ-018 for real, including what happens to this
cron job once a Vercel deployment exists to host Vercel Cron instead.

## Consequences of the original decision (for the record)

- Shipped REQ-014 quickly with zero new infrastructure, which was the right call given no Vercel
  project existed yet and the story was otherwise ready to verify.
- Left REQ-018 an open, honestly-flagged gap in the Knowledge Base traceability table rather than
  a silently-abandoned requirement — the gap was visible, not hidden, which is what surfaced it
  for reconsideration.
