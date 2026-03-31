from __future__ import annotations

from backend.trading.engine.core.models import EngineContext, ResponseRawSnapshot, ResponseVector, ResponseVectorV2
from backend.trading.engine.response.band_response import compute_band_responses
from backend.trading.engine.response.candle_response import compute_candle_responses
from backend.trading.engine.response.context_gate import compute_response_context_gate
from backend.trading.engine.response.micro_response import compute_micro_responses
from backend.trading.engine.response.pattern_response import compute_pattern_responses
from backend.trading.engine.response.sr_response import compute_sr_responses
from backend.trading.engine.response.structure_response import compute_structure_responses
from backend.trading.engine.response.structure_motif import compute_structure_motifs
from backend.trading.engine.response.trendline_response import compute_trendline_responses
from backend.trading.engine.response.transition_vector import build_response_vector_v2 as _build_response_vector_v2


def build_response_raw_snapshot(ctx: EngineContext) -> ResponseRawSnapshot:
    band = compute_band_responses(ctx)
    candle = compute_candle_responses(ctx)
    pattern = compute_pattern_responses(ctx)
    structure_motif = compute_structure_motifs(pattern)
    structure = compute_structure_responses(ctx)
    sr = compute_sr_responses(ctx)
    trendline = compute_trendline_responses(ctx)
    micro = compute_micro_responses(ctx)
    context_gate = compute_response_context_gate(
        ctx,
        candle_motif=dict(candle.get("candle_motif_v1", {}) or {}),
        structure_motif=structure_motif,
        sr_subsystem=dict(sr.get("sr_subsystem_v1", {}) or {}),
        trendline_subsystem=dict(trendline.get("trendline_subsystem_v1", {}) or {}),
        micro_subsystem=dict(micro.get("micro_tf_subsystem_v1", {}) or {}),
    )
    return ResponseRawSnapshot(
        bb20_lower_hold=float(band["r_bb20_lower_hold"]),
        bb20_lower_break=float(band["r_bb20_lower_break"]),
        bb20_mid_hold=float(band["r_bb20_mid_hold"]),
        bb20_mid_reclaim=float(band["r_bb20_mid_reclaim"]),
        bb20_mid_reject=float(band["r_bb20_mid_reject"]),
        bb20_mid_lose=float(band["r_bb20_mid_lose"]),
        bb20_upper_reject=float(band["r_bb20_upper_reject"]),
        bb20_upper_break=float(band["r_bb20_upper_break"]),
        bb44_lower_hold=float(band["r_bb44_lower_hold"]),
        bb44_upper_reject=float(band["r_bb44_upper_reject"]),
        box_lower_bounce=float(structure["r_box_lower_bounce"]),
        box_lower_break=float(structure["r_box_lower_break"]),
        box_mid_hold=float(structure["r_box_mid_hold"]),
        box_mid_reject=float(structure["r_box_mid_reject"]),
        box_upper_reject=float(structure["r_box_upper_reject"]),
        box_upper_break=float(structure["r_box_upper_break"]),
        candle_lower_reject=float(candle["r_candle_lower_reject"]),
        candle_upper_reject=float(candle["r_candle_upper_reject"]),
        pattern_double_bottom=float(pattern["pattern_double_bottom"]),
        pattern_inverse_head_shoulders=float(pattern["pattern_inverse_head_shoulders"]),
        pattern_double_top=float(pattern["pattern_double_top"]),
        pattern_head_shoulders=float(pattern["pattern_head_shoulders"]),
        sr_support_touch=float(sr["r_sr_support_touch"]),
        sr_support_hold=float(sr["r_sr_support_hold"]),
        sr_support_reclaim=float(sr["r_sr_support_reclaim"]),
        sr_support_break=float(sr["r_sr_support_break"]),
        sr_resistance_touch=float(sr["r_sr_resistance_touch"]),
        sr_resistance_reject=float(sr["r_sr_resistance_reject"]),
        sr_resistance_reclaim=float(sr["r_sr_resistance_reclaim"]),
        sr_resistance_break=float(sr["r_sr_resistance_break"]),
        trend_support_touch_m1=float(trendline["r_trend_support_touch_m1"]),
        trend_support_hold_m1=float(trendline["r_trend_support_hold_m1"]),
        trend_support_break_m1=float(trendline["r_trend_support_break_m1"]),
        trend_resistance_touch_m1=float(trendline["r_trend_resistance_touch_m1"]),
        trend_resistance_reject_m1=float(trendline["r_trend_resistance_reject_m1"]),
        trend_resistance_break_m1=float(trendline["r_trend_resistance_break_m1"]),
        trend_support_touch_m15=float(trendline["r_trend_support_touch_m15"]),
        trend_support_hold_m15=float(trendline["r_trend_support_hold_m15"]),
        trend_support_break_m15=float(trendline["r_trend_support_break_m15"]),
        trend_resistance_touch_m15=float(trendline["r_trend_resistance_touch_m15"]),
        trend_resistance_reject_m15=float(trendline["r_trend_resistance_reject_m15"]),
        trend_resistance_break_m15=float(trendline["r_trend_resistance_break_m15"]),
        trend_support_touch_h1=float(trendline["r_trend_support_touch_h1"]),
        trend_support_hold_h1=float(trendline["r_trend_support_hold_h1"]),
        trend_support_break_h1=float(trendline["r_trend_support_break_h1"]),
        trend_resistance_touch_h1=float(trendline["r_trend_resistance_touch_h1"]),
        trend_resistance_reject_h1=float(trendline["r_trend_resistance_reject_h1"]),
        trend_resistance_break_h1=float(trendline["r_trend_resistance_break_h1"]),
        trend_support_touch_h4=float(trendline["r_trend_support_touch_h4"]),
        trend_support_hold_h4=float(trendline["r_trend_support_hold_h4"]),
        trend_support_break_h4=float(trendline["r_trend_support_break_h4"]),
        trend_resistance_touch_h4=float(trendline["r_trend_resistance_touch_h4"]),
        trend_resistance_reject_h4=float(trendline["r_trend_resistance_reject_h4"]),
        trend_resistance_break_h4=float(trendline["r_trend_resistance_break_h4"]),
        micro_bull_reject=float(micro["r_micro_bull_reject"]),
        micro_bear_reject=float(micro["r_micro_bear_reject"]),
        micro_bull_break=float(micro["r_micro_bull_break"]),
        micro_bear_break=float(micro["r_micro_bear_break"]),
        micro_indecision=float(micro["r_micro_indecision"]),
        metadata={
            "response_contract": "raw_snapshot_v1",
            "candle_descriptor_v1": dict(candle.get("candle_descriptor_v1", {}) or {}),
            "candle_pattern_v1": dict(candle.get("candle_pattern_v1", {}) or {}),
            "candle_motif_v1": dict(candle.get("candle_motif_v1", {}) or {}),
            "structure_motif_v1": dict(structure_motif or {}),
            "sr_subsystem_v1": dict(sr.get("sr_subsystem_v1", {}) or {}),
            "trendline_subsystem_v1": dict(trendline.get("trendline_subsystem_v1", {}) or {}),
            "micro_tf_subsystem_v1": dict(micro.get("micro_tf_subsystem_v1", {}) or {}),
            "response_context_gate_v1": dict(context_gate or {}),
            "market_mode": ctx.market_mode,
            "direction_policy": ctx.direction_policy,
            "box_state": ctx.box_state,
            "bb_state": ctx.bb_state,
            "fired_candle_patterns": list((candle.get("candle_pattern_v1", {}) or {}).get("fired_patterns", []) or []),
            "fired_candle_motifs": list((candle.get("candle_motif_v1", {}) or {}).get("fired_motifs", []) or []),
            "fired_structure_motifs": list((structure_motif or {}).get("fired_motifs", []) or []),
            "fired_sr_signals": list((sr.get("sr_subsystem_v1", {}) or {}).get("fired_signals", []) or []),
            "fired_sr_strengths": list((sr.get("sr_subsystem_v1", {}) or {}).get("fired_strengths", []) or []),
            "fired_trendline_signals": list((trendline.get("trendline_subsystem_v1", {}) or {}).get("fired_signals", []) or []),
            "fired_trendline_strengths": list((trendline.get("trendline_subsystem_v1", {}) or {}).get("fired_strengths", []) or []),
            "fired_micro_strengths": list((micro.get("micro_tf_subsystem_v1", {}) or {}).get("fired_strengths", []) or []),
            "fired_context_gate_candidates": list((context_gate or {}).get("fired_candidates", []) or []),
            "fired_patterns": [
                name
                for name, value in pattern.items()
                if float(value) > 0.0
            ],
        },
    )


def build_response_vector_from_raw(raw: ResponseRawSnapshot) -> ResponseVector:
    return ResponseVector(
        r_bb20_lower_hold=float(raw.bb20_lower_hold),
        r_bb20_lower_break=float(raw.bb20_lower_break),
        r_bb20_mid_hold=float(raw.bb20_mid_hold),
        r_bb20_mid_reclaim=float(raw.bb20_mid_reclaim),
        r_bb20_mid_reject=float(raw.bb20_mid_reject),
        r_bb20_mid_lose=float(raw.bb20_mid_lose),
        r_bb20_upper_reject=float(raw.bb20_upper_reject),
        r_bb20_upper_break=float(raw.bb20_upper_break),
        r_bb44_lower_hold=float(raw.bb44_lower_hold),
        r_bb44_upper_reject=float(raw.bb44_upper_reject),
        r_box_lower_bounce=float(raw.box_lower_bounce),
        r_box_lower_break=float(raw.box_lower_break),
        r_box_mid_hold=float(raw.box_mid_hold),
        r_box_mid_reject=float(raw.box_mid_reject),
        r_box_upper_reject=float(raw.box_upper_reject),
        r_box_upper_break=float(raw.box_upper_break),
        r_candle_lower_reject=float(raw.candle_lower_reject),
        r_candle_upper_reject=float(raw.candle_upper_reject),
        r_sr_support_touch=float(raw.sr_support_touch),
        r_sr_support_hold=float(raw.sr_support_hold),
        r_sr_support_reclaim=float(raw.sr_support_reclaim),
        r_sr_support_break=float(raw.sr_support_break),
        r_sr_resistance_touch=float(raw.sr_resistance_touch),
        r_sr_resistance_reject=float(raw.sr_resistance_reject),
        r_sr_resistance_reclaim=float(raw.sr_resistance_reclaim),
        r_sr_resistance_break=float(raw.sr_resistance_break),
        r_trend_support_touch_m1=float(raw.trend_support_touch_m1),
        r_trend_support_hold_m1=float(raw.trend_support_hold_m1),
        r_trend_support_break_m1=float(raw.trend_support_break_m1),
        r_trend_resistance_touch_m1=float(raw.trend_resistance_touch_m1),
        r_trend_resistance_reject_m1=float(raw.trend_resistance_reject_m1),
        r_trend_resistance_break_m1=float(raw.trend_resistance_break_m1),
        r_trend_support_touch_m15=float(raw.trend_support_touch_m15),
        r_trend_support_hold_m15=float(raw.trend_support_hold_m15),
        r_trend_support_break_m15=float(raw.trend_support_break_m15),
        r_trend_resistance_touch_m15=float(raw.trend_resistance_touch_m15),
        r_trend_resistance_reject_m15=float(raw.trend_resistance_reject_m15),
        r_trend_resistance_break_m15=float(raw.trend_resistance_break_m15),
        r_trend_support_touch_h1=float(raw.trend_support_touch_h1),
        r_trend_support_hold_h1=float(raw.trend_support_hold_h1),
        r_trend_support_break_h1=float(raw.trend_support_break_h1),
        r_trend_resistance_touch_h1=float(raw.trend_resistance_touch_h1),
        r_trend_resistance_reject_h1=float(raw.trend_resistance_reject_h1),
        r_trend_resistance_break_h1=float(raw.trend_resistance_break_h1),
        r_trend_support_touch_h4=float(raw.trend_support_touch_h4),
        r_trend_support_hold_h4=float(raw.trend_support_hold_h4),
        r_trend_support_break_h4=float(raw.trend_support_break_h4),
        r_trend_resistance_touch_h4=float(raw.trend_resistance_touch_h4),
        r_trend_resistance_reject_h4=float(raw.trend_resistance_reject_h4),
        r_trend_resistance_break_h4=float(raw.trend_resistance_break_h4),
        r_micro_bull_reject=float(raw.micro_bull_reject),
        r_micro_bear_reject=float(raw.micro_bear_reject),
        r_micro_bull_break=float(raw.micro_bull_break),
        r_micro_bear_break=float(raw.micro_bear_break),
        r_micro_indecision=float(raw.micro_indecision),
        metadata={
            **dict(raw.metadata or {}),
            "response_contract": "legacy_vector_v1",
            "raw_snapshot_contract": "raw_snapshot_v1",
        },
    )


def build_response_vector_execution_bridge_from_raw(raw: ResponseRawSnapshot) -> ResponseVector:
    legacy = build_response_vector_from_raw(raw)
    canonical = build_response_vector_v2_from_raw(raw)

    lower_hold = float(canonical.lower_hold_up)
    lower_break = float(canonical.lower_break_down)
    mid_reclaim = float(canonical.mid_reclaim_up)
    mid_lose = float(canonical.mid_lose_down)
    upper_reject = float(canonical.upper_reject_down)
    upper_break = float(canonical.upper_break_up)

    def _scaled(value: float, scale: float) -> float:
        return max(0.0, min(1.0, float(value) * float(scale)))

    return ResponseVector(
        r_bb20_lower_hold=lower_hold,
        r_bb20_lower_break=lower_break,
        r_bb20_mid_hold=_scaled(mid_reclaim, 0.60),
        r_bb20_mid_reclaim=mid_reclaim,
        r_bb20_mid_reject=_scaled(mid_lose, 0.60),
        r_bb20_mid_lose=mid_lose,
        r_bb20_upper_reject=upper_reject,
        r_bb20_upper_break=upper_break,
        r_bb44_lower_hold=_scaled(lower_hold, 0.30),
        r_bb44_upper_reject=_scaled(upper_reject, 0.30),
        r_box_lower_bounce=_scaled(lower_hold, 0.55),
        r_box_lower_break=_scaled(lower_break, 0.60),
        r_box_mid_hold=_scaled(mid_reclaim, 0.55),
        r_box_mid_reject=_scaled(mid_lose, 0.55),
        r_box_upper_reject=_scaled(upper_reject, 0.55),
        r_box_upper_break=_scaled(upper_break, 0.60),
        r_candle_lower_reject=_scaled(lower_hold, 0.35),
        r_candle_upper_reject=_scaled(upper_reject, 0.35),
        r_sr_support_touch=float(legacy.r_sr_support_touch),
        r_sr_support_hold=float(legacy.r_sr_support_hold),
        r_sr_support_reclaim=float(legacy.r_sr_support_reclaim),
        r_sr_support_break=float(legacy.r_sr_support_break),
        r_sr_resistance_touch=float(legacy.r_sr_resistance_touch),
        r_sr_resistance_reject=float(legacy.r_sr_resistance_reject),
        r_sr_resistance_reclaim=float(legacy.r_sr_resistance_reclaim),
        r_sr_resistance_break=float(legacy.r_sr_resistance_break),
        r_trend_support_touch_m1=float(legacy.r_trend_support_touch_m1),
        r_trend_support_hold_m1=float(legacy.r_trend_support_hold_m1),
        r_trend_support_break_m1=float(legacy.r_trend_support_break_m1),
        r_trend_resistance_touch_m1=float(legacy.r_trend_resistance_touch_m1),
        r_trend_resistance_reject_m1=float(legacy.r_trend_resistance_reject_m1),
        r_trend_resistance_break_m1=float(legacy.r_trend_resistance_break_m1),
        r_trend_support_touch_m15=float(legacy.r_trend_support_touch_m15),
        r_trend_support_hold_m15=float(legacy.r_trend_support_hold_m15),
        r_trend_support_break_m15=float(legacy.r_trend_support_break_m15),
        r_trend_resistance_touch_m15=float(legacy.r_trend_resistance_touch_m15),
        r_trend_resistance_reject_m15=float(legacy.r_trend_resistance_reject_m15),
        r_trend_resistance_break_m15=float(legacy.r_trend_resistance_break_m15),
        r_trend_support_touch_h1=float(legacy.r_trend_support_touch_h1),
        r_trend_support_hold_h1=float(legacy.r_trend_support_hold_h1),
        r_trend_support_break_h1=float(legacy.r_trend_support_break_h1),
        r_trend_resistance_touch_h1=float(legacy.r_trend_resistance_touch_h1),
        r_trend_resistance_reject_h1=float(legacy.r_trend_resistance_reject_h1),
        r_trend_resistance_break_h1=float(legacy.r_trend_resistance_break_h1),
        r_trend_support_touch_h4=float(legacy.r_trend_support_touch_h4),
        r_trend_support_hold_h4=float(legacy.r_trend_support_hold_h4),
        r_trend_support_break_h4=float(legacy.r_trend_support_break_h4),
        r_trend_resistance_touch_h4=float(legacy.r_trend_resistance_touch_h4),
        r_trend_resistance_reject_h4=float(legacy.r_trend_resistance_reject_h4),
        r_trend_resistance_break_h4=float(legacy.r_trend_resistance_break_h4),
        r_micro_bull_reject=float(legacy.r_micro_bull_reject),
        r_micro_bear_reject=float(legacy.r_micro_bear_reject),
        r_micro_bull_break=float(legacy.r_micro_bull_break),
        r_micro_bear_break=float(legacy.r_micro_bear_break),
        r_micro_indecision=float(legacy.r_micro_indecision),
        metadata={
            **dict(legacy.metadata or {}),
            "response_contract": "execution_bridge_v1",
            "raw_snapshot_contract": "raw_snapshot_v1",
            "canonical_response_field": "response_vector_v2",
            "bridge_role": "observe_confirm_energy_legacy_adapter",
            "bridge_strategy": "canonical_axes_primary_core_fields_only",
            "canonical_axes_v2": canonical.to_dict(),
            "execution_bridge_core_v1": {
                "lower_hold_up": lower_hold,
                "lower_break_down": lower_break,
                "mid_reclaim_up": mid_reclaim,
                "mid_lose_down": mid_lose,
                "upper_reject_down": upper_reject,
                "upper_break_up": upper_break,
            },
        },
    )


def build_response_vector(ctx: EngineContext) -> ResponseVector:
    raw = build_response_raw_snapshot(ctx)
    return build_response_vector_from_raw(raw)


def build_response_vector_v2_from_raw(raw: ResponseRawSnapshot) -> ResponseVectorV2:
    return _build_response_vector_v2(raw)


def build_response_vector_v2(ctx: EngineContext) -> ResponseVectorV2:
    raw = build_response_raw_snapshot(ctx)
    return build_response_vector_v2_from_raw(raw)
