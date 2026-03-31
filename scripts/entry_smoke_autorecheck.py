"""
Run entry smoke checks repeatedly (default: every 15 minutes) until pass.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_STATUS = ROOT / "data" / "runtime_status.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.entry_smoke_guard import DEFAULT_DECISIONS, DEFAULT_OUT_DIR, analyze


def _runtime_fresh(status_file: Path, max_age_sec: float) -> tuple[bool, float]:
    try:
        mtime = float(status_file.stat().st_mtime)
    except Exception:
        return (False, float("inf"))
    age = max(0.0, time.time() - mtime)
    return (age <= max(1.0, float(max_age_sec)), age)


def _build_checks(
    *,
    totals: dict,
    min_wait_positive_ratio: float,
    max_sell_only_buy_ratio: float,
    max_entered_sell_only_buy_ratio: float,
) -> dict:
    wait_ratio = float(totals.get("wait_positive_ratio", 0.0) or 0.0)
    sell_only_buy_ratio = float(totals.get("sell_only_buy_ratio", 0.0) or 0.0)
    entered_sell_only_buy_ratio = float(totals.get("sell_only_entered_buy_ratio", 0.0) or 0.0)
    return {
        "wait_positive_ratio_ok": bool(wait_ratio >= float(min_wait_positive_ratio)),
        "sell_only_buy_ratio_ok": bool(sell_only_buy_ratio <= float(max_sell_only_buy_ratio)),
        "entered_sell_only_buy_ratio_ok": bool(
            entered_sell_only_buy_ratio <= float(max_entered_sell_only_buy_ratio)
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto re-check entry smoke guard every fixed interval")
    ap.add_argument("--decisions", default=str(DEFAULT_DECISIONS))
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--tail-rows", type=int, default=2500)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--interval-min", type=float, default=15.0)
    ap.add_argument("--max-cycles", type=int, default=8)
    ap.add_argument("--min-wait-positive-ratio", type=float, default=0.20)
    ap.add_argument("--max-sell-only-buy-ratio", type=float, default=0.10)
    ap.add_argument("--max-entered-sell-only-buy-ratio", type=float, default=0.05)
    ap.add_argument("--runtime-status", default=str(DEFAULT_RUNTIME_STATUS))
    ap.add_argument("--require-runtime-fresh", action="store_true")
    ap.add_argument("--runtime-max-age-sec", type=float, default=180.0)
    args = ap.parse_args()

    decisions_csv = Path(args.decisions).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime_status = Path(args.runtime_status).resolve()
    interval_sec = max(5.0, float(args.interval_min) * 60.0)
    max_cycles = max(1, int(args.max_cycles))
    history: list[dict] = []

    for cycle in range(1, max_cycles + 1):
        report = analyze(
            decisions_csv=decisions_csv,
            hours=float(args.hours),
            tail_rows=int(args.tail_rows),
        )
        totals = dict(report.get("totals", {}) or {})
        checks = _build_checks(
            totals=totals,
            min_wait_positive_ratio=float(args.min_wait_positive_ratio),
            max_sell_only_buy_ratio=float(args.max_sell_only_buy_ratio),
            max_entered_sell_only_buy_ratio=float(args.max_entered_sell_only_buy_ratio),
        )
        runtime_ok, runtime_age_sec = _runtime_fresh(runtime_status, float(args.runtime_max_age_sec))
        cycle_ok = bool(all(checks.values()))
        if bool(args.require_runtime_fresh):
            cycle_ok = bool(cycle_ok and runtime_ok)
        snapshot = {
            "cycle": int(cycle),
            "at": datetime.now().isoformat(timespec="seconds"),
            "checks": checks,
            "totals": totals,
            "runtime_status": {
                "path": str(runtime_status),
                "fresh": bool(runtime_ok),
                "age_sec": round(float(runtime_age_sec), 2),
                "required": bool(args.require_runtime_fresh),
                "max_age_sec": float(args.runtime_max_age_sec),
            },
            "ok": bool(cycle_ok),
        }
        history.append(snapshot)
        print(json.dumps(snapshot, ensure_ascii=False))
        if cycle_ok:
            break
        if cycle < max_cycles:
            time.sleep(interval_sec)

    final = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "interval_min": float(args.interval_min),
        "max_cycles": int(max_cycles),
        "thresholds": {
            "min_wait_positive_ratio": float(args.min_wait_positive_ratio),
            "max_sell_only_buy_ratio": float(args.max_sell_only_buy_ratio),
            "max_entered_sell_only_buy_ratio": float(args.max_entered_sell_only_buy_ratio),
        },
        "history": history,
        "ok": bool(history and history[-1].get("ok", False)),
    }
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"entry_smoke_autorecheck_{ts}.json"
    out_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": final["ok"], "report": str(out_path)}, ensure_ascii=False))
    return 0 if final["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
