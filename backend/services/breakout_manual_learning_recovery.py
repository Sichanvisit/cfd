"""Build replay-backfill recovery windows for breakout manual-only review cases."""

from __future__ import annotations

import csv
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd


BREAKOUT_MANUAL_LEARNING_RECOVERY_VERSION = "breakout_manual_learning_recovery_v1"
BREAKOUT_MANUAL_LEARNING_RECOVERY_COLUMNS = [
    "queue_id",
    "symbol",
    "recovery_type",
    "priority",
    "window_start",
    "window_end",
    "accepted_manual_rows",
    "all_manual_rows",
    "entry_row_count",
    "temporal_status",
    "recommended_action",
    "reason_summary",
    "coverage_state",
    "source_case_count",
    "source_episode_ids",
    "source_action_targets",
    "source_continuation_targets",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _parse_local_timestamp(value: object) -> pd.Timestamp | None:
    text = _to_text(value, "")
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    stamp = pd.Timestamp(parsed)
    if stamp.tzinfo is not None:
        return stamp.tz_convert("Asia/Seoul").tz_localize(None)
    return stamp


def _format_local_timestamp(value: pd.Timestamp | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).isoformat(timespec="seconds")


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _case_window(
    row: Mapping[str, Any],
    *,
    pad_before_minutes: int,
    pad_after_minutes: int,
    fallback_minutes: int,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    anchor_time = _parse_local_timestamp(row.get("anchor_time"))
    ideal_entry_time = _parse_local_timestamp(row.get("ideal_entry_time"))
    ideal_exit_time = _parse_local_timestamp(row.get("ideal_exit_time"))
    known_times = [stamp for stamp in (anchor_time, ideal_entry_time, ideal_exit_time) if stamp is not None]
    if not known_times:
        return None, None

    start_base = min(known_times)
    end_base = max(known_times)
    if start_base == end_base:
        start_base = start_base - timedelta(minutes=int(fallback_minutes))
        end_base = end_base + timedelta(minutes=int(fallback_minutes))

    return (
        start_base - timedelta(minutes=int(pad_before_minutes)),
        end_base + timedelta(minutes=int(pad_after_minutes)),
    )


def _merge_overlapping_review_cases(
    frame: pd.DataFrame,
    *,
    pad_before_minutes: int,
    pad_after_minutes: int,
    merge_gap_minutes: int,
    fallback_minutes: int,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []

    working = frame.copy()
    windows = working.apply(
        lambda row: _case_window(
            row.to_dict(),
            pad_before_minutes=pad_before_minutes,
            pad_after_minutes=pad_after_minutes,
            fallback_minutes=fallback_minutes,
        ),
        axis=1,
    )
    working["window_start_ts"] = windows.apply(lambda item: item[0])
    working["window_end_ts"] = windows.apply(lambda item: item[1])
    working = working[working["window_start_ts"].notna() & working["window_end_ts"].notna()].copy()
    if working.empty:
        return []

    merged_groups: list[dict[str, Any]] = []
    merge_gap = timedelta(minutes=int(merge_gap_minutes))
    for symbol, symbol_rows in working.groupby("symbol", sort=True):
        ordered = symbol_rows.sort_values(["window_start_ts", "window_end_ts"], kind="stable")
        current_rows: list[dict[str, Any]] = []
        current_start: pd.Timestamp | None = None
        current_end: pd.Timestamp | None = None
        for _, review_row in ordered.iterrows():
            row = review_row.to_dict()
            row_start = row.get("window_start_ts")
            row_end = row.get("window_end_ts")
            if current_start is None or current_end is None:
                current_rows = [row]
                current_start = row_start
                current_end = row_end
                continue
            if row_start <= current_end + merge_gap:
                current_rows.append(row)
                current_end = max(current_end, row_end)
                continue
            merged_groups.append(
                {
                    "symbol": symbol,
                    "window_start_ts": current_start,
                    "window_end_ts": current_end,
                    "source_rows": current_rows,
                }
            )
            current_rows = [row]
            current_start = row_start
            current_end = row_end
        if current_rows and current_start is not None and current_end is not None:
            merged_groups.append(
                {
                    "symbol": symbol,
                    "window_start_ts": current_start,
                    "window_end_ts": current_end,
                    "source_rows": current_rows,
                }
            )
    return merged_groups


def build_breakout_manual_learning_recovery_queue(
    learning_rows: Sequence[Mapping[str, Any]] | None,
    *,
    coverage_states: Sequence[str] | None = None,
    pad_before_minutes: int = 15,
    pad_after_minutes: int = 15,
    merge_gap_minutes: int = 5,
    fallback_minutes: int = 20,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    frame = pd.DataFrame(list(learning_rows or []))
    wanted_states = {str(item).strip() for item in (coverage_states or ("manual_only_review_case",)) if str(item).strip()}
    if frame.empty:
        summary = {
            "breakout_manual_learning_recovery_version": BREAKOUT_MANUAL_LEARNING_RECOVERY_VERSION,
            "queue_count": 0,
            "symbol_counts": {},
            "coverage_state_counts": {},
            "action_target_counts": {},
            "continuation_target_counts": {},
            "pad_before_minutes": int(pad_before_minutes),
            "pad_after_minutes": int(pad_after_minutes),
            "merge_gap_minutes": int(merge_gap_minutes),
        }
        return [], summary

    for column in (
        "coverage_state",
        "symbol",
        "action_target",
        "continuation_target",
        "episode_id",
        "anchor_time",
        "ideal_entry_time",
        "ideal_exit_time",
    ):
        if column not in frame.columns:
            frame[column] = ""
    filtered = frame[frame["coverage_state"].fillna("").astype(str).isin(wanted_states)].copy()
    if filtered.empty:
        summary = {
            "breakout_manual_learning_recovery_version": BREAKOUT_MANUAL_LEARNING_RECOVERY_VERSION,
            "queue_count": 0,
            "symbol_counts": {},
            "coverage_state_counts": {},
            "action_target_counts": {},
            "continuation_target_counts": {},
            "pad_before_minutes": int(pad_before_minutes),
            "pad_after_minutes": int(pad_after_minutes),
            "merge_gap_minutes": int(merge_gap_minutes),
        }
        return [], summary

    filtered["symbol"] = filtered["symbol"].fillna("").astype(str).str.upper().str.strip()
    merged_groups = _merge_overlapping_review_cases(
        filtered,
        pad_before_minutes=pad_before_minutes,
        pad_after_minutes=pad_after_minutes,
        merge_gap_minutes=merge_gap_minutes,
        fallback_minutes=fallback_minutes,
    )

    queue_rows: list[dict[str, Any]] = []
    for group in merged_groups:
        source_rows = list(group.get("source_rows") or [])
        symbol = _to_text(group.get("symbol"), "").upper()
        start_ts = group.get("window_start_ts")
        end_ts = group.get("window_end_ts")
        if not source_rows or not symbol or start_ts is None or end_ts is None:
            continue

        episode_ids = sorted({_to_text(row.get("episode_id"), "") for row in source_rows if _to_text(row.get("episode_id"), "")})
        action_targets = sorted({_to_text(row.get("action_target"), "") for row in source_rows if _to_text(row.get("action_target"), "")})
        continuation_targets = sorted(
            {_to_text(row.get("continuation_target"), "") for row in source_rows if _to_text(row.get("continuation_target"), "")}
        )
        coverage_state_values = sorted({_to_text(row.get("coverage_state"), "") for row in source_rows if _to_text(row.get("coverage_state"), "")})
        queue_rows.append(
            {
                "queue_id": (
                    "breakout_learning_recovery::"
                    f"{symbol}::{_format_local_timestamp(start_ts).replace(':', '_')}::{_format_local_timestamp(end_ts).replace(':', '_')}"
                ),
                "symbol": symbol,
                "recovery_type": "replay_backfill_entry_decisions",
                "priority": "high",
                "window_start": _format_local_timestamp(start_ts),
                "window_end": _format_local_timestamp(end_ts),
                "accepted_manual_rows": 0,
                "all_manual_rows": int(len(source_rows)),
                "entry_row_count": 0,
                "temporal_status": "manual_only_review_case",
                "recommended_action": "backfill entry_decisions/detail around manual breakout review cases for runtime alignment",
                "reason_summary": (
                    f"manual_only_breakout_review_cases={len(source_rows)}; "
                    f"action_targets={','.join(action_targets) or 'unknown'}; "
                    f"continuation_targets={','.join(continuation_targets) or 'unknown'}"
                ),
                "coverage_state": "|".join(coverage_state_values),
                "source_case_count": int(len(source_rows)),
                "source_episode_ids": "|".join(episode_ids),
                "source_action_targets": "|".join(action_targets),
                "source_continuation_targets": "|".join(continuation_targets),
            }
        )

    queue_rows = sorted(
        queue_rows,
        key=lambda item: (
            _to_text(item.get("symbol"), ""),
            _to_text(item.get("window_start"), ""),
            _to_text(item.get("queue_id"), ""),
        ),
    )
    summary = {
        "breakout_manual_learning_recovery_version": BREAKOUT_MANUAL_LEARNING_RECOVERY_VERSION,
        "queue_count": int(len(queue_rows)),
        "symbol_counts": {},
        "coverage_state_counts": {},
        "action_target_counts": {},
        "continuation_target_counts": {},
        "pad_before_minutes": int(pad_before_minutes),
        "pad_after_minutes": int(pad_after_minutes),
        "merge_gap_minutes": int(merge_gap_minutes),
    }
    for raw_row in filtered.to_dict("records"):
        symbol = _to_text(raw_row.get("symbol"), "")
        coverage_state = _to_text(raw_row.get("coverage_state"), "")
        action_target = _to_text(raw_row.get("action_target"), "")
        continuation_target = _to_text(raw_row.get("continuation_target"), "")
        summary["symbol_counts"][symbol] = int(summary["symbol_counts"].get(symbol, 0)) + 1
        summary["coverage_state_counts"][coverage_state] = int(summary["coverage_state_counts"].get(coverage_state, 0)) + 1
        summary["action_target_counts"][action_target] = int(summary["action_target_counts"].get(action_target, 0)) + 1
        summary["continuation_target_counts"][continuation_target] = int(
            summary["continuation_target_counts"].get(continuation_target, 0)
        ) + 1
    return queue_rows, summary


def render_breakout_manual_learning_recovery_markdown(
    summary: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]] | None,
) -> str:
    lines = [
        "# Breakout Manual Learning Recovery Queue",
        "",
        f"- version: `{_to_text(summary.get('breakout_manual_learning_recovery_version', ''), '')}`",
        f"- queue_count: `{int(summary.get('queue_count', 0) or 0)}`",
        f"- symbol_counts: `{summary.get('symbol_counts', {})}`",
        f"- coverage_state_counts: `{summary.get('coverage_state_counts', {})}`",
        f"- action_target_counts: `{summary.get('action_target_counts', {})}`",
        f"- continuation_target_counts: `{summary.get('continuation_target_counts', {})}`",
        "",
    ]
    for row in rows or []:
        lines.extend(
            [
                f"## {row.get('queue_id', '')}",
                "",
                f"- symbol: `{row.get('symbol', '')}`",
                f"- window: `{row.get('window_start', '')}` -> `{row.get('window_end', '')}`",
                f"- source_case_count: `{row.get('source_case_count', 0)}`",
                f"- source_episode_ids: `{row.get('source_episode_ids', '')}`",
                f"- source_action_targets: `{row.get('source_action_targets', '')}`",
                f"- source_continuation_targets: `{row.get('source_continuation_targets', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_breakout_manual_learning_recovery_queue(
    *,
    learning_bridge_path: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
    coverage_states: Sequence[str] | None = None,
    pad_before_minutes: int = 15,
    pad_after_minutes: int = 15,
    merge_gap_minutes: int = 5,
    fallback_minutes: int = 20,
) -> dict[str, Any]:
    learning_csv = _resolve_project_path(
        learning_bridge_path,
        Path("data/analysis/breakout_event/breakout_manual_learning_bridge_latest.csv"),
    )
    csv_output_file = _resolve_project_path(
        csv_output_path,
        Path("data/analysis/breakout_event/breakout_manual_learning_recovery_latest.csv"),
    )
    json_output_file = _resolve_project_path(
        json_output_path,
        Path("data/analysis/breakout_event/breakout_manual_learning_recovery_latest.json"),
    )
    markdown_output_file = _resolve_project_path(
        markdown_output_path,
        Path("data/analysis/breakout_event/breakout_manual_learning_recovery_latest.md"),
    )

    learning_rows = _load_csv_rows(learning_csv)
    rows, summary = build_breakout_manual_learning_recovery_queue(
        learning_rows,
        coverage_states=coverage_states,
        pad_before_minutes=int(pad_before_minutes),
        pad_after_minutes=int(pad_after_minutes),
        merge_gap_minutes=int(merge_gap_minutes),
        fallback_minutes=int(fallback_minutes),
    )
    payload = {
        "summary": summary,
        "rows": rows,
        "learning_bridge_path": str(learning_csv),
        "csv_output_path": str(csv_output_file),
        "json_output_path": str(json_output_file),
        "markdown_output_path": str(markdown_output_file),
    }

    csv_output_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_output_file.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BREAKOUT_MANUAL_LEARNING_RECOVERY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in BREAKOUT_MANUAL_LEARNING_RECOVERY_COLUMNS})
    json_output_file.parent.mkdir(parents=True, exist_ok=True)
    json_output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_file.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_file.write_text(
        render_breakout_manual_learning_recovery_markdown(summary, rows),
        encoding="utf-8",
    )
    return payload
