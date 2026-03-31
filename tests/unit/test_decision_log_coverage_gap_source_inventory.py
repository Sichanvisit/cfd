import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "decision_log_coverage_gap_source_inventory.py"
spec = importlib.util.spec_from_file_location("decision_log_coverage_gap_source_inventory", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _touch(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_build_source_inventory_report_counts_sources_and_manifest_links(tmp_path):
    trades_root = tmp_path / "trades"
    archive_root = tmp_path / "archive" / "entry_decisions"
    manifest_root = tmp_path / "manifests"
    baseline_report = tmp_path / "c0.json"

    active_csv = _touch(trades_root / "entry_decisions.csv")
    legacy_csv = _touch(trades_root / "entry_decisions.legacy_20260327_212023.csv")
    active_detail = _touch(trades_root / "entry_decisions.detail.jsonl")
    rotated_detail = _touch(trades_root / "entry_decisions.detail.rotate_20260327_215356_815111.jsonl")
    archive_parquet = _touch(
        archive_root / "year=2026" / "month=03" / "day=27" / "entry_decisions_20260327_220000.parquet"
    )

    _write_json(
        baseline_report,
        {
            "baseline_summary": {
                "coverage_gap_rows": 23,
                "matched_rows": 7,
                "unmatched_outside_coverage": 23,
                "coverage_earliest_time": "2026-03-27T15:29:43",
                "coverage_latest_time": "2026-03-29T23:41:00",
            },
            "baseline_assessment": {
                "coverage_state": "coverage_gap_dominant",
                "reader_ready_but_source_gap_suspected": True,
            },
            "decision_sources": [str(active_csv), str(legacy_csv)],
            "decision_detail_sources": [str(rotated_detail)],
            "decision_archive_sources": [str(archive_parquet)],
        },
    )
    _write_json(
        manifest_root / "archive" / "entry_decisions_archive_20260328_000522.json",
        {
            "created_at": "2026-03-28T00:05:22",
            "job_name": "entry_decisions_archive",
            "output_path": str(archive_parquet),
            "schema_version": "entry_decisions_archive_v1",
            "row_count": 123,
            "time_range_start": "2026-03-27T21:20:23",
            "time_range_end": "2026-03-28T00:05:22",
        },
    )
    _write_json(
        manifest_root / "rollover" / "entry_decisions_rollover_20260328_000522.json",
        {
            "created_at": "2026-03-28T00:05:22",
            "job_name": "entry_decisions_rollover",
            "archive_path": str(archive_parquet),
            "schema_version": "entry_decisions_rollover_v2",
            "archive_time_range_start": "2026-03-27T21:20:23",
            "archive_time_range_end": "2026-03-28T00:05:22",
        },
    )
    _write_json(
        manifest_root / "retention" / "entry_decisions_retention_20260328_000522.json",
        {
            "created_at": "2026-03-28T00:05:22",
            "job_name": "entry_decisions_retention",
            "source_path": str(trades_root),
            "schema_version": "entry_decisions_retention_v1",
        },
    )

    report = module.build_decision_log_coverage_gap_source_inventory_report(
        baseline_report_path=baseline_report,
        trades_root=trades_root,
        archive_root=archive_root,
        manifest_root=manifest_root,
        now=datetime.fromisoformat("2026-03-30T02:00:00"),
    )

    summary = report["inventory_summary"]
    assessment = report["inventory_assessment"]
    source_records = report["source_records"]
    risk_codes = {item["code"] for item in report["risk_flags"]}
    archive_record = next(
        row for row in source_records if Path(row["path"]).resolve() == archive_parquet.resolve()
    )

    assert report["report_version"] == module.REPORT_VERSION
    assert summary["active_csv_count"] == 1
    assert summary["legacy_csv_count"] == 1
    assert summary["active_detail_count"] == 1
    assert summary["rotated_detail_count"] == 1
    assert summary["archive_parquet_count"] == 1
    assert summary["archive_manifest_count"] == 1
    assert summary["rollover_manifest_count"] == 1
    assert summary["retention_manifest_count"] == 1
    assert summary["baseline_referenced_inventory_rows"] >= 4
    assert assessment["recommended_next_step"] == "C2_coverage_audit_report"
    assert "archive_parquet_missing" not in risk_codes
    assert "coverage_gap_still_open" in risk_codes
    assert archive_record["manifest_reference_found"] is True
    assert archive_record["baseline_referenced"] is True


def test_write_source_inventory_report_writes_outputs_and_marks_archive_gap(tmp_path):
    trades_root = tmp_path / "trades"
    archive_root = tmp_path / "archive" / "entry_decisions"
    manifest_root = tmp_path / "manifests"
    baseline_report = tmp_path / "c0.json"
    output_dir = tmp_path / "analysis"

    active_csv = _touch(trades_root / "entry_decisions.csv")
    _touch(trades_root / "entry_decisions.detail.jsonl")
    _write_json(
        baseline_report,
        {
            "baseline_summary": {
                "coverage_gap_rows": 10,
                "matched_rows": 2,
                "unmatched_outside_coverage": 8,
            },
            "baseline_assessment": {
                "coverage_state": "coverage_gap_dominant",
                "reader_ready_but_source_gap_suspected": True,
            },
            "decision_sources": [str(active_csv)],
            "decision_detail_sources": [],
            "decision_archive_sources": [],
        },
    )

    result = module.write_decision_log_coverage_gap_source_inventory_report(
        baseline_report_path=baseline_report,
        trades_root=trades_root,
        archive_root=archive_root,
        manifest_root=manifest_root,
        output_dir=output_dir,
        now=datetime.fromisoformat("2026-03-30T02:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    risk_codes = {item["code"] for item in payload["risk_flags"]}
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["inventory_summary"]["archive_parquet_count"] == 0
    assert payload["inventory_assessment"]["inventory_state"] == "archive_gap_dominant"
    assert "archive_parquet_missing" in risk_codes
    assert "Decision Log Coverage Gap C1 Source Inventory" in markdown
    assert "`archive_parquet_missing`" in markdown
