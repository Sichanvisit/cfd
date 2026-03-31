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
