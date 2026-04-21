from __future__ import annotations

from backend.services.path_checkpoint_pa78_review_packet import build_checkpoint_pa78_review_packet


def test_build_checkpoint_pa78_review_packet_marks_pa7_ready_but_pa8_hold_for_preview_only() -> None:
    payload = build_checkpoint_pa78_review_packet(
        action_eval_payload={
            "summary": {
                "resolved_row_count": 4477,
                "runtime_proxy_match_rate": 0.92182,
                "hold_precision": 0.847619,
                "partial_then_hold_quality": 0.953634,
                "full_exit_precision": 0.996616,
                "manual_exception_count": 1089,
            }
        },
        observation_payload={
            "summary": {
                "position_side_row_count": 4474,
                "open_profit_row_count": 1747,
                "open_loss_row_count": 2655,
                "runner_secured_row_count": 1323,
                "source_counts": {"exit_manage_runner": 1138},
                "family_counts": {"runner_secured_continuation": 1323},
            }
        },
        live_runner_watch_payload={
            "summary": {
                "live_runner_source_row_count": 1138,
                "recent_live_runner_source_row_count": 117,
            }
        },
        pa7_review_processor_payload={
            "summary": {
                "processed_group_count": 12,
                "review_disposition_counts": {
                    "resolved_by_current_policy": 12,
                },
                "recommended_next_action": "record_resolved_by_current_policy_groups_and_continue_pa7",
            }
        },
        scene_disagreement_payload={
            "summary": {
                "high_conf_scene_disagreement_count": 1025,
                "expected_action_alignment_rate": 0.906341,
                "candidate_selected_label_counts": {"trend_exhaustion": 907},
            }
        },
        scene_bias_preview_payload={
            "summary": {
                "preview_changed_row_count": 4,
                "improved_row_count": 4,
                "worsened_row_count": 0,
                "baseline_hindsight_match_rate": 0.969663,
                "preview_hindsight_match_rate": 0.974157,
                "recommended_next_action": "keep_trend_exhaustion_scene_bias_preview_only",
            }
        },
    )

    summary = payload["summary"]
    assert summary["pa7_review_state"] == "REVIEW_PACKET_PROCESSED"
    assert summary["pa8_review_state"] == "READY_FOR_ACTION_BASELINE_REVIEW"
    assert summary["scene_bias_review_state"] == "HOLD_PREVIEW_ONLY_SCENE_BIAS"
    assert summary["action_baseline_review_ready"] is True
    assert summary["scene_bias_review_ready"] is False
    assert "trend_exhaustion_scene_bias_preview_only" in summary["blockers"]
    assert summary["recommended_next_action"] == "prepare_pa8_action_baseline_review_and_keep_scene_bias_preview_only"
