from __future__ import annotations

from backend.trading.engine.core.models import EngineContext
from backend.trading.engine.core.normalizer import normalize_distance


def compute_trendline_position(ctx: EngineContext) -> float:
    scale = ctx.volatility_scale if ctx.volatility_scale is not None else max(abs(ctx.price) * 0.002, 1e-6)
    return normalize_distance(ctx.price, ctx.trendline_value, scale)
