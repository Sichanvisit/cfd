from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_canary_activation_packet import (
    build_checkpoint_pa8_nas100_action_only_canary_activation_packet,
    render_checkpoint_pa8_nas100_action_only_canary_activation_packet_markdown,
)


def test_build_checkpoint_pa8_nas100_action_only_canary_activation_packet_marks_ready() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_activation_packet(
        canary_execution_checklist_payload={
            "summary": {
                "symbol": "NAS100",
                "execution_state": "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION",
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
                "blockers": [],
            },
            "scope_snapshot": {
                "symbol_allowlist": ["NAS100"],
                "surface_allowlist": ["continuation_hold_surface"],
                "checkpoint_type_allowlist": ["RUNNER_CHECK"],
                "family_allowlist": ["profit_hold_bias"],
                "baseline_action_allowlist": ["HOLD"],
                "preview_action": "PARTIAL_THEN_HOLD",
                "preview_reason": "nas100_profit_hold_bias_hold_to_partial_then_hold_preview",
                "change_mode": "action_only_preview_candidate",
            },
            "guardrail_snapshot": {
                "sample_floor": 50,
                "worsened_row_count_ceiling": 0,
                "hold_precision_floor": 0.8,
                "runtime_proxy_match_rate_must_improve": True,
                "partial_then_hold_quality_must_not_regress": True,
                "rollback_watch_metrics": ["hold_precision_drop_below_baseline"],
            },
            "execution_steps": [{"step_id": "preflight", "status": "ready"}],
        },
        canary_review_packet_payload={
            "summary": {
                "canary_review_state": "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW",
                "provisional_canary_ready": True,
            }
        },
    )

    summary = payload["summary"]
    assert summary["activation_state"] == "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW"
    assert summary["allow_activation"] is True
    assert payload["activation_scope"]["scene_bias_excluded"] is True
    assert payload["activation_scope"]["size_change_allowed"] is False


def test_build_checkpoint_pa8_nas100_action_only_canary_activation_packet_holds_with_blocker() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_activation_packet(
        canary_execution_checklist_payload={
            "summary": {
                "symbol": "NAS100",
                "execution_state": "HOLD_CANARY_EXECUTION_CHECKLIST",
                "blockers": ["preview_has_worsened_rows"],
            }
        },
        canary_review_packet_payload={
            "summary": {
                "canary_review_state": "HOLD_PREVIEW_ONLY_REVIEW",
                "provisional_canary_ready": False,
            }
        },
    )

    summary = payload["summary"]
    assert summary["activation_state"] == "HOLD_ACTION_ONLY_CANARY_ACTIVATION_PACKET"
    assert summary["allow_activation"] is False
    assert "preview_has_worsened_rows" in summary["blockers"]


def test_render_checkpoint_pa8_nas100_action_only_canary_activation_packet_markdown_contains_scope() -> None:
    markdown = render_checkpoint_pa8_nas100_action_only_canary_activation_packet_markdown(
        {
            "summary": {
                "activation_state": "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW",
                "allow_activation": True,
                "manual_activation_required": True,
                "canary_review_state": "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW",
                "execution_state": "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION",
                "target_metric_goal": "raise_hold_precision_to_at_least_0.80_without_scene_bias_changes",
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.945946,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "preview_runtime_proxy_match_rate": 0.964195,
                "baseline_partial_then_hold_quality": 0.971302,
                "preview_partial_then_hold_quality": 0.975701,
                "recommended_next_action": "manually_review_and_confirm_nas100_action_only_canary_activation",
                "blockers": [],
            },
            "activation_scope": {
                "activation_id": "pa8_canary::NAS100::continuation_hold_surface::RUNNER_CHECK::profit_hold_bias",
                "symbol_allowlist": ["NAS100"],
                "surface_allowlist": ["continuation_hold_surface"],
                "checkpoint_type_allowlist": ["RUNNER_CHECK"],
                "family_allowlist": ["profit_hold_bias"],
                "baseline_action_allowlist": ["HOLD"],
                "candidate_action": "PARTIAL_THEN_HOLD",
                "scene_bias_excluded": True,
                "size_change_allowed": False,
                "new_entry_logic_allowed": False,
            },
            "activation_guardrails": {
                "sample_floor": 50,
                "worsened_row_count_ceiling": 0,
                "hold_precision_floor": 0.8,
                "runtime_proxy_match_rate_must_improve": True,
                "partial_then_hold_quality_must_not_regress": True,
                "rollback_watch_metrics": ["hold_precision_drop_below_baseline"],
            },
            "activation_checklist": ["Scope stays NAS100-only and family stays profit_hold_bias-only."],
            "monitoring_plan": {
                "monitor_only_scoped_family": True,
                "compare_against_baseline_metrics": ["hold_precision"],
                "first_window_policy": "do_not_widen_scope_during_first_canary_window",
            },
        }
    )

    assert "# PA8 NAS100 Action-Only Canary Activation Packet" in markdown
    assert "- activation_state: `READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW`" in markdown
    assert "- [ ] Scope stays NAS100-only and family stays profit_hold_bias-only." in markdown
    assert "- candidate_action: `PARTIAL_THEN_HOLD`" in markdown
