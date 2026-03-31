"""Shared runtime sink contract helpers for exit manage execution seams."""

from __future__ import annotations

import json
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


def build_exit_manage_runtime_sink_v1(
    *,
    exit_manage_execution_input_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = _as_mapping(exit_manage_execution_input_v1)
    identity = _as_mapping(contract.get("identity"))
    handoff = _as_mapping(contract.get("handoff"))
    posture = _as_mapping(contract.get("posture"))
    decision = _as_mapping(contract.get("decision"))
    wait_state = _as_mapping(contract.get("wait_state"))
    wait_taxonomy = _as_mapping(contract.get("wait_taxonomy"))
    thresholds = _as_mapping(contract.get("thresholds"))
    route = _as_mapping(contract.get("route"))
    regime = _as_mapping(contract.get("regime"))
    performance = _as_mapping(contract.get("performance"))
    shock = _as_mapping(contract.get("shock"))
    runtime = _as_mapping(contract.get("runtime"))

    shock_progress = _as_mapping(shock.get("progress"))
    exit_prediction = _as_mapping(runtime.get("exit_prediction_v1"))
    effective_exit_profile = _to_str(posture.get("effective_exit_profile", ""))

    trade_logger_payload = {
        "entry_setup_id": _to_str(identity.get("entry_setup_id", "")),
        "management_profile_id": _to_str(handoff.get("management_profile_id", "")),
        "invalidation_id": _to_str(handoff.get("invalidation_id", "")),
        "exit_profile": effective_exit_profile,
        "decision_winner": _to_str(decision.get("winner", "")),
        "decision_reason": _to_str(decision.get("decision_reason", "")),
        "utility_exit_now": _to_float(decision.get("utility_exit_now", 0.0), 0.0),
        "utility_hold": _to_float(decision.get("utility_hold", 0.0), 0.0),
        "utility_reverse": _to_float(decision.get("utility_reverse", 0.0), 0.0),
        "utility_wait_exit": _to_float(decision.get("utility_wait_exit", 0.0), 0.0),
        "u_cut_now": _to_float(decision.get("u_cut_now", 0.0), 0.0),
        "u_wait_be": _to_float(decision.get("u_wait_be", 0.0), 0.0),
        "u_wait_tp1": _to_float(decision.get("u_wait_tp1", 0.0), 0.0),
        "u_reverse": _to_float(decision.get("u_reverse", 0.0), 0.0),
        "p_recover_be": _to_float(decision.get("p_recover_be", 0.0), 0.0),
        "p_recover_tp1": _to_float(decision.get("p_recover_tp1", 0.0), 0.0),
        "p_deeper_loss": _to_float(decision.get("p_deeper_loss", 0.0), 0.0),
        "p_reverse_valid": _to_float(decision.get("p_reverse_valid", 0.0), 0.0),
        "exit_wait_selected": int(1 if _to_bool(decision.get("wait_selected", False), False) else 0),
        "exit_wait_decision": _to_str(decision.get("wait_decision", "")),
        "exit_wait_state_family": _to_str(wait_taxonomy.get("state_family", "")),
        "exit_wait_hold_class": _to_str(wait_taxonomy.get("hold_class", "")),
        "exit_wait_decision_family": _to_str(wait_taxonomy.get("decision_family", "")),
        "exit_wait_bridge_status": _to_str(wait_taxonomy.get("bridge_status", "")),
        "final_outcome": _to_str(decision.get("final_outcome", "")),
        "exit_policy_stage": _to_str(posture.get("policy_stage", "")),
        "exit_policy_selector_stage": _to_str(posture.get("chosen_stage", "auto"), "auto"),
        "exit_policy_profile": _to_str(posture.get("execution_profile", "")),
        "exit_wait_state": _to_str(wait_state.get("state", "")),
        "prediction_bundle": json.dumps(
            exit_prediction,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "exit_policy_regime": _to_str(regime.get("name", "")),
        "exit_policy_regime_observed": _to_str(regime.get("observed", "")),
        "exit_policy_regime_switch": _to_str(regime.get("switch_detail", "")),
        "exit_threshold_triplet": _to_str(thresholds.get("exit_threshold_triplet", "")),
        "exit_confirm_ticks_applied": _to_int(thresholds.get("confirm_needed", 0), 0),
        "exit_route_ev": str(route.get("ev", {})),
        "exit_confidence": _to_float(route.get("confidence", 0.0), 0.0),
        "exit_delay_ticks": _to_int(thresholds.get("delay_ticks", 0), 0),
        "peak_profit_at_exit": _to_float(performance.get("peak_profit_at_exit", 0.0), 0.0),
        "giveback_usd": _to_float(performance.get("giveback_usd", 0.0), 0.0),
        "shock_score": _to_float(shock.get("shock_score", 0.0), 0.0),
        "shock_level": _to_str(shock.get("shock_level", "")),
        "shock_reason": _to_str(shock.get("shock_reason", "")),
        "shock_action": _to_str(shock.get("shock_action", "")),
        "pre_shock_stage": _to_str(shock.get("pre_shock_stage", "")),
        "post_shock_stage": _to_str(shock.get("post_shock_stage", "")),
        "shock_at_profit": _to_float(shock.get("shock_at_profit", 0.0), 0.0),
        **dict(shock_progress),
    }

    live_metrics_payload = {
        "decision_winner": _to_str(decision.get("winner", "")),
        "utility_exit_now": _to_float(decision.get("utility_exit_now", 0.0), 0.0),
        "utility_hold": _to_float(decision.get("utility_hold", 0.0), 0.0),
        "utility_reverse": _to_float(decision.get("utility_reverse", 0.0), 0.0),
        "utility_wait_exit": _to_float(decision.get("utility_wait_exit", 0.0), 0.0),
        "u_cut_now": _to_float(decision.get("u_cut_now", 0.0), 0.0),
        "u_wait_be": _to_float(decision.get("u_wait_be", 0.0), 0.0),
        "u_wait_tp1": _to_float(decision.get("u_wait_tp1", 0.0), 0.0),
        "u_reverse": _to_float(decision.get("u_reverse", 0.0), 0.0),
        "exit_policy_stage": _to_str(posture.get("policy_stage", "")),
        "exit_policy_profile": _to_str(posture.get("execution_profile", "")),
        "exit_profile": effective_exit_profile,
        "exit_wait_state": _to_str(wait_state.get("state", "")),
        "exit_wait_selected": int(1 if _to_bool(decision.get("wait_selected", False), False) else 0),
        "exit_wait_decision": _to_str(decision.get("wait_decision", "")),
        "exit_wait_state_family": _to_str(wait_taxonomy.get("state_family", "")),
        "exit_wait_hold_class": _to_str(wait_taxonomy.get("hold_class", "")),
        "exit_wait_decision_family": _to_str(wait_taxonomy.get("decision_family", "")),
        "exit_wait_bridge_status": _to_str(wait_taxonomy.get("bridge_status", "")),
        "p_recover_be": _to_float(decision.get("p_recover_be", 0.0), 0.0),
        "p_recover_tp1": _to_float(decision.get("p_recover_tp1", 0.0), 0.0),
        "p_deeper_loss": _to_float(decision.get("p_deeper_loss", 0.0), 0.0),
        "p_reverse_valid": _to_float(decision.get("p_reverse_valid", 0.0), 0.0),
        "exit_policy_regime": _to_str(regime.get("name", "")),
        "exit_threshold_triplet": _to_str(thresholds.get("exit_threshold_triplet", "")),
        "exit_route_ev": str(route.get("ev", {})),
        "exit_confidence": _to_float(route.get("confidence", 0.0), 0.0),
        "exit_delay_ticks": _to_int(thresholds.get("delay_ticks", 0), 0),
        "peak_profit_at_exit": _to_float(performance.get("peak_profit_at_exit", 0.0), 0.0),
        "giveback_usd": _to_float(performance.get("giveback_usd", 0.0), 0.0),
        "shock_score": _to_float(shock.get("shock_score", 0.0), 0.0),
        "shock_hold_delta_30": _to_float(shock_progress.get("shock_hold_delta_30", 0.0), 0.0),
    }

    return {
        "contract_version": "exit_manage_runtime_sink_v1",
        "summary": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "ticket": _to_int(identity.get("ticket", 0), 0),
            "decision_winner": _to_str(decision.get("winner", "")),
            "exit_profile": effective_exit_profile,
            "exit_wait_state": _to_str(wait_state.get("state", "")),
            "exit_wait_decision": _to_str(decision.get("wait_decision", "")),
            "exit_policy_stage": _to_str(posture.get("policy_stage", "")),
            "exit_policy_regime": _to_str(regime.get("name", "")),
            "shock_score": _to_float(shock.get("shock_score", 0.0), 0.0),
        },
        "trade_logger_payload": trade_logger_payload,
        "live_metrics_payload": live_metrics_payload,
    }


def compact_exit_manage_runtime_sink_v1(
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract_map = _as_mapping(contract)
    return {
        "contract_version": _to_str(
            contract_map.get("contract_version", "exit_manage_runtime_sink_v1")
        ),
        "summary": dict(_as_mapping(contract_map.get("summary"))),
    }
