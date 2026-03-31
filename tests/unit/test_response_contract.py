from backend.trading.engine.core.context import build_engine_context
from backend.trading.engine.core.models import ResponseRawSnapshot, ResponseVectorV2
from backend.trading.engine.response import (
    build_response_raw_snapshot,
    build_response_vector_execution_bridge_from_raw,
    build_response_vector_from_raw,
    build_response_vector_v2_from_raw,
)
from backend.trading.engine.response.context_gate import compute_response_context_gate


def test_response_raw_snapshot_captures_detector_outputs():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=96.0,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        metadata={
            "current_open": 100.2,
            "current_high": 101.0,
            "current_low": 89.95,
            "current_close": 100.5,
            "previous_close": 99.0,
            "band_touch_tolerance": 0.2,
            "box_touch_tolerance": 0.2,
        },
    )

    raw = build_response_raw_snapshot(ctx)

    assert isinstance(raw, ResponseRawSnapshot)
    assert raw.bb20_lower_hold > 0.0
    assert raw.bb20_mid_reclaim > 0.0
    assert raw.box_lower_bounce > 0.0
    assert raw.candle_lower_reject > 0.0
    assert raw.metadata["response_contract"] == "raw_snapshot_v1"
    assert raw.metadata["candle_descriptor_v1"]["version"] == "candle_descriptor_v1"
    assert raw.metadata["candle_pattern_v1"]["version"] == "candle_pattern_v1"
    assert raw.metadata["candle_motif_v1"]["version"] == "candle_motif_v1"
    assert raw.metadata["structure_motif_v1"]["version"] == "structure_motif_v1"
    assert raw.metadata["candle_descriptor_v1"]["lower_wick_energy"] > 0.0
    assert raw.metadata["candle_descriptor_v1"]["close_location_energy"] > 0.0


def test_response_raw_snapshot_exposes_candle_descriptor_v1():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=101.0,
        volatility_scale=8.0,
        metadata={
            "current_open": 100.0,
            "current_high": 102.0,
            "current_low": 90.0,
            "current_close": 101.0,
            "previous_open": 99.5,
            "previous_close": 99.8,
            "recent_range_mean": 8.0,
            "recent_body_mean": 3.0,
        },
    )

    raw = build_response_raw_snapshot(ctx)
    descriptor = raw.metadata["candle_descriptor_v1"]

    assert round(descriptor["body_signed_energy"], 3) == 0.083
    assert round(descriptor["body_shape_energy"], 3) == 0.083
    assert round(descriptor["upper_wick_energy"], 3) == 0.083
    assert round(descriptor["lower_wick_energy"], 3) == 0.833
    assert round(descriptor["close_location_energy"], 3) == 0.833
    assert round(descriptor["wick_balance_energy"], 3) == 0.75
    assert round(descriptor["range_size_energy"], 2) == 1.5
    assert round(descriptor["body_size_energy"], 2) == 0.33
    assert raw.candle_lower_reject > 0.0


def test_response_raw_snapshot_scores_hammer_like_pattern():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=101.0,
        volatility_scale=8.0,
        metadata={
            "current_open": 100.0,
            "current_high": 102.0,
            "current_low": 90.0,
            "current_close": 101.0,
            "previous_open": 99.5,
            "previous_high": 100.5,
            "previous_low": 97.8,
            "previous_close": 99.8,
            "pre_previous_open": 100.2,
            "pre_previous_high": 100.7,
            "pre_previous_low": 98.9,
            "pre_previous_close": 99.7,
            "recent_range_mean": 8.0,
            "recent_body_mean": 3.0,
        },
    )

    raw = build_response_raw_snapshot(ctx)
    patterns = raw.metadata["candle_pattern_v1"]["single_candle_patterns_v1"]
    motifs = raw.metadata["candle_motif_v1"]

    assert patterns["hammer_like"] > 0.55
    assert patterns["shooting_star_like"] < patterns["hammer_like"]
    assert "hammer_like" in raw.metadata["fired_candle_patterns"]
    assert motifs["bull_reject"] > motifs["bear_reject"]
    assert "bull_reject" in raw.metadata["fired_candle_motifs"]


def test_response_raw_snapshot_scores_bullish_engulfing_like_pattern():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=104.5,
        volatility_scale=5.0,
        metadata={
            "current_open": 99.5,
            "current_high": 105.0,
            "current_low": 99.2,
            "current_close": 104.5,
            "previous_open": 103.5,
            "previous_high": 104.0,
            "previous_low": 99.4,
            "previous_close": 100.2,
            "pre_previous_open": 104.0,
            "pre_previous_high": 104.5,
            "pre_previous_low": 102.8,
            "pre_previous_close": 103.2,
            "recent_range_mean": 4.5,
            "recent_body_mean": 2.4,
        },
    )

    raw = build_response_raw_snapshot(ctx)
    patterns = raw.metadata["candle_pattern_v1"]["two_bar_patterns_v1"]
    motifs = raw.metadata["candle_motif_v1"]

    assert patterns["bullish_engulfing_like"] > 0.60
    assert patterns["bearish_engulfing_like"] < 0.30
    assert motifs["bull_reversal_2bar"] > motifs["bear_reversal_2bar"]


def test_response_raw_snapshot_scores_morning_star_like_pattern():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.4,
        volatility_scale=4.0,
        metadata={
            "current_open": 97.8,
            "current_high": 100.8,
            "current_low": 97.6,
            "current_close": 100.4,
            "previous_open": 97.2,
            "previous_high": 97.7,
            "previous_low": 96.7,
            "previous_close": 97.1,
            "pre_previous_open": 101.5,
            "pre_previous_high": 101.7,
            "pre_previous_low": 97.0,
            "pre_previous_close": 97.4,
            "recent_range_mean": 3.8,
            "recent_body_mean": 2.1,
        },
    )

    raw = build_response_raw_snapshot(ctx)
    patterns = raw.metadata["candle_pattern_v1"]["three_bar_patterns_v1"]
    motifs = raw.metadata["candle_motif_v1"]

    assert patterns["morning_star_like"] > 0.55
    assert patterns["evening_star_like"] < patterns["morning_star_like"]
    assert motifs["bull_reversal_3bar"] > motifs["bear_reversal_3bar"]


def test_response_raw_snapshot_scores_indecision_motif_from_doji_family():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.02,
        volatility_scale=3.0,
        metadata={
            "current_open": 100.0,
            "current_high": 101.2,
            "current_low": 98.8,
            "current_close": 100.03,
            "previous_open": 100.6,
            "previous_high": 101.0,
            "previous_low": 99.1,
            "previous_close": 100.1,
            "pre_previous_open": 100.4,
            "pre_previous_high": 100.9,
            "pre_previous_low": 99.0,
            "pre_previous_close": 100.2,
            "recent_range_mean": 2.1,
            "recent_body_mean": 0.7,
        },
    )

    raw = build_response_raw_snapshot(ctx)
    motifs = raw.metadata["candle_motif_v1"]

    assert motifs["indecision"] > 0.55
    assert "indecision" in raw.metadata["fired_candle_motifs"]


def test_response_raw_snapshot_detects_bottom_patterns():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=11.6,
        volatility_scale=2.0,
        metadata={
            "pattern_recent_highs": [11.0, 9.7, 11.5, 9.8, 12.0, 10.0, 12.4],
            "pattern_recent_lows": [10.0, 8.6, 9.6, 7.7, 10.2, 8.5, 10.8],
            "pattern_recent_closes": [10.7, 8.4, 10.8, 8.6, 11.2, 8.9, 11.6],
        },
    )

    raw = build_response_raw_snapshot(ctx)
    structure_motif = raw.metadata["structure_motif_v1"]

    assert raw.pattern_double_bottom > 0.0
    assert raw.pattern_inverse_head_shoulders > 0.0
    assert "pattern_double_bottom" in raw.metadata["fired_patterns"]
    assert structure_motif["reversal_base_up"] > structure_motif["reversal_top_down"]
    assert structure_motif["support_hold_confirm"] > 0.0


def test_response_raw_snapshot_detects_top_patterns():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=8.7,
        volatility_scale=2.0,
        metadata={
            "pattern_recent_highs": [10.0, 11.5, 9.8, 12.6, 10.0, 11.6, 9.1],
            "pattern_recent_lows": [9.0, 10.7, 9.1, 10.8, 9.0, 10.6, 8.5],
            "pattern_recent_closes": [9.7, 11.0, 9.4, 11.8, 9.3, 11.1, 8.7],
        },
    )

    raw = build_response_raw_snapshot(ctx)
    structure_motif = raw.metadata["structure_motif_v1"]

    assert raw.pattern_double_top > 0.0
    assert raw.pattern_head_shoulders > 0.0
    assert "pattern_head_shoulders" in raw.metadata["fired_patterns"]
    assert structure_motif["reversal_top_down"] > structure_motif["reversal_base_up"]
    assert structure_motif["resistance_reject_confirm"] > 0.0


def test_response_raw_snapshot_exposes_sr_support_hold_subsystem():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.3,
        support=100.0,
        resistance=110.0,
        volatility_scale=4.0,
        metadata={
            "current_open": 99.8,
            "current_high": 100.7,
            "current_low": 99.6,
            "current_close": 100.4,
            "previous_close": 99.7,
            "sr_touch_tolerance": 0.5,
        },
    )

    raw = build_response_raw_snapshot(ctx)
    sr_meta = raw.metadata["sr_subsystem_v1"]

    assert raw.sr_support_touch > 0.0
    assert raw.sr_support_hold > 0.0
    assert raw.sr_support_break == 0.0
    assert sr_meta["strengths"]["support_hold_strength"] > sr_meta["strengths"]["support_break_strength"]
    assert "r_sr_support_hold" in sr_meta["fired_signals"]


def test_response_raw_snapshot_exposes_sr_resistance_break_subsystem():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=110.9,
        support=100.0,
        resistance=110.0,
        volatility_scale=4.0,
        metadata={
            "current_open": 109.8,
            "current_high": 111.2,
            "current_low": 109.6,
            "current_close": 110.95,
            "previous_close": 109.7,
            "sr_touch_tolerance": 0.5,
        },
    )

    raw = build_response_raw_snapshot(ctx)
    sr_meta = raw.metadata["sr_subsystem_v1"]

    assert raw.sr_resistance_touch > 0.0
    assert raw.sr_resistance_break > 0.0
    assert raw.sr_resistance_reject == 0.0
    assert raw.sr_resistance_reclaim > 0.0
    assert sr_meta["strengths"]["resistance_break_strength"] >= raw.sr_resistance_break
    assert "r_sr_resistance_break" in sr_meta["fired_signals"]


def test_response_raw_snapshot_exposes_trendline_support_hold_subsystem():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.2,
        volatility_scale=4.0,
        metadata={
            "mtf_trendline_map_v1": {
                "entries": {
                    "15M": {
                        "support_value": 100.0,
                        "support_proximity": 0.82,
                        "resistance_value": 110.0,
                        "resistance_proximity": 0.10,
                    }
                }
            },
            "mtf_trendline_bar_map_v1": {
                "entries": {
                    "15M": {
                        "open": 99.8,
                        "high": 100.6,
                        "low": 99.7,
                        "close": 100.35,
                        "previous_close": 99.6,
                    }
                }
            },
            "trendline_touch_tolerance": 0.5,
        },
    )

    raw = build_response_raw_snapshot(ctx)
    trend_meta = raw.metadata["trendline_subsystem_v1"]

    assert raw.trend_support_touch_m15 > 0.0
    assert raw.trend_support_hold_m15 > 0.0
    assert raw.trend_support_break_m15 == 0.0
    assert trend_meta["strengths"]["trend_support_hold_strength"] > 0.0
    assert "r_trend_support_hold_m15" in trend_meta["fired_signals"]


def test_response_raw_snapshot_exposes_trendline_resistance_break_subsystem():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=110.8,
        volatility_scale=4.0,
        metadata={
            "mtf_trendline_map_v1": {
                "entries": {
                    "1H": {
                        "support_value": 100.0,
                        "support_proximity": 0.12,
                        "resistance_value": 110.0,
                        "resistance_proximity": 0.86,
                    }
                }
            },
            "mtf_trendline_bar_map_v1": {
                "entries": {
                    "1H": {
                        "open": 109.9,
                        "high": 111.1,
                        "low": 109.7,
                        "close": 110.9,
                        "previous_close": 109.5,
                    }
                }
            },
            "trendline_touch_tolerance": 0.5,
        },
    )

    raw = build_response_raw_snapshot(ctx)
    trend_meta = raw.metadata["trendline_subsystem_v1"]

    assert raw.trend_resistance_touch_h1 > 0.0
    assert raw.trend_resistance_break_h1 > 0.0
    assert raw.trend_resistance_reject_h1 == 0.0
    assert trend_meta["strengths"]["trend_resistance_break_strength"] > 0.0
    assert "r_trend_resistance_break_h1" in trend_meta["fired_signals"]


def test_response_raw_snapshot_allows_proximity_rebound_to_promote_trend_support_hold():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=101.3,
        volatility_scale=4.0,
        metadata={
            "mtf_trendline_map_v1": {
                "entries": {
                    "15M": {
                        "support_value": 100.0,
                        "support_proximity": 0.74,
                        "resistance_value": 110.0,
                        "resistance_proximity": 0.08,
                    }
                }
            },
            "mtf_trendline_bar_map_v1": {
                "entries": {
                    "15M": {
                        "open": 100.7,
                        "high": 101.5,
                        "low": 100.92,
                        "close": 101.3,
                        "previous_close": 100.6,
                    }
                }
            },
            "trendline_touch_tolerance": 0.25,
        },
    )

    raw = build_response_raw_snapshot(ctx)

    assert raw.trend_support_touch_m15 > 0.0
    assert raw.trend_support_hold_m15 > 0.0
    assert raw.metadata["trendline_subsystem_v1"]["strengths"]["trend_support_hold_strength"] > 0.0


def test_response_raw_snapshot_exposes_micro_tf_bull_reject_strength():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.3,
        volatility_scale=4.0,
        metadata={
            "micro_tf_bar_map_v1": {
                "entries": {
                    "1M": {"open": 100.0, "high": 100.9, "low": 98.8, "close": 100.5, "previous_close": 99.9},
                    "5M": {"open": 99.9, "high": 100.8, "low": 99.0, "close": 100.4, "previous_close": 99.7},
                }
            },
            "micro_tf_window_map_v1": {
                "entries": {
                    "1M": {
                        "opens": [100.4, 100.1, 100.0],
                        "highs": [100.6, 100.3, 100.9],
                        "lows": [99.9, 99.2, 98.8],
                        "closes": [100.0, 99.8, 100.5],
                    },
                    "5M": {
                        "opens": [100.6, 100.2, 99.9],
                        "highs": [100.8, 100.4, 100.8],
                        "lows": [99.8, 99.3, 99.0],
                        "closes": [100.1, 99.7, 100.4],
                    },
                }
            },
        },
    )

    raw = build_response_raw_snapshot(ctx)
    micro_meta = raw.metadata["micro_tf_subsystem_v1"]

    assert raw.micro_bull_reject > 0.0
    assert micro_meta["strengths"]["micro_bull_reject_strength"] > micro_meta["strengths"]["micro_bear_reject_strength"]
    assert "micro_bull_reject_strength" in micro_meta["fired_strengths"]
    assert "1M" in micro_meta["timeframes_available"]
    assert "5M" in micro_meta["timeframes_available"]


def test_response_raw_snapshot_exposes_micro_tf_bear_break_strength():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=98.2,
        volatility_scale=4.0,
        metadata={
            "micro_tf_bar_map_v1": {
                "entries": {
                    "1M": {"open": 99.8, "high": 99.9, "low": 98.0, "close": 98.2, "previous_close": 99.5},
                    "5M": {"open": 100.4, "high": 100.5, "low": 98.0, "close": 98.2, "previous_close": 100.0},
                }
            },
            "micro_tf_window_map_v1": {
                "entries": {
                    "1M": {
                        "opens": [100.1, 99.9, 99.8],
                        "highs": [100.2, 100.0, 99.9],
                        "lows": [99.7, 99.2, 98.0],
                        "closes": [99.9, 99.4, 98.2],
                    },
                    "5M": {
                        "opens": [100.8, 100.3, 100.4],
                        "highs": [100.9, 100.4, 100.5],
                        "lows": [100.0, 99.1, 98.0],
                        "closes": [100.2, 99.8, 98.2],
                    },
                }
            },
        },
    )

    raw = build_response_raw_snapshot(ctx)
    micro_meta = raw.metadata["micro_tf_subsystem_v1"]

    assert raw.micro_bear_break > 0.0
    assert micro_meta["strengths"]["micro_bear_break_strength"] >= micro_meta["strengths"]["micro_bull_break_strength"]
    assert "micro_bear_break_strength" in micro_meta["fired_strengths"]


def test_response_raw_snapshot_context_gate_promotes_lower_reversal_in_lower_context():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.3,
        support=100.0,
        resistance=110.0,
        volatility_scale=4.0,
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "current_open": 100.0,
            "current_high": 100.9,
            "current_low": 98.8,
            "current_close": 100.5,
            "previous_open": 100.4,
            "previous_high": 100.6,
            "previous_low": 99.2,
            "previous_close": 100.0,
            "pre_previous_open": 100.6,
            "pre_previous_high": 100.8,
            "pre_previous_low": 99.8,
            "pre_previous_close": 100.1,
            "recent_range_mean": 2.4,
            "recent_body_mean": 0.8,
            "sr_touch_tolerance": 0.5,
            "micro_tf_bar_map_v1": {
                "entries": {
                    "1M": {"open": 100.0, "high": 100.9, "low": 98.8, "close": 100.5, "previous_close": 99.9},
                    "5M": {"open": 99.9, "high": 100.8, "low": 99.0, "close": 100.4, "previous_close": 99.7},
                }
            },
            "micro_tf_window_map_v1": {
                "entries": {
                    "1M": {
                        "opens": [100.4, 100.1, 100.0],
                        "highs": [100.6, 100.3, 100.9],
                        "lows": [99.9, 99.2, 98.8],
                        "closes": [100.0, 99.8, 100.5],
                    },
                    "5M": {
                        "opens": [100.6, 100.2, 99.9],
                        "highs": [100.8, 100.4, 100.8],
                        "lows": [99.8, 99.3, 99.0],
                        "closes": [100.1, 99.7, 100.4],
                    },
                }
            },
            "position_gate_input_v1": {
                "zones": {"box_zone": "LOWER", "bb20_zone": "LOWER_EDGE", "bb44_zone": "LOWER"},
                "interpretation": {
                    "primary_label": "LOWER_BIAS",
                    "secondary_context_label": "LOWER_CONTEXT",
                    "mtf_context_weight_profile_v1": {"bias": 0.42, "owner": "STATE_CANDIDATE"},
                },
                "energy": {
                    "middle_neutrality": 0.12,
                    "position_conflict_score": 0.05,
                    "lower_position_force": 0.76,
                    "upper_position_force": 0.18,
                },
                "position_scale": {"compression_score": 0.18, "expansion_score": 0.26, "map_size_state": "NORMAL"},
            },
        },
    )

    raw = build_response_raw_snapshot(ctx)
    gate = raw.metadata["response_context_gate_v1"]

    assert gate["version"] == "response_context_gate_v1"
    assert gate["gated_candle_motif_v1"]["bull_reject"] > gate["gated_candle_motif_v1"]["bear_reject"]
    assert gate["pre_axis_candidates"]["lower_hold_candidate"] > gate["pre_axis_candidates"]["upper_reject_candidate"]
    assert "lower_hold_candidate" in raw.metadata["fired_context_gate_candidates"]


def test_response_raw_snapshot_context_gate_suppresses_lower_reversal_in_middle_context():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.3,
        volatility_scale=4.0,
        box_state="MIDDLE",
        bb_state="MID",
        metadata={
            "current_open": 100.0,
            "current_high": 100.9,
            "current_low": 98.8,
            "current_close": 100.5,
            "previous_open": 100.4,
            "previous_high": 100.6,
            "previous_low": 99.2,
            "previous_close": 100.0,
            "pre_previous_open": 100.6,
            "pre_previous_high": 100.8,
            "pre_previous_low": 99.8,
            "pre_previous_close": 100.1,
            "recent_range_mean": 2.4,
            "recent_body_mean": 0.8,
            "position_gate_input_v1": {
                "zones": {"box_zone": "MIDDLE", "bb20_zone": "MIDDLE", "bb44_zone": "LOWER"},
                "interpretation": {
                    "primary_label": "UNRESOLVED_POSITION",
                    "secondary_context_label": "NEUTRAL_CONTEXT",
                    "mtf_context_weight_profile_v1": {"bias": 0.0, "owner": "STATE_CANDIDATE"},
                },
                "energy": {
                    "middle_neutrality": 0.74,
                    "position_conflict_score": 0.18,
                    "lower_position_force": 0.24,
                    "upper_position_force": 0.20,
                },
                "position_scale": {"compression_score": 0.12, "expansion_score": 0.10, "map_size_state": "NORMAL"},
            },
        },
    )

    raw = build_response_raw_snapshot(ctx)
    gate = raw.metadata["response_context_gate_v1"]

    assert gate["gated_candle_motif_v1"]["bull_reject"] < raw.metadata["candle_motif_v1"]["bull_reject"]
    assert gate["pre_axis_candidates"]["lower_hold_candidate"] < 0.40
    assert gate["gate_weights"]["ambiguity_penalty"] >= 0.58


def test_context_gate_rearms_buy_after_failed_breakdown_squeeze():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.2,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        volatility_scale=4.0,
        metadata={
            "position_gate_input_v1": {
                "zones": {"box_zone": "LOWER", "bb20_zone": "LOWER_EDGE", "bb44_zone": "LOWER"},
                "interpretation": {
                    "primary_label": "LOWER_BIAS",
                    "secondary_context_label": "LOWER_CONTEXT",
                    "mtf_context_weight_profile_v1": {"bias": 0.12, "owner": "STATE_CANDIDATE"},
                },
                "energy": {
                    "middle_neutrality": 0.10,
                    "position_conflict_score": 0.06,
                    "lower_position_force": 0.72,
                    "upper_position_force": 0.18,
                },
                "position_scale": {"compression_score": 0.18, "expansion_score": 0.22, "map_size_state": "NORMAL"},
            }
        },
    )

    gate = compute_response_context_gate(
        ctx,
        candle_motif={
            "bull_reject": 0.58,
            "bull_reversal_2bar": 0.22,
            "bull_reversal_3bar": 0.0,
            "bull_break_body": 0.16,
            "bear_break_body": 0.14,
            "bear_reversal_2bar": 0.0,
            "bear_reversal_3bar": 0.0,
            "indecision": 0.18,
            "climax": 0.0,
        },
        structure_motif={
            "reversal_base_up": 0.52,
            "reversal_top_down": 0.0,
            "support_hold_confirm": 0.44,
            "resistance_reject_confirm": 0.0,
        },
        sr_subsystem={
            "sr_support_proximity": 0.64,
            "sr_resistance_proximity": 0.10,
            "strengths": {
                "support_hold_strength": 0.0,
                "support_break_strength": 0.0,
                "resistance_reject_strength": 0.0,
                "resistance_break_strength": 0.0,
            },
        },
        trendline_subsystem={
            "strengths": {
                "trend_support_hold_strength": 0.0,
                "trend_support_break_strength": 0.78,
                "trend_resistance_reject_strength": 0.0,
                "trend_resistance_break_strength": 0.0,
            },
            "per_timeframe": {
                "1M": {"support_proximity": 0.84, "resistance_proximity": 0.20},
                "15M": {"support_proximity": 0.62, "resistance_proximity": 0.10},
            },
        },
        micro_subsystem={
            "strengths": {
                "micro_bull_reject_strength": 0.68,
                "micro_bear_reject_strength": 0.10,
                "micro_bull_break_strength": 0.24,
                "micro_bear_break_strength": 0.22,
                "micro_indecision_strength": 0.18,
                "micro_reclaim_up_strength": 0.12,
                "micro_lose_down_strength": 0.06,
            }
        },
    )

    failed_break = gate["failed_breakdown_squeeze_v1"]

    assert failed_break["failed_breakdown_strength"] >= 0.45
    assert failed_break["squeeze_up_strength"] > 0.0
    assert gate["pre_axis_candidates"]["lower_hold_candidate"] > gate["pre_axis_candidates"]["lower_break_candidate"]
    assert gate["pre_axis_candidates"]["mid_reclaim_candidate"] > 0.20


def test_legacy_response_vector_is_derived_from_raw_snapshot():
    raw = ResponseRawSnapshot(
        bb20_lower_hold=0.8,
        bb20_mid_reclaim=0.6,
        box_lower_bounce=0.7,
        candle_lower_reject=0.5,
        sr_support_hold=0.45,
        trend_support_hold_m15=0.41,
        micro_bull_reject=0.39,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_from_raw(raw)

    assert vector.r_bb20_lower_hold == 0.8
    assert vector.r_bb20_mid_reclaim == 0.6
    assert vector.r_box_lower_bounce == 0.7
    assert vector.r_candle_lower_reject == 0.5
    assert vector.r_sr_support_hold == 0.45
    assert vector.r_trend_support_hold_m15 == 0.41
    assert vector.r_micro_bull_reject == 0.39
    assert vector.metadata["response_contract"] == "legacy_vector_v1"
    assert vector.metadata["raw_snapshot_contract"] == "raw_snapshot_v1"


def test_response_vector_v2_exposes_canonical_transition_axes():
    raw = ResponseRawSnapshot(
        bb20_lower_hold=0.8,
        bb44_lower_hold=0.4,
        box_lower_bounce=0.7,
        candle_lower_reject=0.5,
        bb20_mid_reclaim=0.6,
        bb20_upper_reject=0.9,
        box_upper_break=0.75,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert isinstance(vector, ResponseVectorV2)
    assert vector.lower_hold_up > 0.8
    assert vector.mid_reclaim_up == 0.6
    assert vector.upper_reject_down == 0.9
    assert vector.upper_break_up == 0.75
    assert vector.metadata["response_contract"] == "canonical_v2"
    assert vector.metadata["raw_snapshot_contract"] == "raw_snapshot_v1"
    assert vector.metadata["dominant_source_by_axis"]["lower_hold_up"] == "bb20_lower_hold"
    assert vector.metadata["dominant_role_by_axis"]["lower_hold_up"] == "primary"
    assert vector.metadata["mapping_mode"] == "context_gated_candidate_primary_only"


def test_response_vector_v2_caps_duplicate_primary_signals():
    raw = ResponseRawSnapshot(
        bb20_upper_reject=1.0,
        box_upper_reject=1.0,
        bb44_upper_reject=1.0,
        candle_upper_reject=1.0,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.upper_reject_down == 1.0
    assert vector.metadata["dominant_role_by_axis"]["upper_reject_down"] == "primary"
    assert vector.metadata["legacy_axis_merge_debug"]["upper_reject_down"]["primary_support"] <= 0.20
    assert vector.metadata["legacy_axis_merge_debug"]["upper_reject_down"]["confirmation_support"] <= 0.12


def test_response_vector_v2_uses_confirmation_sources_when_primary_is_missing():
    raw = ResponseRawSnapshot(
        bb44_lower_hold=1.0,
        candle_lower_reject=0.5,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert 0.82 <= vector.lower_hold_up < 1.0
    assert vector.metadata["dominant_source_by_axis"]["lower_hold_up"] == "bb44_lower_hold"
    assert vector.metadata["dominant_role_by_axis"]["lower_hold_up"] == "confirmation"


def test_response_vector_v2_uses_patterns_as_amplifier_only():
    raw = ResponseRawSnapshot(
        box_lower_bounce=0.60,
        pattern_double_bottom=1.0,
        pattern_inverse_head_shoulders=0.8,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.lower_hold_up > 0.60
    assert vector.metadata["legacy_axis_merge_debug"]["lower_hold_up"]["amplifier_support"] > 0.0
    assert vector.metadata["dominant_role_by_axis"]["lower_hold_up"] == "primary"


def test_response_vector_v2_uses_context_gate_candidate_as_primary_owner():
    raw = ResponseRawSnapshot(
        bb20_lower_hold=0.9,
        box_lower_bounce=0.8,
        metadata={
            "response_contract": "raw_snapshot_v1",
            "response_context_gate_v1": {
                "pre_axis_candidates": {
                    "lower_hold_candidate": 0.30,
                    "lower_break_candidate": 0.10,
                    "mid_reclaim_candidate": 0.0,
                    "mid_lose_candidate": 0.0,
                    "upper_reject_candidate": 0.05,
                    "upper_break_candidate": 0.0,
                }
            },
        },
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.lower_hold_up == 0.30
    assert vector.metadata["dominant_source_by_axis"]["lower_hold_up"] == "lower_hold_candidate"
    assert vector.metadata["dominant_role_by_axis"]["lower_hold_up"] == "gated_candidate"
    assert vector.metadata["axis_merge_debug"]["lower_hold_up"]["candidate_value"] == 0.30
    assert vector.metadata["semantic_owner_contract"] == "context_gate_candidate_primary_only_v1"
    assert vector.metadata["legacy_semantic_blend_enabled"] is False


def test_response_vector_v2_does_not_revive_legacy_axis_when_context_gate_zeroes_it():
    raw = ResponseRawSnapshot(
        bb20_lower_hold=0.95,
        box_lower_bounce=0.90,
        metadata={
            "response_contract": "raw_snapshot_v1",
            "response_context_gate_v1": {
                "pre_axis_candidates": {
                    "lower_hold_candidate": 0.0,
                    "lower_break_candidate": 0.0,
                    "mid_reclaim_candidate": 0.0,
                    "mid_lose_candidate": 0.0,
                    "upper_reject_candidate": 0.0,
                    "upper_break_candidate": 0.0,
                }
            },
        },
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.lower_hold_up == 0.0
    assert vector.metadata["dominant_source_by_axis"]["lower_hold_up"] == ""
    assert vector.metadata["dominant_role_by_axis"]["lower_hold_up"] == "gated_zero"
    assert vector.metadata["axis_merge_debug"]["lower_hold_up"]["used_technical_legacy_fallback"] is False


def test_response_vector_v2_context_gate_freezes_all_axes_when_present():
    raw = ResponseRawSnapshot(
        bb20_lower_hold=0.95,
        box_lower_bounce=0.90,
        bb20_lower_break=0.88,
        box_lower_break=0.82,
        bb20_mid_hold=0.77,
        bb20_mid_reclaim=0.79,
        bb20_mid_reject=0.73,
        bb20_mid_lose=0.71,
        bb20_upper_reject=0.92,
        box_upper_reject=0.87,
        bb20_upper_break=0.83,
        box_upper_break=0.81,
        metadata={
            "response_contract": "raw_snapshot_v1",
            "response_context_gate_v1": {
                "pre_axis_candidates": {
                    "lower_hold_candidate": 0.21,
                    "lower_break_candidate": 0.34,
                    "mid_reclaim_candidate": 0.43,
                    "mid_lose_candidate": 0.27,
                    "upper_reject_candidate": 0.61,
                    "upper_break_candidate": 0.18,
                }
            },
        },
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.lower_hold_up == 0.21
    assert vector.lower_break_down == 0.34
    assert vector.mid_reclaim_up == 0.43
    assert vector.mid_lose_down == 0.27
    assert vector.upper_reject_down == 0.61
    assert vector.upper_break_up == 0.18
    assert all(
        debug["used_technical_legacy_fallback"] is False
        for debug in vector.metadata["axis_merge_debug"].values()
    )


def test_response_vector_v2_uses_technical_legacy_fallback_only_when_gate_is_missing():
    raw = ResponseRawSnapshot(
        bb20_upper_reject=0.72,
        box_upper_reject=0.64,
        bb44_upper_reject=0.40,
        candle_upper_reject=0.50,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.upper_reject_down > 0.72
    assert vector.metadata["context_gate_present"] is False
    assert vector.metadata["dominant_role_by_axis"]["upper_reject_down"] == "primary"
    assert vector.metadata["axis_merge_debug"]["upper_reject_down"]["used_technical_legacy_fallback"] is True
    assert vector.metadata["technical_legacy_fallback_on_missing_gate_only"] is True


def test_response_vector_v2_does_not_create_signal_from_pattern_only():
    raw = ResponseRawSnapshot(
        pattern_double_top=1.0,
        pattern_head_shoulders=1.0,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.upper_reject_down == 0.0
    assert vector.mid_lose_down == 0.0
    assert vector.metadata["dominant_role_by_axis"]["upper_reject_down"] == "none"


def test_response_vector_v2_keeps_axis_mapping_centralized():
    raw = ResponseRawSnapshot(
        bb20_mid_hold=0.55,
        bb20_mid_reclaim=0.60,
        box_mid_hold=0.40,
        bb20_mid_reject=0.20,
        box_mid_reject=0.30,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.mid_reclaim_up > vector.mid_lose_down
    assert set(vector.metadata["axis_source_roles"]["mid_reclaim_up"]["primary_sources"]) == {
        "bb20_mid_hold",
        "bb20_mid_reclaim",
        "box_mid_hold",
    }


def test_response_vector_v2_maps_lower_break_axis():
    raw = ResponseRawSnapshot(
        bb20_lower_break=0.9,
        box_lower_break=0.5,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.lower_break_down > 0.9
    assert vector.metadata["dominant_source_by_axis"]["lower_break_down"] == "bb20_lower_break"
    assert vector.metadata["dominant_role_by_axis"]["lower_break_down"] == "primary"


def test_response_vector_v2_maps_mid_lose_axis():
    raw = ResponseRawSnapshot(
        bb20_mid_reject=0.55,
        bb20_mid_lose=0.8,
        box_mid_reject=0.45,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.mid_lose_down > 0.8
    assert vector.metadata["dominant_source_by_axis"]["mid_lose_down"] == "bb20_mid_lose"
    assert vector.metadata["dominant_role_by_axis"]["mid_lose_down"] == "primary"


def test_response_vector_v2_maps_upper_break_axis():
    raw = ResponseRawSnapshot(
        bb20_upper_break=0.7,
        box_upper_break=0.6,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    vector = build_response_vector_v2_from_raw(raw)

    assert vector.upper_break_up > 0.7
    assert vector.metadata["dominant_source_by_axis"]["upper_break_up"] == "bb20_upper_break"
    assert vector.metadata["dominant_role_by_axis"]["upper_break_up"] == "primary"


def test_response_vector_v2_is_symmetric_for_lower_hold_and_upper_reject():
    lower_raw = ResponseRawSnapshot(
        bb20_lower_hold=0.72,
        bb44_lower_hold=0.40,
        box_lower_bounce=0.64,
        candle_lower_reject=0.50,
        metadata={"response_contract": "raw_snapshot_v1"},
    )
    upper_raw = ResponseRawSnapshot(
        bb20_upper_reject=0.72,
        bb44_upper_reject=0.40,
        box_upper_reject=0.64,
        candle_upper_reject=0.50,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    lower_vector = build_response_vector_v2_from_raw(lower_raw)
    upper_vector = build_response_vector_v2_from_raw(upper_raw)

    assert lower_vector.lower_hold_up == upper_vector.upper_reject_down


def test_response_vector_v2_is_symmetric_for_break_axes():
    lower_raw = ResponseRawSnapshot(
        bb20_lower_break=0.82,
        box_lower_break=0.48,
        metadata={"response_contract": "raw_snapshot_v1"},
    )
    upper_raw = ResponseRawSnapshot(
        bb20_upper_break=0.82,
        box_upper_break=0.48,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    lower_vector = build_response_vector_v2_from_raw(lower_raw)
    upper_vector = build_response_vector_v2_from_raw(upper_raw)

    assert lower_vector.lower_break_down == upper_vector.upper_break_up


def test_response_vector_v2_is_symmetric_for_mid_axes():
    reclaim_raw = ResponseRawSnapshot(
        bb20_mid_hold=0.52,
        bb20_mid_reclaim=0.78,
        box_mid_hold=0.44,
        metadata={"response_contract": "raw_snapshot_v1"},
    )
    lose_raw = ResponseRawSnapshot(
        bb20_mid_reject=0.52,
        bb20_mid_lose=0.78,
        box_mid_reject=0.44,
        metadata={"response_contract": "raw_snapshot_v1"},
    )

    reclaim_vector = build_response_vector_v2_from_raw(reclaim_raw)
    lose_vector = build_response_vector_v2_from_raw(lose_raw)

    assert reclaim_vector.mid_reclaim_up == lose_vector.mid_lose_down


def test_response_vector_execution_bridge_replaces_legacy_core_fields_with_canonical_axes():
    raw = ResponseRawSnapshot(
        bb20_lower_hold=0.70,
        bb20_lower_break=0.80,
        bb20_mid_hold=0.20,
        bb20_mid_reclaim=0.10,
        bb20_mid_reject=0.50,
        bb20_mid_lose=0.40,
        bb20_upper_reject=0.60,
        bb20_upper_break=0.30,
        bb44_lower_hold=0.25,
        bb44_upper_reject=0.20,
        box_lower_bounce=0.60,
        box_lower_break=0.70,
        box_mid_hold=0.18,
        box_mid_reject=0.35,
        box_upper_reject=0.55,
        box_upper_break=0.26,
        candle_lower_reject=0.45,
        candle_upper_reject=0.44,
        metadata={
            "response_context_gate_v1": {
                "pre_axis_candidates": {
                    "lower_hold_candidate": 0.22,
                    "lower_break_candidate": 0.0,
                    "mid_reclaim_candidate": 0.18,
                    "mid_lose_candidate": 0.04,
                    "upper_reject_candidate": 0.0,
                    "upper_break_candidate": 0.33,
                }
            }
        },
    )

    bridge = build_response_vector_execution_bridge_from_raw(raw)

    assert bridge.r_bb20_lower_hold == 0.22
    assert bridge.r_box_lower_break == 0.0
    assert bridge.r_bb20_mid_reclaim == 0.18
    assert bridge.r_bb20_upper_reject == 0.0
    assert bridge.r_bb20_upper_break == 0.33
    assert bridge.metadata["response_contract"] == "execution_bridge_v1"
    assert bridge.metadata["canonical_response_field"] == "response_vector_v2"
