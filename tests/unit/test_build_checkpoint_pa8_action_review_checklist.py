from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_review_checklist import main


def test_build_checkpoint_pa8_action_review_checklist_writes_json_and_markdown(tmp_path: Path) -> None:
    packet_path = tmp_path / "pa8_action_packet.json"
    json_output_path = tmp_path / "checklist.json"
    markdown_output_path = tmp_path / "checklist.md"

    packet_path.write_text(
        json.dumps(
            {
                "summary": {
                    "overall_review_state": "READY_FOR_HUMAN_ACTION_REVIEW",
                    "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                    "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                    "review_order": ["NAS100", "BTCUSD"],
                    "primary_review_symbols": ["NAS100", "BTCUSD"],
                    "support_review_symbols": [],
                    "recommended_next_action": "review_primary_symbols_then_decide_if_action_only_canary_should_wait",
                    "scene_bias_separation_note": "scene_bias_remains_preview_only_while_pa8_reviews_action_baseline",
                },
                "symbol_rows": [
                    {
                        "symbol": "NAS100",
                        "review_state": "PRIMARY_REVIEW",
                        "review_blockers": ["hold_precision_below_symbol_floor"],
                        "review_focuses": ["inspect_hold_precision_boundary"],
                        "resolved_row_count": 3547,
                        "live_runner_source_row_count": 515,
                        "runtime_proxy_match_rate": 0.941077,
                        "hold_precision": 0.759036,
                        "partial_then_hold_quality": 0.971302,
                        "full_exit_precision": 1.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--pa8-action-review-packet-path",
            str(packet_path),
            "--json-output-path",
            str(json_output_path),
            "--markdown-output-path",
            str(markdown_output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["overall_review_state"] == "READY_FOR_HUMAN_ACTION_REVIEW"
    assert markdown_output_path.exists()
    markdown = markdown_output_path.read_text(encoding="utf-8")
    assert "## 1. NAS100" in markdown
