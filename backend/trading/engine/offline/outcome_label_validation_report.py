from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.services.outcome_labeler_contract import (
    OUTCOME_LABELER_MANAGEMENT_LABELS_V1,
    OUTCOME_LABELER_TRANSITION_LABELS_V1,
    OUTCOME_LABELER_VALIDATION_REPORT_V1,
    normalize_outcome_label_status,
    resolve_outcome_label_polarity,
)
from backend.trading.engine.offline.outcome_labeler import build_outcome_label_compact_summary

OUTCOME_LABEL_VALIDATION_REPORT_VERSION = "validation_report_v1"
OUTCOME_LABEL_VALIDATION_REPORT_TYPE = "outcome_label_validation_report_v1"
REPLAY_DATASET_ROW_TYPE_V1 = "replay_dataset_row_v1"


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


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    return value


def _safe_ratio(num: int, den: int) -> float:
    if int(den) <= 0:
        return 0.0
    return round(float(num) / float(den), 6)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def iter_replay_dataset_rows_from_file(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = _project_root() / file_path
    if not file_path.exists():
        return []
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        payload = json.loads(text)
        if isinstance(payload, list):
            return [_coerce_mapping(item) for item in payload if _coerce_mapping(item)]
        return []
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        mapped = _coerce_mapping(payload)
        if mapped:
            rows.append(mapped)
    return rows


def _family_payload(row: Mapping[str, Any], family: str) -> dict[str, Any]:
    outcome_labels = _coerce_mapping(row.get("outcome_labels_v1"))
    key = "transition" if family == "transition" else "trade_management"
    return _coerce_mapping(outcome_labels.get(key))


def _family_metadata(row: Mapping[str, Any], family: str) -> dict[str, Any]:
    return _coerce_mapping(_family_payload(row, family).get("metadata"))


def _row_label_quality_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    replay_row = _coerce_mapping(row)
    direct = _coerce_mapping(replay_row.get("label_quality_summary_v1"))
    if direct:
        return direct
    return build_outcome_label_compact_summary(
        replay_row.get("outcome_labels_v1"),
        row_key=str(replay_row.get("row_key", "") or ""),
        forecast_snapshot=replay_row.get("forecast_snapshots"),
    )


def _forecast_branch_evaluation(row: Mapping[str, Any]) -> dict[str, Any]:
    replay_row = _coerce_mapping(row)
    direct = _coerce_mapping(replay_row.get("forecast_branch_evaluation_v1"))
    if direct:
        return direct
    outcome_labels = _coerce_mapping(replay_row.get("outcome_labels_v1"))
    metadata = _coerce_mapping(outcome_labels.get("metadata"))
    return _coerce_mapping(metadata.get("forecast_branch_evaluation_v1"))


def _row_symbol(row: Mapping[str, Any]) -> str:
    row_identity = _coerce_mapping(row.get("row_identity"))
    if row_identity.get("symbol") not in ("", None):
        return str(row_identity.get("symbol") or "")
    decision_row = _coerce_mapping(row.get("decision_row"))
    return str(decision_row.get("symbol", "") or "")


def _build_label_quality_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    transition_status_counts: dict[str, int] = {}
    management_status_counts: dict[str, int] = {}
    source_descriptor_counts: dict[str, int] = {}
    rows_total = 0
    label_positive_count = 0
    label_negative_count = 0
    label_unknown_count = 0
    ambiguous_rows = 0
    censored_rows = 0

    for row in rows:
        replay_row = _coerce_mapping(row)
        if replay_row.get("row_type") not in ("", None) and str(replay_row.get("row_type")) != REPLAY_DATASET_ROW_TYPE_V1:
            continue
        summary = _row_label_quality_summary(replay_row)
        if not summary:
            continue
        rows_total += 1
        label_positive_count += int(summary.get("label_positive_count", 0))
        label_negative_count += int(summary.get("label_negative_count", 0))
        label_unknown_count += int(summary.get("label_unknown_count", 0))
        if bool(summary.get("label_is_ambiguous")):
            ambiguous_rows += 1
        if bool(summary.get("is_censored")):
            censored_rows += 1

        transition_status = str(summary.get("transition_label_status", "") or "").strip()
        if transition_status:
            transition_status_counts[transition_status] = int(transition_status_counts.get(transition_status, 0)) + 1
        management_status = str(summary.get("management_label_status", "") or "").strip()
        if management_status:
            management_status_counts[management_status] = int(management_status_counts.get(management_status, 0)) + 1
        source_descriptor = str(summary.get("label_source_descriptor", "") or "").strip()
        if source_descriptor:
            source_descriptor_counts[source_descriptor] = int(source_descriptor_counts.get(source_descriptor, 0)) + 1

    return {
        "contract_version": "label_quality_report_summary_v1",
        "rows_total": rows_total,
        "label_positive_count": label_positive_count,
        "label_negative_count": label_negative_count,
        "label_unknown_count": label_unknown_count,
        "ambiguous_rows": ambiguous_rows,
        "censored_rows": censored_rows,
        "transition_status_counts": {str(key): int(value) for key, value in sorted(transition_status_counts.items())},
        "management_status_counts": {str(key): int(value) for key, value in sorted(management_status_counts.items())},
        "source_descriptor_counts": {str(key): int(value) for key, value in sorted(source_descriptor_counts.items())},
    }


def _label_polarity(family_payload: Mapping[str, Any], metadata: Mapping[str, Any], label_name: str) -> str:
    label_polarities = _coerce_mapping(metadata.get("label_polarities"))
    if label_name in label_polarities:
        return str(label_polarities.get(label_name) or "UNKNOWN")
    return resolve_outcome_label_polarity(
        label_status=str(family_payload.get("label_status", "") or ""),
        label_value=family_payload.get(label_name),
    )


def _empty_label_counts(label_names: Sequence[str]) -> dict[str, dict[str, Any]]:
    return {
        label_name: {
            "positive": 0,
            "negative": 0,
            "unknown": 0,
            "scorable_rows": 0,
            "positive_rate": 0.0,
            "dominant_polarity": "UNKNOWN",
            "imbalance_ratio": 0.0,
        }
        for label_name in label_names
    }


def _empty_distribution_bucket() -> dict[str, Any]:
    return {
        "rows": 0,
        "scorable_rows": 0,
        "unknown_rows": 0,
        "censored_rows": 0,
        "status_counts": {},
    }


def _summarize_label_counts(label_counts: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summarized: dict[str, dict[str, Any]] = {}
    for label_name, counts in label_counts.items():
        positive = int(counts.get("positive", 0))
        negative = int(counts.get("negative", 0))
        unknown = int(counts.get("unknown", 0))
        scorable_rows = positive + negative
        if positive > negative:
            dominant = "POSITIVE"
        elif negative > positive:
            dominant = "NEGATIVE"
        else:
            dominant = "UNKNOWN"
        imbalance_ratio = max(positive, negative) / scorable_rows if scorable_rows > 0 else 0.0
        summarized[label_name] = {
            "positive": positive,
            "negative": negative,
            "unknown": unknown,
            "scorable_rows": scorable_rows,
            "positive_rate": _safe_ratio(positive, scorable_rows),
            "dominant_polarity": dominant,
            "imbalance_ratio": round(float(imbalance_ratio), 6),
        }
    return summarized


def _summarize_distribution_buckets(buckets: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for bucket_key in sorted(buckets.keys()):
        bucket = buckets[bucket_key]
        rows = int(bucket.get("rows", 0))
        out[bucket_key] = {
            "rows": rows,
            "scorable_rows": int(bucket.get("scorable_rows", 0)),
            "unknown_rows": int(bucket.get("unknown_rows", 0)),
            "unknown_ratio": _safe_ratio(int(bucket.get("unknown_rows", 0)), rows),
            "censored_rows": int(bucket.get("censored_rows", 0)),
            "censored_ratio": _safe_ratio(int(bucket.get("censored_rows", 0)), rows),
            "status_counts": {str(key): int(value) for key, value in sorted(dict(bucket.get("status_counts", {})).items())},
        }
    return out


def _empty_branch_metric_bucket() -> dict[str, Any]:
    return {
        "rows": 0,
        "scorable_rows": 0,
        "hit_count": 0,
        "miss_count": 0,
        "unknown_count": 0,
        "predicted_positive_rows": 0,
        "actual_positive_rows": 0,
        "average_probability": 0.0,
        "probability_sum": 0.0,
        "probability_count": 0,
    }


def _summarize_branch_metric_buckets(buckets: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summarized: dict[str, dict[str, Any]] = {}
    for metric_name in sorted(buckets.keys()):
        bucket = buckets[metric_name]
        probability_count = int(bucket.get("probability_count", 0))
        average_probability = 0.0
        if probability_count > 0:
            average_probability = round(float(bucket.get("probability_sum", 0.0)) / float(probability_count), 6)
        summarized[metric_name] = {
            "rows": int(bucket.get("rows", 0)),
            "scorable_rows": int(bucket.get("scorable_rows", 0)),
            "hit_count": int(bucket.get("hit_count", 0)),
            "miss_count": int(bucket.get("miss_count", 0)),
            "unknown_count": int(bucket.get("unknown_count", 0)),
            "hit_rate": _safe_ratio(int(bucket.get("hit_count", 0)), int(bucket.get("scorable_rows", 0))),
            "predicted_positive_rows": int(bucket.get("predicted_positive_rows", 0)),
            "actual_positive_rows": int(bucket.get("actual_positive_rows", 0)),
            "average_probability": average_probability,
        }
    return summarized


def _empty_gap_metric_bucket() -> dict[str, Any]:
    return {
        "rows": 0,
        "active_signal_rows": 0,
        "scorable_rows": 0,
        "hit_count": 0,
        "miss_count": 0,
        "unknown_count": 0,
        "positive_signal_rows": 0,
        "negative_signal_rows": 0,
        "gap_abs_sum": 0.0,
    }


def _summarize_gap_metric_buckets(buckets: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summarized: dict[str, dict[str, Any]] = {}
    for metric_name in sorted(buckets.keys()):
        bucket = buckets[metric_name]
        active_signal_rows = int(bucket.get("active_signal_rows", 0))
        average_abs_gap = 0.0
        if active_signal_rows > 0:
            average_abs_gap = round(float(bucket.get("gap_abs_sum", 0.0)) / float(active_signal_rows), 6)
        summarized[metric_name] = {
            "rows": int(bucket.get("rows", 0)),
            "active_signal_rows": active_signal_rows,
            "scorable_rows": int(bucket.get("scorable_rows", 0)),
            "hit_count": int(bucket.get("hit_count", 0)),
            "miss_count": int(bucket.get("miss_count", 0)),
            "unknown_count": int(bucket.get("unknown_count", 0)),
            "hit_rate": _safe_ratio(int(bucket.get("hit_count", 0)), int(bucket.get("scorable_rows", 0))),
            "positive_signal_rows": int(bucket.get("positive_signal_rows", 0)),
            "negative_signal_rows": int(bucket.get("negative_signal_rows", 0)),
            "average_abs_gap": average_abs_gap,
        }
    return summarized


def _build_forecast_branch_performance(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    transition_metrics: dict[str, dict[str, Any]] = {}
    management_metrics: dict[str, dict[str, Any]] = {}
    gap_metrics: dict[str, dict[str, Any]] = {}

    for row in rows:
        replay_row = _coerce_mapping(row)
        if replay_row.get("row_type") not in ("", None) and str(replay_row.get("row_type")) != REPLAY_DATASET_ROW_TYPE_V1:
            continue
        evaluation = _forecast_branch_evaluation(replay_row)
        transition_eval = _coerce_mapping(evaluation.get("transition_forecast_vs_outcome"))
        management_eval = _coerce_mapping(evaluation.get("management_forecast_vs_outcome"))
        gap_eval = _coerce_mapping(evaluation.get("gap_signal_quality"))

        for metric_name, metric_payload in _coerce_mapping(transition_eval.get("evaluations")).items():
            bucket = transition_metrics.setdefault(metric_name, _empty_branch_metric_bucket())
            payload = _coerce_mapping(metric_payload)
            bucket["rows"] = int(bucket.get("rows", 0)) + 1
            if payload.get("scorable") is True:
                bucket["scorable_rows"] = int(bucket.get("scorable_rows", 0)) + 1
                if payload.get("hit") is True:
                    bucket["hit_count"] = int(bucket.get("hit_count", 0)) + 1
                elif payload.get("hit") is False:
                    bucket["miss_count"] = int(bucket.get("miss_count", 0)) + 1
            else:
                bucket["unknown_count"] = int(bucket.get("unknown_count", 0)) + 1
            if payload.get("predicted_positive") is True:
                bucket["predicted_positive_rows"] = int(bucket.get("predicted_positive_rows", 0)) + 1
            if payload.get("actual_positive") is True:
                bucket["actual_positive_rows"] = int(bucket.get("actual_positive_rows", 0)) + 1
            if payload.get("has_forecast") is True:
                bucket["probability_count"] = int(bucket.get("probability_count", 0)) + 1
                bucket["probability_sum"] = float(bucket.get("probability_sum", 0.0)) + float(payload.get("probability", 0.0))

        for metric_name, metric_payload in _coerce_mapping(management_eval.get("evaluations")).items():
            bucket = management_metrics.setdefault(metric_name, _empty_branch_metric_bucket())
            payload = _coerce_mapping(metric_payload)
            bucket["rows"] = int(bucket.get("rows", 0)) + 1
            if payload.get("scorable") is True:
                bucket["scorable_rows"] = int(bucket.get("scorable_rows", 0)) + 1
                if payload.get("hit") is True:
                    bucket["hit_count"] = int(bucket.get("hit_count", 0)) + 1
                elif payload.get("hit") is False:
                    bucket["miss_count"] = int(bucket.get("miss_count", 0)) + 1
            else:
                bucket["unknown_count"] = int(bucket.get("unknown_count", 0)) + 1
            if payload.get("predicted_positive") is True:
                bucket["predicted_positive_rows"] = int(bucket.get("predicted_positive_rows", 0)) + 1
            if payload.get("actual_positive") is True:
                bucket["actual_positive_rows"] = int(bucket.get("actual_positive_rows", 0)) + 1
            if payload.get("has_forecast") is True:
                bucket["probability_count"] = int(bucket.get("probability_count", 0)) + 1
                bucket["probability_sum"] = float(bucket.get("probability_sum", 0.0)) + float(payload.get("probability", 0.0))

        for metric_name, metric_payload in _coerce_mapping(gap_eval.get("evaluations")).items():
            bucket = gap_metrics.setdefault(metric_name, _empty_gap_metric_bucket())
            payload = _coerce_mapping(metric_payload)
            bucket["rows"] = int(bucket.get("rows", 0)) + 1
            if payload.get("signal_active") is True:
                bucket["active_signal_rows"] = int(bucket.get("active_signal_rows", 0)) + 1
                bucket["gap_abs_sum"] = float(bucket.get("gap_abs_sum", 0.0)) + abs(float(payload.get("gap_value", 0.0)))
            if payload.get("scorable") is True:
                bucket["scorable_rows"] = int(bucket.get("scorable_rows", 0)) + 1
                if payload.get("hit") is True:
                    bucket["hit_count"] = int(bucket.get("hit_count", 0)) + 1
                elif payload.get("hit") is False:
                    bucket["miss_count"] = int(bucket.get("miss_count", 0)) + 1
            else:
                bucket["unknown_count"] = int(bucket.get("unknown_count", 0)) + 1
            if payload.get("predicted_positive") is True:
                bucket["positive_signal_rows"] = int(bucket.get("positive_signal_rows", 0)) + 1
            elif payload.get("predicted_positive") is False:
                bucket["negative_signal_rows"] = int(bucket.get("negative_signal_rows", 0)) + 1

    return {
        "contract_version": "forecast_branch_performance_v1",
        "transition_forecast_vs_outcome": _summarize_branch_metric_buckets(transition_metrics),
        "management_forecast_vs_outcome": _summarize_branch_metric_buckets(management_metrics),
        "gap_signal_quality": _summarize_gap_metric_buckets(gap_metrics),
    }


def _family_alerts(
    *,
    family: str,
    rows_total: int,
    scorable_rows: int,
    unknown_ratio: float,
    label_counts: Mapping[str, Mapping[str, Any]],
    symbol_distribution: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    thresholds = dict(OUTCOME_LABELER_VALIDATION_REPORT_V1.get("alert_thresholds", {}) or {})
    unknown_warn = float(thresholds.get("high_unknown_ratio_warn", 0.40))
    unknown_fail = float(thresholds.get("high_unknown_ratio_fail", 0.60))
    skew_warn = float(thresholds.get("label_side_skew_ratio_warn", 0.90))
    skew_fail = float(thresholds.get("label_side_skew_ratio_fail", 0.98))
    symbol_min_scorable = int(thresholds.get("symbol_min_scorable_rows_warn", 3))

    alerts: list[dict[str, Any]] = []
    if rows_total > 0 and unknown_ratio >= unknown_warn:
        alerts.append(
            {
                "family": family,
                "severity": "fail" if unknown_ratio >= unknown_fail else "warn",
                "code": "high_unknown_ratio",
                "message": f"{family} unknown ratio is {unknown_ratio:.3f}, which is above the configured threshold.",
                "metrics": {
                    "rows_total": rows_total,
                    "scorable_rows": scorable_rows,
                    "unknown_ratio": round(float(unknown_ratio), 6),
                },
            }
        )

    for label_name, counts in label_counts.items():
        scorable = int(counts.get("scorable_rows", 0))
        if scorable <= 0:
            alerts.append(
                {
                    "family": family,
                    "severity": "warn",
                    "code": "no_scorable_rows_for_label",
                    "target": label_name,
                    "message": f"{label_name} has no scorable rows in the {family} family.",
                    "metrics": {"scorable_rows": 0},
                }
            )
            continue
        imbalance = float(counts.get("imbalance_ratio", 0.0))
        if imbalance >= skew_warn:
            alerts.append(
                {
                    "family": family,
                    "severity": "fail" if imbalance >= skew_fail else "warn",
                    "code": "label_side_skew",
                    "target": label_name,
                    "message": f"{label_name} is highly one-sided in the {family} family.",
                    "metrics": {
                        "scorable_rows": scorable,
                        "positive": int(counts.get("positive", 0)),
                        "negative": int(counts.get("negative", 0)),
                        "imbalance_ratio": round(float(imbalance), 6),
                    },
                }
            )

    for symbol, bucket in symbol_distribution.items():
        scorable = int(bucket.get("scorable_rows", 0))
        rows = int(bucket.get("rows", 0))
        if rows > 0 and scorable < symbol_min_scorable:
            alerts.append(
                {
                    "family": family,
                    "severity": "warn",
                    "code": "symbol_low_scorable_coverage",
                    "target": symbol,
                    "message": f"{symbol} has only {scorable} scorable {family} rows.",
                    "metrics": {
                        "rows": rows,
                        "scorable_rows": scorable,
                        "unknown_ratio": _safe_ratio(int(bucket.get("unknown_rows", 0)), rows),
                    },
                }
            )
    return alerts


def _build_family_report(rows: Sequence[Mapping[str, Any]], *, family: str, label_names: Sequence[str]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    label_counts = _empty_label_counts(label_names)
    symbol_distribution: dict[str, dict[str, Any]] = {}
    horizon_distribution: dict[str, dict[str, Any]] = {}

    rows_total = 0
    scorable_rows = 0
    unknown_rows = 0
    censored_rows = 0

    for row in rows:
        replay_row = _coerce_mapping(row)
        if replay_row.get("row_type") not in ("", None) and str(replay_row.get("row_type")) != REPLAY_DATASET_ROW_TYPE_V1:
            continue
        quality_summary = _row_label_quality_summary(replay_row)
        family_quality = _coerce_mapping(
            quality_summary.get("transition" if family == "transition" else "management")
        )
        family_payload = _family_payload(replay_row, family)
        metadata = _coerce_mapping(family_payload.get("metadata"))
        status = normalize_outcome_label_status(
            str(family_quality.get("label_status", "") or family_payload.get("label_status", "") or "")
        )
        symbol = _row_symbol(replay_row) or "UNKNOWN"
        horizon_bars = str(family_quality.get("horizon_bars", metadata.get("horizon_bars", "UNKNOWN")) or "UNKNOWN")

        rows_total += 1
        status_counts[status] = int(status_counts.get(status, 0)) + 1
        if status == "VALID":
            scorable_rows += 1
        else:
            unknown_rows += 1
        if status == "CENSORED":
            censored_rows += 1

        symbol_bucket = symbol_distribution.setdefault(symbol, _empty_distribution_bucket())
        symbol_bucket["rows"] = int(symbol_bucket.get("rows", 0)) + 1
        symbol_bucket["status_counts"][status] = int(symbol_bucket["status_counts"].get(status, 0)) + 1
        if status == "VALID":
            symbol_bucket["scorable_rows"] = int(symbol_bucket.get("scorable_rows", 0)) + 1
        else:
            symbol_bucket["unknown_rows"] = int(symbol_bucket.get("unknown_rows", 0)) + 1
        if status == "CENSORED":
            symbol_bucket["censored_rows"] = int(symbol_bucket.get("censored_rows", 0)) + 1

        horizon_bucket = horizon_distribution.setdefault(horizon_bars, _empty_distribution_bucket())
        horizon_bucket["rows"] = int(horizon_bucket.get("rows", 0)) + 1
        horizon_bucket["status_counts"][status] = int(horizon_bucket["status_counts"].get(status, 0)) + 1
        if status == "VALID":
            horizon_bucket["scorable_rows"] = int(horizon_bucket.get("scorable_rows", 0)) + 1
        else:
            horizon_bucket["unknown_rows"] = int(horizon_bucket.get("unknown_rows", 0)) + 1
        if status == "CENSORED":
            horizon_bucket["censored_rows"] = int(horizon_bucket.get("censored_rows", 0)) + 1

        for label_name in label_names:
            polarity = _label_polarity(family_payload, metadata, label_name)
            counter_key = "unknown"
            if polarity == "POSITIVE":
                counter_key = "positive"
            elif polarity == "NEGATIVE":
                counter_key = "negative"
            label_counts[label_name][counter_key] = int(label_counts[label_name].get(counter_key, 0)) + 1

    summarized_label_counts = _summarize_label_counts(label_counts)
    unknown_ratio = _safe_ratio(unknown_rows, rows_total)
    censored_ratio = _safe_ratio(censored_rows, rows_total)
    summarized_symbols = _summarize_distribution_buckets(symbol_distribution)
    summarized_horizons = _summarize_distribution_buckets(horizon_distribution)
    alerts = _family_alerts(
        family=family,
        rows_total=rows_total,
        scorable_rows=scorable_rows,
        unknown_ratio=unknown_ratio,
        label_counts=summarized_label_counts,
        symbol_distribution=summarized_symbols,
    )

    return {
        "rows_total": rows_total,
        "scorable_rows": scorable_rows,
        "unknown_rows": unknown_rows,
        "unknown_ratio": unknown_ratio,
        "censored_rows": censored_rows,
        "censored_ratio": censored_ratio,
        "status_counts": {str(key): int(value) for key, value in sorted(status_counts.items())},
        "label_counts": summarized_label_counts,
        "symbol_distribution": summarized_symbols,
        "horizon_distribution": summarized_horizons,
        "alerts": alerts,
    }


def build_outcome_label_validation_report(replay_rows: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    rows = [_coerce_mapping(row) for row in list(replay_rows or []) if _coerce_mapping(row)]
    transition = _build_family_report(rows, family="transition", label_names=OUTCOME_LABELER_TRANSITION_LABELS_V1)
    management = _build_family_report(rows, family="management", label_names=OUTCOME_LABELER_MANAGEMENT_LABELS_V1)
    label_quality_summary = _build_label_quality_summary(rows)
    forecast_branch_performance = _build_forecast_branch_performance(rows)
    symbols = sorted({symbol for symbol in (str(_row_symbol(row)) for row in rows) if symbol})
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "report_type": OUTCOME_LABEL_VALIDATION_REPORT_TYPE,
        "report_contract": OUTCOME_LABEL_VALIDATION_REPORT_VERSION,
        "input_row_type": REPLAY_DATASET_ROW_TYPE_V1,
        "rows_total": int(len(rows)),
        "symbols": symbols,
        "thresholds": _to_jsonable(dict(OUTCOME_LABELER_VALIDATION_REPORT_V1.get("alert_thresholds", {}) or {})),
        "label_quality_summary_v1": label_quality_summary,
        "transition": transition,
        "management": management,
        "forecast_branch_performance_v1": forecast_branch_performance,
    }


def build_outcome_label_validation_report_from_file(path: str | Path) -> dict[str, Any]:
    return build_outcome_label_validation_report(iter_replay_dataset_rows_from_file(path))


def write_outcome_label_validation_report(
    replay_rows: Sequence[Mapping[str, Any]] | None,
    *,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    report = build_outcome_label_validation_report(replay_rows)
    base_dir = Path(output_dir) if output_dir is not None else (_project_root() / OUTCOME_LABELER_VALIDATION_REPORT_V1["output_targets"]["analysis_dir"])
    path = Path(output_path) if output_path is not None else (
        base_dir / f"outcome_label_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_outcome_label_validation_report_from_file(
    replay_row_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    report = build_outcome_label_validation_report_from_file(replay_row_path)
    base_dir = Path(output_dir) if output_dir is not None else (_project_root() / OUTCOME_LABELER_VALIDATION_REPORT_V1["output_targets"]["analysis_dir"])
    path = Path(output_path) if output_path is not None else (
        base_dir / f"outcome_label_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
