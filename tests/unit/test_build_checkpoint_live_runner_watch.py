import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_live_runner_watch.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_live_runner_watch", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_checkpoint_live_runner_watch_script_writes_json(tmp_path: Path) -> None:
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T15:57:00+09:00",
                "symbol": "NAS100",
                "source": "exit_manage_runner",
                "outcome": "runner_hold",
                "blocked_by": "runner_observe:no_exit",
            }
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    runtime_status_detail_path.write_text(json.dumps({"updated_at": "2026-04-10T15:58:00+09:00"}), encoding="utf-8")
    json_output_path = tmp_path / "checkpoint_live_runner_watch_latest.json"

    rc = module.main(
        [
            "--runtime-status-detail-path",
            str(runtime_status_detail_path),
            "--checkpoint-rows-path",
            str(checkpoint_rows_path),
            "--json-output-path",
            str(json_output_path),
            "--iterations",
            "1",
            "--recent-minutes",
            "60",
        ]
    )

    assert rc == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["live_runner_source_row_count"] == 1
    assert payload["summary"]["last_live_runner_symbol"] == "NAS100"
