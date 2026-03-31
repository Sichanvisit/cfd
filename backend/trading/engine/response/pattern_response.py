from __future__ import annotations

from backend.trading.engine.core.models import EngineContext


def _to_float_list(values) -> list[float]:
    out: list[float] = []
    for value in list(values or []):
        try:
            cast = float(value)
        except Exception:
            continue
        out.append(cast)
    return out


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _local_minima(lows: list[float]) -> list[int]:
    return [idx for idx in range(1, len(lows) - 1) if lows[idx] <= lows[idx - 1] and lows[idx] < lows[idx + 1]]


def _local_maxima(highs: list[float]) -> list[int]:
    return [idx for idx in range(1, len(highs) - 1) if highs[idx] >= highs[idx - 1] and highs[idx] > highs[idx + 1]]


def _avg_range(highs: list[float], lows: list[float], fallback: float) -> float:
    if len(highs) != len(lows) or not highs:
        return max(abs(float(fallback)), 1e-9)
    ranges = [max(float(h) - float(l), 0.0) for h, l in zip(highs, lows)]
    if not ranges:
        return max(abs(float(fallback)), 1e-9)
    return max(sum(ranges) / len(ranges), abs(float(fallback)), 1e-9)


def _double_bottom_strength(highs: list[float], lows: list[float], closes: list[float], avg_range: float) -> float:
    minima = _local_minima(lows)
    if len(minima) < 2:
        return 0.0
    left, right = minima[-2], minima[-1]
    if right - left < 2:
        return 0.0
    left_low = float(lows[left])
    right_low = float(lows[right])
    neckline = max(float(v) for v in highs[left : right + 1])
    tolerance = max(avg_range * 0.60, 1e-9)
    symmetry = _clamp01(1.0 - (abs(left_low - right_low) / tolerance))
    neckline_lift = _clamp01((neckline - max(left_low, right_low)) / max(avg_range * 1.20, 1e-9))
    bounce = _clamp01((float(closes[-1]) - max(left_low, right_low)) / max(neckline - max(left_low, right_low), avg_range))
    return _clamp01((symmetry * 0.40) + (neckline_lift * 0.25) + (bounce * 0.35))


def _double_top_strength(highs: list[float], lows: list[float], closes: list[float], avg_range: float) -> float:
    maxima = _local_maxima(highs)
    if len(maxima) < 2:
        return 0.0
    left, right = maxima[-2], maxima[-1]
    if right - left < 2:
        return 0.0
    left_high = float(highs[left])
    right_high = float(highs[right])
    floor = min(float(v) for v in lows[left : right + 1])
    tolerance = max(avg_range * 0.60, 1e-9)
    symmetry = _clamp01(1.0 - (abs(left_high - right_high) / tolerance))
    floor_drop = _clamp01((min(left_high, right_high) - floor) / max(avg_range * 1.20, 1e-9))
    rejection = _clamp01((min(left_high, right_high) - float(closes[-1])) / max(min(left_high, right_high) - floor, avg_range))
    return _clamp01((symmetry * 0.40) + (floor_drop * 0.25) + (rejection * 0.35))


def _inverse_head_shoulders_strength(highs: list[float], lows: list[float], closes: list[float], avg_range: float) -> float:
    minima = _local_minima(lows)
    if len(minima) < 3:
        return 0.0
    left, head, right = minima[-3], minima[-2], minima[-1]
    if not (left < head < right):
        return 0.0
    left_low = float(lows[left])
    head_low = float(lows[head])
    right_low = float(lows[right])
    shoulder_tolerance = max(avg_range * 0.70, 1e-9)
    shoulder_symmetry = _clamp01(1.0 - (abs(left_low - right_low) / shoulder_tolerance))
    head_depth = _clamp01((min(left_low, right_low) - head_low) / max(avg_range * 0.80, 1e-9))
    if head_depth <= 0.0:
        return 0.0
    left_neck = max(float(v) for v in highs[left : head + 1])
    right_neck = max(float(v) for v in highs[head : right + 1])
    neckline = (left_neck + right_neck) / 2.0
    neckline_reclaim = _clamp01((float(closes[-1]) - neckline) / max(avg_range * 0.80, 1e-9) + 0.5)
    return _clamp01((shoulder_symmetry * 0.30) + (head_depth * 0.35) + (neckline_reclaim * 0.35))


def _head_shoulders_strength(highs: list[float], lows: list[float], closes: list[float], avg_range: float) -> float:
    maxima = _local_maxima(highs)
    if len(maxima) < 3:
        return 0.0
    left, head, right = maxima[-3], maxima[-2], maxima[-1]
    if not (left < head < right):
        return 0.0
    left_high = float(highs[left])
    head_high = float(highs[head])
    right_high = float(highs[right])
    shoulder_tolerance = max(avg_range * 0.70, 1e-9)
    shoulder_symmetry = _clamp01(1.0 - (abs(left_high - right_high) / shoulder_tolerance))
    head_height = _clamp01((head_high - max(left_high, right_high)) / max(avg_range * 0.80, 1e-9))
    if head_height <= 0.0:
        return 0.0
    left_neck = min(float(v) for v in lows[left : head + 1])
    right_neck = min(float(v) for v in lows[head : right + 1])
    neckline = (left_neck + right_neck) / 2.0
    neckline_loss = _clamp01((neckline - float(closes[-1])) / max(avg_range * 0.80, 1e-9) + 0.5)
    return _clamp01((shoulder_symmetry * 0.30) + (head_height * 0.35) + (neckline_loss * 0.35))


def compute_pattern_responses(ctx: EngineContext) -> dict[str, float]:
    md = dict(ctx.metadata or {})
    highs = _to_float_list(md.get("pattern_recent_highs"))
    lows = _to_float_list(md.get("pattern_recent_lows"))
    closes = _to_float_list(md.get("pattern_recent_closes"))
    fallback_scale = float(ctx.volatility_scale or 0.0) * 0.25
    avg_range = _avg_range(highs, lows, fallback_scale if fallback_scale > 0.0 else max(abs(ctx.price) * 0.0006, 1e-9))

    out = {
        "pattern_double_bottom": 0.0,
        "pattern_inverse_head_shoulders": 0.0,
        "pattern_double_top": 0.0,
        "pattern_head_shoulders": 0.0,
    }
    if len(highs) < 5 or len(lows) < 5 or len(closes) < 5:
        return out

    out["pattern_double_bottom"] = _double_bottom_strength(highs, lows, closes, avg_range)
    out["pattern_inverse_head_shoulders"] = _inverse_head_shoulders_strength(highs, lows, closes, avg_range)
    out["pattern_double_top"] = _double_top_strength(highs, lows, closes, avg_range)
    out["pattern_head_shoulders"] = _head_shoulders_strength(highs, lows, closes, avg_range)
    return out
