"""Harvest wrong-side active-action conflicts from runtime entry decisions."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


WRONG_SIDE_CONFLICT_HARVEST_VERSION = "wrong_side_conflict_harvest_v1"

WRONG_SIDE_CONFLICT_HARVEST_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "symbol",
    "market_family",
    "event_time",
    "setup_id",
    "setup_reason",
    "outcome",
    "baseline_action",
    "effective_baseline_action",
    "directional_candidate_action",
    "directional_state",
    "directional_owner_family",
    "bridge_mode",
    "bridge_source",
    "bridge_action",
    "bridge_surface_family",
    "bridge_surface_state",
    "conflict_kind",
    "conflict_resolution_state",
    "guard_applied",
    "primary_failure_label",
    "continuation_failure_label",
    "context_failure_label",
    "blocked_by",
    "action_none_reason",
    "observe_reason",
    "up_bias_score",
    "down_bias_score",
    "bias_gap",
    "warning_count",
    "evidence_summary",
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


def _slug_text(value: object) -> str:
    text = _to_text(value).lower()
    safe = "".join(char if char.isalnum() else "_" for char in text)
    return safe.strip("_")


def _series_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    series = frame[column].fillna("").astype(str).str.strip().replace("", pd.NA).dropna()
    counts = series.value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(key): int(value) for key, value in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _ensure_columns(frame: pd.DataFrame) -> pd.DataFrame:
    local = frame.copy()
    for column in (
        "time",
        "symbol",
        "setup_id",
        "setup_reason",
        "outcome",
        "action",
        "blocked_by",
        "action_none_reason",
        "observe_reason",
        "active_action_conflict_detected",
        "active_action_conflict_guard_applied",
        "active_action_conflict_resolution_state",
        "active_action_conflict_kind",
        "active_action_conflict_baseline_action",
        "active_action_conflict_directional_action",
        "active_action_conflict_directional_state",
        "active_action_conflict_directional_owner_family",
        "active_action_conflict_up_bias_score",
        "active_action_conflict_down_bias_score",
        "active_action_conflict_bias_gap",
        "active_action_conflict_warning_count",
        "active_action_conflict_reason_summary",
        "entry_candidate_bridge_mode",
        "entry_candidate_bridge_source",
        "entry_candidate_bridge_action",
        "entry_candidate_bridge_effective_baseline_action",
        "entry_candidate_bridge_conflict_selected",
        "entry_candidate_surface_family",
        "entry_candidate_surface_state",
    ):
        if column not in local.columns:
            local[column] = ""
    return local


def _derive_labels(
    *,
    baseline_action: str,
    directional_action: str,
    directional_state: str,
    bridge_action: str,
) -> tuple[str, str, str]:
    baseline_u = _to_text(baseline_action).upper()
    directional_u = _to_text(directional_action).upper()
    directional_state_u = _to_text(directional_state).upper()
    bridge_action_u = _to_text(bridge_action).upper()

    if baseline_u == "SELL" and directional_u == "BUY":
        continuation = ""
        if directional_state_u in {"UP_PROBE", "UP_ENTER"} or bridge_action_u == "BUY":
            continuation = "missed_up_continuation"
        return (
            "wrong_side_sell_pressure",
            continuation,
            "false_down_pressure_in_uptrend",
        )
    if baseline_u == "BUY" and directional_u == "SELL":
        continuation = ""
        if directional_state_u in {"DOWN_PROBE", "DOWN_ENTER"} or bridge_action_u == "SELL":
            continuation = "missed_down_continuation"
        return (
            "wrong_side_buy_pressure",
            continuation,
            "false_up_pressure_in_downtrend",
        )
    return ("", "", "")


def _conflict_mask(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)
    detected = frame["active_action_conflict_detected"].map(_to_bool)
    guard_applied = frame["active_action_conflict_guard_applied"].map(_to_bool)
    bridge_conflict = frame["entry_candidate_bridge_mode"].fillna("").astype(str).str.strip().eq("active_action_conflict_resolution")
    return detected | guard_applied | bridge_conflict


def build_wrong_side_conflict_harvest(
    entry_decisions: pd.DataFrame | None,
    *,
    recent_limit: int = 480,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    frame = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()

    summary: dict[str, Any] = {
        "contract_version": WRONG_SIDE_CONFLICT_HARVEST_VERSION,
        "generated_at": generated_at,
        "recent_row_count": 0,
        "row_count": 0,
        "guard_applied_count": 0,
        "bridge_conflict_selected_count": 0,
        "symbol_counts": "{}",
        "primary_failure_label_counts": "{}",
        "continuation_failure_label_counts": "{}",
        "context_failure_label_counts": "{}",
        "bridge_mode_counts": "{}",
        "conflict_resolution_state_counts": "{}",
        "recommended_next_action": "await_fresh_wrong_side_conflicts",
    }
    if frame.empty:
        return pd.DataFrame(columns=WRONG_SIDE_CONFLICT_HARVEST_COLUMNS), summary

    scoped = _ensure_columns(frame)
    scoped["__time_sort"] = pd.to_datetime(scoped["time"], errors="coerce")
    scoped = scoped.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    scoped = scoped.head(max(1, int(recent_limit))).copy()
    summary["recent_row_count"] = int(len(scoped))

    conflicts = scoped.loc[_conflict_mask(scoped)].copy()
    rows: list[dict[str, Any]] = []
    for _, row in conflicts.iterrows():
        baseline_action = _to_text(
            row.get("active_action_conflict_baseline_action")
            or row.get("entry_candidate_bridge_effective_baseline_action")
            or row.get("action")
        ).upper()
        directional_action = _to_text(row.get("active_action_conflict_directional_action")).upper()
        directional_state = _to_text(row.get("active_action_conflict_directional_state")).upper()
        bridge_action = _to_text(row.get("entry_candidate_bridge_action")).upper()
        opposite_candidate_action = (
            directional_action
            if directional_action in {"BUY", "SELL"}
            else bridge_action
            if bridge_action in {"BUY", "SELL"}
            else ""
        )

        if baseline_action not in {"BUY", "SELL"} or opposite_candidate_action not in {"BUY", "SELL"}:
            continue
        if baseline_action == opposite_candidate_action:
            continue

        primary_label, continuation_label, context_label = _derive_labels(
            baseline_action=baseline_action,
            directional_action=opposite_candidate_action,
            directional_state=directional_state,
            bridge_action=bridge_action,
        )
        if not primary_label:
            continue

        event_time = _to_text(row.get("time"))
        bridge_mode = _to_text(row.get("entry_candidate_bridge_mode"))
        evidence_tokens = [
            _to_text(row.get("active_action_conflict_kind")),
            _to_text(row.get("active_action_conflict_reason_summary")),
            bridge_mode,
            _to_text(row.get("entry_candidate_bridge_source")),
            _to_text(row.get("entry_candidate_bridge_action")).upper(),
        ]
        rows.append(
            {
                "observation_event_id": f"{WRONG_SIDE_CONFLICT_HARVEST_VERSION}:{_slug_text(_to_text(row.get('symbol')).upper())}:{_slug_text(event_time)}:{primary_label}",
                "generated_at": generated_at,
                "symbol": _to_text(row.get("symbol")).upper(),
                "market_family": _to_text(row.get("symbol")).upper(),
                "event_time": event_time,
                "setup_id": _to_text(row.get("setup_id")),
                "setup_reason": _to_text(row.get("setup_reason")),
                "outcome": _to_text(row.get("outcome")),
                "baseline_action": baseline_action,
                "effective_baseline_action": _to_text(
                    row.get("entry_candidate_bridge_effective_baseline_action") or baseline_action
                ).upper(),
                "directional_candidate_action": opposite_candidate_action,
                "directional_state": directional_state,
                "directional_owner_family": _to_text(row.get("active_action_conflict_directional_owner_family")),
                "bridge_mode": bridge_mode,
                "bridge_source": _to_text(row.get("entry_candidate_bridge_source")),
                "bridge_action": bridge_action,
                "bridge_surface_family": _to_text(row.get("entry_candidate_surface_family")),
                "bridge_surface_state": _to_text(row.get("entry_candidate_surface_state")),
                "conflict_kind": _to_text(row.get("active_action_conflict_kind")),
                "conflict_resolution_state": _to_text(row.get("active_action_conflict_resolution_state")),
                "guard_applied": bool(_to_bool(row.get("active_action_conflict_guard_applied"))),
                "primary_failure_label": primary_label,
                "continuation_failure_label": continuation_label,
                "context_failure_label": context_label,
                "blocked_by": _to_text(row.get("blocked_by")),
                "action_none_reason": _to_text(row.get("action_none_reason")),
                "observe_reason": _to_text(row.get("observe_reason")),
                "up_bias_score": round(_to_float(row.get("active_action_conflict_up_bias_score")), 6),
                "down_bias_score": round(_to_float(row.get("active_action_conflict_down_bias_score")), 6),
                "bias_gap": round(_to_float(row.get("active_action_conflict_bias_gap")), 6),
                "warning_count": int(_to_float(row.get("active_action_conflict_warning_count"))),
                "evidence_summary": " | ".join(token for token in evidence_tokens if token),
            }
        )

    harvest = pd.DataFrame(rows, columns=WRONG_SIDE_CONFLICT_HARVEST_COLUMNS)
    summary["row_count"] = int(len(harvest))
    if harvest.empty:
        return harvest, summary

    continuation_counts = _series_counts(harvest, "continuation_failure_label")
    continuation_counts.pop("", None)
    context_counts = _series_counts(harvest, "context_failure_label")
    context_counts.pop("", None)
    summary["guard_applied_count"] = int(harvest["guard_applied"].sum())
    summary["bridge_conflict_selected_count"] = int(
        harvest["bridge_mode"].fillna("").astype(str).eq("active_action_conflict_resolution").sum()
    )
    summary["symbol_counts"] = _json_counts(_series_counts(harvest, "symbol"))
    summary["primary_failure_label_counts"] = _json_counts(_series_counts(harvest, "primary_failure_label"))
    summary["continuation_failure_label_counts"] = _json_counts(continuation_counts)
    summary["context_failure_label_counts"] = _json_counts(context_counts)
    summary["bridge_mode_counts"] = _json_counts(_series_counts(harvest, "bridge_mode"))
    summary["conflict_resolution_state_counts"] = _json_counts(_series_counts(harvest, "conflict_resolution_state"))

    top_primary = next(iter(_series_counts(harvest, "primary_failure_label").keys()), "")
    summary["recommended_next_action"] = {
        "wrong_side_sell_pressure": "validate_xau_upper_reversal_conflict_guard",
        "wrong_side_buy_pressure": "validate_downside_conflict_guard",
    }.get(top_primary, "review_wrong_side_conflict_harvest")
    return harvest, summary


def build_wrong_side_conflict_failure_rows(
    entry_decisions: pd.DataFrame | None,
    *,
    generated_at: str,
    recent_limit: int = 480,
    focus_map: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    harvest, _ = build_wrong_side_conflict_harvest(
        entry_decisions,
        recent_limit=recent_limit,
    )
    if harvest.empty:
        return []

    rows: list[dict[str, Any]] = []
    focus = dict(focus_map or {})
    for row in harvest.to_dict(orient="records"):
        symbol = _to_text(row.get("symbol")).upper()
        event_time = _to_text(row.get("event_time"))
        surface_family = _to_text(row.get("bridge_surface_family")) or "follow_through_surface"
        surface_state = _to_text(row.get("bridge_surface_state")) or "continuation_follow"
        evidence_tokens = [
            _to_text(row.get("conflict_kind")),
            _to_text(row.get("evidence_summary")),
            _to_text(row.get("continuation_failure_label")),
            _to_text(row.get("context_failure_label")),
        ]
        for failure_label in (
            _to_text(row.get("primary_failure_label")),
            _to_text(row.get("continuation_failure_label")),
        ):
            if not failure_label:
                continue
            rows.append(
                {
                    "observation_event_id": f"{WRONG_SIDE_CONFLICT_HARVEST_VERSION}:failure:{_slug_text(symbol)}:{_slug_text(event_time)}:{failure_label}",
                    "generated_at": generated_at,
                    "harvest_strength": "candidate",
                    "harvest_source": "wrong_side_conflict_runtime",
                    "source_observation_id": _to_text(row.get("observation_event_id")),
                    "symbol": symbol,
                    "market_family": symbol,
                    "surface_label_family": surface_family,
                    "surface_label_state": surface_state,
                    "failure_label": failure_label,
                    "supervision_strength": "candidate",
                    "source_group": "runtime_entry_conflict",
                    "source_reason": _to_text(row.get("conflict_kind")) or "active_action_conflict_runtime",
                    "source_focus": _to_text(focus.get(symbol)),
                    "event_time": event_time,
                    "anchor_time": "",
                    "time_axis_phase": "",
                    "time_since_breakout_minutes": 0.0,
                    "time_since_entry_minutes": 0.0,
                    "bars_in_state": 0.0,
                    "momentum_decay": 0.0,
                    "outcome": _to_text(row.get("outcome")),
                    "blocked_by": _to_text(row.get("blocked_by")),
                    "action_none_reason": _to_text(row.get("action_none_reason")),
                    "observe_reason": _to_text(row.get("observe_reason")),
                    "exit_reason": "",
                    "evidence_summary": " | ".join(token for token in evidence_tokens if token),
                }
            )
    return rows


def render_wrong_side_conflict_harvest_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Wrong-Side Conflict Harvest",
        "",
        f"- generated_at: `{_to_text(summary.get('generated_at'))}`",
        f"- recent_row_count: `{int(_to_float(summary.get('recent_row_count'))):d}`",
        f"- row_count: `{int(_to_float(summary.get('row_count'))):d}`",
        f"- guard_applied_count: `{int(_to_float(summary.get('guard_applied_count'))):d}`",
        f"- bridge_conflict_selected_count: `{int(_to_float(summary.get('bridge_conflict_selected_count'))):d}`",
        f"- symbol_counts: `{_to_text(summary.get('symbol_counts'), '{}')}`",
        f"- primary_failure_label_counts: `{_to_text(summary.get('primary_failure_label_counts'), '{}')}`",
        f"- continuation_failure_label_counts: `{_to_text(summary.get('continuation_failure_label_counts'), '{}')}`",
        f"- context_failure_label_counts: `{_to_text(summary.get('context_failure_label_counts'), '{}')}`",
        f"- bridge_mode_counts: `{_to_text(summary.get('bridge_mode_counts'), '{}')}`",
        f"- conflict_resolution_state_counts: `{_to_text(summary.get('conflict_resolution_state_counts'), '{}')}`",
        f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`",
        "",
    ]
    if not frame.empty:
        preview = frame.head(8)
        try:
            preview_text = preview.to_markdown(index=False)
        except Exception:
            preview_text = preview.to_string(index=False)
        lines.extend(
            [
                "## Preview",
                "",
                preview_text,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
