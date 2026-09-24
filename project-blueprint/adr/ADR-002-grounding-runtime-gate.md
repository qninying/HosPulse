# ADR-002: Grounding as a runtime gate, not a prompt instruction

**Status:** Accepted

## Context

REQ-006 requires rejecting any AI-generated briefing that states a number not in the input data.
The obvious first line of defense is prompt wording ("only use the numbers given below, never
invent one") — briefing_agent.py and cost_report_copilot.py both do this — but a prompt
instruction is a request, not a guarantee, and this system makes real financial claims about
real hospitals.

## Decision

`pipeline/grounding_guardrail.py`'s `validate_ai_output_is_grounded(text, allowed_facts)` scans
the model's actual output text for dollar/percent/day-shaped figures and checks each one against
the exact facts the engine computed, within a fixed numeric tolerance. A response that fails this
check is never persisted — `UngroundedBriefing` (Briefing Agent) or a per-finding drop (Cost
Report Co-pilot) — regardless of how well-worded the prompt was. The same function is reused by
both agents rather than each writing its own check.

## Consequences

- The guarantee holds even if a future prompt change, a model upgrade, or a completely different
  third agent forgets to ask nicely — the gate is in the code path, not the prompt text.
- Cost Report Co-pilot's grounding check runs per-finding, not per-batch, so one invented number
  drops only that finding rather than an entire valid batch — a deliberate refinement over the
  Briefing Agent's original all-or-nothing behavior, made because the acceptance criteria for
  that story were phrased per-finding.
- The check only recognizes three figure shapes (dollar, percent, days) with fixed tolerances —
  a genuinely new figure kind (e.g. a raw headcount) would silently pass ungrounded. Documented,
  not yet a problem, since nothing in this system currently states that kind of figure.
