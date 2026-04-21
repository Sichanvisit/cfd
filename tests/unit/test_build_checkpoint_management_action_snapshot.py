import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_management_action_snapshot.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_management_action_snapshot", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_management_action_snapshot_script_writes_latest_json(tmp_path: Path) -> None:
    runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    runtime_status_detail_path.write_text(
        json.dumps({"updated_at": "2026-04-10T14:40:00+09:00"}, ensure_ascii=False),
        encoding="utf-8",
    )
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T14:30:00+09:00",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_id": "BTC_L1_CP003",
                "checkpoint_type": "RUNNER_CHECK",
                "position_side": "BUY",
                "position_size_fraction": 0.5,
                "runner_secured": True,
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runtime_continuation_odds": 0.64,
                "runtime_reversal_odds": 0.26,
                "runtime_hold_quality_score": 0.59,
                "runtime_partial_exit_ev": 0.74,
                "runtime_full_exit_risk": 0.22,
                "runtime_rebuy_readiness": 0.22,
            }
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    json_output_path = tmp_path / "checkpoint_management_action_snapshot_latest.json"

    rc = module.main(
        [
            "--runtime-status-detail-path",
            str(runtime_status_detail_path),
            "--checkpoint-rows-path",
            str(checkpoint_rows_path),
            "--json-output-path",
            str(json_output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["resolved_row_count"] == 1
    assert payload["summary"]["management_action_counts"]["PARTIAL_THEN_HOLD"] == 1
