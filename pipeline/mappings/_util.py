"""Shared helpers for source-system mapping modules."""
from __future__ import annotations


def to_float(value) -> float | None:
    """CSV values arrive as strings, and a genuinely missing column comes
    through as None -- every mapping module's compute_metrics() needs the
    same coercion before doing arithmetic on a metric source column, so
    it lives here once instead of duplicated per vendor."""
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    return float(value)
