import pandas as pd

from backend.services.manual_vs_heuristic_wrong_failed_wait_audit import (
    build_wrong_failed_wait_audit,
)


def test_wrong_failed_wait_audit_flags_far_gap_and_wait_dominant_cases() -> None:
    comparison = pd.DataFrame(
        [
            {
                "episode_id": "nas_ep_1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-03T10:45:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "heuristic_barrier_main_label": "correct_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_match_gap_minutes": 165.0,
                "miss_type": "wrong_failed_wait_interpretation",
            },
            {
                "episode_id": "btc_ep_1",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-02T21:46:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "heuristic_barrier_main_label": "correct_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_match_gap_minutes": 89.0,
                "miss_type": "wrong_failed_wait_interpretation",
            },
        ]
    )
    fallback = pd.DataFrame(
        [
            {
                "episode_id": "nas_ep_1",
                "global_detail_entry_wait_decision": "skip",
                "global_detail_blocked_by": "range_lower_buy_requires_lower_edge",
                "global_detail_observe_reason": "lower_rebound_probe_observe",
                "global_detail_core_reason": "energy_soft_block",
                "global_detail_entry_enter_value": "",
                "global_detail_entry_wait_value": "",
            },
            {
                "episode_id": "btc_ep_1",
                "global_detail_entry_wait_decision": "wait_soft_helper_block",
                "global_detail_blocked_by": "outer_band_guard",
                "global_detail_observe_reason": "outer_band_reversal_support_required_observe",
                "global_detail_core_reason": "core_shadow_observe_wait",
                "global_detail_entry_enter_value": 0.40,
                "global_detail_entry_wait_value": 0.53,
            },
        ]
    )

    audit, summary = build_wrong_failed_wait_audit(comparison, fallback)

    assert len(audit) == 2
    nas_row = audit[audit["episode_id"] == "nas_ep_1"].iloc[0].to_dict()
    btc_row = audit[audit["episode_id"] == "btc_ep_1"].iloc[0].to_dict()
    assert nas_row["gap_risk_flag"] == "very_far_gap"
    assert nas_row["pattern_flag"] == "rebound_probe_skip"
    assert nas_row["rule_change_readiness"] == "needs_closer_manual_truth"
    assert btc_row["gap_risk_flag"] == "far_gap"
    assert btc_row["value_bias_flag"] == "wait_value_dominant"
    assert btc_row["pattern_flag"] == "outer_band_helper_wait"
    assert btc_row["rule_change_readiness"] == "needs_closer_manual_truth"
    assert summary["case_count"] == 2
    assert summary["gap_risk_counts"] == {"very_far_gap": 1, "far_gap": 1}


def test_wrong_failed_wait_audit_returns_empty_without_cases() -> None:
    comparison = pd.DataFrame([{"episode_id": "ep_1", "miss_type": ""}])
    fallback = pd.DataFrame()

    audit, summary = build_wrong_failed_wait_audit(comparison, fallback)

    assert audit.empty
    assert summary["case_count"] == 0
