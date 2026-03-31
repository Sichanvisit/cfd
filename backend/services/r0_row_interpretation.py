from __future__ import annotations

import json
from typing import Any, Mapping


R0_ROW_INTERPRETATION_CONTRACT_VERSION = "r0_row_interpretation_v1"
R0_INTERPRETATION_ORDER = (
    "observe_reason",
    "blocked_by",
    "action_none_reason",
    "probe_state",
    "semantic_runtime_state",
)

_NON_ACTION_REASON_TO_FAMILY = {
    "observe_state_wait": "semantic_observe_wait",
    "probe_not_promoted": "probe_not_promoted",
    "confirm_suppressed": "confirm_suppressed",
    "execution_soft_blocked": "execution_soft_blocked",
    "policy_hard_blocked": "policy_hard_blocked",
    "default_side_blocked": "default_side_blocked",
    "opposite_position_lock": "position_lock_blocked",
    "preflight_blocked": "preflight_blocked",
    "observe_confirm_missing": "input_missing",
}


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    if isinstance(parsed, Mapping):
        return dict(parsed)
    return {}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _pick_text(*values: Any) -> str:
    for value in values:
        text = _normalize_text(value)
        if text:
            return text
    return ""


def _to_boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = _normalize_text(value).lower()
    return text in {"1", "true", "yes", "y", "on"}


def _decision_metrics(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    decision_result = _coerce_mapping(row.get("entry_decision_result_v1"))
    return _coerce_mapping(decision_result.get("metrics"))


def resolve_r0_reason_triplet(row: Mapping[str, Any] | None) -> dict[str, str]:
    if not isinstance(row, Mapping):
        return {
            "observe_reason": "",
            "blocked_by": "",
            "action_none_reason": "",
        }

    metrics = _decision_metrics(row)
    observe_confirm = _coerce_mapping(row.get("observe_confirm_v2")) or _coerce_mapping(
        row.get("observe_confirm_v1")
    )
    decision_result = _coerce_mapping(row.get("entry_decision_result_v1"))

    return {
        "observe_reason": _pick_text(
            row.get("observe_reason"),
            metrics.get("observe_reason"),
            observe_confirm.get("reason"),
        ),
        "blocked_by": _pick_text(
            row.get("blocked_by"),
            decision_result.get("blocked_by"),
            metrics.get("blocked_by"),
            _coerce_mapping(observe_confirm.get("metadata")).get("blocked_guard"),
            _coerce_mapping(observe_confirm.get("metadata")).get("blocked_reason"),
        ),
        "action_none_reason": _pick_text(
            row.get("action_none_reason"),
            metrics.get("action_none_reason"),
        ),
    }


def resolve_r0_probe_state(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""

    quick_state = _normalize_text(row.get("quick_trace_state"))
    if quick_state:
        return quick_state

    probe_plan = _coerce_mapping(row.get("entry_probe_plan_v1"))
    probe_candidate = _coerce_mapping(row.get("probe_candidate_v1"))
    blocked_by = resolve_r0_reason_triplet(row).get("blocked_by", "")

    if _to_boolish(probe_plan.get("active")) and _to_boolish(probe_plan.get("ready_for_entry")):
        return "PROBE_READY"
    if _to_boolish(probe_plan.get("active")):
        return "PROBE_WAIT"
    if _to_boolish(probe_candidate.get("active")) and blocked_by:
        return "PROBE_CANDIDATE_BLOCKED"
    if blocked_by:
        return "BLOCKED"
    if _to_boolish(probe_candidate.get("active")):
        return "PROBE_CANDIDATE"
    if resolve_r0_reason_triplet(row).get("observe_reason", ""):
        return "OBSERVE"
    return ""


def resolve_r0_non_action_family(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""

    triplet = resolve_r0_reason_triplet(row)
    action = _normalize_text(row.get("action")).upper()
    probe_state = resolve_r0_probe_state(row)

    if action in {"BUY", "SELL"} and not triplet["action_none_reason"]:
        return ""

    explicit_reason = triplet["action_none_reason"]
    if explicit_reason:
        return _NON_ACTION_REASON_TO_FAMILY.get(explicit_reason, explicit_reason)

    if probe_state in {"PROBE_WAIT", "PROBE_CANDIDATE", "PROBE_CANDIDATE_BLOCKED"}:
        return "probe_not_promoted"
    if probe_state == "PROBE_READY":
        return ""
    if triplet["blocked_by"]:
        return "blocked_non_action"
    if triplet["observe_reason"]:
        return "semantic_observe_wait"
    return ""


def resolve_r0_semantic_runtime(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {
            "semantic_runtime_state": "",
            "semantic_live_rollout_mode": "",
            "semantic_live_reason": "",
            "semantic_live_fallback_reason": "",
            "semantic_live_symbol_allowed": False,
            "semantic_live_entry_stage_allowed": False,
        }

    rollout_mode = _normalize_text(row.get("semantic_live_rollout_mode"))
    live_reason = _normalize_text(row.get("semantic_live_reason"))
    fallback_reason = _normalize_text(row.get("semantic_live_fallback_reason"))
    symbol_allowed = _to_boolish(row.get("semantic_live_symbol_allowed"))
    entry_stage_allowed = _to_boolish(row.get("semantic_live_entry_stage_allowed"))

    state = ""
    if fallback_reason:
        state = "FALLBACK"
    elif live_reason:
        state = "LIVE"
    elif rollout_mode and (
        "semantic_live_symbol_allowed" in row or "semantic_live_entry_stage_allowed" in row
    ):
        state = "CONFIGURED" if (symbol_allowed and entry_stage_allowed) else "INACTIVE"
    elif rollout_mode:
        state = "CONFIGURED"

    return {
        "semantic_runtime_state": state,
        "semantic_live_rollout_mode": rollout_mode,
        "semantic_live_reason": live_reason,
        "semantic_live_fallback_reason": fallback_reason,
        "semantic_live_symbol_allowed": bool(symbol_allowed),
        "semantic_live_entry_stage_allowed": bool(entry_stage_allowed),
    }


def build_r0_row_interpretation_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {
            "contract_version": R0_ROW_INTERPRETATION_CONTRACT_VERSION,
            "interpretation_order": list(R0_INTERPRETATION_ORDER),
            "observe_reason": "",
            "blocked_by": "",
            "action_none_reason": "",
            "probe_state": "",
            "quick_trace_reason": "",
            "probe_candidate_active": False,
            "probe_plan_active": False,
            "probe_plan_ready": False,
            "non_action_family": "",
            **resolve_r0_semantic_runtime(None),
        }

    probe_plan = _coerce_mapping(row.get("entry_probe_plan_v1"))
    probe_candidate = _coerce_mapping(row.get("probe_candidate_v1"))
    triplet = resolve_r0_reason_triplet(row)
    probe_state = resolve_r0_probe_state(row)
    runtime = resolve_r0_semantic_runtime(row)

    return {
        "contract_version": R0_ROW_INTERPRETATION_CONTRACT_VERSION,
        "interpretation_order": list(R0_INTERPRETATION_ORDER),
        **triplet,
        "probe_state": probe_state,
        "quick_trace_reason": _normalize_text(row.get("quick_trace_reason")),
        "probe_candidate_active": bool(_to_boolish(probe_candidate.get("active"))),
        "probe_plan_active": bool(_to_boolish(probe_plan.get("active"))),
        "probe_plan_ready": bool(_to_boolish(probe_plan.get("ready_for_entry"))),
        "non_action_family": resolve_r0_non_action_family(row),
        **runtime,
    }
