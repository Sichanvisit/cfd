"""
State25 execution policy integration recommendation report.

Usage:
  python scripts/teacher_pattern_execution_policy_integration_report.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.teacher_pattern_execution_policy_integration import (  # noqa: E402
    DEFAULT_LATEST_GATE_REPORT_PATH,
    DEFAULT_RUNTIME_STATUS_PATH,
    run_teacher_pattern_execution_policy_integration,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gate-report-path",
        default=str(ROOT / DEFAULT_LATEST_GATE_REPORT_PATH),
    )
    parser.add_argument(
        "--runtime-status-path",
        default=str(ROOT / DEFAULT_RUNTIME_STATUS_PATH),
    )
    args = parser.parse_args()

    gate_report_path = Path(args.gate_report_path)
    if not gate_report_path.exists():
        print(json.dumps({"error": f"missing gate report: {gate_report_path}"}, ensure_ascii=False, indent=2))
        return 1

    runtime_status_path = Path(args.runtime_status_path)
    result = run_teacher_pattern_execution_policy_integration(
        gate_report_path=gate_report_path,
        runtime_status_path=runtime_status_path if runtime_status_path.exists() else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
