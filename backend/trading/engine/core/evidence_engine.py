from __future__ import annotations

from backend.trading.engine.core.models import (
    EvidenceVector,
    PositionSnapshot,
    ResponseVectorV2,
    StateVectorV2,
)

_TOTAL_SUPPORT_WEIGHT = 0.35
_FIT_CONFLICT_DAMP_WEIGHT = 0.25
_POSITION_AUTHORITY_ABSOLUTE_WEIGHT = 0.75
_POSITION_AUTHORITY_RELATIVE_WEIGHT = 0.25
_POSITION_SUPPORTIVE_NEUTRAL_FLOOR = 0.58
_POSITION_NEUTRAL_CONTEXT_FLOOR = 0.45
_POSITION_OPPOSING_NEUTRAL_FLOOR = 0.22

_LOWER_ALIGNMENT_FIT = {
    "ALIGNED_LOWER_STRONG": 1.00,
    "ALIGNED_LOWER_WEAK": 0.92,
}
_UPPER_ALIGNMENT_FIT = {
    "ALIGNED_UPPER_STRONG": 1.00,
    "ALIGNED_UPPER_WEAK": 0.92,
}
_LOWER_BIAS_FIT = {
    "LOWER_BIAS": 0.86,
    "MIDDLE_LOWER_BIAS": 0.80,
}
_UPPER_BIAS_FIT = {
    "UPPER_BIAS": 0.86,
    "MIDDLE_UPPER_BIAS": 0.80,
}
_LOWER_CONTINUATION_BIAS_FIT = {
    "LOWER_BIAS": 0.88,
    "MIDDLE_LOWER_BIAS": 0.82,
}
_UPPER_CONTINUATION_BIAS_FIT = {
    "UPPER_BIAS": 0.88,
    "MIDDLE_UPPER_BIAS": 0.82,
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _capped_dominant_merge(first: float, second: float) -> tuple[float, float, float]:
    dominant = max(float(first), float(second))
    support = min(float(first), float(second))
    total = dominant + (_TOTAL_SUPPORT_WEIGHT * support)
    return total, dominant, support


def _policy_multiplier(side: str, state: StateVectorV2) -> tuple[float, str]:
    policy = str((state.metadata or {}).get("source_direction_policy") or "").upper()
    penalty = _clamp01(state.countertrend_penalty)

    if side == "BUY" and policy == "SELL_ONLY":
        return 1.0 - penalty, "countertrend_buy_penalty"
    if side == "SELL" and policy == "BUY_ONLY":
        return 1.0 - penalty, "countertrend_sell_penalty"
    return 1.0, "direction_policy_neutral"


def _shared_quality_multiplier(state: StateVectorV2) -> float:
    liquidity_mult = max(0.15, 1.0 - _clamp01(state.liquidity_penalty))
    volatility_mult = max(0.15, 1.0 - _clamp01(state.volatility_penalty))
    return (
        float(state.alignment_gain)
        * float(getattr(state, "big_map_alignment_gain", 1.0))
        * _clamp01(state.noise_damp)
        * _clamp01(state.conflict_damp)
        * liquidity_mult
        * volatility_mult
    )


def _topdown_multiplier(side: str, state: StateVectorV2) -> tuple[float, str]:
    bull_bias = _clamp01(float(getattr(state, "topdown_bull_bias", 0.0)))
    bear_bias = _clamp01(float(getattr(state, "topdown_bear_bias", 0.0)))
    if side == "BUY":
        multiplier = 1.0 + (bull_bias * 0.18) - (bear_bias * 0.10)
        return max(0.75, float(multiplier)), "topdown_buy_bias_adjustment"
    multiplier = 1.0 + (bear_bias * 0.18) - (bull_bias * 0.10)
    return max(0.75, float(multiplier)), "topdown_sell_bias_adjustment"


def _position_expected_side(archetype: str) -> str:
    if archetype in {"buy_reversal", "sell_continuation"}:
        return "LOWER"
    return "UPPER"


def _position_authority_snapshot(position_snapshot: PositionSnapshot, *, archetype: str) -> dict:
    interpretation = position_snapshot.interpretation
    energy = position_snapshot.energy
    expected_side = _position_expected_side(archetype)
    secondary_context = str(interpretation.secondary_context_label or "")

    if expected_side == "LOWER":
        support_force = float(energy.lower_position_force or 0.0)
        opposing_force = float(energy.upper_position_force or 0.0)
        supportive_context = secondary_context == "LOWER_CONTEXT"
        neutral_context = secondary_context in {"NEUTRAL_CONTEXT", "MIXED_CONTEXT"}
    else:
        support_force = float(energy.upper_position_force or 0.0)
        opposing_force = float(energy.lower_position_force or 0.0)
        supportive_context = secondary_context == "UPPER_CONTEXT"
        neutral_context = secondary_context in {"NEUTRAL_CONTEXT", "MIXED_CONTEXT"}

    total_force = max(0.0, support_force + opposing_force)
    relative_support = float(support_force / total_force) if total_force > 1e-9 else 0.0
    absolute_support = _clamp01(support_force)
    center_release = max(0.0, 1.0 - _clamp01(float(energy.middle_neutrality or 0.0)))
    authority = _clamp01(
        (
            (_POSITION_AUTHORITY_ABSOLUTE_WEIGHT * absolute_support)
            + (_POSITION_AUTHORITY_RELATIVE_WEIGHT * relative_support)
        )
        * center_release
    )
    if supportive_context:
        neutral_floor = _POSITION_SUPPORTIVE_NEUTRAL_FLOOR
        neutral_floor_reason = "supportive_secondary_context_floor"
    elif neutral_context:
        neutral_floor = _POSITION_NEUTRAL_CONTEXT_FLOOR
        neutral_floor_reason = "neutral_secondary_context_floor"
    else:
        neutral_floor = _POSITION_OPPOSING_NEUTRAL_FLOOR
        neutral_floor_reason = "opposing_secondary_context_floor"

    location_role = "edge_anchor" if authority >= 0.65 else "middle_handoff" if authority <= 0.40 else "shared_authority"
    return {
        "expected_side": expected_side,
        "support_force": float(support_force),
        "opposing_force": float(opposing_force),
        "relative_support": float(relative_support),
        "absolute_support": float(absolute_support),
        "middle_neutrality": float(energy.middle_neutrality or 0.0),
        "center_release": float(center_release),
        "position_authority": float(authority),
        "neutral_floor": float(neutral_floor),
        "neutral_floor_reason": neutral_floor_reason,
        "location_role": location_role,
        "secondary_context_label": secondary_context,
    }


def _position_fit(position_snapshot: PositionSnapshot, *, archetype: str) -> tuple[float, dict]:
    interpretation = position_snapshot.interpretation
    energy = position_snapshot.energy

    primary_label = str(interpretation.primary_label or "")
    bias_label = str(interpretation.bias_label or "")
    secondary_context = str(interpretation.secondary_context_label or "")
    conflict_score = float(energy.position_conflict_score or 0.0)

    if archetype == "buy_reversal":
        if primary_label in _LOWER_ALIGNMENT_FIT:
            base = _LOWER_ALIGNMENT_FIT[primary_label]
            reason = f"{primary_label} supports lower reversal"
        elif bias_label in _LOWER_BIAS_FIT or primary_label in _LOWER_BIAS_FIT:
            label = bias_label if bias_label in _LOWER_BIAS_FIT else primary_label
            base = _LOWER_BIAS_FIT[label]
            reason = f"{label} supports lower reversal bias"
        elif primary_label == "ALIGNED_MIDDLE" and secondary_context == "LOWER_CONTEXT":
            base = 0.72
            reason = "aligned middle with lower context"
        elif primary_label == "UNRESOLVED_POSITION" and secondary_context == "LOWER_CONTEXT":
            base = 0.62
            reason = "unresolved position with lower context"
        elif primary_label in _UPPER_ALIGNMENT_FIT or primary_label in _UPPER_BIAS_FIT:
            base = 0.14
            reason = "upper-side location opposes lower reversal"
        else:
            base = 0.30 if secondary_context == "LOWER_CONTEXT" else 0.22
            reason = "weak lower reversal fit"
    elif archetype == "sell_reversal":
        if primary_label in _UPPER_ALIGNMENT_FIT:
            base = _UPPER_ALIGNMENT_FIT[primary_label]
            reason = f"{primary_label} supports upper reversal"
        elif bias_label in _UPPER_BIAS_FIT or primary_label in _UPPER_BIAS_FIT:
            label = bias_label if bias_label in _UPPER_BIAS_FIT else primary_label
            base = _UPPER_BIAS_FIT[label]
            reason = f"{label} supports upper reversal bias"
        elif primary_label == "ALIGNED_MIDDLE" and secondary_context == "UPPER_CONTEXT":
            base = 0.72
            reason = "aligned middle with upper context"
        elif primary_label == "UNRESOLVED_POSITION" and secondary_context == "UPPER_CONTEXT":
            base = 0.62
            reason = "unresolved position with upper context"
        elif primary_label in _LOWER_ALIGNMENT_FIT or primary_label in _LOWER_BIAS_FIT:
            base = 0.14
            reason = "lower-side location opposes upper reversal"
        else:
            base = 0.30 if secondary_context == "UPPER_CONTEXT" else 0.22
            reason = "weak upper reversal fit"
    elif archetype == "buy_continuation":
        if primary_label in _UPPER_ALIGNMENT_FIT:
            base = _UPPER_ALIGNMENT_FIT[primary_label]
            reason = f"{primary_label} supports upper continuation"
        elif bias_label in _UPPER_CONTINUATION_BIAS_FIT or primary_label in _UPPER_CONTINUATION_BIAS_FIT:
            label = bias_label if bias_label in _UPPER_CONTINUATION_BIAS_FIT else primary_label
            base = _UPPER_CONTINUATION_BIAS_FIT[label]
            reason = f"{label} supports upper continuation bias"
        elif primary_label == "ALIGNED_MIDDLE" and secondary_context == "UPPER_CONTEXT":
            base = 0.78
            reason = "aligned middle with upper continuation context"
        elif primary_label == "UNRESOLVED_POSITION" and secondary_context == "UPPER_CONTEXT":
            base = 0.66
            reason = "unresolved position with upper continuation context"
        elif primary_label in _LOWER_ALIGNMENT_FIT or primary_label in _LOWER_CONTINUATION_BIAS_FIT:
            base = 0.12
            reason = "lower-side location opposes upper continuation"
        else:
            base = 0.32 if secondary_context == "UPPER_CONTEXT" else 0.24
            reason = "weak upper continuation fit"
    else:
        if primary_label in _LOWER_ALIGNMENT_FIT:
            base = _LOWER_ALIGNMENT_FIT[primary_label]
            reason = f"{primary_label} supports lower continuation"
        elif bias_label in _LOWER_CONTINUATION_BIAS_FIT or primary_label in _LOWER_CONTINUATION_BIAS_FIT:
            label = bias_label if bias_label in _LOWER_CONTINUATION_BIAS_FIT else primary_label
            base = _LOWER_CONTINUATION_BIAS_FIT[label]
            reason = f"{label} supports lower continuation bias"
        elif primary_label == "ALIGNED_MIDDLE" and secondary_context == "LOWER_CONTEXT":
            base = 0.78
            reason = "aligned middle with lower continuation context"
        elif primary_label == "UNRESOLVED_POSITION" and secondary_context == "LOWER_CONTEXT":
            base = 0.66
            reason = "unresolved position with lower continuation context"
        elif primary_label in _UPPER_ALIGNMENT_FIT or primary_label in _UPPER_CONTINUATION_BIAS_FIT:
            base = 0.12
            reason = "upper-side location opposes lower continuation"
        else:
            base = 0.32 if secondary_context == "LOWER_CONTEXT" else 0.24
            reason = "weak lower continuation fit"

    authority = _position_authority_snapshot(position_snapshot, archetype=archetype)
    neutral_floor = float(authority["neutral_floor"])
    position_authority = float(authority["position_authority"])
    fit_before_conflict = neutral_floor + (position_authority * (float(base) - neutral_floor))
    conflict_scale = max(0.55, 1.0 - (conflict_score * _FIT_CONFLICT_DAMP_WEIGHT))
    fit = _clamp01(fit_before_conflict * conflict_scale)
    return fit, {
        "base_fit": float(base),
        "fit_before_conflict": float(fit_before_conflict),
        "conflict_scale": float(conflict_scale),
        "fit": float(fit),
        "reason": reason,
        "primary_label": primary_label,
        "bias_label": bias_label,
        "secondary_context_label": secondary_context,
        "position_conflict_score": float(conflict_score),
        "position_authority": authority,
    }


def build_evidence_vector(
    position_snapshot: PositionSnapshot,
    response_vector_v2: ResponseVectorV2,
    state_vector_v2: StateVectorV2,
) -> EvidenceVector:
    shared_quality = _shared_quality_multiplier(state_vector_v2)
    reversal_multiplier = shared_quality * float(state_vector_v2.range_reversal_gain)
    continuation_multiplier = (
        shared_quality
        * float(state_vector_v2.trend_pullback_gain)
        * float(state_vector_v2.breakout_continuation_gain)
    )

    buy_policy_mult, buy_policy_reason = _policy_multiplier("BUY", state_vector_v2)
    sell_policy_mult, sell_policy_reason = _policy_multiplier("SELL", state_vector_v2)
    buy_topdown_mult, buy_topdown_reason = _topdown_multiplier("BUY", state_vector_v2)
    sell_topdown_mult, sell_topdown_reason = _topdown_multiplier("SELL", state_vector_v2)

    buy_reversal_fit, buy_reversal_fit_meta = _position_fit(position_snapshot, archetype="buy_reversal")
    sell_reversal_fit, sell_reversal_fit_meta = _position_fit(position_snapshot, archetype="sell_reversal")
    buy_continuation_fit, buy_continuation_fit_meta = _position_fit(position_snapshot, archetype="buy_continuation")
    sell_continuation_fit, sell_continuation_fit_meta = _position_fit(position_snapshot, archetype="sell_continuation")

    buy_reversal_base = (0.65 * float(response_vector_v2.lower_hold_up)) + (0.35 * float(response_vector_v2.mid_reclaim_up))
    sell_reversal_base = (0.65 * float(response_vector_v2.upper_reject_down)) + (0.35 * float(response_vector_v2.mid_lose_down))
    buy_continuation_base = float(response_vector_v2.upper_break_up)
    sell_continuation_base = float(response_vector_v2.lower_break_down)

    buy_reversal_evidence = buy_reversal_base * reversal_multiplier * buy_reversal_fit * buy_policy_mult * buy_topdown_mult
    sell_reversal_evidence = sell_reversal_base * reversal_multiplier * sell_reversal_fit * sell_policy_mult * sell_topdown_mult
    buy_continuation_evidence = (
        buy_continuation_base * continuation_multiplier * buy_continuation_fit * buy_policy_mult * buy_topdown_mult
    )
    sell_continuation_evidence = (
        sell_continuation_base * continuation_multiplier * sell_continuation_fit * sell_policy_mult * sell_topdown_mult
    )

    buy_total_evidence, buy_dominant_component, buy_support_component = _capped_dominant_merge(
        buy_reversal_evidence,
        buy_continuation_evidence,
    )
    sell_total_evidence, sell_dominant_component, sell_support_component = _capped_dominant_merge(
        sell_reversal_evidence,
        sell_continuation_evidence,
    )

    if buy_total_evidence > sell_total_evidence:
        dominant_side = "BUY"
    elif sell_total_evidence > buy_total_evidence:
        dominant_side = "SELL"
    else:
        dominant_side = "BALANCED"

    dominant_mode_by_side = {
        "BUY": (
            "reversal"
            if buy_reversal_evidence > buy_continuation_evidence
            else "continuation"
            if buy_continuation_evidence > buy_reversal_evidence
            else "balanced"
        ),
        "SELL": (
            "reversal"
            if sell_reversal_evidence > sell_continuation_evidence
            else "continuation"
            if sell_continuation_evidence > sell_reversal_evidence
            else "balanced"
        ),
    }

    fit_reason_buy_reversal = str(buy_reversal_fit_meta.get("reason") or "")
    fit_reason_sell_reversal = str(sell_reversal_fit_meta.get("reason") or "")
    fit_reason_buy_continuation = str(buy_continuation_fit_meta.get("reason") or "")
    fit_reason_sell_continuation = str(sell_continuation_fit_meta.get("reason") or "")

    return EvidenceVector(
        buy_reversal_evidence=float(buy_reversal_evidence),
        sell_reversal_evidence=float(sell_reversal_evidence),
        buy_continuation_evidence=float(buy_continuation_evidence),
        sell_continuation_evidence=float(sell_continuation_evidence),
        buy_total_evidence=float(buy_total_evidence),
        sell_total_evidence=float(sell_total_evidence),
        metadata={
            "evidence_contract": "canonical_v1",
            "mapper_version": "evidence_vector_v1_e4",
            "merge_mode": "capped_dominant_merge",
            "position_contract": "position_snapshot_v2",
            "response_contract": "response_vector_v2",
            "response_mapper_version": str((response_vector_v2.metadata or {}).get("mapper_version") or ""),
            "state_contract": str((state_vector_v2.metadata or {}).get("state_contract") or "canonical_v2"),
            "state_mapper_version": str((state_vector_v2.metadata or {}).get("mapper_version") or ""),
            "position_fit_contract": {
                "inputs": [
                    "PositionInterpretation.primary_label",
                    "PositionInterpretation.bias_label",
                    "PositionInterpretation.secondary_context_label",
                    "PositionEnergySnapshot.position_conflict_score",
                ],
                "direction_source_used": False,
            },
            "shared_quality_multiplier": float(shared_quality),
            "reversal_multiplier": float(reversal_multiplier),
            "continuation_multiplier": float(continuation_multiplier),
            "policy_multipliers": {
                "BUY": float(buy_policy_mult),
                "SELL": float(sell_policy_mult),
            },
            "topdown_multipliers": {
                "BUY": float(buy_topdown_mult),
                "SELL": float(sell_topdown_mult),
            },
            "policy_reasons": {
                "BUY": buy_policy_reason,
                "SELL": sell_policy_reason,
            },
            "topdown_reasons": {
                "BUY": buy_topdown_reason,
                "SELL": sell_topdown_reason,
            },
            "archetype_fit": {
                "buy_reversal": buy_reversal_fit_meta,
                "sell_reversal": sell_reversal_fit_meta,
                "buy_continuation": buy_continuation_fit_meta,
                "sell_continuation": sell_continuation_fit_meta,
            },
            "component_scores": {
                "buy_reversal_base": float(buy_reversal_base),
                "sell_reversal_base": float(sell_reversal_base),
                "buy_continuation_base": float(buy_continuation_base),
                "sell_continuation_base": float(sell_continuation_base),
                "buy_reversal_evidence": float(buy_reversal_evidence),
                "sell_reversal_evidence": float(sell_reversal_evidence),
                "buy_continuation_evidence": float(buy_continuation_evidence),
                "sell_continuation_evidence": float(sell_continuation_evidence),
                "buy_dominant_component": float(buy_dominant_component),
                "buy_support_component": float(buy_support_component),
                "sell_dominant_component": float(sell_dominant_component),
                "sell_support_component": float(sell_support_component),
            },
            "dominant_side": dominant_side,
            "dominant_mode_by_side": dominant_mode_by_side,
            "evidence_reasons": {
                "buy_reversal_evidence": (
                    "lower_hold_up + mid_reclaim_up boosted by range_reversal_gain "
                    "and shared quality "
                    f"(base={buy_reversal_base:.4f}, fit={buy_reversal_fit:.4f}, fit_reason={fit_reason_buy_reversal}, "
                    f"range_reversal_gain={state_vector_v2.range_reversal_gain:.4f}, "
                    f"alignment_gain={state_vector_v2.alignment_gain:.4f}, "
                    f"big_map_alignment_gain={getattr(state_vector_v2, 'big_map_alignment_gain', 1.0):.4f}, "
                    f"noise_damp={state_vector_v2.noise_damp:.4f}, conflict_damp={state_vector_v2.conflict_damp:.4f}, "
                    f"policy={buy_policy_mult:.4f}, topdown={buy_topdown_mult:.4f})"
                ),
                "sell_reversal_evidence": (
                    "upper_reject_down + mid_lose_down boosted by range_reversal_gain "
                    "and shared quality "
                    f"(base={sell_reversal_base:.4f}, fit={sell_reversal_fit:.4f}, fit_reason={fit_reason_sell_reversal}, "
                    f"range_reversal_gain={state_vector_v2.range_reversal_gain:.4f}, "
                    f"alignment_gain={state_vector_v2.alignment_gain:.4f}, "
                    f"big_map_alignment_gain={getattr(state_vector_v2, 'big_map_alignment_gain', 1.0):.4f}, "
                    f"noise_damp={state_vector_v2.noise_damp:.4f}, conflict_damp={state_vector_v2.conflict_damp:.4f}, "
                    f"policy={sell_policy_mult:.4f}, topdown={sell_topdown_mult:.4f})"
                ),
                "buy_continuation_evidence": (
                    "upper_break_up strengthened by trend_pullback_gain and breakout_continuation_gain "
                    f"(base={buy_continuation_base:.4f}, fit={buy_continuation_fit:.4f}, fit_reason={fit_reason_buy_continuation}, "
                    f"trend_pullback_gain={state_vector_v2.trend_pullback_gain:.4f}, "
                    f"breakout_continuation_gain={state_vector_v2.breakout_continuation_gain:.4f}, "
                    f"alignment_gain={state_vector_v2.alignment_gain:.4f}, "
                    f"big_map_alignment_gain={getattr(state_vector_v2, 'big_map_alignment_gain', 1.0):.4f}, "
                    f"noise_damp={state_vector_v2.noise_damp:.4f}, conflict_damp={state_vector_v2.conflict_damp:.4f}, "
                    f"policy={buy_policy_mult:.4f}, topdown={buy_topdown_mult:.4f})"
                ),
                "sell_continuation_evidence": (
                    "lower_break_down strengthened by trend_pullback_gain and breakout_continuation_gain "
                    f"(base={sell_continuation_base:.4f}, fit={sell_continuation_fit:.4f}, fit_reason={fit_reason_sell_continuation}, "
                    f"trend_pullback_gain={state_vector_v2.trend_pullback_gain:.4f}, "
                    f"breakout_continuation_gain={state_vector_v2.breakout_continuation_gain:.4f}, "
                    f"alignment_gain={state_vector_v2.alignment_gain:.4f}, "
                    f"big_map_alignment_gain={getattr(state_vector_v2, 'big_map_alignment_gain', 1.0):.4f}, "
                    f"noise_damp={state_vector_v2.noise_damp:.4f}, conflict_damp={state_vector_v2.conflict_damp:.4f}, "
                    f"policy={sell_policy_mult:.4f}, topdown={sell_topdown_mult:.4f})"
                ),
                "buy_total_evidence": (
                    f"capped dominant merge -> dominant={buy_dominant_component:.4f}, support={buy_support_component:.4f}"
                ),
                "sell_total_evidence": (
                    f"capped dominant merge -> dominant={sell_dominant_component:.4f}, support={sell_support_component:.4f}"
                ),
            },
        },
    )
