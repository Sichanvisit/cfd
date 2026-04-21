from backend.services.bounded_rollout_candidate_gate import (
    build_bounded_rollout_candidate_gate,
    render_bounded_rollout_candidate_gate_markdown,
)


def test_bounded_rollout_candidate_gate_selects_only_reviewable_initial_entry() -> None:
    payload = {
        "rows": [
            {
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "adapter_mode": "btc_observe_relief_adapter",
                "readiness_state": "preview_eval_ready",
                "row_count": 15,
                "positive_count": 10,
                "negative_count": 5,
                "unlabeled_ratio": 0.0,
                "strong_row_count": 7,
                "positive_rate": 0.666667,
                "probe_eligible_count": 0,
                "failed_follow_through_count": 2,
                "early_exit_regret_count": 0,
                "false_breakout_count": 2,
                "missed_good_wait_release_count": 2,
                "late_entry_chase_fail_count": 1,
            },
            {
                "market_family": "NAS100",
                "surface_name": "initial_entry_surface",
                "adapter_mode": "nas_conflict_observe_adapter",
                "readiness_state": "needs_label_resolution",
                "row_count": 17,
                "positive_count": 11,
                "negative_count": 4,
                "unlabeled_ratio": 0.117647,
                "strong_row_count": 8,
                "positive_rate": 0.733333,
                "probe_eligible_count": 0,
                "failed_follow_through_count": 0,
                "early_exit_regret_count": 0,
                "false_breakout_count": 0,
                "missed_good_wait_release_count": 6,
                "late_entry_chase_fail_count": 0,
            },
            {
                "market_family": "XAUUSD",
                "surface_name": "follow_through_surface",
                "adapter_mode": "xau_follow_through_relief_adapter",
                "readiness_state": "single_class_only",
                "row_count": 19,
                "positive_count": 19,
                "negative_count": 0,
                "unlabeled_ratio": 0.0,
                "strong_row_count": 10,
                "positive_rate": 1.0,
                "probe_eligible_count": 56,
                "failed_follow_through_count": 1,
                "early_exit_regret_count": 0,
                "false_breakout_count": 4,
                "missed_good_wait_release_count": 0,
                "late_entry_chase_fail_count": 0,
            },
        ]
    }

    frame, summary = build_bounded_rollout_candidate_gate(payload)
    markdown = render_bounded_rollout_candidate_gate_markdown(summary, frame)

    assert summary["review_canary_count"] == 1
    btc = frame.loc[(frame["market_family"] == "BTCUSD") & (frame["surface_name"] == "initial_entry_surface")].iloc[0]
    assert btc["rollout_candidate_state"] == "REVIEW_CANARY_CANDIDATE"
    nas = frame.loc[(frame["market_family"] == "NAS100") & (frame["surface_name"] == "initial_entry_surface")].iloc[0]
    assert nas["rollout_candidate_state"] == "HOLD_NOT_READY"
    xau = frame.loc[(frame["market_family"] == "XAUUSD") & (frame["surface_name"] == "follow_through_surface")].iloc[0]
    assert xau["rollout_candidate_state"] == "HOLD_OUT_OF_SCOPE"
    assert "Bounded Rollout Candidate Gate" in markdown
