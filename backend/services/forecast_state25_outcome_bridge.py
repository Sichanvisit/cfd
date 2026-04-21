"""Replay/outcome bridge for forecast-state25 runtime rows."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.services.economic_learning_targets import build_economic_target_summary
from backend.services.entry_wait_quality_replay_bridge import (
    build_entry_wait_quality_replay_rows,
    resolve_default_future_bar_path,
)
from backend.services.forecast_state25_runtime_bridge import (
    FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_V1,
    build_forecast_state25_runtime_bridge_v1,
)
from backend.services.storage_compaction import (
    resolve_entry_decision_detail_path,
    resolve_entry_decision_row_key,
)
from backend.trading.engine.offline.outcome_labeler import (
    build_outcome_label_compact_summary,
    build_outcome_labels,
)


FORECAST_STATE25_OUTCOME_BRIDGE_VERSION = "forecast_state25_outcome_bridge_v1"
FORECAST_STATE25_OUTCOME_ROW_VERSION = "forecast_state25_outcome_row_v1"
FORECAST_STATE25_ECONOMIC_ROW_VERSION = "forecast_state25_economic_target_row_v1"
DEFAULT_OUTPUT_DIR = Path("data") / "analysis" / "forecast_state25"


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


def _runtime_bridge_payload(row: Mapping[str, Any] | None) -> dict[str, Any]:
    mapped = _as_mapping(row)
    existing = _as_mapping(mapped.get("forecast_state25_runtime_bridge_v1"))
    if existing:
        return existing
    return build_forecast_state25_runtime_bridge_v1(mapped)


def _row_has_bridge_candidate(row: Mapping[str, Any] | None) -> bool:
    mapped = _as_mapping(row)
    if _as_mapping(mapped.get("forecast_state25_runtime_bridge_v1")):
        return True
    return bool(
        _as_mapping(mapped.get("transition_forecast_v1"))
        or _as_mapping(mapped.get("trade_management_forecast_v1"))
        or _as_mapping(mapped.get("forecast_gap_metrics_v1"))
    )


def _wait_quality_row_key_index(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]],
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    bridged_rows = build_entry_wait_quality_replay_rows(
        entry_decision_rows=entry_decision_rows,
        closed_trade_rows=closed_trade_rows,
        future_bar_rows=future_bar_rows,
        dedupe=False,
    )
    index: dict[str, dict[str, Any]] = {}
    for bridged_row in bridged_rows:
        wait_row = _as_mapping(bridged_row.get("wait_row"))
        row_key = resolve_entry_decision_row_key(wait_row)
        if row_key and row_key not in index:
            index[row_key] = dict(bridged_row)
    return index


def _closed_trade_row_key_index(rows: Sequence[Mapping[str, Any]] | None) -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    for raw_row in rows or []:
        row = _as_mapping(raw_row)
        ticket = _to_int(row.get("ticket", row.get("position_id", 0)), 0)
        if ticket > 0 and ticket not in index:
            index[ticket] = row
    return index


def _economic_target_row_summary(closed_trade_row: Mapping[str, Any] | None) -> dict[str, Any]:
    row = _as_mapping(closed_trade_row)
    learning_total_label = _to_str(row.get("learning_total_label", "")).lower()
    loss_quality_label = _to_str(row.get("loss_quality_label", "")).lower()
    signed_exit_score = _to_float(row.get("signed_exit_score", 0.0), 0.0)
    profit = _to_float(row.get("profit", 0.0), 0.0)
    learning_total_score = _to_float(row.get("learning_total_score", 0.0), 0.0)
    available = bool(
        learning_total_label
        or loss_quality_label
        or abs(signed_exit_score) > 1e-9
        or abs(learning_total_score) > 1e-9
    )
    return {
        "contract_version": FORECAST_STATE25_ECONOMIC_ROW_VERSION,
        "available": bool(available),
        "position_key": _to_int(row.get("ticket", row.get("position_id", 0)), 0),
        "status": _to_str(row.get("status", "")).upper(),
        "exit_reason": _to_str(row.get("exit_reason", "")),
        "learning_total_label": learning_total_label,
        "learning_total_score": learning_total_score,
        "loss_quality_label": loss_quality_label,
        "signed_exit_score": signed_exit_score,
        "profit": profit,
    }


def _resolve_closed_trade_from_outcome_bundle(
    outcome_bundle: Mapping[str, Any] | None,
    *,
    closed_trade_index: Mapping[int, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    bundle = _as_mapping(outcome_bundle)
    transition = _as_mapping(bundle.get("transition"))
    management = _as_mapping(bundle.get("trade_management"))
    candidates = (
        _to_int(_as_mapping(_as_mapping(transition.get("metadata")).get("closed_trade_context")).get("position_key"), 0),
        _to_int(_as_mapping(_as_mapping(management.get("metadata")).get("closed_trade_context")).get("position_key"), 0),
    )
    for candidate in candidates:
        if candidate > 0 and isinstance(closed_trade_index, Mapping):
            row = _as_mapping(closed_trade_index.get(candidate))
            if row:
                return row
    return {}


def _bridge_quality_status(
    *,
    compact_summary: Mapping[str, Any] | None,
    wait_quality_label: str,
    economic_summary: Mapping[str, Any] | None,
) -> str:
    compact = _as_mapping(compact_summary)
    transition_status = _to_str(compact.get("transition_label_status", "")).upper()
    management_status = _to_str(compact.get("management_label_status", "")).upper()
    is_censored = bool(compact.get("is_censored", False))
    is_ambiguous = bool(compact.get("label_is_ambiguous", False))
    has_wait_quality = bool(wait_quality_label and wait_quality_label != "insufficient_evidence")
    has_economic = bool(_as_mapping(economic_summary).get("available", False))
    if is_censored:
        return "censored"
    if is_ambiguous:
        return "ambiguous"
    if transition_status == "VALID" and management_status == "VALID" and has_economic:
        return "full_outcome_bridge"
    if transition_status == "VALID" or management_status == "VALID" or has_wait_quality or has_economic:
        return "partial_outcome_bridge"
    return "insufficient_outcome_context"


def _scene_family_stats(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw_row in rows:
        row = _as_mapping(raw_row)
        bridge = _as_mapping(row.get("forecast_state25_runtime_bridge_v1"))
        state25_hint = _as_mapping(bridge.get("state25_runtime_hint_v1"))
        family = _to_str(state25_hint.get("scene_family", "unknown")).lower() or "unknown"
        grouped.setdefault(family, []).append(row)

    summary: dict[str, dict[str, float | int]] = {}
    for family, family_rows in grouped.items():
        transition_rates = []
        management_rates = []
        for row in family_rows:
            evaluation = _as_mapping(row.get("forecast_branch_evaluation_v1"))
            transition_summary = _as_mapping(_as_mapping(evaluation.get("transition_forecast_vs_outcome")).get("summary"))
            management_summary = _as_mapping(_as_mapping(evaluation.get("management_forecast_vs_outcome")).get("summary"))
            if _to_int(transition_summary.get("scorable_fields"), 0) > 0:
                transition_rates.append(_to_float(transition_summary.get("hit_rate"), 0.0))
            if _to_int(management_summary.get("scorable_fields"), 0) > 0:
                management_rates.append(_to_float(management_summary.get("hit_rate"), 0.0))
        summary[family] = {
            "count": len(family_rows),
            "transition_hit_rate_mean": round(sum(transition_rates) / len(transition_rates), 4) if transition_rates else 0.0,
            "management_hit_rate_mean": round(sum(management_rates) / len(management_rates), 4) if management_rates else 0.0,
        }
    return dict(sorted(summary.items(), key=lambda item: (-int(item[1]["count"]), item[0])))


def build_forecast_state25_outcome_bridge_rows(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]],
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
    position_rows: Sequence[Mapping[str, Any]] | None = None,
    runtime_snapshot_rows: Sequence[Mapping[str, Any]] | None = None,
    symbols: Sequence[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    normalized_symbols = {str(symbol or "").upper() for symbol in (symbols or []) if str(symbol or "").strip()}
    merged_rows = [_as_mapping(row) for row in entry_decision_rows]
    wait_quality_index = _wait_quality_row_key_index(
        entry_decision_rows=merged_rows,
        closed_trade_rows=closed_trade_rows,
        future_bar_rows=future_bar_rows,
    )
    closed_trade_index = _closed_trade_row_key_index(closed_trade_rows)

    target_rows = [row for row in merged_rows if _row_has_bridge_candidate(row)]
    if normalized_symbols:
        target_rows = [row for row in target_rows if _to_str(row.get("symbol", "")).upper() in normalized_symbols]
    target_rows = sorted(target_rows, key=_row_time)
    if limit is not None and int(limit) > 0:
        target_rows = target_rows[-int(limit) :]

    bridged_rows: list[dict[str, Any]] = []
    for row in target_rows:
        row_key = resolve_entry_decision_row_key(row)
        bridge = _runtime_bridge_payload(row)
        outcome_bundle = build_outcome_labels(
            row,
            future_bars=future_bar_rows,
            closed_trade_rows=closed_trade_rows,
            position_rows=position_rows,
            runtime_snapshot_rows=runtime_snapshot_rows,
        )
        outcome_bundle_dict = outcome_bundle.to_dict() if hasattr(outcome_bundle, "to_dict") else _as_mapping(outcome_bundle)
        compact_summary = build_outcome_label_compact_summary(
            outcome_bundle_dict,
            row_key=row_key,
            forecast_snapshot={
                "transition_forecast_v1": _as_mapping(row.get("transition_forecast_v1")),
                "trade_management_forecast_v1": _as_mapping(row.get("trade_management_forecast_v1")),
                "forecast_gap_metrics_v1": _as_mapping(row.get("forecast_gap_metrics_v1")),
            },
        )
        wait_bridge = _as_mapping(wait_quality_index.get(row_key))
        wait_result = _as_mapping(wait_bridge.get("audit_result"))
        wait_quality_label = _to_str(wait_result.get("quality_label", "")).lower()
        matched_closed_trade = _resolve_closed_trade_from_outcome_bundle(
            outcome_bundle_dict,
            closed_trade_index=closed_trade_index,
        )
        economic_summary = _economic_target_row_summary(matched_closed_trade)
        state25_hint = _as_mapping(bridge.get("state25_runtime_hint_v1"))
        forecast_summary = _as_mapping(bridge.get("forecast_runtime_summary_v1"))
        branch_evaluation = _as_mapping(_as_mapping(outcome_bundle_dict.get("metadata")).get("forecast_branch_evaluation_v1"))

        bridged_rows.append(
            {
                "contract_version": FORECAST_STATE25_OUTCOME_ROW_VERSION,
                "row_key": row_key,
                "runtime_scene_key": "|".join(
                    [
                        _to_str(row.get("symbol", "")).upper(),
                        str(int(_row_time(row))),
                        _to_str(state25_hint.get("scene_family", "unknown")).lower() or "unknown",
                        _to_str(forecast_summary.get("decision_hint", "")).upper() or "UNKNOWN",
                    ]
                ),
                "symbol": _to_str(row.get("symbol", "")).upper(),
                "signal_bar_ts": int(_row_time(row)),
                "forecast_state25_runtime_bridge_v1": bridge,
                "state25_runtime_hint_v1": state25_hint,
                "forecast_runtime_summary_v1": forecast_summary,
                "transition_outcome_labels_v1": _as_mapping(outcome_bundle_dict.get("transition")),
                "trade_management_outcome_labels_v1": _as_mapping(outcome_bundle_dict.get("trade_management")),
                "forecast_branch_evaluation_v1": branch_evaluation,
                "outcome_label_compact_summary_v1": compact_summary,
                "matched_closed_trade_row": matched_closed_trade,
                "entry_wait_quality_label": wait_quality_label,
                "entry_wait_quality_result_v1": wait_result,
                "economic_target_summary": economic_summary,
                "bridge_quality_status": _bridge_quality_status(
                    compact_summary=compact_summary,
                    wait_quality_label=wait_quality_label,
                    economic_summary=economic_summary,
                ),
            }
        )
    return bridged_rows


def build_forecast_state25_outcome_bridge_report(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]],
    closed_trade_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
    position_rows: Sequence[Mapping[str, Any]] | None = None,
    runtime_snapshot_rows: Sequence[Mapping[str, Any]] | None = None,
    symbols: Sequence[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    merged_rows = [_as_mapping(row) for row in entry_decision_rows]
    bridge_candidates = [row for row in merged_rows if _row_has_bridge_candidate(row)]
    bridged_rows = build_forecast_state25_outcome_bridge_rows(
        entry_decision_rows=merged_rows,
        closed_trade_rows=closed_trade_rows,
        future_bar_rows=future_bar_rows,
        position_rows=position_rows,
        runtime_snapshot_rows=runtime_snapshot_rows,
        symbols=symbols,
        limit=limit,
    )

    transition_status_counts: dict[str, int] = {}
    management_status_counts: dict[str, int] = {}
    bridge_quality_status_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}
    decision_hint_counts: dict[str, int] = {}
    wait_quality_label_counts: dict[str, int] = {}
    for row in bridged_rows:
        symbol = _to_str(row.get("symbol", "")).upper()
        if symbol:
            symbol_counts[symbol] = int(symbol_counts.get(symbol, 0)) + 1
        quality_status = _to_str(row.get("bridge_quality_status", "")).lower()
        if quality_status:
            bridge_quality_status_counts[quality_status] = int(bridge_quality_status_counts.get(quality_status, 0)) + 1
        compact = _as_mapping(row.get("outcome_label_compact_summary_v1"))
        transition_status = _to_str(compact.get("transition_label_status", "")).upper()
        management_status = _to_str(compact.get("management_label_status", "")).upper()
        if transition_status:
            transition_status_counts[transition_status] = int(transition_status_counts.get(transition_status, 0)) + 1
        if management_status:
            management_status_counts[management_status] = int(management_status_counts.get(management_status, 0)) + 1
        decision_hint = _to_str(_as_mapping(row.get("forecast_runtime_summary_v1")).get("decision_hint", "")).upper()
        if decision_hint:
            decision_hint_counts[decision_hint] = int(decision_hint_counts.get(decision_hint, 0)) + 1
        wait_label = _to_str(row.get("entry_wait_quality_label", "")).lower()
        if wait_label:
            wait_quality_label_counts[wait_label] = int(wait_quality_label_counts.get(wait_label, 0)) + 1

    transition_valid_rows = int(transition_status_counts.get("VALID", 0))
    management_valid_rows = int(management_status_counts.get("VALID", 0))
    rows_with_wait_quality = sum(1 for row in bridged_rows if _to_str(row.get("entry_wait_quality_label", "")) != "")
    rows_with_economic_target = sum(1 for row in bridged_rows if bool(_as_mapping(row.get("economic_target_summary")).get("available", False)))
    full_outcome_eligible_rows = int(bridge_quality_status_counts.get("full_outcome_bridge", 0))
    partial_outcome_eligible_rows = int(bridge_quality_status_counts.get("partial_outcome_bridge", 0))
    insufficient_future_bars_rows = 0
    for row in bridged_rows:
        compact = _as_mapping(row.get("outcome_label_compact_summary_v1"))
        transition_status = _to_str(compact.get("transition_label_status", "")).upper()
        management_status = _to_str(compact.get("management_label_status", "")).upper()
        if transition_status == "INSUFFICIENT_FUTURE_BARS" or management_status == "INSUFFICIENT_FUTURE_BARS":
            insufficient_future_bars_rows += 1
    economic_dataset_summary = build_economic_target_summary(pd.DataFrame(list(closed_trade_rows or [])))

    return {
        "contract_version": FORECAST_STATE25_OUTCOME_BRIDGE_VERSION,
        "scope_freeze_contract": FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_V1["contract_version"],
        "summary": {
            "raw_bridge_candidate_count": len(bridge_candidates),
            "bridged_row_count": len(bridged_rows),
            "transition_valid_rows": transition_valid_rows,
            "management_valid_rows": management_valid_rows,
            "full_outcome_eligible_rows": full_outcome_eligible_rows,
            "partial_outcome_eligible_rows": partial_outcome_eligible_rows,
            "insufficient_future_bars_rows": int(insufficient_future_bars_rows),
            "rows_with_wait_quality": rows_with_wait_quality,
            "rows_with_economic_target": rows_with_economic_target,
            "scene_family_stats": _scene_family_stats(bridged_rows),
        },
        "coverage": {
            "symbol_counts": dict(symbol_counts),
            "decision_hint_counts": dict(decision_hint_counts),
            "transition_status_counts": dict(transition_status_counts),
            "management_status_counts": dict(management_status_counts),
            "bridge_quality_status_counts": dict(bridge_quality_status_counts),
            "wait_quality_label_counts": dict(wait_quality_label_counts),
        },
        "economic_target_dataset_summary": economic_dataset_summary,
        "rows": bridged_rows,
    }


def render_forecast_state25_outcome_bridge_markdown(report: Mapping[str, Any] | None = None) -> str:
    payload = _as_mapping(report)
    summary = _as_mapping(payload.get("summary"))
    coverage = _as_mapping(payload.get("coverage"))
    scene_family_stats = _as_mapping(summary.get("scene_family_stats"))
    lines = [
        "# Forecast-State25 Outcome Bridge Report",
        "",
        f"- raw_bridge_candidate_count: {int(_to_int(summary.get('raw_bridge_candidate_count'), 0))}",
        f"- bridged_row_count: {int(_to_int(summary.get('bridged_row_count'), 0))}",
        f"- transition_valid_rows: {int(_to_int(summary.get('transition_valid_rows'), 0))}",
        f"- management_valid_rows: {int(_to_int(summary.get('management_valid_rows'), 0))}",
        f"- full_outcome_eligible_rows: {int(_to_int(summary.get('full_outcome_eligible_rows'), 0))}",
        f"- partial_outcome_eligible_rows: {int(_to_int(summary.get('partial_outcome_eligible_rows'), 0))}",
        f"- insufficient_future_bars_rows: {int(_to_int(summary.get('insufficient_future_bars_rows'), 0))}",
        f"- rows_with_wait_quality: {int(_to_int(summary.get('rows_with_wait_quality'), 0))}",
        f"- rows_with_economic_target: {int(_to_int(summary.get('rows_with_economic_target'), 0))}",
        "",
        "## Bridge Quality",
        "",
    ]
    for key, value in sorted(_as_mapping(coverage.get("bridge_quality_status_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(
        [
            "",
            "## Label Status",
            "",
        ]
    )
    for key, value in sorted(_as_mapping(coverage.get("transition_status_counts")).items()):
        lines.append(f"- transition_{key.lower()}: {int(_to_int(value, 0))}")
    for key, value in sorted(_as_mapping(coverage.get("management_status_counts")).items()):
        lines.append(f"- management_{key.lower()}: {int(_to_int(value, 0))}")
    lines.extend(
        [
            "",
            "## Scene Families",
            "",
        ]
    )
    for family, family_payload in list(scene_family_stats.items())[:10]:
        stats = _as_mapping(family_payload)
        lines.append(
            "- "
            f"{family}: count={int(_to_int(stats.get('count'), 0))}, "
            f"transition_hit_rate_mean={_to_float(stats.get('transition_hit_rate_mean'), 0.0):.4f}, "
            f"management_hit_rate_mean={_to_float(stats.get('management_hit_rate_mean'), 0.0):.4f}"
        )
    lines.extend(
        [
            "",
            "## Symbols",
            "",
        ]
    )
    for symbol, count in sorted(_as_mapping(coverage.get("symbol_counts")).items()):
        lines.append(f"- {symbol}: {int(_to_int(count, 0))}")
    return "\n".join(lines).strip() + "\n"


def write_forecast_state25_outcome_bridge_report(
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
    future_path = _resolve_project_path(future_bar_path, resolve_default_future_bar_path(entry_path) or Path("")) if future_bar_path or resolve_default_future_bar_path(entry_path) else Path("")
    output_target = _resolve_project_path(
        output_path,
        _project_root() / DEFAULT_OUTPUT_DIR / "forecast_state25_outcome_bridge_latest.json",
    )
    markdown_target = _resolve_project_path(
        markdown_output_path,
        _project_root() / DEFAULT_OUTPUT_DIR / "forecast_state25_outcome_bridge_latest.md",
    )

    entry_rows = _load_csv_rows(entry_path)
    detail_index = _load_detail_index(resolve_entry_decision_detail_path(entry_path))
    merged_entry_rows = [_merge_detail_payload(row, detail_index=detail_index) for row in entry_rows]
    closed_trade_rows = _load_csv_rows(closed_path)
    future_bar_rows = _load_csv_rows(future_path) if future_path and future_path.exists() else []

    report = build_forecast_state25_outcome_bridge_report(
        entry_decision_rows=merged_entry_rows,
        closed_trade_rows=closed_trade_rows,
        future_bar_rows=future_bar_rows,
        symbols=symbols,
        limit=limit,
    )
    output_target.parent.mkdir(parents=True, exist_ok=True)
    markdown_target.parent.mkdir(parents=True, exist_ok=True)
    report["output_path"] = str(output_target)
    report["markdown_output_path"] = str(markdown_target)
    output_target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_target.write_text(render_forecast_state25_outcome_bridge_markdown(report), encoding="utf-8")
    return report
