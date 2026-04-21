"""Replay/outcome bridge for belief-state25 runtime rows."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.services.belief_state25_runtime_bridge import (
    BELIEF_SCOPE_FREEZE_CONTRACT_V1,
    build_belief_state25_runtime_bridge_v1,
)
from backend.services.entry_wait_quality_replay_bridge import resolve_default_future_bar_path
from backend.services.storage_compaction import (
    resolve_entry_decision_detail_path,
    resolve_entry_decision_row_key,
)


BELIEF_OUTCOME_BRIDGE_VERSION = "belief_outcome_bridge_v1"
BELIEF_OUTCOME_ROW_VERSION = "belief_outcome_row_v1"
DEFAULT_OUTPUT_DIR = Path("data") / "analysis" / "belief"
DEFAULT_SHORT_HORIZON_BARS = 3
DEFAULT_MID_HORIZON_BARS = 6
DEFAULT_LONG_HORIZON_BARS = 12


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
    for key in ("signal_bar_ts", "time"):
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


def _belief_bridge_payload(row: Mapping[str, Any] | None) -> dict[str, Any]:
    mapped = _as_mapping(row)
    existing = _as_mapping(mapped.get("belief_state25_runtime_bridge_v1"))
    if existing:
        return existing
    return build_belief_state25_runtime_bridge_v1(mapped)


def _belief_summary(row: Mapping[str, Any] | None) -> dict[str, Any]:
    return _as_mapping(_belief_bridge_payload(row).get("belief_runtime_summary_v1"))


def _belief_input_trace(row: Mapping[str, Any] | None) -> dict[str, Any]:
    return _as_mapping(_belief_bridge_payload(row).get("belief_input_trace_v1"))


def _row_has_bridge_candidate(row: Mapping[str, Any] | None) -> bool:
    mapped = _as_mapping(row)
    if _as_mapping(mapped.get("belief_state25_runtime_bridge_v1")):
        return True
    return bool(_as_mapping(mapped.get("belief_state_v1")))


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


def _opposite_side(side: str) -> str:
    if str(side).upper() == "BUY":
        return "SELL"
    if str(side).upper() == "SELL":
        return "BUY"
    return ""


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


def _dominant_side_from_row(row: Mapping[str, Any] | None) -> str:
    bridge_summary = _as_mapping(_belief_bridge_payload(row).get("belief_runtime_summary_v1"))
    side = _to_str(bridge_summary.get("dominant_side", "")).upper()
    if side in {"BUY", "SELL"}:
        return side
    belief_state = _as_mapping(_as_mapping(row).get("belief_state_v1"))
    side = _to_str(belief_state.get("dominant_side", "")).upper()
    return side if side in {"BUY", "SELL"} else "BALANCED"


def _dominance_confirmed(
    rows: Sequence[Mapping[str, Any]],
    *,
    required_side: str,
    required_count: int = 2,
) -> bool:
    streak = 0
    for raw_row in rows:
        side = _dominant_side_from_row(raw_row)
        if side == required_side:
            streak += 1
            if streak >= required_count:
                return True
        else:
            streak = 0
    return False


def _find_flip_event_row(
    rows: Sequence[Mapping[str, Any]],
    *,
    flip_side: str,
) -> dict[str, Any]:
    for raw_row in rows:
        row = _as_mapping(raw_row)
        outcome = _to_str(row.get("outcome", "")).lower()
        action = _to_str(row.get("action", row.get("direction", ""))).upper()
        if outcome == "entered" and action == flip_side:
            return row
    return {}


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


def _reclaim_move_r(
    *,
    anchor_side: str,
    flip_row: Mapping[str, Any] | None,
    all_future_bars: Sequence[Mapping[str, Any]],
    horizon_end_ts: float,
    reference_unit: float,
) -> float:
    flip = _as_mapping(flip_row)
    if not flip or reference_unit <= 0:
        return 0.0
    flip_ts = _row_time(flip)
    flip_bars = _bars_after_time(all_future_bars, start_ts=flip_ts, end_ts=horizon_end_ts)
    if not flip_bars:
        return 0.0
    flip_anchor_price = _reference_price(flip, flip_bars)
    if flip_anchor_price <= 0:
        return 0.0
    original_side = _opposite_side(anchor_side)
    favorable_move, _ = _favorable_and_adverse_move(original_side, flip_anchor_price, flip_bars)
    return round(float(favorable_move / max(reference_unit, 1e-9)), 6)


def _score_map(
    *,
    f6: float,
    a6: float,
    opposite_move_6: float,
    reclaim_6: float,
    flip_readiness: float,
) -> dict[str, float]:
    return {
        "correct_hold": float(f6 - a6 - max(0.0, flip_readiness - 0.55)),
        "wrong_hold": float(a6 - f6),
        "missed_flip": float(max(0.0, opposite_move_6 - 0.75) + max(0.0, flip_readiness - 0.55)),
        "correct_flip": float(opposite_move_6 - reclaim_6),
        "premature_flip": float(reclaim_6 - opposite_move_6),
    }


def _label_confidence(
    *,
    label: str,
    coverage_ratio: float,
    score_gap: float,
    f3: float,
    f6: float,
    a3: float,
    a6: float,
    opposite_move_6: float,
    reclaim_6: float,
) -> str:
    if not label:
        return "low_skip"
    if coverage_ratio < 0.50:
        return "low_skip"
    if coverage_ratio < 0.70:
        return "weak_usable"
    if label == "correct_hold" and coverage_ratio >= 0.90 and f6 >= 1.00 and a6 <= 0.40 and score_gap >= 0.15:
        return "high"
    if label == "wrong_hold" and coverage_ratio >= 0.90 and a3 >= 0.80 and f6 < 0.30 and score_gap >= 0.15:
        return "high"
    if label == "missed_flip" and coverage_ratio >= 0.90 and opposite_move_6 >= 1.00 and score_gap >= 0.15:
        return "high"
    if label == "correct_flip" and coverage_ratio >= 0.90 and opposite_move_6 >= 1.00 and reclaim_6 < 0.25 and score_gap >= 0.15:
        return "high"
    if label == "premature_flip" and coverage_ratio >= 0.90 and reclaim_6 >= 1.00 and opposite_move_6 < 0.30 and score_gap >= 0.15:
        return "high"
    if score_gap < 0.08:
        return "weak_usable"
    return "medium"


def _belief_break_signature(label: str, *, opp_confirm_6: bool, flip_executed: bool) -> str:
    if label == "wrong_hold":
        return "belief_decay_hold_failure"
    if label == "missed_flip":
        return "opposite_confirmation_ignored"
    if label == "correct_flip":
        return "state_transition_flip_followthrough"
    if label == "premature_flip":
        return "flip_reclaim_failure"
    if label == "correct_hold":
        return "thesis_persistence_valid"
    if opp_confirm_6:
        return "opposite_confirmation_detected"
    if flip_executed:
        return "flip_executed_without_resolution"
    return ""


def _evaluate_belief_outcome_v1(
    row: Mapping[str, Any],
    *,
    future_bars: Sequence[Mapping[str, Any]],
    subsequent_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    bridge = _belief_bridge_payload(row)
    summary = _as_mapping(bridge.get("belief_runtime_summary_v1"))
    input_trace = _as_mapping(bridge.get("belief_input_trace_v1"))
    acting_side = _active_side(summary)
    anchor_context = _to_str(summary.get("anchor_context", "")).lower()
    if not summary.get("available", False) or acting_side not in {"BUY", "SELL"}:
        return {
            "contract_version": BELIEF_OUTCOME_ROW_VERSION,
            "bridge_quality_status": "skip",
            "belief_outcome_label": "",
            "belief_label_confidence": "low_skip",
            "belief_outcome_reason": "belief_summary_missing",
            "belief_break_signature": "",
            "skip_reason": "belief_summary_missing",
        }
    if _to_str(summary.get("dominant_side", "")).upper() == "BALANCED" and anchor_context != "flip_thesis":
        return {
            "contract_version": BELIEF_OUTCOME_ROW_VERSION,
            "bridge_quality_status": "skip",
            "belief_outcome_label": "",
            "belief_label_confidence": "low_skip",
            "belief_outcome_reason": "balanced_belief",
            "belief_break_signature": "",
            "skip_reason": "balanced_belief",
            "belief_anchor_side": acting_side,
            "belief_anchor_context": anchor_context,
        }

    anchor_price = _reference_price(row, future_bars)
    reference_unit = _reference_unit(row, future_bars, anchor_price)
    if anchor_price <= 0 or reference_unit <= 0:
        return {
            "contract_version": BELIEF_OUTCOME_ROW_VERSION,
            "bridge_quality_status": "skip",
            "belief_outcome_label": "",
            "belief_label_confidence": "low_skip",
            "belief_outcome_reason": "reference_unavailable",
            "belief_break_signature": "",
            "skip_reason": "reference_unavailable",
            "belief_anchor_side": acting_side,
            "belief_anchor_context": anchor_context,
        }

    bars_3 = list(future_bars[:DEFAULT_SHORT_HORIZON_BARS])
    bars_6 = list(future_bars[:DEFAULT_MID_HORIZON_BARS])
    bars_12 = list(future_bars[:DEFAULT_LONG_HORIZON_BARS])
    coverage_ratio = min(1.0, float(len(bars_6)) / float(DEFAULT_MID_HORIZON_BARS))
    if not bars_6:
        return {
            "contract_version": BELIEF_OUTCOME_ROW_VERSION,
            "bridge_quality_status": "skip",
            "belief_outcome_label": "",
            "belief_label_confidence": "low_skip",
            "belief_outcome_reason": "future_bars_missing",
            "belief_break_signature": "",
            "skip_reason": "future_bars_missing",
            "belief_anchor_side": acting_side,
            "belief_anchor_context": anchor_context,
        }

    horizon_end_ts = _to_float(_as_mapping(bars_6[-1]).get("time"), 0.0)
    future_follow_rows = list(subsequent_rows or [])
    opposite_side = _opposite_side(acting_side)
    f3_raw, a3_raw = _favorable_and_adverse_move(acting_side, anchor_price, bars_3)
    f6_raw, a6_raw = _favorable_and_adverse_move(acting_side, anchor_price, bars_6)
    f3 = round(float(f3_raw / reference_unit), 6)
    a3 = round(float(a3_raw / reference_unit), 6)
    f6 = round(float(f6_raw / reference_unit), 6)
    a6 = round(float(a6_raw / reference_unit), 6)

    opposite_confirm_3 = bool(
        _dominance_confirmed(future_follow_rows, required_side=opposite_side, required_count=2) or a3 >= 0.60
    )
    opposite_confirm_6 = bool(
        _dominance_confirmed(future_follow_rows, required_side=opposite_side, required_count=2) or a6 >= 0.60
    )
    flip_event_row = _find_flip_event_row(future_follow_rows, flip_side=acting_side)
    belief_flip_executed = bool(flip_event_row)
    reclaim_6 = _reclaim_move_r(
        anchor_side=acting_side,
        flip_row=flip_event_row,
        all_future_bars=bars_12,
        horizon_end_ts=horizon_end_ts,
        reference_unit=reference_unit,
    )
    flip_confirmation_3 = bool(
        _dominance_confirmed(future_follow_rows, required_side=acting_side, required_count=2) or f3 >= 0.60
    )

    active_persistence = _to_float(summary.get("active_persistence"), 0.0)
    flip_readiness = _to_float(summary.get("flip_readiness"), 0.0)
    instability = _to_float(summary.get("belief_instability"), 0.0)
    hold_family_active = anchor_context in {"entry_thesis", "hold_thesis"}
    flip_family_active = anchor_context == "flip_thesis" or flip_readiness >= 0.55

    label_candidates: list[str] = []
    if hold_family_active and active_persistence >= 0.38 and instability <= 0.45 and f6 >= 0.75 and a6 <= 0.60 and not opposite_confirm_6:
        label_candidates.append("correct_hold")
    if hold_family_active and a6 >= 1.00 and f6 < 0.50 and not opposite_confirm_6:
        label_candidates.append("wrong_hold")
    if hold_family_active and (flip_readiness >= 0.55 or opposite_confirm_3) and not belief_flip_executed and a6 >= 0.80:
        label_candidates.append("missed_flip")
    if flip_family_active and belief_flip_executed and f6 >= 0.75 and reclaim_6 < 0.40 and flip_confirmation_3:
        label_candidates.append("correct_flip")
    if flip_family_active and belief_flip_executed and f6 < 0.50 and reclaim_6 >= 0.75:
        label_candidates.append("premature_flip")

    precedence = ["premature_flip", "correct_flip", "missed_flip", "wrong_hold", "correct_hold"]
    scores = _score_map(
        f6=f6,
        a6=a6,
        opposite_move_6=(f6 if flip_family_active else a6),
        reclaim_6=reclaim_6,
        flip_readiness=flip_readiness,
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
        f3=f3,
        f6=f6,
        a3=a3,
        a6=a6,
        opposite_move_6=(f6 if flip_family_active else a6),
        reclaim_6=reclaim_6,
    )
    if score_gap < 0.05 and len(label_candidates) >= 2:
        confidence = "low_skip"
    skip_reason = ""
    if not resolved_label:
        skip_reason = "no_label_match"
    elif confidence == "low_skip":
        skip_reason = "low_confidence"

    return {
        "contract_version": BELIEF_OUTCOME_ROW_VERSION,
        "bridge_quality_status": "labeled" if resolved_label and confidence in {"high", "medium", "weak_usable"} else "skip",
        "belief_anchor_side": acting_side,
        "belief_anchor_context": anchor_context,
        "belief_horizon_bars": DEFAULT_MID_HORIZON_BARS,
        "belief_runtime_summary_v1": summary,
        "belief_input_trace_v1": input_trace,
        "reference_unit_r": round(float(reference_unit), 6),
        "anchor_price": round(float(anchor_price), 6),
        "future_bar_coverage_ratio": round(float(coverage_ratio), 6),
        "future_bar_count": len(bars_6),
        "F_3": f3,
        "F_6": f6,
        "A_3": a3,
        "A_6": a6,
        "OppConfirm_3": bool(opposite_confirm_3),
        "OppConfirm_6": bool(opposite_confirm_6),
        "belief_flip_executed": bool(belief_flip_executed),
        "Reclaim_6": round(float(reclaim_6), 6),
        "label_candidates": list(label_candidates),
        "belief_outcome_label": resolved_label,
        "belief_label_confidence": confidence,
        "belief_outcome_reason": skip_reason or resolved_label or "no_label_match",
        "belief_break_signature": _belief_break_signature(
            resolved_label,
            opp_confirm_6=bool(opposite_confirm_6),
            flip_executed=bool(belief_flip_executed),
        ),
        "belief_conflict_resolver_v1": {
            "used": bool(conflict_resolver_used),
            "scores": {key: round(float(value), 6) for key, value in scores.items()},
            "score_gap": round(float(score_gap), 6),
        },
        "skip_reason": skip_reason,
        "flip_confirmation_3": bool(flip_confirmation_3),
    }


def build_belief_outcome_bridge_rows(
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
        target_rows = target_rows[-int(limit) :]

    future_index = _future_bar_index(future_bar_rows or [])
    decision_index = _decision_row_index(merged_rows)
    closed_index = _closed_trade_index(closed_trade_rows)

    bridged_rows: list[dict[str, Any]] = []
    for row in target_rows:
        bridge = _belief_bridge_payload(row)
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
        outcome_row = _evaluate_belief_outcome_v1(
            row,
            future_bars=future_bars,
            subsequent_rows=subsequent_rows,
        )
        bridged_rows.append(
            {
                "contract_version": BELIEF_OUTCOME_BRIDGE_VERSION,
                "row_key": resolve_entry_decision_row_key(row),
                "symbol": _to_str(row.get("symbol", "")).upper(),
                "time": _row_time(row),
                "outcome": _to_str(row.get("outcome", "")).lower(),
                "belief_state25_runtime_bridge_v1": bridge,
                "belief_outcome_bridge_v1": outcome_row,
                "matched_closed_trade_row": _matched_closed_trade_row(row, closed_trade_index=closed_index),
            }
        )
    return bridged_rows


def build_belief_outcome_bridge_report(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]],
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
    symbols: Sequence[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    merged_rows = [_as_mapping(row) for row in entry_decision_rows]
    bridged_rows = build_belief_outcome_bridge_rows(
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
    eligible_rows = 0
    usable_rows = 0
    weak_usable_rows = 0
    high_confidence_rows = 0
    for raw_row in bridged_rows:
        outcome = _as_mapping(_as_mapping(raw_row).get("belief_outcome_bridge_v1"))
        label = _to_str(outcome.get("belief_outcome_label", "")).lower()
        confidence = _to_str(outcome.get("belief_label_confidence", "")).lower()
        context = _to_str(outcome.get("belief_anchor_context", "")).lower()
        skip_reason = _to_str(outcome.get("skip_reason", "")).lower()
        if label:
            label_counts[label] = int(label_counts.get(label, 0)) + 1
        if confidence:
            confidence_counts[confidence] = int(confidence_counts.get(confidence, 0)) + 1
        if context:
            anchor_context_counts[context] = int(anchor_context_counts.get(context, 0)) + 1
        if skip_reason:
            skip_reason_counts[skip_reason] = int(skip_reason_counts.get(skip_reason, 0)) + 1
        if confidence in {"high", "medium"} and label:
            eligible_rows += 1
        if confidence in {"high", "medium", "weak_usable"} and label:
            usable_rows += 1
        if confidence == "weak_usable" and label:
            weak_usable_rows += 1
        if confidence == "high":
            high_confidence_rows += 1

    labeled_total = sum(label_counts.values())
    summary = {
        "raw_bridge_candidate_count": len([row for row in merged_rows if _row_has_bridge_candidate(row)]),
        "bridged_row_count": len(bridged_rows),
        "labeled_rows": int(labeled_total),
        "eligible_rows": int(eligible_rows),
        "strict_rows": int(eligible_rows),
        "usable_rows": int(usable_rows),
        "weak_usable_rows": int(weak_usable_rows),
        "candidate_gate_usable_rows": int(eligible_rows),
        "high_confidence_rows": int(high_confidence_rows),
        "wrong_hold_ratio": round(float(label_counts.get("wrong_hold", 0)) / max(labeled_total, 1), 4),
        "premature_flip_ratio": round(float(label_counts.get("premature_flip", 0)) / max(labeled_total, 1), 4),
        "missed_flip_ratio": round(float(label_counts.get("missed_flip", 0)) / max(labeled_total, 1), 4),
        "high_confidence_share": round(float(high_confidence_rows) / max(len(bridged_rows), 1), 4),
    }
    coverage = {
        "label_counts": dict(sorted(label_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "anchor_context_counts": dict(sorted(anchor_context_counts.items())),
        "skip_reason_counts": dict(sorted(skip_reason_counts.items())),
    }
    return {
        "contract_version": BELIEF_OUTCOME_BRIDGE_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope_freeze_contract": BELIEF_SCOPE_FREEZE_CONTRACT_V1,
        "summary": summary,
        "coverage": coverage,
        "rows": bridged_rows,
    }


def render_belief_outcome_bridge_markdown(report: Mapping[str, Any] | None = None) -> str:
    payload = _as_mapping(report)
    summary = _as_mapping(payload.get("summary"))
    coverage = _as_mapping(payload.get("coverage"))
    lines = [
        "# Belief Outcome Bridge Report",
        "",
        f"- raw_bridge_candidate_count: {int(_to_int(summary.get('raw_bridge_candidate_count'), 0))}",
        f"- bridged_row_count: {int(_to_int(summary.get('bridged_row_count'), 0))}",
        f"- labeled_rows: {int(_to_int(summary.get('labeled_rows'), 0))}",
        f"- eligible_rows: {int(_to_int(summary.get('eligible_rows'), 0))}",
        f"- usable_rows: {int(_to_int(summary.get('usable_rows'), 0))}",
        f"- weak_usable_rows: {int(_to_int(summary.get('weak_usable_rows'), 0))}",
        f"- high_confidence_rows: {int(_to_int(summary.get('high_confidence_rows'), 0))}",
        f"- wrong_hold_ratio: {float(_to_float(summary.get('wrong_hold_ratio'), 0.0)):.4f}",
        f"- premature_flip_ratio: {float(_to_float(summary.get('premature_flip_ratio'), 0.0)):.4f}",
        f"- missed_flip_ratio: {float(_to_float(summary.get('missed_flip_ratio'), 0.0)):.4f}",
        f"- high_confidence_share: {float(_to_float(summary.get('high_confidence_share'), 0.0)):.4f}",
        "",
        "## Label Counts",
    ]
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
    return "\n".join(lines).strip() + "\n"


def write_belief_outcome_bridge_report(
    *,
    entry_decision_path: str | Path | None = None,
    closed_trade_path: str | Path | None = None,
    future_bar_path: str | Path | None = None,
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
    output_target = _resolve_project_path(
        output_path,
        _project_root() / DEFAULT_OUTPUT_DIR / "belief_outcome_bridge_latest.json",
    )
    markdown_target = _resolve_project_path(
        markdown_output_path,
        _project_root() / DEFAULT_OUTPUT_DIR / "belief_outcome_bridge_latest.md",
    )

    entry_rows = _load_csv_rows(entry_path)
    detail_index = _load_detail_index(resolve_entry_decision_detail_path(entry_path))
    merged_entry_rows = [_merge_detail_payload(row, detail_index=detail_index) for row in entry_rows]
    closed_trade_rows = _load_csv_rows(closed_path)
    future_bar_rows = _load_csv_rows(future_path) if future_path and future_path.exists() else []

    report = build_belief_outcome_bridge_report(
        entry_decision_rows=merged_entry_rows,
        closed_trade_rows=closed_trade_rows,
        future_bar_rows=future_bar_rows,
        symbols=symbols,
        limit=limit,
    )
    report["entry_decision_path"] = str(entry_path)
    report["closed_trade_path"] = str(closed_path)
    report["future_bar_path"] = str(future_path) if future_path else ""
    report["output_path"] = str(output_target)
    report["markdown_output_path"] = str(markdown_target)

    output_target.parent.mkdir(parents=True, exist_ok=True)
    markdown_target.parent.mkdir(parents=True, exist_ok=True)
    output_target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_target.write_text(render_belief_outcome_bridge_markdown(report), encoding="utf-8")
    return report
