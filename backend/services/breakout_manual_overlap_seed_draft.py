"""Build review-needed manual seed drafts from breakout overlap recovery windows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    manual_wait_teacher_defaults,
    normalize_manual_wait_teacher_annotation_df,
)
from backend.services.storage_compaction import resolve_entry_decision_detail_path


BREAKOUT_MANUAL_SEED_RECOVERY_TYPES = {
    "collect_new_manual_overlap",
    "upgrade_manual_overlap_quality",
}

BREAKOUT_MANUAL_SEED_ENTRY_COLUMNS = [
    "decision_row_key",
    "symbol",
    "time",
    "action",
    "outcome",
    "observe_reason",
    "core_reason",
    "blocked_by",
    "entry_wait_decision",
    "entry_wait_state",
    "consumer_check_side",
    "setup_side",
    "core_allowed_action",
    "chart_event_kind_hint",
    "micro_breakout_readiness_state",
    "forecast_state25_candidate_wait_bias_action",
    "forecast_state25_candidate_management_bias",
    "belief_candidate_recommended_family",
    "belief_candidate_supporting_label",
    "barrier_candidate_recommended_family",
    "barrier_candidate_supporting_label",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _with_kst_suffix(value: object) -> str:
    text = _to_text(value, "")
    if not text:
        return ""
    return text if text.endswith("+09:00") else f"{text}+09:00"


def _parse_local_timestamp(value: object) -> pd.Timestamp | None:
    text = _to_text(value, "")
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    stamp = pd.Timestamp(parsed)
    if stamp.tzinfo is not None:
        return stamp.tz_convert("Asia/Seoul").tz_localize(None)
    return stamp


def _count_texts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    series = frame[column].fillna("").astype(str).str.strip()
    series = series[series.ne("")]
    if series.empty:
        return {}
    return {str(key): int(value) for key, value in series.value_counts(dropna=False).to_dict().items()}


def _dominant_text(frame: pd.DataFrame, *columns: str) -> str:
    counts: dict[str, int] = {}
    for column in columns:
        for key, value in _count_texts(frame, column).items():
            counts[key] = int(counts.get(key, 0)) + int(value)
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda item: (-int(item[1]), str(item[0])))[0][0]


def _dominant_side(frame: pd.DataFrame) -> str:
    direction = _dominant_text(frame, "breakout_direction")
    if direction == "UP":
        return "BUY"
    if direction == "DOWN":
        return "SELL"

    side = _dominant_text(frame, "consumer_check_side", "setup_side")
    if side in {"BUY", "SELL"}:
        return side

    allowed = _dominant_text(frame, "core_allowed_action")
    if allowed == "BUY_ONLY":
        return "BUY"
    if allowed == "SELL_ONLY":
        return "SELL"
    return ""


def _wait_like_count(frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    wait_mask = pd.Series(False, index=frame.index)
    if "outcome" in frame.columns:
        wait_mask = wait_mask | frame["outcome"].fillna("").astype(str).str.strip().str.lower().eq("wait")
    if "entry_wait_decision" in frame.columns:
        wait_mask = wait_mask | frame["entry_wait_decision"].fillna("").astype(str).str.contains("wait|observe", case=False, regex=True)
    if "action" in frame.columns:
        wait_mask = wait_mask | frame["action"].fillna("").astype(str).str.strip().eq("")
    return int(wait_mask.sum())


def _entered_count(frame: pd.DataFrame) -> int:
    if frame.empty or "outcome" not in frame.columns:
        return 0
    return int(frame["outcome"].fillna("").astype(str).str.strip().str.lower().eq("entered").sum())


def _breakout_detected_count(frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    if "breakout_detected" in frame.columns:
        detected = frame["breakout_detected"].fillna(False).astype(bool)
        if bool(detected.any()):
            return int(detected.sum())
    if "micro_breakout_readiness_state" not in frame.columns:
        return 0
    readiness = frame["micro_breakout_readiness_state"].fillna("").astype(str).str.strip().str.upper()
    return int(
        readiness.isin(
            {
                "READY_BREAKOUT",
                "COILED_BREAKOUT",
                "BUILDING_BREAKOUT",
            }
        ).sum()
    )


def _seed_label(frame: pd.DataFrame) -> str:
    candidate_target = _dominant_text(frame, "breakout_candidate_action_target")
    management_bias = _dominant_text(frame, "forecast_state25_candidate_management_bias")
    barrier_family = _dominant_text(frame, "barrier_candidate_recommended_family")
    wait_like = _wait_like_count(frame)
    entered = _entered_count(frame)
    breakout_count = _breakout_detected_count(frame)

    if candidate_target == "EXIT_PROTECT" or "protect" in management_bias.lower() or "exit" in management_bias.lower():
        return "good_wait_protective_exit"
    if barrier_family.lower() == "relief_watch" and breakout_count > 0:
        return "good_wait_protective_exit"
    if candidate_target == "ENTER_NOW":
        if wait_like >= max(entered, 1):
            return "bad_wait_missed_move"
        return "good_wait_better_entry"
    if breakout_count > 0 and wait_like > entered:
        return "bad_wait_missed_move"
    if breakout_count > 0 and entered > 0:
        return "good_wait_better_entry"
    return "neutral_wait_small_value"


def _reason_summary(frame: pd.DataFrame, *, window_start: str, window_end: str) -> str:
    breakout_state = _dominant_text(frame, "breakout_state")
    observe_reason = _dominant_text(frame, "observe_reason")
    target = _dominant_text(frame, "breakout_candidate_action_target")
    return (
        f"assistant breakout overlap seed window={window_start}->{window_end}; "
        f"rows={int(len(frame))}; breakout_rows={_breakout_detected_count(frame)}; "
        f"wait_like_rows={_wait_like_count(frame)}; entered_rows={_entered_count(frame)}; "
        f"target={target or 'unknown'}; breakout_state={breakout_state or 'unknown'}; "
        f"observe_reason={observe_reason or 'unknown'}"
    )


def _annotation_note(frame: pd.DataFrame, *, window_start: str, window_end: str) -> str:
    wait_bias = _dominant_text(frame, "forecast_state25_candidate_wait_bias_action")
    breakout_direction = _dominant_text(frame, "breakout_direction")
    return (
        f"assistant seed for breakout manual overlap review from {window_start} -> {window_end}; "
        f"breakout_direction={breakout_direction or 'unknown'}; "
        f"wait_bias_action={wait_bias or 'unknown'}"
    )


def _chart_context(frame: pd.DataFrame) -> str:
    chart_event = _dominant_text(frame, "chart_event_kind_hint")
    if chart_event:
        return f"breakout_overlap::{chart_event.lower()}"
    breakout_state = _dominant_text(frame, "breakout_state")
    if breakout_state:
        return f"breakout_overlap::{breakout_state}"
    return "breakout_overlap::current_entry_window"


def _barrier_hint(frame: pd.DataFrame) -> str:
    target = _dominant_text(frame, "breakout_candidate_action_target")
    if target:
        return target.lower()
    barrier_family = _dominant_text(frame, "barrier_candidate_recommended_family")
    if barrier_family:
        return barrier_family.lower()
    return ""


def load_breakout_manual_overlap_queue(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def load_breakout_manual_overlap_seed_review_entries(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        frame = pd.read_csv(csv_path, low_memory=False)
    return normalize_manual_wait_teacher_annotation_df(frame)


def load_breakout_entry_decision_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame(columns=BREAKOUT_MANUAL_SEED_ENTRY_COLUMNS)
    try:
        frame = pd.read_csv(
            csv_path,
            encoding="utf-8-sig",
            low_memory=False,
            usecols=lambda column: column in BREAKOUT_MANUAL_SEED_ENTRY_COLUMNS,
        )
    except Exception:
        frame = pd.read_csv(
            csv_path,
            low_memory=False,
            usecols=lambda column: column in BREAKOUT_MANUAL_SEED_ENTRY_COLUMNS,
        )
    for column in BREAKOUT_MANUAL_SEED_ENTRY_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper().str.strip()
    frame["time_parsed"] = frame["time"].apply(_parse_local_timestamp)
    return frame


def _detail_row_key(payload: Mapping[str, Any] | None) -> str:
    mapped = dict(payload or {})
    return _to_text(mapped.get("decision_row_key", mapped.get("detail_row_key", "")), "")


def load_breakout_detail_hints(
    path: str | Path | None,
    *,
    wanted_keys: set[str] | None = None,
) -> pd.DataFrame:
    detail_path = Path(path) if path is not None else Path()
    if not detail_path.exists():
        return pd.DataFrame(columns=["decision_row_key", "breakout_detected", "breakout_state", "breakout_direction", "breakout_candidate_action_target"])

    wanted = {str(item).strip() for item in (wanted_keys or set()) if str(item).strip()}
    rows: list[dict[str, Any]] = []
    with detail_path.open("r", encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except Exception:
                continue
            payload = record.get("payload", {}) if isinstance(record, Mapping) else {}
            if not isinstance(payload, Mapping):
                continue
            decision_row_key = _detail_row_key(payload)
            if wanted and decision_row_key not in wanted:
                continue
            breakout_runtime = payload.get("breakout_event_runtime_v1", {})
            breakout_overlay = payload.get("breakout_event_overlay_candidates_v1", {})
            if not isinstance(breakout_runtime, Mapping):
                breakout_runtime = {}
            if not isinstance(breakout_overlay, Mapping):
                breakout_overlay = {}
            rows.append(
                {
                    "decision_row_key": decision_row_key,
                    "breakout_detected": bool(breakout_runtime.get("breakout_detected", False)),
                    "breakout_state": _to_text(breakout_runtime.get("breakout_state", ""), ""),
                    "breakout_direction": _to_text(breakout_runtime.get("breakout_direction", ""), ""),
                    "breakout_candidate_action_target": _to_text(breakout_overlay.get("candidate_action_target", ""), ""),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["decision_row_key", "breakout_detected", "breakout_state", "breakout_direction", "breakout_candidate_action_target"])
    return pd.DataFrame(rows).drop_duplicates(subset=["decision_row_key"], keep="last")


def _merge_review_entries(draft: pd.DataFrame, review_entries: pd.DataFrame | None) -> pd.DataFrame:
    working = draft.copy()
    if review_entries is None or review_entries.empty:
        return working

    if working.empty:
        return normalize_manual_wait_teacher_annotation_df(review_entries)

    review_lookup: dict[str, dict[str, Any]] = {}
    for _, row in review_entries.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        if episode_id:
            review_lookup[episode_id] = row.to_dict()

    override_text_columns = [
        "anchor_side",
        "scene_id",
        "chart_context",
        "box_regime_scope",
        "ideal_entry_time",
        "manual_wait_teacher_label",
        "manual_wait_teacher_confidence",
        "ideal_exit_time",
        "barrier_main_label_hint",
        "wait_outcome_reason_summary",
        "annotation_note",
        "annotation_author",
        "annotation_created_at",
        "annotation_source",
        "review_status",
        "manual_teacher_confidence",
    ]
    override_numeric_columns = [
        "anchor_price",
        "ideal_entry_price",
        "ideal_exit_price",
        "revisit_flag",
    ]

    seen_episode_ids: set[str] = set()
    for index, row in working.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        override = review_lookup.get(episode_id)
        if episode_id:
            seen_episode_ids.add(episode_id)
        if not override:
            continue
        label_override = _to_text(override.get("manual_wait_teacher_label", ""), "").lower()
        for column in override_text_columns:
            if column not in working.columns:
                continue
            override_value = _to_text(override.get(column, ""), "")
            if override_value:
                working.at[index, column] = override_value
        for column in override_numeric_columns:
            if column not in working.columns:
                continue
            value = override.get(column, None)
            try:
                if pd.isna(value):
                    continue
            except TypeError:
                pass
            if value is not None and str(value).strip() != "":
                working.at[index, column] = value
        if label_override:
            for dependent_column in (
                "manual_wait_teacher_polarity",
                "manual_wait_teacher_family",
                "manual_wait_teacher_subtype",
                "manual_wait_teacher_usage_bucket",
            ):
                if dependent_column in working.columns:
                    working.at[index, dependent_column] = ""
            for key, value in manual_wait_teacher_defaults(label_override).items():
                if key in working.columns:
                    working.at[index, key] = value

    merged_rows = [row.to_dict() for _, row in working.iterrows()]
    for episode_id, review_row in review_lookup.items():
        if episode_id in seen_episode_ids:
            continue
        merged_rows.append(dict(review_row))

    return normalize_manual_wait_teacher_annotation_df(pd.DataFrame(merged_rows))


def build_breakout_manual_overlap_seed_draft(
    queue: pd.DataFrame | None,
    *,
    entry_decisions: pd.DataFrame | None = None,
    detail_hints: pd.DataFrame | None = None,
    review_entries: pd.DataFrame | None = None,
) -> pd.DataFrame:
    queue_frame = queue.copy() if queue is not None else pd.DataFrame()
    if queue_frame.empty and (review_entries is None or review_entries.empty):
        return normalize_manual_wait_teacher_annotation_df(pd.DataFrame())

    entry_frame = entry_decisions.copy() if entry_decisions is not None else pd.DataFrame(columns=BREAKOUT_MANUAL_SEED_ENTRY_COLUMNS)
    detail_frame = detail_hints.copy() if detail_hints is not None else pd.DataFrame()
    if not entry_frame.empty and not detail_frame.empty and "decision_row_key" in entry_frame.columns and "decision_row_key" in detail_frame.columns:
        entry_frame = entry_frame.merge(detail_frame, on="decision_row_key", how="left")

    rows: list[dict[str, Any]] = []
    for _, queue_row in queue_frame.iterrows():
        recovery_type = _to_text(queue_row.get("recovery_type", ""), "")
        if recovery_type not in BREAKOUT_MANUAL_SEED_RECOVERY_TYPES:
            continue

        symbol = _to_text(queue_row.get("symbol", ""), "").upper()
        window_start = _with_kst_suffix(queue_row.get("window_start", ""))
        window_end = _with_kst_suffix(queue_row.get("window_end", ""))
        start_ts = _parse_local_timestamp(queue_row.get("window_start", ""))
        end_ts = _parse_local_timestamp(queue_row.get("window_end", ""))

        window_frame = entry_frame.copy()
        if not window_frame.empty:
            symbol_mask = window_frame["symbol"].fillna("").astype(str).str.upper().eq(symbol)
            time_mask = pd.Series(True, index=window_frame.index)
            if start_ts is not None:
                time_mask = time_mask & window_frame["time_parsed"].ge(start_ts)
            if end_ts is not None:
                time_mask = time_mask & window_frame["time_parsed"].le(end_ts)
            window_frame = window_frame[symbol_mask & time_mask].copy()

        label = _seed_label(window_frame)
        anchor_time = window_start
        if not window_frame.empty and "time_parsed" in window_frame.columns:
            earliest = window_frame["time_parsed"].dropna().sort_values()
            if not earliest.empty:
                anchor_time = _with_kst_suffix(earliest.iloc[0].isoformat(timespec="seconds"))

        queue_id = _to_text(queue_row.get("queue_id", ""), "")
        episode_id = queue_id.replace("breakout_recovery::", "breakout_manual_seed::")
        rows.append(
            {
                "annotation_id": episode_id,
                "episode_id": episode_id,
                "symbol": symbol,
                "timeframe": "M1",
                "anchor_side": _dominant_side(window_frame),
                "scene_id": _dominant_text(window_frame, "observe_reason", "core_reason"),
                "chart_context": _chart_context(window_frame),
                "box_regime_scope": "breakout_manual_overlap_window",
                "anchor_time": anchor_time,
                "anchor_price": 0.0,
                "ideal_entry_time": "",
                "ideal_entry_price": 0.0,
                "manual_wait_teacher_label": label,
                "manual_wait_teacher_confidence": "low",
                "ideal_exit_time": "",
                "ideal_exit_price": 0.0,
                "barrier_main_label_hint": _barrier_hint(window_frame),
                "wait_outcome_reason_summary": _reason_summary(window_frame, window_start=window_start, window_end=window_end),
                "annotation_note": _annotation_note(window_frame, window_start=window_start, window_end=window_end),
                "annotation_author": "codex",
                "annotation_created_at": "",
                "annotation_source": "assistant_breakout_overlap_seed",
                "review_status": "needs_manual_recheck",
                "revisit_flag": 1,
                "manual_teacher_confidence": "low",
            }
        )

    draft = normalize_manual_wait_teacher_annotation_df(pd.DataFrame(rows))
    return _merge_review_entries(draft, review_entries)


def build_breakout_manual_overlap_seed_inputs(
    *,
    queue_path: str | Path,
    entry_decision_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    queue = load_breakout_manual_overlap_queue(queue_path)
    entry_frame = load_breakout_entry_decision_frame(entry_decision_path)
    if queue.empty or entry_frame.empty:
        return queue, entry_frame, pd.DataFrame()

    relevant_queue = queue[queue["recovery_type"].fillna("").isin(sorted(BREAKOUT_MANUAL_SEED_RECOVERY_TYPES))].copy()
    if relevant_queue.empty:
        return queue, entry_frame, pd.DataFrame()

    wanted_keys: set[str] = set()
    for _, queue_row in relevant_queue.iterrows():
        symbol = _to_text(queue_row.get("symbol", ""), "").upper()
        start_ts = _parse_local_timestamp(queue_row.get("window_start", ""))
        end_ts = _parse_local_timestamp(queue_row.get("window_end", ""))
        symbol_mask = entry_frame["symbol"].fillna("").astype(str).str.upper().eq(symbol)
        time_mask = pd.Series(True, index=entry_frame.index)
        if start_ts is not None:
            time_mask = time_mask & entry_frame["time_parsed"].ge(start_ts)
        if end_ts is not None:
            time_mask = time_mask & entry_frame["time_parsed"].le(end_ts)
        window = entry_frame[symbol_mask & time_mask]
        if "decision_row_key" in window.columns:
            wanted_keys.update({_to_text(item, "") for item in window["decision_row_key"].tolist() if _to_text(item, "")})

    detail_path = resolve_entry_decision_detail_path(Path(entry_decision_path))
    detail_hints = load_breakout_detail_hints(detail_path, wanted_keys=wanted_keys)
    return queue, entry_frame, detail_hints
