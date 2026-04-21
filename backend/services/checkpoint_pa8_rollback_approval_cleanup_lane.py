from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.checkpoint_improvement_master_board import (
    default_checkpoint_improvement_master_board_json_path,
)
from backend.services.checkpoint_improvement_pa8_closeout_runtime import (
    default_checkpoint_improvement_pa8_closeout_runtime_json_path,
)
from backend.services.improvement_status_policy import APPROVAL_ACTIONABLE_STATUSES
from backend.services.telegram_state_store import TelegramStateStore


CHECKPOINT_PA8_ROLLBACK_APPROVAL_CLEANUP_LANE_CONTRACT_VERSION = (
    "checkpoint_pa8_rollback_approval_cleanup_lane_v1"
)
_ACTIONABLE_STATUSES = set(APPROVAL_ACTIONABLE_STATUSES)


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_checkpoint_pa8_rollback_approval_cleanup_lane_json_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_rollback_approval_cleanup_lane_latest.json"


def default_checkpoint_pa8_rollback_approval_cleanup_lane_markdown_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_rollback_approval_cleanup_lane_latest.md"


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _parse_iso(value: object) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _age_seconds(now_dt: datetime, created_at: object) -> int | None:
    created_dt = _parse_iso(created_at)
    if created_dt is None:
        return None
    age = (now_dt - created_dt).total_seconds()
    return max(0, int(age))


def _deadline_state(*, now_dt: datetime, decision_deadline_ts: object) -> str:
    deadline_dt = _parse_iso(decision_deadline_ts)
    if deadline_dt is None:
        return "NO_DEADLINE"
    if deadline_dt < now_dt:
        return "OVERDUE"
    return "ON_TIME"


def _is_pa8_relevant_group(group: Mapping[str, Any], active_symbols: set[str]) -> bool:
    review_type = _text(group.get("review_type")).upper()
    symbol = _text(group.get("symbol")).upper()
    if review_type.startswith("CANARY_"):
        return True
    return bool(symbol and symbol in active_symbols)


def _group_relevance_code(group: Mapping[str, Any]) -> str:
    review_type = _text(group.get("review_type")).upper()
    if review_type == "CANARY_ROLLBACK_REVIEW":
        return "ROLLBACK_REVIEW_PENDING"
    if review_type == "CANARY_CLOSEOUT_REVIEW":
        return "CLOSEOUT_REVIEW_PENDING"
    if review_type == "CANARY_ACTIVATION_REVIEW":
        return "CANARY_ACTIVATION_PENDING"
    return "OTHER_ACTIONABLE_REVIEW"


def _group_relevance_reason_ko(relevance_code: str) -> str:
    if relevance_code == "ROLLBACK_REVIEW_PENDING":
        return "rollback required symbol에 대한 Telegram review가 아직 남아 있습니다."
    if relevance_code == "CLOSEOUT_REVIEW_PENDING":
        return "closeout review가 Telegram approval backlog에 남아 있습니다."
    if relevance_code == "CANARY_ACTIVATION_PENDING":
        return "canary activation review가 아직 정리되지 않았습니다."
    return "PA8 관련 actionable review가 아직 backlog에 남아 있습니다."


def _row_cleanup_state(
    *,
    rollback_required: bool,
    related_groups: list[Mapping[str, Any]],
    review_candidate: bool,
    apply_candidate: bool,
    closeout_state: str,
) -> str:
    if any(_group_relevance_code(group) == "ROLLBACK_REVIEW_PENDING" for group in related_groups):
        return "ROLLBACK_APPROVAL_PENDING"
    if rollback_required:
        return "ROLLBACK_REVIEW_MISSING_PROMPT"
    if any(_group_relevance_code(group) == "CLOSEOUT_REVIEW_PENDING" for group in related_groups):
        return "CLOSEOUT_REVIEW_PENDING"
    if related_groups:
        return "OTHER_ACTIONABLE_REVIEW_PENDING"
    if review_candidate:
        return "READY_FOR_CLOSEOUT_REVIEW"
    if apply_candidate:
        return "READY_FOR_CLOSEOUT_APPLY"
    if closeout_state == "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW":
        return "WAITING_LIVE_WINDOW"
    return "NO_CLEANUP_REQUIRED"


def _row_cleanup_reason_ko(cleanup_state: str) -> str:
    if cleanup_state == "ROLLBACK_APPROVAL_PENDING":
        return "rollback review가 pending/held 상태라 closeout review보다 먼저 Telegram에서 정리해야 합니다."
    if cleanup_state == "ROLLBACK_REVIEW_MISSING_PROMPT":
        return "rollback required는 감지됐지만 대응 review prompt가 backlog에 보이지 않습니다."
    if cleanup_state == "CLOSEOUT_REVIEW_PENDING":
        return "closeout review 자체가 backlog에 남아 있어 Telegram approval cleanup이 먼저입니다."
    if cleanup_state == "OTHER_ACTIONABLE_REVIEW_PENDING":
        return "같은 심볼의 다른 actionable review backlog가 먼저 비워져야 합니다."
    if cleanup_state == "READY_FOR_CLOSEOUT_REVIEW":
        return "rollback/approval cleanup은 비어 있고 closeout review packet만 남아 있습니다."
    if cleanup_state == "READY_FOR_CLOSEOUT_APPLY":
        return "closeout apply 직전 상태로 approval/apply cleanup 확인만 남아 있습니다."
    if cleanup_state == "WAITING_LIVE_WINDOW":
        return "approval cleanup보다 live window 증거 누적이 먼저 필요한 상태입니다."
    return "현재 rollback/approval cleanup blocker는 보이지 않습니다."


def _priority_score(
    *,
    symbol: str,
    primary_focus_symbol: str,
    cleanup_state: str,
    related_group_count: int,
    approval_age_sec: int | None,
) -> float:
    score = 0.0
    if symbol == primary_focus_symbol:
        score += 40.0
    if cleanup_state == "ROLLBACK_APPROVAL_PENDING":
        score += 70.0
    elif cleanup_state == "ROLLBACK_REVIEW_MISSING_PROMPT":
        score += 60.0
    elif cleanup_state == "CLOSEOUT_REVIEW_PENDING":
        score += 55.0
    elif cleanup_state == "OTHER_ACTIONABLE_REVIEW_PENDING":
        score += 35.0
    elif cleanup_state == "READY_FOR_CLOSEOUT_REVIEW":
        score += 25.0
    score += min(20.0, float(related_group_count) * 5.0)
    if approval_age_sec is not None:
        score += min(15.0, float(approval_age_sec) / 3600.0)
    return round(score, 1)


def _summary_cleanup_state(
    *,
    rollback_approval_pending_count: int,
    relevant_actionable_group_count: int,
    approval_backlog_count: int,
    apply_backlog_count: int,
    rollback_required_symbol_count: int,
    closeout_review_candidate_count: int,
) -> tuple[str, str]:
    if rollback_approval_pending_count > 0:
        return (
            "ROLLBACK_APPROVAL_PENDING",
            "review_pending_pa8_canary_rollback_prompt_in_telegram",
        )
    if relevant_actionable_group_count > 0:
        return (
            "PA8_APPROVAL_BACKLOG_PENDING",
            "process_relevant_pa8_actionable_reviews_in_telegram",
        )
    if apply_backlog_count > 0:
        return (
            "APPROVED_APPLY_BACKLOG_PENDING",
            "drain_approved_apply_backlog_before_new_pa8_closeout_reviews",
        )
    if approval_backlog_count > 0:
        return (
            "NON_PA8_APPROVAL_BACKLOG_PENDING",
            "clear_non_pa8_governance_backlog_before_pa8_closeout_review",
        )
    if rollback_required_symbol_count > 0:
        return (
            "ROLLBACK_REVIEW_MISSING_PROMPT",
            "ensure_pa8_rollback_review_prompt_exists_for_required_symbol",
        )
    if closeout_review_candidate_count > 0:
        return (
            "READY_FOR_CLOSEOUT_REVIEW",
            "prepare_pa8_closeout_review_after_cleanup",
        )
    return (
        "NO_CLEANUP_BLOCKER",
        "continue_pa8_live_window_fill_observation",
    )


def build_checkpoint_pa8_rollback_approval_cleanup_lane(
    *,
    master_board_payload: Mapping[str, Any] | None = None,
    board_json_path: str | Path | None = None,
    pa8_closeout_runtime_payload: Mapping[str, Any] | None = None,
    pa8_closeout_runtime_json_path: str | Path | None = None,
    actionable_groups: list[Mapping[str, Any]] | None = None,
    telegram_state_store: TelegramStateStore | None = None,
    previous_payload: Mapping[str, Any] | None = None,
    previous_json_path: str | Path | None = None,
    now_ts: object | None = None,
) -> dict[str, Any]:
    board = (
        _mapping(master_board_payload)
        if master_board_payload is not None
        else _load_json(board_json_path or default_checkpoint_improvement_master_board_json_path())
    )
    pa8_runtime = (
        _mapping(pa8_closeout_runtime_payload)
        if pa8_closeout_runtime_payload is not None
        else _mapping(_mapping(board.get("readiness_state")).get("pa8_closeout_runtime"))
        or _load_json(
            pa8_closeout_runtime_json_path
            or default_checkpoint_improvement_pa8_closeout_runtime_json_path()
        )
    )
    approval_state = _mapping(board.get("approval_state"))
    summary = _mapping(board.get("summary"))
    readiness_state = _mapping(board.get("readiness_state"))
    active_symbols = {
        _text(_mapping(row).get("symbol")).upper()
        for row in list(_mapping(readiness_state.get("pa8_closeout_surface")).get("symbols", []) or [])
        if _text(_mapping(row).get("symbol"))
    }
    if actionable_groups is None:
        store = telegram_state_store or TelegramStateStore()
        actionable_groups = []
        for status in _ACTIONABLE_STATUSES:
            actionable_groups.extend(store.list_check_groups(status=status, limit=100))
    previous = (
        _mapping(previous_payload)
        if previous_payload is not None
        else _load_json(previous_json_path or default_checkpoint_pa8_rollback_approval_cleanup_lane_json_path())
    )
    previous_summary = _mapping(previous.get("summary"))
    now_dt = _parse_iso(now_ts) or datetime.now().astimezone()

    relevant_groups: list[dict[str, Any]] = []
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for raw_group in actionable_groups or []:
        group = _mapping(raw_group)
        if _text(group.get("status")).lower() not in _ACTIONABLE_STATUSES:
            continue
        if not _is_pa8_relevant_group(group, active_symbols):
            continue
        symbol = _text(group.get("symbol")).upper()
        age_sec = _age_seconds(now_dt, group.get("first_event_ts") or group.get("updated_at"))
        relevance_code = _group_relevance_code(group)
        group_row = {
            "group_id": _to_int(group.get("group_id")),
            "status": _text(group.get("status")).lower(),
            "review_type": _text(group.get("review_type")).upper(),
            "symbol": symbol,
            "scope_key": _text(group.get("scope_key")),
            "reason_summary": _text(group.get("reason_summary")),
            "decision_deadline_ts": _text(group.get("decision_deadline_ts")),
            "approval_age_sec": age_sec,
            "deadline_state": _deadline_state(
                now_dt=now_dt,
                decision_deadline_ts=group.get("decision_deadline_ts"),
            ),
            "relevance_code": relevance_code,
            "relevance_reason_ko": _group_relevance_reason_ko(relevance_code),
        }
        relevant_groups.append(group_row)
        by_symbol.setdefault(symbol, []).append(group_row)

    relevant_groups.sort(
        key=lambda item: (
            0 if _text(item.get("status")) == "pending" else 1,
            -_to_int(item.get("approval_age_sec"), 0),
            _text(item.get("symbol")),
            _to_int(item.get("group_id")),
        )
    )

    runtime_review_summary = _mapping(_mapping(pa8_runtime.get("review_packet")).get("summary"))
    runtime_apply_summary = _mapping(_mapping(pa8_runtime.get("apply_packet")).get("summary"))
    runtime_rows = list(_mapping(pa8_runtime.get("review_packet")).get("rows", []) or [])
    primary_focus_symbol = _text(summary.get("pa8_primary_focus_symbol")).upper()
    rows: list[dict[str, Any]] = []
    for raw_row in runtime_rows:
        row = _mapping(raw_row)
        symbol = _text(row.get("symbol")).upper()
        related_groups = list(by_symbol.get(symbol, []))
        primary_group = related_groups[0] if related_groups else {}
        rollback_required = _to_bool(row.get("rollback_required"))
        review_candidate = _to_bool(row.get("closeout_review_candidate"))
        apply_candidate = any(
            _text(_mapping(apply_row).get("symbol")).upper() == symbol
            and _to_bool(_mapping(apply_row).get("closeout_apply_candidate"))
            for apply_row in list(_mapping(pa8_runtime.get("apply_packet")).get("rows", []) or [])
        )
        cleanup_state = _row_cleanup_state(
            rollback_required=rollback_required,
            related_groups=related_groups,
            review_candidate=review_candidate,
            apply_candidate=apply_candidate,
            closeout_state=_text(row.get("closeout_state")).upper(),
        )
        approval_age_sec = _to_int(primary_group.get("approval_age_sec")) if primary_group else None
        lane_row = {
            "symbol": symbol,
            "cleanup_lane_state": cleanup_state,
            "cleanup_reason_ko": _row_cleanup_reason_ko(cleanup_state),
            "closeout_state": _text(row.get("closeout_state")).upper(),
            "first_window_status": _text(row.get("first_window_status")).upper(),
            "live_observation_ready": _to_bool(row.get("live_observation_ready")),
            "observed_window_row_count": _to_int(row.get("observed_window_row_count")),
            "sample_floor": _to_int(row.get("sample_floor")),
            "active_trigger_count": _to_int(row.get("active_trigger_count")),
            "rollback_required": rollback_required,
            "closeout_review_candidate": review_candidate,
            "closeout_apply_candidate": apply_candidate,
            "approval_group_count": len(related_groups),
            "primary_group_status": _text(primary_group.get("status")),
            "primary_review_type": _text(primary_group.get("review_type")),
            "primary_group_key": _text(primary_group.get("scope_key")),
            "primary_group_reason_summary": _text(primary_group.get("reason_summary")),
            "approval_age_sec": approval_age_sec,
            "deadline_state": _text(primary_group.get("deadline_state")),
            "recommended_next_action": _text(
                primary_group.get("relevance_code")
                and (
                    "review_pending_pa8_canary_rollback_prompt_in_telegram"
                    if _text(primary_group.get("relevance_code")) == "ROLLBACK_REVIEW_PENDING"
                    else "process_relevant_pa8_actionable_reviews_in_telegram"
                )
                or row.get("recommended_next_action")
                or summary.get("next_required_action")
            ),
            "primary_focus_symbol": symbol == primary_focus_symbol,
        }
        lane_row["cleanup_priority_score"] = _priority_score(
            symbol=symbol,
            primary_focus_symbol=primary_focus_symbol,
            cleanup_state=cleanup_state,
            related_group_count=len(related_groups),
            approval_age_sec=approval_age_sec,
        )
        rows.append(lane_row)

    rows.sort(
        key=lambda item: (
            -float(item.get("cleanup_priority_score") or 0.0),
            _text(item.get("symbol")),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["cleanup_priority_rank"] = index

    rollback_required_symbol_count = _to_int(runtime_review_summary.get("rollback_required_symbol_count"))
    closeout_review_candidate_count = _to_int(runtime_review_summary.get("review_candidate_symbol_count"))
    closeout_apply_candidate_count = _to_int(runtime_apply_summary.get("apply_candidate_symbol_count"))
    approval_backlog_count = _to_int(approval_state.get("approval_backlog_count"))
    apply_backlog_count = _to_int(approval_state.get("apply_backlog_count"))
    relevant_actionable_group_count = len(relevant_groups)
    unrelated_actionable_group_count = max(0, approval_backlog_count - relevant_actionable_group_count)
    rollback_approval_pending_count = sum(
        1 for group in relevant_groups if _text(group.get("relevance_code")) == "ROLLBACK_REVIEW_PENDING"
    )
    pending_group_count = sum(1 for group in relevant_groups if _text(group.get("status")) == "pending")
    held_group_count = sum(1 for group in relevant_groups if _text(group.get("status")) == "held")
    overall_cleanup_state, recommended_next_action = _summary_cleanup_state(
        rollback_approval_pending_count=rollback_approval_pending_count,
        relevant_actionable_group_count=relevant_actionable_group_count,
        approval_backlog_count=approval_backlog_count,
        apply_backlog_count=apply_backlog_count,
        rollback_required_symbol_count=rollback_required_symbol_count,
        closeout_review_candidate_count=closeout_review_candidate_count,
    )
    primary_cleanup_symbol = _text(rows[0].get("symbol")) if rows else primary_focus_symbol

    previous_approval_backlog_count = _to_int(previous_summary.get("approval_backlog_count"))
    previous_rollback_approval_pending_count = _to_int(
        previous_summary.get("rollback_approval_pending_count")
    )
    previous_relevant_actionable_group_count = _to_int(
        previous_summary.get("relevant_actionable_group_count")
    )

    return {
        "summary": {
            "contract_version": CHECKPOINT_PA8_ROLLBACK_APPROVAL_CLEANUP_LANE_CONTRACT_VERSION,
            "generated_at": _text(now_ts, now_dt.isoformat()),
            "trigger_state": "PA8_ROLLBACK_APPROVAL_CLEANUP_REFRESHED",
            "recommended_next_action": recommended_next_action,
            "overall_cleanup_state": overall_cleanup_state,
            "primary_focus_symbol": primary_focus_symbol,
            "primary_cleanup_symbol": primary_cleanup_symbol,
            "approval_backlog_count": approval_backlog_count,
            "approval_backlog_delta_count": approval_backlog_count - previous_approval_backlog_count,
            "apply_backlog_count": apply_backlog_count,
            "relevant_actionable_group_count": relevant_actionable_group_count,
            "relevant_actionable_group_delta_count": (
                relevant_actionable_group_count - previous_relevant_actionable_group_count
            ),
            "unrelated_actionable_group_count": unrelated_actionable_group_count,
            "pending_group_count": pending_group_count,
            "held_group_count": held_group_count,
            "rollback_required_symbol_count": rollback_required_symbol_count,
            "rollback_approval_pending_count": rollback_approval_pending_count,
            "rollback_approval_pending_delta_count": (
                rollback_approval_pending_count - previous_rollback_approval_pending_count
            ),
            "closeout_review_candidate_count": closeout_review_candidate_count,
            "closeout_apply_candidate_count": closeout_apply_candidate_count,
            "stale_actionable_count": _to_int(approval_state.get("stale_actionable_count")),
            "oldest_pending_approval_age_sec": approval_state.get("oldest_pending_approval_age_sec"),
        },
        "approval_groups": relevant_groups,
        "rows": rows,
    }


def render_checkpoint_pa8_rollback_approval_cleanup_lane_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    approval_groups = list(body.get("approval_groups", []) or [])
    rows = list(body.get("rows", []) or [])
    lines = [
        "# PA8 Rollback / Approval Cleanup Lane",
        "",
        f"- generated_at: `{_text(summary.get('generated_at'))}`",
        f"- overall_cleanup_state: `{_text(summary.get('overall_cleanup_state'))}`",
        f"- primary_focus_symbol: `{_text(summary.get('primary_focus_symbol'))}`",
        f"- primary_cleanup_symbol: `{_text(summary.get('primary_cleanup_symbol'))}`",
        f"- approval_backlog_count: `{_to_int(summary.get('approval_backlog_count'))}`",
        f"- relevant_actionable_group_count: `{_to_int(summary.get('relevant_actionable_group_count'))}`",
        f"- rollback_approval_pending_count: `{_to_int(summary.get('rollback_approval_pending_count'))}`",
        f"- closeout_review_candidate_count: `{_to_int(summary.get('closeout_review_candidate_count'))}`",
        f"- recommended_next_action: `{_text(summary.get('recommended_next_action'))}`",
        "",
        "## Relevant Approval Groups",
        "",
    ]
    if approval_groups:
        for group in approval_groups:
            group_map = _mapping(group)
            lines.append(
                f"- {_text(group_map.get('symbol'))} | `{_text(group_map.get('review_type'))}` | "
                f"`{_text(group_map.get('status'))}` | age `{_to_int(group_map.get('approval_age_sec'))}` | "
                f"{_text(group_map.get('reason_summary'))}"
            )
    else:
        lines.append("- `none`")
    lines.append("")
    for row in rows:
        row_map = _mapping(row)
        lines.append(f"## {_text(row_map.get('symbol'))}")
        lines.append("")
        for key in (
            "cleanup_lane_state",
            "closeout_state",
            "first_window_status",
            "live_observation_ready",
            "observed_window_row_count",
            "approval_group_count",
            "primary_group_status",
            "primary_review_type",
            "approval_age_sec",
            "recommended_next_action",
        ):
            lines.append(f"- {key}: `{row_map.get(key)}`")
        lines.append(f"- cleanup_reason_ko: {_text(row_map.get('cleanup_reason_ko'))}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def persist_checkpoint_pa8_rollback_approval_cleanup_lane(
    *,
    master_board_payload: Mapping[str, Any] | None = None,
    board_json_path: str | Path | None = None,
    pa8_closeout_runtime_payload: Mapping[str, Any] | None = None,
    pa8_closeout_runtime_json_path: str | Path | None = None,
    actionable_groups: list[Mapping[str, Any]] | None = None,
    telegram_state_store: TelegramStateStore | None = None,
    previous_payload: Mapping[str, Any] | None = None,
    previous_json_path: str | Path | None = None,
    output_json_path: str | Path | None = None,
    output_markdown_path: str | Path | None = None,
    now_ts: object | None = None,
) -> dict[str, Any]:
    payload = build_checkpoint_pa8_rollback_approval_cleanup_lane(
        master_board_payload=master_board_payload,
        board_json_path=board_json_path,
        pa8_closeout_runtime_payload=pa8_closeout_runtime_payload,
        pa8_closeout_runtime_json_path=pa8_closeout_runtime_json_path,
        actionable_groups=actionable_groups,
        telegram_state_store=telegram_state_store,
        previous_payload=previous_payload,
        previous_json_path=previous_json_path,
        now_ts=now_ts,
    )
    json_path = Path(
        output_json_path or default_checkpoint_pa8_rollback_approval_cleanup_lane_json_path()
    )
    markdown_path = Path(
        output_markdown_path or default_checkpoint_pa8_rollback_approval_cleanup_lane_markdown_path()
    )
    _write_json(json_path, payload)
    _write_text(markdown_path, render_checkpoint_pa8_rollback_approval_cleanup_lane_markdown(payload))
    return payload
