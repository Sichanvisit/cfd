"""Path-aware leg runtime assignment helpers for PA1 instrumentation."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


PATH_LEG_RUNTIME_CONTRACT_VERSION = "path_leg_runtime_v1"
PATH_LEG_SNAPSHOT_CONTRACT_VERSION = "path_leg_snapshot_v1"
DEFAULT_PATH_LEG_SYMBOLS = ("BTCUSD", "NAS100", "XAUUSD")
PATH_LEG_RUNTIME_FIELDS = (
    "leg_id",
    "leg_direction",
    "leg_state",
    "leg_transition_reason",
)
PATH_LEG_SNAPSHOT_COLUMNS = [
    "symbol",
    "recent_row_count",
    "assigned_row_count",
    "missing_leg_row_count",
    "missing_leg_row_share",
    "recent_leg_count",
    "active_leg_id",
    "active_leg_direction",
    "active_leg_state",
    "active_leg_transition_reason",
    "latest_time",
    "latest_action",
    "latest_outcome",
    "latest_blocked_by",
]

_LEG_SEQUENCE_PATTERN = re.compile(r"_L(?P<sequence>\d+)$")


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _normalize_action(value: object) -> str:
    text = _to_text(value).upper()
    if text in {"BUY", "LONG"}:
        return "BUY"
    if text in {"SELL", "SHORT"}:
        return "SELL"
    return ""


def _normalize_direction(value: object) -> str:
    action = _normalize_action(value)
    if action == "BUY":
        return "UP"
    if action == "SELL":
        return "DOWN"
    text = _to_text(value).upper()
    if text in {"UP", "BULL", "BULLISH"}:
        return "UP"
    if text in {"DOWN", "BEAR", "BEARISH"}:
        return "DOWN"
    return ""


def _direction_from_action(action: str) -> str:
    if action == "BUY":
        return "UP"
    if action == "SELL":
        return "DOWN"
    return ""


def _resolve_row_timestamp(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    for key in ("time", "signal_time", "timestamp", "bar_time", "signal_bar_ts", "signal_ts"):
        value = payload.get(key)
        text = _to_text(value)
        if not text:
            continue
        if key.endswith("_ts"):
            try:
                ts_value = float(value)
                if ts_value > 1_000_000_000_000:
                    ts_value = ts_value / 1000.0
                return pd.to_datetime(ts_value, unit="s", utc=True).tz_convert("Asia/Seoul").isoformat()
            except Exception:
                continue
        try:
            parsed = pd.to_datetime(text, errors="raise")
        except Exception:
            continue
        if pd.isna(parsed):
            continue
        if getattr(parsed, "tzinfo", None) is None:
            parsed = parsed.tz_localize("Asia/Seoul")
        else:
            parsed = parsed.tz_convert("Asia/Seoul")
        return parsed.isoformat()
    return now_kst_dt().isoformat()


def _timestamp_to_leg_anchor(timestamp_text: str) -> str:
    try:
        parsed = pd.to_datetime(_to_text(timestamp_text), errors="raise")
    except Exception:
        parsed = now_kst_dt()
    if getattr(parsed, "tzinfo", None) is None:
        parsed = parsed.tz_localize("Asia/Seoul")
    else:
        parsed = parsed.tz_convert("Asia/Seoul")
    return parsed.strftime("%Y%m%dT%H%M%S")


def _extract_leg_sequence(*values: object) -> int:
    for value in values:
        text = _to_text(value)
        if not text:
            continue
        match = _LEG_SEQUENCE_PATTERN.search(text)
        if match:
            return _to_int(match.group("sequence"), 0)
    return 0


def _build_leg_id(symbol: str, direction: str, sequence: int, timestamp_text: str) -> str:
    return f"{_to_text(symbol).upper()}_{_to_text(direction).upper()}_{_timestamp_to_leg_anchor(timestamp_text)}_L{int(sequence):04d}"


def extract_leg_runtime_fields(record: Mapping[str, Any] | None) -> dict[str, str]:
    payload = dict(record or {})
    return {
        "leg_id": _to_text(payload.get("leg_id")),
        "leg_direction": _normalize_direction(payload.get("leg_direction")),
        "leg_state": _to_text(payload.get("leg_state")),
        "leg_transition_reason": _to_text(payload.get("leg_transition_reason")),
    }


def _coerce_symbol_state(symbol_state: Mapping[str, Any] | None, symbol: str) -> dict[str, Any]:
    raw = dict(symbol_state or {}) if isinstance(symbol_state, Mapping) else {}
    nested_state = raw.get("symbol_state")
    if isinstance(nested_state, Mapping):
        raw = dict(nested_state)
    symbol_u = _to_text(raw.get("symbol") or symbol).upper()
    active_leg_id = _to_text(raw.get("active_leg_id") or raw.get("leg_id"))
    active_leg_direction = _normalize_direction(raw.get("active_leg_direction") or raw.get("leg_direction"))
    active_leg_state = _to_text(
        raw.get("active_leg_state") or raw.get("leg_state") or ("ACTIVE" if active_leg_id else "IDLE"),
        "IDLE",
    ).upper()
    if active_leg_state == "CLOSED":
        active_leg_id = ""
        active_leg_direction = ""
        active_leg_state = "IDLE"
    next_leg_sequence = max(
        _to_int(raw.get("next_leg_sequence"), 0),
        _extract_leg_sequence(
            raw.get("active_leg_id"),
            raw.get("leg_id"),
            raw.get("last_closed_leg_id"),
        ),
    )
    return {
        "contract_version": PATH_LEG_RUNTIME_CONTRACT_VERSION,
        "symbol": symbol_u,
        "next_leg_sequence": int(next_leg_sequence),
        "active_leg_id": active_leg_id,
        "active_leg_direction": active_leg_direction,
        "active_leg_state": active_leg_state,
        "last_transition_reason": _to_text(
            raw.get("last_transition_reason") or raw.get("leg_transition_reason")
        ),
        "last_seen_at": _to_text(raw.get("last_seen_at") or _resolve_row_timestamp(raw)),
        "last_closed_leg_id": _to_text(raw.get("last_closed_leg_id")),
        "last_closed_direction": _normalize_direction(raw.get("last_closed_direction")),
        "last_closed_at": _to_text(raw.get("last_closed_at")),
    }


def resolve_leg_direction_hint(row: Mapping[str, Any] | None) -> tuple[str, str]:
    payload = dict(row or {})

    bridge_action = _normalize_action(payload.get("entry_candidate_bridge_action"))
    if _to_bool(payload.get("entry_candidate_bridge_selected")) and bridge_action:
        return _direction_from_action(bridge_action), "entry_candidate_bridge_action"

    breakout_direction = _normalize_direction(payload.get("breakout_candidate_direction"))
    if breakout_direction:
        return breakout_direction, "breakout_candidate_direction"

    for key in (
        "countertrend_directional_execution_action",
        "countertrend_directional_candidate_action",
        "countertrend_candidate_action",
        "breakout_candidate_action",
        "consumer_effective_action",
        "action",
        "observe_action",
        "observe_side",
    ):
        direction = _normalize_direction(payload.get(key))
        if direction:
            return direction, key

    intended_direction = _normalize_direction(payload.get("core_intended_direction"))
    if intended_direction:
        return intended_direction, "core_intended_direction"

    countertrend_state = _to_text(payload.get("countertrend_action_state")).upper()
    if countertrend_state.startswith("UP"):
        return "UP", "countertrend_action_state"
    if countertrend_state.startswith("DOWN"):
        return "DOWN", "countertrend_action_state"

    return "", ""


def _has_selected_entry_rearm_signal(row: Mapping[str, Any] | None) -> bool:
    payload = dict(row or {})
    bridge_action = _normalize_action(payload.get("entry_candidate_bridge_action"))
    if _to_bool(payload.get("entry_candidate_bridge_selected")) and bridge_action in {"BUY", "SELL"}:
        return True
    return False


def _should_force_new_leg(row: Mapping[str, Any] | None) -> bool:
    payload = dict(row or {})
    if _to_bool(payload.get("path_leg_force_new_leg")):
        return True
    if _to_text(payload.get("outcome")).lower() == "entered":
        return True
    if _has_selected_entry_rearm_signal(payload):
        return True
    blocked_by = _to_text(payload.get("blocked_by")).lower()
    if blocked_by:
        return False
    observe_action = _normalize_action(payload.get("observe_action"))
    return observe_action in {"BUY", "SELL"}


def _activate_new_leg(
    *,
    symbol: str,
    direction: str,
    transition_reason: str,
    timestamp_text: str,
    state: Mapping[str, Any] | None,
) -> tuple[dict[str, str], dict[str, Any]]:
    current_state = _coerce_symbol_state(state, symbol)
    sequence = max(1, _to_int(current_state.get("next_leg_sequence"), 0) + 1)
    leg_id = _build_leg_id(symbol, direction, sequence, timestamp_text)
    updated_state = {
        **current_state,
        "next_leg_sequence": int(sequence),
        "active_leg_id": leg_id,
        "active_leg_direction": direction,
        "active_leg_state": "ACTIVE",
        "last_transition_reason": _to_text(transition_reason),
        "last_seen_at": _to_text(timestamp_text),
    }
    return (
        {
            "leg_id": leg_id,
            "leg_direction": direction,
            "leg_state": "ACTIVE",
            "leg_transition_reason": _to_text(transition_reason),
        },
        updated_state,
    )


def assign_leg_id(
    symbol: str,
    runtime_row: Mapping[str, Any] | None,
    symbol_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(runtime_row or {})
    symbol_u = _to_text(symbol or payload.get("symbol")).upper()
    row_timestamp = _resolve_row_timestamp(payload)
    state = _coerce_symbol_state(symbol_state, symbol_u)
    direction_hint, direction_source = resolve_leg_direction_hint(payload)
    active_leg_id = _to_text(state.get("active_leg_id"))
    active_leg_direction = _normalize_direction(state.get("active_leg_direction"))

    if active_leg_id:
        if not direction_hint:
            leg_fields = {
                "leg_id": active_leg_id,
                "leg_direction": active_leg_direction,
                "leg_state": "ACTIVE",
                "leg_transition_reason": "carry_forward_active_leg",
            }
            updated_state = {
                **state,
                "last_transition_reason": "carry_forward_active_leg",
                "last_seen_at": row_timestamp,
            }
        elif direction_hint == active_leg_direction:
            leg_fields = {
                "leg_id": active_leg_id,
                "leg_direction": active_leg_direction,
                "leg_state": "ACTIVE",
                "leg_transition_reason": "active_leg_continuation",
            }
            updated_state = {
                **state,
                "last_transition_reason": "active_leg_continuation",
                "last_seen_at": row_timestamp,
            }
        elif _should_force_new_leg(payload):
            leg_fields, updated_state = _activate_new_leg(
                symbol=symbol_u,
                direction=direction_hint,
                transition_reason=f"direction_flip_entered_new_leg::{direction_source or 'direction_hint'}",
                timestamp_text=row_timestamp,
                state={
                    **state,
                    "last_closed_leg_id": active_leg_id,
                    "last_closed_direction": active_leg_direction,
                    "last_closed_at": row_timestamp,
                },
            )
        else:
            leg_fields = {
                "leg_id": active_leg_id,
                "leg_direction": active_leg_direction,
                "leg_state": "ACTIVE",
                "leg_transition_reason": f"retain_active_leg_shallow_rebuild::{direction_source or 'direction_hint'}",
            }
            updated_state = {
                **state,
                "last_transition_reason": leg_fields["leg_transition_reason"],
                "last_seen_at": row_timestamp,
            }
    elif direction_hint:
        leg_fields, updated_state = _activate_new_leg(
            symbol=symbol_u,
            direction=direction_hint,
            transition_reason=f"leg_opened_from::{direction_source or 'direction_hint'}",
            timestamp_text=row_timestamp,
            state=state,
        )
    else:
        leg_fields = {
            "leg_id": "",
            "leg_direction": "",
            "leg_state": "UNASSIGNED",
            "leg_transition_reason": "missing_direction_hint",
        }
        updated_state = {
            **state,
            "active_leg_id": "",
            "active_leg_direction": "",
            "active_leg_state": "IDLE",
            "last_transition_reason": "missing_direction_hint",
            "last_seen_at": row_timestamp,
        }

    return {
        "contract_version": PATH_LEG_RUNTIME_CONTRACT_VERSION,
        "symbol": symbol_u,
        "direction_hint": direction_hint,
        "direction_hint_source": direction_source,
        **leg_fields,
        "symbol_state": updated_state,
    }


def close_active_leg(
    symbol: str,
    symbol_state: Mapping[str, Any] | None = None,
    *,
    reason: str = "full_exit",
    event_time: str = "",
) -> dict[str, Any]:
    symbol_u = _to_text(symbol).upper()
    timestamp_text = _to_text(event_time) or now_kst_dt().isoformat()
    state = _coerce_symbol_state(symbol_state, symbol_u)
    active_leg_id = _to_text(state.get("active_leg_id"))
    active_leg_direction = _normalize_direction(state.get("active_leg_direction"))
    if not active_leg_id:
        updated_state = {
            **state,
            "active_leg_id": "",
            "active_leg_direction": "",
            "active_leg_state": "IDLE",
            "last_transition_reason": f"{_to_text(reason, 'full_exit')}_without_active_leg",
            "last_seen_at": timestamp_text,
        }
        return {
            "contract_version": PATH_LEG_RUNTIME_CONTRACT_VERSION,
            "symbol": symbol_u,
            "leg_id": "",
            "leg_direction": "",
            "leg_state": "IDLE",
            "leg_transition_reason": updated_state["last_transition_reason"],
            "symbol_state": updated_state,
        }

    updated_state = {
        **state,
        "active_leg_id": "",
        "active_leg_direction": "",
        "active_leg_state": "IDLE",
        "last_transition_reason": f"{_to_text(reason, 'full_exit')}_closed_active_leg",
        "last_seen_at": timestamp_text,
        "last_closed_leg_id": active_leg_id,
        "last_closed_direction": active_leg_direction,
        "last_closed_at": timestamp_text,
    }
    return {
        "contract_version": PATH_LEG_RUNTIME_CONTRACT_VERSION,
        "symbol": symbol_u,
        "leg_id": "",
        "leg_direction": "",
        "leg_state": "CLOSED",
        "leg_transition_reason": updated_state["last_transition_reason"],
        "symbol_state": updated_state,
    }


def build_path_leg_snapshot(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    symbols: Iterable[str] = DEFAULT_PATH_LEG_SYMBOLS,
    recent_limit: int = 240,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    runtime_rows = dict(runtime.get("latest_signal_by_symbol", {}) or {})
    frame = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()
    symbol_order = [str(symbol).upper() for symbol in symbols]

    summary: dict[str, Any] = {
        "contract_version": PATH_LEG_SNAPSHOT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "recent_row_count": 0,
        "market_family_row_count": 0,
        "active_leg_count": 0,
        "missing_leg_row_count": 0,
        "missing_leg_row_share": 1.0,
        "symbols": ",".join(symbol_order),
        "symbol_active_leg_map": {},
        "symbol_missing_row_counts": {},
        "recommended_next_action": "collect_more_leg_runtime_rows",
    }

    if frame.empty:
        rows: list[dict[str, Any]] = []
        for symbol in symbol_order:
            runtime_row = dict(runtime_rows.get(symbol, {}) or {})
            runtime_leg_fields = extract_leg_runtime_fields(runtime_row)
            rows.append(
                {
                    "symbol": symbol,
                    "recent_row_count": 0,
                    "assigned_row_count": 0,
                    "missing_leg_row_count": 0,
                    "missing_leg_row_share": 0.0,
                    "recent_leg_count": 0,
                    "active_leg_id": runtime_leg_fields["leg_id"],
                    "active_leg_direction": runtime_leg_fields["leg_direction"],
                    "active_leg_state": runtime_leg_fields["leg_state"],
                    "active_leg_transition_reason": runtime_leg_fields["leg_transition_reason"],
                    "latest_time": _resolve_row_timestamp(runtime_row) if runtime_row else "",
                    "latest_action": _to_text(runtime_row.get("action")),
                    "latest_outcome": _to_text(runtime_row.get("outcome")),
                    "latest_blocked_by": _to_text(runtime_row.get("blocked_by")),
                }
            )
        snapshot = pd.DataFrame(rows, columns=PATH_LEG_SNAPSHOT_COLUMNS)
        summary["active_leg_count"] = int((snapshot["active_leg_id"].fillna("").astype(str).str.len() > 0).sum())
        summary["symbol_active_leg_map"] = {
            str(row["symbol"]): _to_text(row["active_leg_id"])
            for row in snapshot.to_dict(orient="records")
        }
        summary["symbol_missing_row_counts"] = {
            str(row["symbol"]): int(row["missing_leg_row_count"])
            for row in snapshot.to_dict(orient="records")
        }
        return snapshot, summary

    for column in ("time", "symbol", "action", "outcome", "blocked_by"):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["__time_sort"] = pd.to_datetime(frame["time"], errors="coerce")
    recent = frame.sort_values("__time_sort").tail(max(1, int(recent_limit))).copy()
    scoped = recent.loc[recent["symbol"].isin(symbol_order)].copy()
    summary["recent_row_count"] = int(len(recent))
    summary["market_family_row_count"] = int(len(scoped))

    rows: list[dict[str, Any]] = []
    total_missing = 0
    total_scoped = 0

    for symbol in symbol_order:
        symbol_frame = scoped.loc[scoped["symbol"] == symbol].copy().sort_values("__time_sort")
        symbol_state: dict[str, Any] | None = None
        assigned_row_count = 0
        leg_ids: list[str] = []
        last_row: dict[str, Any] = {}

        for record in symbol_frame.to_dict(orient="records"):
            last_row = dict(record)
            assignment = assign_leg_id(symbol, record, symbol_state)
            symbol_state = dict(assignment.get("symbol_state", {}) or {})
            leg_fields = extract_leg_runtime_fields(assignment)
            if leg_fields["leg_id"]:
                assigned_row_count += 1
                leg_ids.append(leg_fields["leg_id"])

        runtime_row = dict(runtime_rows.get(symbol, {}) or {})
        runtime_leg_fields = extract_leg_runtime_fields(runtime_row)
        if runtime_row and not runtime_leg_fields["leg_id"]:
            runtime_assignment = assign_leg_id(symbol, runtime_row, symbol_state)
            runtime_leg_fields = extract_leg_runtime_fields(runtime_assignment)
            symbol_state = dict(runtime_assignment.get("symbol_state", {}) or symbol_state or {})
        elif not runtime_row and symbol_state:
            runtime_leg_fields = {
                "leg_id": _to_text(symbol_state.get("active_leg_id")),
                "leg_direction": _normalize_direction(symbol_state.get("active_leg_direction")),
                "leg_state": _to_text(symbol_state.get("active_leg_state")),
                "leg_transition_reason": _to_text(symbol_state.get("last_transition_reason")),
            }

        recent_row_count = int(len(symbol_frame))
        missing_row_count = max(0, recent_row_count - assigned_row_count)
        total_missing += int(missing_row_count)
        total_scoped += int(recent_row_count)

        latest_source = runtime_row if runtime_row else last_row
        rows.append(
            {
                "symbol": symbol,
                "recent_row_count": recent_row_count,
                "assigned_row_count": int(assigned_row_count),
                "missing_leg_row_count": int(missing_row_count),
                "missing_leg_row_share": (
                    round(float(missing_row_count) / float(recent_row_count), 6)
                    if recent_row_count > 0
                    else 0.0
                ),
                "recent_leg_count": int(len(set(leg_ids))),
                "active_leg_id": runtime_leg_fields["leg_id"],
                "active_leg_direction": runtime_leg_fields["leg_direction"],
                "active_leg_state": runtime_leg_fields["leg_state"],
                "active_leg_transition_reason": runtime_leg_fields["leg_transition_reason"],
                "latest_time": _resolve_row_timestamp(latest_source) if latest_source else "",
                "latest_action": _to_text(latest_source.get("action")),
                "latest_outcome": _to_text(latest_source.get("outcome")),
                "latest_blocked_by": _to_text(latest_source.get("blocked_by")),
            }
        )

    snapshot = pd.DataFrame(rows, columns=PATH_LEG_SNAPSHOT_COLUMNS)
    summary["active_leg_count"] = int((snapshot["active_leg_id"].fillna("").astype(str).str.len() > 0).sum())
    summary["missing_leg_row_count"] = int(total_missing)
    summary["missing_leg_row_share"] = round(float(total_missing) / float(total_scoped), 6) if total_scoped > 0 else 0.0
    summary["symbol_active_leg_map"] = {
        str(row["symbol"]): _to_text(row["active_leg_id"])
        for row in snapshot.to_dict(orient="records")
    }
    summary["symbol_missing_row_counts"] = {
        str(row["symbol"]): int(row["missing_leg_row_count"])
        for row in snapshot.to_dict(orient="records")
    }
    summary["recommended_next_action"] = (
        "proceed_to_pa2_checkpoint_segmentation"
        if summary["missing_leg_row_share"] <= 0.35 and summary["active_leg_count"] >= 1
        else "reduce_unassigned_leg_rows_before_pa2"
    )
    return snapshot, summary
