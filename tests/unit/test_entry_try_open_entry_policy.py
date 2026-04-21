from types import SimpleNamespace

from backend.services.entry_try_open_entry import (
    _build_semantic_owner_runtime_bundle_v1,
    _resolve_setup_specific_pyramid_policy,
)


def test_xau_breakout_sell_keeps_default_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="XAUUSD",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
        box_state="LOWER",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "adverse"
    assert out["require_drawdown"] is True
    assert out["edge_guard"] is True
    assert out["min_prog"] == 0.001


def test_xau_range_upper_sell_keeps_default_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="XAUUSD",
        action="SELL",
        setup_id="range_upper_reversal_sell",
        preflight_allowed_action="BOTH",
        box_state="UPPER",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "adverse"
    assert out["require_drawdown"] is True
    assert out["edge_guard"] is True
    assert out["min_prog"] == 0.001


def test_nas_range_lower_buy_keeps_default_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="NAS100",
        action="BUY",
        setup_id="range_lower_reversal_buy",
        preflight_allowed_action="BOTH",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "adverse"
    assert out["require_drawdown"] is True
    assert out["edge_guard"] is True
    assert out["min_prog"] == 0.001


def test_nas_range_lower_buy_relaxes_first_addon_policy_for_clean_probe():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="NAS100",
        action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_reason="shadow_lower_rebound_probe_observe",
        preflight_allowed_action="BOTH",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] < 0.001


def test_nas_range_lower_buy_relaxes_second_addon_policy_for_clean_probe():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="NAS100",
        action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_reason="shadow_outer_band_reversal_support_required_observe",
        preflight_allowed_action="BUY_ONLY",
        box_state="BELOW",
        same_dir_count=2,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] <= 0.00036


def test_nas_range_lower_buy_relaxes_breakdown_probe_reason_variant():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="NAS100",
        action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_reason="shadow_lower_rebound_probe_observe_nas_lower_breakdown_probe",
        preflight_allowed_action="BOTH",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] < 0.001


def test_nas_breakout_sell_relaxes_first_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="NAS100",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] < 0.001


def test_nas_breakout_sell_relaxes_second_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="NAS100",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="BOTH",
        box_state="BELOW",
        same_dir_count=2,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] <= 0.0004


def test_btc_breakout_sell_relaxes_more_aggressively_for_first_addon():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="BTCUSD",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] <= 0.00035


def test_btc_breakout_sell_relaxes_second_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="BTCUSD",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
        box_state="BELOW",
        same_dir_count=2,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] <= 0.00022


def test_btc_breakout_sell_relaxes_more_aggressively_for_first_addon_when_preflight_is_both():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="BTCUSD",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="BOTH",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] <= 0.00035


def test_btc_upper_shadow_reject_sell_relaxes_first_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="BTCUSD",
        action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        preflight_allowed_action="BOTH",
        box_state="ABOVE",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is True
    assert out["min_prog"] < 0.001


def test_btc_upper_shadow_reject_sell_keeps_default_addon_policy_for_third_addon():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="BTCUSD",
        action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        preflight_allowed_action="BOTH",
        box_state="ABOVE",
        same_dir_count=3,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "adverse"
    assert out["require_drawdown"] is True
    assert out["edge_guard"] is True
    assert out["min_prog"] == 0.001


def test_build_semantic_owner_runtime_bundle_handles_missing_optional_inputs():
    out = _build_semantic_owner_runtime_bundle_v1(
        runtime_snapshot_row={
            "wait_confirm_gap": "",
            "hold_exit_gap": "bad",
            "same_side_flip_gap": 0.24,
            "belief_barrier_tension_gap": None,
        },
        symbol="BTCUSD",
        action="SELL",
        setup_id="breakout_retest_sell",
        setup_side="SELL",
        entry_session_name="NY",
        wait_state=None,
        entry_wait_decision="",
        score=0.0,
        contra_score=0.0,
        prediction_bundle=None,
        shadow_transition_forecast_v1=None,
        shadow_trade_management_forecast_v1=None,
        shadow_observe_confirm=None,
        entry_stage="PROBE",
        actual_effective_entry_threshold=55.0,
        actual_size_multiplier=1.0,
        state25_candidate_runtime_state=None,
    )

    assert isinstance(out["forecast_state25_runtime_bridge_v1"], dict)
    assert isinstance(out["belief_state25_runtime_bridge_v1"], dict)
    assert isinstance(out["barrier_state25_runtime_bridge_v1"], dict)
    assert isinstance(out["detail_fields"], dict)
    assert isinstance(out["flat_fields"], dict)
    assert isinstance(out["flat_fields"]["belief_action_hint_mode"], str)
    assert isinstance(out["flat_fields"]["barrier_action_hint_mode"], str)
    assert "forecast_state25_overlay_mode" in out["flat_fields"]
    assert "state25_candidate_log_only_trace_v1" in out["detail_fields"]
    assert "barrier_state25_runtime_bridge_v1" in out["detail_fields"]


def test_build_semantic_owner_runtime_bundle_reads_wait_state_snapshot_safely():
    out = _build_semantic_owner_runtime_bundle_v1(
        runtime_snapshot_row={},
        symbol="NAS100",
        action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_side="BUY",
        entry_session_name="LONDON",
        wait_state=SimpleNamespace(state="HELPER_SOFT_BLOCK", reason="test_wait_reason"),
        entry_wait_decision="wait_soft_helper_block",
        score=41.0,
        contra_score=12.0,
        prediction_bundle={},
        shadow_transition_forecast_v1={"metadata": {"side_separation": 0.22}},
        shadow_trade_management_forecast_v1={"metadata": {"continue_fail_gap": 0.11}},
        shadow_observe_confirm={"state": "OBSERVE", "reason": "test"},
        entry_stage="PROBE",
        actual_effective_entry_threshold=41.0,
        actual_size_multiplier=0.85,
        state25_candidate_runtime_state={},
    )

    assert out["observe_confirm_runtime_payload"]["observe_confirm_v2"]["state"] == "OBSERVE"
    assert isinstance(out["barrier_state25_runtime_bridge_v1"]["barrier_runtime_summary_v1"], dict)
    assert out["flat_fields"]["state25_candidate_effective_entry_threshold"] == 41.0
