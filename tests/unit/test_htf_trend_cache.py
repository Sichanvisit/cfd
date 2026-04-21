from __future__ import annotations

from backend.services.htf_trend_cache import (
    HtfTrendCache,
    build_htf_alignment_v1,
    compute_htf_trend_snapshot,
)


class _FakeBroker:
    def __init__(self, rates_by_timeframe):
        self._rates_by_timeframe = dict(rates_by_timeframe)
        self.calls = []

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start_pos: int, count: int):
        self.calls.append((str(symbol), int(timeframe), int(start_pos), int(count)))
        return list(self._rates_by_timeframe.get(int(timeframe), []))


def _build_rates(*, start: float, step: float, count: int = 120):
    rows = []
    price = float(start)
    for index in range(count):
        open_price = price
        close_price = price + step
        high_price = max(open_price, close_price) + 0.5
        low_price = min(open_price, close_price) - 0.5
        rows.append(
            {
                "time": 1_700_000_000 + (index * 60),
                "open": float(open_price),
                "high": float(high_price),
                "low": float(low_price),
                "close": float(close_price),
            }
        )
        price = close_price
    return rows


def test_compute_htf_trend_snapshot_handles_insufficient_bars():
    payload = compute_htf_trend_snapshot(
        _build_rates(start=100.0, step=1.0, count=12),
        symbol="NAS100",
        timeframe_label="1H",
        now_ts=1_800_000_000.0,
        ttl_seconds=300.0,
    )

    assert payload["direction"] == "UNKNOWN"
    assert payload["strength"] == "UNKNOWN"
    assert payload["data_state"] == "INSUFFICIENT_BARS"
    assert payload["bar_count"] == 12


def test_htf_trend_cache_returns_cached_snapshot_until_ttl_expires():
    from backend.core.trade_constants import TIMEFRAME_H1

    broker = _FakeBroker({TIMEFRAME_H1: _build_rates(start=100.0, step=1.0)})
    now_box = {"value": 1_800_000_000.0}

    cache = HtfTrendCache(
        broker=broker,
        time_provider=lambda: now_box["value"],
        ttl_by_label={"1H": 300.0},
    )

    first = cache.get_trend("NAS100", "1H")
    second = cache.get_trend("NAS100", "1H")
    now_box["value"] += 301.0
    third = cache.get_trend("NAS100", "1H")

    assert first["direction"] == "UPTREND"
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert third["cache_hit"] is False
    assert len(broker.calls) == 2


def test_build_htf_state_v1_marks_against_htf_when_15m_reverses_against_higher_trend():
    from backend.core.trade_constants import TIMEFRAME_D1, TIMEFRAME_H1, TIMEFRAME_H4, TIMEFRAME_M15

    broker = _FakeBroker(
        {
            TIMEFRAME_M15: _build_rates(start=400.0, step=-2.0),
            TIMEFRAME_H1: _build_rates(start=100.0, step=2.0),
            TIMEFRAME_H4: _build_rates(start=150.0, step=2.2),
            TIMEFRAME_D1: _build_rates(start=220.0, step=2.4),
        }
    )
    cache = HtfTrendCache(broker=broker, time_provider=lambda: 1_800_000_000.0)

    payload = cache.build_htf_state_v1("NAS100")

    assert payload["trend_15m_direction"] == "DOWNTREND"
    assert payload["trend_1h_direction"] == "UPTREND"
    assert payload["trend_4h_direction"] == "UPTREND"
    assert payload["trend_1d_direction"] == "UPTREND"
    assert payload["htf_alignment_state"] == "AGAINST_HTF"
    assert payload["htf_alignment_detail"] == "AGAINST_HTF_UP"
    assert payload["htf_against_severity"] == "HIGH"


def test_build_htf_alignment_v1_returns_mixed_for_non_directional_15m():
    trend_map = {
        "15M": {"direction": "MIXED", "strength_score": 0.1, "age_seconds": 10},
        "1H": {"direction": "UPTREND", "strength_score": 2.1, "age_seconds": 20},
        "4H": {"direction": "UPTREND", "strength_score": 2.2, "age_seconds": 30},
        "1D": {"direction": "UPTREND", "strength_score": 2.3, "age_seconds": 40},
    }

    payload = build_htf_alignment_v1(trend_map, now_ts=1_800_000_000.0)

    assert payload["htf_alignment_state"] == "MIXED_HTF"
    assert payload["htf_alignment_detail"] == "MIXED"
    assert payload["htf_against_severity"] is None
    assert payload["htf_alignment_age_seconds"] == 40
