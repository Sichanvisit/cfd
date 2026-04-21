"""
Forecast-state25 outcome bridge report.

Usage:
  python scripts/forecast_state25_outcome_bridge_report.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.forecast_state25_outcome_bridge import (  # noqa: E402
    write_forecast_state25_outcome_bridge_report,
)


def _default_entry_decisions_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_output_path() -> Path:
    return ROOT / "data" / "analysis" / "forecast_state25" / "forecast_state25_outcome_bridge_latest.json"


def _default_markdown_output_path() -> Path:
    return ROOT / "data" / "analysis" / "forecast_state25" / "forecast_state25_outcome_bridge_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-decisions-path", default=str(_default_entry_decisions_path()))
    parser.add_argument("--closed-trades-path", default=str(_default_closed_history_path()))
    parser.add_argument("--future-bars-path", default="")
    parser.add_argument("--output-path", default=str(_default_output_path()))
    parser.add_argument("--markdown-output-path", default=str(_default_markdown_output_path()))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--print-full", action="store_true")
    args = parser.parse_args()

    report = write_forecast_state25_outcome_bridge_report(
        entry_decision_path=args.entry_decisions_path,
        closed_trade_path=args.closed_trades_path,
        future_bar_path=(args.future_bars_path or None),
        output_path=args.output_path,
        markdown_output_path=args.markdown_output_path,
        symbols=list(args.symbol or []),
        limit=args.limit,
    )
    if args.print_full:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    summary = report.get("summary", {}) or {}
    coverage = report.get("coverage", {}) or {}
    print(
        json.dumps(
            {
                "raw_bridge_candidate_count": summary.get("raw_bridge_candidate_count", 0),
                "bridged_row_count": summary.get("bridged_row_count", 0),
                "transition_valid_rows": summary.get("transition_valid_rows", 0),
                "management_valid_rows": summary.get("management_valid_rows", 0),
                "full_outcome_eligible_rows": summary.get("full_outcome_eligible_rows", 0),
                "partial_outcome_eligible_rows": summary.get("partial_outcome_eligible_rows", 0),
                "insufficient_future_bars_rows": summary.get("insufficient_future_bars_rows", 0),
                "rows_with_wait_quality": summary.get("rows_with_wait_quality", 0),
                "rows_with_economic_target": summary.get("rows_with_economic_target", 0),
                "bridge_quality_status_counts": coverage.get("bridge_quality_status_counts", {}),
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
