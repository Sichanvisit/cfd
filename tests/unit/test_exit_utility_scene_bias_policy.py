from backend.services.exit_utility_scene_bias_policy import (
    compact_exit_utility_scene_bias_bundle_v1,
    resolve_exit_utility_scene_bias_bundle_v1,
)


def test_exit_utility_scene_bias_bundle_marks_xau_lower_edge_hold_bias():
    compact = compact_exit_utility_scene_bias_bundle_v1(
        resolve_exit_utility_scene_bias_bundle_v1(
            exit_utility_input_v1={
                "contract_version": "exit_utility_input_v1",
                "identity": {
                    "symbol": "XAUUSD",
                    "state": "ACTIVE",
                    "entry_direction": "BUY",
                },
                "market": {
                    "regime_now": "RANGE",
                    "current_box_state": "MIDDLE",
                    "current_bb_state": "MID",
                },
                "risk": {
                    "profit": 0.18,
                    "peak_profit": 0.42,
                    "giveback": 0.24,
                    "adverse_risk": False,
                },
                "policy": {
                    "recovery_policy_id": "range_lower_reversal_buy_xau_balanced",
                },
                "bias": {
                    "symbol_edge_execution_overrides_v1": {},
                },
            },
            exit_utility_base_bundle_v1={
                "contract_version": "exit_utility_base_bundle_v1",
                "inputs": {
                    "locked_profit": 0.18,
                },
            },
        )
    )

    assert compact["contract_version"] == "exit_utility_scene_bias_bundle_v1"
    assert compact["flags"]["range_middle_observe"] is True
    assert compact["flags"]["lower_reversal_hold_bias"] is True
    assert compact["flags"]["xau_lower_edge_to_edge_hold_bias"] is True
    assert compact["utility_deltas"]["utility_exit_now_delta"] == -0.572
    assert compact["utility_deltas"]["utility_hold_delta"] == 0.736
    assert compact["utility_deltas"]["utility_wait_exit_delta"] == 0.38


def test_exit_utility_scene_bias_bundle_marks_btc_upper_support_bounce_and_wait_disable():
    compact = compact_exit_utility_scene_bias_bundle_v1(
        resolve_exit_utility_scene_bias_bundle_v1(
            exit_utility_input_v1={
                "contract_version": "exit_utility_input_v1",
                "identity": {
                    "symbol": "BTCUSD",
                    "state": "ACTIVE",
                    "entry_direction": "SELL",
                },
                "market": {
                    "regime_now": "RANGE",
                    "current_box_state": "MIDDLE",
                    "current_bb_state": "MID",
                },
                "risk": {
                    "profit": 0.24,
                    "peak_profit": 0.54,
                    "giveback": 0.30,
                    "adverse_risk": False,
                },
                "policy": {
                    "recovery_policy_id": "range_upper_reversal_sell_btc_tight",
                },
                "bias": {
                    "symbol_edge_execution_overrides_v1": {},
                },
            },
            exit_utility_base_bundle_v1={
                "contract_version": "exit_utility_base_bundle_v1",
                "inputs": {
                    "locked_profit": 0.24,
                },
            },
        )
    )

    assert compact["flags"]["btc_upper_tight"] is True
    assert compact["flags"]["btc_upper_support_bounce_exit"] is True
    assert compact["recovery_overrides"]["force_disable_wait_be"] is True
    assert compact["recovery_overrides"]["force_disable_wait_tp1"] is True
    assert compact["utility_deltas"]["utility_exit_now_delta"] == 0.528
    assert compact["utility_deltas"]["utility_hold_delta"] == -0.645
    assert compact["utility_deltas"]["utility_wait_exit_delta"] == -0.38


def test_exit_utility_scene_bias_bundle_marks_opposite_edge_completion_bias():
    compact = compact_exit_utility_scene_bias_bundle_v1(
        resolve_exit_utility_scene_bias_bundle_v1(
            exit_utility_input_v1={
                "contract_version": "exit_utility_input_v1",
                "identity": {
                    "symbol": "XAUUSD",
                    "state": "ACTIVE",
                    "entry_direction": "BUY",
                },
                "market": {
                    "regime_now": "RANGE",
                    "current_box_state": "UPPER",
                    "current_bb_state": "UPPER_EDGE",
                },
                "risk": {
                    "profit": 0.36,
                    "peak_profit": 0.58,
                    "giveback": 0.22,
                    "adverse_risk": False,
                },
                "policy": {
                    "recovery_policy_id": "range_lower_reversal_buy_xau_balanced",
                },
                "bias": {
                    "symbol_edge_execution_overrides_v1": {
                        "opposite_edge_exit_boost": 0.11,
                    },
                },
            },
            exit_utility_base_bundle_v1={
                "contract_version": "exit_utility_base_bundle_v1",
                "inputs": {
                    "locked_profit": 0.36,
                },
            },
        )
    )

    assert compact["flags"]["reached_opposite_edge"] is True
    assert compact["symbol_edge_completion_bias_v1"]["active"] is True
    assert compact["symbol_edge_completion_bias_v1"]["reason"] == "opposite_edge_completion"
    assert compact["utility_deltas"]["utility_exit_now_delta"] == 0.4532
    assert compact["utility_deltas"]["utility_hold_delta"] == -0.359
    assert compact["utility_deltas"]["utility_wait_exit_delta"] == -0.277


def test_exit_utility_scene_bias_bundle_marks_meaningful_giveback_exit_pressure():
    compact = compact_exit_utility_scene_bias_bundle_v1(
        resolve_exit_utility_scene_bias_bundle_v1(
            exit_utility_input_v1={
                "contract_version": "exit_utility_input_v1",
                "identity": {
                    "symbol": "XAUUSD",
                    "state": "ACTIVE",
                    "entry_direction": "SELL",
                },
                "market": {
                    "regime_now": "NORMAL",
                    "current_box_state": "MIDDLE",
                    "current_bb_state": "MID",
                },
                "risk": {
                    "profit": 0.45,
                    "peak_profit": 1.15,
                    "giveback": 0.70,
                    "adverse_risk": False,
                },
                "policy": {
                    "recovery_policy_id": "trend_pullback_sell",
                },
                "bias": {
                    "symbol_edge_execution_overrides_v1": {},
                },
            },
            exit_utility_base_bundle_v1={
                "contract_version": "exit_utility_base_bundle_v1",
                "inputs": {
                    "locked_profit": 0.45,
                },
            },
        )
    )

    assert compact["flags"]["meaningful_giveback_exit_pressure"] is True
    assert compact["utility_deltas"]["utility_exit_now_delta"] == 0.372
    assert compact["utility_deltas"]["utility_hold_delta"] == -0.44
    assert compact["utility_deltas"]["utility_wait_exit_delta"] == -0.278


def test_exit_utility_scene_bias_bundle_marks_countertrend_topdown_exit_pressure():
    compact = compact_exit_utility_scene_bias_bundle_v1(
        resolve_exit_utility_scene_bias_bundle_v1(
            exit_utility_input_v1={
                "contract_version": "exit_utility_input_v1",
                "identity": {
                    "symbol": "XAUUSD",
                    "state": "ACTIVE",
                    "entry_direction": "SELL",
                },
                "market": {
                    "regime_now": "NORMAL",
                    "current_box_state": "MIDDLE",
                    "current_bb_state": "MID",
                },
                "risk": {
                    "profit": 0.18,
                    "peak_profit": 0.62,
                    "giveback": 0.44,
                    "adverse_risk": False,
                },
                "policy": {
                    "recovery_policy_id": "range_upper_reversal_sell_xau_balanced",
                },
                "bias": {
                    "state_execution_bias_v1": {
                        "countertrend_with_entry": True,
                        "prefer_fast_cut": True,
                        "topdown_state_label": "BULL_CONFLUENCE",
                    },
                    "symbol_edge_execution_overrides_v1": {},
                },
            },
            exit_utility_base_bundle_v1={
                "contract_version": "exit_utility_base_bundle_v1",
                "inputs": {
                    "locked_profit": 0.18,
                },
            },
        )
    )

    assert compact["flags"]["countertrend_topdown_exit_pressure"] is True
    assert compact["utility_deltas"]["utility_exit_now_delta"] == 0.2328
    assert compact["utility_deltas"]["utility_hold_delta"] == -0.286
    assert compact["utility_deltas"]["utility_wait_exit_delta"] == -0.1928


def test_exit_utility_scene_bias_bundle_marks_countertrend_no_green_exit_pressure():
    compact = compact_exit_utility_scene_bias_bundle_v1(
        resolve_exit_utility_scene_bias_bundle_v1(
            exit_utility_input_v1={
                "contract_version": "exit_utility_input_v1",
                "identity": {
                    "symbol": "XAUUSD",
                    "state": "ACTIVE",
                    "entry_direction": "SELL",
                },
                "market": {
                    "regime_now": "NORMAL",
                    "current_box_state": "MIDDLE",
                    "current_bb_state": "MID",
                },
                "risk": {
                    "profit": -0.24,
                    "peak_profit": 0.0,
                    "giveback": 0.0,
                    "adverse_risk": False,
                },
                "policy": {
                    "recovery_policy_id": "range_upper_reversal_sell_xau_balanced",
                },
                "bias": {
                    "state_execution_bias_v1": {
                        "countertrend_with_entry": True,
                        "prefer_fast_cut": False,
                        "topdown_state_label": "BULL_CONFLUENCE",
                    },
                    "symbol_edge_execution_overrides_v1": {},
                },
            },
            exit_utility_base_bundle_v1={
                "contract_version": "exit_utility_base_bundle_v1",
                "inputs": {
                    "locked_profit": 0.0,
                },
            },
        )
    )

    assert compact["flags"]["countertrend_no_green_exit_pressure"] is True
    assert compact["flags"]["countertrend_topdown_exit_pressure"] is False
    assert compact["utility_deltas"]["utility_exit_now_delta"] == 0.24
    assert compact["utility_deltas"]["utility_hold_delta"] == -0.28
    assert compact["utility_deltas"]["utility_wait_exit_delta"] == -0.18


def test_exit_utility_scene_bias_bundle_marks_countertrend_continuation_exit_pressure():
    compact = compact_exit_utility_scene_bias_bundle_v1(
        resolve_exit_utility_scene_bias_bundle_v1(
            exit_utility_input_v1={
                "contract_version": "exit_utility_input_v1",
                "identity": {
                    "symbol": "XAUUSD",
                    "state": "ACTIVE",
                    "entry_direction": "SELL",
                },
                "market": {
                    "regime_now": "NORMAL",
                    "current_box_state": "MIDDLE",
                    "current_bb_state": "MID",
                },
                "risk": {
                    "profit": 0.30,
                    "peak_profit": 0.85,
                    "giveback": 0.55,
                    "adverse_risk": False,
                },
                "policy": {
                    "recovery_policy_id": "trend_pullback_sell",
                },
                "bias": {
                    "state_execution_bias_v1": {
                        "countertrend_with_entry": True,
                        "prefer_fast_cut": False,
                        "topdown_state_label": "BULL_CONFLUENCE",
                    },
                    "symbol_edge_execution_overrides_v1": {},
                },
            },
            exit_utility_base_bundle_v1={
                "contract_version": "exit_utility_base_bundle_v1",
                "inputs": {
                    "locked_profit": 0.30,
                },
            },
        )
    )

    assert compact["flags"]["countertrend_topdown_exit_pressure"] is True
    assert compact["flags"]["countertrend_continuation_exit_pressure"] is True
    assert compact["utility_deltas"]["utility_exit_now_delta"] == 0.461
    assert compact["utility_deltas"]["utility_hold_delta"] == -0.5485
    assert compact["utility_deltas"]["utility_wait_exit_delta"] == -0.381
