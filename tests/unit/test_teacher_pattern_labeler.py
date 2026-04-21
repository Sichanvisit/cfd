from backend.services.teacher_pattern_labeler import build_teacher_pattern_payload_v2


def test_teacher_pattern_labeler_breakout_triangle_pair():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "BUY",
            "micro_breakout_readiness_state": "COILED_BREAKOUT",
            "micro_reversal_risk_state": "LOW_RISK",
            "micro_participation_state": "ACTIVE_PARTICIPATION",
            "micro_gap_context_state": "NO_GAP_CONTEXT",
            "micro_range_compression_ratio_20": 0.82,
            "micro_volume_burst_ratio_20": 2.1,
            "micro_volume_burst_decay_20": 0.18,
            "micro_same_color_run_current": 2,
            "micro_same_color_run_max_20": 3,
            "micro_doji_ratio_20": 0.24,
            "micro_swing_high_retest_count_20": 2,
            "micro_swing_low_retest_count_20": 2,
            "entry_setup_id": "breakout_prepare_buy",
        }
    )

    assert payload["teacher_pattern_id"] == 12
    assert payload["teacher_pattern_secondary_id"] == 23
    assert payload["teacher_entry_bias"] == "breakout"
    assert payload["teacher_label_version"] == "state25_v5"


def test_teacher_pattern_labeler_range_reversal_double_top_pair():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "SELL",
            "micro_reversal_risk_state": "HIGH_RISK",
            "micro_doji_ratio_20": 0.36,
            "micro_swing_high_retest_count_20": 2,
            "micro_swing_low_retest_count_20": 1,
            "entry_setup_id": "range_outer_band_reversal_sell",
        }
    )

    assert payload["teacher_pattern_id"] == 5
    assert payload["teacher_pattern_group"] == "D"
    assert payload["teacher_entry_bias"] == "fade"


def test_teacher_pattern_labeler_gap_fill_progress():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "BUY",
            "entry_session_name": "LONDON",
            "micro_gap_context_state": "GAP_PARTIAL_FILL",
            "micro_gap_fill_progress": 0.47,
            "micro_same_color_run_current": 2,
            "micro_body_size_pct_20": 0.12,
        }
    )

    assert payload["teacher_pattern_id"] == 21
    assert payload["teacher_pattern_group"] == "D"
    assert payload["teacher_label_confidence"] > 0.0


def test_teacher_pattern_labeler_promotes_explicit_range_reversal_over_quiet_loose_market():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "BUY",
            "entry_setup_id": "range_lower_reversal_buy",
            "micro_participation_state": "THIN_PARTICIPATION",
            "micro_reversal_risk_state": "HIGH_RISK",
            "micro_same_color_run_current": 1,
            "micro_same_color_run_max_20": 1,
            "micro_volume_burst_ratio_20": 0.84,
            "micro_doji_ratio_20": 0.0,
            "micro_range_compression_ratio_20": 0.0,
        }
    )

    assert payload["teacher_pattern_id"] == 5
    assert payload["teacher_pattern_group"] == "D"
    assert payload["teacher_entry_bias"] == "fade"


def test_teacher_pattern_labeler_does_not_promote_session_only_row_to_morning_consolidation():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "BUY",
            "entry_session_name": "LONDON",
            "entry_setup_id": "range_upper_reversal_sell",
            "micro_volume_burst_ratio_20": 0.0,
            "micro_range_compression_ratio_20": 0.0,
            "micro_doji_ratio_20": 0.0,
        }
    )

    assert payload == {}


def test_teacher_pattern_labeler_promotes_conflict_range_reversal_without_high_risk_to_pattern_5():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "SELL",
            "entry_setup_id": "range_upper_reversal_sell",
            "entry_wait_state": "CONFLICT",
            "micro_participation_state": "THIN_PARTICIPATION",
            "micro_reversal_risk_state": "",
            "micro_same_color_run_current": 1,
            "micro_same_color_run_max_20": 1,
            "micro_volume_burst_ratio_20": 0.8,
            "micro_doji_ratio_20": 0.0,
            "micro_range_compression_ratio_20": 0.0,
        }
    )

    assert payload["teacher_pattern_id"] == 5
    assert payload["teacher_pattern_group"] == "D"


def test_teacher_pattern_labeler_promotes_passive_high_risk_upper_reversal_sell_to_pattern_25():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "SELL",
            "entry_setup_id": "range_upper_reversal_sell",
            "entry_wait_state": "NOISE",
            "micro_participation_state": "THIN_PARTICIPATION",
            "micro_reversal_risk_state": "HIGH_RISK",
            "micro_same_color_run_current": 0,
            "micro_same_color_run_max_20": 0,
            "micro_volume_burst_ratio_20": 0.7,
            "micro_doji_ratio_20": 0.0,
            "micro_range_compression_ratio_20": 0.0,
        }
    )

    assert payload["teacher_pattern_id"] == 25
    assert payload["teacher_pattern_group"] == "D"
    assert payload["teacher_wait_bias"] == "avoid_wait"


def test_teacher_pattern_labeler_keeps_active_upper_reversal_sell_on_pattern_5():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "SELL",
            "entry_setup_id": "range_upper_reversal_sell",
            "entry_wait_state": "CONFLICT",
            "micro_participation_state": "THIN_PARTICIPATION",
            "micro_reversal_risk_state": "HIGH_RISK",
            "micro_same_color_run_current": 0,
            "micro_same_color_run_max_20": 0,
            "micro_volume_burst_ratio_20": 0.7,
            "micro_doji_ratio_20": 0.0,
            "micro_range_compression_ratio_20": 0.0,
        }
    )

    assert payload["teacher_pattern_id"] == 5
    assert payload["teacher_pattern_group"] == "D"


def test_teacher_pattern_labeler_promotes_confirm_pullback_buy_to_pattern_11():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "BUY",
            "entry_setup_id": "trend_pullback_buy",
            "entry_wait_state": "NONE",
            "entry_score": 170.0,
            "contra_score_at_entry": 59.0,
            "micro_same_color_run_current": 0,
            "micro_same_color_run_max_20": 0,
            "micro_volume_burst_ratio_20": 0.0,
            "micro_doji_ratio_20": 0.0,
            "micro_range_compression_ratio_20": 0.0,
        }
    )

    assert payload["teacher_pattern_id"] == 11
    assert payload["teacher_pattern_group"] == "D"
    assert payload["teacher_entry_bias"] == "confirm"


def test_teacher_pattern_labeler_keeps_conflict_pullback_buy_on_pattern_9():
    payload = build_teacher_pattern_payload_v2(
        {
            "direction": "BUY",
            "entry_setup_id": "trend_pullback_buy",
            "entry_wait_state": "CONFLICT",
            "entry_score": 170.0,
            "contra_score_at_entry": 59.0,
            "micro_same_color_run_current": 0,
            "micro_same_color_run_max_20": 0,
            "micro_volume_burst_ratio_20": 0.0,
            "micro_doji_ratio_20": 0.0,
            "micro_range_compression_ratio_20": 0.0,
        }
    )

    assert payload["teacher_pattern_id"] == 9
    assert payload["teacher_pattern_group"] == "E"


def test_teacher_pattern_labeler_applies_weight_override_surface_to_scores():
    baseline = build_teacher_pattern_payload_v2(
        {
            "direction": "SELL",
            "entry_setup_id": "range_upper_reversal_sell",
            "entry_wait_state": "NOISE",
            "micro_participation_state": "THIN_PARTICIPATION",
            "micro_reversal_risk_state": "HIGH_RISK",
            "micro_same_color_run_current": 0,
            "micro_same_color_run_max_20": 0,
            "micro_volume_burst_ratio_20": 0.7,
            "micro_doji_ratio_20": 0.0,
            "micro_range_compression_ratio_20": 0.0,
            "micro_upper_wick_ratio_20": 0.34,
        }
    )
    adjusted = build_teacher_pattern_payload_v2(
        {
            "direction": "SELL",
            "entry_setup_id": "range_upper_reversal_sell",
            "entry_wait_state": "NOISE",
            "micro_participation_state": "THIN_PARTICIPATION",
            "micro_reversal_risk_state": "HIGH_RISK",
            "micro_same_color_run_current": 0,
            "micro_same_color_run_max_20": 0,
            "micro_volume_burst_ratio_20": 0.7,
            "micro_doji_ratio_20": 0.0,
            "micro_range_compression_ratio_20": 0.0,
            "micro_upper_wick_ratio_20": 0.34,
            "state25_teacher_weight_overrides": {
                "upper_wick_weight": 0.35,
                "range_reversal_weight": 0.80,
            },
        }
    )

    assert baseline["teacher_pattern_id"] == 25
    assert adjusted["teacher_pattern_id"] == 25
    assert adjusted["teacher_primary_score"] < baseline["teacher_primary_score"]
    assert adjusted["teacher_weight_override_count"] == 2
    assert "윗꼬리 반응 비중" in adjusted["teacher_weight_override_display_ko"][0]
