"""Shared taxonomy helpers for exit hold/wait/reverse semantics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.domain.decision_models import WaitState


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _resolve_state_payload(wait_state: WaitState | Mapping[str, Any] | None) -> tuple[str, bool, str]:
    if isinstance(wait_state, WaitState):
        return (
            _to_str(wait_state.state, "NONE").upper(),
            bool(wait_state.hard_wait),
            _to_str(wait_state.reason, ""),
        )
    state_map = _as_mapping(wait_state)
    return (
        _to_str(state_map.get("state", "NONE"), "NONE").upper(),
        _to_bool(state_map.get("hard_wait", False)),
        _to_str(state_map.get("reason", "")),
    )


def _build_state_taxonomy(state: str, hard_wait: bool, reason: str) -> dict[str, Any]:
    recovery_variant = ""
    if state == "REVERSAL_CONFIRM":
        state_family = "confirm_hold"
        hold_class = "hard_hold"
        state_intent = "confirm"
    elif state in {"ACTIVE", "GREEN_CLOSE"}:
        state_family = "active_hold"
        hold_class = "soft_hold"
        state_intent = "hold"
    elif state in {"RECOVERY_BE", "RECOVERY_TP1"}:
        state_family = "recovery_hold"
        hold_class = "soft_hold"
        state_intent = "recover"
        recovery_variant = "be" if state == "RECOVERY_BE" else "tp1"
    elif state == "REVERSE_READY":
        state_family = "reverse_ready"
        hold_class = "soft_hold"
        state_intent = "reverse"
    elif state == "CUT_IMMEDIATE":
        state_family = "exit_pressure"
        hold_class = "no_hold"
        state_intent = "exit"
    else:
        state_family = "neutral"
        hold_class = "none"
        state_intent = "neutral"

    return {
        "state": str(state),
        "state_family": str(state_family),
        "hold_class": str(hold_class),
        "state_intent": str(state_intent),
        "recovery_variant": str(recovery_variant),
        "hard_wait": bool(hard_wait),
        "reason": str(reason),
    }


def _build_decision_taxonomy(utility_result: Mapping[str, Any] | None = None) -> dict[str, Any]:
    utility_map = _as_mapping(utility_result)
    winner = _to_str(utility_map.get("winner", "")).lower()
    decision_reason = _to_str(utility_map.get("decision_reason", ""))
    wait_selected = _to_bool(utility_map.get("wait_selected", False))
    wait_decision = _to_str(utility_map.get("wait_decision", ""))
    recovery_variant = ""

    if winner == "hold":
        decision_family = "hold_continue"
        action_class = "hold"
    elif winner == "wait_exit":
        decision_family = "wait_exit"
        action_class = "wait"
    elif winner in {"wait_be", "wait_tp1"}:
        decision_family = "recovery_wait"
        action_class = "wait"
        recovery_variant = "be" if winner == "wait_be" else "tp1"
    elif winner in {"exit_now", "cut_now"}:
        decision_family = "exit_now"
        action_class = "exit"
        recovery_variant = "cut_now" if winner == "cut_now" else ""
    elif winner in {"reverse", "reverse_now"}:
        decision_family = "reverse_now"
        action_class = "reverse"
        recovery_variant = "reverse_now" if winner == "reverse_now" else ""
    else:
        decision_family = "neutral"
        action_class = "none"

    return {
        "winner": str(winner),
        "decision_family": str(decision_family),
        "action_class": str(action_class),
        "recovery_variant": str(recovery_variant),
        "wait_selected": bool(wait_selected),
        "wait_decision": str(wait_decision),
        "decision_reason": str(decision_reason),
    }


def _build_bridge_taxonomy(
    *,
    state_taxonomy: Mapping[str, Any] | None = None,
    decision_taxonomy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state_map = _as_mapping(state_taxonomy)
    decision_map = _as_mapping(decision_taxonomy)
    state_family = _to_str(state_map.get("state_family", "neutral"), "neutral")
    decision_family = _to_str(decision_map.get("decision_family", "neutral"), "neutral")
    action_class = _to_str(decision_map.get("action_class", "none"), "none")

    if decision_family == "neutral":
        bridge_status = "neutral"
    elif state_family == "neutral":
        bridge_status = "decision_without_hold_state"
    elif state_family == "confirm_hold":
        if action_class == "wait":
            bridge_status = "aligned_confirm_wait"
        elif action_class == "hold":
            bridge_status = "confirm_hold_continues"
        elif action_class == "exit":
            bridge_status = "released_to_exit"
        else:
            bridge_status = "escalated_to_reverse"
    elif state_family == "active_hold":
        if action_class == "hold":
            bridge_status = "aligned_hold_continue"
        elif action_class == "wait":
            bridge_status = "aligned_wait_exit"
        elif action_class == "exit":
            bridge_status = "released_to_exit"
        else:
            bridge_status = "escalated_to_reverse"
    elif state_family == "recovery_hold":
        if decision_family == "recovery_wait":
            bridge_status = "aligned_recovery_wait"
        elif action_class == "exit":
            bridge_status = "released_to_exit"
        elif action_class == "reverse":
            bridge_status = "escalated_to_reverse"
        else:
            bridge_status = "recovery_hold_continues"
    elif state_family == "reverse_ready":
        if action_class == "reverse":
            bridge_status = "aligned_reverse"
        elif action_class == "exit":
            bridge_status = "released_to_exit"
        elif action_class == "wait":
            bridge_status = "reverse_ready_but_waiting"
        else:
            bridge_status = "reverse_ready_but_holding"
    elif state_family == "exit_pressure":
        if action_class == "exit":
            bridge_status = "aligned_exit_pressure"
        elif action_class == "reverse":
            bridge_status = "exit_pressure_to_reverse"
        else:
            bridge_status = "exit_pressure_but_waiting"
    else:
        bridge_status = "neutral"

    return {
        "bridge_status": str(bridge_status),
        "state_family": str(state_family),
        "decision_family": str(decision_family),
        "action_class": str(action_class),
    }


def build_exit_wait_taxonomy_v1(
    *,
    wait_state: WaitState | Mapping[str, Any] | None = None,
    utility_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state, hard_wait, reason = _resolve_state_payload(wait_state)
    state_taxonomy = _build_state_taxonomy(state, hard_wait, reason)
    decision_taxonomy = _build_decision_taxonomy(utility_result)
    bridge_taxonomy = _build_bridge_taxonomy(
        state_taxonomy=state_taxonomy,
        decision_taxonomy=decision_taxonomy,
    )
    return {
        "contract_version": "exit_wait_taxonomy_v1",
        "state": dict(state_taxonomy),
        "decision": dict(decision_taxonomy),
        "bridge": dict(bridge_taxonomy),
    }


def compact_exit_wait_taxonomy_v1(taxonomy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    taxonomy_map = _as_mapping(taxonomy)
    state_map = _as_mapping(taxonomy_map.get("state"))
    decision_map = _as_mapping(taxonomy_map.get("decision"))
    bridge_map = _as_mapping(taxonomy_map.get("bridge"))
    return {
        "contract_version": _to_str(taxonomy_map.get("contract_version", "exit_wait_taxonomy_v1")),
        "state": {
            "state": _to_str(state_map.get("state", "NONE"), "NONE").upper(),
            "state_family": _to_str(state_map.get("state_family", "neutral"), "neutral"),
            "hold_class": _to_str(state_map.get("hold_class", "none"), "none"),
            "state_intent": _to_str(state_map.get("state_intent", "neutral"), "neutral"),
            "recovery_variant": _to_str(state_map.get("recovery_variant", "")),
            "hard_wait": _to_bool(state_map.get("hard_wait", False)),
            "reason": _to_str(state_map.get("reason", "")),
        },
        "decision": {
            "winner": _to_str(decision_map.get("winner", "")),
            "decision_family": _to_str(decision_map.get("decision_family", "neutral"), "neutral"),
            "action_class": _to_str(decision_map.get("action_class", "none"), "none"),
            "recovery_variant": _to_str(decision_map.get("recovery_variant", "")),
            "wait_selected": _to_bool(decision_map.get("wait_selected", False)),
            "wait_decision": _to_str(decision_map.get("wait_decision", "")),
            "decision_reason": _to_str(decision_map.get("decision_reason", "")),
        },
        "bridge": {
            "bridge_status": _to_str(bridge_map.get("bridge_status", "neutral"), "neutral"),
            "state_family": _to_str(bridge_map.get("state_family", "neutral"), "neutral"),
            "decision_family": _to_str(bridge_map.get("decision_family", "neutral"), "neutral"),
            "action_class": _to_str(bridge_map.get("action_class", "none"), "none"),
        },
    }
