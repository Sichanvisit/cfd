from backend.services.path_checkpoint_scene_tagger import tag_runtime_scene


def test_tag_runtime_scene_marks_breakout_retest_hold() -> None:
    payload = tag_runtime_scene(
        symbol="NAS100",
        runtime_row={
            "setup_reason": "breakout retest reclaim hold",
            "observe_action": "BUY",
            "observe_side": "BUY",
        },
        checkpoint_row={
            "surface_name": "follow_through_surface",
            "checkpoint_type": "RECLAIM_CHECK",
            "bars_since_leg_start": 4,
            "bars_since_last_checkpoint": 1,
            "leg_direction": "UP",
            "runtime_continuation_odds": 0.74,
            "runtime_reversal_odds": 0.44,
            "runtime_hold_quality_score": 0.50,
            "runtime_partial_exit_ev": 0.35,
            "runtime_full_exit_risk": 0.20,
            "runtime_rebuy_readiness": 0.42,
            "runtime_score_reason": "continuation_hold_surface::continuation_hold_bias",
        },
    )

    row = payload["row"]
    assert row["runtime_scene_coarse_family"] == "ENTRY_INITIATION"
    assert row["runtime_scene_fine_label"] == "breakout_retest_hold"
    assert row["runtime_scene_confidence_band"] == "high"
    assert row["runtime_scene_maturity"] == "probable"
    assert row["runtime_scene_family_alignment"] == "aligned"


def test_tag_runtime_scene_marks_liquidity_sweep_reclaim() -> None:
    payload = tag_runtime_scene(
        symbol="XAUUSD",
        runtime_row={
            "blocked_by": "active_action_conflict_guard",
            "action_none_reason": "wrong_side_sell_pressure",
            "observe_action": "BUY",
            "observe_side": "BUY",
        },
        checkpoint_row={
            "surface_name": "follow_through_surface",
            "checkpoint_type": "RECLAIM_CHECK",
            "bars_since_leg_start": 3,
            "leg_direction": "UP",
            "runtime_continuation_odds": 0.76,
            "runtime_reversal_odds": 0.40,
            "runtime_hold_quality_score": 0.46,
            "runtime_partial_exit_ev": 0.28,
            "runtime_full_exit_risk": 0.18,
            "runtime_rebuy_readiness": 0.40,
            "runtime_score_reason": "follow_through_surface::continuation_hold_bias",
        },
    )

    row = payload["row"]
    assert row["runtime_scene_coarse_family"] == "ENTRY_INITIATION"
    assert row["runtime_scene_fine_label"] == "liquidity_sweep_reclaim"
    assert row["runtime_scene_confidence_band"] == "high"
    assert row["runtime_scene_modifier_json"] == '{"reclaim": true}'


def test_tag_runtime_scene_marks_trend_exhaustion_and_confirms_transition() -> None:
    payload = tag_runtime_scene(
        symbol="BTCUSD",
        runtime_row={
            "blocked_by": "allow_long_blocked",
            "observe_action": "WAIT",
            "observe_side": "BUY",
        },
        checkpoint_row={
            "surface_name": "continuation_hold_surface",
            "source": "exit_manage_runner",
            "checkpoint_type": "RUNNER_CHECK",
            "bars_since_leg_start": 12,
            "leg_direction": "UP",
            "runner_secured": True,
            "giveback_ratio": 0.30,
            "runtime_continuation_odds": 0.71,
            "runtime_reversal_odds": 0.63,
            "runtime_hold_quality_score": 0.49,
            "runtime_partial_exit_ev": 0.64,
            "runtime_full_exit_risk": 0.42,
            "runtime_rebuy_readiness": 0.16,
            "runtime_score_reason": "continuation_hold_surface::runner_lock_bias",
        },
        previous_runtime_row={
            "checkpoint_runtime_scene_fine_label": "trend_exhaustion",
            "checkpoint_runtime_scene_transition_bars": 2,
        },
    )

    row = payload["row"]
    assert row["runtime_scene_coarse_family"] == "DEFENSIVE_EXIT"
    assert row["runtime_scene_fine_label"] == "trend_exhaustion"
    assert row["runtime_scene_family_alignment"] == "upgrade"
    assert row["runtime_scene_maturity"] == "confirmed"
    assert row["runtime_scene_transition_from"] == "trend_exhaustion"
    assert row["runtime_scene_transition_bars"] == 3
    assert row["runtime_scene_transition_speed"] == "slow"


def test_tag_runtime_scene_marks_time_decay_risk() -> None:
    payload = tag_runtime_scene(
        symbol="NAS100",
        runtime_row={},
        checkpoint_row={
            "surface_name": "continuation_hold_surface",
            "checkpoint_type": "RUNNER_CHECK",
            "bars_since_leg_start": 18,
            "position_side": "BUY",
            "unrealized_pnl_state": "FLAT",
            "current_profit": 0.0,
            "mfe_since_entry": 0.10,
            "mae_since_entry": 0.08,
            "runtime_continuation_odds": 0.40,
            "runtime_reversal_odds": 0.47,
            "runtime_hold_quality_score": 0.24,
            "runtime_partial_exit_ev": 0.26,
            "runtime_full_exit_risk": 0.34,
            "runtime_rebuy_readiness": 0.12,
            "runtime_score_reason": "continuation_hold_surface::balanced_checkpoint_state",
        },
    )

    row = payload["row"]
    assert row["runtime_scene_coarse_family"] == "POSITION_MANAGEMENT"
    assert row["runtime_scene_fine_label"] == "time_decay_risk"
    assert row["runtime_scene_confidence_band"] == "high"
    assert row["runtime_scene_action_bias_strength"] == "medium"


def test_tag_runtime_scene_keeps_healthy_runner_unresolved_after_rebalance() -> None:
    payload = tag_runtime_scene(
        symbol="NAS100",
        runtime_row={
            "setup_reason": "runner lock continue",
        },
        checkpoint_row={
            "surface_name": "continuation_hold_surface",
            "source": "exit_manage_runner",
            "checkpoint_type": "RUNNER_CHECK",
            "bars_since_leg_start": 154,
            "position_side": "BUY",
            "unrealized_pnl_state": "OPEN_PROFIT",
            "runner_secured": True,
            "current_profit": 0.27,
            "mfe_since_entry": 0.27,
            "mae_since_entry": 0.0,
            "giveback_ratio": 0.0,
            "runtime_continuation_odds": 0.888,
            "runtime_reversal_odds": 0.473,
            "runtime_hold_quality_score": 0.57196,
            "runtime_partial_exit_ev": 0.60082,
            "runtime_full_exit_risk": 0.17231,
            "runtime_rebuy_readiness": 0.12,
            "runtime_score_reason": "continuation_hold_surface::runner_lock_bias",
        },
    )

    row = payload["row"]
    assert row["runtime_scene_fine_label"] == "unresolved"
    assert row["runtime_scene_coarse_family"] == "UNRESOLVED"
    assert row["runtime_scene_source"] == "schema_only"


def test_tag_runtime_scene_recovers_flat_late_time_decay_after_rebalance() -> None:
    payload = tag_runtime_scene(
        symbol="NAS100",
        runtime_row={},
        checkpoint_row={
            "surface_name": "continuation_hold_surface",
            "source": "exit_manage_hold",
            "checkpoint_type": "RUNNER_CHECK",
            "bars_since_leg_start": 28,
            "position_side": "BUY",
            "unrealized_pnl_state": "FLAT",
            "runner_secured": False,
            "current_profit": 0.0,
            "mfe_since_entry": 0.10,
            "mae_since_entry": 0.0,
            "giveback_ratio": 0.99,
            "runtime_continuation_odds": 0.551,
            "runtime_reversal_odds": 0.824,
            "runtime_hold_quality_score": 0.25233,
            "runtime_partial_exit_ev": 0.47856,
            "runtime_full_exit_risk": 0.71,
            "runtime_rebuy_readiness": 0.12,
            "runtime_score_reason": "continuation_hold_surface::balanced_checkpoint_state",
        },
    )

    row = payload["row"]
    assert row["runtime_scene_fine_label"] == "time_decay_risk"
    assert row["runtime_scene_coarse_family"] == "POSITION_MANAGEMENT"
    assert row["runtime_scene_confidence_band"] in {"medium", "high"}


def test_tag_runtime_scene_marks_low_edge_gate_without_fine_scene() -> None:
    payload = tag_runtime_scene(
        symbol="BTCUSD",
        runtime_row={},
        checkpoint_row={
            "surface_name": "follow_through_surface",
            "checkpoint_type": "FIRST_PULLBACK_CHECK",
            "position_side": "FLAT",
            "position_size_fraction": 0.0,
            "runtime_continuation_odds": 0.51,
            "runtime_reversal_odds": 0.48,
            "runtime_hold_quality_score": 0.30,
            "runtime_partial_exit_ev": 0.22,
            "runtime_full_exit_risk": 0.25,
            "runtime_rebuy_readiness": 0.33,
        },
    )

    row = payload["row"]
    assert row["runtime_scene_fine_label"] == "unresolved"
    assert row["runtime_scene_gate_label"] == "low_edge_state"
    assert row["runtime_scene_gate_block_level"] == "entry_block"
    assert row["runtime_scene_confidence_band"] == "medium"
    assert row["runtime_scene_family_alignment"] == "unknown"


def test_tag_runtime_scene_preserves_explicit_override_payload() -> None:
    payload = tag_runtime_scene(
        symbol="BTCUSD",
        runtime_row={},
        checkpoint_row={
            "surface_name": "follow_through_surface",
            "checkpoint_type": "INITIAL_PUSH",
            "runtime_scene_fine_label": "breakout",
            "runtime_scene_coarse_family": "ENTRY_INITIATION",
            "runtime_scene_source": "manual_resolution",
            "runtime_scene_confidence_band": "high",
            "runtime_scene_maturity": "confirmed",
        },
    )

    row = payload["row"]
    assert row["runtime_scene_fine_label"] == "breakout"
    assert row["runtime_scene_source"] == "manual_resolution"
    assert payload["detail"]["mode"] == "passthrough_existing_scene_payload"
