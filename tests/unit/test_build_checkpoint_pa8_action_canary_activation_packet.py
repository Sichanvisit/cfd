from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_canary_activation_packet import main


def test_build_checkpoint_pa8_action_canary_activation_packet_writes_outputs(tmp_path: Path) -> None:
    execution_checklist = tmp_path / "execution_checklist.json"
    review_packet = tmp_path / "review_packet.json"
    json_output = tmp_path / "activation_packet.json"
    markdown_output = tmp_path / "activation_packet.md"

    execution_checklist.write_text(
        json.dumps(
            {
                "summary": {
                    "symbol": "NAS100",
                    "execution_state": "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION",
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
                    "blockers": [],
                },
                "scope_snapshot": {
                    "symbol_allowlist": ["NAS100"],
                    "surface_allowlist": ["continuation_hold_surface"],
                    "checkpoint_type_allowlist": ["RUNNER_CHECK"],
                    "family_allowlist": ["profit_hold_bias"],
                    "baseline_action_allowlist": ["HOLD"],
                    "preview_action": "PARTIAL_THEN_HOLD",
                    "preview_reason": "nas100_profit_hold_bias_hold_to_partial_then_hold_preview",
                    "change_mode": "action_only_preview_candidate",
                },
                "guardrail_snapshot": {"sample_floor": 50},
                "execution_steps": [{"step_id": "preflight", "status": "ready"}],
            }
        ),
        encoding="utf-8",
    )
    review_packet.write_text(
        json.dumps(
            {
                "summary": {
                    "canary_review_state": "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW",
                    "provisional_canary_ready": True,
                }
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--execution-checklist-path",
            str(execution_checklist),
            "--canary-review-packet-path",
            str(review_packet),
            "--json-output-path",
            str(json_output),
            "--markdown-output-path",
            str(markdown_output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["allow_activation"] is True
    assert payload["summary"]["activation_state"] == "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW"
    assert markdown_output.exists()
