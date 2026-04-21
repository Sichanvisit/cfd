import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_distribution.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_distribution", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_distribution_script_writes_latest_json(tmp_path: Path) -> None:
    runtime_status_path = tmp_path / "runtime_status.json"
    runtime_status_path.write_text(
        json.dumps(
            {
                "updated_at": "2026-04-10T12:45:00+09:00",
                "latest_signal_by_symbol": {
                    "BTCUSD": {"symbol": "BTCUSD", "time": "2026-04-10T12:41:04+09:00"},
                    "NAS100": {"symbol": "NAS100", "time": "2026-04-10T12:41:02+09:00"},
                    "XAUUSD": {"symbol": "XAUUSD", "time": "2026-04-10T12:41:03+09:00"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    entry_decisions_path = tmp_path / "entry_decisions.csv"
    pd.DataFrame(
        [
            {
                "time": "2026-04-10T12:40:43+09:00",
                "symbol": "BTCUSD",
                "outcome": "wait",
                "observe_action": "WAIT",
                "observe_side": "BUY",
                "breakout_candidate_direction": "UP",
            },
            {
                "time": "2026-04-10T12:40:47+09:00",
                "symbol": "NAS100",
                "outcome": "skipped",
                "blocked_by": "energy_soft_block",
                "observe_action": "SELL",
                "observe_side": "SELL",
                "breakout_candidate_direction": "UP",
            },
            {
                "time": "2026-04-10T12:40:52+09:00",
                "symbol": "XAUUSD",
                "outcome": "wait",
                "blocked_by": "active_action_conflict_guard",
                "observe_action": "SELL",
                "observe_side": "SELL",
                "entry_candidate_bridge_selected": True,
                "entry_candidate_bridge_action": "BUY",
                "breakout_candidate_direction": "UP",
                "active_action_conflict_guard_applied": True,
            },
        ]
    ).to_csv(entry_decisions_path, index=False, encoding="utf-8-sig")
    json_output_path = tmp_path / "checkpoint_distribution_latest.json"

    rc = module.main(
        [
            "--runtime-status-path",
            str(runtime_status_path),
            "--entry-decisions-path",
            str(entry_decisions_path),
            "--recent-limit",
            "20",
            "--json-output-path",
            str(json_output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["checkpoint_count"] >= 3
    assert {row["symbol"] for row in payload["rows"]} == {"BTCUSD", "NAS100", "XAUUSD"}
