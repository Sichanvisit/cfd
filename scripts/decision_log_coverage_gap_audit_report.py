from __future__ import annotations

import argparse
import csv
import json
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
DEFAULT_INVENTORY_REPORT = OUT_DIR / "decision_log_coverage_gap_c1_source_inventory_latest.json"
DEFAULT_MATCH_REPORT = ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b2_decision_row_matches_latest.json"
REPORT_VERSION = "decision_log_coverage_gap_c2_audit_v1"


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = _coerce_text(value)
        if not text:
            return float(default)
        return float(text)
    except Exception:
        return float(default)


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


def _min_iso(values: list[str]) -> str:
    parsed = [item for item in (_parse_dt(value) for value in values) if item is not None]
    if not parsed:
        return ""
    return _to_iso(min(parsed))


def _max_iso(values: list[str]) -> str:
    parsed = [item for item in (_parse_dt(value) for value in values) if item is not None]
    if not parsed:
        return ""
    return _to_iso(max(parsed))


def _classify_open_time_relation(open_dt: datetime | None, coverage_start: datetime | None, coverage_end: datetime | None) -> str:
    if open_dt is None or coverage_start is None or coverage_end is None:
        return "unknown"
    if open_dt < coverage_start:
        return "before_coverage"
    if open_dt > coverage_end:
        return "after_coverage"
    return "inside_coverage_window"


def _trade_window_overlap(open_dt: datetime | None, close_dt: datetime | None, coverage_start: datetime | None, coverage_end: datetime | None) -> bool | None:
    if open_dt is None or coverage_start is None or coverage_end is None:
        return None
    effective_close = close_dt or open_dt
    return bool(open_dt <= coverage_end and effective_close >= coverage_start)


def _gap_seconds(open_dt: datetime | None, coverage_start: datetime | None, coverage_end: datetime | None, relation: str) -> float:
    if open_dt is None or coverage_start is None or coverage_end is None:
        return 0.0
    if relation == "before_coverage":
        return round((coverage_start - open_dt).total_seconds(), 3)
    if relation == "after_coverage":
        return round((open_dt - coverage_end).total_seconds(), 3)
    return 0.0


def _sorted_counts(counter: Counter[str], *, top_n: int | None = None) -> list[dict[str, Any]]:
    items = sorted(counter.items(), key=lambda item: (-int(item[1]), _coerce_text(item[0])))
    if top_n is not None:
        items = items[: max(0, int(top_n))]
    return [{"key": key, "count": int(count)} for key, count in items]


def _top_key(counter: Counter[str]) -> tuple[str, int]:
    if not counter:
        return "", 0
    key, count = max(counter.items(), key=lambda item: (int(item[1]), _coerce_text(item[0])))
    return _coerce_text(key), int(count)


def build_decision_log_coverage_gap_audit_report(
    *,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    inventory_report_path: Path = DEFAULT_INVENTORY_REPORT,
    match_report_path: Path = DEFAULT_MATCH_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    baseline_report = _load_json(baseline_report_path)
    inventory_report = _load_json(inventory_report_path)
    match_report = _load_json(match_report_path)

    baseline_summary = dict(baseline_report.get("baseline_summary", {}) or {})
    baseline_assessment = dict(baseline_report.get("baseline_assessment", {}) or {})
    inventory_summary = dict(inventory_report.get("inventory_summary", {}) or {})
    inventory_assessment = dict(inventory_report.get("inventory_assessment", {}) or {})
    inventory_risk_flags = list(inventory_report.get("risk_flags", []) or [])
    match_summary = dict(match_report.get("summary", {}) or {})
    match_status_counts = dict(match_report.get("match_status_counts", {}) or {})
    matches = list(match_report.get("matches", []) or [])

    coverage_start = _parse_dt(baseline_summary.get("coverage_earliest_time"))
    coverage_end = _parse_dt(baseline_summary.get("coverage_latest_time"))

    audit_rows: list[dict[str, Any]] = []
    outside_symbol_counter: Counter[str] = Counter()
    outside_date_counter: Counter[str] = Counter()
    outside_symbol_date_counter: Counter[str] = Counter()
    outside_setup_counter: Counter[str] = Counter()
    temporal_relation_counter: Counter[str] = Counter()
    overlap_counter: Counter[str] = Counter()

    for match in matches:
        open_dt = _parse_dt(match.get("open_time"))
        close_dt = _parse_dt(match.get("close_time"))
        relation = _classify_open_time_relation(open_dt, coverage_start, coverage_end)
        overlap = _trade_window_overlap(open_dt, close_dt, coverage_start, coverage_end)
        overlap_label = (
            "overlap"
            if overlap is True
            else "no_overlap"
            if overlap is False
            else "unknown"
        )
        within_coverage = bool(match.get("within_decision_log_coverage"))
        match_status = _coerce_text(match.get("match_status"))
        outside_coverage = bool((not within_coverage) or match_status == "unmatched_outside_coverage")
        open_date = _to_iso(open_dt)[:10] if open_dt is not None else ""
        symbol = _coerce_text(match.get("symbol"))
        setup_id = _coerce_text(match.get("entry_setup_id"))
        symbol_date = f"{open_date}|{symbol}" if open_date and symbol else ""
        row = {
            "sample_rank": _safe_int(match.get("sample_rank")),
            "ticket": _safe_int(match.get("ticket")),
            "symbol": symbol,
            "direction": _coerce_text(match.get("direction")),
            "open_time": _coerce_text(match.get("open_time")),
            "close_time": _coerce_text(match.get("close_time")),
            "open_date": open_date,
            "entry_setup_id": setup_id,
            "resolved_pnl": _safe_float(match.get("resolved_pnl")),
            "hold_seconds": _safe_float(match.get("hold_seconds")),
            "priority_score": _safe_float(match.get("priority_score")),
            "forensic_ready": bool(match.get("forensic_ready")),
            "within_decision_log_coverage": within_coverage,
            "match_status": match_status,
            "match_strategy": _coerce_text(match.get("match_strategy")),
            "open_time_relation": relation,
            "trade_window_overlap_coverage": overlap,
            "trade_window_overlap_label": overlap_label,
            "gap_to_coverage_seconds": _gap_seconds(open_dt, coverage_start, coverage_end, relation),
        }
        audit_rows.append(row)
        temporal_relation_counter[relation] += 1
        overlap_counter[overlap_label] += 1
        if not outside_coverage:
            continue
        if symbol:
            outside_symbol_counter[symbol] += 1
        if open_date:
            outside_date_counter[open_date] += 1
        if symbol_date:
            outside_symbol_date_counter[symbol_date] += 1
        if setup_id:
            outside_setup_counter[setup_id] += 1

    outside_rows = [row for row in audit_rows if not bool(row.get("within_decision_log_coverage"))]
    forensic_ready_outside_rows = [row for row in outside_rows if bool(row.get("forensic_ready"))]
    before_rows = [row for row in outside_rows if _coerce_text(row.get("open_time_relation")) == "before_coverage"]
    after_rows = [row for row in outside_rows if _coerce_text(row.get("open_time_relation")) == "after_coverage"]
    inside_window_unmatched_rows = [
        row for row in outside_rows if _coerce_text(row.get("open_time_relation")) == "inside_coverage_window"
    ]

    top_symbol, top_symbol_count = _top_key(outside_symbol_counter)
    top_date, top_date_count = _top_key(outside_date_counter)
    top_symbol_date, top_symbol_date_count = _top_key(outside_symbol_date_counter)
    top_setup, top_setup_count = _top_key(outside_setup_counter)

    audit_summary = {
        "sample_rows": int(len(audit_rows)),
        "matched_rows": _safe_int(match_summary.get("matched_rows")),
        "outside_coverage_rows": int(len(outside_rows)),
        "forensic_ready_outside_rows": int(len(forensic_ready_outside_rows)),
        "before_coverage_rows": int(len(before_rows)),
        "after_coverage_rows": int(len(after_rows)),
        "inside_window_unmatched_rows": int(len(inside_window_unmatched_rows)),
        "trade_window_overlap_rows": int(sum(1 for row in audit_rows if row.get("trade_window_overlap_coverage") is True)),
        "trade_window_non_overlap_rows": int(sum(1 for row in audit_rows if row.get("trade_window_overlap_coverage") is False)),
        "unknown_overlap_rows": int(sum(1 for row in audit_rows if row.get("trade_window_overlap_coverage") is None)),
        "coverage_earliest_time": _coerce_text(baseline_summary.get("coverage_earliest_time")),
        "coverage_latest_time": _coerce_text(baseline_summary.get("coverage_latest_time")),
        "earliest_sample_open_time": _min_iso([_coerce_text(row.get("open_time")) for row in audit_rows]),
        "latest_sample_open_time": _max_iso([_coerce_text(row.get("open_time")) for row in audit_rows]),
        "earliest_outside_open_time": _min_iso([_coerce_text(row.get("open_time")) for row in outside_rows]),
        "latest_outside_open_time": _max_iso([_coerce_text(row.get("open_time")) for row in outside_rows]),
        "top_gap_symbol": top_symbol,
        "top_gap_symbol_count": top_symbol_count,
        "top_gap_open_date": top_date,
        "top_gap_open_date_count": top_date_count,
        "top_gap_symbol_date": top_symbol_date,
        "top_gap_symbol_date_count": top_symbol_date_count,
        "top_gap_setup_id": top_setup,
        "top_gap_setup_id_count": top_setup_count,
        "inventory_archive_parquet_count": _safe_int(inventory_summary.get("archive_parquet_count")),
        "inventory_entry_manifest_source_count": _safe_int(inventory_summary.get("entry_manifest_source_count")),
    }

    recommended_next_step = (
        "C3_archive_generation_hardening"
        if _safe_int(inventory_summary.get("archive_parquet_count")) == 0
        or _safe_int(inventory_summary.get("entry_manifest_source_count")) == 0
        else "C4_targeted_backfill_execution"
    )

    audit_assessment = {
        "coverage_gap_is_operational": bool(inventory_assessment.get("source_inventory_confirms_gap_is_operational"))
        or bool(baseline_assessment.get("reader_ready_but_source_gap_suspected")),
        "gap_is_before_coverage_dominant": bool(len(before_rows) >= max(1, len(outside_rows) - len(before_rows))),
        "gap_is_after_coverage_dominant": bool(len(after_rows) > len(before_rows)),
        "recent_gap_clusters_visible": bool(len(outside_symbol_date_counter) > 0),
        "recommended_next_step": recommended_next_step,
        "audit_focus": (
            "archive_and_retention_hardening"
            if recommended_next_step == "C3_archive_generation_hardening"
            else "targeted_backfill_window_selection"
        ),
    }

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "decision_log_coverage_gap_c2_audit",
        "input_paths": {
            "baseline_report_path": str(baseline_report_path),
            "inventory_report_path": str(inventory_report_path),
            "match_report_path": str(match_report_path),
        },
        "coverage_window": {
            "baseline_earliest_time": _coerce_text(baseline_summary.get("coverage_earliest_time")),
            "baseline_latest_time": _coerce_text(baseline_summary.get("coverage_latest_time")),
            "inventory_earliest_known_source_time": _coerce_text(inventory_summary.get("earliest_known_source_time")),
            "inventory_latest_known_source_time": _coerce_text(inventory_summary.get("latest_known_source_time")),
        },
        "audit_summary": audit_summary,
        "temporal_relation_counts": dict(temporal_relation_counter),
        "trade_window_overlap_counts": dict(overlap_counter),
        "match_status_counts": match_status_counts,
        "outside_coverage_by_symbol": _sorted_counts(outside_symbol_counter),
        "outside_coverage_by_open_date": _sorted_counts(outside_date_counter),
        "outside_coverage_by_symbol_date": _sorted_counts(outside_symbol_date_counter, top_n=25),
        "outside_coverage_by_setup_id": _sorted_counts(outside_setup_counter),
        "risk_flags_from_inventory": inventory_risk_flags,
        "audit_rows": audit_rows,
        "audit_assessment": audit_assessment,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("audit_summary", {}) or {})
    assessment = dict(report.get("audit_assessment", {}) or {})
    by_symbol = list(report.get("outside_coverage_by_symbol", []) or [])
    by_date = list(report.get("outside_coverage_by_open_date", []) or [])
    risk_flags = list(report.get("risk_flags_from_inventory", []) or [])
    lines = [
        "# Decision Log Coverage Gap C2 Audit",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- coverage_earliest_time: `{summary.get('coverage_earliest_time', '')}`",
        f"- coverage_latest_time: `{summary.get('coverage_latest_time', '')}`",
        f"- sample_rows: `{summary.get('sample_rows', 0)}`",
        f"- outside_coverage_rows: `{summary.get('outside_coverage_rows', 0)}`",
        f"- forensic_ready_outside_rows: `{summary.get('forensic_ready_outside_rows', 0)}`",
        f"- before_coverage_rows: `{summary.get('before_coverage_rows', 0)}`",
        f"- after_coverage_rows: `{summary.get('after_coverage_rows', 0)}`",
        f"- inside_window_unmatched_rows: `{summary.get('inside_window_unmatched_rows', 0)}`",
        f"- top_gap_symbol: `{summary.get('top_gap_symbol', '')}` ({summary.get('top_gap_symbol_count', 0)})",
        f"- top_gap_open_date: `{summary.get('top_gap_open_date', '')}` ({summary.get('top_gap_open_date_count', 0)})",
        f"- top_gap_setup_id: `{summary.get('top_gap_setup_id', '')}` ({summary.get('top_gap_setup_id_count', 0)})",
        "",
        "## Outside Coverage By Symbol",
        "",
        "| symbol | count |",
        "|---|---|",
    ]
    for row in by_symbol:
        lines.append(f"| {_coerce_text(row.get('key'))} | {_safe_int(row.get('count'))} |")
    lines.extend(
        [
            "",
            "## Outside Coverage By Open Date",
            "",
            "| open_date | count |",
            "|---|---|",
        ]
    )
    for row in by_date:
        lines.append(f"| {_coerce_text(row.get('key'))} | {_safe_int(row.get('count'))} |")
    lines.extend(
        [
            "",
            "## Inventory Risk Flags",
            "",
        ]
    )
    if not risk_flags:
        lines.append("- none")
    else:
        for flag in risk_flags:
            lines.append(
                f"- `{_coerce_text(flag.get('code'))}` [{_coerce_text(flag.get('severity'))}]: {_coerce_text(flag.get('reason'))}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = list(report.get("audit_rows", []) or [])
    fieldnames = [
        "sample_rank",
        "ticket",
        "symbol",
        "direction",
        "open_time",
        "close_time",
        "open_date",
        "entry_setup_id",
        "resolved_pnl",
        "hold_seconds",
        "priority_score",
        "forensic_ready",
        "within_decision_log_coverage",
        "match_status",
        "match_strategy",
        "open_time_relation",
        "trade_window_overlap_coverage",
        "trade_window_overlap_label",
        "gap_to_coverage_seconds",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_decision_log_coverage_gap_audit_report(
    *,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    inventory_report_path: Path = DEFAULT_INVENTORY_REPORT,
    match_report_path: Path = DEFAULT_MATCH_REPORT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_decision_log_coverage_gap_audit_report(
        baseline_report_path=baseline_report_path,
        inventory_report_path=inventory_report_path,
        match_report_path=match_report_path,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "decision_log_coverage_gap_c2_audit_latest.json"
    latest_csv = output_dir / "decision_log_coverage_gap_c2_audit_latest.csv"
    latest_md = output_dir / "decision_log_coverage_gap_c2_audit_latest.md"
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
    parser = argparse.ArgumentParser(description="Build decision log coverage gap C2 audit report.")
    parser.add_argument(
        "--baseline-report-path",
        type=Path,
        default=DEFAULT_BASELINE_REPORT,
        help="Path to the C0 baseline report JSON.",
    )
    parser.add_argument(
        "--inventory-report-path",
        type=Path,
        default=DEFAULT_INVENTORY_REPORT,
        help="Path to the C1 inventory report JSON.",
    )
    parser.add_argument(
        "--match-report-path",
        type=Path,
        default=DEFAULT_MATCH_REPORT,
        help="Path to the R0-B2 decision row match report JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT_DIR,
        help="Directory where the report outputs will be written.",
    )
    args = parser.parse_args(argv)
    result = write_decision_log_coverage_gap_audit_report(
        baseline_report_path=args.baseline_report_path,
        inventory_report_path=args.inventory_report_path,
        match_report_path=args.match_report_path,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
