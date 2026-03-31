import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "r0_b_actual_entry_forensic_match_rows.py"
spec = importlib.util.spec_from_file_location("r0_b_actual_entry_forensic_match_rows", SCRIPT_PATH)
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


def _write_decision_rows(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _write_detail_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    {
                        "record_type": "entry_decision_detail_v1",
                        "schema_version": "entry_decision_detail_v1",
                        "row_key": str(row.get("decision_row_key", "") or ""),
                        "payload": row,
                    },
                    ensure_ascii=False,
            )
                + "\n"
            )


def _write_archive_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({key for row in rows for key in row.keys()})
    arrays = [pa.array([str(row.get(column, "") or "") for row in rows], type=pa.string()) for column in columns]
    table = pa.Table.from_arrays(arrays, names=columns)
    pq.write_table(table, path)


def test_build_match_report_prefers_exact_decision_row_key_match(tmp_path):
    sample_report = tmp_path / "samples.json"
    decisions = tmp_path / "entry_decisions.csv"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 101,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-29T10:00:00",
                "close_time": "2026-03-29T10:01:00",
                "entry_setup_id": "range_upper_reversal_sell",
                "decision_row_key": "decision|symbol=XAUUSD|ticket=101",
                "runtime_snapshot_key": "runtime-101",
                "trade_link_key": "trade-101",
                "replay_row_key": "replay-101",
                "resolved_pnl": -4.5,
                "hold_seconds": 60.0,
                "priority_score": 18.0,
                "forensic_ready": True,
                "adverse_signals": ["short_hold", "bad_loss"],
            }
        ],
    )
    _write_decision_rows(
        decisions,
        [
            {
                "time": "2026-03-29T10:00:02",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "range_upper_reversal_sell",
                "observe_reason": "observe_upper_reject",
                "blocked_by": "",
                "action_none_reason": "",
                "quick_trace_state": "confirm_ready",
                "quick_trace_reason": "upper_reject_energy",
                "consumer_check_stage": "READY",
                "consumer_check_entry_ready": "true",
                "decision_row_key": "decision|symbol=XAUUSD|ticket=101",
                "runtime_snapshot_key": "runtime-101",
                "trade_link_key": "trade-101",
                "replay_row_key": "replay-101",
                "r0_non_action_family": "",
                "r0_semantic_runtime_state": "active",
            }
        ],
    )

    report = module.build_actual_entry_forensic_match_report(
        sample_report_path=sample_report,
        decision_sources=[decisions],
        decision_detail_sources=[],
        now=datetime.fromisoformat("2026-03-29T12:00:00"),
    )

    assert report["summary"]["matched_rows"] == 1
    assert report["summary"]["exact_matches"] == 1
    match = report["matches"][0]
    assert match["match_status"] == "exact"
    assert match["match_strategy"] == "exact_decision_row_key"
    assert match["matched_observe_reason"] == "observe_upper_reject"


def test_build_match_report_supports_ticketless_decision_row_key_match(tmp_path):
    sample_report = tmp_path / "samples.json"
    decisions = tmp_path / "entry_decisions.csv"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 202,
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-03-29T11:00:00",
                "close_time": "2026-03-29T11:01:10",
                "entry_setup_id": "range_lower_reversal_buy",
                "decision_row_key": "decision|symbol=BTCUSD|ticket=202|ts=abc",
                "runtime_snapshot_key": "runtime-202",
                "trade_link_key": "trade-202",
                "replay_row_key": "",
                "resolved_pnl": -6.0,
                "hold_seconds": 70.0,
                "priority_score": 20.0,
                "forensic_ready": True,
                "adverse_signals": ["short_hold", "cut_now_winner"],
            }
        ],
    )
    _write_decision_rows(
        decisions,
        [
            {
                "time": "2026-03-29T11:00:03",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "range_lower_reversal_buy",
                "decision_row_key": "decision|symbol=BTCUSD|ticket=0|ts=abc",
                "runtime_snapshot_key": "runtime-202-hot",
                "trade_link_key": "",
                "replay_row_key": "",
            }
        ],
    )

    report = module.build_actual_entry_forensic_match_report(
        sample_report_path=sample_report,
        decision_sources=[decisions],
        decision_detail_sources=[],
        now=datetime.fromisoformat("2026-03-29T12:00:00"),
    )

    assert report["summary"]["matched_rows"] == 1
    match = report["matches"][0]
    assert match["match_status"] == "exact"
    assert match["match_strategy"] == "ticketless_decision_row_key"
    assert match["matched_decision_row_key"] == "decision|symbol=BTCUSD|ticket=0|ts=abc"


def test_build_match_report_uses_symbol_action_setup_time_fallback(tmp_path):
    sample_report = tmp_path / "samples.json"
    decisions = tmp_path / "entry_decisions.csv"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 303,
                "symbol": "NAS100",
                "direction": "BUY",
                "open_time": "2026-03-29T09:00:00",
                "close_time": "2026-03-29T09:02:00",
                "entry_setup_id": "trend_pullback_buy",
                "decision_row_key": "",
                "runtime_snapshot_key": "",
                "trade_link_key": "",
                "replay_row_key": "",
                "resolved_pnl": -3.0,
                "hold_seconds": 120.0,
                "priority_score": 16.0,
                "forensic_ready": False,
                "adverse_signals": ["fast_exit"],
            }
        ],
    )
    _write_decision_rows(
        decisions,
        [
            {
                "time": "2026-03-29T09:00:45",
                "symbol": "NAS100",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "trend_pullback_buy",
                "observe_reason": "trend_pullback_confirm",
                "decision_row_key": "",
                "runtime_snapshot_key": "",
                "trade_link_key": "",
                "replay_row_key": "",
            }
        ],
    )

    report = module.build_actual_entry_forensic_match_report(
        sample_report_path=sample_report,
        decision_sources=[decisions],
        decision_detail_sources=[],
        fallback_window_sec=120.0,
        now=datetime.fromisoformat("2026-03-29T12:00:00"),
    )

    assert report["summary"]["matched_rows"] == 1
    assert report["summary"]["fallback_matches"] == 1
    match = report["matches"][0]
    assert match["match_status"] == "fallback"
    assert match["match_strategy"] == "fallback_symbol_action_setup_time"
    assert match["time_delta_sec"] == 45.0


def test_build_match_report_can_match_from_detail_jsonl_source(tmp_path):
    sample_report = tmp_path / "samples.json"
    details = tmp_path / "entry_decisions.detail.jsonl"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 606,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-29T13:00:00",
                "close_time": "2026-03-29T13:00:45",
                "entry_setup_id": "range_upper_reversal_sell",
                "decision_row_key": "decision-606",
                "runtime_snapshot_key": "",
                "trade_link_key": "",
                "replay_row_key": "",
                "resolved_pnl": -2.5,
                "hold_seconds": 45.0,
                "priority_score": 17.0,
                "forensic_ready": True,
                "adverse_signals": ["short_hold"],
            }
        ],
    )
    _write_detail_rows(
        details,
        [
            {
                "time": "2026-03-29T13:00:01",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "range_upper_reversal_sell",
                "observe_reason": "upper_reject_confirm",
                "blocked_by": "",
                "action_none_reason": "",
                "quick_trace_state": "confirm_ready",
                "quick_trace_reason": "upper_reject_energy",
                "probe_plan_ready": True,
                "probe_plan_reason": "enough_energy",
                "consumer_check_stage": "READY",
                "consumer_check_entry_ready": True,
                "decision_row_key": "decision-606",
                "runtime_snapshot_key": "runtime-606",
                "trade_link_key": "",
                "replay_row_key": "",
            }
        ],
    )

    report = module.build_actual_entry_forensic_match_report(
        sample_report_path=sample_report,
        decision_sources=[],
        decision_detail_sources=[details],
        now=datetime.fromisoformat("2026-03-29T14:00:00"),
    )

    assert report["summary"]["matched_rows"] == 1
    assert report["summary"]["exact_matches"] == 1
    match = report["matches"][0]
    assert match["match_status"] == "exact"
    assert match["match_strategy"] == "exact_decision_row_key"
    assert match["matched_source"] == "entry_decisions.detail.jsonl"


def test_build_match_report_can_match_from_archive_parquet_source(tmp_path):
    sample_report = tmp_path / "samples.json"
    archive_path = tmp_path / "archive" / "entry_decisions" / "year=2026" / "month=03" / "day=29" / "entry_decisions_20260329.parquet"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 707,
                "symbol": "NAS100",
                "direction": "BUY",
                "open_time": "2026-03-29T15:00:00",
                "close_time": "2026-03-29T15:00:30",
                "entry_setup_id": "trend_pullback_buy",
                "decision_row_key": "decision-707",
                "runtime_snapshot_key": "",
                "trade_link_key": "",
                "replay_row_key": "",
                "resolved_pnl": -3.5,
                "hold_seconds": 30.0,
                "priority_score": 19.0,
                "forensic_ready": True,
                "adverse_signals": ["short_hold", "bad_loss"],
            }
        ],
    )
    _write_archive_rows(
        archive_path,
        [
            {
                "time": "2026-03-29T15:00:02",
                "symbol": "NAS100",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "trend_pullback_buy",
                "observe_reason": "trend_pullback_confirm",
                "decision_row_key": "decision-707",
                "runtime_snapshot_key": "runtime-707",
            }
        ],
    )

    report = module.build_actual_entry_forensic_match_report(
        sample_report_path=sample_report,
        decision_sources=[],
        decision_detail_sources=[],
        decision_archive_sources=[archive_path],
        now=datetime.fromisoformat("2026-03-29T16:00:00"),
    )

    assert report["summary"]["matched_rows"] == 1
    assert report["summary"]["exact_matches"] == 1
    assert report["decision_archive_sources"] == [str(archive_path)]
    match = report["matches"][0]
    assert match["match_status"] == "exact"
    assert match["match_strategy"] == "exact_decision_row_key"
    assert match["matched_source"] == "entry_decisions_20260329.parquet"


def test_discover_decision_archive_sources_uses_manifest_time_window(tmp_path):
    archive_root = tmp_path / "archive" / "entry_decisions"
    manifest_root = tmp_path / "manifests" / "archive"
    matching_archive = archive_root / "year=2026" / "month=03" / "day=25" / "entry_decisions_match.parquet"
    old_archive = archive_root / "year=2026" / "month=03" / "day=10" / "entry_decisions_old.parquet"
    _write_archive_rows(matching_archive, [{"time": "2026-03-25T12:00:00", "symbol": "BTCUSD"}])
    _write_archive_rows(old_archive, [{"time": "2026-03-10T12:00:00", "symbol": "BTCUSD"}])

    manifest_root.mkdir(parents=True, exist_ok=True)
    (manifest_root / "entry_decisions_archive_20260325_120000.json").write_text(
        json.dumps(
            {
                "output_path": str(matching_archive),
                "time_range_start": "2026-03-25T11:55:00",
                "time_range_end": "2026-03-25T12:10:00",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (manifest_root / "entry_decisions_archive_20260310_120000.json").write_text(
        json.dumps(
            {
                "output_path": str(old_archive),
                "time_range_start": "2026-03-10T11:55:00",
                "time_range_end": "2026-03-10T12:10:00",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    discovered = module.discover_decision_archive_sources(
        archive_root=archive_root,
        archive_manifest_root=manifest_root,
        sample_open_times=[datetime.fromisoformat("2026-03-25T12:00:30")],
        fallback_window_sec=180.0,
    )

    assert discovered == [matching_archive]


def test_build_match_report_does_not_treat_generic_runtime_snapshot_key_as_exact(tmp_path):
    sample_report = tmp_path / "samples.json"
    decisions = tmp_path / "entry_decisions.csv"
    generic_key = "runtime_signal_row_v1|symbol=XAUUSD|anchor_field=signal_bar_ts|anchor_value=0.0|hint=BOTH"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 909,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-27T14:35:49",
                "close_time": "2026-03-27T14:36:10",
                "entry_setup_id": "range_upper_reversal_sell",
                "decision_row_key": "",
                "runtime_snapshot_key": generic_key,
                "trade_link_key": "",
                "replay_row_key": "",
                "resolved_pnl": -4.0,
                "hold_seconds": 21.0,
                "priority_score": 20.0,
                "forensic_ready": True,
                "adverse_signals": ["short_hold"],
            }
        ],
    )
    _write_decision_rows(
        decisions,
        [
            {
                "time": "2026-03-28T00:05:23",
                "symbol": "XAUUSD",
                "action": "",
                "outcome": "wait",
                "setup_id": "",
                "runtime_snapshot_key": generic_key,
                "decision_row_key": "",
                "trade_link_key": "",
                "replay_row_key": "",
            }
        ],
    )

    report = module.build_actual_entry_forensic_match_report(
        sample_report_path=sample_report,
        decision_sources=[decisions],
        fallback_window_sec=180.0,
        decision_detail_sources=[],
        now=datetime.fromisoformat("2026-03-29T12:00:00"),
    )

    match = report["matches"][0]
    assert match["match_status"] == "unmatched_outside_coverage"
    assert match["match_strategy"] == ""


def test_build_match_report_marks_outside_coverage_when_sample_is_older_than_logs(tmp_path):
    sample_report = tmp_path / "samples.json"
    decisions = tmp_path / "entry_decisions.csv"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 404,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-28T08:00:00",
                "close_time": "2026-03-28T08:01:00",
                "entry_setup_id": "range_upper_reversal_sell",
                "decision_row_key": "",
                "runtime_snapshot_key": "",
                "trade_link_key": "",
                "replay_row_key": "",
                "resolved_pnl": -2.0,
                "hold_seconds": 60.0,
                "priority_score": 15.0,
                "forensic_ready": False,
                "adverse_signals": ["short_hold"],
            }
        ],
    )
    _write_decision_rows(
        decisions,
        [
            {
                "time": "2026-03-29T08:00:00",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "range_upper_reversal_sell",
                "decision_row_key": "",
                "runtime_snapshot_key": "",
                "trade_link_key": "",
                "replay_row_key": "",
            }
        ],
    )

    report = module.build_actual_entry_forensic_match_report(
        sample_report_path=sample_report,
        decision_sources=[decisions],
        decision_detail_sources=[],
        decision_archive_sources=[],
        fallback_window_sec=30.0,
        now=datetime.fromisoformat("2026-03-29T12:00:00"),
    )

    assert report["summary"]["matched_rows"] == 0
    assert report["summary"]["unmatched_outside_coverage"] == 1
    match = report["matches"][0]
    assert match["match_status"] == "unmatched_outside_coverage"
    assert match["within_decision_log_coverage"] is False


def test_write_actual_entry_forensic_match_report_writes_json_csv_and_markdown(tmp_path):
    sample_report = tmp_path / "samples.json"
    decisions = tmp_path / "entry_decisions.csv"
    output_dir = tmp_path / "analysis"
    _write_sample_report(
        sample_report,
        [
            {
                "ticket": 505,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-29T13:00:00",
                "close_time": "2026-03-29T13:00:50",
                "entry_setup_id": "range_upper_reversal_sell",
                "decision_row_key": "decision|symbol=XAUUSD|ticket=505",
                "runtime_snapshot_key": "",
                "trade_link_key": "",
                "replay_row_key": "",
                "resolved_pnl": -1.8,
                "hold_seconds": 50.0,
                "priority_score": 14.0,
                "forensic_ready": True,
                "adverse_signals": ["short_hold"],
            }
        ],
    )
    _write_decision_rows(
        decisions,
        [
            {
                "time": "2026-03-29T13:00:02",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "range_upper_reversal_sell",
                "decision_row_key": "decision|symbol=XAUUSD|ticket=505",
                "runtime_snapshot_key": "",
                "trade_link_key": "",
                "replay_row_key": "",
            }
        ],
    )

    result = module.write_actual_entry_forensic_match_report(
        sample_report_path=sample_report,
        output_dir=output_dir,
        decision_sources=[decisions],
        decision_detail_sources=[],
        now=datetime.fromisoformat("2026-03-29T13:30:00"),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
    payload = json.loads(Path(result["latest_json_path"]).read_text(encoding="utf-8"))
    assert payload["report_version"] == module.REPORT_VERSION
    assert payload["summary"]["exact_matches"] == 1
    assert payload["matches"][0]["ticket"] == 505
