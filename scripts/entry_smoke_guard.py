"""
Entry smoke guard checks (regression sentinels).

Checks:
1) wait_score > 0 ratio
2) BUY ratio under preflight_allowed_action == SELL_ONLY
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECISIONS = ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_OUT_DIR = ROOT / "data" / "analysis"


def _to_dt(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat((s or "").strip().lstrip("\ufeff"))
    except Exception:
        return None


def _to_f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _safe_str_map(row: dict[str, Any], key: str) -> str:
    return str((row or {}).get(key, "") or "").strip()


def _canon_symbol(s: str) -> str:
    u = str(s or "").upper()
    if "BTC" in u:
        return "BTCUSD"
    if "XAU" in u or "GOLD" in u:
        return "XAUUSD"
    if "NAS" in u or "US100" in u or "USTEC" in u:
        return "NAS100"
    return u.strip()


def _new_sym_bucket() -> dict[str, Any]:
    return {
        "rows": 0,
        "considered_rows": 0,
        "wait_positive_rows": 0,
        "sell_only_rows": 0,
        "sell_only_buy_rows": 0,
        "sell_only_entered_rows": 0,
        "sell_only_entered_buy_rows": 0,
    }


def _row_value(
    row: list[str],
    mapping: dict[str, int],
    key: str,
    fallback_pos_from_end: int | None = None,
) -> str:
    idx = mapping.get(key, -1)
    if idx >= 0 and idx < len(row):
        return str(row[idx] or "").strip()
    if fallback_pos_from_end is not None:
        pos = len(row) - int(fallback_pos_from_end)
        if pos >= 0 and pos < len(row):
            return str(row[pos] or "").strip()
    return ""


def analyze(decisions_csv: Path, hours: float, tail_rows: int) -> dict[str, Any]:
    now = datetime.now()
    cutoff = now - timedelta(hours=float(max(0.1, hours)))
    rows: list[list[str]] = []
    mapping: dict[str, int] = {}
    with decisions_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        mapping = {str(c).strip(): i for i, c in enumerate(header)}
        for row in reader:
            if not row:
                continue
            dt = _to_dt(_row_value(row, mapping, "time"))
            if dt is None or dt < cutoff:
                continue
            rows.append(row)
    if tail_rows > 0 and len(rows) > tail_rows:
        rows = rows[-tail_rows:]

    total = {
        "rows": 0,
        "considered_rows": 0,
        "wait_positive_rows": 0,
        "sell_only_rows": 0,
        "sell_only_buy_rows": 0,
        "sell_only_entered_rows": 0,
        "sell_only_entered_buy_rows": 0,
    }
    per_symbol: dict[str, dict[str, Any]] = {}

    for row in rows:
        sym = _canon_symbol(_row_value(row, mapping, "symbol"))
        if sym not in per_symbol:
            per_symbol[sym] = _new_sym_bucket()
        b = per_symbol[sym]

        considered = _row_value(row, mapping, "considered")
        is_considered = considered == "1"
        action = _row_value(row, mapping, "action").upper()
        outcome = _row_value(row, mapping, "outcome").lower()
        preflight_allowed = _row_value(row, mapping, "preflight_allowed_action", fallback_pos_from_end=3).upper()
        wait_score = _to_f(_row_value(row, mapping, "wait_score", fallback_pos_from_end=9), 0.0)

        total["rows"] += 1
        b["rows"] += 1
        if is_considered:
            total["considered_rows"] += 1
            b["considered_rows"] += 1
            if wait_score > 0.0:
                total["wait_positive_rows"] += 1
                b["wait_positive_rows"] += 1

        if preflight_allowed == "SELL_ONLY" and action in {"BUY", "SELL"}:
            total["sell_only_rows"] += 1
            b["sell_only_rows"] += 1
            if action == "BUY":
                total["sell_only_buy_rows"] += 1
                b["sell_only_buy_rows"] += 1
            if outcome == "entered":
                total["sell_only_entered_rows"] += 1
                b["sell_only_entered_rows"] += 1
                if action == "BUY":
                    total["sell_only_entered_buy_rows"] += 1
                    b["sell_only_entered_buy_rows"] += 1

    def _ratio(n: int, d: int) -> float:
        return float(n / d) if d > 0 else 0.0

    out_symbols: dict[str, Any] = {}
    for sym, b in sorted(per_symbol.items()):
        out_symbols[sym] = {
            **b,
            "wait_positive_ratio": round(_ratio(b["wait_positive_rows"], b["considered_rows"]), 6),
            "sell_only_buy_ratio": round(_ratio(b["sell_only_buy_rows"], b["sell_only_rows"]), 6),
            "sell_only_entered_buy_ratio": round(
                _ratio(b["sell_only_entered_buy_rows"], b["sell_only_entered_rows"]), 6
            ),
        }

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "window_hours": float(hours),
        "tail_rows_applied": int(tail_rows),
        "totals": {
            **total,
            "wait_positive_ratio": round(_ratio(total["wait_positive_rows"], total["considered_rows"]), 6),
            "sell_only_buy_ratio": round(_ratio(total["sell_only_buy_rows"], total["sell_only_rows"]), 6),
            "sell_only_entered_buy_ratio": round(
                _ratio(total["sell_only_entered_buy_rows"], total["sell_only_entered_rows"]), 6
            ),
        },
        "symbols": out_symbols,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Entry smoke guard checks")
    ap.add_argument("--decisions", default=str(DEFAULT_DECISIONS))
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--tail-rows", type=int, default=2500)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--min-wait-positive-ratio", type=float, default=0.20)
    ap.add_argument("--max-sell-only-buy-ratio", type=float, default=0.10)
    ap.add_argument("--max-entered-sell-only-buy-ratio", type=float, default=0.05)
    args = ap.parse_args()

    decisions_csv = Path(args.decisions).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    report = analyze(
        decisions_csv=decisions_csv,
        hours=float(args.hours),
        tail_rows=int(args.tail_rows),
    )

    totals = dict(report.get("totals", {}) or {})
    wait_ratio = float(totals.get("wait_positive_ratio", 0.0) or 0.0)
    sell_only_buy_ratio = float(totals.get("sell_only_buy_ratio", 0.0) or 0.0)
    entered_sell_only_buy_ratio = float(totals.get("sell_only_entered_buy_ratio", 0.0) or 0.0)

    checks = {
        "wait_positive_ratio_ok": bool(wait_ratio >= float(args.min_wait_positive_ratio)),
        "sell_only_buy_ratio_ok": bool(sell_only_buy_ratio <= float(args.max_sell_only_buy_ratio)),
        "entered_sell_only_buy_ratio_ok": bool(
            entered_sell_only_buy_ratio <= float(args.max_entered_sell_only_buy_ratio)
        ),
    }
    report["thresholds"] = {
        "min_wait_positive_ratio": float(args.min_wait_positive_ratio),
        "max_sell_only_buy_ratio": float(args.max_sell_only_buy_ratio),
        "max_entered_sell_only_buy_ratio": float(args.max_entered_sell_only_buy_ratio),
    }
    report["checks"] = checks
    report["ok"] = bool(all(checks.values()))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"entry_smoke_guard_{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": report["ok"],
                "report": str(out_path),
                "totals": totals,
                "checks": checks,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
