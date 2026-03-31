import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "r0_b_actual_entry_forensic_table.py"
spec = importlib.util.spec_from_file_location("r0_b_actual_entry_forensic_table", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_sample_report(path: Path, top_samples: list[dict]) -> None:
    payload = {
        "report_version": "r0_b1_adverse_entry_sample_v1",
        "generated_at": "2026-03-29T12:00:00",
        "summary": {"selected_rows": len(top_samples)},
        "top_samples": top_samples,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_match_report(path: Path, matches: list[dict]) -> None:
    payload = {
        "report_version": "r0_b2_decision_row_match_v1",
        "generated_at": "2026-03-29T12:10:00",
        "summary": {"sample_rows": len(matches)},
        "matches": matches,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_forensic_table_classifies_strong_exact_and_normalizes_fields(tmp_path):
    sample_report = tmp_path / "samples.json"
    match_report = tmp_path / "matches.json"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 1001,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-29 10:00:00",
                "close_time": "2026-03-29 10:01:00",
                "entry_setup_id": "range_upper_reversal_sell",
                "decision_row_key": "decision-1001",
                "trade_link_key": "trade-1001",
                "runtime_snapshot_key": "runtime-1001",
                "replay_row_key": "replay-1001",
                "resolved_pnl": -3.2,
                "hold_seconds": 60.0,
                "priority_score": 18.0,
                "decision_winner": "cut_now",
                "loss_quality_label": "bad_loss",
                "loss_quality_reason": "fast_exit|large_loss",
                "adverse_signals": ["short_hold", "bad_loss"],
                "forensic_ready": True,
                "has_any_linkage_key": True,
            }
        ],
    )
    _write_match_report(
        match_report,
        [
            {
                "sample_rank": 1,
                "ticket": 1001,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-29 10:00:00",
                "close_time": "2026-03-29 10:01:00",
                "entry_setup_id": "range_upper_reversal_sell",
                "resolved_pnl": -3.2,
                "hold_seconds": 60.0,
                "priority_score": 18.0,
                "forensic_ready": True,
                "match_status": "exact",
                "match_strategy": "exact_decision_row_key",
                "match_score": 100.0,
                "time_delta_sec": None,
                "within_decision_log_coverage": True,
                "matched_time": "2026-03-29T10:00:01",
                "matched_action": "SELL",
                "matched_outcome": "entered",
                "matched_setup_id": "range_upper_reversal_sell",
                "matched_observe_reason": "upper_reject_confirm",
                "matched_blocked_by": "",
                "matched_action_none_reason": "",
                "matched_quick_trace_state": "confirm_ready",
                "matched_quick_trace_reason": "upper_reject_energy",
                "matched_probe_plan_ready": "true",
                "matched_probe_plan_reason": "enough_energy",
                "matched_consumer_check_stage": "READY",
                "matched_consumer_check_entry_ready": "true",
                "matched_r0_non_action_family": "",
                "matched_r0_semantic_runtime_state": "active",
                "matched_decision_row_key": "decision-1001",
                "matched_runtime_snapshot_key": "runtime-1001",
                "matched_trade_link_key": "trade-1001",
                "matched_replay_row_key": "replay-1001",
                "matched_source": "entry_decisions.csv",
            }
        ],
    )

    report = module.build_actual_entry_forensic_table_report(
        sample_report_path=sample_report,
        match_report_path=match_report,
        now=datetime.fromisoformat("2026-03-29T13:00:00"),
    )

    assert report["summary"]["row_count"] == 1
    row = report["forensic_rows"][0]
    assert row["linkage_quality"] == "strong_exact"
    assert row["forensic_confidence"] == "high"
    assert row["action"] == "SELL"
    assert row["setup_id"] == "range_upper_reversal_sell"
    assert row["entry_row_alignment_label"] == "row_supports_entry"
    assert row["suspicious_exact_runtime_linkage"] is False


def test_build_forensic_table_flags_suspicious_exact_runtime_linkage(tmp_path):
    sample_report = tmp_path / "samples.json"
    match_report = tmp_path / "matches.json"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 2002,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-27 14:35:49",
                "close_time": "2026-03-27 14:36:10",
                "entry_setup_id": "range_upper_reversal_sell",
                "resolved_pnl": -4.0,
                "hold_seconds": 21.0,
                "priority_score": 20.0,
                "adverse_signals": ["short_hold", "cut_now_winner"],
            }
        ],
    )
    _write_match_report(
        match_report,
        [
            {
                "sample_rank": 1,
                "ticket": 2002,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-27 14:35:49",
                "close_time": "2026-03-27 14:36:10",
                "entry_setup_id": "range_upper_reversal_sell",
                "resolved_pnl": -4.0,
                "hold_seconds": 21.0,
                "priority_score": 20.0,
                "forensic_ready": True,
                "match_status": "exact",
                "match_strategy": "exact_runtime_snapshot_key",
                "match_score": 90.0,
                "time_delta_sec": None,
                "within_decision_log_coverage": False,
                "matched_time": "2026-03-28T00:05:23",
                "matched_action": "",
                "matched_outcome": "",
                "matched_setup_id": "",
                "matched_observe_reason": "upper_reject_confirm",
                "matched_blocked_by": "barrier_guard",
                "matched_action_none_reason": "",
                "matched_quick_trace_state": "",
                "matched_quick_trace_reason": "",
                "matched_probe_plan_ready": "",
                "matched_probe_plan_reason": "",
                "matched_consumer_check_stage": "PROBE",
                "matched_consumer_check_entry_ready": "",
                "matched_r0_non_action_family": "",
                "matched_r0_semantic_runtime_state": "",
                "matched_decision_row_key": "",
                "matched_runtime_snapshot_key": "runtime_signal_row_v1|symbol=XAUUSD|anchor_field=signal_bar_ts|anchor_value=0.0|hint=BOTH",
                "matched_trade_link_key": "",
                "matched_replay_row_key": "",
                "matched_source": "entry_decisions.csv",
            }
        ],
    )

    report = module.build_actual_entry_forensic_table_report(
        sample_report_path=sample_report,
        match_report_path=match_report,
        now=datetime.fromisoformat("2026-03-29T13:00:00"),
    )

    row = report["forensic_rows"][0]
    assert row["linkage_quality"] == "suspicious_exact_runtime_linkage"
    assert row["suspicious_exact_runtime_linkage"] is True
    assert row["generic_runtime_snapshot_linkage"] is True
    assert row["needs_manual_review"] is True
    assert row["entry_row_alignment_label"] == "row_says_not_ready"
    assert row["decision_entry_gap_sec"] == 34174.0


def test_build_forensic_table_marks_coverage_gap_and_manual_review(tmp_path):
    sample_report = tmp_path / "samples.json"
    match_report = tmp_path / "matches.json"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 3003,
                "symbol": "NAS100",
                "direction": "BUY",
                "open_time": "2026-03-27 09:00:00",
                "close_time": "2026-03-27 09:01:00",
                "entry_setup_id": "trend_pullback_buy",
                "resolved_pnl": -2.5,
                "hold_seconds": 60.0,
                "priority_score": 15.0,
            }
        ],
    )
    _write_match_report(
        match_report,
        [
            {
                "sample_rank": 1,
                "ticket": 3003,
                "symbol": "NAS100",
                "direction": "BUY",
                "open_time": "2026-03-27 09:00:00",
                "close_time": "2026-03-27 09:01:00",
                "entry_setup_id": "trend_pullback_buy",
                "resolved_pnl": -2.5,
                "hold_seconds": 60.0,
                "priority_score": 15.0,
                "forensic_ready": False,
                "match_status": "unmatched_outside_coverage",
                "match_strategy": "",
                "match_score": 0.0,
                "time_delta_sec": None,
                "within_decision_log_coverage": False,
                "matched_time": "",
                "matched_action": "",
                "matched_outcome": "",
                "matched_setup_id": "",
                "matched_observe_reason": "",
                "matched_blocked_by": "",
                "matched_action_none_reason": "",
                "matched_quick_trace_state": "",
                "matched_quick_trace_reason": "",
                "matched_probe_plan_ready": "",
                "matched_probe_plan_reason": "",
                "matched_consumer_check_stage": "",
                "matched_consumer_check_entry_ready": "",
                "matched_r0_non_action_family": "",
                "matched_r0_semantic_runtime_state": "",
                "matched_decision_row_key": "",
                "matched_runtime_snapshot_key": "",
                "matched_trade_link_key": "",
                "matched_replay_row_key": "",
                "matched_source": "",
            }
        ],
    )

    report = module.build_actual_entry_forensic_table_report(
        sample_report_path=sample_report,
        match_report_path=match_report,
        now=datetime.fromisoformat("2026-03-29T13:00:00"),
    )

    row = report["forensic_rows"][0]
    assert row["linkage_quality"] == "coverage_gap"
    assert row["needs_manual_review"] is True
    assert row["entry_row_alignment_label"] == "unknown"
    assert report["summary"]["coverage_gap_rows"] == 1


def test_write_forensic_table_report_writes_json_csv_and_markdown(tmp_path):
    sample_report = tmp_path / "samples.json"
    match_report = tmp_path / "matches.json"
    output_dir = tmp_path / "analysis"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 4004,
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-03-29 12:00:00",
                "close_time": "2026-03-29 12:01:00",
                "entry_setup_id": "range_lower_reversal_buy",
                "resolved_pnl": -1.2,
                "hold_seconds": 60.0,
                "priority_score": 12.0,
            }
        ],
    )
    _write_match_report(
        match_report,
        [
            {
                "sample_rank": 1,
                "ticket": 4004,
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-03-29 12:00:00",
                "close_time": "2026-03-29 12:01:00",
                "entry_setup_id": "range_lower_reversal_buy",
                "resolved_pnl": -1.2,
                "hold_seconds": 60.0,
                "priority_score": 12.0,
                "forensic_ready": True,
                "match_status": "fallback",
                "match_strategy": "fallback_symbol_action_setup_time",
                "match_score": 70.0,
                "time_delta_sec": 2.0,
                "within_decision_log_coverage": True,
                "matched_time": "2026-03-29T12:00:02",
                "matched_action": "BUY",
                "matched_outcome": "entered",
                "matched_setup_id": "range_lower_reversal_buy",
                "matched_observe_reason": "lower_rebound_confirm",
                "matched_blocked_by": "",
                "matched_action_none_reason": "",
                "matched_quick_trace_state": "observe",
                "matched_quick_trace_reason": "lower_hold",
                "matched_probe_plan_ready": "true",
                "matched_probe_plan_reason": "ready",
                "matched_consumer_check_stage": "READY",
                "matched_consumer_check_entry_ready": "true",
                "matched_r0_non_action_family": "",
                "matched_r0_semantic_runtime_state": "active",
                "matched_decision_row_key": "decision-4004",
                "matched_runtime_snapshot_key": "runtime-4004",
                "matched_trade_link_key": "trade-4004",
                "matched_replay_row_key": "replay-4004",
                "matched_source": "entry_decisions.csv",
            }
        ],
    )

    result = module.write_actual_entry_forensic_table_report(
        sample_report_path=sample_report,
        match_report_path=match_report,
        output_dir=output_dir,
        now=datetime.fromisoformat("2026-03-29T13:00:00"),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
    payload = json.loads(Path(result["latest_json_path"]).read_text(encoding="utf-8"))
    assert payload["report_version"] == module.REPORT_VERSION
    assert payload["summary"]["row_count"] == 1
    assert payload["forensic_rows"][0]["ticket"] == 4004
