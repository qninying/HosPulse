"""Live-database integration test for unsubscribe.py's actual write --
the pure token logic is covered without a database in test_unsubscribe.py,
this file only proves the UPDATE itself is real and idempotent.

This project's own rule is that integration tests require explicit opt-in
and must never run automatically -- skipped by default, same convention
as test_row_level_security.py.

Run: cd HosPulse && RUN_UNSUBSCRIBE_INTEGRATION_TESTS=1 ./.venv/bin/python -m pytest pipeline/test_unsubscribe_integration.py -v
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import psycopg2
import pytest

from env import load_env
from unsubscribe import generate_unsubscribe_token, unsubscribe

if not os.environ.get("RUN_UNSUBSCRIBE_INTEGRATION_TESTS"):
    pytest.skip(
        "live-database integration test; set RUN_UNSUBSCRIBE_INTEGRATION_TESTS=1 to run",
        allow_module_level=True,
    )

ROOT = Path(__file__).resolve().parent.parent
load_env(ROOT / ".env")
DATABASE_URL = os.environ["DATABASE_URL"]
SECRET = os.environ["UNSUBSCRIBE_SECRET"]


@pytest.fixture
def member_fixture():
    """One real company and one member with a real email -- deleted
    again even if a test fails."""
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    cur = conn.cursor()
    company_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    email = f"unsubscribe-test-{uuid.uuid4()}@example.com"
    cur.execute("INSERT INTO companies (id, name) VALUES (%s, 'Unsubscribe Test Co')", (company_id,))
    cur.execute(
        "INSERT INTO company_members (company_id, user_id, email) VALUES (%s, %s, %s)",
        (company_id, user_id, email),
    )
    conn.commit()
    try:
        yield conn, company_id, email
    finally:
        cur.execute("DELETE FROM company_members WHERE company_id = %s", (company_id,))
        cur.execute("DELETE FROM companies WHERE id = %s", (company_id,))
        conn.commit()
        cur.close()
        conn.close()


def _unsubscribed_at(conn, company_id, email):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT unsubscribed_at FROM company_members WHERE company_id = %s AND email = %s",
            (company_id, email),
        )
        return cur.fetchone()[0]


def test_a_valid_token_unsubscribes_the_real_row(member_fixture):
    conn, company_id, email = member_fixture
    assert _unsubscribed_at(conn, company_id, email) is None

    token = generate_unsubscribe_token(company_id, email, SECRET)
    result = unsubscribe(company_id, email, token, SECRET, DATABASE_URL)

    assert result.status == "unsubscribed"
    assert _unsubscribed_at(conn, company_id, email) is not None


def test_an_invalid_token_does_not_touch_the_row(member_fixture):
    conn, company_id, email = member_fixture
    result = unsubscribe(company_id, email, "not-a-real-token", SECRET, DATABASE_URL)

    assert result.status == "invalid_token"
    assert _unsubscribed_at(conn, company_id, email) is None


def test_clicking_the_link_twice_does_not_change_the_timestamp(member_fixture):
    conn, company_id, email = member_fixture
    token = generate_unsubscribe_token(company_id, email, SECRET)

    unsubscribe(company_id, email, token, SECRET, DATABASE_URL)
    first_timestamp = _unsubscribed_at(conn, company_id, email)

    unsubscribe(company_id, email, token, SECRET, DATABASE_URL)
    second_timestamp = _unsubscribed_at(conn, company_id, email)

    assert first_timestamp == second_timestamp
