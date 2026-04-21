from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


IMPROVEMENT_STATUS_POLICY_CONTRACT_VERSION = "improvement_status_policy_v1"


READINESS_STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
READINESS_STATUS_PENDING_EVIDENCE = "PENDING_EVIDENCE"
READINESS_STATUS_BLOCKED = "BLOCKED"
READINESS_STATUS_READY_FOR_REVIEW = "READY_FOR_REVIEW"
READINESS_STATUS_READY_FOR_APPLY = "READY_FOR_APPLY"
READINESS_STATUS_APPLIED = "APPLIED"

READINESS_STATUSES = (
    READINESS_STATUS_NOT_APPLICABLE,
    READINESS_STATUS_PENDING_EVIDENCE,
    READINESS_STATUS_BLOCKED,
    READINESS_STATUS_READY_FOR_REVIEW,
    READINESS_STATUS_READY_FOR_APPLY,
    READINESS_STATUS_APPLIED,
)


PROPOSAL_STAGE_OBSERVE = "OBSERVE"
PROPOSAL_STAGE_REPORT_READY = "REPORT_READY"
PROPOSAL_STAGE_REVIEW_PENDING = "REVIEW_PENDING"
PROPOSAL_STAGE_APPROVED_FOR_APPLY = "APPROVED_FOR_APPLY"
PROPOSAL_STAGE_APPLIED = "APPLIED"
PROPOSAL_STAGE_REJECTED = "REJECTED"
PROPOSAL_STAGE_HELD = "HELD"
PROPOSAL_STAGE_SUPERSEDED = "SUPERSEDED"
PROPOSAL_STAGE_EXPIRED = "EXPIRED"

PROPOSAL_STAGES = (
    PROPOSAL_STAGE_OBSERVE,
    PROPOSAL_STAGE_REPORT_READY,
    PROPOSAL_STAGE_REVIEW_PENDING,
    PROPOSAL_STAGE_APPROVED_FOR_APPLY,
    PROPOSAL_STAGE_APPLIED,
    PROPOSAL_STAGE_REJECTED,
    PROPOSAL_STAGE_HELD,
    PROPOSAL_STAGE_SUPERSEDED,
    PROPOSAL_STAGE_EXPIRED,
)


APPROVAL_STATUS_PENDING = "pending"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_HELD = "held"
APPROVAL_STATUS_REJECTED = "rejected"
APPROVAL_STATUS_EXPIRED = "expired"
APPROVAL_STATUS_APPLIED = "applied"
APPROVAL_STATUS_CANCELLED = "cancelled"

APPROVAL_STATUSES = (
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_HELD,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STATUS_EXPIRED,
    APPROVAL_STATUS_APPLIED,
    APPROVAL_STATUS_CANCELLED,
)

APPROVAL_ACTIONABLE_STATUSES = (
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_HELD,
)
APPROVAL_TERMINAL_STATUSES = (
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STATUS_EXPIRED,
    APPROVAL_STATUS_APPLIED,
    APPROVAL_STATUS_CANCELLED,
)
APPROVAL_BACKLOG_STATUSES = (
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_HELD,
)
APPROVAL_CONFLICT_TRACKING_STATUSES = (
    APPROVAL_STATUS_PENDING,
    APPROVAL_STATUS_HELD,
    APPROVAL_STATUS_APPROVED,
)

APPROVAL_ACTION_TO_STATUS = {
    "approve": APPROVAL_STATUS_APPROVED,
    "hold": APPROVAL_STATUS_HELD,
    "reject": APPROVAL_STATUS_REJECTED,
}


READINESS_STATUS_LABELS_KO = {
    READINESS_STATUS_NOT_APPLICABLE: "해당 없음",
    READINESS_STATUS_PENDING_EVIDENCE: "근거 대기",
    READINESS_STATUS_BLOCKED: "차단됨",
    READINESS_STATUS_READY_FOR_REVIEW: "리뷰 준비",
    READINESS_STATUS_READY_FOR_APPLY: "적용 준비",
    READINESS_STATUS_APPLIED: "적용 완료",
}

PROPOSAL_STAGE_LABELS_KO = {
    PROPOSAL_STAGE_OBSERVE: "관찰 중",
    PROPOSAL_STAGE_REPORT_READY: "보고서 준비",
    PROPOSAL_STAGE_REVIEW_PENDING: "리뷰 대기",
    PROPOSAL_STAGE_APPROVED_FOR_APPLY: "적용 승인됨",
    PROPOSAL_STAGE_APPLIED: "적용 완료",
    PROPOSAL_STAGE_REJECTED: "거부됨",
    PROPOSAL_STAGE_HELD: "보류됨",
    PROPOSAL_STAGE_SUPERSEDED: "대체됨",
    PROPOSAL_STAGE_EXPIRED: "만료됨",
}

APPROVAL_STATUS_LABELS_KO = {
    APPROVAL_STATUS_PENDING: "대기",
    APPROVAL_STATUS_APPROVED: "승인",
    APPROVAL_STATUS_HELD: "보류",
    APPROVAL_STATUS_REJECTED: "거부",
    APPROVAL_STATUS_EXPIRED: "만료",
    APPROVAL_STATUS_APPLIED: "적용 완료",
    APPROVAL_STATUS_CANCELLED: "취소",
}


def _text(value: object) -> str:
    return str(value or "").strip()


def normalize_readiness_status(value: object, default: str = READINESS_STATUS_PENDING_EVIDENCE) -> str:
    normalized = _text(value).upper()
    if not normalized:
        return default
    if normalized not in READINESS_STATUSES:
        raise ValueError(f"unsupported_readiness_status::{normalized}")
    return normalized


def normalize_proposal_stage(value: object, default: str = PROPOSAL_STAGE_OBSERVE) -> str:
    normalized = _text(value).upper()
    if not normalized:
        return default
    if normalized not in PROPOSAL_STAGES:
        raise ValueError(f"unsupported_proposal_stage::{normalized}")
    return normalized


def normalize_approval_status(value: object, default: str = APPROVAL_STATUS_PENDING) -> str:
    normalized = _text(value).lower()
    if not normalized:
        return default
    if normalized not in APPROVAL_STATUSES:
        raise ValueError(f"unsupported_approval_status::{normalized}")
    return normalized


def readiness_status_label_ko(value: object) -> str:
    normalized = normalize_readiness_status(value)
    return READINESS_STATUS_LABELS_KO.get(normalized, normalized)


def proposal_stage_label_ko(value: object) -> str:
    normalized = normalize_proposal_stage(value)
    return PROPOSAL_STAGE_LABELS_KO.get(normalized, normalized)


def approval_status_label_ko(value: object) -> str:
    normalized = normalize_approval_status(value)
    return APPROVAL_STATUS_LABELS_KO.get(normalized, normalized)


@dataclass(frozen=True, slots=True)
class StatusEntry:
    domain: str
    value: str
    label_ko: str
    meaning_ko: str
    terminal: bool


def build_improvement_status_baseline() -> dict[str, Any]:
    readiness = [
        asdict(
            StatusEntry(
                domain="readiness_status",
                value=value,
                label_ko=READINESS_STATUS_LABELS_KO[value],
                meaning_ko={
                    READINESS_STATUS_NOT_APPLICABLE: "이 축에는 아직 해당하지 않음",
                    READINESS_STATUS_PENDING_EVIDENCE: "근거가 더 쌓여야 함",
                    READINESS_STATUS_BLOCKED: "명시적 차단 사유가 있음",
                    READINESS_STATUS_READY_FOR_REVIEW: "사람이 검토할 준비가 됨",
                    READINESS_STATUS_READY_FOR_APPLY: "승인 후 바로 적용 가능",
                    READINESS_STATUS_APPLIED: "이미 반영 완료",
                }[value],
                terminal=value == READINESS_STATUS_APPLIED,
            )
        )
        for value in READINESS_STATUSES
    ]
    proposal = [
        asdict(
            StatusEntry(
                domain="proposal_stage",
                value=value,
                label_ko=PROPOSAL_STAGE_LABELS_KO[value],
                meaning_ko={
                    PROPOSAL_STAGE_OBSERVE: "관찰만 하는 단계",
                    PROPOSAL_STAGE_REPORT_READY: "보고서로 surface할 준비가 됨",
                    PROPOSAL_STAGE_REVIEW_PENDING: "사람 검토 대기",
                    PROPOSAL_STAGE_APPROVED_FOR_APPLY: "적용 승인까지 통과",
                    PROPOSAL_STAGE_APPLIED: "반영 완료",
                    PROPOSAL_STAGE_REJECTED: "거부됨",
                    PROPOSAL_STAGE_HELD: "보류됨",
                    PROPOSAL_STAGE_SUPERSEDED: "새 제안으로 대체됨",
                    PROPOSAL_STAGE_EXPIRED: "기한 초과로 만료됨",
                }[value],
                terminal=value in {
                    PROPOSAL_STAGE_APPLIED,
                    PROPOSAL_STAGE_REJECTED,
                    PROPOSAL_STAGE_SUPERSEDED,
                    PROPOSAL_STAGE_EXPIRED,
                },
            )
        )
        for value in PROPOSAL_STAGES
    ]
    approval = [
        asdict(
            StatusEntry(
                domain="approval_status",
                value=value,
                label_ko=APPROVAL_STATUS_LABELS_KO[value],
                meaning_ko={
                    APPROVAL_STATUS_PENDING: "버튼 입력 대기",
                    APPROVAL_STATUS_APPROVED: "승인되어 apply 대기 가능",
                    APPROVAL_STATUS_HELD: "보류됨",
                    APPROVAL_STATUS_REJECTED: "거부됨",
                    APPROVAL_STATUS_EXPIRED: "승인 기한 만료",
                    APPROVAL_STATUS_APPLIED: "적용 완료",
                    APPROVAL_STATUS_CANCELLED: "중복/대체로 취소",
                }[value],
                terminal=value in APPROVAL_TERMINAL_STATUSES,
            )
        )
        for value in APPROVAL_STATUSES
    ]
    return {
        "contract_version": IMPROVEMENT_STATUS_POLICY_CONTRACT_VERSION,
        "readiness_statuses": readiness,
        "proposal_stages": proposal,
        "approval_statuses": approval,
        "rules": {
            "readiness_status_is_not_approval_status": True,
            "proposal_stage_is_not_approval_status": True,
            "approval_actionable_statuses": list(APPROVAL_ACTIONABLE_STATUSES),
            "approval_terminal_statuses": list(APPROVAL_TERMINAL_STATUSES),
            "approval_conflict_tracking_statuses": list(APPROVAL_CONFLICT_TRACKING_STATUSES),
        },
    }


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_improvement_status_baseline_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "improvement_status_baseline_latest.json",
        directory / "improvement_status_baseline_latest.md",
    )


def render_improvement_status_baseline_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Improvement Status Baseline",
        "",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        "",
        "## Readiness Statuses",
    ]
    for row in payload.get("readiness_statuses", []):
        lines.append(
            f"- `{row['value']}` | {row['label_ko']} | {row['meaning_ko']} | terminal={row['terminal']}"
        )
    lines.extend(["", "## Proposal Stages"])
    for row in payload.get("proposal_stages", []):
        lines.append(
            f"- `{row['value']}` | {row['label_ko']} | {row['meaning_ko']} | terminal={row['terminal']}"
        )
    lines.extend(["", "## Approval Statuses"])
    for row in payload.get("approval_statuses", []):
        lines.append(
            f"- `{row['value']}` | {row['label_ko']} | {row['meaning_ko']} | terminal={row['terminal']}"
        )
    lines.extend(["", "## Rules"])
    rules = payload.get("rules", {})
    for key, value in rules.items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines)


def write_improvement_status_baseline_snapshot(
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_improvement_status_baseline()
    default_json_path, default_markdown_path = default_improvement_status_baseline_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        render_improvement_status_baseline_markdown(payload),
        encoding="utf-8",
    )
    return {
        "contract_version": payload["contract_version"],
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }
