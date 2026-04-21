from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_canary_closeout_decision import main


def test_build_checkpoint_pa8_action_canary_closeout_decision_writes_outputs(tmp_path: Path) -> None:
    activation_apply = tmp_path / "activation_apply.json"
    observation = tmp_path / "observation.json"
    rollback = tmp_path / "rollback.json"
    json_output = tmp_path / "closeout.json"
    markdown_output = tmp_path / "closeout.md"

    activation_apply.write_text(
        json.dumps(
            {
                "summary": {"symbol": "NAS100", "active": True, "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY"},
                "active_state": {"guardrails": {"sample_floor": 50}},
            }
        ),
        encoding="utf-8",
    )
    observation.write_text(
        json.dumps(
            {
                "summary": {
                    "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                    "live_observation_ready": False,
                    "observed_window_row_count": 0,
                    "new_worsened_rows": 0,
                },
                "active_triggers": [],
            }
        ),
        encoding="utf-8",
    )
    rollback.write_text(
        json.dumps({"summary": {"rollback_review_state": "READY_WITH_NO_TRIGGER_ACTIVE"}}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--activation-apply-path",
            str(activation_apply),
            "--first-window-observation-path",
            str(observation),
            "--rollback-review-path",
            str(rollback),
            "--json-output-path",
            str(json_output),
            "--markdown-output-path",
            str(markdown_output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["closeout_state"] == "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW"
    assert markdown_output.exists()
