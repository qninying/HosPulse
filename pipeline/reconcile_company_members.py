"""STORY-009: reconcile company_members.user_id to a real auth.users.id
once an operator has actually signed in for real.

The hand-seeded test row (from STORY-008/010's live verification) carries a
random UUID that was never a real Supabase Auth user -- Supabase Auth
creates a brand-new auth.users row with its own UUID at first magic-link
sign-in, it does not adopt an existing seeded UUID. This script closes that
gap by matching on the email column already added to company_members for
weekly briefing delivery.

Idempotent: safe to run any number of times. A row already pointing at the
correct auth.users.id is left untouched and is not reported as a change.

Usage: python3 reconcile_company_members.py
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg2

from env import load_env

ROOT = Path(__file__).resolve().parent.parent


def reconcile(database_url: str) -> list[tuple[str, str, str]]:
    """Returns (email, old_user_id, new_user_id) for every row actually changed."""
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT cm.email, cm.user_id, au.id
                FROM company_members cm
                JOIN auth.users au ON au.email = cm.email
                WHERE cm.email IS NOT NULL AND cm.user_id IS DISTINCT FROM au.id
                """
            )
            changes = [(email, str(old_id), str(new_id)) for email, old_id, new_id in cur.fetchall()]

            cur.execute(
                """
                UPDATE company_members cm
                SET user_id = au.id
                FROM auth.users au
                WHERE cm.email = au.email
                  AND cm.email IS NOT NULL
                  AND cm.user_id IS DISTINCT FROM au.id
                """
            )
    finally:
        conn.close()
    return changes


def run() -> list[tuple[str, str, str]]:
    load_env(ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set -- check .env")
    return reconcile(database_url)


if __name__ == "__main__":
    changes = run()
    if not changes:
        print("No company_members rows needed reconciliation.")
    for email, old_id, new_id in changes:
        print(f"{email}: {old_id} -> {new_id}")
