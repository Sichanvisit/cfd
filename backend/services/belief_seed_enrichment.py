"""Closed-history enrichment for belief replay/outcome bridge rows."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.services.trade_csv_schema import normalize_trade_df


BELIEF_SEED_ENRICHMENT_VERSION = "belief_seed_enrichment_v1"


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

    outcome = _as_mapping(row.get("belief_outcome_bridge_v1"))
    ticket = _to_int(outcome.get("ticket", row.get("ticket", 0)), 0)
    if ticket > 0:
        indices = list((match_index.get("by_ticket", {}) or {}).get(ticket, []) or [])
        if len(indices) == 1:
            return int(indices[0])
    return None


def _belief_confidence_rank(value: str) -> int:
    text = _to_str(value).lower()
    if text == "high":
        return 4
    if text == "medium":
        return 3
    if text == "weak_usable":
        return 2
    if text in {"low", "low_skip"}:
        return 1
    return 0


def _bridge_quality_rank(value: str) -> int:
    text = _to_str(value).lower()
    if text == "labeled":
        return 2
    if text == "skip":
        return 1
    return 0


def _candidate_sort_key(candidate: Mapping[str, Any] | None) -> tuple[int, int, int, float, float]:
    row = _as_mapping(candidate)
    outcome = _as_mapping(row.get("belief_outcome_bridge_v1"))
    label = _to_str(outcome.get("belief_outcome_label", "")).lower()
    confidence = _to_str(outcome.get("belief_label_confidence", "")).lower()
    quality_status = _to_str(outcome.get("bridge_quality_status", "")).lower()
    resolver = _as_mapping(outcome.get("belief_conflict_resolver_v1"))
    score_gap = abs(_to_float(resolver.get("score_gap"), 0.0))
    signal_bar_ts = _to_float(row.get("time", row.get("signal_bar_ts", 0.0)), 0.0)
    return (
        1 if label else 0,
        _belief_confidence_rank(confidence),
        _bridge_quality_rank(quality_status),
        score_gap,
        signal_bar_ts,
    )


def _compact_mix(values: Sequence[str], *, transform=str.lower) -> str:
    counts = Counter(transform(_to_str(value)) for value in values if _to_str(value))
    if not counts:
        return ""
    return ",".join(f"{label}:{count}" for label, count in sorted(counts.items()))


def _build_enrichment_value(rows: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    candidates = [_as_mapping(row) for row in (rows or []) if _as_mapping(row)]
    if not candidates:
        return {
            "belief_anchor_side": "",
            "belief_anchor_context": "",
            "belief_horizon_bars": 0,
            "belief_outcome_label": "",
            "belief_label_confidence": "",
            "belief_break_signature": "",
            "belief_bridge_quality_status": "",
            "belief_outcome_reason": "",
        }

    selected = max(candidates, key=_candidate_sort_key)
    outcome = _as_mapping(selected.get("belief_outcome_bridge_v1"))
    label = _to_str(outcome.get("belief_outcome_label", "")).lower()
    confidence = _to_str(outcome.get("belief_label_confidence", "")).lower()
    anchor_context = _to_str(outcome.get("belief_anchor_context", "")).lower()
    anchor_side = _to_str(outcome.get("belief_anchor_side", "")).upper()
    break_signature = _to_str(outcome.get("belief_break_signature", "")).lower()
    quality_status = _to_str(outcome.get("bridge_quality_status", "")).lower()
    reason_parts = [
        f"selected_row_key={_to_str(selected.get('row_key', '')) or 'unknown'}",
        f"linked_bridge_rows={len(candidates)}",
    ]
    label_mix = _compact_mix([_to_str(_as_mapping(item.get("belief_outcome_bridge_v1")).get("belief_outcome_label", "")).lower() for item in candidates], transform=str)
    confidence_mix = _compact_mix([_to_str(_as_mapping(item.get("belief_outcome_bridge_v1")).get("belief_label_confidence", "")).lower() for item in candidates], transform=str)
    context_mix = _compact_mix([_to_str(_as_mapping(item.get("belief_outcome_bridge_v1")).get("belief_anchor_context", "")).lower() for item in candidates], transform=str)
    if label_mix:
        reason_parts.append(f"label_mix={label_mix}")
    if confidence_mix:
        reason_parts.append(f"confidence_mix={confidence_mix}")
    if context_mix:
        reason_parts.append(f"context_mix={context_mix}")
    explicit_reason = _to_str(outcome.get("belief_outcome_reason", "")).lower()
    if explicit_reason:
        reason_parts.append(f"bridge_reason={explicit_reason}")

    return {
        "belief_anchor_side": anchor_side,
        "belief_anchor_context": anchor_context,
        "belief_horizon_bars": _to_int(outcome.get("belief_horizon_bars", 0), 0),
        "belief_outcome_label": label,
        "belief_label_confidence": confidence,
        "belief_break_signature": break_signature,
        "belief_bridge_quality_status": quality_status,
        "belief_outcome_reason": "|".join(reason_parts),
    }


def _existing_enrichment_present(row: pd.Series | Mapping[str, Any]) -> bool:
    return bool(
        _to_str(row.get("belief_outcome_label", ""))
        or _to_str(row.get("belief_label_confidence", ""))
        or _to_str(row.get("belief_break_signature", ""))
    )


def build_belief_seed_enrichment_plan(
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

    label_distribution: dict[str, int] = {}
    confidence_distribution: dict[str, int] = {}
    anchor_context_distribution: dict[str, int] = {}
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
        label = _to_str(enrichment.get("belief_outcome_label", ""))
        if not label:
            continue
        for target, source in (
            (label_distribution, "belief_outcome_label"),
            (confidence_distribution, "belief_label_confidence"),
            (anchor_context_distribution, "belief_anchor_context"),
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
        "contract_version": BELIEF_SEED_ENRICHMENT_VERSION,
        "total_closed_rows": int(len(dataset)),
        "replay_rows_total": int(len(replay_rows)),
        "unmatched_replay_rows": int(unmatched_replay_rows),
        "matched_trade_rows": int(len(grouped)),
        "existing_enriched_rows": int(existing_enriched_rows),
        "skipped_existing_rows": int(skipped_existing_rows),
        "overwrite_existing": bool(overwrite_existing),
        "label_distribution": dict(sorted(label_distribution.items())),
        "confidence_distribution": dict(sorted(confidence_distribution.items())),
        "anchor_context_distribution": dict(sorted(anchor_context_distribution.items())),
        "preview_samples": preview_samples,
    }


def apply_belief_seed_enrichment(
    frame: pd.DataFrame | None,
    *,
    replay_report: Mapping[str, Any] | None = None,
    overwrite_existing: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    dataset = normalize_trade_df(frame)
    initial_plan = build_belief_seed_enrichment_plan(
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
    skipped_unlabeled_rows = 0
    for row_index, rows in grouped.items():
        if _existing_enrichment_present(dataset.loc[row_index]) and not overwrite_existing:
            skipped_existing_rows += 1
            continue
        enrichment = _build_enrichment_value(rows)
        if not _to_str(enrichment.get("belief_outcome_label", "")):
            skipped_unlabeled_rows += 1
            continue
        for column, value in enrichment.items():
            dataset.at[row_index, column] = value
        updated_rows += 1

    report = dict(initial_plan)
    report.update(
        {
            "unmatched_replay_rows": int(unmatched_replay_rows),
            "updated_rows": int(updated_rows),
            "skipped_existing_rows": int(skipped_existing_rows),
            "skipped_unlabeled_rows": int(skipped_unlabeled_rows),
        }
    )
    return dataset, report


def load_belief_outcome_bridge_report(path: str | Path) -> dict[str, Any]:
    return _load_json(path)
