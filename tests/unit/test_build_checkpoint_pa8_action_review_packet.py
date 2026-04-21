from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_review_packet import main


def test_build_checkpoint_pa8_action_review_packet_writes_summary(tmp_path: Path) -> None:
    pa78 = tmp_path / "pa78.json"
    action_eval = tmp_path / "action_eval.json"
    management = tmp_path / "management.json"
    observation = tmp_path / "observation.json"
    live_runner = tmp_path / "live_runner.json"
    output_path = tmp_path / "pa8_action_review.json"

    pa78.write_text(
        json.dumps(
            {
                "summary": {
                    "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                    "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                    "action_baseline_review_ready": True,
                    "recommended_next_action": "prepare_pa8_action_baseline_review_and_keep_scene_bias_preview_only",
                }
            }
        ),
        encoding="utf-8",
    )
    action_eval.write_text(
        json.dumps(
            {
                "summary": {
                    "resolved_row_count": 5385,
                    "runtime_proxy_match_rate": 0.92182,
                    "hold_precision": 0.848057,
                    "partial_then_hold_quality": 0.953634,
                    "full_exit_precision": 0.998647,
                },
                "rows": [
                    {
                        "symbol": "BTCUSD",
                        "resolved_row_count": 1434,
                        "runtime_proxy_match_rate": 0.889121,
                        "hold_precision": 0.944984,
                        "partial_then_hold_quality": 0.93,
                        "full_exit_precision": 0.997455,
                    },
                    {
                        "symbol": "NAS100",
                        "resolved_row_count": 3547,
                        "runtime_proxy_match_rate": 0.941077,
                        "hold_precision": 0.759036,
                        "partial_then_hold_quality": 0.971302,
                        "full_exit_precision": 1.0,
                    },
                    {
                        "symbol": "XAUUSD",
                        "resolved_row_count": 404,
                        "runtime_proxy_match_rate": 0.868812,
                        "hold_precision": 0.904,
                        "partial_then_hold_quality": 0.933333,
                        "full_exit_precision": 0.976744,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    management.write_text(json.dumps({"rows": []}), encoding="utf-8")
    observation.write_text(
        json.dumps(
            {
                "rows": [
                    {"symbol": "BTCUSD", "live_runner_source_row_count": 573},
                    {"symbol": "NAS100", "live_runner_source_row_count": 515},
                    {"symbol": "XAUUSD", "live_runner_source_row_count": 50},
                ]
            }
        ),
        encoding="utf-8",
    )
    live_runner.write_text(json.dumps({"rows": []}), encoding="utf-8")

    exit_code = main(
        [
            "--pa78-review-packet-path",
            str(pa78),
            "--action-eval-path",
            str(action_eval),
            "--management-snapshot-path",
            str(management),
            "--observation-path",
            str(observation),
            "--live-runner-watch-path",
            str(live_runner),
            "--json-output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["overall_review_state"] == "READY_FOR_HUMAN_ACTION_REVIEW"
    assert payload["summary"]["review_order"] == ["NAS100", "BTCUSD", "XAUUSD"]
