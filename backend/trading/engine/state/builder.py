from __future__ import annotations

from backend.trading.engine.core.models import (
    EngineContext,
    PositionSnapshot,
    StateRawSnapshot,
    StateVector,
    StateVectorV2,
)
from backend.trading.engine.state.coefficients import build_state_vector_v2 as build_state_vector_v2_from_raw
from backend.trading.engine.state.quality_state import compute_quality_state
from backend.trading.engine.state.regime_state import compute_regime_state


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


_TOPDOWN_TRENDLINE_STATE_WEIGHT_BY_TIMEFRAME = {
    "4H": 0.38,
    "1H": 0.30,
    "15M": 0.20,
    "1M": 0.12,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _compute_topdown_confluence(metadata: dict) -> tuple[float, float, dict]:
    ma_map = dict(metadata.get("mtf_ma_big_map_v1") or {})
    trend_map = dict(metadata.get("mtf_trendline_map_v1") or {})
    ma_bias = _to_float(ma_map.get("slope_bias"), _to_float(metadata.get("mtf_bias"), 0.0))
    trend_entries = dict(trend_map.get("entries") or {})

    weighted_sum = 0.0
    total_weight = 0.0
    per_timeframe: dict[str, float] = {}
    for tf, weight in _TOPDOWN_TRENDLINE_STATE_WEIGHT_BY_TIMEFRAME.items():
        entry = dict(trend_entries.get(tf) or {})
        if not entry:
            continue
        nearest_kind = str(entry.get("nearest_kind") or "").upper()
        nearest_side = str(entry.get("nearest_side") or "").upper()
        proximity = _to_float(entry.get("nearest_proximity"), 0.0)
        directional_score = 0.0
        if nearest_kind == "SUPPORT":
            if nearest_side == "ABOVE":
                directional_score = proximity
            elif nearest_side == "BELOW":
                directional_score = -proximity * 0.75
        elif nearest_kind == "RESISTANCE":
            if nearest_side == "BELOW":
                directional_score = -proximity
            elif nearest_side == "ABOVE":
                directional_score = proximity * 0.75
        if directional_score == 0.0:
            continue
        per_timeframe[tf] = directional_score
        weighted_sum += directional_score * float(weight)
        total_weight += float(weight)

    trend_bias = (weighted_sum / total_weight) if total_weight > 0.0 else 0.0
    if abs(ma_bias) <= 0.05 and abs(trend_bias) <= 0.05:
        confluence_bias = 0.0
        conflict_score = 0.0
    elif ma_bias == 0.0 or trend_bias == 0.0:
        confluence_bias = _clamp((float(ma_bias) * 0.60) + (float(trend_bias) * 0.40), -1.0, 1.0)
        conflict_score = 0.0
    elif ma_bias * trend_bias > 0.0:
        direction = 1.0 if ma_bias > 0.0 else -1.0
        confluence_bias = direction * _clamp((abs(float(ma_bias)) * 0.55) + (abs(float(trend_bias)) * 0.45), 0.0, 1.0)
        conflict_score = _clamp(abs(abs(float(ma_bias)) - abs(float(trend_bias))) * 0.25, 0.0, 1.0)
    else:
        confluence_bias = 0.0
        conflict_score = _clamp((abs(float(ma_bias)) * 0.55) + (abs(float(trend_bias)) * 0.45), 0.0, 1.0)

    detail = {
        "ma_bias": float(ma_bias),
        "trend_bias": float(trend_bias),
        "per_timeframe_trend_bias": per_timeframe,
    }
    return float(confluence_bias), float(conflict_score), detail


def build_state_raw_snapshot(ctx: EngineContext) -> StateRawSnapshot:
    regime = compute_regime_state(ctx)
    quality = compute_quality_state(ctx)
    metadata = dict(ctx.metadata or {})
    position_gate_input = dict(metadata.get("position_gate_input_v1") or {})
    interpretation = dict(position_gate_input.get("interpretation") or {})
    energy = dict(position_gate_input.get("energy") or {})
    position_scale = dict(position_gate_input.get("position_scale") or {})
    mtf_context = dict(interpretation.get("mtf_context_weight_profile_v1") or {})
    mtf_ma_map = dict(metadata.get("mtf_ma_big_map_v1") or {})
    topdown_confluence_bias, topdown_conflict_score, topdown_confluence_detail = _compute_topdown_confluence(metadata)
    advanced_inputs = dict(metadata.get("state_advanced_inputs_v1") or {})
    tick_history = dict(advanced_inputs.get("tick_history") or {})
    order_book = dict(advanced_inputs.get("order_book") or {})
    event_risk = dict(advanced_inputs.get("event_risk") or {})
    return StateRawSnapshot(
        market_mode=regime["market_mode"],
        direction_policy=regime["direction_policy"],
        liquidity_state=str(metadata.get("liquidity_state", "UNKNOWN") or "UNKNOWN").upper(),
        s_noise=float(quality["s_noise"]),
        s_conflict=float(quality["s_conflict"]),
        s_alignment=float(quality["s_alignment"]),
        s_disparity=float(quality["s_disparity"]),
        s_volatility=float(quality["s_volatility"]),
        s_topdown_bias=_to_float(mtf_context.get("bias"), 0.0),
        s_topdown_agreement=_to_float(mtf_context.get("agreement_score"), 0.0),
        s_compression=_to_float(position_scale.get("compression_score"), 0.0),
        s_expansion=_to_float(position_scale.get("expansion_score"), 0.0),
        s_middle_neutrality=_to_float(energy.get("middle_neutrality"), 0.0),
        s_current_rsi=_to_float(metadata.get("current_rsi"), 50.0),
        s_current_adx=_to_float(metadata.get("current_adx"), 0.0),
        s_current_plus_di=_to_float(metadata.get("current_plus_di"), 0.0),
        s_current_minus_di=_to_float(metadata.get("current_minus_di"), 0.0),
        s_recent_range_mean=_to_float(metadata.get("recent_range_mean"), 0.0),
        s_recent_body_mean=_to_float(metadata.get("recent_body_mean"), 0.0),
        s_sr_level_rank=_to_float(metadata.get("sr_level_rank"), 0.0),
        s_sr_touch_count=_to_float(metadata.get("sr_touch_count"), 0.0),
        s_session_box_height_ratio=_to_float(metadata.get("session_box_height_ratio"), 0.0),
        s_session_expansion_progress=_to_float(metadata.get("session_expansion_progress"), 0.0),
        s_session_position_bias=_to_float(metadata.get("session_position_bias"), 0.0),
        s_topdown_spacing_score=_to_float(mtf_ma_map.get("spacing_score"), 0.0),
        s_topdown_slope_bias=_to_float(mtf_ma_map.get("slope_bias"), 0.0),
        s_topdown_slope_agreement=_to_float(mtf_ma_map.get("slope_agreement"), 0.0),
        s_topdown_confluence_bias=topdown_confluence_bias,
        s_topdown_conflict_score=topdown_conflict_score,
        s_tick_spread_ratio=_to_float(metadata.get("current_tick_spread_ratio"), 0.0),
        s_rate_spread_ratio=_to_float(metadata.get("current_rate_spread_ratio"), 0.0),
        s_tick_volume_ratio=_to_float(metadata.get("current_tick_volume_ratio"), 0.0),
        s_real_volume_ratio=_to_float(metadata.get("current_real_volume_ratio"), 0.0),
        s_tick_flow_bias=_to_float(tick_history.get("tick_flow_bias"), 0.0),
        s_tick_flow_burst=_to_float(tick_history.get("tick_flow_burst"), 0.0),
        s_order_book_imbalance=_to_float(order_book.get("order_book_imbalance"), 0.0),
        s_order_book_thinness=_to_float(order_book.get("order_book_thinness"), 0.0),
        s_event_risk_score=_to_float(event_risk.get("event_risk_score"), 0.0),
        metadata={
            "state_contract": "raw_snapshot_v1",
            "raw_snapshot_version": "raw_snapshot_v1",
            "symbol": ctx.symbol,
            "price": _to_float(ctx.price, 0.0),
            "signal_timeframe": str(metadata.get("signal_timeframe", "") or ""),
            "signal_bar_ts": int(_to_float(metadata.get("signal_bar_ts"), 0.0)),
            "box_state": ctx.box_state,
            "bb_state": ctx.bb_state,
            "ma_alignment": str(metadata.get("ma_alignment", "MIXED")),
            "spread_ratio": float(metadata.get("current_spread_ratio", 0.0) or 0.0),
            "mtf_bias": _to_float(mtf_context.get("bias"), 0.0),
            "mtf_agreement_score": _to_float(mtf_context.get("agreement_score"), 0.0),
            "mtf_context_owner": str(mtf_context.get("owner") or ""),
            "position_scale_map_size_state": str(position_scale.get("map_size_state") or "UNKNOWN"),
            "position_scale_compression_score": _to_float(position_scale.get("compression_score"), 0.0),
            "position_scale_expansion_score": _to_float(position_scale.get("expansion_score"), 0.0),
            "middle_neutrality": _to_float(energy.get("middle_neutrality"), 0.0),
            "current_rsi": _to_float(metadata.get("current_rsi"), 50.0),
            "current_adx": _to_float(metadata.get("current_adx"), 0.0),
            "current_plus_di": _to_float(metadata.get("current_plus_di"), 0.0),
            "current_minus_di": _to_float(metadata.get("current_minus_di"), 0.0),
            "recent_range_mean": _to_float(metadata.get("recent_range_mean"), 0.0),
            "recent_body_mean": _to_float(metadata.get("recent_body_mean"), 0.0),
            "sr_level_rank": _to_float(metadata.get("sr_level_rank"), 0.0),
            "sr_touch_count": _to_float(metadata.get("sr_touch_count"), 0.0),
            "session_state_source": str(metadata.get("session_state_source", "UNKNOWN") or "UNKNOWN"),
            "session_range_high": _to_float(metadata.get("session_range_high"), 0.0),
            "session_range_low": _to_float(metadata.get("session_range_low"), 0.0),
            "session_box_height": _to_float(metadata.get("session_box_height"), 0.0),
            "session_box_height_ratio": _to_float(metadata.get("session_box_height_ratio"), 0.0),
            "session_expansion_target": _to_float(metadata.get("session_expansion_target"), 0.0),
            "position_in_session_box": str(metadata.get("position_in_session_box", "UNKNOWN") or "UNKNOWN"),
            "session_expansion_progress": _to_float(metadata.get("session_expansion_progress"), 0.0),
            "session_position_bias": _to_float(metadata.get("session_position_bias"), 0.0),
            "topdown_spacing_score": _to_float(mtf_ma_map.get("spacing_score"), 0.0),
            "topdown_slope_bias": _to_float(mtf_ma_map.get("slope_bias"), 0.0),
            "topdown_slope_agreement": _to_float(mtf_ma_map.get("slope_agreement"), 0.0),
            "topdown_confluence_bias": topdown_confluence_bias,
            "topdown_conflict_score": topdown_conflict_score,
            "topdown_confluence_detail_v1": topdown_confluence_detail,
            "current_tick_spread_points": _to_float(metadata.get("current_tick_spread_points"), 0.0),
            "current_tick_spread_ratio": _to_float(metadata.get("current_tick_spread_ratio"), 0.0),
            "current_rate_spread": _to_float(metadata.get("current_rate_spread"), 0.0),
            "current_rate_spread_ratio": _to_float(metadata.get("current_rate_spread_ratio"), 0.0),
            "recent_rate_spread_mean": _to_float(metadata.get("recent_rate_spread_mean"), 0.0),
            "current_tick_volume": _to_float(metadata.get("current_tick_volume"), 0.0),
            "current_tick_volume_ratio": _to_float(metadata.get("current_tick_volume_ratio"), 0.0),
            "recent_tick_volume_mean": _to_float(metadata.get("recent_tick_volume_mean"), 0.0),
            "current_real_volume": _to_float(metadata.get("current_real_volume"), 0.0),
            "current_real_volume_ratio": _to_float(metadata.get("current_real_volume_ratio"), 0.0),
            "recent_real_volume_mean": _to_float(metadata.get("recent_real_volume_mean"), 0.0),
            "state_advanced_inputs_v1": advanced_inputs,
            "advanced_input_activation_state": str(advanced_inputs.get("activation_state", "INACTIVE") or "INACTIVE"),
            "advanced_input_activation_reasons": list(advanced_inputs.get("activation_reasons", []) or []),
            "tick_flow_bias": _to_float(tick_history.get("tick_flow_bias"), 0.0),
            "tick_flow_burst": _to_float(tick_history.get("tick_flow_burst"), 0.0),
            "tick_flow_state": str(tick_history.get("collector_state", "INACTIVE") or "INACTIVE"),
            "tick_sample_size": int(_to_float(tick_history.get("tick_sample_size"), 0.0)),
            "order_book_imbalance": _to_float(order_book.get("order_book_imbalance"), 0.0),
            "order_book_thinness": _to_float(order_book.get("order_book_thinness"), 1.0),
            "order_book_state": str(order_book.get("collector_state", "INACTIVE") or "INACTIVE"),
            "order_book_levels": int(_to_float(order_book.get("order_book_levels"), 0.0)),
            "event_risk_score": _to_float(event_risk.get("event_risk_score"), 0.0),
            "event_risk_state": str(event_risk.get("collector_state", "INACTIVE") or "INACTIVE"),
            "event_risk_match_count": int(_to_float(event_risk.get("event_match_count"), 0.0)),
        },
    )


def build_state_vector_from_raw(raw: StateRawSnapshot) -> StateVector:
    return StateVector(
        market_mode=raw.market_mode,
        direction_policy=raw.direction_policy,
        s_noise=float(raw.s_noise),
        s_conflict=float(raw.s_conflict),
        s_alignment=float(raw.s_alignment),
        s_disparity=float(raw.s_disparity),
        s_volatility=float(raw.s_volatility),
        metadata=dict(raw.metadata or {}),
    )


def build_state_vector(ctx: EngineContext) -> StateVector:
    raw = build_state_raw_snapshot(ctx)
    return build_state_vector_from_raw(raw)


def build_state_vector_v2(
    ctx: EngineContext,
    *,
    position_snapshot: PositionSnapshot | None = None,
) -> StateVectorV2:
    raw = build_state_raw_snapshot(ctx)
    return build_state_vector_v2_from_raw(raw, position_snapshot=position_snapshot)
