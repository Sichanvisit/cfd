import pandas as pd

from backend.services.shadow_correction_knowledge_base import (
    build_shadow_correction_knowledge_base,
)


def test_knowledge_base_appends_new_snapshot() -> None:
    existing = pd.DataFrame()
    first_non_hold = pd.DataFrame(
        [
            {
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "decision": "APPLY_CANDIDATE",
                "bounded_apply_state": "preview_divergence_candidate",
                "value_diff_proxy": 0.118,
                "manual_alignment_improvement": 1.0,
                "drawdown_diff": 0.0,
            }
        ]
    )
    bounded_gate = pd.DataFrame(
        [
            {
                "gate_decision": "ALLOW_BOUNDED_LIVE_CANDIDATE",
                "manual_reference_row_count": 64,
            }
        ]
    )
    approval = pd.DataFrame([{"approval_status": "approved_pending_activation", "value_diff": 0.118}])
    activation = pd.DataFrame([{"activation_status": "activated_candidate_runtime_forced"}])
    observation = pd.DataFrame(
        [
            {
                "rollout_mode": "log_only",
                "shadow_runtime_state": "active",
                "shadow_runtime_reason": "loaded",
                "shadow_loaded": True,
                "entry_threshold_applied_total": 0,
                "entry_partial_live_total": 0,
                "recent_fallback_reason_counts": "{\"baseline_no_action\": 3}",
                "recent_activation_state_counts": "{\"active\": 5}",
                "recent_threshold_would_apply_count": 2,
                "recent_partial_live_would_apply_count": 1,
                "rollout_promotion_readiness": "candidate_threshold_only",
                "recommended_next_action": "review_threshold_only_candidate_from_log_only_counterfactuals",
            }
        ]
    )
    manual_audit = pd.DataFrame(
        [
            {
                "manual_reference_row_count": 64,
                "manual_target_match_rate": 1.0,
            }
        ]
    )

    frame, summary = build_shadow_correction_knowledge_base(
        existing,
        first_non_hold,
        bounded_gate,
        approval,
        activation,
        observation,
        manual_audit,
    )

    assert int(summary["row_count"]) == 1
    row = frame.iloc[0]
    assert row["preview_decision"] == "APPLY_CANDIDATE"
    assert row["gate_decision"] == "ALLOW_BOUNDED_LIVE_CANDIDATE"
    assert row["activation_status"] == "activated_candidate_runtime_forced"
    assert row["rollout_mode"] == "log_only"
    assert int(row["recent_threshold_would_apply_count"]) == 2
    assert row["rollout_promotion_readiness"] == "candidate_threshold_only"


def test_knowledge_base_updates_existing_snapshot_key() -> None:
    existing = pd.DataFrame(
        [
            {
                "knowledge_event_id": "shadow_correction_knowledge::0001",
                "generated_at": "2026-04-08T19:00:00+09:00",
                "knowledge_snapshot_key": "threshold::0.35::0.35::0.65|APPLY_CANDIDATE|ALLOW_BOUNDED_LIVE_CANDIDATE|approved_pending_activation|activated_candidate_runtime_forced|log_only|active|0|0|2|1|candidate_threshold_only",
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "preview_decision": "APPLY_CANDIDATE",
                "bounded_apply_state": "preview_divergence_candidate",
                "gate_decision": "ALLOW_BOUNDED_LIVE_CANDIDATE",
                "approval_status": "approved_pending_activation",
                "activation_status": "activated_candidate_runtime_forced",
                "rollout_mode": "log_only",
                "shadow_runtime_state": "active",
                "shadow_runtime_reason": "loaded",
                "semantic_shadow_loaded": "true",
                "value_diff": 0.05,
                "manual_alignment_improvement": 1.0,
                "drawdown_diff": 0.0,
                "manual_reference_row_count": 64,
                "manual_target_match_rate": 1.0,
                "entry_threshold_applied_total": 0,
                "entry_partial_live_total": 0,
                "recent_fallback_reason_counts": "{\"baseline_no_action\": 3}",
                "recent_activation_state_counts": "{\"active\": 5}",
                "recent_threshold_would_apply_count": 2,
                "recent_partial_live_would_apply_count": 1,
                "rollout_promotion_readiness": "candidate_threshold_only",
                "recommended_next_action": "review_threshold_only_candidate_from_log_only_counterfactuals",
                "rollback_note": "old",
            }
        ]
    )
    first_non_hold = pd.DataFrame(
        [
            {
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "decision": "APPLY_CANDIDATE",
                "bounded_apply_state": "preview_divergence_candidate",
                "value_diff_proxy": 0.118,
                "manual_alignment_improvement": 1.0,
                "drawdown_diff": 0.0,
            }
        ]
    )
    bounded_gate = pd.DataFrame([{"gate_decision": "ALLOW_BOUNDED_LIVE_CANDIDATE", "manual_reference_row_count": 64}])
    approval = pd.DataFrame([{"approval_status": "approved_pending_activation", "value_diff": 0.118}])
    activation = pd.DataFrame([{"activation_status": "activated_candidate_runtime_forced"}])
    observation = pd.DataFrame(
        [
            {
                "rollout_mode": "log_only",
                "shadow_runtime_state": "active",
                "shadow_runtime_reason": "loaded",
                "shadow_loaded": True,
                "entry_threshold_applied_total": 0,
                "entry_partial_live_total": 0,
                "recent_fallback_reason_counts": "{\"baseline_no_action\": 3}",
                "recent_activation_state_counts": "{\"active\": 5}",
                "recent_threshold_would_apply_count": 2,
                "recent_partial_live_would_apply_count": 1,
                "rollout_promotion_readiness": "candidate_threshold_only",
                "recommended_next_action": "review_threshold_only_candidate_from_log_only_counterfactuals",
            }
        ]
    )
    manual_audit = pd.DataFrame([{"manual_reference_row_count": 64, "manual_target_match_rate": 1.0}])

    frame, summary = build_shadow_correction_knowledge_base(
        existing,
        first_non_hold,
        bounded_gate,
        approval,
        activation,
        observation,
        manual_audit,
    )

    assert int(summary["row_count"]) == 1
    assert float(frame.iloc[0]["value_diff"]) == 0.118
    assert frame.iloc[0]["rollout_promotion_readiness"] == "candidate_threshold_only"
