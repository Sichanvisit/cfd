from __future__ import annotations

from backend.trading.engine.core.models import EngineContext


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_quality_state(ctx: EngineContext) -> dict[str, float]:
    md = dict(ctx.metadata or {})
    raw_scores = dict(md.get("raw_scores", {}) or {})
    wait_noise = _to_float(raw_scores.get("wait_noise"), 0.0)
    wait_conflict = _to_float(raw_scores.get("wait_conflict"), 0.0)
    disparity = _to_float(md.get("current_disparity"), 100.0)
    vol_ratio = _to_float(md.get("current_volatility_ratio"), 1.0)
    ma_alignment = str(md.get("ma_alignment", "MIXED") or "MIXED").upper()

    return {
        "s_noise": _clamp01(wait_noise / 25.0),
        "s_conflict": _clamp01(wait_conflict / 25.0),
        "s_alignment": 1.0 if ma_alignment in {"BULL", "BEAR"} else 0.0,
        "s_disparity": _clamp01(abs(disparity - 100.0) / 3.0),
        "s_volatility": _clamp01(abs(vol_ratio - 1.0) / 0.75),
    }
