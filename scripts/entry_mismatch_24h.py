"""
24h entry mismatch/proxy report for NAS100/XAUUSD.

- Reads data/trades/entry_decisions.csv positionally (robust to mixed headers).
- Computes:
  1) entered mismatch ratio (if enough entered rows with extended fields)
  2) candidate mismatch proxy ratio (for action-selected rows)
  3) blocked_by distribution
- Emits one-tweak suggestion per symbol focused on ENTRY_WAIT_* / ENTRY_BOX_CONTRA_*.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import Config


def _sym_float(symbol: str, mapping_name: str, fallback_attr: str, fallback: float) -> float:
    mapping = getattr(Config, mapping_name, {})
    base = float(getattr(Config, fallback_attr, fallback))
    return float(Config.get_symbol_float(symbol, mapping, base))


def analyze(path: Path, hours: float = 24.0) -> dict[str, Any]:
    now = datetime.now()
    cut = now - timedelta(hours=float(hours))
    syms = ["NAS100", "XAUUSD"]

    stats: dict[str, dict[str, Any]] = {
        s: {
            "rows": 0,
            "entered_rows": 0,
            "entered_mismatch": 0,
            "candidate_rows": 0,
            "candidate_mismatch": 0,
            "blocked_by": Counter(),
            "mismatch_reasons_entered": Counter(),
            "mismatch_reasons_candidate": Counter(),
        }
        for s in syms
    }

    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        _ = next(r, None)
        for row in r:
            if len(row) < 6:
                continue
            try:
                dt = datetime.fromisoformat((row[0] or "").strip().lstrip("\ufeff"))
            except Exception:
                continue
            if dt < cut:
                continue
            sym = (row[1] or "").strip().upper()
            if sym not in stats:
                continue

            st = stats[sym]
            st["rows"] += 1
            outcome = (row[4] or "").strip().lower()
            blocked_by = (row[5] or "").strip() or "(none)"
            st["blocked_by"][blocked_by] += 1

            # Extended fields only available on newer rows.
            if len(row) < 41:
                continue
            action = (row[2] or "").strip().upper()
            if action not in {"BUY", "SELL"}:
                continue

            box_state = (row[-10] or "").strip().upper()
            try:
                wait_score = float((row[-9] or "0").strip() or 0.0)
            except Exception:
                wait_score = 0.0
            wait_soft = _sym_float(sym, "ENTRY_WAIT_SOFT_SCORE_BY_SYMBOL", "ENTRY_WAIT_SOFT_SCORE", 45.0)

            reasons = []
            if box_state == "MIDDLE":
                reasons.append("middle")
            if action == "BUY" and box_state in {"UPPER", "ABOVE"}:
                reasons.append("buy_at_upper")
            if action == "SELL" and box_state in {"LOWER", "BELOW"}:
                reasons.append("sell_at_lower")
            if wait_score >= wait_soft:
                reasons.append("high_wait")

            st["candidate_rows"] += 1
            if reasons:
                st["candidate_mismatch"] += 1
                for x in reasons:
                    st["mismatch_reasons_candidate"][x] += 1

            if outcome == "entered":
                st["entered_rows"] += 1
                if reasons:
                    st["entered_mismatch"] += 1
                    for x in reasons:
                        st["mismatch_reasons_entered"][x] += 1

    out: dict[str, Any] = {"window_hours": float(hours), "generated_at": now.isoformat(timespec="seconds"), "symbols": {}}
    for sym in syms:
        st = stats[sym]
        entered_n = int(st["entered_rows"])
        cand_n = int(st["candidate_rows"])
        entered_ratio = float(st["entered_mismatch"] / entered_n) if entered_n else None
        cand_ratio = float(st["candidate_mismatch"] / cand_n) if cand_n else None

        # One-parameter suggestion per symbol in requested families.
        suggestion = {"param": "NO_CHANGE", "current": None, "suggested": None, "reason": "insufficient/neutral"}
        blocks = st["blocked_by"]
        block_total = max(1, int(sum(blocks.values())))
        block_core = float(blocks.get("core_not_passed", 0) / block_total)
        block_util = float(blocks.get("utility_below_u_min", 0) / block_total)

        if cand_ratio is not None and cand_ratio >= 0.55:
            cur = _sym_float(sym, "ENTRY_WAIT_SOFT_SCORE_BY_SYMBOL", "ENTRY_WAIT_SOFT_SCORE", 45.0)
            suggestion = {
                "param": f"ENTRY_WAIT_SOFT_SCORE_{sym}",
                "current": round(cur, 4),
                "suggested": round(max(18.0, cur - 2.0), 4),
                "reason": f"candidate mismatch high ({cand_ratio:.1%})",
            }
        elif block_util >= 0.60:
            cur = _sym_float(sym, "ENTRY_WAIT_SOFT_SCORE_BY_SYMBOL", "ENTRY_WAIT_SOFT_SCORE", 45.0)
            suggestion = {
                "param": f"ENTRY_WAIT_SOFT_SCORE_{sym}",
                "current": round(cur, 4),
                "suggested": round(cur + 2.0, 4),
                "reason": f"utility blocks dominate ({block_util:.1%})",
            }
        elif block_core >= 0.40:
            cur = _sym_float(sym, "ENTRY_BOX_CONTRA_PENALTY_BY_SYMBOL", "ENTRY_BOX_CONTRA_PENALTY", 18.0)
            suggestion = {
                "param": f"ENTRY_BOX_CONTRA_PENALTY_{sym}",
                "current": round(cur, 4),
                "suggested": round(max(6.0, cur - 2.0), 4),
                "reason": f"core_not_passed high ({block_core:.1%})",
            }

        out["symbols"][sym] = {
            "rows_24h": int(st["rows"]),
            "entered_rows_24h": entered_n,
            "entered_mismatch_ratio": entered_ratio,
            "candidate_rows_24h": cand_n,
            "candidate_mismatch_proxy_ratio": cand_ratio,
            "blocked_by_top": dict(st["blocked_by"].most_common(8)),
            "mismatch_reasons_entered": dict(st["mismatch_reasons_entered"]),
            "mismatch_reasons_candidate": dict(st["mismatch_reasons_candidate"]),
            "suggestion": suggestion,
        }
    return out


def main() -> int:
    src = ROOT / "data" / "trades" / "entry_decisions.csv"
    out_dir = ROOT / "data" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = analyze(src, hours=24.0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"entry_mismatch_24h_{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(out_path), "summary": report["symbols"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

