from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_canary_activation_apply import (
    build_checkpoint_pa8_nas100_action_only_canary_activation_apply,
)


def test_build_checkpoint_pa8_action_canary_activation_apply_approves_and_activates() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_activation_apply(
        activation_review_payload={
            "summary": {
                "symbol": "NAS100",
                "review_state": "READY_FOR_HUMAN_ACTIVATION_DECISION",
                "allow_activation": True,
                "blockers": [],
                "eligible_row_count": 82,
                "preview_changed_row_count": 82,
                "worsened_row_count": 0,
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.945946,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "preview_runtime_proxy_match_rate": 0.964195,
                "baseline_partial_then_hold_quality": 0.971302,
                "preview_partial_then_hold_quality": 0.975701,
            },
            "scope_snapshot": {
                "activation_id": "pa8_canary::NAS100::continuation_hold_surface::RUNNER_CHECK::profit_hold_bias",
                "symbol_allowlist": ["NAS100"],
                "surface_allowlist": ["continuation_hold_surface"],
                "checkpoint_type_allowlist": ["RUNNER_CHECK"],
                "family_allowlist": ["profit_hold_bias"],
                "baseline_action_allowlist": ["HOLD"],
                "candidate_action": "PARTIAL_THEN_HOLD",
                "candidate_reason": "nas100_profit_hold_bias_hold_to_partial_then_hold_preview",
                "scene_bias_excluded": True,
            },
            "guardrail_snapshot": {
                "sample_floor": 50,
                "worsened_row_count_ceiling": 0,
                "hold_precision_floor": 0.8,
                "runtime_proxy_match_rate_must_improve": True,
                "partial_then_hold_quality_must_not_regress": True,
                "rollback_watch_metrics": ["hold_precision_drop_below_baseline"],
            },
        },
        approval_decision="APPROVE",
    )

    assert payload["summary"]["activation_apply_state"] == "ACTIVE_ACTION_ONLY_CANARY"
    assert payload["summary"]["approval_state"] == "MANUAL_ACTIVATION_APPROVED"
    assert payload["active_state"]["active"] is True
    assert payload["active_state"]["window_status"] == "FIRST_CANARY_WINDOW_ACTIVE"
