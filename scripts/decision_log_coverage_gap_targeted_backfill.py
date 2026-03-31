from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.entry_decision_rollover import archive_entry_decision_csv_source


OUT_DIR = ROOT / "data" / "analysis" / "decision_log_coverage_gap"
DEFAULT_BASELINE_REPORT = OUT_DIR / "decision_log_coverage_gap_c0_baseline_latest.json"
DEFAULT_INVENTORY_REPORT = OUT_DIR / "decision_log_coverage_gap_c1_source_inventory_latest.json"
DEFAULT_AUDIT_REPORT = OUT_DIR / "decision_log_coverage_gap_c2_audit_latest.json"
DEFAULT_TRADES_ROOT = ROOT / "data" / "trades"
DEFAULT_ARCHIVE_ROOT = DEFAULT_TRADES_ROOT / "archive" / "entry_decisions"
DEFAULT_MANIFEST_ROOT = ROOT / "data" / "manifests"
DEFAULT_BACKFILL_MANIFEST_ROOT = DEFAULT_MANIFEST_ROOT / "backfill"
REPORT_VERSION = "decision_log_coverage_gap_c4_targeted_backfill_v1"
DEFAULT_ADJACENCY_HOURS = 8.0


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        text = _coerce_text(value)
        if not text:
            return int(default)
        return int(float(text))
    except Exception:
        return int(default)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_dt(value: Any) -> datetime | None:
    text = _coerce_text(value)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except Exception:
                dt = None
        if dt is None:
            return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _to_iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.isoformat(timespec="seconds")


def _scan_csv_time_window(path: Path) -> tuple[datetime | None, datetime | None, int]:
    first_dt: datetime | None = None
    last_dt: datetime | None = None
    rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows += 1
            parsed = _parse_dt(row.get("time"))
            if parsed is None:
                continue
            if first_dt is None:
                first_dt = parsed
            last_dt = parsed
    return first_dt, last_dt, rows


def _load_archived_source_paths(manifest_root: Path) -> set[str]:
    archived: set[str] = set()
    archive_dir = manifest_root / "archive"
    if not archive_dir.exists():
        return archived
    for path in sorted(archive_dir.glob("entry_decisions_archive_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        source_path = _coerce_text(payload.get("source_path"))
        if source_path:
            archived.add(str(Path(source_path)))
    return archived


def _discover_csv_sources(trades_root: Path) -> list[Path]:
    candidates: list[Path] = []
    active = trades_root / "entry_decisions.csv"
    if active.exists():
        candidates.append(active)
    for path in sorted(trades_root.glob("entry_decisions.legacy_*.csv")):
        if path.exists():
            candidates.append(path)
    return candidates


def _write_manifest(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _window_overlaps(
    *,
    source_start: datetime | None,
    source_end: datetime | None,
    target_start: datetime | None,
    target_end: datetime | None,
) -> bool:
    if source_start is None or source_end is None or target_start is None or target_end is None:
        return False
    return bool(source_start <= target_end and source_end >= target_start)


def _window_adjacency_reason(
    *,
    source_start: datetime | None,
    source_end: datetime | None,
    target_start: datetime | None,
    target_end: datetime | None,
    adjacency: timedelta,
) -> str:
    if source_start is None or source_end is None or target_start is None or target_end is None:
        return ""
    if source_start > target_end and source_start - target_end <= adjacency:
        return "adjacent_after_target"
    if source_end < target_start and target_start - source_end <= adjacency:
        return "adjacent_before_target"
    return ""


def build_decision_log_coverage_gap_targeted_backfill_report(
    *,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    inventory_report_path: Path = DEFAULT_INVENTORY_REPORT,
    audit_report_path: Path = DEFAULT_AUDIT_REPORT,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    archive_root: Path = DEFAULT_ARCHIVE_ROOT,
    manifest_root: Path = DEFAULT_MANIFEST_ROOT,
    backfill_manifest_root: Path = DEFAULT_BACKFILL_MANIFEST_ROOT,
    execute: bool = True,
    adjacency_hours: float = DEFAULT_ADJACENCY_HOURS,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    baseline_report = _load_json(baseline_report_path)
    inventory_report = _load_json(inventory_report_path)
    audit_report = _load_json(audit_report_path)

    baseline_summary = dict(baseline_report.get("baseline_summary", {}) or {})
    inventory_summary = dict(inventory_report.get("inventory_summary", {}) or {})
    audit_summary = dict(audit_report.get("audit_summary", {}) or {})

    target_start = _parse_dt(audit_summary.get("earliest_outside_open_time"))
    target_end = _parse_dt(audit_summary.get("coverage_earliest_time"))
    adjacency = timedelta(hours=max(0.0, float(adjacency_hours)))
    archived_source_paths = _load_archived_source_paths(manifest_root)

    candidate_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    executed_backfills: list[dict[str, Any]] = []

    for source_path in _discover_csv_sources(trades_root):
        source_start, source_end, row_count = _scan_csv_time_window(source_path)
        detail_path = source_path.with_name(f"{source_path.stem}.detail.jsonl")
        already_archived = str(source_path) in archived_source_paths
        overlap_target = _window_overlaps(
            source_start=source_start,
            source_end=source_end,
            target_start=target_start,
            target_end=target_end,
        )
        adjacency_reason = _window_adjacency_reason(
            source_start=source_start,
            source_end=source_end,
            target_start=target_start,
            target_end=target_end,
            adjacency=adjacency,
        )
        selection_reason = ""
        if overlap_target:
            selection_reason = "primary_overlap_backfill"
        elif adjacency_reason and source_path.name.startswith("entry_decisions.legacy_"):
            selection_reason = f"boundary_support_backfill:{adjacency_reason}"

        candidate_row = {
            "source_path": str(source_path),
            "source_name": source_path.name,
            "source_kind": "legacy_csv" if ".legacy_" in source_path.name else "active_csv",
            "detail_source_path": str(detail_path) if detail_path.exists() else "",
            "detail_source_exists": bool(detail_path.exists()),
            "row_count": int(row_count),
            "source_time_start": _to_iso(source_start),
            "source_time_end": _to_iso(source_end),
            "already_archived": bool(already_archived),
            "overlap_target_window": bool(overlap_target),
            "adjacency_reason": adjacency_reason,
            "selection_reason": selection_reason,
            "selected_for_backfill": bool(selection_reason and not already_archived and row_count > 0),
        }
        candidate_rows.append(candidate_row)
        if candidate_row["selected_for_backfill"]:
            selected_rows.append(candidate_row)

    if execute:
        for index, row in enumerate(selected_rows, start=1):
            source_path = Path(row["source_path"])
            detail_source_path = Path(row["detail_source_path"]) if row["detail_source_path"] else None
            partition_dt = _parse_dt(row["source_time_start"]) or _parse_dt(row["source_time_end"]) or current_now
            result = archive_entry_decision_csv_source(
                source_path=source_path,
                source_detail_path=detail_source_path,
                root=ROOT,
                now=current_now + timedelta(microseconds=index),
                archive_root=archive_root,
                manifest_root=manifest_root,
                trigger_mode="targeted_backfill",
                notes=(
                    "Decision log coverage gap targeted backfill. "
                    f"selection_reason={row['selection_reason']}"
                ),
                archive_partition_dt=partition_dt,
            )
            executed_backfills.append(
                {
                    "source_path": row["source_path"],
                    "source_name": row["source_name"],
                    "selection_reason": row["selection_reason"],
                    **result,
                }
            )

    target_window = {
        "earliest_outside_open_time": _to_iso(target_start),
        "coverage_earliest_time": _coerce_text(audit_summary.get("coverage_earliest_time")),
        "coverage_latest_time": _coerce_text(audit_summary.get("coverage_latest_time")),
        "outside_coverage_rows": _safe_int(audit_summary.get("outside_coverage_rows")),
        "forensic_ready_outside_rows": _safe_int(audit_summary.get("forensic_ready_outside_rows")),
        "before_coverage_rows": _safe_int(audit_summary.get("before_coverage_rows")),
        "top_gap_symbol": _coerce_text(audit_summary.get("top_gap_symbol")),
        "top_gap_open_date": _coerce_text(audit_summary.get("top_gap_open_date")),
        "top_gap_setup_id": _coerce_text(audit_summary.get("top_gap_setup_id")),
    }

    overlap_capable_count = sum(1 for row in candidate_rows if bool(row.get("overlap_target_window")))
    selected_count = len(selected_rows)
    executed_count = sum(1 for row in executed_backfills if bool(row.get("ok")))
    remaining_external_required = bool(target_window["outside_coverage_rows"] > 0 and overlap_capable_count == 0)

    execution_summary = {
        "candidate_source_count": int(len(candidate_rows)),
        "selected_source_count": int(selected_count),
        "executed_backfill_count": int(executed_count),
        "primary_overlap_selection_count": int(
            sum(1 for row in selected_rows if _coerce_text(row.get("selection_reason")) == "primary_overlap_backfill")
        ),
        "boundary_support_selection_count": int(
            sum(1 for row in selected_rows if _coerce_text(row.get("selection_reason")).startswith("boundary_support_backfill"))
        ),
        "already_archived_skip_count": int(sum(1 for row in candidate_rows if bool(row.get("already_archived")))),
        "outside_scope_skip_count": int(
            sum(1 for row in candidate_rows if not bool(row.get("selection_reason")) and not bool(row.get("already_archived")))
        ),
        "internal_overlap_source_available": bool(overlap_capable_count > 0),
        "external_backfill_required": bool(remaining_external_required),
        "coverage_gap_rows_at_start": _safe_int(baseline_summary.get("coverage_gap_rows")),
        "inventory_archive_parquet_count_at_start": _safe_int(inventory_summary.get("archive_parquet_count")),
        "inventory_entry_manifest_source_count_at_start": _safe_int(inventory_summary.get("entry_manifest_source_count")),
    }

    report = {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "decision_log_coverage_gap_c4_targeted_backfill",
        "input_paths": {
            "baseline_report_path": str(baseline_report_path),
            "inventory_report_path": str(inventory_report_path),
            "audit_report_path": str(audit_report_path),
        },
        "target_window": target_window,
        "execution_summary": execution_summary,
        "candidate_sources": candidate_rows,
        "selected_sources": selected_rows,
        "executed_backfills": executed_backfills,
        "backfill_assessment": {
            "backfill_state": (
                "partial_internal_backfill_executed"
                if executed_count > 0
                else "no_internal_overlap_source"
                if remaining_external_required
                else "no_candidate_selected"
            ),
            "recommended_next_step": "C5_forensic_rerun_delta_review",
            "operator_focus": (
                "rerun_forensic_and_measure_delta"
                if executed_count > 0
                else "confirm_remaining_gap_and_prepare_external_backfill_if_needed"
            ),
        },
    }

    timestamp = current_now.strftime("%Y%m%d_%H%M%S")
    manifest_payload = {
        "created_at": current_now.astimezone().isoformat(),
        "job_name": "decision_log_coverage_gap_targeted_backfill",
        "schema_version": REPORT_VERSION,
        "target_window": target_window,
        "execution_summary": execution_summary,
        "selected_sources": selected_rows,
        "executed_backfills": executed_backfills,
        "recommended_next_step": "C5_forensic_rerun_delta_review",
    }
    manifest_path = _write_manifest(
        backfill_manifest_root / f"decision_log_coverage_gap_backfill_{timestamp}.json",
        manifest_payload,
    )
    report["backfill_manifest_path"] = str(manifest_path)
    return report


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = list(report.get("candidate_sources", []) or [])
    fieldnames = [
        "source_path",
        "source_name",
        "source_kind",
        "detail_source_path",
        "detail_source_exists",
        "row_count",
        "source_time_start",
        "source_time_end",
        "already_archived",
        "overlap_target_window",
        "adjacency_reason",
        "selection_reason",
        "selected_for_backfill",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    target_window = dict(report.get("target_window", {}) or {})
    summary = dict(report.get("execution_summary", {}) or {})
    selected = list(report.get("selected_sources", []) or [])
    executed = list(report.get("executed_backfills", []) or [])
    lines = [
        "# Decision Log Coverage Gap C4 Targeted Backfill",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- recommended_next_step: `{dict(report.get('backfill_assessment', {}) or {}).get('recommended_next_step', '')}`",
        f"- backfill_manifest_path: `{report.get('backfill_manifest_path', '')}`",
        "",
        "## Target Window",
        "",
        f"- earliest_outside_open_time: `{target_window.get('earliest_outside_open_time', '')}`",
        f"- coverage_earliest_time: `{target_window.get('coverage_earliest_time', '')}`",
        f"- outside_coverage_rows: `{target_window.get('outside_coverage_rows', 0)}`",
        f"- forensic_ready_outside_rows: `{target_window.get('forensic_ready_outside_rows', 0)}`",
        f"- top_gap_symbol: `{target_window.get('top_gap_symbol', '')}`",
        f"- top_gap_setup_id: `{target_window.get('top_gap_setup_id', '')}`",
        "",
        "## Execution Summary",
        "",
        f"- candidate_source_count: `{summary.get('candidate_source_count', 0)}`",
        f"- selected_source_count: `{summary.get('selected_source_count', 0)}`",
        f"- executed_backfill_count: `{summary.get('executed_backfill_count', 0)}`",
        f"- primary_overlap_selection_count: `{summary.get('primary_overlap_selection_count', 0)}`",
        f"- boundary_support_selection_count: `{summary.get('boundary_support_selection_count', 0)}`",
        f"- external_backfill_required: `{summary.get('external_backfill_required', False)}`",
        "",
        "## Selected Sources",
        "",
    ]
    if not selected:
        lines.append("- none")
    else:
        for row in selected:
            lines.append(
                f"- `{row.get('source_name', '')}` | {row.get('selection_reason', '')} | "
                f"{row.get('source_time_start', '')} -> {row.get('source_time_end', '')} | rows={row.get('row_count', 0)}"
            )
    lines.extend(["", "## Executed Backfills", ""])
    if not executed:
        lines.append("- none")
    else:
        for row in executed:
            lines.append(
                f"- `{row.get('source_name', '')}` | ok={row.get('ok', False)} | "
                f"archive=`{row.get('archive_path', '')}` | manifest=`{row.get('archive_manifest_path', '')}` | "
                f"time_range={row.get('time_range_start', '')} -> {row.get('time_range_end', '')}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_decision_log_coverage_gap_targeted_backfill_report(
    *,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    inventory_report_path: Path = DEFAULT_INVENTORY_REPORT,
    audit_report_path: Path = DEFAULT_AUDIT_REPORT,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    archive_root: Path = DEFAULT_ARCHIVE_ROOT,
    manifest_root: Path = DEFAULT_MANIFEST_ROOT,
    backfill_manifest_root: Path = DEFAULT_BACKFILL_MANIFEST_ROOT,
    output_dir: Path = OUT_DIR,
    execute: bool = True,
    adjacency_hours: float = DEFAULT_ADJACENCY_HOURS,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_decision_log_coverage_gap_targeted_backfill_report(
        baseline_report_path=baseline_report_path,
        inventory_report_path=inventory_report_path,
        audit_report_path=audit_report_path,
        trades_root=trades_root,
        archive_root=archive_root,
        manifest_root=manifest_root,
        backfill_manifest_root=backfill_manifest_root,
        execute=execute,
        adjacency_hours=adjacency_hours,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "decision_log_coverage_gap_c4_backfill_latest.json"
    latest_csv = output_dir / "decision_log_coverage_gap_c4_backfill_latest.csv"
    latest_md = output_dir / "decision_log_coverage_gap_c4_backfill_latest.md"
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(report, latest_csv)
    _write_markdown(report, latest_md)
    return {
        "latest_json_path": str(latest_json),
        "latest_csv_path": str(latest_csv),
        "latest_markdown_path": str(latest_md),
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute targeted backfill for decision_log_coverage_gap.")
    parser.add_argument("--baseline-report-path", type=Path, default=DEFAULT_BASELINE_REPORT)
    parser.add_argument("--inventory-report-path", type=Path, default=DEFAULT_INVENTORY_REPORT)
    parser.add_argument("--audit-report-path", type=Path, default=DEFAULT_AUDIT_REPORT)
    parser.add_argument("--trades-root", type=Path, default=DEFAULT_TRADES_ROOT)
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE_ROOT)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument("--backfill-manifest-root", type=Path, default=DEFAULT_BACKFILL_MANIFEST_ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--adjacency-hours", type=float, default=DEFAULT_ADJACENCY_HOURS)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    result = write_decision_log_coverage_gap_targeted_backfill_report(
        baseline_report_path=args.baseline_report_path,
        inventory_report_path=args.inventory_report_path,
        audit_report_path=args.audit_report_path,
        trades_root=args.trades_root,
        archive_root=args.archive_root,
        manifest_root=args.manifest_root,
        backfill_manifest_root=args.backfill_manifest_root,
        output_dir=args.output_dir,
        execute=not bool(args.plan_only),
        adjacency_hours=float(args.adjacency_hours),
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
