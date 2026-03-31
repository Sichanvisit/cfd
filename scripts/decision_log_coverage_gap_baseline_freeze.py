from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_MATCH_REPORT = (
    ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b2_decision_row_matches_latest.json"
)
DEFAULT_FORENSIC_TABLE_REPORT = (
    ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b3_forensic_table_latest.json"
)
DEFAULT_FAMILY_REPORT = (
    ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b4_family_clustering_latest.json"
)
DEFAULT_ACTION_REPORT = (
    ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic" / "r0_b5_action_candidates_latest.json"
)
OUT_DIR = ROOT / "data" / "analysis" / "decision_log_coverage_gap"
REPORT_VERSION = "decision_log_coverage_gap_c0_baseline_v1"


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


def _top_family(family_counts: dict[str, Any]) -> tuple[str, int]:
    if not isinstance(family_counts, dict) or not family_counts:
        return "", 0
    family, count = max(family_counts.items(), key=lambda item: (_safe_int(item[1]), _coerce_text(item[0])))
    return _coerce_text(family), _safe_int(count)


def _coverage_span_hours(earliest_time: str, latest_time: str) -> float:
    try:
        if not earliest_time or not latest_time:
            return 0.0
        earliest = datetime.fromisoformat(str(earliest_time))
        latest = datetime.fromisoformat(str(latest_time))
        return round(max(0.0, (latest - earliest).total_seconds()) / 3600.0, 3)
    except Exception:
        return 0.0


def build_decision_log_coverage_gap_baseline_report(
    *,
    match_report_path: Path = DEFAULT_MATCH_REPORT,
    forensic_table_report_path: Path = DEFAULT_FORENSIC_TABLE_REPORT,
    family_report_path: Path = DEFAULT_FAMILY_REPORT,
    action_report_path: Path = DEFAULT_ACTION_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    match_report = _load_json(match_report_path)
    forensic_table_report = _load_json(forensic_table_report_path)
    family_report = _load_json(family_report_path)
    action_report = _load_json(action_report_path)

    match_summary = dict(match_report.get("summary", {}) or {})
    match_coverage = dict(match_report.get("coverage", {}) or {})
    forensic_summary = dict(forensic_table_report.get("summary", {}) or {})
    forensic_linkage_quality = dict(forensic_table_report.get("linkage_quality_counts", {}) or {})
    family_summary = dict(family_report.get("summary", {}) or {})
    family_counts = dict(family_report.get("family_counts", {}) or {})
    action_summary = dict(action_report.get("summary", {}) or {})
    action_candidates = list(action_report.get("action_candidates", []) or [])
    top_candidate = dict(action_candidates[0] if action_candidates else {})
    top_family_name, top_family_count = _top_family(family_counts)
    earliest_time = _coerce_text(match_coverage.get("earliest_time"))
    latest_time = _coerce_text(match_coverage.get("latest_time"))
    coverage_gap_rows = _safe_int(forensic_summary.get("coverage_gap_rows"))
    unmatched_outside_coverage = _safe_int(match_summary.get("unmatched_outside_coverage"))

    baseline_summary = {
        "coverage_earliest_time": earliest_time,
        "coverage_latest_time": latest_time,
        "coverage_span_hours": _coverage_span_hours(earliest_time, latest_time),
        "rows_scanned": _safe_int(match_coverage.get("rows_scanned")),
        "source_count": _safe_int(match_coverage.get("source_count")),
        "decision_source_count": int(len(list(match_report.get("decision_sources", []) or []))),
        "decision_detail_source_count": int(len(list(match_report.get("decision_detail_sources", []) or []))),
        "decision_archive_source_count": int(len(list(match_report.get("decision_archive_sources", []) or []))),
        "sample_rows": _safe_int(match_summary.get("sample_rows")),
        "matched_rows": _safe_int(match_summary.get("matched_rows")),
        "exact_matches": _safe_int(match_summary.get("exact_matches")),
        "fallback_matches": _safe_int(match_summary.get("fallback_matches")),
        "unmatched_rows": _safe_int(match_summary.get("unmatched_rows")),
        "unmatched_outside_coverage": unmatched_outside_coverage,
        "forensic_ready_samples": _safe_int(match_summary.get("forensic_ready_samples")),
        "coverage_gap_rows": coverage_gap_rows,
        "fallback_rows": _safe_int(forensic_summary.get("fallback_rows")),
        "strong_exact_rows": _safe_int(forensic_summary.get("strong_exact_rows")),
        "manual_review_rows": _safe_int(forensic_summary.get("manual_review_rows")),
        "suspicious_exact_runtime_linkage_rows": _safe_int(
            forensic_summary.get("suspicious_exact_runtime_linkage_rows")
        ),
        "family_count": _safe_int(family_summary.get("family_count")),
        "repeat_families": _safe_int(family_summary.get("repeat_families")),
        "top_family": top_family_name,
        "top_family_count": top_family_count,
        "candidate_count": _safe_int(action_summary.get("candidate_count")),
        "critical_candidates": _safe_int(action_summary.get("critical_candidates")),
        "high_candidates": _safe_int(action_summary.get("high_candidates")),
        "medium_candidates": _safe_int(action_summary.get("medium_candidates")),
        "low_candidates": _safe_int(action_summary.get("low_candidates")),
        "top_candidate_family": _coerce_text(top_candidate.get("family")),
        "top_candidate_priority": _coerce_text(top_candidate.get("priority")),
        "top_candidate_next_action": _coerce_text(top_candidate.get("next_action")),
    }
    baseline_assessment = {
        "baseline_locked": True,
        "coverage_state": (
            "coverage_gap_dominant"
            if coverage_gap_rows > 0 or unmatched_outside_coverage > 0
            else "coverage_green"
        ),
        "gap_dominant": bool(coverage_gap_rows > 0 or unmatched_outside_coverage > 0),
        "reader_ready_but_source_gap_suspected": bool(
            unmatched_outside_coverage > 0 and _safe_int(baseline_summary["decision_archive_source_count"]) == 0
        ),
        "recommended_next_step": "C1_source_inventory_retention_matrix",
        "handoff_focus": "retention_archive_backfill_before_more_entry_logic_tuning",
    }
    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "baseline_kind": "coverage_gap_c0_baseline",
        "source_reports": {
            "match_report_path": str(match_report_path),
            "forensic_table_report_path": str(forensic_table_report_path),
            "family_report_path": str(family_report_path),
            "action_report_path": str(action_report_path),
        },
        "decision_sources": list(match_report.get("decision_sources", []) or []),
        "decision_detail_sources": list(match_report.get("decision_detail_sources", []) or []),
        "decision_archive_sources": list(match_report.get("decision_archive_sources", []) or []),
        "forensic_linkage_quality_counts": forensic_linkage_quality,
        "family_counts": family_counts,
        "baseline_summary": baseline_summary,
        "baseline_assessment": baseline_assessment,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("baseline_summary", {}) or {})
    assessment = dict(report.get("baseline_assessment", {}) or {})
    family_counts = dict(report.get("family_counts", {}) or {})
    lines = [
        "# Decision Log Coverage Gap C0 Baseline",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- coverage_state: `{assessment.get('coverage_state', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- coverage_earliest_time: `{summary.get('coverage_earliest_time', '')}`",
        f"- coverage_latest_time: `{summary.get('coverage_latest_time', '')}`",
        f"- coverage_span_hours: `{summary.get('coverage_span_hours', 0.0)}`",
        f"- sample_rows: `{summary.get('sample_rows', 0)}`",
        f"- matched_rows: `{summary.get('matched_rows', 0)}`",
        f"- unmatched_outside_coverage: `{summary.get('unmatched_outside_coverage', 0)}`",
        f"- coverage_gap_rows: `{summary.get('coverage_gap_rows', 0)}`",
        f"- top_family: `{summary.get('top_family', '')}` ({summary.get('top_family_count', 0)})",
        f"- top_candidate_family: `{summary.get('top_candidate_family', '')}`",
        "",
        "## Family Counts",
        "",
        "| family | count |",
        "|---|---|",
    ]
    for family, count in family_counts.items():
        lines.append(f"| {_coerce_text(family)} | {_safe_int(count)} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("baseline_summary", {}) or {})
    assessment = dict(report.get("baseline_assessment", {}) or {})
    row = {
        "report_version": _coerce_text(report.get("report_version")),
        "generated_at": _coerce_text(report.get("generated_at")),
        "baseline_kind": _coerce_text(report.get("baseline_kind")),
        "coverage_state": _coerce_text(assessment.get("coverage_state")),
        "recommended_next_step": _coerce_text(assessment.get("recommended_next_step")),
        **summary,
    }
    fieldnames = list(row.keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


def write_decision_log_coverage_gap_baseline_report(
    *,
    match_report_path: Path = DEFAULT_MATCH_REPORT,
    forensic_table_report_path: Path = DEFAULT_FORENSIC_TABLE_REPORT,
    family_report_path: Path = DEFAULT_FAMILY_REPORT,
    action_report_path: Path = DEFAULT_ACTION_REPORT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_decision_log_coverage_gap_baseline_report(
        match_report_path=match_report_path,
        forensic_table_report_path=forensic_table_report_path,
        family_report_path=family_report_path,
        action_report_path=action_report_path,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "decision_log_coverage_gap_c0_baseline_latest.json"
    latest_csv = output_dir / "decision_log_coverage_gap_c0_baseline_latest.csv"
    latest_md = output_dir / "decision_log_coverage_gap_c0_baseline_latest.md"
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
    parser = argparse.ArgumentParser(description="Freeze C0 baseline for decision_log_coverage_gap.")
    parser.add_argument("--match-report", type=Path, default=DEFAULT_MATCH_REPORT)
    parser.add_argument("--forensic-table-report", type=Path, default=DEFAULT_FORENSIC_TABLE_REPORT)
    parser.add_argument("--family-report", type=Path, default=DEFAULT_FAMILY_REPORT)
    parser.add_argument("--action-report", type=Path, default=DEFAULT_ACTION_REPORT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    result = write_decision_log_coverage_gap_baseline_report(
        match_report_path=args.match_report,
        forensic_table_report_path=args.forensic_table_report,
        family_report_path=args.family_report,
        action_report_path=args.action_report,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
