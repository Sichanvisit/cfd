from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.core.config import Config
from backend.services.improvement_board_field_policy import (
    CONFIDENCE_LEVEL_HIGH,
    CONFIDENCE_LEVEL_LIMITED,
    CONFIDENCE_LEVEL_LOW,
    CONFIDENCE_LEVEL_MEDIUM,
)
from backend.services.improvement_status_policy import (
    READINESS_STATUS_BLOCKED,
    READINESS_STATUS_NOT_APPLICABLE,
    READINESS_STATUS_PENDING_EVIDENCE,
    READINESS_STATUS_READY_FOR_APPLY,
    READINESS_STATUS_READY_FOR_REVIEW,
)


IMPROVEMENT_READINESS_SURFACE_CONTRACT_VERSION = "improvement_readiness_surface_v1"

PA8_CLOSEOUT_FOCUS_STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
PA8_CLOSEOUT_FOCUS_STATUS_PENDING_EVIDENCE = "PENDING_EVIDENCE"
PA8_CLOSEOUT_FOCUS_STATUS_WATCHLIST = "WATCHLIST"
PA8_CLOSEOUT_FOCUS_STATUS_CONCENTRATED = "CONCENTRATED"
PA8_CLOSEOUT_FOCUS_STATUS_READY_FOR_REVIEW = "READY_FOR_REVIEW"
PA8_CLOSEOUT_FOCUS_STATUS_BLOCKED = "BLOCKED"

FIRST_SYMBOL_OBSERVATION_STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
FIRST_SYMBOL_OBSERVATION_STATUS_WATCHLIST = "WATCHLIST"
FIRST_SYMBOL_OBSERVATION_STATUS_CONCENTRATED = "CONCENTRATED"
FIRST_SYMBOL_OBSERVATION_STATUS_READY_FOR_CLOSEOUT_REVIEW = "READY_FOR_CLOSEOUT_REVIEW"
FIRST_SYMBOL_OBSERVATION_STATUS_READY_FOR_HANDOFF_REVIEW = "READY_FOR_HANDOFF_REVIEW"
FIRST_SYMBOL_OBSERVATION_STATUS_READY_FOR_HANDOFF_APPLY = "READY_FOR_HANDOFF_APPLY"
FIRST_SYMBOL_OBSERVATION_STATUS_APPLIED = "APPLIED"
FIRST_SYMBOL_OBSERVATION_STATUS_BLOCKED = "BLOCKED"

PA7_NARROW_REVIEW_STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
PA7_NARROW_REVIEW_STATUS_CLEAR = "CLEAR"
PA7_NARROW_REVIEW_STATUS_WATCHLIST = "WATCHLIST"
PA7_NARROW_REVIEW_STATUS_REVIEW_NEEDED = "REVIEW_NEEDED"

PA8_CLOSEOUT_WATCHLIST_PROGRESS_RATIO = 0.50
PA8_CLOSEOUT_CONCENTRATED_PROGRESS_RATIO = 0.80


def default_improvement_readiness_surface_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "improvement_readiness_surface_latest.json"
    )


def default_improvement_readiness_surface_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "improvement_readiness_surface_latest.md"
    )


def default_closed_trade_csv_path() -> Path:
    raw = str(getattr(Config, "CLOSED_TRADE_CSV_PATH", r"data\trades\trade_closed_history.csv") or "").strip()
    path = Path(raw) if raw else Path(r"data\trades\trade_closed_history.csv")
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path.resolve()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
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


def _load_runtime_status_detail_payload(
    *,
    runtime_status_path: str | Path | None,
    runtime_status_payload: Mapping[str, Any],
) -> dict[str, Any]:
    status_path = Path(runtime_status_path or "")
    if not status_path.name:
        return {}
    detail_name = _to_text(runtime_status_payload.get("detail_payload_path"))
    detail_path = status_path.with_name(detail_name) if detail_name else status_path.with_suffix(".detail.json")
    if not detail_path.exists():
        return {}
    return _load_json(detail_path)


def _safe_numeric_series(frame: pd.DataFrame, column_name: str) -> pd.Series:
    if column_name not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[column_name], errors="coerce").fillna(0.0)


def _load_closed_trade_frame(path: str | Path | None) -> pd.DataFrame:
    file_path = Path(path or default_closed_trade_csv_path())
    if not file_path.exists():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except UnicodeDecodeError:
        frame = pd.read_csv(file_path, encoding="utf-8", low_memory=False)
    except Exception:
        return pd.DataFrame()
    return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()


def _build_pa8_closeout_surface(
    *,
    pa8_payload: Mapping[str, Any],
    phase: str,
) -> dict[str, Any]:
    phase_upper = _to_text(phase).upper()
    rows = list(_mapping(pa8_payload).get("rows", []) or [])
    summary = _mapping(_mapping(pa8_payload).get("summary"))
    active_symbol_count = _to_int(summary.get("active_symbol_count"))
    live_window_ready_count = _to_int(summary.get("live_observation_ready_count"))
    surface_rows: list[dict[str, Any]] = []
    ready_count = 0
    pending_count = 0
    blocked_count = 0

    for row in rows:
        row_map = _mapping(row)
        symbol = _to_text(row_map.get("symbol"))
        live_ready = bool(row_map.get("live_observation_ready"))
        active_trigger_count = _to_int(row_map.get("active_trigger_count"))
        observed_window_row_count = _to_int(row_map.get("observed_window_row_count"))
        closeout_state = _to_text(row_map.get("closeout_state"))
        first_window_status = _to_text(row_map.get("first_window_status"))
        next_action = _to_text(row_map.get("recommended_next_action"))

        if phase_upper in {"DEGRADED", "EMERGENCY"}:
            readiness_status = READINESS_STATUS_BLOCKED
            blocking_reason = "system_phase_degraded"
            blocked_count += 1
        elif live_ready:
            readiness_status = READINESS_STATUS_READY_FOR_REVIEW
            blocking_reason = "none"
            ready_count += 1
        else:
            readiness_status = READINESS_STATUS_PENDING_EVIDENCE
            blocking_reason = "live_window_pending"
            pending_count += 1

        surface_rows.append(
            {
                "symbol": symbol,
                "readiness_status": readiness_status,
                "blocking_reason": blocking_reason,
                "closeout_state": closeout_state,
                "first_window_status": first_window_status,
                "live_observation_ready": live_ready,
                "observed_window_row_count": observed_window_row_count,
                "active_trigger_count": active_trigger_count,
                "recommended_next_action": next_action,
            }
        )

    if phase_upper in {"DEGRADED", "EMERGENCY"}:
        overall_status = READINESS_STATUS_BLOCKED
        overall_reason = "system_phase_degraded"
    elif active_symbol_count <= 0 and not surface_rows:
        overall_status = READINESS_STATUS_NOT_APPLICABLE
        overall_reason = "no_active_pa8_canaries"
    elif live_window_ready_count > 0 and live_window_ready_count >= max(active_symbol_count, len(surface_rows), 1):
        overall_status = READINESS_STATUS_READY_FOR_REVIEW
        overall_reason = "none"
    elif active_symbol_count > 0 or surface_rows:
        overall_status = READINESS_STATUS_PENDING_EVIDENCE
        overall_reason = "live_window_pending"
    else:
        overall_status = READINESS_STATUS_NOT_APPLICABLE
        overall_reason = "no_active_pa8_canaries"

    return {
        "readiness_status": overall_status,
        "blocking_reason": overall_reason,
        "ready_symbol_count": max(ready_count, live_window_ready_count),
        "pending_symbol_count": max(pending_count, max(active_symbol_count - live_window_ready_count, 0)),
        "blocked_symbol_count": blocked_count,
        "active_symbol_count": active_symbol_count,
        "live_window_ready_count": live_window_ready_count,
        "closeout_state_counts": dict(summary.get("closeout_state_counts", {}) or {}),
        "recommended_next_action": _to_text(summary.get("recommended_next_action")),
        "symbols": surface_rows,
    }


def _merge_rows_by_symbol(*row_groups: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for group in row_groups:
        for row in group:
            row_map = _mapping(row)
            symbol = _to_text(row_map.get("symbol"))
            if not symbol:
                continue
            current = merged.setdefault(symbol, {"symbol": symbol})
            current.update({key: value for key, value in row_map.items() if value not in ("", None)})
    return merged


def _build_pa9_handoff_surface(
    *,
    handoff_payload: Mapping[str, Any],
    review_payload: Mapping[str, Any],
    apply_payload: Mapping[str, Any],
) -> dict[str, Any]:
    handoff_summary = _mapping(_mapping(handoff_payload).get("summary"))
    review_summary = _mapping(_mapping(review_payload).get("summary"))
    apply_summary = _mapping(_mapping(apply_payload).get("summary"))
    merged_rows = _merge_rows_by_symbol(
        list(_mapping(handoff_payload).get("rows", []) or []),
        list(_mapping(review_payload).get("rows", []) or []),
        list(_mapping(apply_payload).get("rows", []) or []),
    )

    ready_for_review_count = 0
    ready_for_apply_count = 0
    pending_count = 0
    surface_rows: list[dict[str, Any]] = []
    for symbol in sorted(merged_rows):
        row_map = merged_rows[symbol]
        review_candidate = bool(row_map.get("handoff_review_candidate"))
        apply_candidate = bool(row_map.get("handoff_apply_candidate"))
        if apply_candidate:
            readiness_status = READINESS_STATUS_READY_FOR_APPLY
            blocking_reason = "none"
            ready_for_apply_count += 1
        elif review_candidate:
            readiness_status = READINESS_STATUS_READY_FOR_REVIEW
            blocking_reason = "none"
            ready_for_review_count += 1
        else:
            readiness_status = READINESS_STATUS_PENDING_EVIDENCE
            blocking_reason = "pa8_live_window_pending"
            pending_count += 1
        surface_rows.append(
            {
                "symbol": symbol,
                "readiness_status": readiness_status,
                "blocking_reason": blocking_reason,
                "closeout_state": _to_text(row_map.get("closeout_state")),
                "live_observation_ready": bool(row_map.get("live_observation_ready")),
                "observed_window_row_count": _to_int(row_map.get("observed_window_row_count")),
                "sample_floor": _to_int(row_map.get("sample_floor")),
                "active_trigger_count": _to_int(row_map.get("active_trigger_count")),
                "handoff_review_candidate": review_candidate,
                "handoff_apply_candidate": apply_candidate,
                "recommended_next_action": _to_text(
                    row_map.get("closeout_recommended_next_action")
                    or apply_summary.get("recommended_next_action")
                    or review_summary.get("recommended_next_action")
                    or handoff_summary.get("recommended_next_action")
                ),
            }
        )

    if _to_text(apply_summary.get("apply_state")).startswith("READY_FOR_") or ready_for_apply_count > 0:
        overall_status = READINESS_STATUS_READY_FOR_APPLY
        overall_reason = "none"
    elif _to_text(review_summary.get("review_state")).startswith("READY_FOR_") or ready_for_review_count > 0:
        overall_status = READINESS_STATUS_READY_FOR_REVIEW
        overall_reason = "none"
    elif surface_rows:
        overall_status = READINESS_STATUS_PENDING_EVIDENCE
        overall_reason = "pa8_live_window_pending"
    else:
        overall_status = READINESS_STATUS_NOT_APPLICABLE
        overall_reason = "no_active_pa9_candidates"

    return {
        "readiness_status": overall_status,
        "blocking_reason": overall_reason,
        "handoff_state": _to_text(handoff_summary.get("handoff_state")),
        "review_state": _to_text(review_summary.get("review_state")),
        "apply_state": _to_text(apply_summary.get("apply_state")),
        "prepared_symbol_count": _to_int(handoff_summary.get("prepared_symbol_count")),
        "ready_for_review_symbol_count": ready_for_review_count,
        "ready_for_apply_symbol_count": ready_for_apply_count,
        "pending_symbol_count": pending_count,
        "recommended_next_action": _to_text(
            apply_summary.get("recommended_next_action")
            or review_summary.get("recommended_next_action")
            or handoff_summary.get("recommended_next_action")
        ),
        "symbols": surface_rows,
    }


def _build_pa8_closeout_focus_surface(
    *,
    phase: str,
    pa8_surface: Mapping[str, Any],
    pa9_surface: Mapping[str, Any],
) -> dict[str, Any]:
    phase_upper = _to_text(phase).upper()
    merged_rows = _merge_rows_by_symbol(
        list(_mapping(pa8_surface).get("symbols", []) or []),
        list(_mapping(pa9_surface).get("symbols", []) or []),
    )
    active_symbol_count = _to_int(_mapping(pa8_surface).get("active_symbol_count"))
    surface_rows: list[dict[str, Any]] = []
    ready_count = 0
    concentrated_count = 0
    watchlist_count = 0
    pending_count = 0
    blocked_count = 0

    for symbol in sorted(merged_rows):
        row_map = merged_rows[symbol]
        live_ready = bool(
            row_map.get("live_observation_ready")
            or _to_text(row_map.get("readiness_status")).upper() == READINESS_STATUS_READY_FOR_REVIEW
        )
        sample_floor = max(1, _to_int(row_map.get("sample_floor"), 30))
        observed_window_row_count = _to_int(row_map.get("observed_window_row_count"))
        progress_ratio = min(1.0, observed_window_row_count / float(sample_floor))
        active_trigger_count = _to_int(row_map.get("active_trigger_count"))
        closeout_state = _to_text(row_map.get("closeout_state")).upper()
        base_next_action = _to_text(
            row_map.get("recommended_next_action")
            or _mapping(pa8_surface).get("recommended_next_action")
            or _mapping(pa9_surface).get("recommended_next_action")
            or "wait_for_more_live_rows"
        )

        if phase_upper in {"DEGRADED", "EMERGENCY"}:
            focus_status = PA8_CLOSEOUT_FOCUS_STATUS_BLOCKED
            focus_reason_ko = "시스템 phase가 degraded/emergency라 closeout 집중 관찰을 진행할 수 없습니다."
            recommended_next_action = "inspect_degraded_components_and_restore_dependencies"
            focus_score = -1.0
            blocked_count += 1
        elif live_ready or "READY_FOR_" in closeout_state:
            focus_status = PA8_CLOSEOUT_FOCUS_STATUS_READY_FOR_REVIEW
            focus_reason_ko = "live window가 준비돼 closeout review 후보로 바로 볼 수 있습니다."
            recommended_next_action = base_next_action or "review_pa8_closeout_candidate"
            focus_score = 100.0 + (active_trigger_count * 5.0) + (progress_ratio * 10.0)
            ready_count += 1
        elif "ROLLBACK" in closeout_state:
            focus_status = PA8_CLOSEOUT_FOCUS_STATUS_CONCENTRATED
            focus_reason_ko = "rollback 성격 closeout 후보가 보여 우선 집중 관찰이 필요합니다."
            recommended_next_action = (
                f"concentrate_closeout_monitoring_on_{symbol.lower()}_rollback_candidate"
            )
            focus_score = 90.0 + (active_trigger_count * 5.0) + (progress_ratio * 10.0)
            concentrated_count += 1
        elif progress_ratio >= PA8_CLOSEOUT_CONCENTRATED_PROGRESS_RATIO:
            focus_status = PA8_CLOSEOUT_FOCUS_STATUS_CONCENTRATED
            focus_reason_ko = "sample floor의 80% 이상이 쌓여 closeout-ready 직전 집중 관찰 구간입니다."
            recommended_next_action = (
                f"concentrate_closeout_monitoring_on_{symbol.lower()}_until_sample_floor_reached"
            )
            focus_score = 80.0 + (active_trigger_count * 5.0) + (progress_ratio * 10.0)
            concentrated_count += 1
        elif progress_ratio >= PA8_CLOSEOUT_WATCHLIST_PROGRESS_RATIO or active_trigger_count > 0:
            focus_status = PA8_CLOSEOUT_FOCUS_STATUS_WATCHLIST
            focus_reason_ko = "live row가 절반 이상 쌓였거나 active trigger가 있어 watchlist에 올릴 가치가 있습니다."
            recommended_next_action = f"keep_closeout_watchlist_on_{symbol.lower()}"
            focus_score = 50.0 + (active_trigger_count * 5.0) + (progress_ratio * 10.0)
            watchlist_count += 1
        else:
            focus_status = PA8_CLOSEOUT_FOCUS_STATUS_PENDING_EVIDENCE
            focus_reason_ko = "아직 closeout 집중 관찰로 끌어올릴 만큼 live evidence가 충분하지 않습니다."
            recommended_next_action = base_next_action or "wait_for_more_live_rows"
            focus_score = progress_ratio * 10.0
            pending_count += 1

        surface_rows.append(
            {
                "symbol": symbol,
                "focus_status": focus_status,
                "focus_reason_ko": focus_reason_ko,
                "sample_floor": sample_floor,
                "observed_window_row_count": observed_window_row_count,
                "window_progress_ratio": round(progress_ratio, 4),
                "active_trigger_count": active_trigger_count,
                "closeout_state": _to_text(row_map.get("closeout_state")),
                "live_observation_ready": bool(row_map.get("live_observation_ready")),
                "recommended_next_action": recommended_next_action,
                "focus_score": round(focus_score, 4),
            }
        )

    ranked_rows = sorted(
        surface_rows,
        key=lambda row: (
            {
                PA8_CLOSEOUT_FOCUS_STATUS_READY_FOR_REVIEW: 5,
                PA8_CLOSEOUT_FOCUS_STATUS_CONCENTRATED: 4,
                PA8_CLOSEOUT_FOCUS_STATUS_WATCHLIST: 3,
                PA8_CLOSEOUT_FOCUS_STATUS_PENDING_EVIDENCE: 2,
                PA8_CLOSEOUT_FOCUS_STATUS_BLOCKED: 1,
                PA8_CLOSEOUT_FOCUS_STATUS_NOT_APPLICABLE: 0,
            }.get(_to_text(row.get("focus_status")), 0),
            _to_float(row.get("focus_score")),
            _to_int(row.get("observed_window_row_count")),
        ),
        reverse=True,
    )
    for index, row in enumerate(ranked_rows, start=1):
        row["focus_priority_rank"] = index

    primary_row = ranked_rows[0] if ranked_rows else {}
    focus_symbol_count = ready_count + concentrated_count
    if phase_upper in {"DEGRADED", "EMERGENCY"}:
        focus_status = PA8_CLOSEOUT_FOCUS_STATUS_BLOCKED
        blocking_reason = "system_phase_degraded"
        recommended_next_action = "inspect_degraded_components_and_restore_dependencies"
    elif ready_count > 0:
        focus_status = PA8_CLOSEOUT_FOCUS_STATUS_READY_FOR_REVIEW
        blocking_reason = "none"
        recommended_next_action = _to_text(primary_row.get("recommended_next_action"), "review_pa8_closeout_candidate")
    elif concentrated_count > 0:
        focus_status = PA8_CLOSEOUT_FOCUS_STATUS_CONCENTRATED
        blocking_reason = "live_window_pending"
        recommended_next_action = _to_text(primary_row.get("recommended_next_action"), "concentrate_closeout_monitoring_on_primary_symbol")
    elif watchlist_count > 0:
        focus_status = PA8_CLOSEOUT_FOCUS_STATUS_WATCHLIST
        blocking_reason = "live_window_pending"
        recommended_next_action = _to_text(primary_row.get("recommended_next_action"), "keep_pa8_closeout_watchlist")
    elif active_symbol_count > 0 or ranked_rows:
        focus_status = PA8_CLOSEOUT_FOCUS_STATUS_PENDING_EVIDENCE
        blocking_reason = "live_window_pending"
        recommended_next_action = _to_text(_mapping(pa8_surface).get("recommended_next_action"), "wait_for_more_live_rows")
    else:
        focus_status = PA8_CLOSEOUT_FOCUS_STATUS_NOT_APPLICABLE
        blocking_reason = "no_active_pa8_canaries"
        recommended_next_action = "wait_for_active_pa8_canary"

    return {
        "focus_status": focus_status,
        "blocking_reason": blocking_reason,
        "focus_symbol_count": focus_symbol_count,
        "ready_for_review_symbol_count": ready_count,
        "concentrated_symbol_count": concentrated_count,
        "watchlist_symbol_count": watchlist_count,
        "pending_symbol_count": pending_count,
        "blocked_symbol_count": blocked_count,
        "primary_focus_symbol": _to_text(primary_row.get("symbol")),
        "primary_focus_reason_ko": _to_text(primary_row.get("focus_reason_ko")),
        "primary_focus_progress_ratio": _to_float(primary_row.get("window_progress_ratio")),
        "recommended_next_action": recommended_next_action,
        "symbols": ranked_rows,
    }


def _build_first_symbol_closeout_handoff_surface(
    *,
    phase: str,
    pa8_focus_surface: Mapping[str, Any],
    pa9_surface: Mapping[str, Any],
) -> dict[str, Any]:
    phase_upper = _to_text(phase).upper()
    focus_rows = {
        _to_text(row_map.get("symbol")): row_map
        for row_map in (_mapping(row) for row in list(_mapping(pa8_focus_surface).get("symbols", []) or []))
        if _to_text(row_map.get("symbol"))
    }
    handoff_rows = {
        _to_text(row_map.get("symbol")): row_map
        for row_map in (_mapping(row) for row in list(_mapping(pa9_surface).get("symbols", []) or []))
        if _to_text(row_map.get("symbol"))
    }
    primary_symbol = _to_text(pa8_focus_surface.get("primary_focus_symbol"))
    if not primary_symbol:
        for row in list(_mapping(pa9_surface).get("symbols", []) or []):
            row_map = _mapping(row)
            if bool(row_map.get("handoff_apply_candidate")) or bool(row_map.get("handoff_review_candidate")):
                primary_symbol = _to_text(row_map.get("symbol"))
                break
    if not primary_symbol:
        primary_symbol = next(iter(focus_rows or handoff_rows), "")

    if not primary_symbol:
        return {
            "observation_status": FIRST_SYMBOL_OBSERVATION_STATUS_NOT_APPLICABLE,
            "observation_stage": "NONE",
            "primary_symbol": "",
            "reason_ko": "아직 first symbol closeout/handoff 관찰 대상이 없습니다.",
            "recommended_next_action": "wait_for_first_pa8_symbol_candidate",
            "focus_progress_ratio": 0.0,
            "observed_window_row_count": 0,
            "sample_floor": 0,
            "active_trigger_count": 0,
            "handoff_review_candidate": False,
            "handoff_apply_candidate": False,
        }

    focus_row = dict(focus_rows.get(primary_symbol, {}))
    handoff_row = dict(handoff_rows.get(primary_symbol, {}))
    focus_status = _to_text(focus_row.get("focus_status")).upper()
    handoff_apply_candidate = bool(handoff_row.get("handoff_apply_candidate"))
    handoff_review_candidate = bool(handoff_row.get("handoff_review_candidate"))
    handoff_state = _to_text(pa9_surface.get("handoff_state")).upper()
    review_state = _to_text(pa9_surface.get("review_state")).upper()
    apply_state = _to_text(pa9_surface.get("apply_state")).upper()

    if phase_upper in {"DEGRADED", "EMERGENCY"}:
        observation_status = FIRST_SYMBOL_OBSERVATION_STATUS_BLOCKED
        observation_stage = "BLOCKED"
        reason_ko = "시스템 phase가 degraded/emergency라 first symbol 승격 관찰을 밀어붙이지 않습니다."
        recommended_next_action = "inspect_degraded_components_and_restore_dependencies"
    elif (
        handoff_state == "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED"
        or review_state == "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED"
        or apply_state == "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED"
    ):
        observation_status = FIRST_SYMBOL_OBSERVATION_STATUS_APPLIED
        observation_stage = "COMPLETE"
        reason_ko = "first symbol handoff가 이미 적용돼 다음 승격 후보를 보면 됩니다."
        recommended_next_action = "monitor_next_pa8_symbol_for_closeout_handoff"
    elif handoff_apply_candidate:
        observation_status = FIRST_SYMBOL_OBSERVATION_STATUS_READY_FOR_HANDOFF_APPLY
        observation_stage = "PA9_HANDOFF"
        reason_ko = "closeout 이후 PA9 handoff apply 직전까지 왔습니다."
        recommended_next_action = _to_text(
            handoff_row.get("recommended_next_action"),
            "approve_and_apply_pa9_action_baseline_handoff_when_review_is_confirmed",
        )
    elif handoff_review_candidate:
        observation_status = FIRST_SYMBOL_OBSERVATION_STATUS_READY_FOR_HANDOFF_REVIEW
        observation_stage = "PA9_HANDOFF"
        reason_ko = "PA8 closeout 이후 first symbol handoff review를 바로 볼 수 있습니다."
        recommended_next_action = _to_text(
            handoff_row.get("recommended_next_action"),
            "review_prepared_pa9_action_baseline_handoff_packet",
        )
    elif focus_status == PA8_CLOSEOUT_FOCUS_STATUS_READY_FOR_REVIEW:
        observation_status = FIRST_SYMBOL_OBSERVATION_STATUS_READY_FOR_CLOSEOUT_REVIEW
        observation_stage = "PA8_CLOSEOUT"
        reason_ko = "first symbol이 PA8 closeout review 바로 직전 상태입니다."
        recommended_next_action = _to_text(
            focus_row.get("recommended_next_action"),
            "review_pa8_closeout_candidate",
        )
    elif focus_status == PA8_CLOSEOUT_FOCUS_STATUS_CONCENTRATED:
        observation_status = FIRST_SYMBOL_OBSERVATION_STATUS_CONCENTRATED
        observation_stage = "PA8_CLOSEOUT"
        reason_ko = "first symbol closeout-ready 직전이라 집중 관찰 구간입니다."
        recommended_next_action = _to_text(
            focus_row.get("recommended_next_action"),
            "concentrate_closeout_monitoring_on_primary_symbol",
        )
    elif focus_status == PA8_CLOSEOUT_FOCUS_STATUS_WATCHLIST:
        observation_status = FIRST_SYMBOL_OBSERVATION_STATUS_WATCHLIST
        observation_stage = "PA8_CLOSEOUT"
        reason_ko = "first symbol을 watchlist로 두고 live evidence가 쌓이는지 계속 봅니다."
        recommended_next_action = _to_text(
            focus_row.get("recommended_next_action"),
            "keep_first_symbol_watchlist_until_more_live_rows",
        )
    else:
        observation_status = FIRST_SYMBOL_OBSERVATION_STATUS_NOT_APPLICABLE
        observation_stage = "NONE"
        reason_ko = "first symbol 승격 관찰로 올릴 만큼 evidence가 아직 충분하지 않습니다."
        recommended_next_action = _to_text(
            focus_row.get("recommended_next_action")
            or handoff_row.get("recommended_next_action"),
            "wait_for_first_pa8_symbol_candidate",
        )

    return {
        "observation_status": observation_status,
        "observation_stage": observation_stage,
        "primary_symbol": primary_symbol,
        "reason_ko": reason_ko,
        "recommended_next_action": recommended_next_action,
        "focus_progress_ratio": _to_float(
            focus_row.get("window_progress_ratio"),
            0.0,
        ),
        "observed_window_row_count": _to_int(
            handoff_row.get("observed_window_row_count"),
            _to_int(focus_row.get("observed_window_row_count")),
        ),
        "sample_floor": _to_int(
            handoff_row.get("sample_floor"),
            _to_int(focus_row.get("sample_floor")),
        ),
        "active_trigger_count": _to_int(
            handoff_row.get("active_trigger_count"),
            _to_int(focus_row.get("active_trigger_count")),
        ),
        "handoff_review_candidate": handoff_review_candidate,
        "handoff_apply_candidate": handoff_apply_candidate,
    }


def _build_pa7_narrow_review_surface(
    *,
    pa7_review_processor_payload: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _mapping(pa7_review_processor_payload)
    summary = _mapping(payload.get("summary"))
    rows = list(payload.get("group_rows", []) or [])
    filtered_rows: list[dict[str, Any]] = []
    mixed_wait_count = 0
    mixed_count = 0
    for row in rows:
        row_map = _mapping(row)
        disposition = _to_text(row_map.get("review_disposition"))
        if disposition not in {"mixed_wait_boundary_review", "mixed_review"}:
            continue
        lane_status = (
            PA7_NARROW_REVIEW_STATUS_REVIEW_NEEDED
            if disposition == "mixed_wait_boundary_review"
            else PA7_NARROW_REVIEW_STATUS_WATCHLIST
        )
        if disposition == "mixed_wait_boundary_review":
            mixed_wait_count += 1
            reason_ko = "WAIT 경계 혼합 review가 남아 있어 closeout 전 좁게 다시 봐야 합니다."
            recommended_next_action = "review_remaining_mixed_wait_boundary_groups_before_first_closeout"
        else:
            mixed_count += 1
            reason_ko = "혼합 review가 남아 있어 관찰 lane으로 계속 추적합니다."
            recommended_next_action = "keep_watch_on_remaining_mixed_pa7_groups"
        filtered_rows.append(
            {
                "group_key": _to_text(row_map.get("group_key")),
                "symbol": _to_text(row_map.get("symbol")),
                "review_disposition": disposition,
                "lane_status": lane_status,
                "reason_ko": reason_ko,
                "review_reason": _to_text(row_map.get("review_reason")),
                "row_count": _to_int(row_map.get("row_count")),
                "avg_abs_current_profit": _to_float(row_map.get("avg_abs_current_profit")),
                "resolved_baseline_action_label": _to_text(row_map.get("resolved_baseline_action_label")),
                "policy_replay_action_label": _to_text(row_map.get("policy_replay_action_label")),
                "hindsight_best_management_action_label": _to_text(row_map.get("hindsight_best_management_action_label")),
                "recommended_next_action": recommended_next_action,
            }
        )

    filtered_rows = sorted(
        filtered_rows,
        key=lambda row: (
            1 if _to_text(row.get("lane_status")) == PA7_NARROW_REVIEW_STATUS_REVIEW_NEEDED else 0,
            _to_int(row.get("row_count")),
            _to_float(row.get("avg_abs_current_profit")),
        ),
        reverse=True,
    )
    primary_row = filtered_rows[0] if filtered_rows else {}

    if not payload and not summary and not rows:
        status = PA7_NARROW_REVIEW_STATUS_NOT_APPLICABLE
        reason_ko = "PA7 review processor artifact가 아직 없어 narrow review lane을 계산하지 않았습니다."
        recommended_next_action = "wait_for_pa7_review_processor_refresh"
    elif not filtered_rows:
        status = PA7_NARROW_REVIEW_STATUS_CLEAR
        reason_ko = "남아 있는 mixed_wait_boundary_review / mixed_review가 없어 narrow review lane이 비어 있습니다."
        recommended_next_action = "continue_first_symbol_closeout_observation"
    elif mixed_wait_count > 0:
        status = PA7_NARROW_REVIEW_STATUS_REVIEW_NEEDED
        reason_ko = "남아 있는 WAIT 경계 혼합 review를 first closeout 전에 좁게 다시 봐야 합니다."
        recommended_next_action = _to_text(
            primary_row.get("recommended_next_action"),
            "review_remaining_mixed_wait_boundary_groups_before_first_closeout",
        )
    else:
        status = PA7_NARROW_REVIEW_STATUS_WATCHLIST
        reason_ko = "남아 있는 mixed review를 watchlist로 두고 first closeout과 함께 추적합니다."
        recommended_next_action = _to_text(
            primary_row.get("recommended_next_action"),
            "keep_watch_on_remaining_mixed_pa7_groups",
        )

    return {
        "status": status,
        "reason_ko": reason_ko,
        "recommended_next_action": recommended_next_action,
        "group_count": len(filtered_rows),
        "mixed_wait_boundary_group_count": mixed_wait_count,
        "mixed_review_group_count": mixed_count,
        "primary_group_key": _to_text(primary_row.get("group_key")),
        "primary_symbol": _to_text(primary_row.get("symbol")),
        "primary_review_disposition": _to_text(primary_row.get("review_disposition")),
        "rows": filtered_rows[:3],
        "source_recommended_next_action": _to_text(summary.get("recommended_next_action")),
    }


def _build_reverse_surface(
    *,
    phase: str,
    degraded_components: list[str],
    runtime_payload: Mapping[str, Any],
    runtime_detail_payload: Mapping[str, Any],
) -> dict[str, Any]:
    phase_upper = _to_text(phase).upper()
    runtime_recycle = _mapping(_mapping(runtime_payload).get("runtime_recycle"))
    runtime_open_positions_count = _to_int(
        runtime_recycle.get("last_open_positions_count"),
        _to_int(_mapping(runtime_payload).get("runtime_open_positions_count")),
    )
    pending_reverse_by_symbol = _mapping(
        runtime_detail_payload.get("pending_reverse_by_symbol")
        or runtime_payload.get("pending_reverse_by_symbol")
    )
    order_block_by_symbol = _mapping(
        runtime_detail_payload.get("order_block_by_symbol")
        or runtime_payload.get("order_block_by_symbol")
    )

    surface_rows: list[dict[str, Any]] = []
    ready_count = 0
    pending_count = 0
    blocked_count = 0
    symbol_keys = sorted(set(pending_reverse_by_symbol) | set(order_block_by_symbol))
    for symbol in symbol_keys:
        pending = _mapping(pending_reverse_by_symbol.get(symbol))
        block = _mapping(order_block_by_symbol.get(symbol))
        if phase_upper in {"DEGRADED", "EMERGENCY"}:
            readiness_status = READINESS_STATUS_BLOCKED
            blocking_reason = "system_phase_degraded"
            blocked_count += 1
        elif block:
            readiness_status = READINESS_STATUS_BLOCKED
            blocking_reason = _to_text(block.get("reason"), "order_block_active")
            blocked_count += 1
        elif pending:
            if runtime_open_positions_count > 0:
                readiness_status = READINESS_STATUS_PENDING_EVIDENCE
                blocking_reason = "managed_position_still_open"
                pending_count += 1
            else:
                readiness_status = READINESS_STATUS_READY_FOR_APPLY
                blocking_reason = "none"
                ready_count += 1
        else:
            readiness_status = READINESS_STATUS_NOT_APPLICABLE
            blocking_reason = "none"
        surface_rows.append(
            {
                "symbol": symbol,
                "readiness_status": readiness_status,
                "blocking_reason": blocking_reason,
                "pending_action": _to_text(pending.get("action")),
                "pending_score": _to_float(pending.get("score")),
                "pending_reason_count": len(list(pending.get("reasons", []) or [])),
                "pending_reasons": list(pending.get("reasons", []) or [])[:3],
                "expires_in_sec": _to_int(pending.get("expires_in_sec")),
                "order_block_reason": _to_text(block.get("reason")),
                "order_block_remaining_sec": _to_int(block.get("remaining_sec")),
            }
        )

    if phase_upper in {"DEGRADED", "EMERGENCY"}:
        overall_status = READINESS_STATUS_BLOCKED
        overall_reason = "system_phase_degraded"
    elif ready_count > 0:
        overall_status = READINESS_STATUS_READY_FOR_APPLY
        overall_reason = "pending_reverse_candidate_ready"
    elif pending_count > 0 or runtime_open_positions_count > 0:
        overall_status = READINESS_STATUS_PENDING_EVIDENCE
        overall_reason = "managed_position_still_open"
    elif blocked_count > 0:
        overall_status = READINESS_STATUS_BLOCKED
        overall_reason = "order_block_active"
    else:
        overall_status = READINESS_STATUS_NOT_APPLICABLE
        overall_reason = "no_reverse_candidate"

    return {
        "readiness_status": overall_status,
        "blocking_reason": overall_reason,
        "runtime_open_positions_count": runtime_open_positions_count,
        "degraded_components": list(degraded_components or []),
        "ready_symbol_count": ready_count,
        "pending_symbol_count": pending_count,
        "blocked_symbol_count": blocked_count,
        "symbols": surface_rows,
    }


def _build_historical_cost_surface(
    *,
    closed_trade_csv_path: str | Path | None,
    recent_limit: int = 30,
) -> dict[str, Any]:
    frame = _load_closed_trade_frame(closed_trade_csv_path)
    if frame.empty:
        return {
            "confidence_level": CONFIDENCE_LEVEL_LIMITED,
            "blocking_reason": "historical_cost_no_recent_closed_trades",
            "note": "최근 마감 거래가 없어 historical cost confidence를 올릴 근거가 없습니다.",
            "recent_trade_count": 0,
            "recent_safe_trade_count": 0,
            "recent_safe_ratio": 0.0,
        }

    recent = frame.tail(max(1, int(recent_limit))).copy()
    profit = _safe_numeric_series(recent, "profit")
    gross = _safe_numeric_series(recent, "gross_pnl")
    cost = _safe_numeric_series(recent, "cost_total")
    net = _safe_numeric_series(recent, "net_pnl_after_cost")
    explicit_cost_mask = (gross.abs() > 1e-12) | (cost.abs() > 1e-12) | (net.abs() > 1e-12)
    legacy_profit_only_mask = (profit.abs() > 1e-12) & ~explicit_cost_mask
    safe_count = int(explicit_cost_mask.sum())
    recent_trade_count = int(len(recent))
    safe_ratio = (safe_count / recent_trade_count) if recent_trade_count else 0.0

    if recent_trade_count > 0 and safe_count == recent_trade_count and not bool(legacy_profit_only_mask.any()):
        confidence_level = CONFIDENCE_LEVEL_MEDIUM
        blocking_reason = "historical_cost_older_rows_may_still_be_limited"
        note = "최근 마감 거래는 비용 메타가 정리되어 있지만, 과거 구간은 여전히 제한적일 수 있습니다."
    elif safe_count > 0:
        confidence_level = CONFIDENCE_LEVEL_LOW
        blocking_reason = "historical_cost_partially_available"
        note = "최근 일부 거래만 비용 메타가 완전합니다. 과거 및 일부 최근 구간은 추정치로 읽어야 합니다."
    else:
        confidence_level = CONFIDENCE_LEVEL_LIMITED
        blocking_reason = "historical_cost_limited"
        note = "최근 마감 거래에도 비용 메타가 충분히 남아 있지 않아 gross/net/cost 분리를 신뢰하기 어렵습니다."

    return {
        "confidence_level": confidence_level,
        "blocking_reason": blocking_reason,
        "note": note,
        "recent_trade_count": recent_trade_count,
        "recent_safe_trade_count": safe_count,
        "recent_safe_ratio": round(safe_ratio, 4),
    }


def build_improvement_readiness_surface(
    *,
    phase: str,
    degraded_components: list[str] | None = None,
    pa8_payload: Mapping[str, Any] | None = None,
    pa7_review_processor_payload: Mapping[str, Any] | None = None,
    pa9_handoff_payload: Mapping[str, Any] | None = None,
    pa9_review_payload: Mapping[str, Any] | None = None,
    pa9_apply_payload: Mapping[str, Any] | None = None,
    runtime_status_payload: Mapping[str, Any] | None = None,
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
    runtime_status_path: str | Path | None = None,
    closed_trade_csv_path: str | Path | None = None,
    output_json_path: str | Path | None = None,
    output_markdown_path: str | Path | None = None,
    now_ts: object | None = None,
) -> dict[str, Any]:
    run_at = _to_text(now_ts, _now_iso())
    runtime_payload = _mapping(runtime_status_payload)
    runtime_detail_payload = (
        _mapping(runtime_status_detail_payload)
        if runtime_status_detail_payload is not None
        else _load_runtime_status_detail_payload(
            runtime_status_path=runtime_status_path,
            runtime_status_payload=runtime_payload,
        )
    )
    pa8_surface = _build_pa8_closeout_surface(
        pa8_payload=_mapping(pa8_payload),
        phase=phase,
    )
    pa9_surface = _build_pa9_handoff_surface(
        handoff_payload=_mapping(pa9_handoff_payload),
        review_payload=_mapping(pa9_review_payload),
        apply_payload=_mapping(pa9_apply_payload),
    )
    pa8_focus_surface = _build_pa8_closeout_focus_surface(
        phase=phase,
        pa8_surface=pa8_surface,
        pa9_surface=pa9_surface,
    )
    first_symbol_surface = _build_first_symbol_closeout_handoff_surface(
        phase=phase,
        pa8_focus_surface=pa8_focus_surface,
        pa9_surface=pa9_surface,
    )
    pa7_narrow_review_surface = _build_pa7_narrow_review_surface(
        pa7_review_processor_payload=_mapping(pa7_review_processor_payload),
    )
    reverse_surface = _build_reverse_surface(
        phase=phase,
        degraded_components=list(degraded_components or []),
        runtime_payload=runtime_payload,
        runtime_detail_payload=runtime_detail_payload,
    )
    historical_cost_surface = _build_historical_cost_surface(
        closed_trade_csv_path=closed_trade_csv_path,
    )

    payload = {
        "summary": {
            "contract_version": IMPROVEMENT_READINESS_SURFACE_CONTRACT_VERSION,
            "generated_at": run_at,
            "phase": _to_text(phase),
            "pa8_closeout_readiness_status": pa8_surface["readiness_status"],
            "pa8_closeout_focus_status": pa8_focus_surface["focus_status"],
            "pa9_handoff_readiness_status": pa9_surface["readiness_status"],
            "reverse_readiness_status": reverse_surface["readiness_status"],
            "historical_cost_confidence_level": historical_cost_surface["confidence_level"],
            "pa8_ready_symbol_count": pa8_surface["ready_symbol_count"],
            "pa8_pending_symbol_count": pa8_surface["pending_symbol_count"],
            "pa8_focus_symbol_count": pa8_focus_surface["focus_symbol_count"],
            "pa8_primary_focus_symbol": pa8_focus_surface["primary_focus_symbol"],
            "first_symbol_closeout_handoff_status": first_symbol_surface["observation_status"],
            "first_symbol_closeout_handoff_symbol": first_symbol_surface["primary_symbol"],
            "pa9_ready_for_review_symbol_count": pa9_surface["ready_for_review_symbol_count"],
            "pa9_ready_for_apply_symbol_count": pa9_surface["ready_for_apply_symbol_count"],
            "pa7_narrow_review_status": pa7_narrow_review_surface["status"],
            "pa7_narrow_review_group_count": pa7_narrow_review_surface["group_count"],
            "reverse_ready_symbol_count": reverse_surface["ready_symbol_count"],
            "reverse_pending_symbol_count": reverse_surface["pending_symbol_count"],
            "reverse_blocked_symbol_count": reverse_surface["blocked_symbol_count"],
            "historical_cost_recent_trade_count": historical_cost_surface["recent_trade_count"],
            "historical_cost_recent_safe_trade_count": historical_cost_surface["recent_safe_trade_count"],
        },
        "pa8_closeout_surface": pa8_surface,
        "pa8_closeout_focus_surface": pa8_focus_surface,
        "first_symbol_closeout_handoff_surface": first_symbol_surface,
        "pa9_handoff_surface": pa9_surface,
        "pa7_narrow_review_surface": pa7_narrow_review_surface,
        "reverse_surface": reverse_surface,
        "historical_cost_surface": historical_cost_surface,
        "artifacts": {
            "runtime_status_path": str(runtime_status_path or ""),
            "closed_trade_csv_path": str(closed_trade_csv_path or default_closed_trade_csv_path()),
        },
    }

    if output_json_path or output_markdown_path:
        json_path = Path(output_json_path or default_improvement_readiness_surface_json_path())
        markdown_path = Path(output_markdown_path or default_improvement_readiness_surface_markdown_path())
        _write_json(json_path, payload)
        _write_text(markdown_path, render_improvement_readiness_surface_markdown(payload))
    return payload


def build_pnl_readiness_digest_lines(
    readiness_surface_payload: Mapping[str, Any] | None,
) -> list[str]:
    payload = _mapping(readiness_surface_payload)
    pa8_surface = _mapping(payload.get("pa8_closeout_surface"))
    pa9_surface = _mapping(payload.get("pa9_handoff_surface"))
    reverse_surface = _mapping(payload.get("reverse_surface"))
    historical_cost_surface = _mapping(payload.get("historical_cost_surface"))

    lines = [
        "━━ 시스템 상태 ━━",
        "PA8 closeout: "
        + f"{_to_text(pa8_surface.get('readiness_status'), '-')}"
        + f" (준비 { _to_int(pa8_surface.get('ready_symbol_count')) } / 활성 { _to_int(pa8_surface.get('active_symbol_count')) })",
        "first symbol: "
        + f"{_to_text(first_symbol_surface.get('observation_status'), '-')}"
        + f" ({_to_text(first_symbol_surface.get('primary_symbol'), '-')} / {_to_text(first_symbol_surface.get('observation_stage'), '-')})",
        "PA9 handoff: "
        + f"{_to_text(pa9_surface.get('readiness_status'), '-')}"
        + f" (review { _to_int(pa9_surface.get('ready_for_review_symbol_count')) } / apply { _to_int(pa9_surface.get('ready_for_apply_symbol_count')) })",
        "PA7 narrow review: "
        + f"{_to_text(pa7_narrow_review_surface.get('status'), '-')}"
        + f" (remaining { _to_int(pa7_narrow_review_surface.get('group_count')) } / primary { _to_text(pa7_narrow_review_surface.get('primary_symbol'), '-') })",
        "reverse readiness: "
        + f"{_to_text(reverse_surface.get('readiness_status'), '-')}"
        + f" (pending { _to_int(reverse_surface.get('pending_symbol_count')) } / blocked { _to_int(reverse_surface.get('blocked_symbol_count')) } / ready { _to_int(reverse_surface.get('ready_symbol_count')) })",
        "historical cost: "
        + f"{_to_text(historical_cost_surface.get('confidence_level'), '-')}"
        + f" (최근 { _to_int(historical_cost_surface.get('recent_safe_trade_count')) } / { _to_int(historical_cost_surface.get('recent_trade_count')) }건 안전)",
    ]
    return lines


def render_improvement_readiness_surface_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    pa8_surface = _mapping(payload.get("pa8_closeout_surface"))
    pa9_surface = _mapping(payload.get("pa9_handoff_surface"))
    reverse_surface = _mapping(payload.get("reverse_surface"))
    historical_cost_surface = _mapping(payload.get("historical_cost_surface"))

    lines: list[str] = []
    lines.append("# Improvement Readiness Surface")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in (
        "phase",
        "pa8_closeout_readiness_status",
        "pa9_handoff_readiness_status",
        "reverse_readiness_status",
        "historical_cost_confidence_level",
        "pa8_ready_symbol_count",
        "pa8_pending_symbol_count",
        "pa9_ready_for_review_symbol_count",
        "pa9_ready_for_apply_symbol_count",
        "reverse_pending_symbol_count",
        "reverse_blocked_symbol_count",
        "reverse_ready_symbol_count",
        "historical_cost_recent_trade_count",
        "historical_cost_recent_safe_trade_count",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## PA8 Closeout")
    lines.append("")
    lines.append(f"- readiness_status: `{pa8_surface.get('readiness_status')}`")
    lines.append(f"- blocking_reason: `{pa8_surface.get('blocking_reason')}`")
    lines.append(f"- recommended_next_action: `{pa8_surface.get('recommended_next_action')}`")
    for row in list(pa8_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` status=`{row_map.get('readiness_status')}` rows=`{row_map.get('observed_window_row_count')}` triggers=`{row_map.get('active_trigger_count')}`"
        )
    lines.append("")
    lines.append("## PA9 Handoff")
    lines.append("")
    lines.append(f"- readiness_status: `{pa9_surface.get('readiness_status')}`")
    lines.append(f"- blocking_reason: `{pa9_surface.get('blocking_reason')}`")
    lines.append(f"- handoff_state: `{pa9_surface.get('handoff_state')}`")
    lines.append(f"- review_state: `{pa9_surface.get('review_state')}`")
    lines.append(f"- apply_state: `{pa9_surface.get('apply_state')}`")
    for row in list(pa9_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` status=`{row_map.get('readiness_status')}` review=`{row_map.get('handoff_review_candidate')}` apply=`{row_map.get('handoff_apply_candidate')}`"
        )
    lines.append("")
    lines.append("## Reverse")
    lines.append("")
    lines.append(f"- readiness_status: `{reverse_surface.get('readiness_status')}`")
    lines.append(f"- blocking_reason: `{reverse_surface.get('blocking_reason')}`")
    lines.append(f"- runtime_open_positions_count: `{reverse_surface.get('runtime_open_positions_count')}`")
    for row in list(reverse_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` status=`{row_map.get('readiness_status')}` pending_action=`{row_map.get('pending_action')}` block=`{row_map.get('order_block_reason')}`"
        )
    lines.append("")
    lines.append("## Historical Cost")
    lines.append("")
    for key in (
        "confidence_level",
        "blocking_reason",
        "recent_trade_count",
        "recent_safe_trade_count",
        "recent_safe_ratio",
        "note",
    ):
        lines.append(f"- {key}: `{historical_cost_surface.get(key)}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_pnl_readiness_digest_lines(
    readiness_surface_payload: Mapping[str, Any] | None,
) -> list[str]:
    payload = _mapping(readiness_surface_payload)
    pa8_surface = _mapping(payload.get("pa8_closeout_surface"))
    pa8_focus_surface = _mapping(payload.get("pa8_closeout_focus_surface"))
    first_symbol_surface = _mapping(payload.get("first_symbol_closeout_handoff_surface"))
    pa9_surface = _mapping(payload.get("pa9_handoff_surface"))
    pa7_narrow_review_surface = _mapping(payload.get("pa7_narrow_review_surface"))
    reverse_surface = _mapping(payload.get("reverse_surface"))
    historical_cost_surface = _mapping(payload.get("historical_cost_surface"))

    return [
        "━━ 시스템 상태 ━━",
        "PA8 closeout: "
        + f"{_to_text(pa8_surface.get('readiness_status'), '-')}"
        + f" (준비 { _to_int(pa8_surface.get('ready_symbol_count')) } / 활성 { _to_int(pa8_surface.get('active_symbol_count')) })",
        "PA8 focus: "
        + f"{_to_text(pa8_focus_surface.get('focus_status'), '-')}"
        + f" (집중 { _to_int(pa8_focus_surface.get('focus_symbol_count')) } / watchlist { _to_int(pa8_focus_surface.get('watchlist_symbol_count')) } / primary { _to_text(pa8_focus_surface.get('primary_focus_symbol'), '-') })",
        "first symbol: "
        + f"{_to_text(first_symbol_surface.get('observation_status'), '-')}"
        + f" ({_to_text(first_symbol_surface.get('primary_symbol'), '-')} / {_to_text(first_symbol_surface.get('observation_stage'), '-')})",
        "PA9 handoff: "
        + f"{_to_text(pa9_surface.get('readiness_status'), '-')}"
        + f" (review { _to_int(pa9_surface.get('ready_for_review_symbol_count')) } / apply { _to_int(pa9_surface.get('ready_for_apply_symbol_count')) })",
        "PA7 narrow review: "
        + f"{_to_text(pa7_narrow_review_surface.get('status'), '-')}"
        + f" (remaining { _to_int(pa7_narrow_review_surface.get('group_count')) } / primary { _to_text(pa7_narrow_review_surface.get('primary_symbol'), '-') })",
        "reverse readiness: "
        + f"{_to_text(reverse_surface.get('readiness_status'), '-')}"
        + f" (pending { _to_int(reverse_surface.get('pending_symbol_count')) } / blocked { _to_int(reverse_surface.get('blocked_symbol_count')) } / ready { _to_int(reverse_surface.get('ready_symbol_count')) })",
        "historical cost: "
        + f"{_to_text(historical_cost_surface.get('confidence_level'), '-')}"
        + f" (최근 { _to_int(historical_cost_surface.get('recent_safe_trade_count')) } / { _to_int(historical_cost_surface.get('recent_trade_count')) }건 안전)",
    ]


def render_improvement_readiness_surface_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    pa8_surface = _mapping(payload.get("pa8_closeout_surface"))
    pa8_focus_surface = _mapping(payload.get("pa8_closeout_focus_surface"))
    first_symbol_surface = _mapping(payload.get("first_symbol_closeout_handoff_surface"))
    pa9_surface = _mapping(payload.get("pa9_handoff_surface"))
    pa7_narrow_review_surface = _mapping(payload.get("pa7_narrow_review_surface"))
    reverse_surface = _mapping(payload.get("reverse_surface"))
    historical_cost_surface = _mapping(payload.get("historical_cost_surface"))

    lines: list[str] = []
    lines.append("# Improvement Readiness Surface")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in (
        "phase",
        "pa8_closeout_readiness_status",
        "pa8_closeout_focus_status",
        "pa9_handoff_readiness_status",
        "reverse_readiness_status",
        "historical_cost_confidence_level",
        "pa8_ready_symbol_count",
        "pa8_pending_symbol_count",
        "pa8_focus_symbol_count",
        "pa8_primary_focus_symbol",
        "first_symbol_closeout_handoff_status",
        "first_symbol_closeout_handoff_symbol",
        "pa9_ready_for_review_symbol_count",
        "pa9_ready_for_apply_symbol_count",
        "pa7_narrow_review_status",
        "pa7_narrow_review_group_count",
        "reverse_pending_symbol_count",
        "reverse_blocked_symbol_count",
        "reverse_ready_symbol_count",
        "historical_cost_recent_trade_count",
        "historical_cost_recent_safe_trade_count",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## PA8 Closeout")
    lines.append("")
    lines.append(f"- readiness_status: `{pa8_surface.get('readiness_status')}`")
    lines.append(f"- blocking_reason: `{pa8_surface.get('blocking_reason')}`")
    lines.append(f"- recommended_next_action: `{pa8_surface.get('recommended_next_action')}`")
    for row in list(pa8_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` status=`{row_map.get('readiness_status')}` rows=`{row_map.get('observed_window_row_count')}` triggers=`{row_map.get('active_trigger_count')}`"
        )
    lines.append("")
    lines.append("## PA8 Closeout Focus")
    lines.append("")
    for key in (
        "focus_status",
        "blocking_reason",
        "focus_symbol_count",
        "concentrated_symbol_count",
        "watchlist_symbol_count",
        "primary_focus_symbol",
        "primary_focus_reason_ko",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{pa8_focus_surface.get(key)}`")
    for row in list(pa8_focus_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` focus=`{row_map.get('focus_status')}` progress=`{row_map.get('window_progress_ratio')}` reason=`{row_map.get('focus_reason_ko')}`"
        )
    lines.append("")
    lines.append("## First Symbol Closeout/Handoff")
    lines.append("")
    for key in (
        "observation_status",
        "observation_stage",
        "primary_symbol",
        "reason_ko",
        "recommended_next_action",
        "focus_progress_ratio",
        "observed_window_row_count",
        "sample_floor",
        "active_trigger_count",
        "handoff_review_candidate",
        "handoff_apply_candidate",
    ):
        lines.append(f"- {key}: `{first_symbol_surface.get(key)}`")
    lines.append("")
    lines.append("## PA9 Handoff")
    lines.append("")
    lines.append(f"- readiness_status: `{pa9_surface.get('readiness_status')}`")
    lines.append(f"- blocking_reason: `{pa9_surface.get('blocking_reason')}`")
    lines.append(f"- handoff_state: `{pa9_surface.get('handoff_state')}`")
    lines.append(f"- review_state: `{pa9_surface.get('review_state')}`")
    lines.append(f"- apply_state: `{pa9_surface.get('apply_state')}`")
    for row in list(pa9_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` status=`{row_map.get('readiness_status')}` review=`{row_map.get('handoff_review_candidate')}` apply=`{row_map.get('handoff_apply_candidate')}`"
        )
    lines.append("")
    lines.append("## PA7 Narrow Review Lane")
    lines.append("")
    for key in (
        "status",
        "reason_ko",
        "recommended_next_action",
        "group_count",
        "mixed_wait_boundary_group_count",
        "mixed_review_group_count",
        "primary_group_key",
        "primary_symbol",
        "primary_review_disposition",
    ):
        lines.append(f"- {key}: `{pa7_narrow_review_surface.get(key)}`")
    for row in list(pa7_narrow_review_surface.get("rows", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` lane=`{row_map.get('lane_status')}` disposition=`{row_map.get('review_disposition')}` rows=`{row_map.get('row_count')}` key=`{row_map.get('group_key')}`"
        )
    lines.append("")
    lines.append("## Reverse")
    lines.append("")
    lines.append(f"- readiness_status: `{reverse_surface.get('readiness_status')}`")
    lines.append(f"- blocking_reason: `{reverse_surface.get('blocking_reason')}`")
    lines.append(f"- runtime_open_positions_count: `{reverse_surface.get('runtime_open_positions_count')}`")
    for row in list(reverse_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` status=`{row_map.get('readiness_status')}` pending_action=`{row_map.get('pending_action')}` block=`{row_map.get('order_block_reason')}`"
        )
    lines.append("")
    lines.append("## Historical Cost")
    lines.append("")
    for key in (
        "confidence_level",
        "blocking_reason",
        "recent_trade_count",
        "recent_safe_trade_count",
        "recent_safe_ratio",
        "note",
    ):
        lines.append(f"- {key}: `{historical_cost_surface.get(key)}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"
