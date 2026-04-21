"""Recovery utility bundle helpers for exit utility decisions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.core.config import Config
from backend.services.utility_router import compute_reverse_utility


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


def resolve_exit_recovery_utility_bundle_v1(
    *,
    exit_utility_input_v1: Mapping[str, Any] | None = None,
    exit_utility_base_bundle_v1: Mapping[str, Any] | None = None,
    recovery_predictions: Mapping[str, Any] | None = None,
    lower_reversal_hold_bias: bool = False,
) -> dict[str, Any]:
    utility_input = _as_mapping(exit_utility_input_v1)
    base_bundle = _as_mapping(exit_utility_base_bundle_v1)
    recovery_predictions_map = _as_mapping(recovery_predictions)

    identity = _as_mapping(utility_input.get("identity"))
    risk = _as_mapping(utility_input.get("risk"))
    policy = _as_mapping(utility_input.get("policy"))
    bias = _as_mapping(utility_input.get("bias"))
    prediction = _as_mapping(utility_input.get("prediction"))
    base_inputs = _as_mapping(base_bundle.get("inputs"))

    profit = _to_float(risk.get("profit", 0.0), 0.0)
    peak_profit = _to_float(risk.get("peak_profit", profit), profit)
    giveback = _to_float(risk.get("giveback", max(0.0, peak_profit - profit)), 0.0)
    roundtrip_cost = _to_float(risk.get("roundtrip_cost", 0.0), 0.0)
    exit_profile_id = _to_str(identity.get("exit_profile_id", ""), "").lower()
    state_execution_bias = _as_mapping(bias.get("state_execution_bias_v1"))
    countertrend_with_entry = _to_bool(
        state_execution_bias.get("countertrend_with_entry", False),
        False,
    )
    topdown_state_label = _to_str(
        state_execution_bias.get("topdown_state_label", ""),
        "",
    ).upper()

    allow_wait_be_initial = _to_bool(policy.get("allow_wait_be", True), True)
    allow_wait_tp1_initial = _to_bool(policy.get("allow_wait_tp1", False), False)

    p_recover_be = _to_float(recovery_predictions_map.get("p_recover_be", 0.10), 0.10)
    p_recover_tp1 = _to_float(recovery_predictions_map.get("p_recover_tp1", 0.08), 0.08)
    p_deeper_loss = _to_float(recovery_predictions_map.get("p_deeper_loss", 0.30), 0.30)
    p_reverse_valid = _to_float(
        recovery_predictions_map.get(
            "p_reverse_valid",
            prediction.get("p_reverse_valid", 0.25),
        ),
        0.25,
    )

    be_recovery_gain = max(0.10, abs(float(profit)))
    tp1_recovery_gain = max(0.10, (abs(float(profit)) * 1.30) + 0.05)
    cut_penalty = max(0.0, abs(min(0.0, profit)))
    deeper_loss_cost = max(0.10, abs(min(0.0, profit)) * 1.25 + 0.08)

    u_cut_now = -float(cut_penalty)
    u_wait_be = float((p_recover_be * be_recovery_gain) - (p_deeper_loss * deeper_loss_cost) - 0.03)
    u_wait_tp1 = float((p_recover_tp1 * tp1_recovery_gain) - (p_deeper_loss * deeper_loss_cost) - 0.06)
    u_reverse_candidate = compute_reverse_utility(
        p_reverse_valid=float(p_reverse_valid),
        reverse_edge=float(_to_float(base_inputs.get("reverse_edge", 0.10), 0.10)),
        reverse_cost=max(0.05, float(roundtrip_cost)),
    )

    if _to_bool(state_execution_bias.get("prefer_fast_cut", False), False):
        exit_pressure = _to_float(state_execution_bias.get("exit_pressure", 0.0), 0.0)
        u_wait_be -= 0.06 + min(0.08, exit_pressure * 0.35)
        u_wait_tp1 -= 0.08 + min(0.10, exit_pressure * 0.40)

    allow_wait_be_effective = bool(allow_wait_be_initial)
    allow_wait_tp1_effective = bool(allow_wait_tp1_initial)
    wait_be_disable_reason = ""
    wait_tp1_disable_reason = ""

    if not allow_wait_be_effective:
        wait_be_disable_reason = "policy_disallow_wait_be"
        u_wait_be = -999.0
    if not allow_wait_tp1_effective:
        wait_tp1_disable_reason = "policy_disallow_wait_tp1"
        u_wait_tp1 = -999.0

    tight_green_peak_threshold = max(
        0.05,
        float(getattr(Config, "EXIT_TIGHT_PROTECT_GREEN_PEAK_MIN_USD", 0.50)),
    )
    tight_protect_green_disable = bool(
        exit_profile_id == "tight_protect"
        and float(peak_profit) >= float(tight_green_peak_threshold)
        and not bool(lower_reversal_hold_bias)
    )
    if tight_protect_green_disable:
        allow_wait_be_effective = False
        allow_wait_tp1_effective = False
        wait_be_disable_reason = "tight_protect_green_disable"
        wait_tp1_disable_reason = "tight_protect_green_disable"
        u_wait_be = -999.0
        u_wait_tp1 = -999.0

    countertrend_no_green_fast_cut = bool(
        _to_bool(getattr(Config, "EXIT_COUNTERTREND_NO_GREEN_FAST_CUT_ENABLED", True), True)
        and countertrend_with_entry
        and topdown_state_label in {"BULL_CONFLUENCE", "BEAR_CONFLUENCE", "TOPDOWN_CONFLICT"}
        and profit < 0.0
        and peak_profit <= _to_float(getattr(Config, "EXIT_COUNTERTREND_NO_GREEN_MAX_PEAK_USD", 0.10), 0.10)
        and not bool(lower_reversal_hold_bias)
    )
    if countertrend_no_green_fast_cut:
        allow_wait_be_effective = False
        allow_wait_tp1_effective = False
        wait_be_disable_reason = "countertrend_no_green_fast_cut"
        wait_tp1_disable_reason = "countertrend_no_green_fast_cut"
        u_wait_be = -999.0
        u_wait_tp1 = -999.0

    return {
        "contract_version": "exit_recovery_utility_bundle_v1",
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "state": _to_str(identity.get("state", "NONE"), "NONE").upper(),
            "exit_profile_id": str(exit_profile_id),
        },
        "probabilities": {
            "p_recover_be": _round6(p_recover_be, 0.10),
            "p_recover_tp1": _round6(p_recover_tp1, 0.08),
            "p_deeper_loss": _round6(p_deeper_loss, 0.30),
            "p_reverse_valid": _round6(p_reverse_valid, 0.25),
        },
        "inputs": {
            "be_recovery_gain": _round6(be_recovery_gain, 0.10),
            "tp1_recovery_gain": _round6(tp1_recovery_gain, 0.10),
            "cut_penalty": _round6(cut_penalty, 0.0),
            "deeper_loss_cost": _round6(deeper_loss_cost, 0.10),
            "roundtrip_cost": _round6(roundtrip_cost, 0.0),
            "peak_profit": _round6(peak_profit, profit),
            "giveback": _round6(giveback, 0.0),
            "tight_green_peak_threshold": _round6(tight_green_peak_threshold, 0.50),
        },
        "gating": {
            "allow_wait_be_initial": bool(allow_wait_be_initial),
            "allow_wait_tp1_initial": bool(allow_wait_tp1_initial),
            "allow_wait_be_effective": bool(allow_wait_be_effective),
            "allow_wait_tp1_effective": bool(allow_wait_tp1_effective),
            "wait_be_disable_reason": str(wait_be_disable_reason),
            "wait_tp1_disable_reason": str(wait_tp1_disable_reason),
            "tight_protect_green_disable": bool(tight_protect_green_disable),
            "countertrend_no_green_fast_cut": bool(countertrend_no_green_fast_cut),
        },
        "utilities": {
            "u_cut_now": _round6(u_cut_now, 0.0),
            "u_wait_be": _round6(u_wait_be, 0.0),
            "u_wait_tp1": _round6(u_wait_tp1, 0.0),
            "u_reverse_candidate": _round6(u_reverse_candidate, 0.0),
        },
        "detail": {
            "input_contract_version": _to_str(
                utility_input.get("contract_version", "exit_utility_input_v1")
            ),
            "base_bundle_contract_version": _to_str(
                base_bundle.get("contract_version", "exit_utility_base_bundle_v1")
            ),
        },
    }


def compact_exit_recovery_utility_bundle_v1(
    bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_map = _as_mapping(bundle)
    identity = _as_mapping(bundle_map.get("identity"))
    probabilities = _as_mapping(bundle_map.get("probabilities"))
    inputs = _as_mapping(bundle_map.get("inputs"))
    gating = _as_mapping(bundle_map.get("gating"))
    utilities = _as_mapping(bundle_map.get("utilities"))
    detail = _as_mapping(bundle_map.get("detail"))

    return {
        "contract_version": _to_str(
            bundle_map.get("contract_version", "exit_recovery_utility_bundle_v1")
        ),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "state": _to_str(identity.get("state", "NONE"), "NONE").upper(),
            "exit_profile_id": _to_str(identity.get("exit_profile_id", "")),
        },
        "probabilities": {
            "p_recover_be": _round6(probabilities.get("p_recover_be", 0.0), 0.0),
            "p_recover_tp1": _round6(probabilities.get("p_recover_tp1", 0.0), 0.0),
            "p_deeper_loss": _round6(probabilities.get("p_deeper_loss", 0.0), 0.0),
            "p_reverse_valid": _round6(probabilities.get("p_reverse_valid", 0.0), 0.0),
        },
        "inputs": {
            "be_recovery_gain": _round6(inputs.get("be_recovery_gain", 0.0), 0.0),
            "tp1_recovery_gain": _round6(inputs.get("tp1_recovery_gain", 0.0), 0.0),
            "cut_penalty": _round6(inputs.get("cut_penalty", 0.0), 0.0),
            "deeper_loss_cost": _round6(inputs.get("deeper_loss_cost", 0.0), 0.0),
        },
        "gating": {
            "allow_wait_be_initial": _to_bool(gating.get("allow_wait_be_initial", False), False),
            "allow_wait_tp1_initial": _to_bool(gating.get("allow_wait_tp1_initial", False), False),
            "allow_wait_be_effective": _to_bool(gating.get("allow_wait_be_effective", False), False),
            "allow_wait_tp1_effective": _to_bool(gating.get("allow_wait_tp1_effective", False), False),
            "wait_be_disable_reason": _to_str(gating.get("wait_be_disable_reason", "")),
            "wait_tp1_disable_reason": _to_str(gating.get("wait_tp1_disable_reason", "")),
            "tight_protect_green_disable": _to_bool(
                gating.get("tight_protect_green_disable", False),
                False,
            ),
            "countertrend_no_green_fast_cut": _to_bool(
                gating.get("countertrend_no_green_fast_cut", False),
                False,
            ),
        },
        "utilities": {
            "u_cut_now": _round6(utilities.get("u_cut_now", 0.0), 0.0),
            "u_wait_be": _round6(utilities.get("u_wait_be", 0.0), 0.0),
            "u_wait_tp1": _round6(utilities.get("u_wait_tp1", 0.0), 0.0),
            "u_reverse_candidate": _round6(
                utilities.get("u_reverse_candidate", 0.0),
                0.0,
            ),
        },
        "detail": {
            "input_contract_version": _to_str(detail.get("input_contract_version", "")),
            "base_bundle_contract_version": _to_str(
                detail.get("base_bundle_contract_version", "")
            ),
        },
    }
