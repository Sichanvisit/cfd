from backend.services.entry_try_open_entry import (
    _build_runtime_observe_confirm_dual_write,
    _normalize_order_lot,
    _resolve_entry_handoff_ids,
    _resolve_range_lower_buy_shadow_relief,
    _resolve_probe_execution_plan,
    _resolve_semantic_probe_bridge_action,
    _resolve_semantic_live_threshold_trace,
    _resolve_semantic_shadow_activation,
    _should_block_range_lower_buy_dual_bear_context,
)


def test_normalize_order_lot_respects_min_lot_floor():
    assert _normalize_order_lot(base_lot=0.01, size_multiplier=0.50, min_lot=0.01) == 0.01
    assert _normalize_order_lot(base_lot=0.10, size_multiplier=0.50, min_lot=0.01) == 0.05


def test_resolve_entry_handoff_ids_prefers_observe_confirm_and_falls_back_to_context_metadata():
    management_profile_id, invalidation_id = _resolve_entry_handoff_ids(
        shadow_observe_confirm={
            "management_profile_id": "Support_Hold_Profile",
            "invalidation_id": "",
        },
        shadow_entry_context_v1={
            "metadata": {
                "management_profile_id": "ignored_profile",
                "invalidation_id": "Second_Support_Break",
            }
        },
    )

    assert management_profile_id == "support_hold_profile"
    assert invalidation_id == "second_support_break"


def test_build_runtime_observe_confirm_dual_write_prefers_v2_canonical_and_keeps_v1_bridge():
    payload = _build_runtime_observe_confirm_dual_write(
        shadow_observe_confirm={
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "confidence": 0.73,
            "reason": "lower_rebound_confirm",
            "archetype_id": "lower_hold_buy",
            "invalidation_id": "lower_support_fail",
            "management_profile_id": "support_hold_profile",
        }
    )

    assert payload["prs_canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert payload["prs_compatibility_observe_confirm_field"] == "observe_confirm_v1"
    assert payload["observe_confirm_v2"]["archetype_id"] == "lower_hold_buy"
    assert payload["observe_confirm_v1"]["archetype_id"] == "lower_hold_buy"
    assert payload["observe_confirm_output_contract_v2"]["canonical_output_field"] == "observe_confirm_v2"
    assert payload["consumer_input_contract_v1"]["canonical_observe_confirm_field"] == "observe_confirm_v2"


def test_resolve_probe_execution_plan_uses_smaller_probe_lot_and_conservative_stage():
    out = _resolve_probe_execution_plan(
        symbol="NAS100",
        action="BUY",
        entry_stage="balanced",
        base_lot=0.10,
        min_lot=0.01,
        same_dir_count=0,
        probe_plan_v1={
            "active": True,
            "ready_for_entry": True,
            "intended_action": "BUY",
            "recommended_size_multiplier": 0.50,
            "recommended_entry_stage": "conservative",
        },
    )

    assert out["contract_version"] == "entry_probe_execution_v1"
    assert out["probe_active"] is True
    assert out["confirm_add_active"] is False
    assert out["order_lot"] == 0.05
    assert out["size_multiplier"] == 0.50
    assert out["effective_entry_stage"] == "conservative"


def test_resolve_probe_execution_plan_keeps_normal_size_for_confirm_add():
    out = _resolve_probe_execution_plan(
        symbol="BTCUSD",
        action="BUY",
        entry_stage="balanced",
        base_lot=0.01,
        min_lot=0.01,
        same_dir_count=1,
        probe_plan_v1={},
    )

    assert out["probe_active"] is False
    assert out["confirm_add_active"] is True
    assert out["order_lot"] == 0.01
    assert out["size_multiplier"] == 1.0
    assert out["effective_entry_stage"] == "balanced"


def test_resolve_semantic_shadow_activation_reports_runtime_unavailable_reason():
    state, reason = _resolve_semantic_shadow_activation(
        semantic_shadow_prediction_v1={"available": False, "reason": "semantic_runtime_unavailable"},
        semantic_live_guard_v1={"symbol_allowed": True, "entry_stage_allowed": True},
        runtime_diagnostics={"reason": "model_files_missing"},
    )

    assert state == "inactive"
    assert reason == "model_files_missing"


def test_resolve_semantic_shadow_activation_reports_symbol_block_when_prediction_active():
    state, reason = _resolve_semantic_shadow_activation(
        semantic_shadow_prediction_v1={"available": True},
        semantic_live_guard_v1={"symbol_allowed": False, "entry_stage_allowed": True},
        runtime_diagnostics={"reason": "loaded"},
    )

    assert state == "active_symbol_blocked"
    assert reason == "symbol_not_in_allowlist"


def test_resolve_semantic_live_threshold_trace_reports_mode_and_fallback():
    state, reason = _resolve_semantic_live_threshold_trace(
        {"mode": "log_only", "threshold_applied": False, "threshold_state": "mode_no_threshold"}
    )
    assert state == "mode_no_threshold"
    assert reason == "mode_no_threshold"

    state, reason = _resolve_semantic_live_threshold_trace(
        {
            "mode": "threshold_only",
            "threshold_applied": False,
            "threshold_state": "fallback_blocked",
            "threshold_inactive_reason": "symbol_not_in_allowlist",
        }
    )
    assert state == "fallback_blocked"
    assert reason == "symbol_not_in_allowlist"


def test_resolve_range_lower_buy_shadow_relief_allows_btc_probe_observe_breakdown_when_semantic_is_strong():
    allowed, tag = _resolve_range_lower_buy_shadow_relief(
        symbol="BTCUSD",
        core_reason="core_shadow_probe_action",
        setup_reason="shadow_lower_rebound_probe_observe",
        box_state="LOWER",
        bb_state="BREAKDOWN",
        wait_conflict=0.0,
        wait_noise=0.0,
        wait_score=70.0,
        preflight_allowed_action="BOTH",
        compatibility_mode="observe_confirm_v1_fallback",
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.9845},
            "entry_quality": {"probability": 0.9310},
        },
    )

    assert allowed is True
    assert tag == "semantic_probe"


def test_resolve_range_lower_buy_shadow_relief_rejects_probe_when_semantic_is_not_strong_enough():
    allowed, tag = _resolve_range_lower_buy_shadow_relief(
        symbol="BTCUSD",
        core_reason="core_shadow_probe_action",
        setup_reason="shadow_lower_rebound_probe_observe",
        box_state="LOWER",
        bb_state="BREAKDOWN",
        wait_conflict=0.0,
        wait_noise=0.0,
        wait_score=70.0,
        preflight_allowed_action="BOTH",
        compatibility_mode="observe_confirm_v1_fallback",
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.70},
            "entry_quality": {"probability": 0.65},
        },
    )

    assert allowed is False
    assert tag == ""


def test_should_block_range_lower_buy_dual_bear_context_for_btc_when_both_gates_fail():
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="BTCUSD",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=False,
            topdown_gate_pass=False,
        )
        is True
    )


def test_should_block_range_lower_buy_dual_bear_context_for_nas_when_both_gates_fail():
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="NAS100",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=False,
            topdown_gate_pass=False,
        )
        is True
    )


def test_should_not_block_range_lower_buy_when_one_gate_still_passes():
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="BTCUSD",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=True,
            topdown_gate_pass=False,
        )
        is False
    )
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="NAS100",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=False,
            topdown_gate_pass=True,
        )
        is False
    )


def test_should_not_block_other_symbols_or_setups_for_dual_bear_context():
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="XAUUSD",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=False,
            topdown_gate_pass=False,
        )
        is False
    )
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="BTCUSD",
            action="BUY",
            setup_id="trend_pullback_buy",
            h1_gate_pass=False,
            topdown_gate_pass=False,
        )
        is False
    )


def test_resolve_semantic_probe_bridge_action_allows_btc_lower_rebound_when_semantic_is_strong():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        observe_reason="lower_rebound_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="forecast_guard",
        compatibility_mode="observe_confirm_v1_fallback",
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "reason": "probe_pair_gap_not_ready",
            "intended_action": "BUY",
            "default_side_aligned": True,
            "candidate_support": 0.26,
            "action_confirm_score": 0.13,
            "confirm_fake_gap": -0.20,
            "wait_confirm_gap": -0.15,
            "continue_fail_gap": -0.28,
            "same_side_barrier": 0.50,
        },
        default_side_gate_v1={},
        probe_candidate_v1={},
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.98},
            "entry_quality": {"probability": 0.94},
        },
    )

    assert action == "BUY"
    assert reason == "btc_lower_rebound_semantic_probe_bridge"


def test_resolve_semantic_probe_bridge_action_rejects_when_semantic_is_not_strong_enough():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        observe_reason="lower_rebound_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="forecast_guard",
        compatibility_mode="observe_confirm_v1_fallback",
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "reason": "probe_pair_gap_not_ready",
            "intended_action": "BUY",
            "default_side_aligned": True,
            "candidate_support": 0.26,
            "action_confirm_score": 0.13,
            "confirm_fake_gap": -0.20,
            "wait_confirm_gap": -0.15,
            "continue_fail_gap": -0.28,
            "same_side_barrier": 0.50,
        },
        default_side_gate_v1={},
        probe_candidate_v1={},
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.80},
            "entry_quality": {"probability": 0.70},
        },
    )

    assert action == ""
    assert reason == ""


def test_resolve_semantic_probe_bridge_action_allows_btc_upper_reject_when_semantic_is_strong():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        observe_reason="upper_reject_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="",
        compatibility_mode="observe_confirm_v1_fallback",
        entry_probe_plan_v1={
            "active": False,
            "ready_for_entry": False,
            "reason": "probe_not_observe_stage",
            "intended_action": "SELL",
            "candidate_support": 0.51,
        },
        default_side_gate_v1={
            "reason": "lower_edge_sell_requires_break_override",
            "winner_side": "SELL",
            "winner_clear": True,
            "pair_gap": 0.32,
        },
        probe_candidate_v1={
            "candidate_support": 0.51,
            "near_confirm": True,
        },
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.9793},
            "entry_quality": {"probability": 0.9482},
        },
    )

    assert action == "SELL"
    assert reason == "btc_upper_reject_semantic_probe_bridge"


def test_resolve_semantic_probe_bridge_action_rejects_btc_upper_reject_when_gate_is_weak():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        observe_reason="upper_reject_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="",
        compatibility_mode="observe_confirm_v1_fallback",
        entry_probe_plan_v1={
            "active": False,
            "ready_for_entry": False,
            "reason": "probe_not_observe_stage",
            "intended_action": "SELL",
            "candidate_support": 0.44,
        },
        default_side_gate_v1={
            "reason": "lower_edge_sell_requires_break_override",
            "winner_side": "SELL",
            "winner_clear": True,
            "pair_gap": 0.28,
        },
        probe_candidate_v1={
            "candidate_support": 0.44,
            "near_confirm": False,
        },
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.9793},
            "entry_quality": {"probability": 0.9482},
        },
    )

    assert action == ""
    assert reason == ""
