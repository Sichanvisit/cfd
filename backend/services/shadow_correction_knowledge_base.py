"""Durable shadow correction knowledge base artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_CORRECTION_KNOWLEDGE_BASE_VERSION = "shadow_correction_knowledge_base_v0"
SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS = [
    "knowledge_event_id",
    "generated_at",
    "knowledge_snapshot_key",
    "selected_sweep_profile_id",
    "preview_decision",
    "bounded_apply_state",
    "gate_decision",
    "approval_status",
    "activation_status",
    "rollout_mode",
    "shadow_runtime_state",
    "shadow_runtime_reason",
    "semantic_shadow_loaded",
    "value_diff",
    "manual_alignment_improvement",
    "drawdown_diff",
    "manual_reference_row_count",
    "manual_target_match_rate",
    "entry_threshold_applied_total",
    "entry_partial_live_total",
    "recent_fallback_reason_counts",
    "recent_activation_state_counts",
    "recent_threshold_would_apply_count",
    "recent_partial_live_would_apply_count",
    "rollout_promotion_readiness",
    "recommended_next_action",
    "rollback_note",
]


def load_shadow_correction_knowledge_base_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame(columns=SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS)
    try:
        frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        frame = pd.read_csv(csv_path, low_memory=False)
    missing = [col for col in SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS if col not in frame.columns]
    for col in missing:
        frame[col] = ""
    return frame[SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


def build_shadow_correction_knowledge_base(
    existing_frame: pd.DataFrame | None,
    first_non_hold: pd.DataFrame | None,
    bounded_gate: pd.DataFrame | None,
    approval_frame: pd.DataFrame | None,
    activation_frame: pd.DataFrame | None,
    rollout_observation: pd.DataFrame | None,
    manual_reference_audit: pd.DataFrame | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    now = now_kst_dt().isoformat()
    existing = existing_frame.copy() if existing_frame is not None and not existing_frame.empty else pd.DataFrame(
        columns=SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS
    )
    first_row = first_non_hold.iloc[0].to_dict() if first_non_hold is not None and not first_non_hold.empty else {}
    gate_row = bounded_gate.iloc[0].to_dict() if bounded_gate is not None and not bounded_gate.empty else {}
    approval_row = approval_frame.iloc[0].to_dict() if approval_frame is not None and not approval_frame.empty else {}
    activation_row = activation_frame.iloc[0].to_dict() if activation_frame is not None and not activation_frame.empty else {}
    observation_row = rollout_observation.iloc[0].to_dict() if rollout_observation is not None and not rollout_observation.empty else {}
    manual_row = manual_reference_audit.iloc[0].to_dict() if manual_reference_audit is not None and not manual_reference_audit.empty else {}

    selected_sweep_profile_id = _to_text(first_row.get("selected_sweep_profile_id", ""), "")
    preview_decision = _to_text(first_row.get("decision", ""), "")
    bounded_apply_state = _to_text(first_row.get("bounded_apply_state", ""), "")
    gate_decision = _to_text(gate_row.get("gate_decision", ""), "")
    approval_status = _to_text(approval_row.get("approval_status", ""), "")
    activation_status = _to_text(activation_row.get("activation_status", ""), "")
    rollout_mode = _to_text(observation_row.get("rollout_mode", ""), "")
    shadow_runtime_state = _to_text(observation_row.get("shadow_runtime_state", ""), "")
    shadow_runtime_reason = _to_text(observation_row.get("shadow_runtime_reason", ""), "")
    semantic_shadow_loaded = str(bool(observation_row.get("shadow_loaded", False))).lower()
    value_diff = round(_to_float(approval_row.get("value_diff", first_row.get("value_diff_proxy", 0.0))), 6)
    manual_alignment_improvement = round(
        _to_float(approval_row.get("manual_alignment_improvement", first_row.get("manual_alignment_improvement", 0.0))),
        6,
    )
    drawdown_diff = round(_to_float(approval_row.get("drawdown_diff", first_row.get("drawdown_diff", 0.0))), 6)
    manual_reference_row_count = _to_int(manual_row.get("manual_reference_row_count", gate_row.get("manual_reference_row_count", 0)))
    manual_target_match_rate = round(_to_float(manual_row.get("manual_target_match_rate", 0.0)), 6)
    entry_threshold_applied_total = _to_int(observation_row.get("entry_threshold_applied_total", 0))
    entry_partial_live_total = _to_int(observation_row.get("entry_partial_live_total", 0))
    recent_fallback_reason_counts = _to_text(observation_row.get("recent_fallback_reason_counts", ""), "{}")
    recent_activation_state_counts = _to_text(observation_row.get("recent_activation_state_counts", ""), "{}")
    recent_threshold_would_apply_count = _to_int(observation_row.get("recent_threshold_would_apply_count", 0))
    recent_partial_live_would_apply_count = _to_int(observation_row.get("recent_partial_live_would_apply_count", 0))
    rollout_promotion_readiness = _to_text(observation_row.get("rollout_promotion_readiness", ""), "")
    recommended_next_action = _to_text(observation_row.get("recommended_next_action", ""), "") or _to_text(
        activation_row.get("recommended_next_action", ""), ""
    ) or _to_text(gate_row.get("recommended_next_action", ""), "")

    snapshot_key = "|".join(
        [
            selected_sweep_profile_id,
            preview_decision,
            gate_decision,
            approval_status,
            activation_status,
            rollout_mode,
            shadow_runtime_state,
            str(entry_threshold_applied_total),
            str(entry_partial_live_total),
            str(recent_threshold_would_apply_count),
            str(recent_partial_live_would_apply_count),
            rollout_promotion_readiness,
        ]
    )

    if activation_status == "activated_candidate_runtime_forced":
        rollback_note = "forced_activation_demo_only_keep_semantic_live_rollout_bounded"
    elif gate_decision != "ALLOW_BOUNDED_LIVE_CANDIDATE":
        rollback_note = "do_not_promote_beyond_preview_gate"
    else:
        rollback_note = "bounded_candidate_ready_monitor_runtime_before_live_escalation"

    new_row = {
        "knowledge_event_id": f"shadow_correction_knowledge::{len(existing) + 1:04d}",
        "generated_at": now,
        "knowledge_snapshot_key": snapshot_key,
        "selected_sweep_profile_id": selected_sweep_profile_id,
        "preview_decision": preview_decision,
        "bounded_apply_state": bounded_apply_state,
        "gate_decision": gate_decision,
        "approval_status": approval_status,
        "activation_status": activation_status,
        "rollout_mode": rollout_mode,
        "shadow_runtime_state": shadow_runtime_state,
        "shadow_runtime_reason": shadow_runtime_reason,
        "semantic_shadow_loaded": semantic_shadow_loaded,
        "value_diff": value_diff,
        "manual_alignment_improvement": manual_alignment_improvement,
        "drawdown_diff": drawdown_diff,
        "manual_reference_row_count": manual_reference_row_count,
        "manual_target_match_rate": manual_target_match_rate,
        "entry_threshold_applied_total": entry_threshold_applied_total,
        "entry_partial_live_total": entry_partial_live_total,
        "recent_fallback_reason_counts": recent_fallback_reason_counts,
        "recent_activation_state_counts": recent_activation_state_counts,
        "recent_threshold_would_apply_count": recent_threshold_would_apply_count,
        "recent_partial_live_would_apply_count": recent_partial_live_would_apply_count,
        "rollout_promotion_readiness": rollout_promotion_readiness,
        "recommended_next_action": recommended_next_action,
        "rollback_note": rollback_note,
    }

    if existing.empty or "knowledge_snapshot_key" not in existing.columns:
        combined = pd.DataFrame([new_row], columns=SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS)
    else:
        if snapshot_key in existing["knowledge_snapshot_key"].fillna("").astype(str).tolist():
            existing = existing.copy().astype(object)
            existing.loc[
                existing["knowledge_snapshot_key"].fillna("").astype(str) == snapshot_key,
                SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS,
            ] = pd.DataFrame([new_row], columns=SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS).iloc[0].values
            combined = existing[SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS]
        else:
            combined = pd.concat(
                [existing[SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS], pd.DataFrame([new_row])],
                ignore_index=True,
            )

    summary = {
        "shadow_correction_knowledge_base_version": SHADOW_CORRECTION_KNOWLEDGE_BASE_VERSION,
        "generated_at": now,
        "row_count": int(len(combined)),
        "latest_snapshot_key": snapshot_key,
    }
    return combined[SHADOW_CORRECTION_KNOWLEDGE_BASE_COLUMNS], summary


def render_shadow_correction_knowledge_base_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    row = frame.iloc[-1].to_dict() if frame is not None and not frame.empty else {}
    lines = [
        "# Shadow Correction Knowledge Base",
        "",
        f"- version: `{summary.get('shadow_correction_knowledge_base_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- selected_sweep_profile_id: `{row.get('selected_sweep_profile_id', '')}`",
        f"- preview_decision: `{row.get('preview_decision', '')}`",
        f"- gate_decision: `{row.get('gate_decision', '')}`",
        f"- approval_status: `{row.get('approval_status', '')}`",
        f"- activation_status: `{row.get('activation_status', '')}`",
        f"- rollout_mode: `{row.get('rollout_mode', '')}`",
        f"- shadow_runtime: `{row.get('shadow_runtime_state', '')}` / `{row.get('shadow_runtime_reason', '')}`",
        f"- semantic_shadow_loaded: `{row.get('semantic_shadow_loaded', '')}`",
        f"- value_diff: `{row.get('value_diff', 0.0)}`",
        f"- manual_alignment_improvement: `{row.get('manual_alignment_improvement', 0.0)}`",
        f"- entry_threshold_applied_total: `{row.get('entry_threshold_applied_total', 0)}`",
        f"- entry_partial_live_total: `{row.get('entry_partial_live_total', 0)}`",
        f"- recent_fallback_reason_counts: `{row.get('recent_fallback_reason_counts', '{}')}`",
        f"- recent_activation_state_counts: `{row.get('recent_activation_state_counts', '{}')}`",
        f"- recent_threshold_would_apply_count: `{row.get('recent_threshold_would_apply_count', 0)}`",
        f"- recent_partial_live_would_apply_count: `{row.get('recent_partial_live_would_apply_count', 0)}`",
        f"- rollout_promotion_readiness: `{row.get('rollout_promotion_readiness', '')}`",
        f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
        f"- rollback_note: `{row.get('rollback_note', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
