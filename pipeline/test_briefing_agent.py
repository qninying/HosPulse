from datetime import date

import anthropic
import httpx2 as httpx
import pytest

from briefing_agent import (
    ClaudeCallFailed,
    FlaggedHospital,
    IncompleteBriefing,
    InvalidEngineOutput,
    UngroundedBriefing,
    build_facts,
    call_claude_with_retry,
    check_coverage,
    generate_grounded_briefing,
    validate_flagged_hospital,
)


def _hospital(ccn="123456", name="Memorial Rural Hospital", fy=2025):
    return FlaggedHospital(
        provider_ccn=ccn,
        name=name,
        as_of_fiscal_year=fy,
        criteria=[
            {
                "name": "operating_margin_negative",
                "status": "triggered",
                "values": {"fiscal_year": fy, "operating_margin_pct": -5.2, "threshold_pct": 0.0},
            },
            {
                "name": "days_cash_on_hand_low",
                "status": "triggered",
                "values": {"fiscal_year": fy, "days_cash_on_hand": 12.0, "threshold_days": 30.0},
            },
        ],
    )


class FakeTextBlock:
    def __init__(self, text):
        self.text = text


class FakeMessage:
    def __init__(self, text):
        self.content = [FakeTextBlock(text)]


class FakeMessagesEndpoint:
    """Returns responses[i] on the i-th call, or raises if it's an Exception."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def create(self, **kwargs):
        outcome = self.responses[self.calls]
        self.calls += 1
        if isinstance(outcome, BaseException):
            raise outcome
        return FakeMessage(outcome)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessagesEndpoint(responses)


def _rate_limit_error():
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(429, request=req)
    return anthropic.RateLimitError("rate limited", response=resp, body=None)


def _timeout_error():
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APITimeoutError(req)


# --- build_facts: pure flattening logic ---------------------------------


def test_build_facts_flattens_scalar_and_list_values():
    hospital = _hospital()
    facts = build_facts([hospital])
    assert facts["123456:operating_margin_negative:operating_margin_pct"] == -5.2
    assert facts["123456:days_cash_on_hand_low:days_cash_on_hand"] == 12.0


def test_build_facts_flattens_list_valued_criteria():
    hospital = FlaggedHospital(
        "670781",
        "Anson General",
        2025,
        [
            {
                "name": "days_in_ar_rising_two_years",
                "status": "triggered",
                "values": {"fiscal_years": [2023, 2024, 2025], "days_in_ar": [30, 35, 41]},
            }
        ],
    )
    facts = build_facts([hospital])
    assert facts["670781:days_in_ar_rising_two_years:days_in_ar:0"] == 30.0
    assert facts["670781:days_in_ar_rising_two_years:days_in_ar:2"] == 41.0


# --- validate_flagged_hospital: reject bad engine output, not just bad AI output ---


def test_validate_rejects_hospital_with_no_criteria():
    hospital = FlaggedHospital("123456", "Memorial Rural Hospital", 2025, [])
    with pytest.raises(InvalidEngineOutput):
        validate_flagged_hospital(hospital)


def test_validate_rejects_criterion_missing_name_or_status():
    hospital = FlaggedHospital(
        "123456", "Memorial Rural Hospital", 2025,
        [{"values": {"operating_margin_pct": -5.2}}],
    )
    with pytest.raises(InvalidEngineOutput):
        validate_flagged_hospital(hospital)


def test_validate_rejects_criterion_with_non_dict_values():
    hospital = FlaggedHospital(
        "123456", "Memorial Rural Hospital", 2025,
        [{"name": "operating_margin_negative", "status": "triggered", "values": "not a dict"}],
    )
    with pytest.raises(InvalidEngineOutput):
        validate_flagged_hospital(hospital)


def test_validate_rejects_hospital_with_no_numeric_facts():
    hospital = FlaggedHospital(
        "123456", "Memorial Rural Hospital", 2025,
        [{"name": "operating_margin_negative", "status": "not_assessable", "values": {"reason": "no data"}}],
    )
    with pytest.raises(InvalidEngineOutput):
        validate_flagged_hospital(hospital)


def test_validate_passes_a_well_formed_hospital():
    validate_flagged_hospital(_hospital())  # does not raise


def test_generate_grounded_briefing_rejects_invalid_engine_output_before_calling_claude():
    hospital = FlaggedHospital("123456", "Memorial Rural Hospital", 2025, [])
    client = FakeClient([])
    with pytest.raises(InvalidEngineOutput):
        generate_grounded_briefing(client, [hospital])
    assert client.messages.calls == 0


# --- check_coverage ------------------------------------------------------


def test_check_coverage_flags_a_missing_hospital():
    hospitals = [_hospital("123456", "Memorial Rural Hospital"), _hospital("999999", "Second Hospital")]
    missing = check_coverage("Memorial Rural Hospital is struggling.", hospitals)
    assert missing == ["Second Hospital"]


def test_check_coverage_passes_when_all_named():
    hospitals = [_hospital("123456", "Memorial Rural Hospital")]
    assert check_coverage("Memorial Rural Hospital needs attention.", hospitals) == []


# --- call_claude_with_retry: retry / backoff / failure -------------------


def test_retries_on_transient_error_then_succeeds():
    sleeps = []
    client = FakeClient([_timeout_error(), _rate_limit_error(), "final answer"])
    text = call_claude_with_retry(client, "prompt", sleep=sleeps.append)
    assert text == "final answer"
    assert client.messages.calls == 3
    assert sleeps == [1.0, 2.0]  # backoff before attempt 2 and attempt 3


def test_fails_with_clear_error_after_exhausting_retries():
    client = FakeClient([_timeout_error(), _timeout_error(), _timeout_error(), _timeout_error()])
    with pytest.raises(ClaudeCallFailed):
        call_claude_with_retry(client, "prompt", sleep=lambda s: None)
    assert client.messages.calls == 4  # 1 initial + 3 retries, never more


# --- generate_grounded_briefing: the full orchestration ------------------


def test_happy_path_covers_every_flagged_hospital_and_is_grounded():
    hospital = _hospital()
    text = "Memorial Rural Hospital has an operating margin of -5.2% and 12.0 days cash on hand."
    client = FakeClient([text])
    result = generate_grounded_briefing(client, [hospital], as_of_date=date(2026, 9, 23))
    assert result.provider_ccns == ["123456"]
    assert result.body == text
    assert result.as_of_date == date(2026, 9, 23)


def test_ungrounded_figure_is_rejected_and_nothing_is_returned():
    hospital = _hospital()
    # $2,000,000 does not appear anywhere in this hospital's facts
    text = "Memorial Rural Hospital is at risk, needing $2,000,000 to recover."
    client = FakeClient([text])
    with pytest.raises(UngroundedBriefing):
        generate_grounded_briefing(client, [hospital])


def test_missing_hospital_is_rejected():
    hospitals = [_hospital("123456", "Memorial Rural Hospital"), _hospital("999999", "Second Hospital")]
    text = "Memorial Rural Hospital has an operating margin of -5.2%."
    client = FakeClient([text])
    with pytest.raises(IncompleteBriefing):
        generate_grounded_briefing(client, hospitals)


def test_api_failure_propagates_as_claude_call_failed_and_saves_nothing():
    hospital = _hospital()
    client = FakeClient([_timeout_error()] * 4)
    with pytest.raises(ClaudeCallFailed):
        generate_grounded_briefing(client, [hospital], sleep=lambda s: None)
