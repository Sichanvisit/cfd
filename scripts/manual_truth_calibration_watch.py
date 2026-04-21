"""
Run the manual-truth calibration refresh loop repeatedly.
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

from backend.services.manual_truth_calibration_watch import (  # noqa: E402
    DEFAULT_INTERVAL_MIN,
    DEFAULT_MAX_CYCLES,
    DEFAULT_OUT_DIR,
    DEFAULT_RUNTIME_STATUS_PATH,
    DEFAULT_STEP_TIMEOUT_SEC,
    build_manual_truth_calibration_cycle,
    write_manual_truth_calibration_watch_outputs,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Recurring manual-truth calibration watch loop")
    ap.add_argument("--runtime-status", default=str(ROOT / DEFAULT_RUNTIME_STATUS_PATH))
    ap.add_argument("--out-dir", default=str(ROOT / DEFAULT_OUT_DIR))
    ap.add_argument("--interval-min", type=float, default=DEFAULT_INTERVAL_MIN)
    ap.add_argument("--max-cycles", type=int, default=DEFAULT_MAX_CYCLES)
    ap.add_argument("--require-runtime-fresh", action="store_true")
    ap.add_argument("--runtime-max-age-sec", type=float, default=180.0)
    ap.add_argument("--step-timeout-sec", type=float, default=DEFAULT_STEP_TIMEOUT_SEC)
    args = ap.parse_args()

    runtime_status_path = Path(args.runtime_status).resolve()
    out_dir = Path(args.out_dir).resolve()
    history: list[dict] = []
    cycle = 0
    interval_sec = max(5.0, float(args.interval_min) * 60.0)
    max_cycles = int(args.max_cycles)
    python_exe = Path(sys.executable).resolve()

    try:
        while True:
            cycle += 1
            snapshot = build_manual_truth_calibration_cycle(
                cycle=cycle,
                root=ROOT,
                python_exe=python_exe,
                runtime_status_path=runtime_status_path,
                require_runtime_fresh=bool(args.require_runtime_fresh),
                runtime_max_age_sec=float(args.runtime_max_age_sec),
                step_timeout_sec=float(args.step_timeout_sec),
            )
            history.append(snapshot)

            report = {
                "contract_version": "manual_truth_calibration_watch_v1",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "interval_min": float(args.interval_min),
                "max_cycles": int(max_cycles),
                "history_count": len(history),
                "latest_cycle": snapshot,
                "history": history[-20:],
            }
            json_path, md_path = write_manual_truth_calibration_watch_outputs(out_dir=out_dir, report=report)
            print(
                json.dumps(
                    {
                        "cycle": cycle,
                        "status": snapshot.get("status", ""),
                        "ok_task_count": snapshot.get("ok_task_count", 0),
                        "failed_task_count": snapshot.get("failed_task_count", 0),
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
    final_path = out_dir / f"manual_truth_calibration_watch_{ts}.json"
    final_payload = {
        "contract_version": "manual_truth_calibration_watch_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "interval_min": float(args.interval_min),
        "max_cycles": int(max_cycles),
        "history_count": len(history),
        "latest_cycle": history[-1] if history else {},
        "history": history,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    final_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(final_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
