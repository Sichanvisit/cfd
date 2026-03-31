"""Daily staged training DAG entrypoint.

Run:
    py -3.12 -m ml.pipelines.dags.daily_training
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from ml.pipelines.stages import deploy, evaluate, feature_build, ingest, train, validate

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _build_context(args: argparse.Namespace) -> dict:
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    staging_models_dir = Path(args.models_dir) / f"_staging_pipeline_{run_tag}"
    return {
        "run_tag": run_tag,
        "source_csv": str(Path(args.source_csv)),
        "datasets_dir": str(Path(args.datasets_dir)),
        "models_dir": str(Path(args.models_dir)),
        "staging_models_dir": str(staging_models_dir),
        "active_model_path": str(Path(args.models_dir) / "ai_models.joblib"),
        "active_metrics_path": str(Path(args.models_dir) / "metrics.json"),
        "deploy_state_path": str(Path(args.models_dir) / "deploy_state.json"),
        "backup_dir": str(Path(args.models_dir) / "backups"),
        "per_symbol_limit": int(args.per_symbol_limit),
        "symbols": tuple(args.symbols),
        "min_entry_auc": float(args.min_entry_auc),
        "min_exit_auc": float(args.min_exit_auc),
        "min_test_samples": int(args.min_test_samples),
        "min_entry_acc_when_auc_nan": float(args.min_entry_acc_when_auc_nan),
        "min_exit_acc_when_auc_nan": float(args.min_exit_acc_when_auc_nan),
        "force_deploy": bool(args.force),
        "exit_only": bool(args.exit_only),
    }


def run_once(ctx: dict) -> dict:
    for stage in (ingest, validate, feature_build, train, evaluate, deploy):
        ctx = stage.run(ctx)
    return ctx


def main() -> None:
    parser = argparse.ArgumentParser(description="Run staged daily training pipeline DAG.")
    parser.add_argument("--source-csv", default=str(PROJECT_ROOT / "data" / "trades" / "trade_history.csv"))
    parser.add_argument("--datasets-dir", default=str(PROJECT_ROOT / "data" / "datasets"))
    parser.add_argument("--models-dir", default=str(PROJECT_ROOT / "models"))
    parser.add_argument("--per-symbol-limit", type=int, default=100)
    parser.add_argument("--symbols", nargs="+", default=["BTCUSD", "NAS100", "XAUUSD"])
    parser.add_argument("--min-entry-auc", type=float, default=0.35)
    parser.add_argument("--min-exit-auc", type=float, default=0.20)
    parser.add_argument("--min-test-samples", type=int, default=8)
    parser.add_argument("--min-entry-acc-when-auc-nan", type=float, default=0.55)
    parser.add_argument("--min-exit-acc-when-auc-nan", type=float, default=0.55)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--exit-only", action="store_true")
    parser.add_argument("--keep-staging", action="store_true")
    args = parser.parse_args()

    ctx = _build_context(args)
    result = run_once(ctx)
    print(f"[pipeline] gate_ok={result.get('gate_ok')} reason={result.get('gate_reason')}")
    print(f"[pipeline] deployed={result.get('deployed')}")

    if not bool(args.keep_staging):
        staging_dir = Path(result["staging_models_dir"])
        shutil.rmtree(staging_dir, ignore_errors=True)


if __name__ == "__main__":
    main()

