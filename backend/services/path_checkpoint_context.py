"""Path-aware checkpoint context row building and runtime storage for PA3."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.path_checkpoint_segmenter import (
    PATH_CHECKPOINT_TYPES,
)
from backend.services.path_checkpoint_scene_contract import (
    PATH_CHECKPOINT_SCENE_ACTION_BIAS_STRENGTHS,
    PATH_CHECKPOINT_SCENE_ALIGNMENT_STATES,
    PATH_CHECKPOINT_SCENE_COARSE_FAMILIES,
    PATH_CHECKPOINT_SCENE_CONFIDENCE_BANDS,
    PATH_CHECKPOINT_SCENE_GATE_BLOCK_LEVELS,
    PATH_CHECKPOINT_SCENE_MATURITY_LEVELS,
    PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS,
    build_default_scene_runtime_payload,
)
from backend.services.path_checkpoint_scene_tagger import (
    tag_runtime_scene,
)
from backend.services.path_checkpoint_scene_runtime_bridge import (
    PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS,
    PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_PREFIXED_KEYS,
    apply_checkpoint_scene_runtime_bridge_to_runtime_row,
    build_checkpoint_scene_log_only_bridge_v1,
    build_default_scene_candidate_runtime_bridge_payload,
)
from backend.services.path_checkpoint_action_resolver import (
    PATH_CHECKPOINT_MANAGEMENT_ACTION_KEYS,
    PATH_CHECKPOINT_MANAGEMENT_ACTION_PREFIXED_KEYS,
    apply_management_action_to_runtime_row,
    resolve_management_action,
)
from backend.services.path_checkpoint_scoring import (
    PATH_CHECKPOINT_RUNTIME_SCORE_KEYS,
    PATH_CHECKPOINT_RUNTIME_SCORE_PREFIXED_KEYS,
    apply_checkpoint_scores_to_runtime_row,
    build_passive_checkpoint_scores,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_CONTEXT_CONTRACT_VERSION = "path_checkpoint_context_v3"
PATH_CHECKPOINT_CONTEXT_SNAPSHOT_CONTRACT_VERSION = "path_checkpoint_context_snapshot_v3"
PATH_CHECKPOINT_RUNTIME_COLUMNS = [
    "generated_at",
    "source",
    "symbol",
    "surface_name",
    "leg_id",
    "leg_direction",
    "checkpoint_id",
    "checkpoint_type",
    "checkpoint_index_in_leg",
    "checkpoint_transition_reason",
    "bars_since_leg_start",
    "bars_since_last_push",
    "bars_since_last_checkpoint",
    "position_side",
    "position_size_fraction",
    "avg_entry_price",
    "realized_pnl_state",
    "unrealized_pnl_state",
    "runner_secured",
    "mfe_since_entry",
    "mae_since_entry",
    "current_profit",
    "giveback_from_peak",
    "giveback_ratio",
    "checkpoint_rule_family_hint",
    "exit_stage_family",
    *PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS,
    *PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS,
    "runtime_continuation_odds",
    "runtime_reversal_odds",
    "runtime_hold_quality_score",
    "runtime_partial_exit_ev",
    "runtime_full_exit_risk",
    "runtime_rebuy_readiness",
    "runtime_score_reason",
    "management_action_label",
    "management_action_confidence",
    "management_action_reason",
    "management_action_score_gap",
    "ticket",
    "action",
    "outcome",
    "blocked_by",
    "observe_action",
    "observe_side",
    "decision_row_key",
    "runtime_snapshot_key",
    "trade_link_key",
]
PATH_CHECKPOINT_RUNTIME_SCALAR_KEYS = (
    "surface_name",
    "bars_since_leg_start",
    "bars_since_last_push",
    "bars_since_last_checkpoint",
    "position_side",
    "position_size_fraction",
    "avg_entry_price",
    "realized_pnl_state",
    "unrealized_pnl_state",
    "runner_secured",
    "mfe_since_entry",
    "mae_since_entry",
    "current_profit",
    "giveback_from_peak",
    "giveback_ratio",
    "checkpoint_rule_family_hint",
    "exit_stage_family",
    *PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS,
    *PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS,
    *PATH_CHECKPOINT_RUNTIME_SCORE_KEYS,
    *PATH_CHECKPOINT_MANAGEMENT_ACTION_KEYS,
)
PATH_CHECKPOINT_RUNTIME_PREFIXED_KEYS = {
    "surface_name": "checkpoint_surface_name",
    "bars_since_leg_start": "checkpoint_bars_since_leg_start",
    "bars_since_last_push": "checkpoint_bars_since_last_push",
    "bars_since_last_checkpoint": "checkpoint_bars_since_last_checkpoint",
    "position_side": "checkpoint_position_side",
    "position_size_fraction": "checkpoint_position_size_fraction",
    "avg_entry_price": "checkpoint_avg_entry_price",
    "realized_pnl_state": "checkpoint_realized_pnl_state",
    "unrealized_pnl_state": "checkpoint_unrealized_pnl_state",
    "runner_secured": "checkpoint_runner_secured",
    "mfe_since_entry": "checkpoint_mfe_since_entry",
    "mae_since_entry": "checkpoint_mae_since_entry",
    "current_profit": "checkpoint_current_profit",
    "giveback_from_peak": "checkpoint_giveback_from_peak",
    "giveback_ratio": "checkpoint_giveback_ratio",
    "checkpoint_rule_family_hint": "checkpoint_rule_family_hint",
    "exit_stage_family": "checkpoint_exit_stage_family",
    "runtime_scene_coarse_family": "checkpoint_runtime_scene_coarse_family",
    "runtime_scene_fine_label": "checkpoint_runtime_scene_fine_label",
    "runtime_scene_gate_label": "checkpoint_runtime_scene_gate_label",
    "runtime_scene_modifier_json": "checkpoint_runtime_scene_modifier_json",
    "runtime_scene_confidence": "checkpoint_runtime_scene_confidence",
    "runtime_scene_confidence_band": "checkpoint_runtime_scene_confidence_band",
    "runtime_scene_action_bias_strength": "checkpoint_runtime_scene_action_bias_strength",
    "runtime_scene_source": "checkpoint_runtime_scene_source",
    "runtime_scene_maturity": "checkpoint_runtime_scene_maturity",
    "runtime_scene_transition_from": "checkpoint_runtime_scene_transition_from",
    "runtime_scene_transition_bars": "checkpoint_runtime_scene_transition_bars",
    "runtime_scene_transition_speed": "checkpoint_runtime_scene_transition_speed",
    "runtime_scene_family_alignment": "checkpoint_runtime_scene_family_alignment",
    "runtime_scene_gate_block_level": "checkpoint_runtime_scene_gate_block_level",
    "hindsight_scene_fine_label": "checkpoint_hindsight_scene_fine_label",
    "hindsight_scene_quality_tier": "checkpoint_hindsight_scene_quality_tier",
    **PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_PREFIXED_KEYS,
    **PATH_CHECKPOINT_RUNTIME_SCORE_PREFIXED_KEYS,
    **PATH_CHECKPOINT_MANAGEMENT_ACTION_PREFIXED_KEYS,
}
PATH_CHECKPOINT_CONTEXT_SNAPSHOT_COLUMNS = [
    "symbol",
    "recent_row_count",
    "source_counts",
    "surface_counts",
    "checkpoint_type_counts",
    "runner_secured_count",
    "open_profit_row_count",
    "open_loss_row_count",
    "latest_checkpoint_id",
    "latest_surface_name",
    "latest_time",
    "recommended_focus",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_rows_path() -> Path:
    return _repo_root() / "data" / "runtime" / "checkpoint_rows.csv"


def default_checkpoint_detail_path() -> Path:
    return _repo_root() / "data" / "runtime" / "checkpoint_rows.detail.jsonl"


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


def _ensure_checkpoint_csv_schema(csv_file: Path) -> None:
    if not csv_file.exists():
        return
    try:
        frame = pd.read_csv(csv_file, encoding="utf-8-sig", low_memory=False)
    except Exception:
        frame = pd.read_csv(csv_file, low_memory=False)
    existing_columns = list(frame.columns)
    if existing_columns == PATH_CHECKPOINT_RUNTIME_COLUMNS:
        return
    for column in PATH_CHECKPOINT_RUNTIME_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame = frame.loc[:, PATH_CHECKPOINT_RUNTIME_COLUMNS]
    frame.to_csv(csv_file, index=False, encoding="utf-8-sig")


def build_flat_position_state() -> dict[str, Any]:
    return {
        "position_side": "FLAT",
        "position_size_fraction": 0.0,
        "avg_entry_price": 0.0,
        "realized_pnl_state": "NONE",
        "unrealized_pnl_state": "FLAT",
        "runner_secured": False,
        "mfe_since_entry": 0.0,
        "mae_since_entry": 0.0,
        "current_profit": 0.0,
        "giveback_from_peak": 0.0,
        "giveback_ratio": 0.0,
        "ticket": 0,
    }


def build_exit_position_state(
    *,
    direction: str,
    ticket: int,
    current_lot: float,
    entry_lot: float | None = None,
    entry_price: float = 0.0,
    profit: float = 0.0,
    peak_profit: float = 0.0,
    giveback_usd: float | None = None,
    partial_done: bool = False,
    be_moved: bool = False,
) -> dict[str, Any]:
    entry_lot_value = float(entry_lot if entry_lot not in (None, 0, "") else current_lot or 0.0)
    current_lot_value = max(0.0, float(current_lot or 0.0))
    size_fraction = 0.0
    if entry_lot_value > 0.0:
        size_fraction = max(0.0, min(1.0, current_lot_value / entry_lot_value))
    realized_state = "PARTIAL_LOCKED" if partial_done else ("LOCKED" if be_moved else "NONE")
    profit_value = float(profit or 0.0)
    peak_profit_value = float(peak_profit or 0.0)
    if profit_value > 0:
        unrealized_state = "OPEN_PROFIT"
    elif profit_value < 0:
        unrealized_state = "OPEN_LOSS"
    else:
        unrealized_state = "FLAT"
    runner_secured = bool(partial_done or be_moved)
    explicit_giveback = None if giveback_usd in (None, "") else float(giveback_usd)
    if explicit_giveback is not None and explicit_giveback <= 0.0:
        explicit_giveback = None
    derived_peak_anchor = max(0.0, peak_profit_value)
    derived_giveback = max(0.0, derived_peak_anchor - profit_value)
    giveback_from_peak = float(explicit_giveback) if explicit_giveback is not None else float(derived_giveback)
    giveback_base = max(derived_peak_anchor, abs(profit_value), 0.0)
    giveback_ratio = 0.0
    if giveback_base > 1e-9:
        giveback_ratio = max(0.0, min(0.99, giveback_from_peak / giveback_base))
    return {
        "position_side": _to_text(direction).upper() or "FLAT",
        "position_size_fraction": round(float(size_fraction), 6),
        "avg_entry_price": round(float(entry_price or 0.0), 6),
        "realized_pnl_state": realized_state,
        "unrealized_pnl_state": unrealized_state,
        "runner_secured": runner_secured,
        "mfe_since_entry": round(float(max(0.0, peak_profit_value)), 6),
        "mae_since_entry": round(float(max(0.0, -profit_value)) if profit_value < 0 else 0.0, 6),
        "current_profit": round(profit_value, 6),
        "giveback_from_peak": round(float(giveback_from_peak), 6),
        "giveback_ratio": round(float(giveback_ratio), 6),
        "ticket": int(ticket or 0),
    }


def _resolve_exit_stage_family(source: str, row: Mapping[str, Any] | None) -> str:
    row_map = dict(row or {})
    explicit = _to_text(row_map.get("exit_stage_family")).lower()
    if explicit:
        return explicit
    source_text = _to_text(source).lower()
    final_stage = _to_text(row_map.get("exit_manage_final_stage")).lower()
    candidate = " ".join(part for part in (source_text, final_stage) if part)
    if any(token in candidate for token in ("protective", "managed_exit", "recovery")):
        return "protective"
    if "runner" in candidate:
        return "runner"
    if any(token in candidate for token in ("hold", "wait", "delay")):
        return "hold"
    if "backfill" in source_text:
        return "backfill"
    return ""


def _resolve_checkpoint_rule_family_hint(
    source: str,
    row: Mapping[str, Any] | None,
    position_state: Mapping[str, Any] | None,
) -> str:
    row_map = dict(row or {})
    position = dict(position_state or {})
    explicit = _to_text(row_map.get("checkpoint_rule_family_hint")).lower()
    if explicit:
        return explicit
    position_side = _to_text(position.get("position_side"), "FLAT").upper()
    pnl_state = _to_text(position.get("unrealized_pnl_state"), "FLAT").upper()
    runner_secured = _to_bool(position.get("runner_secured"), False)
    stage_family = _resolve_exit_stage_family(source, row_map)
    if position_side == "FLAT":
        return "flat_checkpoint"
    if runner_secured:
        return "runner_secured_continuation"
    if pnl_state == "OPEN_LOSS" and stage_family == "protective":
        return "open_loss_protective"
    if pnl_state == "OPEN_LOSS":
        return "active_open_loss"
    if pnl_state == "OPEN_PROFIT":
        return "profit_hold_bias"
    if pnl_state == "FLAT":
        return "active_flat_profit"
    return "active_position"


def _resolve_surface_name(
    checkpoint_type: str,
    row: Mapping[str, Any] | None,
    position_state: Mapping[str, Any] | None,
    *,
    source: str,
) -> str:
    checkpoint_type_u = _to_text(checkpoint_type).upper()
    row_map = dict(row or {})
    pos_map = dict(position_state or {})
    blocked_by = _to_text(row_map.get("blocked_by")).lower()
    unrealized = _to_text(pos_map.get("unrealized_pnl_state")).upper()
    if checkpoint_type_u in {"INITIAL_PUSH", "FIRST_PULLBACK_CHECK"}:
        return "follow_through_surface"
    if source.startswith("exit") and (unrealized == "OPEN_LOSS" or "protect" in blocked_by or "adverse" in blocked_by):
        return "protective_exit_surface"
    if checkpoint_type_u in {"RECLAIM_CHECK", "LATE_TREND_CHECK", "RUNNER_CHECK"}:
        return "continuation_hold_surface"
    return "follow_through_surface"


def build_checkpoint_context(
    *,
    symbol: str,
    runtime_row: Mapping[str, Any] | None,
    symbol_state: Mapping[str, Any] | None = None,
    position_state: Mapping[str, Any] | None = None,
    source: str = "entry_runtime",
) -> dict[str, Any]:
    row = dict(runtime_row or {})
    state = dict(symbol_state or {})
    checkpoint_type = _to_text(row.get("checkpoint_type")).upper()
    if checkpoint_type not in PATH_CHECKPOINT_TYPES:
        checkpoint_type = ""
    position = dict(position_state or build_flat_position_state())
    rows_since_checkpoint_start = max(1, _to_int(state.get("rows_since_checkpoint_start"), 1))
    leg_row_count = max(1, _to_int(state.get("leg_row_count"), rows_since_checkpoint_start))
    bars_since_last_checkpoint = max(0, rows_since_checkpoint_start - 1)
    if checkpoint_type in {"INITIAL_PUSH", "RECLAIM_CHECK"}:
        bars_since_last_push = 0
    elif checkpoint_type == "FIRST_PULLBACK_CHECK":
        bars_since_last_push = max(1, bars_since_last_checkpoint)
    else:
        bars_since_last_push = max(0, bars_since_last_checkpoint)
    surface_name = _resolve_surface_name(checkpoint_type, row, position, source=source)
    exit_stage_family = _resolve_exit_stage_family(source, row)
    checkpoint_rule_family_hint = _resolve_checkpoint_rule_family_hint(source, row, position)
    scene_payload = build_default_scene_runtime_payload(overrides=row)
    bridge_payload = build_default_scene_candidate_runtime_bridge_payload(overrides=row)
    context_row = {
        "generated_at": _resolve_row_timestamp(row),
        "source": _to_text(source),
        "symbol": _to_text(symbol or row.get("symbol")).upper(),
        "surface_name": surface_name,
        "leg_id": _to_text(row.get("leg_id")),
        "leg_direction": _to_text(row.get("leg_direction")).upper(),
        "checkpoint_id": _to_text(row.get("checkpoint_id")),
        "checkpoint_type": checkpoint_type,
        "checkpoint_index_in_leg": _to_int(row.get("checkpoint_index_in_leg"), 0),
        "checkpoint_transition_reason": _to_text(row.get("checkpoint_transition_reason")),
        "bars_since_leg_start": max(0, leg_row_count - 1),
        "bars_since_last_push": int(bars_since_last_push),
        "bars_since_last_checkpoint": int(bars_since_last_checkpoint),
        "position_side": _to_text(position.get("position_side"), "FLAT").upper(),
        "position_size_fraction": round(_to_float(position.get("position_size_fraction"), 0.0), 6),
        "avg_entry_price": round(_to_float(position.get("avg_entry_price"), 0.0), 6),
        "realized_pnl_state": _to_text(position.get("realized_pnl_state"), "NONE").upper(),
        "unrealized_pnl_state": _to_text(position.get("unrealized_pnl_state"), "FLAT").upper(),
        "runner_secured": bool(_to_bool(position.get("runner_secured"), False)),
        "mfe_since_entry": round(_to_float(position.get("mfe_since_entry"), 0.0), 6),
        "mae_since_entry": round(_to_float(position.get("mae_since_entry"), 0.0), 6),
        "current_profit": round(_to_float(position.get("current_profit"), 0.0), 6),
        "giveback_from_peak": round(_to_float(position.get("giveback_from_peak"), 0.0), 6),
        "giveback_ratio": round(_to_float(position.get("giveback_ratio"), 0.0), 6),
        "checkpoint_rule_family_hint": checkpoint_rule_family_hint,
        "exit_stage_family": exit_stage_family,
        **scene_payload,
        **bridge_payload,
        "ticket": _to_int(position.get("ticket"), 0),
        "action": _to_text(row.get("action")).upper(),
        "outcome": _to_text(row.get("outcome")).lower(),
        "blocked_by": _to_text(row.get("blocked_by")),
        "observe_action": _to_text(row.get("observe_action")).upper(),
        "observe_side": _to_text(row.get("observe_side")).upper(),
        "decision_row_key": _to_text(row.get("decision_row_key")),
        "runtime_snapshot_key": _to_text(row.get("runtime_snapshot_key")),
        "trade_link_key": _to_text(row.get("trade_link_key")),
    }
    return {
        "contract_version": PATH_CHECKPOINT_CONTEXT_CONTRACT_VERSION,
        "row": context_row,
        "detail": {
            "contract_version": PATH_CHECKPOINT_CONTEXT_CONTRACT_VERSION,
            "row": dict(context_row),
            "scene": dict(scene_payload),
            "position_state": dict(position),
            "runtime_row": dict(row),
            "checkpoint_state": dict(state),
        },
    }


def apply_checkpoint_context_to_runtime_row(
    runtime_row: Mapping[str, Any] | None,
    context_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(runtime_row or {})
    context = dict(context_row or {})
    updated["path_checkpoint_context_contract_version"] = PATH_CHECKPOINT_CONTEXT_CONTRACT_VERSION
    for source_key, target_key in PATH_CHECKPOINT_RUNTIME_PREFIXED_KEYS.items():
        if source_key in context:
            updated[target_key] = context.get(source_key)
    return updated


def append_checkpoint_context_row(
    context_row: Mapping[str, Any] | None,
    detail_payload: Mapping[str, Any] | None = None,
    *,
    csv_path: str | Path | None = None,
    detail_path: str | Path | None = None,
) -> dict[str, Any]:
    row = dict(context_row or {})
    detail = dict(detail_payload or {})
    csv_file = Path(csv_path or default_checkpoint_rows_path())
    detail_file = Path(detail_path or default_checkpoint_detail_path())
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    detail_file.parent.mkdir(parents=True, exist_ok=True)
    _ensure_checkpoint_csv_schema(csv_file)

    is_new = not csv_file.exists()
    with csv_file.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=PATH_CHECKPOINT_RUNTIME_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow({column: row.get(column, "") for column in PATH_CHECKPOINT_RUNTIME_COLUMNS})

    with detail_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(detail, ensure_ascii=False, separators=(",", ":")) + "\n")

    return {
        "csv_path": str(csv_file),
        "detail_path": str(detail_file),
        "appended": True,
    }


def _uses_default_checkpoint_runtime_paths(
    *,
    csv_path: str | Path | None,
    detail_path: str | Path | None,
) -> bool:
    csv_file = Path(csv_path or default_checkpoint_rows_path()).resolve()
    detail_file = Path(detail_path or default_checkpoint_detail_path()).resolve()
    return csv_file == default_checkpoint_rows_path().resolve() and detail_file == default_checkpoint_detail_path().resolve()


def record_checkpoint_context(
    *,
    runtime: object | None,
    symbol: str,
    runtime_row: Mapping[str, Any] | None,
    symbol_state: Mapping[str, Any] | None = None,
    position_state: Mapping[str, Any] | None = None,
    source: str = "entry_runtime",
    csv_path: str | Path | None = None,
    detail_path: str | Path | None = None,
    scene_bridge_active_state_path: str | Path | None = None,
    scene_bridge_latest_run_path: str | Path | None = None,
    refresh_analysis: bool = True,
) -> dict[str, Any]:
    symbol_u = _to_text(symbol).upper()
    runtime_rows = getattr(runtime, "latest_signal_by_symbol", None) if runtime is not None else None
    previous_runtime_entry = {}
    if isinstance(runtime_rows, dict):
        previous_runtime_entry = dict(runtime_rows.get(symbol_u, {}) or {})
    payload = build_checkpoint_context(
        symbol=str(symbol),
        runtime_row=runtime_row,
        symbol_state=symbol_state,
        position_state=position_state,
        source=source,
    )
    context_row = dict(payload.get("row", {}) or {})
    detail = dict(payload.get("detail", {}) or {})
    score_payload = build_passive_checkpoint_scores(
        symbol=str(symbol),
        runtime_row=runtime_row,
        checkpoint_row=context_row,
        symbol_state=symbol_state,
        position_state=position_state,
    )
    score_row = dict(score_payload.get("row", {}) or {})
    context_row.update(score_row)
    scene_payload = tag_runtime_scene(
        symbol=str(symbol),
        runtime_row=runtime_row,
        checkpoint_row=context_row,
        symbol_state=symbol_state,
        position_state=position_state,
        previous_runtime_row=previous_runtime_entry,
    )
    scene_row = dict(scene_payload.get("row", {}) or {})
    context_row.update(scene_row)
    action_payload = resolve_management_action(checkpoint_ctx=context_row)
    action_row = {key: action_payload.get(key) for key in PATH_CHECKPOINT_MANAGEMENT_ACTION_KEYS}
    context_row.update(action_row)
    bridge_payload = build_checkpoint_scene_log_only_bridge_v1(
        context_row,
        active_state_path=scene_bridge_active_state_path,
        latest_run_path=scene_bridge_latest_run_path,
    )
    bridge_row = dict(bridge_payload.get("row", {}) or {})
    context_row.update(bridge_row)
    detail["row"] = dict(context_row)
    detail["scene"] = dict(scene_payload.get("detail", {}) or {})
    detail["scoring"] = dict(score_payload.get("detail", {}) or {})
    detail["management_action"] = dict(action_payload or {})
    detail["scene_candidate_bridge"] = dict(bridge_payload.get("detail", {}) or {})
    if isinstance(runtime_rows, dict):
        runtime_entry = dict(previous_runtime_entry or {})
        runtime_entry = apply_checkpoint_context_to_runtime_row(runtime_entry, context_row)
        runtime_entry = apply_checkpoint_scores_to_runtime_row(runtime_entry, score_row)
        runtime_entry = apply_management_action_to_runtime_row(runtime_entry, action_row)
        runtime_entry = apply_checkpoint_scene_runtime_bridge_to_runtime_row(runtime_entry, bridge_row)
        runtime_rows[symbol_u] = runtime_entry
    append_result = append_checkpoint_context_row(
        context_row,
        detail,
        csv_path=csv_path,
        detail_path=detail_path,
    )
    analysis_refresh: dict[str, Any] = {}
    if (
        refresh_analysis
        and _uses_default_checkpoint_runtime_paths(csv_path=csv_path, detail_path=detail_path)
    ):
        try:
            from backend.services.path_checkpoint_analysis_refresh import (
                maybe_refresh_checkpoint_analysis_chain,
            )

            analysis_refresh = maybe_refresh_checkpoint_analysis_chain(
                checkpoint_rows_path=append_result.get("csv_path"),
                runtime_updated_at=_to_text(context_row.get("generated_at")),
            )
        except Exception as exc:
            analysis_refresh = {
                "summary": {
                    "trigger_state": "SKIP_REFRESH_ERROR",
                    "error": _to_text(exc),
                }
            }
    elif not refresh_analysis:
        analysis_refresh = {
            "summary": {
                "trigger_state": "SKIP_REFRESH_DISABLED",
                "recommended_next_action": "refresh_checkpoint_analysis_chain_outside_hot_path",
            }
        }
    return {
        "contract_version": PATH_CHECKPOINT_CONTEXT_CONTRACT_VERSION,
        "row": context_row,
        "detail": detail,
        "append_result": append_result,
        "analysis_refresh": analysis_refresh,
    }


def build_checkpoint_context_snapshot(
    runtime_status: Mapping[str, Any] | None,
    checkpoint_rows: pd.DataFrame | None,
    *,
    recent_limit: int = 400,
    symbols: Iterable[str] = ("BTCUSD", "NAS100", "XAUUSD"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    frame = checkpoint_rows.copy() if checkpoint_rows is not None and not checkpoint_rows.empty else pd.DataFrame()
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_CONTEXT_SNAPSHOT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "recent_row_count": 0,
        "market_family_row_count": 0,
        "runner_secured_count": 0,
        "surface_counts": {},
        "checkpoint_type_counts": {},
        "recommended_next_action": "collect_more_checkpoint_context_rows",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_CONTEXT_SNAPSHOT_COLUMNS), summary

    for column in (
        "generated_at",
        "symbol",
        "source",
        "surface_name",
        "checkpoint_type",
        "runner_secured",
        "unrealized_pnl_state",
        "checkpoint_id",
    ):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")
    recent = frame.sort_values("__time_sort").tail(max(1, int(recent_limit))).copy()
    scoped = recent.loc[recent["symbol"].isin(symbol_order)].copy()
    summary["recent_row_count"] = int(len(recent))
    summary["market_family_row_count"] = int(len(scoped))

    rows: list[dict[str, Any]] = []
    global_surface_counts: dict[str, int] = {}
    global_checkpoint_counts: dict[str, int] = {}
    runner_secured_count = 0

    for symbol in symbol_order:
        symbol_frame = scoped.loc[scoped["symbol"] == symbol].copy().sort_values("__time_sort")
        if symbol_frame.empty:
            rows.append(
                {
                    "symbol": symbol,
                    "recent_row_count": 0,
                    "source_counts": "{}",
                    "surface_counts": "{}",
                    "checkpoint_type_counts": "{}",
                    "runner_secured_count": 0,
                    "open_profit_row_count": 0,
                    "open_loss_row_count": 0,
                    "latest_checkpoint_id": "",
                    "latest_surface_name": "",
                    "latest_time": "",
                    "recommended_focus": f"collect_more_{symbol.lower()}_checkpoint_context_rows",
                }
            )
            continue

        source_counts = symbol_frame["source"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().value_counts().to_dict()
        surface_counts = symbol_frame["surface_name"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().value_counts().to_dict()
        checkpoint_counts = symbol_frame["checkpoint_type"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().value_counts().to_dict()
        latest = symbol_frame.iloc[-1]
        runner_count = int(symbol_frame["runner_secured"].apply(_to_bool).sum())
        profit_rows = int((symbol_frame["unrealized_pnl_state"].fillna("").astype(str).str.upper() == "OPEN_PROFIT").sum())
        loss_rows = int((symbol_frame["unrealized_pnl_state"].fillna("").astype(str).str.upper() == "OPEN_LOSS").sum())
        focus = f"inspect_{symbol.lower()}_checkpoint_context_balance"
        if profit_rows <= 0 and loss_rows <= 0:
            focus = f"collect_more_{symbol.lower()}_live_position_rows"
        elif checkpoint_counts.get("RUNNER_CHECK", 0) <= 0:
            focus = f"inspect_{symbol.lower()}_runner_context_gap"
        elif surface_counts.get("protective_exit_surface", 0) <= 0:
            focus = f"inspect_{symbol.lower()}_protective_exit_context_gap"

        rows.append(
            {
                "symbol": symbol,
                "recent_row_count": int(len(symbol_frame)),
                "source_counts": _json_counts(source_counts),
                "surface_counts": _json_counts(surface_counts),
                "checkpoint_type_counts": _json_counts(checkpoint_counts),
                "runner_secured_count": runner_count,
                "open_profit_row_count": profit_rows,
                "open_loss_row_count": loss_rows,
                "latest_checkpoint_id": _to_text(latest.get("checkpoint_id")),
                "latest_surface_name": _to_text(latest.get("surface_name")),
                "latest_time": _to_text(latest.get("generated_at")),
                "recommended_focus": focus,
            }
        )

        runner_secured_count += runner_count
        for key, value in surface_counts.items():
            global_surface_counts[str(key)] = int(global_surface_counts.get(str(key), 0) + int(value))
        for key, value in checkpoint_counts.items():
            global_checkpoint_counts[str(key)] = int(global_checkpoint_counts.get(str(key), 0) + int(value))

    snapshot = pd.DataFrame(rows, columns=PATH_CHECKPOINT_CONTEXT_SNAPSHOT_COLUMNS)
    summary["runner_secured_count"] = int(runner_secured_count)
    summary["surface_counts"] = dict(global_surface_counts)
    summary["checkpoint_type_counts"] = dict(global_checkpoint_counts)
    summary["recommended_next_action"] = (
        "proceed_to_pa4_passive_score_calculation"
        if summary["market_family_row_count"] > 0 and runner_secured_count >= 1
        else "collect_more_live_checkpoint_context_rows_before_pa4"
    )
    return snapshot, summary
