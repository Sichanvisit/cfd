"""Scene and symbol bias bundle helpers for exit utility decisions."""

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


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _round6(value: object, default: float = 0.0) -> float:
    return round(_to_float(value, default), 6)


def resolve_exit_utility_scene_bias_bundle_v1(
    *,
    exit_utility_input_v1: Mapping[str, Any] | None = None,
    exit_utility_base_bundle_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    utility_input = _as_mapping(exit_utility_input_v1)
    base_bundle = _as_mapping(exit_utility_base_bundle_v1)

    identity = _as_mapping(utility_input.get("identity"))
    market = _as_mapping(utility_input.get("market"))
    risk = _as_mapping(utility_input.get("risk"))
    policy = _as_mapping(utility_input.get("policy"))
    bias = _as_mapping(utility_input.get("bias"))
    base_inputs = _as_mapping(base_bundle.get("inputs"))

    symbol_u = _to_str(identity.get("symbol", "")).upper()
    state = _to_str(identity.get("state", "NONE"), "NONE").upper()
    entry_direction = _to_str(identity.get("entry_direction", "")).upper()
    regime_now = _to_str(market.get("regime_now", "UNKNOWN"), "UNKNOWN").upper()
    current_box_state = _to_str(market.get("current_box_state", "UNKNOWN"), "UNKNOWN").upper()
    current_bb_state = _to_str(market.get("current_bb_state", "UNKNOWN"), "UNKNOWN").upper()
    profit = _to_float(risk.get("profit", 0.0), 0.0)
    peak_profit = _to_float(risk.get("peak_profit", profit), profit)
    giveback = _to_float(risk.get("giveback", max(0.0, peak_profit - profit)), 0.0)
    adverse_risk = _to_bool(risk.get("adverse_risk", False), False)
    recovery_policy_id = _to_str(policy.get("recovery_policy_id", ""))
    locked_profit = _to_float(base_inputs.get("locked_profit", max(0.0, profit)), 0.0)
    symbol_edge_execution_bias = _as_mapping(
        bias.get("symbol_edge_execution_overrides_v1")
    )

    range_middle_observe = bool(regime_now == "RANGE" and current_box_state == "MIDDLE")
    range_lower_edge = bool(
        current_box_state in {"LOWER", "BELOW"} or current_bb_state in {"LOWER_EDGE", "BREAKDOWN"}
    )
    range_upper_edge = bool(
        current_box_state in {"UPPER", "ABOVE"} or current_bb_state in {"UPPER_EDGE", "BREAKOUT"}
    )
    reached_opposite_edge = bool(
        regime_now == "RANGE"
        and (
            (entry_direction == "SELL" and range_lower_edge)
            or (entry_direction == "BUY" and range_upper_edge)
        )
    )

    utility_exit_now_delta = 0.0
    utility_hold_delta = 0.0
    utility_wait_exit_delta = 0.0

    if range_middle_observe and not adverse_risk:
        utility_exit_now_delta -= 0.12
        utility_hold_delta += 0.22
        utility_wait_exit_delta += 0.16

    symbol_edge_completion_bias_v1 = {
        "active": False,
        "reason": "",
        "exit_now_delta": 0.0,
        "hold_delta": 0.0,
        "wait_delta": 0.0,
    }
    if reached_opposite_edge and profit > 0.0:
        utility_exit_now_delta += 0.30 + min(0.30, locked_profit * 0.12)
        utility_hold_delta -= 0.26
        utility_wait_exit_delta -= 0.20
        opposite_edge_exit_boost = _to_float(
            symbol_edge_execution_bias.get("opposite_edge_exit_boost", 0.0),
            0.0,
        )
        if opposite_edge_exit_boost > 0.0:
            utility_exit_now_delta += opposite_edge_exit_boost
            utility_hold_delta -= opposite_edge_exit_boost * 0.90
            utility_wait_exit_delta -= opposite_edge_exit_boost * 0.70
            symbol_edge_completion_bias_v1 = {
                "active": True,
                "reason": "opposite_edge_completion",
                "exit_now_delta": _round6(opposite_edge_exit_boost, 0.0),
                "hold_delta": _round6(-(opposite_edge_exit_boost * 0.90), 0.0),
                "wait_delta": _round6(-(opposite_edge_exit_boost * 0.70), 0.0),
            }

    lower_reversal_hold_bias = bool(
        entry_direction == "BUY"
        and recovery_policy_id
        in {
            "range_lower_reversal_buy_nas_balanced",
            "range_lower_reversal_buy_xau_balanced",
            "range_lower_reversal_buy_btc_balanced",
        }
        and profit > 0.0
        and not adverse_risk
        and not reached_opposite_edge
    )
    xau_lower_edge_to_edge_hold_bias = bool(
        symbol_u == "XAUUSD"
        and entry_direction == "BUY"
        and recovery_policy_id == "range_lower_reversal_buy_xau_balanced"
        and profit > 0.0
        and not adverse_risk
        and not reached_opposite_edge
        and regime_now in {"RANGE", "UNKNOWN"}
        and current_box_state in {"LOWER", "BELOW", "MIDDLE"}
        and current_bb_state in {"LOWER_EDGE", "MID", "UNKNOWN"}
    )
    if xau_lower_edge_to_edge_hold_bias:
        premature_exit_relief = _to_float(
            symbol_edge_execution_bias.get("premature_exit_relief", 0.0),
            0.0,
        )
        mid_noise_hold_boost = _to_float(
            symbol_edge_execution_bias.get("mid_noise_hold_boost", 0.0),
            0.0,
        )
        utility_exit_now_delta -= 0.16 + premature_exit_relief + min(0.10, giveback * 0.12)
        utility_hold_delta += 0.20 + mid_noise_hold_boost + min(0.14, locked_profit * 0.10)
        utility_wait_exit_delta += 0.10 + min(0.10, premature_exit_relief * 0.50)

    nas_upper_hold_bias = bool(
        symbol_u == "NAS100"
        and entry_direction == "SELL"
        and recovery_policy_id in {"range_upper_reversal_sell_nas_balanced", "breakout_retest_nas_balanced"}
        and profit > 0.0
        and not adverse_risk
        and not reached_opposite_edge
    )
    if nas_upper_hold_bias:
        utility_exit_now_delta -= 0.18 + min(0.12, giveback * 0.15)
        utility_hold_delta += 0.24 + min(0.12, locked_profit * 0.10)
        utility_wait_exit_delta += 0.10

    if lower_reversal_hold_bias:
        utility_exit_now_delta -= 0.22 + min(0.12, giveback * 0.18)
        utility_hold_delta += 0.28 + min(0.14, locked_profit * 0.10)
        utility_wait_exit_delta += 0.12

    btc_lower_hold_bias = bool(
        symbol_u == "BTCUSD"
        and entry_direction == "BUY"
        and recovery_policy_id == "range_lower_reversal_buy_btc_balanced"
        and (profit > 0.0 or peak_profit >= 0.12)
        and not adverse_risk
        and not reached_opposite_edge
        and current_box_state in {"LOWER", "BELOW", "MIDDLE"}
        and current_bb_state in {"LOWER_EDGE", "BREAKDOWN", "MID", "UNKNOWN"}
        and giveback <= max(0.22, float(max(peak_profit, profit, 0.0)) * 0.92)
    )
    if btc_lower_hold_bias:
        utility_exit_now_delta -= 0.20 + min(0.12, giveback * 0.15)
        utility_hold_delta += 0.30 + min(0.18, locked_profit * 0.10)
        utility_wait_exit_delta += 0.16

    btc_lower_mid_noise_hold_bias = bool(
        symbol_u == "BTCUSD"
        and entry_direction == "BUY"
        and recovery_policy_id == "range_lower_reversal_buy_btc_balanced"
        and not adverse_risk
        and not reached_opposite_edge
        and regime_now in {"RANGE", "UNKNOWN"}
        and current_box_state in {"LOWER", "BELOW", "MIDDLE"}
        and current_bb_state in {"LOWER_EDGE", "BREAKDOWN", "MID", "UNKNOWN"}
        and peak_profit >= 0.06
        and giveback <= max(0.20, float(max(peak_profit, profit, 0.0)) * 0.90)
    )
    if btc_lower_mid_noise_hold_bias:
        utility_exit_now_delta -= 0.18 + min(0.12, giveback * 0.13)
        utility_hold_delta += 0.24 + min(0.14, float(max(peak_profit, profit, 0.0)) * 0.10)
        utility_wait_exit_delta += 0.14

    btc_upper_tight = bool(
        symbol_u == "BTCUSD"
        and recovery_policy_id == "range_upper_reversal_sell_btc_tight"
    )
    btc_upper_support_bounce_zone = bool(
        current_box_state in {"MIDDLE", "LOWER", "BELOW"}
        and current_bb_state in {"MID", "LOWER_EDGE", "BREAKDOWN", "UNKNOWN"}
    )
    btc_upper_support_bounce_exit = bool(
        btc_upper_tight
        and profit > 0.0
        and btc_upper_support_bounce_zone
        and (
            peak_profit >= 0.18
            or giveback >= max(0.05, profit * 0.25)
            or state in {"GREEN_CLOSE", "NONE"}
        )
    )
    force_disable_wait_be = False
    force_disable_wait_tp1 = False
    recovery_override_reason = ""
    if btc_upper_tight:
        utility_exit_now_delta += 0.12
        utility_hold_delta -= 0.18
        utility_wait_exit_delta -= 0.14
        if profit > 0.0 or peak_profit >= 0.15:
            force_disable_wait_be = True
            force_disable_wait_tp1 = True
            recovery_override_reason = "btc_upper_tight_green_disable"
            utility_exit_now_delta += 0.18 + min(0.15, float(max(peak_profit, profit)) * 0.10)
            utility_hold_delta -= 0.22 + min(0.12, giveback * 0.25)
            utility_wait_exit_delta -= 0.18
    if btc_upper_support_bounce_exit:
        utility_exit_now_delta += 0.24 + min(0.18, float(max(peak_profit, profit)) * 0.10)
        utility_hold_delta -= 0.30 + min(0.18, giveback * 0.30)
        utility_wait_exit_delta -= 0.22

    return {
        "contract_version": "exit_utility_scene_bias_bundle_v1",
        "identity": {
            "symbol": str(symbol_u),
            "entry_direction": str(entry_direction),
            "recovery_policy_id": str(recovery_policy_id),
        },
        "flags": {
            "range_middle_observe": bool(range_middle_observe),
            "reached_opposite_edge": bool(reached_opposite_edge),
            "lower_reversal_hold_bias": bool(lower_reversal_hold_bias),
            "xau_lower_edge_to_edge_hold_bias": bool(xau_lower_edge_to_edge_hold_bias),
            "nas_upper_hold_bias": bool(nas_upper_hold_bias),
            "btc_lower_hold_bias": bool(btc_lower_hold_bias),
            "btc_lower_mid_noise_hold_bias": bool(btc_lower_mid_noise_hold_bias),
            "btc_upper_tight": bool(btc_upper_tight),
            "btc_upper_support_bounce_exit": bool(btc_upper_support_bounce_exit),
        },
        "utility_deltas": {
            "utility_exit_now_delta": _round6(utility_exit_now_delta, 0.0),
            "utility_hold_delta": _round6(utility_hold_delta, 0.0),
            "utility_wait_exit_delta": _round6(utility_wait_exit_delta, 0.0),
        },
        "recovery_overrides": {
            "force_disable_wait_be": bool(force_disable_wait_be),
            "force_disable_wait_tp1": bool(force_disable_wait_tp1),
            "override_reason": str(recovery_override_reason),
        },
        "symbol_edge_completion_bias_v1": dict(symbol_edge_completion_bias_v1),
        "detail": {
            "input_contract_version": _to_str(
                utility_input.get("contract_version", "exit_utility_input_v1")
            ),
            "base_bundle_contract_version": _to_str(
                base_bundle.get("contract_version", "exit_utility_base_bundle_v1")
            ),
        },
    }


def compact_exit_utility_scene_bias_bundle_v1(
    bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_map = _as_mapping(bundle)
    identity = _as_mapping(bundle_map.get("identity"))
    flags = _as_mapping(bundle_map.get("flags"))
    utility_deltas = _as_mapping(bundle_map.get("utility_deltas"))
    recovery_overrides = _as_mapping(bundle_map.get("recovery_overrides"))
    detail = _as_mapping(bundle_map.get("detail"))

    return {
        "contract_version": _to_str(
            bundle_map.get("contract_version", "exit_utility_scene_bias_bundle_v1")
        ),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "entry_direction": _to_str(identity.get("entry_direction", "")).upper(),
            "recovery_policy_id": _to_str(identity.get("recovery_policy_id", "")),
        },
        "flags": {
            "range_middle_observe": _to_bool(flags.get("range_middle_observe", False), False),
            "reached_opposite_edge": _to_bool(flags.get("reached_opposite_edge", False), False),
            "lower_reversal_hold_bias": _to_bool(
                flags.get("lower_reversal_hold_bias", False),
                False,
            ),
            "xau_lower_edge_to_edge_hold_bias": _to_bool(
                flags.get("xau_lower_edge_to_edge_hold_bias", False),
                False,
            ),
            "nas_upper_hold_bias": _to_bool(flags.get("nas_upper_hold_bias", False), False),
            "btc_lower_hold_bias": _to_bool(flags.get("btc_lower_hold_bias", False), False),
            "btc_lower_mid_noise_hold_bias": _to_bool(
                flags.get("btc_lower_mid_noise_hold_bias", False),
                False,
            ),
            "btc_upper_tight": _to_bool(flags.get("btc_upper_tight", False), False),
            "btc_upper_support_bounce_exit": _to_bool(
                flags.get("btc_upper_support_bounce_exit", False),
                False,
            ),
        },
        "utility_deltas": {
            "utility_exit_now_delta": _round6(
                utility_deltas.get("utility_exit_now_delta", 0.0),
                0.0,
            ),
            "utility_hold_delta": _round6(
                utility_deltas.get("utility_hold_delta", 0.0),
                0.0,
            ),
            "utility_wait_exit_delta": _round6(
                utility_deltas.get("utility_wait_exit_delta", 0.0),
                0.0,
            ),
        },
        "recovery_overrides": {
            "force_disable_wait_be": _to_bool(
                recovery_overrides.get("force_disable_wait_be", False),
                False,
            ),
            "force_disable_wait_tp1": _to_bool(
                recovery_overrides.get("force_disable_wait_tp1", False),
                False,
            ),
            "override_reason": _to_str(recovery_overrides.get("override_reason", "")),
        },
        "symbol_edge_completion_bias_v1": dict(
            _as_mapping(bundle_map.get("symbol_edge_completion_bias_v1"))
        ),
        "detail": {
            "input_contract_version": _to_str(detail.get("input_contract_version", "")),
            "base_bundle_contract_version": _to_str(
                detail.get("base_bundle_contract_version", "")
            ),
        },
    }
