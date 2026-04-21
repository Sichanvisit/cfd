from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.build_checkpoint_pa8_action_symbol_review import main


def test_build_checkpoint_pa8_action_symbol_review_writes_outputs(tmp_path: Path) -> None:
    checklist_path = tmp_path / "checklist.json"
    resolved_path = tmp_path / "resolved.csv"
    json_output_path = tmp_path / "nas100_review.json"
    markdown_output_path = tmp_path / "nas100_review.md"

    checklist_path.write_text(
        json.dumps(
            {
                "checklist_rows": [
                    {
                        "symbol": "NAS100",
                        "review_state": "PRIMARY_REVIEW",
                        "goal": "Confirm whether the HOLD boundary for NAS100 is actually correct against hindsight outcomes.",
                        "blockers": ["hold_precision_below_symbol_floor"],
                        "pass_criteria": ["Raise hold_precision to at least 0.80."],
                        "review_focuses": ["inspect_hold_precision_boundary"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with resolved_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "symbol",
                "surface_name",
                "checkpoint_type",
                "checkpoint_rule_family_hint",
                "management_action_label",
                "hindsight_best_management_action_label",
                "management_action_reason",
                "source",
                "current_profit",
                "runtime_hold_quality_score",
                "runtime_partial_exit_ev",
                "runtime_continuation_odds",
                "runtime_reversal_odds",
                "checkpoint_id",
                "hindsight_quality_tier",
                "position_side",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "management_action_label": "HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "management_action_reason": "runner_family_hold_bias",
                "source": "exit_manage_hold",
                "current_profit": "0.12",
                "runtime_hold_quality_score": "0.53",
                "runtime_partial_exit_ev": "0.57",
                "runtime_continuation_odds": "0.84",
                "runtime_reversal_odds": "0.47",
                "checkpoint_id": "CP001",
                "hindsight_quality_tier": "manual_exception",
                "position_side": "LONG",
            }
        )

    exit_code = main(
        [
            "--symbol",
            "NAS100",
            "--pa8-checklist-path",
            str(checklist_path),
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
    assert payload["summary"]["review_result"] == "narrow_hold_boundary_candidate_identified"
    assert markdown_output_path.exists()
    assert "### 1. profit_hold_bias" in markdown_output_path.read_text(encoding="utf-8")
