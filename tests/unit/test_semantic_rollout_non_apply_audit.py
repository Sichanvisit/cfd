from backend.services.semantic_rollout_non_apply_audit import (
    build_semantic_rollout_non_apply_audit,
    render_semantic_rollout_non_apply_audit_markdown,
)


def test_semantic_rollout_non_apply_audit_splits_promotion_and_activation_blockers():
    payload = build_semantic_rollout_non_apply_audit(
        observation_payload={
            "rows": [
                {
                    "rollout_mode": "log_only",
                    "shadow_loaded": True,
                    "shadow_runtime_state": "active",
                    "recent_row_count": 200,
                    "recent_shadow_available_count": 11,
                    "recent_threshold_eligible_count": 0,
                    "recent_partial_live_eligible_count": 0,
                    "recent_threshold_would_apply_count": 0,
                    "recent_partial_live_would_apply_count": 0,
                    "recent_fallback_reason_counts": "{\"baseline_no_action\": 69, \"semantic_unavailable\": 64}",
                    "rollout_promotion_readiness": "blocked_no_eligible_rows",
                    "recommended_next_action": "retain_log_only_and_improve_baseline_action_or_semantic_quality",
                }
            ]
        },
        readiness_payload={
            "rows": [
                {
                    "active_runtime_state": "candidate_stage_ready",
                    "activation_ready_flag": True,
                    "bounded_gate_decision": "ALLOW_BOUNDED_LIVE_CANDIDATE",
                    "recommended_next_action": "request_human_approval_for_candidate_runtime",
                }
            ]
        },
        stage_payload={
            "rows": [
                {
                    "stage_status": "candidate_runtime_staged",
                    "approval_required": True,
                    "staged_file_count": 7,
                    "recommended_next_action": "collect_human_approval_for_bounded_live_candidate",
                }
            ]
        },
        approval_payload={
            "rows": [
                {
                    "approval_status": "approved_pending_activation",
                    "approval_decision": "APPROVE",
                    "recommended_next_action": "activate_bounded_candidate_when_runtime_is_idle",
                }
            ]
        },
        activation_payload={
            "rows": [
                {
                    "activation_status": "blocked_runtime_not_idle",
                    "runtime_idle_flag": False,
                    "open_positions_count": 2,
                    "recommended_next_action": "wait_for_runtime_idle_then_retry_activation",
                }
            ]
        },
    )

    summary = payload["summary"]
    promotion_row = payload["rows"][0]
    activation_row = payload["rows"][-1]

    assert summary["promotion_non_apply_reason_code"] == "baseline_no_action_dominant"
    assert summary["activation_non_apply_reason_code"] == "runtime_not_idle_pending_activation"
    assert promotion_row["blocking"] is True
    assert activation_row["blocking"] is True
    assert activation_row["open_positions_count"] == 2


def test_semantic_rollout_non_apply_markdown_contains_lane_breakdown():
    markdown = render_semantic_rollout_non_apply_audit_markdown(
        {
            "summary": {
                "generated_at": "2026-04-13T14:28:15+09:00",
                "promotion_non_apply_reason_ko": "baseline 자체가 no-action이 많아 semantic 후보가 생기지 않음",
                "activation_non_apply_reason_ko": "승인된 candidate는 있으나 runtime이 idle이 아니어서 activation을 미룸",
                "dominant_recent_fallback_reason": "baseline_no_action",
                "recent_row_count": 200,
                "recent_shadow_available_count": 11,
                "recent_threshold_eligible_count": 0,
                "recent_partial_live_eligible_count": 0,
                "recommended_next_action": "wait_for_runtime_idle_then_retry_activation",
            },
            "rows": [
                {
                    "lane": "promotion_counterfactual",
                    "lane_label_ko": "semantic promotion 관찰 lane",
                    "state": "blocked_no_eligible_rows",
                    "blocking": True,
                    "non_apply_reason_ko": "baseline 자체가 no-action이 많아 semantic 후보가 생기지 않음",
                    "recommended_next_action": "retain_log_only_and_improve_baseline_action_or_semantic_quality",
                    "recent_row_count": 200,
                    "recent_shadow_available_count": 11,
                    "dominant_fallback_reason": "baseline_no_action",
                    "fallback_reason_counts": {"baseline_no_action": 69},
                },
                {
                    "lane": "runtime_activation",
                    "lane_label_ko": "approved candidate activation lane",
                    "state": "blocked_runtime_not_idle",
                    "blocking": True,
                    "non_apply_reason_ko": "승인된 candidate는 있으나 runtime이 idle이 아니어서 activation을 미룸",
                    "recommended_next_action": "wait_for_runtime_idle_then_retry_activation",
                    "runtime_idle_flag": False,
                    "open_positions_count": 2,
                },
            ],
        }
    )

    assert "Semantic Rollout Non-Apply Audit" in markdown
    assert "semantic promotion 관찰 lane" in markdown
    assert "approved candidate activation lane" in markdown
