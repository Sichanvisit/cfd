from __future__ import annotations

from backend.trading.engine.core.models import (
    BarrierState,
    BeliefState,
    EvidenceVector,
    ForecastFeaturesV1,
    PositionSnapshot,
    ResponseVectorV2,
    StateVectorV2,
)


FORECAST_FEATURES_CONTRACT_V1 = {
    "contract_version": "forecast_features_v1",
    "semantic_inputs": [
        "position_snapshot_v2",
        "response_vector_v2",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
    ],
    "semantic_only": True,
    "raw_inputs_used": False,
}

FORECAST_FREEZE_CONTRACT_V1 = {
    "semantic_owner_contract": "forecast_branch_interpretation_only_v1",
    "forecast_freeze_phase": "FR0",
    "forecast_role_statement": (
        "Forecast interprets already-built semantic outputs into transition, management, and comparison branches; "
        "it does not create new semantic owners."
    ),
    "owner_boundaries_v1": {
        "position_location_owner": False,
        "response_event_owner": False,
        "state_market_regime_owner": False,
        "evidence_instant_ground_owner": False,
        "belief_persistence_owner": False,
        "barrier_blocking_owner": False,
    },
    "execution_side_creator_allowed": False,
    "direct_action_creator_allowed": False,
    "summary_side_metadata_allowed": False,
    "summary_mode_metadata_allowed": False,
    "branch_layer_only": True,
}

FORECAST_SEMANTIC_INPUTS_V2_CONTRACT = {
    "contract_version": "semantic_forecast_inputs_v2",
    "phase": "FR1",
    "goal": "harvest rich upstream semantic inputs for downstream forecast branches without changing ownership",
    "sections": [
        "state_harvest",
        "belief_harvest",
        "barrier_harvest",
        "secondary_harvest",
    ],
}

BRIDGE_FIRST_V1_CONTRACT = {
    "contract_version": "bridge_first_v1",
    "phase": "BF1",
    "goal": "summarize semantic layers into small bridge modifiers shared by forecast refinement and product acceptance",
}

ACT_VS_WAIT_BIAS_V1_CONTRACT = {
    "contract_version": "act_vs_wait_bias_v1",
    "bridge_role": "transition_wait_awareness_modifier",
    "owner_mode": "modifier_only",
    "semantic_owner_override_allowed": False,
    "target_surfaces": [
        "transition_forecast",
        "consumer_check_state",
        "product_acceptance_chart_wait",
    ],
    "source_layers": [
        "state",
        "evidence",
        "belief",
        "barrier",
    ],
}

MANAGEMENT_HOLD_REWARD_HINT_V1_CONTRACT = {
    "contract_version": "management_hold_reward_hint_v1",
    "bridge_role": "trade_management_hold_reward_modifier",
    "owner_mode": "modifier_only",
    "semantic_owner_override_allowed": False,
    "target_surfaces": [
        "trade_management_forecast",
        "product_acceptance_hold_exit",
    ],
    "source_layers": [
        "state",
        "evidence",
        "belief",
        "barrier",
    ],
}

MANAGEMENT_FAST_CUT_RISK_V1_CONTRACT = {
    "contract_version": "management_fast_cut_risk_v1",
    "bridge_role": "trade_management_fast_cut_modifier",
    "owner_mode": "modifier_only",
    "semantic_owner_override_allowed": False,
    "target_surfaces": [
        "trade_management_forecast",
        "product_acceptance_exit_caution",
    ],
    "source_layers": [
        "state",
        "evidence",
        "belief",
        "barrier",
    ],
}

TREND_CONTINUATION_MATURITY_V1_CONTRACT = {
    "contract_version": "trend_continuation_maturity_v1",
    "bridge_role": "trade_management_trend_continuation_modifier",
    "owner_mode": "modifier_only",
    "semantic_owner_override_allowed": False,
    "target_surfaces": [
        "trade_management_forecast",
        "product_acceptance_hold_exit",
    ],
    "source_layers": [
        "state",
        "evidence",
        "belief",
        "barrier",
    ],
}

ADVANCED_INPUT_RELIABILITY_V1_CONTRACT = {
    "contract_version": "advanced_input_reliability_v1",
    "bridge_role": "advanced_input_reliability_modifier",
    "owner_mode": "modifier_only",
    "semantic_owner_override_allowed": False,
    "target_surfaces": [
        "transition_forecast",
        "trade_management_forecast",
        "product_acceptance_chart_wait",
    ],
    "source_layers": [
        "state",
    ],
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _state_label_score(label: str, *, high: str, medium: str, low: str) -> float:
    normalized = str(label or "").strip().upper()
    if normalized == str(high or "").strip().upper():
        return 1.0
    if normalized == str(medium or "").strip().upper():
        return 0.55
    if normalized == str(low or "").strip().upper():
        return 0.20
    return 0.0


def _state_label_any_score(
    label: str,
    *,
    highs: tuple[str, ...] = (),
    mediums: tuple[str, ...] = (),
    lows: tuple[str, ...] = (),
) -> float:
    normalized = str(label or "").strip().upper()
    if normalized in {str(value or "").strip().upper() for value in highs}:
        return 1.0
    if normalized in {str(value or "").strip().upper() for value in mediums}:
        return 0.55
    if normalized in {str(value or "").strip().upper() for value in lows}:
        return 0.20
    return 0.0


def _gain_tailwind(value: float, *, neutral: float = 1.0, scale: float = 0.40) -> float:
    return _clamp01(max(float(value or 0.0) - float(neutral), 0.0) / float(scale or 1.0))


def _advanced_activation_score(label: str) -> float:
    normalized = str(label or "").strip().upper()
    if normalized == "ACTIVE":
        return 1.0
    if normalized == "PARTIAL_ACTIVE":
        return 0.72
    if normalized == "PASSIVE_ONLY":
        return 0.30
    if normalized == "INACTIVE":
        return 0.12
    if normalized in {"UNAVAILABLE", "DISABLED"}:
        return 0.0
    return 0.18 if normalized else 0.0


def _collector_available(label: str) -> bool:
    normalized = str(label or "").strip().upper()
    return normalized not in {
        "",
        "UNKNOWN",
        "UNAVAILABLE",
        "DISABLED",
        "INACTIVE",
        "PASSIVE_ONLY",
    }


def _act_vs_wait_bias_v1(
    position_snapshot: PositionSnapshot,
    state_vector_v2: StateVectorV2,
    evidence_vector_v1: EvidenceVector,
    belief_state_v1: BeliefState,
    barrier_state_v1: BarrierState,
) -> dict[str, object]:
    energy = position_snapshot.energy
    state_meta = dict(state_vector_v2.metadata or {})

    dominant_evidence = _clamp01(
        max(
            float(evidence_vector_v1.buy_total_evidence or 0.0),
            float(evidence_vector_v1.sell_total_evidence or 0.0),
        )
    )
    evidence_asymmetry = _clamp01(
        abs(
            float(evidence_vector_v1.buy_total_evidence or 0.0)
            - float(evidence_vector_v1.sell_total_evidence or 0.0)
        )
    )
    dominant_belief = _clamp01(
        max(
            float(belief_state_v1.buy_belief or 0.0),
            float(belief_state_v1.sell_belief or 0.0),
        )
    )
    dominant_persistence = _clamp01(
        max(
            float(belief_state_v1.buy_persistence or 0.0),
            float(belief_state_v1.sell_persistence or 0.0),
        )
    )
    flip_readiness = _clamp01(float(belief_state_v1.flip_readiness or 0.0))
    instability = _clamp01(float(belief_state_v1.belief_instability or 0.0))

    conflict_pressure = _clamp01(
        (0.30 * float(energy.position_conflict_score or 0.0))
        + (0.22 * float(energy.middle_neutrality or 0.0))
        + (0.26 * float(barrier_state_v1.middle_chop_barrier or 0.0))
        + (0.22 * float(barrier_state_v1.conflict_barrier or 0.0))
    )
    friction_pressure = _clamp01(
        (0.38 * float(state_vector_v2.fast_exit_risk_penalty or 0.0))
        + (0.22 * float(state_vector_v2.countertrend_penalty or 0.0))
        + (0.20 * float(state_vector_v2.liquidity_penalty or 0.0))
        + (0.20 * float(state_vector_v2.volatility_penalty or 0.0))
    )
    quality_tailwind = _state_label_score(
        str(state_meta.get("quality_state_label", "") or ""),
        high="HIGH_QUALITY",
        medium="NORMAL_QUALITY",
        low="LOW_QUALITY",
    )
    event_caution = _state_label_score(
        str(state_meta.get("event_risk_state", "") or ""),
        high="HIGH_EVENT_RISK",
        medium="WATCH_EVENT_RISK",
        low="LOW_EVENT_RISK",
    )
    friction_state_pressure = _state_label_score(
        str(state_meta.get("execution_friction_state", "") or ""),
        high="HIGH_FRICTION",
        medium="MEDIUM_FRICTION",
        low="LOW_FRICTION",
    )
    exhaustion_pressure = _state_label_score(
        str(state_meta.get("session_exhaustion_state", "") or ""),
        high="SESSION_EXHAUSTION_HIGH",
        medium="SESSION_EXHAUSTION_RISING",
        low="SESSION_EXHAUSTION_LOW",
    )
    alignment_tailwind = _clamp01(
        (0.40 * max(float(state_vector_v2.topdown_bull_bias or 0.0), float(state_vector_v2.topdown_bear_bias or 0.0)))
        + (0.20 * max(float(state_vector_v2.alignment_gain or 1.0) - 1.0, 0.0))
        + (0.15 * max(float(state_vector_v2.big_map_alignment_gain or 1.0) - 1.0, 0.0))
        + (0.25 * quality_tailwind)
    )

    act_support = _clamp01(
        (0.34 * dominant_evidence)
        + (0.22 * dominant_belief)
        + (0.16 * dominant_persistence)
        + (0.12 * evidence_asymmetry)
        + (0.08 * flip_readiness)
        + (0.08 * alignment_tailwind)
    )
    wait_pressure = _clamp01(
        (0.42 * conflict_pressure)
        + (0.22 * friction_pressure)
        + (0.14 * friction_state_pressure)
        + (0.12 * event_caution)
        + (0.10 * exhaustion_pressure)
    )
    act_vs_wait_bias = _clamp01(0.50 + (0.70 * (act_support - wait_pressure)))
    false_break_risk = _clamp01(
        (0.30 * conflict_pressure)
        + (0.22 * friction_pressure)
        + (0.12 * friction_state_pressure)
        + (0.12 * event_caution)
        + (0.12 * (1.0 - dominant_belief))
        + (0.07 * (1.0 - dominant_persistence))
        + (0.05 * (1.0 - evidence_asymmetry))
    )
    awareness_keep_allowed = bool(
        dominant_evidence >= 0.30
        and (act_vs_wait_bias >= 0.46 or flip_readiness >= 0.32)
        and false_break_risk <= 0.78
    )

    return {
        **dict(ACT_VS_WAIT_BIAS_V1_CONTRACT),
        "act_vs_wait_bias": float(act_vs_wait_bias),
        "false_break_risk": float(false_break_risk),
        "awareness_keep_allowed": bool(awareness_keep_allowed),
        "component_scores": {
            "dominant_evidence": float(dominant_evidence),
            "evidence_asymmetry": float(evidence_asymmetry),
            "dominant_belief": float(dominant_belief),
            "dominant_persistence": float(dominant_persistence),
            "flip_readiness": float(flip_readiness),
            "instability": float(instability),
            "conflict_pressure": float(conflict_pressure),
            "friction_pressure": float(friction_pressure),
            "quality_tailwind": float(quality_tailwind),
            "event_caution": float(event_caution),
            "friction_state_pressure": float(friction_state_pressure),
            "exhaustion_pressure": float(exhaustion_pressure),
            "alignment_tailwind": float(alignment_tailwind),
            "act_support": float(act_support),
            "wait_pressure": float(wait_pressure),
        },
        "reason_summary": (
            f"act_support={act_support:.4f}, wait_pressure={wait_pressure:.4f}, "
            f"conflict_pressure={conflict_pressure:.4f}, false_break_risk={false_break_risk:.4f}"
        ),
    }


def _management_hold_reward_hint_v1(
    position_snapshot: PositionSnapshot,
    state_vector_v2: StateVectorV2,
    evidence_vector_v1: EvidenceVector,
    belief_state_v1: BeliefState,
    barrier_state_v1: BarrierState,
) -> dict[str, object]:
    energy = position_snapshot.energy
    state_meta = dict(state_vector_v2.metadata or {})

    dominant_total_evidence = _clamp01(
        max(
            float(evidence_vector_v1.buy_total_evidence or 0.0),
            float(evidence_vector_v1.sell_total_evidence or 0.0),
        )
    )
    dominant_path_evidence = _clamp01(
        max(
            float(evidence_vector_v1.buy_continuation_evidence or 0.0),
            float(evidence_vector_v1.sell_continuation_evidence or 0.0),
            float(evidence_vector_v1.buy_reversal_evidence or 0.0),
            float(evidence_vector_v1.sell_reversal_evidence or 0.0),
        )
    )
    dominant_belief = _clamp01(
        max(
            float(belief_state_v1.buy_belief or 0.0),
            float(belief_state_v1.sell_belief or 0.0),
        )
    )
    dominant_persistence = _clamp01(
        max(
            float(belief_state_v1.buy_persistence or 0.0),
            float(belief_state_v1.sell_persistence or 0.0),
        )
    )
    belief_spread_strength = _clamp01(abs(float(belief_state_v1.belief_spread or 0.0)))
    hold_patience_tailwind = _gain_tailwind(float(state_vector_v2.hold_patience_gain or 1.0))
    quality_tailwind = _state_label_any_score(
        str(state_meta.get("quality_state_label", "") or ""),
        highs=("HIGH_QUALITY", "GOOD"),
        mediums=("NORMAL_QUALITY", "OK"),
        lows=("LOW_QUALITY", "POOR"),
    )
    confluence_tailwind = _state_label_any_score(
        str(state_meta.get("topdown_confluence_state", "") or ""),
        highs=("BULL_CONFLUENCE", "BEAR_CONFLUENCE", "STRONG_CONFLUENCE"),
        mediums=("WEAK_CONFLUENCE",),
    )
    friction_pressure = _state_label_any_score(
        str(state_meta.get("execution_friction_state", "") or ""),
        highs=("HIGH_FRICTION",),
        mediums=("MEDIUM_FRICTION",),
        lows=("LOW_FRICTION",),
    )
    event_caution = _state_label_any_score(
        str(state_meta.get("event_risk_state", "") or ""),
        highs=("HIGH_EVENT_RISK",),
        mediums=("WATCH_EVENT_RISK",),
        lows=("LOW_EVENT_RISK",),
    )
    exhaustion_pressure = _state_label_any_score(
        str(state_meta.get("session_exhaustion_state", "") or ""),
        highs=("SESSION_EXHAUSTION_HIGH",),
        mediums=("SESSION_EXHAUSTION_RISING",),
        lows=("SESSION_EXHAUSTION_LOW",),
    )
    barrier_pressure = _clamp01(
        (0.30 * float(barrier_state_v1.middle_chop_barrier or 0.0))
        + (0.24 * float(barrier_state_v1.conflict_barrier or 0.0))
        + (
            0.24
            * min(
                float(barrier_state_v1.buy_barrier or 0.0),
                float(barrier_state_v1.sell_barrier or 0.0),
            )
        )
        + (
            0.10
            * max(
                float(barrier_state_v1.buy_barrier or 0.0),
                float(barrier_state_v1.sell_barrier or 0.0),
            )
        )
        + (0.12 * float(state_vector_v2.fast_exit_risk_penalty or 0.0))
    )
    travel_tailwind = _clamp01(
        (0.55 * (1.0 - float(energy.middle_neutrality or 0.0)))
        + (0.45 * (1.0 - float(energy.position_conflict_score or 0.0)))
    )

    hold_positive = _clamp01(
        (0.28 * dominant_total_evidence)
        + (0.24 * dominant_path_evidence)
        + (0.16 * dominant_belief)
        + (0.14 * dominant_persistence)
        + (0.08 * hold_patience_tailwind)
        + (0.05 * quality_tailwind)
        + (0.05 * confluence_tailwind)
    )
    hold_pressure = _clamp01(
        (0.40 * barrier_pressure)
        + (0.18 * friction_pressure)
        + (0.16 * event_caution)
        + (0.14 * exhaustion_pressure)
        + (0.12 * (1.0 - belief_spread_strength))
    )
    hold_reward_hint = _clamp01(0.50 + (0.72 * (hold_positive - hold_pressure)))
    edge_to_edge_tailwind = _clamp01(
        (0.38 * hold_reward_hint)
        + (0.22 * travel_tailwind)
        + (0.18 * dominant_persistence)
        + (0.12 * belief_spread_strength)
        + (0.10 * hold_patience_tailwind)
    )
    hold_patience_allowed = bool(
        dominant_path_evidence >= 0.28
        and hold_reward_hint >= 0.50
        and barrier_pressure <= 0.78
    )

    return {
        **dict(MANAGEMENT_HOLD_REWARD_HINT_V1_CONTRACT),
        "hold_reward_hint": float(hold_reward_hint),
        "edge_to_edge_tailwind": float(edge_to_edge_tailwind),
        "hold_patience_allowed": bool(hold_patience_allowed),
        "component_scores": {
            "dominant_total_evidence": float(dominant_total_evidence),
            "dominant_path_evidence": float(dominant_path_evidence),
            "dominant_belief": float(dominant_belief),
            "dominant_persistence": float(dominant_persistence),
            "belief_spread_strength": float(belief_spread_strength),
            "hold_patience_tailwind": float(hold_patience_tailwind),
            "quality_tailwind": float(quality_tailwind),
            "confluence_tailwind": float(confluence_tailwind),
            "friction_pressure": float(friction_pressure),
            "event_caution": float(event_caution),
            "exhaustion_pressure": float(exhaustion_pressure),
            "barrier_pressure": float(barrier_pressure),
            "travel_tailwind": float(travel_tailwind),
            "hold_positive": float(hold_positive),
            "hold_pressure": float(hold_pressure),
        },
        "reason_summary": (
            f"hold_positive={hold_positive:.4f}, hold_pressure={hold_pressure:.4f}, "
            f"hold_reward_hint={hold_reward_hint:.4f}, edge_to_edge_tailwind={edge_to_edge_tailwind:.4f}"
        ),
    }


def _management_fast_cut_risk_v1(
    position_snapshot: PositionSnapshot,
    state_vector_v2: StateVectorV2,
    evidence_vector_v1: EvidenceVector,
    belief_state_v1: BeliefState,
    barrier_state_v1: BarrierState,
) -> dict[str, object]:
    energy = position_snapshot.energy
    state_meta = dict(state_vector_v2.metadata or {})

    dominant_total_evidence = _clamp01(
        max(
            float(evidence_vector_v1.buy_total_evidence or 0.0),
            float(evidence_vector_v1.sell_total_evidence or 0.0),
        )
    )
    dominant_belief = _clamp01(
        max(
            float(belief_state_v1.buy_belief or 0.0),
            float(belief_state_v1.sell_belief or 0.0),
        )
    )
    dominant_persistence = _clamp01(
        max(
            float(belief_state_v1.buy_persistence or 0.0),
            float(belief_state_v1.sell_persistence or 0.0),
        )
    )
    flip_readiness = _clamp01(float(belief_state_v1.flip_readiness or 0.0))
    instability = _clamp01(float(belief_state_v1.belief_instability or 0.0))
    staying_power = _clamp01(
        (0.38 * dominant_total_evidence)
        + (0.26 * dominant_belief)
        + (0.20 * dominant_persistence)
        + (0.16 * (1.0 - instability))
    )

    fast_exit_pressure = _clamp01(float(state_vector_v2.fast_exit_risk_penalty or 0.0))
    countertrend_pressure = _clamp01(float(state_vector_v2.countertrend_penalty or 0.0))
    liquidity_pressure = _clamp01(float(state_vector_v2.liquidity_penalty or 0.0))
    volatility_pressure = _clamp01(float(state_vector_v2.volatility_penalty or 0.0))
    friction_pressure = _state_label_any_score(
        str(state_meta.get("execution_friction_state", "") or ""),
        highs=("HIGH_FRICTION",),
        mediums=("MEDIUM_FRICTION",),
        lows=("LOW_FRICTION",),
    )
    event_caution = _state_label_any_score(
        str(state_meta.get("event_risk_state", "") or ""),
        highs=("HIGH_EVENT_RISK",),
        mediums=("WATCH_EVENT_RISK",),
        lows=("LOW_EVENT_RISK",),
    )
    exhaustion_pressure = _state_label_any_score(
        str(state_meta.get("session_exhaustion_state", "") or ""),
        highs=("SESSION_EXHAUSTION_HIGH",),
        mediums=("SESSION_EXHAUSTION_RISING",),
        lows=("SESSION_EXHAUSTION_LOW",),
    )
    collision_risk = _clamp01(
        (0.22 * float(barrier_state_v1.middle_chop_barrier or 0.0))
        + (0.20 * float(barrier_state_v1.conflict_barrier or 0.0))
        + (
            0.18
            * max(
                float(barrier_state_v1.buy_barrier or 0.0),
                float(barrier_state_v1.sell_barrier or 0.0),
            )
        )
        + (0.20 * float(energy.position_conflict_score or 0.0))
        + (0.20 * float(energy.middle_neutrality or 0.0))
    )

    cut_pressure = _clamp01(
        (0.28 * fast_exit_pressure)
        + (0.14 * countertrend_pressure)
        + (0.10 * liquidity_pressure)
        + (0.08 * volatility_pressure)
        + (0.12 * friction_pressure)
        + (0.12 * event_caution)
        + (0.08 * exhaustion_pressure)
        + (0.08 * collision_risk)
    )
    cut_positive = _clamp01(
        (0.42 * cut_pressure)
        + (0.26 * instability)
        + (0.18 * flip_readiness)
        + (0.14 * collision_risk)
    )
    fast_cut_risk = _clamp01(0.50 + (0.78 * (cut_positive - staying_power)))
    cut_now_allowed = bool(
        fast_cut_risk >= 0.54
        and (
            collision_risk >= 0.42
            or event_caution >= 0.55
            or fast_exit_pressure >= 0.52
            or instability >= 0.48
        )
    )

    return {
        **dict(MANAGEMENT_FAST_CUT_RISK_V1_CONTRACT),
        "fast_cut_risk": float(fast_cut_risk),
        "collision_risk": float(collision_risk),
        "event_caution": float(event_caution),
        "cut_now_allowed": bool(cut_now_allowed),
        "component_scores": {
            "dominant_total_evidence": float(dominant_total_evidence),
            "dominant_belief": float(dominant_belief),
            "dominant_persistence": float(dominant_persistence),
            "flip_readiness": float(flip_readiness),
            "instability": float(instability),
            "staying_power": float(staying_power),
            "fast_exit_pressure": float(fast_exit_pressure),
            "countertrend_pressure": float(countertrend_pressure),
            "liquidity_pressure": float(liquidity_pressure),
            "volatility_pressure": float(volatility_pressure),
            "friction_pressure": float(friction_pressure),
            "event_caution": float(event_caution),
            "exhaustion_pressure": float(exhaustion_pressure),
            "collision_risk": float(collision_risk),
            "cut_pressure": float(cut_pressure),
            "cut_positive": float(cut_positive),
        },
        "reason_summary": (
            f"cut_pressure={cut_pressure:.4f}, staying_power={staying_power:.4f}, "
            f"fast_cut_risk={fast_cut_risk:.4f}, collision_risk={collision_risk:.4f}"
        ),
    }


def _trend_continuation_maturity_v1(
    position_snapshot: PositionSnapshot,
    state_vector_v2: StateVectorV2,
    evidence_vector_v1: EvidenceVector,
    belief_state_v1: BeliefState,
    barrier_state_v1: BarrierState,
) -> dict[str, object]:
    energy = position_snapshot.energy
    state_meta = dict(state_vector_v2.metadata or {})

    dominant_continuation_evidence = _clamp01(
        max(
            float(evidence_vector_v1.buy_continuation_evidence or 0.0),
            float(evidence_vector_v1.sell_continuation_evidence or 0.0),
        )
    )
    dominant_total_evidence = _clamp01(
        max(
            float(evidence_vector_v1.buy_total_evidence or 0.0),
            float(evidence_vector_v1.sell_total_evidence or 0.0),
        )
    )
    dominant_belief = _clamp01(
        max(
            float(belief_state_v1.buy_belief or 0.0),
            float(belief_state_v1.sell_belief or 0.0),
        )
    )
    dominant_persistence = _clamp01(
        max(
            float(belief_state_v1.buy_persistence or 0.0),
            float(belief_state_v1.sell_persistence or 0.0),
        )
    )
    belief_spread_strength = _clamp01(abs(float(belief_state_v1.belief_spread or 0.0)))
    instability = _clamp01(float(belief_state_v1.belief_instability or 0.0))

    session_regime_tailwind = _state_label_any_score(
        str(state_meta.get("session_regime_state", "") or ""),
        highs=("SESSION_EXPANSION", "SESSION_TREND", "TRENDING"),
        mediums=("SESSION_EDGE_ROTATION", "TRANSITION"),
    )
    session_expansion_tailwind = _state_label_any_score(
        str(state_meta.get("session_expansion_state", "") or ""),
        highs=(
            "UP_ACTIVE_EXPANSION",
            "UP_EXTENDED_EXPANSION",
            "DOWN_ACTIVE_EXPANSION",
            "DOWN_EXTENDED_EXPANSION",
        ),
        mediums=("UP_EARLY_EXPANSION", "DOWN_EARLY_EXPANSION"),
    )
    slope_tailwind = _state_label_any_score(
        str(state_meta.get("topdown_slope_state", "") or ""),
        highs=("UP_SLOPE_ALIGNED", "DOWN_SLOPE_ALIGNED"),
        mediums=("MIXED_SLOPE",),
        lows=("FLAT_SLOPE",),
    )
    confluence_tailwind = _state_label_any_score(
        str(state_meta.get("topdown_confluence_state", "") or ""),
        highs=("BULL_CONFLUENCE", "BEAR_CONFLUENCE", "STRONG_CONFLUENCE"),
        mediums=("WEAK_CONFLUENCE",),
        lows=("TOPDOWN_CONFLICT",),
    )
    quality_tailwind = _state_label_any_score(
        str(state_meta.get("quality_state_label", "") or ""),
        highs=("HIGH_QUALITY", "GOOD"),
        mediums=("NORMAL_QUALITY", "OK"),
        lows=("LOW_QUALITY", "POOR"),
    )
    exhaustion_pressure = _state_label_any_score(
        str(state_meta.get("session_exhaustion_state", "") or ""),
        highs=("SESSION_EXHAUSTION_HIGH",),
        mediums=("SESSION_EXHAUSTION_RISING",),
    )
    friction_pressure = _state_label_any_score(
        str(state_meta.get("execution_friction_state", "") or ""),
        highs=("HIGH_FRICTION",),
        mediums=("MEDIUM_FRICTION",),
    )
    event_caution = _state_label_any_score(
        str(state_meta.get("event_risk_state", "") or ""),
        highs=("HIGH_EVENT_RISK",),
        mediums=("WATCH_EVENT_RISK",),
    )
    travel_tailwind = _clamp01(
        (0.52 * (1.0 - float(energy.middle_neutrality or 0.0)))
        + (0.48 * (1.0 - float(energy.position_conflict_score or 0.0)))
    )
    barrier_pressure = _clamp01(
        (0.34 * float(barrier_state_v1.middle_chop_barrier or 0.0))
        + (0.26 * float(barrier_state_v1.conflict_barrier or 0.0))
        + (
            0.18
            * max(
                float(barrier_state_v1.buy_barrier or 0.0),
                float(barrier_state_v1.sell_barrier or 0.0),
            )
        )
        + (0.12 * event_caution)
        + (0.10 * friction_pressure)
    )

    continuation_positive = _clamp01(
        (0.24 * dominant_continuation_evidence)
        + (0.18 * dominant_total_evidence)
        + (0.16 * dominant_belief)
        + (0.16 * dominant_persistence)
        + (0.08 * belief_spread_strength)
        + (0.06 * session_regime_tailwind)
        + (0.05 * session_expansion_tailwind)
        + (0.03 * slope_tailwind)
        + (0.02 * confluence_tailwind)
        + (0.02 * quality_tailwind)
    )
    continuation_drag = _clamp01(
        (0.36 * barrier_pressure)
        + (0.22 * exhaustion_pressure)
        + (0.14 * friction_pressure)
        + (0.10 * event_caution)
        + (0.10 * float(energy.position_conflict_score or 0.0))
        + (0.08 * instability)
    )
    continuation_maturity = _clamp01(
        (0.64 * continuation_positive)
        + (0.20 * travel_tailwind)
        + (0.16 * (1.0 - continuation_drag))
    )
    trend_hold_confidence = _clamp01(
        0.50 + (0.78 * ((0.72 * continuation_maturity) - (0.28 * exhaustion_pressure)))
    )

    return {
        **dict(TREND_CONTINUATION_MATURITY_V1_CONTRACT),
        "continuation_maturity": float(continuation_maturity),
        "exhaustion_pressure": float(exhaustion_pressure),
        "trend_hold_confidence": float(trend_hold_confidence),
        "component_scores": {
            "dominant_continuation_evidence": float(dominant_continuation_evidence),
            "dominant_total_evidence": float(dominant_total_evidence),
            "dominant_belief": float(dominant_belief),
            "dominant_persistence": float(dominant_persistence),
            "belief_spread_strength": float(belief_spread_strength),
            "instability": float(instability),
            "session_regime_tailwind": float(session_regime_tailwind),
            "session_expansion_tailwind": float(session_expansion_tailwind),
            "slope_tailwind": float(slope_tailwind),
            "confluence_tailwind": float(confluence_tailwind),
            "quality_tailwind": float(quality_tailwind),
            "exhaustion_pressure": float(exhaustion_pressure),
            "friction_pressure": float(friction_pressure),
            "event_caution": float(event_caution),
            "travel_tailwind": float(travel_tailwind),
            "barrier_pressure": float(barrier_pressure),
            "continuation_positive": float(continuation_positive),
            "continuation_drag": float(continuation_drag),
        },
        "reason_summary": (
            f"continuation_positive={continuation_positive:.4f}, continuation_drag={continuation_drag:.4f}, "
            f"continuation_maturity={continuation_maturity:.4f}, trend_hold_confidence={trend_hold_confidence:.4f}"
        ),
    }


def _advanced_input_reliability_v1(
    state_vector_v2: StateVectorV2,
) -> dict[str, object]:
    state_meta = dict(state_vector_v2.metadata or {})
    activation_state = str(state_meta.get("advanced_input_activation_state", "") or "")
    tick_flow_state = str(state_meta.get("tick_flow_state", "") or "")
    order_book_state = str(state_meta.get("order_book_state", "") or "")
    event_risk_state = str(state_meta.get("event_risk_state", "") or "")

    activation_score = _advanced_activation_score(activation_state)
    tick_context_reliable = _collector_available(tick_flow_state) and activation_score >= 0.25
    event_context_available = bool(str(event_risk_state or "").strip())
    event_context_reliable = event_context_available and activation_score >= 0.25
    order_book_available = _collector_available(order_book_state)
    order_book_reliable = order_book_available and activation_score >= 0.65
    event_caution = _state_label_any_score(
        event_risk_state,
        highs=("HIGH_EVENT_RISK",),
        mediums=("WATCH_EVENT_RISK",),
        lows=("LOW_EVENT_RISK",),
    )
    order_book_gap_penalty = 0.0 if order_book_reliable else 0.20 if order_book_available else 0.36
    advanced_positive = _clamp01(
        (0.52 * activation_score)
        + (0.24 * float(tick_context_reliable))
        + (0.16 * float(event_context_reliable))
        + (0.08 * float(order_book_reliable))
    )
    advanced_reliability = _clamp01(
        advanced_positive
        - (0.10 * order_book_gap_penalty)
        - (0.04 * max(event_caution - 0.55, 0.0))
    )

    return {
        **dict(ADVANCED_INPUT_RELIABILITY_V1_CONTRACT),
        "advanced_reliability": float(advanced_reliability),
        "order_book_reliable": bool(order_book_reliable),
        "event_context_reliable": bool(event_context_reliable),
        "component_scores": {
            "activation_score": float(activation_score),
            "tick_context_reliable": float(tick_context_reliable),
            "event_context_available": float(event_context_available),
            "event_context_reliable": float(event_context_reliable),
            "event_caution": float(event_caution),
            "order_book_available": float(order_book_available),
            "order_book_reliable": float(order_book_reliable),
            "order_book_gap_penalty": float(order_book_gap_penalty),
            "advanced_positive": float(advanced_positive),
        },
        "reason_summary": (
            f"activation_score={activation_score:.4f}, tick_context_reliable={int(tick_context_reliable)}, "
            f"event_context_reliable={int(event_context_reliable)}, order_book_reliable={int(order_book_reliable)}, "
            f"advanced_reliability={advanced_reliability:.4f}"
        ),
    }


def _bridge_first_v1(
    position_snapshot: PositionSnapshot,
    state_vector_v2: StateVectorV2,
    evidence_vector_v1: EvidenceVector,
    belief_state_v1: BeliefState,
    barrier_state_v1: BarrierState,
) -> dict[str, object]:
    return {
        **dict(BRIDGE_FIRST_V1_CONTRACT),
        "act_vs_wait_bias_v1": _act_vs_wait_bias_v1(
            position_snapshot,
            state_vector_v2,
            evidence_vector_v1,
            belief_state_v1,
            barrier_state_v1,
        ),
        "management_hold_reward_hint_v1": _management_hold_reward_hint_v1(
            position_snapshot,
            state_vector_v2,
            evidence_vector_v1,
            belief_state_v1,
            barrier_state_v1,
        ),
        "management_fast_cut_risk_v1": _management_fast_cut_risk_v1(
            position_snapshot,
            state_vector_v2,
            evidence_vector_v1,
            belief_state_v1,
            barrier_state_v1,
        ),
        "trend_continuation_maturity_v1": _trend_continuation_maturity_v1(
            position_snapshot,
            state_vector_v2,
            evidence_vector_v1,
            belief_state_v1,
            barrier_state_v1,
        ),
        "advanced_input_reliability_v1": _advanced_input_reliability_v1(
            state_vector_v2,
        ),
    }


def _state_harvest(state_vector_v2: StateVectorV2) -> dict[str, object]:
    metadata = dict(state_vector_v2.metadata or {})
    return {
        "session_regime_state": str(metadata.get("session_regime_state", "") or ""),
        "session_expansion_state": str(metadata.get("session_expansion_state", "") or ""),
        "session_exhaustion_state": str(metadata.get("session_exhaustion_state", "") or ""),
        "micro_breakout_readiness_state": str(metadata.get("micro_breakout_readiness_state", "") or ""),
        "micro_reversal_risk_state": str(metadata.get("micro_reversal_risk_state", "") or ""),
        "micro_participation_state": str(metadata.get("micro_participation_state", "") or ""),
        "micro_gap_context_state": str(metadata.get("micro_gap_context_state", "") or ""),
        "topdown_spacing_state": str(metadata.get("topdown_spacing_state", "") or ""),
        "topdown_slope_state": str(metadata.get("topdown_slope_state", "") or ""),
        "topdown_confluence_state": str(metadata.get("topdown_confluence_state", "") or ""),
        "spread_stress_state": str(metadata.get("spread_stress_state", "") or ""),
        "volume_participation_state": str(metadata.get("volume_participation_state", "") or ""),
        "execution_friction_state": str(metadata.get("execution_friction_state", "") or ""),
        "event_risk_state": str(metadata.get("event_risk_state", "") or ""),
    }


def _belief_harvest(belief_state_v1: BeliefState) -> dict[str, object]:
    return {
        "dominant_side": str(belief_state_v1.dominant_side or "BALANCED"),
        "dominant_mode": str(belief_state_v1.dominant_mode or "balanced"),
        "buy_streak": int(belief_state_v1.buy_streak or 0),
        "sell_streak": int(belief_state_v1.sell_streak or 0),
        "flip_readiness": float(belief_state_v1.flip_readiness or 0.0),
        "belief_instability": float(belief_state_v1.belief_instability or 0.0),
    }


def _barrier_harvest(barrier_state_v1: BarrierState) -> dict[str, object]:
    metadata = dict(barrier_state_v1.metadata or {})
    return {
        "edge_turn_relief_v1": dict(metadata.get("edge_turn_relief_v1", {}) or {}),
        "breakout_fade_barrier_v1": dict(metadata.get("breakout_fade_barrier_v1", {}) or {}),
        "middle_chop_barrier_v2": dict(metadata.get("middle_chop_barrier_v2", {}) or {}),
        "session_open_shock_barrier_v1": dict(metadata.get("session_open_shock_barrier_v1", {}) or {}),
        "duplicate_edge_barrier_v1": dict(metadata.get("duplicate_edge_barrier_v1", {}) or {}),
        "micro_trap_barrier_v1": dict(metadata.get("micro_trap_barrier_v1", {}) or {}),
        "post_event_cooldown_barrier_v1": dict(metadata.get("post_event_cooldown_barrier_v1", {}) or {}),
    }


def _secondary_harvest(state_vector_v2: StateVectorV2) -> dict[str, object]:
    metadata = dict(state_vector_v2.metadata or {})
    return {
        "advanced_input_activation_state": str(metadata.get("advanced_input_activation_state", "") or ""),
        "tick_flow_state": str(metadata.get("tick_flow_state", "") or ""),
        "order_book_state": str(metadata.get("order_book_state", "") or ""),
        "source_current_rsi": float(metadata.get("source_current_rsi", 0.0) or 0.0),
        "source_current_adx": float(metadata.get("source_current_adx", 0.0) or 0.0),
        "source_current_plus_di": float(metadata.get("source_current_plus_di", 0.0) or 0.0),
        "source_current_minus_di": float(metadata.get("source_current_minus_di", 0.0) or 0.0),
        "source_recent_range_mean": float(metadata.get("source_recent_range_mean", 0.0) or 0.0),
        "source_recent_body_mean": float(metadata.get("source_recent_body_mean", 0.0) or 0.0),
        "source_micro_body_size_pct_20": float(metadata.get("source_micro_body_size_pct_20", 0.0) or 0.0),
        "source_micro_upper_wick_ratio_20": float(metadata.get("source_micro_upper_wick_ratio_20", 0.0) or 0.0),
        "source_micro_lower_wick_ratio_20": float(metadata.get("source_micro_lower_wick_ratio_20", 0.0) or 0.0),
        "source_micro_doji_ratio_20": float(metadata.get("source_micro_doji_ratio_20", 0.0) or 0.0),
        "source_micro_same_color_run_current": float(metadata.get("source_micro_same_color_run_current", 0.0) or 0.0),
        "source_micro_same_color_run_max_20": float(metadata.get("source_micro_same_color_run_max_20", 0.0) or 0.0),
        "source_micro_bull_ratio_20": float(metadata.get("source_micro_bull_ratio_20", 0.0) or 0.0),
        "source_micro_bear_ratio_20": float(metadata.get("source_micro_bear_ratio_20", 0.0) or 0.0),
        "source_micro_range_compression_ratio_20": float(metadata.get("source_micro_range_compression_ratio_20", 0.0) or 0.0),
        "source_micro_volume_burst_ratio_20": float(metadata.get("source_micro_volume_burst_ratio_20", 0.0) or 0.0),
        "source_micro_volume_burst_decay_20": float(metadata.get("source_micro_volume_burst_decay_20", 0.0) or 0.0),
        "source_micro_swing_high_retest_count_20": float(metadata.get("source_micro_swing_high_retest_count_20", 0.0) or 0.0),
        "source_micro_swing_low_retest_count_20": float(metadata.get("source_micro_swing_low_retest_count_20", 0.0) or 0.0),
        "source_micro_gap_fill_progress": metadata.get("source_micro_gap_fill_progress"),
        "source_sr_level_rank": float(metadata.get("source_sr_level_rank", 0.0) or 0.0),
        "source_sr_touch_count": float(metadata.get("source_sr_touch_count", 0.0) or 0.0),
    }


def _semantic_forecast_inputs_v2(
    state_vector_v2: StateVectorV2,
    belief_state_v1: BeliefState,
    barrier_state_v1: BarrierState,
) -> dict[str, object]:
    return {
        **dict(FORECAST_SEMANTIC_INPUTS_V2_CONTRACT),
        "state_harvest": _state_harvest(state_vector_v2),
        "belief_harvest": _belief_harvest(belief_state_v1),
        "barrier_harvest": _barrier_harvest(barrier_state_v1),
        "secondary_harvest": _secondary_harvest(state_vector_v2),
    }


def build_forecast_features(
    position_snapshot: PositionSnapshot,
    response_vector_v2: ResponseVectorV2,
    state_vector_v2: StateVectorV2,
    evidence_vector_v1: EvidenceVector,
    belief_state_v1: BeliefState,
    barrier_state_v1: BarrierState,
) -> ForecastFeaturesV1:
    interpretation = position_snapshot.interpretation
    energy = position_snapshot.energy
    bridge_first_v1 = _bridge_first_v1(
        position_snapshot,
        state_vector_v2,
        evidence_vector_v1,
        belief_state_v1,
        barrier_state_v1,
    )

    return ForecastFeaturesV1(
        position_primary_label=str(interpretation.primary_label or "UNRESOLVED_POSITION"),
        position_bias_label=str(interpretation.bias_label or ""),
        position_secondary_context_label=str(interpretation.secondary_context_label or "NEUTRAL_CONTEXT"),
        position_conflict_score=float(energy.position_conflict_score or 0.0),
        middle_neutrality=float(energy.middle_neutrality or 0.0),
        response_vector_v2=response_vector_v2,
        state_vector_v2=state_vector_v2,
        evidence_vector_v1=evidence_vector_v1,
        belief_state_v1=belief_state_v1,
        barrier_state_v1=barrier_state_v1,
        metadata={
            "forecast_features_contract": dict(FORECAST_FEATURES_CONTRACT_V1),
            **dict(FORECAST_FREEZE_CONTRACT_V1),
            "semantic_forecast_inputs_v2": _semantic_forecast_inputs_v2(
                state_vector_v2,
                belief_state_v1,
                barrier_state_v1,
            ),
            "bridge_first_v1": bridge_first_v1,
            "forecast_branch_role": "feature_bundle_only",
            "position_contract": "position_snapshot_v2",
            "response_contract": str((response_vector_v2.metadata or {}).get("mapper_version", "") or "response_vector_v2"),
            "state_contract": str((state_vector_v2.metadata or {}).get("mapper_version", "") or "state_vector_v2"),
            "evidence_contract": str((evidence_vector_v1.metadata or {}).get("mapper_version", "") or "evidence_vector_v1"),
            "belief_contract": str((belief_state_v1.metadata or {}).get("mapper_version", "") or "belief_state_v1"),
            "barrier_contract": str((barrier_state_v1.metadata or {}).get("mapper_version", "") or "barrier_state_v1"),
            "feature_bundle_type": "semantic_feature_package",
            "feature_layers": list(FORECAST_FEATURES_CONTRACT_V1["semantic_inputs"]),
        },
    )
