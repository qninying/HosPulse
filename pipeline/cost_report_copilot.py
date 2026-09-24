"""STORY-011 (`.hospulse` numbering): find possible missed reimbursement by
comparing a hospital's annual CMS cost report figures (cost_report_years,
STORY-001) against its operator-uploaded monthly ledger figures
(hospital_monthly_metrics, STORY-011 `.colaberry` numbering /
export_normalizer.py) for the same fiscal year.

Scope, confirmed with the user before building: cash position and A/R
balance only. These are the only two metrics that exist on both sides of
the data -- revenue, expense, and margin have no monthly-ledger
equivalent to compare against, and inventing one would misrepresent what
this actually checks.

Same "engine flags, AI narrates" split used throughout this codebase
(early_warning.py / briefing_agent.py): detect_discrepancies() is a pure,
deterministic function that decides WHICH differences are material (a
relative difference strictly exceeding MATERIALITY_THRESHOLD_PCT, a
number confirmed with the user, not invented). Claude Opus 5.5 is never
shown an unflagged pair and never decides materiality itself -- its only
job is writing a grounded, plain-English explanation of each difference
the engine already computed, via forced structured output (a tool call),
never free text.

Four ways this can legitimately fail or refuse, all handled explicitly:

- MismatchedFiscalYears: the caller asked to compare a cost report from
  one year against ledger data from a different year. Refused before any
  DB query or Claude call.
- CostReportYearNotFound: no cost_report_years row exists for the
  requested (provider_ccn, fiscal_year).
- ClaudeCallFailed: every attempt to call Claude failed, or a successful
  response carried no report_findings tool call. Nothing is saved.
- A finding citing a cost report line that was never actually flagged is
  dropped (validate_finding_citations), and a finding whose explanation
  states a number not present in the engine's own facts is dropped
  (filter_grounded_findings, reusing grounding_guardrail.py) -- both are
  per-finding drops, not whole-run failures, since the acceptance
  criteria are phrased per finding.

save_findings() is the only write, called once, only with findings that
survived both filters -- there is no path that persists an unvalidated
finding.

Scope lock: this story does not add specialist sign-off. `status`
defaults to 'open' so a later story can add that workflow without a
schema change here, but no decision/approval logic is built in this file.

Usage: python3 cost_report_copilot.py <provider_ccn> <cost_report_fiscal_year> <ledger_year>
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

import anthropic
import psycopg2
import psycopg2.extras

from env import load_env
from grounding_guardrail import validate_ai_output_is_grounded
from pipeline_run_log import finish_pipeline_run, start_pipeline_run

ROOT = Path(__file__).resolve().parent.parent

MODEL = "claude-opus-5-5"
MAX_ATTEMPTS = 4
REQUEST_TIMEOUT_SECONDS = 30.0
BACKOFF_SECONDS = (1.0, 2.0, 4.0)

MATERIALITY_THRESHOLD_PCT = 15.0  # confirmed with the user; strict >, not >=

_RETRYABLE_ERRORS = (
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
    anthropic.OverloadedError,
    anthropic.ServiceUnavailableError,
)

# cost_report_years column -> hospital_monthly_metrics metric_name -> the
# standard metric name this module reports under. Scope-locked to the two
# metrics that exist on both sides of the data.
_METRIC_PAIRS = (
    ("cash_on_hand", "cash_on_hand", "cash_on_hand"),
    ("accounts_receivable_net", "ar_balance", "ar_balance"),
)

_REPORT_FINDINGS_TOOL = {
    "name": "report_findings",
    "description": "Report each already-flagged cost-report-vs-ledger discrepancy as a plain-English finding.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "cost_report_line": {"type": "string"},
                        "cost_report_value": {"type": "number"},
                        "ledger_value": {"type": "number"},
                        "ledger_month": {"type": "string"},
                        "explanation": {"type": "string"},
                    },
                    "required": ["cost_report_line", "cost_report_value", "ledger_value", "ledger_month", "explanation"],
                },
            }
        },
        "required": ["findings"],
    },
}


class ClaudeCallFailed(Exception):
    """Every attempt to call Claude failed, or a successful response had no
    report_findings tool call. Nothing was saved."""


class MismatchedFiscalYears(Exception):
    """The caller asked to compare a cost report and ledger data from
    different years. Refused before any DB query or Claude call."""


class CostReportYearNotFound(Exception):
    """No cost_report_years row exists for this (provider_ccn, fiscal_year)."""


@dataclass
class CostReportYear:
    provider_ccn: str
    fiscal_year: int
    fy_end_date: date | None
    cash_on_hand: float | None
    accounts_receivable_net: float | None
    metric_provenance: dict

    def line_citation(self, field_name: str) -> str | None:
        """None if this metric's provenance is missing or its status isn't
        'ok' -- can't cite a real cost report line for a value that was
        never actually read from the report (reuses the same not_reported /
        unparseable distinction hcris_import.py already records, rather
        than inventing a new one)."""
        prov = (self.metric_provenance or {}).get(field_name)
        if not prov or prov.get("status") != "ok":
            return None
        return f"Worksheet {prov.get('wksht_cd')}, Line {prov.get('line_num')}, Column {prov.get('clmn_num')}"


@dataclass
class LedgerMonth:
    provider_ccn: str
    month: date
    cash_on_hand: float | None
    ar_balance: float | None


@dataclass
class CandidateDiscrepancy:
    provider_ccn: str
    fiscal_year: int
    metric_name: str  # "cash_on_hand" | "ar_balance"
    cost_report_line: str
    cost_report_value: float
    ledger_month: date
    ledger_value: float
    relative_difference_pct: float


@dataclass
class Finding:
    provider_ccn: str
    fiscal_year: int
    metric_name: str
    cost_report_line: str
    cost_report_value: float
    ledger_month: date
    ledger_value: float
    relative_difference_pct: float
    explanation: str
    model: str = field(default=MODEL)


def require_same_year(cost_report_fiscal_year: int, ledger_year: int) -> None:
    """The co-pilot only ever compares a cost report to ledger totals from
    the same year -- refuses, with a reason, rather than silently comparing
    across a year boundary."""
    if cost_report_fiscal_year != ledger_year:
        raise MismatchedFiscalYears(
            f"cannot compare cost report fiscal year {cost_report_fiscal_year} against "
            f"ledger year {ledger_year} -- the co-pilot only compares a cost report to "
            f"ledger totals from the same year"
        )


def detect_discrepancies(cost_report: CostReportYear, ledger: LedgerMonth) -> list[CandidateDiscrepancy]:
    """Pure, no I/O. The only place MATERIALITY_THRESHOLD_PCT is applied --
    Claude never sees an unflagged pair and never decides materiality
    itself. Skips a metric entirely, without error, when either side is
    None, when the cost report side has no 'ok' provenance for it, or when
    the cost report value is exactly 0 (no meaningful percentage against a
    zero baseline) -- missing or unusable data is skipped, never treated as
    a match or a crash."""
    candidates: list[CandidateDiscrepancy] = []
    cost_values = {"cash_on_hand": cost_report.cash_on_hand, "accounts_receivable_net": cost_report.accounts_receivable_net}
    ledger_values = {"cash_on_hand": ledger.cash_on_hand, "ar_balance": ledger.ar_balance}

    for cr_field, ledger_field, metric_name in _METRIC_PAIRS:
        cr_value = cost_values[cr_field]
        lg_value = ledger_values[ledger_field]
        if cr_value is None or lg_value is None or cr_value == 0:
            continue
        line = cost_report.line_citation(cr_field)
        if line is None:
            continue
        relative_diff_pct = abs(cr_value - lg_value) / abs(cr_value) * 100
        if relative_diff_pct > MATERIALITY_THRESHOLD_PCT:
            candidates.append(
                CandidateDiscrepancy(
                    provider_ccn=cost_report.provider_ccn,
                    fiscal_year=cost_report.fiscal_year,
                    metric_name=metric_name,
                    cost_report_line=line,
                    cost_report_value=cr_value,
                    ledger_month=ledger.month,
                    ledger_value=lg_value,
                    relative_difference_pct=round(relative_diff_pct, 2),
                )
            )
    return candidates


def build_facts(candidates: list[CandidateDiscrepancy]) -> dict[str, float]:
    facts: dict[str, float] = {}
    for c in candidates:
        facts[f"{c.metric_name}:cost_report_value"] = c.cost_report_value
        facts[f"{c.metric_name}:ledger_value"] = c.ledger_value
        facts[f"{c.metric_name}:relative_difference_pct"] = c.relative_difference_pct
    return facts


def build_prompt(candidates: list[CandidateDiscrepancy]) -> str:
    lines = [
        "You are a reimbursement specialist's assistant reviewing a hospital's "
        "cost report against its own ledger for the same year. Below are "
        "discrepancies already identified between the cost report and the "
        "ledger -- your job is only to explain each one in plain English, "
        "not to decide whether it matters.",
        "",
        "Hard rule: use ONLY the numbers given below for each discrepancy. "
        "Never invent, estimate, or infer a figure that is not explicitly "
        "listed. Cite the cost_report_line exactly as given.",
        "",
    ]
    for c in candidates:
        lines.append(
            f"- Metric: {c.metric_name}. Cost report line: {c.cost_report_line}. "
            f"Cost report value: ${c.cost_report_value:,.2f}. "
            f"Ledger value (as of {c.ledger_month.isoformat()}): ${c.ledger_value:,.2f}. "
            f"Relative difference: {c.relative_difference_pct}%."
        )
    lines.append("")
    lines.append(
        "Call report_findings with one entry per discrepancy above, each "
        "explaining in one or two sentences why this difference is worth a "
        "specialist's review."
    )
    return "\n".join(lines)


def call_claude_for_findings(
    client: anthropic.Anthropic,
    candidates: list[CandidateDiscrepancy],
    max_attempts: int = MAX_ATTEMPTS,
    backoff: tuple[float, ...] = BACKOFF_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict]:
    prompt = build_prompt(candidates)
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=2000,
                timeout=REQUEST_TIMEOUT_SECONDS,
                tools=[_REPORT_FINDINGS_TOOL],
                tool_choice={"type": "auto"},  # claude-opus-5-5 rejects a forced ("tool"/"any") choice; confirmed live
                messages=[{"role": "user", "content": prompt}],
            )
            for block in response.content:
                if getattr(block, "type", None) == "tool_use" and block.name == "report_findings":
                    return block.input.get("findings", [])
            # A successful call with no report_findings tool_use block is a
            # schema violation, not a transient failure -- a retry with the
            # same prompt would not fix it.
            raise ClaudeCallFailed("Claude response had no report_findings tool call")
        except _RETRYABLE_ERRORS as e:
            last_error = e
            if attempt < max_attempts - 1:
                sleep(backoff[min(attempt, len(backoff) - 1)])
    raise ClaudeCallFailed(
        f"Claude API call failed after {max_attempts} attempts: {last_error!r}"
    ) from last_error


def validate_finding_citations(raw_findings: list[dict], candidates: list[CandidateDiscrepancy]) -> list[dict]:
    """Drops (never raises for) a finding whose cost_report_line is not
    exactly one of the lines detect_discrepancies() actually produced."""
    known_lines = {c.cost_report_line for c in candidates}
    return [f for f in raw_findings if f.get("cost_report_line") in known_lines]


def _render_finding_text(finding: dict) -> str:
    """Renders both the structured numeric fields and the free-text
    explanation into one string before grounding-checking it -- a real
    line with an invented dollar value attached would pass citation
    validation but must still be caught here."""
    return (
        f"{finding.get('cost_report_line')}: cost report ${finding.get('cost_report_value')} "
        f"vs ledger ${finding.get('ledger_value')} as of {finding.get('ledger_month')}. "
        f"{finding.get('explanation', '')}"
    )


def filter_grounded_findings(findings: list[dict], candidates: list[CandidateDiscrepancy]) -> list[Finding]:
    """Runs the grounding check on each finding's own text individually --
    one invented number drops only that finding, not its siblings, per the
    acceptance criterion's singular phrasing ('the finding is rejected').
    Builds each returned Finding's numeric fields from the candidate's own
    known values, never from Claude's echoed numbers."""
    facts = build_facts(candidates)
    by_line = {c.cost_report_line: c for c in candidates}
    kept: list[Finding] = []
    for f in findings:
        result = validate_ai_output_is_grounded(_render_finding_text(f), facts)
        if not result.ok:
            continue
        c = by_line[f["cost_report_line"]]
        kept.append(
            Finding(
                provider_ccn=c.provider_ccn,
                fiscal_year=c.fiscal_year,
                metric_name=c.metric_name,
                cost_report_line=c.cost_report_line,
                cost_report_value=c.cost_report_value,
                ledger_month=c.ledger_month,
                ledger_value=c.ledger_value,
                relative_difference_pct=c.relative_difference_pct,
                explanation=f.get("explanation", ""),
            )
        )
    return kept


def generate_grounded_findings(
    client: anthropic.Anthropic,
    cost_report: CostReportYear,
    ledger: LedgerMonth,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Finding]:
    """Pure orchestration, no DB write: detect -> (skip Claude entirely if
    nothing was flagged) -> call Claude -> validate citations -> filter by
    grounding."""
    candidates = detect_discrepancies(cost_report, ledger)
    if not candidates:
        return []
    raw = call_claude_for_findings(client, candidates, sleep=sleep)
    cited = validate_finding_citations(raw, candidates)
    return filter_grounded_findings(cited, candidates)


def fetch_cost_report_year(database_url: str, provider_ccn: str, fiscal_year: int) -> CostReportYear | None:
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT provider_ccn, fiscal_year, fy_end_date, cash_on_hand,
                       accounts_receivable_net, metric_provenance
                FROM cost_report_years
                WHERE provider_ccn = %s AND fiscal_year = %s
                """,
                (provider_ccn, fiscal_year),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    ccn, fy, fy_end, cash, ar, provenance = row
    return CostReportYear(
        provider_ccn=ccn,
        fiscal_year=fy,
        fy_end_date=fy_end,
        cash_on_hand=float(cash) if cash is not None else None,
        accounts_receivable_net=float(ar) if ar is not None else None,
        metric_provenance=provenance or {},
    )


def _target_ledger_month(cost_report: CostReportYear) -> date:
    """The exact ledger month compared against: the cost report's own
    fiscal-year-end month, normalized to first-of-month (matching how
    hospital_monthly_metrics stores months). Falls back to December of the
    fiscal year only if fy_end_date itself is missing -- no 'nearest
    available month' guessing."""
    if cost_report.fy_end_date is not None:
        return cost_report.fy_end_date.replace(day=1)
    return date(cost_report.fiscal_year, 12, 1)


def fetch_ledger_month(database_url: str, provider_ccn: str, month: date) -> LedgerMonth | None:
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT metric_name, metric_value
                FROM hospital_monthly_metrics
                WHERE provider_ccn = %s AND month = %s AND metric_name IN ('cash_on_hand', 'ar_balance')
                """,
                (provider_ccn, month),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    if not rows:
        return None
    values = {name: (float(value) if value is not None else None) for name, value in rows}
    return LedgerMonth(
        provider_ccn=provider_ccn,
        month=month,
        cash_on_hand=values.get("cash_on_hand"),
        ar_balance=values.get("ar_balance"),
    )


def save_findings(findings: list[Finding], database_url: str) -> None:
    """Idempotent: ON CONFLICT (provider_ccn, fiscal_year, metric_name) DO
    UPDATE, so re-running for the same hospital/year/metric replaces that
    finding instead of accumulating duplicates."""
    if not findings:
        return
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO cost_report_findings (
                    provider_ccn, fiscal_year, metric_name, cost_report_line,
                    cost_report_value, ledger_month, ledger_value,
                    relative_difference_pct, explanation, model
                ) VALUES %s
                ON CONFLICT (provider_ccn, fiscal_year, metric_name) DO UPDATE SET
                    cost_report_line = EXCLUDED.cost_report_line,
                    cost_report_value = EXCLUDED.cost_report_value,
                    ledger_month = EXCLUDED.ledger_month,
                    ledger_value = EXCLUDED.ledger_value,
                    relative_difference_pct = EXCLUDED.relative_difference_pct,
                    explanation = EXCLUDED.explanation,
                    model = EXCLUDED.model,
                    generated_at = now()
                """,
                [
                    (
                        f.provider_ccn, f.fiscal_year, f.metric_name, f.cost_report_line,
                        f.cost_report_value, f.ledger_month, f.ledger_value,
                        f.relative_difference_pct, f.explanation, f.model,
                    )
                    for f in findings
                ],
            )
    finally:
        conn.close()


def generate_and_save_cost_report_findings(
    client: anthropic.Anthropic,
    database_url: str,
    provider_ccn: str,
    cost_report_fiscal_year: int,
    ledger_year: int,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Finding]:
    """The real entry point. Raises MismatchedFiscalYears/
    CostReportYearNotFound before touching Claude. Returns [] (not an
    error) when there's simply no ledger data at that point in time to
    compare against."""
    require_same_year(cost_report_fiscal_year, ledger_year)

    run_id = start_pipeline_run(
        "cost_report_copilot", database_url, run_key=f"{provider_ccn}:{cost_report_fiscal_year}"
    )
    try:
        cost_report = fetch_cost_report_year(database_url, provider_ccn, cost_report_fiscal_year)
        if cost_report is None:
            raise CostReportYearNotFound(
                f"no cost_report_years row for {provider_ccn} FY{cost_report_fiscal_year}"
            )
        ledger = fetch_ledger_month(database_url, provider_ccn, _target_ledger_month(cost_report))
        if ledger is None:
            findings: list[Finding] = []
        else:
            findings = generate_grounded_findings(client, cost_report, ledger, sleep=sleep)
            if findings:
                save_findings(findings, database_url)
    except Exception as exc:
        finish_pipeline_run(run_id, "failed", database_url, error_message=str(exc))
        raise
    finish_pipeline_run(run_id, "succeeded", database_url, rows_affected=len(findings))
    return findings


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "usage: python3 cost_report_copilot.py <provider_ccn> <cost_report_fiscal_year> <ledger_year>",
            file=sys.stderr,
        )
        sys.exit(1)
    load_env(ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set -- check .env")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set -- check .env")

    claude_client = anthropic.Anthropic(api_key=anthropic_api_key)
    provider_ccn_arg, fy_arg, ledger_year_arg = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    try:
        results = generate_and_save_cost_report_findings(
            claude_client, database_url, provider_ccn_arg, fy_arg, ledger_year_arg
        )
    except (MismatchedFiscalYears, CostReportYearNotFound, ClaudeCallFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print(f"No possible missed reimbursement found for {provider_ccn_arg} FY{fy_arg}.")
    else:
        print(json.dumps([f.__dict__ for f in results], indent=2, default=str))
