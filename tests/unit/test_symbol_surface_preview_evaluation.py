import pandas as pd

from backend.services.symbol_surface_preview_evaluation import (
    build_symbol_surface_preview_evaluation,
    render_symbol_surface_preview_evaluation_markdown,
)


def test_symbol_surface_preview_evaluation_flags_single_class_and_ready_rows() -> None:
    initial_entry = pd.DataFrame(
        [
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "enter_now_binary": 0, "training_weight": 0.8, "time_axis_phase": "late_initial"},
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "observe_filter", "enter_now_binary": 0, "training_weight": 0.7, "time_axis_phase": "late_initial"},
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "enter_now_binary": 0, "training_weight": 0.7, "time_axis_phase": "late_initial"},
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "late_release", "enter_now_binary": 1, "training_weight": 0.45, "time_axis_phase": "late_initial"},
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "enter_now_binary": 0, "training_weight": 0.45, "time_axis_phase": "fresh_initial"},
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "initial_break", "enter_now_binary": 1, "training_weight": 1.0, "time_axis_phase": "fresh_initial"},
            {"symbol": "BTCUSD", "market_family": "BTCUSD", "surface_state": "observe_filter", "enter_now_binary": 0, "training_weight": 0.45, "time_axis_phase": "late_initial"},
        ]
    )
    follow_through = pd.DataFrame(
        [
            {"symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "pullback_resume", "continuation_positive_binary": 1, "training_weight": 1.0, "time_axis_phase": "continuation_window"},
            {"symbol": "XAUUSD", "market_family": "XAUUSD", "surface_state": "pullback_resume", "continuation_positive_binary": 1, "training_weight": 1.0, "time_axis_phase": "continuation_window"},
        ]
    )
    protective_exit = pd.DataFrame(
        [{"symbol": "NAS100", "market_family": "NAS100", "surface_state": "protect_exit", "protect_exit_binary": 1, "training_weight": 1.0, "time_axis_phase": "protect_late"}]
    )
    failure_payload = {
        "rows": [
            {"market_family": "BTCUSD", "surface_label_family": "initial_entry_surface", "failure_label": "missed_good_wait_release"},
            {"market_family": "XAUUSD", "surface_label_family": "follow_through_surface", "failure_label": "failed_follow_through"},
            {"market_family": "NAS100", "surface_label_family": "protective_exit_surface", "failure_label": "early_exit_regret"},
        ]
    }
    distribution_payload = {
        "rows": [
            {"market_family": "BTCUSD", "surface_family": "initial_entry_surface", "promotion_gap_note": "underfired_vs_distribution", "combined_gate_state": "PROBE_ELIGIBLE"},
            {"market_family": "XAUUSD", "surface_family": "follow_through_surface", "promotion_gap_note": "", "combined_gate_state": "PROBE_ELIGIBLE"},
        ]
    }
    adapter_payload = {
        "rows": [
            {"market_family": "BTCUSD", "surface_name": "initial_entry_surface", "adapter_mode": "btc_observe_relief_adapter", "recommended_bias_action": "bias_release_wait", "objective_key": "entry_forward_ev", "current_focus": "btc_initial_focus"},
            {"market_family": "XAUUSD", "surface_name": "follow_through_surface", "adapter_mode": "xau_follow_through_relief_adapter", "recommended_bias_action": "bias_probe_relief", "objective_key": "follow_through_extension_ev", "current_focus": "xau_follow_through_focus"},
            {"market_family": "NAS100", "surface_name": "protective_exit_surface", "adapter_mode": "nas_protective_adapter", "recommended_bias_action": "bias_protective_dampen", "objective_key": "protect_exit_loss_avoidance_ev", "current_focus": "nas_protective_focus"},
        ]
    }

    frame, summary = build_symbol_surface_preview_evaluation(
        initial_entry_dataset=initial_entry,
        follow_through_dataset=follow_through,
        continuation_hold_dataset=pd.DataFrame(),
        protective_exit_dataset=protective_exit,
        failure_label_harvest_payload=failure_payload,
        distribution_promotion_gate_payload=distribution_payload,
        market_adapter_layer_payload=adapter_payload,
    )
    markdown = render_symbol_surface_preview_evaluation_markdown(summary, frame)

    assert summary["row_count"] == 12
    btc_initial = frame.loc[(frame["market_family"] == "BTCUSD") & (frame["surface_name"] == "initial_entry_surface")].iloc[0]
    assert btc_initial["readiness_state"] == "preview_eval_ready"
    assert btc_initial["underfire_count"] == 1
    assert btc_initial["missed_good_wait_release_count"] == 0
    assert btc_initial["harvest_missed_good_wait_release_count"] == 1
    xau_follow = frame.loc[(frame["market_family"] == "XAUUSD") & (frame["surface_name"] == "follow_through_surface")].iloc[0]
    assert xau_follow["readiness_state"] in {"insufficient_rows", "single_class_only"}
    assert xau_follow["failed_follow_through_count"] == 0
    assert xau_follow["harvest_failed_follow_through_count"] == 1
    nas_protect = frame.loc[(frame["market_family"] == "NAS100") & (frame["surface_name"] == "protective_exit_surface")].iloc[0]
    assert nas_protect["early_exit_regret_count"] == 0
    assert nas_protect["harvest_early_exit_regret_count"] == 1
    assert "Symbol-Surface Preview Evaluation" in markdown
