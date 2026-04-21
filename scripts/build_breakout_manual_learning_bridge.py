"""Build a breakout manual learning bridge from base and screenshot/manual review cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.breakout_manual_learning_bridge import (  # noqa: E402
    write_breakout_manual_learning_bridge,
)


def _default_manual_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_supplemental_manual_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "breakout_manual_overlap_seed_review_entries.csv"


def _default_entry_decision_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_learning_bridge_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_learning_bridge_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_learning_bridge_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual-path", default=str(_default_manual_path()))
    parser.add_argument("--supplemental-manual-path", default=str(_default_supplemental_manual_path()))
    parser.add_argument("--entry-decision-path", default=str(_default_entry_decision_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--match-tolerance-sec", type=float, default=300.0)
    args = parser.parse_args()

    report = write_breakout_manual_learning_bridge(
        manual_path=Path(args.manual_path),
        supplemental_manual_path=Path(args.supplemental_manual_path),
        entry_decision_path=Path(args.entry_decision_path),
        csv_output_path=Path(args.csv_output_path),
        json_output_path=Path(args.json_output_path),
        md_output_path=Path(args.md_output_path),
        match_tolerance_sec=float(args.match_tolerance_sec),
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
