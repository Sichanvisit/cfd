"""
Entry wait quality replay report.

Usage:
  python scripts/entry_wait_quality_replay_report.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.entry_wait_quality_replay_bridge import (  # noqa: E402
    DEFAULT_FUTURE_BAR_COUNT,
    write_entry_wait_quality_replay_report,
)


def _default_entry_decisions_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_output_path() -> Path:
    return ROOT / "data" / "analysis" / "wait_quality" / "entry_wait_quality_replay_latest.json"


def _default_markdown_output_path() -> Path:
    return ROOT / "data" / "analysis" / "wait_quality" / "entry_wait_quality_replay_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-decisions-path", default=str(_default_entry_decisions_path()))
    parser.add_argument("--closed-trades-path", default=str(_default_closed_history_path()))
    parser.add_argument("--future-bars-path", default="")
    parser.add_argument("--output-path", default=str(_default_output_path()))
    parser.add_argument("--markdown-output-path", default=str(_default_markdown_output_path()))
    parser.add_argument("--max-future-bars", type=int, default=DEFAULT_FUTURE_BAR_COUNT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--no-dedupe", action="store_true")
    parser.add_argument("--print-full", action="store_true")
    args = parser.parse_args()

    report = write_entry_wait_quality_replay_report(
        entry_decision_path=args.entry_decisions_path,
        closed_trade_path=args.closed_trades_path,
        future_bar_path=(args.future_bars_path or None),
        output_path=args.output_path,
        markdown_output_path=args.markdown_output_path,
        dedupe=not bool(args.no_dedupe),
        max_future_bars=int(args.max_future_bars),
        limit=args.limit,
        symbols=list(args.symbol or []),
    )
    if args.print_full:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    summary = report.get("summary", {}) or {}
    label_counts = summary.get("label_counts", {}) or {}
    coverage = report.get("coverage", {}) or {}
    alignment = coverage.get("future_bar_alignment", {}) or {}
    print(
        json.dumps(
            {
                "status": alignment.get("status", ""),
                "raw_wait_candidate_count": coverage.get("raw_wait_candidate_count", 0),
                "bridged_row_count": coverage.get("bridged_row_count", 0),
                "rows_valid": summary.get("rows_valid", 0),
                "positive_rows": summary.get("positive_rows", 0),
                "negative_rows": summary.get("negative_rows", 0),
                "label_counts": {
                    "better_entry_after_wait": label_counts.get("better_entry_after_wait", 0),
                    "avoided_loss_by_wait": label_counts.get("avoided_loss_by_wait", 0),
                    "missed_move_by_wait": label_counts.get("missed_move_by_wait", 0),
                    "delayed_loss_after_wait": label_counts.get("delayed_loss_after_wait", 0),
                    "neutral_wait": label_counts.get("neutral_wait", 0),
                    "insufficient_evidence": label_counts.get("insufficient_evidence", 0),
                },
                "recommended_action": alignment.get("recommended_action", ""),
                "json_path": report.get("output_path", ""),
                "markdown_path": report.get("markdown_output_path", ""),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
