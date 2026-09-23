"""STORY-004: evaluate early-warning flags from already-computed financial
metrics (STORY-002) and store the result per hospital in Supabase.

REQ-004: flag a hospital when operating margin is below 0%, days cash on
hand is below 30, or days in A/R has risen for two fiscal years in a row.
REQ-005: store the exact values that triggered each flag, not just the
verdict.

Missing data is never treated as "no problem" -- an early-warning system
that quietly clears a hospital it couldn't actually check would defeat its
own purpose. A criterion whose required metric is missing is
"not_assessable", not "not_triggered", and a hospital with any
not_assessable criterion (and no actual trigger) is reported as
"not_assessable" overall, not silently cleared.

Usage: python3 early_warning.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import psycopg2
import psycopg2.extras

from env import load_env

ROOT = Path(__file__).resolve().parent.parent

OPERATING_MARGIN_THRESHOLD_PCT = 0.0
DAYS_CASH_ON_HAND_THRESHOLD_DAYS = 30.0


@dataclass
class YearMetrics:
    fiscal_year: int
    operating_margin_pct: float | None
    days_cash_on_hand: float | None
    days_in_ar: float | None


@dataclass
class CriterionResult:
    name: str
    status: str  # "triggered" | "not_triggered" | "not_assessable"
    values: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"name": self.name, "status": self.status, "values": self.values}


@dataclass
class FlagEvaluation:
    provider_ccn: str
    as_of_fiscal_year: int | None
    status: str  # "flagged" | "not_flagged" | "not_assessable"
    criteria: list[CriterionResult]


def evaluate_early_warning_flags(
    provider_ccn: str, years: list[YearMetrics]
) -> FlagEvaluation:
    """`years` must already be sorted ascending by fiscal_year -- same
    convention the Health Snapshot's own trend query uses."""
    if not years:
        criteria = [
            CriterionResult("operating_margin_negative", "not_assessable"),
            CriterionResult("days_cash_on_hand_low", "not_assessable"),
            CriterionResult("days_in_ar_rising_two_years", "not_assessable"),
        ]
        return FlagEvaluation(provider_ccn, None, "not_assessable", criteria)

    latest = years[-1]
    criteria = [
        _evaluate_operating_margin(latest),
        _evaluate_days_cash_on_hand(latest),
        _evaluate_days_in_ar_rising(years),
    ]

    if any(c.status == "triggered" for c in criteria):
        status = "flagged"
    elif any(c.status == "not_assessable" for c in criteria):
        status = "not_assessable"
    else:
        status = "not_flagged"

    return FlagEvaluation(provider_ccn, latest.fiscal_year, status, criteria)


def _evaluate_operating_margin(latest: YearMetrics) -> CriterionResult:
    name = "operating_margin_negative"
    if latest.operating_margin_pct is None:
        return CriterionResult(name, "not_assessable", {"fiscal_year": latest.fiscal_year})
    triggered = latest.operating_margin_pct < OPERATING_MARGIN_THRESHOLD_PCT
    return CriterionResult(
        name,
        "triggered" if triggered else "not_triggered",
        {
            "fiscal_year": latest.fiscal_year,
            "operating_margin_pct": latest.operating_margin_pct,
            "threshold_pct": OPERATING_MARGIN_THRESHOLD_PCT,
        },
    )


def _evaluate_days_cash_on_hand(latest: YearMetrics) -> CriterionResult:
    name = "days_cash_on_hand_low"
    if latest.days_cash_on_hand is None:
        return CriterionResult(name, "not_assessable", {"fiscal_year": latest.fiscal_year})
    triggered = latest.days_cash_on_hand < DAYS_CASH_ON_HAND_THRESHOLD_DAYS
    return CriterionResult(
        name,
        "triggered" if triggered else "not_triggered",
        {
            "fiscal_year": latest.fiscal_year,
            "days_cash_on_hand": latest.days_cash_on_hand,
            "threshold_days": DAYS_CASH_ON_HAND_THRESHOLD_DAYS,
        },
    )


def _evaluate_days_in_ar_rising(years: list[YearMetrics]) -> CriterionResult:
    """"Rising two years in a row" needs three consecutive fiscal years --
    two year-over-year increases back to back. A hospital with a real
    reporting gap (a known pattern in this dataset -- e.g. ANSON GENERAL
    HOSPITAL, CCN 670781, has no FY2023) cannot be honestly evaluated for
    this: comparing its FY2024 and FY2025 alone would silently drop "two
    years in a row" to one, understating what's actually being claimed."""
    name = "days_in_ar_rising_two_years"
    if len(years) < 3:
        return CriterionResult(name, "not_assessable", {"years_available": len(years)})

    y2, y1, y0 = years[-3], years[-2], years[-1]
    if y0.fiscal_year - y1.fiscal_year != 1 or y1.fiscal_year - y2.fiscal_year != 1:
        return CriterionResult(
            name,
            "not_assessable",
            {
                "fiscal_years": [y2.fiscal_year, y1.fiscal_year, y0.fiscal_year],
                "reason": "fiscal years are not consecutive",
            },
        )

    values = [y2.days_in_ar, y1.days_in_ar, y0.days_in_ar]
    if any(v is None for v in values):
        return CriterionResult(
            name,
            "not_assessable",
            {"fiscal_years": [y2.fiscal_year, y1.fiscal_year, y0.fiscal_year]},
        )

    triggered = values[0] < values[1] < values[2]
    return CriterionResult(
        name,
        "triggered" if triggered else "not_triggered",
        {
            "fiscal_years": [y2.fiscal_year, y1.fiscal_year, y0.fiscal_year],
            "days_in_ar": values,
        },
    )


def fetch_all_hospital_years(database_url: str) -> dict[str, list[YearMetrics]]:
    """Latest 3 fiscal years per hospital, ascending -- the same shape and
    limit as the Health Snapshot's own trend query
    (frontend/src/lib/hospitalDetail.ts), so the flag evaluator and the
    public page can never disagree about which years count as "the latest
    three"."""
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT provider_ccn, fiscal_year, operating_margin_pct,
                       days_cash_on_hand, days_in_ar
                FROM (
                    SELECT *,
                           row_number() OVER (
                               PARTITION BY provider_ccn ORDER BY fiscal_year DESC
                           ) AS rn
                    FROM cost_report_years
                ) ranked
                WHERE rn <= 3
                ORDER BY provider_ccn, fiscal_year ASC
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    by_hospital: dict[str, list[YearMetrics]] = {}
    for provider_ccn, fiscal_year, margin, cash, ar in rows:
        # psycopg2 returns Postgres numeric as Decimal; cast to float so
        # both the pure evaluation logic and the jsonb payload we store
        # (json.dumps can't serialize Decimal) work the same way the
        # frontend's own JS-number arithmetic on these columns does.
        by_hospital.setdefault(provider_ccn, []).append(
            YearMetrics(
                fiscal_year,
                float(margin) if margin is not None else None,
                float(cash) if cash is not None else None,
                float(ar) if ar is not None else None,
            )
        )
    return by_hospital


def upsert_flags(evaluations: list[FlagEvaluation], database_url: str) -> None:
    """Idempotent: ON CONFLICT (provider_ccn) DO UPDATE, so re-running the
    evaluator (e.g. after a new fiscal year is imported) replaces a
    hospital's flag state instead of accumulating history or duplicating
    rows -- every side effect in this project must be safe to run twice."""
    if not evaluations:
        return
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO early_warning_flags (
                    provider_ccn, as_of_fiscal_year, status, criteria
                ) VALUES %s
                ON CONFLICT (provider_ccn) DO UPDATE SET
                    as_of_fiscal_year = EXCLUDED.as_of_fiscal_year,
                    status = EXCLUDED.status,
                    criteria = EXCLUDED.criteria,
                    evaluated_at = now()
                """,
                [
                    (
                        e.provider_ccn,
                        e.as_of_fiscal_year,
                        e.status,
                        psycopg2.extras.Json([c.to_json() for c in e.criteria]),
                    )
                    for e in evaluations
                ],
            )
    finally:
        conn.close()


def run() -> list[FlagEvaluation]:
    load_env(ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set -- check .env")

    by_hospital = fetch_all_hospital_years(database_url)
    evaluations = [
        evaluate_early_warning_flags(ccn, years) for ccn, years in by_hospital.items()
    ]
    upsert_flags(evaluations, database_url)
    return evaluations


if __name__ == "__main__":
    results = run()
    flagged = sum(1 for e in results if e.status == "flagged")
    not_assessable = sum(1 for e in results if e.status == "not_assessable")
    not_flagged = len(results) - flagged - not_assessable
    print(
        f"Evaluated {len(results)} hospitals: "
        f"{flagged} flagged, {not_assessable} not assessable, {not_flagged} not flagged"
    )
