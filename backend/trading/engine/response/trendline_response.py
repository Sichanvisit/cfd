from __future__ import annotations

from typing import Any

from backend.trading.engine.core.models import EngineContext

_TRENDLINE_TIMEFRAME_SUFFIX = {
    "1M": "m1",
    "15M": "m15",
    "1H": "h1",
    "4H": "h4",
}


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _merge_strength(primary_scores: list[float], support_scores: list[float], *, primary_support_weight: float = 0.18) -> float:
    if not primary_scores:
        return 0.0
    ordered = sorted((_clamp01(v) for v in primary_scores if float(v) > 0.0), reverse=True)
    if not ordered:
        return 0.0
    dominant = ordered[0]
    support = min(sum(ordered[1:]) * primary_support_weight, 0.18)
    touch = min(sum(_clamp01(v) for v in support_scores) * 0.08, 0.08)
    return _clamp01(dominant + support + touch)


def _timeframe_bar_payload(md: dict[str, Any], tf: str) -> dict[str, Any]:
    bar_map = dict(md.get("mtf_trendline_bar_map_v1") or {})
    return dict(bar_map.get(tf) or {})


def compute_trendline_responses(ctx: EngineContext) -> dict[str, Any]:
    md = dict(ctx.metadata or {})
    trend_map = dict(md.get("mtf_trendline_map_v1") or {})
    entries = dict(trend_map.get("entries") or {})
    scale = max(abs(_to_float(ctx.volatility_scale, 0.0)), abs(_to_float(ctx.price, 0.0)) * 0.00025, 1e-9)
    base_tol = max(
        abs(_to_float(md.get("trendline_touch_tolerance"), 0.0)),
        abs(_to_float(md.get("box_touch_tolerance"), 0.0)) * 2.0,
        abs(_to_float(md.get("band_touch_tolerance"), 0.0)) * 2.0,
        scale * 0.18,
        1e-9,
    )

    out: dict[str, Any] = {}
    support_hold_scores: list[float] = []
    support_break_scores: list[float] = []
    resistance_reject_scores: list[float] = []
    resistance_break_scores: list[float] = []
    support_touch_scores: list[float] = []
    resistance_touch_scores: list[float] = []
    per_tf_debug: dict[str, Any] = {}
    fired_signals: list[str] = []

    for tf, suffix in _TRENDLINE_TIMEFRAME_SUFFIX.items():
        entry = dict(entries.get(tf) or {})
        bar = _timeframe_bar_payload(md, tf)
        open_now = _to_float(bar.get("open"), ctx.price)
        high_now = _to_float(bar.get("high"), ctx.price)
        low_now = _to_float(bar.get("low"), ctx.price)
        close_now = _to_float(bar.get("close"), ctx.price)
        prev_close = _to_float(bar.get("previous_close"), close_now)
        tf_tol = base_tol * {
            "1M": 0.70,
            "15M": 0.90,
            "1H": 1.05,
            "4H": 1.20,
        }.get(tf, 1.0)

        lower_wick = max(0.0, min(open_now, close_now) - low_now)
        upper_wick = max(0.0, high_now - max(open_now, close_now))
        body = max(abs(close_now - open_now), tf_tol * 0.25)

        support_value = entry.get("support_value")
        resistance_value = entry.get("resistance_value")
        support_proximity = _clamp01(_to_float(entry.get("support_proximity"), 0.0))
        resistance_proximity = _clamp01(_to_float(entry.get("resistance_proximity"), 0.0))

        support_touch = support_hold = support_break = 0.0
        resistance_touch = resistance_reject = resistance_break = 0.0

        if support_value is not None:
            support_value = _to_float(support_value)
            touch_proximity = _clamp01(1.0 - max(0.0, low_now - support_value) / max(tf_tol * 2.0, 1e-9))
            wick_reject = lower_wick >= max(body * 0.65, tf_tol * 0.35)
            bull_bias = _clamp01((close_now - open_now) / max(tf_tol * 2.0, 1e-9))
            bear_bias = _clamp01((open_now - close_now) / max(tf_tol * 2.0, 1e-9))
            penetration = _clamp01((support_value - close_now) / max(tf_tol * 1.5, 1e-9))
            proximity_touch_window = low_now <= support_value + (tf_tol * 2.2)
            rebound_probe = (
                close_now >= max(open_now, prev_close - (tf_tol * 0.10))
                and (close_now >= open_now or lower_wick >= max(body * 0.45, tf_tol * 0.25))
            )

            if low_now <= support_value + tf_tol:
                support_touch = max(support_touch, touch_proximity)
            elif support_proximity >= 0.58 and proximity_touch_window:
                support_touch = max(support_touch, _clamp01(support_proximity * 0.82))
            if low_now <= support_value + tf_tol and close_now >= support_value - (tf_tol * 0.15) and (close_now >= open_now or wick_reject):
                support_hold = _clamp01((max(touch_proximity, support_proximity) * 0.58) + (_clamp01(lower_wick / max(tf_tol * 1.5, 1e-9)) * 0.24) + (bull_bias * 0.18))
            elif support_proximity >= 0.62 and proximity_touch_window and rebound_probe and close_now >= support_value - (tf_tol * 0.10):
                support_hold = max(
                    support_hold,
                    _clamp01(
                        (support_proximity * 0.52)
                        + (_clamp01(lower_wick / max(tf_tol * 1.8, 1e-9)) * 0.18)
                        + (bull_bias * 0.16)
                        + (_clamp01((close_now - prev_close) / max(tf_tol * 2.0, 1e-9)) * 0.14)
                    ),
                )
            if close_now < support_value - tf_tol:
                support_break = _clamp01((penetration * 0.72) + (bear_bias * 0.28))

        if resistance_value is not None:
            resistance_value = _to_float(resistance_value)
            touch_proximity = _clamp01(1.0 - max(0.0, resistance_value - high_now) / max(tf_tol * 2.0, 1e-9))
            wick_reject = upper_wick >= max(body * 0.65, tf_tol * 0.35)
            bull_bias = _clamp01((close_now - open_now) / max(tf_tol * 2.0, 1e-9))
            bear_bias = _clamp01((open_now - close_now) / max(tf_tol * 2.0, 1e-9))
            penetration = _clamp01((close_now - resistance_value) / max(tf_tol * 1.5, 1e-9))
            proximity_touch_window = high_now >= resistance_value - (tf_tol * 2.2)
            rejection_probe = (
                close_now <= min(open_now, prev_close + (tf_tol * 0.10))
                and (close_now <= open_now or upper_wick >= max(body * 0.45, tf_tol * 0.25))
            )

            if high_now >= resistance_value - tf_tol:
                resistance_touch = max(resistance_touch, touch_proximity)
            elif resistance_proximity >= 0.58 and proximity_touch_window:
                resistance_touch = max(resistance_touch, _clamp01(resistance_proximity * 0.82))
            if high_now >= resistance_value - tf_tol and close_now <= resistance_value + (tf_tol * 0.15) and (close_now <= open_now or wick_reject):
                resistance_reject = _clamp01((max(touch_proximity, resistance_proximity) * 0.58) + (_clamp01(upper_wick / max(tf_tol * 1.5, 1e-9)) * 0.24) + (bear_bias * 0.18))
            elif resistance_proximity >= 0.62 and proximity_touch_window and rejection_probe and close_now <= resistance_value + (tf_tol * 0.10):
                resistance_reject = max(
                    resistance_reject,
                    _clamp01(
                        (resistance_proximity * 0.52)
                        + (_clamp01(upper_wick / max(tf_tol * 1.8, 1e-9)) * 0.18)
                        + (bear_bias * 0.16)
                        + (_clamp01((prev_close - close_now) / max(tf_tol * 2.0, 1e-9)) * 0.14)
                    ),
                )
            if close_now > resistance_value + tf_tol:
                resistance_break = _clamp01((penetration * 0.72) + (bull_bias * 0.28))

        out[f"r_trend_support_touch_{suffix}"] = support_touch
        out[f"r_trend_support_hold_{suffix}"] = support_hold
        out[f"r_trend_support_break_{suffix}"] = support_break
        out[f"r_trend_resistance_touch_{suffix}"] = resistance_touch
        out[f"r_trend_resistance_reject_{suffix}"] = resistance_reject
        out[f"r_trend_resistance_break_{suffix}"] = resistance_break

        if support_touch > 0.0:
            fired_signals.append(f"r_trend_support_touch_{suffix}")
            support_touch_scores.append(support_touch)
        if support_hold > 0.0:
            fired_signals.append(f"r_trend_support_hold_{suffix}")
            support_hold_scores.append(support_hold)
        if support_break > 0.0:
            fired_signals.append(f"r_trend_support_break_{suffix}")
            support_break_scores.append(support_break)
        if resistance_touch > 0.0:
            fired_signals.append(f"r_trend_resistance_touch_{suffix}")
            resistance_touch_scores.append(resistance_touch)
        if resistance_reject > 0.0:
            fired_signals.append(f"r_trend_resistance_reject_{suffix}")
            resistance_reject_scores.append(resistance_reject)
        if resistance_break > 0.0:
            fired_signals.append(f"r_trend_resistance_break_{suffix}")
            resistance_break_scores.append(resistance_break)

        per_tf_debug[tf] = {
            "support_value": support_value,
            "support_proximity": support_proximity,
            "support_touch": support_touch,
            "support_hold": support_hold,
            "support_break": support_break,
            "resistance_value": resistance_value,
            "resistance_proximity": resistance_proximity,
            "resistance_touch": resistance_touch,
            "resistance_reject": resistance_reject,
            "resistance_break": resistance_break,
            "tolerance": tf_tol,
            "bar": {
                "open": open_now,
                "high": high_now,
                "low": low_now,
                "close": close_now,
                "previous_close": prev_close,
            },
        }

    strengths = {
        "trend_support_hold_strength": _merge_strength(support_hold_scores, support_touch_scores),
        "trend_support_break_strength": _merge_strength(support_break_scores, support_touch_scores),
        "trend_resistance_reject_strength": _merge_strength(resistance_reject_scores, resistance_touch_scores),
        "trend_resistance_break_strength": _merge_strength(resistance_break_scores, resistance_touch_scores),
    }
    fired_strengths = [name for name, value in strengths.items() if float(value) > 0.0]

    out["trendline_subsystem_v1"] = {
        "version": "trendline_subsystem_v1",
        "timeframes_requested": list(_TRENDLINE_TIMEFRAME_SUFFIX.keys()),
        "timeframes_available": [tf for tf in _TRENDLINE_TIMEFRAME_SUFFIX.keys() if tf in entries],
        "per_timeframe": per_tf_debug,
        "fired_signals": fired_signals,
        "fired_strengths": fired_strengths,
        "strengths": strengths,
    }
    return out
