import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "r0_b_actual_entry_forensic_families.py"
spec = importlib.util.spec_from_file_location("r0_b_actual_entry_forensic_families", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_forensic_table_report(path: Path, rows: list[dict]) -> None:
    payload = {
        "report_version": "r0_b3_forensic_table_v1",
        "generated_at": "2026-03-29T13:00:00",
        "summary": {"row_count": len(rows)},
        "forensic_rows": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_family_report_classifies_representative_families(tmp_path):
    report_path = tmp_path / "b3.json"
    _write_forensic_table_report(
        report_path,
        [
            {
                "sample_rank": 1,
                "ticket": 1001,
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "linkage_quality": "coverage_gap",
                "entry_row_alignment_label": "unknown",
                "consumer_check_stage": "",
                "blocked_by": "",
                "observe_reason": "",
                "suspicious_exact_runtime_linkage": False,
                "decision_entry_gap_sec": None,
                "resolved_pnl": -2.0,
                "hold_seconds": 50.0,
                "priority_score": 10.0,
            },
            {
                "sample_rank": 2,
                "ticket": 1002,
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "linkage_quality": "suspicious_exact_runtime_linkage",
                "entry_row_alignment_label": "row_says_not_ready",
                "consumer_check_stage": "PROBE",
                "blocked_by": "barrier_guard",
                "observe_reason": "upper_reject_confirm",
                "suspicious_exact_runtime_linkage": True,
                "decision_entry_gap_sec": 1200.0,
                "resolved_pnl": -3.0,
                "hold_seconds": 40.0,
                "priority_score": 20.0,
            },
            {
                "sample_rank": 3,
                "ticket": 1003,
                "symbol": "NAS100",
                "setup_id": "trend_pullback_buy",
                "linkage_quality": "fallback_match",
                "entry_row_alignment_label": "row_says_not_ready",
                "consumer_check_stage": "PROBE",
                "blocked_by": "",
                "observe_reason": "lower_rebound_confirm",
                "suspicious_exact_runtime_linkage": False,
                "decision_entry_gap_sec": 2.0,
                "resolved_pnl": -1.0,
                "hold_seconds": 60.0,
                "priority_score": 15.0,
            },
            {
                "sample_rank": 4,
                "ticket": 1004,
                "symbol": "XAUUSD",
                "setup_id": "",
                "linkage_quality": "fallback_match",
                "entry_row_alignment_label": "row_says_not_ready",
                "consumer_check_stage": "OBSERVE",
                "blocked_by": "forecast_guard",
                "observe_reason": "upper_reject_probe_observe",
                "suspicious_exact_runtime_linkage": False,
                "decision_entry_gap_sec": 1.0,
                "resolved_pnl": -1.2,
                "hold_seconds": 70.0,
                "priority_score": 14.0,
            },
            {
                "sample_rank": 5,
                "ticket": 1005,
                "symbol": "BTCUSD",
                "setup_id": "range_lower_reversal_buy",
                "linkage_quality": "strong_exact",
                "entry_row_alignment_label": "row_supports_entry",
                "consumer_check_stage": "READY",
                "blocked_by": "",
                "observe_reason": "lower_rebound_confirm",
                "suspicious_exact_runtime_linkage": False,
                "decision_entry_gap_sec": 1.0,
                "resolved_pnl": -1.5,
                "hold_seconds": 90.0,
                "priority_score": 12.0,
            },
        ],
    )

    report = module.build_actual_entry_forensic_family_report(
        forensic_table_report_path=report_path,
        now=datetime.fromisoformat("2026-03-29T14:00:00"),
    )

    rows = {row["sample_rank"]: row for row in report["classified_rows"]}
    assert rows[1]["forensic_family"] == "decision_log_coverage_gap"
    assert rows[2]["forensic_family"] == "runtime_linkage_integrity_gap"
    assert rows[3]["forensic_family"] == "probe_promoted_too_early"
    assert rows[4]["forensic_family"] == "guard_leak"
    assert rows[5]["forensic_family"] == "exit_not_entry_issue"
    assert report["summary"]["family_count"] >= 5
    assert report["summary"]["repeat_families"] == 0


def test_build_family_report_groups_repeated_rows_and_uses_priority_representative(tmp_path):
    report_path = tmp_path / "b3.json"
    _write_forensic_table_report(
        report_path,
        [
            {
                "sample_rank": 11,
                "ticket": 2011,
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "linkage_quality": "fallback_match",
                "entry_row_alignment_label": "row_says_not_ready",
                "consumer_check_stage": "PROBE",
                "blocked_by": "",
                "observe_reason": "upper_reject_confirm",
                "suspicious_exact_runtime_linkage": False,
                "decision_entry_gap_sec": 2.0,
                "resolved_pnl": -1.5,
                "hold_seconds": 80.0,
                "priority_score": 9.0,
            },
            {
                "sample_rank": 12,
                "ticket": 2012,
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "linkage_quality": "fallback_match",
                "entry_row_alignment_label": "row_says_not_ready",
                "consumer_check_stage": "PROBE",
                "blocked_by": "",
                "observe_reason": "upper_reject_confirm",
                "suspicious_exact_runtime_linkage": False,
                "decision_entry_gap_sec": 1.0,
                "resolved_pnl": -2.0,
                "hold_seconds": 60.0,
                "priority_score": 18.0,
            },
        ],
    )

    report = module.build_actual_entry_forensic_family_report(
        forensic_table_report_path=report_path,
        now=datetime.fromisoformat("2026-03-29T14:00:00"),
    )

    assert report["family_counts"]["probe_promoted_too_early"] == 2
    group = report["family_groups"][0]
    assert group["family"] == "probe_promoted_too_early"
    assert group["count"] == 2
    assert group["representative_sample_rank"] == 12
    assert group["representative_ticket"] == 2012


def test_write_family_report_writes_json_csv_and_markdown(tmp_path):
    report_path = tmp_path / "b3.json"
    output_dir = tmp_path / "analysis"
    _write_forensic_table_report(
        report_path,
        [
            {
                "sample_rank": 21,
                "ticket": 3021,
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "linkage_quality": "coverage_gap",
                "entry_row_alignment_label": "unknown",
                "consumer_check_stage": "",
                "blocked_by": "",
                "observe_reason": "",
                "suspicious_exact_runtime_linkage": False,
                "decision_entry_gap_sec": None,
                "resolved_pnl": -1.0,
                "hold_seconds": 30.0,
                "priority_score": 7.0,
            }
        ],
    )

    result = module.write_actual_entry_forensic_family_report(
        forensic_table_report_path=report_path,
        output_dir=output_dir,
        now=datetime.fromisoformat("2026-03-29T14:00:00"),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
    payload = json.loads(Path(result["latest_json_path"]).read_text(encoding="utf-8"))
    assert payload["report_version"] == module.REPORT_VERSION
    assert payload["summary"]["row_count"] == 1
    assert payload["family_counts"]["decision_log_coverage_gap"] == 1
