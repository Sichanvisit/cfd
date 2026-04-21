from backend.services.shadow_auto_first_non_hold_decision import (
    build_shadow_auto_first_non_hold_decision,
)


def test_build_shadow_auto_first_non_hold_decision_returns_reject_for_rejected_divergence():
    frame, summary = build_shadow_auto_first_non_hold_decision(
        {
            "selected_sweep_profile_id": "threshold::0.55::0.55",
            "run_decision": "reject_preview_candidate",
            "divergence_rate": 0.95,
            "proxy_alignment_improvement": 0.1,
            "mapped_alignment_improvement": -0.9,
            "value_diff_proxy": 0.0,
        }
    )

    row = frame.iloc[0]
    assert row["decision"] == "REJECT"
    assert row["bounded_apply_state"] == "preview_divergence_rejected"
    assert summary["decision_counts"]["REJECT"] == 1
