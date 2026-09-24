# ADR-006: Supabase magic-link auth over passwords

**Status:** Accepted

## Context

The STORY-009 operator dashboard needed real authentication — the first auth code this codebase
has ever had (confirmed by a full grep before building: zero hits). Operators are provisioned by
an admin ahead of time (the same real-world flow already used for the weekly-briefing email
list), not self-service signups from the public internet.

## Decision

Real Supabase magic-link (passwordless email) sign-in via `@supabase/ssr`, rather than
email+password. No password field, no password-reset flow, no password storage or hashing
surface to secure. `middleware.ts` refreshes the session and gates only `/dashboard/*`; the
public Health Snapshot and upload pages stay unauthenticated.

## Consequences

- Removes an entire class of implementation (password reset, complexity rules, breach-list
  checks) that a provisioned-operator model doesn't need.
- The hand-seeded test `company_members` row (a random UUID from before any real auth existed)
  had to be reconciled to a real `auth.users.id` after first sign-in — a real, one-time migration
  step (`pipeline/reconcile_company_members.py`), not a null-cost decision.
- Depends on Supabase's own email deliverability and the project's Auth redirect-URL allowlist
  being configured for each real deployment origin — a manual dashboard step outside this
  codebase's own control, worth reconfirming before any deployment beyond localhost.
- No `company_members.user_id → auth.users` foreign key yet (deliberately deferred — adding it
  before reconciliation ran would have failed on the still-orphaned seeded row). A real gap until
  added.
