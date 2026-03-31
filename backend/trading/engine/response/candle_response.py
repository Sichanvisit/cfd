from __future__ import annotations

from backend.trading.engine.core.models import EngineContext
from backend.trading.engine.response.candle_descriptor import compute_candle_descriptor
from backend.trading.engine.response.candle_motif import compute_candle_motifs
from backend.trading.engine.response.candle_pattern import compute_candle_patterns


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def compute_candle_responses(ctx: EngineContext) -> dict[str, float]:
    descriptor = compute_candle_descriptor(ctx)
    pattern = compute_candle_patterns(ctx, descriptor)
    motif = compute_candle_motifs(descriptor, pattern)
    open_now = _to_float(descriptor.get("open"), ctx.price)
    close_now = _to_float(descriptor.get("close"), ctx.price)
    body_shape_energy = _to_float(descriptor.get("body_shape_energy"), 0.0)
    upper_wick_energy = _to_float(descriptor.get("upper_wick_energy"), 0.0)
    lower_wick_energy = _to_float(descriptor.get("lower_wick_energy"), 0.0)

    out = {
        "r_candle_lower_reject": 0.0,
        "r_candle_upper_reject": 0.0,
        "candle_descriptor_v1": descriptor,
        "candle_pattern_v1": pattern,
        "candle_motif_v1": motif,
    }

    # Long lower wick with bullish close implies support response.
    if close_now >= open_now and lower_wick_energy >= max(body_shape_energy * 1.2, 0.25):
        out["r_candle_lower_reject"] = min(1.0, lower_wick_energy)

    # Long upper wick with bearish close implies resistance response.
    if close_now <= open_now and upper_wick_energy >= max(body_shape_energy * 1.2, 0.25):
        out["r_candle_upper_reject"] = min(1.0, upper_wick_energy)

    return out
