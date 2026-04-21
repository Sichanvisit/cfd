"""SA5 shadow correction loop over offline preview execution evaluation."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_CORRECTION_LOOP_VERSION = "shadow_auto_correction_loop_v0"
SHADOW_AUTO_CORRECTION_LOOP_COLUMNS = [
    "shadow_correction_run_id",
    "started_at",
    "finished_at",
    "evaluation_scope",
    "row_count",
    "available_row_count",
    "baseline_value_sum",
    "shadow_value_sum",
    "value_diff",
    "baseline_drawdown",
    "shadow_drawdown",
    "manual_alignment_improvement",
    "decision",
    "decision_reason",
]


def build_shadow_auto_correction_loop(evaluation: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    now = now_kst_dt().isoformat()
    if evaluation is None or evaluation.empty:
        frame = pd.DataFrame(
            [
                {
                    "shadow_correction_run_id": "shadow_correction::0001",
                    "started_at": now,
                    "finished_at": now,
                    "evaluation_scope": "preview_bundle_test_bucket",
                    "row_count": 0,
                    "available_row_count": 0,
                    "baseline_value_sum": 0.0,
                    "shadow_value_sum": 0.0,
                    "value_diff": 0.0,
                    "baseline_drawdown": 0.0,
                    "shadow_drawdown": 0.0,
                    "manual_alignment_improvement": 0.0,
                    "decision": "hold_runtime_unavailable",
                    "decision_reason": "no_execution_evaluation_rows",
                }
            ],
            columns=SHADOW_AUTO_CORRECTION_LOOP_COLUMNS,
        )
    else:
        row = evaluation.iloc[0]
        value_diff = float(row.get("value_diff", 0.0) or 0.0)
        drawdown_diff = float(row.get("drawdown_diff", 0.0) or 0.0)
        alignment = float(row.get("manual_alignment_improvement", 0.0) or 0.0)
        available = int(row.get("available_row_count", 0) or 0)
        if available <= 0:
            decision = "hold_runtime_unavailable"
            reason = "preview_bundle_not_active_in_demo_rows"
        elif value_diff > 0.0 and drawdown_diff <= 0.0 and alignment > 0.0:
            decision = "accept_preview_candidate"
            reason = "shadow_improved_value_and_alignment_without_worse_drawdown"
        elif value_diff < 0.0 or drawdown_diff > 0.0:
            decision = "reject_preview_candidate"
            reason = "shadow_underperformed_or_worsened_drawdown"
        else:
            decision = "hold_for_more_shadow_data"
            reason = "mixed_shadow_outcome"
        frame = pd.DataFrame(
            [
                {
                    "shadow_correction_run_id": "shadow_correction::0001",
                    "started_at": now,
                    "finished_at": now,
                    "evaluation_scope": row.get("evaluation_scope", "preview_bundle_test_bucket"),
                    "row_count": int(row.get("row_count", 0) or 0),
                    "available_row_count": available,
                    "baseline_value_sum": float(row.get("baseline_value_sum", 0.0) or 0.0),
                    "shadow_value_sum": float(row.get("shadow_value_sum", 0.0) or 0.0),
                    "value_diff": value_diff,
                    "baseline_drawdown": float(row.get("baseline_drawdown", 0.0) or 0.0),
                    "shadow_drawdown": float(row.get("shadow_drawdown", 0.0) or 0.0),
                    "manual_alignment_improvement": alignment,
                    "decision": decision,
                    "decision_reason": reason,
                }
            ],
            columns=SHADOW_AUTO_CORRECTION_LOOP_COLUMNS,
        )
    summary = {
        "shadow_auto_correction_loop_version": SHADOW_AUTO_CORRECTION_LOOP_VERSION,
        "generated_at": now,
        "decision_counts": frame["decision"].value_counts().to_dict() if not frame.empty else {},
    }
    return frame, summary


def render_shadow_auto_correction_loop_markdown(summary: Mapping[str, Any], frame: pd.DataFrame) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Shadow Correction Loop",
        "",
        f"- version: `{summary.get('shadow_auto_correction_loop_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- decision: `{row.get('decision', '')}`",
        f"- decision_reason: `{row.get('decision_reason', '')}`",
        f"- value_diff: `{row.get('value_diff', 0.0)}`",
        f"- manual_alignment_improvement: `{row.get('manual_alignment_improvement', 0.0)}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
