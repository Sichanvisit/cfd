"""
Collect wait-score runtime snapshots and recommend conservative symbol-specific tuning.

Usage:
  py -3.12 scripts/wait_tuning_probe.py --duration-min 30 --interval-sec 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import Config


@dataclass
class SymState:
    samples: int = 0
    wait_sum: float = 0.0
    wait_conflict_sum: float = 0.0
    wait_noise_sum: float = 0.0
    blocked: Counter | None = None

    def __post_init__(self) -> None:
        if self.blocked is None:
            self.blocked = Counter()


def _now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _read_status(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _sym_float(symbol: str, mapping_name: str, fallback_attr: str, fallback: float) -> float:
    mapping = getattr(Config, mapping_name, {})
    base = float(getattr(Config, fallback_attr, fallback))
    return float(Config.get_symbol_float(symbol, mapping, base))


def _sym_int(symbol: str, mapping_name: str, fallback_attr: str, fallback: int) -> int:
    mapping = getattr(Config, mapping_name, {})
    base = int(getattr(Config, fallback_attr, fallback))
    return int(Config.get_symbol_int(symbol, mapping, base))


def _recommend_for_symbol(symbol: str, st: SymState) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    if st.samples <= 0:
        return recs

    blocked_total = max(1, int(sum(st.blocked.values())))
    hard_block_ratio = float(st.blocked.get("wait_score_hard_block", 0) / blocked_total)
    core_not_passed_ratio = float(st.blocked.get("core_not_passed", 0) / blocked_total)
    max_pos_ratio = float(st.blocked.get("max_positions_reached", 0) / blocked_total)
    mean_wait = float(st.wait_sum / st.samples)
    mean_conflict = float(st.wait_conflict_sum / st.samples)
    mean_noise = float(st.wait_noise_sum / st.samples)

    soft_now = _sym_float(symbol, "ENTRY_WAIT_SOFT_SCORE_BY_SYMBOL", "ENTRY_WAIT_SOFT_SCORE", 45.0)
    hard_now = _sym_float(symbol, "ENTRY_WAIT_HARD_BLOCK_SCORE_BY_SYMBOL", "ENTRY_WAIT_HARD_BLOCK_SCORE", 70.0)
    pen_now = _sym_float(
        symbol,
        "ENTRY_WAIT_PENALTY_PER_POINT_BY_SYMBOL",
        "ENTRY_WAIT_PENALTY_PER_POINT",
        0.28,
    )
    conflict_now = _sym_int(
        symbol,
        "ENTRY_WAIT_CONFLICT_SCORE_BY_SYMBOL",
        "ENTRY_WAIT_CONFLICT_SCORE",
        20,
    )

    # If max-position lock dominates, skip wait tuning for this cycle.
    if max_pos_ratio >= 0.35:
        recs.append(
            {
                "param": "SKIP_WAIT_TUNING",
                "current": None,
                "suggested": None,
                "reason": f"max_positions_reached dominates ({max_pos_ratio:.1%})",
            }
        )
        return recs

    dominant_noise = mean_noise >= max(1.0, mean_conflict * 1.2)

    # Rule A: over-blocking in wait-heavy range -> ease slightly.
    if hard_block_ratio >= 0.08 or (core_not_passed_ratio >= 0.28 and mean_wait >= (soft_now + 3.0)):
        recs.append(
            {
                "param": f"ENTRY_WAIT_SOFT_SCORE_{symbol}",
                "current": round(soft_now, 4),
                "suggested": round(min(soft_now + 2.0, hard_now - 6.0), 4),
                "reason": (
                    f"wait-heavy skips(hard={hard_block_ratio:.1%}, core_not_passed={core_not_passed_ratio:.1%}, "
                    f"mean_wait={mean_wait:.2f})"
                ),
            }
        )
        if dominant_noise:
            recs.append(
                {
                    "param": f"ENTRY_WAIT_PENALTY_PER_POINT_{symbol}",
                    "current": round(pen_now, 4),
                    "suggested": round(max(0.12, pen_now - 0.02), 4),
                    "reason": f"noise dominates wait component(mean_noise={mean_noise:.2f}, mean_conflict={mean_conflict:.2f})",
                }
            )
        else:
            recs.append(
                {
                    "param": f"ENTRY_WAIT_CONFLICT_SCORE_{symbol}",
                    "current": int(conflict_now),
                    "suggested": int(max(6, conflict_now - 2)),
                    "reason": f"conflict component dominates(mean_conflict={mean_conflict:.2f})",
                }
            )
        return recs[:2]

    # Rule B: wait gating too weak -> tighten slightly.
    if hard_block_ratio <= 0.01 and mean_wait <= (soft_now * 0.35):
        recs.append(
            {
                "param": f"ENTRY_WAIT_SOFT_SCORE_{symbol}",
                "current": round(soft_now, 4),
                "suggested": round(max(soft_now - 1.5, 18.0), 4),
                "reason": f"wait gating weak(hard={hard_block_ratio:.1%}, mean_wait={mean_wait:.2f})",
            }
        )
        recs.append(
            {
                "param": f"ENTRY_WAIT_PENALTY_PER_POINT_{symbol}",
                "current": round(pen_now, 4),
                "suggested": round(min(0.60, pen_now + 0.02), 4),
                "reason": "increase soft-penalty slope slightly",
            }
        )
        return recs[:2]

    recs.append(
        {
            "param": "NO_CHANGE",
            "current": None,
            "suggested": None,
            "reason": (
                f"stable window(mean_wait={mean_wait:.2f}, hard={hard_block_ratio:.1%}, "
                f"core_not_passed={core_not_passed_ratio:.1%})"
            ),
        }
    )
    return recs


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect wait-score telemetry and recommend per-symbol tuning.")
    parser.add_argument("--status-file", default="data/runtime_status.json")
    parser.add_argument("--out-dir", default="data/analysis")
    parser.add_argument("--duration-min", type=float, default=30.0)
    parser.add_argument("--interval-sec", type=float, default=5.0)
    parser.add_argument("--symbols", default="NAS100,XAUUSD")
    args = parser.parse_args()

    status_path = Path(args.status_file).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = _now_ts()
    samples_path = out_dir / f"wait_probe_samples_{run_id}.jsonl"
    report_path = out_dir / f"wait_probe_report_{run_id}.json"

    symbols = [s.strip().upper() for s in str(args.symbols).split(",") if s.strip()]
    end_ts = time.time() + max(1.0, float(args.duration_min) * 60.0)
    last_key: set[tuple[str, str]] = set()
    stats: dict[str, SymState] = {s: SymState() for s in symbols}

    while time.time() < end_ts:
        obj = _read_status(status_path)
        updated_at = str(obj.get("updated_at", "") or "")
        latest = obj.get("latest_signal_by_symbol", {}) if isinstance(obj, dict) else {}
        if not isinstance(latest, dict):
            latest = {}

        for symbol in symbols:
            row = latest.get(symbol, {})
            if not isinstance(row, dict):
                continue
            dedup_key = (updated_at, symbol)
            if dedup_key in last_key:
                continue
            last_key.add(dedup_key)

            wait_score = _safe_num(row.get("wait_score", 0.0))
            wait_conflict = _safe_num(row.get("wait_conflict", 0.0))
            wait_noise = _safe_num(row.get("wait_noise", 0.0))
            blocked_by = str(row.get("blocked_by", "") or "")

            rec = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "runtime_updated_at": updated_at,
                "symbol": symbol,
                "wait_score": wait_score,
                "wait_conflict": wait_conflict,
                "wait_noise": wait_noise,
                "blocked_by": blocked_by,
                "core_reason": str(row.get("core_reason", "") or ""),
                "action_none_reason": str(row.get("action_none_reason", "") or ""),
                "can_long": bool(row.get("can_long", False)),
                "can_short": bool(row.get("can_short", False)),
            }
            with samples_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            st = stats[symbol]
            st.samples += 1
            st.wait_sum += wait_score
            st.wait_conflict_sum += wait_conflict
            st.wait_noise_sum += wait_noise
            st.blocked[blocked_by] += 1

        time.sleep(max(0.5, float(args.interval_sec)))

    summary: dict[str, Any] = {"run_id": run_id, "status_file": str(status_path), "duration_min": float(args.duration_min)}
    symbols_out: dict[str, Any] = {}
    for symbol in symbols:
        st = stats[symbol]
        blocked_total = max(1, int(sum(st.blocked.values())))
        sym_out = {
            "samples": int(st.samples),
            "mean_wait_score": round(float(st.wait_sum / max(1, st.samples)), 4),
            "mean_wait_conflict": round(float(st.wait_conflict_sum / max(1, st.samples)), 4),
            "mean_wait_noise": round(float(st.wait_noise_sum / max(1, st.samples)), 4),
            "blocked_by_counts": dict(st.blocked),
            "blocked_by_ratio": {k: round(float(v / blocked_total), 4) for k, v in st.blocked.items()},
            "recommendations": _recommend_for_symbol(symbol, st),
        }
        symbols_out[symbol] = sym_out
    summary["symbols"] = symbols_out
    summary["samples_file"] = str(samples_path)

    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(report_path), "samples": str(samples_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
