"""Bounded live-apply gate over preview shadow candidates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_BOUNDED_APPLY_GATE_VERSION = "shadow_auto_bounded_apply_gate_v0"
SHADOW_AUTO_BOUNDED_APPLY_GATE_COLUMNS = [
    "gate_event_id",
    "generated_at",
    "selected_sweep_profile_id",
    "preview_decision",
    "preview_bounded_apply_state",
    "manual_reference_row_count",
    "required_manual_reference_row_count",
    "manual_target_match_rate",
    "value_diff_proxy",
    "required_value_diff_proxy",
    "drawdown_diff",
    "new_false_positive_count",
    "gate_decision",
    "gate_reason",
    "live_candidate_ready_flag",
    "recommended_next_action",
]


def load_shadow_auto_bounded_apply_gate_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def build_shadow_auto_bounded_apply_gate(
    first_non_hold: pd.DataFrame | None,
    manual_reference_audit: pd.DataFrame | None,
    *,
    required_manual_reference_row_count: int = 5,
    required_value_diff_proxy: float = 0.01,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    now = now_kst_dt().isoformat()
    decision_row = first_non_hold.iloc[0].to_dict() if first_non_hold is not None and not first_non_hold.empty else {}
    overall_audit = manual_reference_audit.iloc[0].to_dict() if manual_reference_audit is not None and not manual_reference_audit.empty else {}
    preview_decision = str(decision_row.get("decision", "") or "")
    preview_state = str(decision_row.get("bounded_apply_state", "") or "")
    manual_reference_row_count = int(overall_audit.get("manual_reference_row_count", 0) or 0)
    manual_target_match_rate = float(overall_audit.get("manual_target_match_rate", 0.0) or 0.0)
    value_diff_proxy = float(decision_row.get("value_diff_proxy", 0.0) or 0.0)
    drawdown_diff = float(decision_row.get("drawdown_diff", 0.0) or 0.0)
    new_false_positive_count = int(decision_row.get("new_false_positive_count", 0) or 0)

    if preview_decision != "APPLY_CANDIDATE":
        gate_decision = "BLOCK_PREVIEW_DECISION"
        gate_reason = "preview_candidate_not_ready_for_live_gate"
        live_candidate_ready_flag = False
        recommended_next_action = "improve_preview_candidate_before_live_gate"
    elif manual_reference_row_count < int(required_manual_reference_row_count):
        gate_decision = "REQUIRE_MORE_MANUAL_TRUTH"
        gate_reason = "manual_truth_overlap_below_bounded_gate_floor"
        live_candidate_ready_flag = False
        recommended_next_action = "expand_manual_truth_shadow_overlap"
    elif manual_target_match_rate < 0.5:
        gate_decision = "REVIEW_MANUAL_ALIGNMENT"
        gate_reason = "manual_truth_overlap_exists_but_alignment_is_not_stable"
        live_candidate_ready_flag = False
        recommended_next_action = "recheck_shadow_target_mapping_with_manual_truth"
    elif value_diff_proxy < float(required_value_diff_proxy):
        gate_decision = "REQUIRE_POSITIVE_VALUE_EDGE"
        gate_reason = "preview_candidate_has_not_shown_positive_value_edge"
        live_candidate_ready_flag = False
        recommended_next_action = "run_narrow_threshold_sweep_for_positive_value_edge"
    elif drawdown_diff > 0.0:
        gate_decision = "REJECT_DRAWDOWN_REGRESSION"
        gate_reason = "preview_candidate_worsens_drawdown"
        live_candidate_ready_flag = False
        recommended_next_action = "reduce_drawdown_before_bounded_live_candidate"
    elif new_false_positive_count > 0:
        gate_decision = "REVIEW_FALSE_POSITIVES"
        gate_reason = "preview_candidate_still_creates_new_false_positives"
        live_candidate_ready_flag = False
        recommended_next_action = "eliminate_false_positive_pressure_before_live_gate"
    else:
        gate_decision = "ALLOW_BOUNDED_LIVE_CANDIDATE"
        gate_reason = "preview_candidate_clears_manual_truth_and_value_edge_floor"
        live_candidate_ready_flag = True
        recommended_next_action = "stage_candidate_runtime_for_human_approval"

    frame = pd.DataFrame(
        [
            {
                "gate_event_id": "bounded_apply_gate::0001",
                "generated_at": now,
                "selected_sweep_profile_id": str(decision_row.get("selected_sweep_profile_id", "") or ""),
                "preview_decision": preview_decision,
                "preview_bounded_apply_state": preview_state,
                "manual_reference_row_count": manual_reference_row_count,
                "required_manual_reference_row_count": int(required_manual_reference_row_count),
                "manual_target_match_rate": round(manual_target_match_rate, 6),
                "value_diff_proxy": round(value_diff_proxy, 6),
                "required_value_diff_proxy": float(required_value_diff_proxy),
                "drawdown_diff": round(drawdown_diff, 6),
                "new_false_positive_count": new_false_positive_count,
                "gate_decision": gate_decision,
                "gate_reason": gate_reason,
                "live_candidate_ready_flag": live_candidate_ready_flag,
                "recommended_next_action": recommended_next_action,
            }
        ],
        columns=SHADOW_AUTO_BOUNDED_APPLY_GATE_COLUMNS,
    )
    summary = {
        "shadow_auto_bounded_apply_gate_version": SHADOW_AUTO_BOUNDED_APPLY_GATE_VERSION,
        "generated_at": now,
        "gate_decision_counts": frame["gate_decision"].value_counts().to_dict() if not frame.empty else {},
        "live_candidate_ready_count": int(frame["live_candidate_ready_flag"].sum()) if not frame.empty else 0,
    }
    return frame, summary


def render_shadow_auto_bounded_apply_gate_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Shadow Bounded Apply Gate",
        "",
        f"- version: `{summary.get('shadow_auto_bounded_apply_gate_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- preview_decision: `{row.get('preview_decision', '')}`",
        f"- gate_decision: `{row.get('gate_decision', '')}`",
        f"- gate_reason: `{row.get('gate_reason', '')}`",
        f"- manual_reference_row_count: `{row.get('manual_reference_row_count', 0)}` / `{row.get('required_manual_reference_row_count', 0)}`",
        f"- value_diff_proxy: `{row.get('value_diff_proxy', 0.0)}` / `{row.get('required_value_diff_proxy', 0.0)}`",
        f"- drawdown_diff: `{row.get('drawdown_diff', 0.0)}`",
        f"- live_candidate_ready_flag: `{row.get('live_candidate_ready_flag', False)}`",
        f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
