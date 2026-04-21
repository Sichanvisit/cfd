"""Materialize executable backfill bundles for breakout replay recovery windows."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from backend.services.manual_wait_teacher_annotation_schema import MANUAL_WAIT_TEACHER_ANNOTATION_COLUMNS
from backend.services.storage_compaction import resolve_entry_decision_detail_path, resolve_entry_decision_row_key


BREAKOUT_BACKFILL_RUNNER_SCAFFOLD_VERSION = "breakout_backfill_runner_scaffold_v1"
BREAKOUT_BACKFILL_RUNNER_COLUMNS = [
    "job_id",
    "queue_id",
    "recovery_type",
    "symbol",
    "priority",
    "window_start",
    "window_end",
    "coverage_state",
    "coverage_gap_count",
    "selected_source_count",
    "selected_source_names",
    "scoped_entry_row_count",
    "scoped_detail_row_count",
    "manual_anchor_rows",
    "ready_for_replay_execution",
    "external_source_required",
    "job_dir",
    "manifest_path",
    "runner_script_path",
    "replay_command",
]


_KST = ZoneInfo("Asia/Seoul")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _parse_local_dt(value: object) -> datetime | None:
    text = _to_text(value, "")
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(_KST).replace(tzinfo=None)
    return dt


def _local_iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(timespec="seconds")


def _safe_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value, "").lower()
    return text in {"1", "true", "yes", "y"}


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _load_queue_rows(paths: Sequence[Path]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    ordered_rows: list[dict[str, Any]] = []
    for path in paths:
        for row in _load_csv_rows(path):
            if _to_text(row.get("recovery_type"), "") != "replay_backfill_entry_decisions":
                continue
            queue_id = _to_text(row.get("queue_id"), "")
            if queue_id and queue_id in merged:
                merged[queue_id].update(row)
                continue
            payload = dict(row)
            if queue_id:
                merged[queue_id] = payload
            ordered_rows.append(payload)
    return ordered_rows


def _merge_manual_rows(
    primary_rows: Sequence[Mapping[str, Any]],
    supplemental_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    ordered_rows: list[dict[str, Any]] = []
    for raw_row in list(primary_rows) + list(supplemental_rows):
        row = dict(raw_row)
        key = _to_text(row.get("episode_id", row.get("annotation_id", "")), "")
        if key and key in merged:
            merged[key].update(row)
            continue
        if key:
            merged[key] = row
        ordered_rows.append(row)
    return ordered_rows


def discover_entry_decision_sources(trades_root: str | Path) -> list[Path]:
    root = Path(trades_root)
    sources: list[Path] = []
    current = root / "entry_decisions.csv"
    if current.exists():
        sources.append(current)
    sources.extend(sorted(root.glob("entry_decisions.legacy_*.csv")))
    return sources


def scan_entry_decision_source_inventory(trades_root: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in discover_entry_decision_sources(trades_root):
        first_dt: datetime | None = None
        last_dt: datetime | None = None
        row_count = 0
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_count += 1
                parsed = _parse_local_dt(row.get("time"))
                if parsed is None:
                    continue
                if first_dt is None:
                    first_dt = parsed
                last_dt = parsed
        rows.append(
            {
                "source_path": str(path),
                "detail_source_path": str(resolve_entry_decision_detail_path(path)),
                "source_name": path.name,
                "source_kind": "current_csv" if path.name == "entry_decisions.csv" else "legacy_csv",
                "row_count": int(row_count),
                "window_start": _local_iso(first_dt),
                "window_end": _local_iso(last_dt),
            }
        )
    return rows


def _window_overlaps(
    source_start: datetime | None,
    source_end: datetime | None,
    target_start: datetime | None,
    target_end: datetime | None,
) -> bool:
    if source_start is None or source_end is None or target_start is None or target_end is None:
        return False
    return bool(source_start <= target_end and source_end >= target_start)


def _merge_intervals(intervals: Sequence[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    ordered = sorted(intervals, key=lambda item: item[0])
    if not ordered:
        return []
    merged: list[tuple[datetime, datetime]] = [ordered[0]]
    for start, end in ordered[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _coverage_gaps(
    intervals: Sequence[tuple[datetime, datetime]],
    *,
    target_start: datetime,
    target_end: datetime,
) -> list[dict[str, str]]:
    if target_start > target_end:
        return []
    gaps: list[dict[str, str]] = []
    cursor = target_start
    for start, end in _merge_intervals(intervals):
        if end < target_start or start > target_end:
            continue
        clipped_start = max(start, target_start)
        clipped_end = min(end, target_end)
        if cursor < clipped_start:
            gaps.append({"gap_start": _local_iso(cursor), "gap_end": _local_iso(clipped_start)})
        cursor = max(cursor, clipped_end)
    if cursor < target_end:
        gaps.append({"gap_start": _local_iso(cursor), "gap_end": _local_iso(target_end)})
    return gaps


def _job_slug(value: str) -> str:
    text = "".join(char.lower() if char.isalnum() else "_" for char in _to_text(value, "job"))
    return "_".join(part for part in text.split("_") if part)


def _row_time(row: Mapping[str, Any] | None) -> datetime | None:
    return _parse_local_dt((row or {}).get("time", ""))


def _manual_time(row: Mapping[str, Any] | None) -> datetime | None:
    return _parse_local_dt((row or {}).get("anchor_time", ""))


def _select_overlapping_sources(
    source_inventory: Sequence[Mapping[str, Any]],
    *,
    window_start: datetime,
    window_end: datetime,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for raw_row in source_inventory:
        row = dict(raw_row)
        start = _parse_local_dt(row.get("window_start"))
        end = _parse_local_dt(row.get("window_end"))
        if _window_overlaps(start, end, window_start, window_end):
            selected.append(row)
    return sorted(selected, key=lambda item: _to_text(item.get("window_start")))


def _read_filtered_entry_rows(
    source_path: Path,
    *,
    symbol: str,
    window_start: datetime,
    window_end: datetime,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    fieldnames: list[str] = []
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            parsed = _row_time(row)
            if parsed is None or parsed < window_start or parsed > window_end:
                continue
            if _to_text(row.get("symbol"), "").upper() != symbol:
                continue
            rows.append(dict(row))
    return rows, fieldnames


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            payload = {field: row.get(field, "") for field in fieldnames}
            writer.writerow(payload)


def _write_manual_subset(
    path: Path,
    *,
    manual_rows: Sequence[Mapping[str, Any]],
    symbol: str,
    window_start: datetime,
    window_end: datetime,
) -> int:
    scoped_rows = []
    for row in manual_rows:
        if _to_text(row.get("symbol"), "").upper() != symbol:
            continue
        parsed = _manual_time(row)
        if parsed is None or parsed < window_start or parsed > window_end:
            continue
        scoped_rows.append(dict(row))
    fieldnames = list(MANUAL_WAIT_TEACHER_ANNOTATION_COLUMNS)
    if scoped_rows:
        extras = [key for key in scoped_rows[0].keys() if key not in fieldnames]
        fieldnames.extend(extras)
    _write_csv(path, scoped_rows, fieldnames=fieldnames)
    return int(len(scoped_rows))


def _filter_detail_rows(
    source_detail_path: Path,
    *,
    wanted_keys: set[str],
) -> list[str]:
    if not source_detail_path.exists() or not wanted_keys:
        return []
    kept_lines: list[str] = []
    with source_detail_path.open("r", encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except Exception:
                continue
            payload = record.get("payload", {}) if isinstance(record, Mapping) else {}
            if not isinstance(payload, Mapping):
                continue
            row_key = _to_text(payload.get("decision_row_key", payload.get("detail_row_key", "")), "")
            if not row_key:
                row_key = resolve_entry_decision_row_key(payload)
            if row_key in wanted_keys:
                kept_lines.append(line)
    return kept_lines


def _write_detail_lines(path: Path, lines: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig") as handle:
        for line in lines:
            handle.write(f"{line}\n")
    return int(len(lines))


def _build_replay_command(
    *,
    project_root: Path,
    scoped_entry_path: Path,
    closed_trade_path: Path,
    replay_output_dir: Path,
    analysis_dir: Path,
    future_bars_output_path: Path,
    symbol: str,
    future_bars_timeframe: str,
    future_bars_lookback_bars: int,
    future_bars_lookahead_bars: int,
) -> str:
    return (
        "python "
        f'"{project_root / "scripts" / "build_replay_dataset.py"}" '
        f'--entry-decisions "{scoped_entry_path}" '
        f'--closed-trades "{closed_trade_path}" '
        '--fetch-mt5-future-bars '
        f'--future-bars-output "{future_bars_output_path}" '
        f"--future-bars-timeframe {future_bars_timeframe} "
        f"--future-bars-lookback-bars {int(future_bars_lookback_bars)} "
        f"--future-bars-lookahead-bars {int(future_bars_lookahead_bars)} "
        f'--output-dir "{replay_output_dir}" '
        f'--analysis-dir "{analysis_dir}" '
        f"--symbol {symbol}"
    )


def _write_runner_script(path: Path, *, project_root: Path, replay_command: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f'Set-Location -LiteralPath "{project_root}"',
            replay_command,
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def _write_run_all_script(path: Path, runner_paths: Sequence[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["$ErrorActionPreference = 'Stop'"]
    for runner_path in runner_paths:
        lines.append(f'& "{runner_path}"')
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def render_breakout_backfill_runner_scaffold_markdown(
    summary: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]] | None,
) -> str:
    lines = [
        "# Breakout Backfill Runner Scaffold",
        "",
        f"- version: `{_to_text(summary.get('contract_version', ''), '')}`",
        f"- jobs: `{int(summary.get('job_count', 0) or 0)}`",
        f"- ready_for_execution: `{int(summary.get('ready_job_count', 0) or 0)}`",
        f"- partial_coverage_jobs: `{int(summary.get('partial_coverage_jobs', 0) or 0)}`",
        f"- external_source_required_jobs: `{int(summary.get('external_source_required_jobs', 0) or 0)}`",
        f"- run_all_script_path: `{_to_text(summary.get('run_all_script_path', ''), '')}`",
        "",
    ]
    for raw_row in rows or []:
        row = dict(raw_row)
        lines.extend(
            [
                f"## {row.get('job_id', '')}",
                "",
                f"- symbol: `{row.get('symbol', '')}`",
                f"- window: `{row.get('window_start', '')}` -> `{row.get('window_end', '')}`",
                f"- coverage_state: `{row.get('coverage_state', '')}`",
                f"- selected_sources: `{row.get('selected_source_names', '')}`",
                f"- scoped_entry_row_count: `{row.get('scoped_entry_row_count', 0)}`",
                f"- scoped_detail_row_count: `{row.get('scoped_detail_row_count', 0)}`",
                f"- runner_script_path: `{row.get('runner_script_path', '')}`",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def write_breakout_backfill_runner_scaffold(
    *,
    queue_path: str | Path | None = None,
    secondary_queue_path: str | Path | None = None,
    manual_path: str | Path | None = None,
    supplemental_manual_path: str | Path | None = None,
    trades_root: str | Path | None = None,
    closed_trades_path: str | Path | None = None,
    bundle_root: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    md_output_path: str | Path | None = None,
    future_bars_timeframe: str = "M1",
    future_bars_lookback_bars: int = 1,
    future_bars_lookahead_bars: int = 12,
) -> dict[str, Any]:
    project_root = _project_root()
    queue_csv = _resolve_project_path(queue_path, Path("data/analysis/breakout_event/breakout_manual_overlap_recovery_latest.csv"))
    secondary_queue_csv = _resolve_project_path(
        secondary_queue_path,
        Path("data/analysis/breakout_event/breakout_manual_learning_recovery_latest.csv"),
    )
    manual_csv = _resolve_project_path(manual_path, Path("data/manual_annotations/manual_wait_teacher_annotations.csv"))
    supplemental_manual_csv = _resolve_project_path(
        supplemental_manual_path,
        Path("data/manual_annotations/breakout_manual_overlap_seed_review_entries.csv"),
    )
    trades_dir = _resolve_project_path(trades_root, Path("data/trades"))
    closed_trade_csv = _resolve_project_path(closed_trades_path, Path("data/trades/trade_closed_history.csv"))
    bundle_root_path = _resolve_project_path(bundle_root, Path("data/backfill/breakout_event"))
    csv_out = _resolve_project_path(csv_output_path, Path("data/analysis/breakout_event/breakout_backfill_runner_scaffold_latest.csv"))
    json_out = _resolve_project_path(json_output_path, Path("data/analysis/breakout_event/breakout_backfill_runner_scaffold_latest.json"))
    md_out = _resolve_project_path(md_output_path, Path("data/analysis/breakout_event/breakout_backfill_runner_scaffold_latest.md"))

    queue_rows = _load_queue_rows([queue_csv, secondary_queue_csv])
    manual_rows = _merge_manual_rows(_load_csv_rows(manual_csv), _load_csv_rows(supplemental_manual_csv))
    source_inventory = scan_entry_decision_source_inventory(trades_dir)

    report_rows: list[dict[str, Any]] = []
    run_all_paths: list[Path] = []

    for queue_row in queue_rows:
        symbol = _to_text(queue_row.get("symbol"), "").upper()
        window_start = _parse_local_dt(queue_row.get("window_start"))
        window_end = _parse_local_dt(queue_row.get("window_end"))
        if window_start is None or window_end is None:
            continue

        selected_sources = _select_overlapping_sources(
            source_inventory,
            window_start=window_start,
            window_end=window_end,
        )
        job_id = _job_slug(
            f"{symbol}_{queue_row.get('window_start', '')}_{queue_row.get('window_end', '')}"
        )
        job_dir = bundle_root_path / "jobs" / job_id
        scoped_entry_path = job_dir / "entry_decisions_scoped.csv"
        scoped_detail_path = job_dir / "entry_decisions_scoped.detail.jsonl"
        manual_subset_path = job_dir / "manual_anchor_subset.csv"
        manifest_path = job_dir / "breakout_backfill_job_manifest.json"
        runner_script_path = job_dir / "run_replay_dataset.ps1"
        replay_output_dir = job_dir / "replay_dataset"
        analysis_dir = job_dir / "analysis"
        future_bars_output_path = job_dir / "future_bars_m1.csv"

        scoped_rows: list[dict[str, Any]] = []
        scoped_fieldnames: list[str] = []
        selected_keys: set[str] = set()
        seen_keys: set[str] = set()
        row_coverage_intervals: list[tuple[datetime, datetime]] = []
        for source in selected_sources:
            source_path = Path(_to_text(source.get("source_path"), ""))
            source_rows, fieldnames = _read_filtered_entry_rows(
                source_path,
                symbol=symbol,
                window_start=window_start,
                window_end=window_end,
            )
            for field in fieldnames:
                if field not in scoped_fieldnames:
                    scoped_fieldnames.append(field)
            row_times = [parsed for parsed in (_row_time(item) for item in source_rows) if parsed is not None]
            if row_times:
                row_coverage_intervals.append((min(row_times), max(row_times)))
            for row in source_rows:
                row_key = _to_text(row.get("decision_row_key"), "")
                if not row_key:
                    row_key = resolve_entry_decision_row_key(row)
                    row["decision_row_key"] = row_key
                if row_key in seen_keys:
                    continue
                seen_keys.add(row_key)
                selected_keys.add(row_key)
                scoped_rows.append(row)

        scoped_rows = sorted(
            scoped_rows,
            key=lambda item: (_local_iso(_row_time(item)), _to_text(item.get("decision_row_key"))),
        )
        gaps = _coverage_gaps(row_coverage_intervals, target_start=window_start, target_end=window_end)
        if not row_coverage_intervals:
            coverage_state = "no_internal_source"
        elif gaps:
            coverage_state = "partial_internal_source"
        else:
            coverage_state = "full_internal_source"

        if "decision_row_key" not in scoped_fieldnames and scoped_fieldnames:
            scoped_fieldnames.append("decision_row_key")
        if scoped_fieldnames:
            _write_csv(scoped_entry_path, scoped_rows, fieldnames=scoped_fieldnames)
        else:
            scoped_entry_path.parent.mkdir(parents=True, exist_ok=True)
            scoped_entry_path.write_text("", encoding="utf-8-sig")

        detail_lines: list[str] = []
        seen_detail_keys: set[str] = set()
        for source in selected_sources:
            detail_source_path = Path(_to_text(source.get("detail_source_path"), ""))
            for line in _filter_detail_rows(detail_source_path, wanted_keys=selected_keys):
                try:
                    payload = json.loads(line).get("payload", {})
                except Exception:
                    payload = {}
                row_key = _to_text(payload.get("decision_row_key", payload.get("detail_row_key", "")), "")
                if not row_key:
                    row_key = resolve_entry_decision_row_key(payload)
                if row_key in seen_detail_keys:
                    continue
                seen_detail_keys.add(row_key)
                detail_lines.append(line)
        scoped_detail_row_count = _write_detail_lines(scoped_detail_path, detail_lines)
        manual_anchor_rows = _write_manual_subset(
            manual_subset_path,
            manual_rows=manual_rows,
            symbol=symbol,
            window_start=window_start,
            window_end=window_end,
        )

        replay_command = _build_replay_command(
            project_root=project_root,
            scoped_entry_path=scoped_entry_path,
            closed_trade_path=closed_trade_csv,
            replay_output_dir=replay_output_dir,
            analysis_dir=analysis_dir,
            future_bars_output_path=future_bars_output_path,
            symbol=symbol,
            future_bars_timeframe=future_bars_timeframe,
            future_bars_lookback_bars=future_bars_lookback_bars,
            future_bars_lookahead_bars=future_bars_lookahead_bars,
        )
        ready_for_execution = bool(len(scoped_rows) > 0)
        if ready_for_execution:
            _write_runner_script(
                runner_script_path,
                project_root=project_root,
                replay_command=replay_command,
            )
            run_all_paths.append(runner_script_path)

        manifest = {
            "contract_version": BREAKOUT_BACKFILL_RUNNER_SCAFFOLD_VERSION,
            "job_id": job_id,
            "queue_id": _to_text(queue_row.get("queue_id"), ""),
            "recovery_type": _to_text(queue_row.get("recovery_type"), ""),
            "symbol": symbol,
            "priority": _to_text(queue_row.get("priority"), ""),
            "window_start": _local_iso(window_start),
            "window_end": _local_iso(window_end),
            "coverage_state": coverage_state,
            "coverage_gaps": gaps,
            "selected_sources": selected_sources,
            "selected_source_count": int(len(selected_sources)),
            "scoped_entry_row_count": int(len(scoped_rows)),
            "scoped_detail_row_count": int(scoped_detail_row_count),
            "manual_anchor_rows": int(manual_anchor_rows),
            "ready_for_replay_execution": bool(ready_for_execution),
            "external_source_required": bool(coverage_state != "full_internal_source"),
            "scoped_entry_path": str(scoped_entry_path),
            "scoped_detail_path": str(scoped_detail_path),
            "manual_anchor_subset_path": str(manual_subset_path),
            "runner_script_path": str(runner_script_path),
            "replay_output_dir": str(replay_output_dir),
            "analysis_dir": str(analysis_dir),
            "future_bars_output_path": str(future_bars_output_path),
            "replay_command": replay_command,
        }
        job_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        report_rows.append(
            {
                "job_id": job_id,
                "queue_id": _to_text(queue_row.get("queue_id"), ""),
                "recovery_type": _to_text(queue_row.get("recovery_type"), ""),
                "symbol": symbol,
                "priority": _to_text(queue_row.get("priority"), ""),
                "window_start": _local_iso(window_start),
                "window_end": _local_iso(window_end),
                "coverage_state": coverage_state,
                "coverage_gap_count": int(len(gaps)),
                "selected_source_count": int(len(selected_sources)),
                "selected_source_names": "|".join(_to_text(item.get("source_name"), "") for item in selected_sources),
                "scoped_entry_row_count": int(len(scoped_rows)),
                "scoped_detail_row_count": int(scoped_detail_row_count),
                "manual_anchor_rows": int(manual_anchor_rows),
                "ready_for_replay_execution": bool(ready_for_execution),
                "external_source_required": bool(coverage_state != "full_internal_source"),
                "job_dir": str(job_dir),
                "manifest_path": str(manifest_path),
                "runner_script_path": str(runner_script_path if ready_for_execution else ""),
                "replay_command": replay_command,
            }
        )

    run_all_script_path = bundle_root_path / "run_all_breakout_backfill_jobs_latest.ps1"
    _write_run_all_script(run_all_script_path, run_all_paths)

    summary = {
        "contract_version": BREAKOUT_BACKFILL_RUNNER_SCAFFOLD_VERSION,
        "queue_path": str(queue_csv),
        "secondary_queue_path": str(secondary_queue_csv),
        "manual_path": str(manual_csv),
        "supplemental_manual_path": str(supplemental_manual_csv),
        "trades_root": str(trades_dir),
        "closed_trades_path": str(closed_trade_csv),
        "bundle_root": str(bundle_root_path),
        "job_count": int(len(report_rows)),
        "ready_job_count": int(sum(1 for row in report_rows if _safe_bool(row.get("ready_for_replay_execution")))),
        "partial_coverage_jobs": int(sum(1 for row in report_rows if _to_text(row.get("coverage_state")) == "partial_internal_source")),
        "external_source_required_jobs": int(sum(1 for row in report_rows if _safe_bool(row.get("external_source_required")))),
        "run_all_script_path": str(run_all_script_path),
        "source_inventory_count": int(len(source_inventory)),
    }

    csv_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(csv_out, report_rows, fieldnames=BREAKOUT_BACKFILL_RUNNER_COLUMNS)
    payload = {
        "summary": summary,
        "source_inventory": source_inventory,
        "rows": report_rows,
        "queue_path": str(queue_csv),
        "secondary_queue_path": str(secondary_queue_csv),
        "manual_path": str(manual_csv),
        "supplemental_manual_path": str(supplemental_manual_csv),
    }
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_out.write_text(render_breakout_backfill_runner_scaffold_markdown(summary, report_rows), encoding="utf-8")
    return payload
