import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_dataset.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_dataset", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_dataset_script_writes_dataset_and_resolved_csv(tmp_path: Path) -> None:
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T14:20:00+09:00",
                "source": "entry_runtime",
                "symbol": "NAS100",
                "surface_name": "follow_through_surface",
                "leg_id": "NAS_L1",
                "leg_direction": "UP",
                "checkpoint_id": "NAS_L1_CP002",
                "checkpoint_type": "RECLAIM_CHECK",
                "checkpoint_index_in_leg": 2,
                "position_side": "FLAT",
                "position_size_fraction": 0.0,
                "avg_entry_price": 0.0,
                "realized_pnl_state": "NONE",
                "unrealized_pnl_state": "FLAT",
                "runner_secured": False,
                "mfe_since_entry": 0.0,
                "mae_since_entry": 0.0,
                "current_profit": 0.0,
                "runtime_continuation_odds": 0.69,
                "runtime_reversal_odds": 0.23,
                "runtime_hold_quality_score": 0.15,
                "runtime_partial_exit_ev": 0.04,
                "runtime_full_exit_risk": 0.08,
                "runtime_rebuy_readiness": 0.75,
                "runtime_score_reason": "follow_through_surface::pullback_reentry_ready",
            }
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    dataset_output_path = tmp_path / "checkpoint_dataset.csv"
    resolved_output_path = tmp_path / "checkpoint_dataset_resolved.csv"

    rc = module.main(
        [
            "--checkpoint-rows-path",
            str(checkpoint_rows_path),
            "--dataset-output-path",
            str(dataset_output_path),
            "--resolved-output-path",
            str(resolved_output_path),
        ]
    )

    assert rc == 0
    dataset = pd.read_csv(dataset_output_path, encoding="utf-8-sig")
    resolved = pd.read_csv(resolved_output_path, encoding="utf-8-sig")
    assert len(dataset) == 1
    assert resolved.iloc[0]["hindsight_best_management_action_label"] == "REBUY"
