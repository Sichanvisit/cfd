from __future__ import annotations

from typing import Any

from backend.trading.engine.core.context import build_engine_context
from backend.trading.engine.core.models import EngineContext
from backend.trading.engine.response.candle_descriptor import compute_candle_descriptor_from_ohlc
from backend.trading.engine.response.candle_motif import compute_candle_motifs
from backend.trading.engine.response.candle_pattern import compute_candle_patterns

_MICRO_TF_WEIGHTS = {
    "1M": 0.42,
    "5M": 0.58,
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _soft_clip01(value: float, *, scale: float = 1.0) -> float:
    if value <= 0.0:
        return 0.0
    return _clamp01(1.0 - pow(2.718281828, -float(value) / max(float(scale), 1e-9)))


def _window_payload(md: dict[str, Any], tf: str) -> dict[str, Any]:
    return dict((dict(md.get("micro_tf_window_map_v1") or {}).get("entries") or {}).get(tf) or {})


def _bar_payload(md: dict[str, Any], tf: str) -> dict[str, Any]:
    return dict((dict(md.get("micro_tf_bar_map_v1") or {}).get("entries") or {}).get(tf) or {})


def _mean(values: list[float]) -> float:
    if not values:
        return 1e-9
    return sum(float(v) for v in values) / max(1, len(values))


def _build_tf_pattern_context(ctx: EngineContext, tf: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    md = dict(ctx.metadata or {})
    bar = _bar_payload(md, tf)
    window = _window_payload(md, tf)
    opens = [float(v) for v in list(window.get("opens") or [])]
    highs = [float(v) for v in list(window.get("highs") or [])]
    lows = [float(v) for v in list(window.get("lows") or [])]
    closes = [float(v) for v in list(window.get("closes") or [])]
    if not (bar and len(opens) >= 3 and len(highs) >= 3 and len(lows) >= 3 and len(closes) >= 3):
        return {}, {}, {}, {}

    ranges = [max(1e-9, float(h) - float(l)) for h, l in zip(highs, lows)]
    bodies = [abs(float(c) - float(o)) for o, c in zip(opens, closes)]
    range_baseline = max(_mean(ranges[-9:]), 1e-9)
    body_baseline = max(_mean(bodies[-9:]), range_baseline * 0.30, 1e-9)

    descriptor = compute_candle_descriptor_from_ohlc(
        float(bar["open"]),
        float(bar["high"]),
        float(bar["low"]),
        float(bar["close"]),
        range_baseline=range_baseline,
        body_baseline=body_baseline,
    )

    metadata = {
        "current_open": opens[-1],
        "current_high": highs[-1],
        "current_low": lows[-1],
        "current_close": closes[-1],
        "previous_open": opens[-2],
        "previous_high": highs[-2],
        "previous_low": lows[-2],
        "previous_close": closes[-2],
        "pre_previous_open": opens[-3],
        "pre_previous_high": highs[-3],
        "pre_previous_low": lows[-3],
        "pre_previous_close": closes[-3],
        "recent_range_mean": range_baseline,
        "recent_body_mean": body_baseline,
    }
    temp_ctx = build_engine_context(
        symbol=ctx.symbol,
        price=float(bar["close"]),
        market_mode=ctx.market_mode,
        direction_policy=ctx.direction_policy,
        box_state=ctx.box_state,
        bb_state=ctx.bb_state,
        volatility_scale=ctx.volatility_scale,
        metadata=metadata,
    )
    patterns = compute_candle_patterns(temp_ctx, descriptor)
    motifs = compute_candle_motifs(descriptor, patterns)
    return descriptor, patterns, motifs, {
        "range_baseline": float(range_baseline),
        "body_baseline": float(body_baseline),
        "window_size": int(min(len(opens), len(highs), len(lows), len(closes))),
    }


def _micro_reclaim_score(bar: dict[str, Any], window: dict[str, Any]) -> float:
    closes = [float(v) for v in list(window.get("closes") or [])]
    highs = [float(v) for v in list(window.get("highs") or [])]
    lows = [float(v) for v in list(window.get("lows") or [])]
    if len(closes) < 2 or not highs or not lows:
        return 0.0
    current_close = float(bar.get("close", 0.0))
    current_open = float(bar.get("open", current_close))
    prev_close = closes[-2]
    recent_high = max(highs[-5:]) if len(highs) >= 5 else max(highs)
    recent_low = min(lows[-5:]) if len(lows) >= 5 else min(lows)
    local_mid = (recent_high + recent_low) / 2.0
    reclaim = current_close > local_mid and prev_close < local_mid and current_close >= current_open
    if not reclaim:
        return 0.0
    return _clamp01(0.55 + (0.45 * _clamp01((current_close - local_mid) / max(recent_high - local_mid, 1e-9))))


def _micro_lose_score(bar: dict[str, Any], window: dict[str, Any]) -> float:
    closes = [float(v) for v in list(window.get("closes") or [])]
    highs = [float(v) for v in list(window.get("highs") or [])]
    lows = [float(v) for v in list(window.get("lows") or [])]
    if len(closes) < 2 or not highs or not lows:
        return 0.0
    current_close = float(bar.get("close", 0.0))
    current_open = float(bar.get("open", current_close))
    prev_close = closes[-2]
    recent_high = max(highs[-5:]) if len(highs) >= 5 else max(highs)
    recent_low = min(lows[-5:]) if len(lows) >= 5 else min(lows)
    local_mid = (recent_high + recent_low) / 2.0
    lose = current_close < local_mid and prev_close > local_mid and current_close <= current_open
    if not lose:
        return 0.0
    return _clamp01(0.55 + (0.45 * _clamp01((local_mid - current_close) / max(local_mid - recent_low, 1e-9))))


def compute_micro_responses(ctx: EngineContext) -> dict[str, Any]:
    md = dict(ctx.metadata or {})
    per_tf: dict[str, Any] = {}
    bull_reject_scores: list[tuple[float, float]] = []
    bear_reject_scores: list[tuple[float, float]] = []
    bull_break_scores: list[tuple[float, float]] = []
    bear_break_scores: list[tuple[float, float]] = []
    indecision_scores: list[tuple[float, float]] = []
    reclaim_scores: list[tuple[float, float]] = []
    lose_scores: list[tuple[float, float]] = []

    for tf, weight in _MICRO_TF_WEIGHTS.items():
        bar = _bar_payload(md, tf)
        window = _window_payload(md, tf)
        descriptor, patterns, motifs, extra = _build_tf_pattern_context(ctx, tf)
        if not descriptor:
            continue
        reclaim_score = _micro_reclaim_score(bar, window)
        lose_score = _micro_lose_score(bar, window)
        bull_reject = _clamp01(max(_to_float(motifs.get("bull_reject"), 0.0), reclaim_score * 0.72))
        bear_reject = _clamp01(max(_to_float(motifs.get("bear_reject"), 0.0), lose_score * 0.72))
        bull_break = _clamp01(max(_to_float(motifs.get("bull_break_body"), 0.0), reclaim_score * 0.48))
        bear_break = _clamp01(max(_to_float(motifs.get("bear_break_body"), 0.0), lose_score * 0.48))
        indecision = _clamp01(_to_float(motifs.get("indecision"), 0.0) + (_to_float(motifs.get("climax"), 0.0) * 0.18))

        per_tf[tf] = {
            "weight": float(weight),
            "descriptor": descriptor,
            "patterns": patterns,
            "motifs": motifs,
            "micro_reclaim_up": float(reclaim_score),
            "micro_lose_down": float(lose_score),
            "bull_reject_strength": float(bull_reject),
            "bear_reject_strength": float(bear_reject),
            "bull_break_strength": float(bull_break),
            "bear_break_strength": float(bear_break),
            "indecision_strength": float(indecision),
            **extra,
        }

        bull_reject_scores.append((weight, bull_reject))
        bear_reject_scores.append((weight, bear_reject))
        bull_break_scores.append((weight, bull_break))
        bear_break_scores.append((weight, bear_break))
        indecision_scores.append((weight, indecision))
        reclaim_scores.append((weight, reclaim_score))
        lose_scores.append((weight, lose_score))

    def _weighted(values: list[tuple[float, float]]) -> float:
        if not values:
            return 0.0
        total_weight = sum(float(w) for w, _ in values)
        if total_weight <= 1e-9:
            return 0.0
        return _clamp01(sum(float(w) * float(v) for w, v in values) / total_weight)

    strengths = {
        "micro_bull_reject_strength": _weighted(bull_reject_scores),
        "micro_bear_reject_strength": _weighted(bear_reject_scores),
        "micro_bull_break_strength": _weighted(bull_break_scores),
        "micro_bear_break_strength": _weighted(bear_break_scores),
        "micro_indecision_strength": _weighted(indecision_scores),
        "micro_reclaim_up_strength": _weighted(reclaim_scores),
        "micro_lose_down_strength": _weighted(lose_scores),
    }
    fired_strengths = [name for name, value in strengths.items() if float(value) >= 0.40]

    return {
        "r_micro_bull_reject": float(strengths["micro_bull_reject_strength"]),
        "r_micro_bear_reject": float(strengths["micro_bear_reject_strength"]),
        "r_micro_bull_break": float(strengths["micro_bull_break_strength"]),
        "r_micro_bear_break": float(strengths["micro_bear_break_strength"]),
        "r_micro_indecision": float(strengths["micro_indecision_strength"]),
        "micro_tf_subsystem_v1": {
            "version": "micro_tf_subsystem_v1",
            "timeframes_requested": list(_MICRO_TF_WEIGHTS.keys()),
            "timeframes_available": [tf for tf in _MICRO_TF_WEIGHTS.keys() if tf in per_tf],
            "per_timeframe": per_tf,
            "weights": {tf: float(weight) for tf, weight in _MICRO_TF_WEIGHTS.items()},
            "strengths": strengths,
            "fired_strengths": fired_strengths,
        },
    }
