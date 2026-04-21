"""Closed-history enrichment for entry-side wait quality labels."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.services.trade_csv_schema import normalize_trade_df


ENTRY_WAIT_QUALITY_ENRICHMENT_VERSION = "entry_wait_quality_enrichment_v1"
ENTRY_WAIT_QUALITY_POSITIVE_LABELS = {"better_entry_after_wait", "avoided_loss_by_wait"}
ENTRY_WAIT_QUALITY_NEGATIVE_LABELS = {"missed_move_by_wait", "delayed_loss_after_wait"}
ENTRY_WAIT_QUALITY_SUPPORTED_LABELS = (
    ENTRY_WAIT_QUALITY_POSITIVE_LABELS
    | ENTRY_WAIT_QUALITY_NEGATIVE_LABELS
    | {"neutral_wait", "insufficient_evidence"}
)


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


def _to_timestamp(value: object) -> float:
    text = _to_str(value)
    if not text:
        return 0.0
    try:
        return pd.Timestamp(text).timestamp()
    except Exception:
        return _to_float(value, 0.0)


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


def _label_priority(label: str) -> tuple[int, int]:
    text = _to_str(label).lower()
    if text in ENTRY_WAIT_QUALITY_NEGATIVE_LABELS:
        return (2, 0)
    if text in ENTRY_WAIT_QUALITY_POSITIVE_LABELS:
        return (2, 1)
    if text == "neutral_wait":
        return (1, 0)
    if text == "insufficient_evidence":
        return (0, 0)
    return (-1, -1)


def _candidate_sort_key(candidate: Mapping[str, Any] | None) -> tuple[int, int, float, float]:
    row = _as_mapping(candidate)
    audit = _as_mapping(row.get("audit_result"))
    label = _to_str(audit.get("quality_label", "")).lower()
    valid = 1 if _to_str(audit.get("label_status", "")).upper() == "VALID" else 0
    priority, positive_flag = _label_priority(label)
    score = abs(_to_float(audit.get("quality_score"), 0.0))
    wait_ts = _to_timestamp(_as_mapping(row.get("wait_row")).get("time")) or _to_float(
        _as_mapping(row.get("wait_row")).get("signal_bar_ts"), 0.0
    )
    return (valid, priority, score, wait_ts + (positive_flag * 0.000001))


def _compact_label_mix(labels: Sequence[str]) -> str:
    counts = Counter(_to_str(label).lower() for label in labels if _to_str(label))
    if not counts:
        return ""
    return ",".join(f"{label}:{count}" for label, count in sorted(counts.items()))


def _build_enrichment_value(rows: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    candidates = [_as_mapping(row) for row in (rows or []) if _as_mapping(row)]
    if not candidates:
        return {
            "entry_wait_quality_label": "",
            "entry_wait_quality_score": 0.0,
            "entry_wait_quality_reason": "",
        }

    selected = max(candidates, key=_candidate_sort_key)
    audit = _as_mapping(selected.get("audit_result"))
    wait_row = _as_mapping(selected.get("wait_row"))
    selected_label = _to_str(audit.get("quality_label", "")).lower()
    selected_score = _to_float(audit.get("quality_score"), 0.0)
    labels = [_to_str(_as_mapping(item.get("audit_result")).get("quality_label", "")).lower() for item in candidates]
    reason_codes = ",".join(_to_str(code) for code in list(audit.get("reason_codes", []) or []) if _to_str(code))
    reason_parts = [
        f"selected={selected_label or 'unknown'}",
        f"linked_wait_rows={len(candidates)}",
    ]
    label_mix = _compact_label_mix(labels)
    if label_mix:
        reason_parts.append(f"label_mix={label_mix}")
    if reason_codes:
        reason_parts.append(f"reason_codes={reason_codes}")
    wait_time = _to_str(wait_row.get("time", ""))
    if wait_time:
        reason_parts.append(f"selected_wait_time={wait_time}")
    return {
        "entry_wait_quality_label": selected_label,
        "entry_wait_quality_score": round(float(selected_score), 4),
        "entry_wait_quality_reason": "|".join(reason_parts),
    }


def _existing_enrichment_present(row: pd.Series | Mapping[str, Any]) -> bool:
    return bool(_to_str(row.get("entry_wait_quality_label", "")))


def _replay_rows(report: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = _as_mapping(report)
    raw_rows = payload.get("rows", [])
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes, bytearray)):
        return []
    return [_as_mapping(row) for row in raw_rows if _as_mapping(row)]


def build_entry_wait_quality_enrichment_plan(
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
    linked_replay_rows = 0

    for replay_row in replay_rows:
        trade_row = _as_mapping(replay_row.get("next_closed_trade_row"))
        if not trade_row:
            continue
        linked_replay_rows += 1
        matched_index = _resolve_closed_row_index(trade_row, match_index=match_index)
        if matched_index is None:
            unmatched_replay_rows += 1
            continue
        grouped[int(matched_index)].append(replay_row)

    label_distribution: dict[str, int] = {}
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
        label = _to_str(enrichment.get("entry_wait_quality_label", "")).lower()
        if label:
            label_distribution[label] = int(label_distribution.get(label, 0)) + 1
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
        "contract_version": ENTRY_WAIT_QUALITY_ENRICHMENT_VERSION,
        "total_closed_rows": int(len(dataset)),
        "replay_rows_total": int(len(replay_rows)),
        "linked_replay_rows": int(linked_replay_rows),
        "unmatched_replay_rows": int(unmatched_replay_rows),
        "matched_trade_rows": int(len(grouped)),
        "existing_enriched_rows": int(existing_enriched_rows),
        "skipped_existing_rows": int(skipped_existing_rows),
        "overwrite_existing": bool(overwrite_existing),
        "label_distribution": dict(sorted(label_distribution.items())),
        "preview_samples": preview_samples,
    }


def apply_entry_wait_quality_enrichment(
    frame: pd.DataFrame | None,
    *,
    replay_report: Mapping[str, Any] | None = None,
    overwrite_existing: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    dataset = normalize_trade_df(frame)
    initial_plan = build_entry_wait_quality_enrichment_plan(
        dataset,
        replay_report=replay_report,
        overwrite_existing=overwrite_existing,
    )
    replay_rows = _replay_rows(replay_report)
    match_index = _build_closed_history_match_index(dataset)
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    unmatched_replay_rows = 0
    linked_replay_rows = 0
    for replay_row in replay_rows:
        trade_row = _as_mapping(replay_row.get("next_closed_trade_row"))
        if not trade_row:
            continue
        linked_replay_rows += 1
        matched_index = _resolve_closed_row_index(trade_row, match_index=match_index)
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
        dataset.at[row_index, "entry_wait_quality_label"] = enrichment["entry_wait_quality_label"]
        dataset.at[row_index, "entry_wait_quality_score"] = enrichment["entry_wait_quality_score"]
        dataset.at[row_index, "entry_wait_quality_reason"] = enrichment["entry_wait_quality_reason"]
        updated_rows += 1

    report = dict(initial_plan)
    report.update(
        {
            "linked_replay_rows": int(linked_replay_rows),
            "unmatched_replay_rows": int(unmatched_replay_rows),
            "updated_rows": int(updated_rows),
            "skipped_existing_rows": int(skipped_existing_rows),
        }
    )
    return dataset, report


def load_entry_wait_quality_replay_report(path: str | Path) -> dict[str, Any]:
    return _load_json(path)
