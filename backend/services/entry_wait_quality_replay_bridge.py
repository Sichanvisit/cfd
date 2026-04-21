"""Replay bridge for entry-side wait quality audit."""

from __future__ import annotations

import csv
import json
from bisect import bisect_right
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.services.entry_wait_quality_audit import (
    ENTRY_WAIT_QUALITY_AUDIT_CONTRACT_V1,
    build_entry_wait_quality_summary_v1,
    evaluate_entry_wait_quality_v1,
    render_entry_wait_quality_markdown,
)
from backend.services.storage_compaction import resolve_entry_decision_detail_path


ENTRY_WAIT_REPLAY_BRIDGE_VERSION = "entry_wait_quality_replay_bridge_v1"
DEFAULT_FUTURE_BAR_COUNT = 8
DEFAULT_CANDIDATE_TRADE_WINDOW = 64
DEFAULT_OUTPUT_DIR = Path("data") / "analysis" / "wait_quality"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _to_epoch(value: object) -> float | None:
    if value in ("", None):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _normalize_side(value: object) -> str:
    side = _to_str(value).upper()
    if side in {"BUY", "SELL"}:
        return side
    return ""


def _row_time(row: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(row)
    for key in ("time", "signal_bar_ts"):
        resolved = _to_epoch(mapped.get(key))
        if resolved is not None and resolved > 0:
            return float(resolved)
    return 0.0


def _signal_bar_ts(row: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(row)
    resolved = _to_epoch(mapped.get("signal_bar_ts"))
    return float(resolved or 0.0)


def _position_key(row: Mapping[str, Any] | None) -> int:
    mapped = _as_mapping(row)
    for key in ("ticket", "position_id"):
        value = _to_int(mapped.get(key), 0)
        if value > 0:
            return value
    return 0


def _extract_side(row: Mapping[str, Any] | None) -> str:
    mapped = _as_mapping(row)
    for key in ("action", "observe_side", "side", "direction", "setup_side"):
        side = _normalize_side(mapped.get(key))
        if side:
            return side
    return ""


def _bridge_group_key(row: Mapping[str, Any] | None) -> str:
    mapped = _as_mapping(row)
    return "|".join(
        [
            _to_str(mapped.get("symbol", "")).upper(),
            str(int(_signal_bar_ts(mapped))),
            _extract_side(mapped),
            _to_str(mapped.get("entry_wait_decision", "")).lower(),
            _to_str(mapped.get("entry_wait_state", "")).upper(),
            _to_str(mapped.get("observe_reason", "")).lower(),
            _to_str(mapped.get("blocked_by", "")).lower(),
        ]
    )


def _is_wait_candidate(row: Mapping[str, Any] | None) -> bool:
    mapped = _as_mapping(row)
    outcome = _to_str(mapped.get("outcome", "")).lower()
    wait_decision = _to_str(mapped.get("entry_wait_decision", "")).lower()
    wait_selected = _to_bool(mapped.get("entry_wait_selected", False))
    wait_state = _to_str(mapped.get("entry_wait_state", "")).upper()
    if wait_selected:
        return True
    if outcome == "wait":
        return True
    if wait_decision.startswith("wait_"):
        return True
    return bool(wait_state and wait_state not in {"", "NONE"} and outcome in {"wait", "skipped"})


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader if isinstance(row, Mapping)]


def _load_detail_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    detail_index: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = str(raw_line or "").strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, Mapping):
                continue
            row_key = _to_str(record.get("row_key", ""))
            payload = record.get("payload", {})
            if row_key and isinstance(payload, Mapping):
                detail_index[row_key] = dict(payload)
    return detail_index


def _merge_detail_payload(
    row: Mapping[str, Any] | None,
    *,
    detail_index: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    merged = dict(row or {})
    if not detail_index:
        return merged
    candidate_keys: list[str] = []
    for key in ("detail_row_key", "decision_row_key", "replay_row_key"):
        value = _to_str(merged.get(key, ""))
        if value and value not in candidate_keys:
            candidate_keys.append(value)
    for candidate_key in candidate_keys:
        payload = _as_mapping(detail_index.get(candidate_key))
        if payload:
            merged.update(payload)
            merged["detail_row_key"] = candidate_key
            return merged
    return merged


def _future_bar_companion_tokens(entry_path: Path) -> list[str]:
    stem = str(entry_path.stem or "").strip()
    tokens = [stem] if stem else []
    if stem.startswith("entry_decisions."):
        suffix = stem.split("entry_decisions.", 1)[1].strip()
        if suffix:
            tokens.append(suffix)
    if stem.startswith("entry_decisions_"):
        suffix = stem.split("entry_decisions_", 1)[1].strip()
        if suffix:
            tokens.append(suffix)
    return list(dict.fromkeys(token for token in tokens if token))


def resolve_default_future_bar_path(entry_path: Path) -> Path | None:
    market_bars_dir = _project_root() / "data" / "market_bars"
    if not market_bars_dir.exists():
        return None
    candidates: list[Path] = []
    for token in _future_bar_companion_tokens(entry_path):
        candidates.extend(sorted(market_bars_dir.glob(f"future_bars_{token}_*.csv")))
    if not candidates:
        candidates.extend(sorted(market_bars_dir.glob("future_bars_entry_decisions_*.csv")))
    if not candidates:
        return None
    candidates = sorted(
        {path.resolve() for path in candidates},
        key=lambda path: (path.stat().st_mtime, str(path)),
        reverse=True,
    )
    return candidates[0] if candidates else None


def _future_bar_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for raw_row in rows:
        row = _as_mapping(raw_row)
        symbol = _to_str(row.get("symbol", "")).upper()
        if symbol:
            index.setdefault(symbol, []).append(row)
    for symbol, symbol_rows in index.items():
        index[symbol] = sorted(symbol_rows, key=lambda item: _to_float(item.get("time"), float("inf")))
    return index


def _candidate_future_bars(
    decision_row: Mapping[str, Any] | None,
    *,
    future_bar_index: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    max_bars: int = DEFAULT_FUTURE_BAR_COUNT,
) -> list[dict[str, Any]]:
    if not future_bar_index:
        return []
    decision = _as_mapping(decision_row)
    symbol = _to_str(decision.get("symbol", "")).upper()
    symbol_rows = list((future_bar_index or {}).get(symbol, []) or [])
    if not symbol_rows:
        return []
    anchor_ts = _signal_bar_ts(decision) or _row_time(decision)
    selected: list[dict[str, Any]] = []
    for row in symbol_rows:
        bar_ts = _to_float(row.get("time"), 0.0)
        if anchor_ts > 0 and bar_ts <= anchor_ts:
            continue
        selected.append(dict(row))
        if len(selected) >= max_bars:
            break
    return selected


def _build_entered_entry_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    by_symbol_times: dict[str, list[float]] = {}
    for raw_row in rows:
        row = _as_mapping(raw_row)
        if _to_str(row.get("outcome", "")).lower() != "entered":
            continue
        symbol = _to_str(row.get("symbol", "")).upper()
        if not symbol:
            continue
        by_symbol.setdefault(symbol, []).append(row)
    for symbol, symbol_rows in by_symbol.items():
        ordered = sorted(symbol_rows, key=_row_time)
        by_symbol[symbol] = ordered
        by_symbol_times[symbol] = [_row_time(item) for item in ordered]
    return {"by_symbol": by_symbol, "by_symbol_times": by_symbol_times}


def _next_entered_row(
    wait_row: Mapping[str, Any] | None,
    *,
    entered_index: Mapping[str, Any],
) -> dict[str, Any]:
    row = _as_mapping(wait_row)
    symbol = _to_str(row.get("symbol", "")).upper()
    side = _extract_side(row)
    if not symbol or not side:
        return {}
    symbol_rows = list((entered_index.get("by_symbol", {}) or {}).get(symbol, []) or [])
    symbol_times = list((entered_index.get("by_symbol_times", {}) or {}).get(symbol, []) or [])
    if not symbol_rows or not symbol_times:
        return {}
    wait_ts = _row_time(row)
    start_index = bisect_right(symbol_times, wait_ts)
    for candidate in symbol_rows[start_index:]:
        if _extract_side(candidate) == side:
            return dict(candidate)
    return {}


def _build_closed_trade_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_trade_link_key: dict[str, dict[str, Any]] = {}
    by_decision_row_key: dict[str, dict[str, Any]] = {}
    by_runtime_snapshot_key: dict[str, dict[str, Any]] = {}
    by_ticket: dict[int, dict[str, Any]] = {}
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    by_symbol_open_ts: dict[str, list[float]] = {}
    for raw_row in rows:
        row = _as_mapping(raw_row)
        trade_link_key = _to_str(row.get("trade_link_key", ""))
        decision_row_key = _to_str(row.get("decision_row_key", ""))
        runtime_snapshot_key = _to_str(row.get("runtime_snapshot_key", ""))
        if trade_link_key:
            by_trade_link_key[trade_link_key] = row
        if decision_row_key:
            by_decision_row_key[decision_row_key] = row
        if runtime_snapshot_key:
            by_runtime_snapshot_key[runtime_snapshot_key] = row
        ticket = _position_key(row)
        if ticket > 0:
            by_ticket[ticket] = row
        symbol = _to_str(row.get("symbol", "")).upper()
        if symbol:
            by_symbol.setdefault(symbol, []).append(row)
    for symbol, symbol_rows in by_symbol.items():
        ordered = sorted(symbol_rows, key=lambda item: _to_float(item.get("open_ts"), float("inf")))
        by_symbol[symbol] = ordered
        by_symbol_open_ts[symbol] = [_to_float(item.get("open_ts"), float("inf")) for item in ordered]
    return {
        "by_trade_link_key": by_trade_link_key,
        "by_decision_row_key": by_decision_row_key,
        "by_runtime_snapshot_key": by_runtime_snapshot_key,
        "by_ticket": by_ticket,
        "by_symbol": by_symbol,
        "by_symbol_open_ts": by_symbol_open_ts,
    }


def _next_closed_trade_row(
    next_entry_row: Mapping[str, Any] | None,
    *,
    closed_trade_index: Mapping[str, Any],
    candidate_window: int = DEFAULT_CANDIDATE_TRADE_WINDOW,
) -> dict[str, Any]:
    entry = _as_mapping(next_entry_row)
    if not entry:
        return {}
    for key_name, index_name in (
        ("trade_link_key", "by_trade_link_key"),
        ("decision_row_key", "by_decision_row_key"),
        ("runtime_snapshot_key", "by_runtime_snapshot_key"),
    ):
        value = _to_str(entry.get(key_name, ""))
        if value:
            matched = _as_mapping((closed_trade_index.get(index_name, {}) or {}).get(value))
            if matched:
                return dict(matched)
    ticket = _position_key(entry)
    if ticket > 0:
        matched = _as_mapping((closed_trade_index.get("by_ticket", {}) or {}).get(ticket))
        if matched:
            return dict(matched)

    symbol = _to_str(entry.get("symbol", "")).upper()
    side = _extract_side(entry)
    symbol_rows = list((closed_trade_index.get("by_symbol", {}) or {}).get(symbol, []) or [])
    symbol_open_ts = list((closed_trade_index.get("by_symbol_open_ts", {}) or {}).get(symbol, []) or [])
    if not symbol_rows or not symbol_open_ts:
        return {}
    anchor_ts = _to_float(entry.get("time"), 0.0) or _signal_bar_ts(entry)
    start_index = bisect_right(symbol_open_ts, anchor_ts)
    for candidate in symbol_rows[start_index : start_index + max(1, int(candidate_window))]:
        if _extract_side(candidate) == side:
            return dict(candidate)
    return {}


def _resolve_anchor_price(
    wait_row: Mapping[str, Any] | None,
    *,
    future_bars: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[float, str]:
    row = _as_mapping(wait_row)
    for key in ("anchor_price", "signal_price", "decision_price", "entry_request_price", "entry_fill_price"):
        value = _to_float(row.get(key), 0.0)
        if value > 0.0:
            return float(value), str(key)
    future = list(future_bars or [])
    if future:
        first_bar = _as_mapping(future[0])
        for key in ("open", "close", "high", "low"):
            value = _to_float(first_bar.get(key), 0.0)
            if value > 0.0:
                return float(value), f"future_bars_first_{key}"
    return 0.0, "missing"


def _resolve_entry_price_from_trade(
    next_entry_row: Mapping[str, Any] | None,
    next_closed_trade_row: Mapping[str, Any] | None,
) -> tuple[float, str]:
    entry = _as_mapping(next_entry_row)
    trade = _as_mapping(next_closed_trade_row)
    for key in ("entry_fill_price", "entry_request_price", "open_price", "price", "close"):
        value = _to_float(entry.get(key), 0.0)
        if value > 0.0:
            return float(value), str(key)
    for key in ("open_price", "entry_fill_price", "entry_request_price"):
        value = _to_float(trade.get(key), 0.0)
        if value > 0.0:
            return float(value), f"closed_trade_{key}"
    return 0.0, "missing"


def _enrich_next_entry_row(
    next_entry_row: Mapping[str, Any] | None,
    next_closed_trade_row: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    entry = dict(_as_mapping(next_entry_row))
    price_value, price_source = _resolve_entry_price_from_trade(entry, next_closed_trade_row)
    if price_value > 0.0:
        entry.setdefault("entry_fill_price", price_value)
        entry.setdefault("entry_request_price", price_value)
    if entry:
        entry["bridged_entry_price_source"] = str(price_source)
    return entry, str(price_source)


def _time_bounds_from_values(values: Sequence[float]) -> dict[str, Any]:
    cleaned = [float(item) for item in values if float(item) > 0.0]
    if not cleaned:
        return {
            "count": 0,
            "min_ts": 0,
            "max_ts": 0,
        }
    return {
        "count": len(cleaned),
        "min_ts": int(min(cleaned)),
        "max_ts": int(max(cleaned)),
    }


def _wait_anchor_bounds(rows: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    wait_rows = [_as_mapping(row) for row in (rows or [])]
    overall = _time_bounds_from_values([(_signal_bar_ts(row) or _row_time(row)) for row in wait_rows])
    by_symbol: dict[str, dict[str, Any]] = {}
    for row in wait_rows:
        symbol = _to_str(row.get("symbol", "")).upper()
        anchor_ts = _signal_bar_ts(row) or _row_time(row)
        if not symbol or anchor_ts <= 0.0:
            continue
        bucket = by_symbol.setdefault(symbol, {"_values": []})
        bucket["_values"].append(float(anchor_ts))
    normalized_by_symbol: dict[str, dict[str, Any]] = {}
    for symbol, payload in by_symbol.items():
        normalized_by_symbol[symbol] = _time_bounds_from_values(list(payload.get("_values", [])))
    return {
        "overall": overall,
        "by_symbol": normalized_by_symbol,
    }


def _future_bar_bounds(rows: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    future_rows = [_as_mapping(row) for row in (rows or [])]
    overall = _time_bounds_from_values([_to_float(row.get("time"), 0.0) for row in future_rows])
    by_symbol: dict[str, dict[str, Any]] = {}
    for row in future_rows:
        symbol = _to_str(row.get("symbol", "")).upper()
        bar_ts = _to_float(row.get("time"), 0.0)
        if not symbol or bar_ts <= 0.0:
            continue
        bucket = by_symbol.setdefault(symbol, {"_values": []})
        bucket["_values"].append(float(bar_ts))
    normalized_by_symbol: dict[str, dict[str, Any]] = {}
    for symbol, payload in by_symbol.items():
        normalized_by_symbol[symbol] = _time_bounds_from_values(list(payload.get("_values", [])))
    return {
        "overall": overall,
        "by_symbol": normalized_by_symbol,
    }


def _future_bar_alignment_summary(
    wait_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
    bridged_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    wait_bounds = _wait_anchor_bounds(wait_rows)
    future_bounds = _future_bar_bounds(future_bar_rows)
    wait_overall = _as_mapping(wait_bounds.get("overall"))
    future_overall = _as_mapping(future_bounds.get("overall"))
    bridged = [_as_mapping(row) for row in (bridged_rows or [])]
    with_future = sum(1 for row in bridged if _to_bool(_as_mapping(row.get("bridge_flags")).get("has_future_bars"), False))
    total_rows = len(bridged)
    if int(_to_int(future_overall.get("count"), 0)) <= 0:
        status = "missing_future_bar_dataset"
    elif int(_to_int(wait_overall.get("count"), 0)) <= 0:
        status = "no_wait_rows"
    elif int(_to_int(future_overall.get("max_ts"), 0)) < int(_to_int(wait_overall.get("min_ts"), 0)):
        status = "stale_before_waits"
    elif int(_to_int(future_overall.get("min_ts"), 0)) > int(_to_int(wait_overall.get("max_ts"), 0)):
        status = "future_after_waits"
    elif with_future <= 0:
        status = "symbol_or_timestamp_mismatch"
    elif with_future < total_rows:
        status = "partial_overlap"
    else:
        status = "covered"

    by_symbol: dict[str, dict[str, Any]] = {}
    wait_by_symbol = _as_mapping(wait_bounds.get("by_symbol"))
    future_by_symbol = _as_mapping(future_bounds.get("by_symbol"))
    bridge_by_symbol_counts: dict[str, dict[str, int]] = {}
    for row in bridged:
        wait_row = _as_mapping(row.get("wait_row"))
        symbol = _to_str(wait_row.get("symbol", "")).upper()
        if not symbol:
            continue
        bucket = bridge_by_symbol_counts.setdefault(symbol, {"rows": 0, "with_future": 0})
        bucket["rows"] += 1
        if _to_bool(_as_mapping(row.get("bridge_flags")).get("has_future_bars"), False):
            bucket["with_future"] += 1

    all_symbols = sorted(set(wait_by_symbol) | set(future_by_symbol) | set(bridge_by_symbol_counts))
    for symbol in all_symbols:
        wait_symbol = _as_mapping(wait_by_symbol.get(symbol))
        future_symbol = _as_mapping(future_by_symbol.get(symbol))
        bridge_symbol = bridge_by_symbol_counts.get(symbol, {"rows": 0, "with_future": 0})
        if int(_to_int(future_symbol.get("count"), 0)) <= 0:
            symbol_status = "missing_future_bar_dataset"
        elif int(_to_int(wait_symbol.get("count"), 0)) <= 0:
            symbol_status = "no_wait_rows"
        elif int(_to_int(future_symbol.get("max_ts"), 0)) < int(_to_int(wait_symbol.get("min_ts"), 0)):
            symbol_status = "stale_before_waits"
        elif int(bridge_symbol.get("with_future", 0)) <= 0:
            symbol_status = "symbol_or_timestamp_mismatch"
        elif int(bridge_symbol.get("with_future", 0)) < int(bridge_symbol.get("rows", 0)):
            symbol_status = "partial_overlap"
        else:
            symbol_status = "covered"
        by_symbol[symbol] = {
            "status": symbol_status,
            "wait_bounds": wait_symbol,
            "future_bounds": future_symbol,
            "bridged_rows": int(bridge_symbol.get("rows", 0)),
            "bridged_rows_with_future": int(bridge_symbol.get("with_future", 0)),
        }

    recommended_action = ""
    if status == "stale_before_waits":
        recommended_action = "Refresh future bars for the current entry_decisions window before trusting move-based wait labels."
    elif status == "missing_future_bar_dataset":
        recommended_action = "Generate a future bars companion file before trusting move-based wait labels."
    elif status == "symbol_or_timestamp_mismatch":
        recommended_action = "Check symbol/time alignment between wait anchors and future bars companion data."
    elif status == "partial_overlap":
        recommended_action = "Extend future bars slightly if you want the newest wait anchors to avoid insufficient_evidence at the tail."

    return {
        "status": status,
        "wait_bounds": wait_bounds,
        "future_bounds": future_bounds,
        "wait_rows_with_future": int(with_future),
        "wait_rows_without_future": max(0, total_rows - with_future),
        "by_symbol": by_symbol,
        "recommended_action": recommended_action,
    }


def build_entry_wait_quality_replay_rows(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]],
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
    dedupe: bool = True,
    max_future_bars: int = DEFAULT_FUTURE_BAR_COUNT,
) -> list[dict[str, Any]]:
    detail_free_rows = [_as_mapping(row) for row in entry_decision_rows]
    wait_candidates = [row for row in detail_free_rows if _is_wait_candidate(row)]
    ordered_wait_candidates = sorted(wait_candidates, key=_row_time)

    if dedupe:
        deduped: dict[str, dict[str, Any]] = {}
        for row in ordered_wait_candidates:
            key = _bridge_group_key(row)
            if key not in deduped:
                deduped[key] = dict(row)
        wait_rows = list(deduped.values())
    else:
        wait_rows = ordered_wait_candidates

    entered_index = _build_entered_entry_index(detail_free_rows)
    closed_index = _build_closed_trade_index(list(closed_trade_rows or []))
    future_index = _future_bar_index(list(future_bar_rows or []))

    bridged_rows: list[dict[str, Any]] = []
    for wait_row in wait_rows:
        future_bars = _candidate_future_bars(wait_row, future_bar_index=future_index, max_bars=max_future_bars)
        anchor_price, anchor_price_source = _resolve_anchor_price(wait_row, future_bars=future_bars)
        wait_row_local = dict(wait_row)
        if anchor_price > 0.0:
            wait_row_local["anchor_price"] = float(anchor_price)
        next_entry_row = _next_entered_row(wait_row_local, entered_index=entered_index)
        next_closed_trade_row = _next_closed_trade_row(next_entry_row, closed_trade_index=closed_index)
        next_entry_row, next_entry_price_source = _enrich_next_entry_row(next_entry_row, next_closed_trade_row)
        audit_result = evaluate_entry_wait_quality_v1(
            decision_row=wait_row_local,
            future_bars=future_bars,
            next_entry_row=next_entry_row,
            next_closed_trade_row=next_closed_trade_row,
        )
        bridged_rows.append(
            {
                "contract_version": ENTRY_WAIT_REPLAY_BRIDGE_VERSION,
                "wait_row": dict(wait_row_local),
                "wait_side": _extract_side(wait_row_local),
                "wait_group_key": _bridge_group_key(wait_row_local),
                "anchor_price": float(anchor_price),
                "anchor_price_source": str(anchor_price_source),
                "future_bars": list(future_bars),
                "future_bar_count": len(future_bars),
                "next_entry_row": dict(next_entry_row),
                "next_closed_trade_row": dict(next_closed_trade_row),
                "bridge_flags": {
                    "has_future_bars": bool(future_bars),
                    "has_next_entry_row": bool(next_entry_row),
                    "has_next_closed_trade_row": bool(next_closed_trade_row),
                    "has_next_entry_price": bool(_to_float(next_entry_row.get("entry_fill_price"), 0.0) > 0.0),
                },
                "next_entry_price_source": str(next_entry_price_source),
                "audit_result": dict(audit_result),
            }
        )
    return bridged_rows


def build_entry_wait_quality_replay_report(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]],
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
    dedupe: bool = True,
    max_future_bars: int = DEFAULT_FUTURE_BAR_COUNT,
) -> dict[str, Any]:
    raw_wait_candidate_count = sum(1 for row in entry_decision_rows if _is_wait_candidate(row))
    bridged_rows = build_entry_wait_quality_replay_rows(
        entry_decision_rows=entry_decision_rows,
        closed_trade_rows=closed_trade_rows,
        future_bar_rows=future_bar_rows,
        dedupe=dedupe,
        max_future_bars=max_future_bars,
    )
    audit_rows = [dict(row.get("audit_result", {}) or {}) for row in bridged_rows]
    summary = build_entry_wait_quality_summary_v1(audit_rows)

    wait_state_counts: dict[str, int] = {}
    wait_decision_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}
    bridge_flag_counts = {
        "has_future_bars": 0,
        "has_next_entry_row": 0,
        "has_next_closed_trade_row": 0,
        "has_next_entry_price": 0,
    }
    for row in bridged_rows:
        wait_row = _as_mapping(row.get("wait_row"))
        flags = _as_mapping(row.get("bridge_flags"))
        symbol = _to_str(wait_row.get("symbol", "")).upper()
        wait_state = _to_str(wait_row.get("entry_wait_state", "")).upper()
        wait_decision = _to_str(wait_row.get("entry_wait_decision", "")).lower()
        if symbol:
            symbol_counts[symbol] = int(symbol_counts.get(symbol, 0)) + 1
        if wait_state:
            wait_state_counts[wait_state] = int(wait_state_counts.get(wait_state, 0)) + 1
        if wait_decision:
            wait_decision_counts[wait_decision] = int(wait_decision_counts.get(wait_decision, 0)) + 1
        for key in list(bridge_flag_counts.keys()):
            if _to_bool(flags.get(key, False)):
                bridge_flag_counts[key] = int(bridge_flag_counts.get(key, 0)) + 1

    future_bar_alignment = _future_bar_alignment_summary(
        [row.get("wait_row", {}) for row in bridged_rows],
        future_bar_rows,
        bridged_rows,
    )

    return {
        "contract_version": ENTRY_WAIT_REPLAY_BRIDGE_VERSION,
        "audit_contract_version": ENTRY_WAIT_QUALITY_AUDIT_CONTRACT_V1,
        "summary": dict(summary),
        "coverage": {
            "raw_wait_candidate_count": int(raw_wait_candidate_count),
            "bridged_row_count": len(bridged_rows),
            "dedupe_applied": bool(dedupe),
            "bridge_flag_counts": dict(bridge_flag_counts),
            "symbol_counts": dict(symbol_counts),
            "wait_state_counts": dict(wait_state_counts),
            "wait_decision_counts": dict(wait_decision_counts),
            "future_bar_alignment": dict(future_bar_alignment),
        },
        "rows": bridged_rows,
    }


def render_entry_wait_quality_replay_markdown(report: Mapping[str, Any] | None = None) -> str:
    payload = _as_mapping(report)
    summary = _as_mapping(payload.get("summary"))
    coverage = _as_mapping(payload.get("coverage"))
    bridge_flag_counts = _as_mapping(coverage.get("bridge_flag_counts"))
    future_bar_alignment = _as_mapping(coverage.get("future_bar_alignment"))
    wait_bounds = _as_mapping(future_bar_alignment.get("wait_bounds"))
    future_bounds = _as_mapping(future_bar_alignment.get("future_bounds"))
    wait_overall = _as_mapping(wait_bounds.get("overall"))
    future_overall = _as_mapping(future_bounds.get("overall"))
    lines = [
        "# Entry Wait Quality Replay Report",
        "",
        f"- raw_wait_candidate_count: {int(_to_int(coverage.get('raw_wait_candidate_count'), 0))}",
        f"- bridged_row_count: {int(_to_int(coverage.get('bridged_row_count'), 0))}",
        f"- dedupe_applied: {bool(coverage.get('dedupe_applied', False))}",
        f"- has_future_bars: {int(_to_int(bridge_flag_counts.get('has_future_bars'), 0))}",
        f"- has_next_entry_row: {int(_to_int(bridge_flag_counts.get('has_next_entry_row'), 0))}",
        f"- has_next_closed_trade_row: {int(_to_int(bridge_flag_counts.get('has_next_closed_trade_row'), 0))}",
        f"- future_bar_alignment_status: {_to_str(future_bar_alignment.get('status', 'unknown'))}",
        f"- wait_anchor_window: {int(_to_int(wait_overall.get('min_ts'), 0))} -> {int(_to_int(wait_overall.get('max_ts'), 0))}",
        f"- future_bar_window: {int(_to_int(future_overall.get('min_ts'), 0))} -> {int(_to_int(future_overall.get('max_ts'), 0))}",
        f"- wait_rows_with_future: {int(_to_int(future_bar_alignment.get('wait_rows_with_future'), 0))}",
        f"- wait_rows_without_future: {int(_to_int(future_bar_alignment.get('wait_rows_without_future'), 0))}",
        "",
        render_entry_wait_quality_markdown(summary).strip(),
        "",
    ]
    lines.append("## Coverage Note")
    recommended_action = _to_str(future_bar_alignment.get("recommended_action", ""))
    if recommended_action:
        lines.append(f"- {recommended_action}")
    else:
        lines.append("- No immediate coverage warning.")
    lines.append("")
    lines.append("## Wait State Counts")
    for key, value in sorted(_as_mapping(coverage.get("wait_state_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.append("")
    lines.append("## Wait Decision Counts")
    for key, value in sorted(_as_mapping(coverage.get("wait_decision_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    return "\n".join(lines).strip() + "\n"


def write_entry_wait_quality_replay_report(
    *,
    entry_decision_path: str | Path | None = None,
    closed_trade_path: str | Path | None = None,
    future_bar_path: str | Path | None = None,
    output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
    dedupe: bool = True,
    max_future_bars: int = DEFAULT_FUTURE_BAR_COUNT,
    limit: int | None = None,
    symbols: Sequence[str] | None = None,
) -> dict[str, Any]:
    entry_path = _resolve_project_path(entry_decision_path, Path("data/trades/entry_decisions.csv"))
    closed_path = _resolve_project_path(closed_trade_path, Path("data/trades/trade_closed_history.csv"))
    future_path = _resolve_project_path(future_bar_path, Path("")) if future_bar_path is not None else None
    future_bar_resolution = "explicit" if future_path is not None else "none"
    if future_path is None:
        resolved_future = resolve_default_future_bar_path(entry_path)
        if resolved_future is not None:
            future_path = resolved_future
            future_bar_resolution = "auto_companion"

    output_file = _resolve_project_path(
        output_path,
        DEFAULT_OUTPUT_DIR / "entry_wait_quality_replay_latest.json",
    )
    markdown_file = _resolve_project_path(
        markdown_output_path,
        DEFAULT_OUTPUT_DIR / "entry_wait_quality_replay_latest.md",
    )

    detail_index = _load_detail_index(resolve_entry_decision_detail_path(entry_path))
    entry_rows = [_merge_detail_payload(row, detail_index=detail_index) for row in _load_csv_rows(entry_path)]
    if symbols:
        symbol_filter = {_to_str(item).upper() for item in list(symbols) if _to_str(item)}
        entry_rows = [row for row in entry_rows if _to_str(row.get("symbol", "")).upper() in symbol_filter]
    if limit is not None:
        entry_rows = entry_rows[: int(limit)]
    closed_rows = _load_csv_rows(closed_path)
    future_rows = _load_csv_rows(future_path) if future_path is not None and future_path.exists() else []

    report = build_entry_wait_quality_replay_report(
        entry_decision_rows=entry_rows,
        closed_trade_rows=closed_rows,
        future_bar_rows=future_rows,
        dedupe=dedupe,
        max_future_bars=max_future_bars,
    )
    report["entry_decision_path"] = str(entry_path)
    report["closed_trade_path"] = str(closed_path)
    report["future_bar_path"] = str(future_path) if future_path is not None else ""
    report["output_path"] = str(output_file)
    report["future_bar_resolution"] = str(future_bar_resolution)
    report["markdown_output_path"] = str(markdown_file)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_file.parent.mkdir(parents=True, exist_ok=True)
    markdown_file.write_text(render_entry_wait_quality_replay_markdown(report), encoding="utf-8")
    return report
