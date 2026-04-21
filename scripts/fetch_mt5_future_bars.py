from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import MetaTrader5 as mt5

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.trade_constants import (  # noqa: E402
    TIMEFRAME_D1,
    TIMEFRAME_H1,
    TIMEFRAME_H4,
    TIMEFRAME_M1,
    TIMEFRAME_M5,
    TIMEFRAME_M15,
    TIMEFRAME_M30,
)
from backend.integrations.mt5_connection import connect_to_mt5, disconnect_mt5  # noqa: E402


DEFAULT_ENTRY_DECISIONS = PROJECT_ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "market_bars"
DEFAULT_TIMEFRAME = "M15"
DEFAULT_LOOKBACK_BARS = 1
DEFAULT_LOOKAHEAD_BARS = 8

TIMEFRAME_SPECS = {
    "M1": (TIMEFRAME_M1, 60),
    "M5": (TIMEFRAME_M5, 300),
    "M15": (TIMEFRAME_M15, 900),
    "M30": (TIMEFRAME_M30, 1800),
    "H1": (TIMEFRAME_H1, 3600),
    "H4": (TIMEFRAME_H4, 14400),
    "D1": (TIMEFRAME_D1, 86400),
}

OUTPUT_COLUMNS = [
    "symbol",
    "time",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
    "source_timeframe",
]


@dataclass
class AnchorWindow:
    symbol: str
    min_anchor_ts: int
    max_anchor_ts: int
    rows: int = 0


@dataclass
class FutureBarWindow:
    symbol: str
    min_bar_ts: int
    max_bar_ts: int
    rows: int = 0


def _resolve_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _normalize_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _coerce_epoch(value: Any) -> int | None:
    if value in ("", None):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(float(value))
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int(parsed.timestamp())


def _anchor_epoch(row: Mapping[str, Any]) -> int | None:
    signal_bar_ts = _coerce_epoch(row.get("signal_bar_ts"))
    if signal_bar_ts is not None and signal_bar_ts > 0:
        return signal_bar_ts
    return _coerce_epoch(row.get("time"))


def _load_anchor_windows(entry_decisions_path: Path, *, symbols: set[str] | None = None) -> dict[str, AnchorWindow]:
    windows: dict[str, AnchorWindow] = {}
    with entry_decisions_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            symbol = _normalize_symbol(row.get("symbol"))
            if not symbol:
                continue
            if symbols and symbol not in symbols:
                continue
            anchor_ts = _anchor_epoch(row)
            if anchor_ts is None or anchor_ts <= 0:
                continue
            current = windows.get(symbol)
            if current is None:
                windows[symbol] = AnchorWindow(symbol=symbol, min_anchor_ts=anchor_ts, max_anchor_ts=anchor_ts, rows=1)
                continue
            current.min_anchor_ts = min(current.min_anchor_ts, anchor_ts)
            current.max_anchor_ts = max(current.max_anchor_ts, anchor_ts)
            current.rows += 1
    return windows


def _load_existing_future_windows(
    future_bar_path: Path,
    *,
    symbols: set[str] | None = None,
) -> dict[str, FutureBarWindow]:
    if not future_bar_path.exists():
        return {}
    windows: dict[str, FutureBarWindow] = {}
    with future_bar_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            symbol = _normalize_symbol(row.get("symbol"))
            if not symbol:
                continue
            if symbols and symbol not in symbols:
                continue
            bar_ts = _coerce_epoch(row.get("time"))
            if bar_ts is None or bar_ts <= 0:
                continue
            current = windows.get(symbol)
            if current is None:
                windows[symbol] = FutureBarWindow(symbol=symbol, min_bar_ts=bar_ts, max_bar_ts=bar_ts, rows=1)
                continue
            current.min_bar_ts = min(current.min_bar_ts, bar_ts)
            current.max_bar_ts = max(current.max_bar_ts, bar_ts)
            current.rows += 1
    return windows


def _resolve_timeframe_spec(name: str) -> tuple[int, int]:
    key = str(name or DEFAULT_TIMEFRAME).strip().upper()
    if key not in TIMEFRAME_SPECS:
        raise ValueError(f"unsupported timeframe: {name}")
    return TIMEFRAME_SPECS[key]


def _compute_fetch_bounds(
    *,
    min_anchor_ts: int,
    max_anchor_ts: int,
    timeframe_seconds: int,
    lookback_bars: int,
    lookahead_bars: int,
) -> tuple[int, int]:
    start_ts = int(min_anchor_ts) - max(0, int(lookback_bars)) * int(timeframe_seconds)
    end_ts = int(max_anchor_ts) + max(0, int(lookahead_bars)) * int(timeframe_seconds)
    return start_ts, end_ts


def inspect_future_bar_freshness(
    *,
    entry_decisions: str | Path | None = None,
    output_path: str | Path | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    entry_decisions_path = _resolve_path(entry_decisions, DEFAULT_ENTRY_DECISIONS)
    if not entry_decisions_path.exists():
        raise FileNotFoundError(f"entry_decisions source not found: {entry_decisions_path}")

    symbol_filter = {_normalize_symbol(item) for item in list(symbols or []) if _normalize_symbol(item)}
    anchor_windows = _load_anchor_windows(entry_decisions_path, symbols=(symbol_filter or None))
    if not anchor_windows:
        raise ValueError(f"no anchor rows with usable timestamps found under {entry_decisions_path}")

    output_file = _resolve_path(
        output_path,
        DEFAULT_OUTPUT_DIR / f"future_bars_{entry_decisions_path.stem}_{str(timeframe).lower()}.csv",
    )
    future_windows = _load_existing_future_windows(output_file, symbols=(symbol_filter or None))

    per_symbol: dict[str, Any] = {}
    stale_symbols: list[str] = []
    missing_symbols: list[str] = []
    fresh_symbols: list[str] = []
    max_anchor_ts = 0
    max_future_ts = 0
    for symbol, anchor in sorted(anchor_windows.items()):
        future = future_windows.get(symbol)
        symbol_anchor_ts = int(anchor.max_anchor_ts)
        max_anchor_ts = max(max_anchor_ts, symbol_anchor_ts)
        if future is None:
            per_symbol[symbol] = {
                "status": "missing",
                "anchor_rows": int(anchor.rows),
                "max_anchor_ts": symbol_anchor_ts,
                "future_rows": 0,
                "max_future_ts": 0,
                "lag_seconds": None,
            }
            missing_symbols.append(symbol)
            continue
        symbol_future_ts = int(future.max_bar_ts)
        max_future_ts = max(max_future_ts, symbol_future_ts)
        lag_seconds = int(symbol_anchor_ts - symbol_future_ts)
        if symbol_future_ts < symbol_anchor_ts:
            status = "stale"
            stale_symbols.append(symbol)
        else:
            status = "fresh"
            fresh_symbols.append(symbol)
        per_symbol[symbol] = {
            "status": status,
            "anchor_rows": int(anchor.rows),
            "max_anchor_ts": symbol_anchor_ts,
            "future_rows": int(future.rows),
            "max_future_ts": symbol_future_ts,
            "lag_seconds": int(lag_seconds),
        }

    overall_status = "fresh"
    if missing_symbols:
        overall_status = "missing"
    elif stale_symbols:
        overall_status = "stale"

    return {
        "checked_at": datetime.now().astimezone().isoformat(),
        "entry_decisions_path": str(entry_decisions_path),
        "output_path": str(output_file),
        "timeframe": str(timeframe).upper(),
        "status": overall_status,
        "symbols_checked": sorted(anchor_windows.keys()),
        "missing_symbols": missing_symbols,
        "stale_symbols": stale_symbols,
        "fresh_symbols": fresh_symbols,
        "max_anchor_ts": int(max_anchor_ts),
        "max_future_ts": int(max_future_ts),
        "global_lag_seconds": int(max_anchor_ts - max_future_ts) if max_future_ts > 0 else None,
        "per_symbol": per_symbol,
    }


def _rate_field(rate: Any, field: str, default: Any = 0) -> Any:
    if isinstance(rate, Mapping):
        return rate.get(field, default)
    if hasattr(rate, field):
        return getattr(rate, field)
    try:
        return rate[field]
    except Exception:
        return default


def _mt5_rate_to_row(symbol: str, timeframe_name: str, rate: Any) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "time": int(_rate_field(rate, "time", 0) or 0),
        "open": float(_rate_field(rate, "open", 0.0) or 0.0),
        "high": float(_rate_field(rate, "high", 0.0) or 0.0),
        "low": float(_rate_field(rate, "low", 0.0) or 0.0),
        "close": float(_rate_field(rate, "close", 0.0) or 0.0),
        "tick_volume": int(_rate_field(rate, "tick_volume", 0) or 0),
        "spread": int(_rate_field(rate, "spread", 0) or 0),
        "real_volume": int(_rate_field(rate, "real_volume", 0) or 0),
        "source_timeframe": timeframe_name,
    }


def _fetch_symbol_rows(
    *,
    symbol: str,
    timeframe_name: str,
    timeframe_code: int,
    start_ts: int,
    end_ts: int,
) -> list[dict[str, Any]]:
    start_dt = datetime.fromtimestamp(int(start_ts), tz=timezone.utc)
    end_dt = datetime.fromtimestamp(int(end_ts), tz=timezone.utc)
    rates = mt5.copy_rates_range(symbol, timeframe_code, start_dt, end_dt)
    if rates is None:
        return []
    return [_mt5_rate_to_row(symbol, timeframe_name, rate) for rate in rates]


def fetch_mt5_future_bars(
    *,
    entry_decisions: str | Path | None = None,
    output_path: str | Path | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    lookback_bars: int = DEFAULT_LOOKBACK_BARS,
    lookahead_bars: int = DEFAULT_LOOKAHEAD_BARS,
    symbols: list[str] | None = None,
    only_if_stale: bool = False,
) -> dict[str, Any]:
    entry_decisions_path = _resolve_path(entry_decisions, DEFAULT_ENTRY_DECISIONS)
    if not entry_decisions_path.exists():
        raise FileNotFoundError(f"entry_decisions source not found: {entry_decisions_path}")

    timeframe_code, timeframe_seconds = _resolve_timeframe_spec(timeframe)
    symbol_filter = {_normalize_symbol(item) for item in list(symbols or []) if _normalize_symbol(item)}
    windows = _load_anchor_windows(entry_decisions_path, symbols=(symbol_filter or None))
    if not windows:
        raise ValueError(f"no anchor rows with usable timestamps found under {entry_decisions_path}")

    output_file = _resolve_path(
        output_path,
        DEFAULT_OUTPUT_DIR / f"future_bars_{entry_decisions_path.stem}_{str(timeframe).lower()}.csv",
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    freshness_before = inspect_future_bar_freshness(
        entry_decisions=entry_decisions_path,
        output_path=output_file,
        timeframe=timeframe,
        symbols=list(symbol_filter),
    )
    if bool(only_if_stale) and str(freshness_before.get("status", "")).lower() == "fresh":
        return {
            "created_at": datetime.now().astimezone().isoformat(),
            "entry_decisions_path": str(entry_decisions_path),
            "output_path": str(output_file),
            "timeframe": str(timeframe).upper(),
            "timeframe_seconds": int(timeframe_seconds),
            "lookback_bars": int(lookback_bars),
            "lookahead_bars": int(lookahead_bars),
            "symbols_requested": sorted(symbol_filter) if symbol_filter else sorted(windows.keys()),
            "symbols_fetched": [],
            "rows_written": int(
                sum(int((info or {}).get("future_rows", 0) or 0) for info in dict(freshness_before.get("per_symbol", {})).values())
            ),
            "per_symbol": dict(freshness_before.get("per_symbol", {})),
            "skipped": True,
            "skip_reason": "future_bars_already_fresh",
            "freshness_before": freshness_before,
            "freshness_after": freshness_before,
        }

    if not connect_to_mt5():
        raise RuntimeError(f"failed to connect to MT5: {mt5.last_error()}")

    fetched_rows: list[dict[str, Any]] = []
    per_symbol: dict[str, Any] = {}
    try:
        for symbol, window in sorted(windows.items()):
            start_ts, end_ts = _compute_fetch_bounds(
                min_anchor_ts=window.min_anchor_ts,
                max_anchor_ts=window.max_anchor_ts,
                timeframe_seconds=timeframe_seconds,
                lookback_bars=lookback_bars,
                lookahead_bars=lookahead_bars,
            )
            rows = _fetch_symbol_rows(
                symbol=symbol,
                timeframe_name=str(timeframe).upper(),
                timeframe_code=timeframe_code,
                start_ts=start_ts,
                end_ts=end_ts,
            )
            per_symbol[symbol] = {
                "anchor_rows": int(window.rows),
                "min_anchor_ts": int(window.min_anchor_ts),
                "max_anchor_ts": int(window.max_anchor_ts),
                "fetch_start_ts": int(start_ts),
                "fetch_end_ts": int(end_ts),
                "rows_fetched": int(len(rows)),
            }
            fetched_rows.extend(rows)
    finally:
        disconnect_mt5()

    deduped: dict[tuple[str, int], dict[str, Any]] = {}
    for row in fetched_rows:
        key = (_normalize_symbol(row.get("symbol")), int(row.get("time", 0) or 0))
        if key[0] and key[1] > 0:
            deduped[key] = row
    ordered_rows = [deduped[key] for key in sorted(deduped.keys(), key=lambda item: (item[0], item[1]))]

    with output_file.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered_rows)

    freshness_after = inspect_future_bar_freshness(
        entry_decisions=entry_decisions_path,
        output_path=output_file,
        timeframe=timeframe,
        symbols=list(symbol_filter),
    )

    return {
        "created_at": datetime.now().astimezone().isoformat(),
        "entry_decisions_path": str(entry_decisions_path),
        "output_path": str(output_file),
        "timeframe": str(timeframe).upper(),
        "timeframe_seconds": int(timeframe_seconds),
        "lookback_bars": int(lookback_bars),
        "lookahead_bars": int(lookahead_bars),
        "symbols_requested": sorted(symbol_filter) if symbol_filter else sorted(windows.keys()),
        "symbols_fetched": sorted(per_symbol.keys()),
        "rows_written": int(len(ordered_rows)),
        "per_symbol": per_symbol,
        "skipped": False,
        "freshness_before": freshness_before,
        "freshness_after": freshness_after,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch future OHLC bars from MT5 for entry_decisions anchor windows.")
    parser.add_argument("--entry-decisions", default=str(DEFAULT_ENTRY_DECISIONS), help="Path to entry_decisions CSV.")
    parser.add_argument("--output", default="", help="Output CSV path.")
    parser.add_argument("--timeframe", default=DEFAULT_TIMEFRAME, choices=sorted(TIMEFRAME_SPECS.keys()), help="MT5 timeframe.")
    parser.add_argument("--lookback-bars", type=int, default=DEFAULT_LOOKBACK_BARS, help="Bars to include before the earliest anchor.")
    parser.add_argument("--lookahead-bars", type=int, default=DEFAULT_LOOKAHEAD_BARS, help="Bars to include after the latest anchor.")
    parser.add_argument("--symbol", action="append", default=[], help="Optional symbol filter. Repeat for multiple symbols.")
    parser.add_argument("--only-if-stale", action="store_true", help="Skip MT5 fetch when the current future-bar companion already covers the latest anchors.")
    args = parser.parse_args()

    summary = fetch_mt5_future_bars(
        entry_decisions=args.entry_decisions,
        output_path=(args.output or None),
        timeframe=str(args.timeframe),
        lookback_bars=int(args.lookback_bars),
        lookahead_bars=int(args.lookahead_bars),
        symbols=list(args.symbol or []),
        only_if_stale=bool(args.only_if_stale),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
