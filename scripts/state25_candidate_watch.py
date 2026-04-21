"""
Run state25 candidate retrain/gate/integration loop repeatedly.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.teacher_pattern_candidate_pipeline import (  # noqa: E402
    DEFAULT_CANDIDATE_ROOT,
    DEFAULT_CURRENT_BASELINE_DIR,
)
from backend.core.config import Config  # noqa: E402
from backend.services.teacher_pattern_candidate_watch import (  # noqa: E402
    DEFAULT_CLOSED_HISTORY_PATH,
    DEFAULT_INTERVAL_MIN,
    DEFAULT_MAX_CYCLES,
    DEFAULT_OUT_DIR,
    build_teacher_pattern_candidate_watch_cycle,
    write_teacher_pattern_candidate_watch_outputs,
)
from backend.services.teacher_pattern_execution_policy_integration import (  # noqa: E402
    DEFAULT_RUNTIME_STATUS_PATH,
)
from backend.services.teacher_pattern_pilot_baseline import (  # noqa: E402
    DEFAULT_ECONOMIC_TARGET_MIN_SUPPORT,
    DEFAULT_MIN_SEED_ROWS,
    DEFAULT_PATTERN_MIN_SUPPORT,
    DEFAULT_WAIT_QUALITY_MIN_SUPPORT,
)
from backend.services.teacher_pattern_promotion_gate import (  # noqa: E402
    DEFAULT_CANARY_EVIDENCE_PATH,
    DEFAULT_STEP9_WATCH_REPORT_PATH,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Recurring state25 candidate watch loop")
    ap.add_argument("--csv", default=str(ROOT / DEFAULT_CLOSED_HISTORY_PATH))
    ap.add_argument("--runtime-status", default=str(ROOT / DEFAULT_RUNTIME_STATUS_PATH))
    ap.add_argument("--candidate-root", default=str(ROOT / DEFAULT_CANDIDATE_ROOT))
    ap.add_argument(
        "--reference-metrics-path",
        default=str(ROOT / DEFAULT_CURRENT_BASELINE_DIR / "teacher_pattern_pilot_baseline_metrics.json"),
    )
    ap.add_argument("--step9-watch-report-path", default=str(ROOT / DEFAULT_STEP9_WATCH_REPORT_PATH))
    ap.add_argument("--canary-evidence-path", default=str(ROOT / DEFAULT_CANARY_EVIDENCE_PATH))
    ap.add_argument("--out-dir", default=str(ROOT / DEFAULT_OUT_DIR))
    ap.add_argument("--interval-min", type=float, default=DEFAULT_INTERVAL_MIN)
    ap.add_argument("--max-cycles", type=int, default=DEFAULT_MAX_CYCLES)
    ap.add_argument("--require-runtime-fresh", action="store_true")
    ap.add_argument("--runtime-max-age-sec", type=float, default=180.0)
    ap.add_argument("--min-seed-rows", type=int, default=DEFAULT_MIN_SEED_ROWS)
    ap.add_argument("--pattern-min-support", type=int, default=DEFAULT_PATTERN_MIN_SUPPORT)
    ap.add_argument("--wait-quality-min-support", type=int, default=DEFAULT_WAIT_QUALITY_MIN_SUPPORT)
    ap.add_argument("--economic-target-min-support", type=int, default=DEFAULT_ECONOMIC_TARGET_MIN_SUPPORT)
    apply_group = ap.add_mutually_exclusive_group()
    apply_group.add_argument("--apply-ai6", dest="apply_ai6", action="store_true")
    apply_group.add_argument("--no-apply-ai6", dest="apply_ai6", action="store_false")
    ap.set_defaults(apply_ai6=None)
    args = ap.parse_args()

    csv_path = Path(args.csv).resolve()
    runtime_status_path = Path(args.runtime_status).resolve()
    candidate_root = Path(args.candidate_root).resolve()
    reference_metrics_path = Path(args.reference_metrics_path).resolve()
    step9_watch_report_path = Path(args.step9_watch_report_path).resolve()
    canary_evidence_path = Path(args.canary_evidence_path).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not csv_path.exists():
        print(json.dumps({"error": f"missing csv: {csv_path}"}, ensure_ascii=False, indent=2))
        return 1

    history: list[dict] = []
    cycle = 0
    interval_sec = max(5.0, float(args.interval_min) * 60.0)
    max_cycles = int(args.max_cycles)
    effective_apply_ai6 = (
        bool(getattr(Config, "STATE25_CANDIDATE_WATCH_APPLY_AI6", False))
        if args.apply_ai6 is None
        else bool(args.apply_ai6)
    )

    try:
        while True:
            cycle += 1
            snapshot = build_teacher_pattern_candidate_watch_cycle(
                cycle=cycle,
                csv_path=csv_path,
                runtime_status_path=runtime_status_path,
                candidate_root=candidate_root,
                reference_metrics_path=reference_metrics_path,
                step9_watch_report_path=step9_watch_report_path if step9_watch_report_path.exists() else None,
                canary_evidence_path=canary_evidence_path if canary_evidence_path.exists() else None,
                require_runtime_fresh=bool(args.require_runtime_fresh),
                runtime_max_age_sec=float(args.runtime_max_age_sec),
                min_seed_rows=int(args.min_seed_rows),
                pattern_min_support=int(args.pattern_min_support),
                wait_quality_min_support=int(args.wait_quality_min_support),
                economic_target_min_support=int(args.economic_target_min_support),
                apply_ai6=bool(effective_apply_ai6),
            )
            history.append(snapshot)

            report = {
                "contract_version": "teacher_pattern_candidate_watch_v1",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "interval_min": float(args.interval_min),
                "max_cycles": int(max_cycles),
                "apply_ai6_effective": bool(effective_apply_ai6),
                "history_count": len(history),
                "latest_cycle": snapshot,
                "history": history[-20:],
            }
            json_path, md_path = write_teacher_pattern_candidate_watch_outputs(out_dir=out_dir, report=report)
            print(
                json.dumps(
                    {
                        "cycle": cycle,
                        "status": snapshot.get("status", ""),
                        "candidate_id": ((snapshot.get("candidate", {}) or {}).get("candidate_id", "")),
                        "gate_stage": ((snapshot.get("gate", {}) or {}).get("gate_stage", "")),
                        "integration_stage": ((snapshot.get("integration", {}) or {}).get("integration_stage", "")),
                        "binding_mode": ((snapshot.get("binding", {}) or {}).get("binding_mode", "")),
                        "apply_ai6_effective": bool(effective_apply_ai6),
                        "ai6_controller_stage": ((snapshot.get("ai6", {}) or {}).get("controller_stage", "")),
                        "ai6_applied_action": ((snapshot.get("ai6", {}) or {}).get("applied_action", "")),
                        "report": str(json_path),
                        "markdown": str(md_path),
                    },
                    ensure_ascii=False,
                )
            )

            if max_cycles > 0 and cycle >= max_cycles:
                break
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        pass

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = out_dir / f"state25_candidate_watch_{ts}.json"
    final_payload = {
        "contract_version": "teacher_pattern_candidate_watch_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "interval_min": float(args.interval_min),
        "max_cycles": int(max_cycles),
        "apply_ai6_effective": bool(effective_apply_ai6),
        "history_count": len(history),
        "latest_cycle": history[-1] if history else {},
        "history": history,
    }
    final_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(final_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
