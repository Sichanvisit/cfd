"""Replay/outcome bridge for barrier-state25 runtime rows."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence

from backend.services.barrier_state25_runtime_bridge import (
    BARRIER_SCOPE_FREEZE_CONTRACT_V1,
    build_barrier_state25_runtime_bridge_v1,
)
from backend.services.entry_wait_quality_replay_bridge import resolve_default_future_bar_path
from backend.services.storage_compaction import (
    resolve_entry_decision_detail_path,
    resolve_entry_decision_row_key,
)


BARRIER_OUTCOME_BRIDGE_VERSION = "barrier_outcome_bridge_v1"
BARRIER_OUTCOME_ROW_VERSION = "barrier_outcome_row_v1"
BARRIER_READINESS_GATE_VERSION = "barrier_readiness_gate_v1"
BARRIER_BIAS_BASELINE_VERSION = "barrier_bias_baseline_v1"
BARRIER_BIAS_RECOVERY_VERSION = "barrier_bias_recovery_v1"
CORRECT_WAIT_DIAGNOSTIC_VERSION = "correct_wait_diagnostic_v1"
CORRECT_WAIT_CASEBOOK_VERSION = "correct_wait_casebook_v1"
TIMING_EDGE_ABSENT_CASEBOOK_VERSION = "timing_edge_absent_casebook_v1"
WAIT_OUTCOME_VERSION = "wait_outcome_v1"
DEFAULT_OUTPUT_DIR = Path("data") / "analysis" / "barrier"
DEFAULT_RUNTIME_STATUS_PATH = Path("data") / "runtime_status.json"
MIN_BARRIER_READINESS_SEMANTIC_ANCHOR_ROWS = 200
MIN_BARRIER_READINESS_STRICT_ROWS = 40
MIN_BARRIER_READINESS_COVERED_SHARE_EX_PRE_CONTEXT = 0.75
MAX_BARRIER_READINESS_SEMANTIC_SKIP_SHARE_EX_PRE_CONTEXT = 0.05
MAX_BARRIER_READINESS_OVERBLOCK_RATIO = 0.10
MIN_BARRIER_READINESS_COUNTERFACTUAL_DELTA_R_MEAN = 0.10
MIN_BARRIER_READINESS_POSITIVE_ADVANTAGE = 0.10
MAX_BARRIER_READINESS_NEGATIVE_MISMATCH_RATE = 0.20
MAX_BARRIER_READINESS_HEARTBEAT_AGE_SECONDS = 600.0
DEFAULT_SHORT_HORIZON_BARS = 3
DEFAULT_MID_HORIZON_BARS = 6
DEFAULT_LONG_HORIZON_BARS = 12
BARRIER_STRICT_CONFIDENCE_TIERS = frozenset({"high", "medium"})
BARRIER_USABLE_CONFIDENCE_TIERS = frozenset({"weak_usable"})
BARRIER_SKIP_CONFIDENCE_TIERS = frozenset({"low_skip"})


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _as_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value or {})
    if isinstance(value, str):
        text = str(value or "").strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return dict(parsed or {}) if isinstance(parsed, Mapping) else {}
    return {}


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


def _row_time(row: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(row)
    # Prefer decision row time first so "latest rows" reflect recent runtime decisions
    # instead of older anchors with larger signal-bar timestamps.
    for key in ("time", "signal_bar_ts"):
        resolved = _to_epoch(mapped.get(key))
        if resolved is not None:
            return float(resolved)
    return 0.0


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader if isinstance(row, Mapping)]


def _load_json_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return _as_mapping(payload)


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


def _barrier_bridge_payload(row: Mapping[str, Any] | None) -> dict[str, Any]:
    mapped = _as_mapping(row)
    existing = _as_mapping(mapped.get("barrier_state25_runtime_bridge_v1"))
    if existing:
        return existing
    return build_barrier_state25_runtime_bridge_v1(mapped)


def _barrier_summary(row: Mapping[str, Any] | None) -> dict[str, Any]:
    return _as_mapping(_barrier_bridge_payload(row).get("barrier_runtime_summary_v1"))


def _barrier_input_trace(row: Mapping[str, Any] | None) -> dict[str, Any]:
    return _as_mapping(_barrier_bridge_payload(row).get("barrier_input_trace_v1"))


def _row_has_bridge_candidate(row: Mapping[str, Any] | None) -> bool:
    mapped = _as_mapping(row)
    if _as_mapping(mapped.get("barrier_state25_runtime_bridge_v1")):
        return True
    blocked_by = _to_str(mapped.get("blocked_by", "")).lower()
    if blocked_by in {"max_positions_reached", "entry_cooldown"}:
        return True
    return bool(_as_mapping(mapped.get("barrier_state_v1")))


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


def _latest_future_bar_ts_index(
    future_bar_index: Mapping[str, Sequence[Mapping[str, Any]]] | None,
) -> dict[str, float]:
    latest_index: dict[str, float] = {}
    for symbol, rows in (future_bar_index or {}).items():
        symbol_u = _to_str(symbol, "").upper()
        symbol_rows = list(rows or [])
        if not symbol_u or not symbol_rows:
            continue
        latest_index[symbol_u] = max(_to_float(_as_mapping(row).get("time"), 0.0) for row in symbol_rows)
    return latest_index


def _decision_row_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for raw_row in rows:
        row = _as_mapping(raw_row)
        symbol = _to_str(row.get("symbol", "")).upper()
        if symbol:
            index.setdefault(symbol, []).append(row)
    for symbol, symbol_rows in index.items():
        index[symbol] = sorted(symbol_rows, key=_row_time)
    return index


def _candidate_future_bars(
    decision_row: Mapping[str, Any] | None,
    *,
    future_bar_index: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    max_bars: int = DEFAULT_LONG_HORIZON_BARS,
) -> list[dict[str, Any]]:
    if not future_bar_index:
        return []
    decision = _as_mapping(decision_row)
    symbol = _to_str(decision.get("symbol", "")).upper()
    symbol_rows = list((future_bar_index or {}).get(symbol, []) or [])
    if not symbol_rows:
        return []
    anchor_ts = _row_time(decision)
    selected: list[dict[str, Any]] = []
    for row in symbol_rows:
        bar_ts = _to_float(row.get("time"), 0.0)
        if anchor_ts > 0 and bar_ts <= anchor_ts:
            continue
        selected.append(dict(row))
        if len(selected) >= max_bars:
            break
    return selected


def _subsequent_decision_rows(
    row: Mapping[str, Any] | None,
    *,
    decision_row_index: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    horizon_end_ts: float,
) -> list[dict[str, Any]]:
    if not decision_row_index:
        return []
    anchor = _as_mapping(row)
    symbol = _to_str(anchor.get("symbol", "")).upper()
    symbol_rows = list((decision_row_index or {}).get(symbol, []) or [])
    if not symbol_rows:
        return []
    anchor_ts = _row_time(anchor)
    selected: list[dict[str, Any]] = []
    for candidate in symbol_rows:
        candidate_ts = _row_time(candidate)
        if candidate_ts <= anchor_ts:
            continue
        if horizon_end_ts > 0 and candidate_ts > horizon_end_ts:
            continue
        selected.append(dict(candidate))
    return selected


def _closed_trade_index(rows: Sequence[Mapping[str, Any]] | None) -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    for raw_row in rows or []:
        row = _as_mapping(raw_row)
        ticket = _to_int(row.get("ticket", row.get("position_id", 0)), 0)
        if ticket > 0 and ticket not in index:
            index[ticket] = row
    return index


def _matched_closed_trade_row(
    row: Mapping[str, Any] | None,
    *,
    closed_trade_index: Mapping[int, Mapping[str, Any]] | None,
) -> dict[str, Any]:
    mapped = _as_mapping(row)
    ticket = _to_int(mapped.get("ticket", mapped.get("position_id", 0)), 0)
    if ticket > 0 and isinstance(closed_trade_index, Mapping):
        return _as_mapping(closed_trade_index.get(ticket))
    return {}


def _active_side(summary: Mapping[str, Any]) -> str:
    side = _to_str(summary.get("acting_side", "")).upper()
    return side if side in {"BUY", "SELL"} else ""


def _reference_price(row: Mapping[str, Any], future_bars: Sequence[Mapping[str, Any]]) -> float:
    for key in ("entry_fill_price", "open_price", "entry_request_price", "close_price"):
        value = _to_float(row.get(key), 0.0)
        if value > 0:
            return value
    first_bar = _as_mapping(future_bars[0]) if future_bars else {}
    for key in ("open", "close", "high", "low"):
        value = _to_float(first_bar.get(key), 0.0)
        if value > 0:
            return value
    return 0.0


def _symbol_range_floor(symbol: str, anchor_price: float) -> float:
    symbol_u = str(symbol or "").upper()
    if symbol_u == "BTCUSD":
        return 5.0
    if symbol_u == "XAUUSD":
        return 0.8
    if symbol_u == "NAS100":
        return 8.0
    return max(0.05, abs(float(anchor_price or 0.0)) * 0.0005)


def _reference_unit(row: Mapping[str, Any], future_bars: Sequence[Mapping[str, Any]], anchor_price: float) -> float:
    for key in ("expected_adverse_depth", "forecast_expected_adverse_depth"):
        value = _to_float(row.get(key), 0.0)
        if value > 0:
            return value
    first_bar = _as_mapping(future_bars[0]) if future_bars else {}
    signal_bar_range = max(
        0.0,
        _to_float(first_bar.get("high"), 0.0) - _to_float(first_bar.get("low"), 0.0),
    )
    if signal_bar_range > 0:
        return signal_bar_range
    return _symbol_range_floor(_to_str(row.get("symbol", "")), anchor_price)


def _favorable_and_adverse_move(side: str, anchor_price: float, bars: Sequence[Mapping[str, Any]]) -> tuple[float, float]:
    highs = [_to_float(_as_mapping(bar).get("high"), anchor_price) for bar in bars]
    lows = [_to_float(_as_mapping(bar).get("low"), anchor_price) for bar in bars]
    max_high = max(highs or [anchor_price])
    min_low = min(lows or [anchor_price])
    if str(side).upper() == "BUY":
        favorable = max(0.0, max_high - anchor_price)
        adverse = max(0.0, anchor_price - min_low)
    else:
        favorable = max(0.0, anchor_price - min_low)
        adverse = max(0.0, max_high - anchor_price)
    return favorable, adverse


def _bars_after_time(bars: Sequence[Mapping[str, Any]], *, start_ts: float, end_ts: float) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for raw_bar in bars:
        bar = _as_mapping(raw_bar)
        bar_ts = _to_float(bar.get("time"), 0.0)
        if bar_ts <= start_ts:
            continue
        if end_ts > 0 and bar_ts > end_ts:
            break
        selected.append(bar)
    return selected


def _same_thesis_relief_row(
    rows: Sequence[Mapping[str, Any]],
    *,
    anchor_side: str,
) -> dict[str, Any]:
    for raw_row in rows:
        row = _as_mapping(raw_row)
        action = _to_str(row.get("action", row.get("direction", ""))).upper()
        if action != anchor_side:
            continue
        outcome = _to_str(row.get("outcome", "")).lower()
        summary = _barrier_summary(row)
        if outcome == "entered":
            return row
        if _to_str(summary.get("anchor_context", "")).lower() == "relief_release":
            return row
        if _to_float(summary.get("relief_score"), 0.0) >= 0.20:
            return row
    return {}


def _better_entry_gain_r(
    *,
    anchor_side: str,
    anchor_price: float,
    relief_row: Mapping[str, Any] | None,
    relief_bars: Sequence[Mapping[str, Any]],
    reference_unit: float,
) -> float:
    if reference_unit <= 0:
        return 0.0
    relief = _as_mapping(relief_row)
    if not relief:
        return 0.0
    relief_price = _reference_price(relief, relief_bars)
    if relief_price <= 0:
        return 0.0
    if str(anchor_side).upper() == "BUY":
        gain = max(0.0, anchor_price - relief_price)
    else:
        gain = max(0.0, relief_price - anchor_price)
    return round(float(gain / max(reference_unit, 1e-9)), 6)


def _continuation_after_relief_r(
    *,
    anchor_side: str,
    relief_row: Mapping[str, Any] | None,
    all_future_bars: Sequence[Mapping[str, Any]],
    horizon_end_ts: float,
    reference_unit: float,
) -> tuple[float, float]:
    relief = _as_mapping(relief_row)
    if not relief or reference_unit <= 0:
        return 0.0, 0.0
    relief_ts = _row_time(relief)
    relief_bars = _bars_after_time(all_future_bars, start_ts=relief_ts, end_ts=horizon_end_ts)
    if not relief_bars:
        return 0.0, 0.0
    relief_anchor_price = _reference_price(relief, relief_bars)
    if relief_anchor_price <= 0:
        return 0.0, 0.0
    favorable_move, adverse_move = _favorable_and_adverse_move(anchor_side, relief_anchor_price, relief_bars)
    return (
        round(float(favorable_move / max(reference_unit, 1e-9)), 6),
        round(float(adverse_move / max(reference_unit, 1e-9)), 6),
    )


def _score_map(
    *,
    cf_f_6: float,
    cf_a_3: float,
    cf_a_6: float,
    better_entry_gain_6: float,
    barrier_total: float,
    release_f_6: float,
    release_a_6: float,
) -> dict[str, float]:
    score_missed_profit = float(cf_f_6 - cf_a_6)
    return {
        "avoided_loss": float(cf_a_6 - cf_f_6),
        "correct_wait": float(better_entry_gain_6 + min(cf_a_3, 0.75) - max(0.0, cf_a_6 - cf_a_3)),
        "missed_profit": score_missed_profit,
        "overblock": float(score_missed_profit + max(0.0, barrier_total - 0.65)),
        "relief_success": float(release_f_6 - release_a_6),
        "relief_failure": float(release_a_6 - release_f_6),
    }


def _bias_recovery_surface_v1(
    *,
    anchor_context: str,
    blocking_bias: str,
    barrier_total: float,
    barrier_recommended_family: str,
    effective_wait_block: bool,
    cf_f_6: float,
    cf_a_6: float,
    better_entry_gain_6: float,
    later_favorable_continuation_r: float,
    loss_avoided_r: float,
    profit_missed_r: float,
    wait_value_r: float,
    release_f_6: float,
    release_a_6: float,
) -> dict[str, Any]:
    anchor_context_text = _to_str(anchor_context, "").lower()
    blocking_bias_text = _to_str(blocking_bias, "").upper()
    recommended_text = _to_str(barrier_recommended_family, "").lower()
    light_observe_context = (
        anchor_context_text == "wait_block"
        and blocking_bias_text == "LIGHT_BLOCK"
        and recommended_text == "observe_only"
    )
    missed_profit_margin_r = max(
        0.0,
        float(profit_missed_r) - max(float(loss_avoided_r) + 0.15, float(wait_value_r) + 0.05),
    )
    overblock_margin_r = max(
        0.0,
        float(profit_missed_r) + max(0.0, float(barrier_total) - 0.65) - max(float(loss_avoided_r), float(wait_value_r) + 0.10),
    )
    correct_wait_margin_r = max(
        0.0,
        float(better_entry_gain_6) + float(later_favorable_continuation_r) - max(float(loss_avoided_r) - 0.10, float(profit_missed_r) - 0.10),
    )
    relief_success_margin_r = max(0.0, float(release_f_6) - float(release_a_6) - 0.10)
    relief_failure_margin_r = max(0.0, float(release_a_6) - float(release_f_6) - 0.10)

    missed_profit_strict_candidate = bool(
        (effective_wait_block or light_observe_context)
        and float(cf_f_6) >= 1.00
        and float(cf_a_6) <= 0.55
        and missed_profit_margin_r >= 0.20
    )
    missed_profit_weak_candidate = bool(
        (effective_wait_block or light_observe_context)
        and float(cf_f_6) >= 0.75
        and float(cf_a_6) <= 0.85
        and missed_profit_margin_r >= 0.10
    )
    overblock_boundary_candidate = bool(
        effective_wait_block
        and float(barrier_total) >= 0.65
        and float(cf_f_6) >= 1.00
        and float(cf_a_6) <= 0.45
        and overblock_margin_r >= 0.15
    )
    correct_wait_timing_candidate = bool(
        effective_wait_block
        and float(better_entry_gain_6) >= 0.20
        and float(later_favorable_continuation_r) >= 0.25
        and correct_wait_margin_r >= 0.10
    )
    correct_wait_wait_value_candidate = bool(
        effective_wait_block
        and float(wait_value_r) >= 0.45
        and float(later_favorable_continuation_r) >= 0.40
        and float(loss_avoided_r) <= float(wait_value_r) + 0.55
        and float(profit_missed_r) <= float(wait_value_r) + 0.20
    )
    relief_success_weak_candidate = bool(
        anchor_context_text == "relief_release"
        and recommended_text in {"relief_release_bias", "observe_only"}
        and float(release_f_6) >= 0.55
        and float(release_a_6) <= 0.75
        and relief_success_margin_r >= 0.05
    )
    relief_failure_weak_candidate = bool(
        anchor_context_text == "relief_release"
        and float(release_a_6) >= 0.65
        and (
            (float(release_f_6) <= 0.60 and relief_failure_margin_r >= 0.05)
            or (float(release_a_6) >= 1.20 and float(release_a_6) >= float(release_f_6) + 1.00)
        )
    )

    candidate_pool: list[tuple[str, str, float]] = []
    if overblock_boundary_candidate:
        candidate_pool.append(("overblock", "soft_overblock_boundary_recovery", float(overblock_margin_r)))
    if missed_profit_strict_candidate:
        candidate_pool.append(("missed_profit", "soft_missed_profit_strict_recovery", float(missed_profit_margin_r) + 0.10))
    elif missed_profit_weak_candidate:
        candidate_pool.append(("missed_profit", "soft_missed_profit_weak_recovery", float(missed_profit_margin_r)))
    if correct_wait_timing_candidate:
        candidate_pool.append(("correct_wait", "soft_correct_wait_timing_recovery", float(correct_wait_margin_r)))
    elif correct_wait_wait_value_candidate:
        candidate_pool.append(("correct_wait", "soft_correct_wait_wait_value_recovery", float(wait_value_r)))
    if relief_success_weak_candidate:
        candidate_pool.append(("relief_success", "soft_relief_success_recovery", float(relief_success_margin_r)))
    if relief_failure_weak_candidate:
        candidate_pool.append(("relief_failure", "soft_relief_failure_recovery", float(relief_failure_margin_r)))

    priority = {
        "relief_failure": 0,
        "relief_success": 1,
        "overblock": 2,
        "missed_profit": 3,
        "correct_wait": 4,
    }
    candidate_pool.sort(
        key=lambda item: (
            -float(item[2]),
            int(priority.get(_to_str(item[0], "").lower(), 99)),
            _to_str(item[0], ""),
        )
    )
    primary_label = candidate_pool[0][0] if candidate_pool else ""
    primary_reason = candidate_pool[0][1] if candidate_pool else ""

    return {
        "contract_version": BARRIER_BIAS_RECOVERY_VERSION,
        "missed_profit_strict_candidate": bool(missed_profit_strict_candidate),
        "missed_profit_weak_candidate": bool(missed_profit_weak_candidate),
        "overblock_boundary_candidate": bool(overblock_boundary_candidate),
        "correct_wait_timing_candidate": bool(correct_wait_timing_candidate),
        "correct_wait_wait_value_candidate": bool(correct_wait_wait_value_candidate),
        "relief_success_weak_candidate": bool(relief_success_weak_candidate),
        "relief_failure_weak_candidate": bool(relief_failure_weak_candidate),
        "missed_profit_margin_r": round(float(missed_profit_margin_r), 6),
        "overblock_margin_r": round(float(overblock_margin_r), 6),
        "correct_wait_margin_r": round(float(correct_wait_margin_r), 6),
        "relief_success_margin_r": round(float(relief_success_margin_r), 6),
        "relief_failure_margin_r": round(float(relief_failure_margin_r), 6),
        "primary_candidate_label": _to_str(primary_label, "").lower(),
        "primary_candidate_reason": _to_str(primary_reason, "").lower(),
    }


def _soft_bias_recovery_label_candidate(
    *,
    bias_recovery: Mapping[str, Any] | None,
) -> tuple[str, str]:
    mapped = _as_mapping(bias_recovery)
    return (
        _to_str(mapped.get("primary_candidate_label", ""), "").lower(),
        _to_str(mapped.get("primary_candidate_reason", ""), "").lower(),
    )


def _correct_wait_diagnostic_v1(
    *,
    anchor_context: str,
    barrier_recommended_family: str,
    effective_wait_block: bool,
    resolved_label: str,
    weak_candidate_reason: str,
    cf_a_3: float,
    cf_f_6: float,
    better_entry_gain_6: float,
    later_favorable_continuation_r: float,
    loss_avoided_r: float,
    profit_missed_r: float,
    wait_value_r: float,
    bias_recovery: Mapping[str, Any] | None,
) -> dict[str, Any]:
    mapped = _as_mapping(bias_recovery)
    anchor_context_text = _to_str(anchor_context, "").lower()
    recommended_text = _to_str(barrier_recommended_family, "").lower()
    label_text = _to_str(resolved_label, "").lower()
    weak_reason = _to_str(weak_candidate_reason, "").lower()

    candidate_scope_row = bool(
        anchor_context_text == "wait_block"
        and recommended_text in {"wait_bias", "block_bias"}
    )
    strong_entry_gain = bool(float(better_entry_gain_6) >= 0.20)
    continuation_support = bool(float(later_favorable_continuation_r) >= 0.25)
    wait_value_support = bool(float(wait_value_r) >= 0.45)
    adverse_context_support = bool(float(cf_a_3) >= 0.35 or float(loss_avoided_r) >= 1.00)
    loss_balance_support = bool(float(loss_avoided_r) <= float(wait_value_r) + 0.55)
    profit_balance_support = bool(float(profit_missed_r) <= float(wait_value_r) + 0.20)
    timing_candidate = bool(mapped.get("correct_wait_timing_candidate", False))
    wait_value_candidate = bool(mapped.get("correct_wait_wait_value_candidate", False))
    labeled_correct_wait = bool(label_text == "correct_wait")

    blocking_reason = ""
    if not candidate_scope_row:
        blocking_reason = "non_wait_block_scope"
    elif not effective_wait_block:
        blocking_reason = "effective_wait_block_missing"
    elif labeled_correct_wait:
        blocking_reason = "resolved_correct_wait"
    elif timing_candidate or wait_value_candidate or weak_reason.startswith("soft_correct_wait_"):
        blocking_reason = "correct_wait_candidate_recovered"
    elif not strong_entry_gain and not wait_value_support:
        blocking_reason = "timing_edge_absent"
    elif not continuation_support:
        blocking_reason = "continuation_support_absent"
    elif not adverse_context_support:
        blocking_reason = "adverse_context_weak"
    elif not loss_balance_support:
        blocking_reason = "loss_avoided_dominates"
    elif not profit_balance_support:
        blocking_reason = "profit_missed_dominates"
    elif label_text and label_text != "correct_wait":
        blocking_reason = f"competing_label:{label_text}"
    else:
        blocking_reason = "correct_wait_unresolved"

    return {
        "contract_version": CORRECT_WAIT_DIAGNOSTIC_VERSION,
        "candidate_scope_row": candidate_scope_row,
        "effective_wait_block": bool(effective_wait_block),
        "strong_entry_gain": strong_entry_gain,
        "continuation_support": continuation_support,
        "wait_value_support": wait_value_support,
        "adverse_context_support": adverse_context_support,
        "loss_balance_support": loss_balance_support,
        "profit_balance_support": profit_balance_support,
        "timing_candidate": timing_candidate,
        "wait_value_candidate": wait_value_candidate,
        "labeled_correct_wait": labeled_correct_wait,
        "blocking_reason": blocking_reason,
        "better_entry_gain_6": round(float(better_entry_gain_6), 6),
        "later_continuation_f_6": round(float(later_favorable_continuation_r), 6),
        "wait_value_r": round(float(wait_value_r), 6),
        "loss_avoided_r": round(float(loss_avoided_r), 6),
        "profit_missed_r": round(float(profit_missed_r), 6),
    }


def _actual_engine_action_family(row: Mapping[str, Any] | None) -> str:
    mapped = _as_mapping(row)
    outcome = _to_str(mapped.get("outcome", "")).lower()
    action = _to_str(mapped.get("action", "")).upper()
    blocked_by = _to_str(mapped.get("blocked_by", "")).lower()
    observe_reason = _to_str(mapped.get("observe_reason", "")).lower()
    if outcome == "entered":
        return "enter"
    if outcome in {"wait", "skipped"}:
        if blocked_by or action in {"BUY", "SELL"} or observe_reason:
            return "wait_or_block"
    return "observe_only"


def _preferred_action_family(recommended_family: str) -> str:
    family = _to_str(recommended_family, "").lower()
    if family in {"block_bias", "wait_bias", "relief_watch"}:
        return "wait"
    if family == "relief_release_bias":
        return "enter"
    return "observe_only"


def _recommended_action_family(recommended_family: str) -> str:
    preferred_action = _preferred_action_family(recommended_family)
    if preferred_action == "wait":
        return "wait_or_block"
    if preferred_action == "enter":
        return "enter"
    return "observe_only"


def _normalized_recommended_detail_family_v2(
    *,
    recommended_family: str,
    anchor_context: str,
    blocking_bias: str,
    barrier_total: float,
    dominant_cost_family: str,
    cost_balance_margin_r: float,
    relief_score: float,
) -> str:
    family = _to_str(recommended_family, "").lower()
    anchor_context_text = _to_str(anchor_context, "").lower()
    blocking_bias_text = _to_str(blocking_bias, "").upper()
    dominant_cost_text = _to_str(dominant_cost_family, "").lower()

    if family == "block_bias":
        return "block_bias_hard" if float(barrier_total) >= 0.60 or blocking_bias_text == "HARD_BLOCK" else "block_bias_soft"
    if family == "wait_bias":
        return "wait_bias"
    if family == "relief_watch":
        return "relief_watch"
    if family == "relief_release_bias":
        return "relief_release_bias"
    if family != "observe_only":
        return family or "observe_only_soft"

    if anchor_context_text == "wait_block" and blocking_bias_text == "LIGHT_BLOCK":
        if dominant_cost_text == "loss_avoided" and float(cost_balance_margin_r) >= 0.60:
            return "block_bias_soft"
        if dominant_cost_text in {"profit_missed", "wait_value"} or float(cost_balance_margin_r) < 0.60:
            return "wait_bias_soft"
    if anchor_context_text == "wait_block" and blocking_bias_text == "RELIEF_READY" and float(relief_score) >= 0.15:
        return "relief_watch_soft"
    return "observe_only_soft"


def _normalized_recommended_action_family_v2(
    *,
    recommended_family: str,
    anchor_context: str,
    blocking_bias: str,
    barrier_total: float,
    dominant_cost_family: str,
    cost_balance_margin_r: float,
    relief_score: float,
) -> str:
    detail_family = _normalized_recommended_detail_family_v2(
        recommended_family=recommended_family,
        anchor_context=anchor_context,
        blocking_bias=blocking_bias,
        barrier_total=barrier_total,
        dominant_cost_family=dominant_cost_family,
        cost_balance_margin_r=cost_balance_margin_r,
        relief_score=relief_score,
    )
    if detail_family in {"block_bias_hard", "block_bias_soft", "wait_bias", "wait_bias_soft", "relief_watch", "relief_watch_soft"}:
        return "wait_or_block"
    if detail_family == "relief_release_bias":
        return "enter"
    return "observe_only"


def _drift_cost_direction(counterfactual_cost_delta_r: float) -> str:
    if float(counterfactual_cost_delta_r) > 0:
        return "positive"
    if float(counterfactual_cost_delta_r) < 0:
        return "negative"
    return "neutral"


def _drift_status(
    *,
    actual_engine_action_family: str,
    barrier_recommended_family: str,
) -> str:
    actual_family = _to_str(actual_engine_action_family, "").lower() or "unknown"
    target_family = _recommended_action_family(barrier_recommended_family)
    if actual_family == "unknown":
        return "unknown"
    return "aligned" if actual_family == target_family else "mismatch"


def _drift_status_v2(
    *,
    actual_engine_action_family: str,
    normalized_recommended_action_family_v2: str,
) -> str:
    actual_family = _to_str(actual_engine_action_family, "").lower() or "unknown"
    target_family = _to_str(normalized_recommended_action_family_v2, "").lower() or "unknown"
    if actual_family == "unknown":
        return "unknown"
    return "aligned" if actual_family == target_family else "mismatch"


def _counterfactual_cost_delta_r(
    *,
    label: str,
    loss_avoided_r: float,
    profit_missed_r: float,
    wait_value_r: float,
    release_f_6: float,
    release_a_6: float,
) -> float:
    label_text = _to_str(label, "").lower()
    if label_text == "avoided_loss":
        return float(max(0.0, loss_avoided_r))
    if label_text == "correct_wait":
        return float(max(0.0, wait_value_r))
    if label_text == "missed_profit":
        return float(-max(0.0, profit_missed_r))
    if label_text == "overblock":
        return float(-max(0.0, max(profit_missed_r, wait_value_r)))
    if label_text == "relief_success":
        return float(max(0.0, release_f_6 - release_a_6))
    if label_text == "relief_failure":
        return float(-max(0.0, release_a_6 - release_f_6))
    return 0.0


def _counterfactual_outcome_family(
    *,
    actual_engine_action_family: str,
    barrier_recommended_family: str,
    barrier_outcome_label: str,
    skip_reason: str,
) -> str:
    recommended_family = _to_str(barrier_recommended_family, "").lower()
    label = _to_str(barrier_outcome_label, "").lower()
    preferred_action = _preferred_action_family(recommended_family)
    actual_family = _to_str(actual_engine_action_family, "").lower()
    if not recommended_family or recommended_family == "observe_only":
        return "observe_only"
    if not label:
        return "insufficient_evidence" if _to_str(skip_reason, "") else "no_label_match"

    if preferred_action == "wait":
        if actual_family == "enter":
            if label in {"avoided_loss", "correct_wait"}:
                return "counterfactual_wait_better"
            if label in {"missed_profit", "overblock"}:
                return "actual_enter_better"
        if actual_family == "wait_or_block":
            if label in {"avoided_loss", "correct_wait"}:
                return "aligned_wait_gain"
            if label in {"missed_profit", "overblock"}:
                return "aligned_wait_cost"
        return "observe_wait_pending"

    if preferred_action == "enter":
        if actual_family == "enter":
            if label == "relief_success":
                return "aligned_release_gain"
            if label == "relief_failure":
                return "aligned_release_cost"
            return "aligned_release_mixed"
        if label in {"relief_success", "missed_profit", "overblock"}:
            return "counterfactual_release_better"
        if label in {"relief_failure", "avoided_loss", "correct_wait"}:
            return "actual_wait_better"
        return "release_pending"

    return "observe_only"


def _counterfactual_reason_summary(
    *,
    actual_engine_action_family: str,
    barrier_recommended_family: str,
    barrier_outcome_label: str,
    counterfactual_outcome_family: str,
    counterfactual_cost_delta_r: float,
    skip_reason: str,
) -> str:
    basis = _to_str(barrier_outcome_label, "") or _to_str(skip_reason, "") or "no_label_match"
    sign = "positive" if float(counterfactual_cost_delta_r) > 0 else ("negative" if float(counterfactual_cost_delta_r) < 0 else "neutral")
    return "|".join(
        token
        for token in (
            _to_str(actual_engine_action_family, "").lower(),
            _to_str(barrier_recommended_family, "").lower(),
            _to_str(counterfactual_outcome_family, "").lower(),
            basis.lower(),
            sign,
        )
        if token
    )


def _cost_balance_profile(
    *,
    cf_f_6: float,
    cf_a_6: float,
    better_entry_gain_6: float,
    later_favorable_continuation_r: float,
) -> dict[str, float | str]:
    loss_avoided_r = max(0.0, float(cf_a_6))
    profit_missed_r = max(0.0, float(cf_f_6) - float(better_entry_gain_6))
    wait_value_r = max(0.0, float(better_entry_gain_6) + float(later_favorable_continuation_r))
    ranked = sorted(
        (
            ("loss_avoided", loss_avoided_r),
            ("profit_missed", profit_missed_r),
            ("wait_value", wait_value_r),
        ),
        key=lambda item: (-float(item[1]), str(item[0])),
    )
    dominant_name, dominant_value = ranked[0]
    second_name, second_value = ranked[1]
    return {
        "loss_avoided_r": round(float(loss_avoided_r), 6),
        "profit_missed_r": round(float(profit_missed_r), 6),
        "wait_value_r": round(float(wait_value_r), 6),
        "dominant_cost_family": dominant_name,
        "dominant_cost_value_r": round(float(dominant_value), 6),
        "secondary_cost_family": second_name,
        "secondary_cost_value_r": round(float(second_value), 6),
        "cost_balance_margin_r": round(float(dominant_value - second_value), 6),
    }


def _soft_wait_block_label_candidate(
    *,
    anchor_context: str,
    effective_wait_block: bool,
    barrier_total: float,
    barrier_recommended_family: str,
    coverage_ratio: float,
    loss_avoided_r: float,
    profit_missed_r: float,
    wait_value_r: float,
    better_entry_gain_6: float,
) -> tuple[str, str]:
    anchor_context_text = _to_str(anchor_context, "").lower()
    recommended_text = _to_str(barrier_recommended_family, "").lower()
    if anchor_context_text != "wait_block" or not effective_wait_block:
        return "", ""
    if coverage_ratio < 0.90:
        return "", ""
    if recommended_text not in {"wait_bias", "block_bias"}:
        return "", ""
    if (
        loss_avoided_r >= 1.20
        and loss_avoided_r >= profit_missed_r + 0.80
        and loss_avoided_r >= wait_value_r + 0.80
    ):
        return "avoided_loss", "soft_cost_balance_loss_bias"
    if (
        recommended_text == "wait_bias"
        and wait_value_r >= 0.60
        and better_entry_gain_6 >= 0.20
        and wait_value_r >= profit_missed_r + 0.15
    ):
        return "correct_wait", "soft_wait_value_bias"
    if (
        profit_missed_r >= 1.10
        and profit_missed_r >= loss_avoided_r + 0.80
        and profit_missed_r >= wait_value_r + 0.40
    ):
        return ("overblock" if barrier_total >= 0.65 else "missed_profit"), "soft_cost_balance_profit_bias"
    return "", ""


def _effective_wait_block(
    *,
    anchor_context: str,
    barrier_blocked_flag: bool,
    blocking_bias: str,
    barrier_recommended_family: str,
    actual_engine_action_family: str,
) -> bool:
    if barrier_blocked_flag:
        return True
    return (
        _to_str(anchor_context, "").lower() == "wait_block"
        and _to_str(blocking_bias, "").upper() in {"WAIT_BLOCK", "HARD_BLOCK"}
        and _to_str(barrier_recommended_family, "").lower() in {"wait_bias", "block_bias"}
        and _to_str(actual_engine_action_family, "").lower() == "wait_or_block"
    )


def _soft_light_block_label_candidate(
    *,
    anchor_context: str,
    barrier_blocked_flag: bool,
    blocking_bias: str,
    barrier_total: float,
    barrier_recommended_family: str,
    coverage_ratio: float,
    dominant_cost_family: str,
    cost_balance_margin_r: float,
    loss_avoided_r: float,
    profit_missed_r: float,
    wait_value_r: float,
) -> tuple[str, str]:
    anchor_context_text = _to_str(anchor_context, "").lower()
    blocking_bias_text = _to_str(blocking_bias, "").upper()
    recommended_text = _to_str(barrier_recommended_family, "").lower()
    dominant_text = _to_str(dominant_cost_family, "").lower()
    if anchor_context_text != "wait_block" or barrier_blocked_flag:
        return "", ""
    if blocking_bias_text != "LIGHT_BLOCK" or recommended_text != "observe_only":
        return "", ""
    if coverage_ratio < 0.90 or barrier_total > 0.35:
        return "", ""
    if (
        dominant_text == "loss_avoided"
        and loss_avoided_r >= 1.40
        and cost_balance_margin_r >= 1.00
        and loss_avoided_r >= profit_missed_r + 0.80
        and loss_avoided_r >= wait_value_r + 0.80
    ):
        return "avoided_loss", "soft_light_block_loss_bias"
    if (
        dominant_text == "profit_missed"
        and profit_missed_r >= 3.00
        and cost_balance_margin_r >= 2.00
        and profit_missed_r >= loss_avoided_r + 2.00
        and profit_missed_r >= wait_value_r + 2.00
    ):
        return "missed_profit", "soft_light_block_profit_bias"
    return "", ""


def _soft_relief_watch_label_candidate(
    *,
    anchor_context: str,
    barrier_recommended_family: str,
    blocking_bias: str,
    coverage_ratio: float,
    dominant_cost_family: str,
    cost_balance_margin_r: float,
    loss_avoided_r: float,
    profit_missed_r: float,
    wait_value_r: float,
) -> tuple[str, str]:
    if _to_str(anchor_context, "").lower() != "wait_block":
        return "", ""
    if _to_str(barrier_recommended_family, "").lower() != "relief_watch":
        return "", ""
    if _to_str(blocking_bias, "").upper() not in {"RELIEF_READY", "LIGHT_BLOCK"}:
        return "", ""
    if coverage_ratio < 0.90:
        return "", ""
    if (
        _to_str(dominant_cost_family, "").lower() == "loss_avoided"
        and loss_avoided_r >= 1.80
        and cost_balance_margin_r >= 1.50
        and profit_missed_r <= 0.25
        and wait_value_r <= 0.25
    ):
        return "avoided_loss", "soft_relief_watch_loss_bias"
    return "", ""


def _soft_relief_release_label_candidate(
    *,
    anchor_context: str,
    coverage_ratio: float,
    release_f_6: float,
    release_a_6: float,
    dominant_cost_family: str,
    cost_balance_margin_r: float,
) -> tuple[str, str]:
    if _to_str(anchor_context, "").lower() != "relief_release":
        return "", ""
    if coverage_ratio < 0.90:
        return "", ""
    if (
        _to_str(dominant_cost_family, "").lower() == "loss_avoided"
        and release_a_6 >= 1.50
        and cost_balance_margin_r >= 1.50
        and release_f_6 <= 0.65
    ):
        return "relief_failure", "soft_relief_release_loss_bias"
    return "", ""


def _label_confidence(
    *,
    label: str,
    coverage_ratio: float,
    score_gap: float,
    cf_f_6: float,
    cf_a_3: float,
    cf_a_6: float,
    better_entry_gain_6: float,
    barrier_total: float,
    release_f_6: float,
    release_a_6: float,
) -> str:
    if not label:
        return "low_skip"
    if coverage_ratio < 0.50:
        return "low_skip"
    if coverage_ratio < 0.70:
        return "weak_usable"
    if label == "avoided_loss" and coverage_ratio >= 0.90 and cf_a_3 >= 0.80 and cf_f_6 < 0.30 and score_gap >= 0.15:
        return "high"
    if label == "correct_wait" and coverage_ratio >= 0.90 and better_entry_gain_6 >= 0.50 and score_gap >= 0.15:
        return "high"
    if label == "missed_profit" and coverage_ratio >= 0.90 and cf_f_6 >= 1.25 and cf_a_6 <= 0.35 and score_gap >= 0.15:
        return "high"
    if label == "overblock" and coverage_ratio >= 0.90 and barrier_total >= 0.75 and cf_f_6 >= 1.50 and score_gap >= 0.15:
        return "high"
    if label == "relief_success" and coverage_ratio >= 0.90 and release_f_6 >= 1.00 and release_a_6 <= 0.40 and score_gap >= 0.15:
        return "high"
    if label == "relief_failure" and coverage_ratio >= 0.90 and release_a_6 >= 1.00 and release_f_6 < 0.30 and score_gap >= 0.15:
        return "high"
    if score_gap < 0.08:
        return "weak_usable"
    return "medium"


def _evaluate_barrier_outcome_v1(
    row: Mapping[str, Any],
    *,
    future_bars: Sequence[Mapping[str, Any]],
    subsequent_rows: Sequence[Mapping[str, Any]],
    symbol_latest_future_ts: float = 0.0,
) -> dict[str, Any]:
    bridge = _barrier_bridge_payload(row)
    summary = _as_mapping(bridge.get("barrier_runtime_summary_v1"))
    input_trace = _as_mapping(bridge.get("barrier_input_trace_v1"))
    action_hint = _as_mapping(bridge.get("barrier_action_hint_v1"))
    acting_side = _active_side(summary)
    anchor_context = _to_str(summary.get("anchor_context", "")).lower()
    if not summary.get("available", False) or acting_side not in {"BUY", "SELL"}:
        summary_skip_reason = _summary_skip_reason(summary, acting_side, row)
        return {
            "contract_version": BARRIER_OUTCOME_ROW_VERSION,
            "bridge_quality_status": "skip",
            "barrier_outcome_label": "",
            "barrier_label_confidence": "low_skip",
            "barrier_outcome_reason": summary_skip_reason or "barrier_runtime_unavailable",
            "skip_reason": summary_skip_reason or "barrier_runtime_unavailable",
            "barrier_trace_stage": _to_str(summary.get("availability_stage", "")).lower(),
            "barrier_trace_reason": _to_str(summary.get("availability_reason", "")).lower(),
            **_empty_wait_outcome_v1(),
        }

    anchor_price = _reference_price(row, future_bars)
    reference_unit = _reference_unit(row, future_bars, anchor_price)
    anchor_signal_ts = _to_float(row.get("signal_bar_ts"), 0.0) or _row_time(row)
    if anchor_price <= 0 or reference_unit <= 0:
        skip_reason = "counterfactual_anchor_too_weak"
        if not future_bars:
            skip_reason = (
                "future_bar_dataset_stale"
                if symbol_latest_future_ts > 0 and anchor_signal_ts > symbol_latest_future_ts
                else "insufficient_future_bars"
            )
        elif anchor_price <= 0:
            skip_reason = "anchor_price_missing"
        elif reference_unit <= 0:
            skip_reason = "reference_unit_missing"
        return {
            "contract_version": BARRIER_OUTCOME_ROW_VERSION,
            "bridge_quality_status": "skip",
            "barrier_outcome_label": "",
            "barrier_label_confidence": "low_skip",
            "barrier_outcome_reason": skip_reason,
            "skip_reason": skip_reason,
            "barrier_anchor_side": acting_side,
            "barrier_anchor_context": anchor_context,
            "future_bar_count": int(len(future_bars)),
            "future_bar_latest_ts": round(float(symbol_latest_future_ts), 6) if symbol_latest_future_ts > 0 else 0.0,
            "anchor_price": round(float(anchor_price), 6) if anchor_price > 0 else 0.0,
            "reference_unit_r": round(float(reference_unit), 6) if reference_unit > 0 else 0.0,
            **_empty_wait_outcome_v1(),
        }

    bars_3 = list(future_bars[:DEFAULT_SHORT_HORIZON_BARS])
    bars_6 = list(future_bars[:DEFAULT_MID_HORIZON_BARS])
    coverage_ratio = min(1.0, float(len(bars_6)) / float(DEFAULT_MID_HORIZON_BARS))
    if not bars_6:
        return {
            "contract_version": BARRIER_OUTCOME_ROW_VERSION,
            "bridge_quality_status": "skip",
            "barrier_outcome_label": "",
            "barrier_label_confidence": "low_skip",
            "barrier_outcome_reason": "insufficient_future_bars",
            "skip_reason": "insufficient_future_bars",
            "barrier_anchor_side": acting_side,
            "barrier_anchor_context": anchor_context,
            **_empty_wait_outcome_v1(),
        }

    horizon_end_ts = _to_float(_as_mapping(bars_6[-1]).get("time"), 0.0)
    cf_f_3_raw, cf_a_3_raw = _favorable_and_adverse_move(acting_side, anchor_price, bars_3)
    cf_f_6_raw, cf_a_6_raw = _favorable_and_adverse_move(acting_side, anchor_price, bars_6)
    cf_f_3 = round(float(cf_f_3_raw / reference_unit), 6)
    cf_a_3 = round(float(cf_a_3_raw / reference_unit), 6)
    cf_f_6 = round(float(cf_f_6_raw / reference_unit), 6)
    cf_a_6 = round(float(cf_a_6_raw / reference_unit), 6)

    relief_row = _same_thesis_relief_row(subsequent_rows, anchor_side=acting_side)
    relief_bars = _bars_after_time(bars_6, start_ts=_row_time(relief_row), end_ts=horizon_end_ts) if relief_row else []
    better_entry_gain_6 = _better_entry_gain_r(
        anchor_side=acting_side,
        anchor_price=anchor_price,
        relief_row=relief_row,
        relief_bars=relief_bars,
        reference_unit=reference_unit,
    )
    later_favorable_continuation_r, later_adverse_after_relief_r = _continuation_after_relief_r(
        anchor_side=acting_side,
        relief_row=relief_row,
        all_future_bars=bars_6,
        horizon_end_ts=horizon_end_ts,
        reference_unit=reference_unit,
    )

    barrier_total = _to_float(summary.get("barrier_total"), 0.0)
    barrier_blocked_flag = bool(summary.get("barrier_blocked_flag", False))
    barrier_relief_executed = bool(anchor_context == "relief_release")
    blocking_bias = _to_str(summary.get("blocking_bias", "")).upper()
    release_f_6 = cf_f_6 if barrier_relief_executed else 0.0
    release_a_6 = cf_a_6 if barrier_relief_executed else 0.0
    barrier_recommended_family = _to_str(action_hint.get("recommended_family", ""), "observe_only").lower()
    actual_engine_action_family = _actual_engine_action_family(row)
    effective_wait_block = _effective_wait_block(
        anchor_context=anchor_context,
        barrier_blocked_flag=barrier_blocked_flag,
        blocking_bias=blocking_bias,
        barrier_recommended_family=barrier_recommended_family,
        actual_engine_action_family=actual_engine_action_family,
    )
    cost_balance = _cost_balance_profile(
        cf_f_6=cf_f_6,
        cf_a_6=cf_a_6,
        better_entry_gain_6=better_entry_gain_6,
        later_favorable_continuation_r=later_favorable_continuation_r,
    )
    bias_recovery = _bias_recovery_surface_v1(
        anchor_context=anchor_context,
        blocking_bias=blocking_bias,
        barrier_total=barrier_total,
        barrier_recommended_family=barrier_recommended_family,
        effective_wait_block=effective_wait_block,
        cf_f_6=cf_f_6,
        cf_a_6=cf_a_6,
        better_entry_gain_6=better_entry_gain_6,
        later_favorable_continuation_r=later_favorable_continuation_r,
        loss_avoided_r=_to_float(cost_balance.get("loss_avoided_r"), 0.0),
        profit_missed_r=_to_float(cost_balance.get("profit_missed_r"), 0.0),
        wait_value_r=_to_float(cost_balance.get("wait_value_r"), 0.0),
        release_f_6=release_f_6,
        release_a_6=release_a_6,
    )
    weak_candidate_used = False
    weak_candidate_reason = ""

    label_candidates: list[str] = []
    if barrier_blocked_flag and cf_a_6 >= 1.00 and cf_f_6 < 0.50 and better_entry_gain_6 < 0.35:
        label_candidates.append("avoided_loss")
    if (
        barrier_blocked_flag
        and cf_a_3 >= 0.50
        and better_entry_gain_6 >= 0.35
        and bool(relief_row)
        and later_favorable_continuation_r >= 0.60
    ):
        label_candidates.append("correct_wait")
    if barrier_blocked_flag and cf_f_6 >= 1.00 and cf_a_6 <= 0.50 and better_entry_gain_6 < 0.25:
        label_candidates.append("missed_profit")
    if barrier_blocked_flag and barrier_total >= 0.65 and cf_f_6 >= 1.25 and cf_a_6 <= 0.40 and better_entry_gain_6 < 0.20:
        label_candidates.append("overblock")
    if barrier_relief_executed and release_f_6 >= 0.75 and release_a_6 <= 0.60:
        label_candidates.append("relief_success")
    if barrier_relief_executed and release_a_6 >= 0.80 and release_f_6 < 0.50:
        label_candidates.append("relief_failure")
    if not label_candidates:
        if effective_wait_block and cf_a_3 >= 0.35 and better_entry_gain_6 >= 0.20 and later_favorable_continuation_r >= 0.40:
            label_candidates.append("correct_wait")
            weak_candidate_used = True
            weak_candidate_reason = "soft_correct_wait_bridge_recovery"
    if not label_candidates:
        if effective_wait_block and cf_f_6 >= 0.85 and cf_a_6 <= 0.60 and better_entry_gain_6 < 0.35:
            label_candidates.append("missed_profit")
            weak_candidate_used = True
            weak_candidate_reason = "soft_missed_profit_bridge_recovery"
    if not label_candidates:
        if effective_wait_block and barrier_total >= 0.70 and cf_f_6 >= 1.00 and cf_a_6 <= 0.45 and better_entry_gain_6 < 0.30:
            label_candidates.append("overblock")
            weak_candidate_used = True
            weak_candidate_reason = "soft_overblock_bridge_recovery"
    if not label_candidates:
        if anchor_context == "relief_release" and release_f_6 >= 0.55 and release_a_6 <= 0.75:
            label_candidates.append("relief_success")
            weak_candidate_used = True
            weak_candidate_reason = "soft_relief_success_bridge_recovery"
    if not label_candidates:
        soft_label, weak_candidate_reason = _soft_wait_block_label_candidate(
            anchor_context=anchor_context,
            effective_wait_block=effective_wait_block,
            barrier_total=barrier_total,
            barrier_recommended_family=barrier_recommended_family,
            coverage_ratio=coverage_ratio,
            loss_avoided_r=_to_float(cost_balance.get("loss_avoided_r"), 0.0),
            profit_missed_r=_to_float(cost_balance.get("profit_missed_r"), 0.0),
            wait_value_r=_to_float(cost_balance.get("wait_value_r"), 0.0),
            better_entry_gain_6=better_entry_gain_6,
        )
        if soft_label:
            label_candidates.append(soft_label)
            weak_candidate_used = True
    if not label_candidates:
        soft_label, weak_candidate_reason = _soft_light_block_label_candidate(
            anchor_context=anchor_context,
            barrier_blocked_flag=barrier_blocked_flag,
            blocking_bias=blocking_bias,
            barrier_total=barrier_total,
            barrier_recommended_family=barrier_recommended_family,
            coverage_ratio=coverage_ratio,
            dominant_cost_family=_to_str(cost_balance.get("dominant_cost_family", "")),
            cost_balance_margin_r=_to_float(cost_balance.get("cost_balance_margin_r"), 0.0),
            loss_avoided_r=_to_float(cost_balance.get("loss_avoided_r"), 0.0),
            profit_missed_r=_to_float(cost_balance.get("profit_missed_r"), 0.0),
            wait_value_r=_to_float(cost_balance.get("wait_value_r"), 0.0),
        )
        if soft_label:
            label_candidates.append(soft_label)
            weak_candidate_used = True
    if not label_candidates:
        soft_label, weak_candidate_reason = _soft_relief_watch_label_candidate(
            anchor_context=anchor_context,
            barrier_recommended_family=barrier_recommended_family,
            blocking_bias=blocking_bias,
            coverage_ratio=coverage_ratio,
            dominant_cost_family=_to_str(cost_balance.get("dominant_cost_family", "")),
            cost_balance_margin_r=_to_float(cost_balance.get("cost_balance_margin_r"), 0.0),
            loss_avoided_r=_to_float(cost_balance.get("loss_avoided_r"), 0.0),
            profit_missed_r=_to_float(cost_balance.get("profit_missed_r"), 0.0),
            wait_value_r=_to_float(cost_balance.get("wait_value_r"), 0.0),
        )
        if soft_label:
            label_candidates.append(soft_label)
            weak_candidate_used = True
    if not label_candidates:
        soft_label, weak_candidate_reason = _soft_relief_release_label_candidate(
            anchor_context=anchor_context,
            coverage_ratio=coverage_ratio,
            release_f_6=release_f_6,
            release_a_6=release_a_6,
            dominant_cost_family=_to_str(cost_balance.get("dominant_cost_family", "")),
            cost_balance_margin_r=_to_float(cost_balance.get("cost_balance_margin_r"), 0.0),
        )
        if soft_label:
            label_candidates.append(soft_label)
            weak_candidate_used = True
    if not label_candidates:
        soft_label, weak_candidate_reason = _soft_bias_recovery_label_candidate(
            bias_recovery=bias_recovery,
        )
        if soft_label:
            label_candidates.append(soft_label)
            weak_candidate_used = True

    precedence = ["relief_failure", "relief_success", "overblock", "missed_profit", "correct_wait", "avoided_loss"]
    scores = _score_map(
        cf_f_6=cf_f_6,
        cf_a_3=cf_a_3,
        cf_a_6=cf_a_6,
        better_entry_gain_6=better_entry_gain_6,
        barrier_total=barrier_total,
        release_f_6=release_f_6,
        release_a_6=release_a_6,
    )
    resolved_label = ""
    conflict_resolver_used = False
    score_gap = 1.0
    if label_candidates:
        ordered = [label for label in precedence if label in label_candidates]
        resolved_label = ordered[0]
        if len(ordered) >= 2:
            alt_label = ordered[1]
            score_gap = abs(float(scores.get(resolved_label, 0.0)) - float(scores.get(alt_label, 0.0)))
            if score_gap < 0.15 and float(scores.get(alt_label, 0.0)) > float(scores.get(resolved_label, 0.0)):
                resolved_label = alt_label
                conflict_resolver_used = True
        else:
            score_gap = 1.0

    confidence = _label_confidence(
        label=resolved_label,
        coverage_ratio=coverage_ratio,
        score_gap=score_gap,
        cf_f_6=cf_f_6,
        cf_a_3=cf_a_3,
        cf_a_6=cf_a_6,
        better_entry_gain_6=better_entry_gain_6,
        barrier_total=barrier_total,
        release_f_6=release_f_6,
        release_a_6=release_a_6,
    )
    if score_gap < 0.05 and len(label_candidates) >= 2:
        confidence = "low_skip"
    if weak_candidate_used and resolved_label:
        confidence = "weak_usable"

    correct_wait_diagnostic = _correct_wait_diagnostic_v1(
        anchor_context=anchor_context,
        barrier_recommended_family=barrier_recommended_family,
        effective_wait_block=effective_wait_block,
        resolved_label=resolved_label,
        weak_candidate_reason=weak_candidate_reason,
        cf_a_3=cf_a_3,
        cf_f_6=cf_f_6,
        better_entry_gain_6=better_entry_gain_6,
        later_favorable_continuation_r=later_favorable_continuation_r,
        loss_avoided_r=_to_float(cost_balance.get("loss_avoided_r"), 0.0),
        profit_missed_r=_to_float(cost_balance.get("profit_missed_r"), 0.0),
        wait_value_r=_to_float(cost_balance.get("wait_value_r"), 0.0),
        bias_recovery=bias_recovery,
    )

    skip_reason = ""
    if not resolved_label or confidence == "low_skip":
        skip_reason = _taxonomy_skip_reason(
            summary=summary,
            anchor_context=anchor_context,
            barrier_blocked_flag=barrier_blocked_flag,
            barrier_relief_executed=barrier_relief_executed,
            relief_row=relief_row,
            label_candidates=label_candidates,
            score_gap=score_gap,
            confidence=confidence,
            coverage_ratio=coverage_ratio,
            barrier_total=barrier_total,
            barrier_recommended_family=barrier_recommended_family,
            cf_f_6=cf_f_6,
            cf_a_6=cf_a_6,
            better_entry_gain_6=better_entry_gain_6,
            wait_value_r=_to_float(cost_balance.get("wait_value_r"), 0.0),
            dominant_cost_family=_to_str(cost_balance.get("dominant_cost_family", "")),
            cost_balance_margin_r=_to_float(cost_balance.get("cost_balance_margin_r"), 0.0),
            release_f_6=release_f_6,
            release_a_6=release_a_6,
        )

    coverage_bucket = _coverage_bucket(label=resolved_label, confidence=confidence)
    bridge_quality_status = "labeled" if coverage_bucket == "strict" else ("usable" if coverage_bucket == "usable" else "skip")
    counterfactual_cost_delta_r = _counterfactual_cost_delta_r(
        label=resolved_label,
        loss_avoided_r=_to_float(cost_balance.get("loss_avoided_r"), 0.0),
        profit_missed_r=_to_float(cost_balance.get("profit_missed_r"), 0.0),
        wait_value_r=_to_float(cost_balance.get("wait_value_r"), 0.0),
        release_f_6=release_f_6,
        release_a_6=release_a_6,
    )
    counterfactual_outcome_family = _counterfactual_outcome_family(
        actual_engine_action_family=actual_engine_action_family,
        barrier_recommended_family=barrier_recommended_family,
        barrier_outcome_label=resolved_label,
        skip_reason=skip_reason,
    )
    counterfactual_reason_summary = _counterfactual_reason_summary(
        actual_engine_action_family=actual_engine_action_family,
        barrier_recommended_family=barrier_recommended_family,
        barrier_outcome_label=resolved_label,
        counterfactual_outcome_family=counterfactual_outcome_family,
        counterfactual_cost_delta_r=counterfactual_cost_delta_r,
        skip_reason=skip_reason,
    )
    recommended_action_family = _recommended_action_family(barrier_recommended_family)
    normalized_recommended_detail_family_v2 = _normalized_recommended_detail_family_v2(
        recommended_family=barrier_recommended_family,
        anchor_context=anchor_context,
        blocking_bias=blocking_bias,
        barrier_total=barrier_total,
        dominant_cost_family=_to_str(cost_balance.get("dominant_cost_family", "")),
        cost_balance_margin_r=_to_float(cost_balance.get("cost_balance_margin_r"), 0.0),
        relief_score=_to_float(summary.get("relief_score"), 0.0),
    )
    normalized_recommended_action_family_v2 = _normalized_recommended_action_family_v2(
        recommended_family=barrier_recommended_family,
        anchor_context=anchor_context,
        blocking_bias=blocking_bias,
        barrier_total=barrier_total,
        dominant_cost_family=_to_str(cost_balance.get("dominant_cost_family", "")),
        cost_balance_margin_r=_to_float(cost_balance.get("cost_balance_margin_r"), 0.0),
        relief_score=_to_float(summary.get("relief_score"), 0.0),
    )
    drift_status = _drift_status(
        actual_engine_action_family=actual_engine_action_family,
        barrier_recommended_family=barrier_recommended_family,
    )
    drift_status_v2 = _drift_status_v2(
        actual_engine_action_family=actual_engine_action_family,
        normalized_recommended_action_family_v2=normalized_recommended_action_family_v2,
    )
    drift_cost_direction = _drift_cost_direction(counterfactual_cost_delta_r)
    drift_pair_key = (
        f"{_to_str(actual_engine_action_family, '').lower() or 'unknown'}"
        f"->{_to_str(recommended_action_family, '').lower() or 'unknown'}"
    )
    drift_pair_key_v2 = (
        f"{_to_str(actual_engine_action_family, '').lower() or 'unknown'}"
        f"->{_to_str(normalized_recommended_action_family_v2, '').lower() or 'unknown'}"
    )
    wait_outcome_surface = _wait_outcome_surface_v1(
        barrier_outcome_label=resolved_label,
        barrier_label_confidence=confidence,
        coverage_bucket=coverage_bucket,
        weak_candidate_reason=weak_candidate_reason,
        anchor_context=anchor_context,
        blocking_reason=_to_str(correct_wait_diagnostic.get("blocking_reason", ""), ""),
        counterfactual_cost_delta_r=counterfactual_cost_delta_r,
        better_entry_gain_6=better_entry_gain_6,
        later_continuation_f_6=later_favorable_continuation_r,
        loss_avoided_r=_to_float(cost_balance.get("loss_avoided_r"), 0.0),
        profit_missed_r=_to_float(cost_balance.get("profit_missed_r"), 0.0),
        wait_value_r=_to_float(cost_balance.get("wait_value_r"), 0.0),
        release_f_6=release_f_6,
        release_a_6=release_a_6,
    )

    return {
        "contract_version": BARRIER_OUTCOME_ROW_VERSION,
        "bridge_quality_status": bridge_quality_status,
        "barrier_anchor_side": acting_side,
        "barrier_anchor_context": anchor_context,
        "barrier_horizon_bars": DEFAULT_MID_HORIZON_BARS,
        "barrier_primary_component": _to_str(summary.get("top_component", "")).lower(),
        "barrier_runtime_summary_v1": summary,
        "barrier_input_trace_v1": input_trace,
        "barrier_action_hint_v1": action_hint,
        "reference_unit_r": round(float(reference_unit), 6),
        "anchor_price": round(float(anchor_price), 6),
        "future_bar_coverage_ratio": round(float(coverage_ratio), 6),
        "future_bar_count": len(bars_6),
        "CF_F_3": cf_f_3,
        "CF_F_6": cf_f_6,
        "CF_A_3": cf_a_3,
        "CF_A_6": cf_a_6,
        "barrier_total": round(float(barrier_total), 6),
        "blocking_bias": blocking_bias,
        "barrier_blocked_flag": bool(barrier_blocked_flag),
        "effective_wait_block": bool(effective_wait_block),
        "barrier_relief_executed": bool(barrier_relief_executed),
        "BetterEntryGain_6": better_entry_gain_6,
        "LaterContinuation_F_6": later_favorable_continuation_r,
        "LaterContinuation_A_6": later_adverse_after_relief_r,
        "Release_F_6": round(float(release_f_6), 6),
        "Release_A_6": round(float(release_a_6), 6),
        "barrier_cost_loss_avoided_r": _to_float(cost_balance.get("loss_avoided_r"), 0.0),
        "barrier_cost_profit_missed_r": _to_float(cost_balance.get("profit_missed_r"), 0.0),
        "barrier_cost_wait_value_r": _to_float(cost_balance.get("wait_value_r"), 0.0),
        "dominant_cost_family": _to_str(cost_balance.get("dominant_cost_family", "")).lower(),
        "cost_balance_margin_r": _to_float(cost_balance.get("cost_balance_margin_r"), 0.0),
        "bias_recovery_v1": bias_recovery,
        "correct_wait_diagnostic_v1": correct_wait_diagnostic,
        "label_candidates": list(label_candidates),
        "weak_candidate_used": bool(weak_candidate_used),
        "weak_candidate_reason": _to_str(weak_candidate_reason, "").lower(),
        "barrier_outcome_label": resolved_label,
        "barrier_label_confidence": confidence,
        "coverage_bucket": coverage_bucket,
        "barrier_outcome_reason": skip_reason or resolved_label or "no_label_match",
        "barrier_conflict_resolver_v1": {
            "used": bool(conflict_resolver_used),
            "scores": {key: round(float(value), 6) for key, value in scores.items()},
            "score_gap": round(float(score_gap), 6),
        },
        "actual_engine_action_family": actual_engine_action_family,
        "barrier_recommended_family": barrier_recommended_family,
        "recommended_action_family": recommended_action_family,
        "normalized_recommended_detail_family_v2": normalized_recommended_detail_family_v2,
        "normalized_recommended_action_family_v2": normalized_recommended_action_family_v2,
        "counterfactual_preferred_action_family": _preferred_action_family(barrier_recommended_family),
        "counterfactual_outcome_family": counterfactual_outcome_family,
        "counterfactual_cost_delta_r": round(float(counterfactual_cost_delta_r), 6),
        "counterfactual_reason_summary": counterfactual_reason_summary,
        "drift_status": drift_status,
        "drift_status_v2": drift_status_v2,
        "drift_cost_direction": drift_cost_direction,
        "drift_pair_key": drift_pair_key,
        "drift_pair_key_v2": drift_pair_key_v2,
        "skip_reason": skip_reason,
        **wait_outcome_surface,
    }


def build_barrier_outcome_bridge_rows(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]],
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
    symbols: Sequence[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    normalized_symbols = {str(symbol or "").upper() for symbol in (symbols or []) if str(symbol or "").strip()}
    merged_rows = [_as_mapping(row) for row in entry_decision_rows]
    target_rows = [row for row in merged_rows if _row_has_bridge_candidate(row)]
    if normalized_symbols:
        target_rows = [row for row in target_rows if _to_str(row.get("symbol", "")).upper() in normalized_symbols]
    target_rows = sorted(target_rows, key=_row_time)
    if limit is not None and int(limit) > 0:
        target_rows = target_rows[-int(limit):]

    future_index = _future_bar_index(future_bar_rows or [])
    latest_future_ts_index = _latest_future_bar_ts_index(future_index)
    decision_index = _decision_row_index(merged_rows)
    closed_index = _closed_trade_index(closed_trade_rows)

    bridged_rows: list[dict[str, Any]] = []
    for row in target_rows:
        bridge = _barrier_bridge_payload(row)
        future_bars = _candidate_future_bars(row, future_bar_index=future_index)
        horizon_end_ts = (
            _to_float(_as_mapping(future_bars[min(len(future_bars), DEFAULT_MID_HORIZON_BARS) - 1]).get("time"), 0.0)
            if future_bars
            else 0.0
        )
        subsequent_rows = _subsequent_decision_rows(
            row,
            decision_row_index=decision_index,
            horizon_end_ts=horizon_end_ts,
        )
        outcome_row = _evaluate_barrier_outcome_v1(
            row,
            future_bars=future_bars,
            subsequent_rows=subsequent_rows,
            symbol_latest_future_ts=_to_float(latest_future_ts_index.get(_to_str(row.get("symbol", "")).upper()), 0.0),
        )
        bridged_rows.append(
            {
                "contract_version": BARRIER_OUTCOME_BRIDGE_VERSION,
                "row_key": resolve_entry_decision_row_key(row),
                "symbol": _to_str(row.get("symbol", "")).upper(),
                "time": _row_time(row),
                "outcome": _to_str(row.get("outcome", "")).lower(),
                "barrier_state25_runtime_bridge_v1": bridge,
                "barrier_outcome_bridge_v1": outcome_row,
                "matched_closed_trade_row": _matched_closed_trade_row(row, closed_trade_index=closed_index),
            }
        )
    return bridged_rows


def _safe_mean(values: Sequence[float]) -> float:
    cleaned = [float(value) for value in values if float(value) == float(value)]
    if not cleaned:
        return 0.0
    return float(mean(cleaned))


def _coverage_bucket(*, label: str, confidence: str) -> str:
    label_text = _to_str(label, "").lower()
    confidence_text = _to_str(confidence, "").lower()
    if label_text and confidence_text in BARRIER_STRICT_CONFIDENCE_TIERS:
        return "strict"
    if label_text and confidence_text in BARRIER_USABLE_CONFIDENCE_TIERS:
        return "usable"
    return "skip"


def _coverage_policy_v1() -> dict[str, Any]:
    return {
        "strict_confidence_tiers": list(sorted(BARRIER_STRICT_CONFIDENCE_TIERS)),
        "usable_confidence_tiers": list(sorted(BARRIER_USABLE_CONFIDENCE_TIERS)),
        "skip_confidence_tiers": list(sorted(BARRIER_SKIP_CONFIDENCE_TIERS)),
        "compare_gate_usage": "strict_only",
        "baseline_usage": "strict_plus_usable",
        "diagnostic_usage": "all_rows_with_skip_visibility",
        "execution_override": "disabled_log_only_only",
    }


def _top_count_items(counts: Mapping[str, Any] | None, *, limit: int = 3) -> list[dict[str, Any]]:
    ranked = sorted(
        (
            {"key": _to_str(key, ""), "count": int(_to_int(value, 0))}
            for key, value in _as_mapping(counts).items()
            if _to_str(key, "")
        ),
        key=lambda item: (-int(item["count"]), str(item["key"])),
    )
    return ranked[: max(int(limit), 0)]


def _top_count_mean_items(
    counts: Mapping[str, Any] | None,
    sum_values: Mapping[str, Any] | None,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    count_map = _as_mapping(counts)
    sum_map = _as_mapping(sum_values)
    ranked: list[dict[str, Any]] = []
    for raw_key, raw_count in count_map.items():
        key = _to_str(raw_key, "")
        count = int(_to_int(raw_count, 0))
        if not key or count <= 0:
            continue
        mean_delta = float(_to_float(sum_map.get(key), 0.0)) / max(count, 1)
        ranked.append(
            {
                "key": key,
                "count": count,
                "mean_counterfactual_delta_r": round(float(mean_delta), 4),
            }
        )
    ranked.sort(
        key=lambda item: (
            -int(item["count"]),
            -abs(float(item["mean_counterfactual_delta_r"])),
            str(item["key"]),
        )
    )
    return ranked[: max(int(limit), 0)]


def _safe_median(values: Sequence[float] | None) -> float:
    cleaned = [float(value) for value in (values or [])]
    if not cleaned:
        return 0.0
    return float(median(cleaned))


def _increment_count(counter: dict[str, int], key: str) -> None:
    token = _to_str(key, "")
    if not token:
        return
    counter[token] = int(counter.get(token, 0)) + 1


def _increment_group_count(
    target: dict[str, dict[str, int]],
    *,
    group: str,
    key: str,
) -> None:
    group_key = _to_str(group, "unknown") or "unknown"
    key_text = _to_str(key, "")
    if not key_text:
        return
    counter = target.setdefault(group_key, {})
    counter[key_text] = int(counter.get(key_text, 0)) + 1


def _increment_nested_bucket_label(
    target: dict[str, dict[str, dict[str, int]]],
    *,
    group: str,
    bucket: str,
    label: str,
) -> None:
    group_key = _to_str(group, "unknown") or "unknown"
    bucket_key = _to_str(bucket, "combined") or "combined"
    label_key = _to_str(label, "")
    if not label_key:
        return
    group_map = target.setdefault(group_key, {})
    label_counts = group_map.setdefault(bucket_key, {})
    label_counts[label_key] = int(label_counts.get(label_key, 0)) + 1


def _distribution_summary(counts: Mapping[str, Any] | None) -> dict[str, Any]:
    count_map = {
        _to_str(key, ""): int(_to_int(value, 0))
        for key, value in _as_mapping(counts).items()
        if _to_str(key, "")
    }
    count_map = {key: value for key, value in count_map.items() if value > 0}
    total_rows = sum(count_map.values())
    shares = {
        key: round(float(value) / max(total_rows, 1), 4)
        for key, value in sorted(count_map.items())
    }
    return {
        "total_rows": int(total_rows),
        "counts": dict(sorted(count_map.items())),
        "shares": shares,
        "top_labels": _top_count_items(count_map, limit=5),
    }


def _group_distribution_summary(
    grouped: Mapping[str, Mapping[str, Mapping[str, Any]]] | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for raw_group, bucket_counts in _as_mapping(grouped).items():
        group_key = _to_str(raw_group, "unknown") or "unknown"
        bucket_map = _as_mapping(bucket_counts)
        strict = _distribution_summary(_as_mapping(bucket_map.get("strict")))
        usable = _distribution_summary(_as_mapping(bucket_map.get("usable")))
        combined = _distribution_summary(_as_mapping(bucket_map.get("combined")))
        result[group_key] = {
            "strict": strict,
            "usable": usable,
            "combined": combined,
        }
    return dict(sorted(result.items()))


def _metric_value_stats(values: Sequence[float] | None) -> dict[str, Any]:
    numeric = [float(value) for value in (values or [])]
    non_zero = [value for value in numeric if abs(value) > 1e-9]
    row_count = len(numeric)
    return {
        "row_count": int(row_count),
        "non_zero_rows": int(len(non_zero)),
        "non_zero_share": round(float(len(non_zero)) / max(row_count, 1), 4),
        "mean": round(_safe_mean(numeric), 4),
        "median": round(_safe_median(numeric), 4),
    }


def _cost_balance_summary(metrics: Mapping[str, Sequence[float]] | None) -> dict[str, Any]:
    metric_map = _as_mapping(metrics)
    return {
        "loss_avoided_r": _metric_value_stats(metric_map.get("loss_avoided_r", [])),
        "profit_missed_r": _metric_value_stats(metric_map.get("profit_missed_r", [])),
        "wait_value_r": _metric_value_stats(metric_map.get("wait_value_r", [])),
    }


def _empty_wait_outcome_v1() -> dict[str, Any]:
    payload = {
        "contract_version": WAIT_OUTCOME_VERSION,
        "wait_outcome_family": "",
        "wait_outcome_subtype": "",
        "wait_outcome_confidence": "",
        "wait_outcome_usage_bucket": "",
        "wait_outcome_reason_summary": "",
        "wait_outcome_supporting_metrics": {},
        "wait_outcome_revisit_flag": False,
    }
    flat = dict(payload)
    flat["wait_outcome_v1"] = dict(payload)
    return flat


def _timing_edge_absent_subtype(
    *,
    label: str,
    confidence: str,
    counterfactual_cost_delta_r: float,
    profit_missed_r: float,
    loss_avoided_r: float,
    wait_value_r: float,
    better_entry_gain_6: float,
    later_continuation_f_6: float,
) -> str:
    label_text = _to_str(label, "").lower()
    confidence_text = _to_str(confidence, "").lower()
    if (
        label_text == "missed_profit"
        or float(counterfactual_cost_delta_r) <= -0.25
        or float(profit_missed_r) >= float(loss_avoided_r) + 0.10
    ):
        return "missed_profit_leaning"
    if (
        abs(float(better_entry_gain_6)) <= 1e-9
        and float(later_continuation_f_6) <= 0.05
        and float(wait_value_r) <= 0.05
    ):
        return "zero_entry_gain_no_continuation"
    if (
        label_text == "avoided_loss"
        and confidence_text in BARRIER_STRICT_CONFIDENCE_TIERS
        and abs(float(better_entry_gain_6)) <= 1e-9
        and 0.05 < float(later_continuation_f_6) <= 0.25
        and 0.05 < float(wait_value_r) <= 0.25
        and float(loss_avoided_r) >= max(float(wait_value_r), float(profit_missed_r)) + 0.50
    ):
        return "small_continuation_avoided_loss"
    return "timing_edge_other"


def _wait_outcome_surface_v1(
    *,
    barrier_outcome_label: str,
    barrier_label_confidence: str,
    coverage_bucket: str,
    weak_candidate_reason: str,
    anchor_context: str,
    blocking_reason: str,
    counterfactual_cost_delta_r: float,
    better_entry_gain_6: float,
    later_continuation_f_6: float,
    loss_avoided_r: float,
    profit_missed_r: float,
    wait_value_r: float,
    release_f_6: float,
    release_a_6: float,
) -> dict[str, Any]:
    label_text = _to_str(barrier_outcome_label, "").lower()
    confidence_text = _to_str(barrier_label_confidence, "").lower()
    coverage_bucket_text = _to_str(coverage_bucket, "").lower()
    weak_reason = _to_str(weak_candidate_reason, "").lower()
    anchor_context_text = _to_str(anchor_context, "").lower()
    blocking_reason_text = _to_str(blocking_reason, "").lower()

    family = ""
    subtype = ""
    confidence = ""
    usage_bucket = ""
    reason_summary = ""
    revisit_flag = False

    if label_text == "correct_wait":
        family = "timing_improvement"
        subtype = "correct_wait_strict"
        usage_bucket = "strict" if coverage_bucket_text == "strict" else "usable"
        confidence = "high" if usage_bucket == "strict" else "medium"
        reason_summary = "correct_wait_strict"
    elif label_text == "relief_success":
        family = "protective_exit"
        subtype = "profitable_wait_then_exit"
        usage_bucket = "usable" if coverage_bucket_text in {"strict", "usable"} else "diagnostic"
        confidence = "medium" if usage_bucket == "usable" else "low"
        reason_summary = "relief_success_wait_family"
    elif label_text == "relief_failure" or anchor_context_text == "relief_release":
        family = "reversal_escape"
        subtype = "barrier_relief_fail_escape" if label_text == "relief_failure" else "thesis_break_escape_after_wait"
        usage_bucket = "usable" if coverage_bucket_text in {"strict", "usable"} else "diagnostic"
        confidence = "medium" if usage_bucket == "usable" else "low"
        reason_summary = "relief_failure_wait_family" if label_text == "relief_failure" else "relief_release_diagnostic"
        revisit_flag = label_text != "relief_failure"
    elif blocking_reason_text == "timing_edge_absent":
        subtype_key = _timing_edge_absent_subtype(
            label=label_text,
            confidence=confidence_text,
            counterfactual_cost_delta_r=counterfactual_cost_delta_r,
            profit_missed_r=profit_missed_r,
            loss_avoided_r=loss_avoided_r,
            wait_value_r=wait_value_r,
            better_entry_gain_6=better_entry_gain_6,
            later_continuation_f_6=later_continuation_f_6,
        )
        if subtype_key == "missed_profit_leaning":
            family = "failed_wait"
            subtype = "wait_but_missed_move"
            usage_bucket = "usable" if coverage_bucket_text in {"strict", "usable"} else "diagnostic"
            confidence = "medium" if usage_bucket == "usable" else "low"
            reason_summary = subtype_key
        elif subtype_key == "zero_entry_gain_no_continuation":
            family = "failed_wait"
            subtype = "wait_without_timing_edge"
            usage_bucket = "diagnostic"
            confidence = "low"
            reason_summary = subtype_key
        elif subtype_key == "small_continuation_avoided_loss":
            family = "neutral_wait"
            subtype = "small_value_wait"
            usage_bucket = "diagnostic"
            confidence = "low"
            reason_summary = subtype_key
            revisit_flag = True
    elif label_text == "missed_profit":
        family = "failed_wait"
        subtype = "wait_but_missed_move"
        usage_bucket = "strict" if coverage_bucket_text == "strict" else ("usable" if coverage_bucket_text == "usable" else "diagnostic")
        confidence = "high" if usage_bucket == "strict" else ("medium" if usage_bucket == "usable" else "low")
        reason_summary = weak_reason or "missed_profit_wait_family"

    payload = {
        "contract_version": WAIT_OUTCOME_VERSION,
        "wait_outcome_family": family,
        "wait_outcome_subtype": subtype,
        "wait_outcome_confidence": confidence,
        "wait_outcome_usage_bucket": usage_bucket,
        "wait_outcome_reason_summary": reason_summary,
        "wait_outcome_supporting_metrics": {
            "better_entry_gain_6": round(float(better_entry_gain_6), 6),
            "later_continuation_f_6": round(float(later_continuation_f_6), 6),
            "loss_avoided_r": round(float(loss_avoided_r), 6),
            "profit_missed_r": round(float(profit_missed_r), 6),
            "wait_value_r": round(float(wait_value_r), 6),
            "release_f_6": round(float(release_f_6), 6),
            "release_a_6": round(float(release_a_6), 6),
            "counterfactual_cost_delta_r": round(float(counterfactual_cost_delta_r), 6),
        },
        "wait_outcome_revisit_flag": bool(revisit_flag),
    }
    flat = dict(payload)
    flat["wait_outcome_v1"] = dict(payload)
    return flat


def _build_correct_wait_blocking_casebook_v1(
    bridged_rows: Sequence[Mapping[str, Any]] | None,
    *,
    focus_blocking_reason: str,
    contract_version: str,
) -> dict[str, Any]:
    focus_reason = _to_str(focus_blocking_reason, "").lower()
    signature_counts: dict[str, int] = {}
    signature_payloads: dict[str, dict[str, Any]] = {}
    signature_samples: dict[str, dict[str, Any]] = {}
    loss_avoided_values: list[float] = []
    profit_missed_values: list[float] = []
    wait_value_values: list[float] = []
    better_entry_gain_values: list[float] = []
    later_continuation_values: list[float] = []
    loss_wait_margin_values: list[float] = []
    loss_profit_margin_values: list[float] = []
    zero_entry_gain_rows = 0
    small_entry_gain_rows = 0
    wait_value_support_rows = 0
    continuation_support_rows = 0
    effective_wait_block_rows = 0
    row_count = 0

    for raw_row in list(bridged_rows or []):
        bridged_row = _as_mapping(raw_row)
        outcome = _as_mapping(bridged_row.get("barrier_outcome_bridge_v1"))
        diagnostic = _as_mapping(outcome.get("correct_wait_diagnostic_v1"))
        blocking_reason = _to_str(diagnostic.get("blocking_reason", ""), "").lower()
        if blocking_reason != focus_reason:
            continue

        row_count += 1
        bridge = _as_mapping(bridged_row.get("barrier_state25_runtime_bridge_v1"))
        input_trace = _as_mapping(outcome.get("barrier_input_trace_v1"))
        if not input_trace:
            input_trace = _as_mapping(bridge.get("barrier_input_trace_v1"))
        runtime_summary = _as_mapping(outcome.get("barrier_runtime_summary_v1"))
        if not runtime_summary:
            runtime_summary = _as_mapping(bridge.get("barrier_runtime_summary_v1"))

        scene_family = _to_str(input_trace.get("state25_label", ""), "unknown").lower() or "unknown"
        barrier_family = (
            _to_str(
                outcome.get("barrier_primary_component", "")
                or runtime_summary.get("top_component", "")
                or runtime_summary.get("blocking_bias", ""),
                "unknown",
            ).lower()
            or "unknown"
        )
        blocking_bias = (
            _to_str(outcome.get("blocking_bias", "") or runtime_summary.get("blocking_bias", ""), "unknown").lower()
            or "unknown"
        )
        recommended_family = _to_str(outcome.get("barrier_recommended_family", ""), "observe_only").lower()
        actual_family = _to_str(outcome.get("actual_engine_action_family", ""), "unknown").lower()
        normalized_action_family_v2 = _to_str(
            outcome.get("normalized_recommended_action_family_v2", ""),
            _to_str(outcome.get("recommended_action_family", ""), "observe_only"),
        ).lower()
        symbol = _to_str(bridged_row.get("symbol", ""), "UNKNOWN").upper() or "UNKNOWN"
        time_value = _to_str(bridged_row.get("time", ""), "")
        label = _to_str(outcome.get("barrier_outcome_label", ""), "").lower()
        confidence = _to_str(outcome.get("barrier_label_confidence", ""), "").lower()
        drift_pair_key_v2 = _to_str(outcome.get("drift_pair_key_v2", ""), "").lower()
        counterfactual_cost_delta_r = _to_float(outcome.get("counterfactual_cost_delta_r"), 0.0)

        loss_avoided_r = _to_float(diagnostic.get("loss_avoided_r"), 0.0)
        profit_missed_r = _to_float(diagnostic.get("profit_missed_r"), 0.0)
        wait_value_r = _to_float(diagnostic.get("wait_value_r"), 0.0)
        better_entry_gain_6 = _to_float(diagnostic.get("better_entry_gain_6"), 0.0)
        later_continuation_f_6 = _to_float(diagnostic.get("later_continuation_f_6"), 0.0)

        loss_avoided_values.append(loss_avoided_r)
        profit_missed_values.append(profit_missed_r)
        wait_value_values.append(wait_value_r)
        better_entry_gain_values.append(better_entry_gain_6)
        later_continuation_values.append(later_continuation_f_6)
        loss_wait_margin_values.append(loss_avoided_r - wait_value_r)
        loss_profit_margin_values.append(loss_avoided_r - profit_missed_r)
        if abs(better_entry_gain_6) <= 1e-9:
            zero_entry_gain_rows += 1
        if better_entry_gain_6 <= 0.15:
            small_entry_gain_rows += 1
        if bool(diagnostic.get("wait_value_support", False)):
            wait_value_support_rows += 1
        if bool(diagnostic.get("continuation_support", False)):
            continuation_support_rows += 1
        if bool(diagnostic.get("effective_wait_block", False)):
            effective_wait_block_rows += 1

        signature_payload = {
            "scene_family": scene_family,
            "barrier_family": barrier_family,
            "blocking_bias": blocking_bias,
            "recommended_family": recommended_family,
            "loss_avoided_r": round(loss_avoided_r, 3),
            "profit_missed_r": round(profit_missed_r, 3),
            "wait_value_r": round(wait_value_r, 3),
            "better_entry_gain_6": round(better_entry_gain_6, 3),
            "later_continuation_f_6": round(later_continuation_f_6, 3),
        }
        signature_key = json.dumps(signature_payload, ensure_ascii=False, sort_keys=True)
        signature_counts[signature_key] = int(signature_counts.get(signature_key, 0)) + 1
        signature_payloads[signature_key] = dict(signature_payload)
        signature_samples.setdefault(
            signature_key,
            {
                "symbol": symbol,
                "time": time_value,
                "scene_family": scene_family,
                "barrier_family": barrier_family,
                "blocking_bias": blocking_bias,
                "recommended_family": recommended_family,
                "actual_engine_action_family": actual_family,
                "normalized_recommended_action_family_v2": normalized_action_family_v2,
                "loss_avoided_r": round(loss_avoided_r, 6),
                "profit_missed_r": round(profit_missed_r, 6),
                "wait_value_r": round(wait_value_r, 6),
                "better_entry_gain_6": round(better_entry_gain_6, 6),
                "later_continuation_f_6": round(later_continuation_f_6, 6),
                "resolved_label": label,
                "confidence": confidence,
                "drift_pair_key_v2": drift_pair_key_v2,
                "counterfactual_cost_delta_r": round(counterfactual_cost_delta_r, 6),
            },
        )

    ranked_signatures = sorted(
        (
            {
                "key": key,
                "count": int(count),
                "signature": dict(signature_payloads.get(key, {})),
                "sample": dict(signature_samples.get(key, {})),
            }
            for key, count in signature_counts.items()
            if int(count) > 0
        ),
        key=lambda item: (-int(item["count"]), str(item["key"])),
    )
    top_signatures: list[dict[str, Any]] = []
    representative_samples: list[dict[str, Any]] = []
    for item in ranked_signatures[:5]:
        count = int(item["count"])
        top_signatures.append(
            {
                "count": count,
                "share": round(float(count) / max(row_count, 1), 4),
                "signature": dict(item.get("signature", {})),
                "sample": dict(item.get("sample", {})),
            }
        )
        representative_samples.append(dict(item.get("sample", {})))

    return {
        "contract_version": contract_version,
        "focus_blocking_reason": focus_reason,
        "focus_rows": row_count,
        "unique_signatures": len(signature_counts),
        "effective_wait_block_rows": effective_wait_block_rows,
        "wait_value_support_rows": wait_value_support_rows,
        "continuation_support_rows": continuation_support_rows,
        "zero_entry_gain_rows": zero_entry_gain_rows,
        "small_entry_gain_rows": small_entry_gain_rows,
        "mean_loss_avoided_r": round(_safe_mean(loss_avoided_values), 4),
        "mean_profit_missed_r": round(_safe_mean(profit_missed_values), 4),
        "mean_wait_value_r": round(_safe_mean(wait_value_values), 4),
        "mean_better_entry_gain_6": round(_safe_mean(better_entry_gain_values), 4),
        "mean_later_continuation_f_6": round(_safe_mean(later_continuation_values), 4),
        "mean_loss_wait_margin_r": round(_safe_mean(loss_wait_margin_values), 4),
        "mean_loss_profit_margin_r": round(_safe_mean(loss_profit_margin_values), 4),
        "top_signatures": top_signatures,
        "representative_samples": representative_samples,
    }


def _casebook_subtype_profile(
    rows: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    label_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    weak_reason_counts: dict[str, int] = {}
    for raw_row in list(rows or []):
        bridged_row = _as_mapping(raw_row)
        outcome = _as_mapping(bridged_row.get("barrier_outcome_bridge_v1"))
        label = _to_str(outcome.get("barrier_outcome_label", ""), "").lower()
        confidence = _to_str(outcome.get("barrier_label_confidence", ""), "").lower()
        weak_reason = _to_str(outcome.get("weak_candidate_reason", ""), "").lower()
        if label:
            _increment_count(label_counts, label)
        if confidence:
            _increment_count(confidence_counts, confidence)
        if weak_reason:
            _increment_count(weak_reason_counts, weak_reason)
    return {
        "row_count": len(list(rows or [])),
        "label_counts": dict(sorted(label_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "top_labels": _top_count_items(label_counts, limit=5),
        "top_weak_reasons": _top_count_items(weak_reason_counts, limit=5),
    }


def _build_correct_wait_casebook_v1(
    bridged_rows: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    casebook = _build_correct_wait_blocking_casebook_v1(
        bridged_rows,
        focus_blocking_reason="loss_avoided_dominates",
        contract_version=CORRECT_WAIT_CASEBOOK_VERSION,
    )
    casebook["loss_avoided_dominates_rows"] = int(_to_int(casebook.get("focus_rows"), 0))
    return casebook


def _build_timing_edge_absent_casebook_v1(
    bridged_rows: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    filtered_rows: list[dict[str, Any]] = []
    subtype_rows: dict[str, list[dict[str, Any]]] = {
        "zero_entry_gain_no_continuation": [],
        "missed_profit_leaning": [],
        "small_continuation_avoided_loss": [],
        "timing_edge_other": [],
    }
    for raw_row in list(bridged_rows or []):
        bridged_row = _as_mapping(raw_row)
        outcome = _as_mapping(bridged_row.get("barrier_outcome_bridge_v1"))
        diagnostic = _as_mapping(outcome.get("correct_wait_diagnostic_v1"))
        blocking_reason = _to_str(diagnostic.get("blocking_reason", ""), "").lower()
        if blocking_reason != "timing_edge_absent":
            continue
        filtered_rows.append(dict(bridged_row))

        label = _to_str(outcome.get("barrier_outcome_label", ""), "").lower()
        profit_missed_r = _to_float(diagnostic.get("profit_missed_r"), 0.0)
        loss_avoided_r = _to_float(diagnostic.get("loss_avoided_r"), 0.0)
        wait_value_r = _to_float(diagnostic.get("wait_value_r"), 0.0)
        better_entry_gain_6 = _to_float(diagnostic.get("better_entry_gain_6"), 0.0)
        later_continuation_f_6 = _to_float(diagnostic.get("later_continuation_f_6"), 0.0)
        counterfactual_cost_delta_r = _to_float(outcome.get("counterfactual_cost_delta_r"), 0.0)
        confidence = _to_str(outcome.get("barrier_label_confidence", ""), "").lower()

        subtype = _timing_edge_absent_subtype(
            label=label,
            confidence=confidence,
            counterfactual_cost_delta_r=counterfactual_cost_delta_r,
            profit_missed_r=profit_missed_r,
            loss_avoided_r=loss_avoided_r,
            wait_value_r=wait_value_r,
            better_entry_gain_6=better_entry_gain_6,
            later_continuation_f_6=later_continuation_f_6,
        )
        subtype_rows[subtype].append(dict(bridged_row))

    casebook = _build_correct_wait_blocking_casebook_v1(
        filtered_rows,
        focus_blocking_reason="timing_edge_absent",
        contract_version=TIMING_EDGE_ABSENT_CASEBOOK_VERSION,
    )
    casebook["timing_edge_absent_rows"] = int(_to_int(casebook.get("focus_rows"), 0))
    subtype_counts = {
        key: len(value)
        for key, value in sorted(subtype_rows.items())
    }
    casebook["subtype_counts"] = subtype_counts
    casebook["top_subtypes"] = _top_count_items(subtype_counts, limit=5)
    casebook["subtype_casebooks"] = {
        key: _build_correct_wait_blocking_casebook_v1(
            rows,
            focus_blocking_reason="timing_edge_absent",
            contract_version=TIMING_EDGE_ABSENT_CASEBOOK_VERSION,
        )
        for key, rows in sorted(subtype_rows.items())
        if rows
    }
    casebook["subtype_profiles"] = {
        key: _casebook_subtype_profile(rows)
        for key, rows in sorted(subtype_rows.items())
        if rows
    }
    return casebook


def _parse_iso_datetime(value: object) -> datetime | None:
    text = _to_str(value, "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed


def _build_barrier_readiness_gate_v1(
    *,
    summary: Mapping[str, Any] | None,
    coverage: Mapping[str, Any] | None,
    counterfactual_audit: Mapping[str, Any] | None,
    drift_audit: Mapping[str, Any] | None,
    runtime_status: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary_map = _as_mapping(summary)
    coverage_map = _as_mapping(coverage)
    dashboard = _as_mapping(coverage_map.get("dashboard"))
    counterfactual = _as_mapping(counterfactual_audit)
    drift = _as_mapping(drift_audit)
    runtime = _as_mapping(runtime_status)

    semantic_anchor_rows = int(_to_int(summary_map.get("semantic_anchor_rows"), 0))
    strict_rows = int(_to_int(summary_map.get("strict_rows"), 0))
    covered_share_ex_pre_context = float(
        _to_float(dashboard.get("covered_share_ex_pre_context"), 0.0)
    )
    semantic_skip_share_ex_pre_context = float(
        _to_float(dashboard.get("semantic_skip_share_ex_pre_context"), 0.0)
    )
    overblock_ratio = float(_to_float(summary_map.get("overblock_ratio"), 0.0))
    counterfactual_cost_delta_r_mean = float(
        _to_float(summary_map.get("counterfactual_cost_delta_r_mean"), 0.0)
    )
    counterfactual_positive_rate = float(
        _to_float(summary_map.get("counterfactual_positive_rate"), 0.0)
    )
    counterfactual_negative_rate = float(
        _to_float(summary_map.get("counterfactual_negative_rate"), 0.0)
    )
    negative_mismatch_rows = int(_to_int(drift.get("negative_mismatch_rows"), 0))
    negative_mismatch_rate = float(negative_mismatch_rows) / max(semantic_anchor_rows, 1)

    runtime_updated_at = _parse_iso_datetime(runtime.get("updated_at"))
    heartbeat_age_seconds = (
        max((datetime.now().astimezone() - runtime_updated_at).total_seconds(), 0.0)
        if runtime_updated_at is not None
        else None
    )
    runtime_heartbeat_ready = bool(
        runtime_updated_at is not None
        and heartbeat_age_seconds is not None
        and heartbeat_age_seconds <= MAX_BARRIER_READINESS_HEARTBEAT_AGE_SECONDS
        and int(_to_int(runtime.get("loop_count"), 0)) > 0
    )

    checks = {
        "semantic_anchor_rows_ready": bool(
            semantic_anchor_rows >= MIN_BARRIER_READINESS_SEMANTIC_ANCHOR_ROWS
        ),
        "strict_rows_ready": bool(strict_rows >= MIN_BARRIER_READINESS_STRICT_ROWS),
        "covered_share_ready": bool(
            covered_share_ex_pre_context >= MIN_BARRIER_READINESS_COVERED_SHARE_EX_PRE_CONTEXT
        ),
        "semantic_skip_ready": bool(
            semantic_skip_share_ex_pre_context
            <= MAX_BARRIER_READINESS_SEMANTIC_SKIP_SHARE_EX_PRE_CONTEXT
        ),
        "overblock_ready": bool(overblock_ratio <= MAX_BARRIER_READINESS_OVERBLOCK_RATIO),
        "counterfactual_direction_ready": bool(
            counterfactual_cost_delta_r_mean >= MIN_BARRIER_READINESS_COUNTERFACTUAL_DELTA_R_MEAN
            and (counterfactual_positive_rate - counterfactual_negative_rate)
            >= MIN_BARRIER_READINESS_POSITIVE_ADVANTAGE
        ),
        "negative_mismatch_ready": bool(
            negative_mismatch_rate <= MAX_BARRIER_READINESS_NEGATIVE_MISMATCH_RATE
        ),
        "runtime_heartbeat_ready": runtime_heartbeat_ready,
    }
    blockers: list[str] = []
    if not checks["semantic_anchor_rows_ready"]:
        blockers.append("semantic_anchor_rows_below_threshold")
    if not checks["strict_rows_ready"]:
        blockers.append("strict_rows_below_threshold")
    if not checks["covered_share_ready"]:
        blockers.append("covered_share_ex_pre_context_below_threshold")
    if not checks["semantic_skip_ready"]:
        blockers.append("semantic_skip_share_ex_pre_context_above_threshold")
    if not checks["overblock_ready"]:
        blockers.append("overblock_ratio_above_threshold")
    if not checks["counterfactual_direction_ready"]:
        blockers.append("counterfactual_direction_not_positive_enough")
    if not checks["negative_mismatch_ready"]:
        blockers.append("negative_mismatch_rate_above_threshold")
    if not checks["runtime_heartbeat_ready"]:
        blockers.append("runtime_heartbeat_not_stable")

    coverage_ready = all(
        checks[key]
        for key in (
            "semantic_anchor_rows_ready",
            "strict_rows_ready",
            "covered_share_ready",
            "semantic_skip_ready",
            "overblock_ready",
            "counterfactual_direction_ready",
            "negative_mismatch_ready",
        )
    )
    ready = bool(coverage_ready and checks["runtime_heartbeat_ready"])
    if ready:
        stage = "ready_for_next_owner"
    elif coverage_ready:
        stage = "blocked_wiring"
    else:
        stage = "blocked_coverage"

    next_actions: list[str] = []
    if not checks["semantic_anchor_rows_ready"]:
        next_actions.append("Increase semantic anchor rows before using barrier readiness as a handoff signal.")
    if not checks["strict_rows_ready"]:
        next_actions.append("Accumulate more strict high/medium-confidence barrier rows.")
    if not checks["covered_share_ready"] or not checks["semantic_skip_ready"]:
        next_actions.append("Continue coverage engineering until usable coverage stays high without semantic skips.")
    if not checks["counterfactual_direction_ready"] or not checks["negative_mismatch_ready"]:
        next_actions.append("Review drift/counterfactual rows and reduce negative mismatch before advancing.")
    if not checks["runtime_heartbeat_ready"]:
        next_actions.append("Keep runtime heartbeat stable before treating barrier wiring as production-ready.")
    if ready:
        next_actions.append("Barrier coverage is ready; proceed to the next owner while keeping barrier in log-only authority.")

    return {
        "contract_version": BARRIER_READINESS_GATE_VERSION,
        "ready": ready,
        "stage": stage,
        "checks": checks,
        "thresholds": {
            "min_semantic_anchor_rows": MIN_BARRIER_READINESS_SEMANTIC_ANCHOR_ROWS,
            "min_strict_rows": MIN_BARRIER_READINESS_STRICT_ROWS,
            "min_covered_share_ex_pre_context": MIN_BARRIER_READINESS_COVERED_SHARE_EX_PRE_CONTEXT,
            "max_semantic_skip_share_ex_pre_context": MAX_BARRIER_READINESS_SEMANTIC_SKIP_SHARE_EX_PRE_CONTEXT,
            "max_overblock_ratio": MAX_BARRIER_READINESS_OVERBLOCK_RATIO,
            "min_counterfactual_cost_delta_r_mean": MIN_BARRIER_READINESS_COUNTERFACTUAL_DELTA_R_MEAN,
            "min_positive_advantage": MIN_BARRIER_READINESS_POSITIVE_ADVANTAGE,
            "max_negative_mismatch_rate": MAX_BARRIER_READINESS_NEGATIVE_MISMATCH_RATE,
            "max_runtime_heartbeat_age_seconds": MAX_BARRIER_READINESS_HEARTBEAT_AGE_SECONDS,
        },
        "metrics": {
            "semantic_anchor_rows": semantic_anchor_rows,
            "strict_rows": strict_rows,
            "covered_share_ex_pre_context": round(covered_share_ex_pre_context, 4),
            "semantic_skip_share_ex_pre_context": round(semantic_skip_share_ex_pre_context, 4),
            "overblock_ratio": round(overblock_ratio, 4),
            "counterfactual_cost_delta_r_mean": round(counterfactual_cost_delta_r_mean, 4),
            "counterfactual_positive_rate": round(counterfactual_positive_rate, 4),
            "counterfactual_negative_rate": round(counterfactual_negative_rate, 4),
            "negative_mismatch_rate": round(negative_mismatch_rate, 4),
        },
        "runtime_heartbeat": {
            "updated_at": _to_str(runtime.get("updated_at"), ""),
            "loop_count": int(_to_int(runtime.get("loop_count"), 0)),
            "age_seconds": (
                round(float(heartbeat_age_seconds), 1)
                if heartbeat_age_seconds is not None
                else None
            ),
            "healthy": runtime_heartbeat_ready,
        },
        "blockers": blockers,
        "next_actions": next_actions,
        "counterfactual_summary": {
            "top_counterfactual_outcomes": list(
                counterfactual.get("top_counterfactual_outcomes", []) or []
            ),
            "top_mismatch_action_pairs": list(
                drift.get("top_mismatch_action_pairs", []) or []
            ),
        },
    }


def _summary_skip_reason(
    summary: Mapping[str, Any],
    acting_side: str,
    row: Mapping[str, Any] | None = None,
) -> str:
    if bool(summary.get("available", False)) and str(acting_side).upper() in {"BUY", "SELL"}:
        return ""
    mapped = _as_mapping(row)
    availability_stage = _to_str(summary.get("availability_stage", "")).lower()
    availability_reason = _to_str(summary.get("availability_reason", "")).lower()
    reason_summary = _to_str(summary.get("reason_summary", "")).lower()
    blocked_by = _to_str(mapped.get("blocked_by", "")).lower()
    if availability_stage == "pre_context_skip":
        reason = availability_reason or blocked_by or "unknown"
        return f"pre_context_skip:{reason}"
    if reason_summary.startswith("pre_context|"):
        reason = reason_summary.split("|", 1)[1] if "|" in reason_summary else ""
        reason = reason or availability_reason or blocked_by or "unknown"
        return f"pre_context_skip:{reason}"
    if "barrier_missing" in reason_summary:
        return "barrier_state_missing"
    if not str(acting_side).upper() in {"BUY", "SELL"}:
        return "acting_side_unresolved"
    return "barrier_runtime_unavailable"


def _taxonomy_skip_reason(
    *,
    summary: Mapping[str, Any],
    anchor_context: str,
    barrier_blocked_flag: bool,
    barrier_relief_executed: bool,
    relief_row: Mapping[str, Any] | None,
    label_candidates: Sequence[str],
    score_gap: float,
    confidence: str,
    coverage_ratio: float,
    barrier_total: float,
    barrier_recommended_family: str,
    cf_f_6: float,
    cf_a_6: float,
    better_entry_gain_6: float,
    wait_value_r: float,
    dominant_cost_family: str,
    cost_balance_margin_r: float,
    release_f_6: float,
    release_a_6: float,
) -> str:
    if coverage_ratio < 0.70:
        return "insufficient_future_bars"
    if len(label_candidates) >= 2 and score_gap < 0.15:
        return "overlapping_label_candidates"

    top_component = _to_str(summary.get("top_component", "")).lower()
    low_move_profile = (
        cf_f_6 < 0.60
        and cf_a_6 < 0.60
        and better_entry_gain_6 < 0.25
        and release_f_6 < 0.60
        and release_a_6 < 0.80
    )
    if low_move_profile:
        return "low_move_magnitude"

    if barrier_relief_executed or anchor_context == "relief_release":
        if release_f_6 < 0.75 and release_a_6 < 0.80:
            return "release_window_not_mature"

    blocking_bias = _to_str(summary.get("blocking_bias", "")).upper()
    recommended_text = _to_str(barrier_recommended_family, "").lower()

    if (
        not barrier_blocked_flag
        and _to_str(anchor_context, "").lower() == "wait_block"
        and blocking_bias == "LIGHT_BLOCK"
        and recommended_text == "observe_only"
        and float(barrier_total) < 0.35
    ):
        if dominant_cost_family == "loss_avoided":
            return "light_block_loss_avoided_bias"
        if dominant_cost_family == "profit_missed":
            return "light_block_profit_missed_bias"
        return "light_block_observe_only"

    if (
        not barrier_blocked_flag
        and _to_str(anchor_context, "").lower() == "wait_block"
        and blocking_bias == "WAIT_BLOCK"
        and recommended_text == "wait_bias"
    ):
        if dominant_cost_family == "loss_avoided":
            return "wait_bias_loss_avoided_unresolved"
        if dominant_cost_family == "profit_missed":
            return "wait_bias_profit_missed_unresolved"
        return "wait_bias_unresolved"

    if barrier_blocked_flag and not relief_row:
        if better_entry_gain_6 >= 0.20:
            return "no_reentry_or_relief_observed"
        if cf_f_6 < 0.50 and cf_a_6 < 0.50:
            return "counterfactual_anchor_too_weak"

    if top_component == "conflict_barrier":
        return "side_conflict_unresolved"

    if (
        barrier_relief_executed
        and not barrier_blocked_flag
        and recommended_text == "observe_only"
        and dominant_cost_family == "loss_avoided"
    ):
        return "relief_release_loss_avoided_unresolved"

    if (
        barrier_relief_executed
        and not barrier_blocked_flag
        and recommended_text == "observe_only"
        and dominant_cost_family == "profit_missed"
    ):
        return "relief_release_profit_missed_unresolved"

    if (
        barrier_blocked_flag
        and recommended_text in {"wait_bias", "block_bias"}
        and dominant_cost_family == "loss_avoided"
        and cost_balance_margin_r >= 0.80
    ):
        return "loss_avoided_bias_unresolved"

    if (
        barrier_blocked_flag
        and recommended_text in {"wait_bias", "block_bias"}
        and dominant_cost_family in {"profit_missed", "wait_value"}
        and cost_balance_margin_r >= 0.60
    ):
        return "profit_wait_tradeoff_unresolved"

    if (
        barrier_blocked_flag
        and max(float(cf_f_6), float(cf_a_6), float(wait_value_r)) >= 0.60
        and cost_balance_margin_r < 0.50
    ) or (confidence == "low_skip" and better_entry_gain_6 >= 0.20 and cf_f_6 >= 0.50):
        return "ambiguous_cost_balance"

    if confidence == "low_skip":
        return "low_confidence_generic"
    return "no_label_match"


def build_barrier_outcome_bridge_report(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]],
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
    runtime_status: Mapping[str, Any] | None = None,
    symbols: Sequence[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    merged_rows = [_as_mapping(row) for row in entry_decision_rows]
    bridged_rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=merged_rows,
        closed_trade_rows=closed_trade_rows,
        future_bar_rows=future_bar_rows,
        symbols=symbols,
        limit=limit,
    )

    label_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    anchor_context_counts: dict[str, int] = {}
    skip_reason_counts: dict[str, int] = {}
    coverage_bucket_counts: dict[str, int] = {"strict": 0, "usable": 0, "skip": 0}
    actual_engine_action_family_counts: dict[str, int] = {}
    barrier_recommended_family_counts: dict[str, int] = {}
    recommended_action_family_counts: dict[str, int] = {}
    normalized_recommended_detail_family_counts_v2: dict[str, int] = {}
    normalized_recommended_action_family_counts_v2: dict[str, int] = {}
    counterfactual_outcome_family_counts: dict[str, int] = {}
    actual_vs_recommended_counts: dict[str, int] = {}
    normalized_actual_vs_target_action_counts: dict[str, int] = {}
    normalized_actual_vs_target_action_counts_v2: dict[str, int] = {}
    drift_alignment_counts: dict[str, int] = {}
    drift_alignment_counts_v2: dict[str, int] = {}
    mismatch_action_pair_counts: dict[str, int] = {}
    mismatch_action_pair_delta_sums: dict[str, float] = {}
    mismatch_action_pair_counts_v2: dict[str, int] = {}
    mismatch_action_pair_delta_sums_v2: dict[str, float] = {}
    positive_mismatch_pair_counts: dict[str, int] = {}
    positive_mismatch_pair_delta_sums: dict[str, float] = {}
    negative_mismatch_pair_counts: dict[str, int] = {}
    negative_mismatch_pair_delta_sums: dict[str, float] = {}
    symbol_mismatch_counts: dict[str, int] = {}
    scene_family_mismatch_counts: dict[str, int] = {}
    barrier_family_mismatch_counts: dict[str, int] = {}
    repeated_mismatch_case_counts: dict[str, int] = {}
    repeated_mismatch_case_delta_sums: dict[str, float] = {}
    aligned_rows = 0
    mismatch_rows = 0
    unknown_rows = 0
    positive_mismatch_rows = 0
    negative_mismatch_rows = 0
    neutral_mismatch_rows = 0
    eligible_rows = 0
    loss_avoided_values: list[float] = []
    profit_missed_values: list[float] = []
    wait_value_values: list[float] = []
    counterfactual_cost_delta_values: list[float] = []
    counterfactual_positive_values: list[float] = []
    counterfactual_negative_values: list[float] = []
    label_distribution_counts: dict[str, dict[str, int]] = {
        "strict": {},
        "usable": {},
        "combined": {},
    }
    symbol_label_distribution: dict[str, dict[str, dict[str, int]]] = {}
    scene_label_distribution: dict[str, dict[str, dict[str, int]]] = {}
    barrier_family_label_distribution: dict[str, dict[str, dict[str, int]]] = {}
    blocking_bias_label_distribution: dict[str, dict[str, dict[str, int]]] = {}
    cost_values_by_bucket: dict[str, dict[str, list[float]]] = {
        "strict": {"loss_avoided_r": [], "profit_missed_r": [], "wait_value_r": []},
        "usable": {"loss_avoided_r": [], "profit_missed_r": [], "wait_value_r": []},
        "combined": {"loss_avoided_r": [], "profit_missed_r": [], "wait_value_r": []},
    }
    cost_values_by_label: dict[str, dict[str, list[float]]] = {}
    bias_recovery_candidate_counts: dict[str, int] = {}
    bias_recovery_primary_label_counts: dict[str, int] = {}
    bias_recovery_activated_reason_counts: dict[str, int] = {}
    bias_recovery_candidate_counts_by_bucket: dict[str, dict[str, int]] = {
        "strict": {},
        "usable": {},
        "skip": {},
    }
    wait_family_counts: dict[str, int] = {}
    wait_subtype_counts: dict[str, int] = {}
    wait_usage_bucket_counts: dict[str, int] = {}
    wait_family_counts_by_usage_bucket: dict[str, dict[str, int]] = {}
    wait_subtype_counts_by_usage_bucket: dict[str, dict[str, int]] = {}
    wait_family_by_barrier_label: dict[str, dict[str, int]] = {}
    wait_family_by_scene_family: dict[str, dict[str, int]] = {}
    wait_family_by_symbol: dict[str, dict[str, int]] = {}
    correct_wait_blocking_reason_counts: dict[str, int] = {}
    correct_wait_scope_rows = 0
    correct_wait_effective_wait_block_rows = 0
    correct_wait_strong_entry_gain_rows = 0
    correct_wait_continuation_support_rows = 0
    correct_wait_wait_value_support_rows = 0
    correct_wait_timing_candidate_rows = 0
    correct_wait_wait_value_candidate_rows = 0
    correct_wait_labeled_rows = 0
    correct_wait_competing_label_rows = 0
    correct_wait_better_entry_values: list[float] = []
    correct_wait_wait_value_values: list[float] = []
    correct_wait_later_continuation_values: list[float] = []
    for raw_row in bridged_rows:
        bridged_row = _as_mapping(raw_row)
        outcome = _as_mapping(bridged_row.get("barrier_outcome_bridge_v1"))
        bridge = _as_mapping(bridged_row.get("barrier_state25_runtime_bridge_v1"))
        label = _to_str(outcome.get("barrier_outcome_label", "")).lower()
        confidence = _to_str(outcome.get("barrier_label_confidence", "")).lower()
        context = _to_str(outcome.get("barrier_anchor_context", "")).lower()
        skip_reason = _to_str(outcome.get("skip_reason", "")).lower()
        actual_family = _to_str(outcome.get("actual_engine_action_family", "")).lower()
        recommended_family = _to_str(outcome.get("barrier_recommended_family", "")).lower()
        recommended_action_family = _to_str(
            outcome.get("recommended_action_family", _recommended_action_family(recommended_family)),
            "observe_only",
        ).lower()
        wait_outcome = _as_mapping(
            outcome.get("wait_outcome_v1") or {
                "wait_outcome_family": outcome.get("wait_outcome_family", ""),
                "wait_outcome_subtype": outcome.get("wait_outcome_subtype", ""),
                "wait_outcome_usage_bucket": outcome.get("wait_outcome_usage_bucket", ""),
            }
        )
        wait_family = _to_str(wait_outcome.get("wait_outcome_family", ""), "").lower()
        wait_subtype = _to_str(wait_outcome.get("wait_outcome_subtype", ""), "").lower()
        wait_usage_bucket = _to_str(wait_outcome.get("wait_outcome_usage_bucket", ""), "").lower()
        normalized_recommended_detail_family_v2 = _to_str(
            outcome.get("normalized_recommended_detail_family_v2", ""),
            "",
        ).lower()
        normalized_recommended_action_family_v2 = _to_str(
            outcome.get("normalized_recommended_action_family_v2", ""),
            recommended_action_family or "observe_only",
        ).lower()
        bias_recovery = _as_mapping(outcome.get("bias_recovery_v1"))
        correct_wait_diagnostic = _as_mapping(outcome.get("correct_wait_diagnostic_v1"))
        counterfactual_outcome_family = _to_str(outcome.get("counterfactual_outcome_family", "")).lower()
        counterfactual_cost_delta_r = _to_float(outcome.get("counterfactual_cost_delta_r"), 0.0)
        drift_status = _to_str(
            outcome.get(
                "drift_status",
                _drift_status(
                    actual_engine_action_family=actual_family,
                    barrier_recommended_family=recommended_family,
                ),
            ),
            "unknown",
        ).lower()
        drift_status_v2 = _to_str(
            outcome.get(
                "drift_status_v2",
                _drift_status_v2(
                    actual_engine_action_family=actual_family,
                    normalized_recommended_action_family_v2=normalized_recommended_action_family_v2,
                ),
            ),
            "unknown",
        ).lower()
        drift_cost_direction = _to_str(
            outcome.get("drift_cost_direction", _drift_cost_direction(counterfactual_cost_delta_r)),
            "neutral",
        ).lower()
        drift_pair_key = _to_str(
            outcome.get(
                "drift_pair_key",
                f"{actual_family or 'unknown'}->{recommended_action_family or 'unknown'}",
            ),
            "",
        ).lower()
        drift_pair_key_v2 = _to_str(
            outcome.get(
                "drift_pair_key_v2",
                f"{actual_family or 'unknown'}->{normalized_recommended_action_family_v2 or 'unknown'}",
            ),
            "",
        ).lower()
        coverage_bucket = _to_str(
            outcome.get("coverage_bucket", _coverage_bucket(label=label, confidence=confidence)),
            "skip",
        ).lower()
        input_trace = _as_mapping(outcome.get("barrier_input_trace_v1"))
        if not input_trace:
            input_trace = _as_mapping(bridge.get("barrier_input_trace_v1"))
        runtime_summary = _as_mapping(outcome.get("barrier_runtime_summary_v1"))
        if not runtime_summary:
            runtime_summary = _as_mapping(bridge.get("barrier_runtime_summary_v1"))
        symbol = _to_str(bridged_row.get("symbol", "")).upper() or "UNKNOWN"
        scene_family = _to_str(input_trace.get("state25_label", ""), "unknown").lower() or "unknown"
        barrier_family = (
            _to_str(
                outcome.get("barrier_primary_component", "")
                or runtime_summary.get("top_component", "")
                or runtime_summary.get("blocking_bias", ""),
                "unknown",
            ).lower()
            or "unknown"
        )
        blocking_bias = (
            _to_str(outcome.get("blocking_bias", "") or runtime_summary.get("blocking_bias", ""), "unknown").lower()
            or "unknown"
        )
        loss_avoided_r = _to_float(outcome.get("barrier_cost_loss_avoided_r"), 0.0)
        profit_missed_r = _to_float(outcome.get("barrier_cost_profit_missed_r"), 0.0)
        wait_value_r = _to_float(outcome.get("barrier_cost_wait_value_r"), 0.0)
        if label:
            label_counts[label] = int(label_counts.get(label, 0)) + 1
        if bool(correct_wait_diagnostic.get("candidate_scope_row", False)):
            correct_wait_scope_rows += 1
            correct_wait_better_entry_values.append(_to_float(correct_wait_diagnostic.get("better_entry_gain_6"), 0.0))
            correct_wait_wait_value_values.append(_to_float(correct_wait_diagnostic.get("wait_value_r"), 0.0))
            correct_wait_later_continuation_values.append(_to_float(correct_wait_diagnostic.get("later_continuation_f_6"), 0.0))
        if bool(correct_wait_diagnostic.get("effective_wait_block", False)):
            correct_wait_effective_wait_block_rows += 1
        if bool(correct_wait_diagnostic.get("strong_entry_gain", False)):
            correct_wait_strong_entry_gain_rows += 1
        if bool(correct_wait_diagnostic.get("continuation_support", False)):
            correct_wait_continuation_support_rows += 1
        if bool(correct_wait_diagnostic.get("wait_value_support", False)):
            correct_wait_wait_value_support_rows += 1
        if bool(correct_wait_diagnostic.get("timing_candidate", False)):
            correct_wait_timing_candidate_rows += 1
        if bool(correct_wait_diagnostic.get("wait_value_candidate", False)):
            correct_wait_wait_value_candidate_rows += 1
        if bool(correct_wait_diagnostic.get("labeled_correct_wait", False)):
            correct_wait_labeled_rows += 1
        blocking_reason = _to_str(correct_wait_diagnostic.get("blocking_reason", ""), "").lower()
        if blocking_reason:
            correct_wait_blocking_reason_counts[blocking_reason] = int(
                correct_wait_blocking_reason_counts.get(blocking_reason, 0)
            ) + 1
        if blocking_reason.startswith("competing_label:"):
            correct_wait_competing_label_rows += 1
        for candidate_key in (
            "missed_profit_strict_candidate",
            "missed_profit_weak_candidate",
            "overblock_boundary_candidate",
            "correct_wait_timing_candidate",
            "correct_wait_wait_value_candidate",
            "relief_success_weak_candidate",
            "relief_failure_weak_candidate",
        ):
            if bool(bias_recovery.get(candidate_key, False)):
                bias_recovery_candidate_counts[candidate_key] = int(
                    bias_recovery_candidate_counts.get(candidate_key, 0)
                ) + 1
                bucket_counts = bias_recovery_candidate_counts_by_bucket.setdefault(
                    coverage_bucket or "skip",
                    {},
                )
                bucket_counts[candidate_key] = int(bucket_counts.get(candidate_key, 0)) + 1
        primary_recovery_label = _to_str(bias_recovery.get("primary_candidate_label", ""), "").lower()
        if primary_recovery_label:
            bias_recovery_primary_label_counts[primary_recovery_label] = int(
                bias_recovery_primary_label_counts.get(primary_recovery_label, 0)
            ) + 1
        recovery_reason = _to_str(outcome.get("weak_candidate_reason", ""), "").lower()
        if recovery_reason.startswith("soft_") and recovery_reason.endswith("_recovery"):
            bias_recovery_activated_reason_counts[recovery_reason] = int(
                bias_recovery_activated_reason_counts.get(recovery_reason, 0)
            ) + 1
        if confidence:
            confidence_counts[confidence] = int(confidence_counts.get(confidence, 0)) + 1
        if context:
            anchor_context_counts[context] = int(anchor_context_counts.get(context, 0)) + 1
        if skip_reason:
            skip_reason_counts[skip_reason] = int(skip_reason_counts.get(skip_reason, 0)) + 1
        if actual_family:
            actual_engine_action_family_counts[actual_family] = int(actual_engine_action_family_counts.get(actual_family, 0)) + 1
        if recommended_family:
            barrier_recommended_family_counts[recommended_family] = int(barrier_recommended_family_counts.get(recommended_family, 0)) + 1
        if recommended_action_family:
            recommended_action_family_counts[recommended_action_family] = int(
                recommended_action_family_counts.get(recommended_action_family, 0)
            ) + 1
        if wait_family:
            _increment_count(wait_family_counts, wait_family)
            _increment_group_count(
                wait_family_counts_by_usage_bucket,
                group=wait_usage_bucket or "unclassified",
                key=wait_family,
            )
            _increment_group_count(
                wait_family_by_barrier_label,
                group=label or "unlabeled",
                key=wait_family,
            )
            _increment_group_count(
                wait_family_by_scene_family,
                group=scene_family,
                key=wait_family,
            )
            _increment_group_count(
                wait_family_by_symbol,
                group=symbol,
                key=wait_family,
            )
        if wait_subtype:
            _increment_count(wait_subtype_counts, wait_subtype)
            _increment_group_count(
                wait_subtype_counts_by_usage_bucket,
                group=wait_usage_bucket or "unclassified",
                key=wait_subtype,
            )
        if wait_usage_bucket:
            _increment_count(wait_usage_bucket_counts, wait_usage_bucket)
        if normalized_recommended_detail_family_v2:
            normalized_recommended_detail_family_counts_v2[normalized_recommended_detail_family_v2] = int(
                normalized_recommended_detail_family_counts_v2.get(normalized_recommended_detail_family_v2, 0)
            ) + 1
        if normalized_recommended_action_family_v2:
            normalized_recommended_action_family_counts_v2[normalized_recommended_action_family_v2] = int(
                normalized_recommended_action_family_counts_v2.get(normalized_recommended_action_family_v2, 0)
            ) + 1
        if counterfactual_outcome_family:
            counterfactual_outcome_family_counts[counterfactual_outcome_family] = int(
                counterfactual_outcome_family_counts.get(counterfactual_outcome_family, 0)
            ) + 1
        if actual_family or recommended_family:
            pair_key = f"{actual_family or 'unknown'}->{recommended_family or 'unknown'}"
            actual_vs_recommended_counts[pair_key] = int(actual_vs_recommended_counts.get(pair_key, 0)) + 1
        if actual_family or recommended_action_family:
            normalized_pair_key = f"{actual_family or 'unknown'}->{recommended_action_family or 'unknown'}"
            normalized_actual_vs_target_action_counts[normalized_pair_key] = int(
                normalized_actual_vs_target_action_counts.get(normalized_pair_key, 0)
            ) + 1
        if actual_family or normalized_recommended_action_family_v2:
            normalized_pair_key_v2 = f"{actual_family or 'unknown'}->{normalized_recommended_action_family_v2 or 'unknown'}"
            normalized_actual_vs_target_action_counts_v2[normalized_pair_key_v2] = int(
                normalized_actual_vs_target_action_counts_v2.get(normalized_pair_key_v2, 0)
            ) + 1
        if drift_status:
            drift_alignment_counts[drift_status] = int(drift_alignment_counts.get(drift_status, 0)) + 1
        if drift_status_v2:
            drift_alignment_counts_v2[drift_status_v2] = int(drift_alignment_counts_v2.get(drift_status_v2, 0)) + 1
        if drift_status == "aligned":
            aligned_rows += 1
        elif drift_status == "mismatch":
            mismatch_rows += 1
            mismatch_action_pair_counts[drift_pair_key] = int(mismatch_action_pair_counts.get(drift_pair_key, 0)) + 1
            mismatch_action_pair_delta_sums[drift_pair_key] = float(
                mismatch_action_pair_delta_sums.get(drift_pair_key, 0.0)
            ) + float(counterfactual_cost_delta_r)
            symbol_mismatch_counts[symbol] = int(symbol_mismatch_counts.get(symbol, 0)) + 1
            scene_family_mismatch_counts[scene_family] = int(scene_family_mismatch_counts.get(scene_family, 0)) + 1
            barrier_family_mismatch_counts[barrier_family] = int(barrier_family_mismatch_counts.get(barrier_family, 0)) + 1
            repeated_case_key = f"{scene_family}|{barrier_family}|{drift_pair_key}"
            repeated_mismatch_case_counts[repeated_case_key] = int(repeated_mismatch_case_counts.get(repeated_case_key, 0)) + 1
            repeated_mismatch_case_delta_sums[repeated_case_key] = float(
                repeated_mismatch_case_delta_sums.get(repeated_case_key, 0.0)
            ) + float(counterfactual_cost_delta_r)
            if drift_cost_direction == "positive":
                positive_mismatch_rows += 1
                positive_mismatch_pair_counts[drift_pair_key] = int(positive_mismatch_pair_counts.get(drift_pair_key, 0)) + 1
                positive_mismatch_pair_delta_sums[drift_pair_key] = float(
                    positive_mismatch_pair_delta_sums.get(drift_pair_key, 0.0)
                ) + float(counterfactual_cost_delta_r)
            elif drift_cost_direction == "negative":
                negative_mismatch_rows += 1
                negative_mismatch_pair_counts[drift_pair_key] = int(negative_mismatch_pair_counts.get(drift_pair_key, 0)) + 1
                negative_mismatch_pair_delta_sums[drift_pair_key] = float(
                    negative_mismatch_pair_delta_sums.get(drift_pair_key, 0.0)
                ) + float(counterfactual_cost_delta_r)
            else:
                neutral_mismatch_rows += 1
        else:
            unknown_rows += 1
        if drift_status_v2 == "mismatch":
            mismatch_action_pair_counts_v2[drift_pair_key_v2] = int(mismatch_action_pair_counts_v2.get(drift_pair_key_v2, 0)) + 1
            mismatch_action_pair_delta_sums_v2[drift_pair_key_v2] = float(
                mismatch_action_pair_delta_sums_v2.get(drift_pair_key_v2, 0.0)
            ) + float(counterfactual_cost_delta_r)
        coverage_bucket_counts[coverage_bucket] = int(coverage_bucket_counts.get(coverage_bucket, 0)) + 1
        counterfactual_cost_delta_values.append(float(counterfactual_cost_delta_r))
        if counterfactual_cost_delta_r > 0:
            counterfactual_positive_values.append(float(counterfactual_cost_delta_r))
        elif counterfactual_cost_delta_r < 0:
            counterfactual_negative_values.append(float(counterfactual_cost_delta_r))
        if label and coverage_bucket in {"strict", "usable"}:
            _increment_count(label_distribution_counts[coverage_bucket], label)
            _increment_count(label_distribution_counts["combined"], label)
            _increment_nested_bucket_label(
                symbol_label_distribution,
                group=symbol,
                bucket=coverage_bucket,
                label=label,
            )
            _increment_nested_bucket_label(
                symbol_label_distribution,
                group=symbol,
                bucket="combined",
                label=label,
            )
            _increment_nested_bucket_label(
                scene_label_distribution,
                group=scene_family,
                bucket=coverage_bucket,
                label=label,
            )
            _increment_nested_bucket_label(
                scene_label_distribution,
                group=scene_family,
                bucket="combined",
                label=label,
            )
            _increment_nested_bucket_label(
                barrier_family_label_distribution,
                group=barrier_family,
                bucket=coverage_bucket,
                label=label,
            )
            _increment_nested_bucket_label(
                barrier_family_label_distribution,
                group=barrier_family,
                bucket="combined",
                label=label,
            )
            _increment_nested_bucket_label(
                blocking_bias_label_distribution,
                group=blocking_bias,
                bucket=coverage_bucket,
                label=label,
            )
            _increment_nested_bucket_label(
                blocking_bias_label_distribution,
                group=blocking_bias,
                bucket="combined",
                label=label,
            )
            cost_values_by_bucket[coverage_bucket]["loss_avoided_r"].append(loss_avoided_r)
            cost_values_by_bucket[coverage_bucket]["profit_missed_r"].append(profit_missed_r)
            cost_values_by_bucket[coverage_bucket]["wait_value_r"].append(wait_value_r)
            cost_values_by_bucket["combined"]["loss_avoided_r"].append(loss_avoided_r)
            cost_values_by_bucket["combined"]["profit_missed_r"].append(profit_missed_r)
            cost_values_by_bucket["combined"]["wait_value_r"].append(wait_value_r)
            label_cost_values = cost_values_by_label.setdefault(
                label,
                {"loss_avoided_r": [], "profit_missed_r": [], "wait_value_r": []},
            )
            label_cost_values["loss_avoided_r"].append(loss_avoided_r)
            label_cost_values["profit_missed_r"].append(profit_missed_r)
            label_cost_values["wait_value_r"].append(wait_value_r)
        if coverage_bucket == "strict":
            eligible_rows += 1
            loss_avoided_values.append(loss_avoided_r)
            profit_missed_values.append(profit_missed_r)
            wait_value_values.append(wait_value_r)

    labeled_total = sum(label_counts.values())
    total_anchor_rows = len(bridged_rows)
    strict_rows = int(coverage_bucket_counts.get("strict", 0))
    usable_rows = int(coverage_bucket_counts.get("usable", 0))
    skip_rows = int(coverage_bucket_counts.get("skip", 0))
    pre_context_skip_rows = sum(
        int(_to_int(value, 0))
        for key, value in skip_reason_counts.items()
        if _to_str(key, "").lower().startswith("pre_context_skip:")
    )
    semantic_anchor_rows = max(total_anchor_rows - pre_context_skip_rows, 0)
    semantic_skip_rows = max(skip_rows - pre_context_skip_rows, 0)
    summary = {
        "raw_bridge_candidate_count": len([row for row in merged_rows if _row_has_bridge_candidate(row)]),
        "bridged_row_count": total_anchor_rows,
        "total_anchor_rows": total_anchor_rows,
        "pre_context_skip_rows": pre_context_skip_rows,
        "semantic_anchor_rows": semantic_anchor_rows,
        "labeled_rows": int(labeled_total),
        "eligible_rows": int(eligible_rows),
        "strict_rows": strict_rows,
        "usable_rows": usable_rows,
        "skip_rows": skip_rows,
        "semantic_skip_rows": semantic_skip_rows,
        "overblock_ratio": round(float(label_counts.get("overblock", 0)) / max(labeled_total, 1), 4),
        "avoided_loss_rate": round(float(label_counts.get("avoided_loss", 0)) / max(labeled_total, 1), 4),
        "missed_profit_rate": round(float(label_counts.get("missed_profit", 0)) / max(labeled_total, 1), 4),
        "correct_wait_rate": round(float(label_counts.get("correct_wait", 0)) / max(labeled_total, 1), 4),
        "relief_failure_rate": round(float(label_counts.get("relief_failure", 0)) / max(labeled_total, 1), 4),
        "loss_avoided_r_mean": round(_safe_mean(loss_avoided_values), 4),
        "profit_missed_r_mean": round(_safe_mean(profit_missed_values), 4),
        "wait_value_r_mean": round(_safe_mean(wait_value_values), 4),
        "counterfactual_cost_delta_r_mean": round(_safe_mean(counterfactual_cost_delta_values), 4),
        "counterfactual_positive_rate": round(float(len(counterfactual_positive_values)) / max(total_anchor_rows, 1), 4),
        "counterfactual_negative_rate": round(float(len(counterfactual_negative_values)) / max(total_anchor_rows, 1), 4),
    }
    coverage = {
        "label_counts": dict(sorted(label_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "coverage_bucket_counts": dict(sorted(coverage_bucket_counts.items())),
        "anchor_context_counts": dict(sorted(anchor_context_counts.items())),
        "skip_reason_counts": dict(sorted(skip_reason_counts.items())),
        "dashboard": {
            "total_anchor_rows": total_anchor_rows,
            "pre_context_skip_rows": pre_context_skip_rows,
            "semantic_anchor_rows": semantic_anchor_rows,
            "labeled_rows": int(labeled_total),
            "strict_rows": strict_rows,
            "usable_rows": usable_rows,
            "skip_rows": skip_rows,
            "semantic_skip_rows": semantic_skip_rows,
            "strict_share": round(float(strict_rows) / max(total_anchor_rows, 1), 4),
            "usable_share": round(float(usable_rows) / max(total_anchor_rows, 1), 4),
            "skip_share": round(float(skip_rows) / max(total_anchor_rows, 1), 4),
            "strict_share_ex_pre_context": round(float(strict_rows) / max(semantic_anchor_rows, 1), 4),
            "usable_share_ex_pre_context": round(float(usable_rows) / max(semantic_anchor_rows, 1), 4),
            "covered_share_ex_pre_context": round(
                float(strict_rows + usable_rows) / max(semantic_anchor_rows, 1),
                4,
            ),
            "semantic_skip_share_ex_pre_context": round(float(semantic_skip_rows) / max(semantic_anchor_rows, 1), 4),
            "top_skip_reasons": _top_count_items(skip_reason_counts, limit=3),
        },
        "usage_policy_v1": _coverage_policy_v1(),
    }
    counterfactual_audit = {
        "actual_engine_action_family_counts": dict(sorted(actual_engine_action_family_counts.items())),
        "barrier_recommended_family_counts": dict(sorted(barrier_recommended_family_counts.items())),
        "counterfactual_outcome_family_counts": dict(sorted(counterfactual_outcome_family_counts.items())),
        "actual_vs_recommended_counts": dict(sorted(actual_vs_recommended_counts.items())),
        "counterfactual_cost_delta_r_mean": round(_safe_mean(counterfactual_cost_delta_values), 4),
        "counterfactual_positive_r_mean": round(_safe_mean(counterfactual_positive_values), 4),
        "counterfactual_negative_r_mean": round(_safe_mean(counterfactual_negative_values), 4),
        "top_actual_vs_recommended": _top_count_items(actual_vs_recommended_counts, limit=5),
        "top_counterfactual_outcomes": _top_count_items(counterfactual_outcome_family_counts, limit=5),
    }
    drift_audit = {
        "aligned_rows": aligned_rows,
        "mismatch_rows": mismatch_rows,
        "unknown_rows": unknown_rows,
        "mismatch_rate": round(float(mismatch_rows) / max(semantic_anchor_rows, 1), 4),
        "mismatch_rate_v2": round(
            float(sum(int(v) for v in mismatch_action_pair_counts_v2.values())) / max(semantic_anchor_rows, 1),
            4,
        ),
        "positive_mismatch_rows": positive_mismatch_rows,
        "negative_mismatch_rows": negative_mismatch_rows,
        "neutral_mismatch_rows": neutral_mismatch_rows,
        "alignment_counts": dict(sorted(drift_alignment_counts.items())),
        "alignment_counts_v2": dict(sorted(drift_alignment_counts_v2.items())),
        "normalized_actual_vs_target_action_counts": dict(sorted(normalized_actual_vs_target_action_counts.items())),
        "normalized_actual_vs_target_action_counts_v2": dict(sorted(normalized_actual_vs_target_action_counts_v2.items())),
        "normalized_recommended_detail_family_counts_v2": dict(sorted(normalized_recommended_detail_family_counts_v2.items())),
        "normalized_recommended_action_family_counts_v2": dict(sorted(normalized_recommended_action_family_counts_v2.items())),
        "mismatch_action_pair_counts": dict(sorted(mismatch_action_pair_counts.items())),
        "mismatch_action_pair_counts_v2": dict(sorted(mismatch_action_pair_counts_v2.items())),
        "symbol_mismatch_counts": dict(sorted(symbol_mismatch_counts.items())),
        "scene_family_mismatch_counts": dict(sorted(scene_family_mismatch_counts.items())),
        "barrier_family_mismatch_counts": dict(sorted(barrier_family_mismatch_counts.items())),
        "top_mismatch_action_pairs": _top_count_mean_items(
            mismatch_action_pair_counts,
            mismatch_action_pair_delta_sums,
            limit=5,
        ),
        "top_mismatch_action_pairs_v2": _top_count_mean_items(
            mismatch_action_pair_counts_v2,
            mismatch_action_pair_delta_sums_v2,
            limit=5,
        ),
        "top_positive_mismatch_pairs": _top_count_mean_items(
            positive_mismatch_pair_counts,
            positive_mismatch_pair_delta_sums,
            limit=5,
        ),
        "top_negative_mismatch_pairs": _top_count_mean_items(
            negative_mismatch_pair_counts,
            negative_mismatch_pair_delta_sums,
            limit=5,
        ),
        "top_symbol_mismatch": _top_count_items(symbol_mismatch_counts, limit=5),
        "top_scene_family_mismatch": _top_count_items(scene_family_mismatch_counts, limit=5),
        "top_barrier_family_mismatch": _top_count_items(barrier_family_mismatch_counts, limit=5),
        "top_repeated_mismatch_cases": _top_count_mean_items(
            repeated_mismatch_case_counts,
            repeated_mismatch_case_delta_sums,
            limit=5,
        ),
    }
    bias_baseline_v1 = {
        "contract_version": BARRIER_BIAS_BASELINE_VERSION,
        "label_distribution": {
            "strict": _distribution_summary(label_distribution_counts.get("strict")),
            "usable": _distribution_summary(label_distribution_counts.get("usable")),
            "combined": _distribution_summary(label_distribution_counts.get("combined")),
            "by_symbol": _group_distribution_summary(symbol_label_distribution),
            "by_scene_family": _group_distribution_summary(scene_label_distribution),
            "by_barrier_family": _group_distribution_summary(barrier_family_label_distribution),
            "by_blocking_bias": _group_distribution_summary(blocking_bias_label_distribution),
        },
        "cost_balance": {
            "strict": _cost_balance_summary(cost_values_by_bucket.get("strict")),
            "usable": _cost_balance_summary(cost_values_by_bucket.get("usable")),
            "combined": _cost_balance_summary(cost_values_by_bucket.get("combined")),
            "by_label": {
                key: _cost_balance_summary(value)
                for key, value in sorted(cost_values_by_label.items())
            },
        },
        "drift_baseline": {
            "mismatch_rate": round(float(mismatch_rows) / max(semantic_anchor_rows, 1), 4),
            "mismatch_rate_v2": round(
                float(sum(int(v) for v in mismatch_action_pair_counts_v2.values())) / max(semantic_anchor_rows, 1),
                4,
            ),
            "top_normalized_action_pairs": _top_count_items(
                normalized_actual_vs_target_action_counts,
                limit=5,
            ),
            "top_normalized_action_pairs_v2": _top_count_items(
                normalized_actual_vs_target_action_counts_v2,
                limit=5,
            ),
            "top_recommended_action_families": _top_count_items(
                recommended_action_family_counts,
                limit=5,
            ),
            "top_recommended_detail_families_v2": _top_count_items(
                normalized_recommended_detail_family_counts_v2,
                limit=5,
            ),
            "top_mismatch_action_pairs": _top_count_mean_items(
                mismatch_action_pair_counts,
                mismatch_action_pair_delta_sums,
                limit=5,
            ),
            "top_mismatch_action_pairs_v2": _top_count_mean_items(
                mismatch_action_pair_counts_v2,
                mismatch_action_pair_delta_sums_v2,
                limit=5,
            ),
        },
        "skip_baseline": {
            "pre_context_skip_rows": pre_context_skip_rows,
            "semantic_skip_rows": semantic_skip_rows,
            "top_skip_reasons": _top_count_items(skip_reason_counts, limit=5),
        },
    }
    bias_recovery_v1 = {
        "contract_version": BARRIER_BIAS_RECOVERY_VERSION,
        "candidate_counts": dict(sorted(bias_recovery_candidate_counts.items())),
        "candidate_counts_by_bucket": {
            key: dict(sorted(value.items()))
            for key, value in sorted(bias_recovery_candidate_counts_by_bucket.items())
        },
        "primary_candidate_label_counts": dict(sorted(bias_recovery_primary_label_counts.items())),
        "activated_recovery_reason_counts": dict(sorted(bias_recovery_activated_reason_counts.items())),
        "top_candidate_counts": _top_count_items(bias_recovery_candidate_counts, limit=5),
        "top_primary_candidate_labels": _top_count_items(bias_recovery_primary_label_counts, limit=5),
        "top_activated_recovery_reasons": _top_count_items(bias_recovery_activated_reason_counts, limit=5),
    }
    wait_family_v1 = {
        "contract_version": WAIT_OUTCOME_VERSION,
        "family_distribution": {
            "total_rows": int(sum(wait_family_counts.values())),
            "counts": dict(sorted(wait_family_counts.items())),
            "top_families": _top_count_items(wait_family_counts, limit=7),
            "by_usage_bucket": {
                key: _distribution_summary(value)
                for key, value in sorted(wait_family_counts_by_usage_bucket.items())
            },
        },
        "subtype_distribution": {
            "total_rows": int(sum(wait_subtype_counts.values())),
            "counts": dict(sorted(wait_subtype_counts.items())),
            "top_subtypes": _top_count_items(wait_subtype_counts, limit=9),
            "by_usage_bucket": {
                key: _distribution_summary(value)
                for key, value in sorted(wait_subtype_counts_by_usage_bucket.items())
            },
        },
        "usage_bucket_counts": dict(sorted(wait_usage_bucket_counts.items())),
        "by_barrier_label": {
            key: _distribution_summary(value)
            for key, value in sorted(wait_family_by_barrier_label.items())
        },
        "by_scene_family": {
            key: _distribution_summary(value)
            for key, value in sorted(wait_family_by_scene_family.items())
        },
        "by_symbol": {
            key: _distribution_summary(value)
            for key, value in sorted(wait_family_by_symbol.items())
        },
    }
    correct_wait_diagnostic_v1 = {
        "contract_version": CORRECT_WAIT_DIAGNOSTIC_VERSION,
        "scope_rows": correct_wait_scope_rows,
        "effective_wait_block_rows": correct_wait_effective_wait_block_rows,
        "strong_entry_gain_rows": correct_wait_strong_entry_gain_rows,
        "continuation_support_rows": correct_wait_continuation_support_rows,
        "wait_value_support_rows": correct_wait_wait_value_support_rows,
        "timing_candidate_rows": correct_wait_timing_candidate_rows,
        "wait_value_candidate_rows": correct_wait_wait_value_candidate_rows,
        "labeled_correct_wait_rows": correct_wait_labeled_rows,
        "candidate_but_not_labeled_rows": max(
            correct_wait_timing_candidate_rows + correct_wait_wait_value_candidate_rows - correct_wait_labeled_rows,
            0,
        ),
        "competing_label_rows": correct_wait_competing_label_rows,
        "top_blocking_reasons": _top_count_items(correct_wait_blocking_reason_counts, limit=7),
        "mean_better_entry_gain_6": round(_safe_mean(correct_wait_better_entry_values), 4),
        "mean_wait_value_r": round(_safe_mean(correct_wait_wait_value_values), 4),
        "mean_later_continuation_f_6": round(_safe_mean(correct_wait_later_continuation_values), 4),
    }
    correct_wait_casebook_v1 = _build_correct_wait_casebook_v1(bridged_rows)
    timing_edge_absent_casebook_v1 = _build_timing_edge_absent_casebook_v1(bridged_rows)
    readiness_gate = _build_barrier_readiness_gate_v1(
        summary=summary,
        coverage=coverage,
        counterfactual_audit=counterfactual_audit,
        drift_audit=drift_audit,
        runtime_status=runtime_status,
    )
    return {
        "contract_version": BARRIER_OUTCOME_BRIDGE_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope_freeze_contract": BARRIER_SCOPE_FREEZE_CONTRACT_V1,
        "summary": summary,
        "coverage": coverage,
        "counterfactual_audit": counterfactual_audit,
        "drift_audit": drift_audit,
        "bias_baseline_v1": bias_baseline_v1,
        "bias_recovery_v1": bias_recovery_v1,
        "wait_family_v1": wait_family_v1,
        "correct_wait_diagnostic_v1": correct_wait_diagnostic_v1,
        "correct_wait_casebook_v1": correct_wait_casebook_v1,
        "timing_edge_absent_casebook_v1": timing_edge_absent_casebook_v1,
        "readiness_gate": readiness_gate,
        "rows": bridged_rows,
    }


def render_barrier_outcome_bridge_markdown(report: Mapping[str, Any] | None = None) -> str:
    payload = _as_mapping(report)
    summary = _as_mapping(payload.get("summary"))
    coverage = _as_mapping(payload.get("coverage"))
    counterfactual_audit = _as_mapping(payload.get("counterfactual_audit"))
    drift_audit = _as_mapping(payload.get("drift_audit"))
    bias_baseline = _as_mapping(payload.get("bias_baseline_v1"))
    bias_recovery = _as_mapping(payload.get("bias_recovery_v1"))
    wait_family = _as_mapping(payload.get("wait_family_v1"))
    correct_wait_diagnostic = _as_mapping(payload.get("correct_wait_diagnostic_v1"))
    correct_wait_casebook = _as_mapping(payload.get("correct_wait_casebook_v1"))
    timing_edge_absent_casebook = _as_mapping(payload.get("timing_edge_absent_casebook_v1"))
    readiness_gate = _as_mapping(payload.get("readiness_gate"))
    lines = [
        "# Barrier Outcome Bridge Report",
        "",
        f"- raw_bridge_candidate_count: {int(_to_int(summary.get('raw_bridge_candidate_count'), 0))}",
        f"- bridged_row_count: {int(_to_int(summary.get('bridged_row_count'), 0))}",
        f"- pre_context_skip_rows: {int(_to_int(summary.get('pre_context_skip_rows'), 0))}",
        f"- semantic_anchor_rows: {int(_to_int(summary.get('semantic_anchor_rows'), 0))}",
        f"- strict_rows: {int(_to_int(summary.get('strict_rows'), 0))}",
        f"- usable_rows: {int(_to_int(summary.get('usable_rows'), 0))}",
        f"- skip_rows: {int(_to_int(summary.get('skip_rows'), 0))}",
        f"- semantic_skip_rows: {int(_to_int(summary.get('semantic_skip_rows'), 0))}",
        f"- labeled_rows: {int(_to_int(summary.get('labeled_rows'), 0))}",
        f"- eligible_rows: {int(_to_int(summary.get('eligible_rows'), 0))}",
        f"- overblock_ratio: {float(_to_float(summary.get('overblock_ratio'), 0.0)):.4f}",
        f"- avoided_loss_rate: {float(_to_float(summary.get('avoided_loss_rate'), 0.0)):.4f}",
        f"- missed_profit_rate: {float(_to_float(summary.get('missed_profit_rate'), 0.0)):.4f}",
        f"- correct_wait_rate: {float(_to_float(summary.get('correct_wait_rate'), 0.0)):.4f}",
        f"- relief_failure_rate: {float(_to_float(summary.get('relief_failure_rate'), 0.0)):.4f}",
        f"- loss_avoided_r_mean: {float(_to_float(summary.get('loss_avoided_r_mean'), 0.0)):.4f}",
        f"- profit_missed_r_mean: {float(_to_float(summary.get('profit_missed_r_mean'), 0.0)):.4f}",
        f"- wait_value_r_mean: {float(_to_float(summary.get('wait_value_r_mean'), 0.0)):.4f}",
        f"- counterfactual_cost_delta_r_mean: {float(_to_float(summary.get('counterfactual_cost_delta_r_mean'), 0.0)):.4f}",
        f"- counterfactual_positive_rate: {float(_to_float(summary.get('counterfactual_positive_rate'), 0.0)):.4f}",
        f"- counterfactual_negative_rate: {float(_to_float(summary.get('counterfactual_negative_rate'), 0.0)):.4f}",
        "",
        "## Coverage Dashboard",
    ]
    dashboard = _as_mapping(coverage.get("dashboard"))
    lines.extend(
        [
            f"- strict_share: {float(_to_float(dashboard.get('strict_share'), 0.0)):.4f}",
            f"- usable_share: {float(_to_float(dashboard.get('usable_share'), 0.0)):.4f}",
            f"- skip_share: {float(_to_float(dashboard.get('skip_share'), 0.0)):.4f}",
            f"- strict_share_ex_pre_context: {float(_to_float(dashboard.get('strict_share_ex_pre_context'), 0.0)):.4f}",
            f"- usable_share_ex_pre_context: {float(_to_float(dashboard.get('usable_share_ex_pre_context'), 0.0)):.4f}",
            f"- covered_share_ex_pre_context: {float(_to_float(dashboard.get('covered_share_ex_pre_context'), 0.0)):.4f}",
            f"- semantic_skip_share_ex_pre_context: {float(_to_float(dashboard.get('semantic_skip_share_ex_pre_context'), 0.0)):.4f}",
            "",
            "## Top Skip Reasons",
        ]
    )
    top_skip_reasons = dashboard.get("top_skip_reasons", [])
    if not isinstance(top_skip_reasons, list):
        top_skip_reasons = []
    for item in top_skip_reasons:
        mapped = _as_mapping(item)
        lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
    lines.extend(
        [
            "",
            "## Usage Policy",
        ]
    )
    usage_policy = _as_mapping(coverage.get("usage_policy_v1"))
    for key, value in usage_policy.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value)
        lines.append(f"- {key}: {rendered}")
    lines.extend(
        [
            "",
            "## Label Counts",
        ]
    )
    for key, value in sorted(_as_mapping(coverage.get("label_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "## Confidence Counts"])
    for key, value in sorted(_as_mapping(coverage.get("confidence_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "## Anchor Context Counts"])
    for key, value in sorted(_as_mapping(coverage.get("anchor_context_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "## Skip Reason Counts"])
    for key, value in sorted(_as_mapping(coverage.get("skip_reason_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    if bias_baseline:
        label_distribution = _as_mapping(bias_baseline.get("label_distribution"))
        cost_balance = _as_mapping(bias_baseline.get("cost_balance"))
        drift_baseline = _as_mapping(bias_baseline.get("drift_baseline"))
        skip_baseline = _as_mapping(bias_baseline.get("skip_baseline"))
        lines.extend(["", "## Bias Baseline"])
        for bucket in ("strict", "usable", "combined"):
            bucket_payload = _as_mapping(label_distribution.get(bucket))
            lines.extend(["", f"### {bucket.title()} Label Distribution"])
            lines.append(f"- total_rows: {int(_to_int(bucket_payload.get('total_rows'), 0))}")
            for key, value in sorted(_as_mapping(bucket_payload.get("counts")).items()):
                share = _to_float(_as_mapping(bucket_payload.get("shares")).get(key), 0.0)
                lines.append(f"- {key}: {int(_to_int(value, 0))} (share={share:.4f})")
        lines.extend(["", "### Combined Cost Balance"])
        combined_cost = _as_mapping(cost_balance.get("combined"))
        for metric_key in ("loss_avoided_r", "profit_missed_r", "wait_value_r"):
            metric_payload = _as_mapping(combined_cost.get(metric_key))
            lines.append(
                f"- {metric_key}: mean={float(_to_float(metric_payload.get('mean'), 0.0)):.4f}, "
                f"median={float(_to_float(metric_payload.get('median'), 0.0)):.4f}, "
                f"non_zero_share={float(_to_float(metric_payload.get('non_zero_share'), 0.0)):.4f}"
            )
        lines.extend(["", "### Drift Baseline"])
        lines.append(f"- mismatch_rate: {float(_to_float(drift_baseline.get('mismatch_rate'), 0.0)):.4f}")
        lines.append(f"- mismatch_rate_v2: {float(_to_float(drift_baseline.get('mismatch_rate_v2'), 0.0)):.4f}")
        top_normalized_pairs = drift_baseline.get("top_normalized_action_pairs", [])
        if not isinstance(top_normalized_pairs, list):
            top_normalized_pairs = []
        for item in top_normalized_pairs:
            mapped = _as_mapping(item)
            lines.append(f"- normalized_pair {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
        top_normalized_pairs_v2 = drift_baseline.get("top_normalized_action_pairs_v2", [])
        if not isinstance(top_normalized_pairs_v2, list):
            top_normalized_pairs_v2 = []
        for item in top_normalized_pairs_v2:
            mapped = _as_mapping(item)
            lines.append(f"- normalized_pair_v2 {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
        lines.extend(["", "### Skip Baseline"])
        lines.append(f"- pre_context_skip_rows: {int(_to_int(skip_baseline.get('pre_context_skip_rows'), 0))}")
        lines.append(f"- semantic_skip_rows: {int(_to_int(skip_baseline.get('semantic_skip_rows'), 0))}")
        top_skip_baseline = skip_baseline.get("top_skip_reasons", [])
        if not isinstance(top_skip_baseline, list):
            top_skip_baseline = []
        for item in top_skip_baseline:
            mapped = _as_mapping(item)
            lines.append(f"- skip {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
    if bias_recovery:
        lines.extend(["", "## Bias Recovery"])
        top_candidates = bias_recovery.get("top_candidate_counts", [])
        if not isinstance(top_candidates, list):
            top_candidates = []
        lines.extend(["", "### Top Recovery Candidates"])
        for item in top_candidates:
            mapped = _as_mapping(item)
            lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
        top_primary_labels = bias_recovery.get("top_primary_candidate_labels", [])
        if not isinstance(top_primary_labels, list):
            top_primary_labels = []
        lines.extend(["", "### Top Primary Candidate Labels"])
        for item in top_primary_labels:
            mapped = _as_mapping(item)
            lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
        top_reasons = bias_recovery.get("top_activated_recovery_reasons", [])
        if not isinstance(top_reasons, list):
            top_reasons = []
        lines.extend(["", "### Activated Recovery Reasons"])
        for item in top_reasons:
            mapped = _as_mapping(item)
            lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
    if wait_family:
        family_distribution = _as_mapping(wait_family.get("family_distribution"))
        subtype_distribution = _as_mapping(wait_family.get("subtype_distribution"))
        by_barrier_label = _as_mapping(wait_family.get("by_barrier_label"))
        lines.extend(["", "## Wait Outcome Family"])
        lines.append(f"- total_family_rows: {int(_to_int(family_distribution.get('total_rows'), 0))}")
        for key, value in sorted(_as_mapping(family_distribution.get("counts")).items()):
            lines.append(f"- family {key}: {int(_to_int(value, 0))}")
        lines.extend(["", "### Wait Outcome Subtypes"])
        for key, value in sorted(_as_mapping(subtype_distribution.get("counts")).items()):
            lines.append(f"- subtype {key}: {int(_to_int(value, 0))}")
        lines.extend(["", "### Wait Usage Buckets"])
        for key, value in sorted(_as_mapping(wait_family.get("usage_bucket_counts")).items()):
            lines.append(f"- usage_bucket {key}: {int(_to_int(value, 0))}")
        lines.extend(["", "### Wait Families by Barrier Label"])
        for label_key, distribution in sorted(by_barrier_label.items()):
            distribution_map = _as_mapping(distribution)
            counts = _as_mapping(distribution_map.get("counts"))
            if not counts:
                continue
            rendered = ", ".join(
                f"{name}={int(_to_int(count, 0))}"
                for name, count in sorted(counts.items())
            )
            lines.append(f"- {label_key}: {rendered}")
    if correct_wait_diagnostic:
        lines.extend(["", "## Correct-Wait Diagnostic"])
        for key in (
            "scope_rows",
            "effective_wait_block_rows",
            "strong_entry_gain_rows",
            "continuation_support_rows",
            "wait_value_support_rows",
            "timing_candidate_rows",
            "wait_value_candidate_rows",
            "labeled_correct_wait_rows",
            "candidate_but_not_labeled_rows",
            "competing_label_rows",
        ):
            lines.append(f"- {key}: {int(_to_int(correct_wait_diagnostic.get(key), 0))}")
        for key in ("mean_better_entry_gain_6", "mean_wait_value_r", "mean_later_continuation_f_6"):
            lines.append(f"- {key}: {float(_to_float(correct_wait_diagnostic.get(key), 0.0)):.4f}")
        lines.extend(["", "### Correct-Wait Top Blocking Reasons"])
        top_blockers = correct_wait_diagnostic.get("top_blocking_reasons", [])
        if not isinstance(top_blockers, list):
            top_blockers = []
        for item in top_blockers:
            mapped = _as_mapping(item)
            lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
    if correct_wait_casebook:
        lines.extend(["", "## Correct-Wait Casebook"])
        for key in (
            "loss_avoided_dominates_rows",
            "unique_signatures",
            "effective_wait_block_rows",
            "wait_value_support_rows",
            "continuation_support_rows",
            "zero_entry_gain_rows",
            "small_entry_gain_rows",
        ):
            lines.append(f"- {key}: {int(_to_int(correct_wait_casebook.get(key), 0))}")
        for key in (
            "mean_loss_avoided_r",
            "mean_profit_missed_r",
            "mean_wait_value_r",
            "mean_better_entry_gain_6",
            "mean_later_continuation_f_6",
            "mean_loss_wait_margin_r",
            "mean_loss_profit_margin_r",
        ):
            lines.append(f"- {key}: {float(_to_float(correct_wait_casebook.get(key), 0.0)):.4f}")
        lines.extend(["", "### Correct-Wait Top Signatures"])
        top_signatures = correct_wait_casebook.get("top_signatures", [])
        if not isinstance(top_signatures, list):
            top_signatures = []
        for item in top_signatures:
            mapped = _as_mapping(item)
            signature = _as_mapping(mapped.get("signature"))
            sample = _as_mapping(mapped.get("sample"))
            lines.append(
                "- "
                f"{_to_str(signature.get('scene_family', ''), 'unknown')}"
                f" / {_to_str(signature.get('barrier_family', ''), 'unknown')}"
                f" / {_to_str(signature.get('blocking_bias', ''), 'unknown')}"
                f" / {_to_str(signature.get('recommended_family', ''), 'unknown')}"
                f": {int(_to_int(mapped.get('count', 0), 0))}"
                f" (share={float(_to_float(mapped.get('share'), 0.0)):.4f}, "
                f"loss={float(_to_float(signature.get('loss_avoided_r'), 0.0)):.3f}, "
                f"wait={float(_to_float(signature.get('wait_value_r'), 0.0)):.3f}, "
                f"profit={float(_to_float(signature.get('profit_missed_r'), 0.0)):.3f}, "
                f"entry_gain={float(_to_float(signature.get('better_entry_gain_6'), 0.0)):.3f}, "
                f"later={float(_to_float(signature.get('later_continuation_f_6'), 0.0)):.3f}, "
                f"sample={_to_str(sample.get('symbol', ''), 'UNKNOWN')}@{_to_str(sample.get('time', ''), '')})"
            )
    if timing_edge_absent_casebook:
        lines.extend(["", "## Timing-Edge-Absent Casebook"])
        for key in (
            "timing_edge_absent_rows",
            "unique_signatures",
            "effective_wait_block_rows",
            "wait_value_support_rows",
            "continuation_support_rows",
            "zero_entry_gain_rows",
            "small_entry_gain_rows",
        ):
            lines.append(f"- {key}: {int(_to_int(timing_edge_absent_casebook.get(key), 0))}")
        for key in (
            "mean_loss_avoided_r",
            "mean_profit_missed_r",
            "mean_wait_value_r",
            "mean_better_entry_gain_6",
            "mean_later_continuation_f_6",
            "mean_loss_wait_margin_r",
            "mean_loss_profit_margin_r",
        ):
            lines.append(f"- {key}: {float(_to_float(timing_edge_absent_casebook.get(key), 0.0)):.4f}")
        lines.extend(["", "### Timing-Edge-Absent Top Signatures"])
        timing_top_signatures = timing_edge_absent_casebook.get("top_signatures", [])
        if not isinstance(timing_top_signatures, list):
            timing_top_signatures = []
        for item in timing_top_signatures:
            mapped = _as_mapping(item)
            signature = _as_mapping(mapped.get("signature"))
            sample = _as_mapping(mapped.get("sample"))
            lines.append(
                "- "
                f"{_to_str(signature.get('scene_family', ''), 'unknown')}"
                f" / {_to_str(signature.get('barrier_family', ''), 'unknown')}"
                f" / {_to_str(signature.get('blocking_bias', ''), 'unknown')}"
                f" / {_to_str(signature.get('recommended_family', ''), 'unknown')}"
                f": {int(_to_int(mapped.get('count', 0), 0))}"
                f" (share={float(_to_float(mapped.get('share'), 0.0)):.4f}, "
                f"loss={float(_to_float(signature.get('loss_avoided_r'), 0.0)):.3f}, "
                f"wait={float(_to_float(signature.get('wait_value_r'), 0.0)):.3f}, "
                f"profit={float(_to_float(signature.get('profit_missed_r'), 0.0)):.3f}, "
                f"entry_gain={float(_to_float(signature.get('better_entry_gain_6'), 0.0)):.3f}, "
                f"later={float(_to_float(signature.get('later_continuation_f_6'), 0.0)):.3f}, "
                f"sample={_to_str(sample.get('symbol', ''), 'UNKNOWN')}@{_to_str(sample.get('time', ''), '')})"
            )
        lines.extend(["", "### Timing-Edge-Absent Subtypes"])
        timing_top_subtypes = timing_edge_absent_casebook.get("top_subtypes", [])
        if not isinstance(timing_top_subtypes, list):
            timing_top_subtypes = []
        for item in timing_top_subtypes:
            mapped = _as_mapping(item)
            lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
        subtype_profiles = _as_mapping(timing_edge_absent_casebook.get("subtype_profiles"))
        if subtype_profiles:
            lines.extend(["", "### Timing-Edge-Absent Subtype Profiles"])
            for subtype_key, profile in sorted(subtype_profiles.items()):
                mapped = _as_mapping(profile)
                lines.append(f"- {subtype_key}: {int(_to_int(mapped.get('row_count', 0), 0))}")
                top_labels = mapped.get("top_labels", [])
                if not isinstance(top_labels, list):
                    top_labels = []
                for item in top_labels[:3]:
                    label_item = _as_mapping(item)
                    lines.append(
                        f"  - label {_to_str(label_item.get('key', ''))}: {int(_to_int(label_item.get('count', 0), 0))}"
                    )
                top_reasons = mapped.get("top_weak_reasons", [])
                if not isinstance(top_reasons, list):
                    top_reasons = []
                for item in top_reasons[:2]:
                    reason_item = _as_mapping(item)
                    lines.append(
                        f"  - weak {_to_str(reason_item.get('key', ''))}: {int(_to_int(reason_item.get('count', 0), 0))}"
                    )
    lines.extend(["", "## Counterfactual Audit"])
    for key in (
        "counterfactual_cost_delta_r_mean",
        "counterfactual_positive_r_mean",
        "counterfactual_negative_r_mean",
    ):
        lines.append(f"- {key}: {float(_to_float(counterfactual_audit.get(key), 0.0)):.4f}")
    lines.extend(["", "### Top Actual vs Recommended"])
    top_pairs = counterfactual_audit.get("top_actual_vs_recommended", [])
    if not isinstance(top_pairs, list):
        top_pairs = []
    for item in top_pairs:
        mapped = _as_mapping(item)
        lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
    lines.extend(["", "### Top Counterfactual Outcomes"])
    top_outcomes = counterfactual_audit.get("top_counterfactual_outcomes", [])
    if not isinstance(top_outcomes, list):
        top_outcomes = []
    for item in top_outcomes:
        mapped = _as_mapping(item)
        lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
    lines.extend(["", "### Actual Engine Action Families"])
    for key, value in sorted(_as_mapping(counterfactual_audit.get("actual_engine_action_family_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "### Barrier Recommended Families"])
    for key, value in sorted(_as_mapping(counterfactual_audit.get("barrier_recommended_family_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "### Counterfactual Outcome Families"])
    for key, value in sorted(_as_mapping(counterfactual_audit.get("counterfactual_outcome_family_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "## Drift Audit"])
    for key in (
        "aligned_rows",
        "mismatch_rows",
        "unknown_rows",
        "mismatch_rate",
        "positive_mismatch_rows",
        "negative_mismatch_rows",
        "neutral_mismatch_rows",
    ):
        value = drift_audit.get(key)
        if key.endswith("_rate"):
            lines.append(f"- {key}: {float(_to_float(value, 0.0)):.4f}")
        else:
            lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "### Top Mismatch Action Pairs"])
    top_mismatch_pairs = drift_audit.get("top_mismatch_action_pairs", [])
    if not isinstance(top_mismatch_pairs, list):
        top_mismatch_pairs = []
    for item in top_mismatch_pairs:
        mapped = _as_mapping(item)
        lines.append(
            f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))} "
            f"(mean_delta={float(_to_float(mapped.get('mean_counterfactual_delta_r'), 0.0)):.4f})"
        )
    lines.extend(["", "### Top Mismatch Action Pairs V2"])
    top_mismatch_pairs_v2 = drift_audit.get("top_mismatch_action_pairs_v2", [])
    if not isinstance(top_mismatch_pairs_v2, list):
        top_mismatch_pairs_v2 = []
    for item in top_mismatch_pairs_v2:
        mapped = _as_mapping(item)
        lines.append(
            f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))} "
            f"(mean_delta={float(_to_float(mapped.get('mean_counterfactual_delta_r'), 0.0)):.4f})"
        )
    lines.extend(["", "### Top Symbol Mismatch"])
    top_symbol_mismatch = drift_audit.get("top_symbol_mismatch", [])
    if not isinstance(top_symbol_mismatch, list):
        top_symbol_mismatch = []
    for item in top_symbol_mismatch:
        mapped = _as_mapping(item)
        lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
    lines.extend(["", "### Top Scene Family Mismatch"])
    top_scene_mismatch = drift_audit.get("top_scene_family_mismatch", [])
    if not isinstance(top_scene_mismatch, list):
        top_scene_mismatch = []
    for item in top_scene_mismatch:
        mapped = _as_mapping(item)
        lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
    lines.extend(["", "### Top Barrier Family Mismatch"])
    top_barrier_mismatch = drift_audit.get("top_barrier_family_mismatch", [])
    if not isinstance(top_barrier_mismatch, list):
        top_barrier_mismatch = []
    for item in top_barrier_mismatch:
        mapped = _as_mapping(item)
        lines.append(f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))}")
    lines.extend(["", "### Top Repeated Mismatch Cases"])
    top_repeated_mismatch = drift_audit.get("top_repeated_mismatch_cases", [])
    if not isinstance(top_repeated_mismatch, list):
        top_repeated_mismatch = []
    for item in top_repeated_mismatch:
        mapped = _as_mapping(item)
        lines.append(
            f"- {_to_str(mapped.get('key', ''))}: {int(_to_int(mapped.get('count', 0), 0))} "
            f"(mean_delta={float(_to_float(mapped.get('mean_counterfactual_delta_r'), 0.0)):.4f})"
        )
    if readiness_gate:
        runtime_heartbeat = _as_mapping(readiness_gate.get("runtime_heartbeat"))
        lines.extend(
            [
                "",
                "## Readiness Gate",
                f"- ready: {bool(readiness_gate.get('ready', False))}",
                f"- stage: {_to_str(readiness_gate.get('stage', ''), '')}",
                f"- runtime_heartbeat_healthy: {bool(runtime_heartbeat.get('healthy', False))}",
                f"- runtime_heartbeat_age_seconds: {runtime_heartbeat.get('age_seconds', None)}",
            ]
        )
        blockers = list(readiness_gate.get("blockers", []) or [])
        lines.append(
            f"- blockers: {', '.join(str(item) for item in blockers) if blockers else 'none'}"
        )
        checks = _as_mapping(readiness_gate.get("checks"))
        if checks:
            lines.extend(["", "### Readiness Checks"])
            for key, value in checks.items():
                lines.append(f"- {key}: {bool(value)}")
        next_actions = list(readiness_gate.get("next_actions", []) or [])
        if next_actions:
            lines.extend(["", "### Next Actions"])
            for item in next_actions:
                lines.append(f"- {str(item)}")
    return "\n".join(lines).strip() + "\n"


def write_barrier_outcome_bridge_report(
    *,
    entry_decision_path: str | Path | None = None,
    closed_trade_path: str | Path | None = None,
    future_bar_path: str | Path | None = None,
    runtime_status_path: str | Path | None = None,
    output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
    symbols: Sequence[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    default_entry = _project_root() / "data" / "trades" / "entry_decisions.csv"
    default_closed = _project_root() / "data" / "trades" / "trade_closed_history.csv"
    entry_path = _resolve_project_path(entry_decision_path, default_entry)
    closed_path = _resolve_project_path(closed_trade_path, default_closed)
    default_future = resolve_default_future_bar_path(entry_path) or Path("")
    future_path = (
        _resolve_project_path(future_bar_path, default_future)
        if future_bar_path or default_future
        else Path("")
    )
    runtime_status_resolved = _resolve_project_path(
        runtime_status_path,
        _project_root() / DEFAULT_RUNTIME_STATUS_PATH,
    )
    output_target = _resolve_project_path(
        output_path,
        _project_root() / DEFAULT_OUTPUT_DIR / "barrier_outcome_bridge_latest.json",
    )
    markdown_target = _resolve_project_path(
        markdown_output_path,
        _project_root() / DEFAULT_OUTPUT_DIR / "barrier_outcome_bridge_latest.md",
    )

    entry_rows = _load_csv_rows(entry_path)
    detail_index = _load_detail_index(resolve_entry_decision_detail_path(entry_path))
    merged_entry_rows = [_merge_detail_payload(row, detail_index=detail_index) for row in entry_rows]
    closed_trade_rows = _load_csv_rows(closed_path)
    future_bar_rows = _load_csv_rows(future_path) if future_path and future_path.exists() else []
    runtime_status = _load_json_mapping(runtime_status_resolved)

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=merged_entry_rows,
        closed_trade_rows=closed_trade_rows,
        future_bar_rows=future_bar_rows,
        runtime_status=runtime_status,
        symbols=symbols,
        limit=limit,
    )
    report["entry_decision_path"] = str(entry_path)
    report["closed_trade_path"] = str(closed_path)
    report["future_bar_path"] = str(future_path) if future_path else ""
    report["runtime_status_path"] = str(runtime_status_resolved)
    report["output_path"] = str(output_target)
    report["markdown_output_path"] = str(markdown_target)

    output_target.parent.mkdir(parents=True, exist_ok=True)
    markdown_target.parent.mkdir(parents=True, exist_ok=True)
    output_target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_target.write_text(render_barrier_outcome_bridge_markdown(report), encoding="utf-8")
    return report
