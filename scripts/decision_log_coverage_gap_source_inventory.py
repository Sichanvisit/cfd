from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUT_DIR = ROOT / "data" / "analysis" / "decision_log_coverage_gap"
DEFAULT_BASELINE_REPORT = OUT_DIR / "decision_log_coverage_gap_c0_baseline_latest.json"
DEFAULT_TRADES_ROOT = ROOT / "data" / "trades"
DEFAULT_ARCHIVE_ROOT = DEFAULT_TRADES_ROOT / "archive" / "entry_decisions"
DEFAULT_MANIFEST_ROOT = ROOT / "data" / "manifests"
REPORT_VERSION = "decision_log_coverage_gap_c1_source_inventory_v1"

EXPECTED_SOURCE_KINDS = [
    "active_csv",
    "legacy_csv",
    "active_detail",
    "legacy_detail",
    "rotated_detail",
    "archive_parquet",
    "archive_manifest",
    "rollover_manifest",
    "retention_manifest",
]

SOURCE_KIND_LABELS = {
    "active_csv": "active csv",
    "legacy_csv": "legacy csv",
    "active_detail": "active detail jsonl",
    "legacy_detail": "legacy detail jsonl",
    "rotated_detail": "rotated detail jsonl",
    "archive_parquet": "archive parquet",
    "archive_manifest": "archive manifest",
    "rollover_manifest": "rollover manifest",
    "retention_manifest": "retention manifest",
}


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_path_text(value: Any, *, root: Path | None = None) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    path = Path(text)
    if not path.is_absolute() and root is not None:
        path = root / path
    try:
        path = path.resolve()
    except Exception:
        pass
    return str(path)


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


def _parse_iso(value: Any) -> datetime | None:
    text = _coerce_text(value)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _to_iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.isoformat(timespec="seconds")


def _parse_filename_time_hint(path: Path) -> str:
    matches = re.findall(r"(\d{8}_\d{6}(?:_\d{6})?)", path.name)
    if not matches:
        return ""
    value = matches[-1]
    fmt = "%Y%m%d_%H%M%S_%f" if value.count("_") == 2 else "%Y%m%d_%H%M%S"
    try:
        return datetime.strptime(value, fmt).isoformat(timespec="seconds")
    except Exception:
        return ""


def _parse_archive_partition_hint(path: Path) -> str:
    year = ""
    month = ""
    day = ""
    for part in path.parts:
        if part.startswith("year="):
            year = part.split("=", 1)[1]
        elif part.startswith("month="):
            month = part.split("=", 1)[1]
        elif part.startswith("day="):
            day = part.split("=", 1)[1]
    if not (year and month and day):
        return ""
    try:
        return datetime(int(year), int(month), int(day)).isoformat(timespec="seconds")
    except Exception:
        return ""


def _resolve_path(value: Any, *, root: Path) -> Path | None:
    text = _normalize_path_text(value, root=root)
    if not text:
        return None
    return Path(text)


def _min_iso(values: list[str]) -> str:
    parsed = [item for item in (_parse_iso(value) for value in values) if item is not None]
    if not parsed:
        return ""
    return _to_iso(min(parsed))


def _max_iso(values: list[str]) -> str:
    parsed = [item for item in (_parse_iso(value) for value in values) if item is not None]
    if not parsed:
        return ""
    return _to_iso(max(parsed))


def _build_path_record(
    path: Path,
    *,
    source_kind: str,
    baseline_paths: set[str],
    manifest_output_paths: set[str],
) -> dict[str, Any]:
    try:
        path = path.resolve()
    except Exception:
        pass
    exists = path.exists()
    stat = path.stat() if exists else None
    modified_at = _to_iso(datetime.fromtimestamp(stat.st_mtime)) if stat is not None else ""
    filename_time_hint = _parse_filename_time_hint(path)
    partition_time_hint = _parse_archive_partition_hint(path) if source_kind == "archive_parquet" else ""
    known_time_start = partition_time_hint or filename_time_hint or modified_at
    known_time_end = partition_time_hint or filename_time_hint or modified_at
    time_basis = (
        "archive_partition_day"
        if partition_time_hint
        else "filename_hint"
        if filename_time_hint
        else "modified_at"
        if modified_at
        else "unknown"
    )
    path_text = _normalize_path_text(path)
    return {
        "path": path_text,
        "file_name": path.name,
        "source_kind": source_kind,
        "source_kind_label": SOURCE_KIND_LABELS.get(source_kind, source_kind),
        "exists": bool(exists),
        "file_size_bytes": int(stat.st_size) if stat is not None else 0,
        "modified_at": modified_at,
        "filename_time_hint": filename_time_hint,
        "known_time_start": known_time_start,
        "known_time_end": known_time_end,
        "time_basis": time_basis,
        "row_count_known": 0,
        "schema_version": "",
        "source_reference_path": "",
        "source_reference_exists": False,
        "provenance_available": bool(source_kind.endswith("_manifest")),
        "manifest_reference_found": bool(path_text in manifest_output_paths),
        "baseline_referenced": bool(path_text in baseline_paths),
    }


def _manifest_time_window(source_kind: str, payload: dict[str, Any]) -> tuple[str, str, str]:
    if source_kind == "archive_manifest":
        start = _coerce_text(payload.get("time_range_start"))
        end = _coerce_text(payload.get("time_range_end"))
        if start or end:
            return start, end, "manifest_window"
    if source_kind == "rollover_manifest":
        start = _coerce_text(payload.get("archive_time_range_start"))
        end = _coerce_text(payload.get("archive_time_range_end"))
        if start or end:
            return start, end, "manifest_window"
    created_at = _coerce_text(payload.get("created_at"))
    if created_at:
        return created_at, created_at, "manifest_created_at"
    return "", "", "unknown"


def _manifest_reference_path(source_kind: str, payload: dict[str, Any]) -> str:
    if source_kind == "archive_manifest":
        return _coerce_text(payload.get("output_path"))
    if source_kind == "rollover_manifest":
        return (
            _coerce_text(payload.get("archive_path"))
            or _coerce_text(payload.get("source_path"))
            or _coerce_text(payload.get("output_path"))
        )
    if source_kind == "retention_manifest":
        return _coerce_text(payload.get("source_path"))
    return ""


def _build_manifest_record(
    path: Path,
    *,
    source_kind: str,
    root: Path,
) -> tuple[dict[str, Any], str]:
    try:
        path = path.resolve()
    except Exception:
        pass
    payload = _load_json(path)
    exists = path.exists()
    stat = path.stat() if exists else None
    modified_at = _to_iso(datetime.fromtimestamp(stat.st_mtime)) if stat is not None else ""
    known_time_start, known_time_end, time_basis = _manifest_time_window(source_kind, payload)
    source_reference_path = _manifest_reference_path(source_kind, payload)
    resolved_source_reference = _resolve_path(source_reference_path, root=root)
    source_reference_exists = bool(resolved_source_reference and resolved_source_reference.exists())
    record = {
        "path": _normalize_path_text(path),
        "file_name": path.name,
        "source_kind": source_kind,
        "source_kind_label": SOURCE_KIND_LABELS.get(source_kind, source_kind),
        "exists": bool(exists),
        "file_size_bytes": int(stat.st_size) if stat is not None else 0,
        "modified_at": modified_at,
        "filename_time_hint": _parse_filename_time_hint(path),
        "known_time_start": known_time_start,
        "known_time_end": known_time_end,
        "time_basis": time_basis,
        "row_count_known": _safe_int(payload.get("row_count")),
        "schema_version": _coerce_text(payload.get("schema_version")),
        "source_reference_path": (
            _normalize_path_text(resolved_source_reference)
            if resolved_source_reference is not None
            else _normalize_path_text(source_reference_path, root=root)
        ),
        "source_reference_exists": bool(source_reference_exists),
        "provenance_available": True,
        "manifest_reference_found": True,
        "baseline_referenced": False,
    }
    archive_link = ""
    if source_kind == "archive_manifest":
        archive_link = _normalize_path_text(record["source_reference_path"], root=root)
    elif source_kind == "rollover_manifest":
        archive_link = _normalize_path_text(payload.get("archive_path"), root=root)
    return record, archive_link


def _collect_trade_sources(
    *,
    trades_root: Path,
    baseline_paths: set[str],
    manifest_output_paths: set[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    patterns = [
        ("active_csv", [trades_root / "entry_decisions.csv"]),
        ("legacy_csv", sorted(trades_root.glob("entry_decisions.legacy_*.csv"))),
        ("active_detail", [trades_root / "entry_decisions.detail.jsonl"]),
        ("legacy_detail", sorted(trades_root.glob("entry_decisions.legacy_*.detail.jsonl"))),
        ("rotated_detail", sorted(trades_root.glob("entry_decisions.detail.rotate_*.jsonl"))),
    ]
    for source_kind, paths in patterns:
        for path in paths:
            if path.exists():
                records.append(
                    _build_path_record(
                        path,
                        source_kind=source_kind,
                        baseline_paths=baseline_paths,
                        manifest_output_paths=manifest_output_paths,
                    )
                )
    return records


def _collect_archive_sources(
    *,
    archive_root: Path,
    baseline_paths: set[str],
    manifest_output_paths: set[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not archive_root.exists():
        return records
    for path in sorted(archive_root.glob("**/*.parquet")):
        records.append(
            _build_path_record(
                path,
                source_kind="archive_parquet",
                baseline_paths=baseline_paths,
                manifest_output_paths=manifest_output_paths,
            )
        )
    return records


def _collect_manifest_sources(*, manifest_root: Path, root: Path) -> tuple[list[dict[str, Any]], set[str]]:
    records: list[dict[str, Any]] = []
    manifest_output_paths: set[str] = set()
    manifest_specs = [
        ("archive_manifest", manifest_root / "archive", "entry_decisions_archive_*.json"),
        ("rollover_manifest", manifest_root / "rollover", "entry_decisions_rollover_*.json"),
        ("retention_manifest", manifest_root / "retention", "entry_decisions_retention_*.json"),
    ]
    for source_kind, directory, pattern in manifest_specs:
        if not directory.exists():
            continue
        for path in sorted(directory.glob(pattern)):
            record, archive_link = _build_manifest_record(path, source_kind=source_kind, root=root)
            records.append(record)
            if archive_link:
                manifest_output_paths.add(_coerce_text(archive_link))
    return records, manifest_output_paths


def _build_retention_matrix(source_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for source_kind in EXPECTED_SOURCE_KINDS:
        rows = [row for row in source_records if row.get("source_kind") == source_kind]
        count = len(rows)
        total_bytes = sum(_safe_int(row.get("file_size_bytes")) for row in rows)
        earliest = _min_iso([_coerce_text(row.get("known_time_start")) for row in rows])
        latest = _max_iso([_coerce_text(row.get("known_time_end")) for row in rows])
        baseline_referenced_count = sum(1 for row in rows if bool(row.get("baseline_referenced")))
        provenance_count = sum(1 for row in rows if bool(row.get("provenance_available")))
        source_reference_exists_count = sum(1 for row in rows if bool(row.get("source_reference_exists")))
        matrix.append(
            {
                "source_kind": source_kind,
                "source_kind_label": SOURCE_KIND_LABELS.get(source_kind, source_kind),
                "count": count,
                "total_bytes": total_bytes,
                "earliest_known_time": earliest,
                "latest_known_time": latest,
                "baseline_referenced_count": baseline_referenced_count,
                "provenance_count": provenance_count,
                "source_reference_exists_count": source_reference_exists_count,
                "status": "present" if count > 0 else "missing",
            }
        )
    return matrix


def _build_risk_flags(*, counts: Counter[str], baseline_assessment: dict[str, Any], baseline_summary: dict[str, Any]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if counts.get("archive_parquet", 0) == 0:
        flags.append(
            {
                "code": "archive_parquet_missing",
                "severity": "high",
                "reason": "entry_decisions parquet archive source가 현재 inventory에 없다.",
            }
        )
    if counts.get("archive_manifest", 0) == 0:
        flags.append(
            {
                "code": "archive_manifest_missing",
                "severity": "medium",
                "reason": "archive manifest가 없어 archive provenance window를 확인할 수 없다.",
            }
        )
    if counts.get("rollover_manifest", 0) == 0:
        flags.append(
            {
                "code": "rollover_manifest_missing",
                "severity": "medium",
                "reason": "rollover manifest가 없어 active->legacy/archive 전환 이력을 확인하기 어렵다.",
            }
        )
    if counts.get("retention_manifest", 0) == 0:
        flags.append(
            {
                "code": "retention_manifest_missing",
                "severity": "medium",
                "reason": "retention manifest가 없어 cleanup 정책 적용 이력을 추적하기 어렵다.",
            }
        )
    if counts.get("legacy_csv", 0) > 0 and counts.get("archive_parquet", 0) == 0:
        flags.append(
            {
                "code": "legacy_present_without_archive",
                "severity": "high",
                "reason": "legacy csv는 존재하지만 warm archive parquet가 없어 coverage 공백이 생길 위험이 높다.",
            }
        )
    if counts.get("rotated_detail", 0) > 0 and counts.get("archive_parquet", 0) == 0:
        flags.append(
            {
                "code": "rotated_detail_present_without_archive",
                "severity": "high",
                "reason": "detail rotate는 많이 남아 있지만 entry_decisions archive가 없어 detail-only tail 상태다.",
            }
        )
    if bool(baseline_assessment.get("reader_ready_but_source_gap_suspected")):
        flags.append(
            {
                "code": "reader_ready_source_gap_suspected",
                "severity": "critical",
                "reason": "C0 baseline이 reader는 준비됐고 source retention 공백이 의심된다고 가리킨다.",
            }
        )
    if _safe_int(baseline_summary.get("coverage_gap_rows")) > 0:
        flags.append(
            {
                "code": "coverage_gap_still_open",
                "severity": "critical",
                "reason": "baseline 기준 coverage_gap rows가 아직 0이 아니다.",
            }
        )
    return flags


def build_decision_log_coverage_gap_source_inventory_report(
    *,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    archive_root: Path = DEFAULT_ARCHIVE_ROOT,
    manifest_root: Path = DEFAULT_MANIFEST_ROOT,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    baseline_report = _load_json(baseline_report_path)
    baseline_summary = dict(baseline_report.get("baseline_summary", {}) or {})
    baseline_assessment = dict(baseline_report.get("baseline_assessment", {}) or {})

    baseline_paths: set[str] = set()
    for key in ("decision_sources", "decision_detail_sources", "decision_archive_sources"):
        baseline_paths.update(
            _normalize_path_text(item)
            for item in list(baseline_report.get(key, []) or [])
            if _normalize_path_text(item)
        )

    manifest_records, manifest_output_paths = _collect_manifest_sources(manifest_root=manifest_root, root=ROOT)
    trade_records = _collect_trade_sources(
        trades_root=trades_root,
        baseline_paths=baseline_paths,
        manifest_output_paths=manifest_output_paths,
    )
    archive_records = _collect_archive_sources(
        archive_root=archive_root,
        baseline_paths=baseline_paths,
        manifest_output_paths=manifest_output_paths,
    )

    source_records = sorted(
        [*trade_records, *archive_records, *manifest_records],
        key=lambda row: (_coerce_text(row.get("source_kind")), _coerce_text(row.get("path"))),
    )
    for record in source_records:
        if _coerce_text(record.get("source_kind")) != "archive_parquet":
            continue
        if _coerce_text(record.get("path")) in manifest_output_paths:
            record["manifest_reference_found"] = True
            record["provenance_available"] = True
    counts = Counter(_coerce_text(row.get("source_kind")) for row in source_records)
    retention_matrix = _build_retention_matrix(source_records)
    risk_flags = _build_risk_flags(
        counts=counts,
        baseline_assessment=baseline_assessment,
        baseline_summary=baseline_summary,
    )

    inventory_summary = {
        "total_source_records": int(len(source_records)),
        "baseline_referenced_inventory_rows": int(sum(1 for row in source_records if bool(row.get("baseline_referenced")))),
        "active_csv_count": int(counts.get("active_csv", 0)),
        "legacy_csv_count": int(counts.get("legacy_csv", 0)),
        "active_detail_count": int(counts.get("active_detail", 0)),
        "legacy_detail_count": int(counts.get("legacy_detail", 0)),
        "rotated_detail_count": int(counts.get("rotated_detail", 0)),
        "archive_parquet_count": int(counts.get("archive_parquet", 0)),
        "archive_manifest_count": int(counts.get("archive_manifest", 0)),
        "rollover_manifest_count": int(counts.get("rollover_manifest", 0)),
        "retention_manifest_count": int(counts.get("retention_manifest", 0)),
        "entry_manifest_source_count": int(
            counts.get("archive_manifest", 0) + counts.get("rollover_manifest", 0) + counts.get("retention_manifest", 0)
        ),
        "archive_root_exists": bool(archive_root.exists()),
        "manifest_root_exists": bool(manifest_root.exists()),
        "earliest_known_source_time": _min_iso([_coerce_text(row.get("known_time_start")) for row in source_records]),
        "latest_known_source_time": _max_iso([_coerce_text(row.get("known_time_end")) for row in source_records]),
        "coverage_gap_rows": _safe_int(baseline_summary.get("coverage_gap_rows")),
        "unmatched_outside_coverage": _safe_int(baseline_summary.get("unmatched_outside_coverage")),
        "coverage_state": _coerce_text(baseline_assessment.get("coverage_state")),
    }
    inventory_assessment = {
        "inventory_state": (
            "archive_gap_dominant"
            if inventory_summary["archive_parquet_count"] == 0
            else "archive_present"
        ),
        "source_inventory_confirms_gap_is_operational": bool(
            baseline_assessment.get("reader_ready_but_source_gap_suspected")
        )
        and inventory_summary["archive_parquet_count"] == 0,
        "recommended_next_step": "C2_coverage_audit_report",
        "operational_focus": "inventory_and_retention_matrix_before_audit_and_backfill",
    }
    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "decision_log_coverage_gap_c1_source_inventory",
        "baseline_report_path": str(baseline_report_path),
        "trades_root": str(trades_root),
        "archive_root": str(archive_root),
        "manifest_root": str(manifest_root),
        "baseline_snapshot": {
            "coverage_earliest_time": _coerce_text(baseline_summary.get("coverage_earliest_time")),
            "coverage_latest_time": _coerce_text(baseline_summary.get("coverage_latest_time")),
            "coverage_gap_rows": _safe_int(baseline_summary.get("coverage_gap_rows")),
            "matched_rows": _safe_int(baseline_summary.get("matched_rows")),
            "unmatched_outside_coverage": _safe_int(baseline_summary.get("unmatched_outside_coverage")),
            "reader_ready_but_source_gap_suspected": bool(
                baseline_assessment.get("reader_ready_but_source_gap_suspected")
            ),
        },
        "inventory_summary": inventory_summary,
        "retention_matrix": retention_matrix,
        "risk_flags": risk_flags,
        "source_records": source_records,
        "inventory_assessment": inventory_assessment,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("inventory_summary", {}) or {})
    assessment = dict(report.get("inventory_assessment", {}) or {})
    retention_matrix = list(report.get("retention_matrix", []) or [])
    risk_flags = list(report.get("risk_flags", []) or [])
    lines = [
        "# Decision Log Coverage Gap C1 Source Inventory",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- inventory_state: `{assessment.get('inventory_state', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- total_source_records: `{summary.get('total_source_records', 0)}`",
        f"- earliest_known_source_time: `{summary.get('earliest_known_source_time', '')}`",
        f"- latest_known_source_time: `{summary.get('latest_known_source_time', '')}`",
        f"- active_csv_count: `{summary.get('active_csv_count', 0)}`",
        f"- legacy_csv_count: `{summary.get('legacy_csv_count', 0)}`",
        f"- active_detail_count: `{summary.get('active_detail_count', 0)}`",
        f"- legacy_detail_count: `{summary.get('legacy_detail_count', 0)}`",
        f"- rotated_detail_count: `{summary.get('rotated_detail_count', 0)}`",
        f"- archive_parquet_count: `{summary.get('archive_parquet_count', 0)}`",
        f"- entry_manifest_source_count: `{summary.get('entry_manifest_source_count', 0)}`",
        f"- coverage_gap_rows: `{summary.get('coverage_gap_rows', 0)}`",
        "",
        "## Risk Flags",
        "",
    ]
    if not risk_flags:
        lines.append("- none")
    else:
        for flag in risk_flags:
            lines.append(
                f"- `{_coerce_text(flag.get('code'))}` [{_coerce_text(flag.get('severity'))}]: {_coerce_text(flag.get('reason'))}"
            )
    lines.extend(
        [
            "",
            "## Retention Matrix",
            "",
            "| source_kind | count | total_bytes | earliest_known_time | latest_known_time | status |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in retention_matrix:
        lines.append(
            "| {kind} | {count} | {bytes_} | {start} | {end} | {status} |".format(
                kind=_coerce_text(row.get("source_kind")),
                count=_safe_int(row.get("count")),
                bytes_=_safe_int(row.get("total_bytes")),
                start=_coerce_text(row.get("earliest_known_time")),
                end=_coerce_text(row.get("latest_known_time")),
                status=_coerce_text(row.get("status")),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    records = list(report.get("source_records", []) or [])
    fieldnames = [
        "path",
        "file_name",
        "source_kind",
        "source_kind_label",
        "exists",
        "file_size_bytes",
        "modified_at",
        "filename_time_hint",
        "known_time_start",
        "known_time_end",
        "time_basis",
        "row_count_known",
        "schema_version",
        "source_reference_path",
        "source_reference_exists",
        "provenance_available",
        "manifest_reference_found",
        "baseline_referenced",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({name: record.get(name, "") for name in fieldnames})


def write_decision_log_coverage_gap_source_inventory_report(
    *,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    archive_root: Path = DEFAULT_ARCHIVE_ROOT,
    manifest_root: Path = DEFAULT_MANIFEST_ROOT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_decision_log_coverage_gap_source_inventory_report(
        baseline_report_path=baseline_report_path,
        trades_root=trades_root,
        archive_root=archive_root,
        manifest_root=manifest_root,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "decision_log_coverage_gap_c1_source_inventory_latest.json"
    latest_csv = output_dir / "decision_log_coverage_gap_c1_source_inventory_latest.csv"
    latest_md = output_dir / "decision_log_coverage_gap_c1_source_inventory_latest.md"
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
    parser = argparse.ArgumentParser(description="Build decision log coverage gap C1 source inventory report.")
    parser.add_argument(
        "--baseline-report-path",
        type=Path,
        default=DEFAULT_BASELINE_REPORT,
        help="Path to the C0 baseline report JSON.",
    )
    parser.add_argument(
        "--trades-root",
        type=Path,
        default=DEFAULT_TRADES_ROOT,
        help="Directory containing entry_decisions sources.",
    )
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=DEFAULT_ARCHIVE_ROOT,
        help="Directory containing archived entry_decisions parquet files.",
    )
    parser.add_argument(
        "--manifest-root",
        type=Path,
        default=DEFAULT_MANIFEST_ROOT,
        help="Directory containing manifests.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT_DIR,
        help="Directory where the report outputs will be written.",
    )
    args = parser.parse_args(argv)
    result = write_decision_log_coverage_gap_source_inventory_report(
        baseline_report_path=args.baseline_report_path,
        trades_root=args.trades_root,
        archive_root=args.archive_root,
        manifest_root=args.manifest_root,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
