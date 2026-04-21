import pandas as pd

from backend.app.trading_application import TradingApplication


def _build_ohlcv_frame():
    rows = []
    for i in range(25):
        open_price = 105.0 - (i * 0.1)
        close_price = open_price - 0.05
        if i in (6, 12, 18):
            close_price = open_price - 0.002
        high_price = max(open_price, close_price) + 0.08
        low_price = min(open_price, close_price) - 0.07
        tick_volume = 100 + (i * 3)
        if i == 22:
            tick_volume = 500
        elif i == 23:
            tick_volume = 220
        elif i == 24:
            tick_volume = 180
        rows.append(
            {
                "time": pd.Timestamp("2026-04-02 09:00:00") + pd.Timedelta(minutes=i),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "tick_volume": tick_volume,
                "real_volume": 0.0,
            }
        )
    return pd.DataFrame(rows)


def test_build_micro_structure_v1_from_ohlcv_returns_ready_snapshot():
    df = _build_ohlcv_frame()

    out = TradingApplication.build_micro_structure_v1_from_ohlcv(
        df,
        metadata={
            "session_open": 105.0,
            "previous_session_close": 100.0,
        },
    )

    assert out["version"] == "micro_structure_v1"
    assert out["data_state"] == "READY"
    assert out["anchor_state"] == "READY"
    assert out["window_size"] == 20
    assert out["body_size_pct_20"] > 0.0
    assert out["doji_ratio_20"] > 0.0
    assert out["same_color_run_current"] >= 1
    assert out["same_color_run_max_20"] >= out["same_color_run_current"]
    assert out["volume_burst_ratio_20"] > 1.0
    assert out["volume_burst_decay_20"] > 0.0
    assert out["gap_fill_progress"] is not None
    assert 0.0 <= out["gap_fill_progress"] <= 1.0
    assert out["direction_run_stats"]["current"] == out["same_color_run_current"]
    assert out["direction_run_stats"]["max_20"] == out["same_color_run_max_20"]


def test_build_micro_structure_v1_from_ohlcv_marks_insufficient_bars_but_keeps_shape():
    df = _build_ohlcv_frame().head(5)

    out = TradingApplication.build_micro_structure_v1_from_ohlcv(df)

    assert out["data_state"] == "INSUFFICIENT_BARS"
    assert out["window_size"] == 5
    assert "body_size_pct_20" in out
    assert "range_compression_ratio_20" in out
    assert "direction_run_stats" in out
    assert out["anchor_state"] == "MISSING_GAP_ANCHOR"


def test_build_micro_structure_v1_from_ohlcv_keeps_gap_progress_null_without_anchor():
    df = _build_ohlcv_frame()

    out = TradingApplication.build_micro_structure_v1_from_ohlcv(df, metadata={})

    assert out["data_state"] == "READY"
    assert out["anchor_state"] == "MISSING_GAP_ANCHOR"
    assert out["gap_fill_progress"] is None
