"""Source-system mapping registry for STORY-011 export normalization.

Each mapping module in this package declares the shape of one hospital
system's monthly export and how to translate it into HosPulse's standard
metric names. `detect_format()` matches an export purely by its column
fingerprint -- an exact subset check, never a fuzzy or partial match --
so an export missing even one expected column is correctly treated as
unmapped (REQ-012: mark unknown formats as 'needs mapping' rather than
guessing).

Adding support for a new hospital system means adding one module here
and listing it in `_REGISTRY` below -- nothing in export_normalizer.py
changes.
"""
from __future__ import annotations

from types import ModuleType

from . import cerner, epic

_REGISTRY: tuple[ModuleType, ...] = (epic, cerner)


def detect_format(columns) -> ModuleType | None:
    """Return the mapping module whose fingerprint is a subset of `columns`,
    or None if no known mapping matches.
    """
    cols = set(columns)
    for mapping in _REGISTRY:
        if mapping.FINGERPRINT_COLUMNS <= cols:
            return mapping
    return None
