from __future__ import annotations

from backend.trading.engine.core.models import EngineContext
from backend.trading.engine.core.normalizer import normalize_centered


def compute_sr_position(ctx: EngineContext) -> float:
    if ctx.support is None or ctx.resistance is None:
        return 0.0
    return normalize_centered(ctx.price, ctx.support, ctx.resistance)
