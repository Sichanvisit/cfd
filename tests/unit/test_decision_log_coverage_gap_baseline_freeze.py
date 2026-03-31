import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "decision_log_coverage_gap_baseline_freeze.py"
spec = importlib.util.spec_from_file_location("decision_log_coverage_gap_baseline_freeze", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_baseline_report_extracts_core_coverage_gap_metrics(tmp_path):
    match_report = tmp_path / "b2.json"
    forensic_table_report = tmp_path / "b3.json"
    family_report = tmp_path / "b4.json"
    action_report = tmp_path / "b5.json"
    _write_json(
        match_report,
        {
            "report_version": "r0_b2_decision_row_match_v1",
            "coverage": {
                "earliest_time": "2026-03-27T15:29:43",
                "latest_time": "2026-03-29T23:41:00",
                "rows_scanned": 22027,
                "source_count": 7,
            },
            "summary": {
                "sample_rows": 30,
                "matched_rows": 7,
                "exact_matches": 0,
                "fallback_matches": 7,
                "unmatched_rows": 23,
                "unmatched_outside_coverage": 23,
                "forensic_ready_samples": 15,
            },
            "decision_sources": ["active.csv", "legacy.csv"],
            "decision_detail_sources": ["detail.jsonl"],
            "decision_archive_sources": [],
        },
    )
    _write_json(
        forensic_table_report,
        {
            "report_version": "r0_b3_forensic_table_v1",
            "summary": {
                "row_count": 30,
                "manual_review_rows": 30,
                "suspicious_exact_runtime_linkage_rows": 0,
                "coverage_gap_rows": 23,
                "strong_exact_rows": 0,
                "fallback_rows": 7,
            },
            "linkage_quality_counts": {"coverage_gap": 23, "fallback_match": 7},
        },
    )
    _write_json(
        family_report,
        {
            "report_version": "r0_b4_family_clustering_v1",
            "summary": {"row_count": 30, "family_count": 4, "repeat_families": 4},
            "family_counts": {
                "decision_log_coverage_gap": 23,
                "consumer_stage_misalignment": 3,
                "guard_leak": 2,
                "probe_promoted_too_early": 2,
            },
        },
    )
    _write_json(
        action_report,
        {
            "report_version": "r0_b5_action_candidates_v1",
            "summary": {
                "candidate_count": 4,
                "critical_candidates": 1,
                "high_candidates": 3,
                "medium_candidates": 0,
                "low_candidates": 0,
            },
            "action_candidates": [
                {
                    "rank": 1,
                    "family": "decision_log_coverage_gap",
                    "priority": "critical",
                    "next_action": "strengthen retention",
                }
            ],
        },
    )

    report = module.build_decision_log_coverage_gap_baseline_report(
        match_report_path=match_report,
        forensic_table_report_path=forensic_table_report,
        family_report_path=family_report,
        action_report_path=action_report,
        now=datetime.fromisoformat("2026-03-30T01:23:45"),
    )

    summary = report["baseline_summary"]
    assessment = report["baseline_assessment"]
    assert report["report_version"] == module.REPORT_VERSION
    assert summary["coverage_earliest_time"] == "2026-03-27T15:29:43"
    assert summary["sample_rows"] == 30
    assert summary["matched_rows"] == 7
    assert summary["coverage_gap_rows"] == 23
    assert summary["top_family"] == "decision_log_coverage_gap"
    assert summary["top_candidate_family"] == "decision_log_coverage_gap"
    assert assessment["coverage_state"] == "coverage_gap_dominant"
    assert assessment["recommended_next_step"] == "C1_source_inventory_retention_matrix"
    assert assessment["reader_ready_but_source_gap_suspected"] is True


def test_write_baseline_report_writes_json_csv_and_markdown(tmp_path):
    match_report = tmp_path / "b2.json"
    forensic_table_report = tmp_path / "b3.json"
    family_report = tmp_path / "b4.json"
    action_report = tmp_path / "b5.json"
    output_dir = tmp_path / "analysis"
    _write_json(
        match_report,
        {
            "coverage": {
                "earliest_time": "2026-03-27T15:29:43",
                "latest_time": "2026-03-29T23:41:00",
                "rows_scanned": 10,
                "source_count": 2,
            },
            "summary": {
                "sample_rows": 2,
                "matched_rows": 1,
                "exact_matches": 0,
                "fallback_matches": 1,
                "unmatched_rows": 1,
                "unmatched_outside_coverage": 1,
                "forensic_ready_samples": 1,
            },
            "decision_sources": ["active.csv"],
            "decision_detail_sources": [],
            "decision_archive_sources": ["archive.parquet"],
        },
    )
    _write_json(
        forensic_table_report,
        {
            "summary": {
                "row_count": 2,
                "manual_review_rows": 2,
                "suspicious_exact_runtime_linkage_rows": 0,
                "coverage_gap_rows": 1,
                "strong_exact_rows": 0,
                "fallback_rows": 1,
            },
            "linkage_quality_counts": {"coverage_gap": 1, "fallback_match": 1},
        },
    )
    _write_json(
        family_report,
        {
            "summary": {"row_count": 2, "family_count": 1, "repeat_families": 1},
            "family_counts": {"decision_log_coverage_gap": 1},
        },
    )
    _write_json(
        action_report,
        {
            "summary": {
                "candidate_count": 1,
                "critical_candidates": 1,
                "high_candidates": 0,
                "medium_candidates": 0,
                "low_candidates": 0,
            },
            "action_candidates": [
                {
                    "rank": 1,
                    "family": "decision_log_coverage_gap",
                    "priority": "critical",
                    "next_action": "retain more",
                }
            ],
        },
    )

    result = module.write_decision_log_coverage_gap_baseline_report(
        match_report_path=match_report,
        forensic_table_report_path=forensic_table_report,
        family_report_path=family_report,
        action_report_path=action_report,
        output_dir=output_dir,
        now=datetime.fromisoformat("2026-03-30T01:23:45"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["baseline_summary"]["sample_rows"] == 2
    markdown = md_path.read_text(encoding="utf-8")
    assert "Decision Log Coverage Gap C0 Baseline" in markdown
    assert "`decision_log_coverage_gap`" in markdown
