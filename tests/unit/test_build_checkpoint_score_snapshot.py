import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_score_snapshot.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_score_snapshot", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_score_snapshot_script_writes_latest_json(tmp_path: Path) -> None:
    runtime_status_path = tmp_path / "runtime_status.json"
    runtime_status_path.write_text(
        json.dumps({"updated_at": "2026-04-10T14:12:00+09:00"}, ensure_ascii=False),
        encoding="utf-8",
    )
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T14:05:00+09:00",
                "source": "entry_runtime",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "leg_direction": "UP",
                "checkpoint_id": "BTC_CP001",
                "checkpoint_type": "RECLAIM_CHECK",
                "bars_since_last_checkpoint": 1,
                "position_side": "BUY",
                "position_size_fraction": 0.5,
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": True,
                "mfe_since_entry": 10.0,
                "mae_since_entry": 2.0,
                "observe_action": "BUY",
                "observe_side": "BUY",
                "blocked_by": "active_action_conflict_guard",
            },
            {
                "generated_at": "2026-04-10T14:06:00+09:00",
                "source": "exit_manage",
                "symbol": "NAS100",
                "surface_name": "protective_exit_surface",
                "leg_direction": "UP",
                "checkpoint_id": "NAS_CP004",
                "checkpoint_type": "LATE_TREND_CHECK",
                "bars_since_last_checkpoint": 3,
                "position_side": "BUY",
                "position_size_fraction": 1.0,
                "unrealized_pnl_state": "OPEN_LOSS",
                "runner_secured": False,
                "mfe_since_entry": 1.0,
                "mae_since_entry": 8.0,
                "observe_action": "SELL",
                "observe_side": "SELL",
                "blocked_by": "protective_exit fast_cut adverse_reject",
            },
            {
                "generated_at": "2026-04-10T14:07:00+09:00",
                "source": "entry_runtime",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "leg_direction": "UP",
                "checkpoint_id": "XAU_CP003",
                "checkpoint_type": "RUNNER_CHECK",
                "bars_since_last_checkpoint": 2,
                "position_side": "BUY",
                "position_size_fraction": 0.4,
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": True,
                "mfe_since_entry": 6.0,
                "mae_since_entry": 1.0,
                "observe_action": "BUY",
                "observe_side": "BUY",
                "blocked_by": "",
            },
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    json_output_path = tmp_path / "checkpoint_score_snapshot_latest.json"

    rc = module.main(
        [
            "--runtime-status-path",
            str(runtime_status_path),
            "--checkpoint-rows-path",
            str(checkpoint_rows_path),
            "--recent-limit",
            "20",
            "--json-output-path",
            str(json_output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["score_row_count"] == 3
    assert payload["summary"]["recommended_next_action"] == "proceed_to_pa5_hindsight_label_dataset_eval"
    assert {row["symbol"] for row in payload["rows"]} == {"BTCUSD", "NAS100", "XAUUSD"}
