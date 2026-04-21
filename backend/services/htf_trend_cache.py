"""
HTF trend cache and HTF state v1 builder.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from adapters.mt5_broker_adapter import MT5BrokerAdapter
from backend.core.trade_constants import TIMEFRAME_D1, TIMEFRAME_H1, TIMEFRAME_H4, TIMEFRAME_M15
from ports.broker_port import BrokerPort

KST = ZoneInfo("Asia/Seoul")

HTF_TREND_CACHE_VERSION = "htf_trend_cache_v1"
HTF_CONTEXT_VERSION = "htf_context_v1"
HTF_STATE_V1_VERSION = "htf_state_v1"

DEFAULT_TIMEFRAME_LABELS = ("15M", "1H", "4H", "1D")
TIMEFRAME_CONST_BY_LABEL = {
    "15M": TIMEFRAME_M15,
    "1H": TIMEFRAME_H1,
    "4H": TIMEFRAME_H4,
    "1D": TIMEFRAME_D1,
}
DEFAULT_TTL_BY_LABEL = {
    "15M": 60.0,
    "1H": 300.0,
    "4H": 900.0,
    "1D": 3600.0,
}


def _iso_kst_from_ts(ts_value: float) -> str:
    return datetime.fromtimestamp(float(ts_value), tz=KST).isoformat()


def _normalize_frame(raw_rates: Any) -> pd.DataFrame:
    if raw_rates is None:
        return pd.DataFrame()
    frame = pd.DataFrame(raw_rates)
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


def _classify_direction(price: float, ema_fast: float, ema_slow: float) -> str:
    if price > ema_fast > ema_slow:
        return "UPTREND"
    if price < ema_fast < ema_slow:
        return "DOWNTREND"
    return "MIXED"


def _classify_strength(score_abs: float) -> str:
    if score_abs > 2.0:
        return "STRONG"
    if score_abs > 1.0:
        return "MODERATE"
    if score_abs > 0.3:
        return "WEAK"
    return "FLAT"


def _trend_sign(direction: str) -> int:
    norm = str(direction or "").upper().strip()
    if norm == "UPTREND":
        return 1
    if norm == "DOWNTREND":
        return -1
    return 0


def _empty_trend_snapshot(
    *,
    symbol: str,
    timeframe_label: str,
    now_ts: float,
    ttl_seconds: float,
    data_state: str,
) -> dict[str, Any]:
    updated_at = _iso_kst_from_ts(now_ts)
    return {
        "symbol": str(symbol or "").upper().strip(),
        "timeframe_label": str(timeframe_label),
        "direction": "UNKNOWN",
        "strength": "UNKNOWN",
        "strength_score": 0.0,
        "quality": None,
        "price": None,
        "ema20": None,
        "ema50": None,
        "atr14": None,
        "bar_count": 0,
        "source_bar_time": None,
        "updated_at": updated_at,
        "age_seconds": 0,
        "ttl_seconds": float(ttl_seconds),
        "cache_hit": False,
        "data_state": str(data_state),
        "trend_cache_version": HTF_TREND_CACHE_VERSION,
    }


def compute_htf_trend_snapshot(
    frame: pd.DataFrame | None,
    *,
    symbol: str,
    timeframe_label: str,
    now_ts: float,
    ttl_seconds: float,
    ema_fast_span: int = 20,
    ema_slow_span: int = 50,
    atr_period: int = 14,
) -> dict[str, Any]:
    normalized = _normalize_frame(frame)
    if normalized.empty:
        return _empty_trend_snapshot(
            symbol=symbol,
            timeframe_label=timeframe_label,
            now_ts=now_ts,
            ttl_seconds=ttl_seconds,
            data_state="MISSING_RATES",
        )
    required = max(int(ema_slow_span) + 5, int(atr_period) + 5)
    if len(normalized) < required:
        return _empty_trend_snapshot(
            symbol=symbol,
            timeframe_label=timeframe_label,
            now_ts=now_ts,
            ttl_seconds=ttl_seconds,
            data_state="INSUFFICIENT_BARS",
        ) | {"bar_count": int(len(normalized))}

    closes = normalized["close"].astype(float)
    highs = normalized["high"].astype(float)
    lows = normalized["low"].astype(float)

    ema_fast_series = closes.ewm(span=int(ema_fast_span), adjust=False).mean()
    ema_slow_series = closes.ewm(span=int(ema_slow_span), adjust=False).mean()

    prev_close = closes.shift(1)
    tr = pd.concat(
        [
            (highs - lows).abs(),
            (highs - prev_close).abs(),
            (lows - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_series = tr.rolling(int(atr_period)).mean().dropna()

    if atr_series.empty:
        return _empty_trend_snapshot(
            symbol=symbol,
            timeframe_label=timeframe_label,
            now_ts=now_ts,
            ttl_seconds=ttl_seconds,
            data_state="ATR_UNAVAILABLE",
        ) | {"bar_count": int(len(normalized))}

    price = float(closes.iloc[-1])
    ema_fast = float(ema_fast_series.iloc[-1])
    ema_slow = float(ema_slow_series.iloc[-1])
    atr_value = float(atr_series.iloc[-1])
    raw_score = float((ema_fast - ema_slow) / atr_value) if abs(atr_value) > 1e-9 else 0.0
    strength = _classify_strength(abs(raw_score))
    direction = _classify_direction(price, ema_fast, ema_slow)

    source_bar_time = None
    if "time" in normalized.columns and not normalized["time"].isna().all():
        try:
            source_bar = normalized["time"].iloc[-1]
            if isinstance(source_bar, pd.Timestamp):
                if source_bar.tzinfo is None:
                    source_bar = source_bar.tz_localize("UTC").tz_convert(KST)
                else:
                    source_bar = source_bar.tz_convert(KST)
                source_bar_time = source_bar.isoformat()
        except Exception:
            source_bar_time = None

    return {
        "symbol": str(symbol or "").upper().strip(),
        "timeframe_label": str(timeframe_label),
        "direction": str(direction),
        "strength": str(strength),
        "strength_score": float(raw_score),
        "quality": None,
        "price": float(price),
        "ema20": float(ema_fast),
        "ema50": float(ema_slow),
        "atr14": float(atr_value),
        "bar_count": int(len(normalized)),
        "source_bar_time": source_bar_time,
        "updated_at": _iso_kst_from_ts(now_ts),
        "age_seconds": 0,
        "ttl_seconds": float(ttl_seconds),
        "cache_hit": False,
        "data_state": "READY",
        "trend_cache_version": HTF_TREND_CACHE_VERSION,
    }


def _classify_against_severity(opposite_scores: list[float]) -> str | None:
    if not opposite_scores:
        return None
    count = len(opposite_scores)
    mean_abs_score = sum(abs(score) for score in opposite_scores) / max(count, 1)
    if count >= 3 and mean_abs_score >= 2.0:
        return "HIGH"
    if count >= 2 and mean_abs_score >= 1.0:
        return "MEDIUM"
    return "LOW"


def build_htf_alignment_v1(trend_map: dict[str, dict[str, Any]], *, now_ts: float) -> dict[str, Any]:
    trend_15m = dict(trend_map.get("15M", {}) or {})
    sign_15m = _trend_sign(str(trend_15m.get("direction", "")))
    higher_labels = ("1H", "4H", "1D")
    higher_signs = {label: _trend_sign(str(dict(trend_map.get(label, {}) or {}).get("direction", ""))) for label in higher_labels}
    higher_scores = {label: float(dict(trend_map.get(label, {}) or {}).get("strength_score", 0.0) or 0.0) for label in higher_labels}

    match_count = sum(1 for value in higher_signs.values() if value == sign_15m and value != 0)
    opposite_labels = [label for label, value in higher_signs.items() if value == (-1 * sign_15m) and value != 0]
    opposite_scores = [higher_scores[label] for label in opposite_labels]
    mixed_count = sum(1 for value in higher_signs.values() if value == 0)

    alignment_state = "MIXED_HTF"
    alignment_detail = "MIXED"
    against_severity = None

    if sign_15m > 0:
        if match_count == 3:
            alignment_state = "WITH_HTF"
            alignment_detail = "ALL_ALIGNED_UP"
        elif match_count >= 2 and not opposite_labels:
            alignment_state = "WITH_HTF"
            alignment_detail = "MOSTLY_ALIGNED_UP"
        elif len(opposite_labels) >= 2:
            alignment_state = "AGAINST_HTF"
            alignment_detail = "AGAINST_HTF_DOWN"
            against_severity = _classify_against_severity(opposite_scores)
    elif sign_15m < 0:
        if match_count == 3:
            alignment_state = "WITH_HTF"
            alignment_detail = "ALL_ALIGNED_DOWN"
        elif match_count >= 2 and not opposite_labels:
            alignment_state = "WITH_HTF"
            alignment_detail = "MOSTLY_ALIGNED_DOWN"
        elif len(opposite_labels) >= 2:
            alignment_state = "AGAINST_HTF"
            alignment_detail = "AGAINST_HTF_UP"
            against_severity = _classify_against_severity(opposite_scores)

    if sign_15m == 0 or (alignment_state == "MIXED_HTF" and mixed_count >= 0):
        alignment_state = "MIXED_HTF"
        alignment_detail = "MIXED"
        against_severity = None

    max_age = max(
        float(dict(trend_map.get(label, {}) or {}).get("age_seconds", 0) or 0)
        for label in DEFAULT_TIMEFRAME_LABELS
        if label in trend_map
    )

    return {
        "htf_alignment_state": str(alignment_state),
        "htf_alignment_detail": str(alignment_detail),
        "htf_against_severity": against_severity,
        "htf_alignment_updated_at": _iso_kst_from_ts(now_ts),
        "htf_alignment_age_seconds": int(max_age),
        "htf_context_version": HTF_CONTEXT_VERSION,
        "htf_state_version": HTF_STATE_V1_VERSION,
    }


class HtfTrendCache:
    def __init__(
        self,
        broker: BrokerPort | None = None,
        *,
        time_provider=None,
        ttl_by_label: dict[str, float] | None = None,
        rate_count: int = 120,
        ema_fast_span: int = 20,
        ema_slow_span: int = 50,
        atr_period: int = 14,
    ):
        self.broker = broker or MT5BrokerAdapter()
        self._time_provider = time_provider or time.time
        self._ttl_by_label = {**DEFAULT_TTL_BY_LABEL, **dict(ttl_by_label or {})}
        self._rate_count = max(60, int(rate_count))
        self._ema_fast_span = max(5, int(ema_fast_span))
        self._ema_slow_span = max(self._ema_fast_span + 1, int(ema_slow_span))
        self._atr_period = max(5, int(atr_period))
        self._cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._lock = threading.RLock()

    def _now_ts(self) -> float:
        return float(self._time_provider())

    @staticmethod
    def _cache_key(symbol: str, timeframe_label: str) -> tuple[str, str]:
        return (str(symbol or "").upper().strip(), str(timeframe_label or "").upper().strip())

    def invalidate(self, *, symbol: str | None = None, timeframe_label: str | None = None) -> None:
        with self._lock:
            if symbol is None and timeframe_label is None:
                self._cache.clear()
                return
            symbol_key = str(symbol or "").upper().strip() if symbol is not None else None
            tf_key = str(timeframe_label or "").upper().strip() if timeframe_label is not None else None
            delete_keys = []
            for cache_key in self._cache.keys():
                key_symbol, key_tf = cache_key
                if symbol_key is not None and key_symbol != symbol_key:
                    continue
                if tf_key is not None and key_tf != tf_key:
                    continue
                delete_keys.append(cache_key)
            for cache_key in delete_keys:
                self._cache.pop(cache_key, None)

    def _fetch_frame(self, symbol: str, timeframe_label: str) -> pd.DataFrame:
        timeframe_const = TIMEFRAME_CONST_BY_LABEL[str(timeframe_label)]
        raw_rates = self.broker.copy_rates_from_pos(str(symbol), timeframe_const, 0, int(self._rate_count))
        return _normalize_frame(raw_rates)

    def get_trend(self, symbol: str, timeframe_label: str) -> dict[str, Any]:
        symbol_key, tf_key = self._cache_key(symbol, timeframe_label)
        ttl_seconds = float(self._ttl_by_label.get(tf_key, 300.0))
        now_ts = self._now_ts()
        cache_key = (symbol_key, tf_key)

        with self._lock:
            cached = dict(self._cache.get(cache_key, {}) or {})

        if cached:
            cached_at = float(cached.get("_cached_at", 0.0) or 0.0)
            age = max(0.0, now_ts - cached_at)
            if age <= ttl_seconds:
                out = {key: value for key, value in cached.items() if key != "_cached_at"}
                out["age_seconds"] = int(age)
                out["ttl_seconds"] = ttl_seconds
                out["cache_hit"] = True
                return out

        frame = self._fetch_frame(symbol_key, tf_key)
        snapshot = compute_htf_trend_snapshot(
            frame,
            symbol=symbol_key,
            timeframe_label=tf_key,
            now_ts=now_ts,
            ttl_seconds=ttl_seconds,
            ema_fast_span=self._ema_fast_span,
            ema_slow_span=self._ema_slow_span,
            atr_period=self._atr_period,
        )
        stored = dict(snapshot)
        stored["_cached_at"] = now_ts
        with self._lock:
            self._cache[cache_key] = stored
        return snapshot

    def get_all_trends(self, symbol: str, *, timeframe_labels: tuple[str, ...] | None = None) -> dict[str, dict[str, Any]]:
        labels = tuple(timeframe_labels or DEFAULT_TIMEFRAME_LABELS)
        return {label: self.get_trend(symbol, label) for label in labels}

    def build_htf_state_v1(self, symbol: str) -> dict[str, Any]:
        now_ts = self._now_ts()
        trend_map = self.get_all_trends(symbol)
        alignment = build_htf_alignment_v1(trend_map, now_ts=now_ts)

        payload: dict[str, Any] = {
            "symbol": str(symbol or "").upper().strip(),
            "htf_context_version": HTF_CONTEXT_VERSION,
            "htf_state_version": HTF_STATE_V1_VERSION,
            "htf_state_built_at": _iso_kst_from_ts(now_ts),
        }
        for label, prefix in (("15M", "15m"), ("1H", "1h"), ("4H", "4h"), ("1D", "1d")):
            node = dict(trend_map.get(label, {}) or {})
            payload[f"trend_{prefix}_direction"] = node.get("direction")
            payload[f"trend_{prefix}_strength"] = node.get("strength")
            payload[f"trend_{prefix}_strength_score"] = node.get("strength_score")
            payload[f"trend_{prefix}_quality"] = node.get("quality")
            payload[f"trend_{prefix}_updated_at"] = node.get("updated_at")
            payload[f"trend_{prefix}_age_seconds"] = node.get("age_seconds")
        payload.update(alignment)
        return payload
