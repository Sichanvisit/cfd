"""SA6 auto-decision / bounded-apply recommendation over shadow preview runs."""

from __future__ import annotations

from typing import Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_DECISION_ENGINE_VERSION = "shadow_auto_decision_engine_v0"
SHADOW_AUTO_DECISION_ENGINE_COLUMNS = [
    "decision_event_id",
    "generated_at",
    "correction_run_id",
    "preview_bundle_ready",
    "decision",
    "bounded_apply_state",
    "bounded_apply_reason",
    "value_diff",
    "manual_alignment_improvement",
    "available_row_count",
]


def build_shadow_auto_decision_engine(
    correction_loop: pd.DataFrame,
    *,
    preview_bundle_ready: bool,
) -> tuple[pd.DataFrame, dict[str, object]]:
    now = now_kst_dt().isoformat()
    if correction_loop is None or correction_loop.empty:
        frame = pd.DataFrame(
            [
                {
                    "decision_event_id": "shadow_decision::0001",
                    "generated_at": now,
                    "correction_run_id": "",
                    "preview_bundle_ready": bool(preview_bundle_ready),
                    "decision": "HOLD",
                    "bounded_apply_state": "preview_unavailable",
                    "bounded_apply_reason": "missing_correction_loop",
                    "value_diff": 0.0,
                    "manual_alignment_improvement": 0.0,
                    "available_row_count": 0,
                }
            ],
            columns=SHADOW_AUTO_DECISION_ENGINE_COLUMNS,
        )
    else:
        row = correction_loop.iloc[0]
        decision_in = str(row.get("decision", "") or "")
        available_row_count = int(row.get("available_row_count", 0) or 0)
        if not preview_bundle_ready:
            decision = "HOLD"
            bounded_state = "preview_bundle_missing"
            reason = "preview_bundle_not_ready"
        elif decision_in == "accept_preview_candidate" and available_row_count >= 8:
            decision = "APPLY_CANDIDATE"
            bounded_state = "shadow_preview_ready_for_human_approval"
            reason = "preview_shadow_improved_on_test_bucket"
        elif decision_in == "reject_preview_candidate":
            decision = "REJECT"
            bounded_state = "shadow_preview_rejected"
            reason = "preview_shadow_underperformed"
        elif decision_in == "hold_runtime_unavailable":
            decision = "HOLD"
            bounded_state = "shadow_runtime_demo_unavailable"
            reason = "preview_bundle_did_not_activate_in_demo"
        else:
            decision = "FREEZE" if "freeze" in decision_in else "HOLD"
            bounded_state = "needs_more_shadow_evidence"
            reason = decision_in or "mixed_shadow_result"
        frame = pd.DataFrame(
            [
                {
                    "decision_event_id": "shadow_decision::0001",
                    "generated_at": now,
                    "correction_run_id": str(row.get("shadow_correction_run_id", "") or ""),
                    "preview_bundle_ready": bool(preview_bundle_ready),
                    "decision": decision,
                    "bounded_apply_state": bounded_state,
                    "bounded_apply_reason": reason,
                    "value_diff": float(row.get("value_diff", 0.0) or 0.0),
                    "manual_alignment_improvement": float(row.get("manual_alignment_improvement", 0.0) or 0.0),
                    "available_row_count": available_row_count,
                }
            ],
            columns=SHADOW_AUTO_DECISION_ENGINE_COLUMNS,
        )
    summary = {
        "shadow_auto_decision_engine_version": SHADOW_AUTO_DECISION_ENGINE_VERSION,
        "generated_at": now,
        "decision_counts": frame["decision"].value_counts().to_dict() if not frame.empty else {},
    }
    return frame, summary


def render_shadow_auto_decision_engine_markdown(summary: Mapping[str, object], frame: pd.DataFrame) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Shadow Auto Decision",
        "",
        f"- version: `{summary.get('shadow_auto_decision_engine_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- decision: `{row.get('decision', '')}`",
        f"- bounded_apply_state: `{row.get('bounded_apply_state', '')}`",
        f"- bounded_apply_reason: `{row.get('bounded_apply_reason', '')}`",
        f"- value_diff: `{row.get('value_diff', 0.0)}`",
        f"- manual_alignment_improvement: `{row.get('manual_alignment_improvement', 0.0)}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
