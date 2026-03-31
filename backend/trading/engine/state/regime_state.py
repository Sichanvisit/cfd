from __future__ import annotations

from backend.trading.engine.core.models import EngineContext


def compute_regime_state(ctx: EngineContext) -> dict[str, str]:
    return {
        "market_mode": str(ctx.market_mode or "UNKNOWN").upper(),
        "direction_policy": str(ctx.direction_policy or "UNKNOWN").upper(),
    }
