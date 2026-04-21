from __future__ import annotations

import json
from typing import Any, Mapping


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
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
    if isinstance(parsed, Mapping):
        return dict(parsed)
    return {}


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return int(default)


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = _safe_str(value).lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return bool(text)


def _infer_side_from_text(*values: Any) -> str:
    joined = " ".join(_safe_str(value).lower() for value in values if _safe_str(value))
    if not joined:
        return ""
    buy_tokens = (" buy", "buy_", "_buy", "lower", "support", "rebound", "long")
    sell_tokens = (" sell", "sell_", "_sell", "upper", "reject", "short", "breakdown")
    buy_hit = any(token in f" {joined} " for token in buy_tokens)
    sell_hit = any(token in f" {joined} " for token in sell_tokens)
    if buy_hit and not sell_hit:
        return "BUY"
    if sell_hit and not buy_hit:
        return "SELL"
    return ""


def _resolve_position_parts(row: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = row if isinstance(row, Mapping) else {}
    current_context = _coerce_mapping(payload.get("current_entry_context_v1"))
    metadata = _coerce_mapping(current_context.get("metadata"))

    position_snapshot = _coerce_mapping(payload.get("position_snapshot_v2"))
    zones = (
        _coerce_mapping(position_snapshot.get("zones"))
        or _coerce_mapping(payload.get("position_zones_v2"))
        or _coerce_mapping(metadata.get("position_zones_v2"))
    )
    interpretation = (
        _coerce_mapping(position_snapshot.get("interpretation"))
        or _coerce_mapping(payload.get("position_interpretation_v2"))
        or _coerce_mapping(metadata.get("position_interpretation_v2"))
    )
    energy = (
        _coerce_mapping(position_snapshot.get("energy"))
        or _coerce_mapping(payload.get("position_energy_v2"))
        or _coerce_mapping(metadata.get("position_energy_v2"))
    )
    vector = (
        _coerce_mapping(position_snapshot.get("vector"))
        or _coerce_mapping(payload.get("position_vector_v2"))
        or _coerce_mapping(metadata.get("position_vector_v2"))
    )
    response = _coerce_mapping(payload.get("response_vector_v2")) or _coerce_mapping(metadata.get("response_vector_v2"))
    state = _coerce_mapping(payload.get("state_vector_v2")) or _coerce_mapping(metadata.get("state_vector_v2"))
    return current_context, metadata, zones, interpretation, energy, vector, response or state


def _resolve_observe_parts(row: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any], str, str, str, str, str]:
    payload = row if isinstance(row, Mapping) else {}
    current_context = _coerce_mapping(payload.get("current_entry_context_v1"))
    metadata = _coerce_mapping(current_context.get("metadata"))
    entry_decision_result = _coerce_mapping(payload.get("entry_decision_result_v1"))
    entry_result_metrics = _coerce_mapping(entry_decision_result.get("metrics"))
    observe = (
        _coerce_mapping(payload.get("observe_confirm_v2"))
        or _coerce_mapping(metadata.get("observe_confirm_v2"))
        or _coerce_mapping(payload.get("observe_confirm_v1"))
        or _coerce_mapping(metadata.get("observe_confirm_v1"))
    )
    observe_metadata = _coerce_mapping(observe.get("metadata"))
    observe_action = _safe_str(payload.get("observe_action") or observe.get("action")).upper()
    observe_side = _safe_str(payload.get("observe_side") or observe.get("side")).upper()
    observe_reason = _safe_str(
        payload.get("observe_reason") or observe.get("reason") or entry_result_metrics.get("observe_reason")
    )
    blocked_by = _safe_str(
        payload.get("blocked_by")
        or observe_metadata.get("blocked_guard")
        or observe_metadata.get("blocked_reason")
        or entry_decision_result.get("blocked_by")
    )
    action_none_reason = _safe_str(payload.get("action_none_reason") or entry_result_metrics.get("action_none_reason"))
    if not observe_side:
        observe_side = (
            _safe_str(payload.get("next_action_hint")).upper()
            if _safe_str(payload.get("next_action_hint")).upper() in {"BUY", "SELL"}
            else _infer_side_from_text(observe_reason, blocked_by, payload.get("box_state"), payload.get("bb_state"))
        )
    return observe, observe_metadata, observe_action, observe_side, observe_reason, blocked_by, action_none_reason


def _resolve_energy_bias(lower_force: float, upper_force: float, middle_neutrality: float) -> str:
    if middle_neutrality >= max(lower_force, upper_force) and middle_neutrality >= 0.45:
        return "MIDDLE"
    if lower_force >= upper_force + 0.05:
        return "LOWER"
    if upper_force >= lower_force + 0.05:
        return "UPPER"
    return "BALANCED"


def _resolve_execution_bias(observe_action: str, observe_side: str, next_action_hint: str) -> str:
    if observe_action in {"BUY", "SELL"}:
        return observe_action
    if observe_action == "WAIT" and observe_side in {"BUY", "SELL"}:
        return f"WAIT_{observe_side}"
    hint = _safe_str(next_action_hint).upper()
    if hint in {"BUY", "SELL", "BOTH", "HOLD"}:
        return hint
    return "WAIT"


def _resolve_decision_state(
    *,
    is_active: bool,
    display_ready: bool,
    entry_ready: bool,
    consumer_stage: str,
    blocked_by: str,
    observe_action: str,
    wait_policy_state: str,
) -> str:
    if not is_active:
        return "INACTIVE"
    if entry_ready or consumer_stage == "READY":
        return "ENTRY_READY"
    if blocked_by or consumer_stage == "BLOCKED":
        return "BLOCKED"
    if observe_action == "WAIT" or wait_policy_state or consumer_stage in {"OBSERVE", "PROBE"}:
        return "WAIT"
    if display_ready:
        return "DISPLAY_READY"
    return "MONITOR"


def build_legacy_raw_score_surface_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = row if isinstance(row, Mapping) else {}
    buy_score = _safe_int(payload.get("buy_score"))
    sell_score = _safe_int(payload.get("sell_score"))
    wait_score = _safe_int(payload.get("wait_score"))
    entry_threshold = _safe_int(
        payload.get("effective_entry_threshold")
        or payload.get("base_entry_threshold")
        or payload.get("entry_threshold")
    )
    exit_threshold = _safe_int(payload.get("exit_threshold"))
    dominant_side = "BUY" if buy_score > sell_score else ("SELL" if sell_score > buy_score else "BALANCED")
    dominant_score = max(buy_score, sell_score)
    threshold_gap = int(dominant_score - entry_threshold)
    threshold_state = "READY" if dominant_score >= entry_threshold and dominant_side in {"BUY", "SELL"} else "BELOW"
    return {
        "contract_version": "legacy_raw_score_surface_v1",
        "buy_score": int(buy_score),
        "sell_score": int(sell_score),
        "wait_score": int(wait_score),
        "entry_threshold": int(entry_threshold),
        "exit_threshold": int(exit_threshold),
        "next_action_hint": _safe_str(payload.get("next_action_hint")).upper(),
        "summary": {
            "dominant_side": dominant_side,
            "dominant_score": int(dominant_score),
            "lead_gap": int(abs(buy_score - sell_score)),
            "threshold_gap": int(threshold_gap),
            "threshold_state": threshold_state,
        },
    }


def build_position_energy_surface_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = row if isinstance(row, Mapping) else {}
    _, metadata, zones, interpretation, energy, vector, response = _resolve_position_parts(payload)
    _, _, observe_action, observe_side, observe_reason, blocked_by, action_none_reason = _resolve_observe_parts(payload)

    lower_force = _safe_float(energy.get("lower_position_force"))
    upper_force = _safe_float(energy.get("upper_position_force"))
    middle_neutrality = _safe_float(energy.get("middle_neutrality"))
    display_ready = _safe_bool(payload.get("consumer_check_display_ready"))
    entry_ready = _safe_bool(payload.get("consumer_check_entry_ready"))
    consumer_stage = _safe_str(payload.get("consumer_check_stage")).upper()
    wait_policy_state = _safe_str(payload.get("wait_policy_state") or payload.get("entry_wait_state")).upper()
    wait_policy_reason = _safe_str(payload.get("wait_policy_reason") or payload.get("entry_wait_reason"))
    energy_bias = _resolve_energy_bias(lower_force, upper_force, middle_neutrality)
    execution_bias = _resolve_execution_bias(observe_action, observe_side, payload.get("next_action_hint"))
    is_active = _safe_bool(payload.get("is_active", True))
    decision_state = _resolve_decision_state(
        is_active=is_active,
        display_ready=display_ready,
        entry_ready=entry_ready,
        consumer_stage=consumer_stage,
        blocked_by=blocked_by,
        observe_action=observe_action,
        wait_policy_state=wait_policy_state,
    )

    location_code = " / ".join(
        filter(
            None,
            [
                f"BOX:{_safe_str(zones.get('box_zone')).upper()}",
                f"BB20:{_safe_str(zones.get('bb20_zone')).upper()}",
                f"BB44:{_safe_str(zones.get('bb44_zone')).upper()}",
            ],
        )
    )
    position_code = _safe_str(interpretation.get("conflict_kind") or interpretation.get("primary_label")).upper()
    state_reason = blocked_by or action_none_reason or wait_policy_reason or observe_reason or _safe_str(payload.get("inactive_reason"))

    return {
        "contract_version": "position_energy_surface_v1",
        "market_mode": _safe_str(payload.get("market_mode") or metadata.get("market_mode")).upper(),
        "direction_policy": _safe_str(payload.get("direction_policy")).upper(),
        "liquidity_state": _safe_str(payload.get("liquidity_state") or metadata.get("liquidity_state")).upper(),
        "box_state": _safe_str(payload.get("box_state")).upper(),
        "bb_state": _safe_str(payload.get("bb_state")).upper(),
        "location": {
            "box_zone": _safe_str(zones.get("box_zone")).upper(),
            "bb20_zone": _safe_str(zones.get("bb20_zone")).upper(),
            "bb44_zone": _safe_str(zones.get("bb44_zone")).upper(),
            "x_box": _safe_float(vector.get("x_box")),
            "x_bb20": _safe_float(vector.get("x_bb20")),
            "x_bb44": _safe_float(vector.get("x_bb44")),
        },
        "position": {
            "primary_label": _safe_str(interpretation.get("primary_label")).upper(),
            "bias_label": _safe_str(interpretation.get("bias_label")).upper(),
            "conflict_kind": _safe_str(interpretation.get("conflict_kind")).upper(),
        },
        "energy": {
            "lower_position_force": lower_force,
            "upper_position_force": upper_force,
            "middle_neutrality": middle_neutrality,
        },
        "response": {
            "lower_hold_up": _safe_float(response.get("lower_hold_up")),
            "upper_reject_down": _safe_float(response.get("upper_reject_down")),
            "breakout_up": _safe_float(response.get("breakout_up")),
            "breakout_down": _safe_float(response.get("breakout_down")),
        },
        "observe": {
            "action": observe_action,
            "side": observe_side,
            "reason": observe_reason,
            "blocked_by": blocked_by,
            "action_none_reason": action_none_reason,
        },
        "readiness": {
            "display_ready": display_ready,
            "entry_ready": entry_ready,
            "consumer_stage": consumer_stage,
            "consumer_reason": _safe_str(payload.get("consumer_check_reason")),
            "wait_policy_state": wait_policy_state,
            "wait_policy_reason": wait_policy_reason,
            "wait_probe_scene_id": _safe_str(payload.get("wait_probe_scene_id")),
            "wait_probe_ready_for_entry": _safe_bool(payload.get("wait_probe_ready_for_entry")),
        },
        "summary": {
            "decision_state": decision_state,
            "energy_bias": energy_bias,
            "execution_bias": execution_bias,
            "location_code": location_code,
            "position_code": position_code,
            "state_reason": state_reason,
        },
    }


def enrich_runtime_signal_surface_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    payload["legacy_raw_score_v1"] = build_legacy_raw_score_surface_v1(payload)
    payload["position_energy_surface_v1"] = build_position_energy_surface_v1(payload)
    return payload
