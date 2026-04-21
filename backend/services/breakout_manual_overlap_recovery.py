"""Build actionable recovery windows for breakout manual overlap gaps."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence


BREAKOUT_MANUAL_OVERLAP_RECOVERY_VERSION = "breakout_manual_overlap_recovery_v1"
BREAKOUT_MANUAL_OVERLAP_RECOVERY_COLUMNS = [
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
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_epoch(value: object) -> float | None:
    if value in ("", None):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _to_str(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader if isinstance(row, Mapping)]


def _row_time(row: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(row)
    for key in ("anchor_time", "time", "signal_bar_ts"):
        resolved = _to_epoch(mapped.get(key))
        if resolved is not None:
            return float(resolved)
    return 0.0


def _time_bounds(rows: Sequence[Mapping[str, Any]] | None, *, key: str) -> dict[str, Any]:
    selected = []
    for row in rows or []:
        mapped = _as_mapping(row)
        if key == "manual":
            timestamp = _to_epoch(mapped.get("anchor_time"))
        else:
            timestamp = _to_epoch(mapped.get("time", mapped.get("signal_bar_ts")))
        if timestamp is not None and float(timestamp) > 0.0:
            selected.append(float(timestamp))
    if not selected:
        return {"min_ts": 0.0, "max_ts": 0.0, "count": 0}
    return {
        "min_ts": float(min(selected)),
        "max_ts": float(max(selected)),
        "count": int(len(selected)),
    }


def _iso_from_epoch(value: float) -> str:
    if value <= 0.0:
        return ""
    return datetime.fromtimestamp(float(value)).isoformat(timespec="seconds")


def _symbol_index(rows: Sequence[Mapping[str, Any]] | None, *, accepted_only: bool | None = None) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for raw_row in rows or []:
        row = _as_mapping(raw_row)
        symbol = _to_str(row.get("symbol")).upper()
        if not symbol:
            continue
        if accepted_only is True and not _to_str(row.get("review_status")).lower().startswith("accepted"):
            continue
        index.setdefault(symbol, []).append(row)
    for symbol, symbol_rows in index.items():
        index[symbol] = sorted(symbol_rows, key=_row_time)
    return index


def _temporal_status(manual_bounds: Mapping[str, Any] | None, entry_bounds: Mapping[str, Any] | None) -> str:
    manual_min = _to_float(_as_mapping(manual_bounds).get("min_ts"))
    manual_max = _to_float(_as_mapping(manual_bounds).get("max_ts"))
    entry_min = _to_float(_as_mapping(entry_bounds).get("min_ts"))
    entry_max = _to_float(_as_mapping(entry_bounds).get("max_ts"))
    if manual_min <= 0.0 and entry_min <= 0.0:
        return "missing_both"
    if manual_min <= 0.0:
        return "missing_manual"
    if entry_min <= 0.0:
        return "missing_entry"
    if manual_max < entry_min:
        return "manual_before_entry_window"
    if entry_max < manual_min:
        return "entry_before_manual_window"
    return "overlap"


def _window_with_padding(bounds: Mapping[str, Any] | None, *, pad_minutes: int = 10) -> tuple[str, str]:
    min_ts = _to_float(_as_mapping(bounds).get("min_ts"))
    max_ts = _to_float(_as_mapping(bounds).get("max_ts"))
    if min_ts <= 0.0 or max_ts <= 0.0:
        return "", ""
    start = datetime.fromtimestamp(min_ts) - timedelta(minutes=int(pad_minutes))
    end = datetime.fromtimestamp(max_ts) + timedelta(minutes=int(pad_minutes))
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


def _entry_collection_window(entry_bounds: Mapping[str, Any] | None, *, review_window_minutes: int) -> tuple[str, str]:
    min_ts = _to_float(_as_mapping(entry_bounds).get("min_ts"))
    max_ts = _to_float(_as_mapping(entry_bounds).get("max_ts"))
    if min_ts <= 0.0 or max_ts <= 0.0:
        return "", ""
    start = datetime.fromtimestamp(min_ts)
    capped_end = min(
        datetime.fromtimestamp(max_ts),
        start + timedelta(minutes=int(review_window_minutes)),
    )
    return start.isoformat(timespec="seconds"), capped_end.isoformat(timespec="seconds")


def build_breakout_manual_overlap_recovery_queue(
    *,
    entry_rows: Sequence[Mapping[str, Any]] | None,
    manual_rows: Sequence[Mapping[str, Any]] | None,
    review_window_minutes: int = 90,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    accepted_manual_by_symbol = _symbol_index(manual_rows, accepted_only=True)
    all_manual_by_symbol = _symbol_index(manual_rows, accepted_only=False)
    entry_by_symbol = _symbol_index(entry_rows, accepted_only=None)
    symbols = sorted(set(all_manual_by_symbol) | set(entry_by_symbol))

    queue_rows: list[dict[str, Any]] = []
    for symbol in symbols:
        accepted_manual = accepted_manual_by_symbol.get(symbol, [])
        all_manual = all_manual_by_symbol.get(symbol, [])
        entry = entry_by_symbol.get(symbol, [])
        accepted_bounds = _time_bounds(accepted_manual, key="manual")
        all_manual_bounds = _time_bounds(all_manual, key="manual")
        entry_bounds = _time_bounds(entry, key="entry")
        status = _temporal_status(accepted_bounds, entry_bounds)
        accepted_count = int(len(accepted_manual))
        all_count = int(len(all_manual))
        entry_count = int(len(entry))

        if status == "manual_before_entry_window" and accepted_count > 0:
            window_start, window_end = _window_with_padding(accepted_bounds, pad_minutes=10)
            queue_rows.append(
                {
                    "queue_id": f"breakout_recovery::{symbol}::replay_backfill",
                    "symbol": symbol,
                    "recovery_type": "replay_backfill_entry_decisions",
                    "priority": "high",
                    "window_start": window_start,
                    "window_end": window_end,
                    "accepted_manual_rows": accepted_count,
                    "all_manual_rows": all_count,
                    "entry_row_count": entry_count,
                    "temporal_status": status,
                    "recommended_action": "replay older entry_decisions for accepted manual breakout window",
                    "reason_summary": "accepted_manual_window_precedes_entry_window",
                }
            )
            if entry_count > 0:
                start, end = _entry_collection_window(entry_bounds, review_window_minutes=review_window_minutes)
                queue_rows.append(
                    {
                        "queue_id": f"breakout_recovery::{symbol}::collect_new_manual",
                        "symbol": symbol,
                        "recovery_type": "collect_new_manual_overlap",
                        "priority": "medium",
                        "window_start": start,
                        "window_end": end,
                        "accepted_manual_rows": accepted_count,
                        "all_manual_rows": all_count,
                        "entry_row_count": entry_count,
                        "temporal_status": status,
                        "recommended_action": "annotate fresh breakout/manual wait episodes inside current entry_decision window",
                        "reason_summary": "current_entry_window_has_no_accepted_manual_overlap",
                    }
                )
        elif status == "missing_entry" and accepted_count > 0:
            window_start, window_end = _window_with_padding(accepted_bounds, pad_minutes=10)
            queue_rows.append(
                {
                    "queue_id": f"breakout_recovery::{symbol}::missing_entry_backfill",
                    "symbol": symbol,
                    "recovery_type": "replay_backfill_entry_decisions",
                    "priority": "high",
                    "window_start": window_start,
                    "window_end": window_end,
                    "accepted_manual_rows": accepted_count,
                    "all_manual_rows": all_count,
                    "entry_row_count": entry_count,
                    "temporal_status": status,
                    "recommended_action": "generate entry_decisions for manual breakout window before alignment",
                    "reason_summary": "manual_available_but_entry_rows_missing",
                }
            )
        elif status == "missing_manual" and entry_count > 0:
            start, end = _entry_collection_window(entry_bounds, review_window_minutes=review_window_minutes)
            queue_rows.append(
                {
                    "queue_id": f"breakout_recovery::{symbol}::seed_manual",
                    "symbol": symbol,
                    "recovery_type": "collect_new_manual_overlap",
                    "priority": "high",
                    "window_start": start,
                    "window_end": end,
                    "accepted_manual_rows": accepted_count,
                    "all_manual_rows": all_count,
                    "entry_row_count": entry_count,
                    "temporal_status": status,
                    "recommended_action": "annotate first breakout/manual overlap window from current entry_decisions",
                    "reason_summary": "entry_window_available_without_manual_annotations",
                }
            )
        elif status == "overlap" and accepted_count <= 0 and all_count > 0 and entry_count > 0:
            start, end = _entry_collection_window(entry_bounds, review_window_minutes=review_window_minutes)
            queue_rows.append(
                {
                    "queue_id": f"breakout_recovery::{symbol}::upgrade_manual",
                    "symbol": symbol,
                    "recovery_type": "upgrade_manual_overlap_quality",
                    "priority": "medium",
                    "window_start": start,
                    "window_end": end,
                    "accepted_manual_rows": accepted_count,
                    "all_manual_rows": all_count,
                    "entry_row_count": entry_count,
                    "temporal_status": status,
                    "recommended_action": "upgrade non-accepted manual overlap rows in the shared window",
                    "reason_summary": "overlap_exists_but_no_accepted_manual_rows",
                }
            )

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    queue_rows = sorted(
        queue_rows,
        key=lambda item: (
            priority_rank.get(_to_str(item.get("priority")).lower(), 3),
            _to_str(item.get("symbol")),
            _to_str(item.get("window_start")),
        ),
    )

    summary = {
        "breakout_manual_overlap_recovery_version": BREAKOUT_MANUAL_OVERLAP_RECOVERY_VERSION,
        "queue_count": int(len(queue_rows)),
        "symbol_counts": {},
        "recovery_type_counts": {},
        "priority_counts": {},
        "review_window_minutes": int(review_window_minutes),
    }
    for row in queue_rows:
        summary["symbol_counts"][_to_str(row.get("symbol"))] = int(summary["symbol_counts"].get(_to_str(row.get("symbol")), 0)) + 1
        summary["recovery_type_counts"][_to_str(row.get("recovery_type"))] = int(
            summary["recovery_type_counts"].get(_to_str(row.get("recovery_type")), 0)
        ) + 1
        summary["priority_counts"][_to_str(row.get("priority"))] = int(summary["priority_counts"].get(_to_str(row.get("priority")), 0)) + 1
    return queue_rows, summary


def render_breakout_manual_overlap_recovery_markdown(
    summary: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]] | None,
) -> str:
    lines = [
        "# Breakout Manual Overlap Recovery Queue",
        "",
        f"- version: `{summary.get('breakout_manual_overlap_recovery_version', '')}`",
        f"- queue_count: `{summary.get('queue_count', 0)}`",
        f"- symbol_counts: `{summary.get('symbol_counts', {})}`",
        f"- recovery_type_counts: `{summary.get('recovery_type_counts', {})}`",
        f"- priority_counts: `{summary.get('priority_counts', {})}`",
        "",
        "## Queue",
        "",
    ]
    if not rows:
        lines.append("- none")
    else:
        for row in rows:
            mapped = _as_mapping(row)
            lines.extend(
                [
                    f"### {mapped.get('symbol', '')} :: {mapped.get('recovery_type', '')}",
                    "",
                    f"- priority: `{mapped.get('priority', '')}`",
                    f"- window: `{mapped.get('window_start', '')}` -> `{mapped.get('window_end', '')}`",
                    f"- accepted_manual_rows: `{mapped.get('accepted_manual_rows', 0)}`",
                    f"- entry_row_count: `{mapped.get('entry_row_count', 0)}`",
                    f"- temporal_status: `{mapped.get('temporal_status', '')}`",
                    f"- action: `{mapped.get('recommended_action', '')}`",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_breakout_manual_overlap_recovery_queue(
    *,
    entry_decision_path: str | Path | None = None,
    manual_path: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
    review_window_minutes: int = 90,
) -> dict[str, Any]:
    entry_path = _resolve_project_path(entry_decision_path, Path("data/trades/entry_decisions.csv"))
    manual_file = _resolve_project_path(manual_path, Path("data/manual_annotations/manual_wait_teacher_annotations.csv"))
    csv_output_file = _resolve_project_path(
        csv_output_path,
        Path("data/analysis/breakout_event/breakout_manual_overlap_recovery_latest.csv"),
    )
    json_output_file = _resolve_project_path(
        json_output_path,
        Path("data/analysis/breakout_event/breakout_manual_overlap_recovery_latest.json"),
    )
    markdown_output_file = _resolve_project_path(
        markdown_output_path,
        Path("data/analysis/breakout_event/breakout_manual_overlap_recovery_latest.md"),
    )

    entry_rows = _load_csv_rows(entry_path)
    manual_rows = _load_csv_rows(manual_file)
    rows, summary = build_breakout_manual_overlap_recovery_queue(
        entry_rows=entry_rows,
        manual_rows=manual_rows,
        review_window_minutes=int(review_window_minutes),
    )
    payload = {
        "summary": summary,
        "rows": rows,
        "entry_decision_path": str(entry_path),
        "manual_path": str(manual_file),
        "csv_output_path": str(csv_output_file),
        "json_output_path": str(json_output_file),
        "markdown_output_path": str(markdown_output_file),
    }

    csv_output_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_output_file.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BREAKOUT_MANUAL_OVERLAP_RECOVERY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in BREAKOUT_MANUAL_OVERLAP_RECOVERY_COLUMNS})
    json_output_file.parent.mkdir(parents=True, exist_ok=True)
    json_output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_file.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_file.write_text(
        render_breakout_manual_overlap_recovery_markdown(summary, rows),
        encoding="utf-8",
    )
    return payload
