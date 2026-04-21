import pandas as pd

from backend.services.surface_objective_ev_spec import build_surface_objective_ev_spec


def test_surface_objective_ev_spec_materializes_surface_rows_from_market_family_focus() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T01:20:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_audit = {
        "summary": {
            "symbol_focus_map": "{\"NAS100\": \"inspect_nas_conflict_observe_decomposition\", \"BTCUSD\": \"inspect_btcusd_observe_no_action_gap\", \"XAUUSD\": \"inspect_xau_outer_band_follow_through_bridge\"}",
            "symbol_blocked_by_counts": "{\"NAS100\": {\"middle_sr_anchor_guard\": 64}, \"BTCUSD\": {\"BLANK\": 80}, \"XAUUSD\": {\"outer_band_guard\": 51}}",
            "symbol_action_none_reason_counts": "{\"NAS100\": {\"observe_state_wait\": 80}, \"BTCUSD\": {\"observe_state_wait\": 80}, \"XAUUSD\": {\"probe_not_promoted\": 51}}",
            "symbol_observe_reason_counts": "{\"NAS100\": {\"middle_sr_anchor_required_observe\": 64}, \"BTCUSD\": {\"conflict_box_upper_bb20_lower_upper_dominant_observe\": 80}, \"XAUUSD\": {\"outer_band_reversal_support_required_observe\": 79}}",
        }
    }
    exit_audit = {
        "summary": {
            "symbol_focus_map": "{\"NAS100\": \"inspect_nas100_protective_exit_overfire\", \"BTCUSD\": \"inspect_btcusd_protective_exit_overfire\", \"XAUUSD\": \"inspect_xauusd_runner_preservation\"}",
            "symbol_auto_exit_reason_counts": "{\"NAS100\": {\"Protect Exit\": 7}, \"BTCUSD\": {\"Protect Exit\": 12}, \"XAUUSD\": {\"Target\": 3, \"Lock Exit\": 2}}",
        }
    }

    frame, summary, ev_proxy_spec = build_surface_objective_ev_spec(runtime_status, entry_audit, exit_audit)

    assert summary["row_count"] == 12
    assert summary["distribution_gate_principle"] == "cluster_relative_percentile_before_absolute_threshold"
    assert summary["do_nothing_mode"] == "explicit_ev_candidate"
    assert ev_proxy_spec["market_family_adapters"]["XAUUSD"]["entry_focus"] == "inspect_xau_outer_band_follow_through_bridge"
    assert ev_proxy_spec["market_family_adapters"]["XAUUSD"]["exit_focus"] == "inspect_xauusd_runner_preservation"
    assert "failed_follow_through" in ev_proxy_spec["failure_labels"]

    xau_follow = frame.loc[
        (frame["market_family"] == "XAUUSD") & (frame["surface_name"] == "follow_through_surface")
    ].iloc[0]
    assert xau_follow["objective_key"] == "follow_through_extension_ev"
    assert xau_follow["current_focus"] == "inspect_xau_outer_band_follow_through_bridge"
    assert "time_since_breakout" in xau_follow["time_axis_fields"]

    xau_hold = frame.loc[
        (frame["market_family"] == "XAUUSD") & (frame["surface_name"] == "continuation_hold_surface")
    ].iloc[0]
    assert xau_hold["current_focus"] == "inspect_xauusd_runner_preservation"
    assert xau_hold["positive_ev_proxy"] == "runner_hold_ev_proxy"


def test_surface_objective_ev_spec_defaults_when_market_family_audits_missing() -> None:
    frame, summary, ev_proxy_spec = build_surface_objective_ev_spec({}, {}, {})

    assert summary["row_count"] == 12
    assert len(frame) == 12
    assert ev_proxy_spec["recommended_next_action"] == "implement_mf3_check_color_label_formalization"
