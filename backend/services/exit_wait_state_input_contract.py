"""Shared input contract helpers for exit wait-state construction."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.core.config import Config
from backend.services.exit_manage_context_contract import (
    build_exit_manage_context_v1,
    compact_exit_manage_context_v1,
)
from backend.services.exit_profile_router import resolve_recovery_policy


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _extract_state_vector_v2(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    return _as_mapping(payload_map.get("state_vector_v2", payload_map.get("state_vector_effective_v1", {})))


def _extract_belief_state_v1(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    return _as_mapping(payload_map.get("belief_state_v1", payload_map.get("belief_state_effective_v1", {})))


def _extract_state_v2_meta(payload: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    state_vector_v2 = _extract_state_vector_v2(payload)
    return state_vector_v2, _as_mapping(state_vector_v2.get("metadata"))


def resolve_exit_state_execution_bias_v1(
    payload: Mapping[str, Any] | None = None,
    *,
    entry_direction: str = "",
) -> dict[str, Any]:
    state_vector_v2, state_meta = _extract_state_v2_meta(payload)
    if not state_vector_v2:
        return {
            "prefer_hold_through_green": False,
            "prefer_fast_cut": False,
            "hold_bias": 0.0,
            "wait_bias": 0.0,
            "exit_pressure": 0.0,
            "aligned_with_entry": False,
            "countertrend_with_entry": False,
            "topdown_state_label": "",
            "patience_state_label": "",
            "execution_friction_state": "",
            "session_exhaustion_state": "",
            "event_risk_state": "",
        }

    wait_gain = _to_float(state_vector_v2.get("wait_patience_gain", 1.0), 1.0)
    hold_gain = _to_float(state_vector_v2.get("hold_patience_gain", 1.0), 1.0)
    fast_exit_risk = _to_float(state_vector_v2.get("fast_exit_risk_penalty", 0.0), 0.0)
    topdown_state_label = _to_str(state_meta.get("topdown_state_label", "")).upper()
    patience_state_label = _to_str(state_meta.get("patience_state_label", "")).upper()
    execution_friction_state = _to_str(state_meta.get("execution_friction_state", "")).upper()
    session_exhaustion_state = _to_str(state_meta.get("session_exhaustion_state", "")).upper()
    event_risk_state = _to_str(state_meta.get("event_risk_state", "")).upper()
    entry_side = _to_str(entry_direction, "").upper()

    aligned_with_entry = bool(
        (entry_side == "BUY" and topdown_state_label == "BULL_CONFLUENCE")
        or (entry_side == "SELL" and topdown_state_label == "BEAR_CONFLUENCE")
    )
    countertrend_with_entry = bool(
        (entry_side == "BUY" and topdown_state_label == "BEAR_CONFLUENCE")
        or (entry_side == "SELL" and topdown_state_label == "BULL_CONFLUENCE")
        or topdown_state_label == "TOPDOWN_CONFLICT"
    )
    hold_bias = max(0.0, (hold_gain - 1.0) * 0.34)
    wait_bias = max(0.0, (wait_gain - 1.0) * 0.28)
    exit_pressure = max(0.0, fast_exit_risk * 0.28)

    if patience_state_label == "HOLD_FAVOR":
        hold_bias += 0.10
        wait_bias += 0.04
    elif patience_state_label == "WAIT_FAVOR":
        wait_bias += 0.08
    elif patience_state_label == "FAST_EXIT_FAVOR":
        hold_bias = max(0.0, hold_bias - 0.08)
        wait_bias = max(0.0, wait_bias - 0.05)
        exit_pressure += 0.14

    if aligned_with_entry:
        hold_bias += 0.05
    if countertrend_with_entry:
        exit_pressure += 0.12

    if execution_friction_state == "HIGH_FRICTION":
        exit_pressure += 0.08
        wait_bias = max(0.0, wait_bias - 0.03)
    elif execution_friction_state == "LOW_FRICTION":
        hold_bias += 0.02

    if session_exhaustion_state == "HIGH_EXHAUSTION_RISK":
        exit_pressure += 0.08
        hold_bias = max(0.0, hold_bias - 0.03)
    elif session_exhaustion_state == "LOW_EXHAUSTION_RISK":
        hold_bias += 0.02

    if event_risk_state == "HIGH_EVENT_RISK":
        exit_pressure += 0.10
        wait_bias = max(0.0, wait_bias - 0.02)
    elif event_risk_state == "LOW_EVENT_RISK":
        hold_bias += 0.01

    prefer_hold_through_green = bool(
        hold_bias >= 0.12 and exit_pressure <= 0.16 and not countertrend_with_entry
    )
    prefer_fast_cut = bool(
        exit_pressure >= 0.18
        or (
            countertrend_with_entry
            and (fast_exit_risk >= 0.45 or patience_state_label == "FAST_EXIT_FAVOR")
        )
    )

    return {
        "prefer_hold_through_green": bool(prefer_hold_through_green),
        "prefer_fast_cut": bool(prefer_fast_cut),
        "hold_bias": round(float(hold_bias), 6),
        "wait_bias": round(float(wait_bias), 6),
        "exit_pressure": round(float(exit_pressure), 6),
        "aligned_with_entry": bool(aligned_with_entry),
        "countertrend_with_entry": bool(countertrend_with_entry),
        "topdown_state_label": str(topdown_state_label),
        "patience_state_label": str(patience_state_label),
        "execution_friction_state": str(execution_friction_state),
        "session_exhaustion_state": str(session_exhaustion_state),
        "event_risk_state": str(event_risk_state),
    }


def build_exit_wait_state_input_v1(
    *,
    symbol: str = "",
    trade_ctx: Mapping[str, Any] | None = None,
    stage_inputs: Mapping[str, Any] | None = None,
    adverse_risk: bool = False,
    tf_confirm: bool = False,
    chosen_stage: str = "",
    policy_stage: str = "",
    confirm_needed: int = 0,
    exit_signal_score: int = 0,
    score_gap: int = 0,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    trade_ctx_map = _as_mapping(trade_ctx)
    stage_inputs_map = _as_mapping(stage_inputs)
    detail_map = _as_mapping(detail)
    provided_exit_context_v1 = _as_mapping(detail_map.get("exit_manage_context_v1"))
    exit_manage_context_v1 = provided_exit_context_v1 or build_exit_manage_context_v1(
        symbol=symbol,
        trade_ctx=trade_ctx_map,
        stage_inputs=stage_inputs_map,
        chosen_stage=chosen_stage,
        policy_stage=policy_stage,
        exec_profile="",
        confirm_needed=confirm_needed,
        exit_signal_score=exit_signal_score,
        score_gap=score_gap,
        adverse_risk=adverse_risk,
        tf_confirm=tf_confirm,
        detail=detail_map,
    )
    compact_exit_context_v1 = compact_exit_manage_context_v1(exit_manage_context_v1)
    exit_identity_context = _as_mapping(exit_manage_context_v1.get("identity"))
    exit_handoff_context = _as_mapping(exit_manage_context_v1.get("handoff"))
    exit_market_context = _as_mapping(exit_manage_context_v1.get("market"))
    exit_risk_context = _as_mapping(exit_manage_context_v1.get("risk"))
    exit_detail_context = _as_mapping(exit_manage_context_v1.get("detail"))

    profit = _to_float(
        exit_risk_context.get("profit", stage_inputs_map.get("profit", trade_ctx_map.get("profit", 0.0))),
        0.0,
    )
    peak_profit = _to_float(
        exit_risk_context.get(
            "peak_profit",
            stage_inputs_map.get("peak_profit", trade_ctx_map.get("peak_profit_at_exit", profit)),
        ),
        profit,
    )
    giveback = max(0.0, float(peak_profit - profit))
    duration_sec = _to_float(
        exit_risk_context.get("duration_sec", stage_inputs_map.get("duration_sec", trade_ctx_map.get("duration_sec", 0.0))),
        0.0,
    )
    symbol_value = _to_str(symbol or exit_identity_context.get("symbol", trade_ctx_map.get("symbol", ""))).upper()
    regime_now = _to_str(exit_market_context.get("regime_now", stage_inputs_map.get("regime_now", "UNKNOWN")), "UNKNOWN").upper()
    current_box_state = _to_str(
        exit_market_context.get("current_box_state", stage_inputs_map.get("current_box_state", trade_ctx_map.get("box_state", "UNKNOWN"))),
        "UNKNOWN",
    ).upper()
    current_bb_state = _to_str(
        exit_market_context.get("current_bb_state", stage_inputs_map.get("current_bb_state", trade_ctx_map.get("bb_state", "UNKNOWN"))),
        "UNKNOWN",
    ).upper()
    entry_direction = _to_str(
        exit_identity_context.get(
            "entry_direction",
            stage_inputs_map.get("entry_direction", trade_ctx_map.get("direction", trade_ctx_map.get("entry_direction", ""))),
        ),
        "",
    ).upper()

    state_payload_source = "stage_inputs"
    state_payload = stage_inputs_map
    if not (_extract_state_vector_v2(stage_inputs_map) or _extract_belief_state_v1(stage_inputs_map)):
        state_payload_source = "trade_ctx"
        state_payload = trade_ctx_map

    state_vector_v2, state_meta = _extract_state_v2_meta(state_payload)
    belief_state_v1 = _extract_belief_state_v1(state_payload)
    state_exit_bias_v1 = resolve_exit_state_execution_bias_v1(
        state_payload,
        entry_direction=entry_direction,
    )

    reverse_gap = max(1, int(getattr(Config, "EXIT_RECOVERY_REVERSE_SCORE_GAP", 18)))
    recovery_be_max_loss = max(0.05, float(getattr(Config, "EXIT_RECOVERY_BE_MAX_LOSS_USD", 0.90)))
    recovery_tp1_max_loss = max(0.05, float(getattr(Config, "EXIT_RECOVERY_TP1_MAX_LOSS_USD", 0.35)))
    recovery_wait_max_seconds = max(0.0, float(getattr(Config, "EXIT_RECOVERY_WAIT_MAX_SECONDS", 240)))
    recovery_policy = resolve_recovery_policy(
        symbol=symbol_value,
        management_profile_id=_to_str(exit_handoff_context.get("management_profile_id", trade_ctx_map.get("management_profile_id", ""))),
        invalidation_id=_to_str(exit_handoff_context.get("invalidation_id", trade_ctx_map.get("invalidation_id", ""))),
        entry_setup_id=_to_str(exit_identity_context.get("entry_setup_id", trade_ctx_map.get("entry_setup_id", ""))),
        state_vector_v2=state_vector_v2,
        state_metadata=state_meta,
        belief_state_v1=belief_state_v1,
        entry_direction=entry_direction,
        default_be_max_loss_usd=float(recovery_be_max_loss),
        default_tp1_max_loss_usd=float(recovery_tp1_max_loss),
        default_max_wait_seconds=int(recovery_wait_max_seconds),
        default_reverse_score_gap=int(reverse_gap),
    )
    allow_wait_be = _to_bool(recovery_policy.get("allow_wait_be", True))
    allow_wait_tp1 = _to_bool(recovery_policy.get("allow_wait_tp1", False))
    prefer_reverse = _to_bool(recovery_policy.get("prefer_reverse", False))
    recovery_be_max_loss = max(0.05, _to_float(recovery_policy.get("be_max_loss_usd", recovery_be_max_loss), recovery_be_max_loss))
    recovery_tp1_max_loss = max(0.0, _to_float(recovery_policy.get("tp1_max_loss_usd", recovery_tp1_max_loss), recovery_tp1_max_loss))
    recovery_wait_max_seconds = max(0.0, _to_float(recovery_policy.get("max_wait_seconds", recovery_wait_max_seconds), recovery_wait_max_seconds))
    reverse_gap = max(1, _to_int(recovery_policy.get("reverse_score_gap", reverse_gap), reverse_gap))
    belief_execution_bias = _as_mapping(recovery_policy.get("belief_execution_overrides_v1"))
    symbol_edge_execution_bias = _as_mapping(recovery_policy.get("symbol_edge_execution_overrides_v1"))
    state_edge_reverse_v1 = _as_mapping(recovery_policy.get("state_edge_reverse_v1"))

    range_lower_edge = bool(current_box_state in {"LOWER", "BELOW"} or current_bb_state in {"LOWER_EDGE", "BREAKDOWN"})
    range_upper_edge = bool(current_box_state in {"UPPER", "ABOVE"} or current_bb_state in {"UPPER_EDGE", "BREAKOUT"})
    reached_opposite_edge = bool(
        regime_now == "RANGE"
        and (
            (entry_direction == "SELL" and range_lower_edge)
            or (entry_direction == "BUY" and range_upper_edge)
        )
    )

    return {
        "contract_version": "exit_wait_state_input_v1",
        "identity": {
            "symbol": str(symbol_value),
            "entry_setup_id": _to_str(exit_identity_context.get("entry_setup_id", trade_ctx_map.get("entry_setup_id", ""))),
            "entry_direction": str(entry_direction),
            "state_payload_source": str(state_payload_source),
        },
        "market": {
            "regime_now": str(regime_now),
            "current_box_state": str(current_box_state),
            "current_bb_state": str(current_bb_state),
            "range_lower_edge": bool(range_lower_edge),
            "range_upper_edge": bool(range_upper_edge),
            "reached_opposite_edge": bool(reached_opposite_edge),
        },
        "risk": {
            "profit": float(profit),
            "peak_profit": float(peak_profit),
            "giveback": float(giveback),
            "duration_sec": float(duration_sec),
            "adverse_risk": _to_bool(adverse_risk),
            "tf_confirm": _to_bool(tf_confirm),
            "confirm_needed": _to_int(confirm_needed),
            "exit_signal_score": _to_int(exit_signal_score),
            "score_gap": _to_int(score_gap),
        },
        "policy": {
            "recovery_policy_id": _to_str(recovery_policy.get("policy_id", "")),
            "management_profile_id": _to_str(recovery_policy.get("management_profile_id", "")),
            "invalidation_id": _to_str(recovery_policy.get("invalidation_id", "")),
            "entry_setup_id": _to_str(recovery_policy.get("entry_setup_id", "")),
            "allow_wait_be": bool(allow_wait_be),
            "allow_wait_tp1": bool(allow_wait_tp1),
            "prefer_reverse": bool(prefer_reverse),
            "recovery_be_max_loss": float(recovery_be_max_loss),
            "recovery_tp1_max_loss": float(recovery_tp1_max_loss),
            "recovery_wait_max_seconds": float(recovery_wait_max_seconds),
            "reverse_score_gap": int(reverse_gap),
        },
        "bias": {
            "state_exit_bias_v1": dict(state_exit_bias_v1),
            "belief_execution_overrides_v1": dict(belief_execution_bias),
            "symbol_edge_execution_overrides_v1": dict(symbol_edge_execution_bias),
            "state_edge_reverse_v1": dict(state_edge_reverse_v1),
        },
        "state_inputs": {
            "state_vector_v2": dict(state_vector_v2),
            "state_metadata": dict(state_meta),
            "belief_state_v1": dict(belief_state_v1),
        },
        "detail": {
            "route_txt": _to_str(exit_detail_context.get("route_txt", detail_map.get("route_txt", ""))),
            "provided_exit_context": bool(bool(provided_exit_context_v1)),
        },
        "context": {
            "exit_manage_context_v1": dict(compact_exit_context_v1),
        },
    }


def compact_exit_wait_state_input_v1(contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    contract_map = _as_mapping(contract)
    identity = _as_mapping(contract_map.get("identity"))
    market = _as_mapping(contract_map.get("market"))
    risk = _as_mapping(contract_map.get("risk"))
    policy = _as_mapping(contract_map.get("policy"))
    bias = _as_mapping(contract_map.get("bias"))
    detail = _as_mapping(contract_map.get("detail"))
    context = _as_mapping(contract_map.get("context"))
    state_bias = _as_mapping(bias.get("state_exit_bias_v1"))
    belief_bias = _as_mapping(bias.get("belief_execution_overrides_v1"))
    symbol_edge_bias = _as_mapping(bias.get("symbol_edge_execution_overrides_v1"))
    edge_reverse = _as_mapping(bias.get("state_edge_reverse_v1"))

    return {
        "contract_version": _to_str(contract_map.get("contract_version", "exit_wait_state_input_v1")),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "entry_setup_id": _to_str(identity.get("entry_setup_id", "")),
            "entry_direction": _to_str(identity.get("entry_direction", "")).upper(),
            "state_payload_source": _to_str(identity.get("state_payload_source", "")),
        },
        "market": {
            "regime_now": _to_str(market.get("regime_now", "UNKNOWN"), "UNKNOWN").upper(),
            "current_box_state": _to_str(market.get("current_box_state", "UNKNOWN"), "UNKNOWN").upper(),
            "current_bb_state": _to_str(market.get("current_bb_state", "UNKNOWN"), "UNKNOWN").upper(),
            "reached_opposite_edge": _to_bool(market.get("reached_opposite_edge", False)),
        },
        "risk": {
            "profit": _to_float(risk.get("profit", 0.0), 0.0),
            "peak_profit": _to_float(risk.get("peak_profit", 0.0), 0.0),
            "giveback": _to_float(risk.get("giveback", 0.0), 0.0),
            "duration_sec": _to_float(risk.get("duration_sec", 0.0), 0.0),
            "adverse_risk": _to_bool(risk.get("adverse_risk", False)),
            "tf_confirm": _to_bool(risk.get("tf_confirm", False)),
            "score_gap": _to_int(risk.get("score_gap", 0), 0),
        },
        "policy": {
            "recovery_policy_id": _to_str(policy.get("recovery_policy_id", "")),
            "allow_wait_be": _to_bool(policy.get("allow_wait_be", False)),
            "allow_wait_tp1": _to_bool(policy.get("allow_wait_tp1", False)),
            "prefer_reverse": _to_bool(policy.get("prefer_reverse", False)),
            "recovery_be_max_loss": _to_float(policy.get("recovery_be_max_loss", 0.0), 0.0),
            "recovery_tp1_max_loss": _to_float(policy.get("recovery_tp1_max_loss", 0.0), 0.0),
            "recovery_wait_max_seconds": _to_float(policy.get("recovery_wait_max_seconds", 0.0), 0.0),
            "reverse_score_gap": _to_int(policy.get("reverse_score_gap", 0), 0),
        },
        "bias": {
            "prefer_hold_through_green": _to_bool(state_bias.get("prefer_hold_through_green", False)),
            "prefer_fast_cut": _to_bool(state_bias.get("prefer_fast_cut", False)),
            "belief_hold_extension": _to_bool(belief_bias.get("prefer_hold_extension", False)),
            "belief_fast_cut": _to_bool(belief_bias.get("prefer_fast_cut", False)),
            "symbol_edge_active": _to_bool(symbol_edge_bias.get("active", False)),
            "state_edge_reverse_active": _to_bool(edge_reverse.get("active", False)),
        },
        "detail": {
            "route_txt": _to_str(detail.get("route_txt", "")),
            "provided_exit_context": _to_bool(detail.get("provided_exit_context", False)),
        },
        "context": {
            "exit_manage_context_v1": dict(_as_mapping(context.get("exit_manage_context_v1"))),
        },
    }
