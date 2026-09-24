# Architecture Decision Records

Real decisions made while building HosPulse, written down after the fact from what actually
shipped (`PROGRESS.md`, commit history) rather than drafted up front. Each one names the
alternative that was passed over and why, so a later session doesn't silently re-litigate it.

Status is one of `Accepted`, `Proposed`, or `Superseded by ADR-NNN`.

| # | Title | Status |
|---|---|---|
| [001](ADR-001-engine-computes-ai-narrates.md) | Engine computes, AI only narrates | Accepted |
| [002](ADR-002-grounding-runtime-gate.md) | Grounding as a runtime gate, not a prompt instruction | Accepted |
| [003](ADR-003-rls-multitenancy-trusted-pipeline-bypass.md) | Multi-tenancy via Postgres RLS, pipeline as a trusted bypass role | Accepted |
| [004](ADR-004-idempotency-natural-key-upsert-execution-log.md) | Idempotency via natural-key UPSERT + a shared execution-state log | Accepted |
| [005](ADR-005-github-actions-over-vercel-cron.md) | GitHub Actions cron over Vercel Cron | Superseded by [ADR-013](ADR-013-deploy-to-vercel-fulfill-req018.md) |
| [006](ADR-006-supabase-magic-link-auth.md) | Supabase magic-link auth over passwords | Accepted |
| [007](ADR-007-no-frontend-framework.md) | No frontend framework or component library | Accepted |
| [008](ADR-008-static-command-center-no-live-db.md) | Static Command Center, no live DB connection | Accepted |
| [009](ADR-009-cost-report-copilot-scope-lock.md) | Cost Report Co-pilot scoped to cash + A/R only | Accepted |
| [010](ADR-010-no-fabricated-values.md) | No value that could be mistaken for real | Accepted |
| [011](ADR-011-dual-numbering-reconciliation.md) | Reconcile dual story-numbering by auditing overlap, not rebuilding | Accepted |
| [012](ADR-012-live-verification-over-mocks.md) | Live verification over mocks for I/O-touching code | Accepted |
| [013](ADR-013-deploy-to-vercel-fulfill-req018.md) | Deploy to Vercel to fulfill REQ-018 | Accepted |
| [014](ADR-014-supabase-storage-service-role.md) | Supabase Storage via a service_role key, not the anon key | Accepted |
