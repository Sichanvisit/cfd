"""Store baseline-vs-shadow comparison rows from current decision logs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_BASELINE_COMPARE_VERSION = "shadow_auto_baseline_compare_v0"

SHADOW_AUTO_BASELINE_COMPARE_COLUMNS = [
    "comparison_row_id",
    "timestamp",
    "symbol",
    "decision_source_file",
    "decision_source_kind",
    "baseline_mode",
    "shadow_mode",
    "baseline_action",
    "shadow_action",
    "baseline_wait_family",
    "shadow_wait_family",
    "baseline_barrier_label",
    "shadow_barrier_label",
    "baseline_pnl",
    "shadow_pnl",
    "pnl_diff",
    "pnl_source",
    "manual_label",
    "manual_family",
    "baseline_match",
    "shadow_match",
    "match_improvement",
    "manual_episode_id",
    "manual_gap_minutes",
    "shadow_candidate_id",
    "patch_version",
    "semantic_shadow_available",
    "semantic_shadow_compare_label",
    "semantic_shadow_activation_state",
    "shadow_reason",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else default


def _to_bool(value: object, default: bool = False) -> bool:
    text = _to_text(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return bool(default)


def load_shadow_auto_compare_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def load_entry_decision_history(
    root_or_file: str | Path,
    *,
    include_legacy: bool = True,
) -> pd.DataFrame:
    path = Path(root_or_file)
    files: list[Path] = []
    if path.is_dir():
        files.append(path / "entry_decisions.csv")
        if include_legacy:
            files.extend(sorted(path.glob("entry_decisions.legacy_*.csv")))
    else:
        files.append(path)

    frames: list[pd.DataFrame] = []
    for csv_path in files:
        if not csv_path.exists():
            continue
        try:
            frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
        except Exception:
            try:
                frame = pd.read_csv(csv_path, low_memory=False)
            except Exception:
                continue
        frame = frame.copy()
        frame["decision_source_file"] = csv_path.name
        frame["decision_source_kind"] = "legacy" if ".legacy_" in csv_path.name else "current"
        frames.append(frame)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True, sort=False)
    dedup_subset = [col for col in ["time", "symbol", "action", "outcome", "entry_wait_decision", "semantic_shadow_compare_label", "decision_row_key"] if col in combined.columns]
    if dedup_subset:
        combined = combined.drop_duplicates(subset=dedup_subset, keep="last").reset_index(drop=True)
    return combined


def _parse_kst_timestamp(value: object) -> pd.Timestamp:
    text = _to_text(value)
    if not text:
        return pd.NaT
    ts = pd.to_datetime(text, errors="coerce")
    if pd.isna(ts):
        return pd.NaT
    if ts.tzinfo is None:
        try:
            return ts.tz_localize("Asia/Seoul")
        except (TypeError, ValueError):
            return pd.NaT
    return ts.tz_convert("Asia/Seoul")


def _baseline_action(row: pd.Series) -> str:
    action = _to_text(row.get("action")).upper()
    if action:
        return action
    outcome = _to_text(row.get("outcome")).lower()
    entry_wait_decision = _to_text(row.get("entry_wait_decision"))
    if outcome in {"wait", "skipped", "skip"} or entry_wait_decision:
        return "WAIT"
    return "UNKNOWN"


def _shadow_action(row: pd.Series, baseline_action: str) -> str:
    action = _to_text(row.get("core_resolved_shadow_action")).upper()
    if action:
        return action
    action = _to_text(row.get("semantic_shadow_action_hint")).upper()
    if action:
        return action
    if _to_bool(row.get("semantic_shadow_should_enter")):
        if baseline_action in {"BUY", "SELL"}:
            return baseline_action
        return "ENTER"
    if _to_text(row.get("semantic_shadow_compare_label")).lower() == "semantic_later_block":
        return "WAIT"
    if _to_bool(row.get("semantic_shadow_available")):
        return "WAIT"
    return "UNAVAILABLE"


def _shadow_wait_family(row: pd.Series, shadow_action: str) -> str:
    label = _to_text(row.get("semantic_shadow_compare_label")).lower()
    mapping = {
        "semantic_earlier_enter": "enter_earlier",
        "semantic_later_block": "wait_later_block",
        "agree_enter": "enter_agree",
        "unavailable": "unavailable",
    }
    if label in mapping:
        return mapping[label]
    if shadow_action == "WAIT":
        return "shadow_wait"
    if shadow_action in {"BUY", "SELL", "ENTER"}:
        return "shadow_enter"
    return "unknown"


def _match_improvement(baseline_match: str, shadow_match: str) -> str:
    if shadow_match == "potential_improvement" and baseline_match in {"mismatch", "unknown", "freeze"}:
        return "improved"
    if shadow_match in {"likely_worse", "risk_of_overtrade"}:
        return "regression"
    if shadow_match in {"no_change", "likely_repeat_wait"}:
        return "no_material_change"
    return "unknown"


def _shadow_match(
    *,
    manual_family: str,
    baseline_match: str,
    semantic_shadow_available: bool,
    shadow_action: str,
    semantic_shadow_compare_label: str,
) -> str:
    family = manual_family.lower().strip()
    compare_label = semantic_shadow_compare_label.lower().strip()
    baseline = baseline_match.lower().strip()
    if not family:
        return "unknown"
    if not semantic_shadow_available:
        return "unavailable"
    if family == "failed_wait":
        if shadow_action in {"BUY", "SELL", "ENTER"} or compare_label in {"semantic_earlier_enter", "agree_enter"}:
            return "potential_improvement"
        if shadow_action == "WAIT" or compare_label == "semantic_later_block":
            return "likely_repeat_wait"
    if family in {"timing_improvement", "protective_exit", "reversal_escape"}:
        if compare_label == "semantic_later_block":
            return "potential_improvement"
        if compare_label == "semantic_earlier_enter":
            return "likely_worse"
        if compare_label == "agree_enter":
            return "no_change" if baseline == "match" else "potential_improvement"
        if shadow_action == "WAIT" and baseline == "mismatch":
            return "potential_improvement"
    if family == "neutral_wait":
        if shadow_action == "WAIT":
            return "no_change"
        return "risk_of_overtrade"
    return "unknown"


@dataclass(frozen=True)
class _ManualReference:
    episode_id: str
    timestamp: pd.Timestamp
    manual_label: str
    manual_family: str
    baseline_match: str


def _build_manual_reference_map(comparison: pd.DataFrame) -> dict[str, list[_ManualReference]]:
    if comparison is None or comparison.empty:
        return {}
    prepared = comparison.copy()
    prepared["anchor_ts"] = prepared.get("anchor_time", pd.Series(dtype=str)).apply(_parse_kst_timestamp)
    prepared = prepared[prepared["anchor_ts"].notna()].copy()
    result: dict[str, list[_ManualReference]] = {}
    for row in prepared.to_dict(orient="records"):
        symbol = _to_text(row.get("symbol"))
        if not symbol:
            continue
        result.setdefault(symbol, []).append(
            _ManualReference(
                episode_id=_to_text(row.get("episode_id")),
                timestamp=row["anchor_ts"],
                manual_label=_to_text(row.get("manual_wait_teacher_label")),
                manual_family=_to_text(row.get("manual_wait_teacher_family")),
                baseline_match=_to_text(row.get("overall_alignment_grade"), "unknown"),
            )
        )
    for items in result.values():
        items.sort(key=lambda item: item.timestamp.value)
    return result


def _nearest_manual_reference(
    *,
    symbol: str,
    timestamp: pd.Timestamp,
    reference_map: dict[str, list[_ManualReference]],
    threshold_minutes: float,
) -> tuple[_ManualReference | None, float | None]:
    candidates = reference_map.get(symbol, [])
    if not candidates or pd.isna(timestamp):
        return None, None
    best_ref: _ManualReference | None = None
    best_gap: float | None = None
    for candidate in candidates:
        gap_min = abs((timestamp - candidate.timestamp).total_seconds()) / 60.0
        if best_gap is None or gap_min < best_gap:
            best_ref = candidate
            best_gap = gap_min
    if best_gap is None or best_gap > float(threshold_minutes):
        return None, None
    return best_ref, round(float(best_gap), 3)


def _select_shadow_candidate(
    *,
    manual_family: str,
    candidates: list[dict[str, Any]],
    allow_freeze_monitor: bool = True,
) -> tuple[str, str]:
    family = manual_family.strip().lower()
    if not family:
        return "", ""
    for row in candidates:
        if _to_text(row.get("manual_wait_teacher_family")).strip().lower() == family and _to_text(row.get("bridge_status")) != "freeze_track_only":
            return _to_text(row.get("shadow_candidate_id")), _to_text(row.get("patch_version"))
    if allow_freeze_monitor:
        for row in candidates:
            if _to_text(row.get("manual_wait_teacher_family")).strip().lower() != family:
                continue
            if _to_text(row.get("candidate_kind")) != "freeze_monitor":
                continue
            return _to_text(row.get("shadow_candidate_id")), _to_text(row.get("patch_version"))
    return "", ""


def build_shadow_auto_baseline_compare(
    entry_decisions: pd.DataFrame,
    *,
    comparison: pd.DataFrame | None = None,
    shadow_candidates: pd.DataFrame | None = None,
    max_rows: int = 500,
    manual_match_threshold_minutes: float = 120.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    entry_df = entry_decisions.copy() if entry_decisions is not None else pd.DataFrame()
    comparison_df = comparison.copy() if comparison is not None else pd.DataFrame()
    candidates_df = shadow_candidates.copy() if shadow_candidates is not None else pd.DataFrame()

    if entry_df.empty:
        empty = pd.DataFrame(columns=SHADOW_AUTO_BASELINE_COMPARE_COLUMNS)
        summary = {
            "shadow_auto_baseline_compare_version": SHADOW_AUTO_BASELINE_COMPARE_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "shadow_available_rows": 0,
            "manual_reference_rows": 0,
            "match_improvement_counts": {},
            "shadow_activation_state_counts": {},
            "pnl_source": "pending_shadow_execution",
        }
        return empty, summary

    working = entry_df.copy()
    if int(max_rows) > 0:
        working = working.tail(int(max_rows))
    working["timestamp_kst"] = working.get("time", pd.Series(dtype=str)).apply(_parse_kst_timestamp)
    reference_map = _build_manual_reference_map(comparison_df)
    candidate_rows = candidates_df.to_dict(orient="records") if not candidates_df.empty else []

    rows: list[dict[str, Any]] = []
    for row in working.to_dict(orient="records"):
        series = pd.Series(row)
        symbol = _to_text(row.get("symbol"))
        timestamp = row.get("timestamp_kst", pd.NaT)
        baseline_action = _baseline_action(series)
        shadow_action = _shadow_action(series, baseline_action)
        manual_ref, gap_minutes = _nearest_manual_reference(
            symbol=symbol,
            timestamp=timestamp,
            reference_map=reference_map,
            threshold_minutes=manual_match_threshold_minutes,
        )
        manual_label = manual_ref.manual_label if manual_ref else ""
        manual_family = manual_ref.manual_family if manual_ref else ""
        baseline_match = manual_ref.baseline_match if manual_ref else "unknown"
        semantic_shadow_available = _to_bool(row.get("semantic_shadow_available"))
        semantic_shadow_compare_label = _to_text(row.get("semantic_shadow_compare_label"), "unavailable")
        shadow_match = _shadow_match(
            manual_family=manual_family,
            baseline_match=baseline_match,
            semantic_shadow_available=semantic_shadow_available,
            shadow_action=shadow_action,
            semantic_shadow_compare_label=semantic_shadow_compare_label,
        )
        shadow_candidate_id, patch_version = _select_shadow_candidate(
            manual_family=manual_family,
            candidates=candidate_rows,
        )
        timestamp_text = ""
        if not pd.isna(timestamp):
            timestamp_text = timestamp.isoformat()
        baseline_wait_family = _to_text(row.get("entry_wait_decision"))
        rows.append(
            {
                "comparison_row_id": f"shadow_vs_baseline::{symbol}::{timestamp_text or _to_text(row.get('time'))}",
                "timestamp": timestamp_text or _to_text(row.get("time")),
                "symbol": symbol,
                "decision_source_file": _to_text(row.get("decision_source_file")),
                "decision_source_kind": _to_text(row.get("decision_source_kind")),
                "baseline_mode": "baseline",
                "shadow_mode": "shadow_auto",
                "baseline_action": baseline_action,
                "shadow_action": shadow_action,
                "baseline_wait_family": baseline_wait_family,
                "shadow_wait_family": _shadow_wait_family(series, shadow_action),
                "baseline_barrier_label": _to_text(row.get("barrier_action_hint_label"), baseline_wait_family or _to_text(row.get("outcome"))),
                "shadow_barrier_label": semantic_shadow_compare_label,
                "baseline_pnl": None,
                "shadow_pnl": None,
                "pnl_diff": None,
                "pnl_source": "pending_shadow_execution",
                "manual_label": manual_label,
                "manual_family": manual_family,
                "baseline_match": baseline_match,
                "shadow_match": shadow_match,
                "match_improvement": _match_improvement(baseline_match, shadow_match),
                "manual_episode_id": manual_ref.episode_id if manual_ref else "",
                "manual_gap_minutes": gap_minutes,
                "shadow_candidate_id": shadow_candidate_id,
                "patch_version": patch_version,
                "semantic_shadow_available": semantic_shadow_available,
                "semantic_shadow_compare_label": semantic_shadow_compare_label,
                "semantic_shadow_activation_state": _to_text(row.get("semantic_shadow_activation_state")),
                "shadow_reason": _to_text(row.get("semantic_shadow_reason")),
            }
        )

    compare_df = pd.DataFrame(rows, columns=SHADOW_AUTO_BASELINE_COMPARE_COLUMNS)
    summary = {
        "shadow_auto_baseline_compare_version": SHADOW_AUTO_BASELINE_COMPARE_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(compare_df)),
        "shadow_available_rows": int(compare_df["semantic_shadow_available"].fillna(False).astype(bool).sum()) if not compare_df.empty else 0,
        "manual_reference_rows": int(compare_df["manual_label"].fillna("").astype(str).ne("").sum()) if not compare_df.empty else 0,
        "match_improvement_counts": compare_df["match_improvement"].fillna("unknown").value_counts().to_dict() if not compare_df.empty else {},
        "decision_source_kind_counts": compare_df["decision_source_kind"].fillna("").astype(str).replace({"": "unknown"}).value_counts().to_dict()
        if not compare_df.empty
        else {},
        "shadow_activation_state_counts": compare_df["semantic_shadow_activation_state"].fillna("").astype(str).replace({"": "none"}).value_counts().to_dict()
        if not compare_df.empty
        else {},
        "pnl_source": "pending_shadow_execution",
    }
    return compare_df, summary


def render_shadow_auto_baseline_compare_markdown(summary: dict[str, Any], compare_df: pd.DataFrame) -> str:
    lines = [
        "# Shadow Vs Baseline",
        "",
        f"- version: `{summary.get('shadow_auto_baseline_compare_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- shadow_available_rows: `{summary.get('shadow_available_rows', 0)}`",
        f"- manual_reference_rows: `{summary.get('manual_reference_rows', 0)}`",
        f"- pnl_source: `{summary.get('pnl_source', '')}`",
        "",
        "## Aggregate",
        "",
        f"- match_improvement_counts: `{summary.get('match_improvement_counts', {})}`",
        f"- decision_source_kind_counts: `{summary.get('decision_source_kind_counts', {})}`",
        f"- shadow_activation_state_counts: `{summary.get('shadow_activation_state_counts', {})}`",
        "",
        "## Sample Rows",
        "",
    ]
    if compare_df.empty:
        lines.append("- no shadow-vs-baseline rows available")
        return "\n".join(lines) + "\n"

    for row in compare_df.head(5).to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('symbol', '')} @ {row.get('timestamp', '')}",
                "",
                f"- decision_source: `{row.get('decision_source_kind', '')}:{row.get('decision_source_file', '')}`",
                f"- baseline_action: `{row.get('baseline_action', '')}`",
                f"- shadow_action: `{row.get('shadow_action', '')}`",
                f"- manual_label: `{row.get('manual_label', '')}`",
                f"- baseline_match: `{row.get('baseline_match', '')}`",
                f"- shadow_match: `{row.get('shadow_match', '')}`",
                f"- match_improvement: `{row.get('match_improvement', '')}`",
                f"- shadow_candidate_id: `{row.get('shadow_candidate_id', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
