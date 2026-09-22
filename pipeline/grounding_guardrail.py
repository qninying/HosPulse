"""Grounding guardrail: the shared check that keeps every HosPulse AI output
from stating a financial figure that was not actually handed to it.

This is HosPulse's single most important trust guarantee, the one sentence
the architecture is built around: "every number can be traced back to the
exact source line it came from and the AI never invents a figure." Two
places call this:

- The weekly briefing agent (REQ-004, STORY-003): Claude writes plain
  English from the early-warning engine's computed metrics and flags.
- The cost report co-pilot (STORY-011): Claude compares a cost report
  against ledger totals and lists possible missed reimbursement.

Both share the same failure mode, and it is the worst thing HosPulse could
do: state a dollar amount, a percentage, or a day-count that the
deterministic engine never computed. A briefing an executive acts on, or a
reimbursement finding that ends up on a claim filed with a government
payer, is unsafe the moment it contains a number nobody can trace back to
real data. This module is the one place that check lives, so both callers
enforce it the same way.

Usage at the call site (once STORY-003 / STORY-011 exist):

    facts = {"operating_margin": engine.margin, "days_cash": engine.days_cash}
    result = validate_ai_output_is_grounded(claude_response_text, facts)
    if not result.ok:
        log.error("ungrounded_ai_output", reason=result.reason())
        return None  # reject the whole output; never save it partially

Deliberately scoped narrower than "every number in the text": a bare count
("3 hospitals need attention") or a year ("in 2026") is not a financial
claim and is left alone, so the guardrail does not reject ordinary prose
sentences. It checks the three shapes that actually carry a financial or
metric claim in HosPulse's output: a dollar amount, a percentage, and a
day-count (days cash on hand, days in A/R). A companion check for whether a
cost report co-pilot finding cites a real worksheet line (rather than a
real number) is a related but separate concern, not covered here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from numbers import Real

_DOLLAR_RE = re.compile(r"\(?-?\$-?[\d,]+(?:\.\d+)?\)?")
_PERCENT_RE = re.compile(r"\(?-?[\d,]+(?:\.\d+)?%\)?")
_DAYS_RE = re.compile(r"-?[\d,]+(?:\.\d+)?\s*days?\b", re.IGNORECASE)

# Absolute tolerance per kind: generous enough for reasonable display
# rounding (the engine may store more precision than the AI displays),
# tight enough that a genuinely different figure still gets caught.
_TOLERANCE = {
    "dollar": Decimal("0.50"),
    "percent": Decimal("0.05"),
    "days": Decimal("0.5"),
}


@dataclass(frozen=True)
class UngroundedValue:
    """One number in the AI's text that could not be matched to a supplied fact."""

    raw_text: str
    kind: str  # "dollar" | "percent" | "days"
    value: Decimal | None  # None if the token matched the pattern but failed to parse


@dataclass(frozen=True)
class GroundingResult:
    ok: bool
    ungrounded: list[UngroundedValue] = field(default_factory=list)

    def reason(self) -> str:
        if self.ok:
            return "every dollar amount, percentage and day-count matches a supplied fact"
        parts = ", ".join(f"{u.raw_text!r} ({u.kind})" for u in self.ungrounded)
        return f"{len(self.ungrounded)} figure(s) not present in the input data: {parts}"


def _parse_signed_number(raw: str) -> Decimal | None:
    """'$(1,234.50)' -> -1234.50, '-4.1%' -> -4.1, '22 days' -> 22.

    A literal '-' or a wrapping '(' anywhere in the token means negative
    (both plain negative signs and accounting parenthesis notation are in
    real use in financial exports). Returns None if the token contains no
    usable digits or more than one decimal point.
    """
    negative = "(" in raw or "-" in raw
    digits_only = re.sub(r"[^0-9.]", "", raw)
    if not digits_only or digits_only.count(".") > 1:
        return None
    try:
        magnitude = Decimal(digits_only)
    except InvalidOperation:
        return None
    return -magnitude if negative else magnitude


def _extract_candidates(text: str) -> list[tuple[str, str, Decimal | None]]:
    """Every dollar amount, percentage and day-count found in text, in order,
    as (raw_matched_text, kind, parsed_value_or_None)."""
    found: list[tuple[str, str, Decimal | None]] = []
    for pattern, kind in ((_DOLLAR_RE, "dollar"), (_PERCENT_RE, "percent"), (_DAYS_RE, "days")):
        for match in pattern.finditer(text):
            raw = match.group(0)
            found.append((raw, kind, _parse_signed_number(raw)))
    return found


def validate_ai_output_is_grounded(
    text: str,
    allowed_facts: dict[str, Real],
) -> GroundingResult:
    """Check that every dollar amount, percentage and day-count in `text`
    matches a value in `allowed_facts` (the deterministic engine's output),
    within a small tolerance for display rounding.

    `allowed_facts` values may be Decimal, int, or float; they are
    converted to Decimal for comparison, so the caller does not have to
    pre-convert the engine's own numbers. An empty or falsy `text` is
    trivially grounded. A token that looks like a dollar/percent/days
    figure but fails to parse counts as ungrounded rather than being
    silently skipped -- an unparseable figure is exactly the kind of thing
    that should stop the output, not slip through unnoticed.
    """
    if not text:
        return GroundingResult(ok=True)

    allowed = [Decimal(str(v)) for v in allowed_facts.values()]

    ungrounded: list[UngroundedValue] = []
    for raw, kind, value in _extract_candidates(text):
        matched = value is not None and any(abs(value - a) <= _TOLERANCE[kind] for a in allowed)
        if not matched:
            ungrounded.append(UngroundedValue(raw_text=raw, kind=kind, value=value))

    return GroundingResult(ok=not ungrounded, ungrounded=ungrounded)
