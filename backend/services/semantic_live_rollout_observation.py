"""Bounded semantic live rollout observation summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt
from ml.semantic_v1.promotion_guard import SemanticPromotionGuard


SEMANTIC_LIVE_ROLLOUT_OBSERVATION_VERSION = "semantic_live_rollout_observation_v0"
SEMANTIC_LIVE_ROLLOUT_OBSERVATION_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "rollout_mode",
    "shadow_loaded",
    "shadow_runtime_state",
    "shadow_runtime_reason",
    "entry_events_total",
    "entry_alerts_total",
    "entry_threshold_applied_total",
    "entry_fallback_total",
    "entry_partial_live_total",
    "recent_row_count",
    "recent_log_only_count",
    "recent_disabled_count",
    "recent_threshold_applied_count",
    "recent_partial_live_count",
    "recent_shadow_available_count",
    "recent_symbols",
    "recent_trace_quality_states",
    "recent_fallback_reasons",
    "recent_fallback_reason_counts",
    "recent_activation_state_counts",
    "recent_threshold_would_apply_count",
    "recent_partial_live_would_apply_count",
    "recent_threshold_eligible_count",
    "recent_partial_live_eligible_count",
    "recent_threshold_would_apply_symbols",
    "recent_partial_live_would_apply_symbols",
    "rollout_promotion_readiness",
    "recommended_next_action",
]


def load_semantic_live_rollout_observation_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


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


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _stable_join(values: pd.Series) -> str:
    seen: list[str] = []
    for raw in values.fillna("").astype(str):
        text = raw.strip()
        if not text or text in seen:
            continue
        seen.append(text)
    return ",".join(seen)


def _series_json_counts(values: pd.Series) -> str:
    counts = (
        values.fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .to_dict()
    )
    return json.dumps(counts, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _to_bool(value: object) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _build_counterfactual_rollout(row: Mapping[str, Any], *, mode: str) -> dict[str, Any]:
    prediction = {
        "available": _to_bool(row.get("semantic_shadow_available", 0)),
        "should_enter": _to_bool(row.get("semantic_shadow_should_enter", 0)),
        "timing": {
            "probability": _to_float(row.get("semantic_shadow_timing_probability", 0.0)),
            "threshold": _to_float(row.get("semantic_shadow_timing_threshold", 0.55), 0.55),
        },
        "entry_quality": {
            "probability": _to_float(
                row.get("semantic_shadow_entry_quality_probability", row.get("semantic_shadow_timing_probability", 0.0)),
                0.0,
            ),
            "threshold": _to_float(row.get("semantic_shadow_entry_quality_threshold", 0.55), 0.55),
        },
        "trace_quality_state": _to_text(
            row.get("semantic_shadow_trace_quality", row.get("trace_quality_state", "")),
            "unknown",
        ),
    }
    runtime_snapshot_row = {
        "missing_feature_count": _to_int(row.get("missing_feature_count", 0)),
        "compatibility_mode": _to_text(
            row.get("compatibility_mode", row.get("semantic_compatibility_mode", "observe_confirm_v1_fallback")),
            "observe_confirm_v1_fallback",
        ),
    }
    return SemanticPromotionGuard.evaluate_entry_rollout(
        symbol=_to_text(row.get("symbol", ""), ""),
        baseline_action=_to_text(row.get("action", ""), ""),
        entry_stage=_to_text(row.get("entry_stage", ""), ""),
        current_threshold=_to_int(row.get("semantic_live_threshold_before", row.get("entry_threshold", 45)), 45),
        semantic_prediction=prediction,
        runtime_snapshot_row=runtime_snapshot_row,
        mode_override=mode,
    )


def build_semantic_live_rollout_observation(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    recent_limit: int = 200,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    now = now_kst_dt().isoformat()
    payload = dict(runtime_status or {})
    semantic_live_config = dict(payload.get("semantic_live_config", {}) or {})
    semantic_rollout_state = dict(payload.get("semantic_rollout_state", {}) or {})
    entry_bucket = dict(semantic_rollout_state.get("entry", {}) or {})

    entry_frame = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()
    if not entry_frame.empty and "time" in entry_frame.columns:
        entry_frame["time_sort"] = pd.to_datetime(entry_frame["time"], errors="coerce")
        entry_frame = entry_frame.sort_values(by=["time_sort"], ascending=[False], kind="stable").drop(
            columns=["time_sort"]
        )
    if not entry_frame.empty:
        entry_frame = entry_frame.head(max(1, int(recent_limit))).copy()

    rollout_mode = _to_text(semantic_live_config.get("mode", ""), "disabled")
    shadow_loaded = bool(payload.get("semantic_shadow_loaded", False))
    shadow_runtime_state = _to_text(semantic_live_config.get("shadow_runtime_state", ""), "")
    shadow_runtime_reason = _to_text(semantic_live_config.get("shadow_runtime_reason", ""), "")
    entry_events_total = _to_int(entry_bucket.get("events_total", 0))
    entry_alerts_total = _to_int(entry_bucket.get("alerts_total", 0))
    entry_threshold_applied_total = _to_int(entry_bucket.get("threshold_applied_total", 0))
    entry_fallback_total = _to_int(entry_bucket.get("fallback_total", 0))
    entry_partial_live_total = _to_int(entry_bucket.get("partial_live_total", 0))

    recent_row_count = int(len(entry_frame))
    recent_log_only_count = 0
    recent_disabled_count = 0
    recent_threshold_applied_count = 0
    recent_partial_live_count = 0
    recent_shadow_available_count = 0
    recent_symbols = ""
    recent_trace_quality_states = ""
    recent_fallback_reasons = ""
    recent_fallback_reason_counts = "{}"
    recent_activation_state_counts = "{}"
    recent_threshold_would_apply_count = 0
    recent_partial_live_would_apply_count = 0
    recent_threshold_eligible_count = 0
    recent_partial_live_eligible_count = 0
    recent_threshold_would_apply_symbols = ""
    recent_partial_live_would_apply_symbols = ""

    if not entry_frame.empty:
        if "semantic_live_rollout_mode" in entry_frame.columns:
            rollout_modes = entry_frame["semantic_live_rollout_mode"].fillna("").astype(str).str.strip().str.lower()
            recent_log_only_count = int((rollout_modes == "log_only").sum())
            recent_disabled_count = int((rollout_modes == "disabled").sum())
        if "semantic_live_threshold_applied" in entry_frame.columns:
            recent_threshold_applied_count = int(
                entry_frame["semantic_live_threshold_applied"].fillna(0).astype(float).gt(0).sum()
            )
        if "semantic_live_partial_live_applied" in entry_frame.columns:
            recent_partial_live_count = int(
                entry_frame["semantic_live_partial_live_applied"].fillna(0).astype(float).gt(0).sum()
            )
        if "semantic_shadow_available" in entry_frame.columns:
            recent_shadow_available_count = int(
                entry_frame["semantic_shadow_available"].fillna(0).astype(float).gt(0).sum()
            )
        if "symbol" in entry_frame.columns:
            recent_symbols = _stable_join(entry_frame["symbol"])
        if "trace_quality_state" in entry_frame.columns:
            recent_trace_quality_states = _stable_join(entry_frame["trace_quality_state"])
        if "semantic_live_fallback_reason" in entry_frame.columns:
            recent_fallback_reasons = _stable_join(entry_frame["semantic_live_fallback_reason"])
            recent_fallback_reason_counts = _series_json_counts(entry_frame["semantic_live_fallback_reason"])
        if "semantic_shadow_activation_state" in entry_frame.columns:
            recent_activation_state_counts = _series_json_counts(entry_frame["semantic_shadow_activation_state"])

        threshold_symbols: list[str] = []
        partial_symbols: list[str] = []
        for row in entry_frame.to_dict(orient="records"):
            threshold_eval = _build_counterfactual_rollout(row, mode="threshold_only")
            partial_eval = _build_counterfactual_rollout(row, mode="partial_live")
            if not _to_text(threshold_eval.get("fallback_reason", ""), ""):
                recent_threshold_eligible_count += 1
            if not _to_text(partial_eval.get("fallback_reason", ""), ""):
                recent_partial_live_eligible_count += 1
            if bool(threshold_eval.get("threshold_applied", False)):
                recent_threshold_would_apply_count += 1
                threshold_symbols.append(_to_text(row.get("symbol", ""), ""))
            if bool(partial_eval.get("partial_live_applied", False)):
                recent_partial_live_would_apply_count += 1
                partial_symbols.append(_to_text(row.get("symbol", ""), ""))
        if threshold_symbols:
            recent_threshold_would_apply_symbols = ",".join(sorted({s for s in threshold_symbols if s}))
        if partial_symbols:
            recent_partial_live_would_apply_symbols = ",".join(sorted({s for s in partial_symbols if s}))

    rollout_promotion_readiness = "stay_disabled"
    if rollout_mode == "disabled":
        rollout_promotion_readiness = "candidate_log_only"
        recommended_next_action = "enable_log_only_rollout_and_restart_core"
    elif not shadow_loaded or shadow_runtime_state != "active":
        rollout_promotion_readiness = "shadow_runtime_unavailable"
        recommended_next_action = "restore_shadow_runtime_before_rollout_observation"
    elif recent_threshold_would_apply_count > 0 and recent_partial_live_would_apply_count > 0:
        rollout_promotion_readiness = "candidate_partial_live"
        recommended_next_action = "review_partial_live_candidate_from_log_only_counterfactuals"
    elif recent_threshold_would_apply_count > 0:
        rollout_promotion_readiness = "candidate_threshold_only"
        recommended_next_action = "review_threshold_only_candidate_from_log_only_counterfactuals"
    elif recent_row_count > 0 and recent_threshold_eligible_count <= 0 and recent_partial_live_eligible_count <= 0:
        rollout_promotion_readiness = "blocked_no_eligible_rows"
        recommended_next_action = "retain_log_only_and_improve_baseline_action_or_semantic_quality"
    elif entry_threshold_applied_total <= 0 and recent_row_count > 0:
        rollout_promotion_readiness = "observe_more_log_only"
        recommended_next_action = "continue_log_only_observation_until_counterfactual_threshold_cases_appear"
    elif entry_partial_live_total > 0:
        rollout_promotion_readiness = "partial_live_under_review"
        recommended_next_action = "review_partial_live_behavior_before_mode_change"
    else:
        rollout_promotion_readiness = "bounded_log_only_stable"
        recommended_next_action = "continue_bounded_log_only_rollout_observation"

    frame = pd.DataFrame(
        [
            {
                "observation_event_id": "semantic_live_rollout_observation::0001",
                "generated_at": now,
                "runtime_updated_at": _to_text(payload.get("updated_at", ""), ""),
                "rollout_mode": rollout_mode,
                "shadow_loaded": shadow_loaded,
                "shadow_runtime_state": shadow_runtime_state,
                "shadow_runtime_reason": shadow_runtime_reason,
                "entry_events_total": entry_events_total,
                "entry_alerts_total": entry_alerts_total,
                "entry_threshold_applied_total": entry_threshold_applied_total,
                "entry_fallback_total": entry_fallback_total,
                "entry_partial_live_total": entry_partial_live_total,
                "recent_row_count": recent_row_count,
                "recent_log_only_count": recent_log_only_count,
                "recent_disabled_count": recent_disabled_count,
                "recent_threshold_applied_count": recent_threshold_applied_count,
                "recent_partial_live_count": recent_partial_live_count,
                "recent_shadow_available_count": recent_shadow_available_count,
                "recent_symbols": recent_symbols,
                "recent_trace_quality_states": recent_trace_quality_states,
                "recent_fallback_reasons": recent_fallback_reasons,
                "recent_fallback_reason_counts": recent_fallback_reason_counts,
                "recent_activation_state_counts": recent_activation_state_counts,
                "recent_threshold_would_apply_count": recent_threshold_would_apply_count,
                "recent_partial_live_would_apply_count": recent_partial_live_would_apply_count,
                "recent_threshold_eligible_count": recent_threshold_eligible_count,
                "recent_partial_live_eligible_count": recent_partial_live_eligible_count,
                "recent_threshold_would_apply_symbols": recent_threshold_would_apply_symbols,
                "recent_partial_live_would_apply_symbols": recent_partial_live_would_apply_symbols,
                "rollout_promotion_readiness": rollout_promotion_readiness,
                "recommended_next_action": recommended_next_action,
            }
        ],
        columns=SEMANTIC_LIVE_ROLLOUT_OBSERVATION_COLUMNS,
    )
    summary = {
        "semantic_live_rollout_observation_version": SEMANTIC_LIVE_ROLLOUT_OBSERVATION_VERSION,
        "generated_at": now,
        "rollout_mode_counts": frame["rollout_mode"].value_counts().to_dict() if not frame.empty else {},
        "shadow_loaded_count": int(frame["shadow_loaded"].sum()) if not frame.empty else 0,
    }
    return frame, summary


def render_semantic_live_rollout_observation_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Semantic Live Rollout Observation",
        "",
        f"- version: `{summary.get('semantic_live_rollout_observation_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- rollout_mode: `{row.get('rollout_mode', '')}`",
        f"- shadow_loaded: `{row.get('shadow_loaded', False)}`",
        f"- shadow_runtime: `{row.get('shadow_runtime_state', '')}` / `{row.get('shadow_runtime_reason', '')}`",
        f"- entry_events_total: `{row.get('entry_events_total', 0)}`",
        f"- entry_threshold_applied_total: `{row.get('entry_threshold_applied_total', 0)}`",
        f"- entry_partial_live_total: `{row.get('entry_partial_live_total', 0)}`",
        f"- recent_row_count: `{row.get('recent_row_count', 0)}`",
        f"- recent_log_only_count: `{row.get('recent_log_only_count', 0)}`",
        f"- recent_threshold_applied_count: `{row.get('recent_threshold_applied_count', 0)}`",
        f"- recent_partial_live_count: `{row.get('recent_partial_live_count', 0)}`",
        f"- recent_shadow_available_count: `{row.get('recent_shadow_available_count', 0)}`",
        f"- recent_symbols: `{row.get('recent_symbols', '')}`",
        f"- recent_trace_quality_states: `{row.get('recent_trace_quality_states', '')}`",
        f"- recent_fallback_reasons: `{row.get('recent_fallback_reasons', '')}`",
        f"- recent_fallback_reason_counts: `{row.get('recent_fallback_reason_counts', '{}')}`",
        f"- recent_activation_state_counts: `{row.get('recent_activation_state_counts', '{}')}`",
        f"- recent_threshold_would_apply_count: `{row.get('recent_threshold_would_apply_count', 0)}`",
        f"- recent_partial_live_would_apply_count: `{row.get('recent_partial_live_would_apply_count', 0)}`",
        f"- recent_threshold_eligible_count: `{row.get('recent_threshold_eligible_count', 0)}`",
        f"- recent_partial_live_eligible_count: `{row.get('recent_partial_live_eligible_count', 0)}`",
        f"- recent_threshold_would_apply_symbols: `{row.get('recent_threshold_would_apply_symbols', '')}`",
        f"- recent_partial_live_would_apply_symbols: `{row.get('recent_partial_live_would_apply_symbols', '')}`",
        f"- rollout_promotion_readiness: `{row.get('rollout_promotion_readiness', '')}`",
        f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
