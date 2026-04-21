from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_canary_execution_checklist import main


def test_build_checkpoint_pa8_action_canary_execution_checklist_writes_outputs(tmp_path: Path) -> None:
    canary_packet = tmp_path / "canary_packet.json"
    json_output = tmp_path / "execution_checklist.json"
    markdown_output = tmp_path / "execution_checklist.md"

    canary_packet.write_text(
        json.dumps(
            {
                "summary": {
                    "symbol": "NAS100",
                    "canary_review_state": "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW",
                    "provisional_canary_ready": True,
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
                    "recommended_next_action": "prepare_nas100_action_only_provisional_canary_scope",
                    "blockers": [],
                },
                "candidate_scope": {"symbol_allowlist": ["NAS100"]},
                "canary_guardrails": {"sample_floor": 50},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--canary-review-packet-path",
            str(canary_packet),
            "--json-output-path",
            str(json_output),
            "--markdown-output-path",
            str(markdown_output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["execution_state"] == "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION"
    assert markdown_output.exists()
