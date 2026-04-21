from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.build_checkpoint_pa7_review_queue_packet import main


def test_build_checkpoint_pa7_review_queue_packet_writes_output(tmp_path: Path) -> None:
    resolved_path = tmp_path / "resolved.csv"
    output_path = tmp_path / "packet.json"
    pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "open_loss_protective",
                "management_action_label": "WAIT",
                "hindsight_best_management_action_label": "FULL_EXIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
            }
        ]
    ).to_csv(resolved_path, index=False, encoding="utf-8-sig")

    exit_code = main(
        [
            "--resolved-dataset-path",
            str(resolved_path),
            "--json-output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["manual_exception_row_count"] == 1
