from __future__ import annotations

import argparse
import bisect
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUT_DIR = ROOT / "data" / "analysis" / "state_forecast_validation"
DEFAULT_TRADES_ROOT = ROOT / "data" / "trades"
DEFAULT_SF3_REPORT = OUT_DIR / "state_forecast_validation_sf3_usage_latest.json"
REPORT_VERSION = "state_forecast_validation_sf4_value_slice_audit_v1"

ENTRY_BUCKETS: list[tuple[float, float | None, str]] = [
    (0.00, 0.05, "0.00~0.05"),
    (0.05, 0.10, "0.05~0.10"),
    (0.10, 0.20, "0.10~0.20"),
    (0.20, 0.35, "0.20~0.35"),
    (0.35, None, "0.35+"),
]

METRIC_SPECS: dict[str, dict[str, str]] = {
    "p_buy_confirm": {
        "branch_role": "transition_branch",
        "label_field": "buy_confirm_proxy",
        "label_kind": "decision_proxy",
        "description": "BUY confirm score should separate BUY-path rows from non-BUY rows",
    },
    "p_sell_confirm": {
        "branch_role": "transition_branch",
        "label_field": "sell_confirm_proxy",
        "label_kind": "decision_proxy",
        "description": "SELL confirm score should separate SELL-path rows from non-SELL rows",
    },
    "p_false_break": {
        "branch_role": "transition_branch",
        "label_field": "false_break_proxy",
        "label_kind": "decision_proxy",
        "description": "false-break score should separate WAIT/observe rows from directional rows",
    },
    "p_continue_favor": {
        "branch_role": "trade_management_branch",
        "label_field": "continue_favor_proxy",
        "label_kind": "matched_trade_actual",
        "description": "continue-favor score should separate profitable matched trades from losing trades",
    },
    "p_fail_now": {
        "branch_role": "trade_management_branch",
        "label_field": "fail_now_proxy",
        "label_kind": "matched_trade_actual",
        "description": "fail-now score should separate losing matched trades from profitable trades",
    },
}

BRANCH_TO_METRICS = {
    "transition_branch": ["p_buy_confirm", "p_sell_confirm", "p_false_break"],
    "trade_management_branch": ["p_continue_favor", "p_fail_now"],
}
HARVEST_SECTIONS = ["state_harvest", "belief_harvest", "barrier_harvest", "secondary_harvest"]


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any) -> float | None:
    text = _coerce_text(value)
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator > 0 else 0.0


def _safe_avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _decode_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    text = _coerce_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _parse_dt(value: Any) -> datetime | None:
    text = _coerce_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _bucket_label(score: float | None) -> str | None:
    if score is None:
        return None
    for lower, upper, label in ENTRY_BUCKETS:
        if upper is None:
            if score >= lower:
                return label
            continue
        if lower <= score < upper:
            return label
    if score < 0.0:
        return ENTRY_BUCKETS[0][2]
    return ENTRY_BUCKETS[-1][2]


def _monotonic_non_decreasing(values: list[float]) -> bool | None:
    if len(values) < 2:
        return None
    return all(current >= previous for previous, current in zip(values, values[1:]))


def _entry_source_paths(trades_root: Path) -> list[Path]:
    candidates = [
        trades_root / "entry_decisions.csv",
        *sorted(trades_root.glob("entry_decisions.legacy_*.csv")),
    ]
    output: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        if not path.exists():
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        output.append(path)
    return output


def _source_kind(path: Path) -> str:
    if path.name == "entry_decisions.csv":
        return "active_csv"
    if ".legacy_" in path.name:
        return "legacy_csv"
    return "unknown"


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except Exception:
            continue
    return []


def _load_entry_sources(trades_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for path in _entry_source_paths(trades_root):
        source_kind = _source_kind(path)
        loaded_rows = _read_csv_rows(path)
        outcome_counts = Counter(_coerce_text(row.get("outcome")).upper() or "UNKNOWN" for row in loaded_rows)
        rows.extend(
            {
                **row,
                "_source_path": str(path.resolve()),
                "_source_kind": source_kind,
            }
            for row in loaded_rows
        )
        source_rows.append(
            {
                "path": str(path.resolve()),
                "file_name": path.name,
                "source_kind": source_kind,
                "row_count": int(len(loaded_rows)),
                "entered_rows": int(outcome_counts.get("ENTERED", 0)),
                "wait_rows": int(outcome_counts.get("WAIT", 0)),
                "skipped_rows": int(outcome_counts.get("SKIPPED", 0)),
            }
        )
    return rows, source_rows


def _load_closed_history(trades_root: Path) -> list[dict[str, Any]]:
    path = trades_root / "trade_closed_history.csv"
    if not path.exists():
        return []
    return _read_csv_rows(path)


def _build_closed_trade_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], tuple[list[float], list[dict[str, Any]]]]:
    grouped: dict[tuple[str, str], list[tuple[float, dict[str, Any]]]] = {}
    for row in rows:
        symbol = _coerce_text(row.get("symbol")).upper()
        side = _coerce_text(row.get("direction")).upper()
        open_dt = _parse_dt(row.get("open_time"))
        if not symbol or not side or open_dt is None:
            continue
        grouped.setdefault((symbol, side), []).append((open_dt.timestamp(), row))

    index: dict[tuple[str, str], tuple[list[float], list[dict[str, Any]]]] = {}
    for key, items in grouped.items():
        items.sort(key=lambda item: item[0])
        index[key] = ([item[0] for item in items], [item[1] for item in items])
    return index


def _match_closed_trade(
    *,
    closed_trade_index: dict[tuple[str, str], tuple[list[float], list[dict[str, Any]]]],
    symbol: str,
    side: str,
    decision_dt: datetime | None,
    tolerance_seconds: float = 300.0,
) -> dict[str, Any] | None:
    if not symbol or not side or decision_dt is None:
        return None
    key = (symbol, side)
    if key not in closed_trade_index:
        return None
    timestamps, rows = closed_trade_index[key]
    needle = decision_dt.timestamp()
    position = bisect.bisect_left(timestamps, needle)
    candidate_indices = [position - 1, position]
    best_delta: float | None = None
    best_row: dict[str, Any] | None = None
    for index in candidate_indices:
        if index < 0 or index >= len(timestamps):
            continue
        delta = abs(timestamps[index] - needle)
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_row = rows[index]
    if best_delta is None or best_delta > tolerance_seconds:
        return None
    return best_row


def _metric_value_state(separation_gap: float | None, high_low_rate_gap: float | None) -> str:
    if separation_gap is None or high_low_rate_gap is None:
        return "unmeasured"
    if separation_gap >= 0.15 and high_low_rate_gap >= 0.25:
        return "strong"
    if separation_gap >= 0.08 and high_low_rate_gap >= 0.15:
        return "useful"
    if separation_gap >= 0.03 and high_low_rate_gap >= 0.05:
        return "weak"
    return "flat"


def _normalize_rows(
    entry_rows: list[dict[str, Any]],
    closed_trade_index: dict[tuple[str, str], tuple[list[float], list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in entry_rows:
        transition_forecast = _decode_json_object(row.get("transition_forecast_v1"))
        management_forecast = _decode_json_object(row.get("trade_management_forecast_v1"))
        forecast_features = _decode_json_object(row.get("forecast_features_v1"))
        if not transition_forecast and not management_forecast and not forecast_features:
            continue

        observe_confirm = _decode_json_object(row.get("observe_confirm_v1"))
        feature_metadata = dict(forecast_features.get("metadata") or {})
        semantic_inputs = dict(feature_metadata.get("semantic_forecast_inputs_v2") or {})
        state_harvest = dict(semantic_inputs.get("state_harvest") or {})
        secondary_harvest = dict(semantic_inputs.get("secondary_harvest") or {})
        transition_metadata = dict(transition_forecast.get("metadata") or {})
        management_metadata = dict(management_forecast.get("metadata") or {})
        transition_usage = dict(transition_metadata.get("semantic_forecast_inputs_v2_usage_v1") or {})
        management_usage = dict(management_metadata.get("semantic_forecast_inputs_v2_usage_v1") or {})
        transition_grouped = dict(transition_usage.get("grouped_usage") or {})
        management_grouped = dict(management_usage.get("grouped_usage") or {})

        symbol = _coerce_text(row.get("symbol")).upper() or "UNKNOWN_SYMBOL"
        timeframe = _coerce_text(row.get("signal_timeframe")) or "UNKNOWN_TIMEFRAME"
        outcome = _coerce_text(row.get("outcome")).upper() or "UNKNOWN_OUTCOME"
        consumer_side = _coerce_text(row.get("consumer_check_side")).upper()
        consumer_stage = _coerce_text(row.get("consumer_check_stage")).upper()
        observe_action = _coerce_text(observe_confirm.get("action")).upper()
        observe_state = _coerce_text(observe_confirm.get("state")).upper()
        regime_key = (
            _coerce_text(state_harvest.get("session_regime_state"))
            or _coerce_text(secondary_harvest.get("session_regime_state"))
            or _coerce_text(row.get("preflight_regime")).upper()
            or "UNKNOWN_REGIME"
        )
        activation_state = _coerce_text(secondary_harvest.get("advanced_input_activation_state")) or "UNKNOWN_ACTIVATION"
        order_book_state = _coerce_text(secondary_harvest.get("order_book_state")) or "UNKNOWN_ORDER_BOOK"
        decision_dt = _parse_dt(row.get("time"))

        buy_confirm_proxy = 1 if observe_action == "BUY" else 0
        sell_confirm_proxy = 1 if observe_action == "SELL" else 0
        if not observe_action and consumer_stage in {"PROBE", "READY"}:
            if consumer_side == "BUY":
                buy_confirm_proxy = 1
            elif consumer_side == "SELL":
                sell_confirm_proxy = 1
        false_break_proxy = 1 if (observe_action == "WAIT" or observe_state.endswith("OBSERVE") or outcome in {"WAIT", "SKIPPED"}) else 0

        matched_trade = None
        continue_favor_proxy: int | None = None
        fail_now_proxy: int | None = None
        if outcome == "ENTERED":
            resolved_side = observe_action or consumer_side
            matched_trade = _match_closed_trade(
                closed_trade_index=closed_trade_index,
                symbol=symbol,
                side=resolved_side,
                decision_dt=decision_dt,
            )
            if matched_trade is not None:
                profit = _safe_float(matched_trade.get("profit"))
                if profit is not None and abs(profit) > 1e-12:
                    continue_favor_proxy = 1 if profit > 0.0 else 0
                    fail_now_proxy = 1 if profit < 0.0 else 0

        record = {
            "time": _coerce_text(row.get("time")),
            "symbol": symbol,
            "signal_timeframe": timeframe,
            "outcome": outcome,
            "observe_action": observe_action or "UNKNOWN_ACTION",
            "observe_state": observe_state or "UNKNOWN_STATE",
            "consumer_check_side": consumer_side or "UNKNOWN_SIDE",
            "consumer_check_stage": consumer_stage or "UNKNOWN_STAGE",
            "regime_key": regime_key,
            "advanced_input_activation_state": activation_state,
            "order_book_state": order_book_state,
            "p_buy_confirm": _safe_float(transition_forecast.get("p_buy_confirm")),
            "p_sell_confirm": _safe_float(transition_forecast.get("p_sell_confirm")),
            "p_false_break": _safe_float(transition_forecast.get("p_false_break")),
            "p_continue_favor": _safe_float(management_forecast.get("p_continue_favor")),
            "p_fail_now": _safe_float(management_forecast.get("p_fail_now")),
            "buy_confirm_proxy": buy_confirm_proxy,
            "sell_confirm_proxy": sell_confirm_proxy,
            "false_break_proxy": false_break_proxy,
            "continue_favor_proxy": continue_favor_proxy,
            "fail_now_proxy": fail_now_proxy,
            "matched_trade_actual": bool(matched_trade is not None),
            "_source_kind": _coerce_text(row.get("_source_kind")),
            "_source_path": _coerce_text(row.get("_source_path")),
            "transition_branch_present": bool(transition_forecast),
            "trade_management_branch_present": bool(management_forecast),
        }

        for branch_role, grouped_usage in (
            ("transition_branch", transition_grouped),
            ("trade_management_branch", management_grouped),
        ):
            for section in HARVEST_SECTIONS:
                section_usage = dict(grouped_usage.get(section) or {})
                record[f"{branch_role}__{section}__used"] = any(bool(value) for value in section_usage.values())

        normalized.append(record)
    return normalized


def _summarize_metric(rows: list[dict[str, Any]], *, metric_name: str) -> dict[str, Any]:
    spec = METRIC_SPECS[metric_name]
    score_field = metric_name
    label_field = spec["label_field"]
    scored_rows = [row for row in rows if row.get(score_field) is not None]
    labeled_rows = [row for row in scored_rows if row.get(label_field) in {0, 1}]
    positive_scores = [float(row[score_field]) for row in labeled_rows if int(row[label_field]) == 1]
    negative_scores = [float(row[score_field]) for row in labeled_rows if int(row[label_field]) == 0]
    avg_positive = _safe_avg(positive_scores)
    avg_negative = _safe_avg(negative_scores)
    separation_gap = None
    if avg_positive is not None and avg_negative is not None:
        separation_gap = round(avg_positive - avg_negative, 4)

    bucket_rows: list[dict[str, Any]] = []
    bucket_positive_rates: list[float] = []
    low_bucket_positive_rate: float | None = None
    high_bucket_positive_rate: float | None = None
    for _lower, _upper, label in ENTRY_BUCKETS:
        bucket_members = [row for row in labeled_rows if _bucket_label(row.get(score_field)) == label]
        positive_rate = None
        if bucket_members:
            positive_count = sum(int(row[label_field]) for row in bucket_members)
            positive_rate = _ratio(positive_count, len(bucket_members))
            bucket_positive_rates.append(float(positive_rate))
            if low_bucket_positive_rate is None:
                low_bucket_positive_rate = float(positive_rate)
            high_bucket_positive_rate = float(positive_rate)
        bucket_rows.append(
            {
                "metric_name": metric_name,
                "bucket": label,
                "rows": int(len(bucket_members)),
                "avg_score": _safe_avg([float(row[score_field]) for row in bucket_members]),
                "positive_rows": int(sum(int(row[label_field]) for row in bucket_members)) if bucket_members else 0,
                "positive_rate": positive_rate,
            }
        )

    high_low_rate_gap = None
    if low_bucket_positive_rate is not None and high_bucket_positive_rate is not None:
        high_low_rate_gap = round(high_bucket_positive_rate - low_bucket_positive_rate, 4)

    return {
        "metric_name": metric_name,
        "branch_role": spec["branch_role"],
        "label_kind": spec["label_kind"],
        "description": spec["description"],
        "score_rows": int(len(scored_rows)),
        "labeled_rows": int(len(labeled_rows)),
        "positive_rows": int(len(positive_scores)),
        "negative_rows": int(len(negative_scores)),
        "avg_score_positive": avg_positive,
        "avg_score_negative": avg_negative,
        "separation_gap": separation_gap,
        "low_bucket_positive_rate": low_bucket_positive_rate,
        "high_bucket_positive_rate": high_bucket_positive_rate,
        "high_low_rate_gap": high_low_rate_gap,
        "bucket_positive_rate_monotonic": _monotonic_non_decreasing(bucket_positive_rates),
        "value_state": _metric_value_state(separation_gap, high_low_rate_gap),
        "bucket_rows": bucket_rows,
    }


def _slice_rows(
    rows: list[dict[str, Any]],
    *,
    slice_kind: str,
    slice_field: str,
    min_labeled_rows: int,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        slice_key = _coerce_text(row.get(slice_field)) or f"UNKNOWN_{slice_kind.upper()}"
        for metric_name in METRIC_SPECS:
            grouped.setdefault((metric_name, slice_key), []).append(row)

    output: list[dict[str, Any]] = []
    for (metric_name, slice_key), bucket in sorted(grouped.items()):
        summary = _summarize_metric(bucket, metric_name=metric_name)
        if int(summary["labeled_rows"]) < min_labeled_rows:
            continue
        output.append(
            {
                "metric_name": metric_name,
                "slice_kind": slice_kind,
                "slice_key": slice_key,
                "labeled_rows": int(summary["labeled_rows"]),
                "positive_rows": int(summary["positive_rows"]),
                "separation_gap": summary["separation_gap"],
                "high_low_rate_gap": summary["high_low_rate_gap"],
                "bucket_positive_rate_monotonic": summary["bucket_positive_rate_monotonic"],
                "value_state": summary["value_state"],
            }
        )
    return output


def _harvest_section_value_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for branch_role, metrics in BRANCH_TO_METRICS.items():
        if branch_role == "transition_branch":
            branch_rows = [row for row in rows if row.get("transition_branch_present")]
        else:
            branch_rows = [row for row in rows if row.get("trade_management_branch_present")]
        for section in HARVEST_SECTIONS:
            used_key = f"{branch_role}__{section}__used"
            used_rows = [row for row in branch_rows if row.get(used_key)]
            unused_rows = [row for row in branch_rows if not row.get(used_key)]
            used_separations: list[float] = []
            unused_separations: list[float] = []
            metric_rows_with_value = 0
            for metric_name in metrics:
                used_summary = _summarize_metric(used_rows, metric_name=metric_name)
                unused_summary = _summarize_metric(unused_rows, metric_name=metric_name)
                if used_summary["separation_gap"] is not None:
                    used_separations.append(float(used_summary["separation_gap"]))
                    metric_rows_with_value += 1
                if unused_summary["separation_gap"] is not None:
                    unused_separations.append(float(unused_summary["separation_gap"]))
            avg_used = _safe_avg(used_separations)
            avg_unused = _safe_avg(unused_separations)
            separation_delta = None
            if avg_used is not None and avg_unused is not None:
                separation_delta = round(avg_used - avg_unused, 4)
            output.append(
                {
                    "branch_role": branch_role,
                    "harvest_section": section,
                    "branch_rows": int(len(branch_rows)),
                    "section_used_rows": int(len(used_rows)),
                    "section_used_ratio": _ratio(int(len(used_rows)), int(len(branch_rows))),
                    "metric_rows_with_value": int(metric_rows_with_value),
                    "avg_used_separation": avg_used,
                    "avg_unused_separation": avg_unused,
                    "separation_delta": separation_delta,
                }
            )
    return output


def build_state_forecast_validation_forecast_feature_value_slice_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    sf3_report_path: Path = DEFAULT_SF3_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    sf3_report = _load_json(sf3_report_path)
    sf3_summary = dict(sf3_report.get("usage_summary", {}) or {})

    entry_rows, source_rows = _load_entry_sources(trades_root)
    closed_history_rows = _load_closed_history(trades_root)
    closed_trade_index = _build_closed_trade_index(closed_history_rows)
    normalized_rows = _normalize_rows(entry_rows, closed_trade_index)

    metric_rows = [_summarize_metric(normalized_rows, metric_name=metric_name) for metric_name in METRIC_SPECS]
    metric_value_rows = [{key: value for key, value in row.items() if key != "bucket_rows"} for row in metric_rows]
    metric_bucket_rows = [bucket for row in metric_rows for bucket in row["bucket_rows"]]

    symbol_slice_rows = _slice_rows(normalized_rows, slice_kind="symbol", slice_field="symbol", min_labeled_rows=25)
    regime_slice_rows = _slice_rows(normalized_rows, slice_kind="regime", slice_field="regime_key", min_labeled_rows=25)
    activation_keys = {
        _coerce_text(row.get("advanced_input_activation_state"))
        for row in normalized_rows
        if _coerce_text(row.get("advanced_input_activation_state")) and _coerce_text(row.get("advanced_input_activation_state")) != "UNKNOWN_ACTIVATION"
    }
    activation_slice_rows = (
        _slice_rows(
            normalized_rows,
            slice_kind="advanced_activation",
            slice_field="advanced_input_activation_state",
            min_labeled_rows=15,
        )
        if activation_keys
        else []
    )
    harvest_section_rows = _harvest_section_value_rows(normalized_rows)

    suspicious_slices = sorted(
        [
            row
            for row in [*symbol_slice_rows, *regime_slice_rows, *activation_slice_rows]
            if row.get("value_state") in {"flat", "weak"}
        ],
        key=lambda row: (
            float(row.get("separation_gap") or 0.0),
            float(row.get("high_low_rate_gap") or 0.0),
            int(-row.get("labeled_rows", 0)),
        ),
    )[:18]

    entered_rows = sum(1 for row in normalized_rows if row.get("outcome") == "ENTERED")
    matched_rows = sum(1 for row in normalized_rows if bool(row.get("matched_trade_actual")))
    actual_labeled_rows = sum(1 for row in normalized_rows if row.get("continue_favor_proxy") in {0, 1})
    source_kind_counts = Counter(_coerce_text(row.get("_source_kind")) for row in normalized_rows)
    symbol_counts = Counter(_coerce_text(row.get("symbol")) for row in normalized_rows)
    regime_counts = Counter(_coerce_text(row.get("regime_key")) for row in normalized_rows)
    activation_counts = Counter(_coerce_text(row.get("advanced_input_activation_state")) for row in normalized_rows)

    suspicious_candidates = [
        {
            "candidate_type": "secondary_harvest_value_unmeasurable",
            "reason": "secondary_harvest still has zero direct-use rows, so score value cannot be attributed by section usage",
            "section_used_ratio": next(
                (
                    row["section_used_ratio"]
                    for row in harvest_section_rows
                    if row["branch_role"] == "transition_branch" and row["harvest_section"] == "secondary_harvest"
                ),
                0.0,
            ),
            "sf3_secondary_harvest_direct_use_field_count": int(sf3_summary.get("secondary_harvest_direct_use_field_count", 0)),
        },
        {
            "candidate_type": "management_actual_label_coverage",
            "reason": "management value audit is real-outcome based, but only ENTERED rows can be matched to closed trades",
            "entered_rows": int(entered_rows),
            "actual_labeled_rows": int(actual_labeled_rows),
        },
    ]
    if all(float(row.get("section_used_ratio", 0.0) or 0.0) == 0.0 for row in harvest_section_rows):
        suspicious_candidates.append(
            {
                "candidate_type": "csv_usage_trace_projection_gap",
                "reason": "full entry_decisions CSV preserves forecast scores well, but per-row grouped usage trace is stripped so section-level value audit cannot be fully projected",
                "branch_section_rows": int(len(harvest_section_rows)),
                "recommended_followup": "combine SF3 detail usage trace with SF4 value slices in SF5",
            }
        )
    if not activation_keys:
        suspicious_candidates.append(
            {
                "candidate_type": "advanced_activation_slice_unavailable_in_csv_surface",
                "reason": "entry_decisions CSV keeps forecast scores but strips advanced activation metadata needed for activation slice value review",
                "activation_slice_row_count": 0,
                "recommended_followup": "reuse detail-jsonl state surface when SF5 reviews activation/bridge gaps",
            }
        )

    value_summary = {
        "sample_strategy": "entry_decisions_csv_full_scan",
        "entry_source_count": int(len(source_rows)),
        "decision_row_count": int(len(normalized_rows)),
        "closed_trade_row_count": int(len(closed_history_rows)),
        "entered_rows": int(entered_rows),
        "matched_trade_rows": int(matched_rows),
        "management_actual_labeled_rows": int(actual_labeled_rows),
        "transition_branch_rows": int(sum(1 for row in normalized_rows if row.get("transition_branch_present"))),
        "trade_management_branch_rows": int(sum(1 for row in normalized_rows if row.get("trade_management_branch_present"))),
        "strong_metric_count": int(sum(1 for row in metric_value_rows if row.get("value_state") == "strong")),
        "flat_metric_count": int(sum(1 for row in metric_value_rows if row.get("value_state") == "flat")),
        "sf3_secondary_harvest_direct_use_field_count": int(sf3_summary.get("secondary_harvest_direct_use_field_count", 0)),
        "recommended_next_step": "SF5_gap_matrix_bridge_candidate_review",
    }

    value_assessment = {
        "value_audit_state": (
            "management_actual_and_transition_proxy_ready"
            if actual_labeled_rows >= 100
            else "transition_proxy_ready_management_actual_limited"
        ),
        "transition_proxy_value_ready": True,
        "management_actual_value_ready": bool(actual_labeled_rows >= 100),
        "secondary_value_section_ready": bool(int(sf3_summary.get("secondary_harvest_direct_use_field_count", 0)) > 0),
        "recommended_next_step": "SF5_gap_matrix_bridge_candidate_review",
        "primary_gap_call": (
            "secondary_harvest_value_path_missing"
            if int(sf3_summary.get("secondary_harvest_direct_use_field_count", 0)) == 0
            else "slice_bridge_refinement"
        ),
    }

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "state_forecast_validation_sf4_value_slice_audit",
        "sf3_report_path": str(sf3_report_path),
        "trades_root": str(trades_root),
        "value_summary": value_summary,
        "value_assessment": value_assessment,
        "entry_source_rows": source_rows,
        "metric_value_rows": metric_value_rows,
        "metric_bucket_rows": metric_bucket_rows,
        "symbol_slice_rows": symbol_slice_rows,
        "regime_slice_rows": regime_slice_rows,
        "activation_slice_rows": activation_slice_rows,
        "harvest_section_value_rows": harvest_section_rows,
        "symbol_summary": [{"symbol": str(key), "decision_rows": int(value)} for key, value in sorted(symbol_counts.items())],
        "regime_summary": [{"regime_key": str(key), "decision_rows": int(value)} for key, value in sorted(regime_counts.items())],
        "activation_summary_rows": [
            {"advanced_input_activation_state": str(key), "decision_rows": int(value)}
            for key, value in sorted(activation_counts.items())
        ],
        "source_kind_counts": {str(key): int(value) for key, value in sorted(source_kind_counts.items())},
        "suspicious_slice_candidates": suspicious_slices,
        "suspicious_value_candidates": suspicious_candidates,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("value_summary", {}) or {})
    assessment = dict(report.get("value_assessment", {}) or {})
    metric_rows = list(report.get("metric_value_rows", []) or [])
    suspicious = list(report.get("suspicious_slice_candidates", []) or [])
    lines = [
        "# State / Forecast Validation SF4 Value / Slice Audit",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- value_audit_state: `{assessment.get('value_audit_state', '')}`",
        f"- primary_gap_call: `{assessment.get('primary_gap_call', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- decision_row_count: `{summary.get('decision_row_count', 0)}`",
        f"- entered_rows: `{summary.get('entered_rows', 0)}`",
        f"- matched_trade_rows: `{summary.get('matched_trade_rows', 0)}`",
        f"- management_actual_labeled_rows: `{summary.get('management_actual_labeled_rows', 0)}`",
        f"- strong_metric_count: `{summary.get('strong_metric_count', 0)}`",
        f"- flat_metric_count: `{summary.get('flat_metric_count', 0)}`",
        f"- sf3_secondary_harvest_direct_use_field_count: `{summary.get('sf3_secondary_harvest_direct_use_field_count', 0)}`",
        "",
        "## Metric Value Rows",
        "",
        "| metric | label_kind | labeled_rows | separation_gap | high_low_rate_gap | value_state |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in metric_rows:
        lines.append(
            "| {metric} | {label_kind} | {labeled_rows} | {separation_gap} | {high_low_rate_gap} | {value_state} |".format(
                metric=_coerce_text(row.get("metric_name")),
                label_kind=_coerce_text(row.get("label_kind")),
                labeled_rows=int(row.get("labeled_rows", 0) or 0),
                separation_gap=row.get("separation_gap"),
                high_low_rate_gap=row.get("high_low_rate_gap"),
                value_state=_coerce_text(row.get("value_state")),
            )
        )
    lines.extend(
        [
            "",
            "## Suspicious Slice Candidates",
            "",
            "| metric | slice_kind | slice_key | labeled_rows | separation_gap | high_low_rate_gap | state |",
            "|---|---|---|---:|---:|---:|---|",
        ]
    )
    for row in suspicious:
        lines.append(
            "| {metric} | {slice_kind} | {slice_key} | {labeled_rows} | {separation_gap} | {high_low_rate_gap} | {state} |".format(
                metric=_coerce_text(row.get("metric_name")),
                slice_kind=_coerce_text(row.get("slice_kind")),
                slice_key=_coerce_text(row.get("slice_key")),
                labeled_rows=int(row.get("labeled_rows", 0) or 0),
                separation_gap=row.get("separation_gap"),
                high_low_rate_gap=row.get("high_low_rate_gap"),
                state=_coerce_text(row.get("value_state")),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = [
        *list(report.get("symbol_slice_rows", []) or []),
        *list(report.get("regime_slice_rows", []) or []),
        *list(report.get("activation_slice_rows", []) or []),
    ]
    fieldnames = [
        "metric_name",
        "slice_kind",
        "slice_key",
        "labeled_rows",
        "positive_rows",
        "separation_gap",
        "high_low_rate_gap",
        "bucket_positive_rate_monotonic",
        "value_state",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_state_forecast_validation_forecast_feature_value_slice_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    sf3_report_path: Path = DEFAULT_SF3_REPORT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_state_forecast_validation_forecast_feature_value_slice_report(
        trades_root=trades_root,
        sf3_report_path=sf3_report_path,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "state_forecast_validation_sf4_value_latest.json"
    latest_csv = output_dir / "state_forecast_validation_sf4_value_latest.csv"
    latest_md = output_dir / "state_forecast_validation_sf4_value_latest.md"
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(report, latest_csv)
    _write_markdown(report, latest_md)
    return {
        "latest_json_path": str(latest_json),
        "latest_csv_path": str(latest_csv),
        "latest_markdown_path": str(latest_md),
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SF4 forecast feature value / slice audit report.")
    parser.add_argument("--trades-root", type=Path, default=DEFAULT_TRADES_ROOT)
    parser.add_argument("--sf3-report-path", type=Path, default=DEFAULT_SF3_REPORT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    result = write_state_forecast_validation_forecast_feature_value_slice_report(
        trades_root=args.trades_root,
        sf3_report_path=args.sf3_report_path,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
