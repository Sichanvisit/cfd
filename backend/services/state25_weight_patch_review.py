from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from backend.services.improvement_proposal_policy import (
    build_improvement_proposal_envelope,
)
from backend.services.learning_registry_resolver import (
    LEARNING_REGISTRY_BINDING_MODE_DERIVED,
    LEARNING_REGISTRY_BINDING_MODE_EXACT,
    LEARNING_REGISTRY_BINDING_MODE_FALLBACK,
    build_learning_registry_binding_fields,
    build_learning_registry_relation,
    resolve_learning_registry_row,
)
from backend.services.state25_context_bridge import (
    build_state25_candidate_context_bridge_v1,
)
from backend.services.teacher_pattern_active_candidate_runtime import (
    normalize_state25_teacher_weight_overrides,
    render_state25_teacher_weight_override_lines_ko,
)


STATE25_WEIGHT_PATCH_REVIEW_CONTRACT_VERSION = "state25_weight_patch_review_v0"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    rows: list[str] = []
    for raw in value:
        text = _to_text(raw)
        if text:
            rows.append(text)
    return rows


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalized_registry_key_list(
    values: list[object] | tuple[object, ...] | None,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        key = _to_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _target_registry_keys_from_overrides(
    overrides: Mapping[str, Any] | None,
) -> list[str]:
    return _normalized_registry_key_list(
        [f"state25_weight:{_to_text(weight_key)}" for weight_key in dict(overrides or {}).keys()]
    )


def _weight_review_binding_mode(target_registry_keys: list[str]) -> str:
    if len(target_registry_keys) == 1:
        return LEARNING_REGISTRY_BINDING_MODE_EXACT
    if len(target_registry_keys) >= 2:
        return LEARNING_REGISTRY_BINDING_MODE_DERIVED
    return LEARNING_REGISTRY_BINDING_MODE_FALLBACK


def _render_state25_weight_override_lines_via_registry(
    overrides: Mapping[str, Any] | None,
) -> list[str]:
    normalized = normalize_state25_teacher_weight_overrides(overrides)
    if not normalized:
        return []

    lines: list[str] = []
    fallback_lines = render_state25_teacher_weight_override_lines_ko(normalized)
    fallback_by_key = {
        _to_text(weight_key): line
        for weight_key, line in zip(normalized.keys(), fallback_lines)
    }
    for weight_key, proposed_value in normalized.items():
        registry_row = resolve_learning_registry_row(f"state25_weight:{_to_text(weight_key)}")
        label_ko = _to_text(registry_row.get("label_ko"), weight_key)
        description_ko = _to_text(registry_row.get("description_ko"))
        baseline_value = 1.0
        if abs(float(proposed_value) - baseline_value) < 1e-9:
            delta_text = "유지"
        elif float(proposed_value) > baseline_value:
            delta_text = f"상향 x{float(proposed_value):.2f}"
        else:
            delta_text = f"하향 x{float(proposed_value):.2f}"
        if label_ko and description_ko:
            lines.append(
                f"- {label_ko}: {description_ko} / 기준 x{baseline_value:.2f} -> 제안 x{float(proposed_value):.2f} ({delta_text})"
            )
        elif label_ko:
            lines.append(
                f"- {label_ko}: 기준 x{baseline_value:.2f} -> 제안 x{float(proposed_value):.2f} ({delta_text})"
            )
        else:
            fallback_line = fallback_by_key.get(_to_text(weight_key))
            if fallback_line:
                lines.append(fallback_line)
    return lines or fallback_lines


def build_state25_weight_patch_review_candidate_v1(
    *,
    concern_summary_ko: str,
    current_behavior_ko: str,
    proposed_behavior_ko: str,
    evidence_summary_ko: str,
    state25_teacher_weight_overrides: Mapping[str, Any] | None,
    state25_execution_symbol_allowlist: list[str] | None = None,
    state25_execution_entry_stage_allowlist: list[str] | None = None,
    state25_execution_bind_mode: str = "log_only",
    target_component_ko: str = "state25 해석 가중치",
    proposal_summary_ko: str = "",
    candidate_id: str = "",
    trace_id: str = "",
    evidence_registry_keys: list[str] | None = None,
) -> dict[str, Any]:
    symbol_scope = _as_str_list(state25_execution_symbol_allowlist)
    entry_stage_scope = _as_str_list(state25_execution_entry_stage_allowlist)
    overrides = normalize_state25_teacher_weight_overrides(
        state25_teacher_weight_overrides
    )
    resolved_evidence_registry_keys = _normalized_registry_key_list(evidence_registry_keys)
    target_registry_keys = _target_registry_keys_from_overrides(overrides)
    binding_mode = _weight_review_binding_mode(target_registry_keys)
    primary_registry_key = target_registry_keys[0] if target_registry_keys else ""
    execution_bind_mode = _to_text(state25_execution_bind_mode, "log_only")
    bounded_live_enabled = execution_bind_mode in {"bounded_live", "canary"}
    action_target = (
        "state25_weight_patch_bounded_live"
        if bounded_live_enabled
        else "state25_weight_patch_log_only"
    )
    registry_binding_fields = build_learning_registry_binding_fields(
        primary_registry_key,
        binding_mode=binding_mode,
    )
    registry_relation = build_learning_registry_relation(
        evidence_registry_keys=resolved_evidence_registry_keys,
        target_registry_keys=target_registry_keys,
        binding_mode=binding_mode,
    )
    scope_symbol = ",".join(symbol_scope) or "ALL"
    scope_stage = ",".join(entry_stage_scope) or "ALL"
    scope_key = (
        f"STATE25_WEIGHT_PATCH::{scope_symbol}::{scope_stage}::"
        + ",".join(sorted(overrides.keys()))
    )
    proposal_summary = (
        _to_text(proposal_summary_ko)
        or f"{target_component_ko} 조정 제안: {concern_summary_ko}"
    )
    scope_note_ko = (
        f"symbol={scope_symbol} | entry_stage={scope_stage} | "
        f"binding_mode={execution_bind_mode}"
    )
    recommended_action_ko = (
        "bounded live 가중치 조정을 아주 좁은 범위에서 시험 반영합니다."
        if bounded_live_enabled
        else "bounded log-only 가중치 조정을 시험 반영합니다."
    )
    report_lines = [
        f"관찰 장면: {concern_summary_ko}",
        f"현재 해석: {current_behavior_ko}",
        f"제안 해석: {proposed_behavior_ko}",
        f"근거 요약: {evidence_summary_ko}",
        f"적용 범위: {scope_note_ko}",
        "조정 항목:",
        *(
            _render_state25_weight_override_lines_via_registry(overrides)
            or render_state25_teacher_weight_override_lines_ko(overrides)
        ),
    ]
    proposal_envelope = build_improvement_proposal_envelope(
        proposal_id=_to_text(candidate_id),
        proposal_type="STATE25_WEIGHT_PATCH_REVIEW",
        scope_key=scope_key,
        trace_id=_to_text(trace_id),
        summary_ko=proposal_summary,
        why_now_ko=_to_text(evidence_summary_ko),
        recommended_action_ko=recommended_action_ko,
        confidence_level="MEDIUM",
        expected_effect_ko=_to_text(proposed_behavior_ko),
        scope_note_ko=scope_note_ko,
        evidence_snapshot={
            "concern_summary_ko": _to_text(concern_summary_ko),
            "current_behavior_ko": _to_text(current_behavior_ko),
            "proposed_behavior_ko": _to_text(proposed_behavior_ko),
            "state25_execution_symbol_allowlist": symbol_scope,
            "state25_execution_entry_stage_allowlist": entry_stage_scope,
            "state25_execution_bind_mode": execution_bind_mode,
            "state25_teacher_weight_overrides": overrides,
            "evidence_registry_keys": resolved_evidence_registry_keys,
            "target_registry_keys": target_registry_keys,
            "registry_binding_mode": binding_mode,
            "registry_binding_version": registry_binding_fields.get(
                "registry_binding_version"
            ),
        },
    )
    return {
        "contract_version": STATE25_WEIGHT_PATCH_REVIEW_CONTRACT_VERSION,
        "generated_at": _now_iso(),
        "trace_id": _to_text(trace_id),
        "review_type": "STATE25_WEIGHT_PATCH_REVIEW",
        "governance_action": "state25_weight_patch_review",
        "action_target": action_target,
        "scope_key": scope_key,
        "symbol": (symbol_scope[0] if len(symbol_scope) == 1 else ""),
        "candidate_id": _to_text(candidate_id),
        "target_component_ko": _to_text(target_component_ko, "state25 해석 가중치"),
        "concern_summary_ko": _to_text(concern_summary_ko),
        "current_behavior_ko": _to_text(current_behavior_ko),
        "proposed_behavior_ko": _to_text(proposed_behavior_ko),
        "evidence_summary_ko": _to_text(evidence_summary_ko),
        "proposal_summary_ko": proposal_summary,
        "reason_summary_ko": proposal_summary,
        "scope_note_ko": scope_note_ko,
        **registry_binding_fields,
        "registry_binding_ready": bool(registry_relation.get("binding_ready")),
        "evidence_registry_keys": list(
            registry_relation.get("evidence_registry_keys") or []
        ),
        "target_registry_keys": list(
            registry_relation.get("target_registry_keys") or []
        ),
        "evidence_bindings": list(registry_relation.get("evidence_bindings") or []),
        "target_bindings": list(registry_relation.get("target_bindings") or []),
        "proposal_id": proposal_envelope["proposal_id"],
        "proposal_type": proposal_envelope["proposal_type"],
        "proposal_stage": proposal_envelope["proposal_stage"],
        "readiness_status": proposal_envelope["readiness_status"],
        "summary_ko": proposal_envelope["summary_ko"],
        "why_now_ko": proposal_envelope["why_now_ko"],
        "recommended_action_ko": proposal_envelope["recommended_action_ko"],
        "blocking_reason": proposal_envelope["blocking_reason"],
        "confidence_level": proposal_envelope["confidence_level"],
        "expected_effect_ko": proposal_envelope["expected_effect_ko"],
        "decision_deadline_ts": proposal_envelope["decision_deadline_ts"],
        "state25_execution_bind_mode": execution_bind_mode,
        "state25_execution_symbol_allowlist": symbol_scope,
        "state25_execution_entry_stage_allowlist": entry_stage_scope,
        "state25_teacher_weight_overrides": overrides,
        "proposal_envelope": proposal_envelope,
        "weight_patch": {
            "state25_execution_bind_mode": execution_bind_mode,
            "state25_execution_symbol_allowlist": symbol_scope,
            "state25_execution_entry_stage_allowlist": entry_stage_scope,
            "state25_weight_log_only_enabled": not bounded_live_enabled,
            "state25_weight_bounded_live_enabled": bounded_live_enabled,
            "state25_teacher_weight_overrides": overrides,
            "target_registry_keys": target_registry_keys,
        },
        "report_title_ko": "자동 반영 제안 | 가중치 조정",
        "report_lines_ko": report_lines,
        "recommended_action_note": recommended_action_ko,
        "recommended_next_action": (
            "review_state25_weight_patch_and_activate_bounded_live_if_safe"
            if bounded_live_enabled
            else "review_state25_weight_patch_and_apply_if_safe"
        ),
    }


def _bridge_weight_target_overrides(
    bridge_payload: Mapping[str, Any] | None,
    *,
    field_name: str,
) -> dict[str, float]:
    rows = _mapping(bridge_payload).get(field_name)
    if not isinstance(rows, Mapping):
        return {}
    overrides: dict[str, float] = {}
    for raw_weight_key, raw_row in dict(rows).items():
        weight_key = _to_text(raw_weight_key)
        row_map = _mapping(raw_row)
        if not weight_key or not row_map:
            continue
        try:
            overrides[weight_key] = float(row_map.get("target_value"))
        except Exception:
            continue
    return normalize_state25_teacher_weight_overrides(overrides)


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
    return _normalized_registry_key_list(keys)


def build_state25_weight_patch_review_candidate_from_context_bridge_v1(
    runtime_row: Mapping[str, Any] | None,
    *,
    bridge_payload: Mapping[str, Any] | None = None,
    state25_execution_bind_mode: str = "log_only",
) -> dict[str, Any]:
    row_map = _mapping(runtime_row)
    bridge = _mapping(bridge_payload or row_map.get("state25_candidate_context_bridge_v1"))
    requested_overrides = _bridge_weight_target_overrides(
        bridge,
        field_name="weight_adjustments_requested",
    )
    if not requested_overrides and row_map:
        rebuilt_bridge = _mapping(build_state25_candidate_context_bridge_v1(row_map))
        rebuilt_requested_overrides = _bridge_weight_target_overrides(
            rebuilt_bridge,
            field_name="weight_adjustments_requested",
        )
        if rebuilt_requested_overrides:
            bridge = rebuilt_bridge
            requested_overrides = rebuilt_requested_overrides
    if not requested_overrides:
        return {}

    effective_overrides = _bridge_weight_target_overrides(
        bridge,
        field_name="weight_adjustments_effective",
    )
    suppressed = _mapping(bridge.get("weight_adjustments_suppressed"))
    symbol = _to_text(row_map.get("symbol"), "ALL").upper()
    entry_stage = _to_text(row_map.get("entry_stage"))
    consumer_side = _to_text(row_map.get("consumer_check_side")).upper() or "-"
    context_summary = _to_text(row_map.get("context_bundle_summary_ko")) or _to_text(
        row_map.get("context_conflict_label_ko")
    )
    bias_side = _to_text(bridge.get("context_bias_side")).upper()
    try:
        bias_confidence = float(bridge.get("context_bias_side_confidence"))
    except Exception:
        bias_confidence = 0.0
    requested_count = len(requested_overrides)
    effective_count = len(effective_overrides)
    suppressed_count = len(suppressed)
    failure_modes = _as_str_list(bridge.get("failure_modes"))
    guard_modes = _as_str_list(bridge.get("guard_modes"))
    trace_reason_codes = _as_str_list(bridge.get("trace_reason_codes"))
    concern_summary_ko = (
        f"{symbol} {consumer_side} 해석에서 큰 그림 맥락과의 충돌이 관찰되어 "
        "state25 weight-only log-only review가 필요합니다."
    )
    if context_summary:
        concern_summary_ko = (
            f"{symbol} {consumer_side} 해석에서 `{context_summary}` 맥락이 관찰되어 "
            "state25 weight-only log-only review가 필요합니다."
        )
    current_behavior_ko = (
        f"현재 state25는 {consumer_side} 해석을 유지하고 있으나 "
        f"context bridge는 {requested_count}건의 weight 조정 요청을 만들었습니다."
    )
    if bias_side:
        current_behavior_ko = (
            f"현재 state25는 {consumer_side} 해석을 유지하고 있으나 "
            f"context bridge는 {bias_side} 편향({bias_confidence:.2f})을 읽고 "
            f"{requested_count}건의 weight 조정 요청을 만들었습니다."
        )
    proposed_behavior_ko = (
        f"requested {requested_count} / effective {effective_count} / suppressed {suppressed_count} 기준으로 "
        "state25 weight-only bounded review 후보를 log-only로 먼저 관찰합니다."
    )
    evidence_summary_parts = []
    if context_summary:
        evidence_summary_parts.append(context_summary)
    evidence_summary_parts.append(
        f"requested {requested_count} / effective {effective_count} / suppressed {suppressed_count}"
    )
    if failure_modes:
        evidence_summary_parts.append(f"failure={', '.join(failure_modes)}")
    if guard_modes:
        evidence_summary_parts.append(f"guard={', '.join(guard_modes)}")
    evidence_summary_ko = " | ".join(part for part in evidence_summary_parts if part)

    payload = build_state25_weight_patch_review_candidate_v1(
        concern_summary_ko=concern_summary_ko,
        current_behavior_ko=current_behavior_ko,
        proposed_behavior_ko=proposed_behavior_ko,
        evidence_summary_ko=evidence_summary_ko,
        state25_teacher_weight_overrides=requested_overrides,
        state25_execution_symbol_allowlist=[symbol] if symbol and symbol != "ALL" else None,
        state25_execution_entry_stage_allowlist=[entry_stage] if entry_stage else None,
        state25_execution_bind_mode=state25_execution_bind_mode,
        target_component_ko="state25 context bridge weight",
        proposal_summary_ko=f"{symbol} state25 context bridge weight review 후보",
        candidate_id=_to_text(bridge.get("bridge_decision_id")),
        trace_id=f"state25_context_bridge::{_to_text(bridge.get('bridge_decision_id')) or symbol}",
        evidence_registry_keys=_bridge_context_evidence_registry_keys(row_map),
    )
    execution_bind_mode = _to_text(state25_execution_bind_mode, "log_only")
    payload["bridge_source_lane"] = (
        "STATE25_CONTEXT_BRIDGE_WEIGHT_ONLY_BOUNDED_LIVE"
        if execution_bind_mode in {"bounded_live", "canary"}
        else "STATE25_CONTEXT_BRIDGE_WEIGHT_ONLY_LOG_ONLY"
    )
    payload["bridge_stage"] = _to_text(bridge.get("bridge_stage"))
    payload["bridge_translator_state"] = _to_text(bridge.get("translator_state"))
    payload["bridge_context_summary_ko"] = context_summary
    payload["bridge_context_bias_side"] = bias_side
    payload["bridge_context_bias_confidence"] = bias_confidence
    payload["bridge_context_bias_source_keys"] = _as_str_list(
        bridge.get("context_bias_side_source_keys")
    )
    payload["bridge_weight_requested_count"] = requested_count
    payload["bridge_weight_effective_count"] = effective_count
    payload["bridge_weight_suppressed_count"] = suppressed_count
    payload["bridge_requested_overrides"] = requested_overrides
    payload["bridge_effective_overrides"] = effective_overrides
    payload["bridge_failure_modes"] = failure_modes
    payload["bridge_guard_modes"] = guard_modes
    payload["bridge_trace_reason_codes"] = trace_reason_codes
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
            "bridge_weight_requested_count": requested_count,
            "bridge_weight_effective_count": effective_count,
            "bridge_weight_suppressed_count": suppressed_count,
            "bridge_requested_overrides": requested_overrides,
            "bridge_effective_overrides": effective_overrides,
            "bridge_failure_modes": failure_modes,
            "bridge_guard_modes": guard_modes,
            "bridge_trace_reason_codes": trace_reason_codes,
            "bridge_component_activation": payload["bridge_component_activation"],
            "bridge_component_activation_reasons": payload["bridge_component_activation_reasons"],
            "bridge_decision_id": payload["bridge_decision_id"],
        }
    )
    proposal_envelope["evidence_snapshot"] = evidence_snapshot
    payload["proposal_envelope"] = proposal_envelope
    payload["report_lines_ko"] = list(payload.get("report_lines_ko") or []) + [
        f"- bridge_context: {context_summary or '-'}",
        f"- bridge_requested/effective/suppressed: {requested_count}/{effective_count}/{suppressed_count}",
    ]
    return payload
