"""Training stage."""

from __future__ import annotations

from pathlib import Path

from ml.train import train, train_exit_only


def run(ctx: dict) -> dict:
    entry_csv = Path(ctx["entry_csv"])
    exit_csv = Path(ctx["exit_csv"])
    staging_models_dir = Path(ctx["staging_models_dir"])
    exit_only = bool(ctx.get("exit_only", False))
    active_model_path = Path(ctx["active_model_path"])
    active_metrics_path = Path(ctx["active_metrics_path"])
    if exit_only:
        result = train_exit_only(
            exit_csv=exit_csv,
            base_model_path=active_model_path,
            out_dir=staging_models_dir,
            base_metrics_path=active_metrics_path,
        )
    else:
        result = train(entry_csv=entry_csv, exit_csv=exit_csv, out_dir=staging_models_dir)
    ctx["train_result"] = result
    return ctx

