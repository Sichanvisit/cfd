"""Rewrite helpers for exit wait-state classification."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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


def apply_exit_wait_state_rewrite_v1(
    exit_wait_state_input_v1: Mapping[str, Any] | None = None,
    base_state_policy_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = _as_mapping(exit_wait_state_input_v1)
    base_policy = _as_mapping(base_state_policy_v1)
    identity = _as_mapping(contract.get("identity"))
    market = _as_mapping(contract.get("market"))
    risk = _as_mapping(contract.get("risk"))
    policy = _as_mapping(contract.get("policy"))
    bias = _as_mapping(contract.get("bias"))

    state = _to_str(base_policy.get("state", "NONE"), "NONE").upper()
    reason = _to_str(base_policy.get("reason", ""))
    hard_wait = _to_bool(base_policy.get("hard_wait", False))
    base_state = str(state)
    base_reason = str(reason)
    base_hard_wait = bool(hard_wait)
    rewrite_rule = ""
    rewrite_applied = False

    state_execution_bias = _as_mapping(bias.get("state_exit_bias_v1"))
    belief_execution_bias = _as_mapping(bias.get("belief_execution_overrides_v1"))
    symbol_edge_execution_bias = _as_mapping(bias.get("symbol_edge_execution_overrides_v1"))

    profit = _to_float(risk.get("profit", 0.0), 0.0)
    adverse_risk = _to_bool(risk.get("adverse_risk", False))
    tf_confirm = _to_bool(risk.get("tf_confirm", False))
    score_gap = _to_int(risk.get("score_gap", 0), 0)
    recovery_be_max_loss = max(0.05, _to_float(policy.get("recovery_be_max_loss", 0.0), 0.0))
    recovery_tp1_max_loss = max(0.0, _to_float(policy.get("recovery_tp1_max_loss", 0.0), 0.0))
    reverse_gap = max(1, _to_int(policy.get("reverse_score_gap", 1), 1))
    reached_opposite_edge = _to_bool(market.get("reached_opposite_edge", False))
    current_box_state = _to_str(market.get("current_box_state", "UNKNOWN"), "UNKNOWN").upper()
    current_bb_state = _to_str(market.get("current_bb_state", "UNKNOWN"), "UNKNOWN").upper()
    entry_direction = _to_str(identity.get("entry_direction", "")).upper()

    if state == "GREEN_CLOSE" and _to_bool(state_execution_bias.get("prefer_hold_through_green", False)) and not adverse_risk:
        state = "ACTIVE"
        reason = "green_close_hold_bias"
        rewrite_rule = "state_hold_through_green"
        rewrite_applied = True
    elif state == "GREEN_CLOSE" and _to_bool(belief_execution_bias.get("prefer_hold_extension", False)) and not adverse_risk:
        state = "ACTIVE"
        reason = "belief_hold_bias"
        rewrite_rule = "belief_hold_extension"
        rewrite_applied = True
    elif (
        state == "GREEN_CLOSE"
        and _to_bool(symbol_edge_execution_bias.get("prefer_hold_to_opposite_edge", False))
        and float(profit) > 0.0
        and not adverse_risk
        and not reached_opposite_edge
        and entry_direction == "BUY"
        and current_box_state in {"LOWER", "BELOW", "MIDDLE"}
        and current_bb_state in {"LOWER_EDGE", "BREAKDOWN", "MID", "UNKNOWN"}
    ):
        state = "ACTIVE"
        reason = "symbol_edge_hold_bias"
        rewrite_rule = "symbol_edge_hold_to_opposite_edge"
        rewrite_applied = True
    elif state in {"RECOVERY_BE", "RECOVERY_TP1"} and _to_bool(state_execution_bias.get("prefer_fast_cut", False)):
        recovery_limit = recovery_be_max_loss if state == "RECOVERY_BE" else max(recovery_be_max_loss, recovery_tp1_max_loss)
        if (adverse_risk or (tf_confirm and int(score_gap) >= int(reverse_gap))) and abs(float(profit)) >= float(recovery_limit) * 0.72:
            state = "CUT_IMMEDIATE"
            reason = "state_fast_exit_cut"
            hard_wait = False
            rewrite_rule = "state_fast_cut_recovery"
            rewrite_applied = True
    elif state in {"RECOVERY_BE", "RECOVERY_TP1"} and _to_bool(belief_execution_bias.get("prefer_fast_cut", False)):
        recovery_limit = recovery_be_max_loss if state == "RECOVERY_BE" else max(recovery_be_max_loss, recovery_tp1_max_loss)
        belief_cut_limit = min(0.18, float(recovery_limit) * 0.35)
        if (adverse_risk or tf_confirm or int(score_gap) >= max(1, int(reverse_gap * 0.8))) and abs(float(profit)) >= belief_cut_limit:
            state = "CUT_IMMEDIATE"
            reason = "belief_fast_exit_cut"
            hard_wait = False
            rewrite_rule = "belief_fast_cut_recovery"
            rewrite_applied = True
    elif state == "NONE" and _to_bool(state_execution_bias.get("prefer_fast_cut", False)):
        if float(profit) < 0.0 and _to_bool(tf_confirm) and int(score_gap) >= int(reverse_gap):
            state = "CUT_IMMEDIATE"
            reason = "state_fast_exit_cut"
            hard_wait = False
            rewrite_rule = "state_fast_cut_none"
            rewrite_applied = True
    elif state == "NONE" and _to_bool(belief_execution_bias.get("prefer_fast_cut", False)):
        if float(profit) < 0.0 and (_to_bool(tf_confirm) or int(score_gap) >= max(1, int(reverse_gap * 0.8))):
            state = "CUT_IMMEDIATE"
            reason = "belief_fast_exit_cut"
            hard_wait = False
            rewrite_rule = "belief_fast_cut_none"
            rewrite_applied = True

    return {
        "contract_version": "exit_wait_state_rewrite_v1",
        "state": str(state),
        "reason": str(reason),
        "hard_wait": bool(hard_wait),
        "base_state": str(base_state),
        "base_reason": str(base_reason),
        "base_hard_wait": bool(base_hard_wait),
        "base_matched_rule": _to_str(base_policy.get("matched_rule", "")),
        "rewrite_applied": bool(rewrite_applied),
        "rewrite_rule": str(rewrite_rule),
    }
