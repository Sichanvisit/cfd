"""Ingest stage."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def run(ctx: dict) -> dict:
    source_csv = Path(ctx["source_csv"])
    if not source_csv.exists():
        raise FileNotFoundError(f"source trade csv not found: {source_csv}")
    frame = pd.read_csv(source_csv)
    ctx["ingest_rows"] = int(len(frame))
    return ctx

