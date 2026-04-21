from __future__ import annotations

from backend.trading.engine.core.models import PositionSnapshot, StateRawSnapshot, StateVectorV2


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _soft_clip01(value: float, *, scale: float = 1.0) -> float:
    if value <= 0.0:
        return 0.0
    return _clamp01(1.0 - pow(2.718281828, -float(value) / max(float(scale), 1e-9)))


def _map_regime_gains(mode: str) -> tuple[float, float, float]:
    if mode == "RANGE":
        return 1.18, 0.94, 0.90
    if mode == "TREND":
        return 0.88, 1.18, 1.12
    if mode == "SHOCK":
        return 0.72, 0.78, 0.74
    return 1.0, 1.0, 1.0


def _describe_regime_reason(mode: str, axis: str, value: float) -> str:
    if mode == "RANGE":
        mapping = {
            "range_reversal_gain": "market_mode=RANGE -> reversal boost",
            "trend_pullback_gain": "market_mode=RANGE -> pullback baseline damp",
            "breakout_continuation_gain": "market_mode=RANGE -> breakout slight damp",
        }
    elif mode == "TREND":
        mapping = {
            "range_reversal_gain": "market_mode=TREND -> reversal damp",
            "trend_pullback_gain": "market_mode=TREND -> pullback boost",
            "breakout_continuation_gain": "market_mode=TREND -> breakout continuation boost",
        }
    elif mode == "SHOCK":
        mapping = {
            "range_reversal_gain": "market_mode=SHOCK -> reversal damp",
            "trend_pullback_gain": "market_mode=SHOCK -> pullback damp",
            "breakout_continuation_gain": "market_mode=SHOCK -> continuation damp",
        }
    else:
        mapping = {
            "range_reversal_gain": f"market_mode={mode} -> neutral baseline",
            "trend_pullback_gain": f"market_mode={mode} -> neutral baseline",
            "breakout_continuation_gain": f"market_mode={mode} -> neutral baseline",
        }
    return f"{mapping[axis]} (value={value:.4f})"


def _map_noise_damp(noise: float) -> float:
    return _clamp01(1.0 - (float(noise) * 0.55))


def _map_conflict_damp(
    raw_conflict: float,
    position_conflict_score: float,
    position_conflict_kind: str,
) -> tuple[float, float, float]:
    position_basis = float(position_conflict_score)
    if position_conflict_kind:
        position_basis = max(position_basis, 0.45)
    raw_assist = float(raw_conflict) * 0.30
    conflict_basis = max(position_basis, raw_assist)
    return _clamp01(1.0 - (conflict_basis * 0.65)), conflict_basis, raw_assist


def _map_alignment_gain(raw_alignment: float, position_primary_label: str, position_bias_label: str) -> tuple[float, float]:
    alignment_basis = float(raw_alignment)
    if position_primary_label.startswith("ALIGNED_"):
        alignment_basis = max(alignment_basis, 1.0)
    elif position_bias_label or position_primary_label.endswith("_BIAS"):
        alignment_basis = max(alignment_basis, 0.55)
    return 1.0 + (alignment_basis * 0.20), alignment_basis


def _map_countertrend_penalty(policy: str) -> float:
    if policy in {"BUY_ONLY", "SELL_ONLY"}:
        return 0.25
    if policy != "BOTH":
        return 0.10
    return 0.0


def _map_liquidity_penalty(liquidity: str, spread_ratio: float) -> float:
    if liquidity == "BAD":
        penalty = 0.45
    elif liquidity == "OK":
        penalty = 0.18
    elif liquidity == "GOOD":
        penalty = 0.0
    else:
        penalty = 0.10
    return min(0.55, penalty + min(max(float(spread_ratio) - 1.0, 0.0) * 0.12, 0.10))


def _map_volatility_penalty(volatility: float, mode: str) -> float:
    penalty = _clamp01(float(volatility) * 0.60)
    if mode == "SHOCK":
        penalty = max(penalty, 0.35)
    return penalty


def _map_topdown_bias(raw_bias: float, raw_agreement: float) -> tuple[float, float, float]:
    signed_bias = _clamp(float(raw_bias), -1.0, 1.0)
    agreement = _clamp01(float(raw_agreement))
    bull_basis = max(signed_bias, 0.0) * (0.72 + (0.28 * agreement))
    bear_basis = max(-signed_bias, 0.0) * (0.72 + (0.28 * agreement))
    topdown_bull_bias = _soft_clip01(bull_basis, scale=0.30)
    topdown_bear_bias = _soft_clip01(bear_basis, scale=0.30)
    big_map_alignment_gain = 1.0 + (agreement * 0.18)
    return topdown_bull_bias, topdown_bear_bias, big_map_alignment_gain


def _map_patience_cluster(
    *,
    mode: str,
    raw_noise: float,
    raw_conflict: float,
    raw_volatility: float,
    raw_middle_neutrality: float,
    compression: float,
    expansion: float,
    topdown_agreement: float,
    alignment_basis: float,
    liquidity_penalty: float,
    countertrend_penalty: float,
) -> tuple[float, float, float, float]:
    ambiguity = _clamp01(
        max(
            float(raw_conflict),
            float(raw_middle_neutrality) * 0.92,
            float(raw_noise) * 0.58,
        )
    )
    quality_floor = _clamp01(
        1.0
        - max(
            float(raw_noise) * 0.42,
            float(raw_conflict) * 0.48,
            float(raw_volatility) * 0.24,
            float(liquidity_penalty) * 0.78,
        )
    )
    structure_quality = _clamp01(
        max(float(topdown_agreement), float(alignment_basis) * 0.80, quality_floor)
    )

    wait_base = ambiguity + (float(compression) * 0.18) + (float(countertrend_penalty) * 0.20) - (float(topdown_agreement) * 0.12)
    if mode == "SHOCK":
        wait_base += 0.18
    wait_patience_gain = _clamp(1.0 + wait_base * 0.45, 0.85, 1.42)

    confirm_base = (
        (structure_quality * 0.52)
        + (float(topdown_agreement) * 0.22)
        + (float(expansion) * 0.06)
        - (ambiguity * 0.28)
        - (float(countertrend_penalty) * 0.12)
    )
    if mode == "TREND":
        confirm_base += 0.08
    elif mode == "SHOCK":
        confirm_base -= 0.12
    confirm_aggression_gain = _clamp(0.86 + (confirm_base * 0.42), 0.78, 1.34)

    hold_base = (
        (structure_quality * 0.38)
        + (float(topdown_agreement) * 0.20)
        + ((1.0 - float(liquidity_penalty)) * 0.16)
        - (float(raw_volatility) * 0.18)
    )
    if mode == "RANGE":
        hold_base += 0.10 + (float(compression) * 0.08)
    elif mode == "TREND":
        hold_base += 0.08 + (float(expansion) * 0.05)
    elif mode == "SHOCK":
        hold_base -= 0.22
    hold_patience_gain = _clamp(0.86 + (hold_base * 0.48), 0.74, 1.38)

    fast_exit_base = (
        (float(raw_volatility) * 0.40)
        + (float(raw_noise) * 0.26)
        + (float(liquidity_penalty) * 0.54)
        + (float(countertrend_penalty) * 0.34)
        + (ambiguity * 0.18)
        - (float(topdown_agreement) * 0.18)
    )
    if mode == "SHOCK":
        fast_exit_base += 0.18
    fast_exit_risk_penalty = _clamp01(fast_exit_base)

    return wait_patience_gain, confirm_aggression_gain, hold_patience_gain, fast_exit_risk_penalty


def _label_regime_state(mode: str, raw_noise: float, raw_conflict: float, compression: float, expansion: float) -> str:
    if mode == "SHOCK":
        return "SHOCK"
    if mode == "RANGE":
        if max(float(raw_noise), float(raw_conflict)) >= 0.55:
            return "CHOP_NOISE"
        if float(compression) >= 0.60:
            return "RANGE_COMPRESSION"
        return "RANGE_SWING"
    if mode == "TREND":
        if float(expansion) >= 0.62:
            return "BREAKOUT_EXPANSION"
        return "TREND_PULLBACK"
    return "UNKNOWN"


def _score_momentum_quality(
    *,
    rsi: float,
    adx: float,
    plus_di: float,
    minus_di: float,
    disparity_penalty: float,
) -> tuple[float, str, str]:
    adx_score = _clamp01(float(adx) / 35.0)
    di_gap = abs(float(plus_di) - float(minus_di))
    di_score = _clamp01(di_gap / 22.0)
    if float(rsi) <= 0.0:
        rsi_quality = 0.45
    elif 35.0 <= float(rsi) <= 65.0:
        rsi_quality = 1.0
    elif 25.0 <= float(rsi) < 35.0 or 65.0 < float(rsi) <= 75.0:
        rsi_quality = 0.78
    elif 20.0 <= float(rsi) < 25.0 or 75.0 < float(rsi) <= 80.0:
        rsi_quality = 0.58
    else:
        rsi_quality = 0.34

    score = _clamp01((adx_score * 0.45) + (di_score * 0.35) + (rsi_quality * 0.20) - (float(disparity_penalty) * 0.18))

    if float(disparity_penalty) >= 0.72 and (float(rsi) <= 22.0 or float(rsi) >= 78.0):
        label = "EXHAUSTED_MOMENTUM"
    elif score >= 0.68 and float(plus_di) >= float(minus_di) + 3.0:
        label = "BULL_IMPULSE_READY"
    elif score >= 0.68 and float(minus_di) >= float(plus_di) + 3.0:
        label = "BEAR_IMPULSE_READY"
    elif adx_score <= 0.18 and di_score <= 0.15:
        label = "FLAT_MOMENTUM"
    elif score >= 0.48:
        label = "BALANCED_MOMENTUM"
    else:
        label = "WEAK_MOMENTUM"

    reason = (
        f"rsi={float(rsi):.4f}, adx={float(adx):.4f}, plus_di={float(plus_di):.4f}, "
        f"minus_di={float(minus_di):.4f}, disparity_penalty={float(disparity_penalty):.4f} "
        f"-> momentum_quality_score={score:.4f}, label={label}"
    )
    return score, label, reason


def _score_activity_quality(
    *,
    recent_range_mean: float,
    recent_body_mean: float,
    volatility_penalty: float,
) -> tuple[float, str, str]:
    range_mean = max(float(recent_range_mean), 0.0)
    body_mean = max(float(recent_body_mean), 0.0)
    body_share = _clamp01(body_mean / max(range_mean, 1e-9)) if range_mean > 0.0 else 0.0
    volatility_balance = 1.0 - _clamp01(abs(float(volatility_penalty) - 0.25) / 0.75)
    score = _clamp01((body_share * 0.62) + (volatility_balance * 0.38))

    if range_mean <= 0.0:
        label = "UNKNOWN_ACTIVITY"
    elif body_share < 0.18 and float(volatility_penalty) < 0.18:
        label = "DEAD_ACTIVITY"
    elif body_share < 0.22 and float(volatility_penalty) >= 0.55:
        label = "WICKY_NOISE_ACTIVITY"
    elif body_share >= 0.55 and float(volatility_penalty) >= 0.48:
        label = "EXPLOSIVE_ACTIVITY"
    elif score >= 0.56:
        label = "HEALTHY_ACTIVITY"
    else:
        label = "THIN_ACTIVITY"

    reason = (
        f"recent_range_mean={range_mean:.4f}, recent_body_mean={body_mean:.4f}, "
        f"body_share={body_share:.4f}, volatility_penalty={float(volatility_penalty):.4f} "
        f"-> activity_quality_score={score:.4f}, label={label}"
    )
    return score, label, reason


def _score_level_reliability(*, sr_level_rank: float, sr_touch_count: float) -> tuple[float, str, str]:
    rank = max(float(sr_level_rank), 0.0)
    touches = max(float(sr_touch_count), 0.0)
    if rank <= 0.0:
        rank_score = 0.25
    elif rank <= 1.0:
        rank_score = 1.0
    elif rank <= 2.0:
        rank_score = 0.74
    elif rank <= 3.0:
        rank_score = 0.54
    else:
        rank_score = 0.36
    touch_score = _clamp01(touches / 4.0)
    score = _clamp01((rank_score * 0.60) + (max(touch_score, 0.20 if rank > 0 else 0.0) * 0.40))

    if score >= 0.78 and touches >= 2.0 and rank <= 1.0:
        label = "TESTED_PRIMARY_LEVEL"
    elif score >= 0.62 and rank <= 1.0:
        label = "PRIMARY_LEVEL"
    elif score >= 0.46:
        label = "SECONDARY_LEVEL"
    else:
        label = "WEAK_LEVEL"

    reason = (
        f"sr_level_rank={rank:.4f}, sr_touch_count={touches:.4f} "
        f"-> level_reliability_score={score:.4f}, label={label}"
    )
    return score, label, reason


def _label_quality_state(
    noise_damp: float,
    conflict_damp: float,
    liquidity_penalty: float,
    volatility_penalty: float,
    *,
    momentum_quality_score: float = 0.5,
    activity_quality_score: float = 0.5,
    level_reliability_score: float = 0.5,
) -> tuple[str, float]:
    base_composite = (
        (float(noise_damp) * 0.30)
        + (float(conflict_damp) * 0.30)
        + ((1.0 - float(liquidity_penalty)) * 0.20)
        + ((1.0 - float(volatility_penalty)) * 0.20)
    )
    composite = _clamp01(
        (base_composite * 0.74)
        + (float(momentum_quality_score) * 0.14)
        + (float(activity_quality_score) * 0.08)
        + (float(level_reliability_score) * 0.04)
    )
    if composite >= 0.72:
        return "HIGH_QUALITY", composite
    if composite >= 0.46:
        return "MEDIUM_QUALITY", composite
    return "LOW_QUALITY", composite


def _label_topdown_state(raw_bias: float, raw_agreement: float) -> str:
    signed_bias = _clamp(float(raw_bias), -1.0, 1.0)
    agreement = _clamp01(float(raw_agreement))
    if signed_bias >= 0.16 and agreement >= 0.48:
        return "BULL_ALIGNED"
    if signed_bias <= -0.16 and agreement >= 0.48:
        return "BEAR_ALIGNED"
    if abs(signed_bias) >= 0.08:
        return "MIXED_TOPDOWN"
    return "NEUTRAL_TOPDOWN"


def _label_patience_state(
    wait_patience_gain: float,
    confirm_aggression_gain: float,
    hold_patience_gain: float,
    fast_exit_risk_penalty: float,
) -> str:
    if float(fast_exit_risk_penalty) >= 0.58:
        return "FAST_EXIT_FAVOR"
    scored = {
        "WAIT_FAVOR": float(wait_patience_gain),
        "CONFIRM_FAVOR": float(confirm_aggression_gain),
        "HOLD_FAVOR": float(hold_patience_gain),
    }
    return max(scored, key=scored.get)


def _label_session_regime_state(
    session_box_height_ratio: float,
    session_expansion_progress: float,
    session_position_bias: float,
) -> str:
    height_ratio = max(float(session_box_height_ratio), 0.0)
    expansion_progress = max(float(session_expansion_progress), 0.0)
    position_bias = float(session_position_bias)

    if height_ratio <= 0.45:
        return "SESSION_COMPRESSION"
    if expansion_progress >= 0.35:
        return "SESSION_EXPANSION"
    if abs(position_bias) >= 0.55:
        return "SESSION_EDGE_ROTATION"
    return "SESSION_BALANCED"


def _label_session_expansion_state(
    session_expansion_progress: float,
    session_position_bias: float,
) -> str:
    expansion_progress = max(float(session_expansion_progress), 0.0)
    position_bias = float(session_position_bias)

    if expansion_progress <= 0.0:
        return "IN_SESSION_BOX"
    if position_bias >= 0.0:
        if expansion_progress >= 0.90:
            return "UP_EXTENDED_EXPANSION"
        if expansion_progress >= 0.35:
            return "UP_ACTIVE_EXPANSION"
        return "UP_EARLY_EXPANSION"
    if expansion_progress >= 0.90:
        return "DOWN_EXTENDED_EXPANSION"
    if expansion_progress >= 0.35:
        return "DOWN_ACTIVE_EXPANSION"
    return "DOWN_EARLY_EXPANSION"


def _label_session_exhaustion_state(
    session_expansion_progress: float,
    session_position_bias: float,
    volatility_penalty: float,
) -> str:
    expansion_progress = max(float(session_expansion_progress), 0.0)
    position_bias = float(session_position_bias)
    volatility = _clamp01(float(volatility_penalty))

    if expansion_progress >= 1.0 or (expansion_progress >= 0.65 and volatility >= 0.40):
        return "HIGH_EXHAUSTION_RISK"
    if expansion_progress >= 0.40:
        return "MEDIUM_EXHAUSTION_RISK"
    if abs(position_bias) >= 0.90:
        return "EDGE_WATCH"
    return "LOW_EXHAUSTION_RISK"


def _label_topdown_spacing_state(topdown_spacing_score: float) -> str:
    score = _clamp01(float(topdown_spacing_score))
    if score >= 0.72:
        return "WIDE_SPACING"
    if score >= 0.40:
        return "ORDERED_SPACING"
    if score >= 0.18:
        return "TIGHT_SPACING"
    return "FLAT_SPACING"


def _label_topdown_slope_state(topdown_slope_bias: float, topdown_slope_agreement: float) -> str:
    slope_bias = _clamp(float(topdown_slope_bias), -1.0, 1.0)
    agreement = _clamp01(float(topdown_slope_agreement))
    if slope_bias >= 0.16 and agreement >= 0.45:
        return "UP_SLOPE_ALIGNED"
    if slope_bias <= -0.16 and agreement >= 0.45:
        return "DOWN_SLOPE_ALIGNED"
    if abs(slope_bias) >= 0.08:
        return "MIXED_SLOPE"
    return "FLAT_SLOPE"


def _label_topdown_confluence_state(topdown_confluence_bias: float, topdown_conflict_score: float) -> str:
    confluence_bias = _clamp(float(topdown_confluence_bias), -1.0, 1.0)
    conflict_score = _clamp01(float(topdown_conflict_score))
    if conflict_score >= 0.45:
        return "TOPDOWN_CONFLICT"
    if confluence_bias >= 0.16:
        return "BULL_CONFLUENCE"
    if confluence_bias <= -0.16:
        return "BEAR_CONFLUENCE"
    return "WEAK_CONFLUENCE"


def _label_spread_stress_state(tick_spread_ratio: float, rate_spread_ratio: float) -> str:
    tick_ratio = max(float(tick_spread_ratio), 0.0)
    rate_ratio = max(float(rate_spread_ratio), 0.0)
    stress = max(tick_ratio * 1.8, rate_ratio)
    if stress >= 1.60:
        return "HIGH_SPREAD_STRESS"
    if stress >= 1.15:
        return "ELEVATED_SPREAD_STRESS"
    if stress <= 0.55:
        return "TIGHT_SPREAD"
    return "NORMAL_SPREAD"


def _label_volume_participation_state(tick_volume_ratio: float, real_volume_ratio: float) -> str:
    tick_ratio = max(float(tick_volume_ratio), 0.0)
    real_ratio = max(float(real_volume_ratio), 0.0)
    effective_real = real_ratio if real_ratio > 0.0 else tick_ratio
    participation = (tick_ratio * 0.58) + (effective_real * 0.42)
    if participation >= 1.65:
        return "HIGH_PARTICIPATION"
    if participation >= 0.95:
        return "NORMAL_PARTICIPATION"
    if participation >= 0.50:
        return "THIN_PARTICIPATION"
    return "LOW_PARTICIPATION"


def _label_execution_friction_state(
    *,
    tick_spread_ratio: float,
    rate_spread_ratio: float,
    tick_volume_ratio: float,
    real_volume_ratio: float,
    liquidity_penalty: float,
) -> str:
    spread_stress = max(float(tick_spread_ratio) * 1.8, float(rate_spread_ratio), 0.0)
    effective_real = float(real_volume_ratio) if float(real_volume_ratio) > 0.0 else float(tick_volume_ratio)
    participation = (max(float(tick_volume_ratio), 0.0) * 0.58) + (max(effective_real, 0.0) * 0.42)
    friction_score = _clamp01(
        (spread_stress * 0.38)
        + ((1.0 - _clamp(participation / 1.50, 0.0, 1.0)) * 0.32)
        + (float(liquidity_penalty) * 0.30)
    )
    if friction_score >= 0.68:
        return "HIGH_FRICTION"
    if friction_score >= 0.38:
        return "MEDIUM_FRICTION"
    return "LOW_FRICTION"


def _label_advanced_input_activation_state(activation_state: str) -> str:
    state = str(activation_state or "INACTIVE").upper()
    if state == "ACTIVE":
        return "ADVANCED_ACTIVE"
    if state == "PARTIAL_ACTIVE":
        return "ADVANCED_PARTIAL"
    if state == "PASSIVE_ONLY":
        return "ADVANCED_PASSIVE"
    if state == "UNAVAILABLE":
        return "ADVANCED_UNAVAILABLE"
    if state == "DISABLED":
        return "ADVANCED_DISABLED"
    return "ADVANCED_IDLE"


def _label_tick_flow_state(tick_flow_bias: float, tick_flow_burst: float, collector_state: str = "") -> str:
    collector = str(collector_state or "").upper()
    if collector in {"UNAVAILABLE", "DISABLED", "INACTIVE"}:
        return collector
    bias = _clamp(float(tick_flow_bias), -1.0, 1.0)
    burst = _clamp01(float(tick_flow_burst))
    if burst <= 0.20:
        return "QUIET_FLOW"
    if burst >= 0.52 and bias >= 0.24:
        return "BURST_UP_FLOW"
    if burst >= 0.52 and bias <= -0.24:
        return "BURST_DOWN_FLOW"
    return "BALANCED_FLOW"


def _label_order_book_state(order_book_imbalance: float, order_book_thinness: float, collector_state: str = "") -> str:
    collector = str(collector_state or "").upper()
    if collector in {"UNAVAILABLE", "DISABLED", "INACTIVE"}:
        return collector
    imbalance = _clamp(float(order_book_imbalance), -1.0, 1.0)
    thinness = _clamp01(float(order_book_thinness))
    if thinness >= 0.72:
        return "THIN_BOOK"
    if imbalance >= 0.18:
        return "BID_IMBALANCE"
    if imbalance <= -0.18:
        return "ASK_IMBALANCE"
    return "BALANCED_BOOK"


def _label_event_risk_state(event_risk_score: float, collector_state: str = "") -> str:
    collector = str(collector_state or "").upper()
    if collector in {"UNAVAILABLE", "DISABLED", "INACTIVE"}:
        return collector
    score = _clamp01(float(event_risk_score))
    if score >= 0.68:
        return "HIGH_EVENT_RISK"
    if score >= 0.34:
        return "WATCH_EVENT_RISK"
    return "LOW_EVENT_RISK"


def _label_micro_breakout_readiness_state(score: float) -> str:
    value = float(score)
    if value >= 0.72:
        return "BREAKOUT_READY"
    if value >= 0.45:
        return "BREAKOUT_WATCH"
    return "BREAKOUT_NEUTRAL"


def _label_micro_reversal_risk_state(score: float) -> str:
    value = float(score)
    if value >= 0.72:
        return "REVERSAL_RISK_HIGH"
    if value >= 0.45:
        return "REVERSAL_RISK_WATCH"
    return "REVERSAL_RISK_LOW"


def _label_micro_participation_state(burst_score: float, decay_score: float) -> str:
    burst = float(burst_score)
    decay = float(decay_score)
    if burst >= 0.65 and decay <= 0.35:
        return "BURST_CONFIRMED"
    if burst >= 0.45 and decay >= 0.45:
        return "BURST_FADING"
    if burst <= 0.20:
        return "QUIET_PARTICIPATION"
    return "NORMAL_PARTICIPATION"


def _label_micro_gap_context_state(gap_fill_progress: float | None) -> str:
    if gap_fill_progress is None:
        return "GAP_CONTEXT_MISSING"
    value = float(gap_fill_progress)
    if value < 0.33:
        return "EARLY_GAP_FILL"
    if value < 0.85:
        return "ACTIVE_GAP_FILL"
    return "LATE_GAP_FILL"


def _score_micro_structure_cluster(raw: StateRawSnapshot) -> tuple[float, float, float, str, str, str, str]:
    compression_signal = _clamp01(float(raw.s_range_compression_ratio_20))
    burst_signal = _clamp01(max(float(raw.s_volume_burst_ratio_20) - 1.0, 0.0) / 1.5)
    decay_signal = _clamp01(float(raw.s_volume_burst_decay_20))
    doji_signal = _clamp01(float(raw.s_doji_ratio_20) * 2.0)
    run_signal = _clamp01(float(raw.s_same_color_run_current) / 5.0)
    wick_signal = _clamp01(max(float(raw.s_upper_wick_ratio_20), float(raw.s_lower_wick_ratio_20)))
    retest_signal = _clamp01(max(float(raw.s_swing_high_retest_count_20), float(raw.s_swing_low_retest_count_20)) / 3.0)

    breakout_readiness = _clamp01(
        (compression_signal * 0.38)
        + (burst_signal * 0.34)
        + (run_signal * 0.18)
        - (doji_signal * 0.12)
        - (decay_signal * 0.08)
    )
    reversal_risk = _clamp01(
        (wick_signal * 0.38)
        + (retest_signal * 0.32)
        + (doji_signal * 0.18)
        + (decay_signal * 0.12)
    )
    participation_score = _clamp01((burst_signal * 0.65) + ((1.0 - decay_signal) * 0.35))

    return (
        breakout_readiness,
        reversal_risk,
        participation_score,
        _label_micro_breakout_readiness_state(breakout_readiness),
        _label_micro_reversal_risk_state(reversal_risk),
        _label_micro_participation_state(burst_signal, decay_signal),
        _label_micro_gap_context_state(raw.s_gap_fill_progress),
    )


def build_state_vector_v2(
    raw: StateRawSnapshot,
    *,
    position_snapshot: PositionSnapshot | None = None,
) -> StateVectorV2:
    mode = str(raw.market_mode or "UNKNOWN").upper()
    policy = str(raw.direction_policy or "UNKNOWN").upper()
    liquidity = str(raw.liquidity_state or "UNKNOWN").upper()

    range_reversal_gain, trend_pullback_gain, breakout_continuation_gain = _map_regime_gains(mode)

    position_conflict_score = 0.0
    position_primary_label = ""
    position_bias_label = ""
    position_conflict_kind = ""
    position_secondary_context_label = ""
    if position_snapshot is not None:
        position_conflict_score = float(position_snapshot.energy.position_conflict_score or 0.0)
        position_primary_label = str(position_snapshot.interpretation.primary_label or "")
        position_bias_label = str(position_snapshot.interpretation.bias_label or "")
        position_conflict_kind = str(position_snapshot.interpretation.conflict_kind or "")
        position_secondary_context_label = str(position_snapshot.interpretation.secondary_context_label or "")

    noise_damp = _map_noise_damp(float(raw.s_noise))
    conflict_damp, conflict_basis, raw_conflict_assist = _map_conflict_damp(
        float(raw.s_conflict),
        position_conflict_score,
        position_conflict_kind,
    )
    alignment_gain, alignment_basis = _map_alignment_gain(
        float(raw.s_alignment),
        position_primary_label,
        position_bias_label,
    )
    countertrend_penalty = _map_countertrend_penalty(policy)
    spread_ratio = float((raw.metadata or {}).get("spread_ratio", 0.0) or 0.0)
    liquidity_penalty = _map_liquidity_penalty(liquidity, spread_ratio)
    volatility_penalty = _map_volatility_penalty(float(raw.s_volatility), mode)
    topdown_bull_bias, topdown_bear_bias, big_map_alignment_gain = _map_topdown_bias(
        float(raw.s_topdown_bias),
        float(raw.s_topdown_agreement),
    )
    momentum_quality_score, momentum_quality_label, momentum_quality_reason = _score_momentum_quality(
        rsi=float(raw.s_current_rsi),
        adx=float(raw.s_current_adx),
        plus_di=float(raw.s_current_plus_di),
        minus_di=float(raw.s_current_minus_di),
        disparity_penalty=float(raw.s_disparity),
    )
    wait_patience_gain, confirm_aggression_gain, hold_patience_gain, fast_exit_risk_penalty = _map_patience_cluster(
        mode=mode,
        raw_noise=float(raw.s_noise),
        raw_conflict=float(raw.s_conflict),
        raw_volatility=float(raw.s_volatility),
        raw_middle_neutrality=float(raw.s_middle_neutrality),
        compression=float(raw.s_compression),
        expansion=float(raw.s_expansion),
        topdown_agreement=float(raw.s_topdown_agreement),
        alignment_basis=alignment_basis,
        liquidity_penalty=liquidity_penalty,
        countertrend_penalty=countertrend_penalty,
    )
    (
        micro_breakout_readiness_score,
        micro_reversal_risk_score,
        micro_participation_score,
        micro_breakout_readiness_state,
        micro_reversal_risk_state,
        micro_participation_state,
        micro_gap_context_state,
    ) = _score_micro_structure_cluster(raw)
    range_reversal_gain = _clamp(
        range_reversal_gain + (micro_reversal_risk_score * 0.16) - (micro_breakout_readiness_score * 0.07),
        0.70,
        1.45,
    )
    trend_pullback_gain = _clamp(
        trend_pullback_gain + (_clamp01(float(raw.s_same_color_run_current) / 5.0) * 0.05) - (_clamp01(float(raw.s_doji_ratio_20) * 2.0) * 0.03),
        0.70,
        1.45,
    )
    breakout_continuation_gain = _clamp(
        breakout_continuation_gain
        + (micro_breakout_readiness_score * 0.18)
        + (micro_participation_score * 0.06)
        - (micro_reversal_risk_score * 0.08),
        0.70,
        1.45,
    )
    wait_patience_gain = _clamp(
        wait_patience_gain
        + (_clamp01(float(raw.s_range_compression_ratio_20)) * 0.06)
        - (micro_participation_score * 0.03),
        0.85,
        1.48,
    )
    confirm_aggression_gain = _clamp(
        confirm_aggression_gain
        + (micro_breakout_readiness_score * 0.10)
        + (micro_participation_score * 0.04)
        - (micro_reversal_risk_score * 0.06),
        0.72,
        1.34,
    )
    hold_patience_gain = _clamp(
        hold_patience_gain
        - (micro_reversal_risk_score * 0.05)
        + (_clamp01(float(raw.s_same_color_run_current) / 5.0) * 0.03),
        0.70,
        1.38,
    )
    fast_exit_risk_penalty = _clamp01(
        fast_exit_risk_penalty
        + (micro_reversal_risk_score * 0.12)
        + (_clamp01(float(raw.s_volume_burst_decay_20)) * 0.05)
    )
    activity_quality_score, activity_quality_label, activity_quality_reason = _score_activity_quality(
        recent_range_mean=float(raw.s_recent_range_mean),
        recent_body_mean=float(raw.s_recent_body_mean),
        volatility_penalty=volatility_penalty,
    )
    level_reliability_score, level_reliability_label, level_reliability_reason = _score_level_reliability(
        sr_level_rank=float(raw.s_sr_level_rank),
        sr_touch_count=float(raw.s_sr_touch_count),
    )
    regime_state_label = _label_regime_state(
        mode,
        float(raw.s_noise),
        float(raw.s_conflict),
        float(raw.s_compression),
        float(raw.s_expansion),
    )
    quality_state_label, quality_composite_score = _label_quality_state(
        noise_damp,
        conflict_damp,
        liquidity_penalty,
        volatility_penalty,
        momentum_quality_score=momentum_quality_score,
        activity_quality_score=activity_quality_score,
        level_reliability_score=level_reliability_score,
    )
    topdown_state_label = _label_topdown_state(float(raw.s_topdown_bias), float(raw.s_topdown_agreement))
    patience_state_label = _label_patience_state(
        wait_patience_gain,
        confirm_aggression_gain,
        hold_patience_gain,
        fast_exit_risk_penalty,
    )
    session_regime_state = _label_session_regime_state(
        float(raw.s_session_box_height_ratio),
        float(raw.s_session_expansion_progress),
        float(raw.s_session_position_bias),
    )
    session_expansion_state = _label_session_expansion_state(
        float(raw.s_session_expansion_progress),
        float(raw.s_session_position_bias),
    )
    session_exhaustion_state = _label_session_exhaustion_state(
        float(raw.s_session_expansion_progress),
        float(raw.s_session_position_bias),
        volatility_penalty,
    )
    topdown_spacing_state = _label_topdown_spacing_state(float(raw.s_topdown_spacing_score))
    topdown_slope_state = _label_topdown_slope_state(
        float(raw.s_topdown_slope_bias),
        float(raw.s_topdown_slope_agreement),
    )
    topdown_confluence_state = _label_topdown_confluence_state(
        float(raw.s_topdown_confluence_bias),
        float(raw.s_topdown_conflict_score),
    )
    spread_stress_state = _label_spread_stress_state(
        float(raw.s_tick_spread_ratio),
        float(raw.s_rate_spread_ratio),
    )
    volume_participation_state = _label_volume_participation_state(
        float(raw.s_tick_volume_ratio),
        float(raw.s_real_volume_ratio),
    )
    execution_friction_state = _label_execution_friction_state(
        tick_spread_ratio=float(raw.s_tick_spread_ratio),
        rate_spread_ratio=float(raw.s_rate_spread_ratio),
        tick_volume_ratio=float(raw.s_tick_volume_ratio),
        real_volume_ratio=float(raw.s_real_volume_ratio),
        liquidity_penalty=liquidity_penalty,
    )
    tick_flow_collector_state = str((raw.metadata or {}).get("tick_flow_state", "INACTIVE") or "INACTIVE").upper()
    order_book_collector_state = str((raw.metadata or {}).get("order_book_state", "INACTIVE") or "INACTIVE").upper()
    event_risk_collector_state = str((raw.metadata or {}).get("event_risk_state", "INACTIVE") or "INACTIVE").upper()
    advanced_input_activation_state = _label_advanced_input_activation_state(
        (raw.metadata or {}).get("advanced_input_activation_state", "INACTIVE")
    )
    tick_flow_state = _label_tick_flow_state(
        float(raw.s_tick_flow_bias),
        float(raw.s_tick_flow_burst),
        collector_state=tick_flow_collector_state,
    )
    order_book_state = _label_order_book_state(
        float(raw.s_order_book_imbalance),
        float(raw.s_order_book_thinness),
        collector_state=order_book_collector_state,
    )
    event_risk_state = _label_event_risk_state(
        float(raw.s_event_risk_score),
        collector_state=event_risk_collector_state,
    )
    tick_flow_available = tick_flow_collector_state not in {"UNAVAILABLE", "DISABLED", "INACTIVE"}
    order_book_available = order_book_collector_state not in {"UNAVAILABLE", "DISABLED", "INACTIVE"}
    event_risk_available = event_risk_collector_state not in {"UNAVAILABLE", "DISABLED", "INACTIVE"}
    tick_flow_stress = (
        _clamp01((abs(float(raw.s_tick_flow_bias)) * 0.62) + (float(raw.s_tick_flow_burst) * 0.38))
        if tick_flow_available
        else 0.0
    )
    order_book_stress = (
        _clamp01((abs(float(raw.s_order_book_imbalance)) * 0.34) + (float(raw.s_order_book_thinness) * 0.66))
        if order_book_available
        else 0.0
    )
    event_risk_stress = float(raw.s_event_risk_score) if event_risk_available else 0.0
    advanced_execution_stress = _clamp01(
        max(
            event_risk_stress,
            tick_flow_stress,
            order_book_stress,
        )
    )
    wait_patience_gain = _clamp(wait_patience_gain + (advanced_execution_stress * 0.08), 0.85, 1.48)
    confirm_aggression_gain = _clamp(confirm_aggression_gain - (advanced_execution_stress * 0.07), 0.72, 1.34)
    hold_patience_gain = _clamp(
        hold_patience_gain - ((event_risk_stress * 0.12) + ((float(raw.s_order_book_thinness) * 0.06) if order_book_available else 0.0)),
        0.70,
        1.38,
    )
    fast_exit_risk_penalty = _clamp01(fast_exit_risk_penalty + (advanced_execution_stress * 0.20))
    patience_state_label = _label_patience_state(
        wait_patience_gain,
        confirm_aggression_gain,
        hold_patience_gain,
        fast_exit_risk_penalty,
    )

    coefficient_reasons = {
        "range_reversal_gain": _describe_regime_reason(mode, "range_reversal_gain", range_reversal_gain),
        "trend_pullback_gain": _describe_regime_reason(mode, "trend_pullback_gain", trend_pullback_gain),
        "breakout_continuation_gain": _describe_regime_reason(
            mode,
            "breakout_continuation_gain",
            breakout_continuation_gain,
        ),
        "noise_damp": f"s_noise={raw.s_noise:.4f} -> noise_damp={noise_damp:.4f}",
        "conflict_damp": (
            "position quality conflict -> "
            f"position_conflict_score={position_conflict_score:.4f}, "
            f"conflict_kind={position_conflict_kind or 'NONE'}, "
            f"raw_conflict_assist={raw_conflict_assist:.4f}, "
            f"conflict_basis={conflict_basis:.4f}, "
            f"conflict_damp={conflict_damp:.4f}"
        ),
        "alignment_gain": (
            "position quality alignment -> "
            f"raw_alignment={raw.s_alignment:.4f}, "
            f"alignment_basis={alignment_basis:.4f}, "
            f"primary_label={position_primary_label or 'NONE'}, "
            f"bias_label={position_bias_label or 'NONE'}, "
            f"alignment_gain={alignment_gain:.4f}"
        ),
        "countertrend_penalty": (
            f"direction_policy={policy} -> countertrend_penalty={countertrend_penalty:.4f}"
        ),
        "liquidity_penalty": (
            f"liquidity_state={liquidity}, spread_ratio={spread_ratio:.4f} "
            f"-> liquidity_penalty={liquidity_penalty:.4f}"
        ),
        "volatility_penalty": (
            f"s_volatility={raw.s_volatility:.4f}, market_mode={mode} "
            f"-> volatility_penalty={volatility_penalty:.4f}"
        ),
        "micro_structure_breakout_readiness": (
            f"compression={raw.s_range_compression_ratio_20:.4f}, burst_ratio={raw.s_volume_burst_ratio_20:.4f}, "
            f"burst_decay={raw.s_volume_burst_decay_20:.4f}, run_current={raw.s_same_color_run_current:.4f}, "
            f"doji_ratio={raw.s_doji_ratio_20:.4f} -> breakout_readiness={micro_breakout_readiness_score:.4f}"
        ),
        "micro_structure_reversal_risk": (
            f"upper_wick={raw.s_upper_wick_ratio_20:.4f}, lower_wick={raw.s_lower_wick_ratio_20:.4f}, "
            f"retest_high={raw.s_swing_high_retest_count_20:.4f}, retest_low={raw.s_swing_low_retest_count_20:.4f}, "
            f"doji_ratio={raw.s_doji_ratio_20:.4f} -> reversal_risk={micro_reversal_risk_score:.4f}"
        ),
        "micro_structure_participation": (
            f"volume_burst_ratio={raw.s_volume_burst_ratio_20:.4f}, volume_burst_decay={raw.s_volume_burst_decay_20:.4f} "
            f"-> participation_score={micro_participation_score:.4f}, participation_state={micro_participation_state}"
        ),
        "micro_structure_gap_context": (
            f"gap_fill_progress={raw.s_gap_fill_progress!r} -> micro_gap_context_state={micro_gap_context_state}"
        ),
        "momentum_quality_detail": momentum_quality_reason,
        "activity_quality_detail": activity_quality_reason,
        "level_reliability_detail": level_reliability_reason,
        "topdown_bull_bias": (
            f"s_topdown_bias={raw.s_topdown_bias:.4f}, s_topdown_agreement={raw.s_topdown_agreement:.4f} "
            f"-> topdown_bull_bias={topdown_bull_bias:.4f}"
        ),
        "topdown_bear_bias": (
            f"s_topdown_bias={raw.s_topdown_bias:.4f}, s_topdown_agreement={raw.s_topdown_agreement:.4f} "
            f"-> topdown_bear_bias={topdown_bear_bias:.4f}"
        ),
        "big_map_alignment_gain": (
            f"s_topdown_agreement={raw.s_topdown_agreement:.4f} "
            f"-> big_map_alignment_gain={big_map_alignment_gain:.4f}"
        ),
        "wait_patience_gain": (
            f"mode={mode}, s_noise={raw.s_noise:.4f}, s_conflict={raw.s_conflict:.4f}, "
            f"s_middle_neutrality={raw.s_middle_neutrality:.4f}, s_compression={raw.s_compression:.4f}, "
            f"s_topdown_agreement={raw.s_topdown_agreement:.4f} -> wait_patience_gain={wait_patience_gain:.4f}"
        ),
        "confirm_aggression_gain": (
            f"mode={mode}, alignment_basis={alignment_basis:.4f}, s_topdown_agreement={raw.s_topdown_agreement:.4f}, "
            f"s_expansion={raw.s_expansion:.4f}, noise={raw.s_noise:.4f}, conflict={raw.s_conflict:.4f} "
            f"-> confirm_aggression_gain={confirm_aggression_gain:.4f}"
        ),
        "hold_patience_gain": (
            f"mode={mode}, structure_quality=max(topdown_agreement, alignment_basis) "
            f"with s_compression={raw.s_compression:.4f}, s_expansion={raw.s_expansion:.4f} "
            f"-> hold_patience_gain={hold_patience_gain:.4f}"
        ),
        "fast_exit_risk_penalty": (
            f"mode={mode}, s_volatility={raw.s_volatility:.4f}, s_noise={raw.s_noise:.4f}, "
            f"liquidity_penalty={liquidity_penalty:.4f}, countertrend_penalty={countertrend_penalty:.4f} "
            f"-> fast_exit_risk_penalty={fast_exit_risk_penalty:.4f}"
        ),
        "session_regime_state": (
            f"s_session_box_height_ratio={raw.s_session_box_height_ratio:.4f}, "
            f"s_session_expansion_progress={raw.s_session_expansion_progress:.4f}, "
            f"s_session_position_bias={raw.s_session_position_bias:.4f} "
            f"-> session_regime_state={session_regime_state}"
        ),
        "session_expansion_state": (
            f"s_session_expansion_progress={raw.s_session_expansion_progress:.4f}, "
            f"s_session_position_bias={raw.s_session_position_bias:.4f} "
            f"-> session_expansion_state={session_expansion_state}"
        ),
        "session_exhaustion_state": (
            f"s_session_expansion_progress={raw.s_session_expansion_progress:.4f}, "
            f"s_session_position_bias={raw.s_session_position_bias:.4f}, "
            f"volatility_penalty={volatility_penalty:.4f} "
            f"-> session_exhaustion_state={session_exhaustion_state}"
        ),
        "topdown_spacing_state": (
            f"s_topdown_spacing_score={raw.s_topdown_spacing_score:.4f} "
            f"-> topdown_spacing_state={topdown_spacing_state}"
        ),
        "topdown_slope_state": (
            f"s_topdown_slope_bias={raw.s_topdown_slope_bias:.4f}, "
            f"s_topdown_slope_agreement={raw.s_topdown_slope_agreement:.4f} "
            f"-> topdown_slope_state={topdown_slope_state}"
        ),
        "topdown_confluence_state": (
            f"s_topdown_confluence_bias={raw.s_topdown_confluence_bias:.4f}, "
            f"s_topdown_conflict_score={raw.s_topdown_conflict_score:.4f} "
            f"-> topdown_confluence_state={topdown_confluence_state}"
        ),
        "spread_stress_state": (
            f"s_tick_spread_ratio={raw.s_tick_spread_ratio:.4f}, "
            f"s_rate_spread_ratio={raw.s_rate_spread_ratio:.4f} "
            f"-> spread_stress_state={spread_stress_state}"
        ),
        "volume_participation_state": (
            f"s_tick_volume_ratio={raw.s_tick_volume_ratio:.4f}, "
            f"s_real_volume_ratio={raw.s_real_volume_ratio:.4f} "
            f"-> volume_participation_state={volume_participation_state}"
        ),
        "execution_friction_state": (
            f"s_tick_spread_ratio={raw.s_tick_spread_ratio:.4f}, "
            f"s_rate_spread_ratio={raw.s_rate_spread_ratio:.4f}, "
            f"s_tick_volume_ratio={raw.s_tick_volume_ratio:.4f}, "
            f"s_real_volume_ratio={raw.s_real_volume_ratio:.4f}, "
            f"liquidity_penalty={liquidity_penalty:.4f} "
            f"-> execution_friction_state={execution_friction_state}"
        ),
        "advanced_input_activation_state": (
            f"advanced_input_activation_state={(raw.metadata or {}).get('advanced_input_activation_state', 'INACTIVE')} "
            f"-> advanced_input_activation_state={advanced_input_activation_state}"
        ),
        "tick_flow_state": (
            f"s_tick_flow_bias={raw.s_tick_flow_bias:.4f}, s_tick_flow_burst={raw.s_tick_flow_burst:.4f} "
            f"-> tick_flow_state={tick_flow_state}"
        ),
        "order_book_state": (
            f"s_order_book_imbalance={raw.s_order_book_imbalance:.4f}, s_order_book_thinness={raw.s_order_book_thinness:.4f} "
            f"-> order_book_state={order_book_state}"
        ),
        "event_risk_state": (
            f"s_event_risk_score={raw.s_event_risk_score:.4f} "
            f"-> event_risk_state={event_risk_state}"
        ),
        "advanced_execution_stress": (
            f"event_risk={raw.s_event_risk_score:.4f}, tick_flow_bias={raw.s_tick_flow_bias:.4f}, "
            f"tick_flow_burst={raw.s_tick_flow_burst:.4f}, order_book_imbalance={raw.s_order_book_imbalance:.4f}, "
            f"order_book_thinness={raw.s_order_book_thinness:.4f} "
            f"-> advanced_execution_stress={advanced_execution_stress:.4f}"
        ),
    }

    return StateVectorV2(
        range_reversal_gain=range_reversal_gain,
        trend_pullback_gain=trend_pullback_gain,
        breakout_continuation_gain=breakout_continuation_gain,
        noise_damp=noise_damp,
        conflict_damp=conflict_damp,
        alignment_gain=alignment_gain,
        topdown_bull_bias=topdown_bull_bias,
        topdown_bear_bias=topdown_bear_bias,
        big_map_alignment_gain=big_map_alignment_gain,
        wait_patience_gain=wait_patience_gain,
        confirm_aggression_gain=confirm_aggression_gain,
        hold_patience_gain=hold_patience_gain,
        fast_exit_risk_penalty=fast_exit_risk_penalty,
        countertrend_penalty=countertrend_penalty,
        liquidity_penalty=liquidity_penalty,
        volatility_penalty=volatility_penalty,
        metadata={
            "state_contract": "canonical_v3",
            "raw_snapshot_contract": "raw_snapshot_v1",
            "raw_snapshot_version": "raw_snapshot_v1",
            "mapper_version": "state_vector_v2_s9",
            "semantic_owner_contract": "state_market_trust_patience_only_v1",
            "semantic_owner_scope": {
                "allowed_domains": [
                    "regime_interpretation",
                    "topdown_bias_interpretation",
                    "market_quality_interpretation",
                    "patience_and_execution_temperament",
                ],
                "forbidden_domains": [
                    "position_location_identity",
                    "response_event_identity",
                    "direct_buy_sell_side_identity",
                    "trigger_event_ownership",
                ],
                "identity_override_allowed": False,
                "position_owner_claim_allowed": False,
                "response_owner_claim_allowed": False,
            },
            "canonical_state_clusters_v1": [
                "regime_state",
                "topdown_state",
                "quality_state",
                "patience_state",
            ],
            "state_freeze_phase": "S0",
            "source_regime": mode,
            "source_direction_policy": policy,
            "source_liquidity": liquidity,
            "source_symbol": str((raw.metadata or {}).get("symbol") or ""),
            "source_price": float((raw.metadata or {}).get("price") or 0.0),
            "source_signal_timeframe": str((raw.metadata or {}).get("signal_timeframe") or ""),
            "source_signal_bar_ts": int((raw.metadata or {}).get("signal_bar_ts") or 0),
            "source_session_state_source": str((raw.metadata or {}).get("session_state_source") or "UNKNOWN"),
            "source_position_in_session_box": str((raw.metadata or {}).get("position_in_session_box") or "UNKNOWN"),
            "source_noise": float(raw.s_noise),
            "source_conflict": float(raw.s_conflict),
            "source_alignment": float(raw.s_alignment),
            "source_disparity": float(raw.s_disparity),
            "source_volatility": float(raw.s_volatility),
            "source_topdown_bias": float(raw.s_topdown_bias),
            "source_topdown_agreement": float(raw.s_topdown_agreement),
            "source_compression": float(raw.s_compression),
            "source_expansion": float(raw.s_expansion),
            "source_middle_neutrality": float(raw.s_middle_neutrality),
            "source_current_rsi": float(raw.s_current_rsi),
            "source_current_adx": float(raw.s_current_adx),
            "source_current_plus_di": float(raw.s_current_plus_di),
            "source_current_minus_di": float(raw.s_current_minus_di),
            "source_recent_range_mean": float(raw.s_recent_range_mean),
            "source_recent_body_mean": float(raw.s_recent_body_mean),
            "source_micro_body_size_pct_20": float(raw.s_body_size_pct_20),
            "source_micro_upper_wick_ratio_20": float(raw.s_upper_wick_ratio_20),
            "source_micro_lower_wick_ratio_20": float(raw.s_lower_wick_ratio_20),
            "source_micro_doji_ratio_20": float(raw.s_doji_ratio_20),
            "source_micro_same_color_run_current": float(raw.s_same_color_run_current),
            "source_micro_same_color_run_max_20": float(raw.s_same_color_run_max_20),
            "source_micro_bull_ratio_20": float(raw.s_bull_ratio_20),
            "source_micro_bear_ratio_20": float(raw.s_bear_ratio_20),
            "source_micro_range_compression_ratio_20": float(raw.s_range_compression_ratio_20),
            "source_micro_volume_burst_ratio_20": float(raw.s_volume_burst_ratio_20),
            "source_micro_volume_burst_decay_20": float(raw.s_volume_burst_decay_20),
            "source_micro_swing_high_retest_count_20": float(raw.s_swing_high_retest_count_20),
            "source_micro_swing_low_retest_count_20": float(raw.s_swing_low_retest_count_20),
            "source_micro_gap_fill_progress": raw.s_gap_fill_progress,
            "source_sr_level_rank": float(raw.s_sr_level_rank),
            "source_sr_touch_count": float(raw.s_sr_touch_count),
            "source_session_box_height_ratio": float(raw.s_session_box_height_ratio),
            "source_session_expansion_progress": float(raw.s_session_expansion_progress),
            "source_session_position_bias": float(raw.s_session_position_bias),
            "source_topdown_spacing_score": float(raw.s_topdown_spacing_score),
            "source_topdown_slope_bias": float(raw.s_topdown_slope_bias),
            "source_topdown_slope_agreement": float(raw.s_topdown_slope_agreement),
            "source_topdown_confluence_bias": float(raw.s_topdown_confluence_bias),
            "source_topdown_conflict_score": float(raw.s_topdown_conflict_score),
            "source_tick_spread_ratio": float(raw.s_tick_spread_ratio),
            "source_rate_spread_ratio": float(raw.s_rate_spread_ratio),
            "source_tick_volume_ratio": float(raw.s_tick_volume_ratio),
            "source_real_volume_ratio": float(raw.s_real_volume_ratio),
            "source_tick_flow_bias": float(raw.s_tick_flow_bias),
            "source_tick_flow_burst": float(raw.s_tick_flow_burst),
            "source_order_book_imbalance": float(raw.s_order_book_imbalance),
            "source_order_book_thinness": float(raw.s_order_book_thinness),
            "source_event_risk_score": float(raw.s_event_risk_score),
            "source_spread_ratio": spread_ratio,
            "position_primary_label": position_primary_label,
            "position_bias_label": position_bias_label,
            "position_conflict_kind": position_conflict_kind,
            "position_secondary_context_label": position_secondary_context_label,
            "position_conflict_score": position_conflict_score,
            "regime_state_label": regime_state_label,
            "micro_breakout_readiness_score": micro_breakout_readiness_score,
            "micro_reversal_risk_score": micro_reversal_risk_score,
            "micro_participation_score": micro_participation_score,
            "micro_breakout_readiness_state": micro_breakout_readiness_state,
            "micro_reversal_risk_state": micro_reversal_risk_state,
            "micro_participation_state": micro_participation_state,
            "micro_gap_context_state": micro_gap_context_state,
            "micro_structure_detail_v1": {
                "data_state": str((raw.metadata or {}).get("micro_structure_data_state", "MISSING") or "MISSING"),
                "anchor_state": str((raw.metadata or {}).get("micro_structure_anchor_state", "MISSING") or "MISSING"),
                "volume_source": str((raw.metadata or {}).get("micro_structure_volume_source", "") or ""),
                "lookback_bars": int((raw.metadata or {}).get("micro_structure_lookback_bars", 0) or 0),
                "window_size": int((raw.metadata or {}).get("micro_structure_window_size", 0) or 0),
            },
            "quality_state_label": quality_state_label,
            "quality_composite_score": quality_composite_score,
            "quality_state_detail_v1": {
                "momentum_quality_score": momentum_quality_score,
                "momentum_quality_label": momentum_quality_label,
                "activity_quality_score": activity_quality_score,
                "activity_quality_label": activity_quality_label,
                "level_reliability_score": level_reliability_score,
                "level_reliability_label": level_reliability_label,
            },
            "topdown_state_label": topdown_state_label,
            "topdown_spacing_state": topdown_spacing_state,
            "topdown_slope_state": topdown_slope_state,
            "topdown_confluence_state": topdown_confluence_state,
            "spread_stress_state": spread_stress_state,
            "volume_participation_state": volume_participation_state,
            "execution_friction_state": execution_friction_state,
            "advanced_input_activation_state": advanced_input_activation_state,
            "tick_flow_state": tick_flow_state,
            "order_book_state": order_book_state,
            "event_risk_state": event_risk_state,
            "advanced_input_detail_v1": {
                "advanced_execution_stress": advanced_execution_stress,
                "activation_reasons": list((raw.metadata or {}).get("advanced_input_activation_reasons", []) or []),
                "tick_sample_size": int((raw.metadata or {}).get("tick_sample_size", 0) or 0),
                "order_book_levels": int((raw.metadata or {}).get("order_book_levels", 0) or 0),
                "event_risk_match_count": int((raw.metadata or {}).get("event_risk_match_count", 0) or 0),
            },
            "patience_state_label": patience_state_label,
            "session_regime_state": session_regime_state,
            "session_expansion_state": session_expansion_state,
            "session_exhaustion_state": session_exhaustion_state,
            "position_quality_usage": {
                "alignment_gain": ["position_primary_label", "position_bias_label"],
                "conflict_damp": ["position_conflict_score", "position_conflict_kind"],
                "direction_source_used": False,
            },
            "raw_conflict_assist": raw_conflict_assist,
            "conflict_basis": conflict_basis,
            "coefficient_reasons": coefficient_reasons,
        },
    )
