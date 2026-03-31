import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "decision_log_coverage_gap_targeted_backfill.py"
spec = importlib.util.spec_from_file_location("decision_log_coverage_gap_targeted_backfill", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def test_targeted_backfill_archives_overlap_and_boundary_support_sources(tmp_path):
    trades_root = tmp_path / "data" / "trades"
    archive_root = trades_root / "archive" / "entry_decisions"
    manifest_root = tmp_path / "data" / "manifests"
    backfill_manifest_root = manifest_root / "backfill"
    analysis_root = tmp_path / "data" / "analysis" / "decision_log_coverage_gap"
    baseline_report = analysis_root / "c0.json"
    inventory_report = analysis_root / "c1.json"
    audit_report = analysis_root / "c2.json"

    _write_json(baseline_report, {"baseline_summary": {"coverage_gap_rows": 23}})
    _write_json(
        inventory_report,
        {"inventory_summary": {"archive_parquet_count": 0, "entry_manifest_source_count": 0}},
    )
    _write_json(
        audit_report,
        {
            "audit_summary": {
                "earliest_outside_open_time": "2026-03-27T14:35:02",
                "coverage_earliest_time": "2026-03-27T15:29:43",
                "coverage_latest_time": "2026-03-29T23:41:00",
                "outside_coverage_rows": 23,
                "forensic_ready_outside_rows": 15,
                "before_coverage_rows": 23,
                "top_gap_symbol": "XAUUSD",
                "top_gap_open_date": "2026-03-27",
                "top_gap_setup_id": "range_upper_reversal_sell",
            }
        },
    )

    overlap_source = trades_root / "entry_decisions.legacy_20260327_212023.csv"
    support_source = trades_root / "entry_decisions.legacy_20260328_000522.csv"
    later_source = trades_root / "entry_decisions.legacy_20260330_012813.csv"
    _write_csv(
        overlap_source,
        [
            {"time": "2026-03-27T15:29:43", "symbol": "XAUUSD", "action": "SELL"},
            {"time": "2026-03-27T16:00:00", "symbol": "XAUUSD", "action": "SELL"},
        ],
    )
    _write_csv(
        support_source,
        [
            {"time": "2026-03-27T21:20:23", "symbol": "XAUUSD", "action": "SELL"},
            {"time": "2026-03-28T00:04:40", "symbol": "XAUUSD", "action": "SELL"},
        ],
    )
    _write_csv(
        later_source,
        [
            {"time": "2026-03-29T00:05:22", "symbol": "XAUUSD", "action": "SELL"},
            {"time": "2026-03-30T01:28:07", "symbol": "XAUUSD", "action": "SELL"},
        ],
    )

    report = module.build_decision_log_coverage_gap_targeted_backfill_report(
        baseline_report_path=baseline_report,
        inventory_report_path=inventory_report,
        audit_report_path=audit_report,
        trades_root=trades_root,
        archive_root=archive_root,
        manifest_root=manifest_root,
        backfill_manifest_root=backfill_manifest_root,
        execute=True,
        adjacency_hours=8.0,
        now=datetime.fromisoformat("2026-03-30T02:00:00"),
    )

    summary = report["execution_summary"]
    selected = {row["source_name"]: row["selection_reason"] for row in report["selected_sources"]}
    executed = report["executed_backfills"]

    assert summary["selected_source_count"] == 2
    assert summary["executed_backfill_count"] == 2
    assert summary["primary_overlap_selection_count"] == 1
    assert summary["boundary_support_selection_count"] == 1
    assert selected["entry_decisions.legacy_20260327_212023.csv"] == "primary_overlap_backfill"
    assert selected["entry_decisions.legacy_20260328_000522.csv"].startswith("boundary_support_backfill")
    assert later_source.name not in selected
    assert all(Path(item["archive_path"]).exists() for item in executed)
    assert all(Path(item["archive_manifest_path"]).exists() for item in executed)
    assert report["backfill_assessment"]["recommended_next_step"] == "C5_forensic_rerun_delta_review"


def test_targeted_backfill_reports_external_requirement_when_no_internal_overlap_source(tmp_path):
    trades_root = tmp_path / "data" / "trades"
    archive_root = trades_root / "archive" / "entry_decisions"
    manifest_root = tmp_path / "data" / "manifests"
    backfill_manifest_root = manifest_root / "backfill"
    analysis_root = tmp_path / "data" / "analysis" / "decision_log_coverage_gap"
    baseline_report = analysis_root / "c0.json"
    inventory_report = analysis_root / "c1.json"
    audit_report = analysis_root / "c2.json"

    _write_json(baseline_report, {"baseline_summary": {"coverage_gap_rows": 23}})
    _write_json(
        inventory_report,
        {"inventory_summary": {"archive_parquet_count": 0, "entry_manifest_source_count": 0}},
    )
    _write_json(
        audit_report,
        {
            "audit_summary": {
                "earliest_outside_open_time": "2026-03-24T16:28:35",
                "coverage_earliest_time": "2026-03-24T17:00:00",
                "coverage_latest_time": "2026-03-29T23:41:00",
                "outside_coverage_rows": 23,
                "forensic_ready_outside_rows": 15,
                "before_coverage_rows": 23,
            }
        },
    )
    _write_csv(
        trades_root / "entry_decisions.legacy_20260327_212023.csv",
        [
            {"time": "2026-03-27T15:29:43", "symbol": "XAUUSD", "action": "SELL"},
            {"time": "2026-03-27T16:00:00", "symbol": "XAUUSD", "action": "SELL"},
        ],
    )

    report = module.build_decision_log_coverage_gap_targeted_backfill_report(
        baseline_report_path=baseline_report,
        inventory_report_path=inventory_report,
        audit_report_path=audit_report,
        trades_root=trades_root,
        archive_root=archive_root,
        manifest_root=manifest_root,
        backfill_manifest_root=backfill_manifest_root,
        execute=False,
        adjacency_hours=2.0,
        now=datetime.fromisoformat("2026-03-30T02:30:00"),
    )

    summary = report["execution_summary"]
    assert summary["selected_source_count"] == 0
    assert summary["executed_backfill_count"] == 0
    assert summary["internal_overlap_source_available"] is False
    assert summary["external_backfill_required"] is True
