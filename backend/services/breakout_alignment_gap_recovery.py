"""Build new backfill recovery windows for breakout manual-learning cases without replay job windows."""

from __future__ import annotations

import csv
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd


BREAKOUT_ALIGNMENT_GAP_RECOVERY_VERSION = "breakout_alignment_gap_recovery_v1"
BREAKOUT_ALIGNMENT_GAP_RECOVERY_COLUMNS = [
    "queue_id",
    "symbol",
    "recovery_type",
    "priority",
    "window_start",
    "window_end",
    "coverage_state",
    "source_case_count",
    "source_episode_ids",
    "source_action_targets",
    "source_continuation_targets",
    "reason_summary",
    "recommended_action",
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
    stamps = [
        _parse_local_timestamp(row.get("anchor_time")),
        _parse_local_timestamp(row.get("ideal_entry_time")),
        _parse_local_timestamp(row.get("ideal_exit_time")),
    ]
    known = [stamp for stamp in stamps if stamp is not None]
    if not known:
        return None, None
    start = min(known)
    end = max(known)
    if start == end:
        start -= timedelta(minutes=int(fallback_minutes))
        end += timedelta(minutes=int(fallback_minutes))
    return (
        start - timedelta(minutes=int(pad_before_minutes)),
        end + timedelta(minutes=int(pad_after_minutes)),
    )


def _emit_gap_queue_row(
    symbol: str,
    source_rows: Sequence[Mapping[str, Any]],
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> dict[str, Any]:
    source_episode_ids = "|".join(_to_text(row.get("episode_id"), "") for row in source_rows if _to_text(row.get("episode_id"), ""))
    source_action_targets = "|".join(sorted({_to_text(row.get("action_target"), "") for row in source_rows if _to_text(row.get("action_target"), "")}))
    source_continuation_targets = "|".join(sorted({_to_text(row.get("continuation_target"), "") for row in source_rows if _to_text(row.get("continuation_target"), "")}))
    reasons = sorted({_to_text(row.get("reason_summary"), "") for row in source_rows if _to_text(row.get("reason_summary"), "")})
    return {
        "queue_id": f"breakout_alignment_gap::{symbol}::{_format_local_timestamp(window_start).replace(':', '_')}::{_format_local_timestamp(window_end).replace(':', '_')}",
        "symbol": symbol,
        "recovery_type": "replay_backfill_entry_decisions",
        "priority": "high",
        "window_start": _format_local_timestamp(window_start),
        "window_end": _format_local_timestamp(window_end),
        "coverage_state": "manual_unmatched_alignment_gap",
        "source_case_count": int(len(source_rows)),
        "source_episode_ids": source_episode_ids,
        "source_action_targets": source_action_targets,
        "source_continuation_targets": source_continuation_targets,
        "reason_summary": "|".join(reasons),
        "recommended_action": "create_additional_backfill_window_or_rerun_missing_replay_dataset",
        "_source_rows": list(source_rows),
    }


def build_breakout_alignment_gap_recovery_queue(
    alignment_rows: Sequence[Mapping[str, Any]] | None,
    *,
    pad_before_minutes: int = 20,
    pad_after_minutes: int = 20,
    merge_gap_minutes: int = 10,
    fallback_minutes: int = 20,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    frame = pd.DataFrame(list(alignment_rows or []))
    if frame.empty:
        return [], {
            "contract_version": BREAKOUT_ALIGNMENT_GAP_RECOVERY_VERSION,
            "queue_count": 0,
            "reason_counts": {},
            "symbol_counts": {},
        }

    for column in (
        "symbol",
        "coverage_state",
        "episode_id",
        "action_target",
        "continuation_target",
        "reason_summary",
        "anchor_time",
        "ideal_entry_time",
        "ideal_exit_time",
    ):
        if column not in frame.columns:
            frame[column] = ""

    filtered = frame[
        frame["reason_summary"].fillna("").astype(str).isin(
            {
                "no_replay_job_window_for_manual_case",
                "job_window_exists_but_replay_dataset_missing",
            }
        )
    ].copy()
    if filtered.empty:
        return [], {
            "contract_version": BREAKOUT_ALIGNMENT_GAP_RECOVERY_VERSION,
            "queue_count": 0,
            "reason_counts": {},
            "symbol_counts": {},
        }

    filtered["symbol"] = filtered["symbol"].fillna("").astype(str).str.upper().str.strip()
    filtered["window_pair"] = filtered.apply(
        lambda row: _case_window(
            row.to_dict(),
            pad_before_minutes=pad_before_minutes,
            pad_after_minutes=pad_after_minutes,
            fallback_minutes=fallback_minutes,
        ),
        axis=1,
    )
    filtered["window_start_ts"] = filtered["window_pair"].apply(lambda item: item[0])
    filtered["window_end_ts"] = filtered["window_pair"].apply(lambda item: item[1])
    filtered = filtered[filtered["window_start_ts"].notna() & filtered["window_end_ts"].notna()].copy()
    if filtered.empty:
        return [], {
            "contract_version": BREAKOUT_ALIGNMENT_GAP_RECOVERY_VERSION,
            "queue_count": 0,
            "reason_counts": {},
            "symbol_counts": {},
        }

    merge_gap = timedelta(minutes=int(merge_gap_minutes))
    rows: list[dict[str, Any]] = []
    for symbol, group in filtered.groupby("symbol", sort=True):
        ordered = group.sort_values(["window_start_ts", "window_end_ts"], kind="stable")
        current_rows: list[dict[str, Any]] = []
        current_start: pd.Timestamp | None = None
        current_end: pd.Timestamp | None = None
        for _, series in ordered.iterrows():
            row = series.to_dict()
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
            rows.append(_emit_gap_queue_row(symbol, current_rows, current_start, current_end))
            current_rows = [row]
            current_start = row_start
            current_end = row_end
        if current_rows and current_start is not None and current_end is not None:
            rows.append(_emit_gap_queue_row(symbol, current_rows, current_start, current_end))

    summary = {
        "contract_version": BREAKOUT_ALIGNMENT_GAP_RECOVERY_VERSION,
        "queue_count": len(rows),
        "reason_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(src.get("reason_summary"), "") for row in rows for src in row.get("_source_rows", [])]).value_counts().items()
            if str(key)
        },
        "symbol_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(row.get("symbol"), "") for row in rows]).value_counts().items()
            if str(key)
        },
        "pad_before_minutes": int(pad_before_minutes),
        "pad_after_minutes": int(pad_after_minutes),
        "merge_gap_minutes": int(merge_gap_minutes),
    }
    for row in rows:
        row.pop("_source_rows", None)
    return rows, summary


def render_breakout_alignment_gap_recovery_markdown(payload: Mapping[str, Any]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload, Mapping) else {}
    rows = payload.get("rows", []) if isinstance(payload, Mapping) else []
    lines = [
        "# Breakout Alignment Gap Recovery",
        "",
        f"- contract_version: `{_to_text(summary.get('contract_version'), BREAKOUT_ALIGNMENT_GAP_RECOVERY_VERSION)}`",
        f"- queue_count: `{summary.get('queue_count', 0)}`",
        f"- symbol_counts: `{summary.get('symbol_counts', {})}`",
        f"- reason_counts: `{summary.get('reason_counts', {})}`",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {_to_text(row.get('queue_id'), '')}",
                "",
                f"- symbol: `{_to_text(row.get('symbol'), '')}`",
                f"- window: `{_to_text(row.get('window_start'), '')}` -> `{_to_text(row.get('window_end'), '')}`",
                f"- source_case_count: `{_to_text(row.get('source_case_count'), '')}`",
                f"- source_episode_ids: `{_to_text(row.get('source_episode_ids'), '')}`",
                f"- reason_summary: `{_to_text(row.get('reason_summary'), '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_breakout_alignment_gap_recovery_report(
    *,
    alignment_csv_path: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
    pad_before_minutes: int = 20,
    pad_after_minutes: int = 20,
    merge_gap_minutes: int = 10,
    fallback_minutes: int = 20,
) -> dict[str, Any]:
    project_root = _project_root()
    alignment_path = _resolve_project_path(
        alignment_csv_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_replay_learning_alignment_latest.csv",
    )
    csv_path = _resolve_project_path(
        csv_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_alignment_gap_recovery_latest.csv",
    )
    json_path = _resolve_project_path(
        json_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_alignment_gap_recovery_latest.json",
    )
    markdown_path = _resolve_project_path(
        markdown_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_alignment_gap_recovery_latest.md",
    )

    rows, summary = build_breakout_alignment_gap_recovery_queue(
        _load_csv_rows(alignment_path),
        pad_before_minutes=pad_before_minutes,
        pad_after_minutes=pad_after_minutes,
        merge_gap_minutes=merge_gap_minutes,
        fallback_minutes=fallback_minutes,
    )
    payload = {
        "summary": summary,
        "rows": rows,
        "alignment_csv_path": str(alignment_path),
        "csv_output_path": str(csv_path),
        "json_output_path": str(json_path),
        "markdown_output_path": str(markdown_path),
    }

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BREAKOUT_ALIGNMENT_GAP_RECOVERY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in BREAKOUT_ALIGNMENT_GAP_RECOVERY_COLUMNS})

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_breakout_alignment_gap_recovery_markdown(payload), encoding="utf-8")
    return payload
