from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_canary_activation_review import main


def test_build_checkpoint_pa8_action_canary_activation_review_writes_outputs(tmp_path: Path) -> None:
    activation_packet = tmp_path / "activation_packet.json"
    json_output = tmp_path / "activation_review.json"
    markdown_output = tmp_path / "activation_review.md"

    activation_packet.write_text(
        json.dumps(
            {
                "summary": {
                    "symbol": "NAS100",
                    "activation_state": "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW",
                    "allow_activation": True,
                    "blockers": [],
                },
                "activation_scope": {"symbol_allowlist": ["NAS100"]},
                "activation_guardrails": {},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--activation-packet-path",
            str(activation_packet),
            "--json-output-path",
            str(json_output),
            "--markdown-output-path",
            str(markdown_output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["review_state"] == "READY_FOR_HUMAN_ACTIVATION_DECISION"
    assert markdown_output.exists()
