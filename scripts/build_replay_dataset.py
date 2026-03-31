from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from backend.trading.engine.offline.replay_dataset_builder import write_replay_dataset_batch  # noqa: E402
from fetch_mt5_future_bars import fetch_mt5_future_bars  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build replay dataset rows from entry decisions and link them to a validation report.")
    parser.add_argument(
        "--entry-decisions",
        default="data/trades/entry_decisions.csv",
        help="Path to entry_decisions.csv",
    )
    parser.add_argument(
        "--closed-trades",
        default="data/trades/trade_closed_history.csv",
        help="Path to trade_closed_history.csv",
    )
    parser.add_argument(
        "--future-bars",
        default="",
        help="Optional OHLC future bar CSV path with symbol,time,open,high,low,close columns.",
    )
    parser.add_argument(
        "--fetch-mt5-future-bars",
        action="store_true",
        help="Fetch future OHLC bars from MT5 first and feed the generated CSV into replay building.",
    )
    parser.add_argument(
        "--future-bars-output",
        default="",
        help="Output CSV path for MT5-fetched future bars.",
    )
    parser.add_argument(
        "--future-bars-timeframe",
        default="M15",
        help="MT5 timeframe used when --fetch-mt5-future-bars is enabled.",
    )
    parser.add_argument(
        "--future-bars-lookback-bars",
        type=int,
        default=1,
        help="Bars to fetch before the earliest anchor when MT5 backfill is enabled.",
    )
    parser.add_argument(
        "--future-bars-lookahead-bars",
        type=int,
        default=8,
        help="Bars to fetch after the latest anchor when MT5 backfill is enabled.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/datasets/replay_intermediate",
        help="Directory where replay dataset JSONL will be written.",
    )
    parser.add_argument(
        "--analysis-dir",
        default="data/analysis",
        help="Directory where the validation report JSON will be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of decision rows to process.",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Optional symbol filter. Repeat for multiple symbols.",
    )
    parser.add_argument(
        "--entered-only",
        action="store_true",
        help="Only include decision rows where outcome == entered.",
    )
    parser.add_argument(
        "--skip-validation-report",
        action="store_true",
        help="Skip building the validation report after the replay dataset file is written.",
    )
    args = parser.parse_args()

    future_bar_path = (args.future_bars or None)
    future_bar_fetch_summary = None
    if bool(args.fetch_mt5_future_bars):
        future_bar_fetch_summary = fetch_mt5_future_bars(
            entry_decisions=args.entry_decisions,
            output_path=(args.future_bars_output or future_bar_path),
            timeframe=str(args.future_bars_timeframe or "M15"),
            lookback_bars=int(args.future_bars_lookback_bars),
            lookahead_bars=int(args.future_bars_lookahead_bars),
            symbols=list(args.symbol or []),
        )
        future_bar_path = str(future_bar_fetch_summary.get("output_path", "") or future_bar_path or "")

    summary = write_replay_dataset_batch(
        entry_decision_path=args.entry_decisions,
        closed_trade_path=args.closed_trades,
        future_bar_path=future_bar_path,
        output_dir=args.output_dir,
        analysis_dir=args.analysis_dir,
        limit=args.limit,
        symbols=args.symbol,
        entered_only=args.entered_only,
        emit_validation_report=not bool(args.skip_validation_report),
    )
    if future_bar_fetch_summary is not None:
        summary["future_bar_fetch_summary"] = future_bar_fetch_summary
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
