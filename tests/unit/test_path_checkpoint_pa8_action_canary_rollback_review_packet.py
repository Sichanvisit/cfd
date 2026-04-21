from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_canary_rollback_review_packet import (
    build_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet,
    render_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_markdown,
)


def test_build_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_marks_ready() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet(
        activation_packet_payload={
            "summary": {
                "symbol": "NAS100",
                "activation_state": "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW",
                "allow_activation": True,
                "blockers": [],
                "baseline_hold_precision": 0.759036,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "baseline_partial_then_hold_quality": 0.971302,
            },
            "activation_guardrails": {
                "rollback_watch_metrics": [
                    "hold_precision_drop_below_baseline",
                    "new_worsened_rows_detected",
                ]
            },
        },
        monitoring_packet_payload={
            "summary": {
                "monitoring_state": "READY_TO_START_FIRST_CANARY_WINDOW",
            }
        },
    )

    assert payload["summary"]["rollback_review_state"] == "READY_WITH_NO_TRIGGER_ACTIVE"
    assert payload["summary"]["current_trigger_state"] == "no_active_trigger_detected"


def test_render_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_markdown_contains_actions() -> None:
    markdown = render_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_markdown(
        {
            "summary": {
                "rollback_review_state": "READY_WITH_NO_TRIGGER_ACTIVE",
                "current_trigger_state": "no_active_trigger_detected",
                "recommended_next_action": "keep_rollback_packet_ready_during_first_canary_window",
                "baseline_hold_precision": 0.759036,
            },
            "rollback_triggers": ["hold_precision_drop_below_baseline"],
            "rollback_questions": ["Did hold_precision drop below baseline?"],
            "rollback_actions": ["disable_nas100_action_only_canary_scope"],
        }
    )

    assert "# PA8 NAS100 Action-Only Canary Rollback Review Packet" in markdown
    assert "- `hold_precision_drop_below_baseline`" in markdown
    assert "- `disable_nas100_action_only_canary_scope`" in markdown
