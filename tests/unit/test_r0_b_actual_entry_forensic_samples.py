import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "r0_b_actual_entry_forensic_samples.py"
spec = importlib.util.spec_from_file_location("r0_b_actual_entry_forensic_samples", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_closed_history(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def test_build_adverse_entry_sample_report_selects_recent_short_loss_and_excludes_snapshot_restored(tmp_path):
    source = tmp_path / "trade_closed_history.csv"
    _write_closed_history(
        source,
        [
            {
                "ticket": 1,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-28 10:00:00",
                "close_time": "2026-03-28 10:01:20",
                "open_ts": 100,
                "close_ts": 180,
                "profit": -3.25,
                "entry_setup_id": "range_upper_reversal_sell",
                "decision_winner": "cut_now",
                "final_outcome": "cut_now",
                "loss_quality_label": "neutral_loss",
                "loss_quality_reason": "fast_exit|defensive_exit",
                "exit_wait_state": "CUT_IMMEDIATE",
                "decision_row_key": "decision-key-1",
                "trade_link_key": "trade-link-1",
                "runtime_snapshot_key": "runtime-key-1",
                "replay_row_key": "replay-key-1",
                "status": "CLOSED",
            },
            {
                "ticket": 2,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-28 09:30:00",
                "close_time": "2026-03-28 09:31:00",
                "profit": -2.0,
                "entry_setup_id": "snapshot_restored_auto",
                "loss_quality_label": "bad_loss",
                "loss_quality_reason": "fast_exit|large_loss",
                "status": "CLOSED",
            },
            {
                "ticket": 3,
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-03-28 08:00:00",
                "close_time": "2026-03-28 09:00:00",
                "profit": 8.0,
                "entry_setup_id": "range_lower_reversal_buy",
                "loss_quality_label": "non_loss",
                "loss_quality_reason": "profit_non_negative",
                "status": "CLOSED",
            },
        ],
    )

    report = module.build_adverse_entry_sample_report(
        source_path=source,
        window_days=7,
        top_n=10,
        short_hold_sec=180.0,
        now=datetime.fromisoformat("2026-03-29T12:00:00"),
    )

    assert report["summary"]["selected_rows"] == 1
    sample = report["top_samples"][0]
    assert sample["ticket"] == 1
    assert sample["forensic_ready"] is True
    assert "short_hold" in sample["adverse_signals"]
    assert "cut_now_winner" in sample["adverse_signals"]
    assert report["summary"]["forensic_ready_rows"] == 1


def test_build_adverse_entry_sample_report_uses_text_times_when_ts_are_inverted(tmp_path):
    source = tmp_path / "trade_closed_history.csv"
    _write_closed_history(
        source,
        [
            {
                "ticket": 11,
                "symbol": "NAS100",
                "direction": "BUY",
                "open_time": "2026-03-28 10:00:00",
                "close_time": "2026-03-28 10:02:00",
                "open_ts": 2000,
                "close_ts": 1500,
                "profit": -4.0,
                "entry_setup_id": "trend_pullback_buy",
                "loss_quality_label": "bad_loss",
                "loss_quality_reason": "fast_exit|large_loss",
                "decision_winner": "cut_now",
                "final_outcome": "cut_now",
                "status": "CLOSED",
            }
        ],
    )

    report = module.build_adverse_entry_sample_report(
        source_path=source,
        window_days=7,
        top_n=10,
        now=datetime.fromisoformat("2026-03-29T12:00:00"),
    )

    assert report["summary"]["selected_rows"] == 1
    assert report["top_samples"][0]["hold_seconds"] == 120.0


def test_build_adverse_entry_sample_report_can_require_forensic_ready(tmp_path):
    source = tmp_path / "trade_closed_history.csv"
    _write_closed_history(
        source,
        [
            {
                "ticket": 21,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-28 11:00:00",
                "close_time": "2026-03-28 11:01:00",
                "profit": -2.0,
                "entry_setup_id": "range_upper_reversal_sell",
                "loss_quality_label": "neutral_loss",
                "loss_quality_reason": "fast_exit|defensive_exit",
                "decision_winner": "cut_now",
                "final_outcome": "cut_now",
                "decision_row_key": "",
                "trade_link_key": "",
                "status": "CLOSED",
            },
            {
                "ticket": 22,
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-28 11:03:00",
                "close_time": "2026-03-28 11:04:00",
                "profit": -2.5,
                "entry_setup_id": "range_upper_reversal_sell",
                "loss_quality_label": "neutral_loss",
                "loss_quality_reason": "fast_exit|defensive_exit",
                "decision_winner": "cut_now",
                "final_outcome": "cut_now",
                "decision_row_key": "decision-key-22",
                "trade_link_key": "trade-link-22",
                "status": "CLOSED",
            },
        ],
    )

    report = module.build_adverse_entry_sample_report(
        source_path=source,
        window_days=7,
        top_n=10,
        require_forensic_ready=True,
        now=datetime.fromisoformat("2026-03-29T12:00:00"),
    )

    assert report["summary"]["selected_rows"] == 1
    assert report["top_samples"][0]["ticket"] == 22


def test_write_adverse_entry_sample_report_writes_json_csv_and_markdown(tmp_path):
    source = tmp_path / "trade_closed_history.csv"
    output = tmp_path / "analysis"
    _write_closed_history(
        source,
        [
            {
                "ticket": 31,
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-03-28 12:00:00",
                "close_time": "2026-03-28 12:01:30",
                "profit": -5.0,
                "entry_setup_id": "range_lower_reversal_buy",
                "loss_quality_label": "bad_loss",
                "loss_quality_reason": "fast_exit|large_loss",
                "decision_winner": "cut_now",
                "final_outcome": "cut_now",
                "decision_row_key": "decision-key-31",
                "trade_link_key": "trade-link-31",
                "status": "CLOSED",
            }
        ],
    )

    result = module.write_adverse_entry_sample_report(
        source_path=source,
        output_dir=output,
        now=datetime.fromisoformat("2026-03-29T12:00:00"),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
    payload = json.loads(Path(result["latest_json_path"]).read_text(encoding="utf-8"))
    assert payload["report_version"] == module.REPORT_VERSION
    assert payload["summary"]["selected_rows"] == 1
    assert payload["top_samples"][0]["ticket"] == 31
