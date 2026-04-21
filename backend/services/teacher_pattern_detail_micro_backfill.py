"""Richer teacher-pattern backfill using entry decision detail JSONL payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from backend.services.teacher_pattern_labeler import build_teacher_pattern_payload_v2
from backend.services.trade_csv_schema import (
    MICRO_STRUCTURE_SEMANTIC_COLUMNS,
    MICRO_STRUCTURE_SOURCE_COLUMNS,
    TEACHER_PATTERN_COLUMNS,
    normalize_trade_df,
)


DETAIL_BACKFILL_LABEL_SOURCE = "rule_v2_detail_backfill"
DETAIL_BACKFILL_LABEL_REVIEW_STATUS = "backfilled_unreviewed"
DEFAULT_DETAIL_FILE_GLOB = "entry_decisions.detail.rotate_*.jsonl"


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _to_float(value: Any, default: float | None = None) -> float | None:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def _to_int(value: Any, default: int | None = None) -> int | None:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return int(parsed)


def _is_default_like_atr_ratio(value: Any) -> bool:
    parsed = _to_float(value, None)
    if parsed is None:
        return True
    return abs(float(parsed)) <= 1e-12 or abs(float(parsed) - 1.0) <= 1e-12


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    text = _to_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _truthy_key_values(*values: Any) -> list[str]:
    keys: list[str] = []
    for value in values:
        text = _to_text(value)
        if text:
            keys.append(text)
    return keys


def _is_labeled_row(row: pd.Series | dict[str, Any]) -> bool:
    teacher_pattern_id = pd.to_numeric(row.get("teacher_pattern_id"), errors="coerce")
    teacher_pattern_name = _to_text(row.get("teacher_pattern_name"))
    return bool((not pd.isna(teacher_pattern_id) and int(teacher_pattern_id) > 0) or teacher_pattern_name)


def _scoped_indices(frame: pd.DataFrame, recent_limit: int | None) -> list[int]:
    if recent_limit is None or int(recent_limit) <= 0 or len(frame) <= int(recent_limit):
        return list(frame.index)
    working = frame.copy()
    if "close_ts" in working.columns:
        recent_key = pd.to_numeric(working["close_ts"], errors="coerce").fillna(0)
    elif "close_time" in working.columns:
        recent_key = pd.to_datetime(working["close_time"], errors="coerce").view("int64").fillna(0)
    else:
        recent_key = pd.Series(range(len(working)), index=working.index, dtype=float)
    if (recent_key <= 0).all() and "open_ts" in working.columns:
        recent_key = pd.to_numeric(working["open_ts"], errors="coerce").fillna(0)
    ordered = (
        working.assign(_recent_key=recent_key)
        .sort_values(by="_recent_key", ascending=False, kind="stable")
        .head(int(recent_limit))
        .index
    )
    return list(ordered)


def _has_link_key(row: pd.Series | dict[str, Any]) -> bool:
    return any(
        _to_text(row.get(column))
        for column in ("decision_row_key", "runtime_snapshot_key", "trade_link_key")
    )


def _needs_micro_enrichment(row: pd.Series | dict[str, Any]) -> bool:
    semantic_missing = all(_to_text(row.get(column)) == "" for column in MICRO_STRUCTURE_SEMANTIC_COLUMNS)
    numeric_missing = True
    for column in MICRO_STRUCTURE_SOURCE_COLUMNS:
        value = row.get(column)
        parsed = _to_float(value, None)
        if parsed is not None and abs(parsed) > 1e-12:
            numeric_missing = False
            break
    entry_atr_ratio = _to_float(row.get("entry_atr_ratio"), None)
    atr_missing = entry_atr_ratio is None or abs(float(entry_atr_ratio) - 1.0) <= 1e-12 or abs(float(entry_atr_ratio)) <= 1e-12
    return semantic_missing or numeric_missing or atr_missing


def resolve_default_detail_paths(detail_dir: str | Path) -> list[Path]:
    base_dir = Path(detail_dir)
    paths: list[Path] = []
    current = base_dir / "entry_decisions.detail.jsonl"
    if current.exists():
        paths.append(current)
    rotated = sorted(
        base_dir.glob(DEFAULT_DETAIL_FILE_GLOB),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    paths.extend(rotated)
    return paths


def _build_target_index(dataset: pd.DataFrame, recent_limit: int | None) -> tuple[dict[int, dict[str, Any]], dict[str, list[int]]]:
    targets: dict[int, dict[str, Any]] = {}
    key_to_indices: dict[str, list[int]] = {}
    for index in _scoped_indices(dataset, recent_limit):
        row = dataset.loc[index]
        if not _has_link_key(row):
            continue
        if _is_labeled_row(row) and not _needs_micro_enrichment(row):
            continue
        targets[int(index)] = row.to_dict()
        for key in _truthy_key_values(
            row.get("decision_row_key"),
            row.get("trade_link_key"),
        ):
            key_to_indices.setdefault(key, []).append(int(index))
    return targets, key_to_indices


def _iter_detail_records(detail_paths: Iterable[Path]) -> Iterable[tuple[Path, dict[str, Any], list[str]]]:
    for path in detail_paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    detail = json.loads(line)
                except Exception:
                    continue
                payload = detail.get("payload")
                if not isinstance(payload, dict):
                    continue
                keys = _truthy_key_values(
                    payload.get("decision_row_key"),
                    payload.get("trade_link_key"),
                )
                if not keys:
                    continue
                yield path, payload, keys


def _resolve_detail_matches(
    detail_paths: Iterable[Path],
    key_to_indices: dict[str, list[int]],
) -> tuple[dict[int, dict[str, Any]], list[str], int]:
    matched_payloads: dict[int, dict[str, Any]] = {}
    unresolved = {index for indices in key_to_indices.values() for index in indices}
    scanned_paths: list[str] = []
    records_scanned = 0

    for path, payload, keys in _iter_detail_records(detail_paths):
        if str(path) not in scanned_paths:
            scanned_paths.append(str(path))
        records_scanned += 1
        matched_indices: set[int] = set()
        for key in keys:
            for index in key_to_indices.get(key, []):
                if index in unresolved:
                    matched_indices.add(index)
        for index in matched_indices:
            matched_payloads[index] = payload
            unresolved.discard(index)
        if not unresolved:
            break

    return matched_payloads, scanned_paths, records_scanned


def _build_swing_retest_proxy(response_raw: dict[str, Any], side: str) -> int:
    side_u = _to_text(side).upper()
    if side_u == "HIGH":
        pattern_score = max(
            _to_float(response_raw.get("pattern_double_top"), 0.0) or 0.0,
            _to_float(response_raw.get("sr_resistance_touch"), 0.0) or 0.0,
            _to_float(response_raw.get("sr_resistance_reject"), 0.0) or 0.0,
        )
    else:
        pattern_score = max(
            _to_float(response_raw.get("pattern_double_bottom"), 0.0) or 0.0,
            _to_float(response_raw.get("sr_support_touch"), 0.0) or 0.0,
            _to_float(response_raw.get("sr_support_hold"), 0.0) or 0.0,
            _to_float(response_raw.get("sr_support_reclaim"), 0.0) or 0.0,
        )
    if pattern_score >= 0.75:
        return 3
    if pattern_score >= 0.30:
        return 2
    return 0


def _derive_breakout_state(compression: float, volume_burst: float) -> str:
    if compression >= 0.80:
        return "COILED_BREAKOUT"
    if compression >= 0.70 or (compression >= 0.55 and volume_burst >= 1.8):
        return "READY_BREAKOUT"
    if compression >= 0.45:
        return "BUILDING_BREAKOUT"
    return ""


def _derive_reversal_state(upper_wick: float, lower_wick: float, doji_ratio: float, response_raw: dict[str, Any]) -> str:
    response_proxy = max(
        _to_float(response_raw.get("pattern_double_top"), 0.0) or 0.0,
        _to_float(response_raw.get("pattern_double_bottom"), 0.0) or 0.0,
        _to_float(response_raw.get("micro_indecision"), 0.0) or 0.0,
    )
    strength = max(upper_wick, lower_wick, doji_ratio, response_proxy)
    if strength >= 0.30:
        return "HIGH_RISK"
    if strength >= 0.18:
        return "MEDIUM_RISK"
    return "LOW_RISK" if strength > 0.0 else ""


def _derive_participation_state(volume_burst: float, tick_volume_ratio: float, real_volume_ratio: float) -> str:
    effective = max(volume_burst, tick_volume_ratio, real_volume_ratio)
    if effective >= 1.8:
        return "ACTIVE_PARTICIPATION"
    if effective > 0.0 and effective <= 1.05:
        return "THIN_PARTICIPATION"
    return "STEADY_PARTICIPATION" if effective > 0.0 else ""


def _derive_gap_context_state(gap_fill_progress: float | None) -> str:
    if gap_fill_progress is None:
        return ""
    if 0.0 < gap_fill_progress < 1.0:
        return "GAP_PARTIAL_FILL"
    if gap_fill_progress >= 1.0:
        return "GAP_FILLED"
    return "NO_GAP_CONTEXT"


def _extract_detail_enrichment(payload: dict[str, Any]) -> dict[str, Any]:
    state_raw = _coerce_mapping(payload.get("state_raw_snapshot_v1"))
    response_raw = _coerce_mapping(payload.get("response_raw_snapshot_v1"))
    state_meta = _coerce_mapping(state_raw.get("metadata"))

    def _normalize_body_size_pct(raw_value: Any) -> float:
        raw = _to_float(raw_value, None)
        if raw is None:
            return 0.0
        if raw <= 5.0:
            return float(raw)
        reference_price = (
            _to_float(payload.get("entry_request_price"), None)
            or _to_float(payload.get("entry_fill_price"), None)
            or _to_float(state_raw.get("s_current_price"), None)
            or _to_float(state_meta.get("price"), None)
        )
        if reference_price is None or reference_price <= 0.0:
            return float(raw)
        return float((raw / reference_price) * 100.0)

    body_size_raw = state_raw.get("s_body_size_pct_20")
    if (_to_float(body_size_raw, None) or 0.0) <= 0.0:
        body_size_raw = state_raw.get("s_recent_body_mean")
    body_size_pct_20 = _normalize_body_size_pct(body_size_raw)
    doji_ratio_20 = _to_float(state_raw.get("s_doji_ratio_20"), 0.0) or 0.0
    same_color_run_current = _to_int(state_raw.get("s_same_color_run_current"), 0) or 0
    same_color_run_max_20 = _to_int(state_raw.get("s_same_color_run_max_20"), 0) or 0
    range_compression_ratio_20 = _to_float(state_raw.get("s_range_compression_ratio_20"), None)
    if (range_compression_ratio_20 or 0.0) <= 0.0:
        range_compression_ratio_20 = _to_float(state_raw.get("s_compression"), 0.0)
    range_compression_ratio_20 = range_compression_ratio_20 or 0.0
    volume_burst_ratio_20 = _to_float(state_raw.get("s_volume_burst_ratio_20"), None)
    if (volume_burst_ratio_20 or 0.0) <= 0.0:
        volume_burst_ratio_20 = max(
            _to_float(state_raw.get("s_tick_volume_ratio"), 0.0) or 0.0,
            _to_float(state_raw.get("s_real_volume_ratio"), 0.0) or 0.0,
        )
    volume_burst_ratio_20 = volume_burst_ratio_20 or 0.0
    volume_burst_decay_20 = _to_float(state_raw.get("s_volume_burst_decay_20"), 0.0) or 0.0
    gap_fill_progress = _to_float(state_raw.get("s_gap_fill_progress"), None)

    upper_wick_ratio_20 = _to_float(state_raw.get("s_upper_wick_ratio_20"), 0.0) or 0.0
    lower_wick_ratio_20 = _to_float(state_raw.get("s_lower_wick_ratio_20"), 0.0) or 0.0
    swing_high_retest_count_20 = _build_swing_retest_proxy(response_raw, "HIGH")
    swing_low_retest_count_20 = _build_swing_retest_proxy(response_raw, "LOW")

    tick_volume_ratio = _to_float(state_raw.get("s_tick_volume_ratio"), 0.0) or 0.0
    real_volume_ratio = _to_float(state_raw.get("s_real_volume_ratio"), 0.0) or 0.0
    semantic = {
        "micro_breakout_readiness_state": _derive_breakout_state(range_compression_ratio_20, volume_burst_ratio_20),
        "micro_reversal_risk_state": _derive_reversal_state(
            upper_wick_ratio_20,
            lower_wick_ratio_20,
            doji_ratio_20,
            response_raw,
        ),
        "micro_participation_state": _derive_participation_state(
            volume_burst_ratio_20,
            tick_volume_ratio,
            real_volume_ratio,
        ),
        "micro_gap_context_state": _derive_gap_context_state(gap_fill_progress),
    }
    source = {
        "micro_body_size_pct_20": float(body_size_pct_20 or 0.0),
        "micro_doji_ratio_20": float(doji_ratio_20),
        "micro_same_color_run_current": int(same_color_run_current),
        "micro_same_color_run_max_20": int(same_color_run_max_20),
        "micro_range_compression_ratio_20": float(range_compression_ratio_20),
        "micro_volume_burst_ratio_20": float(volume_burst_ratio_20),
        "micro_volume_burst_decay_20": float(volume_burst_decay_20),
        "micro_gap_fill_progress": None if gap_fill_progress is None else float(gap_fill_progress),
    }

    label_overlay = {
        **semantic,
        **source,
        "direction": _to_text(payload.get("action")).upper(),
        "entry_setup_id": _to_text(
            payload.get("entry_setup_id")
            or payload.get("setup_id")
            or payload.get("consumer_setup_id")
        ).lower(),
        "entry_session_name": _to_text(payload.get("entry_session_name")).upper(),
        "prediction_bundle": payload.get("prediction_bundle") if isinstance(payload.get("prediction_bundle"), str) else json.dumps(payload.get("prediction_bundle", {}), ensure_ascii=False),
        "micro_upper_wick_ratio_20": float(upper_wick_ratio_20),
        "micro_lower_wick_ratio_20": float(lower_wick_ratio_20),
        "micro_swing_high_retest_count_20": int(swing_high_retest_count_20),
        "micro_swing_low_retest_count_20": int(swing_low_retest_count_20),
        "micro_bull_ratio_20": float(_to_float(state_raw.get("s_bull_ratio_20"), 0.0) or 0.0),
        "micro_bear_ratio_20": float(_to_float(state_raw.get("s_bear_ratio_20"), 0.0) or 0.0),
    }
    row_overlay = {
        "entry_atr_ratio": _to_float(payload.get("entry_atr_ratio"), None),
        "entry_atr_ratio_proxy": _to_float(payload.get("regime_volatility_ratio"), None),
    }
    return {
        "semantic": semantic,
        "source": source,
        "row_overlay": row_overlay,
        "label_overlay": label_overlay,
    }


def _merge_label_candidate_row(row: dict[str, Any], enrichment: dict[str, Any]) -> dict[str, Any]:
    merged = dict(row)
    merged.update(enrichment.get("semantic", {}))
    merged.update(enrichment.get("source", {}))
    merged.update(enrichment.get("label_overlay", {}))
    return merged


def _apply_numeric_if_missing(dataset: pd.DataFrame, index: int, column: str, value: float | int | None) -> bool:
    if value is None:
        return False
    current = _to_float(dataset.at[index, column], None)
    if current is not None and abs(current) > 1e-12:
        return False
    dataset.at[index, column] = value
    return True


def _apply_text_if_missing(dataset: pd.DataFrame, index: int, column: str, value: str) -> bool:
    if not _to_text(value):
        return False
    if _to_text(dataset.at[index, column]):
        return False
    dataset.at[index, column] = value
    return True


def build_teacher_pattern_detail_micro_backfill_plan(
    frame: pd.DataFrame | None,
    *,
    detail_paths: Iterable[str | Path] | None = None,
    detail_dir: str | Path | None = None,
    recent_limit: int = 2000,
) -> dict[str, Any]:
    dataset = normalize_trade_df(frame)
    target_rows, key_to_indices = _build_target_index(dataset, recent_limit)
    resolved_detail_paths = (
        [Path(path) for path in detail_paths]
        if detail_paths is not None
        else resolve_default_detail_paths(detail_dir or (Path.cwd() / "data" / "trades"))
    )
    matched_payloads, scanned_paths, scanned_records = _resolve_detail_matches(resolved_detail_paths, key_to_indices)

    micro_enriched_rows = 0
    teacher_labeled_rows = 0
    preview_samples: list[dict[str, Any]] = []
    for index, payload in matched_payloads.items():
        row = target_rows[index]
        enrichment = _extract_detail_enrichment(payload)
        if any((value is not None and ((isinstance(value, str) and value) or (not isinstance(value, str) and abs(float(value)) > 1e-12))) for value in enrichment["source"].values()):
            micro_enriched_rows += 1
        teacher_payload = {}
        if not _is_labeled_row(row):
            teacher_payload = build_teacher_pattern_payload_v2(_merge_label_candidate_row(row, enrichment))
            if teacher_payload:
                teacher_labeled_rows += 1
        if len(preview_samples) < 10:
            preview_samples.append(
                {
                    "row_index": int(index),
                    "ticket": str(row.get("ticket", "") or ""),
                    "symbol": str(row.get("symbol", "") or ""),
                    "matched_detail_key": _truthy_key_values(
                        payload.get("decision_row_key"),
                        payload.get("runtime_snapshot_key"),
                        payload.get("trade_link_key"),
                    )[:1],
                    "teacher_pattern_id": int(_to_int(teacher_payload.get("teacher_pattern_id"), 0) or 0),
                    "micro_body_size_pct_20": float(enrichment["source"]["micro_body_size_pct_20"]),
                    "micro_volume_burst_ratio_20": float(enrichment["source"]["micro_volume_burst_ratio_20"]),
                }
            )

    return {
        "total_rows": int(len(dataset)),
        "scoped_rows": int(len(_scoped_indices(dataset, recent_limit))),
        "target_rows": int(len(target_rows)),
        "matched_rows": int(len(matched_payloads)),
        "micro_enriched_rows": int(micro_enriched_rows),
        "teacher_labeled_rows": int(teacher_labeled_rows),
        "recent_limit": int(recent_limit),
        "detail_paths_scanned": scanned_paths,
        "detail_records_scanned": int(scanned_records),
        "preview_samples": preview_samples,
    }


def apply_teacher_pattern_detail_micro_backfill(
    frame: pd.DataFrame | None,
    *,
    detail_paths: Iterable[str | Path] | None = None,
    detail_dir: str | Path | None = None,
    recent_limit: int = 2000,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    dataset = normalize_trade_df(frame)
    target_rows, key_to_indices = _build_target_index(dataset, recent_limit)
    resolved_detail_paths = (
        [Path(path) for path in detail_paths]
        if detail_paths is not None
        else resolve_default_detail_paths(detail_dir or (Path.cwd() / "data" / "trades"))
    )
    matched_payloads, scanned_paths, scanned_records = _resolve_detail_matches(resolved_detail_paths, key_to_indices)

    micro_enriched_rows = 0
    teacher_labeled_rows = 0
    atr_enriched_rows = 0

    for index, payload in matched_payloads.items():
        row = target_rows[index]
        enrichment = _extract_detail_enrichment(payload)
        row_changed = False

        for column in MICRO_STRUCTURE_SEMANTIC_COLUMNS:
            row_changed = _apply_text_if_missing(dataset, index, column, _to_text(enrichment["semantic"].get(column))) or row_changed
        for column in MICRO_STRUCTURE_SOURCE_COLUMNS:
            row_changed = _apply_numeric_if_missing(dataset, index, column, enrichment["source"].get(column)) or row_changed

        entry_atr_ratio = enrichment["row_overlay"].get("entry_atr_ratio")
        if _is_default_like_atr_ratio(entry_atr_ratio):
            for candidate in (
                enrichment["row_overlay"].get("entry_atr_ratio_proxy"),
                row.get("regime_volatility_ratio"),
                dataset.at[index, "regime_volatility_ratio"],
            ):
                if not _is_default_like_atr_ratio(candidate):
                    entry_atr_ratio = _to_float(candidate, None)
                    break
        current_atr = _to_float(dataset.at[index, "entry_atr_ratio"], None)
        if entry_atr_ratio is not None and _is_default_like_atr_ratio(current_atr):
            dataset.at[index, "entry_atr_ratio"] = float(entry_atr_ratio)
            atr_enriched_rows += 1
            row_changed = True

        if row_changed:
            micro_enriched_rows += 1

        if not _is_labeled_row(row):
            teacher_payload = build_teacher_pattern_payload_v2(_merge_label_candidate_row(row, enrichment))
            if teacher_payload:
                for column in TEACHER_PATTERN_COLUMNS:
                    if column == "teacher_label_source":
                        dataset.at[index, column] = DETAIL_BACKFILL_LABEL_SOURCE
                    elif column == "teacher_label_review_status":
                        dataset.at[index, column] = DETAIL_BACKFILL_LABEL_REVIEW_STATUS
                    else:
                        dataset.at[index, column] = teacher_payload.get(column, dataset.at[index, column] if column in dataset.columns else "")
                teacher_labeled_rows += 1

    report = build_teacher_pattern_detail_micro_backfill_plan(
        dataset,
        detail_paths=resolved_detail_paths,
        recent_limit=recent_limit,
    )
    report.update(
        {
            "matched_rows": int(len(matched_payloads)),
            "micro_enriched_rows": int(micro_enriched_rows),
            "teacher_labeled_rows": int(teacher_labeled_rows),
            "atr_enriched_rows": int(atr_enriched_rows),
            "detail_paths_scanned": scanned_paths,
            "detail_records_scanned": int(scanned_records),
        }
    )
    return dataset, report
