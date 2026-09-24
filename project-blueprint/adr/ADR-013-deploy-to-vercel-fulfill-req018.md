# ADR-013: Deploy to Vercel to fulfill REQ-018

**Status:** Proposed (not yet implemented)

## Context

REQ-018 is an explicit `must`-priority constraint: "The system must use Vercel for hosting and
the Anthropic Claude API for AI." The Claude API half is genuinely fulfilled (both real agents
call it, live-verified). The Vercel-hosting half was never fulfilled — [ADR-005](ADR-005-github-actions-over-vercel-cron.md)
used GitHub Actions cron instead, and the Next.js frontend has never been deployed anywhere. This
showed up as a real, correctly-flagged gap in the Knowledge Base traceability table
(`REQ-018: unfulfilled`), which is what surfaced it for a decision rather than leaving it quietly
deferred.

The user was explicit: avoiding a Vercel deployment to sidestep the requirement is not an
acceptable resolution. This ADR records the decision to deploy for real.

## Decision

Deploy the `frontend/` Next.js app to Vercel as the system's real hosting, fulfilling REQ-018's
Vercel half directly. This supersedes ADR-005: once a real Vercel deployment exists, the weekly
briefing email job's scheduling should move from GitHub Actions cron to Vercel Cron, which is
what STORY-008's own original `task_guidance` suggested before ADR-005 deferred it for lack of a
deployment target.

## What this requires (not yet done as of this ADR)

- A Vercel project connected to this GitHub repo, with `NEXT_PUBLIC_SUPABASE_URL` and
  `NEXT_PUBLIC_SUPABASE_ANON_KEY` set as real Vercel environment variables (never the
  `DATABASE_URL`/service-role-equivalent secrets, which stay in GitHub Actions' own secrets for
  the trusted pipeline only — Vercel only ever needs the same anon-key access a signed-in
  browser already has).
- Supabase Auth's redirect-URL allowlist updated to include the real Vercel-assigned (or custom)
  production origin, not just `localhost:3000` (flagged as an open item in ADR-006).
- A decision on whether `pipeline/weekly_briefing_email.py` moves to a Vercel Cron-triggered API
  route or stays a GitHub Actions-invoked script that merely gets its scheduling trigger changed
  — a real design choice, not assumed here.
- Re-verification of the full auth/dashboard flow (ADR-006) against the real deployed origin, not
  just localhost.

## Consequences (anticipated)

- Closes REQ-018 for real rather than leaving it a permanent, accepted gap.
- Introduces a second real deployment target (Vercel) alongside the existing GitHub Actions cron
  and GitHub Pages (Command Center) — three separate hosting surfaces for one small project,
  worth being deliberate about rather than accumulating by accident.
- Vercel's own environment variable and preview-deployment model needs to be understood before
  wiring secrets into it, to avoid a real secret ending up in a preview-deployment log or a
  public preview URL.
