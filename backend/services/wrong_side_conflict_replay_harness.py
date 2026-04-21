"""Replay historical wrong-side conflicts through the current P0 guard/bridge path."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.entry_candidate_bridge import (
    build_entry_candidate_bridge_flat_fields,
    build_entry_candidate_bridge_v1,
)
from backend.services.entry_try_open_entry import _build_active_action_conflict_guard_v1
from backend.services.trade_csv_schema import now_kst_dt


WRONG_SIDE_CONFLICT_REPLAY_HARNESS_VERSION = "wrong_side_conflict_replay_harness_v1"

WRONG_SIDE_CONFLICT_REPLAY_COLUMNS = [
    "replay_observation_id",
    "generated_at",
    "symbol",
    "event_time",
    "setup_id",
    "setup_reason",
    "baseline_action",
    "original_outcome",
    "original_blocked_by",
    "original_action_none_reason",
    "original_bridge_mode",
    "original_bridge_action",
    "original_conflict_detected",
    "original_guard_applied",
    "original_directional_state",
    "original_directional_action",
    "original_up_bias_score",
    "breakout_direction",
    "breakout_action_target",
    "breakout_sensed_up",
    "breakout_selected_original",
    "replay_conflict_detected",
    "replay_guard_eligible",
    "replay_guard_applied",
    "replay_resolution_state",
    "replay_conflict_kind",
    "replay_failure_label",
    "replay_up_bias_score",
    "replay_down_bias_score",
    "replay_bias_gap",
    "replay_warning_count",
    "replay_bridge_mode",
    "replay_bridge_selected",
    "replay_bridge_source",
    "replay_bridge_action",
    "replay_bridge_surface_family",
    "replay_bridge_surface_state",
    "replay_delta",
    "evidence_summary",
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


def _to_bool(value: object) -> bool:
    return _to_text(value).lower() in {"1", "true", "yes", "y"}


def _slug_text(value: object) -> str:
    text = _to_text(value).lower()
    safe = "".join(char if char.isalnum() else "_" for char in text)
    return safe.strip("_")


def _first_text(*values: object, default: str = "") -> str:
    for value in values:
        text = _to_text(value)
        if text:
            return text
    return str(default or "")


def _json_counts(counts: Mapping[str, int]) -> str:
    return (
        json.dumps(
            {str(key): int(value) for key, value in counts.items()},
            ensure_ascii=False,
            sort_keys=True,
        )
        if counts
        else "{}"
    )


def _series_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    series = frame[column].fillna("").astype(str).str.strip().replace("", pd.NA).dropna()
    counts = series.value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _ensure_columns(frame: pd.DataFrame) -> pd.DataFrame:
    local = frame.copy()
    for column in (
        "time",
        "symbol",
        "setup_id",
        "setup_reason",
        "action",
        "outcome",
        "blocked_by",
        "action_none_reason",
        "observe_reason",
        "entry_stage",
        "compatibility_mode",
        "core_reason",
        "core_allowed_action",
        "entry_candidate_bridge_mode",
        "entry_candidate_bridge_source",
        "entry_candidate_bridge_action",
        "entry_candidate_bridge_effective_baseline_action",
        "entry_candidate_surface_family",
        "entry_candidate_surface_state",
        "active_action_conflict_detected",
        "active_action_conflict_guard_applied",
        "active_action_conflict_baseline_action",
        "active_action_conflict_directional_action",
        "active_action_conflict_directional_state",
        "active_action_conflict_up_bias_score",
        "countertrend_continuation_enabled",
        "countertrend_continuation_action",
        "countertrend_continuation_confidence",
        "countertrend_continuation_reason_summary",
        "countertrend_continuation_warning_count",
        "countertrend_continuation_surface_family",
        "countertrend_continuation_surface_state",
        "countertrend_anti_long_score",
        "countertrend_anti_short_score",
        "countertrend_pro_up_score",
        "countertrend_pro_down_score",
        "countertrend_directional_bias",
        "countertrend_action_state",
        "countertrend_directional_candidate_action",
        "countertrend_directional_execution_action",
        "countertrend_directional_state_reason",
        "countertrend_directional_state_rank",
        "countertrend_directional_owner_family",
        "countertrend_directional_down_bias_score",
        "countertrend_directional_up_bias_score",
        "breakout_candidate_action",
        "breakout_candidate_confidence",
        "breakout_candidate_reason",
        "breakout_candidate_source",
        "breakout_candidate_action_target",
        "breakout_candidate_direction",
        "breakout_candidate_surface_family",
        "breakout_candidate_surface_state",
        "forecast_state25_overlay_reason_summary",
        "belief_action_hint_reason_summary",
        "barrier_action_hint_reason_summary",
        "box_state",
        "bb_state",
    ):
        if column not in local.columns:
            local[column] = ""
    return local


def _build_countertrend_signal_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    warning_count = int(_to_float(row.get("countertrend_continuation_warning_count"), 0.0))
    reason_summary = _to_text(row.get("countertrend_continuation_reason_summary"))
    warning_tokens = [token for token in reason_summary.split("|") if token]
    return {
        "contract_version": "countertrend_continuation_signal_v1",
        "enabled": bool(
            _to_bool(row.get("countertrend_continuation_enabled"))
            or _to_text(row.get("countertrend_directional_candidate_action")).upper()
            in {"BUY", "SELL"}
        ),
        "watch_only": False,
        "signal_family": "countertrend_continuation",
        "signal_state": _to_text(row.get("countertrend_continuation_state")),
        "signal_action": _to_text(row.get("countertrend_continuation_action")).upper(),
        "signal_confidence": _to_float(row.get("countertrend_continuation_confidence"), 0.0),
        "warning_count": warning_count,
        "warning_tokens": warning_tokens[:warning_count] if warning_count else warning_tokens,
        "reason_summary": reason_summary,
        "surface_family": _to_text(row.get("countertrend_continuation_surface_family")),
        "surface_state": _to_text(row.get("countertrend_continuation_surface_state")),
        "anti_long_score": _to_float(row.get("countertrend_anti_long_score"), 0.0),
        "anti_short_score": _to_float(row.get("countertrend_anti_short_score"), 0.0),
        "pro_up_score": _to_float(row.get("countertrend_pro_up_score"), 0.0),
        "pro_down_score": _to_float(row.get("countertrend_pro_down_score"), 0.0),
        "directional_bias": _to_text(row.get("countertrend_directional_bias")).upper(),
        "directional_action_state": _to_text(row.get("countertrend_action_state")).upper(),
        "directional_candidate_action": _to_text(
            row.get("countertrend_directional_candidate_action")
        ).upper(),
        "directional_execution_action": _to_text(
            row.get("countertrend_directional_execution_action")
        ).upper(),
        "directional_state_reason": _to_text(row.get("countertrend_directional_state_reason")),
        "directional_owner_family": _to_text(row.get("countertrend_directional_owner_family")),
        "directional_state_rank": int(
            _to_float(row.get("countertrend_directional_state_rank"), 0.0)
        ),
        "directional_down_bias_score": _to_float(
            row.get("countertrend_directional_down_bias_score"), 0.0
        ),
        "directional_up_bias_score": _to_float(
            row.get("countertrend_directional_up_bias_score"), 0.0
        ),
    }


def _build_breakout_runtime_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    direction = _to_text(row.get("breakout_candidate_direction")).upper()
    target = _to_text(row.get("breakout_candidate_action_target")).upper()
    source = _to_text(row.get("breakout_candidate_source"))
    surface_state = _to_text(row.get("breakout_candidate_surface_state")).lower()
    breakout_state = ""
    breakout_type_candidate = ""
    if surface_state == "initial_break":
        breakout_state = "initial_breakout"
        breakout_type_candidate = "initial_breakout_candidate"
    elif surface_state == "continuation_follow":
        breakout_state = "breakout_continuation"
        breakout_type_candidate = "continuation_breakout_candidate"
    elif surface_state == "pullback_resume":
        breakout_state = "breakout_pullback"
        breakout_type_candidate = "reclaim_breakout_candidate"
    confidence = _to_float(row.get("breakout_candidate_confidence"), 0.0)
    if confidence <= 0.0 and target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}:
        confidence = 0.30 if target == "WATCH_BREAKOUT" else 0.34 if target == "PROBE_BREAKOUT" else 0.56
    failure_risk = _to_float(row.get("breakout_failure_risk"), 0.0)
    if failure_risk <= 0.0 and target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}:
        failure_risk = 0.36 if target == "WATCH_BREAKOUT" else 0.30 if target == "PROBE_BREAKOUT" else 0.22
    return {
        "available": bool(source) or (direction in {"UP", "DOWN"} and target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}),
        "breakout_detected": direction in {"UP", "DOWN"},
        "breakout_direction": direction,
        "breakout_confidence": confidence,
        "breakout_failure_risk": failure_risk,
        "breakout_state": breakout_state,
        "breakout_type_candidate": breakout_type_candidate,
        "candidate_action_target": target,
    }


def _build_breakout_overlay_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    source = _to_text(row.get("breakout_candidate_source"))
    target = _to_text(row.get("breakout_candidate_action_target")).upper()
    return {
        "enabled": bool(source) or target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"},
        "candidate_action_target": _to_text(
            row.get("breakout_candidate_action_target"),
            "WATCH_BREAKOUT" if source else "",
        ).upper(),
        "reason_summary": _to_text(row.get("breakout_candidate_reason")),
    }


def _replay_conflict_row(row: Mapping[str, Any]) -> dict[str, Any]:
    symbol = _to_text(row.get("symbol")).upper()
    baseline_action = _first_text(
        row.get("active_action_conflict_baseline_action"),
        row.get("entry_candidate_bridge_effective_baseline_action"),
        row.get("action"),
    ).upper()
    countertrend_signal = _build_countertrend_signal_from_row(row)
    guard = _build_active_action_conflict_guard_v1(
        symbol=symbol,
        baseline_action=baseline_action,
        setup_id=_to_text(row.get("setup_id")),
        setup_reason=_to_text(row.get("setup_reason")),
        runtime_signal_row=dict(row),
        forecast_state25_log_only_overlay_trace_v1={
            "reason_summary": _to_text(row.get("forecast_state25_overlay_reason_summary"))
        },
        belief_action_hint_v1={
            "reason_summary": _to_text(row.get("belief_action_hint_reason_summary"))
        },
        barrier_action_hint_v1={
            "reason_summary": _to_text(row.get("barrier_action_hint_reason_summary"))
        },
        countertrend_continuation_signal_v1=countertrend_signal,
    )
    breakout_runtime = _build_breakout_runtime_from_row(row)
    breakout_overlay = _build_breakout_overlay_from_row(row)
    bridge = build_entry_candidate_bridge_v1(
        symbol=symbol,
        action=baseline_action,
        entry_stage=_to_text(row.get("entry_stage"), "BALANCED"),
        core_reason=_to_text(row.get("core_reason")),
        observe_reason=_to_text(row.get("observe_reason")),
        action_none_reason=_to_text(row.get("action_none_reason")),
        blocked_by=_to_text(row.get("blocked_by")),
        compatibility_mode=_to_text(row.get("compatibility_mode")),
        breakout_event_runtime_v1=breakout_runtime,
        breakout_event_overlay_candidates_v1=breakout_overlay,
        countertrend_continuation_signal_v1=countertrend_signal,
        active_action_conflict_guard_v1=guard,
    )
    bridge_flat = build_entry_candidate_bridge_flat_fields(bridge)
    original_guard_applied = _to_bool(row.get("active_action_conflict_guard_applied"))
    original_bridge_mode = _to_text(row.get("entry_candidate_bridge_mode"))
    replay_guard_applied = bool(guard.get("guard_applied", False))
    replay_bridge_mode = _to_text(bridge_flat.get("entry_candidate_bridge_mode"))
    delta_parts: list[str] = []
    if replay_guard_applied and not original_guard_applied:
        delta_parts.append("guard_promoted")
    if replay_bridge_mode != original_bridge_mode:
        delta_parts.append(f"bridge:{original_bridge_mode}->{replay_bridge_mode}")
    replay_bridge_action = _to_text(bridge_flat.get("entry_candidate_bridge_action")).upper()
    original_bridge_action = _to_text(row.get("entry_candidate_bridge_action")).upper()
    if replay_bridge_action != original_bridge_action:
        delta_parts.append(
            f"bridge_action:{original_bridge_action or 'NONE'}->{replay_bridge_action or 'NONE'}"
        )
    if not delta_parts:
        delta_parts.append("no_change")

    breakout_direction = _to_text(row.get("breakout_candidate_direction")).upper()
    breakout_target = _to_text(
        row.get("breakout_candidate_action_target"),
        _to_text(breakout_overlay.get("candidate_action_target")),
    ).upper()
    breakout_sensed_up = bool(
        breakout_direction == "UP"
        and _to_text(row.get("breakout_candidate_source")) == "breakout_runtime_overlay"
    )
    evidence_tokens = [
        _to_text(row.get("observe_reason")),
        _to_text(row.get("blocked_by")),
        _to_text(row.get("countertrend_directional_state_reason")),
        _to_text(row.get("breakout_candidate_source")),
        breakout_direction,
        replay_bridge_mode,
        replay_bridge_action,
    ]
    return {
        "replay_observation_id": f"{WRONG_SIDE_CONFLICT_REPLAY_HARNESS_VERSION}:{_slug_text(symbol)}:{_slug_text(_to_text(row.get('time')))}",
        "generated_at": "",
        "symbol": symbol,
        "event_time": _to_text(row.get("time")),
        "setup_id": _to_text(row.get("setup_id")),
        "setup_reason": _to_text(row.get("setup_reason")),
        "baseline_action": baseline_action,
        "original_outcome": _to_text(row.get("outcome")),
        "original_blocked_by": _to_text(row.get("blocked_by")),
        "original_action_none_reason": _to_text(row.get("action_none_reason")),
        "original_bridge_mode": original_bridge_mode,
        "original_bridge_action": original_bridge_action,
        "original_conflict_detected": bool(_to_bool(row.get("active_action_conflict_detected"))),
        "original_guard_applied": bool(original_guard_applied),
        "original_directional_state": _to_text(row.get("countertrend_action_state")).upper(),
        "original_directional_action": _to_text(
            row.get("countertrend_directional_candidate_action")
        ).upper(),
        "original_up_bias_score": round(
            _to_float(row.get("countertrend_directional_up_bias_score"), 0.0), 6
        ),
        "breakout_direction": breakout_direction,
        "breakout_action_target": breakout_target,
        "breakout_sensed_up": bool(breakout_sensed_up),
        "breakout_selected_original": bool(
            _to_text(row.get("entry_candidate_bridge_source")) == "breakout_candidate"
        ),
        "replay_conflict_detected": bool(guard.get("conflict_detected", False)),
        "replay_guard_eligible": bool(guard.get("guard_eligible", False)),
        "replay_guard_applied": bool(replay_guard_applied),
        "replay_resolution_state": _to_text(guard.get("resolution_state")),
        "replay_conflict_kind": _to_text(guard.get("conflict_kind")),
        "replay_failure_label": _to_text(guard.get("failure_label")),
        "replay_up_bias_score": round(_to_float(guard.get("up_bias_score"), 0.0), 6),
        "replay_down_bias_score": round(_to_float(guard.get("down_bias_score"), 0.0), 6),
        "replay_bias_gap": round(_to_float(guard.get("bias_gap"), 0.0), 6),
        "replay_warning_count": int(_to_float(guard.get("warning_count"), 0.0)),
        "replay_bridge_mode": replay_bridge_mode,
        "replay_bridge_selected": bool(
            _to_bool(bridge_flat.get("entry_candidate_bridge_selected"))
        ),
        "replay_bridge_source": _to_text(bridge_flat.get("entry_candidate_bridge_source")),
        "replay_bridge_action": replay_bridge_action,
        "replay_bridge_surface_family": _to_text(
            bridge_flat.get("entry_candidate_surface_family")
        ),
        "replay_bridge_surface_state": _to_text(
            bridge_flat.get("entry_candidate_surface_state")
        ),
        "replay_delta": " | ".join(delta_parts),
        "evidence_summary": " | ".join(token for token in evidence_tokens if token),
    }


def _target_conflict_mask(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)
    symbol_mask = frame["symbol"].fillna("").astype(str).str.upper().isin({"XAUUSD", "NAS100", "BTCUSD"})
    setup_ids = frame["setup_id"].fillna("").astype(str).str.lower()
    setup_reasons = frame["setup_reason"].fillna("").astype(str).str.lower()
    setup_mask = setup_ids.eq("range_upper_reversal_sell")
    for token in (
        "shadow_upper_break_fail_confirm",
        "shadow_upper_reject_probe_observe",
        "shadow_upper_reject_confirm",
    ):
        setup_mask = setup_mask | setup_reasons.str.contains(token, regex=False)
    breakout_mask = (
        frame["breakout_candidate_direction"].fillna("").astype(str).str.upper().eq("UP")
    )
    baseline_sell_mask = pd.Series(False, index=frame.index)
    for column in (
        "action",
        "active_action_conflict_baseline_action",
        "entry_candidate_bridge_effective_baseline_action",
    ):
        baseline_sell_mask = baseline_sell_mask | (
            frame[column].fillna("").astype(str).str.upper().eq("SELL")
        )
    return symbol_mask & setup_mask & baseline_sell_mask & breakout_mask


def _build_recent_breakout_conflict_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "row_count": 0,
            "symbol_counts": "{}",
            "sell_only_conflict_count": 0,
            "action_sell_count": 0,
            "watch_only_target_count": 0,
            "breakout_unselected_count": 0,
        }
    scoped = frame.copy()
    breakout_mask = (
        scoped["breakout_candidate_direction"].fillna("").astype(str).str.upper().eq("UP")
        & scoped["breakout_candidate_source"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("breakout_runtime_overlay")
    )
    breakout = scoped.loc[breakout_mask].copy()
    if breakout.empty:
        return {
            "row_count": 0,
            "symbol_counts": "{}",
            "sell_only_conflict_count": 0,
            "action_sell_count": 0,
            "watch_only_target_count": 0,
            "breakout_unselected_count": 0,
        }
    return {
        "row_count": int(len(breakout)),
        "symbol_counts": _json_counts(_series_counts(breakout, "symbol")),
        "sell_only_conflict_count": int(
            breakout["core_allowed_action"]
            .fillna("")
            .astype(str)
            .str.upper()
            .eq("SELL_ONLY")
            .sum()
        ),
        "action_sell_count": int(
            breakout["action"].fillna("").astype(str).str.upper().eq("SELL").sum()
        ),
        "watch_only_target_count": int(
            breakout["breakout_candidate_action_target"]
            .fillna("")
            .astype(str)
            .str.upper()
            .eq("WATCH_BREAKOUT")
            .sum()
        ),
        "breakout_unselected_count": int(
            breakout["entry_candidate_bridge_source"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("breakout_candidate")
            .sum()
        ),
    }


def _build_recent_breakout_conflict_by_symbol(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    breakout_mask = (
        frame["breakout_candidate_direction"].fillna("").astype(str).str.upper().eq("UP")
        & frame["breakout_candidate_source"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("breakout_runtime_overlay")
    )
    breakout = frame.loc[breakout_mask].copy()
    if breakout.empty:
        return []
    rows: list[dict[str, Any]] = []
    for symbol, group in breakout.groupby(breakout["symbol"].fillna("").astype(str)):
        rows.append(
            {
                "symbol": symbol,
                "row_count": int(len(group)),
                "sell_only_conflict_count": int(
                    group["core_allowed_action"]
                    .fillna("")
                    .astype(str)
                    .str.upper()
                    .eq("SELL_ONLY")
                    .sum()
                ),
                "buy_only_count": int(
                    group["core_allowed_action"]
                    .fillna("")
                    .astype(str)
                    .str.upper()
                    .eq("BUY_ONLY")
                    .sum()
                ),
                "action_sell_count": int(
                    group["action"].fillna("").astype(str).str.upper().eq("SELL").sum()
                ),
                "action_buy_count": int(
                    group["action"].fillna("").astype(str).str.upper().eq("BUY").sum()
                ),
                "watch_only_target_count": int(
                    group["breakout_candidate_action_target"]
                    .fillna("")
                    .astype(str)
                    .str.upper()
                    .eq("WATCH_BREAKOUT")
                    .sum()
                ),
                "breakout_selected_count": int(
                    group["entry_candidate_bridge_source"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .eq("breakout_candidate")
                    .sum()
                ),
            }
        )
    return rows


def build_wrong_side_conflict_replay_harness(
    entry_decisions: pd.DataFrame | None,
    *,
    recent_limit: int = 1200,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    frame = (
        entry_decisions.copy()
        if entry_decisions is not None and not entry_decisions.empty
        else pd.DataFrame()
    )
    summary: dict[str, Any] = {
        "contract_version": WRONG_SIDE_CONFLICT_REPLAY_HARNESS_VERSION,
        "generated_at": generated_at,
        "recent_row_count": 0,
        "target_row_count": 0,
        "replay_row_count": 0,
        "original_guard_applied_count": 0,
        "replay_guard_applied_count": 0,
        "original_bridge_conflict_selected_count": 0,
        "replay_bridge_conflict_selected_count": 0,
        "delta_guard_apply_count": 0,
        "delta_bridge_select_count": 0,
        "symbol_counts": "{}",
        "replay_bridge_mode_counts": "{}",
        "replay_delta_counts": "{}",
        "recommended_next_action": "await_target_conflict_rows",
        "recent_breakout_conflict_summary": {},
        "recent_breakout_conflict_by_symbol": [],
    }
    if frame.empty:
        return pd.DataFrame(columns=WRONG_SIDE_CONFLICT_REPLAY_COLUMNS), summary

    scoped = _ensure_columns(frame)
    scoped["__time_sort"] = pd.to_datetime(scoped["time"], errors="coerce")
    scoped = scoped.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    scoped = scoped.head(max(1, int(recent_limit))).copy()
    summary["recent_row_count"] = int(len(scoped))
    summary["recent_breakout_conflict_summary"] = _build_recent_breakout_conflict_summary(
        scoped
    )
    summary["recent_breakout_conflict_by_symbol"] = _build_recent_breakout_conflict_by_symbol(
        scoped
    )

    targets = scoped.loc[_target_conflict_mask(scoped)].copy()
    summary["target_row_count"] = int(len(targets))
    if targets.empty:
        return pd.DataFrame(columns=WRONG_SIDE_CONFLICT_REPLAY_COLUMNS), summary

    rows = []
    for row in targets.to_dict(orient="records"):
        replayed = _replay_conflict_row(row)
        replayed["generated_at"] = generated_at
        rows.append(replayed)

    harness = pd.DataFrame(rows, columns=WRONG_SIDE_CONFLICT_REPLAY_COLUMNS)
    summary["replay_row_count"] = int(len(harness))
    if harness.empty:
        return harness, summary

    summary["original_guard_applied_count"] = int(harness["original_guard_applied"].sum())
    summary["replay_guard_applied_count"] = int(harness["replay_guard_applied"].sum())
    summary["original_bridge_conflict_selected_count"] = int(
        harness["original_bridge_mode"]
        .fillna("")
        .astype(str)
        .eq("active_action_conflict_resolution")
        .sum()
    )
    summary["replay_bridge_conflict_selected_count"] = int(
        harness["replay_bridge_mode"]
        .fillna("")
        .astype(str)
        .eq("active_action_conflict_resolution")
        .sum()
    )
    summary["delta_guard_apply_count"] = int(
        ((harness["replay_guard_applied"]) & (~harness["original_guard_applied"])).sum()
    )
    summary["delta_bridge_select_count"] = int(
        harness["replay_bridge_mode"]
        .fillna("")
        .astype(str)
        .eq("active_action_conflict_resolution")
        .sum()
        - harness["original_bridge_mode"]
        .fillna("")
        .astype(str)
        .eq("active_action_conflict_resolution")
        .sum()
    )
    summary["symbol_counts"] = _json_counts(_series_counts(harness, "symbol"))
    summary["replay_bridge_mode_counts"] = _json_counts(
        _series_counts(harness, "replay_bridge_mode")
    )
    summary["replay_delta_counts"] = _json_counts(_series_counts(harness, "replay_delta"))
    summary["recommended_next_action"] = (
        "proceed_to_xau_upper_reversal_conflict_validation"
    )
    return harness, summary


def render_wrong_side_conflict_replay_harness_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    breakout_summary = summary.get("recent_breakout_conflict_summary", {}) or {}
    breakout_by_symbol = summary.get("recent_breakout_conflict_by_symbol", []) or []
    lines = [
        "# Wrong-Side Conflict Replay Harness",
        "",
        f"- generated_at: `{_to_text(summary.get('generated_at'))}`",
        f"- recent_row_count: `{int(_to_float(summary.get('recent_row_count'))):d}`",
        f"- target_row_count: `{int(_to_float(summary.get('target_row_count'))):d}`",
        f"- replay_row_count: `{int(_to_float(summary.get('replay_row_count'))):d}`",
        f"- original_guard_applied_count: `{int(_to_float(summary.get('original_guard_applied_count'))):d}`",
        f"- replay_guard_applied_count: `{int(_to_float(summary.get('replay_guard_applied_count'))):d}`",
        f"- original_bridge_conflict_selected_count: `{int(_to_float(summary.get('original_bridge_conflict_selected_count'))):d}`",
        f"- replay_bridge_conflict_selected_count: `{int(_to_float(summary.get('replay_bridge_conflict_selected_count'))):d}`",
        f"- delta_guard_apply_count: `{int(_to_float(summary.get('delta_guard_apply_count'))):d}`",
        f"- delta_bridge_select_count: `{int(_to_float(summary.get('delta_bridge_select_count'))):d}`",
        f"- symbol_counts: `{_to_text(summary.get('symbol_counts'), '{}')}`",
        f"- replay_bridge_mode_counts: `{_to_text(summary.get('replay_bridge_mode_counts'), '{}')}`",
        f"- replay_delta_counts: `{_to_text(summary.get('replay_delta_counts'), '{}')}`",
        f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`",
        "",
        "## Recent Breakout Conflict Summary",
        "",
        f"- row_count: `{int(_to_float(breakout_summary.get('row_count'))):d}`",
        f"- symbol_counts: `{_to_text(breakout_summary.get('symbol_counts'), '{}')}`",
        f"- sell_only_conflict_count: `{int(_to_float(breakout_summary.get('sell_only_conflict_count'))):d}`",
        f"- action_sell_count: `{int(_to_float(breakout_summary.get('action_sell_count'))):d}`",
        f"- watch_only_target_count: `{int(_to_float(breakout_summary.get('watch_only_target_count'))):d}`",
        f"- breakout_unselected_count: `{int(_to_float(breakout_summary.get('breakout_unselected_count'))):d}`",
        "",
    ]
    if breakout_by_symbol:
        breakout_frame = pd.DataFrame(breakout_by_symbol)
        try:
            breakout_preview = breakout_frame.to_markdown(index=False)
        except Exception:
            breakout_preview = "```csv\n" + breakout_frame.to_csv(index=False) + "```\n"
        lines.extend(
            [
                "### By Symbol",
                "",
                breakout_preview,
                "",
            ]
        )
    if not frame.empty:
        preview_frame = frame.head(10)
        try:
            preview_text = preview_frame.to_markdown(index=False)
        except Exception:
            preview_text = "```csv\n" + preview_frame.to_csv(index=False) + "```\n"
        lines.extend(
            [
                "## Replay Preview",
                "",
                preview_text,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
