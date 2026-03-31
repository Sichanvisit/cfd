from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from bisect import bisect_left
from typing import Any, Mapping, Sequence, Iterator

from backend.services.storage_compaction import (
    resolve_entry_decision_detail_path,
    resolve_entry_decision_row_key,
)
from backend.trading.engine.core.models import OutcomeLabelsV1
from backend.trading.engine.offline.outcome_labeler import (
    OUTCOME_LABEL_COMPACT_SUMMARY_VERSION,
    build_outcome_label_compact_summary,
    build_outcome_labels,
)
from backend.trading.engine.offline.outcome_label_validation_report import (
    write_outcome_label_validation_report_from_file,
)

REPLAY_DATASET_ROW_TYPE_V1 = "replay_dataset_row_v1"
REPLAY_DATASET_BRIDGE_VERSION = "dataset_builder_bridge_v1"
REPLAY_DATASET_BUILD_MANIFEST_VERSION = "replay_dataset_build_manifest_v1"
DEFAULT_REPLAY_DATASET_OUTPUT_DIR = Path("data/datasets/replay_intermediate")
DEFAULT_REPLAY_DATASET_ANALYSIS_DIR = Path("data/analysis")
REPLAY_LABEL_QUALITY_MANIFEST_VERSION = "replay_label_quality_manifest_v1"
REPLAY_KEY_INTEGRITY_MANIFEST_VERSION = "replay_dataset_key_integrity_manifest_v1"

REPLAY_DATASET_SEMANTIC_SNAPSHOT_FIELDS_V1 = (
    "position_snapshot_v2",
    "response_raw_snapshot_v1",
    "response_vector_v2",
    "state_raw_snapshot_v1",
    "state_vector_v2",
    "evidence_vector_v1",
    "belief_state_v1",
    "barrier_state_v1",
    "observe_confirm_v1",
    "layer_mode_policy_v1",
    "layer_mode_logging_replay_v1",
)

REPLAY_DATASET_FORECAST_SNAPSHOT_FIELDS_V1 = (
    "forecast_features_v1",
    "transition_forecast_v1",
    "trade_management_forecast_v1",
    "forecast_gap_metrics_v1",
)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_timestamp(value: Any) -> float | str | None:
    if value in ("", None):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return str(value)


def _to_epoch(value: Any) -> float | None:
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
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


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


def _resolve_anchor_time(row: Mapping[str, Any] | None) -> tuple[str, float | str | None]:
    if not isinstance(row, Mapping):
        return "", None
    signal_bar_ts = _to_timestamp(row.get("signal_bar_ts"))
    if signal_bar_ts is not None:
        return "signal_bar_ts", signal_bar_ts
    time_value = _to_timestamp(row.get("time"))
    if time_value is not None:
        return "time", time_value
    return "", None


def _position_key(row: Mapping[str, Any] | None) -> int:
    if not isinstance(row, Mapping):
        return 0
    for field in ("ticket", "position_id"):
        value = _to_int(row.get(field), 0)
        if value > 0:
            return value
    return 0


def _decision_row_payload(decision_row: Mapping[str, Any] | None) -> dict[str, Any]:
    return _to_jsonable(_coerce_mapping(decision_row))


def _semantic_snapshots(decision_row: Mapping[str, Any] | None) -> dict[str, Any]:
    decision = _coerce_mapping(decision_row)
    return {
        field: _to_jsonable(_coerce_mapping(decision.get(field)))
        for field in REPLAY_DATASET_SEMANTIC_SNAPSHOT_FIELDS_V1
    }


def _forecast_snapshots(decision_row: Mapping[str, Any] | None) -> dict[str, Any]:
    decision = _coerce_mapping(decision_row)
    snapshots = {}
    for field in REPLAY_DATASET_FORECAST_SNAPSHOT_FIELDS_V1:
        value = decision.get(field)
        if field == "forecast_gap_metrics_v1":
            snapshots[field] = _to_jsonable(_coerce_mapping(value))
        else:
            snapshots[field] = _to_jsonable(_coerce_mapping(value))
    return snapshots


def _row_identity(decision_row: Mapping[str, Any] | None) -> dict[str, Any]:
    decision = _coerce_mapping(decision_row)
    anchor_time_field, anchor_time_value = _resolve_anchor_time(decision)
    return {
        "symbol": str(decision.get("symbol", "") or ""),
        "action": str(decision.get("action", "") or ""),
        "setup_id": str(decision.get("setup_id", "") or ""),
        "setup_side": str(decision.get("setup_side", "") or ""),
        "signal_timeframe": str(decision.get("signal_timeframe", "") or ""),
        "anchor_time_field": anchor_time_field,
        "anchor_time_value": anchor_time_value,
        "ticket": _position_key(decision),
    }


def resolve_replay_dataset_row_key(decision_row: Mapping[str, Any] | None) -> str:
    decision = _coerce_mapping(decision_row)
    explicit_key = str(decision.get("replay_row_key", "") or decision.get("decision_row_key", "") or "").strip()
    if explicit_key:
        return explicit_key
    return resolve_entry_decision_row_key(decision)


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
    return _to_jsonable(_coerce_mapping(outcome_labels))


def _empty_label_quality_manifest(*, dataset_path: Path) -> dict[str, Any]:
    return {
        "manifest_type": REPLAY_LABEL_QUALITY_MANIFEST_VERSION,
        "summary_contract": OUTCOME_LABEL_COMPACT_SUMMARY_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "dataset_path": str(dataset_path),
        "rows_total": 0,
        "label_positive_count": 0,
        "label_negative_count": 0,
        "label_unknown_count": 0,
        "ambiguous_rows": 0,
        "censored_rows": 0,
        "transition_status_counts": {},
        "management_status_counts": {},
        "source_descriptor_counts": {},
    }


def _update_label_quality_manifest(manifest: dict[str, Any], summary: Mapping[str, Any] | None) -> None:
    compact = _coerce_mapping(summary)
    if not compact:
        return
    manifest["rows_total"] = int(manifest.get("rows_total", 0)) + 1
    manifest["label_positive_count"] = int(manifest.get("label_positive_count", 0)) + _to_int(compact.get("label_positive_count"), 0)
    manifest["label_negative_count"] = int(manifest.get("label_negative_count", 0)) + _to_int(compact.get("label_negative_count"), 0)
    manifest["label_unknown_count"] = int(manifest.get("label_unknown_count", 0)) + _to_int(compact.get("label_unknown_count"), 0)
    if bool(compact.get("label_is_ambiguous")):
        manifest["ambiguous_rows"] = int(manifest.get("ambiguous_rows", 0)) + 1
    if bool(compact.get("is_censored")):
        manifest["censored_rows"] = int(manifest.get("censored_rows", 0)) + 1

    transition_status = str(compact.get("transition_label_status", "") or "").strip()
    if transition_status:
        transition_counts = dict(manifest.get("transition_status_counts", {}) or {})
        transition_counts[transition_status] = int(transition_counts.get(transition_status, 0)) + 1
        manifest["transition_status_counts"] = transition_counts

    management_status = str(compact.get("management_label_status", "") or "").strip()
    if management_status:
        management_counts = dict(manifest.get("management_status_counts", {}) or {})
        management_counts[management_status] = int(management_counts.get(management_status, 0)) + 1
        manifest["management_status_counts"] = management_counts

    source_descriptor = str(compact.get("label_source_descriptor", "") or "").strip()
    if source_descriptor:
        descriptor_counts = dict(manifest.get("source_descriptor_counts", {}) or {})
        descriptor_counts[source_descriptor] = int(descriptor_counts.get(source_descriptor, 0)) + 1
        manifest["source_descriptor_counts"] = descriptor_counts


def _write_label_quality_manifest(
    manifest: Mapping[str, Any] | None,
    *,
    analysis_dir: Path,
    timestamp: str,
) -> Path:
    payload = _to_jsonable(_coerce_mapping(manifest))
    path = analysis_dir / f"replay_label_quality_manifest_{timestamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_replay_dataset_build_manifest(
    manifest: Mapping[str, Any] | None,
    *,
    analysis_dir: Path,
    timestamp: str,
) -> Path:
    payload = _to_jsonable(_coerce_mapping(manifest))
    path = analysis_dir / f"replay_dataset_build_manifest_{timestamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _empty_key_integrity_manifest(*, dataset_path: Path) -> dict[str, Any]:
    return {
        "manifest_type": REPLAY_KEY_INTEGRITY_MANIFEST_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "dataset_path": str(dataset_path),
        "rows_total": 0,
        "missing_key_rows": {
            "decision_row_key": 0,
            "runtime_snapshot_key": 0,
            "trade_link_key": 0,
            "replay_row_key": 0,
        },
        "decision_replay_mismatch_rows": 0,
        "detail_schema_declared_rows": 0,
        "detail_row_key_present_rows": 0,
        "by_symbol": {},
    }


def _update_key_integrity_manifest(
    manifest: dict[str, Any],
    *,
    decision_row: Mapping[str, Any] | None,
    replay_row: Mapping[str, Any] | None,
) -> None:
    decision = _coerce_mapping(decision_row)
    replay = _coerce_mapping(replay_row)
    manifest["rows_total"] = int(manifest.get("rows_total", 0)) + 1

    symbol = str(replay.get("symbol", "") or decision.get("symbol", "") or "").upper().strip() or "__MISSING_SYMBOL__"
    by_symbol = dict(manifest.get("by_symbol", {}) or {})
    symbol_entry = dict(
        by_symbol.get(
            symbol,
            {
                "rows": 0,
                "missing_key_rows": {
                    "decision_row_key": 0,
                    "runtime_snapshot_key": 0,
                    "trade_link_key": 0,
                    "replay_row_key": 0,
                },
                "decision_replay_mismatch_rows": 0,
            },
        )
    )
    symbol_entry["rows"] = int(symbol_entry.get("rows", 0)) + 1

    for key_name in ("decision_row_key", "runtime_snapshot_key", "trade_link_key", "replay_row_key"):
        key_value = str(replay.get(key_name, "") or decision.get(key_name, "") or "").strip()
        if not key_value:
            missing = dict(manifest.get("missing_key_rows", {}) or {})
            missing[key_name] = int(missing.get(key_name, 0)) + 1
            manifest["missing_key_rows"] = missing

            symbol_missing = dict(symbol_entry.get("missing_key_rows", {}) or {})
            symbol_missing[key_name] = int(symbol_missing.get(key_name, 0)) + 1
            symbol_entry["missing_key_rows"] = symbol_missing

    decision_row_key = str(replay.get("decision_row_key", "") or decision.get("decision_row_key", "") or "").strip()
    replay_row_key = str(replay.get("replay_row_key", "") or decision.get("replay_row_key", "") or replay.get("row_key", "") or "").strip()
    if decision_row_key and replay_row_key and decision_row_key != replay_row_key:
        manifest["decision_replay_mismatch_rows"] = int(manifest.get("decision_replay_mismatch_rows", 0)) + 1
        symbol_entry["decision_replay_mismatch_rows"] = int(symbol_entry.get("decision_replay_mismatch_rows", 0)) + 1

    if str(decision.get("detail_schema_version", "") or "").strip():
        manifest["detail_schema_declared_rows"] = int(manifest.get("detail_schema_declared_rows", 0)) + 1
    if str(decision.get("detail_row_key", "") or "").strip():
        manifest["detail_row_key_present_rows"] = int(manifest.get("detail_row_key_present_rows", 0)) + 1

    by_symbol[symbol] = symbol_entry
    manifest["by_symbol"] = by_symbol


def _write_key_integrity_manifest(
    manifest: Mapping[str, Any] | None,
    *,
    analysis_dir: Path,
    timestamp: str,
) -> Path:
    payload = _to_jsonable(_coerce_mapping(manifest))
    path = analysis_dir / f"replay_dataset_key_integrity_manifest_{timestamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_project_path(path: str | Path | None, default_relative: Path) -> Path:
    target = Path(path) if path is not None else default_relative
    if not target.is_absolute():
        target = _project_root() / target
    return target


def _future_bar_companion_tokens(entry_path: Path) -> list[str]:
    stem = str(entry_path.stem or "").strip()
    if not stem:
        return []
    tokens: list[str] = []
    if stem.startswith("entry_decisions."):
        suffix = stem.split("entry_decisions.", 1)[1].strip()
        if suffix:
            tokens.append(suffix.replace(".", "_"))
    if stem.startswith("entry_decisions_"):
        suffix = stem.split("entry_decisions_", 1)[1].strip()
        if suffix:
            tokens.append(suffix.replace(".", "_"))
    if stem not in {"entry_decisions", ""}:
        tokens.append(stem.replace(".", "_"))
    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = str(token or "").strip("_ ").lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _resolve_default_future_bar_path(entry_path: Path) -> Path | None:
    market_bars_dir = _project_root() / "data" / "market_bars"
    if not market_bars_dir.exists():
        return None
    candidates: list[Path] = []
    for token in _future_bar_companion_tokens(entry_path):
        candidates.extend(sorted(market_bars_dir.glob(f"future_bars_{token}_*.csv")))
    if not candidates:
        return None
    candidates = sorted(
        {path.resolve() for path in candidates},
        key=lambda path: (path.stat().st_mtime, str(path)),
        reverse=True,
    )
    return candidates[0] if candidates else None


def _row_open_ts(row: Mapping[str, Any] | None) -> float:
    if not isinstance(row, Mapping):
        return float("inf")
    for field in ("open_ts", "open_time"):
        value = _to_epoch(row.get(field))
        if value is not None:
            return float(value)
    return float("inf")


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
            row_key = str(record.get("row_key", "") or "").strip()
            payload = record.get("payload", {})
            if not row_key or not isinstance(payload, Mapping):
                continue
            detail_index[row_key] = dict(payload)
    return detail_index


def _merge_detail_payload(
    row: Mapping[str, Any] | None,
    *,
    detail_index: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any]:
    merged = dict(row or {})
    if not detail_index:
        return merged
    candidate_keys: list[str] = []
    for candidate in (
        merged.get("detail_row_key", ""),
        merged.get("decision_row_key", ""),
        merged.get("replay_row_key", ""),
        resolve_replay_dataset_row_key(merged),
    ):
        candidate_text = str(candidate or "").strip()
        if candidate_text and candidate_text not in candidate_keys:
            candidate_keys.append(candidate_text)
    if not candidate_keys:
        return merged
    matched_key = ""
    detail_payload: Mapping[str, Any] | None = None
    for candidate_key in candidate_keys:
        payload = detail_index.get(candidate_key, {})
        if isinstance(payload, Mapping) and payload:
            matched_key = candidate_key
            detail_payload = payload
            break
    if not isinstance(detail_payload, Mapping) or not detail_payload:
        return merged
    merged.update(dict(detail_payload))
    merged["detail_row_key"] = matched_key
    return merged


def _build_closed_trade_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_ticket: dict[int, dict[str, Any]] = {}
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    by_symbol_open_ts: dict[str, list[float]] = {}
    for raw_row in rows:
        row = _coerce_mapping(raw_row)
        ticket = _position_key(row)
        if ticket > 0:
            by_ticket[ticket] = row
        symbol = str(row.get("symbol", "") or "").upper().strip()
        if symbol:
            by_symbol.setdefault(symbol, []).append(row)
    for symbol, symbol_rows in by_symbol.items():
        ordered = sorted(symbol_rows, key=_row_open_ts)
        by_symbol[symbol] = ordered
        by_symbol_open_ts[symbol] = [_row_open_ts(row) for row in ordered]
    return {
        "by_ticket": by_ticket,
        "by_symbol": by_symbol,
        "by_symbol_open_ts": by_symbol_open_ts,
    }


def _candidate_closed_trade_rows(
    decision_row: Mapping[str, Any] | None,
    *,
    closed_trade_index: Mapping[str, Any],
    candidate_window: int = 32,
) -> list[dict[str, Any]]:
    decision = _coerce_mapping(decision_row)
    ticket = _position_key(decision)
    by_ticket = dict(closed_trade_index.get("by_ticket", {}) or {})
    if ticket > 0 and ticket in by_ticket:
        return [dict(by_ticket[ticket])]

    symbol = str(decision.get("symbol", "") or "").upper().strip()
    if not symbol:
        return []
    symbol_rows = list((closed_trade_index.get("by_symbol", {}) or {}).get(symbol, []) or [])
    symbol_open_ts = list((closed_trade_index.get("by_symbol_open_ts", {}) or {}).get(symbol, []) or [])
    if not symbol_rows:
        return []

    _anchor_field, anchor_time_value = _resolve_anchor_time(decision)
    anchor_ts = _to_epoch(anchor_time_value) or 0.0
    if anchor_ts <= 0.0 or not symbol_open_ts:
        return [dict(row) for row in symbol_rows[:candidate_window]]

    start_index = bisect_left(symbol_open_ts, float(anchor_ts))
    window_rows = symbol_rows[start_index : start_index + candidate_window]
    if not window_rows and start_index > 0:
        window_rows = symbol_rows[max(0, start_index - 1) : max(0, start_index - 1) + candidate_window]
    return [dict(row) for row in window_rows]


def _future_bar_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for raw_row in rows:
        row = _coerce_mapping(raw_row)
        symbol = str(row.get("symbol", "") or "").upper().strip()
        if not symbol:
            continue
        index.setdefault(symbol, []).append(row)
    for symbol, symbol_rows in index.items():
        index[symbol] = sorted(symbol_rows, key=lambda row: _to_float(_to_timestamp(row.get("time")), float("inf")))
    return index


def _candidate_future_bars(
    decision_row: Mapping[str, Any] | None,
    *,
    future_bar_index: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    max_bars: int = 8,
) -> list[dict[str, Any]]:
    if not future_bar_index:
        return []
    decision = _coerce_mapping(decision_row)
    symbol = str(decision.get("symbol", "") or "").upper().strip()
    if not symbol:
        return []
    symbol_rows = list((future_bar_index or {}).get(symbol, []) or [])
    if not symbol_rows:
        return []
    _anchor_field, anchor_time_value = _resolve_anchor_time(decision)
    anchor_ts = _to_epoch(anchor_time_value) or 0.0
    selected: list[dict[str, Any]] = []
    for row in symbol_rows:
        bar_ts_float = _to_epoch(row.get("time")) or 0.0
        if anchor_ts > 0.0 and bar_ts_float <= anchor_ts:
            continue
        selected.append(dict(row))
        if len(selected) >= max_bars:
            break
    return selected


def _iter_entry_decision_rows(
    path: Path,
    *,
    limit: int | None = None,
    symbols: set[str] | None = None,
    entered_only: bool = False,
    detail_index: Mapping[str, Mapping[str, Any]] | None = None,
) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    emitted = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            if not isinstance(raw_row, Mapping):
                continue
            row = dict(raw_row)
            symbol = str(row.get("symbol", "") or "").upper().strip()
            if symbols and symbol not in symbols:
                continue
            if entered_only and str(row.get("outcome", "") or "").strip().lower() != "entered":
                continue
            yield _merge_detail_payload(row, detail_index=detail_index)
            emitted += 1
            if limit is not None and emitted >= int(limit):
                break


def build_replay_dataset_row(
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
    row_key = resolve_replay_dataset_row_key(decision)
    decision_row_key = str(decision.get("decision_row_key", "") or row_key)
    runtime_snapshot_key = str(decision.get("runtime_snapshot_key", "") or "")
    trade_link_key = str(decision.get("trade_link_key", "") or "")
    replay_row_key = str(decision.get("replay_row_key", "") or row_key)
    labels = outcome_labels or build_outcome_labels(
        decision,
        future_bars=future_bars,
        closed_trade_rows=closed_trade_rows,
        position_rows=position_rows,
        runtime_snapshot_rows=runtime_snapshot_rows,
        is_censored=is_censored,
    )
    labels_payload = _outcome_bundle_to_dict(labels)
    labels_metadata = _coerce_mapping(labels_payload.get("metadata"))
    compact_summary = build_outcome_label_compact_summary(
        labels_payload,
        row_key=row_key,
        forecast_snapshot=_forecast_snapshots(decision),
    )
    return {
        "row_type": REPLAY_DATASET_ROW_TYPE_V1,
        "dataset_builder_contract": REPLAY_DATASET_BRIDGE_VERSION,
        "row_key": row_key,
        "decision_row_key": decision_row_key,
        "runtime_snapshot_key": runtime_snapshot_key,
        "trade_link_key": trade_link_key,
        "replay_row_key": replay_row_key,
        "transition_label_status": str(compact_summary.get("transition_label_status", "") or ""),
        "management_label_status": str(compact_summary.get("management_label_status", "") or ""),
        "label_unknown_count": _to_int(compact_summary.get("label_unknown_count"), 0),
        "label_positive_count": _to_int(compact_summary.get("label_positive_count"), 0),
        "label_negative_count": _to_int(compact_summary.get("label_negative_count"), 0),
        "label_is_ambiguous": bool(compact_summary.get("label_is_ambiguous")),
        "label_source_descriptor": str(compact_summary.get("label_source_descriptor", "") or ""),
        "is_censored": bool(compact_summary.get("is_censored")),
        "row_identity": _row_identity(decision),
        "decision_row": _decision_row_payload(decision),
        "semantic_snapshots": _semantic_snapshots(decision),
        "forecast_snapshots": _forecast_snapshots(decision),
        "outcome_labels_v1": labels_payload,
        "label_quality_summary_v1": compact_summary,
        "forecast_branch_evaluation_v1": _to_jsonable(_coerce_mapping(labels_metadata.get("forecast_branch_evaluation_v1"))),
    }


def write_replay_dataset_batch(
    *,
    entry_decision_path: str | Path | None = None,
    closed_trade_path: str | Path | None = None,
    future_bar_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    analysis_dir: str | Path | None = None,
    limit: int | None = None,
    symbols: Sequence[str] | None = None,
    entered_only: bool = False,
    emit_validation_report: bool = True,
) -> dict[str, Any]:
    entry_path = _resolve_project_path(entry_decision_path, Path("data/trades/entry_decisions.csv"))
    closed_path = _resolve_project_path(closed_trade_path, Path("data/trades/trade_closed_history.csv"))
    future_path = _resolve_project_path(future_bar_path, Path("")) if future_bar_path is not None else None
    future_bar_resolution = "explicit" if future_path is not None else "none"
    if future_path is None:
        resolved_future_path = _resolve_default_future_bar_path(entry_path)
        if resolved_future_path is not None:
            future_path = resolved_future_path
            future_bar_resolution = "auto_companion"
    base_output_dir = _resolve_project_path(output_dir, DEFAULT_REPLAY_DATASET_OUTPUT_DIR)
    base_analysis_dir = _resolve_project_path(analysis_dir, DEFAULT_REPLAY_DATASET_ANALYSIS_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_path = Path(output_path) if output_path is not None else (base_output_dir / f"replay_dataset_rows_{timestamp}.jsonl")
    if not dataset_path.is_absolute():
        dataset_path = _project_root() / dataset_path
    dataset_path.parent.mkdir(parents=True, exist_ok=True)

    symbol_filter = {str(item).upper().strip() for item in list(symbols or []) if str(item).strip()}
    closed_trade_rows = _load_csv_rows(closed_path)
    closed_trade_index = _build_closed_trade_index(closed_trade_rows)
    future_bar_rows = _load_csv_rows(future_path) if future_path is not None and future_path.exists() else []
    future_index = _future_bar_index(future_bar_rows)
    detail_index = _load_detail_index(resolve_entry_decision_detail_path(entry_path))

    row_count = 0
    label_quality_manifest = _empty_label_quality_manifest(dataset_path=dataset_path)
    key_integrity_manifest = _empty_key_integrity_manifest(dataset_path=dataset_path)
    semantic_snapshot_present_counts = {field: 0 for field in REPLAY_DATASET_SEMANTIC_SNAPSHOT_FIELDS_V1}
    forecast_snapshot_present_counts = {field: 0 for field in REPLAY_DATASET_FORECAST_SNAPSHOT_FIELDS_V1}
    with dataset_path.open("w", encoding="utf-8", newline="") as handle:
        for decision_row in _iter_entry_decision_rows(
            entry_path,
            limit=limit,
            symbols=symbol_filter or None,
            entered_only=entered_only,
            detail_index=detail_index,
        ):
            candidate_closed_rows = _candidate_closed_trade_rows(
                decision_row,
                closed_trade_index=closed_trade_index,
            )
            candidate_future_bars = _candidate_future_bars(
                decision_row,
                future_bar_index=future_index,
            )
            replay_row = build_replay_dataset_row(
                decision_row,
                future_bars=candidate_future_bars,
                closed_trade_rows=candidate_closed_rows,
            )
            semantic_snapshots = _coerce_mapping(replay_row.get("semantic_snapshots"))
            forecast_snapshots = _coerce_mapping(replay_row.get("forecast_snapshots"))
            for field in REPLAY_DATASET_SEMANTIC_SNAPSHOT_FIELDS_V1:
                if _coerce_mapping(semantic_snapshots.get(field)):
                    semantic_snapshot_present_counts[field] = int(semantic_snapshot_present_counts.get(field, 0)) + 1
            for field in REPLAY_DATASET_FORECAST_SNAPSHOT_FIELDS_V1:
                if _coerce_mapping(forecast_snapshots.get(field)):
                    forecast_snapshot_present_counts[field] = int(forecast_snapshot_present_counts.get(field, 0)) + 1
            handle.write(json.dumps(replay_row, ensure_ascii=False) + "\n")
            _update_label_quality_manifest(label_quality_manifest, replay_row.get("label_quality_summary_v1"))
            _update_key_integrity_manifest(
                key_integrity_manifest,
                decision_row=decision_row,
                replay_row=replay_row,
            )
            row_count += 1

    label_quality_manifest_path = _write_label_quality_manifest(
        label_quality_manifest,
        analysis_dir=base_analysis_dir,
        timestamp=timestamp,
    )
    key_integrity_manifest_path = _write_key_integrity_manifest(
        key_integrity_manifest,
        analysis_dir=base_analysis_dir,
        timestamp=timestamp,
    )
    validation_report_path: str | None = None
    if emit_validation_report:
        report_path = write_outcome_label_validation_report_from_file(
            dataset_path,
            output_dir=base_analysis_dir,
        )
        validation_report_path = str(report_path)

    replay_build_manifest = {
        "manifest_type": REPLAY_DATASET_BUILD_MANIFEST_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "dataset_path": str(dataset_path),
        "entry_decision_path": str(entry_path),
        "detail_sidecar_path": str(resolve_entry_decision_detail_path(entry_path)),
        "closed_trade_path": str(closed_path),
        "future_bar_path": str(future_path) if future_path is not None else "",
        "future_bar_resolution": future_bar_resolution,
        "rows_written": int(row_count),
        "export_kind": "replay_intermediate",
        "selected_semantic_snapshot_fields": list(REPLAY_DATASET_SEMANTIC_SNAPSHOT_FIELDS_V1),
        "selected_forecast_snapshot_fields": list(REPLAY_DATASET_FORECAST_SNAPSHOT_FIELDS_V1),
        "missing_semantic_snapshot_fields": [
            field for field, count in semantic_snapshot_present_counts.items() if int(count) <= 0
        ],
        "missing_forecast_snapshot_fields": [
            field for field, count in forecast_snapshot_present_counts.items() if int(count) <= 0
        ],
        "semantic_snapshot_present_counts": dict(semantic_snapshot_present_counts),
        "forecast_snapshot_present_counts": dict(forecast_snapshot_present_counts),
        "label_quality_manifest_path": str(label_quality_manifest_path),
        "key_integrity_manifest_path": str(key_integrity_manifest_path),
        "validation_report_path": validation_report_path,
    }
    replay_build_manifest_path = _write_replay_dataset_build_manifest(
        replay_build_manifest,
        analysis_dir=base_analysis_dir,
        timestamp=timestamp,
    )

    return {
        "dataset_path": str(dataset_path),
        "validation_report_path": validation_report_path,
        "label_quality_manifest_path": str(label_quality_manifest_path),
        "key_integrity_manifest_path": str(key_integrity_manifest_path),
        "replay_build_manifest_path": str(replay_build_manifest_path),
        "rows_written": int(row_count),
        "entry_decision_path": str(entry_path),
        "closed_trade_path": str(closed_path),
        "future_bar_path": str(future_path) if future_path is not None else "",
        "future_bar_resolution": future_bar_resolution,
        "entered_only": bool(entered_only),
        "limit": int(limit) if limit is not None else None,
        "symbols": sorted(symbol_filter),
    }
