"""Cerner (Oracle Health) monthly financial export mapping.

Different vendor, different column names and totals-row convention from
epic.py -- this is what proves normalization actually reconciles two
distinct export shapes onto the same standard metric names, rather than
hard-coding one vendor's layout.
"""
from __future__ import annotations

from ._util import to_float

SOURCE_SYSTEM_NAME = "cerner"

FINGERPRINT_COLUMNS = frozenset({
    "provider_ccn",
    "period_end",
    "row_category",
    "unrestricted_cash",
    "net_patient_ar",
    "claims_denied_count",
    "claims_total_count",
    "vacant_positions",
})

HOSPITAL_ID_COLUMN = "provider_ccn"
MONTH_COLUMN = "period_end"


def is_totals_row(row) -> bool:
    """Cerner exports mark their grand-total row with row_category ==
    'GRAND_TOTAL' -- a different convention from Epic's, on purpose."""
    return str(row.get("row_category", "")).strip().upper() == "GRAND_TOTAL"


def compute_metrics(row) -> dict:
    """Map one export row to the same standard metric names epic.py
    produces, so a management company can compare hospitals running
    either system."""
    total_claims = to_float(row.get("claims_total_count"))
    denied = to_float(row.get("claims_denied_count"))
    denial_rate_pct = (
        round(100 * denied / total_claims, 2)
        if total_claims not in (None, 0) and denied is not None
        else None
    )
    return {
        "cash_on_hand": to_float(row.get("unrestricted_cash")),
        "ar_balance": to_float(row.get("net_patient_ar")),
        "denial_rate_pct": denial_rate_pct,
        "open_positions": to_float(row.get("vacant_positions")),
    }
