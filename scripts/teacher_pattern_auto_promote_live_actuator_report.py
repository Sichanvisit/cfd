"""Build the AI6 auto-promote / rollback / live-actuator report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.teacher_pattern_auto_promote_live_actuator import (  # noqa: E402
    DEFAULT_ACTIVE_CANDIDATE_STATE_PATH,
    DEFAULT_AUTO_PROMOTE_HISTORY_PATH,
    run_teacher_pattern_auto_promote_live_actuator,
)
from backend.services.teacher_pattern_execution_policy_integration import (  # noqa: E402
    DEFAULT_LATEST_GATE_REPORT_PATH,
)
from backend.services.teacher_pattern_execution_policy_log_only_binding import (  # noqa: E402
    DEFAULT_LATEST_EXECUTION_POLICY_REPORT_PATH,
)
from backend.services.teacher_pattern_auto_promote_live_actuator import (  # noqa: E402
    DEFAULT_LATEST_LOG_ONLY_BINDING_REPORT_PATH,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build AI6 auto-promote / rollback / live-actuator report")
    ap.add_argument("--gate-report-path", default=str(ROOT / DEFAULT_LATEST_GATE_REPORT_PATH))
    ap.add_argument(
        "--execution-policy-report-path",
        default=str(ROOT / DEFAULT_LATEST_EXECUTION_POLICY_REPORT_PATH),
    )
    ap.add_argument(
        "--log-only-binding-report-path",
        default=str(ROOT / DEFAULT_LATEST_LOG_ONLY_BINDING_REPORT_PATH),
    )
    ap.add_argument("--active-candidate-state-path", default=str(ROOT / DEFAULT_ACTIVE_CANDIDATE_STATE_PATH))
    ap.add_argument("--history-path", default=str(ROOT / DEFAULT_AUTO_PROMOTE_HISTORY_PATH))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    result = run_teacher_pattern_auto_promote_live_actuator(
        gate_report_path=Path(args.gate_report_path).resolve(),
        execution_policy_report_path=Path(args.execution_policy_report_path).resolve(),
        log_only_binding_report_path=Path(args.log_only_binding_report_path).resolve(),
        active_candidate_state_path=Path(args.active_candidate_state_path).resolve(),
        history_path=Path(args.history_path).resolve(),
        apply=bool(args.apply),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
