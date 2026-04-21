"""CLI report for teacher-pattern asset-level calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.teacher_pattern_asset_calibration import (
    build_teacher_pattern_asset_calibration_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build asset calibration report from teacher-pattern labeled closed history.")
    parser.add_argument(
        "--csv-path",
        default="data/trades/trade_closed_history.csv",
        help="Closed-history CSV path",
    )
    parser.add_argument(
        "--min-rows-per-symbol",
        type=int,
        default=200,
        help="Minimum labeled rows required per symbol before Step E1 is considered stable.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    frame = pd.read_csv(csv_path, low_memory=False) if csv_path.exists() else pd.DataFrame()
    report = build_teacher_pattern_asset_calibration_report(
        frame,
        min_rows_per_symbol=args.min_rows_per_symbol,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
