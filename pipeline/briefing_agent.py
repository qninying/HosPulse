"""STORY-003: write a grounded hospitals-at-risk briefing.

REQ-006: produce a one-page plain-English briefing covering every hospital
the early-warning engine (STORY-002) flagged.
REQ-004: reject any AI-written briefing that states a number not present in
the engine's own output -- enforced by grounding_guardrail.py, the one
shared check both this agent and the future cost report co-pilot use.

Three ways this can legitimately fail, all handled explicitly, none
surfacing as an unhandled exception or a silent no-op:

- ClaudeCallFailed: the API timed out or rate-limited on every attempt.
  Retried up to MAX_ATTEMPTS times with backoff, then raised. Nothing is
  saved.
- UngroundedBriefing: Claude stated a dollar amount, percentage or
  day-count that does not match a value the engine actually computed
  (invented, or rounded differently from the source data). Not saved.
- IncompleteBriefing: the response leaves out a hospital that was in the
  flagged list. Not saved.

save_briefing() is the only write, called once, only after both checks
pass -- there is no path that persists a partial result.

Usage: python3 briefing_agent.py
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import date, UTC, datetime
from pathlib import Path
from typing import Callable

import anthropic
import psycopg2
import psycopg2.extras

from env import load_env
from grounding_guardrail import validate_ai_output_is_grounded

ROOT = Path(__file__).resolve().parent.parent

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


def fetch_flagged_hospitals(database_url: str) -> list[FlaggedHospital]:
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ewf.provider_ccn, h.name, ewf.as_of_fiscal_year, ewf.criteria
                FROM early_warning_flags ewf
                JOIN hospitals h ON h.provider_ccn = ewf.provider_ccn
                WHERE ewf.status = 'flagged'
                ORDER BY ewf.provider_ccn
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        FlaggedHospital(provider_ccn, name, as_of_fiscal_year, criteria)
        for provider_ccn, name, as_of_fiscal_year, criteria in rows
    ]


def save_briefing(result: BriefingResult, database_url: str) -> None:
    """Idempotent: ON CONFLICT (as_of_date) DO UPDATE, so re-running on the
    same day replaces that day's briefing instead of accumulating
    duplicates."""
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO briefings (as_of_date, provider_ccns, facts, body, model)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (as_of_date) DO UPDATE SET
                    provider_ccns = EXCLUDED.provider_ccns,
                    facts = EXCLUDED.facts,
                    body = EXCLUDED.body,
                    model = EXCLUDED.model,
                    generated_at = now()
                """,
                (
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
    as_of_date: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> BriefingResult:
    """Pure orchestration (no DB write): calls Claude, then rejects the
    result before it ever reaches save_briefing() if coverage or grounding
    fails. Raises IncompleteBriefing / UngroundedBriefing / ClaudeCallFailed
    rather than returning a partial result."""
    as_of_date = as_of_date or datetime.now(UTC).date()
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
        as_of_date=as_of_date,
        provider_ccns=[h.provider_ccn for h in flagged],
        facts=facts,
        body=text,
    )


def run() -> BriefingResult | None:
    load_env(ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set -- check .env")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set -- check .env")

    flagged = fetch_flagged_hospitals(database_url)
    if not flagged:
        print("No flagged hospitals -- nothing to brief.")
        return None

    client = anthropic.Anthropic(api_key=api_key)
    result = generate_grounded_briefing(client, flagged)
    save_briefing(result, database_url)
    print(f"Saved briefing for {result.as_of_date} covering {len(result.provider_ccns)} hospital(s).")
    return result


if __name__ == "__main__":
    run()
