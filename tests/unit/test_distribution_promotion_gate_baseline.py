import pandas as pd

from backend.services.distribution_promotion_gate_baseline import (
    build_distribution_promotion_gate_baseline,
    render_distribution_promotion_gate_baseline_markdown,
)


def test_distribution_promotion_gate_baseline_materializes_relative_probe_and_enter() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T18:20:00+09:00",
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T18:19:59",
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "observe_reason": "upper_reject_probe_observe",
                "blocked_by": "clustered_entry_price_zone",
                "action_none_reason": "probe_not_promoted",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_confidence": 0.91,
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
                "countertrend_action_state": "UP_PROBE",
                "countertrend_directional_candidate_action": "BUY",
                "countertrend_directional_up_bias_score": 0.91,
                "countertrend_directional_down_bias_score": 0.0,
                "countertrend_candidate_confidence": 0.88,
                "countertrend_pro_up_score": 0.89,
                "countertrend_anti_short_score": 0.84,
                "countertrend_continuation_surface_family": "follow_through_surface",
                "countertrend_continuation_surface_state": "continuation_follow",
            },
            {
                "time": "2026-04-09T18:19:50",
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "observe_reason": "upper_reject_probe_observe",
                "blocked_by": "clustered_entry_price_zone",
                "action_none_reason": "probe_not_promoted",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_confidence": 0.73,
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
                "countertrend_action_state": "UP_PROBE",
                "countertrend_directional_candidate_action": "BUY",
                "countertrend_directional_up_bias_score": 0.73,
                "countertrend_directional_down_bias_score": 0.0,
                "countertrend_candidate_confidence": 0.72,
                "countertrend_pro_up_score": 0.7,
                "countertrend_anti_short_score": 0.68,
                "countertrend_continuation_surface_family": "follow_through_surface",
                "countertrend_continuation_surface_state": "continuation_follow",
            },
            {
                "time": "2026-04-09T18:19:40",
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "observe_reason": "upper_reject_probe_observe",
                "blocked_by": "clustered_entry_price_zone",
                "action_none_reason": "probe_not_promoted",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_confidence": 0.58,
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
                "countertrend_action_state": "UP_WATCH",
                "countertrend_directional_candidate_action": "",
                "countertrend_directional_up_bias_score": 0.58,
                "countertrend_directional_down_bias_score": 0.0,
                "countertrend_candidate_confidence": 0.0,
                "countertrend_pro_up_score": 0.57,
                "countertrend_anti_short_score": 0.55,
                "countertrend_continuation_surface_family": "follow_through_surface",
                "countertrend_continuation_surface_state": "continuation_follow",
            },
        ]
    )

    frame, summary = build_distribution_promotion_gate_baseline(
        runtime_status,
        entry_decisions,
        recent_limit=20,
        relative_probe_threshold=0.66,
    )
    markdown = render_distribution_promotion_gate_baseline_markdown(summary, frame)

    assert summary["relevant_row_count"] == 3
    assert summary["cluster_count"] == 1
    top = frame.loc[frame["promotion_score"].idxmax()]
    mid = frame.sort_values("promotion_score", ascending=False).iloc[1]
    low = frame.sort_values("promotion_score", ascending=False).iloc[2]
    assert top["combined_gate_state"] == "ENTER_ELIGIBLE"
    assert mid["combined_gate_state"] == "PROBE_ELIGIBLE"
    assert low["combined_gate_state"] in {"ABSOLUTE_ONLY_HOLD", "WATCH_ONLY"}
    assert "Distribution-Based Promotion Gate Baseline" in markdown


def test_distribution_promotion_gate_baseline_flags_underfire_and_overfire() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T18:21:00+09:00",
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T18:20:59",
                "symbol": "BTCUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "observe_reason": "upper_reject_probe_observe",
                "blocked_by": "forecast_guard",
                "action_none_reason": "observe_state_wait",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_confidence": 0.88,
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
                "countertrend_action_state": "DO_NOTHING",
                "countertrend_directional_candidate_action": "BUY",
                "countertrend_directional_up_bias_score": 0.88,
                "countertrend_directional_down_bias_score": 0.0,
                "countertrend_candidate_confidence": 0.86,
                "countertrend_pro_up_score": 0.83,
                "countertrend_anti_short_score": 0.8,
                "countertrend_continuation_surface_family": "follow_through_surface",
                "countertrend_continuation_surface_state": "continuation_follow",
            },
            {
                "time": "2026-04-09T18:20:49",
                "symbol": "BTCUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "observe_reason": "upper_reject_probe_observe",
                "blocked_by": "",
                "action_none_reason": "",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_confidence": 0.45,
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
                "countertrend_action_state": "UP_PROBE",
                "countertrend_directional_candidate_action": "BUY",
                "countertrend_directional_up_bias_score": 0.45,
                "countertrend_directional_down_bias_score": 0.0,
                "countertrend_candidate_confidence": 0.42,
                "countertrend_pro_up_score": 0.41,
                "countertrend_anti_short_score": 0.4,
                "countertrend_continuation_surface_family": "follow_through_surface",
                "countertrend_continuation_surface_state": "continuation_follow",
            },
            {
                "time": "2026-04-09T18:20:39",
                "symbol": "BTCUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "observe_reason": "upper_reject_probe_observe",
                "blocked_by": "",
                "action_none_reason": "",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_confidence": 0.62,
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
                "countertrend_action_state": "UP_WATCH",
                "countertrend_directional_candidate_action": "",
                "countertrend_directional_up_bias_score": 0.62,
                "countertrend_directional_down_bias_score": 0.0,
                "countertrend_candidate_confidence": 0.0,
                "countertrend_pro_up_score": 0.61,
                "countertrend_anti_short_score": 0.6,
                "countertrend_continuation_surface_family": "follow_through_surface",
                "countertrend_continuation_surface_state": "continuation_follow",
            },
        ]
    )

    frame, summary = build_distribution_promotion_gate_baseline(runtime_status, entry_decisions, recent_limit=20)

    underfired = frame.loc[frame["promotion_gap_note"] == "underfired_vs_distribution"]
    overfired = frame.loc[frame["promotion_gap_note"] == "overfired_vs_distribution"]
    assert not underfired.empty
    assert not overfired.empty
    assert summary["underfired_row_count"] >= 1
    assert summary["overfired_row_count"] >= 1
