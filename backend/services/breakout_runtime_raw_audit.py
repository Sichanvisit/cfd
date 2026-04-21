"""Raw breakout runtime/overlay audit for fresh AI2 baseline-no-action rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.breakout_event_overlay import build_breakout_event_overlay_candidates_v1
from backend.services.breakout_event_runtime import (
    _response_breakout_axis_trace,
    _response_breakout_scores,
    build_breakout_event_runtime_v1,
)
from backend.services.trade_csv_schema import now_kst_dt


BREAKOUT_RUNTIME_RAW_AUDIT_CONTRACT_VERSION = "breakout_runtime_raw_audit_v1"
BREAKOUT_RUNTIME_RAW_AUDIT_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "rollout_mode",
    "time",
    "symbol",
    "detail_row_key",
    "micro_breakout_readiness_state",
    "effective_breakout_readiness_state",
    "breakout_readiness_origin",
    "breakout_up_score",
    "breakout_down_score",
    "breakout_axis_mode",
    "breakout_axis_bridge_applied",
    "breakout_up_source",
    "breakout_down_source",
    "breakout_type_candidate",
    "selected_axis_family",
    "breakout_direction_gap",
    "breakout_direction_gap_normalized",
    "why_none_reason",
    "confirm_side",
    "confirm_score",
    "false_break_score",
    "continuation_score",
    "barrier_total",
    "breakout_direction",
    "breakout_state",
    "breakout_detected",
    "breakout_confidence",
    "breakout_failure_risk",
    "overlay_target",
    "conflict_level",
    "action_demotion_rule",
    "overlay_reason_summary",
    "raw_blocker_family",
]


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
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


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
    normalized = {str(key): int(value) for key, value in counts.items()}
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True) if normalized else "{}"


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _load_matching_detail_payloads(
    detail_path: str | Path,
    row_keys: set[str],
) -> dict[str, dict[str, Any]]:
    file_path = Path(detail_path)
    if not file_path.exists() or not row_keys:
        return {}
    matched: dict[str, dict[str, Any]] = {}
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except Exception:
                continue
            row_key = _to_text(record.get("row_key"))
            if row_key not in row_keys:
                continue
            payload = _coerce_mapping(record.get("payload"))
            if payload:
                matched[row_key] = payload
            if len(matched) >= len(row_keys):
                break
    return matched


def _resolve_raw_blocker_family(
    *,
    breakout_up: float,
    breakout_down: float,
    runtime_payload: Mapping[str, Any],
    overlay_payload: Mapping[str, Any],
) -> str:
    direction = _to_text(runtime_payload.get("breakout_direction")).upper()
    state = _to_text(runtime_payload.get("breakout_state")).lower()
    confidence = _to_float(runtime_payload.get("breakout_confidence"), 0.0)
    failure_risk = _to_float(runtime_payload.get("breakout_failure_risk"), 0.0)
    target = _to_text(overlay_payload.get("candidate_action_target")).upper()
    reason_summary = _to_text(overlay_payload.get("reason_summary")).lower()

    if breakout_up <= 0.0 and breakout_down <= 0.0:
        return "missing_breakout_response_axis"
    if direction == "NONE":
        return _to_text(runtime_payload.get("why_none_reason"), "direction_threshold_not_met")
    if target == "PROBE_BREAKOUT":
        return "confirm_conflict_demoted" if "confirm_conflict" in reason_summary else "probe_breakout_demoted"
    if target == "WATCH_BREAKOUT":
        return "barrier_drag_demoted" if "barrier_drag" in reason_summary else "watch_breakout_demoted"
    if state == "failed_breakout" or failure_risk > 0.55:
        return "failed_or_high_risk_breakout"
    if target != "ENTER_NOW" and confidence < 0.55:
        return "overlay_confidence_below_enter_threshold"
    if target != "ENTER_NOW":
        return "overlay_wait_more_hold"
    return "enter_now_candidate_ready"


def build_breakout_runtime_raw_audit(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    entry_detail_path: str | Path,
    recent_limit: int = 200,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    semantic_live_config = dict(runtime.get("semantic_live_config", {}) or {})
    decisions = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()

    summary: dict[str, Any] = {
        "contract_version": BREAKOUT_RUNTIME_RAW_AUDIT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "rollout_mode": _to_text(semantic_live_config.get("mode"), "disabled"),
        "recent_row_count": 0,
        "baseline_no_action_row_count": 0,
        "detail_match_count": 0,
        "breakout_up_nonzero_count": 0,
        "breakout_down_nonzero_count": 0,
        "direction_none_count": 0,
        "state_pre_breakout_count": 0,
        "overlay_enter_now_count": 0,
        "overlay_wait_more_count": 0,
        "avg_breakout_up_score": 0.0,
        "avg_breakout_down_score": 0.0,
        "avg_primary_axis_score": 0.0,
        "p50_primary_axis_score": 0.0,
        "p75_primary_axis_score": 0.0,
        "p95_primary_axis_score": 0.0,
        "avg_direction_gap_normalized": 0.0,
        "avg_confirm_score": 0.0,
        "avg_false_break_score": 0.0,
        "avg_continuation_score": 0.0,
        "false_break_dominant_count": 0,
        "current_ready_like_count": 0,
        "current_building_like_count": 0,
        "current_coiled_like_count": 0,
        "probe_ready_like_count": 0,
        "probe_building_like_count": 0,
        "probe_coiled_like_count": 0,
        "probe_initial_like_count": 0,
        "probe_reclaim_like_count": 0,
        "breakout_axis_mode_counts": "{}",
        "breakout_up_source_counts": "{}",
        "breakout_down_source_counts": "{}",
        "breakout_type_candidate_counts": "{}",
        "selected_axis_family_counts": "{}",
        "why_none_reason_counts": "{}",
        "raw_blocker_family_counts": "{}",
        "breakout_direction_counts": "{}",
        "breakout_state_counts": "{}",
        "overlay_target_counts": "{}",
        "conflict_level_counts": "{}",
        "action_demotion_rule_counts": "{}",
        "overlay_reason_summary_counts": "{}",
        "micro_breakout_readiness_counts": "{}",
        "effective_breakout_readiness_counts": "{}",
        "recent_symbols": "",
        "recommended_next_action": "collect_breakout_detail_matches",
    }

    if decisions.empty:
        return pd.DataFrame(columns=BREAKOUT_RUNTIME_RAW_AUDIT_COLUMNS), summary

    decisions = decisions.copy()
    for column in (
        "time",
        "symbol",
        "action",
        "entry_authority_rejected_by",
        "entry_candidate_bridge_baseline_no_action",
        "detail_row_key",
    ):
        if column not in decisions.columns:
            decisions[column] = ""

    decisions["__time_sort"] = pd.to_datetime(decisions["time"], errors="coerce")
    decisions = decisions.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    recent = decisions.head(max(1, int(recent_limit))).copy()
    summary["recent_row_count"] = int(len(recent))

    baseline_mask = (
        recent["entry_authority_rejected_by"].fillna("").astype(str).str.strip() == "baseline_no_action"
    )
    if not baseline_mask.any():
        baseline_mask = recent["entry_candidate_bridge_baseline_no_action"].fillna(False).astype(bool)
    if not baseline_mask.any():
        baseline_mask = recent["action"].fillna("").astype(str).str.strip().eq("")
    baseline = recent.loc[baseline_mask].copy()
    summary["baseline_no_action_row_count"] = int(len(baseline))
    if baseline.empty:
        summary["recommended_next_action"] = "retain_breakout_observation_window"
        return pd.DataFrame(columns=BREAKOUT_RUNTIME_RAW_AUDIT_COLUMNS), summary

    row_keys = {
        _to_text(value)
        for value in baseline["detail_row_key"].fillna("").astype(str)
        if _to_text(value)
    }
    detail_payloads = _load_matching_detail_payloads(entry_detail_path, row_keys)
    summary["detail_match_count"] = int(len(detail_payloads))
    if not detail_payloads:
        summary["recommended_next_action"] = "inspect_entry_detail_rotation_or_row_key_alignment"
        return pd.DataFrame(columns=BREAKOUT_RUNTIME_RAW_AUDIT_COLUMNS), summary

    rows: list[dict[str, Any]] = []
    for row in baseline.to_dict(orient="records"):
        detail_row_key = _to_text(row.get("detail_row_key"))
        payload = detail_payloads.get(detail_row_key)
        if not payload:
            continue
        axis_trace = _response_breakout_axis_trace(payload, None)
        breakout_up, breakout_down = _response_breakout_scores(payload, None)
        forecast_bridge = _coerce_mapping(payload.get("forecast_state25_runtime_bridge_v1"))
        belief_bridge = _coerce_mapping(payload.get("belief_state25_runtime_bridge_v1"))
        barrier_bridge = _coerce_mapping(payload.get("barrier_state25_runtime_bridge_v1"))
        barrier_summary = _coerce_mapping(barrier_bridge.get("barrier_runtime_summary_v1"))
        forecast_summary = _coerce_mapping(forecast_bridge.get("forecast_runtime_summary_v1"))
        runtime_payload = build_breakout_event_runtime_v1(
            payload,
            forecast_state25_runtime_bridge_v1=forecast_bridge,
        )
        overlay_payload = build_breakout_event_overlay_candidates_v1(
            payload,
            breakout_event_runtime_v1=runtime_payload,
            forecast_state25_runtime_bridge_v1=forecast_bridge,
            belief_state25_runtime_bridge_v1=belief_bridge,
            barrier_state25_runtime_bridge_v1=barrier_bridge,
        )
        rows.append(
            {
                "observation_event_id": f"breakout_runtime_raw_audit::{detail_row_key}",
                "generated_at": generated_at,
                "runtime_updated_at": summary["runtime_updated_at"],
                "rollout_mode": summary["rollout_mode"],
                "time": _to_text(payload.get("time"), _to_text(row.get("time"))),
                "symbol": _to_text(payload.get("symbol"), _to_text(row.get("symbol"))).upper(),
                "detail_row_key": detail_row_key,
                "micro_breakout_readiness_state": _to_text(payload.get("micro_breakout_readiness_state")).upper(),
                "effective_breakout_readiness_state": _to_text(
                    runtime_payload.get("effective_breakout_readiness_state")
                ).upper(),
                "breakout_readiness_origin": _to_text(runtime_payload.get("breakout_readiness_origin")).lower(),
                "breakout_up_score": round(float(breakout_up), 6),
                "breakout_down_score": round(float(breakout_down), 6),
                "breakout_axis_mode": _to_text(axis_trace.get("breakout_axis_mode"), "missing"),
                "breakout_axis_bridge_applied": bool(axis_trace.get("breakout_axis_bridge_applied")),
                "breakout_up_source": _to_text(axis_trace.get("breakout_up_source")),
                "breakout_down_source": _to_text(axis_trace.get("breakout_down_source")),
                "breakout_type_candidate": _to_text(runtime_payload.get("breakout_type_candidate")).lower(),
                "selected_axis_family": _to_text(runtime_payload.get("selected_axis_family")).lower(),
                "breakout_direction_gap": round(_to_float(runtime_payload.get("breakout_direction_gap"), 0.0), 6),
                "breakout_direction_gap_normalized": round(
                    _to_float(runtime_payload.get("breakout_direction_gap_normalized"), 0.0),
                    6,
                ),
                "why_none_reason": _to_text(runtime_payload.get("why_none_reason")).lower(),
                "confirm_side": _to_text(forecast_summary.get("confirm_side")).upper(),
                "confirm_score": round(_to_float(forecast_summary.get("confirm_score"), 0.0), 6),
                "false_break_score": round(_to_float(forecast_summary.get("false_break_score"), 0.0), 6),
                "continuation_score": round(_to_float(forecast_summary.get("continuation_score"), 0.0), 6),
                "barrier_total": round(_to_float(barrier_summary.get("barrier_total"), 0.0), 6),
                "breakout_direction": _to_text(runtime_payload.get("breakout_direction")).upper(),
                "breakout_state": _to_text(runtime_payload.get("breakout_state")).lower(),
                "breakout_detected": bool(runtime_payload.get("breakout_detected")),
                "breakout_confidence": round(_to_float(runtime_payload.get("breakout_confidence"), 0.0), 6),
                "breakout_failure_risk": round(_to_float(runtime_payload.get("breakout_failure_risk"), 0.0), 6),
                "overlay_target": _to_text(overlay_payload.get("candidate_action_target")).upper(),
                "conflict_level": _to_text(overlay_payload.get("conflict_level")).lower(),
                "action_demotion_rule": _to_text(overlay_payload.get("action_demotion_rule")).lower(),
                "overlay_reason_summary": _to_text(overlay_payload.get("reason_summary")),
                "raw_blocker_family": _resolve_raw_blocker_family(
                    breakout_up=breakout_up,
                    breakout_down=breakout_down,
                    runtime_payload=runtime_payload,
                    overlay_payload=overlay_payload,
                ),
            }
        )

    frame = pd.DataFrame(rows, columns=BREAKOUT_RUNTIME_RAW_AUDIT_COLUMNS)
    if frame.empty:
        summary["recommended_next_action"] = "retain_breakout_observation_window"
        return frame, summary

    primary_axis = pd.to_numeric(
        frame[["breakout_up_score", "breakout_down_score"]].max(axis=1),
        errors="coerce",
    ).astype(float)
    direction_gap = pd.to_numeric(frame["breakout_direction_gap"], errors="coerce").astype(float)
    direction_gap_normalized = (direction_gap / primary_axis.mask(primary_axis == 0.0)).fillna(0.0)
    confirm_or_continuation = frame[["confirm_score", "continuation_score"]].max(axis=1)
    current_ready_like = (primary_axis >= 0.55) & (
        (confirm_or_continuation >= 0.30)
    )
    current_building_like = (primary_axis >= 0.35) & (
        (frame["confirm_score"] >= 0.22) | (frame["breakout_direction_gap"] >= 0.12)
    )
    current_coiled_like = (primary_axis >= 0.22) & (confirm_or_continuation >= 0.15)
    probe_ready_like = (primary_axis >= 0.12) & (
        (frame["confirm_score"] >= 0.08) | (frame["continuation_score"] >= 0.10)
    )
    probe_building_like = (primary_axis >= 0.09) & (
        (frame["confirm_score"] >= 0.07) | (frame["breakout_direction_gap"] >= 0.03)
    )
    probe_coiled_like = (primary_axis >= 0.07) & (confirm_or_continuation >= 0.08)
    probe_initial_like = primary_axis >= 0.10
    probe_reclaim_like = primary_axis >= 0.08

    summary.update(
        {
            "breakout_up_nonzero_count": int((frame["breakout_up_score"] > 0.0).sum()),
            "breakout_down_nonzero_count": int((frame["breakout_down_score"] > 0.0).sum()),
            "direction_none_count": int(frame["breakout_direction"].fillna("").astype(str).eq("NONE").sum()),
            "state_pre_breakout_count": int(frame["breakout_state"].fillna("").astype(str).eq("pre_breakout").sum()),
            "overlay_enter_now_count": int(frame["overlay_target"].fillna("").astype(str).eq("ENTER_NOW").sum()),
            "overlay_wait_more_count": int(frame["overlay_target"].fillna("").astype(str).eq("WAIT_MORE").sum()),
            "avg_breakout_up_score": round(frame["breakout_up_score"].mean(), 6),
            "avg_breakout_down_score": round(frame["breakout_down_score"].mean(), 6),
            "avg_primary_axis_score": round(primary_axis.mean(), 6),
            "p50_primary_axis_score": round(primary_axis.quantile(0.50), 6),
            "p75_primary_axis_score": round(primary_axis.quantile(0.75), 6),
            "p95_primary_axis_score": round(primary_axis.quantile(0.95), 6),
            "avg_direction_gap_normalized": round(direction_gap_normalized.mean(), 6),
            "avg_confirm_score": round(frame["confirm_score"].mean(), 6),
            "avg_false_break_score": round(frame["false_break_score"].mean(), 6),
            "avg_continuation_score": round(frame["continuation_score"].mean(), 6),
            "false_break_dominant_count": int((frame["false_break_score"] > confirm_or_continuation).sum()),
            "current_ready_like_count": int(current_ready_like.sum()),
            "current_building_like_count": int(current_building_like.sum()),
            "current_coiled_like_count": int(current_coiled_like.sum()),
            "probe_ready_like_count": int(probe_ready_like.sum()),
            "probe_building_like_count": int(probe_building_like.sum()),
            "probe_coiled_like_count": int(probe_coiled_like.sum()),
            "probe_initial_like_count": int(probe_initial_like.sum()),
            "probe_reclaim_like_count": int(probe_reclaim_like.sum()),
            "breakout_axis_mode_counts": _series_json_counts(frame["breakout_axis_mode"]),
            "breakout_up_source_counts": _series_json_counts(frame["breakout_up_source"]),
            "breakout_down_source_counts": _series_json_counts(frame["breakout_down_source"]),
            "breakout_type_candidate_counts": _series_json_counts(frame["breakout_type_candidate"]),
            "selected_axis_family_counts": _series_json_counts(frame["selected_axis_family"]),
            "why_none_reason_counts": _series_json_counts(frame["why_none_reason"]),
            "raw_blocker_family_counts": _series_json_counts(frame["raw_blocker_family"]),
            "breakout_direction_counts": _series_json_counts(frame["breakout_direction"]),
            "breakout_state_counts": _series_json_counts(frame["breakout_state"]),
            "overlay_target_counts": _series_json_counts(frame["overlay_target"]),
            "conflict_level_counts": _series_json_counts(frame["conflict_level"]),
            "action_demotion_rule_counts": _series_json_counts(frame["action_demotion_rule"]),
            "overlay_reason_summary_counts": _series_json_counts(frame["overlay_reason_summary"]),
            "micro_breakout_readiness_counts": _series_json_counts(frame["micro_breakout_readiness_state"]),
            "effective_breakout_readiness_counts": _series_json_counts(frame["effective_breakout_readiness_state"]),
            "recent_symbols": _stable_join(frame["symbol"]),
        }
    )

    if summary["breakout_up_nonzero_count"] == 0 and summary["breakout_down_nonzero_count"] == 0:
        recommended_next_action = "inspect_response_vector_breakout_axes"
    elif _to_text(summary.get("effective_breakout_readiness_counts"), "{}") == "{}":
        recommended_next_action = "inspect_breakout_readiness_surrogate_thresholds"
    elif _to_text(summary.get("breakout_type_candidate_counts"), "{}") == "{\"none\": %d}" % len(frame):
        recommended_next_action = "inspect_breakout_type_split_thresholds"
    elif summary["direction_none_count"] == len(frame):
        recommended_next_action = "inspect_breakout_type_split_or_direction_resolver"
    elif summary["state_pre_breakout_count"] == len(frame):
        recommended_next_action = "inspect_breakout_state_resolution_rules"
    elif summary["overlay_enter_now_count"] == 0 and summary["overlay_wait_more_count"] > 0:
        recommended_next_action = "inspect_breakout_overlay_enter_now_thresholds"
    else:
        recommended_next_action = "compare_breakout_enter_now_rows_with_candidate_bridge"
    summary["recommended_next_action"] = recommended_next_action
    return frame, summary


def render_breakout_runtime_raw_audit_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> str:
    row = dict(summary or {})
    lines = [
        "# Breakout Runtime Raw Audit",
        "",
        f"- generated_at: `{_to_text(row.get('generated_at'))}`",
        f"- rollout_mode: `{_to_text(row.get('rollout_mode'), 'disabled')}`",
        f"- recent_row_count: `{int(_to_float(row.get('recent_row_count'), 0.0))}`",
        f"- baseline_no_action_row_count: `{int(_to_float(row.get('baseline_no_action_row_count'), 0.0))}`",
        f"- detail_match_count: `{int(_to_float(row.get('detail_match_count'), 0.0))}`",
        f"- breakout_up_nonzero_count: `{int(_to_float(row.get('breakout_up_nonzero_count'), 0.0))}`",
        f"- breakout_down_nonzero_count: `{int(_to_float(row.get('breakout_down_nonzero_count'), 0.0))}`",
        f"- direction_none_count: `{int(_to_float(row.get('direction_none_count'), 0.0))}`",
        f"- overlay_enter_now_count: `{int(_to_float(row.get('overlay_enter_now_count'), 0.0))}`",
        f"- overlay_wait_more_count: `{int(_to_float(row.get('overlay_wait_more_count'), 0.0))}`",
        f"- avg_breakout_up_score: `{round(_to_float(row.get('avg_breakout_up_score'), 0.0), 6)}`",
        f"- avg_breakout_down_score: `{round(_to_float(row.get('avg_breakout_down_score'), 0.0), 6)}`",
        f"- avg_primary_axis_score: `{round(_to_float(row.get('avg_primary_axis_score'), 0.0), 6)}`",
        f"- p50_primary_axis_score: `{round(_to_float(row.get('p50_primary_axis_score'), 0.0), 6)}`",
        f"- p75_primary_axis_score: `{round(_to_float(row.get('p75_primary_axis_score'), 0.0), 6)}`",
        f"- p95_primary_axis_score: `{round(_to_float(row.get('p95_primary_axis_score'), 0.0), 6)}`",
        f"- avg_direction_gap_normalized: `{round(_to_float(row.get('avg_direction_gap_normalized'), 0.0), 6)}`",
        f"- avg_confirm_score: `{round(_to_float(row.get('avg_confirm_score'), 0.0), 6)}`",
        f"- avg_false_break_score: `{round(_to_float(row.get('avg_false_break_score'), 0.0), 6)}`",
        f"- avg_continuation_score: `{round(_to_float(row.get('avg_continuation_score'), 0.0), 6)}`",
        f"- false_break_dominant_count: `{int(_to_float(row.get('false_break_dominant_count'), 0.0))}`",
        f"- current_ready_like_count: `{int(_to_float(row.get('current_ready_like_count'), 0.0))}`",
        f"- current_building_like_count: `{int(_to_float(row.get('current_building_like_count'), 0.0))}`",
        f"- current_coiled_like_count: `{int(_to_float(row.get('current_coiled_like_count'), 0.0))}`",
        f"- probe_ready_like_count: `{int(_to_float(row.get('probe_ready_like_count'), 0.0))}`",
        f"- probe_building_like_count: `{int(_to_float(row.get('probe_building_like_count'), 0.0))}`",
        f"- probe_coiled_like_count: `{int(_to_float(row.get('probe_coiled_like_count'), 0.0))}`",
        f"- probe_initial_like_count: `{int(_to_float(row.get('probe_initial_like_count'), 0.0))}`",
        f"- probe_reclaim_like_count: `{int(_to_float(row.get('probe_reclaim_like_count'), 0.0))}`",
        f"- breakout_axis_mode_counts: `{_to_text(row.get('breakout_axis_mode_counts'), '{}')}`",
        f"- breakout_up_source_counts: `{_to_text(row.get('breakout_up_source_counts'), '{}')}`",
        f"- breakout_down_source_counts: `{_to_text(row.get('breakout_down_source_counts'), '{}')}`",
        f"- breakout_type_candidate_counts: `{_to_text(row.get('breakout_type_candidate_counts'), '{}')}`",
        f"- selected_axis_family_counts: `{_to_text(row.get('selected_axis_family_counts'), '{}')}`",
        f"- why_none_reason_counts: `{_to_text(row.get('why_none_reason_counts'), '{}')}`",
        f"- raw_blocker_family_counts: `{_to_text(row.get('raw_blocker_family_counts'), '{}')}`",
        f"- breakout_direction_counts: `{_to_text(row.get('breakout_direction_counts'), '{}')}`",
        f"- breakout_state_counts: `{_to_text(row.get('breakout_state_counts'), '{}')}`",
        f"- overlay_target_counts: `{_to_text(row.get('overlay_target_counts'), '{}')}`",
        f"- conflict_level_counts: `{_to_text(row.get('conflict_level_counts'), '{}')}`",
        f"- action_demotion_rule_counts: `{_to_text(row.get('action_demotion_rule_counts'), '{}')}`",
        f"- overlay_reason_summary_counts: `{_to_text(row.get('overlay_reason_summary_counts'), '{}')}`",
        f"- micro_breakout_readiness_counts: `{_to_text(row.get('micro_breakout_readiness_counts'), '{}')}`",
        f"- effective_breakout_readiness_counts: `{_to_text(row.get('effective_breakout_readiness_counts'), '{}')}`",
        f"- recommended_next_action: `{_to_text(row.get('recommended_next_action'))}`",
    ]
    if frame is None or frame.empty:
        lines.extend(["", "_No breakout raw audit rows found._"])
    return "\n".join(lines) + "\n"
