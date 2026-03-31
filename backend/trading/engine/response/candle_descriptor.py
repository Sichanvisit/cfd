from __future__ import annotations

from typing import Any

from backend.trading.engine.core.models import EngineContext

_DESCRIPTOR_VERSION = "candle_descriptor_v1"
_MAX_SIZE_ENERGY = 5.0


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _safe_div(numerator: float, denominator: float, *, default: float = 0.0) -> float:
    denom = abs(float(denominator))
    if denom <= 1e-9:
        return float(default)
    return float(numerator) / denom


def _resolve_baseline(md: dict[str, Any], *, key: str, fallback: float) -> float:
    value = _to_float(md.get(key), 0.0)
    if value > 0.0:
        return float(value)
    return max(float(fallback), 1e-9)


def compute_candle_descriptor_from_ohlc(
    open_now: float,
    high_now: float,
    low_now: float,
    close_now: float,
    *,
    range_baseline: float,
    body_baseline: float,
) -> dict[str, float | str]:
    body = abs(close_now - open_now)
    upper_wick = max(0.0, high_now - max(open_now, close_now))
    lower_wick = max(0.0, min(open_now, close_now) - low_now)
    total_range = max(high_now - low_now, 1e-9)

    upper_wick_energy = _clamp(_safe_div(upper_wick, total_range), 0.0, 1.0)
    lower_wick_energy = _clamp(_safe_div(lower_wick, total_range), 0.0, 1.0)
    return {
        "version": _DESCRIPTOR_VERSION,
        "open": float(open_now),
        "high": float(high_now),
        "low": float(low_now),
        "close": float(close_now),
        "range_points": float(total_range),
        "body_points": float(body),
        "upper_wick_points": float(upper_wick),
        "lower_wick_points": float(lower_wick),
        "range_baseline": float(range_baseline),
        "body_baseline": float(body_baseline),
        "body_signed_energy": _clamp(_safe_div(close_now - open_now, total_range), -1.0, 1.0),
        "body_shape_energy": _clamp(_safe_div(body, total_range), 0.0, 1.0),
        "upper_wick_energy": upper_wick_energy,
        "lower_wick_energy": lower_wick_energy,
        "close_location_energy": _clamp(2.0 * _safe_div(close_now - low_now, total_range) - 1.0, -1.0, 1.0),
        "wick_balance_energy": _clamp(lower_wick_energy - upper_wick_energy, -1.0, 1.0),
        "range_size_energy": _clamp(_safe_div(total_range, range_baseline), 0.0, _MAX_SIZE_ENERGY),
        "body_size_energy": _clamp(_safe_div(body, body_baseline), 0.0, _MAX_SIZE_ENERGY),
    }


def compute_candle_descriptor(ctx: EngineContext) -> dict[str, float | str]:
    md = dict(ctx.metadata or {})
    open_now = _to_float(md.get("current_open"), ctx.price)
    high_now = _to_float(md.get("current_high"), ctx.price)
    low_now = _to_float(md.get("current_low"), ctx.price)
    close_now = _to_float(md.get("current_close"), ctx.price)

    prev_open_raw = md.get("previous_open")
    prev_close_raw = md.get("previous_close")
    prev_open = _to_float(prev_open_raw, 0.0)
    prev_close = _to_float(prev_close_raw, 0.0)
    prev_body = abs(prev_close - prev_open) if prev_open_raw is not None and prev_close_raw is not None else 0.0

    range_baseline = _resolve_baseline(
        md,
        key="recent_range_mean",
        fallback=_to_float(ctx.volatility_scale, high_now - low_now) or max(high_now - low_now, 1e-9),
    )
    body_baseline = _resolve_baseline(
        md,
        key="recent_body_mean",
        fallback=prev_body if prev_body > 0.0 else max((high_now - low_now) * 0.35, 1e-9),
    )
    return compute_candle_descriptor_from_ohlc(
        open_now,
        high_now,
        low_now,
        close_now,
        range_baseline=range_baseline,
        body_baseline=body_baseline,
    )
