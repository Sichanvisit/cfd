"""Backfill open-trade position-side checkpoint rows for PA5 enrichment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_context import (  # noqa: E402
    default_checkpoint_detail_path,
    default_checkpoint_rows_path,
)
from backend.services.path_checkpoint_open_trade_backfill import (  # noqa: E402
    backfill_open_trade_checkpoint_rows,
    default_checkpoint_open_trade_backfill_artifact_path,
    default_runtime_status_detail_path,
    default_trade_db_path,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-status-detail-path", default=str(default_runtime_status_detail_path()))
    parser.add_argument("--trade-db-path", default=str(default_trade_db_path()))
    parser.add_argument("--checkpoint-rows-path", default=str(default_checkpoint_rows_path()))
    parser.add_argument("--checkpoint-detail-path", default=str(default_checkpoint_detail_path()))
    parser.add_argument("--json-output-path", default=str(default_checkpoint_open_trade_backfill_artifact_path()))
    args = parser.parse_args(argv)

    payload = backfill_open_trade_checkpoint_rows(
        runtime_status_detail_path=args.runtime_status_detail_path,
        trade_db_path=args.trade_db_path,
        checkpoint_rows_path=args.checkpoint_rows_path,
        checkpoint_detail_path=args.checkpoint_detail_path,
    )
    json_output_path = Path(args.json_output_path)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"json_output_path": str(json_output_path), **dict(payload.get("summary", {}) or {})}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
