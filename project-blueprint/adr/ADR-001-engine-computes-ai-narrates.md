# ADR-001: Engine computes, AI only narrates

**Status:** Accepted

## Context

Three subsystems need to decide "is this hospital in trouble": the early-warning engine
(`pipeline/early_warning.py`), the slipping-hospital detector (`pipeline/slipping_detector.py`),
and the Cost Report Co-pilot's discrepancy detector (`pipeline/cost_report_copilot.py`). All
three could plausibly have asked an LLM to make the judgment call directly, given the raw
numbers, since Claude is already in the pipeline for narration.

## Decision

Every threshold and trigger is decided by plain, deterministic Python, before Claude is ever
called. Claude's only job is to write a plain-English explanation of a fact the engine already
computed. `detect_discrepancies()`'s 15% materiality check, `evaluate_early_warning_flags()`'s
margin/cash/A-R thresholds, and `evaluate_slipping()`'s month-over-month comparisons are all pure
functions with no model call inside them, fully unit-testable without a live API key.

## Consequences

- Every "why was this flagged" question has a deterministic, auditable answer — a support
  ticket or a specialist's challenge can be answered by reading the threshold constant, not by
  re-prompting a model and hoping for the same answer twice.
- Thresholds that have no stated value in a requirement (the Cost Report Co-pilot's 15%) were
  confirmed with the user as an explicit product decision, not left to the model to infer.
- The LLM's blast radius is capped: a bad Claude response can produce a badly-worded briefing,
  never a false "this hospital is fine" or a missed flag, since flagging never depended on it.
- Cost: this is more code than "just ask the model" — a real detector function, real tests, real
  threshold constants per subsystem, instead of one shared prompt.
