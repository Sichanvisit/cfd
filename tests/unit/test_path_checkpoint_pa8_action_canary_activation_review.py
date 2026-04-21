from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_canary_activation_review import (
    build_checkpoint_pa8_nas100_action_only_canary_activation_review,
    render_checkpoint_pa8_nas100_action_only_canary_activation_review_markdown,
)


def test_build_checkpoint_pa8_nas100_action_only_canary_activation_review_marks_ready() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_activation_review(
        activation_packet_payload={
            "summary": {
                "symbol": "NAS100",
                "activation_state": "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW",
                "allow_activation": True,
                "blockers": [],
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.945946,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "preview_runtime_proxy_match_rate": 0.964195,
            },
            "activation_scope": {
                "symbol_allowlist": ["NAS100"],
                "surface_allowlist": ["continuation_hold_surface"],
                "checkpoint_type_allowlist": ["RUNNER_CHECK"],
                "family_allowlist": ["profit_hold_bias"],
                "candidate_action": "PARTIAL_THEN_HOLD",
            },
            "activation_guardrails": {},
        }
    )

    assert payload["summary"]["review_state"] == "READY_FOR_HUMAN_ACTIVATION_DECISION"
    assert payload["summary"]["recommended_next_action"] == "approve_or_hold_nas100_action_only_canary_activation"


def test_render_checkpoint_pa8_nas100_action_only_canary_activation_review_markdown_contains_conditions() -> None:
    markdown = render_checkpoint_pa8_nas100_action_only_canary_activation_review_markdown(
        {
            "summary": {
                "review_state": "READY_FOR_HUMAN_ACTIVATION_DECISION",
                "activation_state": "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW",
                "allow_activation": True,
                "review_question": "Should this be approved?",
                "recommended_next_action": "approve_or_hold_nas100_action_only_canary_activation",
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.945946,
            },
            "approval_conditions": ["Approve only if the scope remains narrow."],
            "decision_options": ["approve_narrow_bounded_action_only_canary"],
            "scope_snapshot": {"symbol_allowlist": ["NAS100"]},
        }
    )

    assert "# PA8 NAS100 Action-Only Canary Activation Human Review" in markdown
    assert "- [ ] Approve only if the scope remains narrow." in markdown
    assert "- `approve_narrow_bounded_action_only_canary`" in markdown
