"""Base utility bundle helpers for exit utility decision construction."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.services.utility_router import (
    compute_exit_utility,
    compute_hold_utility,
    compute_reverse_utility,
    compute_wait_utility,
)


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


def _round6(value: object, default: float = 0.0) -> float:
    return round(_to_float(value, default), 6)


def resolve_exit_utility_base_bundle_v1(
    *,
    exit_utility_input_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = _as_mapping(exit_utility_input_v1)
    identity = _as_mapping(contract.get("identity"))
    risk = _as_mapping(contract.get("risk"))
    prediction = _as_mapping(contract.get("prediction"))

    profit = _to_float(risk.get("profit", 0.0), 0.0)
    giveback = _to_float(risk.get("giveback", 0.0), 0.0)
    score_gap = abs(_to_float(risk.get("score_gap", 0.0), 0.0))
    adverse_risk = bool(risk.get("adverse_risk", False))
    duration_sec = _to_float(risk.get("duration_sec", 0.0), 0.0)
    roundtrip_cost = _to_float(risk.get("roundtrip_cost", 0.0), 0.0)
    state = _to_str(identity.get("state", "NONE"), "NONE").upper()
    exit_profile_id = _to_str(identity.get("exit_profile_id", ""), "").lower()

    locked_profit = max(0.0, float(profit))
    upside = max(
        0.10,
        (0.25 if locked_profit > 0.0 else 0.15)
        + min(1.25, float(score_gap) / 40.0)
        + (0.10 if exit_profile_id in {"aggressive", "hold_then_trail"} else 0.0),
    )
    giveback_cost = max(0.05, float(giveback) + (0.18 if adverse_risk else 0.08))
    reverse_edge = max(
        0.10,
        min(1.50, float(score_gap) / 32.0)
        + (0.22 if adverse_risk else 0.0)
        + (0.10 if state == "REVERSAL_CONFIRM" else 0.0),
    )
    wait_improvement = _to_float(
        prediction.get("expected_exit_improvement", 0.0),
        0.0,
    )
    wait_miss_cost = _to_float(prediction.get("expected_miss_cost", 0.12), 0.12)
    wait_extra_penalty = max(0.0, 0.03 if duration_sec > 1800 else 0.0)
    p_more_profit = _to_float(prediction.get("p_more_profit", 0.5), 0.5)
    p_giveback = _to_float(prediction.get("p_giveback", 0.4), 0.4)
    p_reverse_valid = _to_float(prediction.get("p_reverse_valid", 0.25), 0.25)
    p_better_exit_if_wait = _to_float(prediction.get("p_better_exit_if_wait", 0.10), 0.10)

    utility_exit_now = compute_exit_utility(
        locked_profit=locked_profit,
        exit_cost=float(roundtrip_cost),
    )
    utility_hold = compute_hold_utility(
        p_more_profit=float(p_more_profit),
        upside=float(upside),
        p_giveback=float(p_giveback),
        giveback=float(giveback_cost),
    )
    utility_reverse = compute_reverse_utility(
        p_reverse_valid=float(p_reverse_valid),
        reverse_edge=float(reverse_edge),
        reverse_cost=max(0.05, float(roundtrip_cost)),
    )
    utility_wait_exit = compute_wait_utility(
        p_better_entry_if_wait=float(p_better_exit_if_wait),
        expected_entry_improvement=float(wait_improvement),
        expected_miss_cost=float(wait_miss_cost),
        extra_penalty=float(wait_extra_penalty),
    )

    return {
        "contract_version": "exit_utility_base_bundle_v1",
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "state": str(state),
            "exit_profile_id": str(exit_profile_id),
        },
        "inputs": {
            "locked_profit": _round6(locked_profit, 0.0),
            "upside": _round6(upside, 0.0),
            "giveback_cost": _round6(giveback_cost, 0.0),
            "reverse_edge": _round6(reverse_edge, 0.0),
            "wait_improvement": _round6(wait_improvement, 0.0),
            "wait_miss_cost": _round6(wait_miss_cost, 0.12),
            "wait_extra_penalty": _round6(wait_extra_penalty, 0.0),
        },
        "probabilities": {
            "p_more_profit": _round6(p_more_profit, 0.5),
            "p_giveback": _round6(p_giveback, 0.4),
            "p_reverse_valid": _round6(p_reverse_valid, 0.25),
            "p_better_exit_if_wait": _round6(p_better_exit_if_wait, 0.10),
        },
        "utilities": {
            "utility_exit_now": _round6(utility_exit_now, 0.0),
            "utility_hold": _round6(utility_hold, 0.0),
            "utility_reverse": _round6(utility_reverse, 0.0),
            "utility_wait_exit": _round6(utility_wait_exit, 0.0),
        },
        "detail": {
            "input_contract_version": _to_str(
                contract.get("contract_version", "exit_utility_input_v1")
            ),
        },
    }


def compact_exit_utility_base_bundle_v1(
    bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_map = _as_mapping(bundle)
    identity = _as_mapping(bundle_map.get("identity"))
    inputs = _as_mapping(bundle_map.get("inputs"))
    probabilities = _as_mapping(bundle_map.get("probabilities"))
    utilities = _as_mapping(bundle_map.get("utilities"))
    detail = _as_mapping(bundle_map.get("detail"))

    return {
        "contract_version": _to_str(
            bundle_map.get("contract_version", "exit_utility_base_bundle_v1")
        ),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "state": _to_str(identity.get("state", "NONE"), "NONE").upper(),
            "exit_profile_id": _to_str(identity.get("exit_profile_id", "")),
        },
        "inputs": {
            "locked_profit": _round6(inputs.get("locked_profit", 0.0), 0.0),
            "upside": _round6(inputs.get("upside", 0.0), 0.0),
            "giveback_cost": _round6(inputs.get("giveback_cost", 0.0), 0.0),
            "reverse_edge": _round6(inputs.get("reverse_edge", 0.0), 0.0),
            "wait_improvement": _round6(inputs.get("wait_improvement", 0.0), 0.0),
            "wait_miss_cost": _round6(inputs.get("wait_miss_cost", 0.0), 0.0),
            "wait_extra_penalty": _round6(inputs.get("wait_extra_penalty", 0.0), 0.0),
        },
        "probabilities": {
            "p_more_profit": _round6(probabilities.get("p_more_profit", 0.0), 0.0),
            "p_giveback": _round6(probabilities.get("p_giveback", 0.0), 0.0),
            "p_reverse_valid": _round6(probabilities.get("p_reverse_valid", 0.0), 0.0),
            "p_better_exit_if_wait": _round6(
                probabilities.get("p_better_exit_if_wait", 0.0),
                0.0,
            ),
        },
        "utilities": {
            "utility_exit_now": _round6(utilities.get("utility_exit_now", 0.0), 0.0),
            "utility_hold": _round6(utilities.get("utility_hold", 0.0), 0.0),
            "utility_reverse": _round6(utilities.get("utility_reverse", 0.0), 0.0),
            "utility_wait_exit": _round6(utilities.get("utility_wait_exit", 0.0), 0.0),
        },
        "detail": {
            "input_contract_version": _to_str(detail.get("input_contract_version", "")),
        },
    }
