"""
State25 phase-2 threshold/size log-only binding report.

Usage:
  python scripts/teacher_pattern_execution_policy_log_only_binding_report.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.teacher_pattern_execution_policy_log_only_binding import (  # noqa: E402
    DEFAULT_LATEST_EXECUTION_POLICY_REPORT_PATH,
    run_teacher_pattern_execution_policy_log_only_binding,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execution-policy-report-path",
        default=str(ROOT / DEFAULT_LATEST_EXECUTION_POLICY_REPORT_PATH),
    )
    args = parser.parse_args()

    report_path = Path(args.execution_policy_report_path)
    if not report_path.exists():
        print(json.dumps({"error": f"missing execution policy report: {report_path}"}, ensure_ascii=False, indent=2))
        return 1

    result = run_teacher_pattern_execution_policy_log_only_binding(
        execution_policy_report_path=report_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
