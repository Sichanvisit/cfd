"""Shared input contract helpers for exit manage execution seams."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.domain.decision_models import WaitState
from backend.services.exit_manage_context_contract import compact_exit_manage_context_v1
from backend.services.exit_wait_taxonomy_contract import compact_exit_wait_taxonomy_v1


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


def _round6(value: object, default: float = 0.0) -> float:
    return round(_to_float(value, default), 6)


def _normalize_shock_progress(progress: Mapping[str, Any] | None = None) -> dict[str, Any]:
    progress_map = _as_mapping(progress)
    return {str(key): value for key, value in progress_map.items()}


def _resolve_wait_state_payload(
    exit_wait_state: WaitState | Mapping[str, Any] | None,
) -> tuple[str, str, bool]:
    if isinstance(exit_wait_state, WaitState):
        return (
            _to_str(exit_wait_state.state, "NONE").upper(),
            _to_str(exit_wait_state.reason, ""),
            bool(exit_wait_state.hard_wait),
        )
    state_map = _as_mapping(exit_wait_state)
    return (
        _to_str(state_map.get("state", "NONE"), "NONE").upper(),
        _to_str(state_map.get("reason", "")),
        _to_bool(state_map.get("hard_wait", False), False),
    )


def build_exit_manage_execution_input_v1(
    *,
    symbol: str = "",
    ticket: int = 0,
    direction: str = "",
    trade_ctx: Mapping[str, Any] | None = None,
    latest_signal_row: Mapping[str, Any] | None = None,
    exit_wait_state: WaitState | Mapping[str, Any] | None = None,
    chosen_stage: str = "",
    policy_stage: str = "",
    exec_profile: str = "",
    protect_threshold: object = 0,
    lock_threshold: object = 0,
    hold_threshold: object = 0,
    confirm_needed: int = 0,
    delay_ticks: int = 0,
    stage_route: Mapping[str, Any] | None = None,
    regime_name: str = "",
    regime_observed: str = "",
    regime_switch_detail: object = "",
    peak_profit: object = 0.0,
    giveback_usd: object = 0.0,
    shock_ctx: Mapping[str, Any] | None = None,
    shock_progress: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    trade_ctx_map = _as_mapping(trade_ctx)
    latest_signal_map = _as_mapping(latest_signal_row)
    stage_route_map = _as_mapping(stage_route)
    shock_ctx_map = _as_mapping(shock_ctx)
    shock_progress_map = _normalize_shock_progress(shock_progress)

    exit_shadow = _as_mapping(latest_signal_map.get("exit_utility_v1"))
    exit_manage_context_v1 = compact_exit_manage_context_v1(
        latest_signal_map.get("exit_manage_context_v1")
    )
    exit_wait_taxonomy_v1 = compact_exit_wait_taxonomy_v1(
        latest_signal_map.get("exit_wait_taxonomy_v1")
    )
    exit_prediction_v1 = _as_mapping(latest_signal_map.get("exit_prediction_v1"))

    handoff = _as_mapping(exit_manage_context_v1.get("handoff"))
    posture = _as_mapping(exit_manage_context_v1.get("posture"))
    wait_state_taxonomy = _as_mapping(exit_wait_taxonomy_v1.get("state"))
    wait_decision_taxonomy = _as_mapping(exit_wait_taxonomy_v1.get("decision"))
    wait_bridge_taxonomy = _as_mapping(exit_wait_taxonomy_v1.get("bridge"))
    wait_state_name, wait_state_reason, wait_state_hard = _resolve_wait_state_payload(exit_wait_state)

    effective_exit_profile = (
        _to_str(posture.get("lifecycle_exit_profile", ""))
        or _to_str(posture.get("resolved_exit_profile", ""))
        or _to_str(trade_ctx_map.get("exit_profile", ""))
        or _to_str(exec_profile, "")
    )

    return {
        "contract_version": "exit_manage_execution_input_v1",
        "identity": {
            "symbol": _to_str(symbol).upper(),
            "ticket": _to_int(ticket, 0),
            "direction": _to_str(direction).upper(),
            "entry_setup_id": _to_str(trade_ctx_map.get("entry_setup_id", "")),
        },
        "handoff": {
            "management_profile_id": _to_str(
                handoff.get(
                    "management_profile_id",
                    trade_ctx_map.get("management_profile_id", ""),
                )
            ),
            "invalidation_id": _to_str(
                handoff.get("invalidation_id", trade_ctx_map.get("invalidation_id", ""))
            ),
            "handoff_source": _to_str(handoff.get("handoff_source", "")),
        },
        "posture": {
            "chosen_stage": _to_str(chosen_stage or posture.get("chosen_stage", "auto"), "auto"),
            "policy_stage": _to_str(policy_stage or posture.get("policy_stage", "")),
            "execution_profile": _to_str(exec_profile or posture.get("execution_profile", "")),
            "resolved_exit_profile": _to_str(posture.get("resolved_exit_profile", "")),
            "lifecycle_exit_profile": _to_str(posture.get("lifecycle_exit_profile", "")),
            "effective_exit_profile": _to_str(effective_exit_profile),
        },
        "decision": {
            "winner": _to_str(exit_shadow.get("winner", "")),
            "decision_reason": _to_str(exit_shadow.get("decision_reason", "")),
            "wait_selected": _to_bool(exit_shadow.get("wait_selected", False), False),
            "wait_decision": _to_str(exit_shadow.get("wait_decision", "")),
            "utility_exit_now": _round6(exit_shadow.get("utility_exit_now", 0.0), 0.0),
            "utility_hold": _round6(exit_shadow.get("utility_hold", 0.0), 0.0),
            "utility_reverse": _round6(exit_shadow.get("utility_reverse", 0.0), 0.0),
            "utility_wait_exit": _round6(exit_shadow.get("utility_wait_exit", 0.0), 0.0),
            "u_cut_now": _round6(exit_shadow.get("u_cut_now", 0.0), 0.0),
            "u_wait_be": _round6(exit_shadow.get("u_wait_be", 0.0), 0.0),
            "u_wait_tp1": _round6(exit_shadow.get("u_wait_tp1", 0.0), 0.0),
            "u_reverse": _round6(exit_shadow.get("u_reverse", 0.0), 0.0),
            "p_recover_be": _round6(exit_shadow.get("p_recover_be", 0.0), 0.0),
            "p_recover_tp1": _round6(exit_shadow.get("p_recover_tp1", 0.0), 0.0),
            "p_deeper_loss": _round6(exit_shadow.get("p_deeper_loss", 0.0), 0.0),
            "p_reverse_valid": _round6(exit_shadow.get("p_reverse_valid", 0.0), 0.0),
            "final_outcome": _to_str(exit_shadow.get("winner", "")),
        },
        "wait_state": {
            "state": _to_str(wait_state_name, "NONE").upper(),
            "reason": _to_str(wait_state_reason, ""),
            "hard_wait": _to_bool(wait_state_hard, False),
        },
        "wait_taxonomy": {
            "state_family": _to_str(wait_state_taxonomy.get("state_family", "")),
            "hold_class": _to_str(wait_state_taxonomy.get("hold_class", "")),
            "decision_family": _to_str(wait_decision_taxonomy.get("decision_family", "")),
            "bridge_status": _to_str(wait_bridge_taxonomy.get("bridge_status", "")),
        },
        "thresholds": {
            "protect_threshold": protect_threshold,
            "lock_threshold": lock_threshold,
            "hold_threshold": hold_threshold,
            "exit_threshold_triplet": f"{protect_threshold}/{lock_threshold}/{hold_threshold}",
            "confirm_needed": _to_int(confirm_needed, 0),
            "delay_ticks": _to_int(delay_ticks, 0),
        },
        "route": {
            "chosen": _to_str(stage_route_map.get("chosen", "")),
            "ev": stage_route_map.get("ev", {}),
            "confidence": _round6(stage_route_map.get("confidence", 0.0), 0.0),
            "hist_n": _to_int(stage_route_map.get("hist_n", 0), 0),
            "reason_codes": list(stage_route_map.get("reason_codes", []) or []),
        },
        "regime": {
            "name": _to_str(regime_name).upper(),
            "observed": _to_str(regime_observed).upper(),
            "switch_detail": _to_str(regime_switch_detail),
        },
        "performance": {
            "peak_profit_at_exit": _round6(peak_profit, 0.0),
            "giveback_usd": _round6(giveback_usd, 0.0),
        },
        "shock": {
            "shock_score": _round6(shock_ctx_map.get("shock_score", 0.0), 0.0),
            "shock_level": _to_str(shock_ctx_map.get("shock_level", "")),
            "shock_reason": _to_str(shock_ctx_map.get("shock_reason", "")),
            "shock_action": _to_str(shock_ctx_map.get("shock_action", "")),
            "pre_shock_stage": _to_str(shock_ctx_map.get("pre_shock_stage", "")),
            "post_shock_stage": _to_str(shock_ctx_map.get("post_shock_stage", "")),
            "shock_at_profit": _round6(shock_ctx_map.get("shock_at_profit", 0.0), 0.0),
            "progress": dict(shock_progress_map),
        },
        "runtime": {
            "exit_utility_v1": dict(exit_shadow),
            "exit_manage_context_v1": dict(exit_manage_context_v1),
            "exit_wait_taxonomy_v1": dict(exit_wait_taxonomy_v1),
            "exit_prediction_v1": dict(exit_prediction_v1),
        },
    }


def compact_exit_manage_execution_input_v1(
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract_map = _as_mapping(contract)
    identity = _as_mapping(contract_map.get("identity"))
    handoff = _as_mapping(contract_map.get("handoff"))
    posture = _as_mapping(contract_map.get("posture"))
    decision = _as_mapping(contract_map.get("decision"))
    wait_state = _as_mapping(contract_map.get("wait_state"))
    wait_taxonomy = _as_mapping(contract_map.get("wait_taxonomy"))
    thresholds = _as_mapping(contract_map.get("thresholds"))
    regime = _as_mapping(contract_map.get("regime"))
    performance = _as_mapping(contract_map.get("performance"))
    shock = _as_mapping(contract_map.get("shock"))

    return {
        "contract_version": _to_str(
            contract_map.get("contract_version", "exit_manage_execution_input_v1")
        ),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "ticket": _to_int(identity.get("ticket", 0), 0),
            "direction": _to_str(identity.get("direction", "")).upper(),
            "entry_setup_id": _to_str(identity.get("entry_setup_id", "")),
        },
        "handoff": {
            "management_profile_id": _to_str(handoff.get("management_profile_id", "")),
            "invalidation_id": _to_str(handoff.get("invalidation_id", "")),
        },
        "posture": {
            "chosen_stage": _to_str(posture.get("chosen_stage", "")),
            "policy_stage": _to_str(posture.get("policy_stage", "")),
            "execution_profile": _to_str(posture.get("execution_profile", "")),
            "effective_exit_profile": _to_str(posture.get("effective_exit_profile", "")),
        },
        "decision": {
            "winner": _to_str(decision.get("winner", "")),
            "decision_reason": _to_str(decision.get("decision_reason", "")),
            "wait_selected": _to_bool(decision.get("wait_selected", False), False),
            "wait_decision": _to_str(decision.get("wait_decision", "")),
        },
        "wait": {
            "state": _to_str(wait_state.get("state", "NONE"), "NONE").upper(),
            "state_family": _to_str(wait_taxonomy.get("state_family", "")),
            "decision_family": _to_str(wait_taxonomy.get("decision_family", "")),
            "bridge_status": _to_str(wait_taxonomy.get("bridge_status", "")),
        },
        "thresholds": {
            "exit_threshold_triplet": _to_str(thresholds.get("exit_threshold_triplet", "")),
            "confirm_needed": _to_int(thresholds.get("confirm_needed", 0), 0),
            "delay_ticks": _to_int(thresholds.get("delay_ticks", 0), 0),
        },
        "regime": {
            "name": _to_str(regime.get("name", "")).upper(),
            "observed": _to_str(regime.get("observed", "")).upper(),
        },
        "performance": {
            "peak_profit_at_exit": _round6(performance.get("peak_profit_at_exit", 0.0), 0.0),
            "giveback_usd": _round6(performance.get("giveback_usd", 0.0), 0.0),
        },
        "shock": {
            "shock_score": _round6(shock.get("shock_score", 0.0), 0.0),
            "shock_level": _to_str(shock.get("shock_level", "")),
        },
    }
