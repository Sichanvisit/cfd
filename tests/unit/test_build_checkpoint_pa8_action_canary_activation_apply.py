from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_canary_activation_apply import main


def test_build_checkpoint_pa8_action_canary_activation_apply_writes_outputs(tmp_path: Path) -> None:
    review_path = tmp_path / "activation_review.json"
    json_output = tmp_path / "activation_apply.json"
    markdown_output = tmp_path / "activation_apply.md"
    active_state_output = tmp_path / "active_state.json"

    review_path.write_text(
        json.dumps(
            {
                "summary": {
                    "symbol": "NAS100",
                    "review_state": "READY_FOR_HUMAN_ACTIVATION_DECISION",
                    "allow_activation": True,
                    "blockers": [],
                },
                "scope_snapshot": {"symbol_allowlist": ["NAS100"]},
                "guardrail_snapshot": {},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--activation-review-path",
            str(review_path),
            "--json-output-path",
            str(json_output),
            "--markdown-output-path",
            str(markdown_output),
            "--active-state-output-path",
            str(active_state_output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["activation_apply_state"] == "ACTIVE_ACTION_ONLY_CANARY"
    assert active_state_output.exists()
    assert markdown_output.exists()
