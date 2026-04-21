import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_eval.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_eval", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_eval_script_writes_latest_json(tmp_path: Path) -> None:
    resolved_path = tmp_path / "checkpoint_dataset_resolved.csv"
    pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "position_side": "BUY",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "HOLD",
                "hindsight_manual_exception_required": False,
                "runtime_hindsight_match": True,
                "runner_capture_eligible": True,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "auto_high",
            },
            {
                "symbol": "XAUUSD",
                "surface_name": "protective_exit_surface",
                "position_side": "BUY",
                "runtime_proxy_management_action_label": "FULL_EXIT",
                "hindsight_best_management_action_label": "FULL_EXIT",
                "hindsight_manual_exception_required": False,
                "runtime_hindsight_match": True,
                "runner_capture_eligible": False,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "auto_high",
            },
        ]
    ).to_csv(resolved_path, index=False, encoding="utf-8-sig")
    json_output_path = tmp_path / "checkpoint_action_eval_latest.json"

    rc = module.main(
        [
            "--resolved-dataset-path",
            str(resolved_path),
            "--json-output-path",
            str(json_output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["resolved_row_count"] == 2
    assert payload["summary"]["full_exit_precision"] == 1.0
    assert {row["symbol"] for row in payload["rows"]} == {"BTCUSD", "NAS100", "XAUUSD"}
