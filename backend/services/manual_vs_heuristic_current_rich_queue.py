"""Current-rich heuristic window collection queue for new manual truth."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.manual_vs_heuristic_comparison import (
    _parse_local_timestamp,
    load_entry_decision_heuristic_frame,
    load_manual_wait_teacher_annotations,
)


MANUAL_VS_HEURISTIC_CURRENT_RICH_QUEUE_VERSION = "manual_vs_heuristic_current_rich_queue_v0"

MANUAL_VS_HEURISTIC_CURRENT_RICH_QUEUE_COLUMNS = [
    "queue_id",
    "symbol",
    "window_start",
    "window_end",
    "row_count",
    "unique_signal_minutes",
    "barrier_label_top",
    "recommended_family_top",
    "wait_decision_top",
    "reason_top",
    "suggested_manual_episode_target",
    "capture_priority",
    "collection_status",
    "collection_note",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _current_only_semantic_rows(heuristics: pd.DataFrame) -> pd.DataFrame:
    if heuristics.empty:
        return pd.DataFrame()
    current = heuristics[heuristics["heuristic_source_kind"].fillna("").astype(str).eq("current")].copy()
    if current.empty:
        return current
    evidence_mask = current.apply(
        lambda row: any(
            _to_text(row.get(key, ""), "")
            for key in [
                "barrier_candidate_supporting_label",
                "barrier_candidate_recommended_family",
                "barrier_action_hint_reason_summary",
                "forecast_decision_hint",
                "belief_candidate_recommended_family",
                "entry_wait_decision",
                "blocked_by",
                "observe_reason",
                "core_reason",
            ]
        ),
        axis=1,
    )
    return current[evidence_mask].copy()


def _top_value(series: pd.Series) -> str:
    cleaned = series.fillna("").astype(str).str.strip()
    cleaned = cleaned[cleaned.ne("")]
    if cleaned.empty:
        return ""
    return cleaned.value_counts().index[0]


def _suggested_episode_target(unique_signal_minutes: int, row_count: int) -> int:
    if unique_signal_minutes >= 25 or row_count >= 300:
        return 5
    if unique_signal_minutes >= 18 or row_count >= 180:
        return 4
    if unique_signal_minutes >= 10 or row_count >= 90:
        return 3
    return 2


def _capture_priority(unique_signal_minutes: int, row_count: int) -> str:
    if unique_signal_minutes >= 18 or row_count >= 180:
        return "high"
    if unique_signal_minutes >= 10 or row_count >= 90:
        return "medium"
    return "low"


def build_manual_vs_heuristic_current_rich_queue(
    manual_annotations: pd.DataFrame,
    heuristic_frame: pd.DataFrame,
    *,
    window_minutes: int = 30,
    limit_per_symbol: int = 4,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manual = manual_annotations.copy() if manual_annotations is not None else pd.DataFrame()
    heuristics = heuristic_frame.copy() if heuristic_frame is not None else pd.DataFrame()

    semantic_current = _current_only_semantic_rows(heuristics)
    if semantic_current.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_CURRENT_RICH_QUEUE_COLUMNS)
        summary = {
            "queue_version": MANUAL_VS_HEURISTIC_CURRENT_RICH_QUEUE_VERSION,
            "queue_count": 0,
            "window_minutes": window_minutes,
            "manual_anchor_time_max": "",
            "heuristic_window_min": "",
            "heuristic_window_max": "",
            "symbol_counts": {},
            "priority_counts": {},
        }
        return empty, summary

    manual_anchor_times = manual.get("anchor_time", pd.Series(dtype=object)).apply(_parse_local_timestamp)
    manual_anchor_max = manual_anchor_times.dropna().max() if not manual_anchor_times.dropna().empty else None

    if manual_anchor_max is not None:
        semantic_current = semantic_current[semantic_current["heuristic_time"] > manual_anchor_max].copy()
    if semantic_current.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_CURRENT_RICH_QUEUE_COLUMNS)
        summary = {
            "queue_version": MANUAL_VS_HEURISTIC_CURRENT_RICH_QUEUE_VERSION,
            "queue_count": 0,
            "window_minutes": window_minutes,
            "manual_anchor_time_max": manual_anchor_max.isoformat() if manual_anchor_max is not None else "",
            "heuristic_window_min": "",
            "heuristic_window_max": "",
            "symbol_counts": {},
            "priority_counts": {},
        }
        return empty, summary

    semantic_current["window_start"] = semantic_current["heuristic_time"].dt.floor(f"{int(window_minutes)}min")
    semantic_current["window_end"] = semantic_current["window_start"] + pd.Timedelta(minutes=int(window_minutes))
    semantic_current["signal_minute"] = semantic_current["heuristic_time"].dt.floor("min")

    rows: list[dict[str, Any]] = []
    for symbol, symbol_group in semantic_current.groupby("symbol", sort=False):
        grouped = []
        for window_start, window_group in symbol_group.groupby("window_start", sort=True):
            row_count = int(len(window_group))
            unique_signal_minutes = int(window_group["signal_minute"].nunique())
            barrier_label_top = _top_value(window_group.get("barrier_candidate_supporting_label", pd.Series(dtype=object)))
            recommended_family_top = _top_value(window_group.get("barrier_candidate_recommended_family", pd.Series(dtype=object)))
            wait_decision_top = _top_value(window_group.get("entry_wait_decision", pd.Series(dtype=object)))
            reason_top = _top_value(window_group.get("barrier_action_hint_reason_summary", pd.Series(dtype=object)))
            if not reason_top:
                reason_top = _top_value(window_group.get("core_reason", pd.Series(dtype=object)))
            grouped.append(
                {
                    "queue_id": f"current_rich::{symbol}::{pd.Timestamp(window_start).isoformat()}",
                    "symbol": _to_text(symbol, ""),
                    "window_start": pd.Timestamp(window_start).isoformat(),
                    "window_end": pd.Timestamp(window_group["window_end"].iloc[0]).isoformat(),
                    "row_count": row_count,
                    "unique_signal_minutes": unique_signal_minutes,
                    "barrier_label_top": barrier_label_top,
                    "recommended_family_top": recommended_family_top,
                    "wait_decision_top": wait_decision_top,
                    "reason_top": reason_top,
                    "suggested_manual_episode_target": _suggested_episode_target(unique_signal_minutes, row_count),
                    "capture_priority": _capture_priority(unique_signal_minutes, row_count),
                    "collection_status": "pending",
                    "collection_note": "current hint-rich window after latest manual corpus",
                }
            )
        ranked = sorted(
            grouped,
            key=lambda item: (
                {"high": 0, "medium": 1, "low": 2}.get(item["capture_priority"], 3),
                -int(item["unique_signal_minutes"]),
                -int(item["row_count"]),
                item["window_start"],
            ),
        )
        rows.extend(ranked[: int(limit_per_symbol)])

    queue = pd.DataFrame(rows)
    if not queue.empty:
        queue["priority_rank"] = queue["capture_priority"].map({"high": 0, "medium": 1, "low": 2}).fillna(3)
        queue = queue.sort_values(
            by=["priority_rank", "symbol", "window_start"],
            kind="stable",
        ).copy()
        queue = queue.drop(columns=["priority_rank"])

    for column in MANUAL_VS_HEURISTIC_CURRENT_RICH_QUEUE_COLUMNS:
        if column not in queue.columns:
            queue[column] = ""
    queue = queue[MANUAL_VS_HEURISTIC_CURRENT_RICH_QUEUE_COLUMNS].copy()

    summary = {
        "queue_version": MANUAL_VS_HEURISTIC_CURRENT_RICH_QUEUE_VERSION,
        "queue_count": int(len(queue)),
        "window_minutes": int(window_minutes),
        "manual_anchor_time_max": manual_anchor_max.isoformat() if manual_anchor_max is not None else "",
        "heuristic_window_min": pd.Timestamp(semantic_current["heuristic_time"].min()).isoformat(),
        "heuristic_window_max": pd.Timestamp(semantic_current["heuristic_time"].max()).isoformat(),
        "symbol_counts": queue["symbol"].value_counts(dropna=False).to_dict(),
        "priority_counts": queue["capture_priority"].value_counts(dropna=False).to_dict(),
    }
    return queue, summary


def render_manual_vs_heuristic_current_rich_queue_markdown(summary: Mapping[str, Any], queue: pd.DataFrame) -> str:
    lines = [
        "# Manual vs Heuristic Current-Rich Collection Queue v0",
        "",
        f"- queue rows: `{summary.get('queue_count', 0)}`",
        f"- window minutes: `{summary.get('window_minutes', 0)}`",
        f"- latest manual anchor: `{summary.get('manual_anchor_time_max', '')}`",
        f"- heuristic-rich window: `{summary.get('heuristic_window_min', '')}` -> `{summary.get('heuristic_window_max', '')}`",
        f"- symbol counts: `{summary.get('symbol_counts', {})}`",
        f"- priority counts: `{summary.get('priority_counts', {})}`",
        "",
        "## Collection Queue",
    ]
    if queue.empty:
        lines.append("- none")
    else:
        for _, row in queue.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("symbol", "")),
                        f"{_to_text(row.get('window_start', ''))} -> {_to_text(row.get('window_end', ''))}",
                        f"priority={_to_text(row.get('capture_priority', ''))}",
                        f"target={_to_text(row.get('suggested_manual_episode_target', ''))}",
                        f"barrier={_to_text(row.get('barrier_label_top', ''), 'blank')}",
                        f"family={_to_text(row.get('recommended_family_top', ''), 'blank')}",
                    ]
                )
            )
    return "\n".join(lines) + "\n"


def load_default_manual_and_current_heuristics(
    manual_annotations_path: str | Path,
    heuristic_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        load_manual_wait_teacher_annotations(manual_annotations_path),
        load_entry_decision_heuristic_frame(heuristic_path),
    )
