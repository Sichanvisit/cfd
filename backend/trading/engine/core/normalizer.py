from __future__ import annotations


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return float(max(low, min(high, value)))


def normalize_centered(price: float, lower: float, upper: float, *, clip: bool = False) -> float:
    width = float(upper) - float(lower)
    if width <= 0.0:
        return 0.0
    mid = (float(upper) + float(lower)) / 2.0
    half = width / 2.0
    value = (float(price) - mid) / max(1e-9, half)
    return clamp(value) if clip else float(value)


def normalize_band_position(
    price: float,
    upper: float | None,
    middle: float | None,
    lower: float | None,
    *,
    clip: bool = False,
) -> float:
    if upper is None or middle is None or lower is None:
        return 0.0
    width = float(upper) - float(lower)
    if width <= 0.0:
        return 0.0
    half = width / 2.0
    value = (float(price) - float(middle)) / max(1e-9, half)
    return clamp(value) if clip else float(value)


def normalize_distance(price: float, anchor: float | None, scale: float | None, *, clip: bool = False) -> float:
    if anchor is None or scale is None:
        return 0.0
    scale_v = abs(float(scale))
    if scale_v <= 0.0:
        return 0.0
    value = (float(price) - float(anchor)) / max(1e-9, scale_v)
    return clamp(value) if clip else float(value)
