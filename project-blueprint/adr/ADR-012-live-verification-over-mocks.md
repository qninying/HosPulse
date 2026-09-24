# ADR-012: Live verification over mocks for I/O-touching code

**Status:** Accepted

## Context

Most of this codebase's real logic touches Postgres or a real LLM API somewhere: HCRIS import,
early-warning evaluation, export normalization, briefing generation, email delivery, cost-report
reconciliation. Standard practice would mock those boundaries in unit tests for speed and
determinism.

## Decision

Pure logic (threshold checks, discrepancy detection, prompt/fact building, retry/backoff
mechanics with a fake client) gets full `pytest` unit coverage and runs in the default `pytest
pipeline/` suite. Anything that actually touches Postgres or calls a real LLM/email API is
deliberately *not* mocked — it's verified live against production once per change, with the
verification steps and results recorded in `PROGRESS.md`, and (where practical, e.g. RLS) an
opt-in integration test gated behind an explicit env var so it never runs automatically.

## Consequences

- Every "idempotent," "retries correctly," "RLS-scoped," or "grounded" claim in this project has
  been demonstrated against the real system it describes, not just asserted against a mock that
  encodes the author's own assumptions about how Postgres or the Anthropic API actually behaves.
- This is how a real, non-mocked bug was caught live during the Cost Report Co-pilot build
  (`claude-opus-5-5` rejecting a forced `tool_choice`) that a mocked test would have hidden by
  construction, since the mock would have been written to expect the same forced-tool-choice call
  that was actually broken.
- Live verification doesn't run in CI and isn't repeatable on demand the way a mocked test suite
  is — each one is a manual, recorded event. Accepted because the alternative (trusting a mock's
  model of a real dependency) has already been shown, in this same project, to hide exactly the
  kind of bug this rule exists to catch.
