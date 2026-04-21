"""
Previous box state v1 calculator.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt

KST = ZoneInfo("Asia/Seoul")

PREVIOUS_BOX_CALCULATOR_VERSION = "previous_box_calculator_v1"
PREVIOUS_BOX_CONTEXT_VERSION = "previous_box_context_v1"
PREVIOUS_BOX_STATE_V1_VERSION = "previous_box_state_v1"


def _normalize_frame(raw_frame: Any) -> pd.DataFrame:
    if raw_frame is None:
        return pd.DataFrame()
    frame = pd.DataFrame(raw_frame)
    if frame.empty:
        return pd.DataFrame()
    for column in ("open", "high", "low", "close"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "time" in frame.columns:
        try:
            frame["time"] = pd.to_datetime(frame["time"], unit="s", errors="coerce")
        except Exception:
            frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
    frame = frame.dropna(subset=[column for column in ("open", "high", "low", "close") if column in frame.columns])
    return frame.reset_index(drop=True)


def _safe_div(numerator: float, denominator: float, *, default: float = 0.0) -> float:
    denom = abs(float(denominator))
    if denom <= 1e-9:
        return float(default)
    return float(numerator) / denom


def _retest_count(series: pd.Series, *, tolerance: float, high_side: bool) -> int:
    if series.empty:
        return 0
    pivot = float(series.max() if high_side else series.min())
    hits = int(sum(1 for value in series.tolist() if abs(float(value) - pivot) <= tolerance))
    return max(0, hits - 1)


def _classify_relation(*, current_price: float, box_high: float, box_low: float, tolerance: float) -> str:
    if current_price > (box_high + tolerance):
        return "ABOVE"
    if current_price < (box_low - tolerance):
        return "BELOW"
    if abs(current_price - box_high) <= tolerance:
        return "AT_HIGH"
    if abs(current_price - box_low) <= tolerance:
        return "AT_LOW"
    return "INSIDE"


def _classify_break_state(
    current_window: pd.DataFrame,
    *,
    current_price: float,
    box_high: float,
    box_low: float,
    tolerance: float,
    break_hold_bars: int,
) -> str:
    closes = pd.to_numeric(current_window.get("close", pd.Series(dtype=float)), errors="coerce").dropna().astype(float)
    highs = pd.to_numeric(current_window.get("high", pd.Series(dtype=float)), errors="coerce").dropna().astype(float)
    lows = pd.to_numeric(current_window.get("low", pd.Series(dtype=float)), errors="coerce").dropna().astype(float)
    opens = pd.to_numeric(current_window.get("open", pd.Series(dtype=float)), errors="coerce").dropna().astype(float)

    recent_closes = closes.tail(max(1, int(break_hold_bars)))
    touched_above = bool(not highs.empty and float(highs.max()) > float(box_high + tolerance))
    touched_below = bool(not lows.empty and float(lows.min()) < float(box_low - tolerance))
    held_above = bool(len(recent_closes) >= int(break_hold_bars) and all(float(value) > box_high for value in recent_closes.tolist()))
    held_below = bool(len(recent_closes) >= int(break_hold_bars) and all(float(value) < box_low for value in recent_closes.tolist()))

    if held_above:
        return "BREAKOUT_HELD"
    if held_below:
        return "BREAKDOWN_HELD"
    if touched_above and current_price < box_high:
        return "BREAKOUT_FAILED"
    if touched_below and current_price > box_low:
        return "RECLAIMED"

    latest_open = float(opens.iloc[-1]) if not opens.empty else current_price
    latest_close = float(closes.iloc[-1]) if not closes.empty else current_price
    if touched_above and current_price <= box_high and latest_close < latest_open:
        return "REJECTED"
    return "INSIDE"


def _classify_confidence(*, is_consolidation: bool, high_retests: int, low_retests: int) -> tuple[str, str]:
    structural_hits = int(high_retests) + int(low_retests)
    if bool(is_consolidation) and int(high_retests) >= 1 and int(low_retests) >= 1:
        return "HIGH", "STRUCTURAL"
    if bool(is_consolidation) or structural_hits >= 2:
        return "MEDIUM", "STRUCTURAL" if structural_hits >= 1 else "MECHANICAL"
    return "LOW", "MECHANICAL"


def _classify_lifecycle(
    *,
    confidence: str,
    is_consolidation: bool,
    relation: str,
    break_state: str,
) -> str:
    if str(confidence or "").upper() == "LOW" and not bool(is_consolidation):
        return "INVALIDATED"
    if str(break_state or "").upper() in {"BREAKOUT_HELD", "BREAKOUT_FAILED", "BREAKDOWN_HELD", "RECLAIMED"}:
        return "BROKEN"
    if str(relation or "").upper() in {"AT_HIGH", "AT_LOW"} and str(confidence or "").upper() in {"MEDIUM", "HIGH"}:
        return "RETESTED"
    if bool(is_consolidation) and str(confidence or "").upper() in {"MEDIUM", "HIGH"}:
        return "CONFIRMED"
    return "FORMING"


def _empty_previous_box_state(*, symbol: str, now_dt: datetime, data_state: str) -> dict[str, Any]:
    return {
        "symbol": str(symbol or "").upper().strip(),
        "previous_box_high": None,
        "previous_box_low": None,
        "previous_box_mid": None,
        "previous_box_mode": "MECHANICAL",
        "previous_box_confidence": "LOW",
        "previous_box_lifecycle": "FORMING",
        "previous_box_is_consolidation": False,
        "previous_box_relation": "UNKNOWN",
        "previous_box_break_state": "UNKNOWN",
        "distance_from_previous_box_high_pct": None,
        "distance_from_previous_box_low_pct": None,
        "previous_box_high_retest_count": 0,
        "previous_box_low_retest_count": 0,
        "previous_box_updated_at": now_dt.isoformat(),
        "previous_box_age_seconds": 0,
        "previous_box_data_state": str(data_state),
        "previous_box_context_version": PREVIOUS_BOX_CONTEXT_VERSION,
        "previous_box_state_version": PREVIOUS_BOX_STATE_V1_VERSION,
        "previous_box_calculator_version": PREVIOUS_BOX_CALCULATOR_VERSION,
    }


def compute_previous_box_state(
    frame: pd.DataFrame | None,
    *,
    symbol: str,
    current_price: float | None = None,
    proxy_state: Mapping[str, Any] | None = None,
    now_dt: datetime | None = None,
    window_size: int = 20,
    atr_period: int = 14,
    consolidation_atr_mult: float = 3.0,
    retest_tolerance_ratio: float = 0.15,
    break_hold_bars: int = 3,
) -> dict[str, Any]:
    built_at = now_dt or now_kst_dt()
    if getattr(built_at, "tzinfo", None) is None:
        built_at = built_at.replace(tzinfo=KST)

    normalized = _normalize_frame(frame)
    if normalized.empty:
        return _empty_previous_box_state(symbol=symbol, now_dt=built_at, data_state="MISSING_FRAME")
    if len(normalized) < (int(window_size) * 2):
        return _empty_previous_box_state(symbol=symbol, now_dt=built_at, data_state="INSUFFICIENT_BARS") | {
            "previous_box_data_state": "INSUFFICIENT_BARS",
        }

    current_window = normalized.tail(int(window_size)).copy()
    previous_window = normalized.iloc[-(int(window_size) * 2): -int(window_size)].copy()

    prev_high = float(pd.to_numeric(previous_window["high"], errors="coerce").max())
    prev_low = float(pd.to_numeric(previous_window["low"], errors="coerce").min())
    prev_mid = float((prev_high + prev_low) / 2.0)
    current_close = float(pd.to_numeric(current_window["close"], errors="coerce").iloc[-1])
    effective_price = float(current_close if current_price is None else current_price)

    prev_highs = pd.to_numeric(previous_window["high"], errors="coerce").dropna().astype(float)
    prev_lows = pd.to_numeric(previous_window["low"], errors="coerce").dropna().astype(float)
    prev_closes = pd.to_numeric(previous_window["close"], errors="coerce").dropna().astype(float)
    prev_opens = pd.to_numeric(previous_window["open"], errors="coerce").dropna().astype(float)

    prev_ranges = (prev_highs - prev_lows).abs()
    mean_range = float(prev_ranges.mean()) if not prev_ranges.empty else 0.0
    median_close = float(prev_closes.abs().median()) if not prev_closes.empty else 0.0
    tolerance = max(mean_range * float(retest_tolerance_ratio), median_close * 0.0005, 1e-9)

    proxy_map = dict(proxy_state or {})
    proxy_high_retests = int(proxy_map.get("swing_high_retest_count_20") or proxy_map.get("micro_swing_high_retest_count_20") or 0)
    proxy_low_retests = int(proxy_map.get("swing_low_retest_count_20") or proxy_map.get("micro_swing_low_retest_count_20") or 0)

    local_high_retests = _retest_count(prev_highs, tolerance=tolerance, high_side=True)
    local_low_retests = _retest_count(prev_lows, tolerance=tolerance, high_side=False)
    high_retests = max(int(local_high_retests), int(proxy_high_retests))
    low_retests = max(int(local_low_retests), int(proxy_low_retests))

    combined = normalized[["high", "low", "close"]].tail((int(window_size) * 2) + int(atr_period) + 5).copy()
    combined["high"] = pd.to_numeric(combined["high"], errors="coerce")
    combined["low"] = pd.to_numeric(combined["low"], errors="coerce")
    combined["close"] = pd.to_numeric(combined["close"], errors="coerce")
    combined = combined.dropna()
    prev_close_series = combined["close"].shift(1)
    tr = pd.concat(
        [
            (combined["high"] - combined["low"]).abs(),
            (combined["high"] - prev_close_series).abs(),
            (combined["low"] - prev_close_series).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_series = tr.rolling(int(atr_period)).mean().dropna()
    avg_atr = float(atr_series.tail(int(window_size)).mean()) if not atr_series.empty else mean_range

    prev_span = float(prev_high - prev_low)
    is_consolidation = bool(avg_atr > 1e-9 and prev_span < (avg_atr * float(consolidation_atr_mult)))
    confidence, mode = _classify_confidence(
        is_consolidation=is_consolidation,
        high_retests=high_retests,
        low_retests=low_retests,
    )

    relation = _classify_relation(
        current_price=effective_price,
        box_high=prev_high,
        box_low=prev_low,
        tolerance=tolerance,
    )
    break_state = _classify_break_state(
        current_window,
        current_price=effective_price,
        box_high=prev_high,
        box_low=prev_low,
        tolerance=tolerance,
        break_hold_bars=break_hold_bars,
    )
    lifecycle = _classify_lifecycle(
        confidence=confidence,
        is_consolidation=is_consolidation,
        relation=relation,
        break_state=break_state,
    )

    return {
        "symbol": str(symbol or "").upper().strip(),
        "previous_box_high": float(prev_high),
        "previous_box_low": float(prev_low),
        "previous_box_mid": float(prev_mid),
        "previous_box_mode": str(mode),
        "previous_box_confidence": str(confidence),
        "previous_box_lifecycle": str(lifecycle),
        "previous_box_is_consolidation": bool(is_consolidation),
        "previous_box_relation": str(relation),
        "previous_box_break_state": str(break_state),
        "distance_from_previous_box_high_pct": float(_safe_div(effective_price - prev_high, prev_high, default=0.0) * 100.0),
        "distance_from_previous_box_low_pct": float(_safe_div(effective_price - prev_low, abs(prev_low), default=0.0) * 100.0),
        "previous_box_high_retest_count": int(high_retests),
        "previous_box_low_retest_count": int(low_retests),
        "previous_box_updated_at": built_at.isoformat(),
        "previous_box_age_seconds": 0,
        "previous_box_data_state": "READY",
        "previous_box_context_version": PREVIOUS_BOX_CONTEXT_VERSION,
        "previous_box_state_version": PREVIOUS_BOX_STATE_V1_VERSION,
        "previous_box_calculator_version": PREVIOUS_BOX_CALCULATOR_VERSION,
    }


class PreviousBoxCalculator:
    def __init__(
        self,
        *,
        time_provider=None,
        window_size: int = 20,
        atr_period: int = 14,
        consolidation_atr_mult: float = 3.0,
        retest_tolerance_ratio: float = 0.15,
        break_hold_bars: int = 3,
    ):
        self._time_provider = time_provider or now_kst_dt
        self._window_size = max(10, int(window_size))
        self._atr_period = max(5, int(atr_period))
        self._consolidation_atr_mult = float(consolidation_atr_mult)
        self._retest_tolerance_ratio = float(retest_tolerance_ratio)
        self._break_hold_bars = max(2, int(break_hold_bars))

    def calculate(
        self,
        frame: pd.DataFrame | None,
        *,
        symbol: str,
        current_price: float | None = None,
        proxy_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        built_at = self._time_provider()
        return compute_previous_box_state(
            frame,
            symbol=symbol,
            current_price=current_price,
            proxy_state=proxy_state,
            now_dt=built_at,
            window_size=self._window_size,
            atr_period=self._atr_period,
            consolidation_atr_mult=self._consolidation_atr_mult,
            retest_tolerance_ratio=self._retest_tolerance_ratio,
            break_hold_bars=self._break_hold_bars,
        )
