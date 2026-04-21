from __future__ import annotations

import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_canary_first_window_observation import main


def test_build_checkpoint_pa8_action_canary_first_window_observation_writes_outputs(tmp_path: Path) -> None:
    activation_apply = tmp_path / "activation_apply.json"
    preview = tmp_path / "preview.json"
    resolved_csv = tmp_path / "resolved.csv"
    json_output = tmp_path / "window.json"
    markdown_output = tmp_path / "window.md"

    activation_apply.write_text(
        json.dumps(
            {
                "summary": {
                    "symbol": "NAS100",
                    "active": True,
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "baseline_hold_precision": 0.75,
                    "baseline_runtime_proxy_match_rate": 0.94,
                    "baseline_partial_then_hold_quality": 0.97,
                },
                "active_state": {"activated_at": "2026-04-11T10:00:00+09:00", "guardrails": {}},
            }
        ),
        encoding="utf-8",
    )
    preview.write_text(
        json.dumps(
            {
                "summary": {
                    "preview_changed_row_count": 82,
                    "preview_hold_precision": 0.94,
                    "preview_runtime_proxy_match_rate": 0.96,
                    "preview_partial_then_hold_quality": 0.97,
                    "worsened_row_count": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    resolved_csv.write_text("symbol,generated_at\n", encoding="utf-8")

    exit_code = main(
        [
            "--activation-apply-path",
            str(activation_apply),
            "--preview-path",
            str(preview),
            "--resolved-dataset-path",
            str(resolved_csv),
            "--json-output-path",
            str(json_output),
            "--markdown-output-path",
            str(markdown_output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["first_window_status"] == "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS"
    assert markdown_output.exists()
