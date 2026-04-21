import json
from pathlib import Path

import pandas as pd

from scripts.build_checkpoint_scene_sanity_check import main


def test_build_checkpoint_scene_sanity_check_writes_artifact(tmp_path: Path) -> None:
    csv_path = tmp_path / "checkpoint_rows.csv"
    json_path = tmp_path / "checkpoint_scene_sanity_latest.json"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T13:00:00+09:00",
                "symbol": "NAS100",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "runtime_continuation_odds": 0.74,
                "runtime_reversal_odds": 0.44,
                "runtime_hold_quality_score": 0.50,
                "runtime_partial_exit_ev": 0.35,
                "runtime_full_exit_risk": 0.20,
                "runtime_rebuy_readiness": 0.42,
                "runtime_score_reason": "continuation_hold_surface::continuation_hold_bias",
                "setup_reason": "breakout retest reclaim hold",
                "observe_action": "BUY",
                "observe_side": "BUY",
            }
        ]
    ).to_csv(csv_path, index=False, encoding="utf-8-sig")

    exit_code = main(
        [
            "--checkpoint-rows-path",
            str(csv_path),
            "--json-output-path",
            str(json_path),
            "--recent-limit",
            "50",
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["row_count"] == 1
    assert payload["summary"]["scene_filled_row_count"] == 1
    nas_row = next(row for row in payload["rows"] if row["symbol"] == "NAS100")
    assert nas_row["top_fine_label"] == "breakout_retest_hold"
