"""
Teacher-pattern Step 9-E3 pilot baseline report.

Usage:
  python scripts/teacher_pattern_pilot_baseline_report.py
  python scripts/teacher_pattern_pilot_baseline_report.py --output-dir models/teacher_pattern_state25_pilot
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.teacher_pattern_pilot_baseline import (  # noqa: E402
    DEFAULT_BARRIER_OUTCOME_MIN_ROWS,
    DEFAULT_BARRIER_OUTCOME_MIN_SUPPORT,
    DEFAULT_BELIEF_OUTCOME_MIN_ROWS,
    DEFAULT_BELIEF_OUTCOME_MIN_SUPPORT,
    DEFAULT_FORECAST_OUTCOME_MIN_SUPPORT,
    DEFAULT_MIN_SEED_ROWS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_ECONOMIC_TARGET_MIN_SUPPORT,
    DEFAULT_PATTERN_MIN_SUPPORT,
    DEFAULT_WAIT_QUALITY_MIN_SUPPORT,
    build_teacher_pattern_pilot_baseline_report,
)


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(_default_closed_history_path()))
    parser.add_argument("--min-seed-rows", type=int, default=DEFAULT_MIN_SEED_ROWS)
    parser.add_argument("--pattern-min-support", type=int, default=DEFAULT_PATTERN_MIN_SUPPORT)
    parser.add_argument("--wait-quality-min-support", type=int, default=DEFAULT_WAIT_QUALITY_MIN_SUPPORT)
    parser.add_argument("--economic-target-min-support", type=int, default=DEFAULT_ECONOMIC_TARGET_MIN_SUPPORT)
    parser.add_argument("--forecast-outcome-min-support", type=int, default=DEFAULT_FORECAST_OUTCOME_MIN_SUPPORT)
    parser.add_argument("--belief-outcome-min-support", type=int, default=DEFAULT_BELIEF_OUTCOME_MIN_SUPPORT)
    parser.add_argument("--belief-outcome-min-rows", type=int, default=DEFAULT_BELIEF_OUTCOME_MIN_ROWS)
    parser.add_argument("--barrier-outcome-min-support", type=int, default=DEFAULT_BARRIER_OUTCOME_MIN_SUPPORT)
    parser.add_argument("--barrier-outcome-min-rows", type=int, default=DEFAULT_BARRIER_OUTCOME_MIN_ROWS)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(json.dumps({"error": f"missing csv: {csv_path}"}, ensure_ascii=False, indent=2))
        return 1

    df = pd.read_csv(csv_path, low_memory=False)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    report = build_teacher_pattern_pilot_baseline_report(
        df,
        min_seed_rows=int(args.min_seed_rows),
        pattern_min_support=int(args.pattern_min_support),
        wait_quality_min_support=int(args.wait_quality_min_support),
        economic_target_min_support=int(args.economic_target_min_support),
        forecast_outcome_min_support=int(args.forecast_outcome_min_support),
        belief_outcome_min_support=int(args.belief_outcome_min_support),
        belief_outcome_min_rows=int(args.belief_outcome_min_rows),
        barrier_outcome_min_support=int(args.barrier_outcome_min_support),
        barrier_outcome_min_rows=int(args.barrier_outcome_min_rows),
        output_dir=output_dir,
    )
    report["csv_path"] = str(csv_path)
    report["output_dir"] = str(output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
