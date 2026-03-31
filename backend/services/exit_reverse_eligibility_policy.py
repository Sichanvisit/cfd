"""Reverse eligibility helpers for exit utility decisions."""

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


def resolve_exit_reverse_eligibility_v1(
    *,
    exit_utility_input_v1: Mapping[str, Any] | None = None,
    exit_recovery_utility_bundle_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    utility_input = _as_mapping(exit_utility_input_v1)
    recovery_bundle = _as_mapping(exit_recovery_utility_bundle_v1)

    identity = _as_mapping(utility_input.get("identity"))
    risk = _as_mapping(utility_input.get("risk"))
    policy = _as_mapping(utility_input.get("policy"))
    recovery_probabilities = _as_mapping(recovery_bundle.get("probabilities"))
    recovery_utilities = _as_mapping(recovery_bundle.get("utilities"))

    state = _to_str(identity.get("state", "NONE"), "NONE").upper()
    profit = _to_float(risk.get("profit", 0.0), 0.0)
    adverse_risk = _to_bool(risk.get("adverse_risk", False), False)
    duration_sec = _to_float(risk.get("duration_sec", 0.0), 0.0)
    score_gap = abs(_to_float(risk.get("score_gap", 0.0), 0.0))
    prefer_reverse = _to_bool(policy.get("prefer_reverse", False), False)
    reverse_gap_required = max(1, int(_to_float(policy.get("reverse_gap_required", 0), 0.0)))
    reverse_min_prob = max(0.05, _to_float(policy.get("reverse_min_prob", 0.58), 0.58))
    reverse_min_hold_seconds = max(
        0.0,
        _to_float(policy.get("reverse_min_hold_seconds", 45.0), 45.0),
    )
    p_reverse_valid = _to_float(
        recovery_probabilities.get("p_reverse_valid", 0.25),
        0.25,
    )
    u_reverse_candidate = _to_float(
        recovery_utilities.get("u_reverse_candidate", 0.0),
        0.0,
    )

    reverse_reason = ""
    reverse_eligible = False

    if profit >= 0.0:
        reverse_reason = "profit_non_negative"
    elif not adverse_risk:
        reverse_reason = "adverse_risk_required"
    elif duration_sec < reverse_min_hold_seconds:
        reverse_reason = "reverse_min_hold_not_met"
    elif p_reverse_valid < reverse_min_prob:
        reverse_reason = "reverse_prob_below_min"
    elif score_gap < reverse_gap_required:
        reverse_reason = "reverse_score_gap_below_min"
    elif state == "REVERSE_READY":
        reverse_eligible = True
        reverse_reason = "reverse_ready"
    elif state == "REVERSAL_CONFIRM":
        if not prefer_reverse:
            reverse_reason = "prefer_reverse_required"
        elif score_gap < float(reverse_gap_required + 4):
            reverse_reason = "reversal_confirm_gap_extension_not_met"
        else:
            reverse_eligible = True
            reverse_reason = "reversal_confirm_prefer_reverse"
    else:
        reverse_reason = "state_not_reverse_ready"

    reverse_bonus = 0.04 if reverse_eligible and prefer_reverse else 0.0
    u_reverse = -999.0 if not reverse_eligible else (u_reverse_candidate + reverse_bonus)

    return {
        "contract_version": "exit_reverse_eligibility_v1",
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "state": str(state),
        },
        "thresholds": {
            "reverse_gap_required": int(reverse_gap_required),
            "reverse_min_prob": _round6(reverse_min_prob, 0.58),
            "reverse_min_hold_seconds": _round6(reverse_min_hold_seconds, 45.0),
        },
        "inputs": {
            "profit": _round6(profit, 0.0),
            "adverse_risk": bool(adverse_risk),
            "duration_sec": _round6(duration_sec, 0.0),
            "score_gap": _round6(score_gap, 0.0),
            "prefer_reverse": bool(prefer_reverse),
            "p_reverse_valid": _round6(p_reverse_valid, 0.25),
        },
        "result": {
            "reverse_eligible": bool(reverse_eligible),
            "reverse_reason": str(reverse_reason),
            "reverse_bonus": _round6(reverse_bonus, 0.0),
            "u_reverse_candidate": _round6(u_reverse_candidate, 0.0),
            "u_reverse": _round6(u_reverse, 0.0),
        },
        "detail": {
            "input_contract_version": _to_str(
                utility_input.get("contract_version", "exit_utility_input_v1")
            ),
            "recovery_bundle_contract_version": _to_str(
                recovery_bundle.get("contract_version", "exit_recovery_utility_bundle_v1")
            ),
        },
    }


def compact_exit_reverse_eligibility_v1(
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy_map = _as_mapping(policy)
    identity = _as_mapping(policy_map.get("identity"))
    thresholds = _as_mapping(policy_map.get("thresholds"))
    inputs = _as_mapping(policy_map.get("inputs"))
    result = _as_mapping(policy_map.get("result"))
    detail = _as_mapping(policy_map.get("detail"))

    return {
        "contract_version": _to_str(
            policy_map.get("contract_version", "exit_reverse_eligibility_v1")
        ),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "state": _to_str(identity.get("state", "NONE"), "NONE").upper(),
        },
        "thresholds": {
            "reverse_gap_required": int(_to_float(thresholds.get("reverse_gap_required", 0), 0.0)),
            "reverse_min_prob": _round6(thresholds.get("reverse_min_prob", 0.0), 0.0),
            "reverse_min_hold_seconds": _round6(
                thresholds.get("reverse_min_hold_seconds", 0.0),
                0.0,
            ),
        },
        "inputs": {
            "profit": _round6(inputs.get("profit", 0.0), 0.0),
            "adverse_risk": _to_bool(inputs.get("adverse_risk", False), False),
            "duration_sec": _round6(inputs.get("duration_sec", 0.0), 0.0),
            "score_gap": _round6(inputs.get("score_gap", 0.0), 0.0),
            "prefer_reverse": _to_bool(inputs.get("prefer_reverse", False), False),
            "p_reverse_valid": _round6(inputs.get("p_reverse_valid", 0.0), 0.0),
        },
        "result": {
            "reverse_eligible": _to_bool(result.get("reverse_eligible", False), False),
            "reverse_reason": _to_str(result.get("reverse_reason", "")),
            "reverse_bonus": _round6(result.get("reverse_bonus", 0.0), 0.0),
            "u_reverse_candidate": _round6(result.get("u_reverse_candidate", 0.0), 0.0),
            "u_reverse": _round6(result.get("u_reverse", 0.0), 0.0),
        },
        "detail": {
            "input_contract_version": _to_str(detail.get("input_contract_version", "")),
            "recovery_bundle_contract_version": _to_str(
                detail.get("recovery_bundle_contract_version", "")
            ),
        },
    }
