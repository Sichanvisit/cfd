"""Validate stage."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = (
    "ticket",
    "symbol",
    "status",
    "open_time",
    "profit",
)


def run(ctx: dict) -> dict:
    source_csv = Path(ctx["source_csv"])
    frame = pd.read_csv(source_csv, nrows=2000)
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"validate failed: missing required columns {missing}")
    ctx["validate_required_columns"] = list(REQUIRED_COLUMNS)
    return ctx

