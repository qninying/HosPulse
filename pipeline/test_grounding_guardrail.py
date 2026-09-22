"""Tests for the grounding guardrail (pipeline/grounding_guardrail.py).

Run: cd HosPulse && ./.venv/bin/python -m pytest pipeline/ -v
"""

from decimal import Decimal

from grounding_guardrail import validate_ai_output_is_grounded


ENGINE_FACTS = {
    "operating_margin_pct": Decimal("-4.1"),
    "days_cash_on_hand": 22,
    "days_in_ar": Decimal("58.0"),
    "denial_increase_dollars": Decimal("184200.00"),
}


def test_happy_path_every_figure_matches_a_supplied_fact():
    text = (
        "Prairie County Memorial: days cash on hand fell to 22 days, "
        "operating margin is -4.1%, driven by $184,200.00 in new denials."
    )
    result = validate_ai_output_is_grounded(text, ENGINE_FACTS)
    assert result.ok
    assert result.ungrounded == []
    assert "matches a supplied fact" in result.reason()


def test_rejects_a_dollar_amount_not_in_the_data():
    text = "Estimated impact: $250,000 in lost revenue."
    result = validate_ai_output_is_grounded(text, ENGINE_FACTS)
    assert not result.ok
    assert len(result.ungrounded) == 1
    assert result.ungrounded[0].kind == "dollar"
    assert result.ungrounded[0].value == Decimal("250000")


def test_rejects_a_percentage_not_in_the_data():
    text = "Operating margin is -6.5% this quarter."
    result = validate_ai_output_is_grounded(text, ENGINE_FACTS)
    assert not result.ok
    assert result.ungrounded[0].kind == "percent"


def test_rejects_a_days_figure_not_in_the_data():
    text = "Days cash on hand dropped to 15 days."
    result = validate_ai_output_is_grounded(text, ENGINE_FACTS)
    assert not result.ok
    assert result.ungrounded[0].kind == "days"


def test_reports_every_ungrounded_value_not_just_the_first():
    text = "Cash is at 15 days and margin is -9.9%, an invented $99,000 gap."
    result = validate_ai_output_is_grounded(text, ENGINE_FACTS)
    assert not result.ok
    assert len(result.ungrounded) == 3
    assert {u.kind for u in result.ungrounded} == {"days", "percent", "dollar"}


def test_accounting_parens_negative_dollar_is_parsed_and_matched():
    # $184,200.00 in the facts; the AI phrases the same figure in
    # parenthesis notation, common in financial exports.
    text = "This showed up as $(184,200.00) on the denial summary."
    result = validate_ai_output_is_grounded(text, ENGINE_FACTS)
    assert result.ok


def test_negative_percent_in_parens_is_parsed_and_matched():
    text = "Margin came in at (4.1%) for the month."
    result = validate_ai_output_is_grounded(text, ENGINE_FACTS)
    assert result.ok


def test_display_rounding_within_tolerance_is_accepted():
    facts = {"days_cash": Decimal("21.67")}
    result = validate_ai_output_is_grounded("Down to 22 days of cash.", facts)
    assert result.ok  # 21.67 rounds to 22, within the 0.5-day tolerance


def test_value_just_outside_tolerance_is_rejected():
    facts = {"days_cash": Decimal("21.0")}
    result = validate_ai_output_is_grounded("Down to 22 days of cash.", facts)
    assert not result.ok  # 1.0 day off, tolerance is 0.5


def test_value_just_inside_tolerance_is_accepted():
    facts = {"days_cash": Decimal("21.6")}
    result = validate_ai_output_is_grounded("Down to 22 days of cash.", facts)
    assert result.ok  # 0.4 day off, tolerance is 0.5


def test_bare_counts_and_years_do_not_trigger_a_false_rejection():
    # No $, %, or "days" attached to these numbers, so they are not
    # financial claims and must not be checked against allowed_facts.
    text = "3 hospitals need attention this week, as of September 2026."
    result = validate_ai_output_is_grounded(text, {})
    assert result.ok


def test_empty_text_is_trivially_grounded():
    assert validate_ai_output_is_grounded("", ENGINE_FACTS).ok
    assert validate_ai_output_is_grounded(None, ENGINE_FACTS).ok


def test_int_and_float_fact_values_are_accepted_not_just_decimal():
    facts = {"days_cash": 22, "margin": -4.1}
    text = "22 days of cash, margin -4.1%."
    assert validate_ai_output_is_grounded(text, facts).ok


def test_reason_names_the_offending_figures():
    text = "Lost $500 and 3.0% we can't explain."
    result = validate_ai_output_is_grounded(text, {})
    reason = result.reason()
    assert "$500" in reason
    assert "3.0%" in reason


def test_malformed_dollar_token_counts_as_ungrounded_not_silently_skipped():
    # "$," matches the dollar pattern (a comma satisfies [\d,]+) but has no
    # actual digit, so it cannot be parsed to a number. That must still
    # block the output, not disappear silently -- an unparseable figure is
    # exactly the kind of thing that should stop and get a human's eyes on
    # it, not slip through because the code couldn't make sense of it.
    text = "Total: $, in adjustments."
    result = validate_ai_output_is_grounded(text, ENGINE_FACTS)
    assert not result.ok
    assert result.ungrounded[0].value is None


def test_a_realistic_two_decimal_point_typo_is_still_rejected():
    # The regex can only ever capture one '.NNN' group per match, so
    # "$1.234.56" is read as the valid sub-token "$1.234" (which parses
    # fine) followed by a bare ".56" that matches no pattern at all. The
    # safety property that actually matters still holds: $1.234 is not a
    # dollar figure the engine ever produced, so the output is rejected
    # regardless of which code path caught it.
    text = "Total: $1.234.56 in adjustments."
    result = validate_ai_output_is_grounded(text, ENGINE_FACTS)
    assert not result.ok
