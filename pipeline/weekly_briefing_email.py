"""STORY-008 (.colaberry) / STORY-010 (.hospulse): email the weekly
hospitals-at-risk briefing to every real operator.

REQ-014: send a weekly email briefing every Monday at 6:00 AM Central.

Reuses, does not rebuild:
- briefing_agent.generate_and_save_company_briefing() (STORY-003 /
  STORY-007) to generate and save one company's grounded briefing, scoped
  to only the hospitals that company manages (company_hospitals,
  STORY-006). One briefing is generated per company, not one shared
  briefing for everyone -- the earlier global design broke the moment a
  real per-company weekly email had to go out (253 nationally-flagged
  hospitals do not fit in one Claude response).
- companies / company_members for the real operator list.

Three ways this can legitimately fail, all handled explicitly, each
isolated to the one company it happened to:

- Briefing generation failure (InvalidEngineOutput / ClaudeCallFailed /
  UngroundedBriefing / IncompleteBriefing from briefing_agent.py): that
  one company's operators receive no email this run and nothing is
  recorded as sent; it does not stop the run for other companies.
- ResendCallFailed: every delivery attempt to one operator failed
  (timeout, connection error, or a retryable Resend status). Retried up
  to MAX_ATTEMPTS times with backoff, then recorded as status='failed' in
  weekly_briefing_emails with the error message. The briefing itself is
  still saved regardless -- this only affects delivery to that operator.
- Idempotency across triggers, not retries: a (company_id, week_of,
  recipient_email) row is reserved via INSERT ... ON CONFLICT DO NOTHING
  *before* Resend is ever called. A run triggered twice in the same week
  sends at most once per operator, even under a concurrent double-trigger.
  A 'failed' row is not auto-retried by a later run -- a human reviews it
  and re-triggers manually; that is this system's dead-letter path.

DST note: GitHub Actions cron runs in UTC, and 6:00 AM Central is either
11:00 or 12:00 UTC depending on the time of year. The workflow schedules
both; should_run_now() is the actual gate that makes exactly one of those
two firings do real work, regardless of which side of the DST transition
it is.

Usage: python3 weekly_briefing_email.py [--force]
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import anthropic
import psycopg2
import resend
from resend.http_client_requests import RequestsClient

import briefing_agent
from env import load_env

ROOT = Path(__file__).resolve().parent.parent
CENTRAL = ZoneInfo("America/Chicago")

FROM_ADDRESS = "onboarding@resend.dev"
MAX_ATTEMPTS = 4  # first attempt + at most 3 retries
REQUEST_TIMEOUT_SECONDS = 10.0
BACKOFF_SECONDS = (1.0, 2.0, 4.0)

# HTTP statuses worth retrying: rate limit and upstream server trouble.
# Anything else (bad request, invalid/missing API key, validation error)
# fails fast -- a different prompt or attempt would not fix it.
_RETRYABLE_HTTP_CODES = {"429", "500", "502", "503", "504"}


class ResendCallFailed(Exception):
    """Every delivery attempt to one operator failed. Recorded as
    'failed' in weekly_briefing_emails; nothing further is retried this
    run."""


@dataclass
class Operator:
    company_id: str
    email: str


def should_run_now(now_central: datetime) -> bool:
    """REQ-014's actual time gate, evaluated in Central time regardless of
    which UTC offset GitHub Actions' cron fired at."""
    return now_central.weekday() == 0 and now_central.hour == 6


def week_start_for(d: date) -> date:
    return d - timedelta(days=d.weekday())


def build_subject(as_of_date: date) -> str:
    return f"HosPulse weekly briefing -- {as_of_date.isoformat()}"


def build_html(body: str) -> str:
    paragraphs = "".join(f"<p>{line}</p>" for line in body.split("\n") if line.strip())
    return f"<div>{paragraphs}</div>"


def fetch_operators(database_url: str) -> list[Operator]:
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT company_id, email FROM company_members WHERE email IS NOT NULL ORDER BY company_id, email"
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [Operator(str(company_id), email) for company_id, email in rows]


def group_operators_by_company(operators: list[Operator]) -> dict[str, list[str]]:
    by_company: dict[str, list[str]] = {}
    for operator in operators:
        by_company.setdefault(operator.company_id, []).append(operator.email)
    return by_company


def reserve_send_slot(conn, company_id: str, week_of: date, recipient_email: str, briefing_id: int) -> int | None:
    """The idempotency gate: reserved before any external call is made.
    Returns None if this (company, week, recipient) was already reserved
    -- already sent, already failed-and-logged, or a concurrent run got
    there first."""
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO weekly_briefing_emails
                (company_id, week_of, recipient_email, briefing_id, status)
            VALUES (%s, %s, %s, %s, 'pending')
            ON CONFLICT (company_id, week_of, recipient_email) DO NOTHING
            RETURNING id
            """,
            (company_id, week_of, recipient_email, briefing_id),
        )
        row = cur.fetchone()
    return row[0] if row else None


def record_send_result(
    conn,
    send_id: int,
    status: str,
    provider_message_id: str | None = None,
    error_message: str | None = None,
) -> None:
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE weekly_briefing_emails
            SET status = %s, provider_message_id = %s, error_message = %s, sent_at = now()
            WHERE id = %s
            """,
            (status, provider_message_id, error_message, send_id),
        )


def send_email_with_retry(
    resend_client,
    to_email: str,
    subject: str,
    html: str,
    max_attempts: int = MAX_ATTEMPTS,
    backoff: tuple[float, ...] = BACKOFF_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Returns Resend's message id. Raises ResendCallFailed if every
    attempt fails. A non-retryable error (bad request, auth) raises
    immediately without exhausting max_attempts."""
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            result = resend_client.Emails.send(
                {"from": FROM_ADDRESS, "to": [to_email], "subject": subject, "html": html}
            )
            return result["id"]
        except resend.exceptions.ResendError as e:
            if str(e.code) not in _RETRYABLE_HTTP_CODES:
                raise ResendCallFailed(
                    f"Resend send to {to_email} failed (non-retryable, code={e.code}): {e.message}"
                ) from e
            last_error = e
        except RuntimeError as e:
            # resend wraps a network-level failure (timeout, connection
            # error) from `requests` as a plain RuntimeError.
            last_error = e
        if attempt < max_attempts - 1:
            sleep(backoff[min(attempt, len(backoff) - 1)])
    raise ResendCallFailed(
        f"Resend send to {to_email} failed after {max_attempts} attempts: {last_error!r}"
    ) from last_error


def run(
    now_central: datetime | None = None,
    force: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    load_env(ROOT / ".env")
    now_central = now_central or datetime.now(CENTRAL)
    if not force and not should_run_now(now_central):
        print(f"Not the scheduled window ({now_central.isoformat()}) -- skipping. Use --force to override.")
        return {"skipped": True, "reason": "not_scheduled_window"}

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set -- check .env")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set -- check .env")
    resend_api_key = os.environ.get("RESEND_API_KEY")
    if not resend_api_key:
        raise RuntimeError("RESEND_API_KEY not set -- check .env")
    resend.api_key = resend_api_key
    resend.default_http_client = RequestsClient(timeout=int(REQUEST_TIMEOUT_SECONDS))
    claude_client = anthropic.Anthropic(api_key=anthropic_api_key)

    operators_by_company = group_operators_by_company(fetch_operators(database_url))
    if not operators_by_company:
        print("No real operators found -- nothing to email.")
        return {"skipped": True, "reason": "no_operators"}

    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        sent, already_sent, failed, no_briefing = 0, 0, 0, 0
        for company_id, emails in operators_by_company.items():
            try:
                briefing = briefing_agent.generate_and_save_company_briefing(claude_client, database_url, company_id)
            except (
                briefing_agent.InvalidEngineOutput,
                briefing_agent.ClaudeCallFailed,
                briefing_agent.UngroundedBriefing,
                briefing_agent.IncompleteBriefing,
            ) as e:
                print(f"Briefing generation failed for company {company_id}, skipping its operators: {e!r}")
                no_briefing += 1
                continue
            if briefing is None:
                no_briefing += 1
                continue

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM briefings WHERE company_id = %s AND as_of_date = %s",
                    (company_id, briefing.as_of_date),
                )
                briefing_id = cur.fetchone()[0]

            week_of = week_start_for(briefing.as_of_date)
            subject = build_subject(briefing.as_of_date)
            html = build_html(briefing.body)

            for email in emails:
                send_id = reserve_send_slot(conn, company_id, week_of, email, briefing_id)
                if send_id is None:
                    already_sent += 1
                    continue
                try:
                    message_id = send_email_with_retry(resend, email, subject, html, sleep=sleep)
                    record_send_result(conn, send_id, "sent", provider_message_id=message_id)
                    sent += 1
                except ResendCallFailed as e:
                    record_send_result(conn, send_id, "failed", error_message=str(e))
                    failed += 1
    finally:
        conn.close()

    print(
        f"Weekly briefing email run: {sent} sent, {already_sent} already sent this week, "
        f"{failed} failed, {no_briefing} company(ies) with nothing to brief."
    )
    return {"skipped": False, "sent": sent, "already_sent": already_sent, "failed": failed, "no_briefing": no_briefing}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="bypass the Monday 6am Central time gate")
    args = parser.parse_args()
    run(force=args.force)
