"""Entry-side wait quality audit helpers.

This module does not change live entry behavior yet. It defines a shadow-only
audit contract for answering whether a skipped/waited entry was helpful or
harmful after the fact.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


ENTRY_WAIT_QUALITY_AUDIT_CONTRACT_V1 = "entry_wait_quality_audit_v1"
ENTRY_WAIT_QUALITY_SUMMARY_CONTRACT_V1 = "entry_wait_quality_summary_v1"

ENTRY_WAIT_QUALITY_LABEL_BETTER_ENTRY = "better_entry_after_wait"
ENTRY_WAIT_QUALITY_LABEL_AVOIDED_LOSS = "avoided_loss_by_wait"
ENTRY_WAIT_QUALITY_LABEL_MISSED_MOVE = "missed_move_by_wait"
ENTRY_WAIT_QUALITY_LABEL_DELAYED_LOSS = "delayed_loss_after_wait"
ENTRY_WAIT_QUALITY_LABEL_NEUTRAL = "neutral_wait"
ENTRY_WAIT_QUALITY_LABEL_INSUFFICIENT = "insufficient_evidence"

ENTRY_WAIT_QUALITY_VALID_LABELS = {
    ENTRY_WAIT_QUALITY_LABEL_BETTER_ENTRY,
    ENTRY_WAIT_QUALITY_LABEL_AVOIDED_LOSS,
    ENTRY_WAIT_QUALITY_LABEL_MISSED_MOVE,
    ENTRY_WAIT_QUALITY_LABEL_DELAYED_LOSS,
    ENTRY_WAIT_QUALITY_LABEL_NEUTRAL,
    ENTRY_WAIT_QUALITY_LABEL_INSUFFICIENT,
}

DEFAULT_MEANINGFUL_MOVE_RATIO = 0.00035
DEFAULT_BETTER_ENTRY_RATIO = 0.0002
DEFAULT_WORSE_ENTRY_RATIO = 0.0002


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _coerce_rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        mapped = _as_mapping(item)
        if mapped:
            rows.append(mapped)
    return rows


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _normalize_side(value: object) -> str:
    side = _to_str(value).upper()
    if side in {"BUY", "SELL"}:
        return side
    return ""


def _row_timestamp(row: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(row)
    for key in ("signal_bar_ts", "time", "timestamp", "ts"):
        resolved = _to_float(mapped.get(key), 0.0)
        if resolved > 0.0:
            return resolved
    return 0.0


def _resolve_bar_high(bar: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(bar)
    for key in ("high", "close", "open", "price"):
        value = _to_float(mapped.get(key), 0.0)
        if value > 0.0:
            return value
    return 0.0


def _resolve_bar_low(bar: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(bar)
    for key in ("low", "close", "open", "price"):
        value = _to_float(mapped.get(key), 0.0)
        if value > 0.0:
            return value
    return 0.0


def _resolve_anchor_price(row: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(row)
    for key in (
        "anchor_price",
        "signal_price",
        "decision_price",
        "entry_request_price",
        "entry_fill_price",
        "price",
        "close",
        "open",
    ):
        value = _to_float(mapped.get(key), 0.0)
        if value > 0.0:
            return value
    return 0.0


def _resolve_next_entry_price(row: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(row)
    for key in ("entry_fill_price", "entry_request_price", "open_price", "price", "close"):
        value = _to_float(mapped.get(key), 0.0)
        if value > 0.0:
            return value
    return 0.0


def _sort_rows_by_ts(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted((_as_mapping(row) for row in rows), key=_row_timestamp)


def _side_metrics(
    *,
    side: str,
    anchor_price: float,
    future_bars: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    if anchor_price <= 0.0:
        return {
            "favorable_move_ratio": 0.0,
            "adverse_move_ratio": 0.0,
            "best_reentry_improvement_ratio": 0.0,
        }
    highs = [_resolve_bar_high(bar) for bar in future_bars]
    lows = [_resolve_bar_low(bar) for bar in future_bars]
    highs = [value for value in highs if value > 0.0]
    lows = [value for value in lows if value > 0.0]
    if not highs or not lows:
        return {
            "favorable_move_ratio": 0.0,
            "adverse_move_ratio": 0.0,
            "best_reentry_improvement_ratio": 0.0,
        }
    if side == "BUY":
        favorable_move_ratio = max(0.0, (max(highs) - anchor_price) / anchor_price)
        adverse_move_ratio = max(0.0, (anchor_price - min(lows)) / anchor_price)
        best_reentry_improvement_ratio = max(0.0, (anchor_price - min(lows)) / anchor_price)
    else:
        favorable_move_ratio = max(0.0, (anchor_price - min(lows)) / anchor_price)
        adverse_move_ratio = max(0.0, (max(highs) - anchor_price) / anchor_price)
        best_reentry_improvement_ratio = max(0.0, (max(highs) - anchor_price) / anchor_price)
    return {
        "favorable_move_ratio": round(float(favorable_move_ratio), 6),
        "adverse_move_ratio": round(float(adverse_move_ratio), 6),
        "best_reentry_improvement_ratio": round(float(best_reentry_improvement_ratio), 6),
    }


def _entry_price_delta_ratio(*, side: str, anchor_price: float, next_entry_price: float) -> float:
    if anchor_price <= 0.0 or next_entry_price <= 0.0:
        return 0.0
    if side == "BUY":
        return round(float((anchor_price - next_entry_price) / anchor_price), 6)
    return round(float((next_entry_price - anchor_price) / anchor_price), 6)


def build_entry_wait_quality_context_v1(
    *,
    decision_row: Mapping[str, Any] | None = None,
    future_bars: Sequence[Mapping[str, Any]] | None = None,
    next_entry_row: Mapping[str, Any] | None = None,
    next_closed_trade_row: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision = _as_mapping(decision_row)
    next_entry = _as_mapping(next_entry_row)
    next_trade = _as_mapping(next_closed_trade_row)
    side = _normalize_side(
        decision.get("action")
        or decision.get("observe_side")
        or next_entry.get("action")
        or next_trade.get("direction")
    )
    anchor_price = _resolve_anchor_price(decision)
    future = _sort_rows_by_ts(_coerce_rows(future_bars))
    next_entry_price = _resolve_next_entry_price(next_entry)
    next_trade_profit = _to_float(next_trade.get("profit", next_trade.get("net_pnl_after_cost", 0.0)), 0.0)

    return {
        "contract_version": ENTRY_WAIT_QUALITY_AUDIT_CONTRACT_V1,
        "decision": {
            "symbol": _to_str(decision.get("symbol", "")).upper(),
            "side": side,
            "time": _to_str(decision.get("time", "")),
            "signal_bar_ts": _to_float(decision.get("signal_bar_ts"), 0.0),
            "wait_selected": _to_bool(decision.get("entry_wait_selected", False)),
            "wait_state": _to_str(decision.get("entry_wait_state", "")).upper(),
            "wait_decision": _to_str(decision.get("entry_wait_decision", "")).lower(),
            "blocked_by": _to_str(decision.get("blocked_by", "")),
            "observe_reason": _to_str(decision.get("observe_reason", "")),
            "anchor_price": float(anchor_price),
        },
        "future_window": {
            "bar_count": len(future),
            "future_bars": list(future),
        },
        "next_entry": {
            "present": bool(next_entry),
            "time": _to_str(next_entry.get("time", "")),
            "side": _normalize_side(next_entry.get("action")),
            "entry_price": float(next_entry_price),
            "outcome": _to_str(next_entry.get("outcome", "")).lower(),
        },
        "next_trade": {
            "present": bool(next_trade),
            "profit": float(next_trade_profit),
            "exit_reason": _to_str(next_trade.get("exit_reason", "")),
        },
        "thresholds": {
            "meaningful_move_ratio": float(DEFAULT_MEANINGFUL_MOVE_RATIO),
            "better_entry_ratio": float(DEFAULT_BETTER_ENTRY_RATIO),
            "worse_entry_ratio": float(DEFAULT_WORSE_ENTRY_RATIO),
        },
    }


def evaluate_entry_wait_quality_v1(
    *,
    decision_row: Mapping[str, Any] | None = None,
    future_bars: Sequence[Mapping[str, Any]] | None = None,
    next_entry_row: Mapping[str, Any] | None = None,
    next_closed_trade_row: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = _as_mapping(context) or build_entry_wait_quality_context_v1(
        decision_row=decision_row,
        future_bars=future_bars,
        next_entry_row=next_entry_row,
        next_closed_trade_row=next_closed_trade_row,
    )
    decision = _as_mapping(ctx.get("decision"))
    future_window = _as_mapping(ctx.get("future_window"))
    next_entry = _as_mapping(ctx.get("next_entry"))
    next_trade = _as_mapping(ctx.get("next_trade"))
    thresholds = _as_mapping(ctx.get("thresholds"))

    side = _normalize_side(decision.get("side"))
    anchor_price = _to_float(decision.get("anchor_price"), 0.0)
    future_rows = _coerce_rows(future_window.get("future_bars"))
    meaningful_move_ratio = _to_float(thresholds.get("meaningful_move_ratio"), DEFAULT_MEANINGFUL_MOVE_RATIO)
    better_entry_ratio = _to_float(thresholds.get("better_entry_ratio"), DEFAULT_BETTER_ENTRY_RATIO)
    worse_entry_ratio = _to_float(thresholds.get("worse_entry_ratio"), DEFAULT_WORSE_ENTRY_RATIO)
    next_entry_price = _to_float(next_entry.get("entry_price"), 0.0)
    next_trade_present = _to_bool(next_trade.get("present"), False)
    next_trade_profit = _to_float(next_trade.get("profit"), 0.0)
    reentry_context_available = bool(next_entry_price > 0.0 and next_trade_present)

    if not side or anchor_price <= 0.0 or (not future_rows and not reentry_context_available):
        return {
            "contract_version": ENTRY_WAIT_QUALITY_AUDIT_CONTRACT_V1,
            "label_status": "INSUFFICIENT_EVIDENCE",
            "quality_label": ENTRY_WAIT_QUALITY_LABEL_INSUFFICIENT,
            "quality_score": 0.0,
            "reason_codes": ["missing_side_anchor_or_future"],
            "metrics": {
                "anchor_price": float(anchor_price),
                "future_bar_count": len(future_rows),
            },
            "context": dict(ctx),
        }

    metrics = _side_metrics(side=side, anchor_price=anchor_price, future_bars=future_rows)
    entry_price_delta_ratio = _entry_price_delta_ratio(
        side=side,
        anchor_price=anchor_price,
        next_entry_price=next_entry_price,
    )

    label = ENTRY_WAIT_QUALITY_LABEL_NEUTRAL
    label_status = "VALID"
    score = 0.0
    reason_codes: list[str] = []

    if (
        reentry_context_available
        and entry_price_delta_ratio >= better_entry_ratio
        and next_trade_profit >= 0.0
    ):
        label = ENTRY_WAIT_QUALITY_LABEL_BETTER_ENTRY
        score = min(1.0, 0.45 + (entry_price_delta_ratio * 1200.0))
        reason_codes = ["better_reentry_price", "next_trade_non_negative"]
    elif (
        reentry_context_available
        and entry_price_delta_ratio <= (-worse_entry_ratio)
        and next_trade_profit < 0.0
    ):
        label = ENTRY_WAIT_QUALITY_LABEL_DELAYED_LOSS
        score = max(-1.0, -0.45 + (entry_price_delta_ratio * 900.0))
        reason_codes = ["worse_reentry_price", "next_trade_negative"]
    elif not future_rows:
        return {
            "contract_version": ENTRY_WAIT_QUALITY_AUDIT_CONTRACT_V1,
            "label_status": "INSUFFICIENT_EVIDENCE",
            "quality_label": ENTRY_WAIT_QUALITY_LABEL_INSUFFICIENT,
            "quality_score": 0.0,
            "reason_codes": ["missing_future_bars_for_move_assessment"],
            "metrics": {
                "anchor_price": float(anchor_price),
                "next_entry_price": float(next_entry_price),
                "next_trade_profit": float(next_trade_profit),
                "entry_price_delta_ratio": float(entry_price_delta_ratio),
                "future_bar_count": 0,
            },
            "context": dict(ctx),
        }
    elif (
        next_entry_price <= 0.0
        and _to_float(metrics.get("adverse_move_ratio"), 0.0) >= meaningful_move_ratio
        and _to_float(metrics.get("favorable_move_ratio"), 0.0) < meaningful_move_ratio
    ):
        label = ENTRY_WAIT_QUALITY_LABEL_AVOIDED_LOSS
        score = min(1.0, 0.35 + (_to_float(metrics.get("adverse_move_ratio"), 0.0) * 800.0))
        reason_codes = ["adverse_move_avoided", "no_same_side_reentry"]
    elif (
        _to_float(metrics.get("favorable_move_ratio"), 0.0) >= meaningful_move_ratio
        and _to_float(metrics.get("best_reentry_improvement_ratio"), 0.0) < better_entry_ratio
        and next_entry_price <= 0.0
    ):
        label = ENTRY_WAIT_QUALITY_LABEL_MISSED_MOVE
        score = max(-1.0, -0.35 - (_to_float(metrics.get("favorable_move_ratio"), 0.0) * 800.0))
        reason_codes = ["same_side_move_happened", "no_better_reentry_seen"]
    else:
        label = ENTRY_WAIT_QUALITY_LABEL_NEUTRAL
        score = 0.0
        reason_codes = ["mixed_or_small_signal"]

    return {
        "contract_version": ENTRY_WAIT_QUALITY_AUDIT_CONTRACT_V1,
        "label_status": str(label_status),
        "quality_label": str(label),
        "quality_score": round(float(score), 4),
        "reason_codes": list(reason_codes),
        "metrics": {
            "anchor_price": float(anchor_price),
            "next_entry_price": float(next_entry_price),
            "next_trade_profit": float(next_trade_profit),
            "entry_price_delta_ratio": float(entry_price_delta_ratio),
            **{key: float(value) for key, value in metrics.items()},
            "future_bar_count": len(future_rows),
        },
        "context": dict(ctx),
    }


def build_entry_wait_quality_summary_v1(
    audit_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = [_as_mapping(item) for item in (audit_rows or [])]
    counts = {label: 0 for label in ENTRY_WAIT_QUALITY_VALID_LABELS}
    valid_rows = 0
    positive_rows = 0
    negative_rows = 0
    for row in rows:
        label = _to_str(row.get("quality_label", ENTRY_WAIT_QUALITY_LABEL_INSUFFICIENT)).lower()
        if label not in counts:
            counts[label] = 0
        counts[label] += 1
        if _to_str(row.get("label_status", "")).upper() == "VALID":
            valid_rows += 1
        score = _to_float(row.get("quality_score"), 0.0)
        if score > 0.0:
            positive_rows += 1
        elif score < 0.0:
            negative_rows += 1

    return {
        "contract_version": ENTRY_WAIT_QUALITY_SUMMARY_CONTRACT_V1,
        "rows_total": len(rows),
        "rows_valid": int(valid_rows),
        "positive_rows": int(positive_rows),
        "negative_rows": int(negative_rows),
        "label_counts": dict(counts),
    }


def render_entry_wait_quality_markdown(summary: Mapping[str, Any] | None = None) -> str:
    payload = _as_mapping(summary)
    label_counts = _as_mapping(payload.get("label_counts"))
    lines = [
        "# Entry Wait Quality Summary",
        "",
        f"- rows_total: {int(_to_float(payload.get('rows_total'), 0))}",
        f"- rows_valid: {int(_to_float(payload.get('rows_valid'), 0))}",
        f"- positive_rows: {int(_to_float(payload.get('positive_rows'), 0))}",
        f"- negative_rows: {int(_to_float(payload.get('negative_rows'), 0))}",
        "",
        "## Label Counts",
    ]
    for label in (
        ENTRY_WAIT_QUALITY_LABEL_BETTER_ENTRY,
        ENTRY_WAIT_QUALITY_LABEL_AVOIDED_LOSS,
        ENTRY_WAIT_QUALITY_LABEL_MISSED_MOVE,
        ENTRY_WAIT_QUALITY_LABEL_DELAYED_LOSS,
        ENTRY_WAIT_QUALITY_LABEL_NEUTRAL,
        ENTRY_WAIT_QUALITY_LABEL_INSUFFICIENT,
    ):
        lines.append(f"- {label}: {int(_to_float(label_counts.get(label), 0))}")
    return "\n".join(lines).strip() + "\n"
