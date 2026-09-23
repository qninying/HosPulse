"""Epic (Community Connect) monthly financial export mapping.

Every mapping module in this package exposes the same four names, which
is the whole contract `export_normalizer.py` and `detect_format()` rely
on: FINGERPRINT_COLUMNS, HOSPITAL_ID_COLUMN, MONTH_COLUMN, is_totals_row,
compute_metrics.
"""
from __future__ import annotations

from ._util import to_float

SOURCE_SYSTEM_NAME = "epic"

FINGERPRINT_COLUMNS = frozenset({
    "hospital_ccn",
    "report_month",
    "line_type",
    "cash_balance",
    "net_ar_balance",
    "denied_claims",
    "total_claims",
    "open_fte_positions",
})

HOSPITAL_ID_COLUMN = "hospital_ccn"
MONTH_COLUMN = "report_month"


def is_totals_row(row) -> bool:
    """Epic exports carry a synthetic 'TOTAL' line_type row -- a
    system-generated grand total, not a real month's data -- that must
    be dropped before mapping (failure path: 'a totals row is counted
    as a data row')."""
    return str(row.get("line_type", "")).strip().upper() == "TOTAL"


def compute_metrics(row) -> dict:
    """Map one export row to HosPulse's standard monthly metric names.

    denial_rate_pct is derived here since Epic doesn't report it
    directly -- None (not 0) when total_claims is 0 or missing, so an
    idle or unreported month is never misread as a 0% denial rate.
    """
    total_claims = to_float(row.get("total_claims"))
    denied = to_float(row.get("denied_claims"))
    denial_rate_pct = (
        round(100 * denied / total_claims, 2)
        if total_claims not in (None, 0) and denied is not None
        else None
    )
    return {
        "cash_on_hand": to_float(row.get("cash_balance")),
        "ar_balance": to_float(row.get("net_ar_balance")),
        "denial_rate_pct": denial_rate_pct,
        "open_positions": to_float(row.get("open_fte_positions")),
    }
