from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from backend.core.config import Config
from backend.services.storage_compaction import resolve_entry_decision_row_key
from backend.services.outcome_labeler_contract import (
    OUTCOME_LABEL_CONTRACT_V1,
    OUTCOME_LABELER_MANAGEMENT_LABELS_V1,
    OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
    OUTCOME_LABELER_OUTCOME_SIGNAL_SOURCE_V1,
    OUTCOME_LABELER_SHADOW_OUTPUT_V1,
    OUTCOME_LABELER_TRANSITION_LABELS_V1,
    OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
    build_management_horizon_descriptor,
    build_outcome_signal_source_descriptor,
    build_transition_horizon_descriptor,
    normalize_outcome_label_status,
    resolve_entry_decision_anchor_time,
    resolve_outcome_label_polarity,
    resolve_outcome_label_status_from_flags,
)
from backend.trading.engine.core.models import (
    OutcomeLabelsV1,
    TradeManagementOutcomeLabelsV1,
    TransitionOutcomeLabelsV1,
)

OUTCOME_LABELER_ENGINE_VERSION = "outcome_labeler_engine_v1"
OUTCOME_LABELER_SHADOW_OUTPUT_VERSION = "shadow_label_output_v1"
_MIN_DIRECTIONAL_MOVE_RATIO = 0.00035
_PULLBACK_MOVE_RATIO = 0.0002
_EDGE_TRAVEL_RATIO = 0.0012
_DOMINANCE_RATIO = 1.15
_FLAT_RETURN_RATIO = 0.00015
_FORECAST_POSITIVE_THRESHOLD = 0.5
_GAP_SIGNAL_DEADBAND = 0.05
OUTCOME_LABEL_COMPACT_SUMMARY_VERSION = "label_quality_summary_v1"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_ratio(num: int, den: int) -> float:
    if int(den) <= 0:
        return 0.0
    return round(float(num) / float(den), 6)


def _to_timestamp(value: Any) -> float | None:
    if value in ("", None):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return float(parsed.timestamp())
    except ValueError:
        return None


def _normalize_side(value: Any) -> str:
    side = str(value or "").strip().upper()
    if side in {"BUY", "SELL"}:
        return side
    return ""


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        try:
            candidate = value.to_dict()
        except TypeError:
            candidate = None
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, Mapping):
            return dict(parsed)
    return {}


def _coerce_rows(rows: Any) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if isinstance(rows, Mapping):
        return [dict(rows)]
    if hasattr(rows, "to_dict") and hasattr(rows, "columns"):
        try:
            records = rows.to_dict("records")
        except TypeError:
            records = []
        return [dict(item) for item in records if isinstance(item, Mapping)]
    if isinstance(rows, str):
        return []
    if isinstance(rows, Iterable):
        out: list[dict[str, Any]] = []
        for item in rows:
            mapped = _coerce_mapping(item)
            if mapped:
                out.append(mapped)
        return out
    return []


def _row_timestamp(row: Mapping[str, Any] | None) -> float | None:
    if not isinstance(row, Mapping):
        return None
    for field in ("signal_bar_ts", "time", "timestamp", "ts", "open_ts", "close_ts", "open_time", "close_time"):
        resolved = _to_timestamp(row.get(field))
        if resolved is not None:
            return resolved
    return None


def _row_price(row: Mapping[str, Any] | None, fields: Sequence[str]) -> float:
    if not isinstance(row, Mapping):
        return 0.0
    for field in fields:
        value = _to_float(row.get(field), 0.0)
        if value > 0.0:
            return value
    return 0.0


def _position_key(row: Mapping[str, Any] | None) -> int:
    if not isinstance(row, Mapping):
        return 0
    for field in ("ticket", "position_id"):
        value = _to_int(row.get(field), 0)
        if value > 0:
            return value
    return 0


def _direction_from_row(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""
    for field in ("direction", "action", "setup_side", "side"):
        side = _normalize_side(row.get(field))
        if side:
            return side
    return ""


def _bar_price(bar: Mapping[str, Any] | None, field: str, fallback_fields: Sequence[str]) -> float:
    if not isinstance(bar, Mapping):
        return 0.0
    primary = _to_float(bar.get(field), 0.0)
    if primary > 0.0:
        return primary
    return _row_price(bar, fallback_fields)


def _sort_rows_by_timestamp(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted((_coerce_mapping(row) for row in rows), key=lambda row: (_row_timestamp(row) or float("inf"), _position_key(row)))


def _future_rows_after_anchor(
    future_bars: Sequence[Mapping[str, Any]],
    *,
    anchor_ts: float,
    cap_ts: float | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for bar in _sort_rows_by_timestamp(future_bars):
        bar_ts = _row_timestamp(bar)
        if bar_ts is None or bar_ts <= anchor_ts:
            continue
        if cap_ts is not None and bar_ts > cap_ts:
            continue
        rows.append(bar)
    return rows


def _has_censoring(rows: Sequence[Mapping[str, Any]], *, explicit_censored: bool = False) -> bool:
    if explicit_censored:
        return True
    for row in rows:
        if bool(row.get("is_censored")) or bool(row.get("censored")) or bool(row.get("data_gap")):
            return True
    return False


def _dominant_side(*, bullish_move: float, bearish_move: float, min_move: float = _MIN_DIRECTIONAL_MOVE_RATIO) -> str:
    if bullish_move < min_move and bearish_move < min_move:
        return ""
    if bullish_move >= bearish_move * _DOMINANCE_RATIO and bullish_move >= min_move:
        return "BUY"
    if bearish_move >= bullish_move * _DOMINANCE_RATIO and bearish_move >= min_move:
        return "SELL"
    return "AMBIGUOUS"


def _path_metrics(
    future_bars: Sequence[Mapping[str, Any]],
    *,
    baseline_price: float,
) -> dict[str, Any]:
    if baseline_price <= 0.0:
        return {"is_valid": False}

    ordered = list(future_bars)
    highs = [_bar_price(bar, "high", ("open", "close", "price")) for bar in ordered]
    lows = [_bar_price(bar, "low", ("open", "close", "price")) for bar in ordered]
    closes = [_bar_price(bar, "close", ("open", "price")) for bar in ordered]

    if not highs or not lows or not closes:
        return {"is_valid": False}

    early_window = ordered[: max(1, min(2, len(ordered)))]
    early_high = max(_bar_price(bar, "high", ("open", "close", "price")) for bar in early_window)
    early_low = min(_bar_price(bar, "low", ("open", "close", "price")) for bar in early_window)
    last_close = closes[-1]

    bullish_move = max(0.0, (max(highs) - baseline_price) / baseline_price)
    bearish_move = max(0.0, (baseline_price - min(lows)) / baseline_price)
    net_return = (last_close - baseline_price) / baseline_price
    early_bullish = max(0.0, (early_high - baseline_price) / baseline_price)
    early_bearish = max(0.0, (baseline_price - early_low) / baseline_price)

    early_side = _dominant_side(bullish_move=early_bullish, bearish_move=early_bearish, min_move=_PULLBACK_MOVE_RATIO)
    dominant_side = _dominant_side(bullish_move=bullish_move, bearish_move=bearish_move)
    ambiguous = dominant_side == "AMBIGUOUS" or (
        bullish_move >= _MIN_DIRECTIONAL_MOVE_RATIO
        and bearish_move >= _MIN_DIRECTIONAL_MOVE_RATIO
        and min(bullish_move, bearish_move) > 0.0
        and (max(bullish_move, bearish_move) / max(min(bullish_move, bearish_move), 1e-9)) < _DOMINANCE_RATIO
    )

    return {
        "is_valid": True,
        "bar_count": len(ordered),
        "bullish_move_ratio": bullish_move,
        "bearish_move_ratio": bearish_move,
        "net_return_ratio": net_return,
        "early_bullish_move_ratio": early_bullish,
        "early_bearish_move_ratio": early_bearish,
        "early_dominant_side": "" if early_side == "AMBIGUOUS" else early_side,
        "dominant_side": "" if dominant_side == "AMBIGUOUS" else dominant_side,
        "is_ambiguous": bool(ambiguous),
    }


def _same_side_metrics(path_metrics: Mapping[str, Any], *, position_side: str) -> tuple[float, float, float, float]:
    if position_side == "SELL":
        same_side_mfe = _to_float(path_metrics.get("bearish_move_ratio"), 0.0)
        opposite_side_mae = _to_float(path_metrics.get("bullish_move_ratio"), 0.0)
        early_same_side = _to_float(path_metrics.get("early_bearish_move_ratio"), 0.0)
        early_opposite_side = _to_float(path_metrics.get("early_bullish_move_ratio"), 0.0)
    else:
        same_side_mfe = _to_float(path_metrics.get("bullish_move_ratio"), 0.0)
        opposite_side_mae = _to_float(path_metrics.get("bearish_move_ratio"), 0.0)
        early_same_side = _to_float(path_metrics.get("early_bullish_move_ratio"), 0.0)
        early_opposite_side = _to_float(path_metrics.get("early_bearish_move_ratio"), 0.0)
    return same_side_mfe, opposite_side_mae, early_same_side, early_opposite_side


def _rounded_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    return value


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return _rounded_value(value)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _slugify_token(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip().lower()
    if not text:
        return fallback
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in text)
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or fallback


def _reason_block(
    reason_code: str,
    reason_text: str,
    *,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "reason_code": str(reason_code or "").strip(),
        "reason_text": str(reason_text or "").strip(),
        "evidence": {str(key): _rounded_value(value) for key, value in dict(evidence or {}).items() if value not in ("", None)},
    }


def _future_window_bounds(
    future_bars: Sequence[Mapping[str, Any]],
    *,
    family: str,
    anchor_ts: float | None,
    closed_trade_row: Mapping[str, Any] | None,
) -> tuple[float | None, float | None]:
    timestamps = [_row_timestamp(bar) for bar in future_bars]
    ordered = [timestamp for timestamp in timestamps if timestamp is not None]
    close_ts = _to_timestamp((closed_trade_row or {}).get("close_ts")) or _to_timestamp((closed_trade_row or {}).get("close_time"))
    start = ordered[0] if ordered else None
    end = ordered[-1] if ordered else None
    if family == "management" and close_ts is not None and anchor_ts is not None and close_ts > anchor_ts:
        if start is None:
            start = close_ts
        end = close_ts
    return start, end


def _build_source_files_metadata() -> dict[str, Any]:
    required_inputs = list(OUTCOME_LABELER_OUTCOME_SIGNAL_SOURCE_V1.get("required_inputs", []) or [])
    optional_inputs = list(OUTCOME_LABELER_OUTCOME_SIGNAL_SOURCE_V1.get("optional_inputs", []) or [])
    anchor_sources = []
    future_sources = []
    if required_inputs:
        anchor_sources = list((required_inputs[0] or {}).get("path_candidates", []) or [])
    if len(required_inputs) > 1:
        future_sources = list((required_inputs[1] or {}).get("path_candidates", []) or [])
    return {
        "anchor": anchor_sources,
        "future_outcome": future_sources,
        "optional": [str(item.get("source", "") or "") for item in optional_inputs if isinstance(item, Mapping)],
    }


def _forecast_probability_summary(forecast_snapshot: Mapping[str, Any]) -> tuple[dict[str, float], str, float]:
    probabilities: dict[str, float] = {}
    for key, value in dict(forecast_snapshot or {}).items():
        key_text = str(key or "")
        if not key_text.startswith("p_"):
            continue
        probabilities[key_text] = _to_float(value, 0.0)
    if not probabilities:
        return {}, "", 0.0
    top_field, top_value = max(probabilities.items(), key=lambda item: (item[1], item[0]))
    return {key: _rounded_value(value) for key, value in probabilities.items()}, top_field, _rounded_value(top_value)


def _compact_label_source_descriptor(value: Any) -> str:
    descriptor = _coerce_mapping(value)
    if not descriptor:
        return ""
    anchor_source = str(descriptor.get("anchor_source", "") or "").strip()
    anchor_time_field = str(descriptor.get("anchor_time_field", "") or "").strip()
    future_source = str(descriptor.get("future_source", "") or "").strip()
    join_stages = [str(item).strip() for item in list(descriptor.get("deterministic_join_stages", []) or []) if str(item).strip()]

    parts: list[str] = []
    if anchor_source or anchor_time_field:
        parts.append(f"anchor={anchor_source or 'unknown'}:{anchor_time_field or 'unknown'}")
    if future_source:
        parts.append(f"future={future_source}")
    if join_stages:
        parts.append(f"join={'>'.join(join_stages)}")
    return "|".join(parts)


def _to_bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if float(value) == 1.0:
            return True
        if float(value) == 0.0:
            return False
        return None
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _forecast_field_mapping(family: str) -> dict[str, str]:
    if family == "transition":
        return {
            "p_buy_confirm": "buy_confirm_success_label",
            "p_sell_confirm": "sell_confirm_success_label",
            "p_false_break": "false_break_label",
            "p_reversal_success": "reversal_success_label",
            "p_continuation_success": "continuation_success_label",
        }
    return {
        "p_continue_favor": "continue_favor_label",
        "p_fail_now": "fail_now_label",
        "p_recover_after_pullback": "recover_after_pullback_label",
        "p_reach_tp1": "reach_tp1_label",
        "p_opposite_edge_reach": "opposite_edge_reach_label",
        "p_better_reentry_if_cut": "better_reentry_if_cut_label",
    }


def _build_forecast_vs_outcome_evaluation(
    *,
    family: str,
    forecast_snapshot: Mapping[str, Any],
    family_payload: Mapping[str, Any],
) -> dict[str, Any]:
    mapping = _forecast_field_mapping(family)
    probabilities, top_field, top_value = _forecast_probability_summary(forecast_snapshot)
    label_status = normalize_outcome_label_status(str(family_payload.get("label_status", "") or ""))
    evaluations: dict[str, Any] = {}
    scorable_fields = 0
    hit_count = 0
    miss_count = 0
    unknown_count = 0

    for forecast_field, label_name in mapping.items():
        has_forecast = forecast_field in dict(forecast_snapshot or {})
        probability = _to_float(forecast_snapshot.get(forecast_field), 0.0)
        actual_positive = _to_bool_or_none(family_payload.get(label_name))
        predicted_positive = probability >= _FORECAST_POSITIVE_THRESHOLD if has_forecast else None
        scorable = bool(has_forecast and label_status == "VALID" and actual_positive is not None)
        hit = predicted_positive == actual_positive if scorable else None
        miss = (not hit) if scorable else None
        if scorable:
            scorable_fields += 1
            if hit:
                hit_count += 1
            else:
                miss_count += 1
        else:
            unknown_count += 1
        evaluations[forecast_field] = {
            "label_name": label_name,
            "probability": _rounded_value(probability),
            "has_forecast": has_forecast,
            "predicted_positive": predicted_positive,
            "actual_positive": actual_positive,
            "scorable": scorable,
            "hit": hit,
            "miss": miss,
        }

    top_field_hit = None
    if top_field:
        top_eval = _coerce_mapping(evaluations.get(top_field))
        top_field_hit = top_eval.get("hit")

    return {
        "contract_version": "forecast_vs_outcome_v1",
        "family": family,
        "label_status": label_status,
        "evaluations": evaluations,
        "summary": {
            "scorable_fields": scorable_fields,
            "hit_count": hit_count,
            "miss_count": miss_count,
            "unknown_count": unknown_count,
            "hit_rate": _safe_ratio(hit_count, scorable_fields),
            "top_forecast_field": top_field,
            "top_forecast_probability": top_value,
            "top_field_hit": top_field_hit,
        },
    }


def _resolve_gap_actual_positive(
    gap_name: str,
    *,
    transition_payload: Mapping[str, Any],
    management_payload: Mapping[str, Any],
) -> bool | None:
    buy_confirm = _to_bool_or_none(transition_payload.get("buy_confirm_success_label"))
    sell_confirm = _to_bool_or_none(transition_payload.get("sell_confirm_success_label"))
    false_break = _to_bool_or_none(transition_payload.get("false_break_label"))
    reversal = _to_bool_or_none(transition_payload.get("reversal_success_label"))
    continuation = _to_bool_or_none(transition_payload.get("continuation_success_label"))
    continue_favor = _to_bool_or_none(management_payload.get("continue_favor_label"))
    fail_now = _to_bool_or_none(management_payload.get("fail_now_label"))
    recover_after_pullback = _to_bool_or_none(management_payload.get("recover_after_pullback_label"))
    better_reentry = _to_bool_or_none(management_payload.get("better_reentry_if_cut_label"))
    opposite_edge_reach = _to_bool_or_none(management_payload.get("opposite_edge_reach_label"))

    if gap_name in {"transition_confirm_fake_gap", "wait_confirm_gap"}:
        if buy_confirm is True or sell_confirm is True:
            return True
        if false_break is True:
            return False
        return None
    if gap_name == "transition_reversal_continuation_gap":
        if reversal is True:
            return True
        if continuation is True:
            return False
        return None
    if gap_name == "management_continue_fail_gap":
        if continue_favor is True:
            return True
        if fail_now is True:
            return False
        return None
    if gap_name == "management_recover_reentry_gap":
        if recover_after_pullback is True:
            return True
        if better_reentry is True:
            return False
        return None
    if gap_name == "hold_exit_gap":
        if continue_favor is True or opposite_edge_reach is True:
            return True
        if fail_now is True:
            return False
        return None
    if gap_name == "same_side_flip_gap":
        if continue_favor is True:
            return True
        if better_reentry is True:
            return False
        return None
    if gap_name == "belief_barrier_tension_gap":
        if continue_favor is True or buy_confirm is True or sell_confirm is True:
            return True
        if fail_now is True or false_break is True:
            return False
        return None
    return None


def _gap_quality_state(
    *,
    predicted_positive: bool | None,
    actual_positive: bool | None,
    hit: bool | None,
) -> str:
    if predicted_positive is None:
        return "weak_signal"
    if actual_positive is None or hit is None:
        return "unscorable"
    if hit and predicted_positive:
        return "aligned_positive"
    if hit and not predicted_positive:
        return "aligned_negative"
    if predicted_positive:
        return "misaligned_positive"
    return "misaligned_negative"


def _build_gap_signal_quality(
    *,
    gap_snapshot: Mapping[str, Any],
    transition_payload: Mapping[str, Any],
    management_payload: Mapping[str, Any],
) -> dict[str, Any]:
    gap_fields = (
        "transition_side_separation",
        "transition_confirm_fake_gap",
        "transition_reversal_continuation_gap",
        "management_continue_fail_gap",
        "management_recover_reentry_gap",
        "wait_confirm_gap",
        "hold_exit_gap",
        "same_side_flip_gap",
        "belief_barrier_tension_gap",
    )
    evaluations: dict[str, Any] = {}
    scorable_signals = 0
    active_signals = 0
    hit_count = 0
    miss_count = 0
    unknown_count = 0

    for gap_name in gap_fields:
        if gap_name not in dict(gap_snapshot or {}):
            continue
        gap_value = _to_float(gap_snapshot.get(gap_name), 0.0)
        predicted_positive = None
        if gap_value >= _GAP_SIGNAL_DEADBAND:
            predicted_positive = True
        elif gap_value <= -_GAP_SIGNAL_DEADBAND:
            predicted_positive = False
        actual_positive = _resolve_gap_actual_positive(
            gap_name,
            transition_payload=transition_payload,
            management_payload=management_payload,
        )
        scorable = predicted_positive is not None and actual_positive is not None
        hit = predicted_positive == actual_positive if scorable else None
        if predicted_positive is not None:
            active_signals += 1
        if scorable:
            scorable_signals += 1
            if hit:
                hit_count += 1
            else:
                miss_count += 1
        else:
            unknown_count += 1
        evaluations[gap_name] = {
            "gap_value": _rounded_value(gap_value),
            "signal_active": predicted_positive is not None,
            "predicted_positive": predicted_positive,
            "actual_positive": actual_positive,
            "scorable": scorable,
            "hit": hit,
            "quality_state": _gap_quality_state(
                predicted_positive=predicted_positive,
                actual_positive=actual_positive,
                hit=hit,
            ),
        }

    dominant_gap = ""
    dominant_gap_strength = 0.0
    if evaluations:
        dominant_gap, dominant_gap_payload = max(
            evaluations.items(),
            key=lambda item: (abs(_to_float(_coerce_mapping(item[1]).get("gap_value"), 0.0)), item[0]),
        )
        dominant_gap_strength = abs(_to_float(_coerce_mapping(dominant_gap_payload).get("gap_value"), 0.0))

    return {
        "contract_version": "gap_signal_quality_v1",
        "evaluations": evaluations,
        "summary": {
            "active_signals": active_signals,
            "scorable_signals": scorable_signals,
            "hit_count": hit_count,
            "miss_count": miss_count,
            "unknown_count": unknown_count,
            "hit_rate": _safe_ratio(hit_count, scorable_signals),
            "dominant_gap": dominant_gap,
            "dominant_gap_strength": _rounded_value(dominant_gap_strength),
        },
    }


def _build_forecast_branch_evaluation(
    *,
    forecast_snapshot: Mapping[str, Any],
    transition_payload: Mapping[str, Any],
    management_payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "contract_version": "forecast_branch_evaluation_v1",
        "transition_forecast_vs_outcome": _build_forecast_vs_outcome_evaluation(
            family="transition",
            forecast_snapshot=_coerce_mapping(forecast_snapshot.get("transition_forecast_v1")),
            family_payload=transition_payload,
        ),
        "management_forecast_vs_outcome": _build_forecast_vs_outcome_evaluation(
            family="management",
            forecast_snapshot=_coerce_mapping(forecast_snapshot.get("trade_management_forecast_v1")),
            family_payload=management_payload,
        ),
        "gap_signal_quality": _build_gap_signal_quality(
            gap_snapshot=_coerce_mapping(forecast_snapshot.get("forecast_gap_metrics_v1")),
            transition_payload=transition_payload,
            management_payload=management_payload,
        ),
    }


def _family_shadow_summary(
    *,
    family: str,
    family_payload: Mapping[str, Any],
    label_names: Sequence[str],
    forecast_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = _coerce_mapping(family_payload.get("metadata"))
    probabilities, top_field, top_value = _forecast_probability_summary(forecast_snapshot)
    label_polarities = _coerce_mapping(metadata.get("label_polarities"))
    label_reasons = _coerce_mapping(metadata.get("label_reasons"))
    label_status = normalize_outcome_label_status(str(family_payload.get("label_status", "") or ""))
    positive_labels: list[str] = []
    negative_labels: list[str] = []
    unknown_labels: list[str] = []
    reason_codes: dict[str, str] = {}
    for label_name in label_names:
        polarity = str(label_polarities.get(label_name, "UNKNOWN") or "UNKNOWN")
        if polarity == "POSITIVE":
            positive_labels.append(label_name)
        elif polarity == "NEGATIVE":
            negative_labels.append(label_name)
        else:
            unknown_labels.append(label_name)
        reason_codes[label_name] = str(_coerce_mapping(label_reasons.get(label_name)).get("reason_code", "") or "")
    return {
        "family": family,
        "label_status": label_status,
        "label_status_reason_code": str(_coerce_mapping(metadata.get("label_status_reason")).get("reason_code", "") or ""),
        "label_source_descriptor": _compact_label_source_descriptor(metadata.get("signal_source_descriptor")),
        "horizon_bars": _to_int(metadata.get("horizon_bars"), 0),
        "scorable": label_status == "VALID",
        "is_ambiguous": label_status == "AMBIGUOUS",
        "is_censored": label_status == "CENSORED",
        "positive_labels": positive_labels,
        "negative_labels": negative_labels,
        "unknown_labels": unknown_labels,
        "positive_count": len(positive_labels),
        "negative_count": len(negative_labels),
        "unknown_count": len(unknown_labels),
        "forecast_probabilities": probabilities,
        "top_forecast_probability_field": top_field,
        "top_forecast_probability": top_value,
        "reason_codes": reason_codes,
        "forecast_vs_outcome_v1": _to_jsonable(_coerce_mapping(metadata.get("forecast_vs_outcome_v1"))),
    }


def build_outcome_label_compact_summary(
    outcome_labels: OutcomeLabelsV1 | Mapping[str, Any] | None,
    *,
    row_key: str = "",
    forecast_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_dict = _outcome_bundle_to_dict(outcome_labels)
    bundle_metadata = _coerce_mapping(bundle_dict.get("metadata"))
    transition_payload = _coerce_mapping(bundle_dict.get("transition"))
    management_payload = _coerce_mapping(bundle_dict.get("trade_management"))
    forecast_snapshot = _coerce_mapping(forecast_snapshot)

    transition_summary = _family_shadow_summary(
        family="transition",
        family_payload=transition_payload,
        label_names=OUTCOME_LABELER_TRANSITION_LABELS_V1,
        forecast_snapshot=_coerce_mapping(forecast_snapshot.get("transition_forecast_v1")),
    )
    management_summary = _family_shadow_summary(
        family="management",
        family_payload=management_payload,
        label_names=OUTCOME_LABELER_MANAGEMENT_LABELS_V1,
        forecast_snapshot=_coerce_mapping(forecast_snapshot.get("trade_management_forecast_v1")),
    )
    label_source_descriptor = (
        _compact_label_source_descriptor(bundle_metadata.get("signal_source_descriptor"))
        or str(transition_summary.get("label_source_descriptor", "") or "")
        or str(management_summary.get("label_source_descriptor", "") or "")
    )
    return {
        "contract_version": OUTCOME_LABEL_COMPACT_SUMMARY_VERSION,
        "row_key": str(row_key or ""),
        "transition_label_status": str(transition_summary.get("label_status", "") or ""),
        "management_label_status": str(management_summary.get("label_status", "") or ""),
        "label_positive_count": int(transition_summary.get("positive_count", 0)) + int(management_summary.get("positive_count", 0)),
        "label_negative_count": int(transition_summary.get("negative_count", 0)) + int(management_summary.get("negative_count", 0)),
        "label_unknown_count": int(transition_summary.get("unknown_count", 0)) + int(management_summary.get("unknown_count", 0)),
        "label_is_ambiguous": bool(transition_summary.get("is_ambiguous")) or bool(management_summary.get("is_ambiguous")),
        "label_source_descriptor": label_source_descriptor,
        "is_censored": bool(transition_summary.get("is_censored")) or bool(management_summary.get("is_censored")),
        "transition": transition_summary,
        "management": management_summary,
    }


def _decision_context(decision_row: Mapping[str, Any] | None) -> dict[str, Any]:
    decision = _coerce_mapping(decision_row)
    return {
        "symbol": str(decision.get("symbol", "") or ""),
        "action": str(decision.get("action", "") or ""),
        "setup_id": str(decision.get("setup_id", "") or ""),
        "setup_side": str(decision.get("setup_side", "") or ""),
        "time": decision.get("time"),
        "signal_bar_ts": _to_timestamp(decision.get("signal_bar_ts")),
        "signal_timeframe": str(decision.get("signal_timeframe", "") or ""),
        "ticket": _position_key(decision),
    }


def _forecast_snapshot(decision_row: Mapping[str, Any] | None) -> dict[str, Any]:
    decision = _coerce_mapping(decision_row)
    return {
        "transition_forecast_v1": _to_jsonable(_coerce_mapping(decision.get("transition_forecast_v1"))),
        "trade_management_forecast_v1": _to_jsonable(_coerce_mapping(decision.get("trade_management_forecast_v1"))),
        "forecast_gap_metrics_v1": _to_jsonable(_coerce_mapping(decision.get("forecast_gap_metrics_v1"))),
    }


def _default_shadow_output_path(
    *,
    decision_row: Mapping[str, Any] | None,
    output_dir: str | Path | None = None,
) -> Path:
    decision = _coerce_mapping(decision_row)
    base_dir = Path(output_dir) if output_dir is not None else (_project_root() / OUTCOME_LABELER_SHADOW_OUTPUT_V1["output_targets"]["analysis_dir"])
    symbol = _slugify_token(decision.get("symbol"), fallback="symbol")
    anchor_field, anchor_value = resolve_entry_decision_anchor_time(decision)
    anchor_part = anchor_value
    if anchor_field == "time" and anchor_value not in ("", None):
        anchor_part = str(anchor_value).replace(":", "").replace("-", "").replace("T", "_")
    anchor_slug = _slugify_token(anchor_part, fallback="anchor")
    filename = f"outcome_label_shadow_{symbol}_{anchor_slug}.json"
    return base_dir / filename


def _outcome_bundle_to_dict(outcome_labels: OutcomeLabelsV1 | Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(outcome_labels, OutcomeLabelsV1):
        return outcome_labels.to_dict()
    if hasattr(outcome_labels, "to_dict") and callable(getattr(outcome_labels, "to_dict")):
        try:
            candidate = outcome_labels.to_dict()
        except TypeError:
            candidate = {}
        if isinstance(candidate, Mapping):
            return _to_jsonable(candidate)
    mapped = _coerce_mapping(outcome_labels)
    return _to_jsonable(mapped)


def _build_matched_outcome_rows(
    *,
    future_bars: Sequence[Mapping[str, Any]],
    position_context: Mapping[str, Any] | None,
    closed_trade_row: Mapping[str, Any] | None,
    position_match_meta: Mapping[str, Any],
    closed_match_meta: Mapping[str, Any],
) -> dict[str, Any]:
    future_bar_timestamps = [_row_timestamp(bar) for bar in future_bars]
    return {
        "position_context": {
            "position_key": _position_key(position_context),
            "direction": _direction_from_row(position_context),
            "source_name": str((position_context or {}).get("_source_name", "") or ""),
            "match_method": str((position_match_meta or {}).get("match_method", "") or ""),
            "candidate_count": _to_int((position_match_meta or {}).get("candidate_count"), 0),
        },
        "closed_trade_context": {
            "position_key": _position_key(closed_trade_row),
            "status": str((closed_trade_row or {}).get("status", "") or ""),
            "exit_reason": str((closed_trade_row or {}).get("exit_reason", "") or ""),
            "match_method": str((closed_match_meta or {}).get("match_method", "") or ""),
            "candidate_count": _to_int((closed_match_meta or {}).get("candidate_count"), 0),
        },
        "future_bars": {
            "count": len(future_bars),
            "timestamps": [timestamp for timestamp in future_bar_timestamps if timestamp is not None],
        },
    }


def _build_label_status_reason(
    *,
    family: str,
    label_status: str,
    horizon_bars: int,
    future_bars: Sequence[Mapping[str, Any]],
    position_match_meta: Mapping[str, Any],
    closed_match_meta: Mapping[str, Any],
    path_metrics: Mapping[str, Any],
    closed_trade_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    normalized_status = normalize_outcome_label_status(label_status)
    common_evidence = {
        "family": family,
        "label_status": normalized_status,
        "future_bar_count": len(future_bars),
        "horizon_bars": horizon_bars,
        "position_match_method": str((position_match_meta or {}).get("match_method", "") or ""),
        "closed_trade_match_method": str((closed_match_meta or {}).get("match_method", "") or ""),
        "path_is_valid": bool(path_metrics.get("is_valid")),
        "path_is_ambiguous": bool(path_metrics.get("is_ambiguous")),
    }
    close_ts = _to_timestamp((closed_trade_row or {}).get("close_ts")) or _to_timestamp((closed_trade_row or {}).get("close_time"))
    if close_ts is not None:
        common_evidence["closed_trade_close_ts"] = close_ts

    if normalized_status == "VALID":
        return _reason_block(
            "valid_complete_horizon",
            f"Future window covered the required {family} horizon and produced a unique scorable path.",
            evidence=common_evidence,
        )
    if normalized_status == "INSUFFICIENT_FUTURE_BARS":
        return _reason_block(
            "insufficient_future_bars",
            f"Only {len(future_bars)} future bars were available for the required {horizon_bars}-bar {family} horizon.",
            evidence=common_evidence,
        )
    if normalized_status == "NO_POSITION_CONTEXT":
        return _reason_block(
            "no_position_context",
            f"The anchor row could not be linked to a deterministic live-position context for {family} labeling.",
            evidence=common_evidence,
        )
    if normalized_status == "NO_EXIT_CONTEXT":
        return _reason_block(
            "no_exit_context",
            f"The row lacked closed-trade or exit context required to score {family} outcomes.",
            evidence=common_evidence,
        )
    if normalized_status == "AMBIGUOUS":
        return _reason_block(
            "ambiguous_future_path",
            f"Future path evidence remained ambiguous within the {horizon_bars}-bar {family} horizon.",
            evidence=common_evidence,
        )
    if normalized_status == "CENSORED":
        return _reason_block(
            "censored_future_path",
            f"The {family} future window was censored or interrupted before safe scoring.",
            evidence=common_evidence,
        )
    return _reason_block(
        "invalid_anchor_or_outcome_payload",
        f"The anchor row or future outcome payload was malformed for {family} labeling.",
        evidence=common_evidence,
    )


def _build_unknown_label_reason(
    *,
    label_name: str,
    label_status: str,
    label_status_reason: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_status = normalize_outcome_label_status(label_status)
    return _reason_block(
        f"unknown_due_to_{normalized_status.lower()}",
        f"{label_name} could not be scored because family status resolved to {normalized_status}.",
        evidence={
            "label_status": normalized_status,
            "status_reason_code": str((label_status_reason or {}).get("reason_code", "") or ""),
        },
    )


def _build_transition_label_reasons(
    *,
    label_values: Mapping[str, bool | None],
    label_status: str,
    label_status_reason: Mapping[str, Any],
    path_metrics: Mapping[str, Any],
    horizon_bars: int,
) -> dict[str, dict[str, Any]]:
    normalized_status = normalize_outcome_label_status(label_status)
    if normalized_status != "VALID":
        return {
            label_name: _build_unknown_label_reason(
                label_name=label_name,
                label_status=normalized_status,
                label_status_reason=label_status_reason,
            )
            for label_name in OUTCOME_LABELER_TRANSITION_LABELS_V1
        }

    dominant_side = str(path_metrics.get("dominant_side", "") or "") or "NONE"
    early_side = str(path_metrics.get("early_dominant_side", "") or "") or "NONE"
    bullish_move = _to_float(path_metrics.get("bullish_move_ratio"), 0.0)
    bearish_move = _to_float(path_metrics.get("bearish_move_ratio"), 0.0)
    net_return = _to_float(path_metrics.get("net_return_ratio"), 0.0)
    evidence = {
        "horizon_bars": horizon_bars,
        "dominant_side": dominant_side,
        "early_dominant_side": early_side,
        "bullish_move_ratio": bullish_move,
        "bearish_move_ratio": bearish_move,
        "net_return_ratio": net_return,
    }

    return {
        "buy_confirm_success_label": _reason_block(
            "same_side_confirmation_observed" if label_values.get("buy_confirm_success_label") else "buy_confirmation_not_observed",
            (
                f"Buy side stayed dominant through the {horizon_bars}-bar transition window with bullish move {bullish_move:.6f} and net return {net_return:.6f}."
                if label_values.get("buy_confirm_success_label")
                else f"Buy confirm did not hold within the {horizon_bars}-bar transition window; dominant side ended as {dominant_side} with net return {net_return:.6f}."
            ),
            evidence=evidence,
        ),
        "sell_confirm_success_label": _reason_block(
            "same_side_confirmation_observed" if label_values.get("sell_confirm_success_label") else "sell_confirmation_not_observed",
            (
                f"Sell side stayed dominant through the {horizon_bars}-bar transition window with bearish move {bearish_move:.6f} and net return {net_return:.6f}."
                if label_values.get("sell_confirm_success_label")
                else f"Sell confirm did not hold within the {horizon_bars}-bar transition window; dominant side ended as {dominant_side} with net return {net_return:.6f}."
            ),
            evidence=evidence,
        ),
        "false_break_label": _reason_block(
            "quick_invalidation_observed" if label_values.get("false_break_label") else "break_path_held",
            (
                f"An early move failed to hold through the {horizon_bars}-bar window; early side was {early_side} and final dominant side was {dominant_side}."
                if label_values.get("false_break_label")
                else f"The projected break held through the {horizon_bars}-bar window without quick invalidation; early side was {early_side} and final dominant side was {dominant_side}."
            ),
            evidence=evidence,
        ),
        "reversal_success_label": _reason_block(
            "meaningful_reversal_observed" if label_values.get("reversal_success_label") else "reversal_not_confirmed",
            (
                f"Control rotated from {early_side} to {dominant_side} within the {horizon_bars}-bar transition window, producing meaningful reversal follow-through."
                if label_values.get("reversal_success_label")
                else f"The path did not rotate into sustained opposite-direction control within {horizon_bars} bars; early side was {early_side} and final dominant side was {dominant_side}."
            ),
            evidence=evidence,
        ),
        "continuation_success_label": _reason_block(
            "same_side_continuation_observed" if label_values.get("continuation_success_label") else "continuation_not_confirmed",
            (
                f"The same side stayed in control from the early window to the close of the {horizon_bars}-bar transition horizon."
                if label_values.get("continuation_success_label")
                else f"Same-side continuation broke down within the {horizon_bars}-bar horizon; early side was {early_side} and final dominant side was {dominant_side}."
            ),
            evidence=evidence,
        ),
    }


def _build_management_label_reasons(
    *,
    label_values: Mapping[str, bool | None],
    label_status: str,
    label_status_reason: Mapping[str, Any],
    management_metrics: Mapping[str, Any],
    horizon_bars: int,
) -> dict[str, dict[str, Any]]:
    normalized_status = normalize_outcome_label_status(label_status)
    if normalized_status != "VALID":
        return {
            label_name: _build_unknown_label_reason(
                label_name=label_name,
                label_status=normalized_status,
                label_status_reason=label_status_reason,
            )
            for label_name in OUTCOME_LABELER_MANAGEMENT_LABELS_V1
        }

    position_side = str(management_metrics.get("position_side", "") or "") or "UNKNOWN"
    same_side_mfe = _to_float(management_metrics.get("same_side_mfe"), 0.0)
    opposite_side_mae = _to_float(management_metrics.get("opposite_side_mae"), 0.0)
    early_opposite_side = _to_float(management_metrics.get("early_opposite_side"), 0.0)
    realized_profit = _to_float(management_metrics.get("realized_profit"), 0.0)
    exit_reason = str(management_metrics.get("exit_reason", "") or "")
    evidence = {
        "horizon_bars": horizon_bars,
        "position_side": position_side,
        "same_side_mfe": same_side_mfe,
        "opposite_side_mae": opposite_side_mae,
        "early_opposite_side": early_opposite_side,
        "realized_profit": realized_profit,
        "exit_reason": exit_reason,
    }

    return {
        "continue_favor_label": _reason_block(
            "hold_favor_observed" if label_values.get("continue_favor_label") else "hold_favor_not_observed",
            (
                f"Same-side MFE {same_side_mfe:.6f} exceeded opposite-side MAE {opposite_side_mae:.6f} without rapid failure, so holding remained favorable."
                if label_values.get("continue_favor_label")
                else f"Holding lost edge within the {horizon_bars}-bar management window because opposite-side MAE {opposite_side_mae:.6f} challenged same-side MFE {same_side_mfe:.6f}."
            ),
            evidence=evidence,
        ),
        "fail_now_label": _reason_block(
            "rapid_failure_observed" if label_values.get("fail_now_label") else "rapid_failure_not_observed",
            (
                f"Adverse excursion {opposite_side_mae:.6f} arrived before meaningful same-side extension {same_side_mfe:.6f}, so immediate cut beat hold."
                if label_values.get("fail_now_label")
                else f"No rapid failure dominated the management window; same-side MFE {same_side_mfe:.6f} kept the position competitive."
            ),
            evidence=evidence,
        ),
        "recover_after_pullback_label": _reason_block(
            "pullback_recovery_observed" if label_values.get("recover_after_pullback_label") else "pullback_recovery_not_observed",
            (
                f"An initial pullback {early_opposite_side:.6f} was followed by recovery to same-side MFE {same_side_mfe:.6f}, so holding beat immediate cut."
                if label_values.get("recover_after_pullback_label")
                else f"The path did not recover strongly enough after pullback within the {horizon_bars}-bar management window."
            ),
            evidence=evidence,
        ),
        "reach_tp1_label": _reason_block(
            "tp1_reached" if label_values.get("reach_tp1_label") else "tp1_not_reached",
            (
                f"The realized path reached the project's TP1 observable with exit reason '{exit_reason}' and realized profit {realized_profit:.6f}."
                if label_values.get("reach_tp1_label")
                else f"No canonical TP1 event was observed within the {horizon_bars}-bar management window; exit reason was '{exit_reason}' and realized profit was {realized_profit:.6f}."
            ),
            evidence=evidence,
        ),
        "opposite_edge_reach_label": _reason_block(
            "opposite_edge_reached" if label_values.get("opposite_edge_reach_label") else "opposite_edge_not_reached",
            (
                f"The path traveled far enough to reach the projected opposite edge with same-side MFE {same_side_mfe:.6f}."
                if label_values.get("opposite_edge_reach_label")
                else f"The path stalled before the projected opposite edge; same-side MFE finished at {same_side_mfe:.6f}."
            ),
            evidence=evidence,
        ),
        "better_reentry_if_cut_label": _reason_block(
            "better_reentry_than_hold_observed" if label_values.get("better_reentry_if_cut_label") else "better_reentry_than_hold_not_observed",
            (
                f"Early adverse move {early_opposite_side:.6f} created a better cut-and-reentry path than passive hold."
                if label_values.get("better_reentry_if_cut_label")
                else f"Passive hold was at least as good as cutting and re-entering later; early adverse move was {early_opposite_side:.6f}."
            ),
            evidence=evidence,
        ),
    }


def _resolve_position_context(
    decision_row: Mapping[str, Any] | None,
    *,
    anchor_ts: float | None,
    position_rows: Sequence[Mapping[str, Any]],
    closed_trade_rows: Sequence[Mapping[str, Any]],
    runtime_snapshot_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    decision = _coerce_mapping(decision_row)
    decision_key = _position_key(decision)
    symbol = str(decision.get("symbol", "") or "").upper().strip()
    direction = _direction_from_row(decision)
    setup_side = _normalize_side(decision.get("setup_side"))

    candidate_sources = [
        ("position_rows", _coerce_rows(position_rows)),
        ("runtime_snapshot_rows", _coerce_rows(runtime_snapshot_rows)),
        ("closed_trade_rows", _coerce_rows(closed_trade_rows)),
    ]
    combined_candidates: list[dict[str, Any]] = []
    for source_name, rows in candidate_sources:
        for row in rows:
            candidate = dict(row)
            candidate["_source_name"] = source_name
            combined_candidates.append(candidate)

    if decision_key > 0:
        exact_matches = [row for row in combined_candidates if _position_key(row) == decision_key]
        if exact_matches:
            exact_matches = sorted(
                exact_matches,
                key=lambda row: (
                    0 if row.get("_source_name") == "position_rows" else 1 if row.get("_source_name") == "runtime_snapshot_rows" else 2,
                    -(_row_timestamp(row) or 0.0),
                ),
            )
            return exact_matches[0], {
                "stage": "anchor_to_position_context",
                "match_method": "exact_position_key",
                "candidate_count": len(exact_matches),
                "position_key": decision_key,
                "source_name": exact_matches[0].get("_source_name", ""),
            }

    directional_candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for candidate in combined_candidates:
        candidate_symbol = str(candidate.get("symbol", "") or "").upper().strip()
        if symbol and candidate_symbol != symbol:
            continue
        candidate_direction = _direction_from_row(candidate)
        if direction and candidate_direction and candidate_direction != direction:
            continue
        open_ts = _to_timestamp(candidate.get("open_ts"))
        if open_ts is None:
            open_ts = _to_timestamp(candidate.get("open_time"))
        if open_ts is None or anchor_ts is None:
            continue
        distance = open_ts - anchor_ts
        if distance < 0:
            continue
        sort_key = (
            distance,
            0 if candidate_direction == direction and direction else 1,
            0 if setup_side and candidate_direction == setup_side else 1,
            -open_ts,
            -_position_key(candidate),
        )
        directional_candidates.append((sort_key, candidate))

    if not directional_candidates:
        return None, {
            "stage": "anchor_to_position_context",
            "match_method": "no_match",
            "candidate_count": 0,
            "position_key": decision_key,
        }

    directional_candidates.sort(key=lambda item: item[0])
    best_key, best_row = directional_candidates[0]
    if len(directional_candidates) > 1 and directional_candidates[1][0] == best_key:
        return None, {
            "stage": "anchor_to_position_context",
            "match_method": "ambiguous_fallback_match",
            "candidate_count": len(directional_candidates),
            "position_key": decision_key,
        }
    return best_row, {
        "stage": "anchor_to_position_context",
        "match_method": "symbol_direction_open_time_fallback",
        "candidate_count": len(directional_candidates),
        "position_key": _position_key(best_row),
        "source_name": best_row.get("_source_name", ""),
    }


def _resolve_closed_trade_row(
    decision_row: Mapping[str, Any] | None,
    position_context: Mapping[str, Any] | None,
    *,
    anchor_ts: float | None,
    closed_trade_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    closed_rows = _coerce_rows(closed_trade_rows)
    if isinstance(position_context, Mapping) and position_context.get("_source_name") == "closed_trade_rows":
        return dict(position_context), {
            "stage": "position_context_to_closed_outcome",
            "match_method": "position_context_is_closed_trade",
            "candidate_count": 1,
            "position_key": _position_key(position_context),
        }

    decision = _coerce_mapping(decision_row)
    position_key = _position_key(position_context) or _position_key(decision)
    if position_key > 0:
        exact = [row for row in closed_rows if _position_key(row) == position_key]
        if exact:
            exact = sorted(exact, key=lambda row: (0 if _position_key(row) == position_key else 1, -_to_float(row.get("close_ts"), 0.0)))
            return exact[0], {
                "stage": "position_context_to_closed_outcome",
                "match_method": "exact_position_key",
                "candidate_count": len(exact),
                "position_key": position_key,
            }

    symbol = str((position_context or decision).get("symbol", "") or "").upper().strip()
    direction = _direction_from_row(position_context or decision)
    reference_open_ts = _to_timestamp((position_context or {}).get("open_ts")) or _to_timestamp((position_context or {}).get("open_time"))
    if reference_open_ts is None:
        reference_open_ts = anchor_ts
    directional_candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for row in closed_rows:
        candidate_symbol = str(row.get("symbol", "") or "").upper().strip()
        if symbol and candidate_symbol != symbol:
            continue
        candidate_direction = _direction_from_row(row)
        if direction and candidate_direction and candidate_direction != direction:
            continue
        open_ts = _to_timestamp(row.get("open_ts")) or _to_timestamp(row.get("open_time"))
        if open_ts is None or reference_open_ts is None:
            continue
        sort_key = (
            1 if position_key <= 0 else 0,
            0 if open_ts == reference_open_ts else 1,
            abs(open_ts - reference_open_ts),
            -(_to_timestamp(row.get("close_ts")) or 0.0),
        )
        directional_candidates.append((sort_key, row))

    if not directional_candidates:
        return None, {
            "stage": "position_context_to_closed_outcome",
            "match_method": "no_match",
            "candidate_count": 0,
            "position_key": position_key,
        }

    directional_candidates.sort(key=lambda item: item[0])
    best_key, best_row = directional_candidates[0]
    if len(directional_candidates) > 1 and directional_candidates[1][0] == best_key:
        return None, {
            "stage": "position_context_to_closed_outcome",
            "match_method": "ambiguous_fallback_match",
            "candidate_count": len(directional_candidates),
            "position_key": position_key,
        }
    return best_row, {
        "stage": "position_context_to_closed_outcome",
        "match_method": "symbol_direction_open_time_fallback",
        "candidate_count": len(directional_candidates),
        "position_key": _position_key(best_row),
    }


def _baseline_price(
    decision_row: Mapping[str, Any] | None,
    *,
    future_bars: Sequence[Mapping[str, Any]],
    position_context: Mapping[str, Any] | None,
    closed_trade_row: Mapping[str, Any] | None,
) -> float:
    for row, fields in (
        (position_context, ("open_price", "entry_fill_price", "entry_request_price", "price")),
        (closed_trade_row, ("open_price",)),
        (decision_row, ("entry_fill_price", "entry_request_price", "price", "open_price")),
    ):
        price = _row_price(row, fields)
        if price > 0.0:
            return price
    if future_bars:
        return _row_price(future_bars[0], ("open", "close", "price"))
    return 0.0


def _build_family_metadata(
    *,
    family: str,
    decision_row: Mapping[str, Any] | None,
    anchor_field: str,
    anchor_value: Any,
    anchor_ts: float | None,
    future_bars: Sequence[Mapping[str, Any]],
    position_context: Mapping[str, Any] | None,
    closed_trade_row: Mapping[str, Any] | None,
    position_match_meta: Mapping[str, Any],
    closed_match_meta: Mapping[str, Any],
    path_metrics: Mapping[str, Any],
    label_values: Mapping[str, bool | None],
    label_status: str,
    horizon_descriptor: Mapping[str, Any],
    label_reasons: Mapping[str, Mapping[str, Any]],
    label_status_reason: Mapping[str, Any],
) -> dict[str, Any]:
    label_contract = (
        OUTCOME_LABEL_CONTRACT_V1["transition_type"]
        if family == "transition"
        else OUTCOME_LABEL_CONTRACT_V1["trade_management_type"]
    )
    horizon_bars = _to_int(horizon_descriptor.get("horizon_bars"), 0)
    future_window_start, future_window_end = _future_window_bounds(
        future_bars,
        family=family,
        anchor_ts=anchor_ts,
        closed_trade_row=closed_trade_row,
    )
    label_polarities = {
        label_name: resolve_outcome_label_polarity(label_status=label_status, label_value=label_value)
        for label_name, label_value in label_values.items()
    }
    return {
        "engine_version": OUTCOME_LABELER_ENGINE_VERSION,
        "labeler_version": OUTCOME_LABELER_ENGINE_VERSION,
        "label_contract": label_contract,
        "family": family,
        "offline_only": True,
        "anchor_time_field": anchor_field,
        "anchor_time_value": anchor_value,
        "anchor_timestamp": anchor_ts,
        "horizon_bars": horizon_bars,
        "future_window_start": future_window_start,
        "future_window_end": future_window_end,
        "future_bar_count": len(future_bars),
        "source_files": _build_source_files_metadata(),
        "matched_outcome_rows": _build_matched_outcome_rows(
            future_bars=future_bars,
            position_context=position_context,
            closed_trade_row=closed_trade_row,
            position_match_meta=position_match_meta,
            closed_match_meta=closed_match_meta,
        ),
        "horizon_descriptor": dict(horizon_descriptor),
        "signal_source_descriptor": build_outcome_signal_source_descriptor(decision_row),
        "position_context": {
            "position_key": _position_key(position_context),
            "direction": _direction_from_row(position_context),
            "source_name": str((position_context or {}).get("_source_name", "") or ""),
            "match_meta": dict(position_match_meta or {}),
        },
        "closed_trade_context": {
            "position_key": _position_key(closed_trade_row),
            "status": str((closed_trade_row or {}).get("status", "") or ""),
            "exit_reason": str((closed_trade_row or {}).get("exit_reason", "") or ""),
            "match_meta": dict(closed_match_meta or {}),
        },
        "path_metrics": dict(path_metrics or {}),
        "label_polarities": label_polarities,
        "label_status": normalize_outcome_label_status(label_status),
        "label_status_reason": dict(label_status_reason or {}),
        "label_reasons": {
            str(label_name): dict(reason_block or {})
            for label_name, reason_block in dict(label_reasons or {}).items()
        },
    }


def label_transition_outcomes(
    decision_row: Mapping[str, Any] | None,
    *,
    future_bars: Sequence[Mapping[str, Any]] | None = None,
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    position_rows: Sequence[Mapping[str, Any]] | None = None,
    runtime_snapshot_rows: Sequence[Mapping[str, Any]] | None = None,
    is_censored: bool = False,
) -> TransitionOutcomeLabelsV1:
    decision = _coerce_mapping(decision_row)
    anchor_field, anchor_value = resolve_entry_decision_anchor_time(decision)
    anchor_ts = _to_timestamp(anchor_value)
    future_rows = _coerce_rows(future_bars)
    position_context, position_match_meta = _resolve_position_context(
        decision,
        anchor_ts=anchor_ts,
        position_rows=_coerce_rows(position_rows),
        closed_trade_rows=_coerce_rows(closed_trade_rows),
        runtime_snapshot_rows=_coerce_rows(runtime_snapshot_rows),
    )
    closed_trade_row, closed_match_meta = _resolve_closed_trade_row(
        decision,
        position_context,
        anchor_ts=anchor_ts,
        closed_trade_rows=_coerce_rows(closed_trade_rows),
    )

    sliced_future = []
    if anchor_ts is not None:
        sliced_future = _future_rows_after_anchor(
            future_rows,
            anchor_ts=anchor_ts,
        )[:OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1]

    label_status = resolve_outcome_label_status_from_flags(
        is_invalid=anchor_ts is None or not bool(decision.get("symbol")),
        has_position_context=True,
        has_future_bars=len(sliced_future) >= OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
        has_exit_context=closed_trade_row is not None,
        requires_exit_context=False,
        is_ambiguous=False,
        is_censored=_has_censoring(sliced_future, explicit_censored=is_censored),
    )

    baseline_price = _baseline_price(
        decision,
        future_bars=sliced_future,
        position_context=position_context,
        closed_trade_row=closed_trade_row,
    )
    path_metrics = _path_metrics(sliced_future, baseline_price=baseline_price) if label_status != "INVALID" else {"is_valid": False}
    if label_status == "VALID" and (not path_metrics.get("is_valid")):
        label_status = "INVALID"
    if label_status == "VALID" and bool(path_metrics.get("is_ambiguous")):
        label_status = "AMBIGUOUS"

    if label_status == "VALID":
        dominant_side = str(path_metrics.get("dominant_side", "") or "")
        early_side = str(path_metrics.get("early_dominant_side", "") or "")
        bullish_move = _to_float(path_metrics.get("bullish_move_ratio"), 0.0)
        bearish_move = _to_float(path_metrics.get("bearish_move_ratio"), 0.0)
        net_return = _to_float(path_metrics.get("net_return_ratio"), 0.0)
        early_max_move = max(
            _to_float(path_metrics.get("early_bullish_move_ratio"), 0.0),
            _to_float(path_metrics.get("early_bearish_move_ratio"), 0.0),
        )
        reversal_positive = (
            early_side in {"BUY", "SELL"}
            and dominant_side in {"BUY", "SELL"}
            and dominant_side != early_side
            and max(bullish_move, bearish_move) >= _MIN_DIRECTIONAL_MOVE_RATIO
            and abs(net_return) >= _PULLBACK_MOVE_RATIO
        )
        continuation_positive = (
            early_side in {"BUY", "SELL"}
            and dominant_side == early_side
            and max(bullish_move, bearish_move) >= _MIN_DIRECTIONAL_MOVE_RATIO
            and (
                (dominant_side == "BUY" and net_return > 0.0)
                or (dominant_side == "SELL" and net_return < 0.0)
            )
        )
        false_break_positive = (
            early_max_move >= _MIN_DIRECTIONAL_MOVE_RATIO
            and (
                dominant_side in {"", "AMBIGUOUS"}
                or abs(net_return) <= _FLAT_RETURN_RATIO
                or (early_side in {"BUY", "SELL"} and dominant_side in {"BUY", "SELL"} and dominant_side != early_side and not reversal_positive)
            )
        )
        label_values: dict[str, bool | None] = {
            "buy_confirm_success_label": dominant_side == "BUY" and bullish_move >= _MIN_DIRECTIONAL_MOVE_RATIO and net_return > -_FLAT_RETURN_RATIO,
            "sell_confirm_success_label": dominant_side == "SELL" and bearish_move >= _MIN_DIRECTIONAL_MOVE_RATIO and net_return < _FLAT_RETURN_RATIO,
            "false_break_label": bool(false_break_positive),
            "reversal_success_label": bool(reversal_positive),
            "continuation_success_label": bool(continuation_positive),
        }
    else:
        label_values = {
            "buy_confirm_success_label": None,
            "sell_confirm_success_label": None,
            "false_break_label": None,
            "reversal_success_label": None,
            "continuation_success_label": None,
        }
    label_status = normalize_outcome_label_status(label_status)
    label_status_reason = _build_label_status_reason(
        family="transition",
        label_status=label_status,
        horizon_bars=OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
        future_bars=sliced_future,
        position_match_meta=position_match_meta,
        closed_match_meta=closed_match_meta,
        path_metrics=path_metrics,
        closed_trade_row=closed_trade_row,
    )
    label_reasons = _build_transition_label_reasons(
        label_values=label_values,
        label_status=label_status,
        label_status_reason=label_status_reason,
        path_metrics=path_metrics,
        horizon_bars=OUTCOME_LABELER_TRANSITION_HORIZON_BARS_V1,
    )

    metadata = _build_family_metadata(
        family="transition",
        decision_row=decision,
        anchor_field=anchor_field,
        anchor_value=anchor_value,
        anchor_ts=anchor_ts,
        future_bars=sliced_future,
        position_context=position_context,
        closed_trade_row=closed_trade_row,
        position_match_meta=position_match_meta,
        closed_match_meta=closed_match_meta,
        path_metrics=path_metrics,
        label_values=label_values,
        label_status=label_status,
        horizon_descriptor=build_transition_horizon_descriptor(),
        label_reasons=label_reasons,
        label_status_reason=label_status_reason,
    )
    return TransitionOutcomeLabelsV1(
        buy_confirm_success_label=label_values["buy_confirm_success_label"],
        sell_confirm_success_label=label_values["sell_confirm_success_label"],
        false_break_label=label_values["false_break_label"],
        reversal_success_label=label_values["reversal_success_label"],
        continuation_success_label=label_values["continuation_success_label"],
        label_status=label_status,
        metadata=metadata,
    )


def label_management_outcomes(
    decision_row: Mapping[str, Any] | None,
    *,
    future_bars: Sequence[Mapping[str, Any]] | None = None,
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    position_rows: Sequence[Mapping[str, Any]] | None = None,
    runtime_snapshot_rows: Sequence[Mapping[str, Any]] | None = None,
    is_censored: bool = False,
) -> TradeManagementOutcomeLabelsV1:
    decision = _coerce_mapping(decision_row)
    anchor_field, anchor_value = resolve_entry_decision_anchor_time(decision)
    anchor_ts = _to_timestamp(anchor_value)
    future_rows = _coerce_rows(future_bars)
    position_context, position_match_meta = _resolve_position_context(
        decision,
        anchor_ts=anchor_ts,
        position_rows=_coerce_rows(position_rows),
        closed_trade_rows=_coerce_rows(closed_trade_rows),
        runtime_snapshot_rows=_coerce_rows(runtime_snapshot_rows),
    )
    closed_trade_row, closed_match_meta = _resolve_closed_trade_row(
        decision,
        position_context,
        anchor_ts=anchor_ts,
        closed_trade_rows=_coerce_rows(closed_trade_rows),
    )

    close_ts = _to_timestamp((closed_trade_row or {}).get("close_ts")) or _to_timestamp((closed_trade_row or {}).get("close_time"))
    sliced_future = []
    if anchor_ts is not None:
        sliced_future = _future_rows_after_anchor(
            future_rows,
            anchor_ts=anchor_ts,
            cap_ts=close_ts,
        )[:OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1]

    position_context_available = position_context is not None or _position_key(closed_trade_row) > 0
    exit_context_available = closed_trade_row is not None
    horizon_complete = len(sliced_future) >= OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1 or bool(
        close_ts is not None and anchor_ts is not None and close_ts > anchor_ts
    )
    label_status = resolve_outcome_label_status_from_flags(
        is_invalid=anchor_ts is None or not bool(decision.get("symbol")),
        has_position_context=position_context_available,
        has_future_bars=horizon_complete,
        has_exit_context=exit_context_available,
        requires_exit_context=True,
        is_ambiguous=False,
        is_censored=_has_censoring(sliced_future, explicit_censored=is_censored),
    )

    baseline_price = _baseline_price(
        decision,
        future_bars=sliced_future,
        position_context=position_context,
        closed_trade_row=closed_trade_row,
    )
    path_metrics = _path_metrics(sliced_future, baseline_price=baseline_price) if label_status != "INVALID" else {"is_valid": False}
    if label_status == "VALID" and (not path_metrics.get("is_valid")):
        if exit_context_available:
            path_metrics = {
                "is_valid": True,
                "bar_count": 0,
                "bullish_move_ratio": 0.0,
                "bearish_move_ratio": 0.0,
                "net_return_ratio": 0.0,
                "early_bullish_move_ratio": 0.0,
                "early_bearish_move_ratio": 0.0,
                "early_dominant_side": "",
                "dominant_side": "",
                "is_ambiguous": False,
            }
        else:
            label_status = "INVALID"
    if label_status == "VALID" and bool(path_metrics.get("is_ambiguous")):
        label_status = "AMBIGUOUS"

    if label_status == "VALID":
        position_side = _direction_from_row(position_context or closed_trade_row or decision)
        same_side_mfe, opposite_side_mae, _early_same_side, early_opposite_side = _same_side_metrics(
            path_metrics,
            position_side=position_side or "BUY",
        )
        net_return = _to_float(path_metrics.get("net_return_ratio"), 0.0)
        same_side_net = net_return if position_side != "SELL" else -net_return
        realized_profit = _to_float(
            (closed_trade_row or {}).get("net_pnl_after_cost"),
            _to_float((closed_trade_row or {}).get("profit"), 0.0),
        )
        exit_reason = str((closed_trade_row or {}).get("exit_reason", "") or "").strip()
        recovered = (
            early_opposite_side >= max(_PULLBACK_MOVE_RATIO, same_side_mfe * 0.25)
            and same_side_mfe > early_opposite_side * 1.1
            and same_side_net > 0.0
        )
        fail_now = opposite_side_mae >= max(same_side_mfe * 1.15, _MIN_DIRECTIONAL_MOVE_RATIO) and same_side_net <= _PULLBACK_MOVE_RATIO
        tp1_hit = "RECOVERY TP1" in exit_reason.upper() or realized_profit >= float(getattr(Config, "EXIT_RECOVERY_TP1_CLOSE_USD", 0.12))
        opposite_edge_reach = "OPPOSITE_EDGE" in exit_reason.upper() or same_side_mfe >= _EDGE_TRAVEL_RATIO
        better_reentry = (
            early_opposite_side >= _PULLBACK_MOVE_RATIO
            and same_side_mfe >= _MIN_DIRECTIONAL_MOVE_RATIO
            and early_opposite_side >= same_side_mfe * 0.55
        )
        label_values: dict[str, bool | None] = {
            "continue_favor_label": same_side_mfe > max(opposite_side_mae * 1.2, _MIN_DIRECTIONAL_MOVE_RATIO) and not fail_now,
            "fail_now_label": bool(fail_now),
            "recover_after_pullback_label": bool(recovered and not fail_now),
            "reach_tp1_label": bool(tp1_hit),
            "opposite_edge_reach_label": bool(opposite_edge_reach),
            "better_reentry_if_cut_label": bool(better_reentry and not fail_now),
        }
    else:
        label_values = {
            "continue_favor_label": None,
            "fail_now_label": None,
            "recover_after_pullback_label": None,
            "reach_tp1_label": None,
            "opposite_edge_reach_label": None,
            "better_reentry_if_cut_label": None,
        }
        position_side = _direction_from_row(position_context or closed_trade_row or decision)
        same_side_mfe = 0.0
        opposite_side_mae = 0.0
        early_opposite_side = 0.0
        realized_profit = _to_float(
            (closed_trade_row or {}).get("net_pnl_after_cost"),
            _to_float((closed_trade_row or {}).get("profit"), 0.0),
        )
        exit_reason = str((closed_trade_row or {}).get("exit_reason", "") or "").strip()

    label_status = normalize_outcome_label_status(label_status)
    label_status_reason = _build_label_status_reason(
        family="management",
        label_status=label_status,
        horizon_bars=OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
        future_bars=sliced_future,
        position_match_meta=position_match_meta,
        closed_match_meta=closed_match_meta,
        path_metrics=path_metrics,
        closed_trade_row=closed_trade_row,
    )
    label_reasons = _build_management_label_reasons(
        label_values=label_values,
        label_status=label_status,
        label_status_reason=label_status_reason,
        management_metrics={
            "position_side": position_side,
            "same_side_mfe": same_side_mfe,
            "opposite_side_mae": opposite_side_mae,
            "early_opposite_side": early_opposite_side,
            "realized_profit": realized_profit,
            "exit_reason": exit_reason,
        },
        horizon_bars=OUTCOME_LABELER_MANAGEMENT_HORIZON_BARS_V1,
    )

    metadata = _build_family_metadata(
        family="management",
        decision_row=decision,
        anchor_field=anchor_field,
        anchor_value=anchor_value,
        anchor_ts=anchor_ts,
        future_bars=sliced_future,
        position_context=position_context,
        closed_trade_row=closed_trade_row,
        position_match_meta=position_match_meta,
        closed_match_meta=closed_match_meta,
        path_metrics=path_metrics,
        label_values=label_values,
        label_status=label_status,
        horizon_descriptor=build_management_horizon_descriptor(),
        label_reasons=label_reasons,
        label_status_reason=label_status_reason,
    )
    return TradeManagementOutcomeLabelsV1(
        continue_favor_label=label_values["continue_favor_label"],
        fail_now_label=label_values["fail_now_label"],
        recover_after_pullback_label=label_values["recover_after_pullback_label"],
        reach_tp1_label=label_values["reach_tp1_label"],
        opposite_edge_reach_label=label_values["opposite_edge_reach_label"],
        better_reentry_if_cut_label=label_values["better_reentry_if_cut_label"],
        label_status=label_status,
        metadata=metadata,
    )


def build_outcome_labels(
    decision_row: Mapping[str, Any] | None,
    *,
    future_bars: Sequence[Mapping[str, Any]] | None = None,
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    position_rows: Sequence[Mapping[str, Any]] | None = None,
    runtime_snapshot_rows: Sequence[Mapping[str, Any]] | None = None,
    is_censored: bool = False,
) -> OutcomeLabelsV1:
    transition = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=closed_trade_rows,
        position_rows=position_rows,
        runtime_snapshot_rows=runtime_snapshot_rows,
        is_censored=is_censored,
    )
    trade_management = label_management_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=closed_trade_rows,
        position_rows=position_rows,
        runtime_snapshot_rows=runtime_snapshot_rows,
        is_censored=is_censored,
    )
    decision = _coerce_mapping(decision_row)
    anchor_field, anchor_value = resolve_entry_decision_anchor_time(decision)
    forecast_snapshot = _forecast_snapshot(decision)
    forecast_branch_evaluation = _build_forecast_branch_evaluation(
        forecast_snapshot=forecast_snapshot,
        transition_payload=transition.to_dict(),
        management_payload=trade_management.to_dict(),
    )
    transition.metadata["forecast_vs_outcome_v1"] = _coerce_mapping(
        forecast_branch_evaluation.get("transition_forecast_vs_outcome")
    )
    trade_management.metadata["forecast_vs_outcome_v1"] = _coerce_mapping(
        forecast_branch_evaluation.get("management_forecast_vs_outcome")
    )
    return OutcomeLabelsV1(
        transition=transition,
        trade_management=trade_management,
        metadata={
            "engine_version": OUTCOME_LABELER_ENGINE_VERSION,
            "labeler_version": OUTCOME_LABELER_ENGINE_VERSION,
            "label_contract": OUTCOME_LABEL_CONTRACT_V1["bundle_type"],
            "offline_only": True,
            "anchor_time_field": anchor_field,
            "anchor_time_value": anchor_value,
            "symbol": str(decision.get("symbol", "") or ""),
            "action": str(decision.get("action", "") or ""),
            "transition_status": transition.label_status,
            "trade_management_status": trade_management.label_status,
            "signal_source_descriptor": build_outcome_signal_source_descriptor(decision),
            "source_files": _build_source_files_metadata(),
            "forecast_branch_evaluation_v1": forecast_branch_evaluation,
        },
    )


def build_outcome_label_shadow_row(
    decision_row: Mapping[str, Any] | None,
    *,
    outcome_labels: OutcomeLabelsV1 | Mapping[str, Any] | None = None,
    future_bars: Sequence[Mapping[str, Any]] | None = None,
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    position_rows: Sequence[Mapping[str, Any]] | None = None,
    runtime_snapshot_rows: Sequence[Mapping[str, Any]] | None = None,
    is_censored: bool = False,
) -> dict[str, Any]:
    decision = _coerce_mapping(decision_row)
    row_key = resolve_entry_decision_row_key(decision)
    bundle = outcome_labels or build_outcome_labels(
        decision,
        future_bars=future_bars,
        closed_trade_rows=closed_trade_rows,
        position_rows=position_rows,
        runtime_snapshot_rows=runtime_snapshot_rows,
        is_censored=is_censored,
    )
    bundle_dict = _outcome_bundle_to_dict(bundle)
    forecast_snapshot = _forecast_snapshot(decision)
    compact_summary = build_outcome_label_compact_summary(
        bundle_dict,
        row_key=row_key,
        forecast_snapshot=forecast_snapshot,
    )
    return {
        "row_type": OUTCOME_LABELER_SHADOW_OUTPUT_V1["row_type"],
        "shadow_output_contract": OUTCOME_LABELER_SHADOW_OUTPUT_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "row_key": row_key,
        "decision_context": _to_jsonable(_decision_context(decision)),
        "forecast_snapshot": forecast_snapshot,
        "outcome_labels_v1": bundle_dict,
        "forecast_branch_evaluation_v1": _to_jsonable(
            _coerce_mapping(_coerce_mapping(bundle_dict.get("metadata")).get("forecast_branch_evaluation_v1"))
        ),
        "label_quality_summary_v1": compact_summary,
        "transition_label_summary": _coerce_mapping(compact_summary.get("transition")),
        "management_label_summary": _coerce_mapping(compact_summary.get("management")),
    }


def write_outcome_label_shadow_output(
    decision_row: Mapping[str, Any] | None,
    *,
    outcome_labels: OutcomeLabelsV1 | Mapping[str, Any] | None = None,
    future_bars: Sequence[Mapping[str, Any]] | None = None,
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    position_rows: Sequence[Mapping[str, Any]] | None = None,
    runtime_snapshot_rows: Sequence[Mapping[str, Any]] | None = None,
    is_censored: bool = False,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    shadow_row = build_outcome_label_shadow_row(
        decision_row,
        outcome_labels=outcome_labels,
        future_bars=future_bars,
        closed_trade_rows=closed_trade_rows,
        position_rows=position_rows,
        runtime_snapshot_rows=runtime_snapshot_rows,
        is_censored=is_censored,
    )
    path = Path(output_path) if output_path is not None else _default_shadow_output_path(
        decision_row=decision_row,
        output_dir=output_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(shadow_row, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
