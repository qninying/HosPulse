"""Compliance follow-up: a real one-click unsubscribe for the weekly
briefing email (pipeline/weekly_briefing_email.py), not a mailto link.

The link embedded in each email is HMAC-signed per (company_id, email)
using UNSUBSCRIBE_SECRET, so an unauthenticated visitor can unsubscribe
without logging in, but cannot unsubscribe someone else's address by
guessing or editing the URL -- verify_unsubscribe_token() only accepts a
token it can re-derive from the same secret.

The write itself is idempotent: unsubscribed_at is set once, via
COALESCE, and never overwritten by a repeat click -- clicking twice must
not change anything a second time.

This module is called two ways:
- Imported directly by weekly_briefing_email.py to build each recipient's
  link (build_unsubscribe_url).
- As a subprocess from frontend/src/app/api/unsubscribe/route.ts (GET
  request from the email link), the same bridge pattern
  export_normalizer.py already established for the upload route: Node
  never touches the database directly, it shells out and parses the
  final JSON line this script prints.

Usage: python3 unsubscribe.py --company <uuid> --email <email> --token <token>
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import psycopg2

from env import load_env

ROOT = Path(__file__).resolve().parent.parent


def generate_unsubscribe_token(company_id: str, email: str, secret: str) -> str:
    message = f"{company_id}:{email}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_unsubscribe_token(company_id: str, email: str, token: str, secret: str) -> bool:
    expected = generate_unsubscribe_token(company_id, email, secret)
    # Constant-time compare -- a naive `==` would let an attacker learn
    # the correct token one byte at a time from response-time differences.
    return hmac.compare_digest(expected, token)


def build_unsubscribe_url(company_id: str, email: str, secret: str, base_url: str) -> str:
    token = generate_unsubscribe_token(company_id, email, secret)
    query = urllib.parse.urlencode({"company": company_id, "email": email, "token": token})
    return f"{base_url.rstrip('/')}/api/unsubscribe?{query}"


@dataclass
class UnsubscribeResult:
    status: str  # "unsubscribed" | "invalid_token"


def unsubscribe(
    company_id: str, email: str, token: str, secret: str, database_url: str
) -> UnsubscribeResult:
    if not verify_unsubscribe_token(company_id, email, token, secret):
        return UnsubscribeResult(status="invalid_token")

    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE company_members
                SET unsubscribed_at = COALESCE(unsubscribed_at, now())
                WHERE company_id = %s AND email = %s
                """,
                (company_id, email),
            )
    finally:
        conn.close()
    return UnsubscribeResult(status="unsubscribed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()

    load_env(ROOT / ".env")
    secret = os.environ.get("UNSUBSCRIBE_SECRET")
    database_url = os.environ.get("DATABASE_URL")
    if not secret or not database_url:
        print(json.dumps({"status": "error", "message": "server misconfigured"}))
        sys.exit(1)

    result = unsubscribe(args.company, args.email, args.token, secret, database_url)
    print(json.dumps({"status": result.status}))
    sys.exit(0)
