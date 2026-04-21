from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_canary_rollback_review_packet import main


def test_build_checkpoint_pa8_action_canary_rollback_review_packet_writes_outputs(tmp_path: Path) -> None:
    activation_packet = tmp_path / "activation_packet.json"
    monitoring_packet = tmp_path / "monitoring_packet.json"
    json_output = tmp_path / "rollback_packet.json"
    markdown_output = tmp_path / "rollback_packet.md"

    activation_packet.write_text(
        json.dumps(
            {
                "summary": {
                    "symbol": "NAS100",
                    "activation_state": "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW",
                    "allow_activation": True,
                    "blockers": [],
                },
                "activation_guardrails": {
                    "rollback_watch_metrics": ["hold_precision_drop_below_baseline"],
                },
            }
        ),
        encoding="utf-8",
    )
    monitoring_packet.write_text(
        json.dumps({"summary": {"monitoring_state": "READY_TO_START_FIRST_CANARY_WINDOW"}}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--activation-packet-path",
            str(activation_packet),
            "--monitoring-packet-path",
            str(monitoring_packet),
            "--json-output-path",
            str(json_output),
            "--markdown-output-path",
            str(markdown_output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["rollback_review_state"] == "READY_WITH_NO_TRIGGER_ACTIVE"
    assert markdown_output.exists()
