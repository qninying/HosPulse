"""Exports both real AI agents' run history from production Postgres into
a small, committed JSON file the static Command Center can read -- the
Command Center has no live database connection (it's a GitHub Pages
static site, and this repo's own rule is no secrets committed to it), so
"how many times has this agent actually run" has to be snapshotted into a
file the same way plan.json/progress.json already are, not queried live
from the browser.

AGENT-001 (Briefing Agent): a "run" is one company-scoped briefings row
(company_id IS NOT NULL) -- the pre-STORY-008 global briefing (one shared
row for every nationally-flagged hospital, company_id NULL) was a
different, since-removed code path and would misrepresent what AGENT-001
does today if counted here.

AGENT-002 (Cost Report Co-pilot): a "run" is one row in cost_report_findings
-- each is a genuine possible-missed-reimbursement finding that survived
both the citation check and the grounding check.

Both agents' `outcomes` dict is generic ({label: count}) rather than
agent-specific, so the Command Center's display code doesn't need to know
each agent's own status vocabulary.

This is a manual snapshot, not a live feed: re-run it and commit the
result whenever the real numbers should be refreshed, same cadence as
`scripts/build_plan.py` for the rest of the Command Center's data.

Usage: python3 export_agent_run_stats.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

from env import load_env

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / ".colaberry" / "agent_runs.json"


def fetch_briefing_agent_stats(database_url: str) -> dict:
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*), max(generated_at) FROM briefings WHERE company_id IS NOT NULL"
            )
            runs_recorded, last_run_at = cur.fetchone()

            cur.execute("SELECT status, count(*) FROM weekly_briefing_emails GROUP BY status")
            counts = {status: count for status, count in cur.fetchall()}
    finally:
        conn.close()

    return {
        "runs_recorded": runs_recorded,
        "last_run_at": last_run_at.isoformat() if last_run_at else None,
        "outcomes": {
            "sent": counts.get("sent", 0),
            "failed": counts.get("failed", 0),
            "pending": counts.get("pending", 0),
        },
    }


def fetch_cost_report_copilot_stats(database_url: str) -> dict:
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*), max(generated_at) FROM cost_report_findings")
            runs_recorded, last_run_at = cur.fetchone()

            cur.execute("SELECT status, count(*) FROM cost_report_findings GROUP BY status")
            counts = {status: count for status, count in cur.fetchall()}
    finally:
        conn.close()

    return {
        "runs_recorded": runs_recorded,
        "last_run_at": last_run_at.isoformat() if last_run_at else None,
        "outcomes": counts,
    }


def run() -> dict:
    load_env(ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set -- check .env")

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agents": {
            "AGENT-001": fetch_briefing_agent_stats(database_url),
            "AGENT-002": fetch_cost_report_copilot_stats(database_url),
        },
    }
    OUTPUT_PATH.write_text(json.dumps(stats, indent=2) + "\n")
    return stats


if __name__ == "__main__":
    stats = run()
    print(json.dumps(stats, indent=2))
