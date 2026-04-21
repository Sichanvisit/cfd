from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.services.improvement_status_policy import (
    READINESS_STATUS_APPLIED,
    READINESS_STATUS_BLOCKED,
    READINESS_STATUS_NOT_APPLICABLE,
    READINESS_STATUS_PENDING_EVIDENCE,
    READINESS_STATUS_READY_FOR_APPLY,
    READINESS_STATUS_READY_FOR_REVIEW,
)


IMPROVEMENT_BOARD_FIELD_POLICY_CONTRACT_VERSION = "improvement_board_field_policy_v1"

BOARD_SECTION_NAMES = (
    "summary",
    "readiness_state",
    "system_state",
    "watch_state",
    "runtime_state",
    "pa_state",
    "approval_state",
    "health_state",
    "orchestrator_contract",
    "artifacts",
)

BOARD_SUMMARY_FIELDS = (
    "contract_version",
    "field_policy_version",
    "generated_at",
    "trigger_state",
    "recommended_next_action",
    "phase",
    "blocking_reason",
    "next_required_action",
    "active_pa8_symbol_count",
    "live_window_ready_count",
    "runtime_open_positions_count",
    "runtime_flat_since",
    "pending_approval_count",
    "held_approval_count",
    "approved_apply_backlog_count",
    "oldest_pending_approval_age_sec",
    "last_successful_apply_ts",
    "degraded_components",
    "reconcile_backlog_count",
    "same_scope_conflict_count",
    "pa8_closeout_readiness_status",
    "pa8_closeout_focus_status",
    "pa8_focus_symbol_count",
    "pa8_primary_focus_symbol",
    "first_symbol_closeout_handoff_status",
    "first_symbol_closeout_handoff_symbol",
    "pa8_closeout_review_state",
    "pa8_closeout_apply_state",
    "pa9_handoff_readiness_status",
    "pa7_narrow_review_status",
    "pa7_narrow_review_group_count",
    "reverse_readiness_status",
    "historical_cost_confidence_level",
)

BOARD_READINESS_FIELDS = (
    "pa8_closeout_readiness_status",
    "pa8_closeout_blocking_reason",
    "pa8_closeout_next_required_action",
    "pa8_closeout_focus_status",
    "pa8_closeout_focus_reason",
    "pa8_closeout_focus_next_required_action",
    "pa8_primary_focus_symbol",
    "pa8_focus_symbol_count",
    "pa8_focus_watchlist_symbol_count",
    "first_symbol_closeout_handoff_status",
    "first_symbol_closeout_handoff_symbol",
    "first_symbol_closeout_handoff_stage",
    "first_symbol_closeout_handoff_reason",
    "first_symbol_closeout_handoff_next_required_action",
    "pa8_closeout_review_state",
    "pa8_closeout_apply_state",
    "pa9_handoff_readiness_status",
    "pa9_handoff_blocking_reason",
    "pa9_handoff_next_required_action",
    "pa7_narrow_review_status",
    "pa7_narrow_review_group_count",
    "pa7_narrow_review_primary_group_key",
    "pa7_narrow_review_next_required_action",
    "reverse_readiness_status",
    "reverse_blocking_reason",
    "reverse_next_required_action",
    "historical_cost_confidence_level",
    "historical_cost_blocking_reason",
    "historical_cost_note",
)

BOARD_BLOCKING_REASONS = (
    "none",
    "system_phase_emergency",
    "system_phase_degraded",
    "dependency_degraded",
    "approved_apply_backlog",
    "approval_backlog_pending",
    "pa7_review_backlog",
    "pa8_live_window_pending",
    "pa8_closeout_blocked",
    "pa9_handoff_review_ready",
    "pa8_closeout_apply_pending_before_pa9",
    "historical_cost_limited",
    "reverse_wait_for_flat",
    "reverse_score_not_strong_enough",
)

CONFIDENCE_LEVEL_HIGH = "HIGH"
CONFIDENCE_LEVEL_MEDIUM = "MEDIUM"
CONFIDENCE_LEVEL_LOW = "LOW"
CONFIDENCE_LEVEL_LIMITED = "LIMITED"

CONFIDENCE_LEVELS = (
    CONFIDENCE_LEVEL_HIGH,
    CONFIDENCE_LEVEL_MEDIUM,
    CONFIDENCE_LEVEL_LOW,
    CONFIDENCE_LEVEL_LIMITED,
)


def _text(value: object) -> str:
    return str(value or "").strip()


def normalize_board_blocking_reason(value: object, default: str = "none") -> str:
    normalized = _text(value).lower()
    if not normalized:
        return default
    return normalized


def normalize_confidence_level(
    value: object,
    default: str = CONFIDENCE_LEVEL_LIMITED,
) -> str:
    normalized = _text(value).upper()
    if not normalized:
        return default
    if normalized not in CONFIDENCE_LEVELS:
        raise ValueError(f"unsupported_confidence_level::{normalized}")
    return normalized


def derive_pa8_closeout_readiness_status(
    *,
    phase: str,
    active_symbol_count: int,
    live_window_ready_count: int,
) -> str:
    phase_upper = _text(phase).upper()
    if active_symbol_count <= 0:
        return READINESS_STATUS_NOT_APPLICABLE
    if phase_upper in {"DEGRADED", "EMERGENCY"}:
        return READINESS_STATUS_BLOCKED
    if live_window_ready_count >= active_symbol_count:
        return READINESS_STATUS_READY_FOR_REVIEW
    return READINESS_STATUS_PENDING_EVIDENCE


def derive_pa9_handoff_readiness_status(
    *,
    pa9_handoff_state: str,
    pa9_review_state: str,
    pa9_apply_state: str,
) -> str:
    combined = " ".join(
        [
            _text(pa9_handoff_state).upper(),
            _text(pa9_review_state).upper(),
            _text(pa9_apply_state).upper(),
        ]
    )
    if (
        _text(pa9_handoff_state).upper() == "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED"
        and _text(pa9_review_state).upper() == "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED"
        and _text(pa9_apply_state).upper() == "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED"
    ):
        return READINESS_STATUS_APPLIED
    if "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_APPLY_REVIEW" in combined:
        return READINESS_STATUS_READY_FOR_APPLY
    if (
        "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW" in combined
        or "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW" in combined
    ):
        return READINESS_STATUS_READY_FOR_REVIEW
    if "HOLD_PENDING_PA8_LIVE_WINDOW" in combined:
        return READINESS_STATUS_PENDING_EVIDENCE
    return READINESS_STATUS_NOT_APPLICABLE


def derive_reverse_readiness_status(
    *,
    phase: str,
    degraded_components: list[str] | None,
    runtime_open_positions_count: int,
) -> str:
    phase_upper = _text(phase).upper()
    if phase_upper in {"DEGRADED", "EMERGENCY"}:
        return READINESS_STATUS_BLOCKED
    if runtime_open_positions_count > 0:
        return READINESS_STATUS_PENDING_EVIDENCE
    return READINESS_STATUS_NOT_APPLICABLE


@dataclass(frozen=True, slots=True)
class FieldEntry:
    section: str
    field_name: str
    meaning_ko: str


def build_improvement_board_field_baseline() -> dict[str, Any]:
    highlight_fields = [
        asdict(
            FieldEntry(
                section="summary",
                field_name="blocking_reason",
                meaning_ko="현재 전체 진행을 막고 있는 대표 차단 사유",
            )
        ),
        asdict(
            FieldEntry(
                section="summary",
                field_name="next_required_action",
                meaning_ko="다음 단계로 가기 위해 가장 먼저 필요한 핵심 행동",
            )
        ),
        asdict(
            FieldEntry(
                section="readiness_state",
                field_name="pa8_closeout_readiness_status",
                meaning_ko="PA8 closeout이 지금 어떤 readiness 단계인지",
            )
        ),
        asdict(
            FieldEntry(
                section="readiness_state",
                field_name="pa9_handoff_readiness_status",
                meaning_ko="PA9 handoff가 지금 어떤 readiness 단계인지",
            )
        ),
        asdict(
            FieldEntry(
                section="readiness_state",
                field_name="pa8_closeout_focus_status",
                meaning_ko="PA8 closeout 관찰축에서 지금 어떤 심볼을 집중 관찰해야 하는지 보여주는 focus 상태",
            )
        ),
        asdict(
            FieldEntry(
                section="readiness_state",
                field_name="pa8_primary_focus_symbol",
                meaning_ko="지금 가장 먼저 closeout readiness를 집중 관찰해야 하는 대표 심볼",
            )
        ),
        asdict(
            FieldEntry(
                section="readiness_state",
                field_name="reverse_readiness_status",
                meaning_ko="reverse가 지금 blocked인지 pending인지 ready인지",
            )
        ),
        asdict(
            FieldEntry(
                section="readiness_state",
                field_name="historical_cost_confidence_level",
                meaning_ko="historical cost 집계 신뢰도 수준",
            )
        ),
    ]
    return {
        "contract_version": IMPROVEMENT_BOARD_FIELD_POLICY_CONTRACT_VERSION,
        "section_names": list(BOARD_SECTION_NAMES),
        "summary_fields": list(BOARD_SUMMARY_FIELDS),
        "readiness_fields": list(BOARD_READINESS_FIELDS),
        "blocking_reasons": list(BOARD_BLOCKING_REASONS),
        "confidence_levels": list(CONFIDENCE_LEVELS),
        "highlight_fields": highlight_fields,
    }


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_improvement_board_field_baseline_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "improvement_board_field_baseline_latest.json",
        directory / "improvement_board_field_baseline_latest.md",
    )


def render_improvement_board_field_baseline_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Improvement Board Field Baseline",
        "",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        "",
        "## Sections",
    ]
    for name in payload.get("section_names", []):
        lines.append(f"- `{name}`")
    lines.extend(["", "## Summary Fields"])
    for field_name in payload.get("summary_fields", []):
        lines.append(f"- `{field_name}`")
    lines.extend(["", "## Readiness Fields"])
    for field_name in payload.get("readiness_fields", []):
        lines.append(f"- `{field_name}`")
    lines.extend(["", "## Blocking Reasons"])
    for value in payload.get("blocking_reasons", []):
        lines.append(f"- `{value}`")
    lines.extend(["", "## Confidence Levels"])
    for value in payload.get("confidence_levels", []):
        lines.append(f"- `{value}`")
    lines.extend(["", "## Highlight Fields"])
    for row in payload.get("highlight_fields", []):
        lines.append(f"- `{row['section']}.{row['field_name']}` | {row['meaning_ko']}")
    return "\n".join(lines)


def write_improvement_board_field_baseline_snapshot(
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_improvement_board_field_baseline()
    default_json_path, default_markdown_path = default_improvement_board_field_baseline_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        render_improvement_board_field_baseline_markdown(payload),
        encoding="utf-8",
    )
    return {
        "contract_version": payload["contract_version"],
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }
