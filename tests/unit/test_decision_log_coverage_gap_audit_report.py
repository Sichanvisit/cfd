import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "decision_log_coverage_gap_audit_report.py"
spec = importlib.util.spec_from_file_location("decision_log_coverage_gap_audit_report", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_c2_audit_report_aggregates_gap_distribution_and_next_step(tmp_path):
    baseline_report = tmp_path / "c0.json"
    inventory_report = tmp_path / "c1.json"
    match_report = tmp_path / "b2.json"

    _write_json(
        baseline_report,
        {
            "baseline_summary": {
                "coverage_earliest_time": "2026-03-27T15:29:43",
                "coverage_latest_time": "2026-03-29T23:41:00",
                "coverage_gap_rows": 3,
                "matched_rows": 1,
                "unmatched_outside_coverage": 2,
            },
            "baseline_assessment": {
                "reader_ready_but_source_gap_suspected": True,
            },
        },
    )
    _write_json(
        inventory_report,
        {
            "inventory_summary": {
                "archive_parquet_count": 0,
                "entry_manifest_source_count": 0,
                "earliest_known_source_time": "2026-03-27T15:41:24",
                "latest_known_source_time": "2026-03-30T00:54:15",
            },
            "inventory_assessment": {
                "source_inventory_confirms_gap_is_operational": True,
            },
            "risk_flags": [
                {"code": "archive_parquet_missing", "severity": "high", "reason": "archive missing"}
            ],
        },
    )
    _write_json(
        match_report,
        {
            "summary": {
                "sample_rows": 3,
                "matched_rows": 1,
                "unmatched_rows": 2,
                "unmatched_outside_coverage": 2,
            },
            "match_status_counts": {
                "unmatched_outside_coverage": 2,
                "fallback": 1,
            },
            "matches": [
                {
                    "sample_rank": 1,
                    "ticket": 1,
                    "symbol": "XAUUSD",
                    "direction": "SELL",
                    "open_time": "2026-03-27 14:35:49",
                    "close_time": "2026-03-27 14:37:14",
                    "entry_setup_id": "range_upper_reversal_sell",
                    "resolved_pnl": -7.96,
                    "hold_seconds": 85.0,
                    "priority_score": 11.296,
                    "forensic_ready": True,
                    "within_decision_log_coverage": False,
                    "match_status": "unmatched_outside_coverage",
                    "match_strategy": "",
                },
                {
                    "sample_rank": 2,
                    "ticket": 2,
                    "symbol": "BTCUSD",
                    "direction": "BUY",
                    "open_time": "2026-03-28 12:00:00",
                    "close_time": "2026-03-28 12:05:00",
                    "entry_setup_id": "range_lower_reversal_buy",
                    "resolved_pnl": -1.5,
                    "hold_seconds": 300.0,
                    "priority_score": 8.0,
                    "forensic_ready": True,
                    "within_decision_log_coverage": True,
                    "match_status": "fallback",
                    "match_strategy": "fallback_symbol_time",
                },
                {
                    "sample_rank": 3,
                    "ticket": 3,
                    "symbol": "NAS100",
                    "direction": "SELL",
                    "open_time": "2026-03-30 01:00:00",
                    "close_time": "2026-03-30 01:10:00",
                    "entry_setup_id": "trend_pullback_sell",
                    "resolved_pnl": -2.0,
                    "hold_seconds": 600.0,
                    "priority_score": 7.0,
                    "forensic_ready": False,
                    "within_decision_log_coverage": False,
                    "match_status": "unmatched_outside_coverage",
                    "match_strategy": "",
                },
            ],
        },
    )

    report = module.build_decision_log_coverage_gap_audit_report(
        baseline_report_path=baseline_report,
        inventory_report_path=inventory_report,
        match_report_path=match_report,
        now=datetime.fromisoformat("2026-03-30T03:00:00"),
    )

    summary = report["audit_summary"]
    assessment = report["audit_assessment"]
    temporal = report["temporal_relation_counts"]
    by_symbol = {row["key"]: row["count"] for row in report["outside_coverage_by_symbol"]}
    by_date = {row["key"]: row["count"] for row in report["outside_coverage_by_open_date"]}

    assert report["report_version"] == module.REPORT_VERSION
    assert summary["sample_rows"] == 3
    assert summary["outside_coverage_rows"] == 2
    assert summary["forensic_ready_outside_rows"] == 1
    assert summary["before_coverage_rows"] == 1
    assert summary["after_coverage_rows"] == 1
    assert summary["inside_window_unmatched_rows"] == 0
    assert summary["top_gap_symbol_count"] == 1
    assert temporal["before_coverage"] == 1
    assert temporal["inside_coverage_window"] == 1
    assert temporal["after_coverage"] == 1
    assert by_symbol["XAUUSD"] == 1
    assert by_symbol["NAS100"] == 1
    assert by_date["2026-03-27"] == 1
    assert by_date["2026-03-30"] == 1
    assert assessment["recommended_next_step"] == "C3_archive_generation_hardening"
    assert assessment["coverage_gap_is_operational"] is True


def test_write_c2_audit_report_writes_json_csv_and_markdown(tmp_path):
    baseline_report = tmp_path / "c0.json"
    inventory_report = tmp_path / "c1.json"
    match_report = tmp_path / "b2.json"
    output_dir = tmp_path / "analysis"

    _write_json(
        baseline_report,
        {
            "baseline_summary": {
                "coverage_earliest_time": "2026-03-27T15:29:43",
                "coverage_latest_time": "2026-03-29T23:41:00",
                "coverage_gap_rows": 1,
                "matched_rows": 0,
                "unmatched_outside_coverage": 1,
            },
            "baseline_assessment": {
                "reader_ready_but_source_gap_suspected": True,
            },
        },
    )
    _write_json(
        inventory_report,
        {
            "inventory_summary": {
                "archive_parquet_count": 0,
                "entry_manifest_source_count": 0,
                "earliest_known_source_time": "2026-03-27T15:41:24",
                "latest_known_source_time": "2026-03-30T00:54:15",
            },
            "inventory_assessment": {
                "source_inventory_confirms_gap_is_operational": True,
            },
            "risk_flags": [],
        },
    )
    _write_json(
        match_report,
        {
            "summary": {
                "sample_rows": 1,
                "matched_rows": 0,
                "unmatched_rows": 1,
                "unmatched_outside_coverage": 1,
            },
            "match_status_counts": {
                "unmatched_outside_coverage": 1,
            },
            "matches": [
                {
                    "sample_rank": 1,
                    "ticket": 10,
                    "symbol": "XAUUSD",
                    "direction": "SELL",
                    "open_time": "2026-03-27 14:35:49",
                    "close_time": "2026-03-27 14:37:14",
                    "entry_setup_id": "range_upper_reversal_sell",
                    "resolved_pnl": -7.96,
                    "hold_seconds": 85.0,
                    "priority_score": 11.296,
                    "forensic_ready": True,
                    "within_decision_log_coverage": False,
                    "match_status": "unmatched_outside_coverage",
                    "match_strategy": "",
                }
            ],
        },
    )

    result = module.write_decision_log_coverage_gap_audit_report(
        baseline_report_path=baseline_report,
        inventory_report_path=inventory_report,
        match_report_path=match_report,
        output_dir=output_dir,
        now=datetime.fromisoformat("2026-03-30T03:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["audit_summary"]["outside_coverage_rows"] == 1
    assert payload["audit_assessment"]["recommended_next_step"] == "C3_archive_generation_hardening"
    assert "Decision Log Coverage Gap C2 Audit" in markdown
    assert "`C3_archive_generation_hardening`" in markdown
