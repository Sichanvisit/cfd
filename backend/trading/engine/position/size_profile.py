from __future__ import annotations

from typing import Any

from backend.trading.engine.core.models import EngineContext

_POSITION_SCALE_VERSION = "v1_position_scale"
_COMPRESSED_RATIO = 0.75
_EXPANDED_RATIO = 1.35


def _safe_span(upper: float | None, lower: float | None) -> float:
    if upper is None or lower is None:
        return 0.0
    try:
        return max(0.0, float(upper) - float(lower))
    except (TypeError, ValueError):
        return 0.0


def _safe_ratio(value: float, scale: float | None) -> float:
    try:
        scale_value = float(scale or 0.0)
    except (TypeError, ValueError):
        scale_value = 0.0
    if value <= 0.0 or scale_value <= 0.0:
        return 0.0
    return float(value) / scale_value


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _compression_score(ratio: float) -> float:
    if ratio <= 0.0:
        return 0.0
    return _bounded(1.0 - min(float(ratio), 1.0))


def _expansion_score(ratio: float) -> float:
    if ratio <= 0.0:
        return 0.0
    if ratio <= 1.0:
        return 0.0
    return _bounded(1.0 - (1.0 / float(ratio)))


def _classify_ratio(ratio: float, *, lower_label: str, upper_label: str) -> str:
    if ratio <= 0.0:
        return "UNKNOWN"
    if ratio < _COMPRESSED_RATIO:
        return lower_label
    if ratio > _EXPANDED_RATIO:
        return upper_label
    return "NORMAL"


def _mean(values: list[float]) -> float:
    valid = [float(value) for value in values if float(value) > 0.0]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


def compute_position_scale_metadata(ctx: EngineContext) -> dict[str, Any]:
    box_height = _safe_span(ctx.box_high, ctx.box_low)
    bb20_width = _safe_span(ctx.bb20_up, ctx.bb20_dn)
    bb44_width = _safe_span(ctx.bb44_up, ctx.bb44_dn)

    box_height_ratio = _safe_ratio(box_height, ctx.volatility_scale)
    bb20_width_ratio = _safe_ratio(bb20_width, ctx.volatility_scale)
    bb44_width_ratio = _safe_ratio(bb44_width, ctx.volatility_scale)
    inner_outer_band_ratio = 0.0
    if bb44_width > 0.0:
        inner_outer_band_ratio = bb20_width / bb44_width

    compression_score = _mean(
        [
            _compression_score(box_height_ratio),
            _compression_score(bb20_width_ratio),
            _compression_score(bb44_width_ratio),
        ]
    )
    expansion_score = _mean(
        [
            _expansion_score(box_height_ratio),
            _expansion_score(bb20_width_ratio),
            _expansion_score(bb44_width_ratio),
        ]
    )
    map_ratio = _mean([box_height_ratio, bb20_width_ratio, bb44_width_ratio])

    return {
        "version": _POSITION_SCALE_VERSION,
        "volatility_scale": float(ctx.volatility_scale or 0.0),
        "box_height": box_height,
        "bb20_width": bb20_width,
        "bb44_width": bb44_width,
        "box_height_ratio": box_height_ratio,
        "bb20_width_ratio": bb20_width_ratio,
        "bb44_width_ratio": bb44_width_ratio,
        "inner_outer_band_ratio": inner_outer_band_ratio,
        "box_size_state": _classify_ratio(box_height_ratio, lower_label="SMALL", upper_label="WIDE"),
        "bb20_width_state": _classify_ratio(bb20_width_ratio, lower_label="COMPRESSED", upper_label="EXPANDED"),
        "bb44_width_state": _classify_ratio(bb44_width_ratio, lower_label="COMPRESSED", upper_label="EXPANDED"),
        "map_size_state": _classify_ratio(map_ratio, lower_label="COMPRESSED", upper_label="EXPANDED"),
        "compression_score": compression_score,
        "expansion_score": expansion_score,
    }
