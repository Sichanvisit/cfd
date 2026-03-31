from __future__ import annotations

from backend.trading.engine.core.models import EngineContext
from backend.trading.engine.core.normalizer import normalize_distance


def compute_ma_positions(ctx: EngineContext) -> dict[str, float]:
    scale = ctx.volatility_scale if ctx.volatility_scale is not None else max(abs(ctx.price) * 0.002, 1e-6)
    return {
        "x_ma20": normalize_distance(ctx.price, ctx.ma20, scale),
        "x_ma60": normalize_distance(ctx.price, ctx.ma60, scale),
    }
