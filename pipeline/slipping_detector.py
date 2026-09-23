"""STORY-012: surface slipping hospitals from operator-uploaded monthly
metrics (hospital_monthly_metrics, STORY-011), so a management company
sees the decline the moment a month's export is normalized rather than
waiting for its own next monthly review cycle.

REQ-016: surface a slipping hospital at least 4 weeks earlier than the
operator's current reporting cycle. There is no timestamped "operator
reporting cycle" anywhere in this system to literally measure elapsed
time against -- the defensible reading, confirmed with the user, is
structural: detection runs automatically at data-ingestion time (this
module, called right after STORY-011 normalizes a month) rather than
waiting for a human's own ~monthly review, which is what "4 weeks
earlier" means in practice.

REQ-016 gives no numeric thresholds (unlike REQ-004/REQ-005, which said
"below 0%" and "below 30 days" explicitly). Rather than invent an
unstated magic number, each criterion below triggers on a plain
month-over-month directional change -- confirmed with the user as the
implementation of "2 consecutive months of decline/rise":

  - cash_on_hand declining
  - denial_rate_pct rising
  - ar_balance rising

Missing data is never treated as "no problem," same philosophy as
STORY-004: a criterion whose required metric is missing in either month,
or whose two latest months aren't genuinely consecutive calendar months,
is "not_assessable", not "not_triggered".

Usage: python3 slipping_detector.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

import psycopg2
import psycopg2.extras

from env import load_env


@dataclass
class MonthMetrics:
    month: str  # ISO date, first-of-month
    cash_on_hand: float | None
    denial_rate_pct: float | None
    ar_balance: float | None


@dataclass
class CriterionResult:
    name: str
    status: str  # "triggered" | "not_triggered" | "not_assessable"
    values: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"name": self.name, "status": self.status, "values": self.values}


@dataclass
class SlippingEvaluation:
    provider_ccn: str
    as_of_month: str | None
    status: str  # "slipping" | "not_slipping" | "not_assessable"
    criteria: list[CriterionResult]


def _months_apart(earlier: str, later: str) -> int:
    """Calendar months between two ISO 'YYYY-MM-DD' dates, e.g. 2026-12-01
    -> 2027-01-01 is 1, correctly crossing the year boundary."""
    ey, em = int(earlier[:4]), int(earlier[5:7])
    ly, lm = int(later[:4]), int(later[5:7])
    return (ly * 12 + lm) - (ey * 12 + em)


def evaluate_slipping(provider_ccn: str, months: list[MonthMetrics]) -> SlippingEvaluation:
    """`months` must already be sorted ascending by month."""
    if not months:
        criteria = [
            CriterionResult("cash_on_hand_declining", "not_assessable"),
            CriterionResult("denial_rate_rising", "not_assessable"),
            CriterionResult("ar_balance_rising", "not_assessable"),
        ]
        return SlippingEvaluation(provider_ccn, None, "not_assessable", criteria)

    as_of_month = months[-1].month

    if len(months) < 2 or _months_apart(months[-2].month, months[-1].month) != 1:
        reason = (
            {"months_available": len(months)}
            if len(months) < 2
            else {
                "months": [months[-2].month, months[-1].month],
                "reason": "the two latest months are not consecutive calendar months",
            }
        )
        criteria = [
            CriterionResult("cash_on_hand_declining", "not_assessable", reason),
            CriterionResult("denial_rate_rising", "not_assessable", reason),
            CriterionResult("ar_balance_rising", "not_assessable", reason),
        ]
        return SlippingEvaluation(provider_ccn, as_of_month, "not_assessable", criteria)

    prior, latest = months[-2], months[-1]
    criteria = [
        _evaluate_cash_declining(prior, latest),
        _evaluate_denial_rate_rising(prior, latest),
        _evaluate_ar_balance_rising(prior, latest),
    ]

    if any(c.status == "triggered" for c in criteria):
        status = "slipping"
    elif any(c.status == "not_assessable" for c in criteria):
        status = "not_assessable"
    else:
        status = "not_slipping"

    return SlippingEvaluation(provider_ccn, as_of_month, status, criteria)


def _evaluate_cash_declining(prior: MonthMetrics, latest: MonthMetrics) -> CriterionResult:
    name = "cash_on_hand_declining"
    if prior.cash_on_hand is None or latest.cash_on_hand is None:
        return CriterionResult(name, "not_assessable", {"months": [prior.month, latest.month]})
    triggered = latest.cash_on_hand < prior.cash_on_hand
    return CriterionResult(
        name,
        "triggered" if triggered else "not_triggered",
        {
            "months": [prior.month, latest.month],
            "cash_on_hand": [prior.cash_on_hand, latest.cash_on_hand],
        },
    )


def _evaluate_denial_rate_rising(prior: MonthMetrics, latest: MonthMetrics) -> CriterionResult:
    name = "denial_rate_rising"
    if prior.denial_rate_pct is None or latest.denial_rate_pct is None:
        return CriterionResult(name, "not_assessable", {"months": [prior.month, latest.month]})
    triggered = latest.denial_rate_pct > prior.denial_rate_pct
    return CriterionResult(
        name,
        "triggered" if triggered else "not_triggered",
        {
            "months": [prior.month, latest.month],
            "denial_rate_pct": [prior.denial_rate_pct, latest.denial_rate_pct],
        },
    )


def _evaluate_ar_balance_rising(prior: MonthMetrics, latest: MonthMetrics) -> CriterionResult:
    name = "ar_balance_rising"
    if prior.ar_balance is None or latest.ar_balance is None:
        return CriterionResult(name, "not_assessable", {"months": [prior.month, latest.month]})
    triggered = latest.ar_balance > prior.ar_balance
    return CriterionResult(
        name,
        "triggered" if triggered else "not_triggered",
        {
            "months": [prior.month, latest.month],
            "ar_balance": [prior.ar_balance, latest.ar_balance],
        },
    )


def fetch_all_hospital_months(database_url: str) -> dict[str, list[MonthMetrics]]:
    """Every (hospital, month) with at least one normalized metric,
    ascending by month. hospital_monthly_metrics stores one row per
    (hospital, month, metric_name) -- pivoted here into one MonthMetrics
    per (hospital, month), same long-to-wide pivot-in-Python style
    hcris_import.py already uses for its worksheet rows. A hospital with
    no monthly data at all (never normalized via STORY-011) is simply
    absent, same as fetch_all_hospital_years() in early_warning.py."""
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT provider_ccn, month, metric_name, metric_value
                FROM hospital_monthly_metrics
                ORDER BY provider_ccn, month ASC
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    pivoted: dict[tuple[str, str], dict[str, float]] = {}
    for provider_ccn, month, metric_name, metric_value in rows:
        month_str = month.isoformat()
        key = (provider_ccn, month_str)
        pivoted.setdefault(key, {})[metric_name] = (
            float(metric_value) if metric_value is not None else None
        )

    by_hospital: dict[str, list[MonthMetrics]] = {}
    for (provider_ccn, month_str), metrics in sorted(pivoted.items(), key=lambda kv: kv[0]):
        by_hospital.setdefault(provider_ccn, []).append(
            MonthMetrics(
                month=month_str,
                cash_on_hand=metrics.get("cash_on_hand"),
                denial_rate_pct=metrics.get("denial_rate_pct"),
                ar_balance=metrics.get("ar_balance"),
            )
        )
    return by_hospital


def upsert_alerts(evaluations: list[SlippingEvaluation], database_url: str) -> None:
    """Idempotent: ON CONFLICT (provider_ccn) DO UPDATE, so re-running the
    detector (e.g. after a new month is normalized) replaces a hospital's
    alert state instead of accumulating history or duplicating rows."""
    if not evaluations:
        return
    conn = psycopg2.connect(database_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO slipping_hospital_alerts (
                    provider_ccn, as_of_month, status, criteria
                ) VALUES %s
                ON CONFLICT (provider_ccn) DO UPDATE SET
                    as_of_month = EXCLUDED.as_of_month,
                    status = EXCLUDED.status,
                    criteria = EXCLUDED.criteria,
                    analyzed_at = now()
                """,
                [
                    (
                        e.provider_ccn,
                        e.as_of_month,
                        e.status,
                        psycopg2.extras.Json([c.to_json() for c in e.criteria]),
                    )
                    for e in evaluations
                ],
            )
    finally:
        conn.close()


def run(database_url: str) -> list[SlippingEvaluation]:
    by_hospital = fetch_all_hospital_months(database_url)
    evaluations = [
        evaluate_slipping(ccn, months) for ccn, months in by_hospital.items()
    ]
    upsert_alerts(evaluations, database_url)
    return evaluations


if __name__ == "__main__":
    import os
    from pathlib import Path

    ROOT = Path(__file__).resolve().parent.parent
    load_env(ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set -- check .env")

    results = run(database_url)
    slipping = sum(1 for e in results if e.status == "slipping")
    not_assessable = sum(1 for e in results if e.status == "not_assessable")
    not_slipping = len(results) - slipping - not_assessable
    print(
        f"Evaluated {len(results)} hospitals: "
        f"{slipping} slipping, {not_assessable} not assessable, {not_slipping} not slipping"
    )
