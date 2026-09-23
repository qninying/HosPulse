"""STORY-006: proves row-level security actually isolates each
management company's data, using real Postgres RLS rather than a mock
or "the policy definition exists" check.

`SET LOCAL ROLE authenticated; SET LOCAL request.jwt.claim.sub = ...` is
the standard way to test Supabase RLS from outside the running app --
confirmed live against this database's actual `auth.uid()` definition
(reads `request.jwt.claim.sub`) before writing the policies in
pipeline/schema.sql's STORY-006 section, rather than assumed.

This touches the live Supabase database directly. This project's own
rule is that integration tests require explicit opt-in and must never
run automatically -- skipped by default, unlike the rest of pipeline/'s
pure-logic tests.

Run: cd HosPulse && RUN_RLS_INTEGRATION_TESTS=1 ./.venv/bin/python -m pytest pipeline/test_row_level_security.py -v
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import psycopg2
import pytest

from env import load_env

if not os.environ.get("RUN_RLS_INTEGRATION_TESTS"):
    pytest.skip(
        "live-database integration test; set RUN_RLS_INTEGRATION_TESTS=1 to run",
        allow_module_level=True,
    )

ROOT = Path(__file__).resolve().parent.parent
load_env(ROOT / ".env")
DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture
def rls_fixture():
    """Two real hospitals, two companies, one user each, and one month
    of metrics per hospital -- everything the isolation checks below
    need. Always cleaned up, even if a test fails."""
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT provider_ccn FROM hospitals ORDER BY provider_ccn LIMIT 2")
    ccn_a, ccn_b = [r[0] for r in cur.fetchall()]

    company_a, company_b = str(uuid.uuid4()), str(uuid.uuid4())
    user_a, user_b, stranger = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    source_a, source_b = f"rls_test_{uuid.uuid4()}.csv", f"rls_test_{uuid.uuid4()}.csv"

    cur.execute(
        "INSERT INTO companies (id, name) VALUES (%s, 'RLS Test Co A'), (%s, 'RLS Test Co B')",
        (company_a, company_b),
    )
    cur.execute(
        "INSERT INTO company_members (company_id, user_id) VALUES (%s, %s), (%s, %s)",
        (company_a, user_a, company_b, user_b),
    )
    cur.execute(
        "INSERT INTO company_hospitals (company_id, provider_ccn) VALUES (%s, %s), (%s, %s)",
        (company_a, ccn_a, company_b, ccn_b),
    )
    cur.execute(
        "INSERT INTO export_conversions (source_file, source_file_hash, source_system, "
        "status, metrics_count, provider_ccn) VALUES (%s, %s, 'epic', 'ok', 1, %s) RETURNING id",
        (source_a, f"hash-{source_a}", ccn_a),
    )
    conv_a = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO export_conversions (source_file, source_file_hash, source_system, "
        "status, metrics_count, provider_ccn) VALUES (%s, %s, 'epic', 'ok', 1, %s) RETURNING id",
        (source_b, f"hash-{source_b}", ccn_b),
    )
    conv_b = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO hospital_monthly_metrics (provider_ccn, month, metric_name, metric_value, "
        "source_file, source_system, conversion_id) VALUES (%s, '2026-09-01', 'cash_on_hand', "
        "100000, %s, 'epic', %s)",
        (ccn_a, source_a, conv_a),
    )
    cur.execute(
        "INSERT INTO hospital_monthly_metrics (provider_ccn, month, metric_name, metric_value, "
        "source_file, source_system, conversion_id) VALUES (%s, '2026-09-01', 'cash_on_hand', "
        "200000, %s, 'epic', %s)",
        (ccn_b, source_b, conv_b),
    )
    cur.execute(
        "INSERT INTO slipping_hospital_alerts (provider_ccn, status) VALUES (%s, 'not_slipping') "
        "ON CONFLICT (provider_ccn) DO UPDATE SET status = EXCLUDED.status",
        (ccn_a,),
    )
    cur.execute(
        "INSERT INTO slipping_hospital_alerts (provider_ccn, status) VALUES (%s, 'not_slipping') "
        "ON CONFLICT (provider_ccn) DO UPDATE SET status = EXCLUDED.status",
        (ccn_b,),
    )
    conn.commit()

    try:
        yield {
            "conn": conn,
            "ccn_a": ccn_a,
            "ccn_b": ccn_b,
            "user_a": user_a,
            "user_b": user_b,
            "stranger": stranger,
            "source_a": source_a,
            "source_b": source_b,
        }
    finally:
        cur.execute(
            "DELETE FROM hospital_monthly_metrics WHERE source_file IN (%s, %s)",
            (source_a, source_b),
        )
        cur.execute(
            "DELETE FROM export_conversions WHERE source_file IN (%s, %s)", (source_a, source_b)
        )
        cur.execute(
            "DELETE FROM slipping_hospital_alerts WHERE provider_ccn IN (%s, %s)", (ccn_a, ccn_b)
        )
        cur.execute(
            "DELETE FROM company_hospitals WHERE company_id IN (%s, %s)", (company_a, company_b)
        )
        cur.execute(
            "DELETE FROM company_members WHERE company_id IN (%s, %s)", (company_a, company_b)
        )
        cur.execute("DELETE FROM companies WHERE id IN (%s, %s)", (company_a, company_b))
        conn.commit()
        conn.close()


def _query_as(conn, role: str, jwt_sub: str | None, sql: str, params: tuple = ()) -> list:
    """Runs `sql` as `role` with request.jwt.claim.sub set to `jwt_sub`
    (unset entirely for a fully anonymous session) -- genuinely exercises
    RLS rather than mocking it. Always rolled back: a read-only probe."""
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute(f"SET LOCAL ROLE {role}")
        if jwt_sub is not None:
            cur.execute("SET LOCAL request.jwt.claim.sub = %s", (jwt_sub,))
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.execute("ROLLBACK")
    return rows


def test_a_company_sees_only_its_own_hospitals_monthly_metrics(rls_fixture):
    rows = _query_as(
        rls_fixture["conn"],
        "authenticated",
        rls_fixture["user_a"],
        "SELECT provider_ccn FROM hospital_monthly_metrics WHERE source_file IN (%s, %s)",
        (rls_fixture["source_a"], rls_fixture["source_b"]),
    )
    assert rows == [(rls_fixture["ccn_a"],)]


def test_the_other_company_sees_only_its_own_hospitals_monthly_metrics(rls_fixture):
    rows = _query_as(
        rls_fixture["conn"],
        "authenticated",
        rls_fixture["user_b"],
        "SELECT provider_ccn FROM hospital_monthly_metrics WHERE source_file IN (%s, %s)",
        (rls_fixture["source_a"], rls_fixture["source_b"]),
    )
    assert rows == [(rls_fixture["ccn_b"],)]


def test_export_conversions_audit_rows_are_also_company_scoped(rls_fixture):
    rows = _query_as(
        rls_fixture["conn"],
        "authenticated",
        rls_fixture["user_a"],
        "SELECT provider_ccn FROM export_conversions WHERE source_file IN (%s, %s)",
        (rls_fixture["source_a"], rls_fixture["source_b"]),
    )
    assert rows == [(rls_fixture["ccn_a"],)]


def test_slipping_hospital_alerts_are_also_company_scoped(rls_fixture):
    rows = _query_as(
        rls_fixture["conn"],
        "authenticated",
        rls_fixture["user_a"],
        "SELECT provider_ccn FROM slipping_hospital_alerts WHERE provider_ccn IN (%s, %s)",
        (rls_fixture["ccn_a"], rls_fixture["ccn_b"]),
    )
    assert rows == [(rls_fixture["ccn_a"],)]


def test_a_user_with_no_company_membership_sees_nothing(rls_fixture):
    rows = _query_as(
        rls_fixture["conn"],
        "authenticated",
        rls_fixture["stranger"],
        "SELECT provider_ccn FROM hospital_monthly_metrics WHERE source_file IN (%s, %s)",
        (rls_fixture["source_a"], rls_fixture["source_b"]),
    )
    assert rows == []


def test_a_fully_anonymous_session_sees_nothing(rls_fixture):
    rows = _query_as(
        rls_fixture["conn"],
        "anon",
        None,
        "SELECT provider_ccn FROM hospital_monthly_metrics WHERE source_file IN (%s, %s)",
        (rls_fixture["source_a"], rls_fixture["source_b"]),
    )
    assert rows == []
