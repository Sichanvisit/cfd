"""Build executable breakout replay backfill bundles from recovery windows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.breakout_backfill_runner_scaffold import (  # noqa: E402
    write_breakout_backfill_runner_scaffold,
)


def _default_queue_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_overlap_recovery_latest.csv"


def _default_secondary_queue_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_manual_learning_recovery_latest.csv"


def _default_manual_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_supplemental_manual_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "breakout_manual_overlap_seed_review_entries.csv"


def _default_trades_root() -> Path:
    return ROOT / "data" / "trades"


def _default_closed_trades_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_bundle_root() -> Path:
    return ROOT / "data" / "backfill" / "breakout_event"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_backfill_runner_scaffold_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_backfill_runner_scaffold_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_backfill_runner_scaffold_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-path", default=str(_default_queue_path()))
    parser.add_argument("--secondary-queue-path", default=str(_default_secondary_queue_path()))
    parser.add_argument("--manual-path", default=str(_default_manual_path()))
    parser.add_argument("--supplemental-manual-path", default=str(_default_supplemental_manual_path()))
    parser.add_argument("--trades-root", default=str(_default_trades_root()))
    parser.add_argument("--closed-trades-path", default=str(_default_closed_trades_path()))
    parser.add_argument("--bundle-root", default=str(_default_bundle_root()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--future-bars-timeframe", default="M1")
    parser.add_argument("--future-bars-lookback-bars", type=int, default=1)
    parser.add_argument("--future-bars-lookahead-bars", type=int, default=12)
    args = parser.parse_args()

    payload = write_breakout_backfill_runner_scaffold(
        queue_path=Path(args.queue_path),
        secondary_queue_path=Path(args.secondary_queue_path),
        manual_path=Path(args.manual_path),
        supplemental_manual_path=Path(args.supplemental_manual_path),
        trades_root=Path(args.trades_root),
        closed_trades_path=Path(args.closed_trades_path),
        bundle_root=Path(args.bundle_root),
        csv_output_path=Path(args.csv_output_path),
        json_output_path=Path(args.json_output_path),
        md_output_path=Path(args.md_output_path),
        future_bars_timeframe=str(args.future_bars_timeframe),
        future_bars_lookback_bars=int(args.future_bars_lookback_bars),
        future_bars_lookahead_bars=int(args.future_bars_lookahead_bars),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
