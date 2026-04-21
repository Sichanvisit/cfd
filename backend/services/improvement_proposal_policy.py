from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from backend.services.improvement_status_policy import (
    PROPOSAL_STAGE_REPORT_READY,
    READINESS_STATUS_READY_FOR_REVIEW,
    normalize_proposal_stage,
    normalize_readiness_status,
)


IMPROVEMENT_PROPOSAL_POLICY_CONTRACT_VERSION = "improvement_proposal_policy_v1"
REQUIRED_PROPOSAL_ENVELOPE_FIELDS = (
    "proposal_id",
    "proposal_type",
    "scope_key",
    "trace_id",
    "proposal_stage",
    "readiness_status",
    "summary_ko",
    "why_now_ko",
    "recommended_action_ko",
    "blocking_reason",
    "decision_deadline_ts",
)


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _compact_slug(value: str, *, fallback: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", _text(value)).strip("_").lower()
    return normalized or fallback


def build_improvement_proposal_id(
    *,
    proposal_type: str,
    scope_key: str,
    trace_id: str = "",
) -> str:
    type_slug = _compact_slug(proposal_type, fallback="proposal")
    scope_slug = _compact_slug(scope_key, fallback="scope")
    trace_slug = _compact_slug(trace_id, fallback=uuid4().hex[:8])
    return f"prop_{type_slug}_{scope_slug}_{trace_slug}"


def build_improvement_proposal_envelope(
    *,
    proposal_type: str,
    scope_key: str,
    trace_id: str,
    summary_ko: str,
    why_now_ko: str,
    recommended_action_ko: str,
    proposal_stage: str = PROPOSAL_STAGE_REPORT_READY,
    readiness_status: str = READINESS_STATUS_READY_FOR_REVIEW,
    blocking_reason: str = "",
    decision_deadline_ts: str = "",
    proposal_id: str = "",
    confidence_level: str = "",
    expected_effect_ko: str = "",
    scope_note_ko: str = "",
    evidence_snapshot: Mapping[str, Any] | None = None,
    report_message_ref: str = "",
    check_message_ref: str = "",
    supersedes_proposal_id: str = "",
    related_approval_id: str = "",
    related_apply_job_key: str = "",
) -> dict[str, Any]:
    normalized_type = _text(proposal_type).upper()
    normalized_scope = _text(scope_key)
    normalized_trace = _text(trace_id)
    normalized_stage = normalize_proposal_stage(proposal_stage)
    normalized_readiness = normalize_readiness_status(readiness_status)
    resolved_id = _text(proposal_id) or build_improvement_proposal_id(
        proposal_type=normalized_type,
        scope_key=normalized_scope,
        trace_id=normalized_trace,
    )
    envelope = {
        "proposal_id": resolved_id,
        "proposal_type": normalized_type,
        "scope_key": normalized_scope,
        "trace_id": normalized_trace,
        "proposal_stage": normalized_stage,
        "readiness_status": normalized_readiness,
        "summary_ko": _text(summary_ko),
        "why_now_ko": _text(why_now_ko),
        "recommended_action_ko": _text(recommended_action_ko),
        "blocking_reason": _text(blocking_reason),
        "decision_deadline_ts": _text(decision_deadline_ts),
        "confidence_level": _text(confidence_level),
        "expected_effect_ko": _text(expected_effect_ko),
        "scope_note_ko": _text(scope_note_ko),
        "evidence_snapshot": dict(evidence_snapshot or {}),
        "report_message_ref": _text(report_message_ref),
        "check_message_ref": _text(check_message_ref),
        "supersedes_proposal_id": _text(supersedes_proposal_id),
        "related_approval_id": _text(related_approval_id),
        "related_apply_job_key": _text(related_apply_job_key),
    }
    validate_improvement_proposal_envelope(envelope)
    return envelope


def validate_improvement_proposal_envelope(
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = _mapping(envelope)
    missing = [
        field for field in REQUIRED_PROPOSAL_ENVELOPE_FIELDS if field not in payload
    ]
    if missing:
        raise ValueError(f"missing_proposal_envelope_fields::{','.join(missing)}")
    if not _text(payload.get("proposal_type")):
        raise ValueError("proposal_type_required")
    if not _text(payload.get("scope_key")):
        raise ValueError("scope_key_required")
    if not _text(payload.get("trace_id")):
        raise ValueError("trace_id_required")
    normalize_proposal_stage(payload.get("proposal_stage"))
    normalize_readiness_status(payload.get("readiness_status"))
    return payload


def ensure_improvement_proposal_envelope(
    candidate: Mapping[str, Any] | None,
    *,
    proposal_type: str = "",
    trace_id: str = "",
    default_proposal_stage: str = PROPOSAL_STAGE_REPORT_READY,
    default_readiness_status: str = READINESS_STATUS_READY_FOR_REVIEW,
) -> dict[str, Any]:
    candidate_map = _mapping(candidate)
    embedded = _mapping(candidate_map.get("proposal_envelope"))
    if embedded:
        validated = validate_improvement_proposal_envelope(embedded)
        return dict(validated)

    resolved_type = _text(
        proposal_type
        or candidate_map.get("proposal_type")
        or candidate_map.get("review_type")
    ).upper()
    resolved_trace = _text(trace_id or candidate_map.get("trace_id"))
    resolved_scope = _text(candidate_map.get("scope_key"))
    summary_ko = _text(
        candidate_map.get("summary_ko")
        or candidate_map.get("proposal_summary_ko")
        or candidate_map.get("reason_summary_ko")
        or candidate_map.get("reason_summary")
    )
    why_now_ko = _text(
        candidate_map.get("why_now_ko")
        or candidate_map.get("evidence_summary_ko")
        or candidate_map.get("trigger_summary")
        or summary_ko
    )
    recommended_action_ko = _text(
        candidate_map.get("recommended_action_ko")
        or candidate_map.get("recommended_action_note")
        or candidate_map.get("recommended_next_action")
    )
    return build_improvement_proposal_envelope(
        proposal_id=_text(
            candidate_map.get("proposal_id") or candidate_map.get("candidate_id")
        ),
        proposal_type=resolved_type,
        scope_key=resolved_scope,
        trace_id=resolved_trace,
        proposal_stage=_text(
            candidate_map.get("proposal_stage"),
            default_proposal_stage,
        ),
        readiness_status=_text(
            candidate_map.get("readiness_status"),
            default_readiness_status,
        ),
        summary_ko=summary_ko,
        why_now_ko=why_now_ko,
        recommended_action_ko=recommended_action_ko,
        blocking_reason=_text(candidate_map.get("blocking_reason")),
        decision_deadline_ts=_text(candidate_map.get("decision_deadline_ts")),
        confidence_level=_text(candidate_map.get("confidence_level")),
        expected_effect_ko=_text(candidate_map.get("expected_effect_ko")),
        scope_note_ko=_text(
            candidate_map.get("scope_note_ko") or candidate_map.get("scope_note")
        ),
        evidence_snapshot=_mapping(candidate_map.get("evidence_snapshot")),
        report_message_ref=_text(candidate_map.get("report_message_ref")),
        check_message_ref=_text(candidate_map.get("check_message_ref")),
        supersedes_proposal_id=_text(candidate_map.get("supersedes_proposal_id")),
        related_approval_id=_text(
            candidate_map.get("related_approval_id") or candidate_map.get("approval_id")
        ),
        related_apply_job_key=_text(
            candidate_map.get("related_apply_job_key")
            or candidate_map.get("apply_job_key")
        ),
    )


def build_improvement_proposal_envelope_baseline() -> dict[str, Any]:
    example = build_improvement_proposal_envelope(
        proposal_type="STATE25_WEIGHT_PATCH_REVIEW",
        scope_key="BTCUSD:state25:upper_wick_weight",
        trace_id="trace_state25_btc_example",
        summary_ko="윗꼬리 비중 과대 해석 조정 제안",
        why_now_ko="최근 BTC 장면에서 상방 추진력 대비 하단 해석이 과도하게 읽혔습니다.",
        recommended_action_ko="bounded log-only 가중치 조정을 시험 반영 후 검토합니다.",
        confidence_level="MEDIUM",
        expected_effect_ko="상방 추진력 오판을 줄이고 조기 반전 판단을 더 안정적으로 만들 수 있습니다.",
        scope_note_ko="symbol=BTCUSD | entry_stage=READY | binding_mode=log_only",
        evidence_snapshot={"scene": "upper_wick_bias", "sample_count": 7},
    )
    return {
        "contract_version": IMPROVEMENT_PROPOSAL_POLICY_CONTRACT_VERSION,
        "required_fields": list(REQUIRED_PROPOSAL_ENVELOPE_FIELDS),
        "example_envelope": example,
    }


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_improvement_proposal_envelope_baseline_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "improvement_proposal_envelope_baseline_latest.json",
        directory / "improvement_proposal_envelope_baseline_latest.md",
    )


def render_improvement_proposal_envelope_baseline_markdown(payload: dict[str, Any]) -> str:
    example = _mapping(payload.get("example_envelope"))
    lines = [
        "# Improvement Proposal Envelope Baseline",
        "",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        "",
        "## Required Fields",
    ]
    for field_name in payload.get("required_fields", []):
        lines.append(f"- `{field_name}`")
    lines.extend(["", "## Example Envelope"])
    for key in REQUIRED_PROPOSAL_ENVELOPE_FIELDS:
        lines.append(f"- {key}: `{example.get(key, '')}`")
    lines.extend(
        [
            "",
            "## Optional Highlights",
            f"- confidence_level: `{example.get('confidence_level', '')}`",
            f"- expected_effect_ko: {example.get('expected_effect_ko', '')}",
            f"- scope_note_ko: {example.get('scope_note_ko', '')}",
        ]
    )
    return "\n".join(lines)


def write_improvement_proposal_envelope_baseline_snapshot(
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_improvement_proposal_envelope_baseline()
    default_json_path, default_markdown_path = (
        default_improvement_proposal_envelope_baseline_paths()
    )
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        render_improvement_proposal_envelope_baseline_markdown(payload),
        encoding="utf-8",
    )
    return {
        "contract_version": payload["contract_version"],
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }
