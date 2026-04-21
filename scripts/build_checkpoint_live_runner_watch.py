"""Build or poll a live watch artifact for exit_manage_runner checkpoint growth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_context import (  # noqa: E402
    default_checkpoint_rows_path,
)
from backend.services.path_checkpoint_live_runner_watch import (  # noqa: E402
    build_checkpoint_live_runner_watch,
    default_checkpoint_live_runner_watch_path,
)
from backend.services.path_checkpoint_open_trade_backfill import (  # noqa: E402
    default_runtime_status_detail_path,
)


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-status-detail-path", default=str(default_runtime_status_detail_path()))
    parser.add_argument("--checkpoint-rows-path", default=str(default_checkpoint_rows_path()))
    parser.add_argument("--json-output-path", default=str(default_checkpoint_live_runner_watch_path()))
    parser.add_argument("--recent-minutes", type=int, default=30)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=float, default=5.0)
    args = parser.parse_args(argv)

    json_output_path = Path(args.json_output_path)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    previous_payload = _load_json(json_output_path)
    latest_payload: dict[str, object] = {}
    total_iterations = max(1, int(args.iterations))

    for iteration in range(total_iterations):
        rows, summary = build_checkpoint_live_runner_watch(
            _load_json(args.runtime_status_detail_path),
            _load_csv(args.checkpoint_rows_path),
            previous_summary=dict(previous_payload.get("summary", {}) or {}),
            recent_minutes=max(1, int(args.recent_minutes)),
        )
        latest_payload = {
            "summary": summary,
            "rows": rows.to_dict(orient="records"),
        }
        print(
            json.dumps(
                {
                    "iteration": iteration + 1,
                    "iterations": total_iterations,
                    "json_output_path": str(json_output_path),
                    **summary,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        previous_payload = latest_payload
        if iteration + 1 < total_iterations:
            time.sleep(max(0.0, float(args.sleep_seconds)))

    json_output_path.write_text(json.dumps(latest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
