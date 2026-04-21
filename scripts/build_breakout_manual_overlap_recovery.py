"""Build breakout manual-overlap recovery queue outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.breakout_manual_overlap_recovery import (  # noqa: E402
    write_breakout_manual_overlap_recovery_queue,
)


def _default_entry_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_manual_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_overlap_recovery_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_overlap_recovery_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_overlap_recovery_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-decision-path", default=str(_default_entry_path()))
    parser.add_argument("--manual-path", default=str(_default_manual_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--review-window-minutes", type=int, default=90)
    args = parser.parse_args()

    payload = write_breakout_manual_overlap_recovery_queue(
        entry_decision_path=args.entry_decision_path,
        manual_path=args.manual_path,
        csv_output_path=args.csv_output_path,
        json_output_path=args.json_output_path,
        markdown_output_path=args.md_output_path,
        review_window_minutes=int(args.review_window_minutes),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
