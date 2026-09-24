from datetime import date

import anthropic
import httpx2 as httpx
import pytest

from cost_report_copilot import (
    CandidateDiscrepancy,
    ClaudeCallFailed,
    CostReportYear,
    Finding,
    LedgerMonth,
    MismatchedFiscalYears,
    build_facts,
    call_claude_for_findings,
    detect_discrepancies,
    filter_grounded_findings,
    generate_grounded_findings,
    require_same_year,
    validate_finding_citations,
)


def _cost_report(ccn="370149", fy=2024, cash=16600.0, ar=22663037.0, cash_ok=True, ar_ok=True):
    provenance = {}
    if cash_ok:
        provenance["cash_on_hand"] = {"wksht_cd": "G000000", "line_num": "00100", "clmn_num": "00100", "status": "ok"}
    if ar_ok:
        provenance["accounts_receivable_net"] = {"wksht_cd": "G000000", "line_num": "00400", "clmn_num": "00100", "status": "ok"}
    return CostReportYear(
        provider_ccn=ccn, fiscal_year=fy, fy_end_date=date(fy, 12, 31),
        cash_on_hand=cash, accounts_receivable_net=ar, metric_provenance=provenance,
    )


def _ledger(ccn="370149", month=date(2024, 12, 1), cash=10000.0, ar=22700000.0):
    return LedgerMonth(provider_ccn=ccn, month=month, cash_on_hand=cash, ar_balance=ar)


class FakeToolUseBlock:
    type = "tool_use"

    def __init__(self, name, input):
        self.name = name
        self.input = input


class FakeMessage:
    def __init__(self, content_blocks):
        self.content = content_blocks


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


def _findings_response(findings):
    return [FakeToolUseBlock("report_findings", {"findings": findings})]


def _rate_limit_error():
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(429, request=req)
    return anthropic.RateLimitError("rate limited", response=resp, body=None)


def _timeout_error():
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APITimeoutError(req)


# --- detect_discrepancies: the 15% materiality rule ----------------------


def test_flags_a_difference_strictly_above_15_percent():
    candidates = detect_discrepancies(_cost_report(cash=16600.0), _ledger(cash=10000.0))
    names = [c.metric_name for c in candidates]
    assert "cash_on_hand" in names


def test_does_not_flag_at_exactly_15_percent():
    cr = _cost_report(cash=100.0, ar=None, ar_ok=False)
    ledger = _ledger(cash=115.0, ar=None)
    assert detect_discrepancies(cr, ledger) == []


def test_does_not_flag_within_15_percent():
    cr = _cost_report(cash=100.0, ar=None, ar_ok=False)
    ledger = _ledger(cash=105.0, ar=None)
    assert detect_discrepancies(cr, ledger) == []


def test_skips_a_metric_that_is_none_on_the_cost_report_side():
    cr = _cost_report(cash=None, ar=None, ar_ok=False)
    ledger = _ledger(cash=10000.0, ar=None)
    assert detect_discrepancies(cr, ledger) == []


def test_skips_a_metric_that_is_none_on_the_ledger_side():
    cr = _cost_report(cash=16600.0, ar=None, ar_ok=False)
    ledger = _ledger(cash=None, ar=None)
    assert detect_discrepancies(cr, ledger) == []


def test_skips_a_metric_whose_provenance_status_is_not_ok():
    cr = _cost_report(cash=16600.0, ar=None, cash_ok=False, ar_ok=False)
    ledger = _ledger(cash=10000.0, ar=None)
    assert detect_discrepancies(cr, ledger) == []


def test_cash_and_ar_are_evaluated_independently():
    # cash differs by ~40% (flag), ar differs by ~0.16% (no flag)
    cr = _cost_report(cash=16600.0, ar=22663037.0)
    ledger = _ledger(cash=10000.0, ar=22700000.0)
    candidates = detect_discrepancies(cr, ledger)
    names = {c.metric_name for c in candidates}
    assert names == {"cash_on_hand"}


def test_skips_a_zero_cost_report_value_rather_than_dividing_by_zero():
    cr = _cost_report(cash=0.0, ar=None, ar_ok=False)
    ledger = _ledger(cash=500.0, ar=None)
    assert detect_discrepancies(cr, ledger) == []


# --- require_same_year: criterion 2 ---------------------------------------


def test_require_same_year_raises_naming_both_years_when_they_differ():
    with pytest.raises(MismatchedFiscalYears, match="2024.*2023|2023.*2024"):
        require_same_year(2024, 2023)


def test_require_same_year_does_not_raise_when_equal():
    require_same_year(2024, 2024)  # does not raise


# --- validate_finding_citations: criterion 3 ------------------------------


def test_drops_a_finding_citing_an_unknown_cost_report_line():
    candidates = detect_discrepancies(_cost_report(cash=16600.0), _ledger(cash=10000.0))
    findings = [{"cost_report_line": "Worksheet Z, Line 99, Column 1", "explanation": "made up"}]
    assert validate_finding_citations(findings, candidates) == []


def test_keeps_a_finding_citing_a_real_cost_report_line():
    candidates = detect_discrepancies(_cost_report(cash=16600.0), _ledger(cash=10000.0))
    real_line = candidates[0].cost_report_line
    findings = [{"cost_report_line": real_line, "explanation": "real"}]
    assert validate_finding_citations(findings, candidates) == findings


# --- filter_grounded_findings: criterion 4 --------------------------------


def test_drops_a_finding_with_an_ungrounded_dollar_figure():
    candidates = detect_discrepancies(_cost_report(cash=16600.0), _ledger(cash=10000.0))
    line = candidates[0].cost_report_line
    findings = [{
        "cost_report_line": line, "cost_report_value": 16600.0, "ledger_value": 10000.0,
        "ledger_month": "2024-12-01", "explanation": "The hospital may be owed an extra $500,000.",
    }]
    assert filter_grounded_findings(findings, candidates) == []


def test_keeps_a_finding_that_only_cites_known_values():
    candidates = detect_discrepancies(_cost_report(cash=16600.0), _ledger(cash=10000.0))
    line = candidates[0].cost_report_line
    findings = [{
        "cost_report_line": line, "cost_report_value": 16600.0, "ledger_value": 10000.0,
        "ledger_month": "2024-12-01", "explanation": "Cash on hand differs between the two records.",
    }]
    result = filter_grounded_findings(findings, candidates)
    assert len(result) == 1
    assert isinstance(result[0], Finding)
    assert result[0].cost_report_line == line


def test_one_ungrounded_finding_does_not_drop_a_sibling_grounded_finding():
    cr = _cost_report(cash=16600.0, ar=22663037.0)
    ledger = _ledger(cash=10000.0, ar=50000000.0)  # both flag
    candidates = detect_discrepancies(cr, ledger)
    assert len(candidates) == 2
    good, bad = candidates[0], candidates[1]
    findings = [
        {
            "cost_report_line": good.cost_report_line, "cost_report_value": good.cost_report_value,
            "ledger_value": good.ledger_value, "ledger_month": "2024-12-01", "explanation": "A real gap worth review.",
        },
        {
            "cost_report_line": bad.cost_report_line, "cost_report_value": bad.cost_report_value,
            "ledger_value": bad.ledger_value, "ledger_month": "2024-12-01",
            "explanation": "This could mean $9,999,999 in missed reimbursement.",
        },
    ]
    result = filter_grounded_findings(findings, candidates)
    assert len(result) == 1
    assert result[0].cost_report_line == good.cost_report_line


# --- call_claude_for_findings: retry mechanics ----------------------------


def test_retries_on_transient_error_then_succeeds():
    sleeps = []
    candidates = detect_discrepancies(_cost_report(cash=16600.0), _ledger(cash=10000.0))
    client = FakeClient([_timeout_error(), _rate_limit_error(), _findings_response([{"cost_report_line": candidates[0].cost_report_line, "explanation": "ok"}])])
    result = call_claude_for_findings(client, candidates, sleep=sleeps.append)
    assert result == [{"cost_report_line": candidates[0].cost_report_line, "explanation": "ok"}]
    assert client.messages.calls == 3
    assert sleeps == [1.0, 2.0]


def test_fails_after_exhausting_retries():
    candidates = detect_discrepancies(_cost_report(cash=16600.0), _ledger(cash=10000.0))
    client = FakeClient([_timeout_error()] * 4)
    with pytest.raises(ClaudeCallFailed):
        call_claude_for_findings(client, candidates, sleep=lambda s: None)
    assert client.messages.calls == 4


def test_no_tool_call_in_response_fails_immediately_without_consuming_a_retry():
    candidates = detect_discrepancies(_cost_report(cash=16600.0), _ledger(cash=10000.0))
    client = FakeClient([[]])  # a "successful" response with no content blocks at all
    with pytest.raises(ClaudeCallFailed):
        call_claude_for_findings(client, candidates, sleep=lambda s: None)
    assert client.messages.calls == 1


# --- generate_grounded_findings: full pure orchestration ------------------


def test_happy_path_returns_one_grounded_finding_for_the_flagged_metric():
    cr = _cost_report(cash=16600.0, ar=22663037.0)
    ledger = _ledger(cash=10000.0, ar=22700000.0)
    candidates = detect_discrepancies(cr, ledger)
    line = candidates[0].cost_report_line
    client = FakeClient([_findings_response([{
        "cost_report_line": line, "cost_report_value": 16600.0, "ledger_value": 10000.0,
        "ledger_month": "2024-12-01", "explanation": "Cash on hand differs materially between the two records.",
    }])])
    result = generate_grounded_findings(client, cr, ledger, sleep=lambda s: None)
    assert len(result) == 1
    assert result[0].metric_name == "cash_on_hand"
    assert result[0].cost_report_value == 16600.0
    assert result[0].ledger_value == 10000.0


def test_returns_empty_and_never_calls_claude_when_nothing_is_flagged():
    cr = _cost_report(cash=16600.0, ar=22663037.0)
    ledger = _ledger(cash=16700.0, ar=22700000.0)  # both within 15%
    client = FakeClient([])
    result = generate_grounded_findings(client, cr, ledger, sleep=lambda s: None)
    assert result == []
    assert client.messages.calls == 0


# --- build_facts -----------------------------------------------------------


def test_build_facts_includes_both_values_and_the_percentage():
    candidates = detect_discrepancies(_cost_report(cash=16600.0), _ledger(cash=10000.0))
    facts = build_facts(candidates)
    assert facts["cash_on_hand:cost_report_value"] == 16600.0
    assert facts["cash_on_hand:ledger_value"] == 10000.0
    assert "cash_on_hand:relative_difference_pct" in facts
