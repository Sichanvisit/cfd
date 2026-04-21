"""Closed-history enrichment for forecast-state25 replay/outcome bridge rows."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.services.trade_csv_schema import normalize_trade_df


FORECAST_STATE25_SEED_ENRICHMENT_VERSION = "forecast_state25_seed_enrichment_v1"


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


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


def _load_json(path: str | Path) -> dict[str, Any]:
    json_path = Path(path)
    if not json_path.exists():
        return {}
    return _as_mapping(json.loads(json_path.read_text(encoding="utf-8")))


def _build_closed_history_match_index(frame: pd.DataFrame) -> dict[str, dict[Any, list[int]]]:
    by_trade_link_key: dict[str, list[int]] = defaultdict(list)
    by_decision_row_key: dict[str, list[int]] = defaultdict(list)
    by_runtime_snapshot_key: dict[str, list[int]] = defaultdict(list)
    by_ticket: dict[int, list[int]] = defaultdict(list)
    by_symbol_open_ts: dict[tuple[str, int], list[int]] = defaultdict(list)

    for index, row in frame.iterrows():
        trade_link_key = _to_str(row.get("trade_link_key", ""))
        decision_row_key = _to_str(row.get("decision_row_key", ""))
        runtime_snapshot_key = _to_str(row.get("runtime_snapshot_key", ""))
        ticket = _to_int(row.get("ticket", 0), 0)
        symbol = _to_str(row.get("symbol", "")).upper()
        open_ts = _to_int(row.get("open_ts", 0), 0)
        if trade_link_key:
            by_trade_link_key[trade_link_key].append(int(index))
        if decision_row_key:
            by_decision_row_key[decision_row_key].append(int(index))
        if runtime_snapshot_key:
            by_runtime_snapshot_key[runtime_snapshot_key].append(int(index))
        if ticket > 0:
            by_ticket[ticket].append(int(index))
        if symbol and open_ts > 0:
            by_symbol_open_ts[(symbol, open_ts)].append(int(index))

    return {
        "by_trade_link_key": dict(by_trade_link_key),
        "by_decision_row_key": dict(by_decision_row_key),
        "by_runtime_snapshot_key": dict(by_runtime_snapshot_key),
        "by_ticket": dict(by_ticket),
        "by_symbol_open_ts": dict(by_symbol_open_ts),
    }


def _resolve_closed_row_index(
    trade_row: Mapping[str, Any] | None,
    *,
    match_index: Mapping[str, Mapping[Any, Sequence[int]]],
) -> int | None:
    trade = _as_mapping(trade_row)
    for field_name, index_name in (
        ("trade_link_key", "by_trade_link_key"),
        ("decision_row_key", "by_decision_row_key"),
        ("runtime_snapshot_key", "by_runtime_snapshot_key"),
    ):
        value = _to_str(trade.get(field_name, ""))
        indices = list((match_index.get(index_name, {}) or {}).get(value, []) or [])
        if len(indices) == 1:
            return int(indices[0])
    ticket = _to_int(trade.get("ticket", trade.get("position_id", 0)), 0)
    if ticket > 0:
        indices = list((match_index.get("by_ticket", {}) or {}).get(ticket, []) or [])
        if len(indices) == 1:
            return int(indices[0])
    symbol = _to_str(trade.get("symbol", "")).upper()
    open_ts = _to_int(trade.get("open_ts", 0), 0)
    if symbol and open_ts > 0:
        indices = list((match_index.get("by_symbol_open_ts", {}) or {}).get((symbol, open_ts), []) or [])
        if len(indices) == 1:
            return int(indices[0])
    return None


def _replay_rows(report: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = _as_mapping(report)
    raw_rows = payload.get("rows", [])
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes, bytearray)):
        return []
    return [_as_mapping(row) for row in raw_rows if _as_mapping(row)]


def _resolve_closed_row_index_from_bridge_row(
    bridge_row: Mapping[str, Any] | None,
    *,
    match_index: Mapping[str, Mapping[Any, Sequence[int]]],
) -> int | None:
    row = _as_mapping(bridge_row)
    matched_closed_trade_row = _as_mapping(row.get("matched_closed_trade_row"))
    matched_index = _resolve_closed_row_index(matched_closed_trade_row, match_index=match_index)
    if matched_index is not None:
        return matched_index

    row_key = _to_str(row.get("row_key", ""))
    if row_key:
        indices = list((match_index.get("by_decision_row_key", {}) or {}).get(row_key, []) or [])
        if len(indices) == 1:
            return int(indices[0])

    economic_summary = _as_mapping(row.get("economic_target_summary"))
    position_key = _to_int(economic_summary.get("position_key", 0), 0)
    if position_key > 0:
        indices = list((match_index.get("by_ticket", {}) or {}).get(position_key, []) or [])
        if len(indices) == 1:
            return int(indices[0])
    return None


def _bridge_quality_rank(status: str) -> int:
    text = _to_str(status).lower()
    if text == "full_outcome_bridge":
        return 3
    if text == "partial_outcome_bridge":
        return 2
    if text == "runtime_bridge_only":
        return 1
    return 0


def _outcome_status_rank(status: str) -> int:
    text = _to_str(status).upper()
    if text == "VALID":
        return 2
    if text:
        return 1
    return 0


def _candidate_sort_key(candidate: Mapping[str, Any] | None) -> tuple[int, int, int, int, float, float]:
    row = _as_mapping(candidate)
    compact = _as_mapping(row.get("outcome_label_compact_summary_v1"))
    transition_status = _to_str(compact.get("transition_label_status", "")).upper()
    management_status = _to_str(compact.get("management_label_status", "")).upper()
    quality_status = _to_str(row.get("bridge_quality_status", "")).lower()
    wait_quality_label = _to_str(row.get("entry_wait_quality_label", "")).lower()
    wait_quality_result = _as_mapping(row.get("entry_wait_quality_result_v1"))
    economic_summary = _as_mapping(row.get("economic_target_summary"))
    info_score = abs(_to_float(wait_quality_result.get("quality_score"), 0.0)) + abs(
        _to_float(economic_summary.get("learning_total_score"), 0.0)
    )
    signal_bar_ts = _to_float(row.get("signal_bar_ts", 0.0), 0.0)
    return (
        _bridge_quality_rank(quality_status),
        _outcome_status_rank(transition_status) + _outcome_status_rank(management_status),
        1 if bool(economic_summary.get("available", False)) else 0,
        1 if wait_quality_label else 0,
        info_score,
        signal_bar_ts,
    )


def _compact_mix(values: Sequence[str], *, transform=str.lower) -> str:
    counts = Counter(transform(_to_str(value)) for value in values if _to_str(value))
    if not counts:
        return ""
    return ",".join(f"{label}:{count}" for label, count in sorted(counts.items()))


def _normalize_outcome_status(value: object) -> str:
    return _to_str(value).strip().lower().replace(" ", "_")


def _build_enrichment_value(rows: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    candidates = [_as_mapping(row) for row in (rows or []) if _as_mapping(row)]
    if not candidates:
        return {
            "forecast_state25_scene_family": "",
            "forecast_state25_group_hint": "",
            "forecast_confirm_side": "",
            "forecast_decision_hint": "",
            "forecast_wait_confirm_gap": 0.0,
            "forecast_hold_exit_gap": 0.0,
            "forecast_same_side_flip_gap": 0.0,
            "forecast_belief_barrier_tension_gap": 0.0,
            "forecast_transition_outcome_status": "",
            "forecast_management_outcome_status": "",
            "forecast_state25_bridge_quality_status": "",
            "forecast_state25_bridge_reason": "",
        }

    selected = max(candidates, key=_candidate_sort_key)
    bridge = _as_mapping(selected.get("forecast_state25_runtime_bridge_v1"))
    state25_hint = _as_mapping(selected.get("state25_runtime_hint_v1")) or _as_mapping(bridge.get("state25_runtime_hint_v1"))
    forecast_summary = _as_mapping(selected.get("forecast_runtime_summary_v1")) or _as_mapping(
        bridge.get("forecast_runtime_summary_v1")
    )
    compact = _as_mapping(selected.get("outcome_label_compact_summary_v1"))
    transition_status = _normalize_outcome_status(compact.get("transition_label_status", ""))
    management_status = _normalize_outcome_status(compact.get("management_label_status", ""))
    bridge_quality_status = _to_str(selected.get("bridge_quality_status", "")).lower()
    decision_hints = [
        _to_str(_as_mapping(item.get("forecast_runtime_summary_v1")).get("decision_hint", "")).upper()
        for item in candidates
    ]
    quality_mix = _compact_mix([_to_str(item.get("bridge_quality_status", "")).lower() for item in candidates], transform=str)
    transition_mix = _compact_mix(
        [
            _normalize_outcome_status(_as_mapping(item.get("outcome_label_compact_summary_v1")).get("transition_label_status", ""))
            for item in candidates
        ],
        transform=str,
    )
    management_mix = _compact_mix(
        [
            _normalize_outcome_status(_as_mapping(item.get("outcome_label_compact_summary_v1")).get("management_label_status", ""))
            for item in candidates
        ],
        transform=str,
    )
    reason_parts = [
        f"selected_row_key={_to_str(selected.get('row_key', '')) or 'unknown'}",
        f"linked_bridge_rows={len(candidates)}",
    ]
    decision_mix = _compact_mix(decision_hints, transform=str)
    if decision_mix:
        reason_parts.append(f"decision_hint_mix={decision_mix}")
    if quality_mix:
        reason_parts.append(f"bridge_quality_mix={quality_mix}")
    if transition_mix:
        reason_parts.append(f"transition_status_mix={transition_mix}")
    if management_mix:
        reason_parts.append(f"management_status_mix={management_mix}")

    return {
        "forecast_state25_scene_family": _to_str(state25_hint.get("scene_family", "")).lower(),
        "forecast_state25_group_hint": _to_str(state25_hint.get("scene_group_hint", "")),
        "forecast_confirm_side": _to_str(forecast_summary.get("confirm_side", "")).upper(),
        "forecast_decision_hint": _to_str(forecast_summary.get("decision_hint", "")).upper(),
        "forecast_wait_confirm_gap": round(_to_float(forecast_summary.get("wait_confirm_gap", 0.0), 0.0), 6),
        "forecast_hold_exit_gap": round(_to_float(forecast_summary.get("hold_exit_gap", 0.0), 0.0), 6),
        "forecast_same_side_flip_gap": round(_to_float(forecast_summary.get("same_side_flip_gap", 0.0), 0.0), 6),
        "forecast_belief_barrier_tension_gap": round(
            _to_float(forecast_summary.get("belief_barrier_tension_gap", 0.0), 0.0),
            6,
        ),
        "forecast_transition_outcome_status": transition_status,
        "forecast_management_outcome_status": management_status,
        "forecast_state25_bridge_quality_status": bridge_quality_status,
        "forecast_state25_bridge_reason": "|".join(reason_parts),
    }


def _existing_enrichment_present(row: pd.Series | Mapping[str, Any]) -> bool:
    return bool(
        _to_str(row.get("forecast_state25_scene_family", ""))
        or _to_str(row.get("forecast_decision_hint", ""))
        or _to_str(row.get("forecast_transition_outcome_status", ""))
        or _to_str(row.get("forecast_management_outcome_status", ""))
    )


def build_forecast_state25_seed_enrichment_plan(
    frame: pd.DataFrame | None,
    *,
    replay_report: Mapping[str, Any] | None = None,
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    dataset = normalize_trade_df(frame)
    replay_rows = _replay_rows(replay_report)
    match_index = _build_closed_history_match_index(dataset)
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    unmatched_replay_rows = 0

    for replay_row in replay_rows:
        matched_index = _resolve_closed_row_index_from_bridge_row(replay_row, match_index=match_index)
        if matched_index is None:
            unmatched_replay_rows += 1
            continue
        grouped[int(matched_index)].append(replay_row)

    scene_family_distribution: dict[str, int] = {}
    decision_hint_distribution: dict[str, int] = {}
    transition_status_distribution: dict[str, int] = {}
    management_status_distribution: dict[str, int] = {}
    bridge_quality_distribution: dict[str, int] = {}
    existing_enriched_rows = 0
    skipped_existing_rows = 0
    preview_samples: list[dict[str, Any]] = []
    for row_index, rows in grouped.items():
        existing = _existing_enrichment_present(dataset.loc[row_index])
        if existing:
            existing_enriched_rows += 1
            if not overwrite_existing:
                skipped_existing_rows += 1
                continue
        enrichment = _build_enrichment_value(rows)
        for target, source in (
            (scene_family_distribution, "forecast_state25_scene_family"),
            (decision_hint_distribution, "forecast_decision_hint"),
            (transition_status_distribution, "forecast_transition_outcome_status"),
            (management_status_distribution, "forecast_management_outcome_status"),
            (bridge_quality_distribution, "forecast_state25_bridge_quality_status"),
        ):
            value = _to_str(enrichment.get(source, ""))
            if value:
                target[value] = int(target.get(value, 0)) + 1
        if len(preview_samples) < 10:
            preview_samples.append(
                {
                    "row_index": int(row_index),
                    "ticket": str(dataset.loc[row_index].get("ticket", "") or ""),
                    "symbol": str(dataset.loc[row_index].get("symbol", "") or ""),
                    **enrichment,
                }
            )

    return {
        "contract_version": FORECAST_STATE25_SEED_ENRICHMENT_VERSION,
        "total_closed_rows": int(len(dataset)),
        "replay_rows_total": int(len(replay_rows)),
        "unmatched_replay_rows": int(unmatched_replay_rows),
        "matched_trade_rows": int(len(grouped)),
        "existing_enriched_rows": int(existing_enriched_rows),
        "skipped_existing_rows": int(skipped_existing_rows),
        "overwrite_existing": bool(overwrite_existing),
        "scene_family_distribution": dict(sorted(scene_family_distribution.items())),
        "decision_hint_distribution": dict(sorted(decision_hint_distribution.items())),
        "transition_status_distribution": dict(sorted(transition_status_distribution.items())),
        "management_status_distribution": dict(sorted(management_status_distribution.items())),
        "bridge_quality_distribution": dict(sorted(bridge_quality_distribution.items())),
        "preview_samples": preview_samples,
    }


def apply_forecast_state25_seed_enrichment(
    frame: pd.DataFrame | None,
    *,
    replay_report: Mapping[str, Any] | None = None,
    overwrite_existing: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    dataset = normalize_trade_df(frame)
    initial_plan = build_forecast_state25_seed_enrichment_plan(
        dataset,
        replay_report=replay_report,
        overwrite_existing=overwrite_existing,
    )
    replay_rows = _replay_rows(replay_report)
    match_index = _build_closed_history_match_index(dataset)
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    unmatched_replay_rows = 0
    for replay_row in replay_rows:
        matched_index = _resolve_closed_row_index_from_bridge_row(replay_row, match_index=match_index)
        if matched_index is None:
            unmatched_replay_rows += 1
            continue
        grouped[int(matched_index)].append(replay_row)

    updated_rows = 0
    skipped_existing_rows = 0
    for row_index, rows in grouped.items():
        if _existing_enrichment_present(dataset.loc[row_index]) and not overwrite_existing:
            skipped_existing_rows += 1
            continue
        enrichment = _build_enrichment_value(rows)
        for column, value in enrichment.items():
            dataset.at[row_index, column] = value
        updated_rows += 1

    report = dict(initial_plan)
    report.update(
        {
            "unmatched_replay_rows": int(unmatched_replay_rows),
            "updated_rows": int(updated_rows),
            "skipped_existing_rows": int(skipped_existing_rows),
        }
    )
    return dataset, report


def load_forecast_state25_outcome_bridge_report(path: str | Path) -> dict[str, Any]:
    return _load_json(path)
