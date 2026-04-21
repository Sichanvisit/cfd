"""
Teacher-pattern experiment seed readiness report.

Usage:
  python scripts/teacher_pattern_experiment_seed_report.py
  python scripts/teacher_pattern_experiment_seed_report.py --min-seed-rows 1000
  python scripts/teacher_pattern_experiment_seed_report.py --economic-primary-min-support 25
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

from backend.services.teacher_pattern_experiment_seed import build_teacher_pattern_experiment_seed_report  # noqa: E402


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(_default_closed_history_path()))
    parser.add_argument("--min-seed-rows", type=int, default=1000)
    parser.add_argument("--economic-primary-min-support", type=int, default=25)
    parser.add_argument("--economic-loss-min-support", type=int, default=25)
    parser.add_argument("--economic-bucket-min-support", type=int, default=25)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(json.dumps({"error": f"missing csv: {csv_path}"}, ensure_ascii=False, indent=2))
        return 1

    df = pd.read_csv(csv_path, low_memory=False)
    report = build_teacher_pattern_experiment_seed_report(
        df,
        min_seed_rows=int(args.min_seed_rows),
        economic_primary_min_support=int(args.economic_primary_min_support),
        economic_loss_min_support=int(args.economic_loss_min_support),
        economic_bucket_min_support=int(args.economic_bucket_min_support),
    )
    report["csv_path"] = str(csv_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
