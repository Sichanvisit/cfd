from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "profitability_operations_p2_zero_pnl_gap_audit_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_CLOSED_TRADES_PATH = ROOT / "data" / "trades" / "trade_closed_history.csv"


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except Exception:
            continue
    return []


def _tail(rows: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    if size <= 0 or len(rows) <= size:
        return rows
    return rows[-size:]


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_float(value: Any) -> float | None:
    text = _coerce_text(value)
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _normalize_symbol(value: Any) -> str:
    return _coerce_text(value).upper()


def _normalize_side(value: Any) -> str:
    return _coerce_text(value).upper() or "UNKNOWN"


def _parse_dt(value: Any) -> datetime | None:
    text = _coerce_text(value)
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


def _after_since(row: dict[str, Any], since_dt: datetime | None) -> bool:
    if since_dt is None:
        return True
    for key in ("close_time", "open_time"):
        dt_value = _parse_dt(row.get(key))
        if dt_value is not None:
            return dt_value >= since_dt
    for key in ("close_ts", "open_ts"):
        numeric = _coerce_float(row.get(key))
        if numeric is not None:
            try:
                return datetime.fromtimestamp(numeric) >= since_dt
            except Exception:
                continue
    return False


def _resolve_setup_bucket(row: dict[str, Any]) -> str:
    setup_id = _coerce_text(row.get("entry_setup_id"))
    if setup_id == "snapshot_restored_auto":
        return "snapshot_restored_auto"
    if setup_id:
        return "explicit_setup"
    return "legacy_without_setup"


def _resolve_setup_key(row: dict[str, Any]) -> str:
    setup_id = _coerce_text(row.get("entry_setup_id"))
    if setup_id:
        return setup_id
    direction = _normalize_side(row.get("direction"))
    entry_stage = _coerce_text(row.get("entry_stage")) or "unknown_stage"
    return f"legacy_trade_without_setup_id::{direction}::{entry_stage}"


def _resolve_regime_key(row: dict[str, Any]) -> str:
    return _coerce_text(row.get("regime_at_entry")) or "UNKNOWN_REGIME"


def _resolve_zero_pnl_pattern(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    profit = _coerce_float(row.get("profit"))
    gross = _coerce_float(row.get("gross_pnl"))
    net = _coerce_float(row.get("net_pnl_after_cost"))
    cost = _coerce_float(row.get("cost_total"))

    effective_pnl = net if net is not None else (profit or 0.0)
    if effective_pnl != 0.0:
        return "", {}

    diagnostics = {
        "profit": 0.0 if profit is None else profit,
        "gross_pnl": 0.0 if gross is None else gross,
        "net_pnl_after_cost": 0.0 if net is None else net,
        "cost_total": 0.0 if cost is None else cost,
    }

    if net == 0.0 and profit not in (None, 0.0):
        return "net_zero_overrides_nonzero_profit", diagnostics
    if net == 0.0 and gross not in (None, 0.0):
        return "net_zero_overrides_nonzero_gross", diagnostics
    if profit in (None, 0.0) and gross in (None, 0.0) and net in (None, 0.0):
        return "all_pnl_fields_zero_or_missing", diagnostics
    return "other_zero_pattern", diagnostics


def build_profitability_operations_p2_zero_pnl_gap_audit(
    *,
    closed_trades_path: Path = DEFAULT_CLOSED_TRADES_PATH,
    tail: int = 5000,
    since: str = "",
    symbol_filter: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()
    since_dt = _parse_dt(since)
    symbol_filter = _normalize_symbol(symbol_filter)

    rows = _tail(_read_csv(closed_trades_path), tail)
    rows = [row for row in rows if _after_since(row, since_dt)]

    pattern_counter: Counter[str] = Counter()
    metadata_flags: Counter[str] = Counter()
    bucket_rows: list[dict[str, Any]] = []

    grouped: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}

    for row in rows:
        symbol = _normalize_symbol(row.get("symbol"))
        if not symbol:
            continue
        if symbol_filter and symbol != symbol_filter:
            continue
        pattern, diagnostics = _resolve_zero_pnl_pattern(row)
        if not pattern:
            continue

        setup_bucket = _resolve_setup_bucket(row)
        setup_key = _resolve_setup_key(row)
        regime_key = _resolve_regime_key(row)
        key = (pattern, setup_bucket, symbol, setup_key, regime_key)
        if key not in grouped:
            grouped[key] = {
                "pattern": pattern,
                "setup_bucket": setup_bucket,
                "symbol": symbol,
                "setup_key": setup_key,
                "regime_key": regime_key,
                "zero_pnl_row_count": 0,
                "missing_setup_count": 0,
                "missing_regime_count": 0,
                "missing_decision_winner_count": 0,
                "missing_decision_reason_count": 0,
                "top_decision_winner": Counter(),
                "top_exit_wait_state": Counter(),
                "profit_abs_sum": 0.0,
                "max_abs_profit": 0.0,
            }

        bucket = grouped[key]
        bucket["zero_pnl_row_count"] += 1
        pattern_counter[pattern] += 1

        setup_id = _coerce_text(row.get("entry_setup_id"))
        regime = _coerce_text(row.get("regime_at_entry"))
        decision_winner = _coerce_text(row.get("decision_winner"))
        decision_reason = _coerce_text(row.get("decision_reason"))
        exit_wait_state = _coerce_text(row.get("exit_wait_state"))
        profit_value = abs(float(diagnostics["profit"]))

        if not setup_id:
            bucket["missing_setup_count"] += 1
            metadata_flags["missing_setup"] += 1
        if not regime:
            bucket["missing_regime_count"] += 1
            metadata_flags["missing_regime"] += 1
        if not decision_winner:
            bucket["missing_decision_winner_count"] += 1
            metadata_flags["missing_decision_winner"] += 1
        if not decision_reason:
            bucket["missing_decision_reason_count"] += 1
            metadata_flags["missing_decision_reason"] += 1
        if decision_winner:
            bucket["top_decision_winner"][decision_winner] += 1
        if exit_wait_state:
            bucket["top_exit_wait_state"][exit_wait_state] += 1

        bucket["profit_abs_sum"] += profit_value
        bucket["max_abs_profit"] = max(float(bucket["max_abs_profit"]), profit_value)

    for bucket in grouped.values():
        count = int(bucket["zero_pnl_row_count"])
        bucket_rows.append(
            {
                "pattern": bucket["pattern"],
                "setup_bucket": bucket["setup_bucket"],
                "symbol": bucket["symbol"],
                "setup_key": bucket["setup_key"],
                "regime_key": bucket["regime_key"],
                "zero_pnl_row_count": count,
                "missing_setup_ratio": round(bucket["missing_setup_count"] / count, 4) if count else 0.0,
                "missing_regime_ratio": round(bucket["missing_regime_count"] / count, 4) if count else 0.0,
                "missing_decision_winner_ratio": round(bucket["missing_decision_winner_count"] / count, 4) if count else 0.0,
                "missing_decision_reason_ratio": round(bucket["missing_decision_reason_count"] / count, 4) if count else 0.0,
                "profit_abs_sum": round(float(bucket["profit_abs_sum"]), 4),
                "avg_abs_profit": round(float(bucket["profit_abs_sum"]) / count, 4) if count else 0.0,
                "max_abs_profit": round(float(bucket["max_abs_profit"]), 4),
                "top_decision_winner": bucket["top_decision_winner"].most_common(1)[0][0] if bucket["top_decision_winner"] else "",
                "top_exit_wait_state": bucket["top_exit_wait_state"].most_common(1)[0][0] if bucket["top_exit_wait_state"] else "",
            }
        )

    bucket_rows = sorted(
        bucket_rows,
        key=lambda row: (-int(row["zero_pnl_row_count"]), -float(row["profit_abs_sum"]), row["symbol"], row["setup_key"]),
    )

    suspicious_buckets = bucket_rows[:10]
    top_concerns = [
        f"{row['symbol']} / {row['setup_key']} / {row['regime_key']} | {row['pattern']} | rows={row['zero_pnl_row_count']} | avg_abs_profit={row['avg_abs_profit']}"
        for row in suspicious_buckets[:3]
    ]

    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "tail": tail,
            "since": _coerce_text(since),
            "symbol_filter": symbol_filter,
            "closed_trades_path": str(closed_trades_path),
        },
        "audit_summary": {
            "zero_pnl_row_count": sum(pattern_counter.values()),
            "top_pattern": pattern_counter.most_common(1)[0][0] if pattern_counter else "",
            "pattern_count": len(pattern_counter),
            "suspicious_bucket_count": len(bucket_rows),
        },
        "pattern_summary": [
            {"pattern": pattern, "count": count}
            for pattern, count in pattern_counter.most_common()
        ],
        "metadata_gap_summary": [
            {"flag": flag, "count": count}
            for flag, count in metadata_flags.most_common()
        ],
        "bucket_summary": bucket_rows,
        "suspicious_zero_pnl_buckets": suspicious_buckets,
        "quick_read_summary": {
            "top_concerns": top_concerns,
            "next_review_queue": [
                f"{row['symbol']} / {row['setup_key']} / {row['regime_key']}"
                for row in suspicious_buckets[:3]
            ],
        },
    }


def write_profitability_operations_p2_zero_pnl_gap_audit(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    closed_trades_path: Path = DEFAULT_CLOSED_TRADES_PATH,
    tail: int = 5000,
    since: str = "",
    symbol_filter: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_profitability_operations_p2_zero_pnl_gap_audit(
        closed_trades_path=closed_trades_path,
        tail=tail,
        since=since,
        symbol_filter=symbol_filter,
        now=now,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p2_zero_pnl_gap_audit_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p2_zero_pnl_gap_audit_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p2_zero_pnl_gap_audit_latest.md"

    latest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_rows = report["bucket_summary"]
    fieldnames = list(csv_rows[0].keys()) if csv_rows else [
        "pattern",
        "setup_bucket",
        "symbol",
        "setup_key",
        "regime_key",
        "zero_pnl_row_count",
        "missing_setup_ratio",
        "missing_regime_ratio",
        "missing_decision_winner_ratio",
        "missing_decision_reason_ratio",
        "profit_abs_sum",
        "avg_abs_profit",
        "max_abs_profit",
        "top_decision_winner",
        "top_exit_wait_state",
    ]
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    markdown_lines = [
        "# Profitability / Operations P2 Zero PnL Gap Audit",
        "",
        f"- `report_version`: `{report['report_version']}`",
        f"- `generated_at`: `{report['generated_at']}`",
        f"- `zero_pnl_row_count`: `{report['audit_summary']['zero_pnl_row_count']}`",
        f"- `top_pattern`: `{report['audit_summary']['top_pattern']}`",
        "",
        "## Top Concerns",
    ]
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_concerns"] or ["(none)"])])
    markdown_lines.extend(["", "## Pattern Summary"])
    for row in report["pattern_summary"][:10]:
        markdown_lines.append(f"- `{row['pattern']}` | count={row['count']}")
    markdown_lines.extend(["", "## Metadata Gap Summary"])
    for row in report["metadata_gap_summary"][:10]:
        markdown_lines.append(f"- `{row['flag']}` | count={row['count']}")
    latest_markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "suspicious_bucket_count": len(report["suspicious_zero_pnl_buckets"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tail", type=int, default=5000)
    parser.add_argument("--since", type=str, default="")
    parser.add_argument("--symbol", type=str, default="")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = write_profitability_operations_p2_zero_pnl_gap_audit(
        output_dir=args.output_dir,
        closed_trades_path=DEFAULT_CLOSED_TRADES_PATH,
        tail=args.tail,
        since=args.since,
        symbol_filter=args.symbol,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
