from __future__ import annotations

from backend.trading.engine.core.models import EngineContext
from backend.trading.engine.core.normalizer import normalize_band_position


def compute_bb20_position(ctx: EngineContext) -> float:
    return normalize_band_position(ctx.price, ctx.bb20_up, ctx.bb20_mid, ctx.bb20_dn)


def compute_bb44_position(ctx: EngineContext) -> float:
    return normalize_band_position(ctx.price, ctx.bb44_up, ctx.bb44_mid, ctx.bb44_dn)
