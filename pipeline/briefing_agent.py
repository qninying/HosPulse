"""STORY-003 / STORY-007: write a grounded hospitals-at-risk briefing,
scoped to one management company at a time.

REQ-006: produce a one-page plain-English briefing covering every hospital
the early-warning engine (STORY-002) flagged, and reject any AI-written
briefing that states a number not present in the engine's own output --
enforced by grounding_guardrail.py, the one shared check both this agent and
the future cost report co-pilot use.

Company-scoped since STORY-008 / STORY-010 (weekly_briefing_email.py):
the original build predated company_hospitals (STORY-006) and generated
one shared "every flagged hospital nationally" briefing -- that broke the
moment a real per-company weekly email had to go out (253 flagged
hospitals do not fit in one Claude response, and a company should only
ever be briefed on hospitals it actually manages, same boundary already
enforced by RLS for reads). generate_and_save_company_briefing() is the
real entry point now; weekly_briefing_email.py calls it once per company.

Four ways this can legitimately fail, all handled explicitly, none
surfacing as an unhandled exception or a silent no-op:

- InvalidEngineOutput: the engine's own output for a flagged hospital is
  malformed (missing criteria, a criterion missing name/status/values) or
  has no numeric facts at all. Checked before Claude is ever called.
  Not saved.
- ClaudeCallFailed: the API timed out or rate-limited on every attempt.
  Retried up to MAX_ATTEMPTS times with backoff, then raised. Nothing is
  saved.
- UngroundedBriefing: Claude stated a dollar amount, percentage or
  day-count that does not match a value the engine actually computed
  (invented, or rounded differently from the source data). Not saved.
- IncompleteBriefing: the response leaves out a hospital that was in the
  flagged list. Not saved.

save_briefing() is the only write, called once, only after every check
passes -- there is no path that persists a partial result.

No standalone usage: this module is called by weekly_briefing_email.py,
once per company.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, UTC, datetime
from typing import Callable

import anthropic
import psycopg2
import psycopg2.extras

from grounding_guardrail import validate_ai_output_is_grounded

MODEL = "claude-sonnet-5"
MAX_ATTEMPTS = 4  # first attempt + at most 3 retries, per STORY-003
REQUEST_TIMEOUT_SECONDS = 30.0
BACKOFF_SECONDS = (1.0, 2.0, 4.0)  # between attempts 1->2, 2->3, 3->4

# Errors worth retrying: transient, not something a different prompt would
# fix. Anything else (auth, bad request, etc.) fails fast on the first try.
_RETRYABLE_ERRORS = (
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
    anthropic.OverloadedError,
    anthropic.ServiceUnavailableError,
)


class ClaudeCallFailed(Exception):
    """Every attempt to call Claude failed. Nothing was saved."""


class UngroundedBriefing(Exception):
    """The response contained a figure not present in the engine's output. Not saved."""


class IncompleteBriefing(Exception):
    """The response left out a hospital that was flagged. Not saved."""


class InvalidEngineOutput(Exception):
    """The engine's own output for a flagged hospital is malformed, or has
    nothing numeric in it to ground a briefing in. Claude is never called
    with it. Not saved."""


@dataclass
class FlaggedHospital:
    provider_ccn: str
    name: str | None
    as_of_fiscal_year: int | None
    criteria: list[dict]

    def display_name(self) -> str:
        return self.name or self.provider_ccn


@dataclass
class BriefingResult:
    company_id: str
    as_of_date: date
    provider_ccns: list[str]
    facts: dict[str, float]
    body: str
    model: str = field(default=MODEL)


def _flatten_numeric_facts(hospital: FlaggedHospital) -> dict[str, float]:
    """Every number in this hospital's criteria values, flattened to a flat
    dict keyed uniquely per hospital -- the "allowed facts" a grounding
    check compares the AI's text against. Deliberately includes
    not-triggered and not-assessable criteria too: they are still numbers
    the engine actually computed, so they are still legitimate to cite."""
    facts: dict[str, float] = {}
    for criterion in hospital.criteria:
        name = criterion.get("name", "criterion")
        for key, value in (criterion.get("values") or {}).items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                facts[f"{hospital.provider_ccn}:{name}:{key}"] = float(value)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, (int, float)) and not isinstance(item, bool):
                        facts[f"{hospital.provider_ccn}:{name}:{key}:{i}"] = float(item)
    return facts


def validate_flagged_hospital(hospital: FlaggedHospital) -> None:
    """REQ-006 / STORY-007: reject engine output that is structurally
    malformed or has nothing numeric to brief on, before it ever reaches a
    prompt. This is distinct from the grounding check below -- grounding
    catches Claude inventing a number; this catches the engine handing us
    garbage in the first place."""
    if not hospital.criteria:
        raise InvalidEngineOutput(
            f"{hospital.display_name()} is flagged but has no criteria recorded -- "
            "nothing for a briefing to be grounded in."
        )
    for criterion in hospital.criteria:
        if not isinstance(criterion, dict) or "name" not in criterion or "status" not in criterion:
            raise InvalidEngineOutput(
                f"{hospital.display_name()} has a malformed criterion "
                f"(missing name/status): {criterion!r}"
            )
        values = criterion.get("values")
        if values is not None and not isinstance(values, dict):
            raise InvalidEngineOutput(
                f"{hospital.display_name()}'s criterion {criterion.get('name')!r} "
                f"has a non-dict values field: {values!r}"
            )
    if not _flatten_numeric_facts(hospital):
        raise InvalidEngineOutput(
            f"{hospital.display_name()} has no numeric facts in its criteria -- "
            "nothing to ground a briefing in."
        )


def build_facts(flagged: list[FlaggedHospital]) -> dict[str, float]:
    facts: dict[str, float] = {}
    for hospital in flagged:
        facts.update(_flatten_numeric_facts(hospital))
    return facts


def build_prompt(flagged: list[FlaggedHospital]) -> str:
    lines = [
        "You are writing a one-page, plain-English briefing for a rural "
        "hospital management company's CEO, covering every hospital listed "
        "below that the early-warning engine flagged.",
        "",
        "Hard rule: use ONLY the numbers given for each hospital below. "
        "Never invent, estimate, round differently, or infer a figure that "
        "is not explicitly listed. If you have nothing numeric to say about "
        "something, describe it in words instead of guessing a number.",
        "Mention every hospital below by the exact name given.",
        "",
    ]
    for hospital in flagged:
        lines.append(f"## {hospital.display_name()} (as of fiscal year {hospital.as_of_fiscal_year})")
        for criterion in hospital.criteria:
            lines.append(f"- {criterion.get('name')}: {criterion.get('status')} {criterion.get('values')}")
        lines.append("")
    lines.append(
        "Write the briefing now: one short paragraph per hospital explaining "
        "why it needs attention, in plain English a non-financial executive "
        "can act on without reading spreadsheets."
    )
    return "\n".join(lines)


def check_coverage(text: str, flagged: list[FlaggedHospital]) -> list[str]:
    """Names of flagged hospitals missing from the response text."""
    lowered = text.lower()
    return [h.display_name() for h in flagged if h.display_name().lower() not in lowered]


def call_claude_with_retry(
    client: anthropic.Anthropic,
    prompt: str,
    max_attempts: int = MAX_ATTEMPTS,
    backoff: tuple[float, ...] = BACKOFF_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=2000,
                timeout=REQUEST_TIMEOUT_SECONDS,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(block.text for block in response.content if hasattr(block, "text"))
        except _RETRYABLE_ERRORS as e:
            last_error = e
            if attempt < max_attempts - 1:
                sleep(backoff[min(attempt, len(backoff) - 1)])
    raise ClaudeCallFailed(
        f"Claude API call failed after {max_attempts} attempts: {last_error!r}"
    ) from last_error


def fetch_flagged_hospitals_for_company(database_url: str, company_id: str) -> list[FlaggedHospital]:
    """Only hospitals this company actually manages (company_hospitals,
    STORY-006) -- never every flagged hospital nationally."""
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ewf.provider_ccn, h.name, ewf.as_of_fiscal_year, ewf.criteria
                FROM early_warning_flags ewf
                JOIN hospitals h ON h.provider_ccn = ewf.provider_ccn
                JOIN company_hospitals ch ON ch.provider_ccn = ewf.provider_ccn
                WHERE ewf.status = 'flagged' AND ch.company_id = %s
                ORDER BY ewf.provider_ccn
                """,
                (company_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        FlaggedHospital(provider_ccn, name, as_of_fiscal_year, criteria)
        for provider_ccn, name, as_of_fiscal_year, criteria in rows
    ]


def save_briefing(result: BriefingResult, database_url: str) -> None:
    """Idempotent: ON CONFLICT (company_id, as_of_date) DO UPDATE, so
    re-running on the same day for the same company replaces that day's
    briefing instead of accumulating duplicates."""
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO briefings (company_id, as_of_date, provider_ccns, facts, body, model)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id, as_of_date) DO UPDATE SET
                    provider_ccns = EXCLUDED.provider_ccns,
                    facts = EXCLUDED.facts,
                    body = EXCLUDED.body,
                    model = EXCLUDED.model,
                    generated_at = now()
                """,
                (
                    result.company_id,
                    result.as_of_date,
                    psycopg2.extras.Json(result.provider_ccns),
                    psycopg2.extras.Json(result.facts),
                    result.body,
                    result.model,
                ),
            )
    finally:
        conn.close()


def generate_grounded_briefing(
    client: anthropic.Anthropic,
    flagged: list[FlaggedHospital],
    company_id: str,
    as_of_date: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> BriefingResult:
    """Pure orchestration (no DB write): calls Claude, then rejects the
    result before it ever reaches save_briefing() if coverage or grounding
    fails. Raises IncompleteBriefing / UngroundedBriefing / ClaudeCallFailed
    rather than returning a partial result."""
    as_of_date = as_of_date or datetime.now(UTC).date()
    for hospital in flagged:
        validate_flagged_hospital(hospital)

    facts = build_facts(flagged)
    prompt = build_prompt(flagged)

    text = call_claude_with_retry(client, prompt, sleep=sleep)

    missing = check_coverage(text, flagged)
    if missing:
        raise IncompleteBriefing(
            f"Briefing left out {len(missing)} flagged hospital(s): {', '.join(missing)}"
        )

    grounding = validate_ai_output_is_grounded(text, facts)
    if not grounding.ok:
        raise UngroundedBriefing(grounding.reason())

    return BriefingResult(
        company_id=company_id,
        as_of_date=as_of_date,
        provider_ccns=[h.provider_ccn for h in flagged],
        facts=facts,
        body=text,
    )


def generate_and_save_company_briefing(
    client: anthropic.Anthropic,
    database_url: str,
    company_id: str,
    as_of_date: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> BriefingResult | None:
    """The real entry point, called once per company by
    weekly_briefing_email.py. Returns None if this company has no flagged
    hospitals right now -- nothing to brief, not an error."""
    flagged = fetch_flagged_hospitals_for_company(database_url, company_id)
    if not flagged:
        return None
    result = generate_grounded_briefing(client, flagged, company_id, as_of_date=as_of_date, sleep=sleep)
    save_briefing(result, database_url)
    return result
