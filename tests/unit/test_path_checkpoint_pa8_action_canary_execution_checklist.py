from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_canary_execution_checklist import (
    build_checkpoint_pa8_nas100_action_only_canary_execution_checklist,
    render_checkpoint_pa8_nas100_action_only_canary_execution_checklist_markdown,
)


def test_build_checkpoint_pa8_nas100_action_only_canary_execution_checklist_marks_ready() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_execution_checklist(
        canary_review_packet_payload={
            "summary": {
                "symbol": "NAS100",
                "canary_review_state": "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW",
                "provisional_canary_ready": True,
                "target_metric_goal": "raise_hold_precision_to_at_least_0.80_without_scene_bias_changes",
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.945946,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "preview_runtime_proxy_match_rate": 0.964195,
                "baseline_partial_then_hold_quality": 0.971302,
                "preview_partial_then_hold_quality": 0.975701,
                "eligible_row_count": 82,
                "preview_changed_row_count": 82,
                "improved_row_count": 82,
                "worsened_row_count": 0,
                "recommended_next_action": "prepare_nas100_action_only_provisional_canary_scope",
                "blockers": [],
            },
            "candidate_scope": {
                "symbol_allowlist": ["NAS100"],
                "surface_allowlist": ["continuation_hold_surface"],
                "checkpoint_type_allowlist": ["RUNNER_CHECK"],
                "family_allowlist": ["profit_hold_bias"],
                "baseline_action_allowlist": ["HOLD"],
                "preview_action": "PARTIAL_THEN_HOLD",
                "scene_bias_mode": "preview_only_excluded_from_canary_scope",
            },
            "canary_guardrails": {
                "sample_floor": 50,
                "worsened_row_count_ceiling": 0,
                "hold_precision_floor": 0.8,
                "runtime_proxy_match_rate_must_improve": True,
                "partial_then_hold_quality_must_not_regress": True,
            },
            "review_context": {"preview_summary": {"eligible_row_count": 82}},
        }
    )

    summary = payload["summary"]
    assert summary["execution_state"] == "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION"
    assert summary["recommended_next_action"] == "review_and_confirm_nas100_bounded_action_only_canary_execution"
    assert payload["scope_snapshot"]["symbol_allowlist"] == ["NAS100"]
    assert payload["execution_steps"][0]["status"] == "ready"


def test_build_checkpoint_pa8_nas100_action_only_canary_execution_checklist_holds_when_not_ready() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_execution_checklist(
        canary_review_packet_payload={
            "summary": {
                "symbol": "NAS100",
                "canary_review_state": "HOLD_PREVIEW_ONLY_REVIEW",
                "provisional_canary_ready": False,
                "recommended_next_action": "keep_nas100_profit_hold_bias_preview_only",
                "blockers": ["preview_has_worsened_rows"],
            }
        }
    )

    summary = payload["summary"]
    assert summary["execution_state"] == "HOLD_CANARY_EXECUTION_CHECKLIST"
    assert summary["recommended_next_action"] == "keep_nas100_action_only_canary_in_review"
    assert payload["execution_steps"][0]["status"] == "hold"


def test_render_checkpoint_pa8_nas100_action_only_canary_execution_checklist_markdown_contains_steps() -> None:
    markdown = render_checkpoint_pa8_nas100_action_only_canary_execution_checklist_markdown(
        {
            "summary": {
                "canary_review_state": "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW",
                "execution_state": "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION",
                "provisional_canary_ready": True,
                "target_metric_goal": "raise_hold_precision_to_at_least_0.80_without_scene_bias_changes",
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.945946,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "preview_runtime_proxy_match_rate": 0.964195,
                "baseline_partial_then_hold_quality": 0.971302,
                "preview_partial_then_hold_quality": 0.975701,
                "recommended_next_action": "review_and_confirm_nas100_bounded_action_only_canary_execution",
            },
            "scope_snapshot": {
                "symbol_allowlist": ["NAS100"],
                "surface_allowlist": ["continuation_hold_surface"],
                "checkpoint_type_allowlist": ["RUNNER_CHECK"],
                "family_allowlist": ["profit_hold_bias"],
                "baseline_action_allowlist": ["HOLD"],
                "preview_action": "PARTIAL_THEN_HOLD",
                "scene_bias_mode": "preview_only_excluded_from_canary_scope",
            },
            "guardrail_snapshot": {
                "sample_floor": 50,
                "worsened_row_count_ceiling": 0,
                "hold_precision_floor": 0.8,
                "runtime_proxy_match_rate_must_improve": True,
                "partial_then_hold_quality_must_not_regress": True,
            },
            "execution_steps": [
                {
                    "step_id": "preflight",
                    "title": "Preflight Freeze",
                    "status": "ready",
                    "goal": "Freeze scope.",
                    "check_items": ["Confirm the candidate scope is still NAS100."],
                }
            ],
            "checklist_rows": [
                {
                    "phase": "scope",
                    "goal": "Freeze the canary to a narrow slice.",
                    "checks": ["Symbol allowlist is NAS100 only."],
                }
            ],
        }
    )

    assert "# PA8 NAS100 Action-Only Canary Execution Checklist" in markdown
    assert "- execution_state: `READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION`" in markdown
    assert "### preflight" in markdown
    assert "- [ ] Confirm the candidate scope is still NAS100." in markdown
