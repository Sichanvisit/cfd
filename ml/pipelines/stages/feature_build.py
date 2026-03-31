"""Feature build stage."""

from __future__ import annotations

from pathlib import Path

from ml.dataset_builder import build_datasets


def run(ctx: dict) -> dict:
    source_csv = Path(ctx["source_csv"])
    datasets_dir = Path(ctx["datasets_dir"])
    per_symbol_limit = int(ctx.get("per_symbol_limit", 100))
    symbols = tuple(ctx.get("symbols", ("BTCUSD", "NAS100", "XAUUSD")))
    entry_csv, exit_csv = build_datasets(
        source_csv=source_csv,
        out_dir=datasets_dir,
        per_symbol_limit=per_symbol_limit,
        symbols=symbols,
    )
    ctx["entry_csv"] = str(entry_csv)
    ctx["exit_csv"] = str(exit_csv)
    return ctx

