from backend.services.market_adapter_layer import (
    build_market_adapter_layer,
    render_market_adapter_layer_markdown,
)


def test_market_adapter_layer_materializes_symbol_surface_rows() -> None:
    entry_audit_payload = {
        "summary": {
            "runtime_updated_at": "2026-04-09T18:40:00+09:00",
            "symbol_focus_map": '{"NAS100":"inspect_nas_conflict_observe_decomposition","BTCUSD":"inspect_btcusd_observe_no_action_gap","XAUUSD":"inspect_xau_outer_band_follow_through_bridge"}',
        }
    }
    exit_audit_payload = {
        "summary": {
            "runtime_updated_at": "2026-04-09T18:40:00+09:00",
            "symbol_focus_map": '{"NAS100":"inspect_nas100_protective_exit_overfire","BTCUSD":"inspect_btcusd_protective_exit_overfire","XAUUSD":"inspect_xauusd_runner_preservation"}',
        }
    }
    surface_objective_payload = {
        "summary": {
            "symbols": ["NAS100", "BTCUSD", "XAUUSD"],
            "market_adapter_principle": "shared_surface_plus_market_family_adapter",
        },
        "rows": [
            {
                "surface_name": "initial_entry_surface",
                "objective_key": "entry_forward_ev",
                "positive_ev_proxy": "entry_forward_ev_proxy",
                "do_nothing_ev_proxy": "do_nothing_ev_proxy",
                "false_positive_cost_proxy": "entry_false_positive_cost_proxy",
                "time_axis_fields": ["bars_in_state", "time_since_last_relief"],
                "current_blocker_signature": "observe_no_action_gap",
            },
            {
                "surface_name": "follow_through_surface",
                "objective_key": "follow_through_extension_ev",
                "positive_ev_proxy": "follow_through_extension_ev_proxy",
                "do_nothing_ev_proxy": "wait_more_ev_proxy",
                "false_positive_cost_proxy": "late_follow_through_penalty_proxy",
                "time_axis_fields": ["time_since_breakout", "bars_in_state", "momentum_decay"],
                "current_blocker_signature": "follow_through_bridge",
            },
            {
                "surface_name": "continuation_hold_surface",
                "objective_key": "runner_hold_ev",
                "positive_ev_proxy": "runner_hold_ev_proxy",
                "do_nothing_ev_proxy": "lock_profit_now_ev_proxy",
                "false_positive_cost_proxy": "runner_giveback_cost_proxy",
                "time_axis_fields": ["time_since_entry", "bars_in_state", "momentum_decay"],
                "current_blocker_signature": "runner_preservation",
            },
            {
                "surface_name": "protective_exit_surface",
                "objective_key": "protect_exit_loss_avoidance_ev",
                "positive_ev_proxy": "protect_exit_loss_avoidance_ev_proxy",
                "do_nothing_ev_proxy": "hold_and_absorb_risk_ev_proxy",
                "false_positive_cost_proxy": "false_cut_regret_proxy",
                "time_axis_fields": ["time_since_entry", "bars_in_state", "momentum_decay"],
                "current_blocker_signature": "protective_exit_overfire",
            },
        ],
    }
    failure_payload = {
        "rows": [
            {"market_family": "XAUUSD", "surface_label_family": "follow_through_surface", "failure_label": "failed_follow_through"},
            {"market_family": "XAUUSD", "surface_label_family": "continuation_hold_surface", "failure_label": "early_exit_regret"},
            {"market_family": "BTCUSD", "surface_label_family": "initial_entry_surface", "failure_label": "missed_good_wait_release"},
        ]
    }
    distribution_payload = {
        "rows": [
            {
                "market_family": "XAUUSD",
                "surface_family": "follow_through_surface",
                "combined_gate_state": "PROBE_ELIGIBLE",
                "candidate_source": "countertrend_candidate",
            },
            {
                "market_family": "XAUUSD",
                "surface_family": "follow_through_surface",
                "combined_gate_state": "PROBE_ELIGIBLE",
                "candidate_source": "countertrend_candidate",
            },
            {
                "market_family": "BTCUSD",
                "surface_family": "initial_entry_surface",
                "combined_gate_state": "WATCH_ONLY",
                "candidate_source": "breakout_candidate",
            },
        ]
    }

    frame, summary = build_market_adapter_layer(
        entry_audit_payload,
        exit_audit_payload,
        surface_objective_payload,
        failure_payload,
        distribution_payload,
    )
    markdown = render_market_adapter_layer_markdown(summary, frame)

    assert summary["row_count"] == 12
    assert summary["recommended_next_action"] == "proceed_to_mf15_preview_dataset_export"
    xau_follow = frame.loc[
        (frame["market_family"] == "XAUUSD") & (frame["surface_name"] == "follow_through_surface")
    ].iloc[0]
    assert xau_follow["adapter_mode"] == "xau_follow_through_relief_adapter"
    assert xau_follow["distribution_combined_gate"] == "PROBE_ELIGIBLE"
    assert xau_follow["dominant_candidate_source"] == "countertrend_candidate"
    assert xau_follow["recommended_bias_action"] == "bias_probe_relief"
    btc_initial = frame.loc[
        (frame["market_family"] == "BTCUSD") & (frame["surface_name"] == "initial_entry_surface")
    ].iloc[0]
    assert btc_initial["adapter_mode"] == "btc_observe_relief_adapter"
    assert "Market Adapter Layer" in markdown


def test_market_adapter_layer_handles_missing_optional_inputs() -> None:
    frame, summary = build_market_adapter_layer(
        {"summary": {"symbol_focus_map": '{"XAUUSD":"inspect_xau_outer_band_follow_through_bridge"}'}},
        {"summary": {"symbol_focus_map": '{"XAUUSD":"inspect_xauusd_runner_preservation"}'}},
        {
            "summary": {"symbols": ["XAUUSD"]},
            "rows": [
                {
                    "surface_name": "follow_through_surface",
                    "objective_key": "follow_through_extension_ev",
                    "positive_ev_proxy": "follow_through_extension_ev_proxy",
                    "do_nothing_ev_proxy": "wait_more_ev_proxy",
                    "false_positive_cost_proxy": "late_follow_through_penalty_proxy",
                    "time_axis_fields": [],
                    "current_blocker_signature": "",
                }
            ],
        },
        {},
        {},
    )

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["dominant_failure_label"] == ""
    assert row["distribution_combined_gate"] == ""
    assert summary["row_count"] == 1
