from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_canary_review_packet import main


def test_build_checkpoint_pa8_action_canary_review_packet_writes_outputs(tmp_path: Path) -> None:
    pa8_packet = tmp_path / "pa8_packet.json"
    nas100_review = tmp_path / "nas100_review.json"
    preview = tmp_path / "preview.json"
    json_output = tmp_path / "canary_packet.json"
    markdown_output = tmp_path / "canary_packet.md"

    pa8_packet.write_text(
        json.dumps(
            {
                "summary": {
                    "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                    "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                    "action_baseline_review_ready": True,
                },
                "symbol_rows": [{"symbol": "NAS100", "review_state": "PRIMARY_REVIEW"}],
            }
        ),
        encoding="utf-8",
    )
    nas100_review.write_text(
        json.dumps({"summary": {"symbol": "NAS100", "review_result": "narrow_hold_boundary_candidate_identified"}}),
        encoding="utf-8",
    )
    preview.write_text(
        json.dumps(
            {
                "summary": {
                    "eligible_row_count": 82,
                    "preview_changed_row_count": 82,
                    "improved_row_count": 82,
                    "worsened_row_count": 0,
                    "baseline_hold_precision": 0.759036,
                    "preview_hold_precision": 0.945946,
                    "baseline_runtime_proxy_match_rate": 0.941077,
                    "preview_runtime_proxy_match_rate": 0.964195,
                    "baseline_partial_then_hold_quality": 0.971302,
                    "preview_partial_then_hold_quality": 0.975701,
                }
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--pa8-action-review-packet-path",
            str(pa8_packet),
            "--nas100-symbol-review-path",
            str(nas100_review),
            "--nas100-preview-path",
            str(preview),
            "--json-output-path",
            str(json_output),
            "--markdown-output-path",
            str(markdown_output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["provisional_canary_ready"] is True
    assert payload["summary"]["recommended_next_action"] == "prepare_nas100_action_only_provisional_canary_scope"
    assert markdown_output.exists()
