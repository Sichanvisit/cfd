"""Evaluation/gate stage."""

from __future__ import annotations

from ml.pipelines.gate import evaluate_metrics_gate


def run(ctx: dict) -> dict:
    result = dict(ctx.get("train_result", {}) or {})
    metrics = dict(result.get("metrics", {}) or {})
    ok, reason = evaluate_metrics_gate(
        metrics=metrics,
        min_entry_auc=float(ctx.get("min_entry_auc", 0.35)),
        min_exit_auc=float(ctx.get("min_exit_auc", 0.20)),
        min_test_samples=int(ctx.get("min_test_samples", 8)),
        min_entry_acc_when_auc_nan=float(ctx.get("min_entry_acc_when_auc_nan", 0.55)),
        min_exit_acc_when_auc_nan=float(ctx.get("min_exit_acc_when_auc_nan", 0.55)),
    )
    if bool(ctx.get("force_deploy", False)):
        ok = True
        reason = "force deploy"
    ctx["gate_ok"] = bool(ok)
    ctx["gate_reason"] = str(reason)
    return ctx

