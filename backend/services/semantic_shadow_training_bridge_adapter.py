"""Adapt forecast outcome bridge rows into a joinable semantic shadow training bridge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FORECAST_OUTCOME_BRIDGE_PATH = (
    PROJECT_ROOT / "data" / "analysis" / "forecast_state25" / "forecast_state25_outcome_bridge_latest.json"
)
DEFAULT_ARCHIVE_ROOT = PROJECT_ROOT / "data" / "trades" / "archive" / "entry_decisions"

SEMANTIC_SHADOW_TRAINING_BRIDGE_ADAPTER_VERSION = "semantic_shadow_training_bridge_adapter_v0"

SEMANTIC_SHADOW_TRAINING_BRIDGE_ADAPTER_COLUMNS = [
    "bridge_adapter_row_id",
    "symbol",
    "signal_bar_ts",
    "bridge_row_key",
    "bridge_normalized_key",
    "bridge_decision_time",
    "archive_source_file",
    "archive_replay_row_key",
    "archive_decision_row_key",
    "archive_time",
    "match_strategy",
    "match_status",
    "match_gap_seconds",
    "candidate_count_for_key",
    "bridge_quality_status",
    "entry_wait_quality_label",
    "learning_total_label",
    "learning_total_score",
    "loss_quality_label",
    "signed_exit_score",
    "transition_label_status",
    "management_label_status",
    "scene_family",
    "wait_bias_hint",
    "forecast_decision_hint",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _to_float(value: object, default: float | None = None) -> float | None:
    text = _to_text(value)
    if not text:
        return default
    try:
        return float(text)
    except Exception:
        return default


def _key_segment(row_key: object, segment_name: str) -> str:
    text = _to_text(row_key)
    prefix = f"{segment_name}="
    for part in text.split("|"):
        if part.startswith(prefix):
            return part[len(prefix) :]
    return ""


def _normalize_row_key(row_key: object) -> str:
    text = _to_text(row_key)
    if not text:
        return ""
    parts = [part for part in text.split("|") if part and not part.startswith("decision_time=")]
    return "|".join(parts)


def _parse_timestamp(value: object) -> pd.Timestamp:
    text = _to_text(value)
    if not text:
        return pd.NaT
    try:
        numeric = float(text)
    except Exception:
        numeric = None
    if numeric is not None:
        return pd.to_datetime(numeric, unit="s", errors="coerce")
    return pd.to_datetime(text, errors="coerce")


def _bridge_decision_time(row: dict[str, Any]) -> pd.Timestamp:
    direct = _parse_timestamp(row.get("decision_time"))
    if pd.notna(direct):
        return direct
    return _parse_timestamp(_key_segment(row.get("row_key"), "decision_time"))


def _archive_decision_time(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype="datetime64[ns]")
    parsed = pd.to_datetime(frame.get("time", pd.Series(dtype=str)), errors="coerce")
    missing = parsed.isna()
    if bool(missing.any()):
        fallback = frame.get("archive_replay_row_key", pd.Series(dtype=str)).apply(
            lambda value: _parse_timestamp(_key_segment(value, "decision_time"))
        )
        parsed = parsed.where(~missing, fallback)
    return parsed


def load_semantic_shadow_training_bridge_adapter_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame(columns=SEMANTIC_SHADOW_TRAINING_BRIDGE_ADAPTER_COLUMNS)
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _load_forecast_bridge_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def _load_archive_candidates(archive_root: Path, normalized_keys: set[str]) -> pd.DataFrame:
    if not archive_root.exists() or not normalized_keys:
        return pd.DataFrame()

    rows: list[pd.DataFrame] = []
    wanted_columns = ["replay_row_key", "decision_row_key", "time", "signal_bar_ts", "symbol"]
    for parquet_path in sorted(archive_root.rglob("*.parquet")):
        try:
            frame = pd.read_parquet(parquet_path, columns=wanted_columns)
        except Exception:
            continue
        if frame.empty or "replay_row_key" not in frame.columns:
            continue
        frame = frame.copy()
        frame["archive_replay_row_key"] = frame["replay_row_key"].fillna("").astype(str).str.strip()
        frame["bridge_normalized_key"] = frame["archive_replay_row_key"].apply(_normalize_row_key)
        frame = frame.loc[frame["bridge_normalized_key"].isin(normalized_keys)].copy()
        if frame.empty:
            continue
        frame["archive_decision_row_key"] = frame.get("decision_row_key", pd.Series(dtype=str)).fillna("").astype(str).str.strip()
        frame["archive_time"] = frame.get("time", pd.Series(dtype=str)).fillna("").astype(str).str.strip()
        frame["archive_ts"] = _archive_decision_time(frame)
        try:
            relative = parquet_path.relative_to(PROJECT_ROOT)
            frame["archive_source_file"] = str(relative)
        except ValueError:
            frame["archive_source_file"] = str(parquet_path)
        rows.append(
            frame[
                [
                    "archive_source_file",
                    "archive_replay_row_key",
                    "archive_decision_row_key",
                    "archive_time",
                    "archive_ts",
                    "bridge_normalized_key",
                ]
            ].copy()
        )

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _select_archive_match(
    *,
    bridge_row_key: str,
    bridge_normalized_key: str,
    bridge_ts: pd.Timestamp,
    archive_df: pd.DataFrame,
    max_gap_seconds: float,
) -> tuple[str, str, float | None, int, dict[str, Any]]:
    if archive_df.empty or not bridge_normalized_key:
        return ("", "unmatched", None, 0, {})

    exact_subset = archive_df.loc[
        archive_df["archive_replay_row_key"].fillna("").astype(str) == bridge_row_key
    ].copy()
    if not exact_subset.empty:
        candidate_count = int(len(exact_subset))
        if pd.notna(bridge_ts):
            valid = exact_subset.loc[exact_subset["archive_ts"].notna()].copy()
            if not valid.empty:
                valid["gap_seconds"] = (valid["archive_ts"] - bridge_ts).abs().dt.total_seconds()
                matched = valid.sort_values(["gap_seconds", "archive_time"], ascending=[True, True]).iloc[0].to_dict()
                gap = _to_float(matched.get("gap_seconds"))
                return ("exact_replay_row_key", "matched", gap, candidate_count, matched)
        matched = exact_subset.iloc[0].to_dict()
        return ("exact_replay_row_key", "matched", None, candidate_count, matched)

    normalized_subset = archive_df.loc[
        archive_df["bridge_normalized_key"].fillna("").astype(str) == bridge_normalized_key
    ].copy()
    candidate_count = int(len(normalized_subset))
    if normalized_subset.empty:
        return ("normalized_key_nearest_time", "unmatched", None, 0, {})

    if pd.isna(bridge_ts):
        matched = normalized_subset.iloc[0].to_dict()
        return ("normalized_key_nearest_time", "matched", None, candidate_count, matched)

    valid = normalized_subset.loc[normalized_subset["archive_ts"].notna()].copy()
    if valid.empty:
        return ("normalized_key_nearest_time", "unmatched", None, candidate_count, {})

    valid["gap_seconds"] = (valid["archive_ts"] - bridge_ts).abs().dt.total_seconds()
    matched = valid.sort_values(["gap_seconds", "archive_time"], ascending=[True, True]).iloc[0].to_dict()
    gap = _to_float(matched.get("gap_seconds"))
    if gap is not None and gap > float(max_gap_seconds):
        return ("normalized_key_nearest_time", "gap_exceeds_limit", gap, candidate_count, matched)
    return ("normalized_key_nearest_time", "matched", gap, candidate_count, matched)


def build_semantic_shadow_training_bridge_adapter(
    *,
    forecast_outcome_bridge_path: str | Path | None = None,
    archive_root: str | Path | None = None,
    max_gap_seconds: float = 180.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    resolved_bridge_path = (
        Path(forecast_outcome_bridge_path) if forecast_outcome_bridge_path is not None else DEFAULT_FORECAST_OUTCOME_BRIDGE_PATH
    )
    resolved_archive_root = Path(archive_root) if archive_root is not None else DEFAULT_ARCHIVE_ROOT

    bridge_rows = _load_forecast_bridge_rows(resolved_bridge_path)
    normalized_keys = {
        _normalize_row_key(row.get("row_key"))
        for row in bridge_rows
        if _normalize_row_key(row.get("row_key"))
    }
    archive_df = _load_archive_candidates(resolved_archive_root, normalized_keys)

    adapter_rows: list[dict[str, Any]] = []
    for idx, bridge_row in enumerate(bridge_rows, start=1):
        bridge_row_key = _to_text(bridge_row.get("row_key"))
        bridge_normalized_key = _normalize_row_key(bridge_row_key)
        bridge_ts = _bridge_decision_time(bridge_row)
        economic_target = bridge_row.get("economic_target_summary") if isinstance(bridge_row.get("economic_target_summary"), dict) else {}
        outcome_compact = (
            bridge_row.get("outcome_label_compact_summary_v1")
            if isinstance(bridge_row.get("outcome_label_compact_summary_v1"), dict)
            else {}
        )
        state25_hint = bridge_row.get("state25_runtime_hint_v1") if isinstance(bridge_row.get("state25_runtime_hint_v1"), dict) else {}
        forecast_runtime = (
            bridge_row.get("forecast_runtime_summary_v1")
            if isinstance(bridge_row.get("forecast_runtime_summary_v1"), dict)
            else {}
        )
        match_strategy, match_status, gap_seconds, candidate_count, matched = _select_archive_match(
            bridge_row_key=bridge_row_key,
            bridge_normalized_key=bridge_normalized_key,
            bridge_ts=bridge_ts,
            archive_df=archive_df,
            max_gap_seconds=max_gap_seconds,
        )
        adapter_rows.append(
            {
                "bridge_adapter_row_id": f"semantic_bridge::{idx:04d}",
                "symbol": _to_text(bridge_row.get("symbol")),
                "signal_bar_ts": _to_text(bridge_row.get("signal_bar_ts")),
                "bridge_row_key": bridge_row_key,
                "bridge_normalized_key": bridge_normalized_key,
                "bridge_decision_time": bridge_ts.isoformat() if pd.notna(bridge_ts) else "",
                "archive_source_file": _to_text(matched.get("archive_source_file")),
                "archive_replay_row_key": _to_text(matched.get("archive_replay_row_key")),
                "archive_decision_row_key": _to_text(matched.get("archive_decision_row_key")),
                "archive_time": _to_text(matched.get("archive_time")),
                "match_strategy": match_strategy,
                "match_status": match_status,
                "match_gap_seconds": round(float(gap_seconds), 3) if gap_seconds is not None else None,
                "candidate_count_for_key": candidate_count,
                "bridge_quality_status": _to_text(bridge_row.get("bridge_quality_status")),
                "entry_wait_quality_label": _to_text(bridge_row.get("entry_wait_quality_label")),
                "learning_total_label": _to_text(economic_target.get("learning_total_label")),
                "learning_total_score": _to_float(economic_target.get("learning_total_score")),
                "loss_quality_label": _to_text(economic_target.get("loss_quality_label")),
                "signed_exit_score": _to_float(economic_target.get("signed_exit_score")),
                "transition_label_status": _to_text(outcome_compact.get("transition_label_status")),
                "management_label_status": _to_text(outcome_compact.get("management_label_status")),
                "scene_family": _to_text(state25_hint.get("scene_family")),
                "wait_bias_hint": _to_text(state25_hint.get("wait_bias_hint")),
                "forecast_decision_hint": _to_text(forecast_runtime.get("decision_hint")),
            }
        )

    frame = pd.DataFrame(adapter_rows, columns=SEMANTIC_SHADOW_TRAINING_BRIDGE_ADAPTER_COLUMNS)
    matched_mask = frame["match_status"].fillna("").astype(str).eq("matched") if not frame.empty else pd.Series(dtype=bool)
    exact_mask = frame["match_strategy"].fillna("").astype(str).eq("exact_replay_row_key") & matched_mask if not frame.empty else pd.Series(dtype=bool)
    normalized_mask = frame["match_strategy"].fillna("").astype(str).eq("normalized_key_nearest_time") & matched_mask if not frame.empty else pd.Series(dtype=bool)
    gap_mask = frame["match_status"].fillna("").astype(str).eq("gap_exceeds_limit") if not frame.empty else pd.Series(dtype=bool)
    match_gaps = pd.to_numeric(frame.loc[matched_mask, "match_gap_seconds"], errors="coerce") if not frame.empty else pd.Series(dtype=float)

    bridge_row_count = int(len(frame))
    matched_row_count = int(matched_mask.sum()) if not frame.empty else 0
    exact_match_count = int(exact_mask.sum()) if not frame.empty else 0
    normalized_match_count = int(normalized_mask.sum()) if not frame.empty else 0
    gap_exceeds_limit_count = int(gap_mask.sum()) if not frame.empty else 0
    unmatched_row_count = max(0, bridge_row_count - matched_row_count - gap_exceeds_limit_count)
    match_rate = round(float(matched_row_count) / float(max(1, bridge_row_count)), 6)
    training_bridge_ready = matched_row_count > 0

    summary = {
        "semantic_shadow_training_bridge_adapter_version": SEMANTIC_SHADOW_TRAINING_BRIDGE_ADAPTER_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "forecast_outcome_bridge_path": str(resolved_bridge_path),
        "archive_root": str(resolved_archive_root),
        "bridge_row_count": bridge_row_count,
        "matched_row_count": matched_row_count,
        "exact_match_count": exact_match_count,
        "normalized_nearest_time_match_count": normalized_match_count,
        "gap_exceeds_limit_count": gap_exceeds_limit_count,
        "unmatched_row_count": unmatched_row_count,
        "match_rate": match_rate,
        "median_match_gap_seconds": round(float(match_gaps.median()), 3) if not match_gaps.dropna().empty else None,
        "max_match_gap_seconds": round(float(match_gaps.max()), 3) if not match_gaps.dropna().empty else None,
        "training_bridge_ready": bool(training_bridge_ready),
        "recommended_next_action": (
            "materialize_semantic_training_dataset_from_bridge" if training_bridge_ready else "inspect_bridge_join_keys_and_time_windows"
        ),
        "match_status_counts": frame["match_status"].value_counts().to_dict() if not frame.empty else {},
    }
    return frame, summary


def render_semantic_shadow_training_bridge_adapter_markdown(
    summary: dict[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Semantic Shadow Training Bridge Adapter",
        "",
        f"- version: `{summary.get('semantic_shadow_training_bridge_adapter_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- bridge_row_count: `{summary.get('bridge_row_count', 0)}`",
        f"- matched_row_count: `{summary.get('matched_row_count', 0)}`",
        f"- exact_match_count: `{summary.get('exact_match_count', 0)}`",
        f"- normalized_nearest_time_match_count: `{summary.get('normalized_nearest_time_match_count', 0)}`",
        f"- gap_exceeds_limit_count: `{summary.get('gap_exceeds_limit_count', 0)}`",
        f"- unmatched_row_count: `{summary.get('unmatched_row_count', 0)}`",
        f"- match_rate: `{summary.get('match_rate', 0.0)}`",
        f"- median_match_gap_seconds: `{summary.get('median_match_gap_seconds', '')}`",
        f"- max_match_gap_seconds: `{summary.get('max_match_gap_seconds', '')}`",
        f"- training_bridge_ready: `{summary.get('training_bridge_ready', False)}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
        "## Aggregate",
        "",
        f"- match_status_counts: `{summary.get('match_status_counts', {})}`",
        "",
        "## Sample Rows",
        "",
    ]
    if frame.empty:
        lines.append("- no training bridge adapter rows available")
        return "\n".join(lines) + "\n"

    for row in frame.head(10).to_dict(orient="records"):
        lines.extend(
            [
                f"- `{row.get('bridge_adapter_row_id', '')}` | symbol=`{row.get('symbol', '')}` | match_status=`{row.get('match_status', '')}` | match_strategy=`{row.get('match_strategy', '')}` | gap_sec=`{row.get('match_gap_seconds', '')}`",
                f"  - scene_family=`{row.get('scene_family', '')}` | wait_bias=`{row.get('wait_bias_hint', '')}` | learning_total_label=`{row.get('learning_total_label', '')}` | archive_source=`{row.get('archive_source_file', '')}`",
            ]
        )
    return "\n".join(lines) + "\n"
