import pandas as pd

from backend.services.countertrend_materialization_check import (
    build_countertrend_materialization_check,
    render_countertrend_materialization_check_markdown,
)


def test_countertrend_materialization_check_flags_target_family_candidate_rows() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T11:40:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T11:39:58",
                "symbol": "XAUUSD",
                "action": "BUY",
                "outcome": "wait",
                "setup_id": "range_lower_reversal_buy",
                "setup_reason": "shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
                "blocked_by": "",
                "action_none_reason": "observe_state_wait",
                "countertrend_continuation_enabled": True,
                "countertrend_continuation_state": "down_continuation_bias",
                "countertrend_continuation_action": "SELL",
                "countertrend_continuation_confidence": 0.82,
                "countertrend_continuation_reason_summary": "forecast_wait_bias|belief_fragile_thesis|barrier_wait_block",
                "countertrend_candidate_action": "SELL",
                "countertrend_candidate_confidence": 0.82,
                "countertrend_candidate_reason": "countertrend_continuation_signal_v1",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "SELL",
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
            },
            {
                "time": "2026-04-09T11:39:55",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "wait",
                "setup_id": "",
                "setup_reason": "",
                "blocked_by": "",
                "action_none_reason": "observe_state_wait",
                "countertrend_continuation_enabled": False,
                "countertrend_continuation_state": "",
                "countertrend_continuation_action": "",
                "countertrend_continuation_confidence": 0.0,
                "countertrend_continuation_reason_summary": "",
                "countertrend_candidate_action": "",
                "countertrend_candidate_confidence": 0.0,
                "countertrend_candidate_reason": "",
                "entry_candidate_bridge_source": "",
                "entry_candidate_bridge_action": "",
                "entry_candidate_surface_family": "",
                "entry_candidate_surface_state": "",
            },
        ]
    )

    frame, summary = build_countertrend_materialization_check(runtime_status, entry_decisions, recent_limit=20)
    markdown = render_countertrend_materialization_check_markdown(summary, frame)

    assert summary["field_presence_ok"] is True
    assert summary["symbol_row_count"] == 1
    assert summary["target_family_row_count"] == 1
    assert summary["countertrend_enabled_count"] == 1
    assert summary["countertrend_candidate_sell_count"] == 1
    assert summary["recommended_next_action"] == "proceed_to_mf7b_directional_evidence_split"
    assert not frame.empty
    assert bool(frame.iloc[0]["target_family_match"]) is True
    assert frame.iloc[0]["countertrend_candidate_action"] == "SELL"
    assert "proceed_to_mf7b_directional_evidence_split" in markdown


def test_countertrend_materialization_check_waits_for_target_family_rows() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T11:41:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T11:40:58",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "blocked_by": "",
                "action_none_reason": "probe_not_promoted",
                "countertrend_continuation_enabled": False,
                "countertrend_continuation_state": "",
                "countertrend_continuation_action": "",
                "countertrend_continuation_confidence": 0.0,
                "countertrend_continuation_reason_summary": "",
                "countertrend_candidate_action": "",
                "countertrend_candidate_confidence": 0.0,
                "countertrend_candidate_reason": "",
                "entry_candidate_bridge_source": "",
                "entry_candidate_bridge_action": "",
                "entry_candidate_surface_family": "",
                "entry_candidate_surface_state": "",
            }
        ]
    )

    _, summary = build_countertrend_materialization_check(runtime_status, entry_decisions, recent_limit=20)

    assert summary["field_presence_ok"] is True
    assert summary["symbol_row_count"] == 1
    assert summary["target_family_row_count"] == 0
    assert summary["countertrend_enabled_count"] == 0
    assert summary["countertrend_candidate_sell_count"] == 0
    assert summary["recommended_next_action"] == "await_fresh_xau_lower_reversal_rows"
