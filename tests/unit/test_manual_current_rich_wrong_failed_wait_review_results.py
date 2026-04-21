import pandas as pd

from backend.services.manual_current_rich_wrong_failed_wait_review_results import (
    build_current_rich_wrong_failed_wait_review_results,
)


def test_review_results_keep_wait_bias_for_failed_wait_proxies() -> None:
    queue = pd.DataFrame(
        [
            {
                "episode_id": "btc_seed_1",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-06T18:30:00+09:00",
                "target_followup_pattern": "btc_helper_wait_failed_wait_check",
                "review_priority": "p1",
            },
            {
                "episode_id": "nas_seed_1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-06T17:30:00+09:00",
                "target_followup_pattern": "nas_failed_wait_shift_proxy",
                "review_priority": "p1",
            },
        ]
    )
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-06 18:31:00",
                "symbol": "BTCUSD",
                "barrier_candidate_recommended_family": "relief_watch",
                "barrier_candidate_supporting_label": "correct_wait",
                "barrier_action_hint_reason_summary": "relief_watch|balanced",
                "entry_wait_decision": "wait_soft_helper_block",
                "observe_reason": "outer_band_reversal_support_required_observe",
                "blocked_by": "outer_band_guard",
                "core_reason": "core_shadow_observe_wait",
                "action": "SELL",
            },
            {
                "time": "2026-04-06 17:31:00",
                "symbol": "NAS100",
                "barrier_candidate_recommended_family": "relief_watch",
                "barrier_candidate_supporting_label": "correct_wait",
                "barrier_action_hint_reason_summary": "relief_watch|balanced",
                "entry_wait_decision": "skip",
                "observe_reason": "upper_break_fail_confirm",
                "blocked_by": "energy_soft_block",
                "core_reason": "energy_soft_block",
                "action": "SELL",
            },
        ]
    )

    review, summary = build_current_rich_wrong_failed_wait_review_results(queue, entry_decisions)

    assert len(review) == 2
    btc_row = review[review["episode_id"] == "btc_seed_1"].iloc[0].to_dict()
    nas_row = review[review["episode_id"] == "nas_seed_1"].iloc[0].to_dict()
    assert btc_row["review_decision"] == "keep_wait_bias"
    assert btc_row["canonical_action"] == "do_not_promote_failed_wait_seed"
    assert nas_row["review_decision"] == "do_not_shift_failed_wait"
    assert nas_row["canonical_action"] == "do_not_promote_failed_wait_seed"
    assert summary["decision_counts"] == {"keep_wait_bias": 1, "do_not_shift_failed_wait": 1}


def test_review_results_returns_empty_when_queue_missing() -> None:
    review, summary = build_current_rich_wrong_failed_wait_review_results(pd.DataFrame(), pd.DataFrame())

    assert review.empty
    assert summary["row_count"] == 0
