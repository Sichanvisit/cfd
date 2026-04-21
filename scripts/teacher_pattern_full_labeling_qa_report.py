"""
Teacher-pattern Step E2 full labeling QA report.

Usage:
  python scripts/teacher_pattern_full_labeling_qa_report.py
  python scripts/teacher_pattern_full_labeling_qa_report.py --min-labeled-rows 10000
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

from backend.services.teacher_pattern_full_labeling_qa import build_teacher_pattern_full_labeling_qa_report  # noqa: E402


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(_default_closed_history_path()))
    parser.add_argument("--min-labeled-rows", type=int, default=10_000)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(json.dumps({"error": f"missing csv: {csv_path}"}, ensure_ascii=False, indent=2))
        return 1

    df = pd.read_csv(csv_path, low_memory=False)
    report = build_teacher_pattern_full_labeling_qa_report(
        df,
        min_labeled_rows=int(args.min_labeled_rows),
    )
    report["csv_path"] = str(csv_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
