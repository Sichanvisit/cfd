"""Build Step 9-E4 confusion tuning report from current seed and pilot baseline output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.teacher_pattern_confusion_tuning import (  # noqa: E402
    build_teacher_pattern_confusion_tuning_report,
)
from backend.services.teacher_pattern_full_labeling_qa import (  # noqa: E402
    build_teacher_pattern_full_labeling_qa_report,
)


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_baseline_metrics_path() -> Path:
    return ROOT / "models" / "teacher_pattern_state25_pilot" / "teacher_pattern_pilot_baseline_metrics.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-path", default=str(_default_closed_history_path()))
    parser.add_argument("--baseline-metrics-path", default=str(_default_baseline_metrics_path()))
    parser.add_argument("--min-labeled-rows", type=int, default=10_000)
    parser.add_argument("--min-confusion-count", type=int, default=3)
    parser.add_argument("--min-confusion-ratio", type=float, default=0.01)
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    baseline_metrics_path = Path(args.baseline_metrics_path)

    frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    baseline_report = json.loads(baseline_metrics_path.read_text(encoding="utf-8"))
    full_qa_report = build_teacher_pattern_full_labeling_qa_report(frame, min_labeled_rows=args.min_labeled_rows)
    report = build_teacher_pattern_confusion_tuning_report(
        full_qa_report=full_qa_report,
        baseline_report=baseline_report,
        min_confusion_count=args.min_confusion_count,
        min_confusion_ratio=args.min_confusion_ratio,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
