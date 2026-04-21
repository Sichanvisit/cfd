"""
Run the checkpoint improvement orchestrator loop repeatedly.
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

from backend.services.checkpoint_improvement_orchestrator_watch_runner import (  # noqa: E402
    CheckpointImprovementOrchestratorWatchRunner,
    default_runtime_status_path,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Recurring checkpoint improvement orchestrator watch")
    ap.add_argument("--runtime-status", default=str(default_runtime_status_path()))
    ap.add_argument("--interval-sec", type=float, default=60.0)
    ap.add_argument("--max-cycles", type=int, default=0)
    ap.add_argument("--require-runtime-fresh", action="store_true")
    ap.add_argument("--runtime-max-age-sec", type=float, default=180.0)
    args = ap.parse_args()

    runner = CheckpointImprovementOrchestratorWatchRunner(
        runtime_status_path=Path(args.runtime_status).resolve(),
    )
    history: list[dict] = []
    cycle = 0
    interval_sec = max(1.0, float(args.interval_sec))
    max_cycles = int(args.max_cycles)

    try:
        while True:
            cycle += 1
            payload = runner.run_cycle(
                cycle_index=cycle,
                require_runtime_fresh=bool(args.require_runtime_fresh),
                runtime_max_age_sec=float(args.runtime_max_age_sec),
            )
            history.append(payload)
            summary = payload.get("summary", {}) or {}
            print(
                json.dumps(
                    {
                        "cycle": cycle,
                        "trigger_state": summary.get("trigger_state", ""),
                        "recommended_next_action": summary.get("recommended_next_action", ""),
                        "runtime_status_fresh": summary.get("runtime_status_fresh", False),
                        "overall_health_status": summary.get("overall_health_status", ""),
                        "recovery_state": summary.get("recovery_state", ""),
                        "report": summary.get("report_path", ""),
                    },
                    ensure_ascii=False,
                )
            )

            if max_cycles > 0 and cycle >= max_cycles:
                break
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        pass

    final_payload = {
        "contract_version": "checkpoint_improvement_orchestrator_watch_v0",
        "generated_at": datetime.now().astimezone().isoformat(),
        "interval_sec": interval_sec,
        "max_cycles": max_cycles,
        "history_count": len(history),
        "latest_cycle": history[-1] if history else {},
        "history": history[-20:],
    }
    print(json.dumps({"ok": True, "latest_cycle_count": len(history)}, ensure_ascii=False))
    Path(ROOT / "data" / "analysis" / "shadow_auto").mkdir(parents=True, exist_ok=True)
    final_path = ROOT / "data" / "analysis" / "shadow_auto" / "checkpoint_improvement_orchestrator_watch_history_latest.json"
    final_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
