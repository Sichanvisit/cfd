"""Surface contracts for exit wait-state metadata and runtime summaries."""

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


def build_exit_wait_state_surface_v1(
    *,
    exit_wait_state_input_v1: Mapping[str, Any] | None = None,
    exit_wait_state_policy_v1: Mapping[str, Any] | None = None,
    exit_wait_state_rewrite_v1: Mapping[str, Any] | None = None,
    score: float = 0.0,
    penalty: float = 0.0,
    conflict: float = 0.0,
    noise: float = 0.0,
) -> dict[str, Any]:
    contract = _as_mapping(exit_wait_state_input_v1)
    state_policy = _as_mapping(exit_wait_state_policy_v1)
    state_rewrite = _as_mapping(exit_wait_state_rewrite_v1)
    identity = _as_mapping(contract.get("identity"))
    market = _as_mapping(contract.get("market"))
    risk = _as_mapping(contract.get("risk"))
    policy = _as_mapping(contract.get("policy"))
    bias = _as_mapping(contract.get("bias"))
    detail = _as_mapping(contract.get("detail"))
    compact_exit_context = _as_mapping(_as_mapping(contract.get("context")).get("exit_manage_context_v1"))
    posture = _as_mapping(compact_exit_context.get("posture"))

    state_exit_bias = _as_mapping(bias.get("state_exit_bias_v1"))
    belief_execution_overrides = _as_mapping(bias.get("belief_execution_overrides_v1"))
    symbol_edge_execution_overrides = _as_mapping(bias.get("symbol_edge_execution_overrides_v1"))

    return {
        "contract_version": "exit_wait_state_surface_v1",
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "entry_setup_id": _to_str(identity.get("entry_setup_id", "")),
            "entry_direction": _to_str(identity.get("entry_direction", "")).upper(),
            "chosen_stage": _to_str(posture.get("chosen_stage", "")),
            "policy_stage": _to_str(posture.get("policy_stage", "")),
        },
        "state": {
            "state": _to_str(state_rewrite.get("state", state_policy.get("state", "NONE")), "NONE").upper(),
            "reason": _to_str(state_rewrite.get("reason", state_policy.get("reason", ""))),
            "hard_wait": _to_bool(
                state_rewrite.get("hard_wait", state_policy.get("hard_wait", False)),
                False,
            ),
            "base_state": _to_str(
                state_rewrite.get("base_state", state_policy.get("state", "NONE")),
                "NONE",
            ).upper(),
            "base_reason": _to_str(
                state_rewrite.get("base_reason", state_policy.get("reason", "")),
            ),
            "base_hard_wait": _to_bool(
                state_rewrite.get("base_hard_wait", state_policy.get("hard_wait", False)),
                False,
            ),
            "base_matched_rule": _to_str(
                state_rewrite.get("base_matched_rule", state_policy.get("matched_rule", "")),
            ),
            "rewrite_applied": _to_bool(state_rewrite.get("rewrite_applied", False), False),
            "rewrite_rule": _to_str(state_rewrite.get("rewrite_rule", "")),
        },
        "scoring": {
            "score": _to_float(score, 0.0),
            "penalty": _to_float(penalty, 0.0),
            "conflict": _to_float(conflict, 0.0),
            "noise": _to_float(noise, 0.0),
        },
        "policy": {
            "recovery_policy_id": _to_str(policy.get("recovery_policy_id", "")),
            "management_profile_id": _to_str(policy.get("management_profile_id", "")),
            "invalidation_id": _to_str(policy.get("invalidation_id", "")),
            "entry_setup_id": _to_str(policy.get("entry_setup_id", "")),
            "allow_wait_be": _to_bool(policy.get("allow_wait_be", False), False),
            "allow_wait_tp1": _to_bool(policy.get("allow_wait_tp1", False), False),
            "prefer_reverse": _to_bool(policy.get("prefer_reverse", False), False),
            "recovery_be_max_loss": _to_float(policy.get("recovery_be_max_loss", 0.0), 0.0),
            "recovery_tp1_max_loss": _to_float(policy.get("recovery_tp1_max_loss", 0.0), 0.0),
            "recovery_wait_max_seconds": _to_float(policy.get("recovery_wait_max_seconds", 0.0), 0.0),
            "reverse_score_gap": _to_int(policy.get("reverse_score_gap", 0), 0),
        },
        "market": {
            "regime_now": _to_str(market.get("regime_now", "UNKNOWN"), "UNKNOWN").upper(),
            "current_box_state": _to_str(market.get("current_box_state", "UNKNOWN"), "UNKNOWN").upper(),
            "current_bb_state": _to_str(market.get("current_bb_state", "UNKNOWN"), "UNKNOWN").upper(),
            "reached_opposite_edge": _to_bool(market.get("reached_opposite_edge", False), False),
        },
        "risk": {
            "profit": _to_float(risk.get("profit", 0.0), 0.0),
            "peak_profit": _to_float(risk.get("peak_profit", 0.0), 0.0),
            "giveback": _to_float(risk.get("giveback", 0.0), 0.0),
            "duration_sec": _to_float(risk.get("duration_sec", 0.0), 0.0),
            "tf_confirm": _to_bool(risk.get("tf_confirm", False), False),
            "adverse_risk": _to_bool(risk.get("adverse_risk", False), False),
            "confirm_needed": _to_int(risk.get("confirm_needed", 0), 0),
            "exit_signal_score": _to_int(risk.get("exit_signal_score", 0), 0),
            "score_gap": _to_int(risk.get("score_gap", 0), 0),
        },
        "bias": {
            "state_prefer_hold_through_green": _to_bool(
                state_exit_bias.get("prefer_hold_through_green", False),
                False,
            ),
            "state_prefer_fast_cut": _to_bool(state_exit_bias.get("prefer_fast_cut", False), False),
            "belief_hold_extension": _to_bool(
                belief_execution_overrides.get("prefer_hold_extension", False),
                False,
            ),
            "belief_fast_cut": _to_bool(
                belief_execution_overrides.get("prefer_fast_cut", False),
                False,
            ),
            "symbol_edge_hold_to_opposite_edge": _to_bool(
                symbol_edge_execution_overrides.get("prefer_hold_to_opposite_edge", False),
                False,
            ),
        },
        "detail": {
            "route_txt": _to_str(detail.get("route_txt", "")),
            "input_contract_version": _to_str(contract.get("contract_version", "")),
            "base_policy_contract_version": _to_str(state_policy.get("contract_version", "")),
            "rewrite_contract_version": _to_str(state_rewrite.get("contract_version", "")),
        },
    }


def compact_exit_wait_state_surface_v1(surface: Mapping[str, Any] | None = None) -> dict[str, Any]:
    surface_map = _as_mapping(surface)
    identity = _as_mapping(surface_map.get("identity"))
    state = _as_mapping(surface_map.get("state"))
    scoring = _as_mapping(surface_map.get("scoring"))
    policy = _as_mapping(surface_map.get("policy"))
    market = _as_mapping(surface_map.get("market"))
    risk = _as_mapping(surface_map.get("risk"))
    bias = _as_mapping(surface_map.get("bias"))
    detail = _as_mapping(surface_map.get("detail"))

    return {
        "contract_version": _to_str(surface_map.get("contract_version", "exit_wait_state_surface_v1")),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "entry_direction": _to_str(identity.get("entry_direction", "")).upper(),
            "chosen_stage": _to_str(identity.get("chosen_stage", "")),
            "policy_stage": _to_str(identity.get("policy_stage", "")),
        },
        "state": {
            "state": _to_str(state.get("state", "NONE"), "NONE").upper(),
            "reason": _to_str(state.get("reason", "")),
            "hard_wait": _to_bool(state.get("hard_wait", False), False),
            "base_state": _to_str(state.get("base_state", "NONE"), "NONE").upper(),
            "base_reason": _to_str(state.get("base_reason", "")),
            "rewrite_applied": _to_bool(state.get("rewrite_applied", False), False),
            "rewrite_rule": _to_str(state.get("rewrite_rule", "")),
            "base_matched_rule": _to_str(state.get("base_matched_rule", "")),
        },
        "scoring": {
            "score": _to_float(scoring.get("score", 0.0), 0.0),
            "penalty": _to_float(scoring.get("penalty", 0.0), 0.0),
        },
        "policy": {
            "recovery_policy_id": _to_str(policy.get("recovery_policy_id", "")),
            "allow_wait_be": _to_bool(policy.get("allow_wait_be", False), False),
            "allow_wait_tp1": _to_bool(policy.get("allow_wait_tp1", False), False),
            "prefer_reverse": _to_bool(policy.get("prefer_reverse", False), False),
            "recovery_be_max_loss": _to_float(policy.get("recovery_be_max_loss", 0.0), 0.0),
            "recovery_tp1_max_loss": _to_float(policy.get("recovery_tp1_max_loss", 0.0), 0.0),
            "recovery_wait_max_seconds": _to_float(policy.get("recovery_wait_max_seconds", 0.0), 0.0),
            "reverse_score_gap": _to_int(policy.get("reverse_score_gap", 0), 0),
        },
        "market": {
            "regime_now": _to_str(market.get("regime_now", "UNKNOWN"), "UNKNOWN").upper(),
            "current_box_state": _to_str(market.get("current_box_state", "UNKNOWN"), "UNKNOWN").upper(),
            "current_bb_state": _to_str(market.get("current_bb_state", "UNKNOWN"), "UNKNOWN").upper(),
        },
        "risk": {
            "profit": _to_float(risk.get("profit", 0.0), 0.0),
            "giveback": _to_float(risk.get("giveback", 0.0), 0.0),
            "duration_sec": _to_float(risk.get("duration_sec", 0.0), 0.0),
            "tf_confirm": _to_bool(risk.get("tf_confirm", False), False),
            "adverse_risk": _to_bool(risk.get("adverse_risk", False), False),
            "score_gap": _to_int(risk.get("score_gap", 0), 0),
        },
        "bias": {
            "state_prefer_hold_through_green": _to_bool(
                bias.get("state_prefer_hold_through_green", False),
                False,
            ),
            "state_prefer_fast_cut": _to_bool(bias.get("state_prefer_fast_cut", False), False),
            "belief_hold_extension": _to_bool(bias.get("belief_hold_extension", False), False),
            "belief_fast_cut": _to_bool(bias.get("belief_fast_cut", False), False),
            "symbol_edge_hold_to_opposite_edge": _to_bool(
                bias.get("symbol_edge_hold_to_opposite_edge", False),
                False,
            ),
        },
        "detail": {
            "route_txt": _to_str(detail.get("route_txt", "")),
        },
    }
