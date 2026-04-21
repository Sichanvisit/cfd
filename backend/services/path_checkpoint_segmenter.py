"""Path-aware checkpoint segmentation helpers for PA2 instrumentation."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from backend.services.path_leg_runtime import (
    DEFAULT_PATH_LEG_SYMBOLS,
    assign_leg_id,
    extract_leg_runtime_fields,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_SEGMENTER_CONTRACT_VERSION = "path_checkpoint_segmenter_v1"
PATH_CHECKPOINT_DISTRIBUTION_CONTRACT_VERSION = "checkpoint_distribution_v1"
PATH_CHECKPOINT_TYPES = (
    "INITIAL_PUSH",
    "FIRST_PULLBACK_CHECK",
    "RECLAIM_CHECK",
    "LATE_TREND_CHECK",
    "RUNNER_CHECK",
)
PATH_CHECKPOINT_DISTRIBUTION_COLUMNS = [
    "symbol",
    "recent_row_count",
    "checkpoint_count",
    "new_checkpoint_share",
    "active_leg_id",
    "active_checkpoint_id",
    "active_checkpoint_type",
    "active_checkpoint_index",
    "checkpoint_type_counts",
    "latest_time",
    "latest_blocked_by",
    "recommended_focus",
]

_CHECKPOINT_PRECEDENCE = {
    "INITIAL_PUSH": 1,
    "FIRST_PULLBACK_CHECK": 2,
    "RECLAIM_CHECK": 3,
    "LATE_TREND_CHECK": 4,
    "RUNNER_CHECK": 5,
}
_LEG_ACTION_BY_DIRECTION = {"UP": "BUY", "DOWN": "SELL"}


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


def _resolve_row_timestamp(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    for key in ("time", "signal_time", "timestamp", "bar_time", "signal_bar_ts", "signal_ts"):
        value = payload.get(key)
        if value in ("", None):
            continue
        if key.endswith("_ts"):
            try:
                ts_value = float(value)
                if ts_value > 1_000_000_000_000:
                    ts_value = ts_value / 1000.0
                return pd.to_datetime(ts_value, unit="s", utc=True).tz_convert("Asia/Seoul").isoformat()
            except Exception:
                continue
        text = _to_text(value)
        if not text:
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


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _coerce_checkpoint_state(symbol_state: Mapping[str, Any] | None, symbol: str) -> dict[str, Any]:
    raw = dict(symbol_state or {}) if isinstance(symbol_state, Mapping) else {}
    nested_state = raw.get("symbol_state")
    if isinstance(nested_state, Mapping):
        raw = dict(nested_state)
    return {
        "contract_version": PATH_CHECKPOINT_SEGMENTER_CONTRACT_VERSION,
        "symbol": _to_text(raw.get("symbol") or symbol).upper(),
        "active_leg_id": _to_text(raw.get("active_leg_id")),
        "active_checkpoint_id": _to_text(raw.get("active_checkpoint_id")),
        "active_checkpoint_type": _to_text(raw.get("active_checkpoint_type")),
        "active_checkpoint_index": _to_int(raw.get("active_checkpoint_index"), 0),
        "leg_row_count": _to_int(raw.get("leg_row_count"), 0),
        "rows_since_checkpoint_start": _to_int(raw.get("rows_since_checkpoint_start"), 0),
        "last_transition_reason": _to_text(raw.get("last_transition_reason")),
        "last_seen_at": _to_text(raw.get("last_seen_at")),
    }


def extract_checkpoint_fields(record: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(record or {})
    checkpoint_type = _to_text(payload.get("checkpoint_type"))
    if checkpoint_type not in PATH_CHECKPOINT_TYPES:
        checkpoint_type = ""
    return {
        "checkpoint_id": _to_text(payload.get("checkpoint_id")),
        "checkpoint_type": checkpoint_type,
        "checkpoint_index_in_leg": _to_int(payload.get("checkpoint_index_in_leg"), 0),
        "checkpoint_transition_reason": _to_text(payload.get("checkpoint_transition_reason")),
    }


def _is_opposite_pressure(leg_direction: str, row: Mapping[str, Any] | None) -> bool:
    payload = dict(row or {})
    leg_action = _LEG_ACTION_BY_DIRECTION.get(_to_text(leg_direction).upper(), "")
    opposite_action = "SELL" if leg_action == "BUY" else ("BUY" if leg_action == "SELL" else "")
    observe_action = _normalize_action(payload.get("observe_action"))
    observe_side = _normalize_action(payload.get("observe_side"))
    blocked_by = _to_text(payload.get("blocked_by")).lower()
    consumer_stage = _to_text(payload.get("consumer_check_stage")).upper()
    action_none_reason = _to_text(payload.get("action_none_reason")).lower()
    reason_blob = " ".join(
        filter(
            None,
            [
                blocked_by,
                action_none_reason,
                _to_text(payload.get("consumer_check_reason")).lower(),
                _to_text(payload.get("setup_reason")).lower(),
            ],
        )
    )
    opposite_signal = observe_action == opposite_action or observe_side == opposite_action
    pressure_tokens = (
        "reject",
        "pullback",
        "probe",
        "observe",
        "reversal",
        "upper",
        "lower",
        "soft_block",
    )
    return bool(
        opposite_signal
        or consumer_stage in {"BLOCKED", "PROBE"}
        or any(token in reason_blob for token in pressure_tokens)
    )


def _is_reclaim_signal(leg_direction: str, row: Mapping[str, Any] | None) -> bool:
    payload = dict(row or {})
    leg_action = _LEG_ACTION_BY_DIRECTION.get(_to_text(leg_direction).upper(), "")
    bridge_action = _normalize_action(payload.get("entry_candidate_bridge_action"))
    breakout_action = _normalize_action(payload.get("breakout_candidate_action"))
    observe_action = _normalize_action(payload.get("observe_action"))
    observe_side = _normalize_action(payload.get("observe_side"))
    countertrend_state = _to_text(payload.get("countertrend_action_state")).upper()
    consumer_stage = _to_text(payload.get("consumer_check_stage")).upper()
    setup_trigger_state = _to_text(payload.get("setup_trigger_state")).upper()
    if _to_bool(payload.get("entry_candidate_bridge_selected")) and bridge_action == leg_action:
        return True
    if _to_bool(payload.get("active_action_conflict_guard_applied")) and bridge_action == leg_action:
        return True
    if breakout_action == leg_action:
        return True
    if observe_action == leg_action and consumer_stage in {"PROBE", "READY"}:
        return True
    if observe_side == leg_action and setup_trigger_state == "READY":
        return True
    if leg_direction == "UP" and countertrend_state.startswith("UP"):
        return True
    if leg_direction == "DOWN" and countertrend_state.startswith("DOWN"):
        return True
    return False


def _is_runner_context(row: Mapping[str, Any] | None) -> bool:
    payload = dict(row or {})
    source = _to_text(payload.get("source")).lower()
    stage_family = _to_text(payload.get("exit_stage_family")).lower()
    rule_family = _to_text(payload.get("checkpoint_rule_family_hint")).lower()
    return bool(
        _to_bool(payload.get("runner_secured"))
        or stage_family == "runner"
        or "runner" in source
        or rule_family == "runner_secured_continuation"
    )


def _is_protective_context(row: Mapping[str, Any] | None) -> bool:
    payload = dict(row or {})
    source = _to_text(payload.get("source")).lower()
    stage_family = _to_text(payload.get("exit_stage_family")).lower()
    rule_family = _to_text(payload.get("checkpoint_rule_family_hint")).lower()
    return bool(
        stage_family == "protective"
        or source.startswith("exit_manage_protective")
        or source.startswith("exit_manage_managed_exit")
        or source.startswith("exit_manage_recovery")
        or rule_family in {"open_loss_protective", "active_open_loss", "protective_exit_bias", "full_exit_candidate"}
    )


def _is_late_hold_context(row: Mapping[str, Any] | None) -> bool:
    payload = dict(row or {})
    source = _to_text(payload.get("source")).lower()
    stage_family = _to_text(payload.get("exit_stage_family")).lower()
    rule_family = _to_text(payload.get("checkpoint_rule_family_hint")).lower()
    return bool(
        stage_family == "hold"
        or source.startswith("exit_manage_hold")
        or rule_family in {"profit_hold_bias", "profit_trim_bias", "wait_bias", "active_flat_profit"}
    )


def classify_checkpoint_type(
    leg_ctx: Mapping[str, Any] | None,
    runtime_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    leg_state = dict(leg_ctx or {})
    row = dict(runtime_row or {})
    leg_id = _to_text(row.get("leg_id") or leg_state.get("active_leg_id"))
    leg_direction = _to_text(row.get("leg_direction") or leg_state.get("leg_direction")).upper()
    leg_row_count = max(1, _to_int(leg_state.get("leg_row_count"), 1))
    if not leg_id or leg_direction not in {"UP", "DOWN"}:
        return {
            "checkpoint_type": "",
            "checkpoint_candidate_reason": "missing_leg_context",
            "checkpoint_evidence": {},
        }

    opposite_pressure = _is_opposite_pressure(leg_direction, row)
    reclaim_signal = _is_reclaim_signal(leg_direction, row)
    runner_context = _is_runner_context(row)
    protective_context = _is_protective_context(row)
    late_hold_context = _is_late_hold_context(row)
    late_threshold = 8
    runner_threshold = 16

    if leg_row_count <= 1:
        return {
            "checkpoint_type": "INITIAL_PUSH",
            "checkpoint_candidate_reason": "initial_leg_rows",
            "checkpoint_evidence": {"leg_row_count": leg_row_count},
        }

    if reclaim_signal:
        return {
            "checkpoint_type": "RECLAIM_CHECK",
            "checkpoint_candidate_reason": "reclaim_signal_detected",
            "checkpoint_evidence": {"leg_row_count": leg_row_count},
        }

    if opposite_pressure and leg_row_count <= 6:
        return {
            "checkpoint_type": "FIRST_PULLBACK_CHECK",
            "checkpoint_candidate_reason": "opposite_pressure_early_leg",
            "checkpoint_evidence": {"leg_row_count": leg_row_count},
        }

    if runner_context and leg_row_count >= late_threshold:
        return {
            "checkpoint_type": "RUNNER_CHECK",
            "checkpoint_candidate_reason": "explicit_runner_context",
            "checkpoint_evidence": {
                "leg_row_count": leg_row_count,
                "runner_secured": _to_bool(row.get("runner_secured")),
                "exit_stage_family": _to_text(row.get("exit_stage_family")).lower(),
                "checkpoint_rule_family_hint": _to_text(row.get("checkpoint_rule_family_hint")).lower(),
            },
        }

    if (protective_context or late_hold_context) and leg_row_count >= late_threshold:
        return {
            "checkpoint_type": "LATE_TREND_CHECK",
            "checkpoint_candidate_reason": "contextual_late_management",
            "checkpoint_evidence": {
                "leg_row_count": leg_row_count,
                "protective_context": protective_context,
                "late_hold_context": late_hold_context,
                "exit_stage_family": _to_text(row.get("exit_stage_family")).lower(),
                "checkpoint_rule_family_hint": _to_text(row.get("checkpoint_rule_family_hint")).lower(),
            },
        }

    if leg_row_count >= runner_threshold:
        return {
            "checkpoint_type": "RUNNER_CHECK",
            "checkpoint_candidate_reason": "runner_threshold_reached",
            "checkpoint_evidence": {"leg_row_count": leg_row_count},
        }

    if leg_row_count >= late_threshold:
        return {
            "checkpoint_type": "LATE_TREND_CHECK",
            "checkpoint_candidate_reason": "late_trend_threshold_reached",
            "checkpoint_evidence": {"leg_row_count": leg_row_count},
        }

    if opposite_pressure:
        return {
            "checkpoint_type": "FIRST_PULLBACK_CHECK",
            "checkpoint_candidate_reason": "opposite_pressure_detected",
            "checkpoint_evidence": {"leg_row_count": leg_row_count},
        }

    return {
        "checkpoint_type": "INITIAL_PUSH",
        "checkpoint_candidate_reason": "default_initial_progression",
        "checkpoint_evidence": {"leg_row_count": leg_row_count},
    }


def _build_checkpoint_id(leg_id: str, checkpoint_index: int) -> str:
    return f"{_to_text(leg_id)}_CP{int(checkpoint_index):03d}"


def assign_checkpoint_context(
    symbol: str,
    runtime_row: Mapping[str, Any] | None,
    symbol_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = dict(runtime_row or {})
    symbol_u = _to_text(symbol or row.get("symbol")).upper()
    row_leg_fields = extract_leg_runtime_fields(row)
    checkpoint_state = _coerce_checkpoint_state(symbol_state, symbol_u)
    active_leg_id = _to_text(checkpoint_state.get("active_leg_id"))

    if not row_leg_fields["leg_id"]:
        leg_assignment = assign_leg_id(symbol_u, row, checkpoint_state)
        row_leg_fields = extract_leg_runtime_fields(leg_assignment)
        row.update(row_leg_fields)
    leg_id = _to_text(row_leg_fields["leg_id"])
    leg_direction = _to_text(row_leg_fields["leg_direction"]).upper()
    row_timestamp = _resolve_row_timestamp(row)

    if not leg_id or leg_direction not in {"UP", "DOWN"}:
        updated_state = {
            **checkpoint_state,
            "active_leg_id": "",
            "active_checkpoint_id": "",
            "active_checkpoint_type": "",
            "active_checkpoint_index": 0,
            "leg_row_count": 0,
            "rows_since_checkpoint_start": 0,
            "last_transition_reason": "missing_leg_context",
            "last_seen_at": row_timestamp,
        }
        return {
            "contract_version": PATH_CHECKPOINT_SEGMENTER_CONTRACT_VERSION,
            "symbol": symbol_u,
            "checkpoint_id": "",
            "checkpoint_type": "",
            "checkpoint_index_in_leg": 0,
            "checkpoint_transition_reason": "missing_leg_context",
            "symbol_state": updated_state,
        }

    leg_changed = leg_id != active_leg_id
    if leg_changed:
        checkpoint_state = {
            **checkpoint_state,
            "active_leg_id": leg_id,
            "active_checkpoint_id": "",
            "active_checkpoint_type": "",
            "active_checkpoint_index": 0,
            "leg_row_count": 0,
            "rows_since_checkpoint_start": 0,
        }

    leg_row_count = max(1, _to_int(checkpoint_state.get("leg_row_count"), 0) + 1)
    classify_ctx = {
        "leg_id": leg_id,
        "leg_direction": leg_direction,
        "leg_row_count": leg_row_count,
        "active_checkpoint_type": _to_text(checkpoint_state.get("active_checkpoint_type")),
        "active_checkpoint_index": _to_int(checkpoint_state.get("active_checkpoint_index"), 0),
    }
    classification = classify_checkpoint_type(classify_ctx, row)
    candidate_type = _to_text(classification.get("checkpoint_type"))
    candidate_reason = _to_text(classification.get("checkpoint_candidate_reason"))
    active_checkpoint_type = _to_text(checkpoint_state.get("active_checkpoint_type"))
    active_checkpoint_index = _to_int(checkpoint_state.get("active_checkpoint_index"), 0)
    rows_since_checkpoint_start = _to_int(checkpoint_state.get("rows_since_checkpoint_start"), 0)

    open_new_checkpoint = False
    transition_reason = "checkpoint_continuation"

    if not active_checkpoint_type or leg_changed:
        open_new_checkpoint = True
        candidate_type = candidate_type or "INITIAL_PUSH"
        transition_reason = "leg_start_checkpoint_opened" if leg_changed or not active_checkpoint_type else "checkpoint_opened"
    elif not candidate_type:
        candidate_type = active_checkpoint_type
    elif candidate_type == active_checkpoint_type:
        transition_reason = "checkpoint_continuation"
    elif _CHECKPOINT_PRECEDENCE.get(candidate_type, 0) > _CHECKPOINT_PRECEDENCE.get(active_checkpoint_type, 0):
        if (
            candidate_type == "RUNNER_CHECK"
            and leg_row_count < 16
            and candidate_reason != "explicit_runner_context"
        ):
            candidate_type = active_checkpoint_type
            transition_reason = "runner_threshold_not_met"
        else:
            open_new_checkpoint = True
            transition_reason = f"checkpoint_progression::{active_checkpoint_type}_to_{candidate_type}"
    elif candidate_type == "FIRST_PULLBACK_CHECK" and active_checkpoint_type in {"RECLAIM_CHECK", "LATE_TREND_CHECK", "RUNNER_CHECK"}:
        candidate_type = active_checkpoint_type
        transition_reason = "retain_active_checkpoint_shallow_rebuild"
    elif rows_since_checkpoint_start <= 0:
        open_new_checkpoint = True
        transition_reason = f"checkpoint_refresh::{candidate_reason or candidate_type.lower()}"
    else:
        candidate_type = active_checkpoint_type
        transition_reason = "checkpoint_continuation"

    if open_new_checkpoint:
        checkpoint_index = max(1, active_checkpoint_index + 1)
        checkpoint_id = _build_checkpoint_id(leg_id, checkpoint_index)
        rows_since_checkpoint_start = 1
    else:
        checkpoint_index = max(1, active_checkpoint_index or 1)
        checkpoint_id = _to_text(checkpoint_state.get("active_checkpoint_id")) or _build_checkpoint_id(leg_id, checkpoint_index)
        rows_since_checkpoint_start = max(1, rows_since_checkpoint_start + 1)

    updated_state = {
        **checkpoint_state,
        "active_leg_id": leg_id,
        "active_checkpoint_id": checkpoint_id,
        "active_checkpoint_type": candidate_type,
        "active_checkpoint_index": int(checkpoint_index),
        "leg_row_count": int(leg_row_count),
        "rows_since_checkpoint_start": int(rows_since_checkpoint_start),
        "last_transition_reason": transition_reason,
        "last_seen_at": row_timestamp,
    }
    return {
        "contract_version": PATH_CHECKPOINT_SEGMENTER_CONTRACT_VERSION,
        "symbol": symbol_u,
        "checkpoint_id": checkpoint_id,
        "checkpoint_type": candidate_type,
        "checkpoint_index_in_leg": int(checkpoint_index),
        "checkpoint_transition_reason": transition_reason,
        "checkpoint_candidate_reason": candidate_reason,
        "symbol_state": updated_state,
    }


def build_checkpoint_distribution(
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
        "contract_version": PATH_CHECKPOINT_DISTRIBUTION_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "recent_row_count": 0,
        "market_family_row_count": 0,
        "checkpoint_count": 0,
        "new_checkpoint_share": 0.0,
        "symbols": ",".join(symbol_order),
        "symbol_active_checkpoint_map": {},
        "symbol_checkpoint_type_counts": {},
        "recommended_next_action": "collect_more_checkpoint_rows",
    }
    if frame.empty:
        rows: list[dict[str, Any]] = []
        for symbol in symbol_order:
            runtime_row = dict(runtime_rows.get(symbol, {}) or {})
            checkpoint_assignment = assign_checkpoint_context(symbol, runtime_row, runtime_row)
            checkpoint_fields = extract_checkpoint_fields(checkpoint_assignment)
            rows.append(
                {
                    "symbol": symbol,
                    "recent_row_count": 0,
                    "checkpoint_count": int(checkpoint_fields["checkpoint_index_in_leg"]),
                    "new_checkpoint_share": 0.0,
                    "active_leg_id": _to_text(runtime_row.get("leg_id")),
                    "active_checkpoint_id": checkpoint_fields["checkpoint_id"],
                    "active_checkpoint_type": checkpoint_fields["checkpoint_type"],
                    "active_checkpoint_index": int(checkpoint_fields["checkpoint_index_in_leg"]),
                    "checkpoint_type_counts": "{}",
                    "latest_time": _resolve_row_timestamp(runtime_row) if runtime_row else "",
                    "latest_blocked_by": _to_text(runtime_row.get("blocked_by")),
                    "recommended_focus": f"collect_more_{symbol.lower()}_checkpoint_rows",
                }
            )
        distribution = pd.DataFrame(rows, columns=PATH_CHECKPOINT_DISTRIBUTION_COLUMNS)
        return distribution, summary

    for column in ("time", "symbol", "blocked_by", "observe_action", "observe_side"):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["__time_sort"] = pd.to_datetime(frame["time"], errors="coerce")
    recent = frame.sort_values("__time_sort").tail(max(1, int(recent_limit))).copy()
    scoped = recent.loc[recent["symbol"].isin(symbol_order)].copy()
    summary["recent_row_count"] = int(len(recent))
    summary["market_family_row_count"] = int(len(scoped))

    rows: list[dict[str, Any]] = []
    total_rows = 0
    total_checkpoints = 0

    for symbol in symbol_order:
        symbol_frame = scoped.loc[scoped["symbol"] == symbol].copy().sort_values("__time_sort")
        checkpoint_state: dict[str, Any] | None = None
        leg_state: dict[str, Any] | None = None
        checkpoint_counts: dict[str, int] = {}
        checkpoint_ids: list[str] = []
        last_checkpoint: dict[str, Any] = {}

        for record in symbol_frame.to_dict(orient="records"):
            if not _to_text(record.get("leg_id")):
                leg_assignment = assign_leg_id(symbol, record, leg_state)
                record.update(extract_leg_runtime_fields(leg_assignment))
                leg_state = dict(leg_assignment.get("symbol_state", {}) or {})
            assignment = assign_checkpoint_context(symbol, record, checkpoint_state or leg_state or record)
            checkpoint_state = dict(assignment.get("symbol_state", {}) or {})
            checkpoint_fields = extract_checkpoint_fields(assignment)
            checkpoint_type = _to_text(checkpoint_fields["checkpoint_type"])
            checkpoint_id = _to_text(checkpoint_fields["checkpoint_id"])
            last_checkpoint = {**record, **checkpoint_fields}
            if checkpoint_type:
                checkpoint_counts[checkpoint_type] = int(checkpoint_counts.get(checkpoint_type, 0) + 1)
            if checkpoint_id and checkpoint_id not in checkpoint_ids:
                checkpoint_ids.append(checkpoint_id)

        runtime_row = dict(runtime_rows.get(symbol, {}) or {})
        if runtime_row:
            if not _to_text(runtime_row.get("leg_id")):
                leg_assignment = assign_leg_id(symbol, runtime_row, leg_state)
                runtime_row.update(extract_leg_runtime_fields(leg_assignment))
                leg_state = dict(leg_assignment.get("symbol_state", {}) or leg_state or {})
            runtime_assignment = assign_checkpoint_context(symbol, runtime_row, checkpoint_state or leg_state or runtime_row)
            runtime_checkpoint_fields = extract_checkpoint_fields(runtime_assignment)
            active_checkpoint_id = runtime_checkpoint_fields["checkpoint_id"]
            active_checkpoint_type = runtime_checkpoint_fields["checkpoint_type"]
            active_checkpoint_index = int(runtime_checkpoint_fields["checkpoint_index_in_leg"])
            latest_source = {**runtime_row, **runtime_checkpoint_fields}
        else:
            active_checkpoint_id = _to_text(checkpoint_state.get("active_checkpoint_id")) if checkpoint_state else ""
            active_checkpoint_type = _to_text(checkpoint_state.get("active_checkpoint_type")) if checkpoint_state else ""
            active_checkpoint_index = _to_int(checkpoint_state.get("active_checkpoint_index"), 0) if checkpoint_state else 0
            latest_source = dict(last_checkpoint)

        row_count = int(len(symbol_frame))
        checkpoint_count = int(len(checkpoint_ids))
        new_checkpoint_share = round(float(checkpoint_count) / float(row_count), 6) if row_count > 0 else 0.0
        focus = f"inspect_{symbol.lower()}_checkpoint_progression"
        if new_checkpoint_share > 0.7:
            focus = f"reduce_{symbol.lower()}_checkpoint_oversegmentation"
        elif checkpoint_counts.get("RECLAIM_CHECK", 0) <= 0:
            focus = f"inspect_{symbol.lower()}_reclaim_gap"
        elif checkpoint_counts.get("RUNNER_CHECK", 0) > checkpoint_counts.get("LATE_TREND_CHECK", 0):
            focus = f"delay_{symbol.lower()}_runner_threshold"

        rows.append(
            {
                "symbol": symbol,
                "recent_row_count": row_count,
                "checkpoint_count": checkpoint_count,
                "new_checkpoint_share": new_checkpoint_share,
                "active_leg_id": _to_text(latest_source.get("leg_id")),
                "active_checkpoint_id": active_checkpoint_id,
                "active_checkpoint_type": active_checkpoint_type,
                "active_checkpoint_index": active_checkpoint_index,
                "checkpoint_type_counts": _json_counts(checkpoint_counts),
                "latest_time": _resolve_row_timestamp(latest_source) if latest_source else "",
                "latest_blocked_by": _to_text(latest_source.get("blocked_by")),
                "recommended_focus": focus,
            }
        )
        total_rows += row_count
        total_checkpoints += checkpoint_count

    distribution = pd.DataFrame(rows, columns=PATH_CHECKPOINT_DISTRIBUTION_COLUMNS)
    summary["checkpoint_count"] = int(total_checkpoints)
    summary["new_checkpoint_share"] = round(float(total_checkpoints) / float(total_rows), 6) if total_rows > 0 else 0.0
    summary["symbol_active_checkpoint_map"] = {
        str(row["symbol"]): _to_text(row["active_checkpoint_id"])
        for row in distribution.to_dict(orient="records")
    }
    summary["symbol_checkpoint_type_counts"] = {
        str(row["symbol"]): json.loads(str(row["checkpoint_type_counts"] or "{}"))
        for row in distribution.to_dict(orient="records")
    }
    summary["recommended_next_action"] = (
        "proceed_to_pa3_checkpoint_context_storage"
        if summary["checkpoint_count"] >= 3 and summary["new_checkpoint_share"] <= 0.6
        else "refine_checkpoint_segmentation_before_pa3"
    )
    return distribution, summary
