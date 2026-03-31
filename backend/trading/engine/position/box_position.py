from __future__ import annotations

from backend.trading.engine.core.models import EngineContext
from backend.trading.engine.core.normalizer import normalize_centered


def compute_box_position(ctx: EngineContext) -> float:
    if ctx.box_low is None or ctx.box_high is None:
        return 0.0
    return normalize_centered(ctx.price, ctx.box_low, ctx.box_high)
