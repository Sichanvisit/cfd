"""Validate NAS/XAU upper-reversal sell rows against breakout-up conflict correction."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt
from backend.services.wrong_side_conflict_replay_harness import (
    build_wrong_side_conflict_replay_harness,
)


UPPER_REVERSAL_BREAKOUT_CONFLICT_VALIDATION_VERSION = (
    "upper_reversal_breakout_conflict_validation_v1"
)
DEFAULT_UPPER_REVERSAL_BREAKOUT_SYMBOLS = ("XAUUSD", "NAS100", "BTCUSD")
DEFAULT_UPPER_REVERSAL_SETUP_IDS = ("range_upper_reversal_sell",)
DEFAULT_UPPER_REVERSAL_SETUP_REASON_TOKENS = (
    "shadow_upper_break_fail_confirm",
    "shadow_upper_reject_probe_observe",
    "shadow_upper_reject_confirm",
)

REQUIRED_UPPER_REVERSAL_BREAKOUT_FIELDS = (
    "breakout_candidate_direction",
    "breakout_candidate_action_target",
    "active_action_conflict_detected",
    "active_action_conflict_guard_applied",
    "active_action_conflict_resolution_state",
    "active_action_conflict_kind",
    "active_action_conflict_precedence_owner",
    "active_action_conflict_breakout_direction",
    "active_action_conflict_breakout_target",
    "entry_candidate_bridge_mode",
    "entry_candidate_bridge_conflict_selected",
    "entry_candidate_bridge_action",
)

UPPER_REVERSAL_BREAKOUT_CONFLICT_VALIDATION_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "scope_bucket",
    "symbol",
    "time",
    "action",
    "outcome",
    "setup_id",
    "setup_reason",
    "target_family_match",
    "baseline_sell_context",
    "breakout_direction",
    "breakout_action_target",
    "countertrend_action_state",
    "countertrend_directional_candidate_action",
    "active_action_conflict_detected",
    "active_action_conflict_guard_applied",
    "active_action_conflict_resolution_state",
    "active_action_conflict_kind",
    "active_action_conflict_precedence_owner",
    "entry_candidate_bridge_mode",
    "entry_candidate_bridge_conflict_selected",
    "entry_candidate_bridge_action",
    "validation_note",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _to_bool(value: object) -> bool:
    return _to_text(value).lower() in {"1", "true", "yes", "y"}


def _series_counts(values: pd.Series) -> dict[str, int]:
    if values.empty:
        return {}
    series = values.fillna("").astype(str).str.strip().replace("", pd.NA).dropna()
    return {str(key): int(value) for key, value in series.value_counts().to_dict().items()}


def _json_counts(counts: Mapping[str, int]) -> str:
    return (
        json.dumps(
            {str(k): int(v) for k, v in counts.items()},
            ensure_ascii=False,
            sort_keys=True,
        )
        if counts
        else "{}"
    )


def _ensure_columns(frame: pd.DataFrame) -> pd.DataFrame:
    local = frame.copy()
    for column in (
        "time",
        "symbol",
        "action",
        "outcome",
        "setup_id",
        "setup_reason",
        "blocked_by",
        "action_none_reason",
        "breakout_candidate_direction",
        "breakout_candidate_action_target",
        "countertrend_action_state",
        "countertrend_directional_candidate_action",
        "active_action_conflict_detected",
        "active_action_conflict_guard_applied",
        "active_action_conflict_resolution_state",
        "active_action_conflict_kind",
        "active_action_conflict_precedence_owner",
        "active_action_conflict_breakout_direction",
        "active_action_conflict_breakout_target",
        "active_action_conflict_baseline_action",
        "entry_candidate_bridge_mode",
        "entry_candidate_bridge_conflict_selected",
        "entry_candidate_bridge_action",
        "entry_candidate_bridge_effective_baseline_action",
    ):
        if column not in local.columns:
            local[column] = ""
    return local


def _target_family_mask(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)
    symbols = frame["symbol"].fillna("").astype(str).str.upper()
    setup_ids = frame["setup_id"].fillna("").astype(str).str.lower()
    setup_reasons = frame["setup_reason"].fillna("").astype(str).str.lower()
    breakout_direction = (
        frame["breakout_candidate_direction"].fillna("").astype(str).str.upper()
    )
    conflict_breakout_direction = (
        frame["active_action_conflict_breakout_direction"]
        .fillna("")
        .astype(str)
        .str.upper()
    )
    baseline_context = pd.Series(False, index=frame.index)
    for column in (
        "action",
        "active_action_conflict_baseline_action",
        "entry_candidate_bridge_effective_baseline_action",
    ):
        series = frame[column].fillna("").astype(str).str.upper()
        baseline_context = baseline_context | series.eq("SELL")
    id_match = setup_ids.isin({value.lower() for value in DEFAULT_UPPER_REVERSAL_SETUP_IDS})
    reason_match = pd.Series(False, index=frame.index)
    for token in DEFAULT_UPPER_REVERSAL_SETUP_REASON_TOKENS:
        reason_match = reason_match | setup_reasons.str.contains(token.lower(), regex=False)
    symbol_match = symbols.isin({value.upper() for value in DEFAULT_UPPER_REVERSAL_BREAKOUT_SYMBOLS})
    breakout_up = breakout_direction.eq("UP") | conflict_breakout_direction.eq("UP")
    return symbol_match & (id_match | reason_match) & breakout_up & baseline_context


def _recommended_next_action(
    *,
    field_presence_ok: bool,
    fresh_symbol_row_count: int,
    fresh_target_family_row_count: int,
    live_guard_applied_count: int,
    live_bridge_conflict_selected_count: int,
    replay_target_row_count: int,
    replay_guard_applied_count: int,
    live_residual_entered_sell_count: int,
) -> str:
    if not field_presence_ok:
        return "repair_upper_reversal_conflict_runtime_schema_or_restart_core"
    if replay_target_row_count <= 0:
        return "await_upper_reversal_breakout_conflict_rows"
    if fresh_symbol_row_count <= 0:
        return "await_fresh_nas_xau_rows"
    if fresh_target_family_row_count <= 0:
        return "await_fresh_upper_reversal_breakout_conflict_rows"
    if live_guard_applied_count <= 0 and replay_guard_applied_count > 0:
        return "await_fresh_post_restart_upper_reversal_conflict_rows"
    if live_guard_applied_count > 0 and live_residual_entered_sell_count > 0:
        return "inspect_breakout_execution_precedence_scope_gap"
    if live_guard_applied_count > 0 or live_bridge_conflict_selected_count > 0:
        return "proceed_to_mf17_signoff_after_p0e_validation"
    return "inspect_upper_reversal_breakout_conflict_guard"


def build_upper_reversal_breakout_conflict_validation(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    recent_limit: int = 240,
    replay_recent_limit: int = 1200,
    replay_result: tuple[pd.DataFrame, Mapping[str, Any]] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    frame = (
        entry_decisions.copy()
        if entry_decisions is not None and not entry_decisions.empty
        else pd.DataFrame()
    )

    summary: dict[str, Any] = {
        "contract_version": UPPER_REVERSAL_BREAKOUT_CONFLICT_VALIDATION_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "recent_row_count": 0,
        "fresh_symbol_row_count": 0,
        "fresh_target_family_row_count": 0,
        "field_presence_ok": False,
        "field_presence_missing": list(REQUIRED_UPPER_REVERSAL_BREAKOUT_FIELDS),
        "live_conflict_detected_count": 0,
        "live_guard_applied_count": 0,
        "live_bridge_conflict_selected_count": 0,
        "live_residual_entered_sell_count": 0,
        "live_precedence_owner_counts": "{}",
        "live_resolution_state_counts": "{}",
        "live_breakout_target_counts": "{}",
        "live_bridge_mode_counts": "{}",
        "replay_target_row_count": 0,
        "replay_guard_applied_count": 0,
        "replay_bridge_conflict_selected_count": 0,
        "replay_symbol_counts": "{}",
        "replay_bridge_mode_counts": "{}",
        "recommended_next_action": "repair_upper_reversal_conflict_runtime_schema_or_restart_core",
    }
    if frame.empty:
        return pd.DataFrame(columns=UPPER_REVERSAL_BREAKOUT_CONFLICT_VALIDATION_COLUMNS), summary

    decisions = _ensure_columns(frame)
    decisions["__time_sort"] = pd.to_datetime(decisions["time"], errors="coerce")
    decisions = decisions.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    recent = decisions.head(max(1, int(recent_limit))).copy()
    summary["recent_row_count"] = int(len(recent))

    required_missing = [
        field for field in REQUIRED_UPPER_REVERSAL_BREAKOUT_FIELDS if field not in recent.columns
    ]
    field_presence_ok = len(required_missing) == 0
    summary["field_presence_ok"] = bool(field_presence_ok)
    summary["field_presence_missing"] = required_missing

    fresh_symbol_frame = recent.loc[
        recent["symbol"].fillna("").astype(str).str.upper().isin(
            {value.upper() for value in DEFAULT_UPPER_REVERSAL_BREAKOUT_SYMBOLS}
        )
    ].copy()
    summary["fresh_symbol_row_count"] = int(len(fresh_symbol_frame))

    fresh_symbol_frame["target_family_match"] = _target_family_mask(fresh_symbol_frame)
    target_frame = fresh_symbol_frame.loc[fresh_symbol_frame["target_family_match"]].copy()
    summary["fresh_target_family_row_count"] = int(len(target_frame))

    if replay_result is None:
        replay_frame, replay_summary = build_wrong_side_conflict_replay_harness(
            entry_decisions,
            recent_limit=max(1, int(replay_recent_limit)),
        )
    else:
        replay_frame, replay_summary = replay_result
    replay_summary = dict(replay_summary or {})
    summary["replay_target_row_count"] = int(_to_float(replay_summary.get("target_row_count")))
    summary["replay_guard_applied_count"] = int(
        _to_float(replay_summary.get("replay_guard_applied_count"))
    )
    summary["replay_bridge_conflict_selected_count"] = int(
        _to_float(replay_summary.get("replay_bridge_conflict_selected_count"))
    )
    summary["replay_symbol_counts"] = _to_text(replay_summary.get("symbol_counts"), "{}")
    summary["replay_bridge_mode_counts"] = _to_text(
        replay_summary.get("replay_bridge_mode_counts"),
        "{}",
    )

    if target_frame.empty:
        summary["recommended_next_action"] = _recommended_next_action(
            field_presence_ok=field_presence_ok,
            fresh_symbol_row_count=int(len(fresh_symbol_frame)),
            fresh_target_family_row_count=0,
            live_guard_applied_count=0,
            live_bridge_conflict_selected_count=0,
            replay_target_row_count=summary["replay_target_row_count"],
            replay_guard_applied_count=summary["replay_guard_applied_count"],
            live_residual_entered_sell_count=0,
        )
        return pd.DataFrame(columns=UPPER_REVERSAL_BREAKOUT_CONFLICT_VALIDATION_COLUMNS), summary

    conflict_detected = target_frame["active_action_conflict_detected"].map(_to_bool)
    guard_applied = target_frame["active_action_conflict_guard_applied"].map(_to_bool)
    bridge_conflict_selected = target_frame["entry_candidate_bridge_conflict_selected"].map(
        _to_bool
    )
    bridge_mode_series = (
        target_frame["entry_candidate_bridge_mode"].fillna("").astype(str).str.strip()
    )
    residual_entered_sell_mask = (
        target_frame["action"].fillna("").astype(str).str.upper().eq("SELL")
        & target_frame["outcome"].fillna("").astype(str).str.lower().eq("entered")
        & (~guard_applied)
    )

    summary["live_conflict_detected_count"] = int(conflict_detected.sum())
    summary["live_guard_applied_count"] = int(guard_applied.sum())
    summary["live_bridge_conflict_selected_count"] = int(
        bridge_conflict_selected.sum()
        + (
            bridge_mode_series.eq("active_action_conflict_resolution")
            & target_frame["entry_candidate_bridge_action"]
            .fillna("")
            .astype(str)
            .str.upper()
            .isin({"BUY", "SELL"})
        ).sum()
    )
    summary["live_residual_entered_sell_count"] = int(residual_entered_sell_mask.sum())
    summary["live_precedence_owner_counts"] = _json_counts(
        _series_counts(target_frame["active_action_conflict_precedence_owner"])
    )
    summary["live_resolution_state_counts"] = _json_counts(
        _series_counts(target_frame["active_action_conflict_resolution_state"])
    )
    summary["live_breakout_target_counts"] = _json_counts(
        _series_counts(target_frame["breakout_candidate_action_target"])
    )
    summary["live_bridge_mode_counts"] = _json_counts(_series_counts(bridge_mode_series))
    summary["recommended_next_action"] = _recommended_next_action(
        field_presence_ok=field_presence_ok,
        fresh_symbol_row_count=int(len(fresh_symbol_frame)),
        fresh_target_family_row_count=int(len(target_frame)),
        live_guard_applied_count=int(summary["live_guard_applied_count"]),
        live_bridge_conflict_selected_count=int(summary["live_bridge_conflict_selected_count"]),
        replay_target_row_count=int(summary["replay_target_row_count"]),
        replay_guard_applied_count=int(summary["replay_guard_applied_count"]),
        live_residual_entered_sell_count=int(summary["live_residual_entered_sell_count"]),
    )

    rows: list[dict[str, Any]] = []
    for _, row in target_frame.iterrows():
        note_parts: list[str] = ["target_family"]
        if _to_bool(row.get("active_action_conflict_detected")):
            note_parts.append("conflict_detected")
        if _to_bool(row.get("active_action_conflict_guard_applied")):
            note_parts.append("guard_applied")
        bridge_mode = _to_text(row.get("entry_candidate_bridge_mode"))
        if bridge_mode:
            note_parts.append(bridge_mode)
        if _to_bool(row.get("entry_candidate_bridge_conflict_selected")):
            note_parts.append("bridge_conflict_selected")
        if (
            _to_text(row.get("action")).upper() == "SELL"
            and _to_text(row.get("outcome")).lower() == "entered"
            and not _to_bool(row.get("active_action_conflict_guard_applied"))
        ):
            note_parts.append("residual_entered_sell")

        baseline_context = _to_text(
            row.get("active_action_conflict_baseline_action")
            or row.get("entry_candidate_bridge_effective_baseline_action")
            or row.get("action")
        ).upper()
        breakout_direction = _to_text(
            row.get("active_action_conflict_breakout_direction")
            or row.get("breakout_candidate_direction")
        ).upper()
        breakout_target = _to_text(
            row.get("active_action_conflict_breakout_target")
            or row.get("breakout_candidate_action_target")
        ).upper()
        event_time = _to_text(row.get("time"))

        rows.append(
            {
                "observation_event_id": (
                    f"{UPPER_REVERSAL_BREAKOUT_CONFLICT_VALIDATION_VERSION}:"
                    f"{_to_text(row.get('symbol')).upper()}:{event_time.replace(':', '').replace('-', '')}"
                ),
                "generated_at": generated_at,
                "runtime_updated_at": _to_text(runtime.get("updated_at")),
                "scope_bucket": "fresh_target_slice",
                "symbol": _to_text(row.get("symbol")).upper(),
                "time": event_time,
                "action": _to_text(row.get("action")).upper(),
                "outcome": _to_text(row.get("outcome")),
                "setup_id": _to_text(row.get("setup_id")),
                "setup_reason": _to_text(row.get("setup_reason")),
                "target_family_match": bool(row.get("target_family_match", False)),
                "baseline_sell_context": baseline_context,
                "breakout_direction": breakout_direction,
                "breakout_action_target": breakout_target,
                "countertrend_action_state": _to_text(row.get("countertrend_action_state")).upper(),
                "countertrend_directional_candidate_action": _to_text(
                    row.get("countertrend_directional_candidate_action")
                ).upper(),
                "active_action_conflict_detected": bool(
                    _to_bool(row.get("active_action_conflict_detected"))
                ),
                "active_action_conflict_guard_applied": bool(
                    _to_bool(row.get("active_action_conflict_guard_applied"))
                ),
                "active_action_conflict_resolution_state": _to_text(
                    row.get("active_action_conflict_resolution_state")
                ).upper(),
                "active_action_conflict_kind": _to_text(
                    row.get("active_action_conflict_kind")
                ),
                "active_action_conflict_precedence_owner": _to_text(
                    row.get("active_action_conflict_precedence_owner")
                ),
                "entry_candidate_bridge_mode": bridge_mode,
                "entry_candidate_bridge_conflict_selected": bool(
                    _to_bool(row.get("entry_candidate_bridge_conflict_selected"))
                ),
                "entry_candidate_bridge_action": _to_text(
                    row.get("entry_candidate_bridge_action")
                ).upper(),
                "validation_note": "|".join(note_parts),
            }
        )

    return pd.DataFrame(rows, columns=UPPER_REVERSAL_BREAKOUT_CONFLICT_VALIDATION_COLUMNS), summary


def render_upper_reversal_breakout_conflict_validation_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> str:
    payload = dict(summary or {})
    rows = frame.copy() if frame is not None and not frame.empty else pd.DataFrame()
    lines = [
        "# Upper-Reversal Breakout Conflict Validation",
        "",
        f"- generated_at: `{_to_text(payload.get('generated_at'))}`",
        f"- runtime_updated_at: `{_to_text(payload.get('runtime_updated_at'))}`",
        f"- recent_row_count: `{int(payload.get('recent_row_count') or 0)}`",
        f"- fresh_symbol_row_count: `{int(payload.get('fresh_symbol_row_count') or 0)}`",
        f"- fresh_target_family_row_count: `{int(payload.get('fresh_target_family_row_count') or 0)}`",
        f"- live_conflict_detected_count: `{int(payload.get('live_conflict_detected_count') or 0)}`",
        f"- live_guard_applied_count: `{int(payload.get('live_guard_applied_count') or 0)}`",
        f"- live_bridge_conflict_selected_count: `{int(payload.get('live_bridge_conflict_selected_count') or 0)}`",
        f"- live_residual_entered_sell_count: `{int(payload.get('live_residual_entered_sell_count') or 0)}`",
        f"- replay_target_row_count: `{int(payload.get('replay_target_row_count') or 0)}`",
        f"- replay_guard_applied_count: `{int(payload.get('replay_guard_applied_count') or 0)}`",
        f"- replay_bridge_conflict_selected_count: `{int(payload.get('replay_bridge_conflict_selected_count') or 0)}`",
        f"- field_presence_ok: `{bool(payload.get('field_presence_ok'))}`",
        f"- recommended_next_action: `{_to_text(payload.get('recommended_next_action'))}`",
        "",
        "## Live Counts",
        "",
        f"- live_precedence_owner_counts: `{_to_text(payload.get('live_precedence_owner_counts'), '{}')}`",
        f"- live_resolution_state_counts: `{_to_text(payload.get('live_resolution_state_counts'), '{}')}`",
        f"- live_breakout_target_counts: `{_to_text(payload.get('live_breakout_target_counts'), '{}')}`",
        f"- live_bridge_mode_counts: `{_to_text(payload.get('live_bridge_mode_counts'), '{}')}`",
        "",
        "## Replay Counts",
        "",
        f"- replay_symbol_counts: `{_to_text(payload.get('replay_symbol_counts'), '{}')}`",
        f"- replay_bridge_mode_counts: `{_to_text(payload.get('replay_bridge_mode_counts'), '{}')}`",
    ]
    if rows.empty:
        lines.extend(["", "## Fresh Target Rows", "", "- no rows materialized"])
        return "\n".join(lines) + "\n"

    lines.extend(["", "## Fresh Target Rows", ""])
    for _, row in rows.head(12).iterrows():
        lines.append(
            "- "
            + f"{_to_text(row.get('time'))} | `{_to_text(row.get('symbol'))}` | "
            + f"`{_to_text(row.get('setup_id'))}` | "
            + f"breakout={_to_text(row.get('breakout_action_target')) or 'NONE'} | "
            + f"guard={_to_text(row.get('active_action_conflict_guard_applied'))} | "
            + f"bridge={_to_text(row.get('entry_candidate_bridge_mode')) or 'NONE'} | "
            + f"note={_to_text(row.get('validation_note'))}"
        )
    return "\n".join(lines) + "\n"
