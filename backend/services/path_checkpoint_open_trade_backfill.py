"""Backfill position-side checkpoint rows from open trade snapshots."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.path_checkpoint_context import (
    build_exit_position_state,
    default_checkpoint_detail_path,
    default_checkpoint_rows_path,
    record_checkpoint_context,
)
from backend.services.path_checkpoint_segmenter import (
    assign_checkpoint_context,
    extract_checkpoint_fields,
)
from backend.services.path_leg_runtime import (
    assign_leg_id,
    extract_leg_runtime_fields,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_OPEN_TRADE_BACKFILL_CONTRACT_VERSION = "checkpoint_open_trade_backfill_v2"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_runtime_status_detail_path() -> Path:
    return _repo_root() / "data" / "runtime_status.detail.json"


def default_trade_db_path() -> Path:
    return _repo_root() / "data" / "trades" / "trades.db"


def default_checkpoint_open_trade_backfill_artifact_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_open_trade_backfill_latest.json"


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


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_checkpoint_rows(path: str | Path | None = None) -> pd.DataFrame:
    csv_path = Path(path or default_checkpoint_rows_path())
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _load_open_trades(path: str | Path | None = None) -> list[dict[str, Any]]:
    db_path = Path(path or default_trade_db_path())
    if not db_path.exists():
        return []
    query = """
    SELECT
      ticket,
      symbol,
      direction,
      lot,
      open_time,
      open_ts,
      open_price,
      profit,
      decision_row_key,
      runtime_snapshot_key,
      trade_link_key,
      entry_setup_id,
      management_profile_id,
      invalidation_id,
      exit_profile,
      peak_profit_at_exit,
      giveback_usd,
      shock_at_profit,
      exit_wait_decision_family,
      exit_wait_bridge_status,
      status
    FROM open_trades
    WHERE UPPER(COALESCE(status, '')) = 'OPEN'
    ORDER BY CAST(COALESCE(open_ts, '0') AS REAL) ASC, CAST(COALESCE(ticket, '0') AS REAL) ASC
    """
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(query).fetchall()
    finally:
        con.close()
    return [dict(row) for row in rows]


def _load_recent_closed_trades(path: str | Path | None = None, *, limit: int = 80) -> list[dict[str, Any]]:
    db_path = Path(path or default_trade_db_path())
    if not db_path.exists():
        return []
    query = f"""
    SELECT
      ticket,
      symbol,
      direction,
      lot,
      open_time,
      open_ts,
      open_price,
      profit,
      decision_row_key,
      runtime_snapshot_key,
      trade_link_key,
      entry_setup_id,
      management_profile_id,
      invalidation_id,
      exit_profile,
      exit_policy_stage,
      exit_wait_state_family,
      exit_wait_hold_class,
      peak_profit_at_exit,
      giveback_usd,
      shock_at_profit,
      exit_wait_decision_family,
      exit_wait_bridge_status,
      exit_reason,
      close_ts,
      updated_at,
      status
    FROM closed_trades
    ORDER BY CAST(COALESCE(close_ts, '0') AS REAL) DESC, CAST(COALESCE(ticket, '0') AS REAL) DESC
    LIMIT {max(1, int(limit))}
    """
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(query).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        con.close()
    return [dict(row) for row in rows]


def _build_existing_key_set(checkpoint_rows: pd.DataFrame | None) -> set[tuple[str, int, str]]:
    if checkpoint_rows is None or checkpoint_rows.empty:
        return set()
    frame = checkpoint_rows.copy()
    for column in ("source", "ticket", "runtime_snapshot_key"):
        if column not in frame.columns:
            frame[column] = ""
    keys: set[tuple[str, int, str]] = set()
    for row in frame.to_dict(orient="records"):
        keys.add(
            (
                _to_text(row.get("source")),
                _to_int(row.get("ticket"), 0),
                _to_text(row.get("runtime_snapshot_key")),
            )
        )
    return keys


def _build_prior_state_maps(checkpoint_rows: pd.DataFrame | None) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if checkpoint_rows is None or checkpoint_rows.empty:
        return {}, {}
    frame = checkpoint_rows.copy()
    for column in (
        "generated_at",
        "symbol",
        "leg_id",
        "leg_direction",
        "checkpoint_id",
        "checkpoint_type",
        "checkpoint_index_in_leg",
        "bars_since_leg_start",
        "bars_since_last_checkpoint",
        "checkpoint_transition_reason",
    ):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")
    frame = frame.sort_values("__time_sort")
    leg_states: dict[str, dict[str, Any]] = {}
    checkpoint_states: dict[str, dict[str, Any]] = {}
    for symbol, symbol_frame in frame.groupby("symbol", sort=False):
        latest = symbol_frame.iloc[-1]
        leg_id = _to_text(latest.get("leg_id"))
        checkpoint_id = _to_text(latest.get("checkpoint_id"))
        if not symbol or not leg_id:
            continue
        leg_states[symbol] = {
            "symbol": symbol,
            "active_leg_id": leg_id,
            "active_leg_direction": _to_text(latest.get("leg_direction")).upper(),
            "active_leg_state": "ACTIVE",
            "last_transition_reason": _to_text(latest.get("checkpoint_transition_reason")),
            "last_seen_at": _to_text(latest.get("generated_at")),
        }
        checkpoint_states[symbol] = {
            "symbol": symbol,
            "active_leg_id": leg_id,
            "active_checkpoint_id": checkpoint_id,
            "active_checkpoint_type": _to_text(latest.get("checkpoint_type")).upper(),
            "active_checkpoint_index": _to_int(latest.get("checkpoint_index_in_leg"), 0),
            "leg_row_count": max(0, _to_int(latest.get("bars_since_leg_start"), 0) + 1),
            "rows_since_checkpoint_start": max(0, _to_int(latest.get("bars_since_last_checkpoint"), 0) + 1),
            "last_transition_reason": _to_text(latest.get("checkpoint_transition_reason")),
            "last_seen_at": _to_text(latest.get("generated_at")),
        }
    return leg_states, checkpoint_states


def _build_prior_trade_context_map(checkpoint_rows: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if checkpoint_rows is None or checkpoint_rows.empty:
        return {}
    frame = checkpoint_rows.copy()
    for column in (
        "generated_at",
        "ticket",
        "trade_link_key",
        "runner_secured",
        "position_size_fraction",
        "checkpoint_rule_family_hint",
        "exit_stage_family",
        "giveback_from_peak",
        "giveback_ratio",
    ):
        if column not in frame.columns:
            frame[column] = ""
    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")
    frame = frame.sort_values("__time_sort")
    context_map: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        ticket = _to_int(row.get("ticket"), 0)
        trade_link_key = _to_text(row.get("trade_link_key"))
        payload = {
            "runner_secured": _to_bool(row.get("runner_secured"), False),
            "position_size_fraction": _to_float(row.get("position_size_fraction"), 0.0),
            "checkpoint_rule_family_hint": _to_text(row.get("checkpoint_rule_family_hint")).lower(),
            "exit_stage_family": _to_text(row.get("exit_stage_family")).lower(),
            "giveback_from_peak": _to_float(row.get("giveback_from_peak"), 0.0),
            "giveback_ratio": _to_float(row.get("giveback_ratio"), 0.0),
        }
        if ticket > 0:
            context_map[f"ticket::{ticket}"] = dict(payload)
        if trade_link_key:
            context_map[f"trade::{trade_link_key}"] = dict(payload)
    return context_map


def _resolve_backfill_profit(trade: Mapping[str, Any] | None) -> float:
    trade_map = dict(trade or {})
    direct_profit = _to_float(trade_map.get("profit"), 0.0)
    if abs(direct_profit) > 1e-9:
        return float(direct_profit)
    shock_profit = _to_float(trade_map.get("shock_at_profit"), 0.0)
    if abs(shock_profit) > 1e-9:
        return float(shock_profit)
    return 0.0


def _runtime_exit_risk_value(runtime_row: Mapping[str, Any] | None, key: str) -> float:
    runtime_map = dict(runtime_row or {})
    exit_ctx = dict(runtime_map.get("exit_manage_context_v1") or {})
    risk_map = dict(exit_ctx.get("risk") or {})
    return _to_float(risk_map.get(str(key or "")), 0.0)


def _collect_backfill_context_text(
    trade: Mapping[str, Any] | None,
    runtime_row: Mapping[str, Any] | None = None,
) -> str:
    trade_map = dict(trade or {})
    runtime_map = dict(runtime_row or {})
    exit_ctx = dict(runtime_map.get("exit_manage_context_v1") or {})
    posture_map = dict(exit_ctx.get("posture") or {})
    wait_taxonomy = dict(runtime_map.get("exit_wait_taxonomy_v1") or {})
    state_map = dict(wait_taxonomy.get("state") or {})
    decision_map = dict(wait_taxonomy.get("decision") or {})
    bridge_map = dict(wait_taxonomy.get("bridge") or {})
    texts = [
        trade_map.get("exit_reason"),
        trade_map.get("exit_policy_stage"),
        trade_map.get("exit_wait_decision_family"),
        trade_map.get("exit_wait_bridge_status"),
        trade_map.get("exit_wait_state_family"),
        trade_map.get("exit_wait_hold_class"),
        trade_map.get("exit_profile"),
        runtime_map.get("exit_policy_stage"),
        runtime_map.get("exit_wait_decision_family"),
        runtime_map.get("exit_wait_bridge_status"),
        runtime_map.get("exit_wait_state_family"),
        runtime_map.get("exit_wait_hold_class"),
        posture_map.get("policy_stage"),
        posture_map.get("chosen_stage"),
        posture_map.get("resolved_exit_profile"),
        state_map.get("state_family"),
        state_map.get("hold_class"),
        state_map.get("reason"),
        decision_map.get("decision_family"),
        decision_map.get("decision_reason"),
        bridge_map.get("bridge_status"),
    ]
    return " ".join(_to_text(value).lower() for value in texts if _to_text(value))


def _resolve_backfill_peak_profit(
    trade: Mapping[str, Any] | None,
    runtime_row: Mapping[str, Any] | None = None,
    *,
    effective_profit: float = 0.0,
) -> float:
    trade_map = dict(trade or {})
    trade_peak = _to_float(trade_map.get("peak_profit_at_exit"), 0.0)
    runtime_peak = max(0.0, _runtime_exit_risk_value(runtime_row, "peak_profit"))
    giveback_value = _resolve_backfill_giveback(trade, runtime_row)
    inferred_peak = max(0.0, float(effective_profit or 0.0)) + max(0.0, float(giveback_value or 0.0))
    return max(trade_peak, runtime_peak, inferred_peak, max(0.0, float(effective_profit or 0.0)))


def _resolve_backfill_giveback(
    trade: Mapping[str, Any] | None,
    runtime_row: Mapping[str, Any] | None = None,
) -> float:
    trade_map = dict(trade or {})
    direct_giveback = _to_float(trade_map.get("giveback_usd"), 0.0)
    if direct_giveback > 0.0:
        return float(direct_giveback)
    runtime_giveback = max(0.0, _runtime_exit_risk_value(runtime_row, "giveback"))
    if runtime_giveback > 0.0:
        return float(runtime_giveback)
    shock_profit = abs(_to_float(trade_map.get("shock_at_profit"), 0.0))
    if shock_profit > 0.0:
        return float(shock_profit)
    return 0.0


def _infer_backfill_runner_flags(
    trade: Mapping[str, Any] | None,
    runtime_row: Mapping[str, Any] | None = None,
) -> tuple[bool, bool]:
    trade_map = dict(trade or {})
    decision_family = _to_text(trade_map.get("exit_wait_decision_family")).lower()
    bridge_status = _to_text(trade_map.get("exit_wait_bridge_status")).lower()
    context_text = _collect_backfill_context_text(trade_map, runtime_row)
    partial_done = any(token in context_text for token in ("partial", "partial_then_runner_hold", "runner_hold"))
    be_moved = partial_done or any(
        token in context_text
        for token in ("runner_preservation", "lock", "break_even", "hold_continue", "aligned_hold_continue")
    )
    runtime_peak_profit = max(0.0, _runtime_exit_risk_value(runtime_row, "peak_profit"))
    if (not be_moved) and runtime_peak_profit > 0.0 and "mid" in context_text and "hold" in context_text:
        be_moved = True
    if (not partial_done) and any(token in decision_family for token in ("partial", "runner")):
        partial_done = True
    if (not be_moved) and any(token in bridge_status for token in ("runner_preservation", "lock", "break_even")):
        be_moved = True
    return bool(partial_done), bool(be_moved)


def _infer_backfill_stage_family(
    trade: Mapping[str, Any] | None,
    runtime_row: Mapping[str, Any] | None = None,
) -> str:
    candidate = _collect_backfill_context_text(trade, runtime_row)
    if any(token in candidate for token in ("runner", "lock", "break_even")):
        return "runner"
    if "hold_continue" in candidate:
        return "runner"
    if any(token in candidate for token in ("protect", "recovery", "managed_exit", "tight_protect")):
        return "protective"
    if any(token in candidate for token in ("hold", "wait", "mid", "late")):
        return "hold"
    return "backfill"


def _resolve_trade_event_timestamp(
    trade: Mapping[str, Any] | None,
    *,
    prefer_close: bool,
) -> tuple[float, str]:
    trade_map = dict(trade or {})
    ordered_keys = ("close_ts", "updated_at", "open_ts", "open_time") if prefer_close else ("open_ts", "updated_at", "open_time", "close_ts")
    for key in ordered_keys:
        value = trade_map.get(key)
        if value in (None, ""):
            continue
        numeric_value = _to_float(value, 0.0)
        if numeric_value > 0.0:
            ts_value = numeric_value / 1000.0 if numeric_value > 1_000_000_000_000 else numeric_value
            timestamp = pd.to_datetime(ts_value, unit="s", utc=True).tz_convert("Asia/Seoul").isoformat()
            return float(ts_value), timestamp
        text_value = _to_text(value)
        if not text_value:
            continue
        try:
            parsed = pd.to_datetime(text_value, errors="raise")
        except Exception:
            continue
        if pd.isna(parsed):
            continue
        if getattr(parsed, "tzinfo", None) is None:
            parsed = parsed.tz_localize("Asia/Seoul")
        else:
            parsed = parsed.tz_convert("Asia/Seoul")
        return float(parsed.timestamp()), parsed.isoformat()
    generated_at = now_kst_dt()
    return float(generated_at.timestamp()), generated_at.isoformat()


def _classify_closed_trade_backfill_kind(
    trade: Mapping[str, Any] | None,
    *,
    effective_profit: float,
    peak_profit: float,
) -> str:
    if max(float(effective_profit or 0.0), float(peak_profit or 0.0)) <= 0.0:
        return ""
    context_text = _collect_backfill_context_text(trade, None)
    exit_reason = _to_text(dict(trade or {}).get("exit_reason")).lower()
    runner_like = any(token in context_text for token in ("runner", "lock", "break_even", "hold_continue"))
    hold_like = any(token in context_text for token in ("hold", "mid", "late"))
    target_like = "target" in exit_reason or "tp1" in context_text
    if runner_like:
        return "runner"
    if hold_like or target_like:
        return "hold"
    return ""


def _infer_backfill_rule_family_hint(
    trade: Mapping[str, Any] | None,
    *,
    stage_family: str,
    partial_done: bool,
    be_moved: bool,
    effective_profit: float,
) -> str:
    if partial_done or be_moved or stage_family == "runner":
        return "runner_secured_continuation"
    if float(effective_profit or 0.0) < 0.0 and stage_family == "protective":
        return "open_loss_protective"
    if float(effective_profit or 0.0) < 0.0:
        return "active_open_loss"
    if float(effective_profit or 0.0) > 0.0:
        return "profit_hold_bias"
    peak_profit = _to_float(dict(trade or {}).get("peak_profit_at_exit"), 0.0)
    if peak_profit > 0.0:
        return "active_flat_profit"
    return "active_position"


def _resolve_prior_trade_context(
    prior_trade_context_map: Mapping[str, dict[str, Any]] | None,
    trade: Mapping[str, Any] | None,
) -> dict[str, Any]:
    context_map = dict(prior_trade_context_map or {})
    trade_map = dict(trade or {})
    trade_link_key = _to_text(trade_map.get("trade_link_key"))
    ticket = _to_int(trade_map.get("ticket"), 0)
    if trade_link_key and f"trade::{trade_link_key}" in context_map:
        return dict(context_map.get(f"trade::{trade_link_key}") or {})
    if ticket > 0 and f"ticket::{ticket}" in context_map:
        return dict(context_map.get(f"ticket::{ticket}") or {})
    return {}


def backfill_open_trade_checkpoint_rows(
    *,
    runtime_status_detail_path: str | Path | None = None,
    trade_db_path: str | Path | None = None,
    checkpoint_rows_path: str | Path | None = None,
    checkpoint_detail_path: str | Path | None = None,
    source: str = "open_trade_backfill",
) -> dict[str, Any]:
    runtime_detail = _load_json(runtime_status_detail_path or default_runtime_status_detail_path())
    latest_signal_by_symbol = dict(runtime_detail.get("latest_signal_by_symbol") or {})
    checkpoint_rows = _load_checkpoint_rows(checkpoint_rows_path)
    existing_keys = _build_existing_key_set(checkpoint_rows)
    leg_states, checkpoint_states = _build_prior_state_maps(checkpoint_rows)
    prior_trade_context_map = _build_prior_trade_context_map(checkpoint_rows)
    open_trades = _load_open_trades(trade_db_path)
    closed_trades = _load_recent_closed_trades(trade_db_path)
    appended_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []
    missing_runtime_symbols: list[str] = []
    source_key = _to_text(source)
    closed_candidate_count = 0
    closed_appended_count = 0

    for trade in open_trades:
        symbol = _to_text(trade.get("symbol")).upper()
        runtime_row = dict(latest_signal_by_symbol.get(symbol) or {})
        if not runtime_row:
            missing_runtime_symbols.append(symbol)
            skipped_rows.append(
                {
                    "ticket": _to_int(trade.get("ticket"), 0),
                    "symbol": symbol,
                    "reason": "missing_runtime_row",
                }
            )
            continue

        payload = dict(runtime_row)
        payload["symbol"] = symbol
        payload["action"] = _to_text(trade.get("direction")).upper()
        payload["decision_row_key"] = _to_text(payload.get("decision_row_key")) or _to_text(trade.get("decision_row_key"))
        payload["runtime_snapshot_key"] = _to_text(payload.get("runtime_snapshot_key")) or _to_text(trade.get("runtime_snapshot_key"))
        payload["trade_link_key"] = _to_text(payload.get("trade_link_key")) or _to_text(trade.get("trade_link_key"))

        ticket = _to_int(trade.get("ticket"), 0)
        dedupe_key = (source_key, ticket, _to_text(payload.get("runtime_snapshot_key")))
        if dedupe_key in existing_keys:
            skipped_rows.append({"ticket": ticket, "symbol": symbol, "reason": "already_backfilled"})
            continue

        leg_assignment = assign_leg_id(symbol, payload, leg_states.get(symbol))
        payload.update(extract_leg_runtime_fields(leg_assignment))
        leg_states[symbol] = dict(leg_assignment.get("symbol_state", {}) or {})

        checkpoint_assignment = assign_checkpoint_context(symbol, payload, checkpoint_states.get(symbol, leg_states[symbol]))
        payload.update(extract_checkpoint_fields(checkpoint_assignment))
        checkpoint_states[symbol] = dict(checkpoint_assignment.get("symbol_state", {}) or {})

        effective_profit = _resolve_backfill_profit(trade)
        partial_done, be_moved = _infer_backfill_runner_flags(trade, runtime_row)
        prior_trade_context = _resolve_prior_trade_context(prior_trade_context_map, trade)
        if not partial_done and bool(prior_trade_context.get("runner_secured")):
            partial_done = True
        if not be_moved and (
            bool(prior_trade_context.get("runner_secured"))
            or _to_float(prior_trade_context.get("position_size_fraction"), 1.0) < 0.99
            or _to_text(prior_trade_context.get("checkpoint_rule_family_hint")).lower() == "runner_secured_continuation"
        ):
            be_moved = True
        stage_family = _infer_backfill_stage_family(trade, runtime_row)
        if stage_family == "backfill" and _to_text(prior_trade_context.get("exit_stage_family")).lower():
            stage_family = _to_text(prior_trade_context.get("exit_stage_family")).lower()
        payload["exit_stage_family"] = stage_family
        payload["checkpoint_rule_family_hint"] = _infer_backfill_rule_family_hint(
            trade,
            stage_family=stage_family,
            partial_done=partial_done,
            be_moved=be_moved,
            effective_profit=effective_profit,
        )
        record_payload = record_checkpoint_context(
            runtime=None,
            symbol=symbol,
            runtime_row=payload,
            symbol_state=checkpoint_states[symbol],
            position_state=build_exit_position_state(
                direction=_to_text(trade.get("direction")).upper(),
                ticket=ticket,
                current_lot=_to_float(trade.get("lot"), 0.0),
                entry_lot=_to_float(trade.get("lot"), 0.0),
                entry_price=_to_float(trade.get("open_price"), 0.0),
                profit=effective_profit,
                peak_profit=_resolve_backfill_peak_profit(trade, runtime_row, effective_profit=effective_profit),
                giveback_usd=_resolve_backfill_giveback(trade, runtime_row),
                partial_done=partial_done,
                be_moved=be_moved,
            ),
            source=source_key,
            csv_path=checkpoint_rows_path or default_checkpoint_rows_path(),
            detail_path=checkpoint_detail_path or default_checkpoint_detail_path(),
        )
        appended_row = dict(record_payload.get("row", {}) or {})
        appended_rows.append(appended_row)
        existing_keys.add((source_key, ticket, _to_text(appended_row.get("runtime_snapshot_key"))))

    for trade in closed_trades:
        symbol = _to_text(trade.get("symbol")).upper()
        runtime_row = dict(latest_signal_by_symbol.get(symbol) or {})
        if not runtime_row:
            continue
        effective_profit = _resolve_backfill_profit(trade)
        peak_profit = _resolve_backfill_peak_profit(trade, runtime_row, effective_profit=effective_profit)
        closed_kind = _classify_closed_trade_backfill_kind(
            trade,
            effective_profit=effective_profit,
            peak_profit=peak_profit,
        )
        if not closed_kind:
            continue
        closed_candidate_count += 1
        source_key = "closed_trade_runner_backfill" if closed_kind == "runner" else "closed_trade_hold_backfill"
        ticket = _to_int(trade.get("ticket"), 0)
        dedupe_runtime_snapshot_key = _to_text(trade.get("runtime_snapshot_key")) or f"closed_trade::{ticket}::{_to_text(trade.get('close_ts'))}"
        dedupe_key = (source_key, ticket, dedupe_runtime_snapshot_key)
        if dedupe_key in existing_keys:
            continue

        payload = dict(runtime_row)
        event_time, event_timestamp = _resolve_trade_event_timestamp(trade, prefer_close=True)
        payload["time"] = event_time
        payload["timestamp"] = event_timestamp
        payload["symbol"] = symbol
        payload["action"] = _to_text(trade.get("direction")).upper()
        payload["observe_action"] = _to_text(payload.get("observe_action"), "WAIT") or "WAIT"
        payload["decision_row_key"] = _to_text(payload.get("decision_row_key")) or _to_text(trade.get("decision_row_key"))
        payload["runtime_snapshot_key"] = dedupe_runtime_snapshot_key
        payload["trade_link_key"] = _to_text(payload.get("trade_link_key")) or _to_text(trade.get("trade_link_key"))
        payload["blocked_by"] = _to_text(trade.get("exit_reason")) or _to_text(payload.get("blocked_by"))
        payload["outcome"] = "runner_hold" if closed_kind == "runner" else "closed_profit_hold"

        leg_assignment = assign_leg_id(symbol, payload, leg_states.get(symbol))
        payload.update(extract_leg_runtime_fields(leg_assignment))
        leg_states[symbol] = dict(leg_assignment.get("symbol_state", {}) or {})

        checkpoint_assignment = assign_checkpoint_context(symbol, payload, checkpoint_states.get(symbol, leg_states[symbol]))
        payload.update(extract_checkpoint_fields(checkpoint_assignment))
        checkpoint_states[symbol] = dict(checkpoint_assignment.get("symbol_state", {}) or {})

        partial_done, be_moved = _infer_backfill_runner_flags(trade, runtime_row)
        if closed_kind == "runner":
            be_moved = True
        stage_family = _infer_backfill_stage_family(trade, runtime_row)
        if stage_family == "backfill":
            stage_family = "runner" if closed_kind == "runner" else "hold"
        payload["exit_stage_family"] = stage_family
        payload["checkpoint_rule_family_hint"] = _infer_backfill_rule_family_hint(
            trade,
            stage_family=stage_family,
            partial_done=partial_done,
            be_moved=be_moved,
            effective_profit=effective_profit,
        )

        record_payload = record_checkpoint_context(
            runtime=None,
            symbol=symbol,
            runtime_row=payload,
            symbol_state=checkpoint_states[symbol],
            position_state=build_exit_position_state(
                direction=_to_text(trade.get("direction")).upper(),
                ticket=ticket,
                current_lot=_to_float(trade.get("lot"), 0.0),
                entry_lot=_to_float(trade.get("lot"), 0.0),
                entry_price=_to_float(trade.get("open_price"), 0.0),
                profit=effective_profit,
                peak_profit=peak_profit,
                giveback_usd=_resolve_backfill_giveback(trade, runtime_row),
                partial_done=partial_done,
                be_moved=be_moved,
            ),
            source=source_key,
            csv_path=checkpoint_rows_path or default_checkpoint_rows_path(),
            detail_path=checkpoint_detail_path or default_checkpoint_detail_path(),
        )
        appended_row = dict(record_payload.get("row", {}) or {})
        appended_rows.append(appended_row)
        closed_appended_count += 1
        existing_keys.add((source_key, ticket, _to_text(appended_row.get("runtime_snapshot_key"))))

    checkpoint_rows_after = _load_checkpoint_rows(checkpoint_rows_path or default_checkpoint_rows_path())
    runner_secured_row_count_after = 0
    if not checkpoint_rows_after.empty and "runner_secured" in checkpoint_rows_after.columns:
        runner_secured_row_count_after = int(
            checkpoint_rows_after["runner_secured"].fillna("").astype(str).str.lower().isin({"true", "1"}).sum()
        )
    summary = {
        "contract_version": PATH_CHECKPOINT_OPEN_TRADE_BACKFILL_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "runtime_updated_at": _to_text(runtime_detail.get("updated_at")),
        "open_trade_count": int(len(open_trades)),
        "closed_trade_count": int(len(closed_trades)),
        "closed_candidate_count": int(closed_candidate_count),
        "appended_count": int(len(appended_rows)),
        "closed_appended_count": int(closed_appended_count),
        "skipped_count": int(len(skipped_rows)),
        "missing_runtime_symbol_count": int(len(set(missing_runtime_symbols))),
        "appended_symbol_counts": pd.Series([row.get("symbol", "") for row in appended_rows]).value_counts().to_dict() if appended_rows else {},
        "position_side_row_count_after": int(
            (
                _load_checkpoint_rows(checkpoint_rows_path or default_checkpoint_rows_path())["position_side"]
                .fillna("")
                .astype(str)
                .str.upper()
                != "FLAT"
            ).sum()
        )
        if (checkpoint_rows_path or default_checkpoint_rows_path()) and Path(checkpoint_rows_path or default_checkpoint_rows_path()).exists()
        else 0,
        "runner_secured_row_count_after": int(runner_secured_row_count_after),
        "recommended_next_action": (
            "rebuild_pa5_dataset_after_position_side_backfill"
            if appended_rows
            else "wait_for_new_open_trade_or_runtime_checkpoint"
        ),
    }
    return {
        "summary": summary,
        "appended_rows": appended_rows,
        "skipped_rows": skipped_rows,
    }
