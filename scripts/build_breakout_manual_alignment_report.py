"""Build breakout manual alignment report outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.breakout_event_report import (  # noqa: E402
    write_breakout_manual_alignment_report,
)


def _default_entry_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_manual_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_alignment_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_alignment_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_alignment_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-decision-path", default=str(_default_entry_path()))
    parser.add_argument("--manual-path", default=str(_default_manual_path()))
    parser.add_argument("--future-bar-path", default="")
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--match-tolerance-sec", type=float, default=300.0)
    parser.add_argument("--max-future-bars", type=int, default=8)
    parser.add_argument("--accepted-only", action="store_true")
    parser.add_argument("--symbols", nargs="*", default=None)
    args = parser.parse_args()

    report = write_breakout_manual_alignment_report(
        entry_decision_path=args.entry_decision_path,
        manual_path=args.manual_path,
        future_bar_path=(args.future_bar_path or None),
        csv_output_path=args.csv_output_path,
        json_output_path=args.json_output_path,
        markdown_output_path=args.md_output_path,
        accepted_only=bool(args.accepted_only),
        symbols=args.symbols,
        match_tolerance_sec=float(args.match_tolerance_sec),
        max_future_bars=int(args.max_future_bars),
    )
    print(
        json.dumps(
            {
                "csv_output_path": str(report.get("csv_output_path", "")),
                "json_output_path": str(report.get("json_output_path", "")),
                "markdown_output_path": str(report.get("markdown_output_path", "")),
                "coverage": report.get("coverage", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
