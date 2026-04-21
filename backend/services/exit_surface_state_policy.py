"""Helpers for splitting exit actions into protective vs continuation-hold surfaces."""

from __future__ import annotations


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def resolve_exit_surface_state_v1(
    *,
    action_source: str = "",
    candidate_kind: str = "",
    reason: str = "",
    partial_executed: bool = False,
    stop_lock_applied: bool = False,
) -> dict[str, object]:
    contract_version = "exit_surface_state_v1"
    source = str(action_source or "").strip().lower()
    kind = str(candidate_kind or "").strip().lower()
    reason_text = str(reason or "").strip()
    reason_lower = reason_text.lower()

    out = {
        "contract_version": contract_version,
        "surface_family": "",
        "surface_state": "",
        "policy_scope": "",
        "state_reason": "",
        "should_record": False,
    }

    if source in {"partial_action", "runner_preservation"}:
        if kind == "partial_then_runner_hold" or _to_bool(partial_executed, False):
            out.update(
                {
                    "surface_family": "continuation_hold_surface",
                    "surface_state": "PARTIAL_REDUCE",
                    "policy_scope": "EXIT_SURFACE_CONTINUATION",
                    "state_reason": reason_text or "partial_then_runner_hold",
                    "should_record": True,
                }
            )
            return out
        if kind in {"runner_lock_only", "runner_continue"} or _to_bool(stop_lock_applied, False):
            out.update(
                {
                    "surface_family": "continuation_hold_surface",
                    "surface_state": "HOLD_RUNNER",
                    "policy_scope": "EXIT_SURFACE_CONTINUATION",
                    "state_reason": reason_text or "runner_lock_only",
                    "should_record": True,
                }
            )
            return out
        return out

    protect_kinds = {
        "emergency_stop",
        "protect_exit",
        "adverse_stop",
        "recovery_exit",
        "time_stop",
        "adverse_recheck_protect",
    }
    lock_kinds = {
        "lock_exit",
        "target_exit",
        "adverse_recheck_lock",
    }
    if kind in protect_kinds or reason_lower in {"emergency stop", "protect exit", "recovery exit", "time stop", "adverse stop"}:
        out.update(
            {
                "surface_family": "protective_exit_surface",
                "surface_state": "EXIT_PROTECT",
                "policy_scope": "EXIT_SURFACE_PROTECTIVE",
                "state_reason": reason_text or kind or "protective_exit",
                "should_record": True,
            }
        )
        return out
    if kind in lock_kinds or reason_lower in {"lock exit", "target"}:
        out.update(
            {
                "surface_family": "protective_exit_surface",
                "surface_state": "LOCK_PROFIT",
                "policy_scope": "EXIT_SURFACE_PROTECTIVE",
                "state_reason": reason_text or kind or "lock_profit",
                "should_record": True,
            }
        )
        return out
    return out
