"""
Teacher-pattern Step 9 watch report.

Usage:
  python scripts/teacher_pattern_step9_watch_report.py
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

from backend.services.teacher_pattern_asset_calibration import (  # noqa: E402
    build_teacher_pattern_asset_calibration_report,
)
from backend.services.teacher_pattern_confusion_tuning import (  # noqa: E402
    DEFAULT_MIN_CONFUSION_COUNT,
    DEFAULT_MIN_CONFUSION_RATIO,
    build_teacher_pattern_confusion_tuning_report,
)
from backend.services.teacher_pattern_execution_handoff import (  # noqa: E402
    DEFAULT_MIN_COVERED_PRIMARY_COUNT,
    DEFAULT_MIN_GROUP_TEST_MACRO_F1,
    DEFAULT_MIN_LABELED_ROWS,
    DEFAULT_MIN_PATTERN_TEST_MACRO_F1,
    DEFAULT_MIN_SUPPORTED_PATTERN_COUNT,
    build_teacher_pattern_execution_handoff_report,
)
from backend.services.teacher_pattern_experiment_seed import (  # noqa: E402
    build_teacher_pattern_experiment_seed_report,
)
from backend.services.teacher_pattern_full_labeling_qa import (  # noqa: E402
    build_teacher_pattern_full_labeling_qa_report,
)
from backend.services.teacher_pattern_step9_watch import (  # noqa: E402
    DEFAULT_RECHECK_TOTAL_ROW_DELTA,
    build_teacher_pattern_step9_watch_report,
    render_teacher_pattern_step9_watch_markdown,
)


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_baseline_metrics_path() -> Path:
    return ROOT / "models" / "teacher_pattern_state25_pilot" / "teacher_pattern_pilot_baseline_metrics.json"


def _default_runtime_status_path() -> Path:
    return ROOT / "data" / "runtime_status.json"


def _default_output_path() -> Path:
    return ROOT / "data" / "analysis" / "teacher_pattern_state25" / "teacher_pattern_step9_watch_latest.json"


def _default_markdown_output_path() -> Path:
    return ROOT / "data" / "analysis" / "teacher_pattern_state25" / "teacher_pattern_step9_watch_latest.md"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-path", default=str(_default_closed_history_path()))
    parser.add_argument("--baseline-metrics-path", default=str(_default_baseline_metrics_path()))
    parser.add_argument("--runtime-status-path", default=str(_default_runtime_status_path()))
    parser.add_argument("--output-path", default=str(_default_output_path()))
    parser.add_argument("--markdown-output-path", default=str(_default_markdown_output_path()))
    parser.add_argument("--min-labeled-rows", type=int, default=DEFAULT_MIN_LABELED_ROWS)
    parser.add_argument("--min-covered-primary-count", type=int, default=DEFAULT_MIN_COVERED_PRIMARY_COUNT)
    parser.add_argument("--min-supported-pattern-count", type=int, default=DEFAULT_MIN_SUPPORTED_PATTERN_COUNT)
    parser.add_argument("--min-group-test-macro-f1", type=float, default=DEFAULT_MIN_GROUP_TEST_MACRO_F1)
    parser.add_argument("--min-pattern-test-macro-f1", type=float, default=DEFAULT_MIN_PATTERN_TEST_MACRO_F1)
    parser.add_argument("--min-confusion-count", type=int, default=DEFAULT_MIN_CONFUSION_COUNT)
    parser.add_argument("--min-confusion-ratio", type=float, default=DEFAULT_MIN_CONFUSION_RATIO)
    parser.add_argument("--min-recheck-total-row-delta", type=int, default=DEFAULT_RECHECK_TOTAL_ROW_DELTA)
    parser.add_argument("--ignore-previous", action="store_true")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    baseline_metrics_path = Path(args.baseline_metrics_path)
    runtime_status_path = Path(args.runtime_status_path)
    output_path = Path(args.output_path)
    markdown_output_path = Path(args.markdown_output_path)

    if not csv_path.exists():
        print(json.dumps({"error": f"missing csv: {csv_path}"}, ensure_ascii=False, indent=2))
        return 1
    if not baseline_metrics_path.exists():
        print(json.dumps({"error": f"missing baseline metrics: {baseline_metrics_path}"}, ensure_ascii=False, indent=2))
        return 1

    frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    baseline_report = _load_json(baseline_metrics_path)
    seed_report = build_teacher_pattern_experiment_seed_report(frame, min_seed_rows=int(args.min_labeled_rows))
    asset_report = build_teacher_pattern_asset_calibration_report(frame)
    full_qa_report = build_teacher_pattern_full_labeling_qa_report(
        frame,
        min_labeled_rows=int(args.min_labeled_rows),
    )
    confusion_report = build_teacher_pattern_confusion_tuning_report(
        full_qa_report=full_qa_report,
        baseline_report=baseline_report,
        min_confusion_count=int(args.min_confusion_count),
        min_confusion_ratio=float(args.min_confusion_ratio),
    )
    execution_report = build_teacher_pattern_execution_handoff_report(
        asset_calibration_report=asset_report,
        full_qa_report=full_qa_report,
        baseline_report=baseline_report,
        confusion_report=confusion_report,
        min_labeled_rows=int(args.min_labeled_rows),
        min_covered_primary_count=int(args.min_covered_primary_count),
        min_supported_pattern_count=int(args.min_supported_pattern_count),
        min_group_test_macro_f1=float(args.min_group_test_macro_f1),
        min_pattern_test_macro_f1=float(args.min_pattern_test_macro_f1),
    )

    runtime_status_report: dict[str, object] | None = None
    if runtime_status_path.exists():
        runtime_status_report = _load_json(runtime_status_path)

    previous_watch_report: dict[str, object] | None = None
    if not args.ignore_previous and output_path.exists():
        previous_watch_report = _load_json(output_path)

    report = build_teacher_pattern_step9_watch_report(
        seed_report=seed_report,
        full_qa_report=full_qa_report,
        baseline_report=baseline_report,
        confusion_report=confusion_report,
        execution_handoff_report=execution_report,
        runtime_status_report=runtime_status_report,
        previous_watch_report=previous_watch_report,
        min_labeled_rows=int(args.min_labeled_rows),
        min_recheck_total_row_delta=int(args.min_recheck_total_row_delta),
    )
    report["csv_path"] = str(csv_path)
    report["baseline_metrics_path"] = str(baseline_metrics_path)
    report["runtime_status_path"] = str(runtime_status_path) if runtime_status_path.exists() else ""
    report["markdown_output_path"] = str(markdown_output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(render_teacher_pattern_step9_watch_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
