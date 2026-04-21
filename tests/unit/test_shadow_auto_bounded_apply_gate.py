import pandas as pd

from backend.services.shadow_auto_bounded_apply_gate import (
    build_shadow_auto_bounded_apply_gate,
)


def test_bounded_apply_gate_blocks_when_manual_truth_is_thin() -> None:
    first_non_hold = pd.DataFrame(
        [
            {
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "decision": "APPLY_CANDIDATE",
                "bounded_apply_state": "preview_divergence_candidate",
                "value_diff_proxy": 0.05,
                "drawdown_diff": 0.0,
                "new_false_positive_count": 0,
            }
        ]
    )
    manual_audit = pd.DataFrame(
        [
            {
                "manual_reference_row_count": 1,
                "manual_target_match_rate": 1.0,
            }
        ]
    )

    frame, _summary = build_shadow_auto_bounded_apply_gate(
        first_non_hold,
        manual_audit,
        required_manual_reference_row_count=5,
        required_value_diff_proxy=0.01,
    )

    row = frame.iloc[0]
    assert row["gate_decision"] == "REQUIRE_MORE_MANUAL_TRUTH"
    assert bool(row["live_candidate_ready_flag"]) is False


def test_bounded_apply_gate_allows_live_candidate_when_all_checks_clear() -> None:
    first_non_hold = pd.DataFrame(
        [
            {
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "decision": "APPLY_CANDIDATE",
                "bounded_apply_state": "preview_divergence_candidate",
                "value_diff_proxy": 0.05,
                "drawdown_diff": 0.0,
                "new_false_positive_count": 0,
            }
        ]
    )
    manual_audit = pd.DataFrame(
        [
            {
                "manual_reference_row_count": 5,
                "manual_target_match_rate": 0.8,
            }
        ]
    )

    frame, summary = build_shadow_auto_bounded_apply_gate(
        first_non_hold,
        manual_audit,
        required_manual_reference_row_count=5,
        required_value_diff_proxy=0.01,
    )

    row = frame.iloc[0]
    assert row["gate_decision"] == "ALLOW_BOUNDED_LIVE_CANDIDATE"
    assert bool(row["live_candidate_ready_flag"]) is True
    assert summary["live_candidate_ready_count"] == 1
