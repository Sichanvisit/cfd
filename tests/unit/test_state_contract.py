from backend.trading.engine.core.models import (
    EngineContext,
    PositionEnergySnapshot,
    PositionInterpretation,
    PositionSnapshot,
    StateRawSnapshot,
)
from backend.trading.engine.state.builder import (
    build_state_raw_snapshot,
    build_state_vector,
    build_state_vector_from_raw,
    build_state_vector_v2_from_raw,
)


def test_state_raw_snapshot_preserves_raw_market_state_inputs():
    ctx = EngineContext(
        symbol="BTCUSD",
        price=100.0,
        market_mode="RANGE",
        direction_policy="BUY_ONLY",
        metadata={
            "liquidity_state": "OK",
            "raw_scores": {"wait_noise": 7.5, "wait_conflict": 5.0},
            "current_disparity": 98.4,
            "current_rsi": 61.5,
            "current_adx": 27.0,
            "current_plus_di": 31.0,
            "current_minus_di": 14.0,
            "current_volatility_ratio": 1.15,
            "current_tick_spread_points": 0.45,
            "current_tick_spread_ratio": 0.22,
            "current_rate_spread": 7.0,
            "current_rate_spread_ratio": 1.18,
            "recent_rate_spread_mean": 5.9,
            "current_tick_volume": 1480.0,
            "current_tick_volume_ratio": 1.34,
            "recent_tick_volume_mean": 1100.0,
            "current_real_volume": 720.0,
            "current_real_volume_ratio": 1.12,
            "recent_real_volume_mean": 640.0,
            "state_advanced_inputs_v1": {
                "activation_state": "ACTIVE",
                "activation_reasons": ["spread_stress", "low_participation"],
                "tick_history": {
                    "tick_flow_bias": 0.41,
                    "tick_flow_burst": 0.72,
                    "tick_sample_size": 96,
                    "collector_state": "BURST_UP_FLOW",
                },
                "order_book": {
                    "order_book_imbalance": -0.24,
                    "order_book_thinness": 0.63,
                    "order_book_levels": 4,
                    "collector_state": "THIN_BOOK",
                },
                "event_risk": {
                    "event_risk_score": 0.58,
                    "event_match_count": 2,
                    "collector_state": "WATCH_EVENT_RISK",
                },
            },
            "recent_range_mean": 12.0,
            "recent_body_mean": 6.2,
            "ma_alignment": "BULL",
            "current_spread_ratio": 1.1,
            "sr_level_rank": 1,
            "sr_touch_count": 3,
            "session_state_source": "ASIA",
            "session_range_high": 112.0,
            "session_range_low": 96.0,
            "session_box_height": 16.0,
            "session_box_height_ratio": 1.33,
            "session_expansion_target": 120.0,
            "position_in_session_box": "UPPER",
            "session_expansion_progress": 0.42,
            "session_position_bias": 0.66,
            "mtf_ma_big_map_v1": {
                "spacing_score": 0.63,
                "slope_bias": 0.44,
                "slope_agreement": 0.78,
            },
            "mtf_trendline_map_v1": {
                "entries": {
                    "1H": {
                        "nearest_kind": "SUPPORT",
                        "nearest_side": "ABOVE",
                        "nearest_proximity": 0.65,
                    },
                    "15M": {
                        "nearest_kind": "RESISTANCE",
                        "nearest_side": "ABOVE",
                        "nearest_proximity": 0.50,
                    },
                }
            },
            "position_gate_input_v1": {
                "interpretation": {
                    "mtf_context_weight_profile_v1": {
                        "bias": 0.42,
                        "agreement_score": 0.66,
                        "owner": "STATE_CANDIDATE",
                    }
                },
                "energy": {
                    "middle_neutrality": 0.31,
                },
                "position_scale": {
                    "compression_score": 0.22,
                    "expansion_score": 0.71,
                    "map_size_state": "EXPANDED",
                },
            },
        },
    )

    raw = build_state_raw_snapshot(ctx)

    assert raw.market_mode == "RANGE"
    assert raw.direction_policy == "BUY_ONLY"
    assert raw.liquidity_state == "OK"
    assert raw.s_topdown_bias == 0.42
    assert raw.s_topdown_agreement == 0.66
    assert raw.s_compression == 0.22
    assert raw.s_expansion == 0.71
    assert raw.s_middle_neutrality == 0.31
    assert raw.s_current_rsi == 61.5
    assert raw.s_current_adx == 27.0
    assert raw.s_current_plus_di == 31.0
    assert raw.s_current_minus_di == 14.0
    assert raw.s_recent_range_mean == 12.0
    assert raw.s_recent_body_mean == 6.2
    assert raw.s_sr_level_rank == 1.0
    assert raw.s_sr_touch_count == 3.0
    assert raw.s_session_box_height_ratio == 1.33
    assert raw.s_session_expansion_progress == 0.42
    assert raw.s_session_position_bias == 0.66
    assert raw.s_topdown_spacing_score == 0.63
    assert raw.s_topdown_slope_bias == 0.44
    assert raw.s_topdown_slope_agreement == 0.78
    assert raw.s_topdown_confluence_bias > 0.0
    assert 0.0 <= raw.s_topdown_conflict_score < 0.1
    assert raw.s_tick_spread_ratio == 0.22
    assert raw.s_rate_spread_ratio == 1.18
    assert raw.s_tick_volume_ratio == 1.34
    assert raw.s_real_volume_ratio == 1.12
    assert raw.s_tick_flow_bias == 0.41
    assert raw.s_tick_flow_burst == 0.72
    assert raw.s_order_book_imbalance == -0.24
    assert raw.s_order_book_thinness == 0.63
    assert raw.s_event_risk_score == 0.58
    assert raw.metadata["state_contract"] == "raw_snapshot_v1"
    assert raw.metadata["raw_snapshot_version"] == "raw_snapshot_v1"
    assert raw.metadata["ma_alignment"] == "BULL"
    assert raw.metadata["mtf_bias"] == 0.42
    assert raw.metadata["mtf_agreement_score"] == 0.66
    assert raw.metadata["position_scale_map_size_state"] == "EXPANDED"
    assert raw.metadata["current_rsi"] == 61.5
    assert raw.metadata["current_adx"] == 27.0
    assert raw.metadata["sr_level_rank"] == 1.0
    assert raw.metadata["sr_touch_count"] == 3.0
    assert raw.metadata["session_state_source"] == "ASIA"
    assert raw.metadata["session_range_high"] == 112.0
    assert raw.metadata["session_range_low"] == 96.0
    assert raw.metadata["session_box_height"] == 16.0
    assert raw.metadata["session_box_height_ratio"] == 1.33
    assert raw.metadata["session_expansion_target"] == 120.0
    assert raw.metadata["position_in_session_box"] == "UPPER"
    assert raw.metadata["session_expansion_progress"] == 0.42
    assert raw.metadata["session_position_bias"] == 0.66
    assert raw.metadata["topdown_spacing_score"] == 0.63
    assert raw.metadata["topdown_slope_bias"] == 0.44
    assert raw.metadata["topdown_slope_agreement"] == 0.78
    assert raw.metadata["topdown_confluence_bias"] > 0.0
    assert 0.0 <= raw.metadata["topdown_conflict_score"] < 0.1
    assert raw.metadata["topdown_confluence_detail_v1"]["ma_bias"] == 0.44
    assert raw.metadata["current_tick_spread_points"] == 0.45
    assert raw.metadata["current_tick_spread_ratio"] == 0.22
    assert raw.metadata["current_rate_spread"] == 7.0
    assert raw.metadata["current_rate_spread_ratio"] == 1.18
    assert raw.metadata["recent_rate_spread_mean"] == 5.9
    assert raw.metadata["current_tick_volume"] == 1480.0
    assert raw.metadata["current_tick_volume_ratio"] == 1.34
    assert raw.metadata["recent_tick_volume_mean"] == 1100.0
    assert raw.metadata["current_real_volume"] == 720.0
    assert raw.metadata["current_real_volume_ratio"] == 1.12
    assert raw.metadata["recent_real_volume_mean"] == 640.0
    assert raw.metadata["advanced_input_activation_state"] == "ACTIVE"
    assert raw.metadata["advanced_input_activation_reasons"] == ["spread_stress", "low_participation"]
    assert raw.metadata["tick_flow_bias"] == 0.41
    assert raw.metadata["tick_flow_burst"] == 0.72
    assert raw.metadata["tick_flow_state"] == "BURST_UP_FLOW"
    assert raw.metadata["tick_sample_size"] == 96
    assert raw.metadata["order_book_imbalance"] == -0.24
    assert raw.metadata["order_book_thinness"] == 0.63
    assert raw.metadata["order_book_state"] == "THIN_BOOK"
    assert raw.metadata["order_book_levels"] == 4
    assert raw.metadata["event_risk_score"] == 0.58
    assert raw.metadata["event_risk_state"] == "WATCH_EVENT_RISK"
    assert raw.metadata["event_risk_match_count"] == 2


def test_state_raw_snapshot_promotes_micro_structure_v1_into_canonical_fields():
    ctx = EngineContext(
        symbol="NAS100",
        price=200.0,
        metadata={
            "recent_body_mean": 4.2,
            "position_gate_input_v1": {"position_scale": {"compression_score": 0.35}},
            "micro_structure_v1": {
                "version": "micro_structure_v1",
                "data_state": "READY",
                "anchor_state": "READY",
                "lookback_bars": 20,
                "baseline_lookback_bars": 50,
                "window_size": 20,
                "volume_source": "tick_volume",
                "body_size_pct_20": 0.18,
                "upper_wick_ratio_20": 0.22,
                "lower_wick_ratio_20": 0.11,
                "doji_ratio_20": 0.15,
                "same_color_run_current": 4,
                "same_color_run_max_20": 7,
                "bull_ratio_20": 0.65,
                "bear_ratio_20": 0.35,
                "direction_run_stats": {
                    "same_color_run_current": 4,
                    "same_color_run_max_20": 7,
                    "bull_ratio_20": 0.65,
                    "bear_ratio_20": 0.35,
                },
                "range_compression_ratio_20": 0.44,
                "volume_burst_ratio_20": 1.9,
                "volume_burst_decay_20": 0.48,
                "swing_high_retest_count_20": 2,
                "swing_low_retest_count_20": 1,
                "gap_fill_progress": 0.72,
            },
        },
    )

    raw = build_state_raw_snapshot(ctx)

    assert raw.s_body_size_pct_20 == 0.18
    assert raw.s_upper_wick_ratio_20 == 0.22
    assert raw.s_lower_wick_ratio_20 == 0.11
    assert raw.s_doji_ratio_20 == 0.15
    assert raw.s_same_color_run_current == 4.0
    assert raw.s_same_color_run_max_20 == 7.0
    assert raw.s_bull_ratio_20 == 0.65
    assert raw.s_bear_ratio_20 == 0.35
    assert raw.s_range_compression_ratio_20 == 0.44
    assert raw.s_volume_burst_ratio_20 == 1.9
    assert raw.s_volume_burst_decay_20 == 0.48
    assert raw.s_swing_high_retest_count_20 == 2.0
    assert raw.s_swing_low_retest_count_20 == 1.0
    assert raw.s_gap_fill_progress == 0.72
    assert raw.metadata["micro_structure_version"] == "micro_structure_v1"
    assert raw.metadata["micro_structure_data_state"] == "READY"
    assert raw.metadata["micro_structure_anchor_state"] == "READY"
    assert raw.metadata["micro_structure_volume_source"] == "tick_volume"
    assert raw.metadata["micro_body_size_pct_20"] == 0.18
    assert raw.metadata["micro_direction_run_stats_v1"]["same_color_run_max_20"] == 7.0
    assert raw.metadata["micro_gap_fill_progress"] == 0.72


def test_state_raw_snapshot_keeps_micro_structure_defaults_when_snapshot_missing():
    ctx = EngineContext(
        symbol="XAUUSD",
        price=100.0,
        metadata={
            "recent_body_mean": 3.3,
            "position_gate_input_v1": {"position_scale": {"compression_score": 0.28}},
        },
    )

    raw = build_state_raw_snapshot(ctx)

    assert raw.s_body_size_pct_20 == 3.3
    assert raw.s_upper_wick_ratio_20 == 0.0
    assert raw.s_doji_ratio_20 == 0.0
    assert raw.s_same_color_run_current == 0.0
    assert raw.s_range_compression_ratio_20 == 0.28
    assert raw.s_volume_burst_decay_20 == 0.0
    assert raw.s_gap_fill_progress is None
    assert raw.metadata["micro_structure_data_state"] == "MISSING"
    assert raw.metadata["micro_structure_anchor_state"] == "MISSING"
    assert raw.metadata["micro_structure_v1"] == {}
    assert raw.metadata["micro_gap_fill_progress"] is None


def test_state_vector_legacy_is_derived_only_from_state_raw_snapshot():
    ctx = EngineContext(
        symbol="XAUUSD",
        price=100.0,
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        metadata={
            "liquidity_state": "GOOD",
            "raw_scores": {"wait_noise": 10.0, "wait_conflict": 2.5},
            "current_disparity": 102.0,
            "current_volatility_ratio": 1.2,
            "ma_alignment": "BEAR",
            "current_spread_ratio": 0.9,
        },
    )

    raw = build_state_raw_snapshot(ctx)
    legacy_from_raw = build_state_vector_from_raw(raw)
    legacy_from_ctx = build_state_vector(ctx)

    assert legacy_from_ctx.to_dict() == legacy_from_raw.to_dict()


def test_state_vector_v2_boosts_range_reversal_regime():
    raw = StateRawSnapshot(
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        s_noise=0.10,
        s_conflict=0.10,
        s_alignment=0.0,
        s_volatility=0.15,
    )

    vector = build_state_vector_v2_from_raw(raw)

    assert vector.range_reversal_gain > 1.0
    assert vector.trend_pullback_gain < 1.0
    assert vector.breakout_continuation_gain < 1.0


def test_state_vector_v2_exposes_exact_canonical_fields():
    raw = StateRawSnapshot(
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
    )

    payload = build_state_vector_v2_from_raw(raw).to_dict()

    assert set(payload.keys()) == {
        "range_reversal_gain",
        "trend_pullback_gain",
        "breakout_continuation_gain",
        "noise_damp",
        "conflict_damp",
        "alignment_gain",
        "topdown_bull_bias",
        "topdown_bear_bias",
        "big_map_alignment_gain",
        "wait_patience_gain",
        "confirm_aggression_gain",
        "hold_patience_gain",
        "fast_exit_risk_penalty",
        "countertrend_penalty",
        "liquidity_penalty",
        "volatility_penalty",
        "metadata",
    }


def test_state_vector_v2_keeps_unavailable_advanced_inputs_neutral():
    raw = StateRawSnapshot(
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        s_order_book_thinness=1.0,
        metadata={
            "advanced_input_activation_state": "PARTIAL_ACTIVE",
            "tick_flow_state": "UNAVAILABLE",
            "order_book_state": "UNAVAILABLE",
            "event_risk_state": "UNAVAILABLE",
        },
    )

    vector = build_state_vector_v2_from_raw(raw)
    meta = vector.metadata
    advanced = meta["advanced_input_detail_v1"]

    assert meta["tick_flow_state"] == "UNAVAILABLE"
    assert meta["order_book_state"] == "UNAVAILABLE"
    assert meta["event_risk_state"] == "UNAVAILABLE"
    assert advanced["advanced_execution_stress"] == 0.0


def test_state_vector_v2_exposes_explanatory_metadata_contract():
    raw = StateRawSnapshot(
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        s_noise=0.56,
        s_conflict=0.30,
        s_alignment=0.0,
        s_volatility=0.25,
    )

    vector = build_state_vector_v2_from_raw(raw)
    meta = vector.metadata
    reasons = meta["coefficient_reasons"]

    assert meta["state_contract"] == "canonical_v3"
    assert meta["raw_snapshot_version"] == "raw_snapshot_v1"
    assert meta["mapper_version"] == "state_vector_v2_s9"
    assert meta["semantic_owner_contract"] == "state_market_trust_patience_only_v1"
    assert meta["state_freeze_phase"] == "S0"
    assert meta["canonical_state_clusters_v1"] == [
        "regime_state",
        "topdown_state",
        "quality_state",
        "patience_state",
    ]
    owner_scope = meta["semantic_owner_scope"]
    assert owner_scope["identity_override_allowed"] is False
    assert owner_scope["position_owner_claim_allowed"] is False
    assert owner_scope["response_owner_claim_allowed"] is False
    assert set(owner_scope["allowed_domains"]) == {
        "regime_interpretation",
        "topdown_bias_interpretation",
        "market_quality_interpretation",
        "patience_and_execution_temperament",
    }
    assert set(owner_scope["forbidden_domains"]) == {
        "position_location_identity",
        "response_event_identity",
        "direct_buy_sell_side_identity",
        "trigger_event_ownership",
    }
    assert meta["source_regime"] == "RANGE"
    assert meta["source_liquidity"] == "GOOD"
    assert meta["source_noise"] == 0.56
    assert meta["source_conflict"] == 0.30
    assert meta["source_alignment"] == 0.0
    assert meta["source_volatility"] == 0.25
    assert meta["source_current_rsi"] == 50.0
    assert meta["source_current_adx"] == 0.0
    assert meta["source_micro_body_size_pct_20"] == 0.0
    assert meta["source_micro_upper_wick_ratio_20"] == 0.0
    assert meta["source_micro_lower_wick_ratio_20"] == 0.0
    assert meta["source_micro_doji_ratio_20"] == 0.0
    assert meta["source_micro_same_color_run_current"] == 0.0
    assert meta["source_micro_same_color_run_max_20"] == 0.0
    assert meta["source_micro_bull_ratio_20"] == 0.0
    assert meta["source_micro_bear_ratio_20"] == 0.0
    assert meta["source_micro_range_compression_ratio_20"] == 0.0
    assert meta["source_micro_volume_burst_ratio_20"] == 0.0
    assert meta["source_micro_volume_burst_decay_20"] == 0.0
    assert meta["source_micro_swing_high_retest_count_20"] == 0.0
    assert meta["source_micro_swing_low_retest_count_20"] == 0.0
    assert meta["source_micro_gap_fill_progress"] is None
    assert meta["source_sr_level_rank"] == 0.0
    assert meta["source_sr_touch_count"] == 0.0
    assert meta["source_session_box_height_ratio"] == 0.0
    assert meta["source_session_expansion_progress"] == 0.0
    assert meta["source_session_position_bias"] == 0.0
    assert meta["source_topdown_spacing_score"] == 0.0
    assert meta["source_topdown_slope_bias"] == 0.0
    assert meta["source_topdown_slope_agreement"] == 0.0
    assert meta["source_topdown_confluence_bias"] == 0.0
    assert meta["source_topdown_conflict_score"] == 0.0
    assert meta["source_tick_spread_ratio"] == 0.0
    assert meta["source_rate_spread_ratio"] == 0.0
    assert meta["source_tick_volume_ratio"] == 0.0
    assert meta["source_real_volume_ratio"] == 0.0
    assert meta["source_tick_flow_bias"] == 0.0
    assert meta["source_tick_flow_burst"] == 0.0
    assert meta["source_order_book_imbalance"] == 0.0
    assert meta["source_order_book_thinness"] == 0.0
    assert meta["source_event_risk_score"] == 0.0
    assert meta["regime_state_label"] in {"RANGE_SWING", "CHOP_NOISE", "RANGE_COMPRESSION"}
    assert meta["micro_breakout_readiness_state"] in {"BREAKOUT_READY", "BREAKOUT_WATCH", "BREAKOUT_NEUTRAL"}
    assert meta["micro_reversal_risk_state"] in {"REVERSAL_RISK_HIGH", "REVERSAL_RISK_WATCH", "REVERSAL_RISK_LOW"}
    assert meta["micro_participation_state"] in {"BURST_CONFIRMED", "BURST_FADING", "QUIET_PARTICIPATION", "NORMAL_PARTICIPATION"}
    assert meta["micro_gap_context_state"] in {"GAP_CONTEXT_MISSING", "EARLY_GAP_FILL", "ACTIVE_GAP_FILL", "LATE_GAP_FILL"}
    assert meta["quality_state_label"] in {"HIGH_QUALITY", "MEDIUM_QUALITY", "LOW_QUALITY"}
    assert 0.0 <= meta["quality_composite_score"] <= 1.0
    micro_detail = meta["micro_structure_detail_v1"]
    assert set(micro_detail.keys()) == {
        "data_state",
        "anchor_state",
        "volume_source",
        "lookback_bars",
        "window_size",
    }
    detail = meta["quality_state_detail_v1"]
    assert set(detail.keys()) == {
        "momentum_quality_score",
        "momentum_quality_label",
        "activity_quality_score",
        "activity_quality_label",
        "level_reliability_score",
        "level_reliability_label",
    }
    assert meta["topdown_state_label"] in {"BULL_ALIGNED", "BEAR_ALIGNED", "MIXED_TOPDOWN", "NEUTRAL_TOPDOWN"}
    assert meta["patience_state_label"] in {"WAIT_FAVOR", "CONFIRM_FAVOR", "HOLD_FAVOR", "FAST_EXIT_FAVOR"}
    assert meta["session_regime_state"] in {
        "SESSION_COMPRESSION",
        "SESSION_EXPANSION",
        "SESSION_EDGE_ROTATION",
        "SESSION_BALANCED",
    }
    assert meta["session_expansion_state"] in {
        "IN_SESSION_BOX",
        "UP_EARLY_EXPANSION",
        "UP_ACTIVE_EXPANSION",
        "UP_EXTENDED_EXPANSION",
        "DOWN_EARLY_EXPANSION",
        "DOWN_ACTIVE_EXPANSION",
        "DOWN_EXTENDED_EXPANSION",
    }
    assert meta["session_exhaustion_state"] in {
        "LOW_EXHAUSTION_RISK",
        "MEDIUM_EXHAUSTION_RISK",
        "HIGH_EXHAUSTION_RISK",
        "EDGE_WATCH",
    }
    assert meta["topdown_spacing_state"] in {
        "WIDE_SPACING",
        "ORDERED_SPACING",
        "TIGHT_SPACING",
        "FLAT_SPACING",
    }
    assert meta["topdown_slope_state"] in {
        "UP_SLOPE_ALIGNED",
        "DOWN_SLOPE_ALIGNED",
        "MIXED_SLOPE",
        "FLAT_SLOPE",
    }
    assert meta["topdown_confluence_state"] in {
        "BULL_CONFLUENCE",
        "BEAR_CONFLUENCE",
        "TOPDOWN_CONFLICT",
        "WEAK_CONFLUENCE",
    }
    assert meta["spread_stress_state"] in {
        "HIGH_SPREAD_STRESS",
        "ELEVATED_SPREAD_STRESS",
        "NORMAL_SPREAD",
        "TIGHT_SPREAD",
    }
    assert meta["volume_participation_state"] in {
        "HIGH_PARTICIPATION",
        "NORMAL_PARTICIPATION",
        "THIN_PARTICIPATION",
        "LOW_PARTICIPATION",
    }
    assert meta["execution_friction_state"] in {
        "HIGH_FRICTION",
        "MEDIUM_FRICTION",
        "LOW_FRICTION",
    }
    assert meta["advanced_input_activation_state"] in {
        "ADVANCED_ACTIVE",
        "ADVANCED_PARTIAL",
        "ADVANCED_PASSIVE",
        "ADVANCED_UNAVAILABLE",
        "ADVANCED_DISABLED",
        "ADVANCED_IDLE",
    }
    assert meta["tick_flow_state"] in {
        "BURST_UP_FLOW",
        "BURST_DOWN_FLOW",
        "QUIET_FLOW",
        "BALANCED_FLOW",
        "INACTIVE",
        "UNAVAILABLE",
        "DISABLED",
    }
    assert meta["order_book_state"] in {
        "THIN_BOOK",
        "BID_IMBALANCE",
        "ASK_IMBALANCE",
        "BALANCED_BOOK",
        "INACTIVE",
        "UNAVAILABLE",
        "DISABLED",
    }
    assert meta["event_risk_state"] in {
        "HIGH_EVENT_RISK",
        "WATCH_EVENT_RISK",
        "LOW_EVENT_RISK",
        "INACTIVE",
        "UNAVAILABLE",
        "DISABLED",
    }
    advanced_detail = meta["advanced_input_detail_v1"]
    assert set(advanced_detail.keys()) == {
        "advanced_execution_stress",
        "activation_reasons",
        "tick_sample_size",
        "order_book_levels",
        "event_risk_match_count",
    }
    assert set(reasons.keys()) == {
        "range_reversal_gain",
        "trend_pullback_gain",
        "breakout_continuation_gain",
        "noise_damp",
        "conflict_damp",
        "alignment_gain",
        "momentum_quality_detail",
        "activity_quality_detail",
        "level_reliability_detail",
        "topdown_bull_bias",
        "topdown_bear_bias",
        "big_map_alignment_gain",
        "wait_patience_gain",
        "confirm_aggression_gain",
        "hold_patience_gain",
        "fast_exit_risk_penalty",
        "session_regime_state",
        "session_expansion_state",
        "session_exhaustion_state",
        "topdown_spacing_state",
        "topdown_slope_state",
        "topdown_confluence_state",
        "spread_stress_state",
        "volume_participation_state",
        "execution_friction_state",
        "advanced_input_activation_state",
        "tick_flow_state",
        "order_book_state",
        "event_risk_state",
        "advanced_execution_stress",
        "countertrend_penalty",
        "liquidity_penalty",
        "volatility_penalty",
        "micro_structure_breakout_readiness",
        "micro_structure_reversal_risk",
        "micro_structure_participation",
        "micro_structure_gap_context",
    }
    assert "reversal boost" in reasons["range_reversal_gain"]
    assert "noise_damp=" in reasons["noise_damp"]
    assert "position quality conflict" in reasons["conflict_damp"]
    assert "position quality alignment" in reasons["alignment_gain"]
    assert "momentum_quality_score=" in reasons["momentum_quality_detail"]
    assert "activity_quality_score=" in reasons["activity_quality_detail"]
    assert "level_reliability_score=" in reasons["level_reliability_detail"]
    assert "topdown_bull_bias" in reasons["topdown_bull_bias"]
    assert "wait_patience_gain=" in reasons["wait_patience_gain"]
    assert "session_regime_state=" in reasons["session_regime_state"]
    assert "session_expansion_state=" in reasons["session_expansion_state"]
    assert "session_exhaustion_state=" in reasons["session_exhaustion_state"]
    assert "topdown_spacing_state=" in reasons["topdown_spacing_state"]
    assert "topdown_slope_state=" in reasons["topdown_slope_state"]
    assert "topdown_confluence_state=" in reasons["topdown_confluence_state"]
    assert "spread_stress_state=" in reasons["spread_stress_state"]
    assert "volume_participation_state=" in reasons["volume_participation_state"]
    assert "execution_friction_state=" in reasons["execution_friction_state"]
    assert "advanced_input_activation_state=" in reasons["advanced_input_activation_state"]
    assert "tick_flow_state=" in reasons["tick_flow_state"]
    assert "order_book_state=" in reasons["order_book_state"]
    assert "event_risk_state=" in reasons["event_risk_state"]
    assert "advanced_execution_stress=" in reasons["advanced_execution_stress"]
    assert "breakout_readiness=" in reasons["micro_structure_breakout_readiness"]
    assert "reversal_risk=" in reasons["micro_structure_reversal_risk"]
    assert "participation_state=" in reasons["micro_structure_participation"]
    assert "micro_gap_context_state=" in reasons["micro_structure_gap_context"]


def test_state_vector_v2_micro_structure_adjusts_breakout_vs_reversal_bias():
    breakout = build_state_vector_v2_from_raw(
        StateRawSnapshot(
            market_mode="RANGE",
            direction_policy="BOTH",
            liquidity_state="GOOD",
            s_range_compression_ratio_20=0.82,
            s_volume_burst_ratio_20=2.2,
            s_volume_burst_decay_20=0.18,
            s_same_color_run_current=4.0,
            s_doji_ratio_20=0.04,
        )
    )
    reversal = build_state_vector_v2_from_raw(
        StateRawSnapshot(
            market_mode="RANGE",
            direction_policy="BOTH",
            liquidity_state="GOOD",
            s_upper_wick_ratio_20=0.76,
            s_lower_wick_ratio_20=0.68,
            s_swing_high_retest_count_20=2.0,
            s_swing_low_retest_count_20=1.0,
            s_doji_ratio_20=0.24,
            s_volume_burst_decay_20=0.61,
        )
    )

    assert breakout.breakout_continuation_gain > reversal.breakout_continuation_gain
    assert reversal.range_reversal_gain > breakout.range_reversal_gain
    assert breakout.metadata["micro_breakout_readiness_state"] in {"BREAKOUT_READY", "BREAKOUT_WATCH"}
    assert reversal.metadata["micro_reversal_risk_state"] in {"REVERSAL_RISK_HIGH", "REVERSAL_RISK_WATCH"}


def test_state_vector_v2_keeps_gain_and_damp_penalty_philosophy():
    raw = StateRawSnapshot(
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        liquidity_state="BAD",
        s_noise=0.65,
        s_conflict=0.80,
        s_alignment=0.45,
        s_volatility=0.75,
        metadata={"spread_ratio": 1.7},
    )

    vector = build_state_vector_v2_from_raw(raw)

    assert vector.range_reversal_gain >= 0.0
    assert vector.trend_pullback_gain >= 0.0
    assert vector.breakout_continuation_gain >= 0.0
    assert vector.alignment_gain >= 1.0
    assert 0.0 <= vector.topdown_bull_bias <= 1.0
    assert 0.0 <= vector.topdown_bear_bias <= 1.0
    assert vector.big_map_alignment_gain >= 1.0
    assert vector.wait_patience_gain >= 0.0
    assert vector.confirm_aggression_gain >= 0.0
    assert vector.hold_patience_gain >= 0.0
    assert 0.0 <= vector.fast_exit_risk_penalty <= 1.0
    assert 0.0 <= vector.noise_damp <= 1.0
    assert 0.0 <= vector.conflict_damp <= 1.0
    assert 0.0 <= vector.countertrend_penalty <= 1.0
    assert 0.0 <= vector.liquidity_penalty <= 1.0
    assert 0.0 <= vector.volatility_penalty <= 1.0
    assert vector.metadata["mapper_version"] == "state_vector_v2_s9"


def test_state_vector_v2_boosts_trend_pullback_and_breakout():
    raw = StateRawSnapshot(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        liquidity_state="OK",
        s_noise=0.10,
        s_conflict=0.05,
        s_alignment=0.3,
        s_volatility=0.20,
    )

    vector = build_state_vector_v2_from_raw(raw)

    assert vector.range_reversal_gain < 1.0
    assert vector.trend_pullback_gain > 1.0
    assert vector.breakout_continuation_gain > 1.0
    assert vector.countertrend_penalty > 0.0


def test_state_vector_v2_shock_increases_damp_and_penalty():
    raw = StateRawSnapshot(
        market_mode="SHOCK",
        direction_policy="BOTH",
        liquidity_state="BAD",
        s_noise=0.85,
        s_conflict=0.70,
        s_alignment=0.0,
        s_volatility=0.90,
        metadata={"spread_ratio": 1.8},
    )

    vector = build_state_vector_v2_from_raw(raw)

    assert vector.range_reversal_gain < 1.0
    assert vector.trend_pullback_gain < 1.0
    assert vector.noise_damp < 0.6
    assert vector.conflict_damp < 0.9
    assert vector.metadata["raw_conflict_assist"] > 0.0
    assert vector.liquidity_penalty > 0.4
    assert vector.volatility_penalty >= 0.35


def test_state_vector_v2_uses_position_conflict_and_alignment_context():
    raw = StateRawSnapshot(
        market_mode="RANGE",
        direction_policy="SELL_ONLY",
        liquidity_state="OK",
        s_noise=0.10,
        s_conflict=0.15,
        s_alignment=0.0,
        s_volatility=0.10,
    )
    position_snapshot = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_UPPER_WEAK",
            conflict_kind="CONFLICT_BOX_UPPER_BB20_LOWER",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.55),
    )

    vector = build_state_vector_v2_from_raw(raw, position_snapshot=position_snapshot)

    assert vector.alignment_gain > 1.0
    assert vector.conflict_damp < 0.7
    assert vector.metadata["position_primary_label"] == "ALIGNED_UPPER_WEAK"
    assert vector.metadata["position_conflict_kind"] == "CONFLICT_BOX_UPPER_BB20_LOWER"
    assert vector.metadata["position_conflict_score"] == 0.55
    assert vector.metadata["position_quality_usage"]["direction_source_used"] is False


def test_state_vector_v2_exposes_topdown_and_patience_when_raw_inputs_exist():
    raw = StateRawSnapshot(
        market_mode="TREND",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        s_noise=0.12,
        s_conflict=0.08,
        s_alignment=0.40,
        s_volatility=0.18,
        s_topdown_bias=0.52,
        s_topdown_agreement=0.74,
        s_compression=0.18,
        s_expansion=0.66,
        s_middle_neutrality=0.14,
        s_topdown_spacing_score=0.62,
        s_topdown_slope_bias=0.41,
        s_topdown_slope_agreement=0.73,
        s_topdown_confluence_bias=0.48,
        s_topdown_conflict_score=0.08,
    )

    vector = build_state_vector_v2_from_raw(raw)

    assert vector.topdown_bull_bias > 0.0
    assert vector.topdown_bear_bias == 0.0
    assert vector.big_map_alignment_gain > 1.0
    assert vector.confirm_aggression_gain > 1.0
    assert vector.hold_patience_gain > 1.0
    assert vector.metadata["topdown_state_label"] == "BULL_ALIGNED"
    assert vector.metadata["topdown_spacing_state"] == "ORDERED_SPACING"
    assert vector.metadata["topdown_slope_state"] == "UP_SLOPE_ALIGNED"
    assert vector.metadata["topdown_confluence_state"] == "BULL_CONFLUENCE"


def test_state_vector_v2_enriches_quality_detail_labels_from_existing_inputs():
    raw = StateRawSnapshot(
        market_mode="TREND",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        s_noise=0.12,
        s_conflict=0.10,
        s_alignment=0.35,
        s_disparity=0.18,
        s_volatility=0.20,
        s_current_rsi=62.0,
        s_current_adx=31.0,
        s_current_plus_di=29.0,
        s_current_minus_di=12.0,
        s_recent_range_mean=15.0,
        s_recent_body_mean=8.5,
        s_sr_level_rank=1.0,
        s_sr_touch_count=3.0,
    )

    vector = build_state_vector_v2_from_raw(raw)
    detail = vector.metadata["quality_state_detail_v1"]

    assert detail["momentum_quality_label"] in {"BULL_IMPULSE_READY", "BALANCED_MOMENTUM"}
    assert detail["activity_quality_label"] in {"HEALTHY_ACTIVITY", "EXPLOSIVE_ACTIVITY"}
    assert detail["level_reliability_label"] in {"TESTED_PRIMARY_LEVEL", "PRIMARY_LEVEL"}
    assert detail["momentum_quality_score"] > 0.5
    assert detail["activity_quality_score"] > 0.4
    assert detail["level_reliability_score"] > 0.6


def test_state_vector_v2_exposes_session_state_labels_when_session_inputs_exist():
    raw = StateRawSnapshot(
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        s_noise=0.14,
        s_conflict=0.10,
        s_volatility=0.28,
        s_session_box_height_ratio=0.38,
        s_session_expansion_progress=0.72,
        s_session_position_bias=0.92,
    )

    vector = build_state_vector_v2_from_raw(raw)
    meta = vector.metadata

    assert meta["session_regime_state"] in {"SESSION_COMPRESSION", "SESSION_EXPANSION"}
    assert meta["session_expansion_state"] == "UP_ACTIVE_EXPANSION"
    assert meta["session_exhaustion_state"] in {"MEDIUM_EXHAUSTION_RISK", "HIGH_EXHAUSTION_RISK"}


def test_state_vector_v2_exposes_spread_volume_execution_labels():
    raw = StateRawSnapshot(
        market_mode="TREND",
        direction_policy="BOTH",
        liquidity_state="OK",
        s_noise=0.10,
        s_conflict=0.08,
        s_volatility=0.22,
        s_tick_spread_ratio=0.72,
        s_rate_spread_ratio=1.36,
        s_tick_volume_ratio=0.48,
        s_real_volume_ratio=0.52,
    )

    vector = build_state_vector_v2_from_raw(raw)
    meta = vector.metadata

    assert meta["spread_stress_state"] in {"ELEVATED_SPREAD_STRESS", "HIGH_SPREAD_STRESS"}
    assert meta["volume_participation_state"] in {"THIN_PARTICIPATION", "LOW_PARTICIPATION"}
    assert meta["execution_friction_state"] in {"MEDIUM_FRICTION", "HIGH_FRICTION"}


def test_state_vector_v2_noise_damp_decreases_as_noise_increases():
    low_noise = build_state_vector_v2_from_raw(
        StateRawSnapshot(market_mode="RANGE", direction_policy="BOTH", liquidity_state="GOOD", s_noise=0.10)
    )
    high_noise = build_state_vector_v2_from_raw(
        StateRawSnapshot(market_mode="RANGE", direction_policy="BOTH", liquidity_state="GOOD", s_noise=0.80)
    )

    assert high_noise.noise_damp < low_noise.noise_damp


def test_state_vector_v2_conflict_damp_decreases_as_conflict_increases():
    low_conflict = build_state_vector_v2_from_raw(
        StateRawSnapshot(market_mode="RANGE", direction_policy="BOTH", liquidity_state="GOOD", s_conflict=0.10)
    )
    high_conflict = build_state_vector_v2_from_raw(
        StateRawSnapshot(market_mode="RANGE", direction_policy="BOTH", liquidity_state="GOOD", s_conflict=0.80)
    )

    assert high_conflict.conflict_damp < low_conflict.conflict_damp


def test_state_vector_v2_treats_raw_conflict_as_assist_when_position_is_clean():
    raw = StateRawSnapshot(
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        s_conflict=1.0,
    )
    position_snapshot = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_MIDDLE",
            secondary_context_label="LOWER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )

    vector = build_state_vector_v2_from_raw(raw, position_snapshot=position_snapshot)

    assert vector.conflict_damp > 0.75
    assert vector.metadata["raw_conflict_assist"] == 0.3
    assert vector.metadata["position_conflict_kind"] == ""


def test_state_vector_v2_uses_bias_label_for_alignment_quality_only():
    raw = StateRawSnapshot(
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        s_alignment=0.0,
    )
    position_snapshot = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="UPPER_BIAS",
            bias_label="UPPER_BIAS",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )

    vector = build_state_vector_v2_from_raw(raw, position_snapshot=position_snapshot)

    assert vector.alignment_gain > 1.0
    assert vector.metadata["position_bias_label"] == "UPPER_BIAS"


def test_state_vector_v2_position_alignment_is_not_directional():
    raw = StateRawSnapshot(
        market_mode="RANGE",
        direction_policy="BOTH",
        liquidity_state="GOOD",
        s_alignment=0.0,
    )
    upper = build_state_vector_v2_from_raw(
        raw,
        position_snapshot=PositionSnapshot(
            interpretation=PositionInterpretation(primary_label="ALIGNED_UPPER_WEAK"),
            energy=PositionEnergySnapshot(position_conflict_score=0.0),
        ),
    )
    lower = build_state_vector_v2_from_raw(
        raw,
        position_snapshot=PositionSnapshot(
            interpretation=PositionInterpretation(primary_label="ALIGNED_LOWER_WEAK"),
            energy=PositionEnergySnapshot(position_conflict_score=0.0),
        ),
    )

    assert upper.alignment_gain == lower.alignment_gain
    assert upper.countertrend_penalty == lower.countertrend_penalty == 0.0


def test_state_vector_v2_liquidity_penalty_increases_with_worse_liquidity():
    good = build_state_vector_v2_from_raw(
        StateRawSnapshot(market_mode="RANGE", direction_policy="BOTH", liquidity_state="GOOD")
    )
    ok = build_state_vector_v2_from_raw(
        StateRawSnapshot(market_mode="RANGE", direction_policy="BOTH", liquidity_state="OK")
    )
    bad = build_state_vector_v2_from_raw(
        StateRawSnapshot(market_mode="RANGE", direction_policy="BOTH", liquidity_state="BAD")
    )

    assert good.liquidity_penalty < ok.liquidity_penalty < bad.liquidity_penalty


def test_state_vector_v2_volatility_penalty_increases_with_higher_volatility():
    calm = build_state_vector_v2_from_raw(
        StateRawSnapshot(market_mode="RANGE", direction_policy="BOTH", liquidity_state="GOOD", s_volatility=0.10)
    )
    hot = build_state_vector_v2_from_raw(
        StateRawSnapshot(market_mode="RANGE", direction_policy="BOTH", liquidity_state="GOOD", s_volatility=0.80)
    )

    assert hot.volatility_penalty > calm.volatility_penalty
