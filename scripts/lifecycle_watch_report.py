from __future__ import annotations

import csv
import json
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "data" / "trades" / "entry_decisions.csv"
OPEN_TRADES = ROOT / "data" / "trades" / "trade_history.csv"
CLOSED_TRADES = ROOT / "data" / "trades" / "trade_closed_history.csv"
OUT_DIR = ROOT / "data" / "analysis"


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            continue
    return []


def _tail(rows: list[dict], n: int) -> list[dict]:
    if n <= 0:
        return rows
    return rows[-n:]


def _normalize_symbol(value: str) -> str:
    return str(value or "").upper()


def _parse_dt(value: str):
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _after_since(row: dict, since_dt) -> bool:
    if since_dt is None:
        return True
    for key in ("ts", "timestamp", "time", "created_at", "open_time", "close_time"):
        dt = _parse_dt(row.get(key, ""))
        if dt is not None:
            return dt >= since_dt
    return False


def _is_setup_ticket(value: str, *, exclude_snapshot_restored: bool) -> bool:
    ticket_setup = str(value or "").strip()
    if not ticket_setup:
        return False
    if exclude_snapshot_restored and ticket_setup == "snapshot_restored_auto":
        return False
    return True


def _build_ticket_lifecycle(sym_open: list[dict], sym_closed: list[dict], *, exclude_snapshot_restored: bool) -> list[dict]:
    by_ticket: dict[str, dict] = {}

    for row in sym_open:
        ticket = str(row.get("ticket", "") or "").strip()
        if not ticket:
            continue
        setup_id = str(row.get("entry_setup_id", "") or "").strip()
        if not _is_setup_ticket(setup_id, exclude_snapshot_restored=exclude_snapshot_restored):
            continue
        state = by_ticket.setdefault(ticket, {"ticket": ticket})
        state.update(
            {
                "symbol": row.get("symbol", ""),
                "direction": row.get("direction", ""),
                "status": "OPEN",
                "open_time": row.get("open_time", ""),
                "close_time": "",
                "entry_setup_id": setup_id,
                "entry_wait_state": row.get("entry_wait_state", ""),
                "exit_profile": row.get("exit_profile", ""),
                "decision_winner": "",
                "decision_reason": "",
                "exit_wait_state": "",
                "profit": row.get("profit", ""),
                "peak_profit_at_exit": row.get("peak_profit_at_exit", ""),
            }
        )

    for row in sym_closed:
        ticket = str(row.get("ticket", "") or "").strip()
        if not ticket:
            continue
        setup_id = str(row.get("entry_setup_id", "") or "").strip()
        if not _is_setup_ticket(setup_id, exclude_snapshot_restored=exclude_snapshot_restored):
            continue
        state = by_ticket.setdefault(ticket, {"ticket": ticket})
        state.update(
            {
                "symbol": row.get("symbol", ""),
                "direction": row.get("direction", ""),
                "status": str(row.get("status", "") or "CLOSED").upper() or "CLOSED",
                "open_time": row.get("open_time", state.get("open_time", "")),
                "close_time": row.get("close_time", ""),
                "entry_setup_id": setup_id,
                "entry_wait_state": row.get("entry_wait_state", state.get("entry_wait_state", "")),
                "exit_profile": row.get("exit_profile", row.get("exit_policy_profile", state.get("exit_profile", ""))),
                "decision_winner": row.get("decision_winner", ""),
                "decision_reason": row.get("decision_reason", ""),
                "exit_wait_state": row.get("exit_wait_state", ""),
                "profit": row.get("profit", ""),
                "peak_profit_at_exit": row.get("peak_profit_at_exit", ""),
            }
        )

    def _sort_key(item: dict):
        return _parse_dt(item.get("close_time", "")) or _parse_dt(item.get("open_time", "")) or datetime.min

    return sorted(by_ticket.values(), key=_sort_key)[-10:]


def build_report(
    tail_n: int = 500,
    *,
    exclude_snapshot_restored: bool = False,
    since: str = "",
    symbol_filter: str = "",
    setup_only: bool = False,
) -> dict:
    decisions = _tail(_read_csv(DECISIONS), tail_n)
    open_rows = _read_csv(OPEN_TRADES)
    closed_rows = _tail(_read_csv(CLOSED_TRADES), tail_n)
    since_dt = _parse_dt(since)
    symbol_filter = _normalize_symbol(symbol_filter)

    decisions = [r for r in decisions if _after_since(r, since_dt)]
    open_rows = [r for r in open_rows if _after_since(r, since_dt)]
    closed_rows = [r for r in closed_rows if _after_since(r, since_dt)]

    report: dict = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tail_n": tail_n,
        "exclude_snapshot_restored": bool(exclude_snapshot_restored),
        "since": str(since or ""),
        "symbol_filter": str(symbol_filter or ""),
        "setup_only": bool(setup_only),
        "symbols": {},
        "open_total": 0,
    }

    open_active = [r for r in open_rows if str(r.get("status", "")).upper() == "OPEN"]
    report["open_total"] = len(open_active)

    symbols = sorted(
        {
            *[_normalize_symbol(r.get("symbol", "")) for r in decisions],
            *[_normalize_symbol(r.get("symbol", "")) for r in open_active],
            *[_normalize_symbol(r.get("symbol", "")) for r in closed_rows],
        }
    )

    for symbol in symbols:
        if not symbol:
            continue
        if symbol_filter and symbol != symbol_filter:
            continue
        sym_decisions = [r for r in decisions if _normalize_symbol(r.get("symbol", "")) == symbol]
        sym_open = [r for r in open_active if _normalize_symbol(r.get("symbol", "")) == symbol]
        sym_closed = [r for r in closed_rows if _normalize_symbol(r.get("symbol", "")) == symbol]
        if exclude_snapshot_restored:
            sym_open = [r for r in sym_open if str(r.get("entry_setup_id", "") or "").strip() != "snapshot_restored_auto"]
            sym_closed = [r for r in sym_closed if str(r.get("entry_setup_id", "") or "").strip() != "snapshot_restored_auto"]
        if setup_only:
            sym_decisions = [r for r in sym_decisions if str(r.get("setup_id", "") or "").strip()]
            sym_open = [r for r in sym_open if str(r.get("entry_setup_id", "") or "").strip()]
            sym_closed = [r for r in sym_closed if str(r.get("entry_setup_id", "") or "").strip()]

        outcomes = Counter(str(r.get("outcome", "") or "") for r in sym_decisions)
        blocked = Counter(str(r.get("blocked_by", "") or "") for r in sym_decisions if str(r.get("blocked_by", "") or ""))
        setups = Counter(str(r.get("setup_id", "") or "") for r in sym_decisions if str(r.get("setup_id", "") or ""))
        lifecycle_winners = Counter(str(r.get("decision_winner", "") or "") for r in sym_closed if str(r.get("decision_winner", "") or ""))
        lifecycle_reasons = Counter(str(r.get("decision_reason", "") or "") for r in sym_closed if str(r.get("decision_reason", "") or ""))
        exit_wait_states = Counter(str(r.get("exit_wait_state", "") or "") for r in sym_closed if str(r.get("exit_wait_state", "") or ""))
        ticket_lifecycle = _build_ticket_lifecycle(
            sym_open,
            sym_closed,
            exclude_snapshot_restored=exclude_snapshot_restored,
        )

        open_by_dir = Counter(str(r.get("direction", "") or "") for r in sym_open)
        recent_closed = []
        for r in sym_closed[-5:]:
            recent_closed.append(
                {
                    "ticket": r.get("ticket", ""),
                    "direction": r.get("direction", ""),
                    "close_time": r.get("close_time", ""),
                    "profit": r.get("profit", ""),
                    "entry_setup_id": r.get("entry_setup_id", ""),
                    "decision_winner": r.get("decision_winner", ""),
                    "decision_reason": r.get("decision_reason", ""),
                    "exit_wait_state": r.get("exit_wait_state", ""),
                }
            )

        report["symbols"][symbol] = {
            "decision_rows": len(sym_decisions),
            "entered": int(outcomes.get("entered", 0)),
            "wait": int(outcomes.get("wait", 0)),
            "skipped": int(outcomes.get("skipped", 0)),
            "top_blocked_by": blocked.most_common(8),
            "top_setups": setups.most_common(8),
            "lifecycle_winners": lifecycle_winners.most_common(8),
            "lifecycle_reasons": lifecycle_reasons.most_common(8),
            "support_bounce_exit_count": int(lifecycle_reasons.get("exit_now_support_bounce", 0)),
            "exit_wait_states": exit_wait_states.most_common(8),
            "open_count": len(sym_open),
            "open_by_direction": dict(open_by_dir),
            "recent_open": [
                {
                    "ticket": r.get("ticket", ""),
                    "direction": r.get("direction", ""),
                    "open_time": r.get("open_time", ""),
                    "entry_setup_id": r.get("entry_setup_id", ""),
                    "entry_wait_state": r.get("entry_wait_state", ""),
                    "exit_profile": r.get("exit_profile", ""),
                }
                for r in sym_open[-5:]
            ],
            "recent_closed": recent_closed,
            "recent_ticket_lifecycle": ticket_lifecycle,
            "three_entry_reached": len(sym_open) >= 3 or any(v >= 3 for v in open_by_dir.values()),
        }

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tail", type=int, default=500)
    parser.add_argument("--exclude-snapshot-restored", action="store_true")
    parser.add_argument("--since", type=str, default="")
    parser.add_argument("--symbol", type=str, default="")
    parser.add_argument("--setup-only", action="store_true")
    args = parser.parse_args()

    report = build_report(
        tail_n=int(args.tail),
        exclude_snapshot_restored=bool(args.exclude_snapshot_restored),
        since=str(args.since or ""),
        symbol_filter=str(args.symbol or ""),
        setup_only=bool(args.setup_only),
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"lifecycle_watch_report_{ts}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    for symbol, payload in report["symbols"].items():
        print(
            f"{symbol}: entered={payload['entered']} wait={payload['wait']} "
            f"skipped={payload['skipped']} open={payload['open_count']} three_entry_reached={payload['three_entry_reached']}"
        )


if __name__ == "__main__":
    main()
