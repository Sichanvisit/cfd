"""Shared entry wait-state policy helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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


def _upper(value: object) -> str:
    return str(value or "").strip().upper()


def _lower(value: object) -> str:
    return str(value or "").strip().lower()


def _required_side(policy: object) -> str:
    upper = _upper(policy)
    if upper == "BUY_ONLY":
        return "BUY"
    if upper == "SELL_ONLY":
        return "SELL"
    return ""


def resolve_entry_wait_state_policy_v1(
    *,
    symbol: str = "",
    action: str = "",
    blocked_by: str = "",
    action_none_reason: str = "",
    box_state: str = "",
    bb_state: str = "",
    observe_reason: str = "",
    core_allowed_action: str = "",
    preflight_allowed_action: str = "",
    setup_reason: str = "",
    setup_trigger_state: str = "",
    wait_score: float = 0.0,
    wait_conflict: float = 0.0,
    wait_noise: float = 0.0,
    wait_soft: float = 0.0,
    wait_hard: float = 0.0,
    action_readiness: float = 0.0,
    wait_vs_enter_hint: str = "",
    soft_block_active: bool = False,
    soft_block_reason: str = "",
    soft_block_strength: float = 0.0,
    policy_hard_block_active: bool = False,
    policy_suppressed: bool = False,
    observe_metadata: Mapping[str, Any] | None = None,
    state_wait_bias_v1: Mapping[str, Any] | None = None,
    belief_wait_bias_v1: Mapping[str, Any] | None = None,
    edge_pair_wait_bias_v1: Mapping[str, Any] | None = None,
    symbol_probe_temperament_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    observe_metadata_local = _as_mapping(observe_metadata)
    state_wait_bias = _as_mapping(state_wait_bias_v1)
    belief_wait_bias = _as_mapping(belief_wait_bias_v1)
    edge_pair_wait_bias = _as_mapping(edge_pair_wait_bias_v1)
    symbol_probe_temperament = _as_mapping(symbol_probe_temperament_v1)

    symbol_upper = _upper(symbol)
    action_upper = _upper(action)
    blocked_by_text = str(blocked_by or "")
    action_none_reason_text = str(action_none_reason or "")
    box_state_upper = _upper(box_state)
    bb_state_upper = _upper(bb_state)
    observe_reason_text = str(observe_reason or "")
    core_allowed_action_upper = _upper(core_allowed_action)
    preflight_allowed_action_upper = _upper(preflight_allowed_action)
    setup_reason_text = str(setup_reason or "")
    setup_trigger_state_upper = _upper(setup_trigger_state)
    wait_vs_enter_hint_text = _lower(wait_vs_enter_hint)
    symbol_probe_scene_id = str(symbol_probe_temperament.get("scene_id", "") or "").lower()

    required_side = _required_side(preflight_allowed_action_upper) or _required_side(core_allowed_action_upper)
    need_retest = blocked_by_text in {
        "bb_channel_breakdown_buy_blocked",
        "bb_channel_breakout_sell_blocked",
    } or ("retest" in setup_reason_text.lower())
    against_mode = bool(required_side and action_upper and (action_upper != required_side))
    if blocked_by_text == "preflight_action_blocked":
        against_mode = True

    xau_second_support_probe = bool(
        symbol_upper == "XAUUSD"
        and action_upper in {"", "BUY"}
        and box_state_upper in {"LOWER", "LOWER_EDGE"}
        and bb_state_upper in {"MID", "MIDDLE", "LOWER", "LOWER_EDGE"}
        and _to_bool(observe_metadata_local.get("xau_second_support_probe_relief", False))
    )
    xau_upper_sell_probe = bool(
        symbol_upper == "XAUUSD"
        and action_upper in {"", "SELL"}
        and box_state_upper in {"UPPER", "UPPER_EDGE", "ABOVE"}
        and bb_state_upper in {"MID", "MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
        and (
            symbol_probe_scene_id == "xau_upper_sell_probe"
            or observe_reason_text == "upper_reject_probe_observe"
        )
    )

    state = "NONE"
    reason = ""
    if policy_hard_block_active:
        state = "POLICY_BLOCK"
        reason = blocked_by_text or action_none_reason_text or "layer_mode_policy_hard_block"
    elif policy_suppressed:
        state = "POLICY_SUPPRESSED"
        reason = blocked_by_text or action_none_reason_text or "layer_mode_confirm_suppressed"
    elif against_mode:
        state = "AGAINST_MODE"
        reason = blocked_by_text or action_none_reason_text or f"required_{required_side.lower()}"
    elif xau_second_support_probe:
        state = "ACTIVE"
        reason = observe_reason_text or action_none_reason_text or blocked_by_text or "xau_second_support_probe_wait"
    elif xau_upper_sell_probe:
        state = "ACTIVE"
        reason = observe_reason_text or action_none_reason_text or blocked_by_text or "xau_upper_sell_probe_wait"
    elif observe_reason_text == "edge_approach_observe":
        state = "EDGE_APPROACH"
        reason = observe_reason_text
    elif "observe" in observe_reason_text.lower() and box_state_upper in {"LOWER", "UPPER", "BELOW", "ABOVE"}:
        state = "EDGE_APPROACH"
        reason = observe_reason_text
    elif "observe" in setup_reason_text.lower() and box_state_upper in {"LOWER", "UPPER", "BELOW", "ABOVE"}:
        state = "EDGE_APPROACH"
        reason = setup_reason_text or observe_reason_text or "edge_approach_observe"
    elif need_retest or (setup_trigger_state_upper == "WEAK" and "BREAKOUT" in setup_reason_text.upper()):
        state = "NEED_RETEST"
        reason = blocked_by_text or setup_reason_text or "need_retest"
    elif box_state_upper == "MIDDLE" or bb_state_upper == "MID":
        state = "CENTER"
        reason = observe_reason_text or action_none_reason_text or "center_zone_wait"
    elif wait_conflict > 0.0 and wait_conflict >= max(wait_noise, 1e-9):
        state = "CONFLICT"
        reason = observe_reason_text or blocked_by_text or "score_conflict"
    elif wait_noise > 0.0:
        state = "NOISE"
        reason = observe_reason_text or action_none_reason_text or "noise_wait"
    elif wait_score > 0.0:
        state = "ACTIVE"
        reason = observe_reason_text or action_none_reason_text or blocked_by_text or "wait_score_active"
    elif soft_block_active:
        state = "HELPER_SOFT_BLOCK"
        reason = soft_block_reason or blocked_by_text or action_none_reason_text or observe_reason_text or "energy_soft_block"
    elif wait_vs_enter_hint_text == "prefer_wait" and _to_float(action_readiness) <= 0.40:
        state = "HELPER_WAIT"
        reason = observe_reason_text or action_none_reason_text or blocked_by_text or "energy_wait_bias"

    btc_lower_strong_score_soft_wait = bool(
        symbol_upper == "BTCUSD"
        and box_state_upper == "LOWER"
        and bb_state_upper in {"MID", "UNKNOWN"}
        and preflight_allowed_action_upper in {"BOTH", "BUY_ONLY"}
        and blocked_by_text in {"core_not_passed", "dynamic_threshold_not_met"}
        and action_upper in {"", "BUY"}
        and _to_float(wait_score) <= 80.0
        and _to_float(wait_conflict) <= 20.0
        and _to_float(wait_noise) <= 18.0
    )

    hard_wait = bool(
        state in {"POLICY_BLOCK", "POLICY_SUPPRESSED", "AGAINST_MODE", "NEED_RETEST"}
        or _to_float(wait_score) >= _to_float(wait_hard)
        or (blocked_by_text in {"core_not_passed", "dynamic_threshold_not_met"} and _to_float(wait_score) >= _to_float(wait_soft))
        or (soft_block_active and _to_float(soft_block_strength) >= 0.75 and wait_vs_enter_hint_text != "prefer_enter")
    )

    if (
        _to_bool(state_wait_bias.get("prefer_confirm_release", False))
        and state in {"CENTER", "CONFLICT", "EDGE_APPROACH", "ACTIVE", "HELPER_WAIT"}
        and not policy_hard_block_active
        and not policy_suppressed
        and not against_mode
        and not need_retest
        and _to_float(wait_score) < (_to_float(wait_hard) + 6.0)
    ):
        hard_wait = False
    if (
        _to_bool(state_wait_bias.get("prefer_wait_lock", False))
        and state in {"CENTER", "CONFLICT", "ACTIVE", "HELPER_WAIT"}
        and not policy_hard_block_active
        and not against_mode
        and _to_float(wait_score) >= max(_to_float(wait_soft) * 0.92, 1.0)
        and wait_vs_enter_hint_text != "prefer_enter"
    ):
        hard_wait = True
    if (
        _to_bool(belief_wait_bias.get("prefer_confirm_release", False))
        and state in {"CENTER", "CONFLICT", "EDGE_APPROACH", "ACTIVE", "HELPER_WAIT", "HELPER_SOFT_BLOCK"}
        and not policy_hard_block_active
        and not policy_suppressed
        and not against_mode
        and not need_retest
        and _to_float(wait_score) < (_to_float(wait_hard) + 8.0)
        and wait_vs_enter_hint_text != "prefer_wait"
    ):
        hard_wait = False
    if (
        _to_bool(belief_wait_bias.get("prefer_wait_lock", False))
        and state in {"CENTER", "CONFLICT", "ACTIVE", "HELPER_WAIT", "HELPER_SOFT_BLOCK"}
        and not policy_hard_block_active
        and not against_mode
        and _to_float(wait_score) >= max(_to_float(wait_soft) * 0.86, 1.0)
        and wait_vs_enter_hint_text != "prefer_enter"
    ):
        hard_wait = True
    if (
        _to_bool(edge_pair_wait_bias.get("prefer_confirm_release", False))
        and state in {"CENTER", "CONFLICT", "EDGE_APPROACH", "ACTIVE", "HELPER_WAIT", "HELPER_SOFT_BLOCK"}
        and not policy_hard_block_active
        and not policy_suppressed
        and not against_mode
        and not need_retest
        and wait_vs_enter_hint_text != "prefer_wait"
    ):
        hard_wait = False
    if (
        _to_bool(edge_pair_wait_bias.get("prefer_wait_lock", False))
        and state in {"CENTER", "CONFLICT", "EDGE_APPROACH", "ACTIVE", "HELPER_WAIT", "HELPER_SOFT_BLOCK"}
        and not policy_hard_block_active
        and not against_mode
        and _to_float(wait_score) >= max(_to_float(wait_soft) * 0.84, 1.0)
        and wait_vs_enter_hint_text != "prefer_enter"
    ):
        hard_wait = True
    if btc_lower_strong_score_soft_wait and state in {"CENTER", "CONFLICT"}:
        hard_wait = False
    if (
        (xau_second_support_probe or xau_upper_sell_probe)
        and state in {"ACTIVE", "CENTER", "NOISE", "EDGE_APPROACH", "HELPER_WAIT", "HELPER_SOFT_BLOCK"}
        and not policy_hard_block_active
        and not policy_suppressed
        and not against_mode
        and not need_retest
    ):
        hard_wait = False

    return {
        "contract_version": "entry_wait_state_policy_v1",
        "state": str(state),
        "reason": str(reason),
        "hard_wait": bool(hard_wait),
        "required_side": str(required_side),
        "need_retest": bool(need_retest),
        "against_mode": bool(against_mode),
        "btc_lower_strong_score_soft_wait": bool(btc_lower_strong_score_soft_wait),
        "xau_second_support_probe": bool(xau_second_support_probe),
        "xau_upper_sell_probe": bool(xau_upper_sell_probe),
    }
