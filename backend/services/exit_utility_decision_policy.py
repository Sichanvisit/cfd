"""Final winner and decision-policy helpers for exit utility decisions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.services.utility_router import select_utility_winner


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


def resolve_exit_utility_decision_policy_v1(
    *,
    exit_utility_input_v1: Mapping[str, Any] | None = None,
    utility_candidates_v1: Mapping[str, Any] | None = None,
    exit_utility_scene_bias_bundle_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    utility_input = _as_mapping(exit_utility_input_v1)
    candidates = _as_mapping(utility_candidates_v1)
    scene_bundle = _as_mapping(exit_utility_scene_bias_bundle_v1)

    identity = _as_mapping(utility_input.get("identity"))
    risk = _as_mapping(utility_input.get("risk"))
    scene_flags = _as_mapping(scene_bundle.get("flags"))

    state = _to_str(identity.get("state", "NONE"), "NONE").upper()
    profit = _to_float(risk.get("profit", 0.0), 0.0)
    btc_upper_support_bounce_exit = _to_bool(
        scene_flags.get("btc_upper_support_bounce_exit", False),
        False,
    )

    utility_exit_now = _to_float(candidates.get("utility_exit_now", 0.0), 0.0)
    utility_hold = _to_float(candidates.get("utility_hold", 0.0), 0.0)
    utility_reverse = _to_float(candidates.get("utility_reverse", 0.0), 0.0)
    utility_wait_exit = _to_float(candidates.get("utility_wait_exit", 0.0), 0.0)
    u_cut_now = _to_float(candidates.get("u_cut_now", 0.0), 0.0)
    u_wait_be = _to_float(candidates.get("u_wait_be", 0.0), 0.0)
    u_wait_tp1 = _to_float(candidates.get("u_wait_tp1", 0.0), 0.0)
    u_reverse = _to_float(candidates.get("u_reverse", 0.0), 0.0)

    if profit < 0.0 or state in {"RECOVERY_BE", "RECOVERY_TP1", "CUT_IMMEDIATE", "REVERSE_READY", "REVERSAL_CONFIRM"}:
        decision_mode = "recovery_path"
        winner, winner_value = select_utility_winner(
            {
                "cut_now": float(u_cut_now),
                "wait_be": float(u_wait_be),
                "wait_tp1": float(u_wait_tp1),
                "reverse_now": float(u_reverse),
            },
            priority=["cut_now", "wait_be", "wait_tp1", "reverse_now"],
        )
        decision_reason = {
            "cut_now": "cut_now_best",
            "wait_be": "wait_be_recovery",
            "wait_tp1": "wait_tp1_recovery",
            "reverse_now": "reverse_now_best",
        }.get(winner, "exit_recovery_shadow_unknown")
    else:
        decision_mode = "profit_path"
        winner, winner_value = select_utility_winner(
            {
                "exit_now": float(utility_exit_now),
                "hold": float(utility_hold),
                "reverse": float(utility_reverse),
                "wait_exit": float(utility_wait_exit),
            },
            priority=["exit_now", "wait_exit", "reverse", "hold"],
        )
        decision_reason = {
            "exit_now": "exit_now_best",
            "hold": "hold_best",
            "reverse": "reverse_best",
            "wait_exit": (
                "wait_exit_green_close"
                if state == "GREEN_CLOSE"
                else ("wait_exit_reversal_confirm" if state == "REVERSAL_CONFIRM" else "wait_exit_recovery")
            ),
        }.get(winner, "exit_shadow_unknown")
        if winner == "exit_now" and btc_upper_support_bounce_exit:
            decision_reason = "exit_now_support_bounce"

    wait_selected = bool(winner in {"wait_exit", "wait_be", "wait_tp1"})
    wait_decision = str(decision_reason if wait_selected else "")

    return {
        "contract_version": "exit_utility_decision_policy_v1",
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "state": str(state),
            "decision_mode": str(decision_mode),
        },
        "result": {
            "winner": str(winner),
            "winner_value": _round6(winner_value, 0.0),
            "decision_reason": str(decision_reason),
            "wait_selected": bool(wait_selected),
            "wait_decision": str(wait_decision),
        },
        "taxonomy_input": {
            "winner": str(winner),
            "decision_reason": str(decision_reason),
            "wait_selected": bool(wait_selected),
            "wait_decision": str(wait_decision),
        },
        "detail": {
            "input_contract_version": _to_str(
                utility_input.get("contract_version", "exit_utility_input_v1")
            ),
            "scene_bundle_contract_version": _to_str(
                scene_bundle.get("contract_version", "exit_utility_scene_bias_bundle_v1")
            ),
        },
    }


def compact_exit_utility_decision_policy_v1(
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy_map = _as_mapping(policy)
    identity = _as_mapping(policy_map.get("identity"))
    result = _as_mapping(policy_map.get("result"))
    detail = _as_mapping(policy_map.get("detail"))

    return {
        "contract_version": _to_str(
            policy_map.get("contract_version", "exit_utility_decision_policy_v1")
        ),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "state": _to_str(identity.get("state", "NONE"), "NONE").upper(),
            "decision_mode": _to_str(identity.get("decision_mode", "")),
        },
        "result": {
            "winner": _to_str(result.get("winner", "")),
            "winner_value": _round6(result.get("winner_value", 0.0), 0.0),
            "decision_reason": _to_str(result.get("decision_reason", "")),
            "wait_selected": _to_bool(result.get("wait_selected", False), False),
            "wait_decision": _to_str(result.get("wait_decision", "")),
        },
        "detail": {
            "input_contract_version": _to_str(detail.get("input_contract_version", "")),
            "scene_bundle_contract_version": _to_str(
                detail.get("scene_bundle_contract_version", "")
            ),
        },
    }
