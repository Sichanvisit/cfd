from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path


_TRACKED_EVENT_KINDS = (
    "BUY_WAIT",
    "SELL_WAIT",
    "BUY_PROBE",
    "SELL_PROBE",
    "BUY_READY",
    "SELL_READY",
    "WAIT",
    "BUY_WATCH",
    "SELL_WATCH",
    "ENTER_BUY",
    "ENTER_SELL",
    "EXIT_NOW",
    "HOLD",
)

_PRIMARY_EVENT_KINDS = (
    "BUY_WAIT",
    "SELL_WAIT",
    "BUY_PROBE",
    "SELL_PROBE",
    "BUY_READY",
    "SELL_READY",
    "WAIT",
)

_BUY_FAMILIES = ("BUY_WAIT", "BUY_PROBE", "BUY_READY", "BUY_WATCH")
_SELL_FAMILIES = ("SELL_WAIT", "SELL_PROBE", "SELL_READY", "SELL_WATCH")
_EXIT_FAMILIES = ("EXIT_NOW",)
_ZONE_KEYS = ("LOWER", "MIDDLE", "UPPER", "UNKNOWN")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_chart_flow_distribution_output_path() -> Path:
    raw_path = str(os.getenv("CHART_FLOW_DISTRIBUTION_PATH", "") or "").strip()
    if raw_path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = (_project_root() / path).resolve()
        return path.resolve()
    return (_project_root() / "data" / "analysis" / "chart_flow_distribution_latest.json").resolve()


def _normalize_symbol(symbol: str) -> str:
    return str(symbol or "").strip().upper()


def _normalize_event_kind(kind: str) -> str:
    return str(kind or "").strip().upper()


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return float(parsed) if parsed == parsed else float(default)


def _zone_bucket_for_event(event: dict) -> str:
    box_state = str(event.get("box_state", "") or "").strip().upper()
    bb_state = str(event.get("bb_state", "") or "").strip().upper()

    if box_state in {"LOWER", "LOWER_EDGE", "BELOW"}:
        return "LOWER"
    if box_state in {"MIDDLE", "MID"}:
        return "MIDDLE"
    if box_state in {"UPPER", "UPPER_EDGE", "ABOVE"}:
        return "UPPER"

    if bb_state in {"LOWER", "LOWER_EDGE", "BELOW", "BREAKDOWN"}:
        return "LOWER"
    if bb_state in {"MID", "MIDDLE"}:
        return "MIDDLE"
    if bb_state in {"UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}:
        return "UPPER"
    return "UNKNOWN"


def _load_history_payload(path: Path) -> tuple[str, list[dict]]:
    try:
        payload = json.loads(path.read_text(encoding="ascii"))
    except (OSError, ValueError, TypeError):
        return "", []

    if isinstance(payload, dict):
        symbol = _normalize_symbol(payload.get("symbol", "") or path.stem.replace("_flow_history", ""))
        raw_events = payload.get("events", [])
    elif isinstance(payload, list):
        symbol = _normalize_symbol(path.stem.replace("_flow_history", ""))
        raw_events = payload
    else:
        symbol = _normalize_symbol(path.stem.replace("_flow_history", ""))
        raw_events = []

    events = []
    if isinstance(raw_events, list):
        for event in raw_events:
            if isinstance(event, dict):
                events.append(dict(event))
    return symbol, events


def load_flow_history_by_symbol(save_dir: str | Path) -> dict[str, list[dict]]:
    base = Path(save_dir).resolve()
    if not base.exists():
        return {}
    history_by_symbol: dict[str, list[dict]] = {}
    for path in sorted(base.glob("*_flow_history.json")):
        symbol, events = _load_history_payload(path)
        if symbol:
            history_by_symbol[symbol] = events
    return history_by_symbol


def _slice_events(events: list[dict], *, window_mode: str, window_value: int, now_ts: int | None) -> list[dict]:
    if not events:
        return []
    mode = str(window_mode or "candles").strip().lower()
    value = max(1, int(window_value or 1))
    if mode == "hours":
        latest_ts = max(_safe_int(event.get("ts", 0), 0) for event in events)
        ref_ts = max(_safe_int(now_ts, latest_ts), latest_ts)
        min_ts = ref_ts - (value * 3600)
        return [dict(event) for event in events if _safe_int(event.get("ts", 0), 0) >= min_ts]
    return [dict(event) for event in events[-value:]]


def _presence_ratios(event_counts: dict[str, int]) -> dict[str, float]:
    total_events = sum(int(event_counts.get(kind, 0) or 0) for kind in _PRIMARY_EVENT_KINDS)
    if total_events <= 0:
        return {
            "total_events": 0,
            "buy_presence_ratio": 0.0,
            "sell_presence_ratio": 0.0,
            "neutral_ratio": 0.0,
            "buy_minus_sell": 0.0,
        }
    buy_events = sum(int(event_counts.get(kind, 0) or 0) for kind in _BUY_FAMILIES)
    sell_events = sum(int(event_counts.get(kind, 0) or 0) for kind in _SELL_FAMILIES)
    neutral_events = int(event_counts.get("WAIT", 0) or 0)
    buy_presence_ratio = float(buy_events / total_events)
    sell_presence_ratio = float(sell_events / total_events)
    neutral_ratio = float(neutral_events / total_events)
    return {
        "total_events": int(total_events),
        "buy_presence_ratio": buy_presence_ratio,
        "sell_presence_ratio": sell_presence_ratio,
        "neutral_ratio": neutral_ratio,
        "buy_minus_sell": float(buy_presence_ratio - sell_presence_ratio),
    }


def _empty_zone_counts() -> dict[str, dict[str, int]]:
    return {zone: {kind: 0 for kind in _PRIMARY_EVENT_KINDS} for zone in _ZONE_KEYS}


def _build_symbol_summary(symbol: str, events: list[dict]) -> dict:
    event_counts = Counter()
    zone_counts = _empty_zone_counts()
    strength_level_counts = Counter()
    event_kind_by_strength_level: dict[str, Counter] = {}
    blocked_by_counts = Counter()
    action_none_reason_counts = Counter()
    probe_scene_counts = Counter()
    flat_exit_count = 0
    flat_exit_reasons = Counter()
    flat_exit_events = []

    for raw_event in events:
        event = dict(raw_event or {})
        event_kind = _normalize_event_kind(event.get("event_kind", ""))
        if event_kind:
            event_counts[event_kind] += 1
        zone = _zone_bucket_for_event(event)
        if event_kind in _PRIMARY_EVENT_KINDS:
            zone_counts.setdefault(zone, {kind: 0 for kind in _PRIMARY_EVENT_KINDS})
            zone_counts[zone][event_kind] += 1

        level = _safe_int(event.get("level", event.get("strength_level", 0)), 0)
        if level > 0:
            strength_level_counts[level] += 1
            kind_counter = event_kind_by_strength_level.setdefault(str(level), Counter())
            if event_kind:
                kind_counter[event_kind] += 1

        blocked_by = _normalize_text(event.get("blocked_by", ""))
        if blocked_by:
            blocked_by_counts[blocked_by] += 1
        action_none_reason = _normalize_text(event.get("action_none_reason", ""))
        if action_none_reason:
            action_none_reason_counts[action_none_reason] += 1
        probe_scene_id = _normalize_text(event.get("probe_scene_id", ""))
        if probe_scene_id:
            probe_scene_counts[probe_scene_id] += 1

        my_position_count = _safe_float(event.get("my_position_count", 0.0), 0.0)
        if event_kind in _EXIT_FAMILIES and my_position_count <= 0.0:
            flat_exit_count += 1
            reason = _normalize_text(event.get("reason", "")) or "unknown"
            flat_exit_reasons[reason] += 1
            flat_exit_events.append(
                {
                    "ts": _safe_int(event.get("ts", 0), 0),
                    "reason": reason,
                    "event_kind": event_kind,
                }
            )

    tracked_event_counts = {kind: int(event_counts.get(kind, 0) or 0) for kind in _TRACKED_EVENT_KINDS}
    presence = _presence_ratios(tracked_event_counts)
    zone_presence = {}
    for zone in _ZONE_KEYS:
        zone_presence[zone] = _presence_ratios(zone_counts.get(zone, {}))

    return {
        "symbol": _normalize_symbol(symbol),
        "window_event_count": int(len(events)),
        "latest_event_ts": max((_safe_int(event.get("ts", 0), 0) for event in events), default=0),
        "event_counts": tracked_event_counts,
        "presence": presence,
        "zone_counts": zone_counts,
        "zone_presence": zone_presence,
        "strength_level_counts": {str(level): int(count) for level, count in sorted(strength_level_counts.items())},
        "event_kind_by_strength_level": {
            str(level): {kind: int(count) for kind, count in sorted(counter.items())}
            for level, counter in sorted(event_kind_by_strength_level.items(), key=lambda item: int(item[0]))
        },
        "blocked_by_counts": {str(key): int(count) for key, count in sorted(blocked_by_counts.items())},
        "action_none_reason_counts": {str(key): int(count) for key, count in sorted(action_none_reason_counts.items())},
        "probe_scene_counts": {str(key): int(count) for key, count in sorted(probe_scene_counts.items())},
        "flat_exit_count": int(flat_exit_count),
        "flat_exit_reasons": {str(key): int(count) for key, count in sorted(flat_exit_reasons.items())},
        "flat_exit_events": flat_exit_events,
    }


def build_chart_flow_distribution_report(
    history_by_symbol: dict[str, list[dict]] | None,
    *,
    window_mode: str = "candles",
    window_value: int = 16,
    baseline_mode: str = "override_on",
    now_ts: int | None = None,
) -> dict:
    history_payload = dict(history_by_symbol or {})
    symbols_summary: dict[str, dict] = {}
    global_event_counts = Counter()
    flat_exit_symbols = []

    for symbol, raw_events in sorted(history_payload.items()):
        events = [dict(event) for event in list(raw_events or []) if isinstance(event, dict)]
        sliced = _slice_events(events, window_mode=window_mode, window_value=window_value, now_ts=now_ts)
        summary = _build_symbol_summary(symbol, sliced)
        symbols_summary[_normalize_symbol(symbol)] = summary
        for kind, count in summary.get("event_counts", {}).items():
            global_event_counts[str(kind)] += int(count or 0)
        if int(summary.get("flat_exit_count", 0) or 0) > 0:
            flat_exit_symbols.append(
                {
                    "symbol": _normalize_symbol(symbol),
                    "flat_exit_count": int(summary.get("flat_exit_count", 0) or 0),
                    "reasons": dict(summary.get("flat_exit_reasons", {}) or {}),
                }
            )

    global_event_counts_dict = {kind: int(global_event_counts.get(kind, 0) or 0) for kind in _TRACKED_EVENT_KINDS}
    global_presence = _presence_ratios(global_event_counts_dict)

    for symbol, summary in symbols_summary.items():
        presence = dict(summary.get("presence", {}) or {})
        summary["deviation"] = {
            "buy_deviation": float(presence.get("buy_presence_ratio", 0.0) - global_presence.get("buy_presence_ratio", 0.0)),
            "sell_deviation": float(presence.get("sell_presence_ratio", 0.0) - global_presence.get("sell_presence_ratio", 0.0)),
            "neutral_deviation": float(presence.get("neutral_ratio", 0.0) - global_presence.get("neutral_ratio", 0.0)),
        }

    imbalance_warnings = []
    for symbol, summary in symbols_summary.items():
        presence = dict(summary.get("presence", {}) or {})
        total_events = int(presence.get("total_events", 0) or 0)
        buy_minus_sell = _safe_float(presence.get("buy_minus_sell", 0.0), 0.0)
        if total_events >= 4 and abs(buy_minus_sell) >= 0.35:
            imbalance_warnings.append(
                {
                    "symbol": symbol,
                    "buy_minus_sell": float(buy_minus_sell),
                    "total_events": total_events,
                }
            )

    return {
        "contract_version": "chart_flow_distribution_v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "window": {
            "mode": str(window_mode or "candles"),
            "value": int(max(1, int(window_value or 1))),
        },
        "baseline_mode": str(baseline_mode or "override_on"),
        "symbols": symbols_summary,
        "global_summary": {
            "event_counts": global_event_counts_dict,
            "presence": global_presence,
            "symbol_count": int(len(symbols_summary)),
        },
        "anomalies": {
            "flat_exit_count": int(sum(int(item.get("flat_exit_count", 0) or 0) for item in flat_exit_symbols)),
            "flat_exit_symbols": flat_exit_symbols,
            "extreme_imbalance_symbols": imbalance_warnings,
        },
    }


def write_chart_flow_distribution_report(
    report: dict,
    *,
    output_path: str | Path | None = None,
) -> Path:
    path = Path(output_path).resolve() if output_path else resolve_chart_flow_distribution_output_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def generate_and_write_chart_flow_distribution_report(
    *,
    history_by_symbol: dict[str, list[dict]] | None = None,
    save_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    window_mode: str = "candles",
    window_value: int = 16,
    baseline_mode: str = "override_on",
    now_ts: int | None = None,
) -> tuple[dict, Path]:
    histories = dict(history_by_symbol or {})
    if not histories and save_dir is not None:
        histories = load_flow_history_by_symbol(save_dir)
    report = build_chart_flow_distribution_report(
        histories,
        window_mode=window_mode,
        window_value=window_value,
        baseline_mode=baseline_mode,
        now_ts=now_ts,
    )
    path = write_chart_flow_distribution_report(report, output_path=output_path)
    return report, path
