import pandas as pd

from backend.services.countertrend_down_bootstrap_validation import (
    build_countertrend_down_bootstrap_validation,
    render_countertrend_down_bootstrap_validation_markdown,
)


def test_countertrend_down_bootstrap_validation_counts_down_watch_and_probe_rows() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T17:05:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T17:04:58",
                "symbol": "XAUUSD",
                "action": "BUY",
                "outcome": "wait",
                "setup_id": "range_lower_reversal_buy",
                "setup_reason": "shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
                "blocked_by": "",
                "action_none_reason": "observe_state_wait",
                "countertrend_directional_bias": "DOWN",
                "countertrend_action_state": "DOWN_WATCH",
                "countertrend_directional_candidate_action": "",
                "countertrend_directional_execution_action": "",
                "countertrend_directional_state_reason": "down_watch::anti_long_supportive_or_pro_down_initial",
                "countertrend_directional_state_rank": 1,
                "countertrend_anti_long_score": 0.36,
                "countertrend_anti_short_score": 0.0,
                "countertrend_pro_up_score": 0.0,
                "countertrend_pro_down_score": 0.34,
                "countertrend_directional_owner_family": "direction_agnostic_continuation",
                "countertrend_directional_down_bias_score": 0.351,
                "countertrend_directional_up_bias_score": 0.0,
                "countertrend_continuation_reason_summary": "forecast_wait_bias",
            },
            {
                "time": "2026-04-09T17:04:55",
                "symbol": "XAUUSD",
                "action": "BUY",
                "outcome": "wait",
                "setup_id": "trend_pullback_buy",
                "setup_reason": "shadow_outer_band_reversal_support_required_observe",
                "blocked_by": "outer_band_guard",
                "action_none_reason": "probe_not_promoted",
                "countertrend_directional_bias": "DOWN",
                "countertrend_action_state": "DOWN_PROBE",
                "countertrend_directional_candidate_action": "SELL",
                "countertrend_directional_execution_action": "",
                "countertrend_directional_state_reason": "down_probe::anti_long_strong_plus_pro_down_supportive",
                "countertrend_directional_state_rank": 2,
                "countertrend_anti_long_score": 1.0,
                "countertrend_anti_short_score": 0.0,
                "countertrend_pro_up_score": 0.0,
                "countertrend_pro_down_score": 0.92,
                "countertrend_directional_owner_family": "direction_agnostic_continuation",
                "countertrend_directional_down_bias_score": 0.964,
                "countertrend_directional_up_bias_score": 0.0,
                "countertrend_continuation_reason_summary": "forecast_wait_bias|belief_fragile_thesis|barrier_wait_block",
            },
            {
                "time": "2026-04-09T17:04:50",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "wait",
                "setup_id": "",
                "setup_reason": "",
                "blocked_by": "",
                "action_none_reason": "observe_state_wait",
                "countertrend_directional_bias": "NONE",
                "countertrend_action_state": "DO_NOTHING",
                "countertrend_directional_candidate_action": "",
                "countertrend_directional_execution_action": "",
                "countertrend_directional_state_reason": "no_directional_edge",
                "countertrend_directional_state_rank": 0,
                "countertrend_anti_long_score": 0.0,
                "countertrend_anti_short_score": 0.0,
                "countertrend_pro_up_score": 0.0,
                "countertrend_pro_down_score": 0.0,
                "countertrend_directional_owner_family": "",
                "countertrend_directional_down_bias_score": 0.0,
                "countertrend_directional_up_bias_score": 0.0,
                "countertrend_continuation_reason_summary": "",
            },
        ]
    )

    frame, summary = build_countertrend_down_bootstrap_validation(runtime_status, entry_decisions, recent_limit=20)
    markdown = render_countertrend_down_bootstrap_validation_markdown(summary, frame)

    assert summary["field_presence_ok"] is True
    assert summary["target_family_row_count"] == 2
    assert summary["down_watch_count"] == 1
    assert summary["down_probe_count"] == 1
    assert summary["down_enter_count"] == 0
    assert summary["candidate_sell_count"] == 1
    assert summary["execution_sell_count"] == 0
    assert summary["invalid_state_mismatch_count"] == 0
    assert summary["enter_reserved_violation_count"] == 0
    assert summary["recommended_next_action"] == "proceed_to_mf7e_up_symmetry_extension"
    assert not frame.empty
    assert "DOWN_PROBE" in markdown


def test_countertrend_down_bootstrap_validation_flags_down_enter_violation() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T17:06:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T17:05:58",
                "symbol": "XAUUSD",
                "action": "BUY",
                "outcome": "wait",
                "setup_id": "range_lower_reversal_buy",
                "setup_reason": "shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
                "blocked_by": "",
                "action_none_reason": "observe_state_wait",
                "countertrend_directional_bias": "DOWN",
                "countertrend_action_state": "DOWN_ENTER",
                "countertrend_directional_candidate_action": "SELL",
                "countertrend_directional_execution_action": "SELL",
                "countertrend_directional_state_reason": "down_enter::anti_long_strong_plus_pro_down_confirmed",
                "countertrend_directional_state_rank": 3,
                "countertrend_anti_long_score": 1.0,
                "countertrend_anti_short_score": 0.0,
                "countertrend_pro_up_score": 0.0,
                "countertrend_pro_down_score": 1.0,
                "countertrend_directional_owner_family": "direction_agnostic_continuation",
                "countertrend_directional_down_bias_score": 1.0,
                "countertrend_directional_up_bias_score": 0.0,
                "countertrend_continuation_reason_summary": "forecast_wait_bias|belief_fragile_thesis|barrier_wait_block",
            }
        ]
    )

    _, summary = build_countertrend_down_bootstrap_validation(runtime_status, entry_decisions, recent_limit=20)

    assert summary["down_enter_count"] == 1
    assert summary["enter_reserved_violation_count"] == 1
    assert summary["recommended_next_action"] == "inspect_directional_state_machine_enter_gate"


def test_countertrend_down_bootstrap_validation_waits_for_target_family_rows() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T17:07:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T17:06:58",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "blocked_by": "",
                "action_none_reason": "",
                "countertrend_directional_bias": "NONE",
                "countertrend_action_state": "DO_NOTHING",
                "countertrend_directional_candidate_action": "",
                "countertrend_directional_execution_action": "",
                "countertrend_directional_state_reason": "no_directional_edge",
                "countertrend_directional_state_rank": 0,
                "countertrend_anti_long_score": 0.0,
                "countertrend_anti_short_score": 0.0,
                "countertrend_pro_up_score": 0.0,
                "countertrend_pro_down_score": 0.0,
                "countertrend_directional_owner_family": "",
                "countertrend_directional_down_bias_score": 0.0,
                "countertrend_directional_up_bias_score": 0.0,
                "countertrend_continuation_reason_summary": "",
            }
        ]
    )

    _, summary = build_countertrend_down_bootstrap_validation(runtime_status, entry_decisions, recent_limit=20)

    assert summary["symbol_row_count"] == 1
    assert summary["target_family_row_count"] == 0
    assert summary["recommended_next_action"] == "await_fresh_xau_lower_reversal_rows"
