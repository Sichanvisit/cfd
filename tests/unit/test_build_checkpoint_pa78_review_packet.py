from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa78_review_packet import main


def test_build_checkpoint_pa78_review_packet_writes_summary(tmp_path: Path) -> None:
    action_eval = tmp_path / "action_eval.json"
    observation = tmp_path / "observation.json"
    live_runner = tmp_path / "live_runner.json"
    pa7_review_processor = tmp_path / "pa7_review_processor.json"
    scene_disagreement = tmp_path / "scene_disagreement.json"
    scene_preview = tmp_path / "scene_preview.json"
    output_path = tmp_path / "review_packet.json"

    action_eval.write_text(
        json.dumps(
            {
                "summary": {
                    "resolved_row_count": 4477,
                    "runtime_proxy_match_rate": 0.92182,
                    "hold_precision": 0.847619,
                    "partial_then_hold_quality": 0.953634,
                    "full_exit_precision": 0.996616,
                    "manual_exception_count": 1089,
                }
            }
        ),
        encoding="utf-8",
    )
    observation.write_text(
        json.dumps({"summary": {"position_side_row_count": 4474, "source_counts": {"exit_manage_runner": 1138}}}),
        encoding="utf-8",
    )
    live_runner.write_text(
        json.dumps({"summary": {"live_runner_source_row_count": 1138, "recent_live_runner_source_row_count": 117}}),
        encoding="utf-8",
    )
    pa7_review_processor.write_text(
        json.dumps(
            {
                "summary": {
                    "processed_group_count": 12,
                    "review_disposition_counts": {"resolved_by_current_policy": 12},
                    "recommended_next_action": "record_resolved_by_current_policy_groups_and_continue_pa7",
                }
            }
        ),
        encoding="utf-8",
    )
    scene_disagreement.write_text(
        json.dumps({"summary": {"high_conf_scene_disagreement_count": 1025, "expected_action_alignment_rate": 0.906341}}),
        encoding="utf-8",
    )
    scene_preview.write_text(
        json.dumps(
            {
                "summary": {
                    "preview_changed_row_count": 4,
                    "improved_row_count": 4,
                    "worsened_row_count": 0,
                    "baseline_hindsight_match_rate": 0.969663,
                    "preview_hindsight_match_rate": 0.974157,
                }
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--action-eval-path",
            str(action_eval),
            "--observation-path",
            str(observation),
            "--live-runner-watch-path",
            str(live_runner),
            "--pa7-review-processor-path",
            str(pa7_review_processor),
            "--scene-disagreement-path",
            str(scene_disagreement),
            "--scene-bias-preview-path",
            str(scene_preview),
            "--json-output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["pa7_review_state"] == "REVIEW_PACKET_PROCESSED"
    assert payload["summary"]["pa8_review_state"] == "READY_FOR_ACTION_BASELINE_REVIEW"
