import pandas as pd

from backend.services.shadow_auto_decision_engine import build_shadow_auto_decision_engine


def test_build_shadow_auto_decision_engine_returns_apply_candidate_for_strong_preview_accept():
    correction = pd.DataFrame(
        [
            {
                "shadow_correction_run_id": "shadow_correction::0001",
                "decision": "accept_preview_candidate",
                "available_row_count": 12,
                "value_diff": 1.5,
                "manual_alignment_improvement": 0.2,
            }
        ]
    )

    frame, summary = build_shadow_auto_decision_engine(correction, preview_bundle_ready=True)

    row = frame.iloc[0]
    assert row["decision"] == "APPLY_CANDIDATE"
    assert row["bounded_apply_state"] == "shadow_preview_ready_for_human_approval"
    assert summary["decision_counts"]["APPLY_CANDIDATE"] == 1


def test_build_shadow_auto_decision_engine_holds_when_preview_bundle_is_missing():
    correction = pd.DataFrame(
        [
            {
                "shadow_correction_run_id": "shadow_correction::0001",
                "decision": "accept_preview_candidate",
                "available_row_count": 12,
                "value_diff": 1.5,
                "manual_alignment_improvement": 0.2,
            }
        ]
    )

    frame, _summary = build_shadow_auto_decision_engine(correction, preview_bundle_ready=False)

    row = frame.iloc[0]
    assert row["decision"] == "HOLD"
    assert row["bounded_apply_state"] == "preview_bundle_missing"
