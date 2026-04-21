from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_canary_monitoring_packet import (
    build_checkpoint_pa8_nas100_action_only_canary_monitoring_packet,
    render_checkpoint_pa8_nas100_action_only_canary_monitoring_packet_markdown,
)


def test_build_checkpoint_pa8_nas100_action_only_canary_monitoring_packet_marks_ready() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_monitoring_packet(
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
                "baseline_partial_then_hold_quality": 0.971302,
                "preview_partial_then_hold_quality": 0.975701,
            },
            "monitoring_plan": {
                "compare_against_baseline_metrics": [
                    "hold_precision",
                    "runtime_proxy_match_rate",
                    "partial_then_hold_quality",
                ]
            },
        }
    )

    assert payload["summary"]["monitoring_state"] == "READY_TO_START_FIRST_CANARY_WINDOW"
    assert payload["summary"]["first_window_status"] == "AWAIT_FIRST_CANARY_WINDOW_RESULTS"
    assert payload["summary"]["current_hold_precision"] is None


def test_render_checkpoint_pa8_nas100_action_only_canary_monitoring_packet_markdown_contains_triggers() -> None:
    markdown = render_checkpoint_pa8_nas100_action_only_canary_monitoring_packet_markdown(
        {
            "summary": {
                "monitoring_state": "READY_TO_START_FIRST_CANARY_WINDOW",
                "first_window_status": "AWAIT_FIRST_CANARY_WINDOW_RESULTS",
                "recommended_next_action": "start_collecting_first_canary_window_observations",
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.945946,
            },
            "tracked_metrics": ["hold_precision"],
            "monitoring_questions": ["Does hold_precision remain above the baseline once the canary is observed live?"],
            "success_criteria": ["hold_precision stays above baseline"],
            "fail_fast_triggers": ["hold_precision_drop_below_baseline"],
        }
    )

    assert "# PA8 NAS100 Action-Only Canary Monitoring Packet" in markdown
    assert "- `hold_precision`" in markdown
    assert "- `hold_precision_drop_below_baseline`" in markdown
