"""Guarded runtime recycle helpers for long-running trading loops."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import time
from typing import Any, Mapping

from backend.services.runtime_signal_surface import build_position_energy_surface_v1


RUNTIME_RECYCLE_CONTRACT_VERSION = "runtime_recycle_v1"
RUNTIME_RECYCLE_HEALTH_CONTRACT_VERSION = "runtime_recycle_health_v1"
RUNTIME_RECYCLE_DRIFT_CONTRACT_VERSION = "runtime_recycle_drift_v1"
RUNTIME_RECYCLE_MODE_DISABLED = "disabled"
RUNTIME_RECYCLE_MODE_LOG_ONLY = "log_only"
RUNTIME_RECYCLE_MODE_REEXEC = "reexec"

_MODE_ALIASES = {
    "": RUNTIME_RECYCLE_MODE_DISABLED,
    "0": RUNTIME_RECYCLE_MODE_DISABLED,
    "false": RUNTIME_RECYCLE_MODE_DISABLED,
    "off": RUNTIME_RECYCLE_MODE_DISABLED,
    "disabled": RUNTIME_RECYCLE_MODE_DISABLED,
    "dry_run": RUNTIME_RECYCLE_MODE_LOG_ONLY,
    "log": RUNTIME_RECYCLE_MODE_LOG_ONLY,
    "log_only": RUNTIME_RECYCLE_MODE_LOG_ONLY,
    "observe": RUNTIME_RECYCLE_MODE_LOG_ONLY,
    "reload": RUNTIME_RECYCLE_MODE_REEXEC,
    "reexec": RUNTIME_RECYCLE_MODE_REEXEC,
    "restart": RUNTIME_RECYCLE_MODE_REEXEC,
}

_DRIFT_STAGE_STATES = {"OBSERVE", "BLOCKED", "PROBE", "NONE"}
_DRIFT_DECISION_STATES = {"WAIT", "BLOCKED", "MONITOR", "DISPLAY_READY"}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(text)


def _normalize_mode(value: Any) -> str:
    key = str(value or "").strip().lower()
    return _MODE_ALIASES.get(key, RUNTIME_RECYCLE_MODE_DISABLED)


def _iso(ts: float) -> str:
    if float(ts or 0.0) <= 0.0:
        return ""
    try:
        return datetime.fromtimestamp(float(ts)).isoformat(timespec="seconds")
    except Exception:
        return ""


def _safe_div(numerator: float, denominator: float) -> float:
    denom = float(denominator or 0.0)
    if denom <= 0.0:
        return 0.0
    return float(numerator) / denom


def _coerce_counter_map(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    payload: dict[str, int] = {}
    for key, raw in value.items():
        name = str(key or "").strip()
        count = max(0, _to_int(raw, 0))
        if name and count > 0:
            payload[name] = int(count)
    return payload


def _dominant_entry(counter_map: Mapping[str, int] | None, *, total: int) -> dict[str, Any]:
    payload = _coerce_counter_map(counter_map)
    if not payload or int(total or 0) <= 0:
        return {"label": "", "count": 0, "ratio": 0.0}
    label, count = max(payload.items(), key=lambda item: int(item[1]))
    return {
        "label": str(label or ""),
        "count": int(count or 0),
        "ratio": round(_safe_div(int(count or 0), int(total or 0)), 4),
    }


def _decision_state_counts(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for _, raw_row in dict(latest_signal_by_symbol or {}).items():
        if not isinstance(raw_row, Mapping):
            continue
        decision_state = str(
            (
                build_position_energy_surface_v1(raw_row)
                .get("summary", {})
                .get("decision_state", "")
            )
            or ""
        ).strip().upper()
        if decision_state:
            counter[decision_state] += 1
    return {str(key): int(value) for key, value in counter.items() if int(value) > 0}


def build_runtime_recycle_health_v1(
    *,
    recent_runtime_summary: Mapping[str, Any] | None = None,
    default_recent_window: Mapping[str, Any] | None = None,
    latest_signal_by_symbol: Mapping[str, Any] | None = None,
    now_ts: float | None = None,
    signal_stale_sec: int = 900,
) -> dict[str, Any]:
    now = float(time.time() if now_ts is None else now_ts)
    summary = dict(recent_runtime_summary or {})
    window = dict(default_recent_window or {})
    latest_rows = dict(latest_signal_by_symbol or {})
    stale_after_sec = max(1, int(signal_stale_sec or 0))

    signal_age_by_symbol: dict[str, int | None] = {}
    stale_symbols: list[str] = []
    fresh_symbol_count = 0
    max_signal_age_sec = 0
    for symbol, raw_row in latest_rows.items():
        row = dict(raw_row or {}) if isinstance(raw_row, Mapping) else {}
        symbol_name = str(symbol or row.get("symbol") or "").strip().upper()
        if not symbol_name:
            continue
        runtime_snapshot_ts = _to_float(
            row.get("runtime_snapshot_generated_ts")
            or row.get("time")
            or row.get("timestamp_ts"),
            0.0,
        )
        if runtime_snapshot_ts <= 0.0:
            signal_age_by_symbol[symbol_name] = None
            stale_symbols.append(symbol_name)
            continue
        age_sec = max(0, int(now - runtime_snapshot_ts))
        signal_age_by_symbol[symbol_name] = int(age_sec)
        max_signal_age_sec = max(max_signal_age_sec, int(age_sec))
        if age_sec >= stale_after_sec:
            stale_symbols.append(symbol_name)
        else:
            fresh_symbol_count += 1

    signal_row_count = len(signal_age_by_symbol)
    stale_symbol_count = len(stale_symbols)
    state = "healthy"
    reason = "fresh_live_signal_rows"
    trigger_recommended = False

    if signal_row_count <= 0:
        state = "insufficient"
        reason = "no_live_signal_rows"
    elif stale_symbol_count >= signal_row_count:
        state = "stale"
        reason = "all_live_signal_rows_stale"
        trigger_recommended = True
    elif stale_symbol_count > 0:
        state = "degraded"
        reason = "partial_live_signal_rows_stale"

    if not bool(summary.get("available", False)):
        if state == "healthy":
            state = "insufficient"
            reason = str(summary.get("reason", "") or "summary_unavailable")
    elif int(window.get("row_count", 0) or 0) <= 0 and state == "healthy":
        state = "watch"
        reason = "summary_empty"

    return {
        "contract_version": RUNTIME_RECYCLE_HEALTH_CONTRACT_VERSION,
        "state": str(state),
        "reason": str(reason),
        "trigger_recommended": bool(trigger_recommended),
        "signal_stale_sec": int(stale_after_sec),
        "summary_available": bool(summary.get("available", False)),
        "summary_reason": str(summary.get("reason", "") or ""),
        "recent_row_count": int(window.get("row_count", 0) or 0),
        "live_symbol_count": int(signal_row_count),
        "fresh_symbol_count": int(fresh_symbol_count),
        "stale_symbol_count": int(stale_symbol_count),
        "stale_symbols": stale_symbols,
        "max_signal_age_sec": int(max_signal_age_sec),
        "signal_age_by_symbol": signal_age_by_symbol,
    }


def build_runtime_recycle_drift_v1(
    *,
    recent_runtime_summary: Mapping[str, Any] | None = None,
    default_recent_window: Mapping[str, Any] | None = None,
    latest_signal_by_symbol: Mapping[str, Any] | None = None,
    now_ts: float | None = None,
    min_rows: int = 40,
    stage_dominance_threshold: float = 0.85,
    block_dominance_threshold: float = 0.85,
    decision_dominance_threshold: float = 0.90,
    min_signal_count: int = 2,
) -> dict[str, Any]:
    del now_ts  # reserved for future drift freshness features
    summary = dict(recent_runtime_summary or {})
    window = dict(default_recent_window or {})
    row_count = max(0, int(window.get("row_count", 0) or 0))
    min_required_rows = max(1, int(min_rows or 0))
    required_signal_count = max(1, int(min_signal_count or 0))

    stage_counts = _coerce_counter_map(window.get("stage_counts", {}))
    blocked_reason_counts = _coerce_counter_map(window.get("blocked_reason_counts", {}))
    display_ready_summary = dict(window.get("display_ready_summary", {}) or {})
    wait_bridge_summary = dict(window.get("wait_state_decision_bridge_summary", {}) or {})
    decision_state_counts = _decision_state_counts(latest_signal_by_symbol)

    blocked_row_count = max(0, _to_int(display_ready_summary.get("blocked_row_count"), 0))
    entry_ready_true = max(0, _to_int(display_ready_summary.get("entry_ready_true"), 0))
    display_ready_true = max(0, _to_int(display_ready_summary.get("display_ready_true"), 0))
    bridge_row_count = max(0, _to_int(wait_bridge_summary.get("bridge_row_count"), 0))
    state_to_decision_counts = _coerce_counter_map(wait_bridge_summary.get("state_to_decision_counts", {}))

    stage_dominance = _dominant_entry(stage_counts, total=row_count)
    blocked_reason_dominance = _dominant_entry(blocked_reason_counts, total=blocked_row_count)
    bridge_dominance = _dominant_entry(state_to_decision_counts, total=bridge_row_count)
    decision_state_total = sum(int(value) for value in decision_state_counts.values())
    decision_state_dominance = _dominant_entry(decision_state_counts, total=decision_state_total)

    signals: list[str] = []
    reasons: list[str] = []

    if row_count < min_required_rows:
        state = "insufficient"
        reason = "insufficient_rows"
        trigger_recommended = False
    elif not bool(summary.get("available", False)):
        state = "insufficient"
        reason = str(summary.get("reason", "") or "summary_unavailable")
        trigger_recommended = False
    else:
        stage_label = str(stage_dominance.get("label", "") or "").upper()
        stage_ratio = _to_float(stage_dominance.get("ratio"), 0.0)
        if stage_label in _DRIFT_STAGE_STATES and stage_ratio >= float(stage_dominance_threshold):
            signals.append("stage_lock")
            reasons.append(f"stage_lock:{stage_label}:{stage_ratio:.2f}")

        block_label = str(blocked_reason_dominance.get("label", "") or "")
        block_ratio = _to_float(blocked_reason_dominance.get("ratio"), 0.0)
        if block_label and blocked_row_count >= max(8, min_required_rows // 3) and block_ratio >= float(block_dominance_threshold):
            signals.append("blocked_reason_lock")
            reasons.append(f"blocked_reason_lock:{block_label}:{block_ratio:.2f}")

        bridge_label = str(bridge_dominance.get("label", "") or "")
        bridge_ratio = _to_float(bridge_dominance.get("ratio"), 0.0)
        bridge_is_wait_like = "->skip" in bridge_label.lower() or "->wait" in bridge_label.lower()
        if bridge_label and bridge_row_count >= max(8, min_required_rows // 3) and bridge_ratio >= float(block_dominance_threshold) and bridge_is_wait_like:
            signals.append("wait_bridge_lock")
            reasons.append(f"wait_bridge_lock:{bridge_label}:{bridge_ratio:.2f}")

        decision_label = str(decision_state_dominance.get("label", "") or "").upper()
        decision_ratio = _to_float(decision_state_dominance.get("ratio"), 0.0)
        if decision_label in _DRIFT_DECISION_STATES and decision_state_total >= 2 and decision_ratio >= float(decision_dominance_threshold):
            signals.append("decision_state_lock")
            reasons.append(f"decision_state_lock:{decision_label}:{decision_ratio:.2f}")

        if entry_ready_true == 0:
            signals.append("entry_ready_zero")
            reasons.append("entry_ready_zero")

        if display_ready_true == 0:
            signals.append("display_ready_zero")
            reasons.append("display_ready_zero")

        trigger_recommended = len(signals) >= required_signal_count
        if trigger_recommended:
            state = "drifted"
            reason = reasons[0] if reasons else "drift_detected"
        elif signals:
            state = "watch"
            reason = reasons[0]
        else:
            state = "stable"
            reason = "drift_not_detected"

    return {
        "contract_version": RUNTIME_RECYCLE_DRIFT_CONTRACT_VERSION,
        "state": str(state),
        "reason": str(reason),
        "trigger_recommended": bool(trigger_recommended),
        "signal_count": int(len(signals)),
        "signals": signals,
        "reasons": reasons,
        "recent_row_count": int(row_count),
        "min_rows": int(min_required_rows),
        "required_signal_count": int(required_signal_count),
        "stage_dominance_threshold": float(stage_dominance_threshold),
        "block_dominance_threshold": float(block_dominance_threshold),
        "decision_dominance_threshold": float(decision_dominance_threshold),
        "stage_dominance": stage_dominance,
        "blocked_reason_dominance": blocked_reason_dominance,
        "wait_bridge_dominance": bridge_dominance,
        "decision_state_counts": decision_state_counts,
        "decision_state_dominance": decision_state_dominance,
        "display_ready_summary": {
            "display_ready_true": int(display_ready_true),
            "display_ready_false": max(0, _to_int(display_ready_summary.get("display_ready_false"), 0)),
            "entry_ready_true": int(entry_ready_true),
            "entry_ready_false": max(0, _to_int(display_ready_summary.get("entry_ready_false"), 0)),
            "blocked_row_count": int(blocked_row_count),
        },
        "wait_state_decision_bridge_summary": {
            "bridge_row_count": int(bridge_row_count),
            "state_to_decision_counts": state_to_decision_counts,
        },
    }


def build_runtime_recycle_state(
    *,
    mode: str,
    interval_sec: int,
    flat_grace_sec: int = 0,
    post_order_grace_sec: int = 0,
    now_ts: float | None = None,
) -> dict[str, Any]:
    now = float(time.time() if now_ts is None else now_ts)
    interval = max(0, int(interval_sec or 0))
    clean_mode = _normalize_mode(mode)
    next_due_at = float(now + interval) if interval > 0 else 0.0
    return {
        "contract_version": RUNTIME_RECYCLE_CONTRACT_VERSION,
        "mode": clean_mode,
        "interval_sec": int(interval),
        "flat_grace_sec": max(0, int(flat_grace_sec or 0)),
        "post_order_grace_sec": max(0, int(post_order_grace_sec or 0)),
        "started_at_ts": float(now),
        "next_due_at_ts": float(next_due_at),
        "flat_since_ts": 0.0,
        "last_checked_at_ts": 0.0,
        "last_checked_loop_count": 0,
        "last_action_at_ts": 0.0,
        "last_action_loop_count": 0,
        "last_action": "",
        "last_status": "boot",
        "last_reason": "boot",
        "last_block_reason": "",
        "last_trigger_family": "",
        "last_health_state": "unknown",
        "last_health_reason": "",
        "last_drift_state": "unknown",
        "last_drift_reason": "",
        "last_open_positions_count": 0,
        "last_owned_open_positions_count": 0,
        "log_only_count": 0,
        "reexec_count": 0,
    }


def evaluate_runtime_recycle(
    state: dict[str, Any] | None,
    *,
    loop_count: int,
    mode: str,
    interval_sec: int,
    flat_grace_sec: int,
    post_order_grace_sec: int,
    open_positions_count: int,
    owned_open_positions_count: int,
    last_order_ts: float = 0.0,
    health_snapshot: Mapping[str, Any] | None = None,
    drift_snapshot: Mapping[str, Any] | None = None,
    now_ts: float | None = None,
) -> dict[str, Any]:
    now = float(time.time() if now_ts is None else now_ts)
    working = dict(state or {})
    interval = max(0, int(interval_sec or 0))
    flat_grace = max(0, int(flat_grace_sec or 0))
    post_order_grace = max(0, int(post_order_grace_sec or 0))
    clean_mode = _normalize_mode(mode)
    health = dict(health_snapshot or {})
    drift = dict(drift_snapshot or {})

    started_at = _to_float(working.get("started_at_ts"), now)
    if started_at <= 0.0 or started_at > now:
        started_at = float(now)
    next_due_at = _to_float(working.get("next_due_at_ts"), started_at + float(interval))
    if interval <= 0:
        next_due_at = 0.0
    elif next_due_at <= 0.0:
        next_due_at = float(started_at + float(interval))

    open_count = max(0, int(open_positions_count or 0))
    owned_count = max(0, int(owned_open_positions_count or 0))
    flat_since_ts = _to_float(working.get("flat_since_ts"), 0.0)
    if open_count > 0:
        flat_since_ts = 0.0
    elif flat_since_ts <= 0.0:
        flat_since_ts = float(now)

    uptime_sec = max(0, int(now - started_at))
    due_now = bool(interval > 0 and now >= next_due_at)
    due_in_sec = 0 if due_now else max(0, int(next_due_at - now))
    flat_elapsed_sec = max(0, int(now - flat_since_ts)) if flat_since_ts > 0 else 0
    since_last_order_sec: int | None = None
    if float(last_order_ts or 0.0) > 0.0:
        since_last_order_sec = max(0, int(now - float(last_order_ts)))

    status = "waiting"
    reason = "interval_not_reached"
    action = "none"
    trigger_family = ""
    if clean_mode == RUNTIME_RECYCLE_MODE_DISABLED or interval <= 0:
        status = "disabled"
        reason = "disabled"
    elif not due_now:
        status = "waiting"
        reason = "interval_not_reached"
    elif open_count > 0:
        status = "blocked"
        reason = "open_positions_present"
    elif flat_grace > 0 and flat_elapsed_sec < flat_grace:
        status = "blocked"
        reason = "flat_grace_active"
    elif since_last_order_sec is not None and post_order_grace > 0 and since_last_order_sec < post_order_grace:
        status = "blocked"
        reason = "post_order_grace_active"
    else:
        health_trigger = _to_bool(health.get("trigger_recommended"))
        drift_trigger = _to_bool(drift.get("trigger_recommended"))
        if not health and not drift:
            status = "triggered"
            reason = "due_and_flat"
        elif health_trigger:
            status = "triggered"
            trigger_family = "health"
            reason = str(health.get("reason", "") or "health_triggered")
        elif drift_trigger:
            status = "triggered"
            trigger_family = "drift"
            reason = str(drift.get("reason", "") or "drift_triggered")
        else:
            status = "blocked"
            reason = "health_drift_not_confirmed"

        if status == "triggered":
            action = (
                RUNTIME_RECYCLE_MODE_REEXEC
                if clean_mode == RUNTIME_RECYCLE_MODE_REEXEC
                else RUNTIME_RECYCLE_MODE_LOG_ONLY
            )
            next_due_at = float(now + float(interval))
            if action == RUNTIME_RECYCLE_MODE_LOG_ONLY:
                working["log_only_count"] = _to_int(working.get("log_only_count"), 0) + 1
            else:
                working["reexec_count"] = _to_int(working.get("reexec_count"), 0) + 1
            working["last_action_at_ts"] = float(now)
            working["last_action_loop_count"] = int(loop_count)
            working["last_action"] = str(action)
            working["last_trigger_family"] = str(trigger_family)

    working["contract_version"] = RUNTIME_RECYCLE_CONTRACT_VERSION
    working["mode"] = clean_mode
    working["interval_sec"] = int(interval)
    working["flat_grace_sec"] = int(flat_grace)
    working["post_order_grace_sec"] = int(post_order_grace)
    working["started_at_ts"] = float(started_at)
    working["next_due_at_ts"] = float(next_due_at)
    working["flat_since_ts"] = float(flat_since_ts)
    working["last_checked_at_ts"] = float(now)
    working["last_checked_loop_count"] = int(loop_count)
    working["last_status"] = str(status)
    working["last_reason"] = str(reason)
    working["last_open_positions_count"] = int(open_count)
    working["last_owned_open_positions_count"] = int(owned_count)
    working["last_health_state"] = str(health.get("state", "") or "unknown")
    working["last_health_reason"] = str(health.get("reason", "") or "")
    working["last_drift_state"] = str(drift.get("state", "") or "unknown")
    working["last_drift_reason"] = str(drift.get("reason", "") or "")
    if status == "blocked":
        working["last_block_reason"] = str(reason)

    decision = {
        "contract_version": RUNTIME_RECYCLE_CONTRACT_VERSION,
        "mode": clean_mode,
        "status": str(status),
        "reason": str(reason),
        "action": str(action),
        "trigger_family": str(trigger_family),
        "loop_count": int(loop_count),
        "uptime_sec": int(uptime_sec),
        "interval_sec": int(interval),
        "next_due_in_sec": int(due_in_sec),
        "open_positions_count": int(open_count),
        "owned_open_positions_count": int(owned_count),
        "flat_elapsed_sec": int(flat_elapsed_sec),
        "flat_grace_sec": int(flat_grace),
        "post_order_grace_sec": int(post_order_grace),
        "since_last_order_sec": since_last_order_sec,
        "health": health,
        "drift": drift,
        "state": working,
    }
    return decision


def export_runtime_recycle_state(state: dict[str, Any] | None) -> dict[str, Any]:
    working = dict(state or {})
    started_at_ts = _to_float(working.get("started_at_ts"), 0.0)
    next_due_at_ts = _to_float(working.get("next_due_at_ts"), 0.0)
    flat_since_ts = _to_float(working.get("flat_since_ts"), 0.0)
    last_checked_at_ts = _to_float(working.get("last_checked_at_ts"), 0.0)
    last_action_at_ts = _to_float(working.get("last_action_at_ts"), 0.0)
    return {
        "contract_version": RUNTIME_RECYCLE_CONTRACT_VERSION,
        "mode": _normalize_mode(working.get("mode")),
        "interval_sec": _to_int(working.get("interval_sec"), 0),
        "flat_grace_sec": _to_int(working.get("flat_grace_sec"), 0),
        "post_order_grace_sec": _to_int(working.get("post_order_grace_sec"), 0),
        "started_at_ts": float(started_at_ts),
        "started_at": _iso(started_at_ts),
        "next_due_at_ts": float(next_due_at_ts),
        "next_due_at": _iso(next_due_at_ts),
        "flat_since_ts": float(flat_since_ts),
        "flat_since": _iso(flat_since_ts),
        "last_checked_at_ts": float(last_checked_at_ts),
        "last_checked_at": _iso(last_checked_at_ts),
        "last_checked_loop_count": _to_int(working.get("last_checked_loop_count"), 0),
        "last_action_at_ts": float(last_action_at_ts),
        "last_action_at": _iso(last_action_at_ts),
        "last_action_loop_count": _to_int(working.get("last_action_loop_count"), 0),
        "last_action": str(working.get("last_action", "") or ""),
        "last_status": str(working.get("last_status", "") or ""),
        "last_reason": str(working.get("last_reason", "") or ""),
        "last_block_reason": str(working.get("last_block_reason", "") or ""),
        "last_trigger_family": str(working.get("last_trigger_family", "") or ""),
        "last_health_state": str(working.get("last_health_state", "") or ""),
        "last_health_reason": str(working.get("last_health_reason", "") or ""),
        "last_drift_state": str(working.get("last_drift_state", "") or ""),
        "last_drift_reason": str(working.get("last_drift_reason", "") or ""),
        "last_open_positions_count": _to_int(working.get("last_open_positions_count"), 0),
        "last_owned_open_positions_count": _to_int(working.get("last_owned_open_positions_count"), 0),
        "log_only_count": _to_int(working.get("log_only_count"), 0),
        "reexec_count": _to_int(working.get("reexec_count"), 0),
    }
