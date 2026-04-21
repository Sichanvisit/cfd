"""Materialize time-axis contract fields for multi-surface manual supervision rows."""

from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    normalize_manual_wait_teacher_annotation_df,
)
from backend.services.trade_csv_schema import now_kst_dt


SURFACE_TIME_AXIS_CONTRACT_VERSION = "surface_time_axis_contract_v1"

SURFACE_TIME_AXIS_CONTRACT_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "annotation_id",
    "episode_id",
    "symbol",
    "market_family",
    "surface_label_family",
    "surface_label_state",
    "surface_action_bias",
    "timeframe",
    "timeframe_minutes",
    "anchor_time",
    "ideal_entry_time",
    "ideal_exit_time",
    "expected_time_axis_fields",
    "time_axis_quality",
    "time_axis_phase",
    "time_since_breakout_minutes",
    "time_since_entry_minutes",
    "bars_in_state",
    "bars_since_probe_activation",
    "momentum_decay",
    "time_since_last_relief_minutes",
    "time_axis_source",
]

SURFACE_DEFAULT_EXPECTED_FIELDS = {
    "initial_entry_surface": ["bars_in_state", "time_since_last_relief"],
    "follow_through_surface": ["time_since_breakout", "bars_in_state", "momentum_decay"],
    "continuation_hold_surface": ["time_since_entry", "bars_in_state", "momentum_decay"],
    "protective_exit_surface": ["time_since_entry", "bars_in_state", "momentum_decay"],
}

SURFACE_DECAY_HORIZON_BARS = {
    "initial_entry_surface": 6.0,
    "follow_through_surface": 8.0,
    "continuation_hold_surface": 20.0,
    "protective_exit_surface": 12.0,
}


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


def _json_loads_dict(text: object) -> dict[str, Any]:
    raw = _to_text(text)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _parse_timeframe_minutes(timeframe: object) -> float:
    text = _to_text(timeframe).upper()
    if not text:
        return 1.0
    match = re.fullmatch(r"([MHDW])(\d+)", text)
    if not match:
        return 1.0
    prefix, amount_text = match.groups()
    amount = max(1, int(amount_text))
    if prefix == "M":
        return float(amount)
    if prefix == "H":
        return float(amount * 60)
    if prefix == "D":
        return float(amount * 60 * 24)
    if prefix == "W":
        return float(amount * 60 * 24 * 7)
    return 1.0


def _minutes_between(start: object, end: object) -> float:
    start_dt = pd.to_datetime(start, errors="coerce")
    end_dt = pd.to_datetime(end, errors="coerce")
    if pd.isna(start_dt) or pd.isna(end_dt):
        return 0.0
    delta = (end_dt - start_dt).total_seconds() / 60.0
    return round(max(0.0, delta), 6)


def _series_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    series = frame[column].fillna("").astype(str).str.strip()
    series = series.replace("", pd.NA).dropna()
    counts = series.value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _json_counts(counts: dict[str, int]) -> str:
    return json.dumps(counts, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _source_group(annotation_source: object) -> str:
    source = _to_text(annotation_source).lower()
    if source == "chart_annotated":
        return "manual_chart"
    if "breakout_chart_inferred" in source:
        return "breakout_chart_seed"
    if "breakout_overlap_seed" in source:
        return "breakout_overlap_seed"
    if "current_rich_seed" in source:
        return "current_rich_seed"
    if "assistant" in source:
        return "assistant_seed"
    return "manual_seed"


def _source_rank(source_group: str) -> int:
    return {
        "manual_chart": 4,
        "breakout_chart_seed": 3,
        "breakout_overlap_seed": 2,
        "current_rich_seed": 1,
        "assistant_seed": 1,
        "manual_seed": 2,
    }.get(source_group, 1)


def _review_rank(review_status: object) -> int:
    status = _to_text(review_status).lower()
    if status in {"accepted_canonical", "accepted_strict", "accepted_coarse", "approved", "canonical"}:
        return 4
    if status in {"accepted", "pending_review", "pending"}:
        return 3
    if status in {"needs_manual_recheck", "draft", "queued"}:
        return 2
    return 1


def _confidence_rank(confidence: object) -> int:
    return {
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(_to_text(confidence).lower(), 1)


def _prepare_time_source(frame: pd.DataFrame | None) -> pd.DataFrame:
    normalized = normalize_manual_wait_teacher_annotation_df(frame)
    if normalized.empty:
        return normalized
    out = normalized.copy()
    out["source_group"] = out["annotation_source"].apply(_source_group)
    out["__join_key"] = out["annotation_id"].replace("", pd.NA).fillna(out["episode_id"])
    out["__review_rank"] = out["review_status"].apply(_review_rank)
    out["__confidence_rank"] = (
        out["manual_teacher_confidence"].replace("", pd.NA).fillna(out["manual_wait_teacher_confidence"]).apply(_confidence_rank)
    )
    out["__source_rank"] = out["source_group"].apply(_source_rank)
    out["__quality_rank"] = out["__review_rank"] * 100 + out["__confidence_rank"] * 10 + out["__source_rank"]
    keep_columns = [
        "__join_key",
        "annotation_id",
        "episode_id",
        "timeframe",
        "anchor_time",
        "ideal_entry_time",
        "ideal_exit_time",
        "annotation_source",
        "__quality_rank",
    ]
    return out[keep_columns].sort_values(["__join_key", "__quality_rank"], ascending=[True, False]).drop_duplicates(
        "__join_key", keep="first"
    )


def _expected_fields_for_surface(surface_label_family: str, surface_spec_map: dict[str, Any]) -> list[str]:
    spec = dict(surface_spec_map.get(surface_label_family, {}) or {})
    fields = spec.get("time_axis_fields")
    if isinstance(fields, list) and fields:
        return [str(field) for field in fields]
    return list(SURFACE_DEFAULT_EXPECTED_FIELDS.get(surface_label_family, []))


def _time_axis_phase(surface_label_family: str, bars_in_state: float) -> str:
    bars = float(bars_in_state)
    if surface_label_family == "follow_through_surface":
        if bars <= 1:
            return "fresh_breakout"
        if bars <= 3:
            return "follow_through_window"
        if bars <= 8:
            return "continuation_window"
        return "stale_follow_through"
    if surface_label_family == "initial_entry_surface":
        if bars <= 1:
            return "fresh_initial"
        if bars <= 3:
            return "early_initial"
        return "late_initial"
    if surface_label_family == "continuation_hold_surface":
        if bars <= 3:
            return "runner_fresh"
        if bars <= 12:
            return "runner_active"
        return "runner_late"
    if surface_label_family == "protective_exit_surface":
        if bars <= 2:
            return "protect_early"
        if bars <= 8:
            return "protect_active"
        return "protect_late"
    return "time_unknown"


def _infer_time_axis(
    row: pd.Series,
    *,
    timeframe_minutes: float,
) -> tuple[float, float, float, float, float, str]:
    anchor_time = _to_text(row.get("anchor_time"))
    ideal_entry_time = _to_text(row.get("ideal_entry_time"))
    ideal_exit_time = _to_text(row.get("ideal_exit_time"))
    surface_label_family = _to_text(row.get("surface_label_family"))
    surface_label_state = _to_text(row.get("surface_label_state"))
    chart_context = _to_text(row.get("chart_context")).lower()
    barrier_hint = _to_text(row.get("barrier_main_label_hint")).lower()

    time_since_breakout_minutes = 0.0
    if anchor_time and ideal_entry_time:
        time_since_breakout_minutes = _minutes_between(anchor_time, ideal_entry_time)
    elif anchor_time and ideal_exit_time:
        time_since_breakout_minutes = _minutes_between(anchor_time, ideal_exit_time)

    time_since_entry_minutes = 0.0
    if ideal_entry_time and ideal_exit_time:
        time_since_entry_minutes = _minutes_between(ideal_entry_time, ideal_exit_time)
    elif ideal_entry_time and anchor_time:
        time_since_entry_minutes = _minutes_between(ideal_entry_time, anchor_time)

    bars_since_probe_activation = round(time_since_breakout_minutes / max(1.0, timeframe_minutes), 6)

    if surface_label_family in {"initial_entry_surface", "follow_through_surface"}:
        bars_in_state = bars_since_probe_activation
    else:
        bars_in_state = round(time_since_entry_minutes / max(1.0, timeframe_minutes), 6)
        if bars_in_state <= 0:
            bars_in_state = bars_since_probe_activation

    time_since_last_relief_minutes = 0.0
    if surface_label_state in {"pullback_resume", "timing_better_entry"} or barrier_hint == "wait_then_enter":
        time_since_last_relief_minutes = time_since_breakout_minutes
    elif any(token in chart_context for token in ("reclaim", "pullback", "resume", "retest")):
        time_since_last_relief_minutes = time_since_breakout_minutes
    elif surface_label_family in {"continuation_hold_surface", "protective_exit_surface"}:
        time_since_last_relief_minutes = time_since_entry_minutes

    horizon = float(SURFACE_DECAY_HORIZON_BARS.get(surface_label_family, 8.0))
    momentum_decay = round(min(1.0, float(bars_in_state) / max(1.0, horizon)), 6)

    if ideal_entry_time and ideal_exit_time:
        quality = "entry_exit_direct"
    elif anchor_time and ideal_entry_time:
        quality = "anchor_entry_direct"
    elif anchor_time:
        quality = "anchor_only"
    else:
        quality = "missing"

    return (
        round(time_since_breakout_minutes, 6),
        round(time_since_entry_minutes, 6),
        round(bars_in_state, 6),
        round(bars_since_probe_activation, 6),
        round(time_since_last_relief_minutes, 6),
        quality,
    )


def build_surface_time_axis_contract(
    check_color_label_formalization: pd.DataFrame | None,
    surface_objective_spec: pd.DataFrame | None,
    manual_wait_teacher_annotations: pd.DataFrame | None,
    breakout_manual_overlap_seed_draft: pd.DataFrame | None,
    breakout_manual_overlap_seed_review_entries: pd.DataFrame | None,
    manual_current_rich_seed_draft: pd.DataFrame | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    labels = check_color_label_formalization.copy() if check_color_label_formalization is not None else pd.DataFrame()
    if labels.empty:
        summary = {
            "contract_version": SURFACE_TIME_AXIS_CONTRACT_VERSION,
            "generated_at": generated_at,
            "row_count": 0,
            "surface_label_family_counts": "{}",
            "time_axis_phase_counts": "{}",
            "time_axis_quality_counts": "{}",
            "recommended_next_action": "collect_formalized_surface_rows",
        }
        return pd.DataFrame(columns=SURFACE_TIME_AXIS_CONTRACT_COLUMNS), summary

    spec_frame = surface_objective_spec.copy() if surface_objective_spec is not None else pd.DataFrame()
    surface_spec_map: dict[str, Any] = {}
    if not spec_frame.empty:
        for _, spec_row in spec_frame.iterrows():
            surface_spec_map[_to_text(spec_row.get("surface_name"))] = {
                "time_axis_fields": _json_loads_dict("{}"),
            }
        for _, spec_row in spec_frame.iterrows():
            surface_name = _to_text(spec_row.get("surface_name"))
            try:
                time_axis_fields = json.loads(_to_text(spec_row.get("time_axis_fields"), "[]"))
            except Exception:
                time_axis_fields = []
            if not isinstance(time_axis_fields, list):
                time_axis_fields = []
            surface_spec_map[surface_name] = {
                "time_axis_fields": [str(field) for field in time_axis_fields],
            }

    source_frames = [
        _prepare_time_source(manual_wait_teacher_annotations),
        _prepare_time_source(breakout_manual_overlap_seed_draft),
        _prepare_time_source(breakout_manual_overlap_seed_review_entries),
        _prepare_time_source(manual_current_rich_seed_draft),
    ]
    combined_source = pd.concat([frame for frame in source_frames if frame is not None and not frame.empty], ignore_index=True)
    if combined_source.empty:
        combined_source = pd.DataFrame(columns=["__join_key", "timeframe", "anchor_time", "ideal_entry_time", "ideal_exit_time"])
    else:
        combined_source = combined_source.sort_values(["__join_key", "__quality_rank"], ascending=[True, False]).drop_duplicates(
            "__join_key", keep="first"
        )

    source_lookup = combined_source.set_index("__join_key").to_dict(orient="index") if not combined_source.empty else {}

    rows: list[dict[str, Any]] = []
    for _, row in labels.iterrows():
        annotation_id = _to_text(row.get("annotation_id"))
        episode_id = _to_text(row.get("episode_id"))
        join_key = annotation_id or episode_id
        source_row = dict(source_lookup.get(join_key, {}))
        timeframe = _to_text(source_row.get("timeframe"), "M1")
        anchor_time = _to_text(source_row.get("anchor_time"), _to_text(row.get("anchor_time")))
        ideal_entry_time = _to_text(source_row.get("ideal_entry_time"))
        ideal_exit_time = _to_text(source_row.get("ideal_exit_time"))
        timeframe_minutes = _parse_timeframe_minutes(timeframe)
        (
            time_since_breakout_minutes,
            time_since_entry_minutes,
            bars_in_state,
            bars_since_probe_activation,
            time_since_last_relief_minutes,
            time_axis_quality,
        ) = _infer_time_axis(
            pd.Series(
                {
                    **row.to_dict(),
                    "anchor_time": anchor_time,
                    "ideal_entry_time": ideal_entry_time,
                    "ideal_exit_time": ideal_exit_time,
                }
            ),
            timeframe_minutes=timeframe_minutes,
        )
        surface_label_family = _to_text(row.get("surface_label_family"))
        expected_fields = _expected_fields_for_surface(surface_label_family, surface_spec_map)
        time_axis_phase = _time_axis_phase(surface_label_family, bars_in_state)
        observation_event_id = f"{SURFACE_TIME_AXIS_CONTRACT_VERSION}:{re.sub(r'[^0-9A-Za-z]+', '_', join_key).strip('_').lower()}"
        rows.append(
            {
                "observation_event_id": observation_event_id,
                "generated_at": generated_at,
                "annotation_id": annotation_id,
                "episode_id": episode_id,
                "symbol": _to_text(row.get("symbol")),
                "market_family": _to_text(row.get("market_family") or row.get("symbol")),
                "surface_label_family": surface_label_family,
                "surface_label_state": _to_text(row.get("surface_label_state")),
                "surface_action_bias": _to_text(row.get("surface_action_bias")),
                "timeframe": timeframe,
                "timeframe_minutes": timeframe_minutes,
                "anchor_time": anchor_time,
                "ideal_entry_time": ideal_entry_time,
                "ideal_exit_time": ideal_exit_time,
                "expected_time_axis_fields": json.dumps(expected_fields, ensure_ascii=False),
                "time_axis_quality": time_axis_quality,
                "time_axis_phase": time_axis_phase,
                "time_since_breakout_minutes": time_since_breakout_minutes,
                "time_since_entry_minutes": time_since_entry_minutes,
                "bars_in_state": bars_in_state,
                "bars_since_probe_activation": bars_since_probe_activation,
                "momentum_decay": round(min(1.0, float(bars_in_state) / max(1.0, SURFACE_DECAY_HORIZON_BARS.get(surface_label_family, 8.0))), 6),
                "time_since_last_relief_minutes": time_since_last_relief_minutes,
                "time_axis_source": time_axis_quality,
            }
        )

    frame = pd.DataFrame(rows, columns=SURFACE_TIME_AXIS_CONTRACT_COLUMNS)
    summary = {
        "contract_version": SURFACE_TIME_AXIS_CONTRACT_VERSION,
        "generated_at": generated_at,
        "row_count": int(len(frame)),
        "surface_label_family_counts": _json_counts(_series_counts(frame, "surface_label_family")),
        "time_axis_phase_counts": _json_counts(_series_counts(frame, "time_axis_phase")),
        "time_axis_quality_counts": _json_counts(_series_counts(frame, "time_axis_quality")),
        "avg_time_since_breakout_minutes": round(float(frame["time_since_breakout_minutes"].mean()), 6) if not frame.empty else 0.0,
        "avg_time_since_entry_minutes": round(float(frame["time_since_entry_minutes"].mean()), 6) if not frame.empty else 0.0,
        "avg_bars_in_state": round(float(frame["bars_in_state"].mean()), 6) if not frame.empty else 0.0,
        "recommended_next_action": "use_time_axis_contract_in_xau_follow_through_and_runner_surfaces",
    }
    return frame, summary


def render_surface_time_axis_contract_markdown(summary: dict[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Surface Time-Axis Contract",
        "",
        f"- generated_at: `{_to_text(summary.get('generated_at'))}`",
        f"- row_count: `{int(summary.get('row_count', 0) or 0)}`",
        f"- surface_label_family_counts: `{_to_text(summary.get('surface_label_family_counts'), '{}')}`",
        f"- time_axis_phase_counts: `{_to_text(summary.get('time_axis_phase_counts'), '{}')}`",
        f"- time_axis_quality_counts: `{_to_text(summary.get('time_axis_quality_counts'), '{}')}`",
        f"- avg_time_since_breakout_minutes: `{_to_float(summary.get('avg_time_since_breakout_minutes'))}`",
        f"- avg_time_since_entry_minutes: `{_to_float(summary.get('avg_time_since_entry_minutes'))}`",
        f"- avg_bars_in_state: `{_to_float(summary.get('avg_bars_in_state'))}`",
        f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`",
        "",
        "## Preview",
        "",
    ]
    if frame.empty:
        lines.append("- no rows")
        return "\n".join(lines)

    preview_columns = [
        "symbol",
        "surface_label_family",
        "surface_label_state",
        "time_axis_phase",
        "time_since_breakout_minutes",
        "time_since_entry_minutes",
        "bars_in_state",
        "momentum_decay",
    ]
    preview = frame.loc[:, preview_columns].head(12)
    header = "| " + " | ".join(preview_columns) + " |"
    divider = "| " + " | ".join(["---"] * len(preview_columns)) + " |"
    lines.append(header)
    lines.append(divider)
    for _, row in preview.iterrows():
        values = [_to_text(row.get(column)).replace("|", "/") for column in preview_columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)
