"""Heuristic scene-axis tagging for checkpoint runtime rows (SA2)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pandas as pd

from backend.services.path_checkpoint_scene_contract import (
    PATH_CHECKPOINT_SCENE_GATE_BLOCK_LEVELS,
    PATH_CHECKPOINT_SCENE_UNRESOLVED_COARSE_FAMILY,
    PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    PATH_CHECKPOINT_SCENE_UNKNOWN_ALIGNMENT,
    PATH_CHECKPOINT_SCENE_UNKNOWN_TRANSITION_SPEED,
    build_default_scene_runtime_payload,
)


PATH_CHECKPOINT_SCENE_TAGGER_CONTRACT_VERSION = "path_checkpoint_scene_tagger_v1"

_EXHAUSTION_MIN_BARS_BY_SYMBOL = {
    "BTCUSD": 10,
    "XAUUSD": 8,
    "NAS100": 8,
}
_TIME_DECAY_MIN_BARS_BY_SYMBOL = {
    "BTCUSD": 30,
    "XAUUSD": 20,
    "NAS100": 15,
}
_ENTRY_INITIATION_SURFACES = {"initial_entry_surface", "follow_through_surface"}
_CONTINUATION_SURFACES = {"follow_through_surface", "continuation_hold_surface"}
_POSITION_MANAGEMENT_SURFACES = {"continuation_hold_surface"}
_DEFENSIVE_EXIT_SURFACES = {"protective_exit_surface"}
_RECLAIM_TYPES = {"FIRST_PULLBACK_CHECK", "RECLAIM_CHECK"}
_LATE_TYPES = {"LATE_TREND_CHECK", "RUNNER_CHECK"}
_ENTRY_CHECK_TYPES = {"INITIAL_PUSH", "FIRST_PULLBACK_CHECK", "RECLAIM_CHECK"}
_REASON_SWEEP_TOKENS = (
    "wrong_side",
    "active_action_conflict_guard",
    "sweep",
    "reclaim",
    "stop_hunt",
)
_REASON_BREAKOUT_TOKENS = (
    "breakout",
    "follow_through",
    "followthrough",
    "reclaim",
    "bridge",
)
_REASON_LATE_TREND_TOKENS = (
    "runner",
    "late",
    "lock",
    "exhaust",
    "partial",
)
_REASON_BALANCED_TOKENS = (
    "balanced_checkpoint_state",
    "wait",
    "timeout",
    "stalled",
)
_GATE_BLOCK_LEVEL_BY_LABEL = {
    "none": "none",
    "low_edge_state": "entry_block",
    "dead_leg_wait": "all_block",
    "ambiguous_structure": "all_block",
}


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


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


def _clamp(value: float) -> float:
    return round(max(0.0, min(0.99, float(value))), 6)


def _normalize_action(value: object) -> str:
    text = _to_text(value).upper()
    if text in {"BUY", "LONG"}:
        return "BUY"
    if text in {"SELL", "SHORT"}:
        return "SELL"
    return ""


def _build_reason_blob(runtime_row: Mapping[str, Any], checkpoint_row: Mapping[str, Any]) -> str:
    return " ".join(
        filter(
            None,
            [
                _to_text(runtime_row.get("blocked_by")).lower(),
                _to_text(runtime_row.get("action_none_reason")).lower(),
                _to_text(runtime_row.get("consumer_check_reason")).lower(),
                _to_text(runtime_row.get("setup_reason")).lower(),
                _to_text(runtime_row.get("entry_candidate_bridge_mode")).lower(),
                _to_text(checkpoint_row.get("runtime_score_reason")).lower(),
                _to_text(checkpoint_row.get("checkpoint_transition_reason")).lower(),
                _to_text(checkpoint_row.get("management_action_reason")).lower(),
            ],
        )
    )


def _extract_previous_scene_state(previous_runtime_row: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(previous_runtime_row or {})
    fine_label = _to_text(
        row.get("checkpoint_runtime_scene_fine_label") or row.get("runtime_scene_fine_label"),
        PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    )
    gate_label = _to_text(
        row.get("checkpoint_runtime_scene_gate_label") or row.get("runtime_scene_gate_label"),
        "none",
    )
    transition_bars = _to_int(
        row.get("checkpoint_runtime_scene_transition_bars")
        if row.get("checkpoint_runtime_scene_transition_bars") not in (None, "")
        else row.get("runtime_scene_transition_bars"),
        0,
    )
    return {
        "fine_label": fine_label,
        "gate_label": gate_label,
        "transition_bars": transition_bars,
    }


def _resolve_confidence_band(confidence: float) -> str:
    if confidence >= 0.80:
        return "high"
    if confidence >= 0.60:
        return "medium"
    return "low"


def _resolve_maturity(
    *,
    confidence: float,
    band: str,
    current_fine_label: str,
    previous_scene: Mapping[str, Any],
) -> str:
    if current_fine_label == PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL:
        return "provisional"
    previous_fine = _to_text(previous_scene.get("fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
    if previous_fine == current_fine_label and confidence >= 0.80:
        return "confirmed"
    if band in {"high", "medium"}:
        return "probable"
    return "provisional"


def _resolve_transition(
    *,
    current_fine_label: str,
    previous_scene: Mapping[str, Any],
) -> tuple[str, int, str]:
    previous_fine = _to_text(previous_scene.get("fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
    previous_bars = _to_int(previous_scene.get("transition_bars"), 0)
    if current_fine_label == PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL:
        return previous_fine, 0, PATH_CHECKPOINT_SCENE_UNKNOWN_TRANSITION_SPEED
    if previous_fine == current_fine_label:
        bars = previous_bars + 1
    else:
        bars = 0
    if bars == 0:
        speed = "fast"
    elif bars <= 2:
        speed = "normal"
    else:
        speed = "slow"
    return previous_fine, bars, speed


def _resolve_family_alignment(surface_name: str, coarse_family: str, gate_label: str) -> str:
    surface = _to_text(surface_name).lower()
    coarse = _to_text(coarse_family)
    if gate_label != "none" and coarse == PATH_CHECKPOINT_SCENE_UNRESOLVED_COARSE_FAMILY:
        return PATH_CHECKPOINT_SCENE_UNKNOWN_ALIGNMENT
    if coarse == "ENTRY_INITIATION":
        if surface in _ENTRY_INITIATION_SURFACES:
            return "aligned"
        if surface == "continuation_hold_surface":
            return "downgrade"
        if surface == "protective_exit_surface":
            return "conflict"
    if coarse == "CONTINUATION":
        if surface in _CONTINUATION_SURFACES:
            return "aligned"
        if surface == "protective_exit_surface":
            return "downgrade"
    if coarse == "POSITION_MANAGEMENT":
        if surface in _POSITION_MANAGEMENT_SURFACES:
            return "aligned"
        if surface == "protective_exit_surface":
            return "downgrade"
    if coarse == "DEFENSIVE_EXIT":
        if surface in _DEFENSIVE_EXIT_SURFACES:
            return "aligned"
        if surface in _ENTRY_INITIATION_SURFACES | _POSITION_MANAGEMENT_SURFACES:
            return "upgrade"
    if coarse == "NO_TRADE":
        return "aligned"
    return PATH_CHECKPOINT_SCENE_UNKNOWN_ALIGNMENT


def _resolve_action_bias_strength(
    *,
    fine_label: str,
    gate_label: str,
    band: str,
    maturity: str,
    alignment: str,
) -> str:
    if alignment == "conflict":
        return "none"
    if gate_label != "none":
        if band == "high":
            return "hard"
        if band == "medium":
            return "medium"
        return "soft"
    if fine_label in {"trend_exhaustion", "time_decay_risk"}:
        if maturity == "confirmed" and band == "high":
            return "hard"
        if band in {"high", "medium"}:
            return "medium"
        return "soft"
    if fine_label in {"breakout_retest_hold", "liquidity_sweep_reclaim"}:
        if alignment == "downgrade":
            return "soft"
        if band in {"high", "medium"}:
            return "medium"
        return "soft"
    return "none"


def _candidate_trend_exhaustion(features: Mapping[str, Any]) -> dict[str, Any] | None:
    symbol = _to_text(features.get("symbol")).upper()
    checkpoint_type = _to_text(features.get("checkpoint_type")).upper()
    if checkpoint_type not in _LATE_TYPES:
        return None
    bars_since_leg_start = _to_int(features.get("bars_since_leg_start"), 0)
    threshold = _EXHAUSTION_MIN_BARS_BY_SYMBOL.get(symbol, 8)
    if bars_since_leg_start < threshold:
        return None
    position_side = _to_text(features.get("position_side")).upper()
    pnl_state = _to_text(features.get("unrealized_pnl_state")).upper()
    partial_exit = _to_float(features.get("partial_exit"), 0.0)
    hold_quality = _to_float(features.get("hold_quality"), 0.0)
    continuation = _to_float(features.get("continuation"), 0.0)
    reversal = _to_float(features.get("reversal"), 0.0)
    full_exit = _to_float(features.get("full_exit"), 0.0)
    giveback_ratio = _to_float(features.get("giveback_ratio"), 0.0)
    current_profit = _to_float(features.get("current_profit"), 0.0)
    mfe_since_entry = _to_float(features.get("mfe_since_entry"), 0.0)
    runner_secured = _to_bool(features.get("runner_secured"), False)
    reason_blob = _to_text(features.get("reason_blob")).lower()
    if position_side == "FLAT":
        return None
    if pnl_state == "OPEN_LOSS":
        return None
    if not (pnl_state == "OPEN_PROFIT" or runner_secured):
        return None
    if partial_exit < max(0.60, hold_quality + 0.02):
        return None
    if continuation < reversal - 0.02:
        return None
    if full_exit >= 0.74:
        return None
    delta = continuation - reversal
    healthy_runner = (
        runner_secured
        and continuation >= 0.885
        and reversal <= 0.49
        and giveback_ratio <= 0.12
        and current_profit >= max(0.20, mfe_since_entry - 0.08)
    )
    if healthy_runner:
        return None
    late_pressure = (
        giveback_ratio >= 0.18
        or reversal >= 0.52
        or delta <= 0.20
        or (
            giveback_ratio >= 0.12
            and any(token in reason_blob for token in _REASON_LATE_TREND_TOKENS)
        )
    )
    if not late_pressure:
        return None
    if continuation > 0.90 and giveback_ratio < 0.12 and reversal < 0.52:
        return None
    confidence = 0.58
    if bars_since_leg_start >= threshold + 2:
        confidence += 0.08
    if partial_exit >= 0.64:
        confidence += 0.08
    if giveback_ratio >= 0.25:
        confidence += 0.08
    if reversal >= 0.58:
        confidence += 0.08
    if delta <= 0.18:
        confidence += 0.06
    if runner_secured:
        confidence += 0.04
    return {
        "coarse_family": "DEFENSIVE_EXIT",
        "fine_label": "trend_exhaustion",
        "confidence": _clamp(confidence),
        "modifier": {"late_trend": True},
        "reason": "heuristic_trend_exhaustion",
    }


def _candidate_time_decay_risk(features: Mapping[str, Any]) -> dict[str, Any] | None:
    symbol = _to_text(features.get("symbol")).upper()
    checkpoint_type = _to_text(features.get("checkpoint_type")).upper()
    if checkpoint_type not in _LATE_TYPES:
        return None
    bars_since_leg_start = _to_int(features.get("bars_since_leg_start"), 0)
    threshold = _TIME_DECAY_MIN_BARS_BY_SYMBOL.get(symbol, 20)
    if bars_since_leg_start < threshold:
        return None
    pnl_state = _to_text(features.get("unrealized_pnl_state")).upper()
    runner_secured = _to_bool(features.get("runner_secured"), False)
    hold_quality = _to_float(features.get("hold_quality"), 0.0)
    partial_exit = _to_float(features.get("partial_exit"), 0.0)
    continuation = _to_float(features.get("continuation"), 0.0)
    current_profit = abs(_to_float(features.get("current_profit"), 0.0))
    mfe_since_entry = _to_float(features.get("mfe_since_entry"), 0.0)
    mae_since_entry = _to_float(features.get("mae_since_entry"), 0.0)
    giveback_ratio = _to_float(features.get("giveback_ratio"), 0.0)
    reason_blob = _to_text(features.get("reason_blob")).lower()
    if pnl_state not in {"FLAT", "OPEN_PROFIT"}:
        return None
    if runner_secured:
        return None
    small_motion = pnl_state == "FLAT" or (
        current_profit <= 0.12 and max(mfe_since_entry, mae_since_entry) <= 0.30
    )
    if not small_motion:
        return None
    if hold_quality > 0.42:
        return None
    if partial_exit > 0.50:
        return None
    if continuation > 0.60:
        return None
    if pnl_state == "OPEN_PROFIT" and giveback_ratio < 0.35:
        return None
    if not (pnl_state == "FLAT" or any(token in reason_blob for token in _REASON_BALANCED_TOKENS)):
        return None
    confidence = 0.56
    if bars_since_leg_start >= threshold + 3:
        confidence += 0.10
    if pnl_state == "FLAT":
        confidence += 0.08
    if hold_quality <= 0.30:
        confidence += 0.06
    return {
        "coarse_family": "POSITION_MANAGEMENT",
        "fine_label": "time_decay_risk",
        "confidence": _clamp(confidence),
        "modifier": {},
        "reason": "heuristic_time_decay_risk",
    }


def _candidate_liquidity_sweep_reclaim(features: Mapping[str, Any]) -> dict[str, Any] | None:
    checkpoint_type = _to_text(features.get("checkpoint_type")).upper()
    if checkpoint_type not in _RECLAIM_TYPES:
        return None
    reason_blob = _to_text(features.get("reason_blob")).lower()
    continuation = _to_float(features.get("continuation"), 0.0)
    reversal = _to_float(features.get("reversal"), 0.0)
    observe_action = _normalize_action(features.get("observe_action"))
    observe_side = _normalize_action(features.get("observe_side"))
    leg_action = _normalize_action(features.get("leg_action"))
    if not any(token in reason_blob for token in _REASON_SWEEP_TOKENS):
        return None
    if continuation < 0.62:
        return None
    if reversal > 0.52:
        return None
    if leg_action and observe_action and observe_action not in {"", leg_action} and observe_side not in {"", leg_action}:
        return None
    confidence = 0.58
    if "wrong_side" in reason_blob or "active_action_conflict_guard" in reason_blob:
        confidence += 0.14
    if checkpoint_type == "RECLAIM_CHECK":
        confidence += 0.10
    if continuation >= 0.72:
        confidence += 0.08
    return {
        "coarse_family": "ENTRY_INITIATION",
        "fine_label": "liquidity_sweep_reclaim",
        "confidence": _clamp(confidence),
        "modifier": {"reclaim": True},
        "reason": "heuristic_liquidity_sweep_reclaim",
    }


def _candidate_breakout_retest_hold(features: Mapping[str, Any]) -> dict[str, Any] | None:
    checkpoint_type = _to_text(features.get("checkpoint_type")).upper()
    surface_name = _to_text(features.get("surface_name")).lower()
    if checkpoint_type not in _RECLAIM_TYPES:
        return None
    if surface_name not in {"follow_through_surface", "continuation_hold_surface"}:
        return None
    continuation = _to_float(features.get("continuation"), 0.0)
    reversal = _to_float(features.get("reversal"), 0.0)
    hold_quality = _to_float(features.get("hold_quality"), 0.0)
    reason_blob = _to_text(features.get("reason_blob")).lower()
    if continuation < 0.60:
        return None
    if hold_quality < 0.38:
        return None
    reason_support = (
        reversal <= continuation - 0.04
        or any(token in reason_blob for token in _REASON_BREAKOUT_TOKENS)
        or "continuation_hold_bias" in reason_blob
    )
    if not reason_support:
        return None
    confidence = 0.56
    if checkpoint_type == "RECLAIM_CHECK":
        confidence += 0.10
    if any(token in reason_blob for token in ("breakout", "reclaim")):
        confidence += 0.10
    if continuation >= 0.70:
        confidence += 0.08
    modifier = {"reclaim": True} if checkpoint_type == "RECLAIM_CHECK" else {"retest_clean": True}
    return {
        "coarse_family": "ENTRY_INITIATION",
        "fine_label": "breakout_retest_hold",
        "confidence": _clamp(confidence),
        "modifier": modifier,
        "reason": "heuristic_breakout_retest_hold",
    }


def _candidate_low_edge_gate(features: Mapping[str, Any]) -> dict[str, Any] | None:
    checkpoint_type = _to_text(features.get("checkpoint_type")).upper()
    surface_name = _to_text(features.get("surface_name")).lower()
    position_side = _to_text(features.get("position_side")).upper()
    continuation = _to_float(features.get("continuation"), 0.0)
    reversal = _to_float(features.get("reversal"), 0.0)
    hold_quality = _to_float(features.get("hold_quality"), 0.0)
    partial_exit = _to_float(features.get("partial_exit"), 0.0)
    full_exit = _to_float(features.get("full_exit"), 0.0)
    rebuy = _to_float(features.get("rebuy"), 0.0)
    reason_blob = _to_text(features.get("reason_blob")).lower()
    if checkpoint_type not in _ENTRY_CHECK_TYPES:
        return None
    if surface_name not in {"initial_entry_surface", "follow_through_surface", "continuation_hold_surface"}:
        return None
    max_signal = max(continuation, reversal, hold_quality, partial_exit, full_exit, rebuy)
    spread = abs(continuation - reversal)
    if spread > 0.10:
        return None
    if max_signal > 0.68:
        return None
    if full_exit >= 0.70 or rebuy >= 0.66:
        return None
    confidence = 0.58
    if position_side == "FLAT":
        confidence += 0.06
    if max_signal <= 0.56:
        confidence += 0.08
    if checkpoint_type in {"FIRST_PULLBACK_CHECK", "RECLAIM_CHECK"}:
        confidence += 0.06
    if "balanced_checkpoint_state" in reason_blob:
        confidence += 0.06
    return {
        "gate_label": "low_edge_state",
        "confidence": _clamp(confidence),
        "reason": "heuristic_low_edge_state",
    }


def _select_fine_scene(features: Mapping[str, Any]) -> dict[str, Any] | None:
    candidates = [
        candidate
        for candidate in (
            _candidate_liquidity_sweep_reclaim(features),
            _candidate_breakout_retest_hold(features),
            _candidate_trend_exhaustion(features),
            _candidate_time_decay_risk(features),
        )
        if candidate
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            _to_float(item.get("confidence"), 0.0),
            1 if item.get("fine_label") == "liquidity_sweep_reclaim" else 0,
        ),
    )


def _select_gate(features: Mapping[str, Any]) -> dict[str, Any] | None:
    return _candidate_low_edge_gate(features)


def _build_feature_map(
    *,
    symbol: str,
    runtime_row: Mapping[str, Any],
    checkpoint_row: Mapping[str, Any],
    position_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    position = dict(position_state or {})
    leg_direction = _to_text(checkpoint_row.get("leg_direction") or runtime_row.get("leg_direction")).upper()
    leg_action = "BUY" if leg_direction == "UP" else ("SELL" if leg_direction == "DOWN" else "")
    return {
        "symbol": _to_text(symbol or checkpoint_row.get("symbol") or runtime_row.get("symbol")).upper(),
        "surface_name": _to_text(checkpoint_row.get("surface_name")).lower(),
        "source": _to_text(checkpoint_row.get("source") or runtime_row.get("source")).lower(),
        "checkpoint_type": _to_text(checkpoint_row.get("checkpoint_type")).upper(),
        "bars_since_leg_start": _to_int(checkpoint_row.get("bars_since_leg_start"), 0),
        "bars_since_last_push": _to_int(checkpoint_row.get("bars_since_last_push"), 0),
        "bars_since_last_checkpoint": _to_int(checkpoint_row.get("bars_since_last_checkpoint"), 0),
        "position_side": _to_text(checkpoint_row.get("position_side") or position.get("position_side")).upper(),
        "position_size_fraction": _to_float(checkpoint_row.get("position_size_fraction"), position.get("position_size_fraction", 0.0)),
        "unrealized_pnl_state": _to_text(checkpoint_row.get("unrealized_pnl_state") or position.get("unrealized_pnl_state")).upper(),
        "runner_secured": _to_bool(checkpoint_row.get("runner_secured"), _to_bool(position.get("runner_secured"), False)),
        "current_profit": _to_float(checkpoint_row.get("current_profit"), position.get("current_profit", 0.0)),
        "mfe_since_entry": _to_float(checkpoint_row.get("mfe_since_entry"), position.get("mfe_since_entry", 0.0)),
        "mae_since_entry": _to_float(checkpoint_row.get("mae_since_entry"), position.get("mae_since_entry", 0.0)),
        "giveback_from_peak": _to_float(checkpoint_row.get("giveback_from_peak"), 0.0),
        "giveback_ratio": _to_float(checkpoint_row.get("giveback_ratio"), 0.0),
        "checkpoint_rule_family_hint": _to_text(checkpoint_row.get("checkpoint_rule_family_hint")).lower(),
        "exit_stage_family": _to_text(checkpoint_row.get("exit_stage_family")).lower(),
        "continuation": _to_float(checkpoint_row.get("runtime_continuation_odds"), 0.0),
        "reversal": _to_float(checkpoint_row.get("runtime_reversal_odds"), 0.0),
        "hold_quality": _to_float(checkpoint_row.get("runtime_hold_quality_score"), 0.0),
        "partial_exit": _to_float(checkpoint_row.get("runtime_partial_exit_ev"), 0.0),
        "full_exit": _to_float(checkpoint_row.get("runtime_full_exit_risk"), 0.0),
        "rebuy": _to_float(checkpoint_row.get("runtime_rebuy_readiness"), 0.0),
        "observe_action": _to_text(runtime_row.get("observe_action")),
        "observe_side": _to_text(runtime_row.get("observe_side")),
        "leg_action": leg_action,
        "reason_blob": _build_reason_blob(runtime_row, checkpoint_row),
    }


def tag_runtime_scene(
    *,
    symbol: str,
    runtime_row: Mapping[str, Any] | None,
    checkpoint_row: Mapping[str, Any] | None,
    symbol_state: Mapping[str, Any] | None = None,
    position_state: Mapping[str, Any] | None = None,
    previous_runtime_row: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _ = dict(symbol_state or {})
    row = dict(runtime_row or {})
    checkpoint = dict(checkpoint_row or {})
    previous_scene = _extract_previous_scene_state(previous_runtime_row)

    merged_scene_overrides = {}
    for payload in (row, checkpoint):
        for key in build_default_scene_runtime_payload().keys():
            if key in payload:
                merged_scene_overrides[key] = payload.get(key)
    base_payload = build_default_scene_runtime_payload(merged_scene_overrides)
    explicit_scene_present = (
        base_payload.get("runtime_scene_source") not in {"", "schema_only"}
        and (
            base_payload.get("runtime_scene_fine_label") != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
            or base_payload.get("runtime_scene_gate_label") != "none"
        )
    )
    if explicit_scene_present:
        return {
            "contract_version": PATH_CHECKPOINT_SCENE_TAGGER_CONTRACT_VERSION,
            "row": base_payload,
            "detail": {
                "contract_version": PATH_CHECKPOINT_SCENE_TAGGER_CONTRACT_VERSION,
                "mode": "passthrough_existing_scene_payload",
                "selected_scene": dict(base_payload),
                "previous_scene": dict(previous_scene),
            },
        }

    features = _build_feature_map(
        symbol=str(symbol),
        runtime_row=row,
        checkpoint_row=checkpoint,
        position_state=position_state,
    )
    fine_candidate = _select_fine_scene(features)
    gate_candidate = _select_gate(features)

    payload = build_default_scene_runtime_payload()
    if fine_candidate:
        payload["runtime_scene_coarse_family"] = _to_text(
            fine_candidate.get("coarse_family"),
            PATH_CHECKPOINT_SCENE_UNRESOLVED_COARSE_FAMILY,
        )
        payload["runtime_scene_fine_label"] = _to_text(
            fine_candidate.get("fine_label"),
            PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
        )
        payload["runtime_scene_modifier_json"] = json.dumps(
            dict(fine_candidate.get("modifier") or {}),
            ensure_ascii=False,
            sort_keys=True,
        )
        payload["runtime_scene_confidence"] = _clamp(fine_candidate.get("confidence", 0.0))
        payload["runtime_scene_source"] = "heuristic_v1"
    if gate_candidate:
        gate_confidence = _to_float(gate_candidate.get("confidence"), 0.0)
        current_confidence = _to_float(payload.get("runtime_scene_confidence"), 0.0)
        payload["runtime_scene_gate_label"] = _to_text(gate_candidate.get("gate_label"), "none")
        payload["runtime_scene_gate_block_level"] = _GATE_BLOCK_LEVEL_BY_LABEL.get(payload["runtime_scene_gate_label"], "none")
        payload["runtime_scene_source"] = "heuristic_v1"
        if not fine_candidate:
            payload["runtime_scene_confidence"] = _clamp(gate_confidence)
        else:
            payload["runtime_scene_confidence"] = _clamp(max(current_confidence, gate_confidence))

    band = _resolve_confidence_band(_to_float(payload.get("runtime_scene_confidence"), 0.0))
    payload["runtime_scene_confidence_band"] = band
    maturity = _resolve_maturity(
        confidence=_to_float(payload.get("runtime_scene_confidence"), 0.0),
        band=band,
        current_fine_label=_to_text(payload.get("runtime_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL),
        previous_scene=previous_scene,
    )
    payload["runtime_scene_maturity"] = maturity
    transition_from, transition_bars, transition_speed = _resolve_transition(
        current_fine_label=_to_text(payload.get("runtime_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL),
        previous_scene=previous_scene,
    )
    payload["runtime_scene_transition_from"] = transition_from
    payload["runtime_scene_transition_bars"] = transition_bars
    payload["runtime_scene_transition_speed"] = transition_speed
    alignment = _resolve_family_alignment(
        _to_text(checkpoint.get("surface_name")),
        _to_text(payload.get("runtime_scene_coarse_family")),
        _to_text(payload.get("runtime_scene_gate_label"), "none"),
    )
    payload["runtime_scene_family_alignment"] = alignment
    payload["runtime_scene_action_bias_strength"] = _resolve_action_bias_strength(
        fine_label=_to_text(payload.get("runtime_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL),
        gate_label=_to_text(payload.get("runtime_scene_gate_label"), "none"),
        band=band,
        maturity=maturity,
        alignment=alignment,
    )
    if _to_text(payload.get("runtime_scene_gate_block_level"), "none") not in PATH_CHECKPOINT_SCENE_GATE_BLOCK_LEVELS:
        payload["runtime_scene_gate_block_level"] = "none"

    detail = {
        "contract_version": PATH_CHECKPOINT_SCENE_TAGGER_CONTRACT_VERSION,
        "mode": "heuristic_v1",
        "features": dict(features),
        "previous_scene": dict(previous_scene),
        "selected_fine_candidate": dict(fine_candidate or {}),
        "selected_gate_candidate": dict(gate_candidate or {}),
        "row": dict(payload),
    }
    return {
        "contract_version": PATH_CHECKPOINT_SCENE_TAGGER_CONTRACT_VERSION,
        "row": payload,
        "detail": detail,
    }
