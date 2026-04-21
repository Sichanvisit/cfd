import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_position_side_observation.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_position_side_observation", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_position_side_observation_script_writes_json(tmp_path: Path) -> None:
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T14:30:00+09:00",
                "symbol": "NAS100",
                "source": "exit_manage_hold",
                "position_side": "SELL",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": False,
                "management_action_label": "PARTIAL_THEN_HOLD",
            }
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    json_output_path = tmp_path / "checkpoint_position_side_observation_latest.json"

    rc = module.main(
        [
            "--checkpoint-rows-path",
            str(checkpoint_rows_path),
            "--json-output-path",
            str(json_output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["position_side_row_count"] == 1
