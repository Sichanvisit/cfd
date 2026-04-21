from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.integrations import notifier
from backend.services.telegram_route_ownership_policy import (
    OWNER_IMPROVEMENT_CHECK_INBOX,
    OWNER_IMPROVEMENT_REPORT_TOPIC,
    validate_telegram_route_ownership,
)


CHECKPOINT_IMPROVEMENT_P5_OBSERVATION_CONTRACT_VERSION = (
    "checkpoint_improvement_p5_observation_runtime_v0"
)

FIRST_SYMBOL_STATUS_RANK = {
    "NOT_APPLICABLE": 0,
    "WATCHLIST": 1,
    "CONCENTRATED": 2,
    "READY_FOR_CLOSEOUT_REVIEW": 3,
    "READY_FOR_HANDOFF_REVIEW": 4,
    "READY_FOR_HANDOFF_APPLY": 5,
    "APPLIED": 6,
    "BLOCKED": -1,
}
FIRST_SYMBOL_ALERTABLE_STATUSES = {
    "CONCENTRATED",
    "READY_FOR_CLOSEOUT_REVIEW",
    "READY_FOR_HANDOFF_REVIEW",
    "READY_FOR_HANDOFF_APPLY",
    "APPLIED",
}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_checkpoint_improvement_p5_observation_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "checkpoint_improvement_p5_observation_latest.json",
        directory / "checkpoint_improvement_p5_observation_latest.md",
    )


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        parsed = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _status_rank(status: object) -> int:
    return FIRST_SYMBOL_STATUS_RANK.get(_text(status).upper(), 0)


def _first_symbol_event(
    *,
    previous_payload: Mapping[str, Any],
    board_payload: Mapping[str, Any],
) -> dict[str, Any]:
    previous_summary = _mapping(previous_payload.get("summary"))
    summary = _mapping(board_payload.get("summary"))
    readiness_state = _mapping(board_payload.get("readiness_state"))
    first_symbol_surface = _mapping(readiness_state.get("first_symbol_closeout_handoff_surface"))

    previous_status = _text(previous_summary.get("first_symbol_status")).upper()
    previous_symbol = _text(previous_summary.get("first_symbol_symbol")).upper()
    current_status = _text(first_symbol_surface.get("observation_status")).upper()
    current_symbol = _text(first_symbol_surface.get("primary_symbol")).upper()
    current_stage = _text(first_symbol_surface.get("observation_stage")).upper()

    should_surface = False
    trigger_reason = ""
    if current_status in FIRST_SYMBOL_ALERTABLE_STATUSES:
        if _status_rank(current_status) > _status_rank(previous_status):
            should_surface = True
            trigger_reason = "status_escalated"
        elif current_symbol and current_symbol != previous_symbol:
            should_surface = True
            trigger_reason = "primary_symbol_changed"
        elif current_status != previous_status:
            should_surface = True
            trigger_reason = "status_changed"

    progress_ratio = _to_float(first_symbol_surface.get("focus_progress_ratio"))
    return {
        "should_surface": should_surface,
        "trigger_reason": trigger_reason,
        "previous_status": previous_status or "NOT_APPLICABLE",
        "previous_symbol": previous_symbol,
        "current_status": current_status or "NOT_APPLICABLE",
        "current_symbol": current_symbol,
        "current_stage": current_stage,
        "reason_ko": _text(first_symbol_surface.get("reason_ko")),
        "recommended_next_action": _text(first_symbol_surface.get("recommended_next_action")),
        "observed_window_row_count": _to_int(first_symbol_surface.get("observed_window_row_count")),
        "sample_floor": _to_int(first_symbol_surface.get("sample_floor")),
        "active_trigger_count": _to_int(first_symbol_surface.get("active_trigger_count")),
        "focus_progress_ratio": progress_ratio,
        "focus_progress_pct": round(progress_ratio * 100.0, 1),
        "handoff_review_candidate": bool(first_symbol_surface.get("handoff_review_candidate")),
        "handoff_apply_candidate": bool(first_symbol_surface.get("handoff_apply_candidate")),
        "blocking_reason": _text(summary.get("blocking_reason")),
        "next_required_action": _text(summary.get("next_required_action")),
    }


def _pa7_narrow_review_event(
    *,
    previous_payload: Mapping[str, Any],
    board_payload: Mapping[str, Any],
) -> dict[str, Any]:
    previous_summary = _mapping(previous_payload.get("summary"))
    readiness_state = _mapping(board_payload.get("readiness_state"))
    narrow_review = _mapping(readiness_state.get("pa7_narrow_review_surface"))

    previous_status = _text(previous_summary.get("pa7_narrow_review_status")).upper()
    current_status = _text(narrow_review.get("status")).upper()
    group_count = _to_int(narrow_review.get("group_count"))
    should_surface = current_status == "REVIEW_NEEDED" and previous_status != "REVIEW_NEEDED"
    cleared = previous_status == "REVIEW_NEEDED" and current_status == "CLEAR"
    if cleared:
        should_surface = True

    return {
        "should_surface": should_surface,
        "cleared": cleared,
        "previous_status": previous_status or "NOT_APPLICABLE",
        "current_status": current_status or "NOT_APPLICABLE",
        "group_count": group_count,
        "mixed_wait_boundary_group_count": _to_int(narrow_review.get("mixed_wait_boundary_group_count")),
        "mixed_review_group_count": _to_int(narrow_review.get("mixed_review_group_count")),
        "primary_group_key": _text(narrow_review.get("primary_group_key")),
        "primary_symbol": _text(narrow_review.get("primary_symbol")).upper(),
        "primary_review_disposition": _text(narrow_review.get("primary_review_disposition")),
        "reason_ko": _text(narrow_review.get("reason_ko")),
        "recommended_next_action": _text(narrow_review.get("recommended_next_action")),
    }


def _render_check_text(
    *,
    first_symbol_event: Mapping[str, Any],
    pa7_event: Mapping[str, Any],
) -> str:
    lines = ["[P5-5 관찰] first symbol closeout/handoff"]
    if bool(first_symbol_event.get("should_surface")):
        lines.extend(
            [
                f"- 대상: {_text(first_symbol_event.get('current_symbol'), '-')}",
                f"- 상태: {_text(first_symbol_event.get('previous_status'), '-')} -> {_text(first_symbol_event.get('current_status'), '-')}",
                f"- 진행: {_to_int(first_symbol_event.get('observed_window_row_count'))}/{_to_int(first_symbol_event.get('sample_floor'))} rows",
                f"- 트리거: {_to_int(first_symbol_event.get('active_trigger_count'))}개",
            ]
        )
    if bool(pa7_event.get("should_surface")):
        status_line = (
            "REVIEW_NEEDED -> CLEAR"
            if bool(pa7_event.get("cleared"))
            else f"{_text(pa7_event.get('previous_status'), '-')} -> {_text(pa7_event.get('current_status'), '-')}"
        )
        lines.extend(
            [
                f"- PA7 narrow review: {status_line}",
                f"- 남은 그룹: {_to_int(pa7_event.get('group_count'))}개",
            ]
        )
    next_action = _text(
        first_symbol_event.get("recommended_next_action")
        or pa7_event.get("recommended_next_action")
        or "inspect_report_topic_for_p5_5_details"
    )
    lines.extend(
        [
            f"- 다음: {next_action}",
            "- 원문 보고서는 보고서 topic에서 확인",
        ]
    )
    return "\n".join(lines)


def _render_report_text(
    *,
    board_payload: Mapping[str, Any],
    first_symbol_event: Mapping[str, Any],
    pa7_event: Mapping[str, Any],
) -> str:
    summary = _mapping(board_payload.get("summary"))
    readiness_state = _mapping(board_payload.get("readiness_state"))
    first_symbol_surface = _mapping(readiness_state.get("first_symbol_closeout_handoff_surface"))
    narrow_review = _mapping(readiness_state.get("pa7_narrow_review_surface"))

    lines = [
        "[P5-5 보고서] first symbol closeout/handoff 관찰",
        f"시각: {_text(summary.get('generated_at'), '-')}",
        "",
        "1. First Symbol",
        f"- 대상: {_text(first_symbol_surface.get('primary_symbol'), '-')}",
        f"- 상태 전이: {_text(first_symbol_event.get('previous_status'), '-')} -> {_text(first_symbol_event.get('current_status'), '-')}",
        f"- stage: {_text(first_symbol_surface.get('observation_stage'), '-')}",
        f"- 관찰 진행: {_to_int(first_symbol_surface.get('observed_window_row_count'))}/{_to_int(first_symbol_surface.get('sample_floor'))} rows ({_to_float(first_symbol_event.get('focus_progress_pct')):.1f}%)",
        f"- 활성 트리거: {_to_int(first_symbol_surface.get('active_trigger_count'))}개",
        f"- handoff review candidate: {bool(first_symbol_surface.get('handoff_review_candidate'))}",
        f"- handoff apply candidate: {bool(first_symbol_surface.get('handoff_apply_candidate'))}",
        f"- 이유: {_text(first_symbol_surface.get('reason_ko'), '-')}",
        f"- 다음 액션: {_text(first_symbol_surface.get('recommended_next_action'), '-')}",
        "",
        "2. PA7 Narrow Review Lane",
        f"- 상태 전이: {_text(pa7_event.get('previous_status'), '-')} -> {_text(pa7_event.get('current_status'), '-')}",
        f"- 남은 그룹: {_to_int(narrow_review.get('group_count'))}개",
        f"- mixed_wait_boundary: {_to_int(narrow_review.get('mixed_wait_boundary_group_count'))}개",
        f"- mixed_review: {_to_int(narrow_review.get('mixed_review_group_count'))}개",
        f"- primary symbol: {_text(narrow_review.get('primary_symbol'), '-')}",
        f"- primary disposition: {_text(narrow_review.get('primary_review_disposition'), '-')}",
        f"- 이유: {_text(narrow_review.get('reason_ko'), '-')}",
        f"- 다음 액션: {_text(narrow_review.get('recommended_next_action'), '-')}",
        "",
        "3. Board Summary",
        f"- blocking_reason: {_text(summary.get('blocking_reason'), '-')}",
        f"- next_required_action: {_text(summary.get('next_required_action'), '-')}",
        f"- pa8_closeout_review_state: {_text(summary.get('pa8_closeout_review_state'), '-')}",
        f"- pa8_closeout_apply_state: {_text(summary.get('pa8_closeout_apply_state'), '-')}",
        f"- pa9_handoff_readiness_status: {_text(summary.get('pa9_handoff_readiness_status'), '-')}",
    ]
    return "\n".join(lines)


def _render_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    first_symbol_event = _mapping(payload.get("first_symbol_event"))
    pa7_event = _mapping(payload.get("pa7_narrow_review_event"))
    delivery = _mapping(payload.get("delivery"))

    lines = [
        "# Checkpoint Improvement P5 Observation Runtime",
        "",
        "## Summary",
        "",
    ]
    for key in (
        "trigger_state",
        "recommended_next_action",
        "first_symbol_status",
        "first_symbol_symbol",
        "pa7_narrow_review_status",
        "check_sent",
        "report_sent",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.extend(
        [
            "",
            "## First Symbol Event",
            "",
        ]
    )
    for key in (
        "previous_status",
        "current_status",
        "current_symbol",
        "current_stage",
        "observed_window_row_count",
        "sample_floor",
        "active_trigger_count",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{first_symbol_event.get(key)}`")
    lines.extend(
        [
            "",
            "## PA7 Narrow Review Event",
            "",
        ]
    )
    for key in (
        "previous_status",
        "current_status",
        "group_count",
        "primary_symbol",
        "primary_review_disposition",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{pa7_event.get(key)}`")
    lines.extend(
        [
            "",
            "## Delivery",
            "",
            f"- check: `{_text(_mapping(delivery.get('check')).get('telegram_message_id'))}`",
            f"- report: `{_text(_mapping(delivery.get('report')).get('telegram_message_id'))}`",
            "",
        ]
    )
    return "\n".join(lines)


def build_checkpoint_improvement_p5_observation_runtime(
    *,
    master_board_payload: Mapping[str, Any] | None,
    now_ts: object | None = None,
    snapshot_json_path: str | Path | None = None,
    snapshot_markdown_path: str | Path | None = None,
    notify: bool = True,
    send_sync: Callable[..., dict[str, Any] | None] = notifier.send_telegram_sync,
) -> dict[str, Any]:
    json_path, markdown_path = default_checkpoint_improvement_p5_observation_paths()
    resolved_json_path = Path(snapshot_json_path or json_path)
    resolved_markdown_path = Path(snapshot_markdown_path or markdown_path)
    previous_payload = _load_json(resolved_json_path)
    board_payload = _mapping(master_board_payload)
    run_at = _text(now_ts, _now_iso())

    if not board_payload:
        payload = {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_P5_OBSERVATION_CONTRACT_VERSION,
                "generated_at": run_at,
                "trigger_state": "MASTER_BOARD_MISSING",
                "recommended_next_action": "wait_for_master_board_after_orchestrator_tick",
                "first_symbol_status": _text(_mapping(previous_payload.get("summary")).get("first_symbol_status")),
                "first_symbol_symbol": _text(_mapping(previous_payload.get("summary")).get("first_symbol_symbol")),
                "pa7_narrow_review_status": _text(_mapping(previous_payload.get("summary")).get("pa7_narrow_review_status")),
                "check_sent": False,
                "report_sent": False,
            },
            "first_symbol_event": {},
            "pa7_narrow_review_event": {},
            "delivery": {},
        }
        _write_json(resolved_json_path, payload)
        _write_text(resolved_markdown_path, _render_markdown(payload))
        return payload

    first_symbol_event = _first_symbol_event(
        previous_payload=previous_payload,
        board_payload=board_payload,
    )
    pa7_event = _pa7_narrow_review_event(
        previous_payload=previous_payload,
        board_payload=board_payload,
    )

    should_surface = bool(first_symbol_event.get("should_surface")) or bool(pa7_event.get("should_surface"))
    trigger_state = "NO_P5_5_EVENT"
    if bool(first_symbol_event.get("should_surface")) and bool(pa7_event.get("should_surface")):
        trigger_state = "FIRST_SYMBOL_AND_PA7_NARROW_REVIEW_SURFACED"
    elif bool(first_symbol_event.get("should_surface")):
        trigger_state = "FIRST_SYMBOL_SURFACED"
    elif bool(pa7_event.get("should_surface")):
        trigger_state = "PA7_NARROW_REVIEW_SURFACED"

    check_delivery: dict[str, Any] = {}
    report_delivery: dict[str, Any] = {}
    if notify and should_surface:
        validate_telegram_route_ownership(owner_key=OWNER_IMPROVEMENT_CHECK_INBOX, route="check")
        validate_telegram_route_ownership(owner_key=OWNER_IMPROVEMENT_REPORT_TOPIC, route="report")
        check_text = _render_check_text(
            first_symbol_event=first_symbol_event,
            pa7_event=pa7_event,
        )
        report_text = _render_report_text(
            board_payload=board_payload,
            first_symbol_event=first_symbol_event,
            pa7_event=pa7_event,
        )
        check_response = send_sync(check_text, route="check", parse_mode=None)
        report_response = send_sync(report_text, route="report", parse_mode=None)
        if isinstance(check_response, Mapping):
            check_delivery = dict(check_response)
        if isinstance(report_response, Mapping):
            report_delivery = dict(report_response)

    summary = _mapping(board_payload.get("summary"))
    payload = {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_P5_OBSERVATION_CONTRACT_VERSION,
            "generated_at": run_at,
            "trigger_state": trigger_state,
            "recommended_next_action": _text(
                first_symbol_event.get("recommended_next_action")
                or pa7_event.get("recommended_next_action")
                or summary.get("next_required_action")
                or "continue_observing_first_symbol_closeout_handoff"
            ),
            "first_symbol_status": _text(first_symbol_event.get("current_status")),
            "first_symbol_symbol": _text(first_symbol_event.get("current_symbol")),
            "pa7_narrow_review_status": _text(pa7_event.get("current_status")),
            "check_sent": bool(check_delivery),
            "report_sent": bool(report_delivery),
        },
        "first_symbol_event": first_symbol_event,
        "pa7_narrow_review_event": pa7_event,
        "delivery": {
            "check": check_delivery,
            "report": report_delivery,
        },
    }
    _write_json(resolved_json_path, payload)
    _write_text(resolved_markdown_path, _render_markdown(payload))
    return payload
