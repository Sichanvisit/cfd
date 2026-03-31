"""
Automatic retrain + validation gate + model deployment.

Default single run:
    py -3.12 ml/retrain_and_deploy.py

Periodic mode:
    py -3.12 ml/retrain_and_deploy.py --interval-minutes 10
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.dataset_builder import build_datasets
from ml.train import train, train_exit_only

MODELS_DIR = PROJECT_ROOT / "models"
DATA_TRADES = PROJECT_ROOT / "data" / "trades" / "trade_history.csv"
DATASETS_DIR = PROJECT_ROOT / "data" / "datasets"
ACTIVE_MODEL = MODELS_DIR / "ai_models.joblib"
ACTIVE_METRICS = MODELS_DIR / "metrics.json"
BACKUP_DIR = MODELS_DIR / "backups"


def _is_good_metrics(
    metrics: dict,
    min_entry_auc: float,
    min_exit_auc: float,
    min_test_samples: int,
    min_entry_acc_when_auc_nan: float,
    min_exit_acc_when_auc_nan: float,
) -> tuple[bool, str]:
    em = metrics.get("entry_metrics", {})
    xm = metrics.get("exit_metrics", {})
    e_auc = em.get("auc")
    x_auc = xm.get("auc")
    e_n = int(em.get("samples", 0))
    x_n = int(xm.get("samples", 0))

    if e_n < min_test_samples or x_n < min_test_samples:
        return False, f"insufficient test samples entry={e_n}, exit={x_n}"

    e_auc_nan = (e_auc is None) or math.isnan(float(e_auc))
    x_auc_nan = (x_auc is None) or math.isnan(float(x_auc))
    e_acc = float(em.get("accuracy", 0.0) or 0.0)
    x_acc = float(xm.get("accuracy", 0.0) or 0.0)

    # In small/biased samples AUC can be NaN (single-class test split).
    # Use accuracy fallback gate to keep deployment pipeline alive.
    if e_auc_nan:
        if e_acc < float(min_entry_acc_when_auc_nan):
            return False, f"entry auc nan and acc {e_acc:.3f} < {min_entry_acc_when_auc_nan:.3f}"
    elif float(e_auc) < min_entry_auc:
        return False, f"entry auc {float(e_auc):.3f} < {min_entry_auc:.3f}"

    if x_auc_nan:
        if x_acc < float(min_exit_acc_when_auc_nan):
            return False, f"exit auc nan and acc {x_acc:.3f} < {min_exit_acc_when_auc_nan:.3f}"
    elif float(x_auc) < min_exit_auc:
        return False, f"exit auc {float(x_auc):.3f} < {min_exit_auc:.3f}"

    return True, "pass"


def _backup_active(now_tag: str):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if ACTIVE_MODEL.exists():
        shutil.copy2(ACTIVE_MODEL, BACKUP_DIR / f"ai_models_{now_tag}.joblib")
    if ACTIVE_METRICS.exists():
        shutil.copy2(ACTIVE_METRICS, BACKUP_DIR / f"metrics_{now_tag}.json")


def run_once(
    min_entry_auc: float,
    min_exit_auc: float,
    min_test_samples: int,
    min_entry_acc_when_auc_nan: float,
    min_exit_acc_when_auc_nan: float,
    force: bool = False,
    exit_only: bool = False,
) -> bool:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    entry_path, exit_path = build_datasets(DATA_TRADES, DATASETS_DIR)

    now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    staging_dir = MODELS_DIR / f"_staging_{now_tag}"
    if exit_only:
        result = train_exit_only(
            exit_csv=exit_path,
            base_model_path=ACTIVE_MODEL,
            out_dir=staging_dir,
            base_metrics_path=ACTIVE_METRICS,
        )
    else:
        result = train(entry_path, exit_path, staging_dir)
    metrics = result["metrics"]
    if exit_only:
        em = metrics.get("exit_metrics", {})
        x_auc = em.get("auc")
        x_n = int(em.get("samples", 0))
        x_acc = float(em.get("accuracy", 0.0) or 0.0)
        if x_n < min_test_samples:
            ok, reason = False, f"insufficient exit test samples={x_n}"
        else:
            x_auc_nan = (x_auc is None) or math.isnan(float(x_auc))
            if x_auc_nan and x_acc < float(min_exit_acc_when_auc_nan):
                ok, reason = False, f"exit auc nan and acc {x_acc:.3f} < {min_exit_acc_when_auc_nan:.3f}"
            elif (not x_auc_nan) and float(x_auc) < min_exit_auc:
                ok, reason = False, f"exit auc {float(x_auc):.3f} < {min_exit_auc:.3f}"
            else:
                ok, reason = True, "pass(exit_only)"
    else:
        ok, reason = _is_good_metrics(
            metrics,
            min_entry_auc,
            min_exit_auc,
            min_test_samples,
            min_entry_acc_when_auc_nan,
            min_exit_acc_when_auc_nan,
        )
    if force:
        ok = True
        reason = "force deploy"

    print(f"[gate] {reason}")
    if not ok:
        shutil.rmtree(staging_dir, ignore_errors=True)
        return False

    _backup_active(now_tag)
    shutil.copy2(result["model_path"], ACTIVE_MODEL)
    shutil.copy2(result["metrics_path"], ACTIVE_METRICS)

    deploy_state = {
        "deployed_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(staging_dir),
        "metrics": metrics,
        "gate": {
            "min_entry_auc": min_entry_auc,
            "min_exit_auc": min_exit_auc,
            "min_test_samples": min_test_samples,
            "min_entry_acc_when_auc_nan": min_entry_acc_when_auc_nan,
            "min_exit_acc_when_auc_nan": min_exit_acc_when_auc_nan,
            "force": force,
            "exit_only": bool(exit_only),
        },
    }
    (MODELS_DIR / "deploy_state.json").write_text(json.dumps(deploy_state, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(staging_dir, ignore_errors=True)
    print("[deploy] model promoted to models/ai_models.joblib")
    return True


def main():
    parser = argparse.ArgumentParser(description="Retrain and auto-deploy model with quality gate.")
    parser.add_argument("--min-entry-auc", type=float, default=0.35)
    parser.add_argument("--min-exit-auc", type=float, default=0.20)
    parser.add_argument("--min-test-samples", type=int, default=8)
    parser.add_argument("--min-entry-acc-when-auc-nan", type=float, default=0.55)
    parser.add_argument("--min-exit-acc-when-auc-nan", type=float, default=0.55)
    parser.add_argument("--interval-minutes", type=int, default=0, help="0 means run once")
    parser.add_argument("--force", action="store_true", help="Bypass gate and deploy newest model")
    parser.add_argument("--exit-only", action="store_true", help="Retrain/deploy exit model only, keep current entry model")
    args = parser.parse_args()

    if args.interval_minutes <= 0:
        run_once(
            args.min_entry_auc,
            args.min_exit_auc,
            args.min_test_samples,
            args.min_entry_acc_when_auc_nan,
            args.min_exit_acc_when_auc_nan,
            force=args.force,
            exit_only=args.exit_only,
        )
        return

    print(f"[scheduler] running every {args.interval_minutes} minutes")
    while True:
        try:
            run_once(
                args.min_entry_auc,
                args.min_exit_auc,
                args.min_test_samples,
                args.min_entry_acc_when_auc_nan,
                args.min_exit_acc_when_auc_nan,
                force=args.force,
                exit_only=args.exit_only,
            )
        except Exception as exc:
            print(f"[scheduler] cycle failed: {exc}")
        time.sleep(max(1, args.interval_minutes) * 60)


if __name__ == "__main__":
    main()
