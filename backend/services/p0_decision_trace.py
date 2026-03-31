from __future__ import annotations

import json
from typing import Any, Mapping


P0_DECISION_TRACE_CONTRACT_V1 = {
    "contract_version": "p0_decision_trace_contract_v1",
    "scope": "entry_decision_logging_and_runtime_surface",
    "purpose": [
        "make decision ownership explicit",
        "make immediate guard path explicit",
        "carry coverage-aware state into downstream observability",
    ],
    "identity_owner_values": [
        "semantic",
        "legacy",
        "unknown",
    ],
    "execution_gate_owner_values": [
        "legacy",
        "semantic",
        "shared",
        "unknown",
    ],
    "coverage_state_values": [
        "in_scope_runtime",
        "outside_coverage",
        "unknown",
    ],
}


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    text = _coerce_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = _coerce_text(value)
        if text:
            return text
    return ""


def resolve_p0_coverage_state(row: Mapping[str, Any] | None) -> tuple[str, str]:
    row_local = dict(row or {})
    explicit = _coerce_text(row_local.get("p0_coverage_state") or row_local.get("coverage_state"))
    if explicit:
        return explicit, "explicit_row_field"
    r0_family = _coerce_text(row_local.get("r0_non_action_family"))
    if r0_family == "decision_log_coverage_gap":
        return "outside_coverage", "r0_non_action_family"
    runtime_snapshot_key = _coerce_text(row_local.get("runtime_snapshot_key"))
    if runtime_snapshot_key:
        return "in_scope_runtime", "runtime_snapshot_key"
    return "unknown", "fallback_unknown"


def resolve_p0_decision_ownership(row: Mapping[str, Any] | None) -> dict[str, str]:
    row_local = dict(row or {})
    has_semantic_identity = bool(
        _first_nonempty(
            row_local.get("consumer_archetype_id"),
            row_local.get("consumer_invalidation_id"),
            row_local.get("consumer_management_profile_id"),
            row_local.get("observe_confirm_v2"),
            row_local.get("observe_confirm_v1"),
            row_local.get("shadow_state_v1"),
        )
    )
    has_legacy_execution = bool(
        _first_nonempty(
            row_local.get("decision_rule_version"),
            row_local.get("core_reason"),
            row_local.get("effective_entry_threshold"),
            row_local.get("base_entry_threshold"),
        )
    )
    has_shadow_compare = bool(
        _coerce_text(row_local.get("semantic_shadow_model_version"))
        or str(row_local.get("semantic_shadow_available", "")).strip().lower() in {"true", "1"}
    )

    if has_semantic_identity:
        identity_owner = "semantic"
    elif has_legacy_execution:
        identity_owner = "legacy"
    else:
        identity_owner = "unknown"

    if has_semantic_identity and has_legacy_execution:
        execution_gate_owner = "shared"
        relation = "semantic_identity_with_legacy_execution_gate"
    elif has_semantic_identity and has_shadow_compare:
        execution_gate_owner = "semantic"
        relation = "semantic_identity_with_shadow_compare"
    elif has_semantic_identity:
        execution_gate_owner = "semantic"
        relation = "semantic_primary"
    elif has_legacy_execution:
        execution_gate_owner = "legacy"
        relation = "legacy_primary"
    else:
        execution_gate_owner = "unknown"
        relation = "unknown"

    return {
        "identity_owner": identity_owner,
        "execution_gate_owner": execution_gate_owner,
        "decision_owner_relation": relation,
    }


def build_p0_decision_trace_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    row_local = dict(row or {})
    ownership = resolve_p0_decision_ownership(row_local)
    coverage_state, coverage_source = resolve_p0_coverage_state(row_local)

    consumer_open_guard = _coerce_mapping(row_local.get("consumer_open_guard_v1"))
    entry_blocked_guard = _coerce_mapping(row_local.get("entry_blocked_guard_v1"))
    probe_promotion_guard = _coerce_mapping(row_local.get("probe_promotion_guard_v1"))

    guard_failures: list[str] = []
    active_guards: list[str] = []
    for guard_name, payload in (
        ("consumer_open_guard_v1", consumer_open_guard),
        ("entry_blocked_guard_v1", entry_blocked_guard),
        ("probe_promotion_guard_v1", probe_promotion_guard),
    ):
        if not payload:
            continue
        if bool(payload.get("guard_active", False)):
            active_guards.append(guard_name)
        if bool(payload.get("guard_active", False)) and not bool(payload.get("allows_open", True)):
            failure_code = _coerce_text(payload.get("failure_code"))
            if failure_code:
                guard_failures.append(failure_code)

    action = _coerce_text(row_local.get("consumer_effective_action") or row_local.get("action")).upper()
    observe_reason = _coerce_text(row_local.get("observe_reason"))
    blocked_by = _coerce_text(row_local.get("blocked_by"))
    action_none_reason = _coerce_text(row_local.get("action_none_reason"))
    quick_trace_state = _coerce_text(row_local.get("quick_trace_state"))
    quick_trace_reason = _coerce_text(row_local.get("quick_trace_reason"))
    consumer_stage = _coerce_text(
        row_local.get("consumer_check_stage")
        or consumer_open_guard.get("check_stage")
    ).upper()
    outcome = _coerce_text(row_local.get("outcome"))

    dominant_guard_failure = guard_failures[0] if guard_failures else ""
    dominant_reason = _first_nonempty(
        dominant_guard_failure,
        blocked_by,
        action_none_reason,
        quick_trace_reason,
        observe_reason,
    )

    if outcome == "entered":
        lifecycle_stage_hint = "entry_opened"
    elif dominant_guard_failure:
        lifecycle_stage_hint = "entry_blocked"
    elif action_none_reason:
        lifecycle_stage_hint = "entry_non_action"
    elif action in {"BUY", "SELL"}:
        lifecycle_stage_hint = "entry_candidate"
    else:
        lifecycle_stage_hint = "entry_idle"

    return {
        "contract_version": "p0_decision_trace_v1",
        "identity_owner": ownership["identity_owner"],
        "execution_gate_owner": ownership["execution_gate_owner"],
        "decision_owner_relation": ownership["decision_owner_relation"],
        "coverage_state": coverage_state,
        "coverage_source": coverage_source,
        "action": action,
        "outcome": outcome,
        "observe_reason": observe_reason,
        "blocked_by": blocked_by,
        "action_none_reason": action_none_reason,
        "quick_trace_state": quick_trace_state,
        "quick_trace_reason": quick_trace_reason,
        "consumer_check_stage": consumer_stage,
        "guard_failures": guard_failures,
        "active_guards": active_guards,
        "dominant_guard_failure": dominant_guard_failure,
        "dominant_reason": dominant_reason,
        "lifecycle_stage_hint": lifecycle_stage_hint,
        "one_line": " | ".join(
            [
                ownership["decision_owner_relation"] or "unknown",
                action or "NONE",
                dominant_reason or "-",
                coverage_state or "unknown",
            ]
        ),
    }
