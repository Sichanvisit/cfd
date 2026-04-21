"""SA6a first non-HOLD decision surface over the divergence run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_FIRST_NON_HOLD_VERSION = "shadow_auto_first_non_hold_v1"
SHADOW_AUTO_FIRST_NON_HOLD_COLUMNS = [
    "decision_event_id",
    "generated_at",
    "selected_sweep_profile_id",
    "run_decision",
    "decision",
    "decision_reason",
    "bounded_apply_state",
    "divergence_rate",
    "manual_reference_row_count",
    "manual_alignment_improvement",
    "proxy_alignment_improvement",
    "mapped_alignment_improvement",
    "drawdown_diff",
    "new_false_positive_count",
    "value_diff_proxy",
]


def load_shadow_auto_first_non_hold_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def build_shadow_auto_first_non_hold_decision(
    divergence_summary: dict[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    summary_in = dict(divergence_summary or {})
    now = now_kst_dt().isoformat()
    run_decision = str(summary_in.get("run_decision", "") or "")
    divergence_rate = float(summary_in.get("divergence_rate", 0.0) or 0.0)
    value_diff_proxy = float(summary_in.get("value_diff_proxy", 0.0) or 0.0)
    mapped_alignment_improvement = float(summary_in.get("mapped_alignment_improvement", 0.0) or 0.0)
    proxy_alignment_improvement = float(summary_in.get("proxy_alignment_improvement", 0.0) or 0.0)
    manual_reference_row_count = int(summary_in.get("manual_reference_row_count", 0) or 0)
    manual_alignment_improvement = float(summary_in.get("manual_alignment_improvement", 0.0) or 0.0)
    drawdown_diff = float(summary_in.get("drawdown_diff", 0.0) or 0.0)
    new_false_positive_count = int(summary_in.get("new_false_positive_count", 0) or 0)

    if run_decision == "apply_candidate_preview" and divergence_rate > 0.0:
        decision = "APPLY_CANDIDATE"
        bounded_apply_state = "preview_divergence_candidate"
        decision_reason = "bounded_divergence_found_without_value_drawdown_regression"
    elif run_decision == "reject_preview_candidate":
        decision = "REJECT"
        bounded_apply_state = "preview_divergence_rejected"
        if new_false_positive_count > 0:
            decision_reason = "divergence_present_but_false_positive_pressure_too_high"
        elif manual_reference_row_count > 0 and manual_alignment_improvement < 0.0:
            decision_reason = "divergence_present_but_manual_truth_alignment_regressed"
        elif mapped_alignment_improvement < 0.0:
            decision_reason = "divergence_present_but_mapped_target_alignment_regressed"
        elif value_diff_proxy < 0.0 or drawdown_diff > 0.0:
            decision_reason = "divergence_present_but_value_or_drawdown_deteriorated"
        else:
            decision_reason = "divergence_present_but_alignment_or_value_conflict"
    else:
        decision = "HOLD"
        bounded_apply_state = "needs_more_shadow_evidence"
        decision_reason = run_decision or "missing_divergence_run"

    frame = pd.DataFrame(
        [
            {
                "decision_event_id": "shadow_non_hold::0001",
                "generated_at": now,
                "selected_sweep_profile_id": str(summary_in.get("selected_sweep_profile_id", "") or ""),
                "run_decision": run_decision,
                "decision": decision,
                "decision_reason": decision_reason,
                "bounded_apply_state": bounded_apply_state,
                "divergence_rate": round(divergence_rate, 6),
                "manual_reference_row_count": manual_reference_row_count,
                "manual_alignment_improvement": round(manual_alignment_improvement, 6),
                "proxy_alignment_improvement": round(proxy_alignment_improvement, 6),
                "mapped_alignment_improvement": round(mapped_alignment_improvement, 6),
                "drawdown_diff": round(drawdown_diff, 6),
                "new_false_positive_count": new_false_positive_count,
                "value_diff_proxy": round(value_diff_proxy, 6),
            }
        ],
        columns=SHADOW_AUTO_FIRST_NON_HOLD_COLUMNS,
    )
    summary = {
        "shadow_auto_first_non_hold_version": SHADOW_AUTO_FIRST_NON_HOLD_VERSION,
        "generated_at": now,
        "decision_counts": frame["decision"].value_counts().to_dict() if not frame.empty else {},
        "bounded_apply_state_counts": frame["bounded_apply_state"].value_counts().to_dict() if not frame.empty else {},
    }
    return frame, summary


def render_shadow_auto_first_non_hold_markdown(summary: dict[str, Any], frame: pd.DataFrame) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Shadow First Non-HOLD Decision",
        "",
        f"- version: `{summary.get('shadow_auto_first_non_hold_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- decision: `{row.get('decision', '')}`",
        f"- decision_reason: `{row.get('decision_reason', '')}`",
        f"- bounded_apply_state: `{row.get('bounded_apply_state', '')}`",
        f"- divergence_rate: `{row.get('divergence_rate', 0.0)}`",
        f"- manual_reference_row_count: `{row.get('manual_reference_row_count', 0)}`",
        f"- manual_alignment_improvement: `{row.get('manual_alignment_improvement', 0.0)}`",
        f"- mapped_alignment_improvement: `{row.get('mapped_alignment_improvement', 0.0)}`",
        f"- drawdown_diff: `{row.get('drawdown_diff', 0.0)}`",
        f"- new_false_positive_count: `{row.get('new_false_positive_count', 0)}`",
        f"- value_diff_proxy: `{row.get('value_diff_proxy', 0.0)}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
