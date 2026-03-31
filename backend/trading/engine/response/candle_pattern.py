from __future__ import annotations

import math
from typing import Any

from backend.trading.engine.core.models import EngineContext
from backend.trading.engine.response.candle_descriptor import compute_candle_descriptor_from_ohlc

_PATTERN_VERSION = "candle_pattern_v1"
_EPS = 1e-9


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _positive(value: float) -> float:
    return max(0.0, float(value))


def _negative(value: float) -> float:
    return max(0.0, -float(value))


def _soft_clip01(value: float, *, scale: float = 1.0) -> float:
    if value <= 0.0:
        return 0.0
    return _clamp01(1.0 - math.exp(-float(value) / max(float(scale), _EPS)))


def _descriptor(md: dict[str, Any], prefix: str, *, range_baseline: float, body_baseline: float) -> dict[str, float | str]:
    return compute_candle_descriptor_from_ohlc(
        _to_float(md.get(f"{prefix}_open")),
        _to_float(md.get(f"{prefix}_high")),
        _to_float(md.get(f"{prefix}_low")),
        _to_float(md.get(f"{prefix}_close")),
        range_baseline=range_baseline,
        body_baseline=body_baseline,
    )


def _size_weight(size_energy: float) -> float:
    return 0.75 + (0.25 * _soft_clip01(max(float(size_energy) - 0.60, 0.0), scale=0.90))


def _current_body_strength(descriptor: dict[str, float | str]) -> float:
    return _clamp01((0.55 * _positive(_to_float(descriptor.get("body_signed_energy")))) + (0.45 * _clamp01(_to_float(descriptor.get("body_shape_energy")))))


def _current_bear_strength(descriptor: dict[str, float | str]) -> float:
    return _clamp01((0.55 * _negative(_to_float(descriptor.get("body_signed_energy")))) + (0.45 * _clamp01(_to_float(descriptor.get("body_shape_energy")))))


def _doji_like(descriptor: dict[str, float | str]) -> float:
    body_shape = _clamp01(_to_float(descriptor.get("body_shape_energy")))
    upper = _clamp01(_to_float(descriptor.get("upper_wick_energy")))
    lower = _clamp01(_to_float(descriptor.get("lower_wick_energy")))
    centered = 1.0 - abs(_to_float(descriptor.get("close_location_energy")))
    return _clamp01((0.45 * (1.0 - body_shape)) + (0.30 * min(upper + lower, 1.0)) + (0.25 * centered))


def _spinning_top_like(descriptor: dict[str, float | str]) -> float:
    body_shape = _clamp01(_to_float(descriptor.get("body_shape_energy")))
    upper = _clamp01(_to_float(descriptor.get("upper_wick_energy")))
    lower = _clamp01(_to_float(descriptor.get("lower_wick_energy")))
    symmetry = 1.0 - min(abs(upper - lower), 1.0)
    return _clamp01((0.45 * (1.0 - body_shape)) + (0.35 * min(upper + lower, 1.0)) + (0.20 * symmetry))


def _marubozu_like(descriptor: dict[str, float | str], *, bullish: bool) -> float:
    body_shape = _clamp01(_to_float(descriptor.get("body_shape_energy")))
    upper = _clamp01(_to_float(descriptor.get("upper_wick_energy")))
    lower = _clamp01(_to_float(descriptor.get("lower_wick_energy")))
    close_loc = _to_float(descriptor.get("close_location_energy"))
    direction = _positive(_to_float(descriptor.get("body_signed_energy"))) if bullish else _negative(_to_float(descriptor.get("body_signed_energy")))
    close_score = _positive(close_loc) if bullish else _negative(close_loc)
    base = (
        (0.35 * body_shape)
        + (0.25 * direction)
        + (0.20 * close_score)
        + (0.10 * (1.0 - upper))
        + (0.10 * (1.0 - lower))
    )
    return _clamp01(base * _size_weight(_to_float(descriptor.get("body_size_energy"))))


def _hammer_family(descriptor: dict[str, float | str], *, inverted: bool, bearish_close: bool) -> float:
    upper = _clamp01(_to_float(descriptor.get("upper_wick_energy")))
    lower = _clamp01(_to_float(descriptor.get("lower_wick_energy")))
    body = _clamp01(_to_float(descriptor.get("body_shape_energy")))
    body_signed = _to_float(descriptor.get("body_signed_energy"))
    close_loc = _to_float(descriptor.get("close_location_energy"))
    primary_wick = upper if inverted else lower
    opposite_wick = lower if inverted else upper
    close_score = _negative(close_loc) if bearish_close else _positive(close_loc)
    direction_score = _negative(body_signed) if bearish_close else _positive(body_signed)
    base = (
        (0.38 * primary_wick)
        + (0.18 * (1.0 - opposite_wick))
        + (0.18 * (1.0 - body))
        + (0.16 * close_score)
        + (0.10 * direction_score)
    )
    return _clamp01(base * _size_weight(_to_float(descriptor.get("range_size_energy"))))


def _engulf_score(cur_md: dict[str, Any], prev_md: dict[str, Any], *, bullish: bool, body_baseline: float, range_baseline: float) -> float:
    cur_open = _to_float(cur_md.get("current_open"))
    cur_close = _to_float(cur_md.get("current_close"))
    prev_open = _to_float(prev_md.get("previous_open"))
    prev_close = _to_float(prev_md.get("previous_close"))
    cur_desc = compute_candle_descriptor_from_ohlc(
        _to_float(cur_md.get("current_open")),
        _to_float(cur_md.get("current_high")),
        _to_float(cur_md.get("current_low")),
        _to_float(cur_md.get("current_close")),
        range_baseline=range_baseline,
        body_baseline=body_baseline,
    )
    prev_desc = compute_candle_descriptor_from_ohlc(
        _to_float(prev_md.get("previous_open")),
        _to_float(prev_md.get("previous_high")),
        _to_float(prev_md.get("previous_low")),
        _to_float(prev_md.get("previous_close")),
        range_baseline=range_baseline,
        body_baseline=body_baseline,
    )
    prev_body = max(abs(prev_close - prev_open), body_baseline, _EPS)
    cur_body = max(abs(cur_close - cur_open), _EPS)
    cur_low = min(cur_open, cur_close)
    cur_high = max(cur_open, cur_close)
    prev_low = min(prev_open, prev_close)
    prev_high = max(prev_open, prev_close)

    if bullish:
        direction = math.sqrt(max(_current_bear_strength(prev_desc) * _current_body_strength(cur_desc), 0.0))
        upper_cover = _clamp01((cur_high - prev_high) / prev_body)
        lower_cover = _clamp01((prev_low - cur_low) / prev_body)
    else:
        direction = math.sqrt(max(_current_body_strength(prev_desc) * _current_bear_strength(cur_desc), 0.0))
        upper_cover = _clamp01((prev_high - cur_high) / prev_body)
        lower_cover = _clamp01((cur_low - prev_low) / prev_body)

    engulf_cover = 0.5 * upper_cover + 0.5 * lower_cover
    size_ratio = _clamp01(cur_body / prev_body)
    confirmation = 0.55 + (0.30 * engulf_cover) + (0.15 * size_ratio)
    return _clamp01(direction * confirmation)


def _harami_score(cur_desc: dict[str, float | str], prev_desc: dict[str, float | str], cur_md: dict[str, Any], prev_md: dict[str, Any], *, cross: bool) -> float:
    cur_open = _to_float(cur_md.get("current_open"))
    cur_close = _to_float(cur_md.get("current_close"))
    prev_open = _to_float(prev_md.get("previous_open"))
    prev_close = _to_float(prev_md.get("previous_close"))
    cur_low = min(cur_open, cur_close)
    cur_high = max(cur_open, cur_close)
    prev_low = min(prev_open, prev_close)
    prev_high = max(prev_open, prev_close)
    prev_body = max(abs(prev_close - prev_open), _EPS)
    contain_low = _clamp01((cur_low - prev_low) / prev_body)
    contain_high = _clamp01((prev_high - cur_high) / prev_body)
    containment = 0.5 * contain_low + 0.5 * contain_high
    size_small = _clamp01(1.0 - _to_float(cur_desc.get("body_shape_energy")))
    doji_bonus = _doji_like(cur_desc) if cross else 0.0
    return _clamp01((0.45 * containment) + (0.35 * size_small) + (0.20 * doji_bonus))


def _tweezer_score(cur_desc: dict[str, float | str], prev_desc: dict[str, float | str], cur_md: dict[str, Any], prev_md: dict[str, Any], *, top: bool, range_baseline: float) -> float:
    cur_extreme = _to_float(cur_md.get("current_high")) if top else _to_float(cur_md.get("current_low"))
    prev_extreme = _to_float(prev_md.get("previous_high")) if top else _to_float(prev_md.get("previous_low"))
    similarity = _clamp01(1.0 - (abs(cur_extreme - prev_extreme) / max(range_baseline * 0.60, _EPS)))
    rejection = _hammer_family(cur_desc, inverted=top, bearish_close=top) if top else _hammer_family(cur_desc, inverted=False, bearish_close=False)
    prior_probe = _hammer_family(prev_desc, inverted=top, bearish_close=top) if top else _hammer_family(prev_desc, inverted=False, bearish_close=False)
    return _clamp01((0.45 * similarity) + (0.35 * rejection) + (0.20 * prior_probe))


def _reclaim_into_body(cur_close: float, anchor_open: float, anchor_close: float, body_baseline: float, *, bullish: bool) -> float:
    body_high = max(anchor_open, anchor_close)
    body_low = min(anchor_open, anchor_close)
    if bullish:
        midpoint = (body_high + body_low) / 2.0
        return _clamp01((cur_close - midpoint) / max(body_high - midpoint, body_baseline, _EPS))
    midpoint = (body_high + body_low) / 2.0
    return _clamp01((midpoint - cur_close) / max(midpoint - body_low, body_baseline, _EPS))


def _three_bar_star_score(cur_desc: dict[str, float | str], prev_desc: dict[str, float | str], prev2_desc: dict[str, float | str], md: dict[str, Any], *, bullish: bool, body_baseline: float) -> float:
    first_strength = _current_bear_strength(prev2_desc) if bullish else _current_body_strength(prev2_desc)
    pause = _clamp01((0.60 * _doji_like(prev_desc)) + (0.40 * (1.0 - _to_float(prev_desc.get("body_shape_energy")))))
    third_strength = _current_body_strength(cur_desc) if bullish else _current_bear_strength(cur_desc)
    reclaim = _reclaim_into_body(
        _to_float(md.get("current_close")),
        _to_float(md.get("pre_previous_open")),
        _to_float(md.get("pre_previous_close")),
        body_baseline,
        bullish=bullish,
    )
    return _clamp01((0.25 * first_strength) + (0.20 * pause) + (0.35 * third_strength) + (0.20 * reclaim))


def _three_soldiers_score(cur_desc: dict[str, float | str], prev_desc: dict[str, float | str], prev2_desc: dict[str, float | str], md: dict[str, Any], *, bullish: bool) -> float:
    descriptors = [prev2_desc, prev_desc, cur_desc]
    if bullish:
        direction = sum(_current_body_strength(d) for d in descriptors) / 3.0
        closes = [
            _to_float(md.get("pre_previous_close")),
            _to_float(md.get("previous_close")),
            _to_float(md.get("current_close")),
        ]
        stair = _clamp01(0.5 * _clamp01(closes[1] - closes[0]) + 0.5 * _clamp01(closes[2] - closes[1]))
        close_bias = sum(_positive(_to_float(d.get("close_location_energy"))) for d in descriptors) / 3.0
    else:
        direction = sum(_current_bear_strength(d) for d in descriptors) / 3.0
        closes = [
            _to_float(md.get("pre_previous_close")),
            _to_float(md.get("previous_close")),
            _to_float(md.get("current_close")),
        ]
        stair = _clamp01(0.5 * _clamp01(closes[0] - closes[1]) + 0.5 * _clamp01(closes[1] - closes[2]))
        close_bias = sum(_negative(_to_float(d.get("close_location_energy"))) for d in descriptors) / 3.0
    body_weight = sum(_size_weight(_to_float(d.get("body_size_energy"))) for d in descriptors) / 3.0
    return _clamp01(((0.45 * direction) + (0.25 * stair) + (0.30 * close_bias)) * body_weight)


def compute_candle_patterns(ctx: EngineContext, descriptor: dict[str, float | str] | None = None) -> dict[str, Any]:
    md = dict(ctx.metadata or {})
    descriptor = dict(descriptor or {})
    range_baseline = max(_to_float(descriptor.get("range_baseline"), md.get("recent_range_mean") or ctx.volatility_scale or 1.0), _EPS)
    body_baseline = max(_to_float(descriptor.get("body_baseline"), md.get("recent_body_mean") or (range_baseline * 0.35)), _EPS)
    current = descriptor or _descriptor(md, "current", range_baseline=range_baseline, body_baseline=body_baseline)
    previous = _descriptor(md, "previous", range_baseline=range_baseline, body_baseline=body_baseline)
    pre_previous = _descriptor(md, "pre_previous", range_baseline=range_baseline, body_baseline=body_baseline)

    hammer_like = _hammer_family(current, inverted=False, bearish_close=False)
    inverted_hammer_like = _hammer_family(current, inverted=True, bearish_close=False)
    hanging_man_like = _hammer_family(current, inverted=False, bearish_close=True)
    shooting_star_like = _hammer_family(current, inverted=True, bearish_close=True)
    doji_like = _doji_like(current)
    long_legged_doji_like = _clamp01(doji_like * (0.55 + (0.45 * min(_to_float(current.get("upper_wick_energy")) + _to_float(current.get("lower_wick_energy")), 1.0))) * _size_weight(_to_float(current.get("range_size_energy"))))
    dragonfly_doji_like = _clamp01((0.55 * doji_like) + (0.30 * _clamp01(_to_float(current.get("lower_wick_energy")))) + (0.15 * _positive(_to_float(current.get("close_location_energy")))))
    gravestone_doji_like = _clamp01((0.55 * doji_like) + (0.30 * _clamp01(_to_float(current.get("upper_wick_energy")))) + (0.15 * _negative(_to_float(current.get("close_location_energy")))))
    bullish_marubozu_like = _marubozu_like(current, bullish=True)
    bearish_marubozu_like = _marubozu_like(current, bullish=False)
    spinning_top_like = _spinning_top_like(current)

    bullish_engulfing_like = _engulf_score(md, md, bullish=True, body_baseline=body_baseline, range_baseline=range_baseline)
    bearish_engulfing_like = _engulf_score(md, md, bullish=False, body_baseline=body_baseline, range_baseline=range_baseline)
    harami_like = _harami_score(current, previous, md, md, cross=False)
    harami_cross_like = _harami_score(current, previous, md, md, cross=True)
    tweezer_top_like = _tweezer_score(current, previous, md, md, top=True, range_baseline=range_baseline)
    tweezer_bottom_like = _tweezer_score(current, previous, md, md, top=False, range_baseline=range_baseline)

    morning_star_like = _three_bar_star_score(current, previous, pre_previous, md, bullish=True, body_baseline=body_baseline)
    evening_star_like = _three_bar_star_score(current, previous, pre_previous, md, bullish=False, body_baseline=body_baseline)
    three_white_soldiers_like = _three_soldiers_score(current, previous, pre_previous, md, bullish=True)
    three_black_crows_like = _three_soldiers_score(current, previous, pre_previous, md, bullish=False)

    single = {
        "hammer_like": hammer_like,
        "inverted_hammer_like": inverted_hammer_like,
        "hanging_man_like": hanging_man_like,
        "shooting_star_like": shooting_star_like,
        "doji_like": doji_like,
        "long_legged_doji_like": long_legged_doji_like,
        "dragonfly_doji_like": dragonfly_doji_like,
        "gravestone_doji_like": gravestone_doji_like,
        "bullish_marubozu_like": bullish_marubozu_like,
        "bearish_marubozu_like": bearish_marubozu_like,
        "spinning_top_like": spinning_top_like,
    }
    two_bar = {
        "bullish_engulfing_like": bullish_engulfing_like,
        "bearish_engulfing_like": bearish_engulfing_like,
        "harami_like": harami_like,
        "harami_cross_like": harami_cross_like,
        "tweezer_top_like": tweezer_top_like,
        "tweezer_bottom_like": tweezer_bottom_like,
    }
    three_bar = {
        "morning_star_like": morning_star_like,
        "evening_star_like": evening_star_like,
        "three_white_soldiers_like": three_white_soldiers_like,
        "three_black_crows_like": three_black_crows_like,
    }
    fired = [
        name
        for group in (single, two_bar, three_bar)
        for name, value in group.items()
        if _to_float(value) >= 0.55
    ]
    return {
        "version": _PATTERN_VERSION,
        "single_candle_patterns_v1": single,
        "two_bar_patterns_v1": two_bar,
        "three_bar_patterns_v1": three_bar,
        "fired_patterns": fired,
    }
