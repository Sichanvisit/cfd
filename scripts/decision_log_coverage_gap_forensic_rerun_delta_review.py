from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUT_DIR = ROOT / "data" / "analysis" / "decision_log_coverage_gap"
FORENSIC_OUT_DIR = ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic"
DEFAULT_B2_REPORT = FORENSIC_OUT_DIR / "r0_b2_decision_row_matches_latest.json"
DEFAULT_B3_REPORT = FORENSIC_OUT_DIR / "r0_b3_forensic_table_latest.json"
DEFAULT_B4_REPORT = FORENSIC_OUT_DIR / "r0_b4_family_clustering_latest.json"
DEFAULT_B5_REPORT = FORENSIC_OUT_DIR / "r0_b5_action_candidates_latest.json"
DEFAULT_BASELINE_SNAPSHOT = OUT_DIR / "decision_log_coverage_gap_c5_before_snapshot.json"
REPORT_VERSION = "decision_log_coverage_gap_c5_forensic_rerun_delta_v1"


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


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_script_module(script_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed_to_load_module: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _top_counter_key(counter_like: Any) -> tuple[str, int]:
    if not isinstance(counter_like, dict) or not counter_like:
        return "", 0
    key, value = max(counter_like.items(), key=lambda item: (_safe_int(item[1]), _coerce_text(item[0])))
    return _coerce_text(key), _safe_int(value)


def _extract_b2_metrics(report: dict[str, Any]) -> dict[str, Any]:
    summary = dict(report.get("summary", {}) or {})
    coverage = dict(report.get("coverage", {}) or {})
    return {
        "sample_rows": _safe_int(summary.get("sample_rows")),
        "matched_rows": _safe_int(summary.get("matched_rows")),
        "exact_matches": _safe_int(summary.get("exact_matches")),
        "fallback_matches": _safe_int(summary.get("fallback_matches")),
        "unmatched_rows": _safe_int(summary.get("unmatched_rows")),
        "unmatched_outside_coverage": _safe_int(summary.get("unmatched_outside_coverage")),
        "decision_source_count": len(list(report.get("decision_sources", []) or [])),
        "detail_source_count": len(list(report.get("decision_detail_sources", []) or [])),
        "archive_source_count": len(list(report.get("decision_archive_sources", []) or [])),
        "rows_scanned": _safe_int(coverage.get("rows_scanned")),
        "source_count": _safe_int(coverage.get("source_count")),
        "coverage_earliest_time": _coerce_text(coverage.get("earliest_time")),
        "coverage_latest_time": _coerce_text(coverage.get("latest_time")),
    }


def _extract_b3_metrics(report: dict[str, Any]) -> dict[str, Any]:
    summary = dict(report.get("summary", {}) or {})
    return {
        "row_count": _safe_int(summary.get("row_count")),
        "manual_review_rows": _safe_int(summary.get("manual_review_rows")),
        "suspicious_exact_runtime_linkage_rows": _safe_int(summary.get("suspicious_exact_runtime_linkage_rows")),
        "coverage_gap_rows": _safe_int(summary.get("coverage_gap_rows")),
        "strong_exact_rows": _safe_int(summary.get("strong_exact_rows")),
        "fallback_rows": _safe_int(summary.get("fallback_rows")),
    }


def _extract_b4_metrics(report: dict[str, Any]) -> dict[str, Any]:
    summary = dict(report.get("summary", {}) or {})
    family_counts = dict(report.get("family_counts", {}) or {})
    top_family, top_family_count = _top_counter_key(family_counts)
    return {
        "row_count": _safe_int(summary.get("row_count")),
        "family_count": _safe_int(summary.get("family_count")),
        "repeat_families": _safe_int(summary.get("repeat_families")),
        "top_family": top_family,
        "top_family_count": top_family_count,
        "decision_log_coverage_gap_count": _safe_int(family_counts.get("decision_log_coverage_gap")),
        "consumer_stage_misalignment_count": _safe_int(family_counts.get("consumer_stage_misalignment")),
        "guard_leak_count": _safe_int(family_counts.get("guard_leak")),
        "probe_promoted_too_early_count": _safe_int(family_counts.get("probe_promoted_too_early")),
    }


def _extract_b5_metrics(report: dict[str, Any]) -> dict[str, Any]:
    summary = dict(report.get("summary", {}) or {})
    candidates = list(report.get("action_candidates", []) or [])
    top = dict(candidates[0] if candidates else {})
    return {
        "candidate_count": _safe_int(summary.get("candidate_count")),
        "critical_candidates": _safe_int(summary.get("critical_candidates")),
        "high_candidates": _safe_int(summary.get("high_candidates")),
        "medium_candidates": _safe_int(summary.get("medium_candidates")),
        "low_candidates": _safe_int(summary.get("low_candidates")),
        "top_candidate_family": _coerce_text(top.get("family")),
        "top_candidate_priority": _coerce_text(top.get("priority")),
    }


def _diff_numeric_metrics(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    keys = sorted(set(before.keys()) | set(after.keys()))
    for key in keys:
        before_value = before.get(key)
        after_value = after.get(key)
        if isinstance(before_value, str) or isinstance(after_value, str):
            if before_value != after_value:
                diff[key] = {
                    "before": before_value,
                    "after": after_value,
                }
            continue
        before_int = _safe_int(before_value)
        after_int = _safe_int(after_value)
        if before_int != after_int:
            diff[key] = {
                "before": before_int,
                "after": after_int,
                "delta": after_int - before_int,
            }
    return diff


def build_forensic_rerun_delta_review_report(
    *,
    before_reports: dict[str, dict[str, Any]],
    after_reports: dict[str, dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)

    before_b2 = _extract_b2_metrics(before_reports.get("b2", {}))
    before_b3 = _extract_b3_metrics(before_reports.get("b3", {}))
    before_b4 = _extract_b4_metrics(before_reports.get("b4", {}))
    before_b5 = _extract_b5_metrics(before_reports.get("b5", {}))

    after_b2 = _extract_b2_metrics(after_reports.get("b2", {}))
    after_b3 = _extract_b3_metrics(after_reports.get("b3", {}))
    after_b4 = _extract_b4_metrics(after_reports.get("b4", {}))
    after_b5 = _extract_b5_metrics(after_reports.get("b5", {}))

    before_snapshot = {
        "b2": before_b2,
        "b3": before_b3,
        "b4": before_b4,
        "b5": before_b5,
    }
    after_snapshot = {
        "b2": after_b2,
        "b3": after_b3,
        "b4": after_b4,
        "b5": after_b5,
    }
    deltas = {
        "b2": _diff_numeric_metrics(before_b2, after_b2),
        "b3": _diff_numeric_metrics(before_b3, after_b3),
        "b4": _diff_numeric_metrics(before_b4, after_b4),
        "b5": _diff_numeric_metrics(before_b5, after_b5),
    }

    archive_source_delta = _safe_int(after_b2.get("archive_source_count")) - _safe_int(before_b2.get("archive_source_count"))
    matched_rows_delta = _safe_int(after_b2.get("matched_rows")) - _safe_int(before_b2.get("matched_rows"))
    unmatched_outside_delta = _safe_int(after_b2.get("unmatched_outside_coverage")) - _safe_int(before_b2.get("unmatched_outside_coverage"))
    coverage_gap_delta = _safe_int(after_b3.get("coverage_gap_rows")) - _safe_int(before_b3.get("coverage_gap_rows"))
    manual_review_delta = _safe_int(after_b3.get("manual_review_rows")) - _safe_int(before_b3.get("manual_review_rows"))

    if matched_rows_delta > 0 or coverage_gap_delta < 0 or unmatched_outside_delta < 0:
        rerun_state = "forensic_delta_positive"
        recommended_next_step = "C6_close_out_handoff"
    elif archive_source_delta > 0:
        rerun_state = "archive_provenance_improved_but_gap_unchanged"
        recommended_next_step = "C6_close_out_handoff"
    else:
        rerun_state = "no_material_forensic_delta"
        recommended_next_step = "C6_close_out_handoff"

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "decision_log_coverage_gap_c5_forensic_rerun_delta_review",
        "before_snapshot": before_snapshot,
        "after_snapshot": after_snapshot,
        "deltas": deltas,
        "delta_summary": {
            "archive_source_delta": archive_source_delta,
            "matched_rows_delta": matched_rows_delta,
            "unmatched_outside_coverage_delta": unmatched_outside_delta,
            "coverage_gap_rows_delta": coverage_gap_delta,
            "manual_review_rows_delta": manual_review_delta,
            "before_top_family": _coerce_text(before_b4.get("top_family")),
            "after_top_family": _coerce_text(after_b4.get("top_family")),
            "before_top_candidate_family": _coerce_text(before_b5.get("top_candidate_family")),
            "after_top_candidate_family": _coerce_text(after_b5.get("top_candidate_family")),
        },
        "assessment": {
            "rerun_state": rerun_state,
            "recommended_next_step": recommended_next_step,
            "remaining_gap_interpretation": (
                "internal archive provenance improved but remaining gap still appears to sit outside currently available workspace coverage"
                if archive_source_delta > 0 and coverage_gap_delta == 0 and unmatched_outside_delta == 0
                else "forensic metrics improved after rerun"
                if rerun_state == "forensic_delta_positive"
                else "rerun did not materially change coverage or family metrics"
            ),
            "operator_focus": (
                "close_out_current_coverage_track_and record remaining external gap explicitly"
                if rerun_state != "forensic_delta_positive"
                else "close_out_current_coverage_track with measured improvement"
            ),
        },
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    delta_summary = dict(report.get("delta_summary", {}) or {})
    assessment = dict(report.get("assessment", {}) or {})
    lines = [
        "# Decision Log Coverage Gap C5 Forensic Rerun Delta Review",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- rerun_state: `{assessment.get('rerun_state', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Delta Summary",
        "",
        f"- archive_source_delta: `{delta_summary.get('archive_source_delta', 0)}`",
        f"- matched_rows_delta: `{delta_summary.get('matched_rows_delta', 0)}`",
        f"- unmatched_outside_coverage_delta: `{delta_summary.get('unmatched_outside_coverage_delta', 0)}`",
        f"- coverage_gap_rows_delta: `{delta_summary.get('coverage_gap_rows_delta', 0)}`",
        f"- manual_review_rows_delta: `{delta_summary.get('manual_review_rows_delta', 0)}`",
        f"- before_top_family: `{delta_summary.get('before_top_family', '')}`",
        f"- after_top_family: `{delta_summary.get('after_top_family', '')}`",
        f"- before_top_candidate_family: `{delta_summary.get('before_top_candidate_family', '')}`",
        f"- after_top_candidate_family: `{delta_summary.get('after_top_candidate_family', '')}`",
        "",
        "## Assessment",
        "",
        f"- remaining_gap_interpretation: {assessment.get('remaining_gap_interpretation', '')}",
        f"- operator_focus: {assessment.get('operator_focus', '')}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    import csv

    rows: list[dict[str, Any]] = []
    before_snapshot = dict(report.get("before_snapshot", {}) or {})
    after_snapshot = dict(report.get("after_snapshot", {}) or {})
    deltas = dict(report.get("deltas", {}) or {})
    for stage in ("b2", "b3", "b4", "b5"):
        before_metrics = dict(before_snapshot.get(stage, {}) or {})
        after_metrics = dict(after_snapshot.get(stage, {}) or {})
        stage_deltas = dict(deltas.get(stage, {}) or {})
        keys = sorted(set(before_metrics.keys()) | set(after_metrics.keys()))
        for key in keys:
            row = {
                "stage": stage,
                "metric": key,
                "before": before_metrics.get(key, ""),
                "after": after_metrics.get(key, ""),
                "delta": "",
            }
            delta_info = stage_deltas.get(key)
            if isinstance(delta_info, dict) and "delta" in delta_info:
                row["delta"] = delta_info.get("delta", "")
            rows.append(row)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stage", "metric", "before", "after", "delta"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_forensic_rerun_delta_review_report(
    *,
    b2_report_path: Path = DEFAULT_B2_REPORT,
    b3_report_path: Path = DEFAULT_B3_REPORT,
    b4_report_path: Path = DEFAULT_B4_REPORT,
    b5_report_path: Path = DEFAULT_B5_REPORT,
    baseline_snapshot_path: Path = DEFAULT_BASELINE_SNAPSHOT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    baseline_snapshot = _load_json_if_exists(baseline_snapshot_path)
    if baseline_snapshot:
        before_reports = {
            "b2": dict(baseline_snapshot.get("b2", {}) or {}),
            "b3": dict(baseline_snapshot.get("b3", {}) or {}),
            "b4": dict(baseline_snapshot.get("b4", {}) or {}),
            "b5": dict(baseline_snapshot.get("b5", {}) or {}),
        }
        baseline_snapshot_source = "frozen_snapshot"
    else:
        before_reports = {
            "b2": _load_json_if_exists(b2_report_path),
            "b3": _load_json_if_exists(b3_report_path),
            "b4": _load_json_if_exists(b4_report_path),
            "b5": _load_json_if_exists(b5_report_path),
        }
        _write_json(baseline_snapshot_path, before_reports)
        baseline_snapshot_source = "captured_from_current_latest"

    b2_module = _load_script_module(ROOT / "scripts" / "r0_b_actual_entry_forensic_match_rows.py", "c5_b2_module")
    b3_module = _load_script_module(ROOT / "scripts" / "r0_b_actual_entry_forensic_table.py", "c5_b3_module")
    b4_module = _load_script_module(ROOT / "scripts" / "r0_b_actual_entry_forensic_families.py", "c5_b4_module")
    b5_module = _load_script_module(ROOT / "scripts" / "r0_b_actual_entry_forensic_actions.py", "c5_b5_module")

    after_b2_result = b2_module.write_actual_entry_forensic_match_report(output_dir=FORENSIC_OUT_DIR)
    after_b3_result = b3_module.write_actual_entry_forensic_table_report(output_dir=FORENSIC_OUT_DIR)
    after_b4_result = b4_module.write_actual_entry_forensic_family_report(output_dir=FORENSIC_OUT_DIR)
    after_b5_result = b5_module.write_actual_entry_forensic_action_report(output_dir=FORENSIC_OUT_DIR)

    after_reports = {
        "b2": dict(after_b2_result.get("report", {}) or {}),
        "b3": dict(after_b3_result.get("report", {}) or {}),
        "b4": dict(after_b4_result.get("report", {}) or {}),
        "b5": dict(after_b5_result.get("report", {}) or {}),
    }

    report = build_forensic_rerun_delta_review_report(
        before_reports=before_reports,
        after_reports=after_reports,
        now=now,
    )
    report["rerun_output_paths"] = {
        "b2_latest_json_path": str(after_b2_result.get("latest_json_path", "")),
        "b3_latest_json_path": str(after_b3_result.get("latest_json_path", "")),
        "b4_latest_json_path": str(after_b4_result.get("latest_json_path", "")),
        "b5_latest_json_path": str(after_b5_result.get("latest_json_path", "")),
    }
    report["baseline_snapshot"] = {
        "path": str(baseline_snapshot_path),
        "source": baseline_snapshot_source,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "decision_log_coverage_gap_c5_delta_latest.json"
    latest_csv = output_dir / "decision_log_coverage_gap_c5_delta_latest.csv"
    latest_md = output_dir / "decision_log_coverage_gap_c5_delta_latest.md"
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
    parser = argparse.ArgumentParser(description="Rerun B2-B5 and write C5 forensic delta review.")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--baseline-snapshot", type=Path, default=DEFAULT_BASELINE_SNAPSHOT)
    args = parser.parse_args(argv)
    result = write_forensic_rerun_delta_review_report(
        output_dir=args.output_dir,
        baseline_snapshot_path=args.baseline_snapshot,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
