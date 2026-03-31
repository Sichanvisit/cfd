"""Shared entry wait-decision policy helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.services.utility_router import compute_entry_utility, compute_wait_utility


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _lower(value: object) -> str:
    return str(value or "").strip().lower()


def resolve_entry_wait_decision_policy_v1(
    *,
    blocked_reason: str = "",
    raw_entry_score: float = 0.0,
    effective_threshold: float = 0.0,
    core_score: float = 0.0,
    utility_u: float | None = None,
    utility_u_min: float | None = None,
    wait_state_state: str = "",
    wait_state_score: float = 0.0,
    wait_state_penalty: float = 0.0,
    wait_state_hard_wait: bool = False,
    wait_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    wait_metadata_local = _as_mapping(wait_metadata)
    state = str(wait_state_state or "NONE").upper()
    blocked_reason_text = str(blocked_reason or "")
    threshold_margin = (_to_float(raw_entry_score) - _to_float(effective_threshold)) / max(
        1.0,
        _to_float(effective_threshold, 1.0),
    )
    threshold_margin = max(-1.0, min(1.0, float(threshold_margin)))
    utility_margin = 0.0
    if utility_u is not None and utility_u_min is not None:
        utility_margin = _to_float(utility_u) - _to_float(utility_u_min)

    enter_value = float(threshold_margin + utility_margin + (_to_float(core_score) * 0.35))
    if blocked_reason_text == "core_not_passed":
        enter_value -= 0.45
    elif blocked_reason_text == "dynamic_threshold_not_met":
        enter_value -= 0.35
    elif blocked_reason_text == "setup_rejected":
        enter_value -= 0.55

    state_bonus = {
        "POLICY_BLOCK": 1.65,
        "POLICY_SUPPRESSED": 1.35,
        "AGAINST_MODE": 1.40,
        "NEED_RETEST": 1.15,
        "EDGE_APPROACH": 1.05,
        "CONFLICT": 0.85,
        "CENTER": 0.75,
        "NOISE": 0.65,
        "HELPER_SOFT_BLOCK": 0.70,
        "HELPER_WAIT": 0.55,
        "ACTIVE": 0.45,
    }.get(state, 0.0)
    wait_value = float(
        state_bonus
        + min(1.0, max(0.0, _to_float(wait_state_score) / 100.0)) * 0.45
        + min(1.0, max(0.0, _to_float(wait_state_penalty) / 20.0)) * 0.20
    )

    action_readiness = _to_float(wait_metadata_local.get("action_readiness", 0.0))
    wait_vs_enter_hint = _lower(wait_metadata_local.get("wait_vs_enter_hint", ""))
    soft_block_active = _to_bool(wait_metadata_local.get("soft_block_active", False))
    soft_block_strength = _to_float(wait_metadata_local.get("soft_block_strength", 0.0))
    policy_hard_block_active = _to_bool(wait_metadata_local.get("policy_hard_block_active", False))
    policy_suppressed = _to_bool(wait_metadata_local.get("policy_suppressed", False))

    belief_wait_bias = _as_mapping(wait_metadata_local.get("belief_wait_bias_v1"))
    belief_prefer_confirm_release = _to_bool(belief_wait_bias.get("prefer_confirm_release", False))
    belief_prefer_wait_lock = _to_bool(belief_wait_bias.get("prefer_wait_lock", False))

    edge_pair_wait_bias = _as_mapping(wait_metadata_local.get("edge_pair_wait_bias_v1"))
    edge_pair_prefer_confirm_release = _to_bool(edge_pair_wait_bias.get("prefer_confirm_release", False))
    edge_pair_prefer_wait_lock = _to_bool(edge_pair_wait_bias.get("prefer_wait_lock", False))

    symbol_probe_temperament = _as_mapping(wait_metadata_local.get("symbol_probe_temperament_v1"))
    symbol_probe_prefer_confirm_release = _to_bool(
        symbol_probe_temperament.get("prefer_confirm_release", False)
    )
    symbol_probe_prefer_wait_lock = _to_bool(symbol_probe_temperament.get("prefer_wait_lock", False))

    xau_second_support_probe = _to_bool(wait_metadata_local.get("xau_second_support_probe", False))
    xau_upper_sell_probe = _to_bool(wait_metadata_local.get("xau_upper_sell_probe", False))

    enter_value += float((action_readiness - 0.50) * 0.90)
    wait_value += float(max(0.0, 0.50 - action_readiness) * 0.55)
    if xau_second_support_probe:
        enter_value += 0.22
        wait_value -= 0.14
    if xau_upper_sell_probe:
        enter_value += 0.22
        wait_value -= 0.14
    if wait_vs_enter_hint == "prefer_enter":
        enter_value += 0.28
        wait_value -= 0.14
    elif wait_vs_enter_hint == "prefer_wait":
        wait_value += 0.32
        enter_value -= 0.18
    if soft_block_active:
        wait_value += float(0.18 + (soft_block_strength * 0.32))
        enter_value -= float(0.10 + (soft_block_strength * 0.24))
    if policy_hard_block_active:
        wait_value += 0.95
        enter_value -= 0.90
    elif policy_suppressed:
        wait_value += 0.70
        enter_value -= 0.62

    enter_value += _to_float(belief_wait_bias.get("enter_value_delta", 0.0))
    wait_value += _to_float(belief_wait_bias.get("wait_value_delta", 0.0))
    enter_value += _to_float(edge_pair_wait_bias.get("enter_value_delta", 0.0))
    wait_value += _to_float(edge_pair_wait_bias.get("wait_value_delta", 0.0))
    enter_value += _to_float(symbol_probe_temperament.get("enter_value_delta", 0.0))
    wait_value += _to_float(symbol_probe_temperament.get("wait_value_delta", 0.0))

    if blocked_reason_text == "core_not_passed":
        wait_value += 0.35
    elif blocked_reason_text == "edge_approach_observe":
        wait_value += 0.45
    elif blocked_reason_text == "conflict_observe_wait":
        wait_value += 0.42
    elif blocked_reason_text == "dynamic_threshold_not_met":
        wait_value += 0.25
    elif blocked_reason_text == "setup_rejected":
        wait_value += 0.20

    enter_value = compute_entry_utility(
        p_win=max(0.05, min(0.95, 0.5 + (enter_value * 0.12))),
        expected_reward=max(0.10, 1.0 + max(0.0, threshold_margin)),
        expected_risk=max(0.10, 1.0 + max(0.0, -threshold_margin)),
        cost=0.15,
        context_adj=max(-0.40, min(0.40, _to_float(core_score) * 0.20)),
    )
    wait_value = compute_wait_utility(
        p_better_entry_if_wait=max(0.05, min(0.95, 0.5 + (wait_value * 0.10))),
        expected_entry_improvement=max(0.10, 0.8 + (state_bonus * 0.20)),
        expected_miss_cost=0.18,
        extra_penalty=max(0.0, 0.04 if state == "NONE" else 0.0),
    )

    helper_wait_margin = -0.10
    generic_wait_margin = -0.05
    if belief_prefer_confirm_release:
        helper_wait_margin = 0.28
        generic_wait_margin = 0.40
    elif belief_prefer_wait_lock:
        helper_wait_margin = -0.18
        generic_wait_margin = -0.14
    if edge_pair_prefer_confirm_release:
        helper_wait_margin = max(helper_wait_margin, 0.18)
        generic_wait_margin = max(generic_wait_margin, 0.26)
    elif edge_pair_prefer_wait_lock:
        helper_wait_margin = min(helper_wait_margin, -0.15)
        generic_wait_margin = min(generic_wait_margin, -0.12)
    if symbol_probe_prefer_confirm_release:
        helper_wait_margin = max(helper_wait_margin, 0.12)
        generic_wait_margin = max(generic_wait_margin, 0.18)
    elif symbol_probe_prefer_wait_lock:
        helper_wait_margin = min(helper_wait_margin, -0.12)
        generic_wait_margin = min(generic_wait_margin, -0.10)

    selected = False
    decision = "skip"
    if policy_hard_block_active:
        selected = True
        decision = "wait_policy_hard_block"
    elif policy_suppressed:
        selected = True
        decision = "wait_policy_suppressed"
    elif (
        soft_block_active
        and wait_vs_enter_hint == "prefer_wait"
        and float(wait_value) >= float(enter_value) + helper_wait_margin
    ):
        selected = True
        decision = "wait_soft_helper_block"
    elif (
        wait_vs_enter_hint == "prefer_wait"
        and action_readiness <= 0.40
        and state in {"NONE", "ACTIVE", "NOISE", "HELPER_WAIT", "HELPER_SOFT_BLOCK"}
        and float(wait_value) >= float(enter_value) + helper_wait_margin
    ):
        selected = True
        decision = "wait_soft_helper_bias"
    elif bool(wait_state_hard_wait) and state != "NONE":
        selected = True
        decision = f"wait_hard_{state.lower()}"
    elif blocked_reason_text == "edge_approach_observe" and state == "EDGE_APPROACH":
        selected = True
        decision = "wait_soft_edge_approach"
    elif blocked_reason_text == "conflict_observe_wait" and state in {"CONFLICT", "EDGE_APPROACH", "ACTIVE"}:
        selected = True
        decision = "wait_soft_conflict_observe"
    elif state != "NONE" and blocked_reason_text in {
        "core_not_passed",
        "edge_approach_observe",
        "conflict_observe_wait",
        "dynamic_threshold_not_met",
        "setup_rejected",
    }:
        if float(wait_value) >= float(enter_value) + generic_wait_margin:
            selected = True
            decision = f"wait_soft_{state.lower()}"

    return {
        "contract_version": "entry_wait_decision_policy_v1",
        "selected": bool(selected),
        "decision": str(decision),
        "enter_value": float(enter_value),
        "wait_value": float(wait_value),
        "policy_hint_applied": bool(policy_hard_block_active or policy_suppressed),
        "energy_hint_applied": bool(soft_block_active or wait_vs_enter_hint or action_readiness > 0.0),
        "helper_wait_margin": float(helper_wait_margin),
        "generic_wait_margin": float(generic_wait_margin),
    }
