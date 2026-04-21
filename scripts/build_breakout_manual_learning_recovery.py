"""Build replay-backfill recovery windows from breakout manual learning cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.breakout_manual_learning_recovery import (  # noqa: E402
    write_breakout_manual_learning_recovery_queue,
)


def _default_learning_bridge_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_learning_bridge_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_learning_recovery_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_learning_recovery_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_learning_recovery_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learning-bridge-path", default=str(_default_learning_bridge_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--pad-before-minutes", type=int, default=15)
    parser.add_argument("--pad-after-minutes", type=int, default=15)
    parser.add_argument("--merge-gap-minutes", type=int, default=5)
    parser.add_argument("--fallback-minutes", type=int, default=20)
    args = parser.parse_args()

    payload = write_breakout_manual_learning_recovery_queue(
        learning_bridge_path=Path(args.learning_bridge_path),
        csv_output_path=Path(args.csv_output_path),
        json_output_path=Path(args.json_output_path),
        markdown_output_path=Path(args.md_output_path),
        pad_before_minutes=int(args.pad_before_minutes),
        pad_after_minutes=int(args.pad_after_minutes),
        merge_gap_minutes=int(args.merge_gap_minutes),
        fallback_minutes=int(args.fallback_minutes),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
