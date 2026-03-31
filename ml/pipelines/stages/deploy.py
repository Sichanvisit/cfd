"""Deployment stage."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


def _backup_active(active_model: Path, active_metrics: Path, backup_dir: Path, tag: str) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    if active_model.exists():
        shutil.copy2(active_model, backup_dir / f"ai_models_{tag}.joblib")
    if active_metrics.exists():
        shutil.copy2(active_metrics, backup_dir / f"metrics_{tag}.json")


def run(ctx: dict) -> dict:
    if not bool(ctx.get("gate_ok", False)):
        ctx["deployed"] = False
        return ctx

    train_result = dict(ctx.get("train_result", {}) or {})
    model_path = Path(train_result["model_path"])
    metrics_path = Path(train_result["metrics_path"])
    metrics = dict(train_result.get("metrics", {}) or {})

    active_model = Path(ctx["active_model_path"])
    active_metrics = Path(ctx["active_metrics_path"])
    deploy_state_path = Path(ctx["deploy_state_path"])
    backup_dir = Path(ctx["backup_dir"])
    now_tag = str(ctx.get("run_tag", datetime.now().strftime("%Y%m%d_%H%M%S")))

    _backup_active(active_model, active_metrics, backup_dir, now_tag)
    active_model.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(model_path, active_model)
    shutil.copy2(metrics_path, active_metrics)

    deploy_state = {
        "deployed_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(Path(ctx["staging_models_dir"])),
        "gate_reason": str(ctx.get("gate_reason", "")),
        "metrics": metrics,
        "gate": {
            "min_entry_auc": float(ctx.get("min_entry_auc", 0.35)),
            "min_exit_auc": float(ctx.get("min_exit_auc", 0.20)),
            "min_test_samples": int(ctx.get("min_test_samples", 8)),
            "min_entry_acc_when_auc_nan": float(ctx.get("min_entry_acc_when_auc_nan", 0.55)),
            "min_exit_acc_when_auc_nan": float(ctx.get("min_exit_acc_when_auc_nan", 0.55)),
            "force": bool(ctx.get("force_deploy", False)),
            "exit_only": bool(ctx.get("exit_only", False)),
        },
    }
    deploy_state_path.write_text(json.dumps(deploy_state, ensure_ascii=False, indent=2), encoding="utf-8")
    ctx["deployed"] = True
    return ctx

