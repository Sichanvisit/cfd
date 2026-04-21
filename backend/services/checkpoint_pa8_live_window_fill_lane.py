from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.checkpoint_improvement_master_board import (
    default_checkpoint_improvement_master_board_json_path,
)


CHECKPOINT_PA8_LIVE_WINDOW_FILL_LANE_CONTRACT_VERSION = (
    "checkpoint_pa8_live_window_fill_lane_v1"
)


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_checkpoint_pa8_live_window_fill_lane_json_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_live_window_fill_lane_latest.json"


def default_checkpoint_pa8_live_window_fill_lane_markdown_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_live_window_fill_lane_latest.md"


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


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


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


def _fill_lane_state(
    *,
    closeout_state: str,
    observed_window_row_count: int,
    sample_floor: int,
    live_observation_ready: bool,
    active_trigger_count: int,
) -> str:
    if closeout_state == "ROLLBACK_REQUIRED":
        return "ROLLBACK_REVIEW_PENDING"
    if (
        sample_floor > 0
        and observed_window_row_count >= sample_floor
        and live_observation_ready
        and active_trigger_count <= 0
    ):
        return "READY_FOR_REVIEW"
    if observed_window_row_count > 0:
        return "ACTIVE_FILL"
    return "SEEDED_WAITING_ROWS"


def _fill_lane_reason_ko(fill_lane_state: str) -> str:
    if fill_lane_state == "ROLLBACK_REVIEW_PENDING":
        return "live row는 들어왔지만 rollback review를 먼저 처리해야 합니다."
    if fill_lane_state == "READY_FOR_REVIEW":
        return "sample floor와 live observation 조건이 충족되어 review로 바로 볼 수 있습니다."
    if fill_lane_state == "ACTIVE_FILL":
        return "live row가 누적 중이라 sample floor까지 계속 채우는 단계입니다."
    return "first window는 열렸지만 post-activation live row가 아직 충분히 들어오지 않았습니다."


def _velocity_state(current: int, previous: int | None) -> str:
    if previous is None:
        return "INITIAL_SNAPSHOT"
    delta = current - previous
    if delta > 0:
        return "GAINING_ROWS"
    if delta < 0:
        return "RESET_OR_ROLLED"
    if current > 0:
        return "FLAT_NO_GAIN"
    return "WAITING_FIRST_ROWS"


def _velocity_reason_ko(current: int, previous: int | None) -> str:
    state = _velocity_state(current, previous)
    if state == "GAINING_ROWS":
        return "직전 스냅샷보다 live row가 늘었습니다."
    if state == "RESET_OR_ROLLED":
        return "직전 스냅샷보다 live row가 줄어 재시드/롤백 가능성을 같이 봐야 합니다."
    if state == "FLAT_NO_GAIN":
        return "live row는 있으나 이번 스냅샷에서 추가 증가는 없었습니다."
    if state == "WAITING_FIRST_ROWS":
        return "아직 첫 live row를 기다리는 상태입니다."
    return "이번이 첫 fill lane 스냅샷입니다."


def _priority_score(
    *,
    symbol: str,
    primary_focus_symbol: str,
    fill_lane_state: str,
    progress_pct: float,
    active_trigger_count: int,
) -> float:
    score = progress_pct
    if symbol == primary_focus_symbol:
        score += 40.0
    if fill_lane_state == "ROLLBACK_REVIEW_PENDING":
        score += 60.0
    elif fill_lane_state == "READY_FOR_REVIEW":
        score += 50.0
    elif fill_lane_state == "ACTIVE_FILL":
        score += 20.0
    if active_trigger_count > 0:
        score += min(20.0, float(active_trigger_count) * 5.0)
    return round(score, 1)


def build_checkpoint_pa8_live_window_fill_lane(
    *,
    master_board_payload: Mapping[str, Any] | None = None,
    board_json_path: str | Path | None = None,
    previous_payload: Mapping[str, Any] | None = None,
    previous_json_path: str | Path | None = None,
    now_ts: object | None = None,
) -> dict[str, Any]:
    board = (
        _mapping(master_board_payload)
        if master_board_payload is not None
        else _load_json(board_json_path or default_checkpoint_improvement_master_board_json_path())
    )
    readiness_state = _mapping(board.get("readiness_state"))
    board_summary = _mapping(board.get("summary"))
    closeout_surface = _mapping(readiness_state.get("pa8_closeout_surface"))
    focus_surface = _mapping(readiness_state.get("pa8_closeout_focus_surface"))

    previous = (
        _mapping(previous_payload)
        if previous_payload is not None
        else _load_json(previous_json_path or default_checkpoint_pa8_live_window_fill_lane_json_path())
    )
    previous_rows = {
        _text(_mapping(row).get("symbol")).upper(): _mapping(row)
        for row in list(previous.get("rows", []) or [])
        if _text(_mapping(row).get("symbol"))
    }

    focus_rows = {
        _text(_mapping(row).get("symbol")).upper(): _mapping(row)
        for row in list(focus_surface.get("symbols", []) or [])
        if _text(_mapping(row).get("symbol"))
    }

    primary_focus_symbol = _text(
        focus_surface.get("primary_focus_symbol")
        or board_summary.get("pa8_primary_focus_symbol")
    ).upper()

    rows: list[dict[str, Any]] = []
    for raw_row in list(closeout_surface.get("symbols", []) or []):
        row = _mapping(raw_row)
        symbol = _text(row.get("symbol")).upper()
        focus_row = focus_rows.get(symbol, {})
        previous_row = previous_rows.get(symbol, {})

        observed_window_row_count = _to_int(row.get("observed_window_row_count"))
        sample_floor = _to_int(focus_row.get("sample_floor"), _to_int(row.get("sample_floor"), 0))
        rows_remaining_to_floor = max(0, sample_floor - observed_window_row_count)
        progress_pct = round((float(observed_window_row_count) / float(max(1, sample_floor))) * 100.0, 1)
        previous_observed_window_row_count = (
            _to_int(previous_row.get("observed_window_row_count"))
            if previous_row
            else None
        )
        progress_delta_rows = (
            observed_window_row_count - previous_observed_window_row_count
            if previous_observed_window_row_count is not None
            else observed_window_row_count
        )
        previous_progress_pct = (
            _to_float(previous_row.get("progress_pct"))
            if previous_row
            else None
        )
        progress_delta_pct = (
            round(progress_pct - previous_progress_pct, 1)
            if previous_progress_pct is not None
            else progress_pct
        )
        active_trigger_count = _to_int(row.get("active_trigger_count"))
        live_observation_ready = _to_bool(row.get("live_observation_ready"))
        closeout_state = _text(row.get("closeout_state"))
        fill_lane_state = _fill_lane_state(
            closeout_state=closeout_state,
            observed_window_row_count=observed_window_row_count,
            sample_floor=sample_floor,
            live_observation_ready=live_observation_ready,
            active_trigger_count=active_trigger_count,
        )
        priority_score = _priority_score(
            symbol=symbol,
            primary_focus_symbol=primary_focus_symbol,
            fill_lane_state=fill_lane_state,
            progress_pct=progress_pct,
            active_trigger_count=active_trigger_count,
        )
        lane_row = {
            "symbol": symbol,
            "focus_status": _text(focus_row.get("focus_status")),
            "fill_lane_state": fill_lane_state,
            "fill_lane_reason_ko": _fill_lane_reason_ko(fill_lane_state),
            "first_window_status": _text(row.get("first_window_status")),
            "closeout_state": closeout_state,
            "live_observation_ready": live_observation_ready,
            "observed_window_row_count": observed_window_row_count,
            "sample_floor": sample_floor,
            "rows_remaining_to_floor": rows_remaining_to_floor,
            "progress_pct": progress_pct,
            "progress_delta_rows": progress_delta_rows,
            "progress_delta_pct": progress_delta_pct,
            "velocity_state": _velocity_state(
                observed_window_row_count,
                previous_observed_window_row_count,
            ),
            "velocity_reason_ko": _velocity_reason_ko(
                observed_window_row_count,
                previous_observed_window_row_count,
            ),
            "active_trigger_count": active_trigger_count,
            "recommended_next_action": _text(
                row.get("recommended_next_action")
                or focus_row.get("recommended_next_action")
            ),
            "primary_focus_symbol": symbol == primary_focus_symbol,
            "priority_score": priority_score,
        }
        rows.append(lane_row)

    rows.sort(
        key=lambda item: (
            -_to_float(item.get("priority_score"), 0.0),
            _text(item.get("symbol")),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["fill_priority_rank"] = index

    rollback_pending_count = sum(1 for row in rows if _text(row.get("fill_lane_state")) == "ROLLBACK_REVIEW_PENDING")
    ready_for_review_count = sum(1 for row in rows if _text(row.get("fill_lane_state")) == "READY_FOR_REVIEW")
    active_fill_count = sum(1 for row in rows if _text(row.get("fill_lane_state")) == "ACTIVE_FILL")
    waiting_first_rows_count = sum(1 for row in rows if _text(row.get("fill_lane_state")) == "SEEDED_WAITING_ROWS")
    total_rows_remaining_to_floor = sum(_to_int(row.get("rows_remaining_to_floor")) for row in rows)

    if rollback_pending_count > 0:
        overall_fill_state = "ROLLBACK_REVIEW_PENDING"
        recommended_next_action = "process_pa8_rollback_candidates_before_more_fill_observation"
    elif ready_for_review_count > 0:
        overall_fill_state = "READY_FOR_REVIEW"
        recommended_next_action = "inspect_live_ready_symbol_windows_first"
    elif active_fill_count > 0:
        overall_fill_state = "ACTIVE_FILL"
        recommended_next_action = "continue_accumulating_post_activation_live_rows_until_sample_floor"
    else:
        overall_fill_state = "WAITING_FIRST_ROWS"
        recommended_next_action = "keep_canary_active_and_wait_for_post_activation_rows"

    generated_at = _text(now_ts, datetime.now().astimezone().isoformat())
    return {
        "summary": {
            "contract_version": CHECKPOINT_PA8_LIVE_WINDOW_FILL_LANE_CONTRACT_VERSION,
            "generated_at": generated_at,
            "trigger_state": "PA8_LIVE_WINDOW_FILL_REFRESHED",
            "recommended_next_action": recommended_next_action,
            "overall_fill_state": overall_fill_state,
            "primary_focus_symbol": primary_focus_symbol,
            "symbol_count": len(rows),
            "ready_for_review_count": ready_for_review_count,
            "rollback_pending_count": rollback_pending_count,
            "active_fill_count": active_fill_count,
            "waiting_first_rows_count": waiting_first_rows_count,
            "total_rows_remaining_to_floor": total_rows_remaining_to_floor,
        },
        "rows": rows,
    }


def render_checkpoint_pa8_live_window_fill_lane_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows", []) or [])
    lines = [
        "# PA8 Live Window Fill Lane",
        "",
        f"- generated_at: `{_text(summary.get('generated_at'))}`",
        f"- overall_fill_state: `{_text(summary.get('overall_fill_state'))}`",
        f"- primary_focus_symbol: `{_text(summary.get('primary_focus_symbol'))}`",
        f"- ready_for_review_count: `{_to_int(summary.get('ready_for_review_count'))}`",
        f"- rollback_pending_count: `{_to_int(summary.get('rollback_pending_count'))}`",
        f"- active_fill_count: `{_to_int(summary.get('active_fill_count'))}`",
        f"- waiting_first_rows_count: `{_to_int(summary.get('waiting_first_rows_count'))}`",
        f"- total_rows_remaining_to_floor: `{_to_int(summary.get('total_rows_remaining_to_floor'))}`",
        f"- recommended_next_action: `{_text(summary.get('recommended_next_action'))}`",
        "",
    ]
    for row in rows:
        row_map = _mapping(row)
        lines.append(f"## { _text(row_map.get('symbol')) }")
        lines.append("")
        lines.append(f"- fill_lane_state: `{_text(row_map.get('fill_lane_state'))}`")
        lines.append(f"- reason_ko: {_text(row_map.get('fill_lane_reason_ko'))}")
        lines.append(f"- observed_window_row_count: `{_to_int(row_map.get('observed_window_row_count'))}`")
        lines.append(f"- sample_floor: `{_to_int(row_map.get('sample_floor'))}`")
        lines.append(f"- rows_remaining_to_floor: `{_to_int(row_map.get('rows_remaining_to_floor'))}`")
        lines.append(f"- progress_pct: `{_to_float(row_map.get('progress_pct'))}`")
        lines.append(f"- progress_delta_rows: `{_to_int(row_map.get('progress_delta_rows'))}`")
        lines.append(f"- velocity_state: `{_text(row_map.get('velocity_state'))}`")
        lines.append(f"- velocity_reason_ko: {_text(row_map.get('velocity_reason_ko'))}")
        lines.append(f"- active_trigger_count: `{_to_int(row_map.get('active_trigger_count'))}`")
        lines.append(f"- closeout_state: `{_text(row_map.get('closeout_state'))}`")
        lines.append(f"- recommended_next_action: `{_text(row_map.get('recommended_next_action'))}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def persist_checkpoint_pa8_live_window_fill_lane(
    *,
    master_board_payload: Mapping[str, Any] | None = None,
    board_json_path: str | Path | None = None,
    previous_payload: Mapping[str, Any] | None = None,
    previous_json_path: str | Path | None = None,
    output_json_path: str | Path | None = None,
    output_markdown_path: str | Path | None = None,
    now_ts: object | None = None,
) -> dict[str, Any]:
    payload = build_checkpoint_pa8_live_window_fill_lane(
        master_board_payload=master_board_payload,
        board_json_path=board_json_path,
        previous_payload=previous_payload,
        previous_json_path=previous_json_path,
        now_ts=now_ts,
    )
    json_path = Path(output_json_path or default_checkpoint_pa8_live_window_fill_lane_json_path())
    markdown_path = Path(output_markdown_path or default_checkpoint_pa8_live_window_fill_lane_markdown_path())
    _write_json(json_path, payload)
    _write_text(markdown_path, render_checkpoint_pa8_live_window_fill_lane_markdown(payload))
    return payload
