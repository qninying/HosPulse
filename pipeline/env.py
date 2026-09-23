"""Shared .env loader.

Extracted out of hcris_import.py and early_warning.py once a third module
(export_normalizer.py) needed the same function -- this project's own
composition rule is "three is the threshold" for lifting duplicated logic.
"""
from __future__ import annotations

import os
from pathlib import Path


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)
