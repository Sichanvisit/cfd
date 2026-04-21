"""Queue manual-truth collection windows for shadow divergence rows lacking overlap."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_VERSION = "shadow_auto_manual_overlap_queue_v0"
SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_COLUMNS = [
    "queue_id",
    "selected_sweep_profile_id",
    "symbol",
    "window_start",
    "window_end",
    "row_count",
    "unique_signal_minutes",
    "dominant_baseline_action",
    "dominant_shadow_action",
    "dominant_target_action",
    "dominant_target_label_seed",
    "suggested_manual_episode_target",
    "capture_priority",
    "collection_status",
    "collection_note",
]


def load_shadow_auto_manual_overlap_queue_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    text = _to_text(value, "").lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return bool(default)


def _top_value(series: pd.Series) -> str:
    cleaned = series.fillna("").astype(str).str.strip()
    cleaned = cleaned[cleaned.ne("")]
    if cleaned.empty:
        return ""
    return str(cleaned.value_counts().index[0])


def _suggested_label_from_target(target_action: str, shadow_action: str, baseline_action: str) -> str:
    target = _to_text(target_action, "").lower()
    shadow = _to_text(shadow_action, "").lower()
    baseline = _to_text(baseline_action, "").lower()
    if target == "exit_protect" or shadow == "exit_protect":
        return "good_wait_protective_exit"
    if target == "wait_more":
        return "good_wait_better_entry"
    if target == "enter_now" and baseline == "wait_more" and shadow == "enter_now":
        return "bad_wait_missed_move"
    return "neutral_wait_small_value"


def _suggested_episode_target(unique_signal_minutes: int, row_count: int) -> int:
    if unique_signal_minutes >= 20 or row_count >= 20:
        return 4
    if unique_signal_minutes >= 10 or row_count >= 10:
        return 3
    return 2


def _capture_priority(unique_signal_minutes: int, row_count: int) -> str:
    if unique_signal_minutes >= 20 or row_count >= 20:
        return "high"
    if unique_signal_minutes >= 10 or row_count >= 10:
        return "medium"
    return "low"


def build_shadow_auto_manual_overlap_queue(
    divergence_rows: pd.DataFrame | None,
    *,
    window_minutes: int = 30,
    limit_per_symbol: int = 4,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = divergence_rows.copy() if divergence_rows is not None else pd.DataFrame()
    if source.empty:
        empty = pd.DataFrame(columns=SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_COLUMNS)
        summary = {
            "shadow_auto_manual_overlap_queue_version": SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "queue_count": 0,
            "symbol_counts": {},
            "priority_counts": {},
        }
        return empty, summary

    working = source.copy()
    working = working[
        working.get("action_diverged_flag", pd.Series(dtype=object)).map(_to_bool)
        & ~working.get("manual_reference_found", pd.Series(dtype=object)).map(_to_bool)
    ].copy()
    if working.empty:
        empty = pd.DataFrame(columns=SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_COLUMNS)
        summary = {
            "shadow_auto_manual_overlap_queue_version": SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "queue_count": 0,
            "symbol_counts": {},
            "priority_counts": {},
        }
        return empty, summary

    working["signal_ts"] = pd.to_datetime(working["bridge_decision_time"], errors="coerce")
    working = working.dropna(subset=["signal_ts"]).copy()
    if working.empty:
        empty = pd.DataFrame(columns=SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_COLUMNS)
        summary = {
            "shadow_auto_manual_overlap_queue_version": SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "queue_count": 0,
            "symbol_counts": {},
            "priority_counts": {},
        }
        return empty, summary

    working["window_start"] = working["signal_ts"].dt.floor(f"{int(window_minutes)}min")
    working["window_end"] = working["window_start"] + pd.Timedelta(minutes=int(window_minutes))
    working["signal_minute"] = working["signal_ts"].dt.floor("min")

    rows: list[dict[str, Any]] = []
    for symbol, symbol_group in working.groupby("symbol", sort=False):
        grouped_rows: list[dict[str, Any]] = []
        for (profile_id, window_start), subset in symbol_group.groupby(
            ["selected_sweep_profile_id", "window_start"],
            sort=True,
        ):
            row_count = int(len(subset))
            unique_signal_minutes = int(subset["signal_minute"].nunique())
            dominant_baseline_action = _top_value(subset.get("baseline_action_class", pd.Series(dtype=object)))
            dominant_shadow_action = _top_value(subset.get("shadow_action_class", pd.Series(dtype=object)))
            dominant_target_action = _top_value(subset.get("effective_target_action_class", pd.Series(dtype=object)))
            dominant_target_label_seed = _suggested_label_from_target(
                dominant_target_action,
                dominant_shadow_action,
                dominant_baseline_action,
            )
            grouped_rows.append(
                {
                    "queue_id": f"shadow_manual_overlap::{symbol}::{pd.Timestamp(window_start).isoformat()}::{_to_text(profile_id, 'profile')}",
                    "selected_sweep_profile_id": _to_text(profile_id, ""),
                    "symbol": _to_text(symbol, "").upper(),
                    "window_start": pd.Timestamp(window_start).isoformat(),
                    "window_end": pd.Timestamp(subset["window_end"].iloc[0]).isoformat(),
                    "row_count": row_count,
                    "unique_signal_minutes": unique_signal_minutes,
                    "dominant_baseline_action": dominant_baseline_action,
                    "dominant_shadow_action": dominant_shadow_action,
                    "dominant_target_action": dominant_target_action,
                    "dominant_target_label_seed": dominant_target_label_seed,
                    "suggested_manual_episode_target": _suggested_episode_target(unique_signal_minutes, row_count),
                    "capture_priority": _capture_priority(unique_signal_minutes, row_count),
                    "collection_status": "pending",
                    "collection_note": "manual truth needed to reduce REQUIRE_MORE_MANUAL_TRUTH bounded gate",
                }
            )
        ranked = sorted(
            grouped_rows,
            key=lambda item: (
                {"high": 0, "medium": 1, "low": 2}.get(item["capture_priority"], 3),
                -int(item["unique_signal_minutes"]),
                -int(item["row_count"]),
                item["window_start"],
            ),
        )
        rows.extend(ranked[: int(limit_per_symbol)])

    queue = pd.DataFrame(rows)
    if not queue.empty:
        queue["priority_rank"] = queue["capture_priority"].map({"high": 0, "medium": 1, "low": 2}).fillna(3)
        queue = queue.sort_values(by=["priority_rank", "symbol", "window_start"], kind="stable").drop(columns=["priority_rank"])
    for column in SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_COLUMNS:
        if column not in queue.columns:
            queue[column] = ""
    queue = queue[SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_COLUMNS].copy()
    summary = {
        "shadow_auto_manual_overlap_queue_version": SHADOW_AUTO_MANUAL_OVERLAP_QUEUE_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "queue_count": int(len(queue)),
        "symbol_counts": queue["symbol"].value_counts(dropna=False).to_dict() if not queue.empty else {},
        "priority_counts": queue["capture_priority"].value_counts(dropna=False).to_dict() if not queue.empty else {},
        "profile_counts": queue["selected_sweep_profile_id"].value_counts(dropna=False).to_dict() if not queue.empty else {},
    }
    return queue, summary


def render_shadow_auto_manual_overlap_queue_markdown(
    summary: Mapping[str, Any],
    queue: pd.DataFrame,
) -> str:
    lines = [
        "# Shadow Manual-Truth Overlap Collection Queue",
        "",
        f"- version: `{summary.get('shadow_auto_manual_overlap_queue_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- queue_count: `{summary.get('queue_count', 0)}`",
        f"- symbol_counts: `{summary.get('symbol_counts', {})}`",
        f"- priority_counts: `{summary.get('priority_counts', {})}`",
        "",
        "## Queue",
        "",
    ]
    if queue.empty:
        lines.append("- none")
    else:
        for row in queue.to_dict(orient="records"):
            lines.extend(
                [
                    f"### {row.get('symbol', '')} :: {row.get('window_start', '')}",
                    "",
                    f"- profile: `{row.get('selected_sweep_profile_id', '')}`",
                    f"- row_count: `{row.get('row_count', 0)}`",
                    f"- unique_signal_minutes: `{row.get('unique_signal_minutes', 0)}`",
                    f"- target_action: `{row.get('dominant_target_action', '')}`",
                    f"- label_seed: `{row.get('dominant_target_label_seed', '')}`",
                    f"- priority: `{row.get('capture_priority', '')}`",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"
