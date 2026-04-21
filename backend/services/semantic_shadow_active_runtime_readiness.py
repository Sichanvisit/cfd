"""Guarded readiness surface for promoting preview shadow runtime toward active use."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SEMANTIC_SHADOW_ACTIVE_RUNTIME_READINESS_VERSION = "semantic_shadow_active_runtime_readiness_v0"
SEMANTIC_SHADOW_ACTIVE_RUNTIME_READINESS_COLUMNS = [
    "readiness_event_id",
    "generated_at",
    "preview_bundle_ready",
    "preview_model_dir",
    "active_model_dir",
    "candidate_stage_dir",
    "bounded_gate_decision",
    "live_candidate_ready_flag",
    "active_runtime_state",
    "activation_ready_flag",
    "candidate_stage_created",
    "activation_block_reason",
    "recommended_next_action",
]


def load_semantic_shadow_active_runtime_readiness_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def build_semantic_shadow_active_runtime_readiness(
    preview_bundle_summary: Mapping[str, Any] | None,
    bounded_gate: pd.DataFrame | None,
    *,
    preview_model_dir: str | Path,
    active_model_dir: str | Path,
    candidate_stage_dir: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    now = now_kst_dt().isoformat()
    preview_summary = dict(preview_bundle_summary or {})
    bounded_row = bounded_gate.iloc[0].to_dict() if bounded_gate is not None and not bounded_gate.empty else {}
    preview_ready = bool(preview_summary.get("bundle_ready", False))
    gate_decision = str(bounded_row.get("gate_decision", "") or "")
    live_candidate_ready_flag = str(bounded_row.get("live_candidate_ready_flag", "")).lower() in {"true", "1", "yes"}
    preview_dir = Path(preview_model_dir)
    active_dir = Path(active_model_dir)
    stage_dir = Path(candidate_stage_dir)

    candidate_stage_created = False
    if not preview_ready:
        active_runtime_state = "preview_bundle_missing"
        activation_ready_flag = False
        activation_block_reason = "preview_bundle_not_ready"
        recommended_next_action = "rebuild_preview_bundle_before_runtime_stage"
    elif gate_decision != "ALLOW_BOUNDED_LIVE_CANDIDATE" or not live_candidate_ready_flag:
        active_runtime_state = "blocked_preview_only"
        activation_ready_flag = False
        activation_block_reason = gate_decision or "bounded_gate_not_ready"
        recommended_next_action = str(bounded_row.get("recommended_next_action", "") or "keep_preview_only")
    else:
        stage_dir.mkdir(parents=True, exist_ok=True)
        candidate_stage_created = True
        active_runtime_state = "candidate_stage_ready"
        activation_ready_flag = True
        activation_block_reason = ""
        recommended_next_action = "request_human_approval_for_candidate_runtime"

    frame = pd.DataFrame(
        [
            {
                "readiness_event_id": "semantic_shadow_runtime::0001",
                "generated_at": now,
                "preview_bundle_ready": preview_ready,
                "preview_model_dir": str(preview_dir),
                "active_model_dir": str(active_dir),
                "candidate_stage_dir": str(stage_dir),
                "bounded_gate_decision": gate_decision,
                "live_candidate_ready_flag": bool(live_candidate_ready_flag),
                "active_runtime_state": active_runtime_state,
                "activation_ready_flag": activation_ready_flag,
                "candidate_stage_created": candidate_stage_created,
                "activation_block_reason": activation_block_reason,
                "recommended_next_action": recommended_next_action,
            }
        ],
        columns=SEMANTIC_SHADOW_ACTIVE_RUNTIME_READINESS_COLUMNS,
    )
    summary = {
        "semantic_shadow_active_runtime_readiness_version": SEMANTIC_SHADOW_ACTIVE_RUNTIME_READINESS_VERSION,
        "generated_at": now,
        "active_runtime_state_counts": frame["active_runtime_state"].value_counts().to_dict() if not frame.empty else {},
        "activation_ready_count": int(frame["activation_ready_flag"].sum()) if not frame.empty else 0,
    }
    return frame, summary


def render_semantic_shadow_active_runtime_readiness_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Semantic Shadow Active Runtime Readiness",
        "",
        f"- version: `{summary.get('semantic_shadow_active_runtime_readiness_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- preview_bundle_ready: `{row.get('preview_bundle_ready', False)}`",
        f"- bounded_gate_decision: `{row.get('bounded_gate_decision', '')}`",
        f"- active_runtime_state: `{row.get('active_runtime_state', '')}`",
        f"- activation_ready_flag: `{row.get('activation_ready_flag', False)}`",
        f"- activation_block_reason: `{row.get('activation_block_reason', '')}`",
        f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
