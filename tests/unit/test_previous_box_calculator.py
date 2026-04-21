from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.services.previous_box_calculator import PreviousBoxCalculator, compute_previous_box_state

KST = ZoneInfo("Asia/Seoul")


def _build_box_rows(*, low: float, high: float, count: int = 20):
    rows = []
    for index in range(count):
        open_price = low + (0.2 if index % 2 == 0 else 0.6)
        close_price = low + (0.6 if index % 2 == 0 else 0.2)
        rows.append(
            {
                "time": 1_700_000_000 + (index * 60),
                "open": open_price,
                "high": high - (0.05 if index % 3 else 0.0),
                "low": low + (0.05 if index % 4 else 0.0),
                "close": close_price,
            }
        )
    return rows


def _build_trend_rows(*, start: float, step: float, count: int = 20, time_offset: int = 0):
    rows = []
    price = float(start)
    for index in range(count):
        open_price = price
        close_price = price + step
        rows.append(
            {
                "time": 1_700_100_000 + time_offset + (index * 60),
                "open": open_price,
                "high": max(open_price, close_price) + 0.3,
                "low": min(open_price, close_price) - 0.3,
                "close": close_price,
            }
        )
        price = close_price
    return rows


def test_previous_box_state_handles_insufficient_bars():
    payload = compute_previous_box_state(
        _build_box_rows(low=100.0, high=101.0, count=18),
        symbol="NAS100",
        now_dt=datetime(2026, 4, 13, 22, 0, tzinfo=KST),
    )

    assert payload["previous_box_data_state"] == "INSUFFICIENT_BARS"
    assert payload["previous_box_break_state"] == "UNKNOWN"


def test_previous_box_state_marks_confirmed_structural_box_inside():
    previous_rows = _build_box_rows(low=100.0, high=101.0, count=20)
    current_rows = _build_box_rows(low=100.1, high=100.9, count=20)

    payload = compute_previous_box_state(
        previous_rows + current_rows,
        symbol="NAS100",
        now_dt=datetime(2026, 4, 13, 22, 0, tzinfo=KST),
    )

    assert payload["previous_box_data_state"] == "READY"
    assert payload["previous_box_is_consolidation"] is True
    assert payload["previous_box_confidence"] in {"MEDIUM", "HIGH"}
    assert payload["previous_box_mode"] == "STRUCTURAL"
    assert payload["previous_box_relation"] == "INSIDE"
    assert payload["previous_box_break_state"] == "INSIDE"
    assert payload["previous_box_lifecycle"] == "CONFIRMED"


def test_previous_box_state_marks_breakout_held_when_recent_closes_hold_above_box():
    previous_rows = _build_box_rows(low=100.0, high=101.0, count=20)
    current_rows = _build_trend_rows(start=101.2, step=0.4, count=20, time_offset=20_000)

    payload = compute_previous_box_state(
        previous_rows + current_rows,
        symbol="NAS100",
        now_dt=datetime(2026, 4, 13, 22, 0, tzinfo=KST),
    )

    assert payload["previous_box_break_state"] == "BREAKOUT_HELD"
    assert payload["previous_box_relation"] == "ABOVE"
    assert payload["previous_box_lifecycle"] == "BROKEN"
    assert payload["distance_from_previous_box_high_pct"] > 0.0


def test_previous_box_state_marks_invalidated_for_non_consolidation_previous_range():
    previous_rows = _build_trend_rows(start=100.0, step=1.6, count=20)
    current_rows = _build_trend_rows(start=132.0, step=0.2, count=20, time_offset=20_000)

    payload = compute_previous_box_state(
        previous_rows + current_rows,
        symbol="NAS100",
        now_dt=datetime(2026, 4, 13, 22, 0, tzinfo=KST),
    )

    assert payload["previous_box_is_consolidation"] is False
    assert payload["previous_box_confidence"] == "LOW"
    assert payload["previous_box_lifecycle"] == "INVALIDATED"
    assert payload["previous_box_mode"] == "MECHANICAL"


def test_previous_box_calculator_accepts_proxy_retests():
    previous_rows = _build_box_rows(low=100.0, high=101.0, count=20)
    current_rows = _build_box_rows(low=100.1, high=100.8, count=20)

    calculator = PreviousBoxCalculator(
        time_provider=lambda: datetime(2026, 4, 13, 22, 0, tzinfo=KST),
    )
    payload = calculator.calculate(
        previous_rows + current_rows,
        symbol="NAS100",
        proxy_state={
            "micro_swing_high_retest_count_20": 2,
            "micro_swing_low_retest_count_20": 1,
        },
    )

    assert payload["previous_box_high_retest_count"] >= 2
    assert payload["previous_box_low_retest_count"] >= 1
    assert payload["previous_box_mode"] == "STRUCTURAL"
