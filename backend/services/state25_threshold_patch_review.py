from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from backend.services.improvement_proposal_policy import (
    build_improvement_proposal_envelope,
)
from backend.services.learning_registry_resolver import (
    LEARNING_REGISTRY_BINDING_MODE_EXACT,
    build_learning_registry_binding_fields,
    build_learning_registry_relation,
)
from backend.services.state25_context_bridge import (
    build_state25_candidate_context_bridge_v1,
)


STATE25_THRESHOLD_PATCH_REVIEW_CONTRACT_VERSION = "state25_threshold_patch_review_v0"
STATE25_THRESHOLD_PRIMARY_REGISTRY_KEY = "state25_threshold:entry_harden_delta_points"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for raw in value:
        text = _to_text(raw)
        if not text or text in seen:
            continue
        seen.add(text)
        rows.append(text)
    return rows


def _bridge_context_evidence_registry_keys(
    runtime_row: Mapping[str, Any] | None,
) -> list[str]:
    row_map = _mapping(runtime_row)
    keys: list[str] = []
    if _to_text(row_map.get("htf_alignment_state")).upper():
        keys.append("misread:htf_alignment_state")
    if _to_text(row_map.get("htf_alignment_detail")).upper():
        keys.append("misread:htf_alignment_detail")
    if _to_text(row_map.get("htf_against_severity")).upper():
        keys.append("misread:htf_against_severity")
    if _to_text(row_map.get("previous_box_break_state")).upper():
        keys.append("misread:previous_box_break_state")
    if _to_text(row_map.get("previous_box_relation")).upper():
        keys.append("misread:previous_box_relation")
    if _to_text(row_map.get("previous_box_lifecycle")).upper():
        keys.append("misread:previous_box_lifecycle")
    if _to_text(row_map.get("previous_box_confidence")).upper():
        keys.append("misread:previous_box_confidence")
    if _to_text(row_map.get("context_conflict_state")).upper() not in {"", "NONE"}:
        keys.append("misread:context_conflict_state")
    if _to_text(row_map.get("context_conflict_intensity")).upper():
        keys.append("misread:context_conflict_intensity")
    if _to_text(row_map.get("late_chase_risk_state")).upper() not in {"", "NONE"}:
        keys.append("misread:late_chase_risk_state")
    if _to_text(row_map.get("late_chase_reason")).upper():
        keys.append("misread:late_chase_reason")
    return _as_str_list(keys)


def build_state25_threshold_patch_review_candidate_v1(
    *,
    concern_summary_ko: str,
    current_behavior_ko: str,
    proposed_behavior_ko: str,
    evidence_summary_ko: str,
    threshold_delta_points_requested: float,
    threshold_delta_points_effective: float,
    threshold_delta_pct_requested: float = 0.0,
    threshold_delta_pct_effective: float = 0.0,
    threshold_delta_direction: str = "HARDEN",
    threshold_delta_reason_keys: list[str] | None = None,
    threshold_base_points: float = 0.0,
    threshold_candidate_points: float = 0.0,
    state25_execution_symbol_allowlist: list[str] | None = None,
    state25_execution_entry_stage_allowlist: list[str] | None = None,
    state25_execution_bind_mode: str = "log_only",
    candidate_id: str = "",
    trace_id: str = "",
    evidence_registry_keys: list[str] | None = None,
    without_bridge_decision: str = "",
    with_bridge_decision: str = "",
    bridge_changed_decision: bool = False,
    score_reference_value: float = 0.0,
    score_source_field: str = "",
) -> dict[str, Any]:
    symbol_scope = _as_str_list(state25_execution_symbol_allowlist)
    entry_stage_scope = _as_str_list(state25_execution_entry_stage_allowlist)
    reason_keys = _as_str_list(threshold_delta_reason_keys)
    evidence_keys = _as_str_list(evidence_registry_keys)
    execution_bind_mode = _to_text(state25_execution_bind_mode, "log_only")
    bounded_live_enabled = execution_bind_mode in {"bounded_live", "canary"}
    action_target = (
        "state25_threshold_patch_bounded_live"
        if bounded_live_enabled
        else "state25_threshold_patch_log_only"
    )
    binding_fields = build_learning_registry_binding_fields(
        STATE25_THRESHOLD_PRIMARY_REGISTRY_KEY,
        binding_mode=LEARNING_REGISTRY_BINDING_MODE_EXACT,
    )
    relation = build_learning_registry_relation(
        evidence_registry_keys=evidence_keys,
        target_registry_keys=[STATE25_THRESHOLD_PRIMARY_REGISTRY_KEY],
        binding_mode=LEARNING_REGISTRY_BINDING_MODE_EXACT,
    )
    scope_symbol = ",".join(symbol_scope) or "ALL"
    scope_stage = ",".join(entry_stage_scope) or "ALL"
    scope_key = (
        f"STATE25_THRESHOLD_PATCH::{scope_symbol}::{scope_stage}::"
        f"{threshold_delta_direction or 'HARDEN'}"
    )
    summary_ko = _to_text(concern_summary_ko) or "state25 threshold review 후보"
    scope_note_ko = (
        f"symbol={scope_symbol} | entry_stage={scope_stage} | "
        f"binding_mode={execution_bind_mode}"
    )
    recommended_action_ko = (
        "bounded live threshold harden을 아주 좁은 범위에서 시험 반영합니다."
        if bounded_live_enabled
        else "bounded log-only threshold harden review를 먼저 backlog에 올립니다."
    )
    proposal_envelope = build_improvement_proposal_envelope(
        proposal_id=_to_text(candidate_id),
        proposal_type="STATE25_THRESHOLD_PATCH_REVIEW",
        scope_key=scope_key,
        trace_id=_to_text(trace_id),
        summary_ko=summary_ko,
        why_now_ko=_to_text(evidence_summary_ko),
        recommended_action_ko=recommended_action_ko,
        confidence_level="MEDIUM",
        expected_effect_ko=_to_text(proposed_behavior_ko),
        scope_note_ko=scope_note_ko,
        evidence_snapshot={
            "threshold_delta_points_requested": round(float(threshold_delta_points_requested), 6),
            "threshold_delta_points_effective": round(float(threshold_delta_points_effective), 6),
            "threshold_delta_pct_requested": round(float(threshold_delta_pct_requested), 6),
            "threshold_delta_pct_effective": round(float(threshold_delta_pct_effective), 6),
            "threshold_delta_direction": _to_text(threshold_delta_direction, "HARDEN"),
            "threshold_delta_reason_keys": reason_keys,
            "threshold_base_points": round(float(threshold_base_points), 6),
            "threshold_candidate_points": round(float(threshold_candidate_points), 6),
            "score_reference_value": round(float(score_reference_value), 6),
            "score_source_field": _to_text(score_source_field),
            "without_bridge_decision": _to_text(without_bridge_decision),
            "with_bridge_decision": _to_text(with_bridge_decision),
            "bridge_changed_decision": bool(bridge_changed_decision),
            "state25_execution_symbol_allowlist": symbol_scope,
            "state25_execution_entry_stage_allowlist": entry_stage_scope,
            "state25_execution_bind_mode": execution_bind_mode,
            "evidence_registry_keys": evidence_keys,
            "target_registry_keys": [STATE25_THRESHOLD_PRIMARY_REGISTRY_KEY],
        },
    )
    report_lines_ko = [
        f"관찰 장면: {_to_text(concern_summary_ko)}",
        f"현재 해석: {_to_text(current_behavior_ko)}",
        f"제안 해석: {_to_text(proposed_behavior_ko)}",
        f"근거 요약: {_to_text(evidence_summary_ko)}",
        f"적용 범위: {scope_note_ko}",
        (
            f"- threshold requested/effective: +{float(threshold_delta_points_requested):.2f}pt / "
            f"+{float(threshold_delta_points_effective):.2f}pt"
        ),
        f"- threshold direction: {_to_text(threshold_delta_direction, 'HARDEN')}",
    ]
    if reason_keys:
        report_lines_ko.append(f"- reason_keys: {', '.join(reason_keys)}")
    if _to_text(without_bridge_decision) or _to_text(with_bridge_decision):
        report_lines_ko.append(
            f"- decision counterfactual: {_to_text(without_bridge_decision, '-')} -> {_to_text(with_bridge_decision, '-')}"
        )
    return {
        "contract_version": STATE25_THRESHOLD_PATCH_REVIEW_CONTRACT_VERSION,
        "generated_at": _now_iso(),
        "trace_id": _to_text(trace_id),
        "review_type": "STATE25_THRESHOLD_PATCH_REVIEW",
        "governance_action": "state25_threshold_patch_review",
        "action_target": action_target,
        "scope_key": scope_key,
        "symbol": (symbol_scope[0] if len(symbol_scope) == 1 else ""),
        "candidate_id": _to_text(candidate_id),
        "concern_summary_ko": _to_text(concern_summary_ko),
        "current_behavior_ko": _to_text(current_behavior_ko),
        "proposed_behavior_ko": _to_text(proposed_behavior_ko),
        "evidence_summary_ko": _to_text(evidence_summary_ko),
        "proposal_summary_ko": summary_ko,
        "summary_ko": summary_ko,
        "reason_summary_ko": summary_ko,
        "scope_note_ko": scope_note_ko,
        **binding_fields,
        "registry_binding_ready": bool(binding_fields.get("registry_found"))
        and bool(relation.get("binding_ready")),
        "evidence_registry_keys": list(relation.get("evidence_registry_keys") or []),
        "target_registry_keys": list(relation.get("target_registry_keys") or []),
        "evidence_bindings": list(relation.get("evidence_bindings") or []),
        "target_bindings": list(relation.get("target_bindings") or []),
        "proposal_id": proposal_envelope["proposal_id"],
        "proposal_type": proposal_envelope["proposal_type"],
        "proposal_stage": proposal_envelope["proposal_stage"],
        "readiness_status": proposal_envelope["readiness_status"],
        "why_now_ko": proposal_envelope["why_now_ko"],
        "recommended_action_ko": proposal_envelope["recommended_action_ko"],
        "blocking_reason": proposal_envelope["blocking_reason"],
        "confidence_level": proposal_envelope["confidence_level"],
        "expected_effect_ko": proposal_envelope["expected_effect_ko"],
        "decision_deadline_ts": proposal_envelope["decision_deadline_ts"],
        "state25_execution_bind_mode": execution_bind_mode,
        "state25_execution_symbol_allowlist": symbol_scope,
        "state25_execution_entry_stage_allowlist": entry_stage_scope,
        "threshold_patch": {
            "state25_execution_bind_mode": execution_bind_mode,
            "state25_execution_symbol_allowlist": symbol_scope,
            "state25_execution_entry_stage_allowlist": entry_stage_scope,
            "state25_threshold_log_only_enabled": not bounded_live_enabled,
            "state25_threshold_log_only_requested_points": round(float(threshold_delta_points_requested), 6),
            "state25_threshold_log_only_effective_points": round(float(threshold_delta_points_effective), 6),
            "state25_threshold_log_only_requested_pct": round(float(threshold_delta_pct_requested), 6),
            "state25_threshold_log_only_effective_pct": round(float(threshold_delta_pct_effective), 6),
            "state25_threshold_log_only_direction": _to_text(threshold_delta_direction, "HARDEN"),
            "state25_threshold_log_only_reason_keys": reason_keys,
            "state25_threshold_bounded_live_enabled": bounded_live_enabled,
        },
        "proposal_envelope": proposal_envelope,
        "report_title_ko": "자동 반영 제안 | threshold 조정",
        "report_lines_ko": report_lines_ko,
        "recommended_action_note": recommended_action_ko,
        "recommended_next_action": (
            "review_state25_threshold_patch_and_activate_bounded_live_if_safe"
            if bounded_live_enabled
            else "review_state25_threshold_patch_and_keep_log_only"
        ),
    }


def build_state25_threshold_patch_review_candidate_from_context_bridge_v1(
    runtime_row: Mapping[str, Any] | None,
    *,
    bridge_payload: Mapping[str, Any] | None = None,
    state25_execution_bind_mode: str = "log_only",
) -> dict[str, Any]:
    row_map = _mapping(runtime_row)
    bridge = _mapping(bridge_payload or row_map.get("state25_candidate_context_bridge_v1"))
    requested = _mapping(bridge.get("threshold_adjustment_requested"))
    if _to_float(requested.get("threshold_delta_points"), 0.0) <= 0.0 and row_map:
        rebuilt = _mapping(build_state25_candidate_context_bridge_v1(row_map))
        rebuilt_requested = _mapping(rebuilt.get("threshold_adjustment_requested"))
        if _to_float(rebuilt_requested.get("threshold_delta_points"), 0.0) > 0.0:
            bridge = rebuilt
            requested = rebuilt_requested
    if _to_float(requested.get("threshold_delta_points"), 0.0) <= 0.0:
        return {}

    effective = _mapping(bridge.get("threshold_adjustment_effective"))
    suppressed = _mapping(bridge.get("threshold_adjustment_suppressed"))
    decision_counterfactual = _mapping(bridge.get("decision_counterfactual"))
    symbol = _to_text(row_map.get("symbol"), "ALL").upper()
    entry_stage = _to_text(row_map.get("entry_stage"))
    consumer_side = _to_text(row_map.get("consumer_check_side")).upper() or "-"
    context_summary = _to_text(row_map.get("context_bundle_summary_ko")) or _to_text(
        row_map.get("context_conflict_label_ko")
    )
    requested_points = _to_float(requested.get("threshold_delta_points"), 0.0)
    effective_points = _to_float(effective.get("threshold_delta_points"), 0.0)
    requested_pct = _to_float(requested.get("threshold_delta_pct"), 0.0)
    effective_pct = _to_float(effective.get("threshold_delta_pct"), 0.0)
    direction = _to_text(
        effective.get("threshold_delta_direction")
        or requested.get("threshold_delta_direction"),
        "HARDEN",
    )
    reason_keys = _as_str_list(
        effective.get("threshold_delta_reason_keys")
        or requested.get("threshold_delta_reason_keys")
    )
    concern_summary_ko = (
        f"{symbol} {consumer_side} 진입에서 큰 그림 맥락 기준 threshold harden review가 필요합니다."
    )
    if context_summary:
        concern_summary_ko = (
            f"{symbol} {consumer_side} 진입에서 `{context_summary}` 맥락 기준 threshold harden review가 필요합니다."
        )
    current_behavior_ko = (
        f"현재 state25는 {consumer_side} 방향 해석을 유지하고 있고, bridge는 requested +{requested_points:.2f}pt "
        "threshold harden 후보를 만들었습니다."
    )
    proposed_behavior_ko = (
        f"requested +{requested_points:.2f}pt / effective +{effective_points:.2f}pt 기준으로 "
        "threshold harden log-only review 후보를 먼저 관찰합니다."
    )
    evidence_parts = []
    if context_summary:
        evidence_parts.append(context_summary)
    evidence_parts.append(
        f"requested +{requested_points:.2f}pt / effective +{effective_points:.2f}pt"
    )
    if reason_keys:
        evidence_parts.append(f"reason={', '.join(reason_keys)}")
    if _to_bool(decision_counterfactual.get("bridge_changed_decision"), False):
        evidence_parts.append(
            "decision="
            f"{_to_text(decision_counterfactual.get('without_bridge_decision'), '-')}->"
            f"{_to_text(decision_counterfactual.get('with_bridge_decision'), '-')}"
        )
    failure_modes = _as_str_list(bridge.get("failure_modes"))
    guard_modes = _as_str_list(bridge.get("guard_modes"))
    if failure_modes:
        evidence_parts.append(f"failure={', '.join(failure_modes)}")
    if guard_modes:
        evidence_parts.append(f"guard={', '.join(guard_modes)}")
    payload = build_state25_threshold_patch_review_candidate_v1(
        concern_summary_ko=concern_summary_ko,
        current_behavior_ko=current_behavior_ko,
        proposed_behavior_ko=proposed_behavior_ko,
        evidence_summary_ko=" | ".join(part for part in evidence_parts if part),
        threshold_delta_points_requested=requested_points,
        threshold_delta_points_effective=effective_points,
        threshold_delta_pct_requested=requested_pct,
        threshold_delta_pct_effective=effective_pct,
        threshold_delta_direction=direction,
        threshold_delta_reason_keys=reason_keys,
        threshold_base_points=_to_float(requested.get("threshold_base_points"), 0.0),
        threshold_candidate_points=_to_float(
            effective.get("threshold_candidate_points")
            or requested.get("threshold_candidate_points"),
            0.0,
        ),
        state25_execution_symbol_allowlist=[symbol] if symbol and symbol != "ALL" else None,
        state25_execution_entry_stage_allowlist=[entry_stage] if entry_stage else None,
        state25_execution_bind_mode=state25_execution_bind_mode,
        candidate_id=_to_text(bridge.get("bridge_decision_id")),
        trace_id=f"state25_context_bridge_threshold::{_to_text(bridge.get('bridge_decision_id')) or symbol}",
        evidence_registry_keys=_bridge_context_evidence_registry_keys(row_map),
        without_bridge_decision=_to_text(decision_counterfactual.get("without_bridge_decision")),
        with_bridge_decision=_to_text(decision_counterfactual.get("with_bridge_decision")),
        bridge_changed_decision=_to_bool(
            decision_counterfactual.get("bridge_changed_decision"), False
        ),
        score_reference_value=_to_float(
            decision_counterfactual.get("score_reference_value"), 0.0
        ),
        score_source_field=_to_text(decision_counterfactual.get("score_source_field")),
    )
    execution_bind_mode = _to_text(state25_execution_bind_mode, "log_only")
    payload["bridge_source_lane"] = (
        "STATE25_CONTEXT_BRIDGE_THRESHOLD_BOUNDED_LIVE"
        if execution_bind_mode in {"bounded_live", "canary"}
        else "STATE25_CONTEXT_BRIDGE_THRESHOLD_LOG_ONLY"
    )
    payload["bridge_stage"] = _to_text(bridge.get("bridge_stage"))
    payload["bridge_translator_state"] = _to_text(bridge.get("translator_state"))
    payload["bridge_context_summary_ko"] = context_summary
    payload["bridge_threshold_requested_points"] = requested_points
    payload["bridge_threshold_effective_points"] = effective_points
    payload["bridge_threshold_suppressed_count"] = int(1 if suppressed else 0)
    payload["bridge_threshold_direction"] = direction
    payload["bridge_threshold_reason_keys"] = reason_keys
    payload["bridge_threshold_requested_pct"] = requested_pct
    payload["bridge_threshold_effective_pct"] = effective_pct
    payload["bridge_threshold_base_points"] = _to_float(
        requested.get("threshold_base_points"), 0.0
    )
    payload["bridge_threshold_candidate_points"] = _to_float(
        effective.get("threshold_candidate_points")
        or requested.get("threshold_candidate_points"),
        0.0,
    )
    payload["bridge_threshold_changed_decision"] = _to_bool(
        decision_counterfactual.get("bridge_changed_decision"),
        False,
    )
    payload["bridge_without_bridge_decision"] = _to_text(
        decision_counterfactual.get("without_bridge_decision")
    )
    payload["bridge_with_bridge_decision"] = _to_text(
        decision_counterfactual.get("with_bridge_decision")
    )
    payload["bridge_score_reference_value"] = _to_float(
        decision_counterfactual.get("score_reference_value"),
        0.0,
    )
    payload["bridge_score_source_field"] = _to_text(
        decision_counterfactual.get("score_source_field")
    )
    payload["bridge_failure_modes"] = failure_modes
    payload["bridge_guard_modes"] = guard_modes
    payload["bridge_trace_reason_codes"] = _as_str_list(bridge.get("trace_reason_codes"))
    payload["bridge_trace_lines_ko"] = _as_str_list(bridge.get("trace_lines_ko"))
    payload["bridge_component_activation"] = _mapping(
        bridge.get("component_activation")
    )
    payload["bridge_component_activation_reasons"] = _mapping(
        bridge.get("component_activation_reasons")
    )
    payload["bridge_decision_id"] = _to_text(bridge.get("bridge_decision_id"))
    payload["hindsight_link_key"] = _to_text(bridge.get("hindsight_link_key"))
    payload["proposal_link_key"] = _to_text(bridge.get("proposal_link_key"))
    payload["state25_candidate_context_bridge_v1"] = bridge
    proposal_envelope = _mapping(payload.get("proposal_envelope"))
    evidence_snapshot = _mapping(proposal_envelope.get("evidence_snapshot"))
    evidence_snapshot.update(
        {
            "bridge_source_lane": payload["bridge_source_lane"],
            "bridge_stage": payload["bridge_stage"],
            "bridge_translator_state": payload["bridge_translator_state"],
            "bridge_context_summary_ko": context_summary,
            "bridge_threshold_requested_points": requested_points,
            "bridge_threshold_effective_points": effective_points,
            "bridge_threshold_suppressed_count": payload["bridge_threshold_suppressed_count"],
            "bridge_threshold_direction": direction,
            "bridge_threshold_reason_keys": reason_keys,
            "bridge_threshold_changed_decision": payload["bridge_threshold_changed_decision"],
            "bridge_without_bridge_decision": payload["bridge_without_bridge_decision"],
            "bridge_with_bridge_decision": payload["bridge_with_bridge_decision"],
            "bridge_score_reference_value": payload["bridge_score_reference_value"],
            "bridge_failure_modes": failure_modes,
            "bridge_guard_modes": guard_modes,
            "bridge_trace_reason_codes": payload["bridge_trace_reason_codes"],
            "bridge_component_activation": payload["bridge_component_activation"],
            "bridge_component_activation_reasons": payload["bridge_component_activation_reasons"],
            "bridge_decision_id": payload["bridge_decision_id"],
        }
    )
    proposal_envelope["evidence_snapshot"] = evidence_snapshot
    payload["proposal_envelope"] = proposal_envelope
    payload["report_lines_ko"] = list(payload.get("report_lines_ko") or []) + [
        f"- bridge_context: {context_summary or '-'}",
        f"- bridge_threshold requested/effective: +{requested_points:.2f}pt / +{effective_points:.2f}pt",
    ]
    return payload
