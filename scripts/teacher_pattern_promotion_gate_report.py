"""
State25 promotion gate / rollback report.

Usage:
  python scripts/teacher_pattern_promotion_gate_report.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.teacher_pattern_promotion_gate import (  # noqa: E402
    DEFAULT_CANARY_EVIDENCE_PATH,
    DEFAULT_LATEST_CANDIDATE_MANIFEST,
    DEFAULT_STEP9_WATCH_REPORT_PATH,
    run_teacher_pattern_promotion_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate-manifest-path",
        default=str(ROOT / DEFAULT_LATEST_CANDIDATE_MANIFEST),
    )
    parser.add_argument(
        "--step9-watch-report-path",
        default=str(ROOT / DEFAULT_STEP9_WATCH_REPORT_PATH),
    )
    parser.add_argument(
        "--canary-evidence-path",
        default=str(ROOT / DEFAULT_CANARY_EVIDENCE_PATH),
    )
    args = parser.parse_args()

    manifest_path = Path(args.candidate_manifest_path)
    if not manifest_path.exists():
        print(json.dumps({"error": f"missing candidate manifest: {manifest_path}"}, ensure_ascii=False, indent=2))
        return 1

    step9_path = Path(args.step9_watch_report_path)
    canary_path = Path(args.canary_evidence_path)
    result = run_teacher_pattern_promotion_gate(
        candidate_manifest_path=manifest_path,
        step9_watch_report_path=step9_path if step9_path.exists() else None,
        canary_evidence_path=canary_path if canary_path.exists() else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
