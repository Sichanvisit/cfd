from backend.services.context_classifier import ContextClassifier
from backend.services.layer_mode_contract import build_layer_mode_effective_metadata
from backend.trading.engine.core.forecast_engine import (
    ForecastRuleV1,
    build_trade_management_forecast,
    build_transition_forecast,
    extract_forecast_gap_metrics,
    get_default_forecast_engine,
)
from backend.trading.engine.core.forecast_features import build_forecast_features
from backend.trading.engine.core.models import (
    BarrierState,
    BeliefState,
    EvidenceVector,
    ForecastFeaturesV1,
    TradeManagementForecast,
    TransitionForecast,
    PositionEnergySnapshot,
    PositionInterpretation,
    PositionSnapshot,
    ResponseVectorV2,
    StateVectorV2,
)


def test_forecast_features_v1_exposes_exact_canonical_fields():
    payload = ForecastFeaturesV1().to_dict()

    assert set(payload.keys()) == {
        "position_primary_label",
        "position_bias_label",
        "position_secondary_context_label",
        "position_conflict_score",
        "middle_neutrality",
        "response_vector_v2",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
        "metadata",
    }


def test_forecast_features_builder_packages_semantic_inputs_without_reinterpreting():
    position_snapshot = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="MIDDLE_UPPER_BIAS",
            bias_label="MIDDLE_UPPER_BIAS",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(
            position_conflict_score=0.27,
            middle_neutrality=0.61,
        ),
    )
    response_vector_v2 = ResponseVectorV2(
        mid_reclaim_up=0.44,
        upper_break_up=0.32,
        metadata={"mapper_version": "response_vector_v2_r5"},
    )
    state_vector_v2 = StateVectorV2(
        trend_pullback_gain=1.17,
        alignment_gain=1.08,
        metadata={"mapper_version": "state_vector_v2_s9"},
    )
    evidence_vector_v1 = EvidenceVector(
        buy_continuation_evidence=0.38,
        buy_total_evidence=0.38,
        metadata={"mapper_version": "evidence_vector_v1_e4"},
    )
    belief_state_v1 = BeliefState(
        buy_belief=0.24,
        belief_spread=0.19,
        metadata={"mapper_version": "belief_state_v1_b4"},
    )
    barrier_state_v1 = BarrierState(
        buy_barrier=0.12,
        middle_chop_barrier=0.31,
        metadata={"mapper_version": "barrier_state_v1_br11"},
    )

    features = build_forecast_features(
        position_snapshot,
        response_vector_v2,
        state_vector_v2,
        evidence_vector_v1,
        belief_state_v1,
        barrier_state_v1,
    )

    assert features.position_primary_label == "MIDDLE_UPPER_BIAS"
    assert features.position_bias_label == "MIDDLE_UPPER_BIAS"
    assert features.position_secondary_context_label == "UPPER_CONTEXT"
    assert features.position_conflict_score == 0.27
    assert features.middle_neutrality == 0.61
    assert features.response_vector_v2.to_dict() == response_vector_v2.to_dict()
    assert features.state_vector_v2.to_dict() == state_vector_v2.to_dict()
    assert features.evidence_vector_v1.to_dict() == evidence_vector_v1.to_dict()
    assert features.belief_state_v1.to_dict() == belief_state_v1.to_dict()
    assert features.barrier_state_v1.to_dict() == barrier_state_v1.to_dict()
    assert features.metadata["forecast_features_contract"]["contract_version"] == "forecast_features_v1"
    assert features.metadata["forecast_features_contract"]["raw_inputs_used"] is False
    assert features.metadata["feature_bundle_type"] == "semantic_feature_package"
    assert features.metadata["semantic_owner_contract"] == "forecast_branch_interpretation_only_v1"
    assert features.metadata["forecast_freeze_phase"] == "FR0"
    assert features.metadata["forecast_branch_role"] == "feature_bundle_only"
    assert features.metadata["semantic_forecast_inputs_v2"]["contract_version"] == "semantic_forecast_inputs_v2"
    assert features.metadata["semantic_forecast_inputs_v2"]["phase"] == "FR1"
    assert "state_harvest" in features.metadata["semantic_forecast_inputs_v2"]
    assert "belief_harvest" in features.metadata["semantic_forecast_inputs_v2"]
    assert "barrier_harvest" in features.metadata["semantic_forecast_inputs_v2"]
    assert "secondary_harvest" in features.metadata["semantic_forecast_inputs_v2"]
    assert features.metadata["direct_action_creator_allowed"] is False
    assert features.metadata["execution_side_creator_allowed"] is False
    assert features.metadata["owner_boundaries_v1"]["position_location_owner"] is False
    assert features.metadata["owner_boundaries_v1"]["response_event_owner"] is False
    assert features.metadata["semantic_forecast_inputs_v2"]["belief_harvest"]["dominant_side"] == "BALANCED"
    assert features.metadata["semantic_forecast_inputs_v2"]["belief_harvest"]["flip_readiness"] == 0.0
    assert features.metadata["response_contract"] == "response_vector_v2_r5"
    assert features.metadata["state_contract"] == "state_vector_v2_s9"
    assert features.metadata["evidence_contract"] == "evidence_vector_v1_e4"
    assert features.metadata["belief_contract"] == "belief_state_v1_b4"
    assert features.metadata["barrier_contract"] == "barrier_state_v1_br11"


def test_forecast_features_builder_harvests_micro_structure_states():
    features = _build_features(
        primary_label="ALIGNED_UPPER_WEAK",
        secondary_context_label="UPPER_CONTEXT",
        state_metadata={
            "micro_breakout_readiness_state": "BREAKOUT_READY",
            "micro_reversal_risk_state": "REVERSAL_RISK_WATCH",
            "micro_participation_state": "BURST_CONFIRMED",
            "micro_gap_context_state": "ACTIVE_GAP_FILL",
            "source_micro_body_size_pct_20": 0.21,
            "source_micro_upper_wick_ratio_20": 0.33,
            "source_micro_lower_wick_ratio_20": 0.12,
            "source_micro_doji_ratio_20": 0.08,
            "source_micro_same_color_run_current": 4.0,
            "source_micro_same_color_run_max_20": 6.0,
            "source_micro_bull_ratio_20": 0.65,
            "source_micro_bear_ratio_20": 0.35,
            "source_micro_range_compression_ratio_20": 0.71,
            "source_micro_volume_burst_ratio_20": 1.92,
            "source_micro_volume_burst_decay_20": 0.24,
            "source_micro_swing_high_retest_count_20": 2.0,
            "source_micro_swing_low_retest_count_20": 1.0,
            "source_micro_gap_fill_progress": 0.58,
        },
    )

    semantic = features.metadata["semantic_forecast_inputs_v2"]
    state_harvest = semantic["state_harvest"]
    secondary_harvest = semantic["secondary_harvest"]

    assert state_harvest["micro_breakout_readiness_state"] == "BREAKOUT_READY"
    assert state_harvest["micro_reversal_risk_state"] == "REVERSAL_RISK_WATCH"
    assert state_harvest["micro_participation_state"] == "BURST_CONFIRMED"
    assert state_harvest["micro_gap_context_state"] == "ACTIVE_GAP_FILL"
    assert secondary_harvest["source_micro_body_size_pct_20"] == 0.21
    assert secondary_harvest["source_micro_range_compression_ratio_20"] == 0.71
    assert secondary_harvest["source_micro_volume_burst_decay_20"] == 0.24
    assert secondary_harvest["source_micro_gap_fill_progress"] == 0.58


def test_context_classifier_engine_bundle_exposes_forecast_features():
    classifier = ContextClassifier()
    bundle = classifier.build_engine_context_snapshot(
        symbol="BTCUSD",
        tick=type("Tick", (), {"bid": 100.0, "ask": 100.2})(),
        df_all={},
        scorer=None,
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        spread_ratio=0.02,
        box_state="MIDDLE",
        bb_state="MID",
        raw_scores={"buy_score": 10.0, "sell_score": 8.0},
    )

    features = bundle["forecast_features"]

    assert isinstance(features, ForecastFeaturesV1)
    assert features.metadata["forecast_features_contract"]["contract_version"] == "forecast_features_v1"
    assert features.metadata["feature_layers"] == [
        "position_snapshot_v2",
        "response_vector_v2",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
    ]


def test_transition_forecast_exposes_exact_canonical_fields():
    payload = TransitionForecast().to_dict()

    assert set(payload.keys()) == {
        "p_buy_confirm",
        "p_sell_confirm",
        "p_false_break",
        "p_reversal_success",
        "p_continuation_success",
        "metadata",
    }


def _build_features(
    *,
    primary_label: str,
    secondary_context_label: str,
    position_conflict_score: float = 0.0,
    middle_neutrality: float = 0.0,
    lower_hold_up: float = 0.0,
    lower_break_down: float = 0.0,
    mid_reclaim_up: float = 0.0,
    mid_lose_down: float = 0.0,
    upper_reject_down: float = 0.0,
    upper_break_up: float = 0.0,
    buy_reversal: float = 0.0,
    sell_reversal: float = 0.0,
    buy_continuation: float = 0.0,
    sell_continuation: float = 0.0,
    buy_total: float = 0.0,
    sell_total: float = 0.0,
    buy_belief: float = 0.0,
    sell_belief: float = 0.0,
    buy_persistence: float = 0.0,
    sell_persistence: float = 0.0,
    belief_spread: float = 0.0,
    flip_readiness: float = 0.0,
    belief_instability: float = 0.0,
    transition_age: int = 0,
    buy_barrier: float = 0.0,
    sell_barrier: float = 0.0,
    middle_chop_barrier: float = 0.0,
    conflict_barrier: float = 0.0,
    wait_patience_gain: float = 1.0,
    confirm_aggression_gain: float = 1.0,
    hold_patience_gain: float = 1.0,
    fast_exit_risk_penalty: float = 0.0,
    countertrend_penalty: float = 0.0,
    liquidity_penalty: float = 0.0,
    volatility_penalty: float = 0.0,
    state_metadata: dict | None = None,
    barrier_metadata: dict | None = None,
) -> ForecastFeaturesV1:
    state_metadata = {
        "mapper_version": "state_vector_v2_s9",
        **dict(state_metadata or {}),
    }
    barrier_metadata = {
        "mapper_version": "barrier_state_v1_br11",
        **dict(barrier_metadata or {}),
    }
    return build_forecast_features(
        PositionSnapshot(
            interpretation=PositionInterpretation(
                primary_label=primary_label,
                secondary_context_label=secondary_context_label,
            ),
            energy=PositionEnergySnapshot(
                position_conflict_score=position_conflict_score,
                middle_neutrality=middle_neutrality,
            ),
        ),
        ResponseVectorV2(
            lower_hold_up=lower_hold_up,
            lower_break_down=lower_break_down,
            mid_reclaim_up=mid_reclaim_up,
            mid_lose_down=mid_lose_down,
            upper_reject_down=upper_reject_down,
            upper_break_up=upper_break_up,
        ),
        StateVectorV2(
            wait_patience_gain=wait_patience_gain,
            confirm_aggression_gain=confirm_aggression_gain,
            hold_patience_gain=hold_patience_gain,
            fast_exit_risk_penalty=fast_exit_risk_penalty,
            countertrend_penalty=countertrend_penalty,
            liquidity_penalty=liquidity_penalty,
            volatility_penalty=volatility_penalty,
            metadata=state_metadata,
        ),
        EvidenceVector(
            buy_reversal_evidence=buy_reversal,
            sell_reversal_evidence=sell_reversal,
            buy_continuation_evidence=buy_continuation,
            sell_continuation_evidence=sell_continuation,
            buy_total_evidence=buy_total,
            sell_total_evidence=sell_total,
            metadata={"mapper_version": "evidence_vector_v1_e4"},
        ),
        BeliefState(
            buy_belief=buy_belief,
            sell_belief=sell_belief,
            buy_persistence=buy_persistence,
            sell_persistence=sell_persistence,
            belief_spread=belief_spread,
            flip_readiness=flip_readiness,
            belief_instability=belief_instability,
            transition_age=transition_age,
            metadata={"mapper_version": "belief_state_v1_b4"},
        ),
        BarrierState(
            buy_barrier=buy_barrier,
            sell_barrier=sell_barrier,
            middle_chop_barrier=middle_chop_barrier,
            conflict_barrier=conflict_barrier,
            metadata=barrier_metadata,
        ),
    )


def test_forecast_features_builder_exposes_bf1_act_wait_bridge_summary():
    features = _build_features(
        primary_label="ALIGNED_MIDDLE",
        secondary_context_label="NEUTRAL_CONTEXT",
        position_conflict_score=0.41,
        middle_neutrality=0.66,
        buy_continuation=0.58,
        buy_total=0.72,
        sell_total=0.28,
        buy_belief=0.62,
        sell_belief=0.18,
        buy_persistence=0.59,
        sell_persistence=0.12,
        belief_spread=0.44,
        buy_barrier=0.12,
        sell_barrier=0.24,
        middle_chop_barrier=0.21,
        conflict_barrier=0.14,
        state_metadata={
            "quality_state_label": "GOOD",
            "topdown_confluence_state": "BULL_CONFLUENCE",
            "execution_friction_state": "LOW_FRICTION",
        },
    )

    bridge_root = features.metadata["bridge_first_v1"]
    bridge = bridge_root["act_vs_wait_bias_v1"]

    assert bridge_root["contract_version"] == "bridge_first_v1"
    assert bridge_root["phase"] == "BF1"
    assert bridge["contract_version"] == "act_vs_wait_bias_v1"
    assert bridge["bridge_role"] == "transition_wait_awareness_modifier"
    assert 0.0 <= bridge["act_vs_wait_bias"] <= 1.0
    assert 0.0 <= bridge["false_break_risk"] <= 1.0
    assert isinstance(bridge["awareness_keep_allowed"], bool)
    assert "act_support=" in bridge["reason_summary"]
    assert "wait_pressure=" in bridge["reason_summary"]


def test_forecast_features_builder_exposes_bf2_hold_reward_bridge_summary():
    features = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        position_conflict_score=0.18,
        middle_neutrality=0.22,
        buy_continuation=0.76,
        buy_total=0.81,
        sell_total=0.22,
        buy_belief=0.68,
        sell_belief=0.16,
        buy_persistence=0.71,
        sell_persistence=0.08,
        belief_spread=0.57,
        buy_barrier=0.09,
        sell_barrier=0.23,
        middle_chop_barrier=0.12,
        conflict_barrier=0.06,
        state_metadata={
            "quality_state_label": "GOOD",
            "topdown_confluence_state": "BULL_CONFLUENCE",
            "event_risk_state": "LOW_EVENT_RISK",
            "session_exhaustion_state": "SESSION_EXHAUSTION_LOW",
            "execution_friction_state": "LOW_FRICTION",
        },
        hold_patience_gain=1.24,
    )

    bridge_root = features.metadata["bridge_first_v1"]
    bridge = bridge_root["management_hold_reward_hint_v1"]

    assert bridge_root["contract_version"] == "bridge_first_v1"
    assert bridge["contract_version"] == "management_hold_reward_hint_v1"
    assert bridge["bridge_role"] == "trade_management_hold_reward_modifier"
    assert 0.0 <= bridge["hold_reward_hint"] <= 1.0
    assert 0.0 <= bridge["edge_to_edge_tailwind"] <= 1.0
    assert isinstance(bridge["hold_patience_allowed"], bool)
    assert "hold_positive=" in bridge["reason_summary"]
    assert "hold_pressure=" in bridge["reason_summary"]


def test_forecast_features_builder_exposes_bf3_fast_cut_bridge_summary():
    features = _build_features(
        primary_label="ALIGNED_MIDDLE",
        secondary_context_label="NEUTRAL_CONTEXT",
        position_conflict_score=0.62,
        middle_neutrality=0.74,
        buy_total=0.48,
        sell_total=0.42,
        buy_belief=0.36,
        sell_belief=0.32,
        buy_persistence=0.28,
        sell_persistence=0.24,
        belief_spread=0.05,
        flip_readiness=0.58,
        belief_instability=0.72,
        buy_barrier=0.31,
        sell_barrier=0.38,
        middle_chop_barrier=0.64,
        conflict_barrier=0.56,
        fast_exit_risk_penalty=0.68,
        countertrend_penalty=0.44,
        liquidity_penalty=0.33,
        volatility_penalty=0.41,
        state_metadata={
            "event_risk_state": "HIGH_EVENT_RISK",
            "session_exhaustion_state": "SESSION_EXHAUSTION_HIGH",
            "execution_friction_state": "HIGH_FRICTION",
        },
    )

    bridge_root = features.metadata["bridge_first_v1"]
    bridge = bridge_root["management_fast_cut_risk_v1"]

    assert bridge_root["contract_version"] == "bridge_first_v1"
    assert bridge["contract_version"] == "management_fast_cut_risk_v1"
    assert bridge["bridge_role"] == "trade_management_fast_cut_modifier"
    assert 0.0 <= bridge["fast_cut_risk"] <= 1.0
    assert 0.0 <= bridge["collision_risk"] <= 1.0
    assert 0.0 <= bridge["event_caution"] <= 1.0
    assert isinstance(bridge["cut_now_allowed"], bool)
    assert "cut_pressure=" in bridge["reason_summary"]
    assert "staying_power=" in bridge["reason_summary"]


def test_forecast_features_builder_exposes_bf4_trend_maturity_bridge_summary():
    features = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        position_conflict_score=0.18,
        middle_neutrality=0.20,
        buy_continuation=0.82,
        buy_total=0.84,
        sell_total=0.18,
        buy_belief=0.72,
        sell_belief=0.12,
        buy_persistence=0.76,
        sell_persistence=0.06,
        belief_spread=0.63,
        belief_instability=0.18,
        buy_barrier=0.08,
        sell_barrier=0.20,
        middle_chop_barrier=0.10,
        conflict_barrier=0.06,
        state_metadata={
            "session_regime_state": "SESSION_EXPANSION",
            "session_expansion_state": "UP_ACTIVE_EXPANSION",
            "topdown_slope_state": "UP_SLOPE_ALIGNED",
            "topdown_confluence_state": "BULL_CONFLUENCE",
            "quality_state_label": "GOOD",
            "session_exhaustion_state": "SESSION_EXHAUSTION_LOW",
            "execution_friction_state": "LOW_FRICTION",
            "event_risk_state": "LOW_EVENT_RISK",
        },
    )

    bridge_root = features.metadata["bridge_first_v1"]
    bridge = bridge_root["trend_continuation_maturity_v1"]

    assert bridge_root["contract_version"] == "bridge_first_v1"
    assert bridge["contract_version"] == "trend_continuation_maturity_v1"
    assert bridge["bridge_role"] == "trade_management_trend_continuation_modifier"
    assert 0.0 <= bridge["continuation_maturity"] <= 1.0
    assert 0.0 <= bridge["exhaustion_pressure"] <= 1.0
    assert 0.0 <= bridge["trend_hold_confidence"] <= 1.0
    assert "continuation_positive=" in bridge["reason_summary"]
    assert "continuation_drag=" in bridge["reason_summary"]


def test_forecast_features_builder_exposes_bf5_advanced_input_reliability_bridge_summary():
    features = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.78,
        buy_total=0.80,
        buy_belief=0.70,
        buy_persistence=0.74,
        buy_barrier=0.10,
        middle_chop_barrier=0.12,
        conflict_barrier=0.08,
        state_metadata={
            "advanced_input_activation_state": "PARTIAL_ACTIVE",
            "tick_flow_state": "BURST_UP_FLOW",
            "order_book_state": "UNAVAILABLE",
            "event_risk_state": "LOW_EVENT_RISK",
        },
    )

    bridge_root = features.metadata["bridge_first_v1"]
    bridge = bridge_root["advanced_input_reliability_v1"]

    assert bridge_root["contract_version"] == "bridge_first_v1"
    assert bridge["contract_version"] == "advanced_input_reliability_v1"
    assert bridge["bridge_role"] == "advanced_input_reliability_modifier"
    assert 0.0 <= bridge["advanced_reliability"] <= 1.0
    assert bridge["order_book_reliable"] is False
    assert bridge["event_context_reliable"] is True
    assert "activation_score=" in bridge["reason_summary"]
    assert "advanced_reliability=" in bridge["reason_summary"]


def test_transition_forecast_prefers_buy_confirm_for_strong_buy_readiness():
    features = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        buy_reversal=0.86,
        buy_total=0.86,
        buy_belief=0.72,
        buy_persistence=0.68,
        belief_spread=0.70,
        buy_barrier=0.08,
        sell_barrier=0.24,
    )

    forecast = build_transition_forecast(features)

    assert forecast.p_buy_confirm > forecast.p_sell_confirm
    assert forecast.p_buy_confirm > 0.50
    assert forecast.metadata["confirm_fake_gap"] > 0.15
    assert forecast.p_reversal_success > forecast.p_continuation_success
    assert forecast.metadata["dominant_side"] == "BUY"
    assert "buy_readiness" in forecast.metadata["forecast_reasons"]["p_buy_confirm"]


def test_transition_forecast_prefers_sell_confirm_for_strong_sell_readiness():
    features = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        upper_reject_down=1.0,
        sell_reversal=0.84,
        sell_total=0.84,
        sell_belief=0.70,
        sell_persistence=0.66,
        belief_spread=-0.68,
        buy_barrier=0.22,
        sell_barrier=0.07,
    )

    forecast = build_transition_forecast(features)

    assert forecast.p_sell_confirm > forecast.p_buy_confirm
    assert forecast.metadata["confirm_fake_gap"] > 0.15
    assert forecast.p_reversal_success > forecast.p_continuation_success
    assert forecast.metadata["dominant_side"] == "SELL"


def test_transition_forecast_prefers_reversal_success_for_lower_hold_structure():
    features = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        buy_reversal=0.79,
        buy_total=0.79,
        buy_belief=0.63,
        buy_persistence=0.60,
        belief_spread=0.58,
        buy_barrier=0.11,
        sell_barrier=0.27,
        middle_chop_barrier=0.10,
        conflict_barrier=0.06,
    )

    forecast = build_transition_forecast(features)

    assert forecast.p_reversal_success > forecast.p_continuation_success
    assert forecast.p_reversal_success > 0.0
    assert forecast.metadata["reversal_continuation_gap"] > 0.10
    assert forecast.metadata["dominant_mode"] == "reversal"


def test_transition_forecast_raises_false_break_when_belief_is_weak_and_friction_is_high():
    features = _build_features(
        primary_label="ALIGNED_MIDDLE",
        secondary_context_label="NEUTRAL_CONTEXT",
        buy_continuation=0.65,
        buy_total=0.65,
        buy_belief=0.12,
        buy_persistence=0.08,
        belief_spread=0.01,
        buy_barrier=0.30,
        sell_barrier=0.30,
        middle_chop_barrier=0.88,
        conflict_barrier=0.61,
        middle_neutrality=0.94,
    )

    forecast = build_transition_forecast(features)

    assert forecast.p_false_break > 0.20
    assert forecast.metadata["component_scores"]["structural_friction"] == 0.88
    assert forecast.p_false_break > forecast.p_buy_confirm


def test_transition_competition_aware_scoring_suppresses_confirm_when_false_break_pressure_rises():
    calm_features = _build_features(
        primary_label="ALIGNED_UPPER_WEAK",
        secondary_context_label="UPPER_CONTEXT",
        upper_reject_down=1.0,
        sell_reversal=0.70,
        sell_total=0.70,
        sell_belief=0.58,
        sell_persistence=0.54,
        belief_spread=-0.46,
        buy_barrier=0.20,
        sell_barrier=0.10,
        middle_chop_barrier=0.10,
        conflict_barrier=0.08,
    )
    stressed_features = _build_features(
        primary_label="ALIGNED_UPPER_WEAK",
        secondary_context_label="UPPER_CONTEXT",
        upper_reject_down=1.0,
        sell_reversal=0.70,
        sell_total=0.70,
        sell_belief=0.18,
        sell_persistence=0.12,
        belief_spread=-0.04,
        buy_barrier=0.20,
        sell_barrier=0.10,
        middle_chop_barrier=0.82,
        conflict_barrier=0.62,
    )

    calm = build_transition_forecast(calm_features)
    stressed = build_transition_forecast(stressed_features)

    assert stressed.metadata["component_scores"]["false_break_pressure"] > calm.metadata["component_scores"]["false_break_pressure"]
    assert stressed.p_sell_confirm < calm.p_sell_confirm
    assert stressed.p_false_break > calm.p_false_break


def test_transition_forecast_reversal_structure_gets_confirm_relief_against_false_break():
    features = _build_features(
        primary_label="ALIGNED_UPPER_WEAK",
        secondary_context_label="UPPER_CONTEXT",
        upper_reject_down=1.0,
        sell_reversal=0.08,
        sell_total=0.08,
        sell_belief=0.03,
        sell_persistence=0.0,
        belief_spread=-0.03,
        buy_barrier=0.10,
        sell_barrier=0.07,
        middle_chop_barrier=0.12,
        conflict_barrier=0.03,
    )

    forecast = build_transition_forecast(features)
    scores = forecast.metadata["component_scores"]

    assert scores["sell_path_mode"] == "reversal"
    assert scores["sell_reversal_signal"] == 1.0
    assert scores["sell_reversal_path_support"] > 0.30
    assert scores["dominant_reversal_support"] > 0.30
    assert forecast.p_sell_confirm > forecast.p_false_break


def test_transition_forecast_prefers_continuation_success_for_upper_break_structure():
    features = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        upper_break_up=1.0,
        buy_continuation=0.91,
        buy_total=0.91,
        buy_belief=0.74,
        buy_persistence=0.72,
        belief_spread=0.73,
        transition_age=3,
        buy_barrier=0.06,
        sell_barrier=0.26,
    )

    forecast = build_transition_forecast(features)

    assert forecast.p_continuation_success > forecast.p_reversal_success
    assert forecast.metadata["reversal_continuation_gap"] > 0.10
    assert forecast.metadata["dominant_mode"] == "continuation"


def test_transition_forecast_edge_turn_scene_support_boosts_reversal_path():
    baseline = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        lower_hold_up=0.82,
        mid_reclaim_up=0.54,
        buy_reversal=0.74,
        buy_total=0.74,
        buy_belief=0.60,
        buy_persistence=0.58,
        belief_spread=0.52,
        buy_barrier=0.10,
        sell_barrier=0.24,
    )
    scene = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        lower_hold_up=0.82,
        mid_reclaim_up=0.54,
        buy_reversal=0.74,
        buy_total=0.74,
        buy_belief=0.60,
        buy_persistence=0.58,
        belief_spread=0.52,
        flip_readiness=0.48,
        buy_barrier=0.10,
        sell_barrier=0.24,
        state_metadata={
            "session_regime_state": "SESSION_EDGE_ROTATION",
            "topdown_confluence_state": "WEAK_CONFLUENCE",
        },
        barrier_metadata={
            "edge_turn_relief_v1": {
                "buy_relief": 0.60,
                "sell_relief": 0.0,
            },
        },
    )

    baseline_forecast = build_transition_forecast(baseline)
    scene_forecast = build_transition_forecast(scene)

    support = scene_forecast.metadata["scene_transition_support_v1"]
    usage = scene_forecast.metadata["semantic_forecast_inputs_v2_usage_v1"]

    assert support["p_edge_turn_success"] > 0.0
    assert support["edge_turn"]["buy_edge_turn_support"] > 0.0
    assert scene_forecast.p_reversal_success > baseline_forecast.p_reversal_success
    assert usage["grouped_usage"]["state_harvest"]["session_regime_state"] is True
    assert usage["grouped_usage"]["state_harvest"]["topdown_confluence_state"] is True
    assert usage["grouped_usage"]["belief_harvest"]["flip_readiness"] is True
    assert usage["grouped_usage"]["barrier_harvest"]["edge_turn_relief_v1"] is True


def test_transition_forecast_breakout_scene_support_boosts_continuation_path():
    baseline = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        upper_break_up=0.90,
        buy_continuation=0.82,
        buy_total=0.82,
        buy_belief=0.66,
        buy_persistence=0.62,
        belief_spread=0.60,
        transition_age=2,
        buy_barrier=0.08,
        sell_barrier=0.25,
    )
    scene = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        upper_break_up=0.90,
        buy_continuation=0.82,
        buy_total=0.82,
        buy_belief=0.66,
        buy_persistence=0.62,
        belief_spread=0.60,
        transition_age=2,
        buy_barrier=0.08,
        sell_barrier=0.25,
        state_metadata={
            "session_regime_state": "SESSION_EXPANSION",
            "session_expansion_state": "UP_ACTIVE_EXPANSION",
            "topdown_slope_state": "UP_SLOPE_ALIGNED",
            "topdown_confluence_state": "BULL_CONFLUENCE",
        },
        barrier_metadata={
            "breakout_fade_barrier_v1": {
                "buy_fade_barrier": 0.0,
                "sell_fade_barrier": 0.35,
            },
        },
    )

    baseline_forecast = build_transition_forecast(baseline)
    scene_forecast = build_transition_forecast(scene)

    support = scene_forecast.metadata["scene_transition_support_v1"]

    assert support["breakout_continuation"]["buy_breakout_continuation_support"] > 0.0
    assert scene_forecast.p_continuation_success > baseline_forecast.p_continuation_success


def test_transition_forecast_failed_break_scene_support_promotes_reclaim_thesis():
    baseline = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        lower_hold_up=0.68,
        lower_break_down=0.32,
        mid_reclaim_up=0.58,
        buy_reversal=0.60,
        buy_total=0.60,
        buy_belief=0.56,
        buy_persistence=0.48,
        belief_spread=0.41,
        buy_barrier=0.10,
        sell_barrier=0.22,
    )
    scene = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        lower_hold_up=0.68,
        lower_break_down=0.32,
        mid_reclaim_up=0.58,
        buy_reversal=0.60,
        buy_total=0.60,
        buy_belief=0.56,
        buy_persistence=0.48,
        belief_spread=0.41,
        flip_readiness=0.55,
        belief_instability=0.28,
        buy_barrier=0.10,
        sell_barrier=0.22,
        barrier_metadata={
            "duplicate_edge_barrier_v1": {
                "common_boost": 0.08,
                "buy_side_boost": 0.0,
                "sell_side_boost": 0.0,
            },
            "micro_trap_barrier_v1": {
                "common_boost": 0.06,
                "buy_side_boost": 0.0,
                "sell_side_boost": 0.0,
            },
        },
    )

    baseline_forecast = build_transition_forecast(baseline)
    scene_forecast = build_transition_forecast(scene)

    support = scene_forecast.metadata["scene_transition_support_v1"]

    assert support["p_failed_breakdown_reclaim"] > 0.0
    assert scene_forecast.p_reversal_success > baseline_forecast.p_reversal_success


def test_transition_forecast_suppresses_continuation_confirm_for_wait_like_upper_edge_observe_structure():
    features = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        upper_reject_down=0.72,
        upper_break_up=1.0,
        sell_reversal=0.62,
        buy_continuation=0.95,
        buy_total=0.95,
        sell_total=0.62,
        buy_belief=0.42,
        buy_persistence=0.20,
        belief_spread=0.41,
        transition_age=1,
        buy_barrier=0.0,
        sell_barrier=0.04,
        middle_chop_barrier=0.16,
        conflict_barrier=0.0,
    )

    forecast = build_transition_forecast(features)
    scores = forecast.metadata["component_scores"]

    assert scores["buy_path_mode"] == "continuation"
    assert scores["buy_confirm_path_gate"] < 0.20
    assert forecast.p_buy_confirm < 0.15
    assert forecast.p_false_break > forecast.p_buy_confirm


def test_context_classifier_engine_bundle_exposes_transition_forecast():
    classifier = ContextClassifier()
    bundle = classifier.build_engine_context_snapshot(
        symbol="BTCUSD",
        tick=type("Tick", (), {"bid": 100.0, "ask": 100.2})(),
        df_all={},
        scorer=None,
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        spread_ratio=0.02,
        box_state="MIDDLE",
        bb_state="MID",
        raw_scores={"buy_score": 10.0, "sell_score": 8.0},
    )

    forecast = bundle["transition_forecast"]

    assert isinstance(forecast, TransitionForecast)
    assert forecast.metadata["forecast_contract"] == "transition_forecast_v1"
    assert forecast.metadata["features_contract"] == "forecast_features_v1"
    assert forecast.metadata["engine_name"] == "ForecastRuleV1"
    assert forecast.metadata["baseline_contract"]["baseline_role"] == "shadow_baseline"
    assert forecast.metadata["baseline_contract"]["score_semantics"] == "scenario_score"
    assert forecast.metadata["baseline_contract"]["shadow_ready"] is True


def test_trade_management_forecast_exposes_exact_canonical_fields():
    payload = TradeManagementForecast().to_dict()

    assert set(payload.keys()) == {
        "p_continue_favor",
        "p_fail_now",
        "p_recover_after_pullback",
        "p_reach_tp1",
        "p_opposite_edge_reach",
        "p_better_reentry_if_cut",
        "metadata",
    }


def test_trade_management_forecast_prefers_continue_when_same_side_strength_is_high():
    features = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.88,
        buy_total=0.88,
        buy_belief=0.74,
        buy_persistence=0.72,
        belief_spread=0.71,
        buy_barrier=0.08,
        sell_barrier=0.24,
        middle_chop_barrier=0.12,
        conflict_barrier=0.05,
        middle_neutrality=0.18,
    )

    forecast = build_trade_management_forecast(features)

    assert forecast.p_continue_favor > forecast.p_fail_now
    assert forecast.p_continue_favor > 0.40
    assert forecast.metadata["continue_fail_gap"] > 0.10
    assert forecast.p_continue_favor > forecast.p_better_reentry_if_cut
    assert forecast.metadata["dominant_side"] == "BUY"


def test_trade_management_forecast_prefers_fail_now_when_opposing_strength_and_friction_rise():
    features = _build_features(
        primary_label="ALIGNED_MIDDLE",
        secondary_context_label="NEUTRAL_CONTEXT",
        buy_total=0.36,
        sell_total=0.33,
        buy_belief=0.18,
        sell_belief=0.16,
        buy_persistence=0.10,
        sell_persistence=0.08,
        belief_spread=0.02,
        buy_barrier=0.33,
        sell_barrier=0.30,
        middle_chop_barrier=0.84,
        conflict_barrier=0.60,
        middle_neutrality=0.92,
    )

    forecast = build_trade_management_forecast(features)

    assert forecast.p_fail_now > forecast.p_continue_favor
    assert forecast.metadata["continue_fail_gap"] < 0.0
    assert forecast.p_better_reentry_if_cut > 0.0


def test_trade_management_competition_aware_scoring_suppresses_continue_when_fail_pressure_rises():
    stable_features = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        buy_reversal=0.76,
        buy_total=0.76,
        buy_belief=0.66,
        buy_persistence=0.68,
        belief_spread=0.60,
        buy_barrier=0.08,
        sell_barrier=0.24,
        middle_chop_barrier=0.10,
        conflict_barrier=0.06,
        middle_neutrality=0.18,
    )
    pressured_features = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        buy_reversal=0.76,
        buy_total=0.76,
        sell_total=0.34,
        buy_belief=0.34,
        sell_belief=0.22,
        buy_persistence=0.18,
        sell_persistence=0.12,
        belief_spread=0.06,
        buy_barrier=0.20,
        sell_barrier=0.28,
        middle_chop_barrier=0.72,
        conflict_barrier=0.56,
        middle_neutrality=0.74,
    )

    stable = build_trade_management_forecast(stable_features)
    pressured = build_trade_management_forecast(pressured_features)

    assert pressured.metadata["component_scores"]["fail_pressure"] > stable.metadata["component_scores"]["fail_pressure"]
    assert pressured.p_continue_favor < stable.p_continue_favor
    assert pressured.p_fail_now > stable.p_fail_now


def test_trade_management_forecast_raises_recover_after_pullback_when_belief_persists():
    features = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        buy_reversal=0.72,
        buy_total=0.72,
        buy_belief=0.66,
        buy_persistence=0.80,
        belief_spread=0.62,
        buy_barrier=0.10,
        sell_barrier=0.22,
        middle_chop_barrier=0.15,
        conflict_barrier=0.08,
        middle_neutrality=0.22,
    )

    forecast = build_trade_management_forecast(features)

    assert forecast.p_recover_after_pullback > 0.30
    assert forecast.p_recover_after_pullback > forecast.p_better_reentry_if_cut
    assert forecast.metadata["recover_reentry_gap"] > 0.0
    assert forecast.p_reach_tp1 > 0.0


def test_trade_management_scene_support_boosts_hold_for_good_entry_noise_hold():
    baseline = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        buy_reversal=0.74,
        buy_total=0.74,
        buy_belief=0.66,
        buy_persistence=0.68,
        belief_spread=0.58,
        buy_barrier=0.10,
        sell_barrier=0.22,
        middle_chop_barrier=0.18,
        conflict_barrier=0.08,
        middle_neutrality=0.30,
    )
    scene = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        buy_reversal=0.74,
        buy_total=0.74,
        buy_belief=0.66,
        buy_persistence=0.68,
        belief_spread=0.58,
        buy_barrier=0.10,
        sell_barrier=0.22,
        middle_chop_barrier=0.18,
        conflict_barrier=0.08,
        middle_neutrality=0.30,
        state_metadata={
            "execution_friction_state": "MEDIUM_FRICTION",
        },
        barrier_metadata={
            "middle_chop_barrier_v2": {
                "scene_boost": 0.12,
                "execution_friction_state": "MEDIUM_FRICTION",
                "volume_participation_state": "THIN_PARTICIPATION",
            },
        },
    )
    scene.state_vector_v2.hold_patience_gain = 1.28
    scene.state_vector_v2.fast_exit_risk_penalty = 0.12
    scene.belief_state_v1.buy_streak = 3

    baseline_forecast = build_trade_management_forecast(baseline)
    scene_forecast = build_trade_management_forecast(scene)

    support = scene_forecast.metadata["management_scene_support_v1"]

    assert support["p_hold_through_noise"] > 0.0
    assert scene_forecast.p_fail_now <= baseline_forecast.p_fail_now
    assert scene_forecast.p_recover_after_pullback > baseline_forecast.p_recover_after_pullback


def test_trade_management_scene_support_detects_premature_exit_risk_under_middle_noise():
    features = _build_features(
        primary_label="ALIGNED_MIDDLE",
        secondary_context_label="NEUTRAL_CONTEXT",
        buy_total=0.62,
        buy_belief=0.58,
        buy_persistence=0.60,
        belief_spread=0.56,
        buy_barrier=0.18,
        sell_barrier=0.24,
        middle_chop_barrier=0.62,
        conflict_barrier=0.22,
        middle_neutrality=0.80,
        state_metadata={
            "execution_friction_state": "HIGH_FRICTION",
        },
        barrier_metadata={
            "middle_chop_barrier_v2": {
                "scene_boost": 0.24,
                "execution_friction_state": "HIGH_FRICTION",
                "volume_participation_state": "THIN_PARTICIPATION",
            },
        },
    )
    features.state_vector_v2.hold_patience_gain = 1.18
    features.state_vector_v2.fast_exit_risk_penalty = 0.46
    features.belief_state_v1.dominant_side = "BUY"
    features.belief_state_v1.buy_streak = 2

    forecast = build_trade_management_forecast(features)
    support = forecast.metadata["management_scene_support_v1"]

    assert support["p_premature_exit_risk"] > 0.0
    assert support["premature_exit"]["execution_friction_state"] == "HIGH_FRICTION"


def test_trade_management_scene_support_scores_flip_after_exit_quality_for_clean_reentry():
    baseline = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        sell_reversal=0.58,
        sell_total=0.58,
        sell_belief=0.54,
        sell_persistence=0.46,
        belief_spread=-0.36,
        buy_barrier=0.24,
        sell_barrier=0.10,
        middle_chop_barrier=0.20,
        conflict_barrier=0.08,
        middle_neutrality=0.28,
    )
    scene = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        sell_reversal=0.58,
        sell_total=0.58,
        sell_belief=0.54,
        sell_persistence=0.46,
        belief_spread=-0.36,
        flip_readiness=0.58,
        belief_instability=0.22,
        buy_barrier=0.24,
        sell_barrier=0.10,
        middle_chop_barrier=0.20,
        conflict_barrier=0.08,
        middle_neutrality=0.28,
        barrier_metadata={
            "duplicate_edge_barrier_v1": {
                "common_boost": 0.02,
                "buy_side_boost": 0.0,
                "sell_side_boost": 0.0,
            },
            "post_event_cooldown_barrier_v1": {
                "common_boost": 0.0,
                "event_risk_state": "LOW_EVENT_RISK",
            },
        },
    )
    scene.belief_state_v1.dominant_side = "SELL"
    scene.belief_state_v1.sell_streak = 2

    baseline_forecast = build_trade_management_forecast(baseline)
    scene_forecast = build_trade_management_forecast(scene)

    support = scene_forecast.metadata["management_scene_support_v1"]

    assert support["p_flip_after_exit_quality"] > 0.0
    assert scene_forecast.p_better_reentry_if_cut > baseline_forecast.p_better_reentry_if_cut


def test_trade_management_forecast_bf2_hold_reward_bridge_boosts_continue_path():
    baseline = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.76,
        buy_total=0.81,
        sell_total=0.22,
        buy_belief=0.68,
        sell_belief=0.16,
        buy_persistence=0.71,
        sell_persistence=0.08,
        belief_spread=0.57,
        buy_barrier=0.09,
        sell_barrier=0.23,
        middle_chop_barrier=0.12,
        conflict_barrier=0.06,
        position_conflict_score=0.18,
        middle_neutrality=0.22,
    )
    bridged = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.76,
        buy_total=0.81,
        sell_total=0.22,
        buy_belief=0.68,
        sell_belief=0.16,
        buy_persistence=0.71,
        sell_persistence=0.08,
        belief_spread=0.57,
        buy_barrier=0.09,
        sell_barrier=0.23,
        middle_chop_barrier=0.12,
        conflict_barrier=0.06,
        position_conflict_score=0.18,
        middle_neutrality=0.22,
        state_metadata={
            "quality_state_label": "GOOD",
            "topdown_confluence_state": "BULL_CONFLUENCE",
            "event_risk_state": "LOW_EVENT_RISK",
            "session_exhaustion_state": "SESSION_EXHAUSTION_LOW",
            "execution_friction_state": "LOW_FRICTION",
        },
        hold_patience_gain=1.24,
    )

    baseline_forecast = build_trade_management_forecast(baseline)
    bridged_forecast = build_trade_management_forecast(bridged)

    assert bridged_forecast.p_continue_favor > baseline_forecast.p_continue_favor
    assert bridged_forecast.p_reach_tp1 > baseline_forecast.p_reach_tp1
    assert bridged_forecast.p_opposite_edge_reach > baseline_forecast.p_opposite_edge_reach


def test_trade_management_forecast_bf3_fast_cut_bridge_boosts_fail_and_reentry_path():
    baseline = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.74,
        buy_total=0.78,
        sell_total=0.24,
        buy_belief=0.66,
        sell_belief=0.18,
        buy_persistence=0.68,
        sell_persistence=0.10,
        belief_spread=0.48,
        flip_readiness=0.18,
        belief_instability=0.18,
        buy_barrier=0.12,
        sell_barrier=0.26,
        middle_chop_barrier=0.14,
        conflict_barrier=0.08,
        position_conflict_score=0.20,
        middle_neutrality=0.24,
        fast_exit_risk_penalty=0.10,
        countertrend_penalty=0.08,
        liquidity_penalty=0.05,
        volatility_penalty=0.06,
        state_metadata={
            "event_risk_state": "LOW_EVENT_RISK",
            "session_exhaustion_state": "SESSION_EXHAUSTION_LOW",
            "execution_friction_state": "LOW_FRICTION",
        },
    )
    bridged = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.74,
        buy_total=0.78,
        sell_total=0.24,
        buy_belief=0.66,
        sell_belief=0.18,
        buy_persistence=0.68,
        sell_persistence=0.10,
        belief_spread=0.48,
        flip_readiness=0.62,
        belief_instability=0.76,
        buy_barrier=0.30,
        sell_barrier=0.42,
        middle_chop_barrier=0.66,
        conflict_barrier=0.58,
        position_conflict_score=0.61,
        middle_neutrality=0.73,
        fast_exit_risk_penalty=0.72,
        countertrend_penalty=0.48,
        liquidity_penalty=0.36,
        volatility_penalty=0.44,
        state_metadata={
            "event_risk_state": "HIGH_EVENT_RISK",
            "session_exhaustion_state": "SESSION_EXHAUSTION_HIGH",
            "execution_friction_state": "HIGH_FRICTION",
        },
    )

    baseline_forecast = build_trade_management_forecast(baseline)
    bridged_forecast = build_trade_management_forecast(bridged)

    assert bridged_forecast.p_fail_now > baseline_forecast.p_fail_now
    assert bridged_forecast.p_better_reentry_if_cut > baseline_forecast.p_better_reentry_if_cut
    assert bridged_forecast.p_continue_favor < baseline_forecast.p_continue_favor


def test_trade_management_forecast_bf4_trend_bridge_boosts_continue_and_reach_path():
    baseline = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.74,
        buy_total=0.79,
        sell_total=0.20,
        buy_belief=0.67,
        sell_belief=0.14,
        buy_persistence=0.70,
        sell_persistence=0.08,
        belief_spread=0.54,
        belief_instability=0.26,
        buy_barrier=0.12,
        sell_barrier=0.24,
        middle_chop_barrier=0.16,
        conflict_barrier=0.10,
        position_conflict_score=0.24,
        middle_neutrality=0.28,
        state_metadata={
            "session_regime_state": "SESSION_EDGE_ROTATION",
            "session_expansion_state": "",
            "topdown_slope_state": "FLAT_SLOPE",
            "topdown_confluence_state": "WEAK_CONFLUENCE",
            "quality_state_label": "NORMAL_QUALITY",
            "session_exhaustion_state": "SESSION_EXHAUSTION_RISING",
            "execution_friction_state": "MEDIUM_FRICTION",
            "event_risk_state": "WATCH_EVENT_RISK",
        },
    )
    bridged = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.82,
        buy_total=0.84,
        sell_total=0.18,
        buy_belief=0.73,
        sell_belief=0.10,
        buy_persistence=0.78,
        sell_persistence=0.04,
        belief_spread=0.64,
        belief_instability=0.14,
        buy_barrier=0.08,
        sell_barrier=0.20,
        middle_chop_barrier=0.10,
        conflict_barrier=0.06,
        position_conflict_score=0.16,
        middle_neutrality=0.18,
        state_metadata={
            "session_regime_state": "SESSION_EXPANSION",
            "session_expansion_state": "UP_ACTIVE_EXPANSION",
            "topdown_slope_state": "UP_SLOPE_ALIGNED",
            "topdown_confluence_state": "BULL_CONFLUENCE",
            "quality_state_label": "GOOD",
            "session_exhaustion_state": "SESSION_EXHAUSTION_LOW",
            "execution_friction_state": "LOW_FRICTION",
            "event_risk_state": "LOW_EVENT_RISK",
        },
    )

    baseline_forecast = build_trade_management_forecast(baseline)
    bridged_forecast = build_trade_management_forecast(bridged)

    assert bridged_forecast.p_continue_favor > baseline_forecast.p_continue_favor
    assert bridged_forecast.p_reach_tp1 > baseline_forecast.p_reach_tp1
    assert bridged_forecast.p_opposite_edge_reach > baseline_forecast.p_opposite_edge_reach


def test_trade_management_forecast_bf5_reliability_bridge_strengthens_trend_effect_when_inputs_are_available():
    baseline = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.82,
        buy_total=0.84,
        sell_total=0.16,
        buy_belief=0.72,
        sell_belief=0.10,
        buy_persistence=0.78,
        sell_persistence=0.04,
        belief_spread=0.63,
        belief_instability=0.14,
        buy_barrier=0.08,
        sell_barrier=0.20,
        middle_chop_barrier=0.10,
        conflict_barrier=0.06,
        position_conflict_score=0.16,
        middle_neutrality=0.18,
        state_metadata={
            "session_regime_state": "SESSION_EXPANSION",
            "session_expansion_state": "UP_ACTIVE_EXPANSION",
            "topdown_slope_state": "UP_SLOPE_ALIGNED",
            "topdown_confluence_state": "BULL_CONFLUENCE",
            "quality_state_label": "GOOD",
            "session_exhaustion_state": "SESSION_EXHAUSTION_LOW",
            "execution_friction_state": "LOW_FRICTION",
            "event_risk_state": "LOW_EVENT_RISK",
        },
    )
    bridged = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.82,
        buy_total=0.84,
        sell_total=0.16,
        buy_belief=0.72,
        sell_belief=0.10,
        buy_persistence=0.78,
        sell_persistence=0.04,
        belief_spread=0.63,
        belief_instability=0.14,
        buy_barrier=0.08,
        sell_barrier=0.20,
        middle_chop_barrier=0.10,
        conflict_barrier=0.06,
        position_conflict_score=0.16,
        middle_neutrality=0.18,
        state_metadata={
            "session_regime_state": "SESSION_EXPANSION",
            "session_expansion_state": "UP_ACTIVE_EXPANSION",
            "topdown_slope_state": "UP_SLOPE_ALIGNED",
            "topdown_confluence_state": "BULL_CONFLUENCE",
            "quality_state_label": "GOOD",
            "session_exhaustion_state": "SESSION_EXHAUSTION_LOW",
            "execution_friction_state": "LOW_FRICTION",
            "event_risk_state": "LOW_EVENT_RISK",
            "advanced_input_activation_state": "PARTIAL_ACTIVE",
            "tick_flow_state": "BURST_UP_FLOW",
            "order_book_state": "UNAVAILABLE",
        },
    )

    baseline_forecast = build_trade_management_forecast(baseline)
    bridged_forecast = build_trade_management_forecast(bridged)

    assert bridged_forecast.p_continue_favor > baseline_forecast.p_continue_favor
    assert bridged_forecast.p_reach_tp1 > baseline_forecast.p_reach_tp1
    assert bridged_forecast.metadata["bridge_first_v1"]["advanced_input_reliability_v1"]["event_context_reliable"] is True


def test_context_classifier_engine_bundle_exposes_trade_management_forecast():
    classifier = ContextClassifier()
    bundle = classifier.build_engine_context_snapshot(
        symbol="BTCUSD",
        tick=type("Tick", (), {"bid": 100.0, "ask": 100.2})(),
        df_all={},
        scorer=None,
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        spread_ratio=0.02,
        box_state="MIDDLE",
        bb_state="MID",
        raw_scores={"buy_score": 10.0, "sell_score": 8.0},
    )

    forecast = bundle["trade_management_forecast"]

    assert isinstance(forecast, TradeManagementForecast)
    assert forecast.metadata["forecast_contract"] == "trade_management_forecast_v1"
    assert forecast.metadata["features_contract"] == "forecast_features_v1"
    assert forecast.metadata["engine_name"] == "ForecastRuleV1"
    assert forecast.metadata["baseline_contract"]["baseline_role"] == "shadow_baseline"
    assert forecast.metadata["baseline_contract"]["comparison_target_contract"] == "ForecastModelV1"


def test_context_classifier_engine_bundle_exposes_full_forecast_bundle():
    classifier = ContextClassifier()
    bundle = classifier.build_engine_context_snapshot(
        symbol="BTCUSD",
        tick=type("Tick", (), {"bid": 100.0, "ask": 100.2})(),
        df_all={},
        scorer=None,
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        spread_ratio=0.02,
        box_state="MIDDLE",
        bb_state="MID",
        raw_scores={"buy_score": 10.0, "sell_score": 8.0},
    )

    assert isinstance(bundle["forecast_features"], ForecastFeaturesV1)
    assert isinstance(bundle["transition_forecast"], TransitionForecast)
    assert isinstance(bundle["trade_management_forecast"], TradeManagementForecast)


def test_default_forecast_engine_is_rule_v1():
    engine = get_default_forecast_engine()

    assert isinstance(engine, ForecastRuleV1)


def test_rule_forecast_baseline_contract_is_explicit_and_non_probabilistic():
    features = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.74,
        buy_total=0.74,
        buy_belief=0.58,
        buy_persistence=0.52,
        belief_spread=0.55,
        buy_barrier=0.09,
    )

    transition = build_transition_forecast(features)
    management = build_trade_management_forecast(features)

    for forecast in (transition, management):
        baseline = forecast.metadata["baseline_contract"]
        assert baseline["baseline_contract"] == "forecast_rule_baseline_v1"
        assert baseline["baseline_name"] == "ForecastRuleV1"
        assert baseline["baseline_role"] == "shadow_baseline"
        assert baseline["score_semantics"] == "scenario_score"
        assert baseline["calibrated_probability"] is False
        assert baseline["shadow_ready"] is True
        assert baseline["comparison_target_contract"] == "ForecastModelV1"


def test_transition_forecast_metadata_contract_is_explicit_and_explanatory():
    features = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        buy_reversal=0.82,
        buy_total=0.82,
        buy_belief=0.67,
        buy_persistence=0.61,
        belief_spread=0.64,
        buy_barrier=0.09,
        sell_barrier=0.28,
        middle_chop_barrier=0.11,
        conflict_barrier=0.07,
    )

    forecast = build_transition_forecast(features)
    metadata = forecast.metadata

    assert "side_separation" in metadata
    assert "confirm_fake_gap" in metadata
    assert "reversal_continuation_gap" in metadata
    assert metadata["side_separation"] == abs(forecast.p_buy_confirm - forecast.p_sell_confirm)
    assert metadata["confirm_fake_gap"] == max(forecast.p_buy_confirm, forecast.p_sell_confirm) - forecast.p_false_break
    assert metadata["reversal_continuation_gap"] == abs(
        forecast.p_reversal_success - forecast.p_continuation_success
    )

    assert {
        "forecast_contract",
        "mapper_version",
        "score_formula_version",
        "features_contract",
        "scene_transition_support_v1",
        "component_scores",
        "dominant_side",
        "dominant_mode",
        "gap_reasons",
        "forecast_reasons",
    }.issubset(metadata.keys())
    assert metadata["mapper_version"] == "transition_forecast_v1_fc11"
    assert metadata["semantic_owner_contract"] == "forecast_branch_interpretation_only_v1"
    assert metadata["forecast_freeze_phase"] == "FR0"
    assert metadata["forecast_pre_ml_phase"] == "FR10"
    assert metadata["forecast_branch_role"] == "transition_branch"
    assert metadata["pre_ml_readiness_contract_v1"]["contract_version"] == "forecast_pre_ml_readiness_v1"
    assert metadata["pre_ml_readiness_contract_v1"]["ml_usage_role"] == "feature_only_not_owner"
    assert metadata["pre_ml_readiness_contract_v1"]["owner_collision_allowed"] is False
    assert metadata["pre_ml_readiness_contract_v1"]["semantic_owner_override_allowed"] is False
    assert metadata["pre_ml_readiness_contract_v1"]["explainable_without_ml"] is True
    assert metadata["pre_ml_required_feature_values_v1"]["p_buy_confirm"] == forecast.p_buy_confirm
    assert metadata["pre_ml_required_feature_values_v1"]["p_sell_confirm"] == forecast.p_sell_confirm
    assert metadata["pre_ml_required_feature_values_v1"]["p_reversal_success"] == forecast.p_reversal_success
    assert metadata["pre_ml_required_feature_values_v1"]["p_continuation"] == forecast.p_continuation_success
    assert metadata["pre_ml_required_feature_values_v1"]["p_false_break"] == forecast.p_false_break
    assert metadata["pre_ml_recommended_feature_values_v1"]["edge_turn_success"] == metadata["scene_transition_support_v1"]["p_edge_turn_success"]
    assert {entry["public_name"] for entry in metadata["pre_ml_readiness_contract_v1"]["required_feature_fields_v1"]} == {
        "p_buy_confirm",
        "p_sell_confirm",
        "p_reversal_success",
        "p_continuation",
        "p_false_break",
    }
    assert {entry["public_name"] for entry in metadata["pre_ml_readiness_contract_v1"]["recommended_feature_fields_v1"]} == {
        "edge_turn_success",
    }
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["contract_version"] == "semantic_forecast_inputs_v2_usage_v1"
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["usage_status"] == "harvested_with_usage_trace"
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["state_harvest"]["session_regime_state"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["belief_harvest"]["flip_readiness"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["barrier_harvest"]["edge_turn_relief_v1"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["secondary_harvest"]["advanced_input_activation_state"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["secondary_harvest"]["tick_flow_state"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["secondary_harvest"]["order_book_state"] is True
    assert metadata["direct_action_creator_allowed"] is False
    assert metadata["execution_side_creator_allowed"] is False
    assert metadata["summary_side_metadata_allowed"] is True
    assert metadata["summary_mode_metadata_allowed"] is True
    assert metadata["score_formula_version"] == "transition_fc11_scene_transition_refinement_v1"
    assert metadata["bridge_first_v1"]["advanced_input_reliability_v1"]["contract_version"] == "advanced_input_reliability_v1"
    assert set(metadata["scene_transition_support_v1"].keys()) == {
        "p_edge_turn_success",
        "p_failed_breakdown_reclaim",
        "p_failed_breakout_flush",
        "p_continuation_exhaustion",
        "edge_turn",
        "breakout_continuation",
        "failed_break",
    }
    assert metadata["competition_mode"] == "confirm_vs_false_break"
    assert metadata["mode_competition_mode"] == "reversal_vs_continuation"
    assert metadata["compression_mode"] == "core_multiplicative_support_additive"
    assert "false_break_pressure" in metadata["component_scores"]
    assert "buy_confirm_readiness" in metadata["component_scores"]
    assert "sell_confirm_readiness" in metadata["component_scores"]
    assert "buy_confirm_core" in metadata["component_scores"]
    assert "buy_confirm_support" in metadata["component_scores"]
    assert "buy_confirm_momentum" in metadata["component_scores"]
    assert "dominant_persistence" in metadata["component_scores"]
    assert "buy_confirm_path_gate" in metadata["component_scores"]
    assert "buy_continuation_observe_gate" in metadata["component_scores"]
    assert "transition_age_norm" in metadata["component_scores"]
    assert "sell_reversal_signal" in metadata["component_scores"]
    assert "sell_reversal_path_support" in metadata["component_scores"]
    assert "dominant_reversal_support" in metadata["component_scores"]
    assert "buy_edge_turn_support" in metadata["component_scores"]
    assert "sell_edge_turn_support" in metadata["component_scores"]
    assert "buy_breakout_scene_support" in metadata["component_scores"]
    assert "sell_breakout_scene_support" in metadata["component_scores"]
    assert "p_edge_turn_success" in metadata["component_scores"]
    assert "p_failed_breakdown_reclaim" in metadata["component_scores"]
    assert "p_failed_breakout_flush" in metadata["component_scores"]
    assert "p_continuation_exhaustion" in metadata["component_scores"]
    assert "reversal_support" in metadata["component_scores"]
    assert "reversal_competition_pressure" in metadata["component_scores"]
    assert "continuation_support" in metadata["component_scores"]
    assert "continuation_competition_pressure" in metadata["component_scores"]
    assert set(metadata["forecast_reasons"].keys()) == {
        "p_buy_confirm",
        "p_sell_confirm",
        "p_false_break",
        "p_reversal_success",
        "p_continuation_success",
    }
    assert set(metadata["gap_reasons"].keys()) == {
        "side_separation",
        "confirm_fake_gap",
        "reversal_continuation_gap",
    }
    assert "confirm_fake_gap=" in metadata["gap_reasons"]["confirm_fake_gap"]
    assert "reversal_continuation_gap=" in metadata["gap_reasons"]["reversal_continuation_gap"]
    assert "buy_total_evidence" in metadata["forecast_reasons"]["p_buy_confirm"]
    assert "buy_belief" in metadata["forecast_reasons"]["p_buy_confirm"]
    assert "buy_barrier" in metadata["forecast_reasons"]["p_buy_confirm"]
    assert "buy_confirm_core" in metadata["forecast_reasons"]["p_buy_confirm"]
    assert "buy_confirm_support" in metadata["forecast_reasons"]["p_buy_confirm"]
    assert "buy_confirm_momentum" in metadata["forecast_reasons"]["p_buy_confirm"]
    assert "buy_confirm_path_support" in metadata["forecast_reasons"]["p_buy_confirm"]
    assert "false_break_pressure" in metadata["forecast_reasons"]["p_buy_confirm"]
    assert "middle_chop_barrier" in metadata["forecast_reasons"]["p_false_break"]
    assert "conflict_barrier" in metadata["forecast_reasons"]["p_false_break"]
    assert "dominant_persistence" in metadata["forecast_reasons"]["p_false_break"]
    assert "dominant_reversal_support" in metadata["forecast_reasons"]["p_false_break"]
    assert "false_break_pressure" in metadata["forecast_reasons"]["p_false_break"]
    assert "bf5_advanced_reliability" in metadata["forecast_reasons"]["p_false_break"]
    assert "buy_reversal_core" in metadata["forecast_reasons"]["p_reversal_success"]
    assert "reversal_support" in metadata["forecast_reasons"]["p_reversal_success"]
    assert "reversal_competition_pressure" in metadata["forecast_reasons"]["p_reversal_success"]
    assert "buy_continuation_core" in metadata["forecast_reasons"]["p_continuation_success"]
    assert "continuation_support" in metadata["forecast_reasons"]["p_continuation_success"]
    assert "continuation_competition_pressure" in metadata["forecast_reasons"]["p_continuation_success"]


def test_transition_forecast_metadata_includes_bf1_bridge_reasoning():
    features = _build_features(
        primary_label="ALIGNED_MIDDLE",
        secondary_context_label="NEUTRAL_CONTEXT",
        position_conflict_score=0.41,
        middle_neutrality=0.66,
        buy_continuation=0.58,
        buy_total=0.72,
        sell_total=0.28,
        buy_belief=0.62,
        sell_belief=0.18,
        buy_persistence=0.59,
        sell_persistence=0.12,
        belief_spread=0.44,
        buy_barrier=0.12,
        sell_barrier=0.24,
        middle_chop_barrier=0.21,
        conflict_barrier=0.14,
        state_metadata={
            "quality_state_label": "GOOD",
            "topdown_confluence_state": "BULL_CONFLUENCE",
            "execution_friction_state": "LOW_FRICTION",
        },
    )

    forecast = build_transition_forecast(features)
    bridge = forecast.metadata["bridge_first_v1"]["act_vs_wait_bias_v1"]
    scores = forecast.metadata["component_scores"]
    reason = forecast.metadata["forecast_reasons"]["p_false_break"]

    assert bridge["contract_version"] == "act_vs_wait_bias_v1"
    assert abs(scores["bf1_act_vs_wait_bias"] - bridge["act_vs_wait_bias"]) < 1e-9
    assert abs(scores["bf1_false_break_risk"] - bridge["false_break_risk"]) < 1e-9
    assert scores["bf1_awareness_keep_allowed"] == bridge["awareness_keep_allowed"]
    assert "bf5_advanced_reliability" in scores
    assert "bf1_act_vs_wait_bias" in reason
    assert "bf1_false_break_risk" in reason
    assert "bf1_awareness_keep_allowed" in reason
    assert "bf5_advanced_reliability" in reason


def test_trade_management_forecast_metadata_contract_is_explicit_and_explanatory():
    features = _build_features(
        primary_label="ALIGNED_UPPER_STRONG",
        secondary_context_label="UPPER_CONTEXT",
        buy_continuation=0.84,
        buy_total=0.84,
        buy_belief=0.69,
        buy_persistence=0.64,
        belief_spread=0.58,
        buy_barrier=0.08,
        sell_barrier=0.26,
        middle_chop_barrier=0.14,
        conflict_barrier=0.09,
        middle_neutrality=0.21,
    )

    forecast = build_trade_management_forecast(features)
    metadata = forecast.metadata

    assert "continue_fail_gap" in metadata
    assert "recover_reentry_gap" in metadata
    assert metadata["continue_fail_gap"] == forecast.p_continue_favor - forecast.p_fail_now
    assert metadata["recover_reentry_gap"] == (
        forecast.p_recover_after_pullback - forecast.p_better_reentry_if_cut
    )

    assert {
        "forecast_contract",
        "mapper_version",
        "score_formula_version",
        "features_contract",
        "management_scene_support_v1",
        "component_scores",
        "dominant_side",
        "dominant_mode",
        "gap_reasons",
        "forecast_reasons",
    }.issubset(metadata.keys())
    assert metadata["mapper_version"] == "trade_management_forecast_v1_fc9"
    assert metadata["semantic_owner_contract"] == "forecast_branch_interpretation_only_v1"
    assert metadata["forecast_freeze_phase"] == "FR0"
    assert metadata["forecast_pre_ml_phase"] == "FR10"
    assert metadata["forecast_branch_role"] == "trade_management_branch"
    assert metadata["pre_ml_readiness_contract_v1"]["contract_version"] == "forecast_pre_ml_readiness_v1"
    assert metadata["pre_ml_readiness_contract_v1"]["ml_usage_role"] == "feature_only_not_owner"
    assert metadata["pre_ml_readiness_contract_v1"]["owner_collision_allowed"] is False
    assert metadata["pre_ml_required_feature_values_v1"]["p_continue_favor"] == forecast.p_continue_favor
    assert metadata["pre_ml_required_feature_values_v1"]["p_fail_now"] == forecast.p_fail_now
    assert metadata["pre_ml_required_feature_values_v1"]["p_reach_tp1"] == forecast.p_reach_tp1
    assert metadata["pre_ml_required_feature_values_v1"]["p_better_reentry_if_cut"] == forecast.p_better_reentry_if_cut
    assert metadata["pre_ml_required_feature_values_v1"]["p_recover_after_pullback"] == forecast.p_recover_after_pullback
    assert metadata["pre_ml_recommended_feature_values_v1"]["premature_exit_risk"] == metadata["management_scene_support_v1"]["p_premature_exit_risk"]
    assert {entry["public_name"] for entry in metadata["pre_ml_readiness_contract_v1"]["required_feature_fields_v1"]} == {
        "p_continue_favor",
        "p_fail_now",
        "p_reach_tp1",
        "p_better_reentry_if_cut",
        "p_recover_after_pullback",
    }
    assert {entry["public_name"] for entry in metadata["pre_ml_readiness_contract_v1"]["recommended_feature_fields_v1"]} == {
        "premature_exit_risk",
    }
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["contract_version"] == "semantic_forecast_inputs_v2_usage_v1"
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["usage_status"] == "harvested_with_usage_trace"
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["belief_harvest"]["dominant_side"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["belief_harvest"]["flip_readiness"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["barrier_harvest"]["middle_chop_barrier_v2"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["barrier_harvest"]["post_event_cooldown_barrier_v1"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["secondary_harvest"]["advanced_input_activation_state"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["secondary_harvest"]["tick_flow_state"] is True
    assert metadata["semantic_forecast_inputs_v2_usage_v1"]["grouped_usage"]["secondary_harvest"]["order_book_state"] is True
    assert metadata["direct_action_creator_allowed"] is False
    assert metadata["execution_side_creator_allowed"] is False
    assert metadata["summary_side_metadata_allowed"] is True
    assert metadata["summary_mode_metadata_allowed"] is True
    assert metadata["score_formula_version"] == "management_fc9_scene_hold_cut_trend_reliability_bridge_v1"
    assert metadata["bridge_first_v1"]["management_hold_reward_hint_v1"]["contract_version"] == "management_hold_reward_hint_v1"
    assert metadata["bridge_first_v1"]["management_fast_cut_risk_v1"]["contract_version"] == "management_fast_cut_risk_v1"
    assert metadata["bridge_first_v1"]["trend_continuation_maturity_v1"]["contract_version"] == "trend_continuation_maturity_v1"
    assert metadata["bridge_first_v1"]["advanced_input_reliability_v1"]["contract_version"] == "advanced_input_reliability_v1"
    assert set(metadata["management_scene_support_v1"].keys()) == {
        "p_hold_through_noise",
        "p_premature_exit_risk",
        "p_edge_to_edge_completion",
        "p_flip_after_exit_quality",
        "p_stop_then_recover_risk",
        "good_entry_hold",
        "premature_exit",
        "reentry_flip",
    }
    assert metadata["competition_mode"] == "continue_vs_fail"
    assert metadata["recovery_competition_mode"] == "recover_vs_reentry"
    assert metadata["compression_mode"] == "core_multiplicative_support_additive"
    assert "dominance_strength_gap" in metadata["component_scores"]
    assert "hold_core" in metadata["component_scores"]
    assert "hold_support" in metadata["component_scores"]
    assert "hold_readiness" in metadata["component_scores"]
    assert "continue_momentum" in metadata["component_scores"]
    assert "fail_pressure" in metadata["component_scores"]
    assert "recovery_support" in metadata["component_scores"]
    assert "reentry_support" in metadata["component_scores"]
    assert "p_hold_through_noise" in metadata["component_scores"]
    assert "p_premature_exit_risk" in metadata["component_scores"]
    assert "p_edge_to_edge_completion" in metadata["component_scores"]
    assert "p_flip_after_exit_quality" in metadata["component_scores"]
    assert "p_stop_then_recover_risk" in metadata["component_scores"]
    assert "bf2_hold_reward_hint" in metadata["component_scores"]
    assert "bf2_edge_to_edge_tailwind" in metadata["component_scores"]
    assert "bf2_hold_patience_allowed" in metadata["component_scores"]
    assert "bf3_fast_cut_risk" in metadata["component_scores"]
    assert "bf3_collision_risk" in metadata["component_scores"]
    assert "bf3_event_caution" in metadata["component_scores"]
    assert "bf3_cut_now_allowed" in metadata["component_scores"]
    assert "bf4_continuation_maturity" in metadata["component_scores"]
    assert "bf4_exhaustion_pressure" in metadata["component_scores"]
    assert "bf4_trend_hold_confidence" in metadata["component_scores"]
    assert "bf5_advanced_reliability" in metadata["component_scores"]
    assert "bf5_order_book_reliable" in metadata["component_scores"]
    assert "bf5_event_context_reliable" in metadata["component_scores"]
    assert set(metadata["forecast_reasons"].keys()) == {
        "p_continue_favor",
        "p_fail_now",
        "p_recover_after_pullback",
        "p_reach_tp1",
        "p_opposite_edge_reach",
        "p_better_reentry_if_cut",
    }
    assert set(metadata["gap_reasons"].keys()) == {
        "continue_fail_gap",
        "recover_reentry_gap",
    }
    assert "continue_fail_gap=" in metadata["gap_reasons"]["continue_fail_gap"]
    assert "recover_reentry_gap=" in metadata["gap_reasons"]["recover_reentry_gap"]
    assert "belief_spread" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "hold_core" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "hold_support" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "continue_momentum" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "fail_pressure" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "p_hold_through_noise" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "p_edge_to_edge_completion" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "bf2_hold_reward_hint" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "bf2_edge_to_edge_tailwind" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "bf2_hold_patience_allowed" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "bf3_fast_cut_risk" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "bf3_cut_now_allowed" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "bf4_continuation_maturity" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "bf4_trend_hold_confidence" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "bf5_advanced_reliability" in metadata["forecast_reasons"]["p_continue_favor"]
    assert "conflict_barrier" in metadata["forecast_reasons"]["p_fail_now"]
    assert "hold_readiness" in metadata["forecast_reasons"]["p_fail_now"]
    assert "p_flip_after_exit_quality" in metadata["forecast_reasons"]["p_fail_now"]
    assert "p_stop_then_recover_risk" in metadata["forecast_reasons"]["p_fail_now"]
    assert "bf3_fast_cut_risk" in metadata["forecast_reasons"]["p_fail_now"]
    assert "bf3_collision_risk" in metadata["forecast_reasons"]["p_fail_now"]
    assert "bf3_event_caution" in metadata["forecast_reasons"]["p_fail_now"]
    assert "bf4_trend_hold_confidence" in metadata["forecast_reasons"]["p_fail_now"]
    assert "bf5_order_book_reliable" in metadata["forecast_reasons"]["p_fail_now"]
    assert "recovery_support" in metadata["forecast_reasons"]["p_recover_after_pullback"]
    assert "dominant_persistence" in metadata["forecast_reasons"]["p_recover_after_pullback"]
    assert "p_hold_through_noise" in metadata["forecast_reasons"]["p_recover_after_pullback"]
    assert "bf2_hold_reward_hint" in metadata["forecast_reasons"]["p_recover_after_pullback"]
    assert "bf3_fast_cut_risk" in metadata["forecast_reasons"]["p_recover_after_pullback"]
    assert "bf4_trend_hold_confidence" in metadata["forecast_reasons"]["p_recover_after_pullback"]
    assert "bf5_reliability_floor" in metadata["forecast_reasons"]["p_recover_after_pullback"]
    assert "dominant_path_evidence" in metadata["forecast_reasons"]["p_reach_tp1"]
    assert "continue_favor" in metadata["forecast_reasons"]["p_reach_tp1"]
    assert "p_edge_to_edge_completion" in metadata["forecast_reasons"]["p_reach_tp1"]
    assert "bf2_hold_reward_hint" in metadata["forecast_reasons"]["p_reach_tp1"]
    assert "bf3_fast_cut_risk" in metadata["forecast_reasons"]["p_reach_tp1"]
    assert "bf4_continuation_maturity" in metadata["forecast_reasons"]["p_reach_tp1"]
    assert "bf4_exhaustion_pressure" in metadata["forecast_reasons"]["p_reach_tp1"]
    assert "bf5_advanced_reliability" in metadata["forecast_reasons"]["p_reach_tp1"]
    assert "edge_travel_basis" in metadata["forecast_reasons"]["p_opposite_edge_reach"]
    assert "bf2_edge_to_edge_tailwind" in metadata["forecast_reasons"]["p_opposite_edge_reach"]
    assert "bf3_collision_risk" in metadata["forecast_reasons"]["p_opposite_edge_reach"]
    assert "bf4_continuation_maturity" in metadata["forecast_reasons"]["p_opposite_edge_reach"]
    assert "bf4_trend_hold_confidence" in metadata["forecast_reasons"]["p_opposite_edge_reach"]
    assert "bf5_order_book_reliable" in metadata["forecast_reasons"]["p_opposite_edge_reach"]
    assert "reentry_support" in metadata["forecast_reasons"]["p_better_reentry_if_cut"]
    assert "recover_after_pullback" in metadata["forecast_reasons"]["p_better_reentry_if_cut"]
    assert "p_flip_after_exit_quality" in metadata["forecast_reasons"]["p_better_reentry_if_cut"]
    assert "bf3_fast_cut_risk" in metadata["forecast_reasons"]["p_better_reentry_if_cut"]
    assert "bf3_collision_risk" in metadata["forecast_reasons"]["p_better_reentry_if_cut"]
    assert "bf3_event_caution" in metadata["forecast_reasons"]["p_better_reentry_if_cut"]
    assert "bf5_event_context_reliable" in metadata["forecast_reasons"]["p_better_reentry_if_cut"]


def test_forecast_gap_metrics_freeze_contract_is_explicit():
    features = _build_features(
        primary_label="ALIGNED_LOWER_STRONG",
        secondary_context_label="LOWER_CONTEXT",
        lower_hold_up=0.71,
        mid_reclaim_up=0.52,
        buy_reversal=0.82,
        buy_total=0.82,
        buy_belief=0.73,
        buy_persistence=0.66,
        belief_spread=0.58,
        buy_barrier=0.11,
        sell_barrier=0.23,
    )

    transition = build_transition_forecast(features)
    management = build_trade_management_forecast(features)
    gap_metrics = extract_forecast_gap_metrics(transition, management)

    assert gap_metrics["transition_side_separation"] == transition.metadata["side_separation"]
    assert gap_metrics["management_continue_fail_gap"] == management.metadata["continue_fail_gap"]
    assert "wait_confirm_gap" in gap_metrics
    assert "hold_exit_gap" in gap_metrics
    assert "same_side_flip_gap" in gap_metrics
    assert "belief_barrier_tension_gap" in gap_metrics
    assert gap_metrics["metadata"]["forecast_contract"] == "forecast_gap_metrics_v1"
    assert gap_metrics["metadata"]["mapper_version"] == "forecast_gap_metrics_v1_fg2"
    assert gap_metrics["metadata"]["semantic_owner_contract"] == "forecast_branch_interpretation_only_v1"
    assert gap_metrics["metadata"]["forecast_freeze_phase"] == "FR0"
    assert gap_metrics["metadata"]["forecast_pre_ml_phase"] == "FR10"
    assert gap_metrics["metadata"]["forecast_branch_role"] == "gap_metrics_branch"
    assert gap_metrics["metadata"]["pre_ml_readiness_contract_v1"]["contract_version"] == "forecast_pre_ml_readiness_v1"
    assert gap_metrics["metadata"]["pre_ml_readiness_contract_v1"]["ml_usage_role"] == "feature_only_not_owner"
    assert gap_metrics["metadata"]["pre_ml_readiness_contract_v1"]["owner_collision_allowed"] is False
    assert gap_metrics["metadata"]["pre_ml_required_feature_values_v1"]["transition_side_separation"] == gap_metrics["transition_side_separation"]
    assert gap_metrics["metadata"]["pre_ml_required_feature_values_v1"]["transition_confirm_fake_gap"] == gap_metrics["transition_confirm_fake_gap"]
    assert gap_metrics["metadata"]["pre_ml_required_feature_values_v1"]["transition_reversal_continuation_gap"] == gap_metrics["transition_reversal_continuation_gap"]
    assert gap_metrics["metadata"]["pre_ml_required_feature_values_v1"]["management_continue_fail_gap"] == gap_metrics["management_continue_fail_gap"]
    assert gap_metrics["metadata"]["pre_ml_required_feature_values_v1"]["management_recover_reentry_gap"] == gap_metrics["management_recover_reentry_gap"]
    assert gap_metrics["metadata"]["pre_ml_recommended_feature_values_v1"]["hold_exit_gap"] == gap_metrics["hold_exit_gap"]
    assert gap_metrics["metadata"]["pre_ml_recommended_feature_values_v1"]["same_side_flip_gap"] == gap_metrics["same_side_flip_gap"]
    assert {entry["public_name"] for entry in gap_metrics["metadata"]["pre_ml_readiness_contract_v1"]["required_feature_fields_v1"]} == {
        "transition_side_separation",
        "transition_confirm_fake_gap",
        "transition_reversal_continuation_gap",
        "management_continue_fail_gap",
        "management_recover_reentry_gap",
    }
    assert {entry["public_name"] for entry in gap_metrics["metadata"]["pre_ml_readiness_contract_v1"]["recommended_feature_fields_v1"]} == {
        "hold_exit_gap",
        "same_side_flip_gap",
    }
    assert gap_metrics["metadata"]["promotion_phase"] == "FR4"
    assert gap_metrics["metadata"]["semantic_forecast_inputs_v2_usage_v1"]["usage_status"] == "derived_from_branch_outputs_only"
    assert set(gap_metrics["metadata"]["execution_gap_support_v1"].keys()) == {
        "confirm_wait_state",
        "hold_exit_state",
        "same_side_flip_state",
        "belief_barrier_tension_state",
        "dominant_execution_gap",
    }
    assert "wait_confirm_gap" in gap_metrics["metadata"]["gap_semantics_v2"]
    assert "transition_fields" in gap_metrics["metadata"]["branch_output_usage_v2"]
    assert "trade_management_fields" in gap_metrics["metadata"]["branch_output_usage_v2"]
    assert gap_metrics["metadata"]["direct_action_creator_allowed"] is False
    assert gap_metrics["metadata"]["execution_side_creator_allowed"] is False


def test_forecast_effective_wrapper_freeze_contract_is_explicit():
    payload = build_layer_mode_effective_metadata(
        {
            "forecast_features_v1": {"position_primary_label": "LOWER_BIAS"},
            "transition_forecast_v1": {"metadata": {"forecast_contract": "transition_forecast_v1"}},
            "trade_management_forecast_v1": {"metadata": {"forecast_contract": "trade_management_forecast_v1"}},
            "forecast_gap_metrics_v1": {"transition_side_separation": 0.22},
        }
    )["forecast_effective_policy_v1"]

    assert payload["semantic_owner_contract"] == "forecast_branch_interpretation_only_v1"
    assert payload["forecast_freeze_phase"] == "FR0"
    assert payload["forecast_branch_role"] == "effective_wrapper_only"
    assert payload["direct_action_creator_allowed"] is False
    assert payload["execution_side_creator_allowed"] is False
    assert payload["current_effective_mode"] == "assist"
    assert payload["policy_overlay_applied"] is True
    assert payload["utility_overlay_applied"] is True
    assert "raw_effective_delta_v1" in payload
    assert "policy_overlay_trace_v1" in payload


def test_wrapper_functions_accept_pluggable_engine_without_changing_contract():
    class DummyForecastEngine:
        def build_transition_forecast(self, features):
            return TransitionForecast(
                p_buy_confirm=0.11,
                p_sell_confirm=0.22,
                p_false_break=0.33,
                p_reversal_success=0.44,
                p_continuation_success=0.55,
                metadata={"engine_name": "DummyForecastEngine"},
            )

        def build_trade_management_forecast(self, features):
            return TradeManagementForecast(
                p_continue_favor=0.12,
                p_fail_now=0.23,
                p_recover_after_pullback=0.34,
                p_reach_tp1=0.45,
                p_opposite_edge_reach=0.56,
                p_better_reentry_if_cut=0.67,
                metadata={"engine_name": "DummyForecastEngine"},
            )

    features = _build_features(
        primary_label="ALIGNED_MIDDLE",
        secondary_context_label="NEUTRAL_CONTEXT",
    )
    engine = DummyForecastEngine()

    transition = build_transition_forecast(features, engine=engine)
    management = build_trade_management_forecast(features, engine=engine)

    assert transition.p_sell_confirm == 0.22
    assert transition.metadata["engine_name"] == "DummyForecastEngine"
    assert management.p_better_reentry_if_cut == 0.67
    assert management.metadata["engine_name"] == "DummyForecastEngine"
