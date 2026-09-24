# ADR-014: Supabase Storage via a service_role key, not the anon key

**Status:** Accepted

## Context

REQ-017's last remaining gap was Supabase Storage — uploaded export files were parsed for
metrics but the raw bytes never persisted anywhere (`frontend/src/app/api/upload/route.ts`
writes to a temp directory and `rm -rf`s it in a `finally` block regardless of outcome). The
Next.js upload route has only the anon key (confirmed: no service-role-equivalent secret exists
anywhere in this project's env files before this decision). Two ways to let it write to Storage:
add a Storage policy permitting the anon key to write, or give the trusted Python pipeline a real
service_role key and have archival happen there instead.

## Decision

The Python pipeline (`pipeline/supabase_storage.py`) got a real Supabase `service_role` key,
read from the repo-root `.env`, never referenced anywhere in `frontend/`. This mirrors the exact
trust model already used for every Postgres write in this project: a trusted backend bypasses
access control (RLS for Postgres, Storage policies for Storage); the anon key stays read-only
and stays out of the write path entirely. The `hospital-exports` bucket has zero Storage
policies — fails closed by default, identical to how `export_conversions` started with zero RLS
policies before STORY-006 added company scoping.

The archive call sits inside `export_normalizer.py`'s `_store()` closure, which
`phi_guardrail.ingest_file_with_phi_gate()` only invokes after confirming a file is PHI-clean —
live-verified: a PHI-bearing file produces zero Postgres rows and a 400 (object not found) when
queried against the exact path its hash would have used.

A Storage upload failure never fails the conversion — `upload_export_file()` returns `None`
rather than raising, `export_conversions.storage_path` stays `NULL` (honestly meaning "not
archived," never a lie that it worked), and the metrics — the primary, already-proven value —
still save. Confirmed live: this was not a hypothetical, the first real Storage bucket didn't
exist yet when the code was written, and the pipeline degraded gracefully (logged a warning,
`storage_path = NULL`) rather than crashing, until the bucket and key were actually provisioned.

## Consequences

- Closes REQ-017 fully: Postgres, Auth (ADR-006), and now Storage are all genuinely real, no
  bundled requirement left half-true.
- Introduces a second real secret credential type in this project (alongside `DATABASE_URL`) that
  fully bypasses access control if leaked — the `service_role` key lives only in the repo-root
  `.env`, which is gitignored and confirmed absent from git history, same handling as every other
  real secret in this project.
- No retrieval UI was built — nothing reads these files back yet. A future specialist-review
  flow (`.hospulse` STORY-012) is the real, anticipated consumer; building read access before a
  real reader exists would repeat the same premature-Storage-bucket reasoning STORY-005 already
  rejected once.
- The anon-key-only Next.js route still never touches Supabase directly — this decision changed
  nothing about that route, keeping the existing, already-tested upload flow's trust boundary
  exactly where it was.
