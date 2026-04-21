import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_scene_eval.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_scene_eval", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_scene_eval_script_writes_json(tmp_path: Path) -> None:
    scene_dataset_path = tmp_path / "checkpoint_scene_dataset.csv"
    json_output_path = tmp_path / "checkpoint_scene_eval_latest.json"
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
                "unrealized_pnl_state": "FLAT",
                "runner_secured": False,
                "current_profit": 0.0,
                "mfe_since_entry": 0.0,
                "mae_since_entry": 0.0,
                "giveback_ratio": 0.0,
                "runtime_scene_coarse_family": "ENTRY_INITIATION",
                "runtime_scene_fine_label": "breakout_retest_hold",
                "runtime_scene_gate_label": "none",
                "runtime_scene_modifier_json": "{\"reclaim\":true}",
                "runtime_scene_confidence": 0.82,
                "runtime_scene_confidence_band": "high",
                "runtime_scene_action_bias_strength": "medium",
                "runtime_scene_source": "heuristic_v1",
                "runtime_scene_maturity": "confirmed",
                "runtime_scene_transition_from": "unresolved",
                "runtime_scene_transition_bars": 0,
                "runtime_scene_transition_speed": "fast",
                "runtime_scene_family_alignment": "aligned",
                "runtime_scene_gate_block_level": "none",
                "hindsight_scene_fine_label": "breakout_retest_hold",
                "hindsight_scene_quality_tier": "auto_high",
                "hindsight_scene_label_source": "scene_bootstrap_v1",
                "hindsight_scene_confidence": 0.82,
                "hindsight_scene_reason": "scene_bootstrap_breakout_retest_confirmation",
                "hindsight_scene_resolution_state": "bootstrap_confirmed",
                "runtime_hindsight_scene_match": True,
                "runtime_proxy_management_action_label": "REBUY",
                "hindsight_best_management_action_label": "REBUY",
            }
        ]
    ).to_csv(scene_dataset_path, index=False, encoding="utf-8-sig")

    rc = module.main(
        [
            "--scene-dataset-path",
            str(scene_dataset_path),
            "--json-output-path",
            str(json_output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["resolved_row_count"] == 1
    assert payload["summary"]["runtime_hindsight_scene_match_rate"] == 1.0
    nas_row = next(row for row in payload["rows"] if row["symbol"] == "NAS100")
    assert nas_row["hindsight_scene_resolved_row_count"] == 1
