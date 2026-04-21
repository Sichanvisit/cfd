"""
Run cap-based CFD storage retention once or on a fixed interval.
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

from backend.services.cfd_storage_retention import (  # noqa: E402
    DEFAULT_CHECKPOINT_DETAIL_MIN_BYTES,
    DEFAULT_STORAGE_CAP_BYTES,
    DEFAULT_STORAGE_RUNTIME_TRIM_ENABLED,
    DEFAULT_STORAGE_WATCH_INTERVAL_MIN,
    run_cfd_storage_retention,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recurring CFD storage retention")
    parser.add_argument("--mode", default="background", choices=("preflight", "background", "manual"))
    parser.add_argument("--cap-gb", type=float, default=float(DEFAULT_STORAGE_CAP_BYTES) / (1024 * 1024 * 1024))
    parser.add_argument(
        "--checkpoint-detail-min-gb",
        type=float,
        default=float(DEFAULT_CHECKPOINT_DETAIL_MIN_BYTES) / (1024 * 1024 * 1024),
    )
    parser.add_argument("--interval-min", type=float, default=float(DEFAULT_STORAGE_WATCH_INTERVAL_MIN))
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-checkpoint-trim", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    interval_sec = max(60.0, float(args.interval_min) * 60.0)
    max_cycles = int(args.max_cycles)
    allow_trim = bool(DEFAULT_STORAGE_RUNTIME_TRIM_ENABLED) and not bool(args.skip_checkpoint_trim)
    cycle = 0
    history: list[dict[str, object]] = []

    try:
        while True:
            cycle += 1
            payload = run_cfd_storage_retention(
                root=ROOT,
                cap_bytes=int(float(args.cap_gb) * 1024 * 1024 * 1024),
                mode=str(args.mode or "background"),
                dry_run=bool(args.dry_run),
                allow_checkpoint_trim=allow_trim,
                checkpoint_detail_min_bytes=int(float(args.checkpoint_detail_min_gb) * 1024 * 1024 * 1024),
            )
            summary = dict(payload.get("summary", {}) or {})
            history.append(
                {
                    "cycle": int(cycle),
                    "generated_at": payload.get("generated_at", ""),
                    "mode": summary.get("mode", ""),
                    "before_gb": summary.get("before_gb", 0),
                    "after_gb": summary.get("after_gb", 0),
                    "deleted_gb": summary.get("deleted_gb", 0),
                    "deleted_count": summary.get("deleted_count", 0),
                    "checkpoint_detail_trimmed": summary.get("checkpoint_detail_trimmed", False),
                    "under_cap": summary.get("under_cap", False),
                }
            )
            print(json.dumps(history[-1], ensure_ascii=False))
            if max_cycles > 0 and cycle >= max_cycles:
                break
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        pass

    final_payload = {
        "contract_version": "cfd_storage_retention_watch_v1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "interval_min": float(args.interval_min),
        "max_cycles": max_cycles,
        "history_count": len(history),
        "history": history[-20:],
    }
    output_path = ROOT / "data" / "analysis" / "shadow_auto" / "cfd_storage_retention_watch_history_latest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "history_count": len(history), "path": str(output_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
