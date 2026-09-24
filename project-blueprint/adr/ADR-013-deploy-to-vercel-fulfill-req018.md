# ADR-013: Deploy to Vercel to fulfill REQ-018

**Status:** Accepted (deployed and live-verified; Cron migration is a separate follow-up, see below)

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

## What was actually done

- A real Vercel project was created via the dashboard's GitHub import (root directory set to
  `frontend/`, since the Next.js app lives in a subdirectory of this repo, not the root), with
  `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` set as real Vercel environment
  variables — never `DATABASE_URL` or any service-role-equivalent secret, which stay in GitHub
  Actions' own secrets for the trusted pipeline only. Vercel only ever needs the same anon-key
  access a signed-in browser already has. Live production URL: `https://hos-pulse.vercel.app`.
- Supabase Auth's redirect-URL allowlist was updated to include
  `https://hos-pulse.vercel.app/auth/callback` alongside the existing `localhost:3000` entry.
- The full magic-link sign-in → dashboard flow (ADR-006) was re-verified against the real
  deployed origin, not just localhost — confirmed rendering the same 3 real hospitals correctly.

## Real bug found and fixed along the way

Testing the production sign-in flow hit `error=email rate limit exceeded` — Supabase's default
built-in email service has a strict per-hour send cap, already worn down by this session's own
repeated localhost + production test sends. Rather than just waiting out the limit, configured
Resend (the same account already used for weekly briefings, `pipeline/weekly_briefing_email.py`)
as Supabase Auth's custom SMTP provider (`smtp.resend.com`, port 587, sender
`onboarding@resend.dev`) — a real, permanent, production-appropriate fix rather than a one-time
workaround, since the default rate limit would have resurfaced the moment real operators started
signing in.

## Follow-up, not yet done (separate from this ADR's own scope)

- **Vercel Cron migration for the weekly briefing job** is still open: whether
  `pipeline/weekly_briefing_email.py` moves to a Vercel Cron-triggered API route, or GitHub
  Actions keeps invoking it with only its trigger source reconsidered, is a real design choice
  not yet made. [ADR-005](ADR-005-github-actions-over-vercel-cron.md) stays the record of the
  original GitHub Actions decision until this is actually decided and built.

## Consequences

- Closes REQ-018's Vercel-hosting half for real — confirmed live, not just deployed and assumed
  working.
- Introduces a third real deployment surface (Vercel) alongside the existing GitHub Actions cron
  and GitHub Pages (Command Center) for one small project — worth being deliberate about as the
  system grows, rather than accumulating hosting surfaces by accident.
- Supabase Auth's email delivery is now a real dependency on the same Resend account the weekly
  briefings already depend on — a single point of failure worth knowing about, not a hidden one.
