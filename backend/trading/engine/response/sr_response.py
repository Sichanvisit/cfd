from __future__ import annotations

from typing import Any

from backend.trading.engine.core.models import EngineContext
from backend.trading.engine.core.normalizer import normalize_distance


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _soft_hold_strength(*, proximity: float, wick_bias: float, body_bias: float) -> float:
    return _clamp01((proximity * 0.58) + (wick_bias * 0.24) + (body_bias * 0.18))


def _soft_break_strength(*, penetration: float, body_bias: float) -> float:
    return _clamp01((penetration * 0.72) + (body_bias * 0.28))


def _build_strengths(raw: dict[str, float]) -> dict[str, float]:
    support_hold_strength = _clamp01(
        max(raw["r_sr_support_hold"], raw["r_sr_support_reclaim"] * 0.88)
        + min(raw["r_sr_support_touch"] * 0.18, 0.12)
    )
    support_break_strength = _clamp01(
        raw["r_sr_support_break"] + min(raw["r_sr_support_touch"] * 0.10, 0.08)
    )
    resistance_reject_strength = _clamp01(
        max(raw["r_sr_resistance_reject"], raw["r_sr_resistance_touch"] * 0.22)
    )
    resistance_break_strength = _clamp01(
        max(raw["r_sr_resistance_break"], raw["r_sr_resistance_reclaim"] * 0.88)
        + min(raw["r_sr_resistance_touch"] * 0.10, 0.08)
    )
    return {
        "support_hold_strength": support_hold_strength,
        "support_break_strength": support_break_strength,
        "resistance_reject_strength": resistance_reject_strength,
        "resistance_break_strength": resistance_break_strength,
    }


def compute_sr_responses(ctx: EngineContext) -> dict[str, Any]:
    md = dict(ctx.metadata or {})
    price_now = _to_float(ctx.price, 0.0)
    open_now = _to_float(md.get("current_open"), price_now)
    high_now = _to_float(md.get("current_high"), price_now)
    low_now = _to_float(md.get("current_low"), price_now)
    close_now = _to_float(md.get("current_close"), price_now)
    prev_close = _to_float(md.get("previous_close"), close_now)
    support = _to_float(ctx.support, 0.0) if ctx.support is not None else None
    resistance = _to_float(ctx.resistance, 0.0) if ctx.resistance is not None else None
    scale = max(
        abs(_to_float(ctx.volatility_scale, 0.0)),
        abs(price_now) * 0.00025,
        1e-9,
    )
    sr_tol = max(
        abs(_to_float(md.get("sr_touch_tolerance"), 0.0)),
        abs(_to_float(md.get("box_touch_tolerance"), 0.0)) * 2.0,
        abs(_to_float(md.get("band_touch_tolerance"), 0.0)) * 2.0,
        scale * 0.18,
        1e-9,
    )

    lower_wick = max(0.0, min(open_now, close_now) - low_now)
    upper_wick = max(0.0, high_now - max(open_now, close_now))
    body = max(abs(close_now - open_now), sr_tol * 0.25)
    bull_body_bias = _clamp01((close_now - open_now) / max(sr_tol * 2.0, 1e-9))
    bear_body_bias = _clamp01((open_now - close_now) / max(sr_tol * 2.0, 1e-9))

    out: dict[str, Any] = {
        "r_sr_support_touch": 0.0,
        "r_sr_support_hold": 0.0,
        "r_sr_support_reclaim": 0.0,
        "r_sr_support_break": 0.0,
        "r_sr_resistance_touch": 0.0,
        "r_sr_resistance_reject": 0.0,
        "r_sr_resistance_reclaim": 0.0,
        "r_sr_resistance_break": 0.0,
    }

    support_proximity = 0.0
    resistance_proximity = 0.0
    support_signed_distance = 0.0
    resistance_signed_distance = 0.0

    if support is not None:
        support_signed_distance = float(normalize_distance(price_now, support, scale, clip=False))
        support_proximity = float(1.0 / (1.0 + abs(support_signed_distance)))
        touch_proximity = _clamp01(1.0 - max(0.0, low_now - support) / max(sr_tol * 2.0, 1e-9))
        close_back_above = close_now >= support - (sr_tol * 0.15)
        close_above_support = close_now >= support + (sr_tol * 0.05)
        close_below_support = close_now < support - sr_tol
        wick_reject = lower_wick >= max(body * 0.70, sr_tol * 0.35)
        penetration = _clamp01((support - close_now) / max(sr_tol * 1.5, 1e-9))

        if low_now <= support + sr_tol:
            out["r_sr_support_touch"] = max(out["r_sr_support_touch"], touch_proximity)
        if low_now <= support + sr_tol and close_back_above and (close_now >= open_now or wick_reject):
            out["r_sr_support_hold"] = max(
                out["r_sr_support_hold"],
                _soft_hold_strength(
                    proximity=max(touch_proximity, support_proximity),
                    wick_bias=_clamp01(lower_wick / max(sr_tol * 1.5, 1e-9)),
                    body_bias=bull_body_bias,
                ),
            )
        if prev_close < support - (sr_tol * 0.25) and close_above_support:
            reclaim_body_bias = _clamp01((close_now - support) / max(sr_tol * 1.5, 1e-9))
            out["r_sr_support_reclaim"] = max(
                out["r_sr_support_reclaim"],
                _clamp01((reclaim_body_bias * 0.70) + (support_proximity * 0.30)),
            )
        if close_below_support:
            out["r_sr_support_break"] = max(
                out["r_sr_support_break"],
                _soft_break_strength(penetration=penetration, body_bias=bear_body_bias),
            )

    if resistance is not None:
        resistance_signed_distance = float(normalize_distance(price_now, resistance, scale, clip=False))
        resistance_proximity = float(1.0 / (1.0 + abs(resistance_signed_distance)))
        touch_proximity = _clamp01(1.0 - max(0.0, resistance - high_now) / max(sr_tol * 2.0, 1e-9))
        close_back_below = close_now <= resistance + (sr_tol * 0.15)
        close_above_resistance = close_now > resistance + sr_tol
        close_clear_break = close_now >= resistance + (sr_tol * 0.05)
        wick_reject = upper_wick >= max(body * 0.70, sr_tol * 0.35)
        penetration = _clamp01((close_now - resistance) / max(sr_tol * 1.5, 1e-9))

        if high_now >= resistance - sr_tol:
            out["r_sr_resistance_touch"] = max(out["r_sr_resistance_touch"], touch_proximity)
        if high_now >= resistance - sr_tol and close_back_below and (close_now <= open_now or wick_reject):
            out["r_sr_resistance_reject"] = max(
                out["r_sr_resistance_reject"],
                _soft_hold_strength(
                    proximity=max(touch_proximity, resistance_proximity),
                    wick_bias=_clamp01(upper_wick / max(sr_tol * 1.5, 1e-9)),
                    body_bias=bear_body_bias,
                ),
            )
        if prev_close < resistance - (sr_tol * 0.25) and close_clear_break:
            reclaim_body_bias = _clamp01((close_now - resistance) / max(sr_tol * 1.5, 1e-9))
            out["r_sr_resistance_reclaim"] = max(
                out["r_sr_resistance_reclaim"],
                _clamp01((reclaim_body_bias * 0.70) + (resistance_proximity * 0.30)),
            )
        if close_above_resistance:
            out["r_sr_resistance_break"] = max(
                out["r_sr_resistance_break"],
                _soft_break_strength(penetration=penetration, body_bias=bull_body_bias),
            )

    strengths = _build_strengths(out)
    fired_signals = [name for name, value in out.items() if name.startswith("r_sr_") and float(value) > 0.0]
    fired_strengths = [name for name, value in strengths.items() if float(value) > 0.0]

    out["sr_subsystem_v1"] = {
        "version": "sr_subsystem_v1",
        "sr_active_support_tf": str(md.get("sr_active_support_tf") or "1H"),
        "sr_active_resistance_tf": str(md.get("sr_active_resistance_tf") or "1H"),
        "sr_support_proximity": float(support_proximity),
        "sr_resistance_proximity": float(resistance_proximity),
        "sr_support_signed_distance": float(support_signed_distance),
        "sr_resistance_signed_distance": float(resistance_signed_distance),
        "sr_touch_count": int(_to_float(md.get("sr_touch_count"), 0.0)),
        "sr_level_rank": int(_to_float(md.get("sr_level_rank"), 1.0)),
        "touch_tolerance": float(sr_tol),
        "strengths": strengths,
        "fired_signals": fired_signals,
        "fired_strengths": fired_strengths,
    }
    return out
