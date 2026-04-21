"""Barrier-drag calibration guidance for breakout overlay demotion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.breakout_event_overlay import (
    BREAKOUT_SOFT_BARRIER_PROBE_CONFIDENCE_MIN,
    BREAKOUT_SOFT_BARRIER_PROBE_CONTINUATION_MIN,
    BREAKOUT_SOFT_BARRIER_PROBE_MAX,
    BREAKOUT_SOFT_BARRIER_PROBE_MIN,
)
from backend.services.trade_csv_schema import now_kst_dt


BREAKOUT_BARRIER_DRAG_CALIBRATOR_CONTRACT_VERSION = "breakout_barrier_drag_calibrator_v1"
BREAKOUT_BARRIER_DRAG_CALIBRATOR_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "source_scope",
    "symbol",
    "episode_or_row_key",
    "action_target",
    "overlay_target",
    "historical_alignment_result",
    "conflict_level",
    "action_demotion_rule",
    "barrier_total",
    "breakout_confidence",
    "confirm_score",
    "continuation_score",
    "soft_probe_window_hit",
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


def _load_frame(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _stable_json_counts(values: pd.Series) -> str:
    counts = (
        values.fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .to_dict()
    )
    normalized = {str(key): int(value) for key, value in counts.items()}
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True) if normalized else "{}"


def _soft_probe_window_hit(row: Mapping[str, Any]) -> bool:
    barrier_total = _to_float(row.get("barrier_total"), 0.0)
    breakout_confidence = _to_float(
        row.get("breakout_confidence", row.get("runtime_breakout_confidence", 0.0)),
        0.0,
    )
    confirm_score = _to_float(row.get("confirm_score"), 0.0)
    continuation_score = _to_float(row.get("continuation_score"), 0.0)
    return bool(
        BREAKOUT_SOFT_BARRIER_PROBE_MIN <= barrier_total <= BREAKOUT_SOFT_BARRIER_PROBE_MAX
        and breakout_confidence >= BREAKOUT_SOFT_BARRIER_PROBE_CONFIDENCE_MIN
        and (
            confirm_score >= BREAKOUT_SOFT_BARRIER_PROBE_CONTINUATION_MIN
            or continuation_score >= BREAKOUT_SOFT_BARRIER_PROBE_CONTINUATION_MIN
        )
    )


def build_breakout_barrier_drag_calibrator(
    historical_bridge_csv_path: str | Path,
    runtime_raw_audit_csv_path: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    historical = _load_frame(historical_bridge_csv_path)
    runtime = _load_frame(runtime_raw_audit_csv_path)

    summary: dict[str, Any] = {
        "contract_version": BREAKOUT_BARRIER_DRAG_CALIBRATOR_CONTRACT_VERSION,
        "generated_at": generated_at,
        "historical_row_count": int(len(historical)),
        "historical_barrier_drag_count": 0,
        "historical_supportive_barrier_count": 0,
        "historical_supportive_barrier_min": 0.0,
        "historical_supportive_barrier_max": 0.0,
        "historical_supportive_barrier_p75": 0.0,
        "historical_supportive_confidence_p25": 0.0,
        "historical_supportive_confirm_p25": 0.0,
        "historical_supportive_continuation_p25": 0.0,
        "live_row_count": int(len(runtime)),
        "live_barrier_drag_count": 0,
        "live_soft_probe_window_count": 0,
        "historical_alignment_result_counts": "{}",
        "live_overlay_target_counts": "{}",
        "recommended_soft_probe_barrier_min": round(BREAKOUT_SOFT_BARRIER_PROBE_MIN, 6),
        "recommended_soft_probe_barrier_max": round(BREAKOUT_SOFT_BARRIER_PROBE_MAX, 6),
        "recommended_soft_probe_confidence_min": round(BREAKOUT_SOFT_BARRIER_PROBE_CONFIDENCE_MIN, 6),
        "recommended_soft_probe_support_min": round(BREAKOUT_SOFT_BARRIER_PROBE_CONTINUATION_MIN, 6),
        "recommended_next_action": "collect_barrier_drag_inputs",
    }

    rows: list[dict[str, Any]] = []

    if not historical.empty:
        historical_barrier = historical.loc[historical.get("conflict_level", "").fillna("").astype(str).eq("barrier_drag")].copy()
        summary["historical_barrier_drag_count"] = int(len(historical_barrier))
        if not historical_barrier.empty:
            supportive = historical_barrier.loc[
                historical_barrier.get("historical_alignment_result", "").fillna("").astype(str).eq("demoted_but_supportive")
            ].copy()
            summary["historical_supportive_barrier_count"] = int(len(supportive))
            if not supportive.empty:
                summary["historical_supportive_barrier_min"] = round(_to_float(supportive["barrier_total"].min()), 6)
                summary["historical_supportive_barrier_max"] = round(_to_float(supportive["barrier_total"].max()), 6)
                summary["historical_supportive_barrier_p75"] = round(_to_float(supportive["barrier_total"].quantile(0.75)), 6)
                summary["historical_supportive_confidence_p25"] = round(
                    _to_float(supportive["runtime_breakout_confidence"].quantile(0.25)),
                    6,
                )
                summary["historical_supportive_confirm_p25"] = round(
                    _to_float(supportive["confirm_score"].quantile(0.25)),
                    6,
                )
                summary["historical_supportive_continuation_p25"] = round(
                    _to_float(supportive["continuation_score"].quantile(0.25)),
                    6,
                )
            summary["historical_alignment_result_counts"] = _stable_json_counts(
                historical_barrier.get("historical_alignment_result", pd.Series(dtype=str))
            )

            for record in historical_barrier.to_dict(orient="records"):
                rows.append(
                    {
                        "observation_event_id": f"breakout_barrier_drag_calibrator::historical::{_to_text(record.get('episode_id'))}",
                        "generated_at": generated_at,
                        "source_scope": "historical",
                        "symbol": _to_text(record.get("symbol")).upper(),
                        "episode_or_row_key": _to_text(record.get("episode_id")),
                        "action_target": _to_text(record.get("action_target")).upper(),
                        "overlay_target": _to_text(record.get("overlay_target")).upper(),
                        "historical_alignment_result": _to_text(record.get("historical_alignment_result")),
                        "conflict_level": _to_text(record.get("conflict_level")).lower(),
                        "action_demotion_rule": _to_text(record.get("action_demotion_rule")).lower(),
                        "barrier_total": round(_to_float(record.get("barrier_total"), 0.0), 6),
                        "breakout_confidence": round(_to_float(record.get("runtime_breakout_confidence"), 0.0), 6),
                        "confirm_score": round(_to_float(record.get("confirm_score"), 0.0), 6),
                        "continuation_score": round(_to_float(record.get("continuation_score"), 0.0), 6),
                        "soft_probe_window_hit": bool(_soft_probe_window_hit(record)),
                    }
                )

    if not runtime.empty:
        live_barrier = runtime.loc[
            runtime.get("conflict_level", "").fillna("").astype(str).isin(["barrier_drag", "stacked_conflict"])
        ].copy()
        summary["live_barrier_drag_count"] = int(len(live_barrier))
        if not live_barrier.empty:
            live_barrier["soft_probe_window_hit"] = live_barrier.apply(_soft_probe_window_hit, axis=1)
            summary["live_soft_probe_window_count"] = int(live_barrier["soft_probe_window_hit"].fillna(False).astype(bool).sum())
            summary["live_overlay_target_counts"] = _stable_json_counts(live_barrier.get("overlay_target", pd.Series(dtype=str)))
            for record in live_barrier.to_dict(orient="records"):
                rows.append(
                    {
                        "observation_event_id": f"breakout_barrier_drag_calibrator::live::{_to_text(record.get('detail_row_key'))}",
                        "generated_at": generated_at,
                        "source_scope": "live",
                        "symbol": _to_text(record.get("symbol")).upper(),
                        "episode_or_row_key": _to_text(record.get("detail_row_key")),
                        "action_target": "",
                        "overlay_target": _to_text(record.get("overlay_target")).upper(),
                        "historical_alignment_result": "",
                        "conflict_level": _to_text(record.get("conflict_level")).lower(),
                        "action_demotion_rule": _to_text(record.get("action_demotion_rule")).lower(),
                        "barrier_total": round(_to_float(record.get("barrier_total"), 0.0), 6),
                        "breakout_confidence": round(_to_float(record.get("breakout_confidence"), 0.0), 6),
                        "confirm_score": round(_to_float(record.get("confirm_score"), 0.0), 6),
                        "continuation_score": round(_to_float(record.get("continuation_score"), 0.0), 6),
                        "soft_probe_window_hit": bool(record.get("soft_probe_window_hit")),
                    }
                )

    frame = pd.DataFrame(rows, columns=BREAKOUT_BARRIER_DRAG_CALIBRATOR_COLUMNS)
    if summary["historical_supportive_barrier_count"] > 0 and summary["live_soft_probe_window_count"] > 0:
        summary["recommended_next_action"] = "allow_soft_probe_for_moderate_barrier_drag"
    elif summary["historical_supportive_barrier_count"] > 0:
        summary["recommended_next_action"] = "retain_soft_probe_window_and_wait_for_live_matches"
    elif summary["live_barrier_drag_count"] > 0:
        summary["recommended_next_action"] = "collect_more_historical_barrier_drag_labels"
    return frame, summary


def render_breakout_barrier_drag_calibrator_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> str:
    row = dict(summary or {})
    lines = [
        "# Breakout Barrier Drag Calibrator",
        "",
        f"- generated_at: `{_to_text(row.get('generated_at'))}`",
        f"- historical_barrier_drag_count: `{int(_to_float(row.get('historical_barrier_drag_count'), 0.0))}`",
        f"- historical_supportive_barrier_count: `{int(_to_float(row.get('historical_supportive_barrier_count'), 0.0))}`",
        f"- historical_supportive_barrier_min: `{_to_float(row.get('historical_supportive_barrier_min'), 0.0)}`",
        f"- historical_supportive_barrier_max: `{_to_float(row.get('historical_supportive_barrier_max'), 0.0)}`",
        f"- historical_supportive_barrier_p75: `{_to_float(row.get('historical_supportive_barrier_p75'), 0.0)}`",
        f"- historical_supportive_confidence_p25: `{_to_float(row.get('historical_supportive_confidence_p25'), 0.0)}`",
        f"- historical_supportive_confirm_p25: `{_to_float(row.get('historical_supportive_confirm_p25'), 0.0)}`",
        f"- historical_supportive_continuation_p25: `{_to_float(row.get('historical_supportive_continuation_p25'), 0.0)}`",
        f"- live_barrier_drag_count: `{int(_to_float(row.get('live_barrier_drag_count'), 0.0))}`",
        f"- live_soft_probe_window_count: `{int(_to_float(row.get('live_soft_probe_window_count'), 0.0))}`",
        f"- recommended_soft_probe_barrier_min: `{_to_float(row.get('recommended_soft_probe_barrier_min'), 0.0)}`",
        f"- recommended_soft_probe_barrier_max: `{_to_float(row.get('recommended_soft_probe_barrier_max'), 0.0)}`",
        f"- recommended_soft_probe_confidence_min: `{_to_float(row.get('recommended_soft_probe_confidence_min'), 0.0)}`",
        f"- recommended_soft_probe_support_min: `{_to_float(row.get('recommended_soft_probe_support_min'), 0.0)}`",
        f"- recommended_next_action: `{_to_text(row.get('recommended_next_action'))}`",
    ]
    if frame is not None and not frame.empty:
        lines.extend(["", "## Preview", "", "```text", frame.head(15).to_csv(index=False), "```"])
    return "\n".join(lines) + "\n"
