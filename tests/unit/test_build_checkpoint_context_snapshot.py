import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_context_snapshot.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_context_snapshot", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_context_snapshot_script_writes_latest_json(tmp_path: Path) -> None:
    runtime_status_path = tmp_path / "runtime_status.json"
    runtime_status_path.write_text(
        json.dumps({"updated_at": "2026-04-10T13:08:00+09:00"}, ensure_ascii=False),
        encoding="utf-8",
    )
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T13:05:00+09:00",
                "source": "entry_runtime",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "runner_secured": False,
                "unrealized_pnl_state": "FLAT",
                "checkpoint_id": "BTC_CP001",
            },
            {
                "generated_at": "2026-04-10T13:06:00+09:00",
                "source": "exit_manage",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "runner_secured": True,
                "unrealized_pnl_state": "OPEN_PROFIT",
                "checkpoint_id": "XAU_CP004",
            },
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    json_output_path = tmp_path / "checkpoint_context_snapshot_latest.json"

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
    assert payload["summary"]["runner_secured_count"] == 1
    assert {row["symbol"] for row in payload["rows"]} == {"BTCUSD", "NAS100", "XAUUSD"}
