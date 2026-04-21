from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_preview import main


def test_build_checkpoint_pa8_action_preview_writes_outputs(tmp_path: Path) -> None:
    resolved_path = tmp_path / "resolved.csv"
    json_output_path = tmp_path / "preview.json"
    markdown_output_path = tmp_path / "preview.md"

    with resolved_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "symbol",
                "checkpoint_id",
                "surface_name",
                "checkpoint_type",
                "checkpoint_rule_family_hint",
                "runtime_proxy_management_action_label",
                "hindsight_best_management_action_label",
                "unrealized_pnl_state",
                "current_profit",
                "runtime_hold_quality_score",
                "runtime_partial_exit_ev",
                "runtime_full_exit_risk",
                "runtime_continuation_odds",
                "runtime_reversal_odds",
                "giveback_ratio",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "NAS100",
                "checkpoint_id": "CP1",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "current_profit": "0.12",
                "runtime_hold_quality_score": "0.53",
                "runtime_partial_exit_ev": "0.57",
                "runtime_full_exit_risk": "0.19",
                "runtime_continuation_odds": "0.84",
                "runtime_reversal_odds": "0.47",
                "giveback_ratio": "0.0",
            }
        )

    exit_code = main(
        [
            "--resolved-dataset-path",
            str(resolved_path),
            "--json-output-path",
            str(json_output_path),
            "--markdown-output-path",
            str(markdown_output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["eligible_row_count"] == 1
    assert markdown_output_path.exists()
    assert "PA8 NAS100 Profit Hold Bias Action Preview" in markdown_output_path.read_text(encoding="utf-8")
