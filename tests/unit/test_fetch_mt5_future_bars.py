import importlib.util
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fetch_mt5_future_bars.py"
spec = importlib.util.spec_from_file_location("fetch_mt5_future_bars", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_load_anchor_windows_prefers_signal_bar_ts_and_filters_symbols(tmp_path):
    source = tmp_path / "entry_decisions.csv"
    pd.DataFrame(
        [
            {"symbol": "BTCUSD", "signal_bar_ts": 1773665100, "time": "2026-03-16T18:55:45"},
            {"symbol": "BTCUSD", "signal_bar_ts": 1773666000, "time": "2026-03-16T19:10:45"},
            {"symbol": "XAUUSD", "signal_bar_ts": "", "time": "2026-03-16T18:56:00"},
        ]
    ).to_csv(source, index=False, encoding="utf-8-sig")

    windows = module._load_anchor_windows(source, symbols={"BTCUSD"})

    assert sorted(windows) == ["BTCUSD"]
    assert windows["BTCUSD"].min_anchor_ts == 1773665100
    assert windows["BTCUSD"].max_anchor_ts == 1773666000
    assert windows["BTCUSD"].rows == 2


def test_compute_fetch_bounds_expands_by_bar_count():
    start_ts, end_ts = module._compute_fetch_bounds(
        min_anchor_ts=1773665100,
        max_anchor_ts=1773666000,
        timeframe_seconds=900,
        lookback_bars=1,
        lookahead_bars=8,
    )

    assert start_ts == 1773664200
    assert end_ts == 1773673200


def test_mt5_rate_to_row_normalizes_fields():
    rate = {
        "time": 1773666000,
        "open": 70000.1,
        "high": 70100.2,
        "low": 69900.3,
        "close": 70050.4,
        "tick_volume": 123,
        "spread": 9,
        "real_volume": 77,
    }

    row = module._mt5_rate_to_row("BTCUSD", "M15", rate)

    assert row == {
        "symbol": "BTCUSD",
        "time": 1773666000,
        "open": 70000.1,
        "high": 70100.2,
        "low": 69900.3,
        "close": 70050.4,
        "tick_volume": 123,
        "spread": 9,
        "real_volume": 77,
        "source_timeframe": "M15",
    }


def test_inspect_future_bar_freshness_marks_stale_and_fresh(tmp_path):
    entry_path = tmp_path / "entry_decisions.csv"
    future_path = tmp_path / "future_bars_entry_decisions_m15.csv"
    pd.DataFrame(
        [
            {"symbol": "BTCUSD", "signal_bar_ts": 2000, "time": "2026-03-16T18:55:45"},
            {"symbol": "XAUUSD", "signal_bar_ts": 1500, "time": "2026-03-16T18:56:00"},
        ]
    ).to_csv(entry_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"symbol": "BTCUSD", "time": 1900, "open": 1, "high": 2, "low": 0.5, "close": 1.5},
            {"symbol": "XAUUSD", "time": 1500, "open": 1, "high": 2, "low": 0.5, "close": 1.5},
        ]
    ).to_csv(future_path, index=False, encoding="utf-8-sig")

    summary = module.inspect_future_bar_freshness(
        entry_decisions=entry_path,
        output_path=future_path,
        timeframe="M15",
    )

    assert summary["status"] == "stale"
    assert summary["stale_symbols"] == ["BTCUSD"]
    assert summary["fresh_symbols"] == ["XAUUSD"]
    assert summary["per_symbol"]["BTCUSD"]["lag_seconds"] == 100


def test_fetch_mt5_future_bars_only_if_stale_skips_without_mt5_when_fresh(tmp_path, monkeypatch):
    entry_path = tmp_path / "entry_decisions.csv"
    future_path = tmp_path / "future_bars_entry_decisions_m15.csv"
    pd.DataFrame(
        [
            {"symbol": "BTCUSD", "signal_bar_ts": 2000, "time": "2026-03-16T18:55:45"},
        ]
    ).to_csv(entry_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"symbol": "BTCUSD", "time": 2100, "open": 1, "high": 2, "low": 0.5, "close": 1.5},
        ]
    ).to_csv(future_path, index=False, encoding="utf-8-sig")

    def _boom():
        raise AssertionError("MT5 should not be called when future bars are already fresh")

    monkeypatch.setattr(module, "connect_to_mt5", _boom)

    summary = module.fetch_mt5_future_bars(
        entry_decisions=entry_path,
        output_path=future_path,
        timeframe="M15",
        only_if_stale=True,
    )

    assert summary["skipped"] is True
    assert summary["skip_reason"] == "future_bars_already_fresh"
    assert summary["freshness_before"]["status"] == "fresh"
    assert summary["freshness_after"]["status"] == "fresh"
