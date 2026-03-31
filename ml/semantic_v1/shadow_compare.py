from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENTRY_DECISIONS_PATH = PROJECT_ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_REPLAY_SOURCE = PROJECT_ROOT / "data" / "datasets" / "replay_intermediate"
DEFAULT_PRODUCTION_COMPARE_REPLAY_SOURCE = PROJECT_ROOT / "data" / "datasets" / "replay_intermediate_compare_live"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "analysis"

SHADOW_COMPARE_REPORT_VERSION = "semantic_shadow_compare_report_v2"
SOURCE_ALIGNMENT_POLICY_VERSION = "shadow_compare_compare_source_alignment_v1"
NON_PRODUCTION_SOURCE_RULES: tuple[tuple[str, str, str], ...] = (
    ("r2_audit", "audit_test_source", "name_matches_r2_audit"),
    ("smoke", "audit_test_source", "name_matches_smoke"),
    ("tail3000", "audit_test_source", "name_matches_tail3000"),
    ("tail300", "audit_test_source", "name_matches_tail300"),
    ("legacy", "legacy_snapshot_source", "path_matches_legacy"),
)
READ_COLUMNS = {
    "time",
    "symbol",
    "action",
    "outcome",
    "blocked_by",
    "setup_id",
    "setup_side",
    "entry_stage",
    "preflight_regime",
    "decision_row_key",
    "runtime_snapshot_key",
    "trade_link_key",
    "replay_row_key",
    "semantic_shadow_available",
    "semantic_shadow_model_version",
    "semantic_shadow_trace_quality",
    "semantic_shadow_timing_probability",
    "semantic_shadow_timing_threshold",
    "semantic_shadow_timing_decision",
    "semantic_shadow_entry_quality_probability",
    "semantic_shadow_entry_quality_threshold",
    "semantic_shadow_entry_quality_decision",
    "semantic_shadow_exit_management_probability",
    "semantic_shadow_exit_management_threshold",
    "semantic_shadow_exit_management_decision",
    "semantic_shadow_should_enter",
    "semantic_shadow_action_hint",
    "semantic_shadow_compare_label",
    "semantic_shadow_reason",
}


def _coerce_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if value in ("", None):
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _path_mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()
    except OSError:
        return ""


def _has_replay_rows(path: Path) -> bool:
    if path.is_file():
        return True
    if not path.is_dir():
        return False
    return any(item.is_file() for item in path.glob("*.jsonl"))


def _resolve_default_compare_replay_source() -> Path:
    if _has_replay_rows(DEFAULT_PRODUCTION_COMPARE_REPLAY_SOURCE):
        return DEFAULT_PRODUCTION_COMPARE_REPLAY_SOURCE
    return DEFAULT_REPLAY_SOURCE
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _read_entry_decisions(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=sorted(READ_COLUMNS))
    try:
        return pd.read_csv(
            path,
            encoding="utf-8-sig",
            engine="python",
            on_bad_lines="skip",
            usecols=lambda column: column in READ_COLUMNS,
        )
    except Exception:
        try:
            return pd.read_csv(
                path,
                encoding="utf-8",
                engine="python",
                on_bad_lines="skip",
                usecols=lambda column: column in READ_COLUMNS,
            )
        except Exception:
            return pd.DataFrame(columns=sorted(READ_COLUMNS))


def _to_iso_from_series(series: pd.Series) -> str:
    if series.empty:
        return ""
    parsed = pd.to_datetime(series, errors="coerce")
    parsed = parsed.dropna()
    if parsed.empty:
        return ""
    value = parsed.iloc[0]
    try:
        return value.isoformat()
    except Exception:
        return str(value)


def _classify_replay_source_file(path: Path) -> tuple[str, str]:
    lowered = path.as_posix().lower()
    for needle, source_class, reason in NON_PRODUCTION_SOURCE_RULES:
        if needle in lowered:
            return source_class, reason
    return "production_compare_source", ""


def _source_file_record(
    path: Path,
    *,
    source_class: str,
    selection_reason: str,
) -> dict[str, Any]:
    return {
        "name": path.name,
        "path": str(path),
        "source_class": source_class,
        "selection_reason": selection_reason,
        "mtime": _path_mtime_iso(path),
    }


def _source_class_counts(records: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        key = str(record.get("source_class", "") or "").strip() or "UNKNOWN"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _resolve_replay_source_inventory(path: Path, *, explicit_source: bool) -> dict[str, Any]:
    if path.is_file():
        source_class, reason = _classify_replay_source_file(path)
        selection_reason = "explicit_file_override" if reason else "explicit_file"
        selected_record = _source_file_record(
            path,
            source_class=source_class,
            selection_reason=selection_reason,
        )
        return {
            "selection_policy_version": SOURCE_ALIGNMENT_POLICY_VERSION,
            "explicit_source": explicit_source,
            "selection_mode": selection_reason,
            "selected_paths": [path],
            "selected_files": [selected_record],
            "excluded_files": [],
            "inventory_file_count": 1,
            "selected_file_count": 1,
            "excluded_file_count": 0,
            "selected_source_class_counts": {source_class: 1},
            "excluded_source_class_counts": {},
        }

    all_files = sorted(item for item in path.glob("*.jsonl") if item.is_file())
    selected_paths: list[Path] = []
    selected_files: list[dict[str, Any]] = []
    excluded_files: list[dict[str, Any]] = []
    selection_mode = "explicit_directory_override" if explicit_source else "default_production_only"

    for file_path in all_files:
        source_class, reason = _classify_replay_source_file(file_path)
        if explicit_source:
            selection_reason = "explicit_source_override" if reason else "explicit_directory"
            selected_paths.append(file_path)
            selected_files.append(
                _source_file_record(
                    file_path,
                    source_class=source_class,
                    selection_reason=selection_reason,
                )
            )
            continue
        if source_class == "production_compare_source":
            selected_paths.append(file_path)
            selected_files.append(
                _source_file_record(
                    file_path,
                    source_class=source_class,
                    selection_reason="default_production_include",
                )
            )
        else:
            excluded_files.append(
                _source_file_record(
                    file_path,
                    source_class=source_class,
                    selection_reason=reason or "default_non_production_exclude",
                )
            )

    return {
        "selection_policy_version": SOURCE_ALIGNMENT_POLICY_VERSION,
        "explicit_source": explicit_source,
        "selection_mode": selection_mode,
        "selected_paths": selected_paths,
        "selected_files": selected_files,
        "excluded_files": excluded_files,
        "inventory_file_count": len(all_files),
        "selected_file_count": len(selected_paths),
        "excluded_file_count": len(excluded_files),
        "selected_source_class_counts": _source_class_counts(selected_files),
        "excluded_source_class_counts": _source_class_counts(excluded_files),
    }


def _extract_replay_row_time(row: Mapping[str, Any]) -> str:
    decision_row = _coerce_mapping(row.get("decision_row"))
    for value in (
        decision_row.get("time"),
        row.get("decision_time"),
        row.get("time"),
    ):
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _build_replay_coverage_summary(replay_times: list[pd.Timestamp]) -> dict[str, Any]:
    if not replay_times:
        return {
            "coverage_status": "unavailable",
            "replay_time_row_count": 0,
            "replay_first_time": "",
            "replay_last_time": "",
            "_replay_first_time": None,
            "_replay_last_time": None,
        }

    parsed = pd.Series(replay_times).dropna().sort_values()
    if parsed.empty:
        return {
            "coverage_status": "unavailable",
            "replay_time_row_count": 0,
            "replay_first_time": "",
            "replay_last_time": "",
            "_replay_first_time": None,
            "_replay_last_time": None,
        }

    first_time = parsed.iloc[0]
    last_time = parsed.iloc[-1]
    return {
        "coverage_status": "available",
        "replay_time_row_count": int(len(parsed)),
        "replay_first_time": first_time.isoformat(),
        "replay_last_time": last_time.isoformat(),
        "_replay_first_time": first_time,
        "_replay_last_time": last_time,
    }


def _align_entry_frame_to_replay_coverage(
    entry_df: pd.DataFrame,
    *,
    coverage: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(entry_df, pd.DataFrame) or entry_df.empty:
        return pd.DataFrame(columns=getattr(entry_df, "columns", [])), {
            "alignment_status": "entry_rows_unavailable",
            "alignment_reason": "entry_rows_unavailable",
            "compare_window_strategy": "replay_coverage_overlap",
            "entry_rows_before_alignment": 0,
            "entry_rows_after_alignment": 0,
            "dropped_entry_rows": 0,
            "aligned_entry_first_time": "",
            "aligned_entry_last_time": "",
        }

    first_time = coverage.get("_replay_first_time")
    last_time = coverage.get("_replay_last_time")
    if first_time is None or last_time is None:
        return entry_df.copy(), {
            "alignment_status": "coverage_unavailable_unbounded",
            "alignment_reason": "replay_coverage_unavailable",
            "compare_window_strategy": "replay_coverage_overlap",
            "entry_rows_before_alignment": int(len(entry_df)),
            "entry_rows_after_alignment": int(len(entry_df)),
            "dropped_entry_rows": 0,
            "aligned_entry_first_time": _to_iso_from_series(entry_df.get("time", pd.Series(dtype=str)).head(1)),
            "aligned_entry_last_time": _to_iso_from_series(entry_df.get("time", pd.Series(dtype=str)).tail(1)),
        }

    parsed_entry_times = pd.to_datetime(entry_df.get("time", pd.Series(dtype=str)), errors="coerce")
    valid_mask = parsed_entry_times.notna() & parsed_entry_times.ge(first_time) & parsed_entry_times.le(last_time)
    aligned = entry_df.loc[valid_mask].copy()
    alignment_status = "aligned" if not aligned.empty else "no_entry_overlap_with_replay_coverage"
    return aligned, {
        "alignment_status": alignment_status,
        "alignment_reason": "" if alignment_status == "aligned" else "entry_rows_outside_replay_coverage",
        "compare_window_strategy": "replay_coverage_overlap",
        "entry_rows_before_alignment": int(len(entry_df)),
        "entry_rows_after_alignment": int(len(aligned)),
        "dropped_entry_rows": int(len(entry_df) - len(aligned)),
        "aligned_entry_first_time": _to_iso_from_series(
            aligned.get("time", pd.Series(dtype=str)).sort_values(ascending=True).head(1)
        ),
        "aligned_entry_last_time": _to_iso_from_series(
            aligned.get("time", pd.Series(dtype=str)).sort_values(ascending=False).head(1)
        ),
    }


def _source_scope_summary(
    *,
    entry_df: pd.DataFrame,
    aligned_entry_df: pd.DataFrame,
    replay_source: Path,
    source_inventory: Mapping[str, Any],
    replay_coverage: Mapping[str, Any],
    alignment: Mapping[str, Any],
) -> dict[str, Any]:
    entry_times = entry_df.get("time", pd.Series(dtype=str))
    entry_times = entry_times.fillna("").astype(str).str.strip()
    non_empty_entry_times = entry_times[entry_times != ""]
    aligned_times = aligned_entry_df.get("time", pd.Series(dtype=str))
    aligned_times = aligned_times.fillna("").astype(str).str.strip()
    non_empty_aligned_times = aligned_times[aligned_times != ""]

    return {
        "entry_decisions_path": str(DEFAULT_ENTRY_DECISIONS_PATH),
        "replay_source_path": str(replay_source),
        "entry_rows": int(len(entry_df)),
        "entry_first_time": _to_iso_from_series(non_empty_entry_times.sort_values(ascending=True).head(1)),
        "entry_last_time": _to_iso_from_series(non_empty_entry_times.sort_values(ascending=False).head(1)),
        "aligned_entry_rows": int(alignment.get("entry_rows_after_alignment", len(aligned_entry_df)) or 0),
        "aligned_entry_first_time": str(alignment.get("aligned_entry_first_time", "") or ""),
        "aligned_entry_last_time": str(alignment.get("aligned_entry_last_time", "") or ""),
        "selection_policy_version": str(
            source_inventory.get("selection_policy_version", SOURCE_ALIGNMENT_POLICY_VERSION) or SOURCE_ALIGNMENT_POLICY_VERSION
        ),
        "selection_mode": str(source_inventory.get("selection_mode", "") or ""),
        "explicit_source": bool(source_inventory.get("explicit_source", False)),
        "inventory_file_count": int(source_inventory.get("inventory_file_count", 0) or 0),
        "selected_file_count": int(source_inventory.get("selected_file_count", 0) or 0),
        "excluded_file_count": int(source_inventory.get("excluded_file_count", 0) or 0),
        "selected_source_class_counts": dict(source_inventory.get("selected_source_class_counts", {}) or {}),
        "excluded_source_class_counts": dict(source_inventory.get("excluded_source_class_counts", {}) or {}),
        "selected_replay_files": list(source_inventory.get("selected_files", []) or [])[:12],
        "excluded_replay_files": list(source_inventory.get("excluded_files", []) or [])[:12],
        "coverage_status": str(replay_coverage.get("coverage_status", "") or ""),
        "replay_time_row_count": int(replay_coverage.get("replay_time_row_count", 0) or 0),
        "replay_first_time": str(replay_coverage.get("replay_first_time", "") or ""),
        "replay_last_time": str(replay_coverage.get("replay_last_time", "") or ""),
        "alignment_status": str(alignment.get("alignment_status", "") or ""),
        "alignment_reason": str(alignment.get("alignment_reason", "") or ""),
        "compare_window_strategy": str(alignment.get("compare_window_strategy", "") or ""),
        "dropped_entry_rows": int(alignment.get("dropped_entry_rows", 0) or 0),
    }


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = str(raw_line or "").strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, Mapping):
                yield dict(parsed)


def _resolve_replay_paths(path: Path, *, explicit_source: bool = False) -> list[Path]:
    inventory = _resolve_replay_source_inventory(path, explicit_source=explicit_source)
    return list(inventory.get("selected_paths", []) or [])


def _load_replay_label_frame_bundle(
    path: str | Path | None = None,
    *,
    explicit_source: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = Path(path) if path is not None else DEFAULT_REPLAY_SOURCE
    source_inventory = _resolve_replay_source_inventory(source, explicit_source=explicit_source)
    rows: list[dict[str, Any]] = []
    replay_times: list[pd.Timestamp] = []
    for file_path in list(source_inventory.get("selected_paths", []) or []):
        for row in _iter_jsonl(file_path):
            replay_time_text = _extract_replay_row_time(row)
            if replay_time_text:
                replay_time = pd.to_datetime(replay_time_text, errors="coerce")
                if pd.notna(replay_time):
                    replay_times.append(replay_time)
            summary = _coerce_mapping(row.get("label_quality_summary_v1"))
            transition = _coerce_mapping(summary.get("transition"))
            management = _coerce_mapping(summary.get("management"))
            replay_row_key = str(
                row.get("replay_row_key", "")
                or row.get("row_key", "")
                or summary.get("row_key", "")
                or ""
            ).strip()
            decision_row_key = str(row.get("decision_row_key", "") or replay_row_key).strip()
            join_key = replay_row_key or decision_row_key
            if not join_key:
                continue
            rows.append(
                {
                    "join_key": join_key,
                    "decision_row_key": decision_row_key,
                    "replay_row_key": replay_row_key,
                    "transition_label_status": str(
                        row.get("transition_label_status", "")
                        or summary.get("transition_label_status", "")
                        or ""
                    ),
                    "management_label_status": str(
                        row.get("management_label_status", "")
                        or summary.get("management_label_status", "")
                        or ""
                    ),
                    "label_positive_count": _to_int(
                        row.get("label_positive_count", summary.get("label_positive_count")), 0
                    ),
                    "label_negative_count": _to_int(
                        row.get("label_negative_count", summary.get("label_negative_count")), 0
                    ),
                    "label_unknown_count": _to_int(
                        row.get("label_unknown_count", summary.get("label_unknown_count")), 0
                    ),
                    "label_is_ambiguous": bool(
                        row.get("label_is_ambiguous", summary.get("label_is_ambiguous"))
                    ),
                    "label_source_descriptor": str(
                        row.get("label_source_descriptor", summary.get("label_source_descriptor", "")) or ""
                    ),
                    "is_censored": bool(row.get("is_censored", summary.get("is_censored"))),
                    "transition_positive_count": _to_int(transition.get("positive_count"), 0),
                    "transition_negative_count": _to_int(transition.get("negative_count"), 0),
                    "transition_unknown_count": _to_int(transition.get("unknown_count"), 0),
                    "management_positive_count": _to_int(management.get("positive_count"), 0),
                    "management_negative_count": _to_int(management.get("negative_count"), 0),
                    "management_unknown_count": _to_int(management.get("unknown_count"), 0),
                }
            )
    if not rows:
        return pd.DataFrame(), {
            "source_inventory": source_inventory,
            "replay_coverage": _build_replay_coverage_summary(replay_times),
        }
    frame = pd.DataFrame(rows)
    frame = frame.drop_duplicates(subset=["join_key"], keep="last")
    return frame, {
        "source_inventory": source_inventory,
        "replay_coverage": _build_replay_coverage_summary(replay_times),
    }


def _load_replay_label_frame(path: str | Path | None = None) -> pd.DataFrame:
    frame, _ = _load_replay_label_frame_bundle(path)
    return frame


def _actual_positive(row: Mapping[str, Any]) -> int | None:
    status = str(row.get("transition_label_status", "") or "").strip().upper()
    if status != "VALID":
        return None
    if bool(row.get("label_is_ambiguous")) or bool(row.get("is_censored")):
        return None
    positive = _to_int(row.get("transition_positive_count"), _to_int(row.get("label_positive_count"), 0))
    negative = _to_int(row.get("transition_negative_count"), _to_int(row.get("label_negative_count"), 0))
    if positive <= 0 and negative <= 0:
        return None
    return 1 if positive > negative else 0


def _scorable_exclusion_reason(row: Mapping[str, Any]) -> str:
    raw_status = row.get("transition_label_status", "")
    if pd.isna(raw_status):
        return "missing_replay_join"
    status = str(raw_status or "").strip().upper()
    if status == "":
        return "missing_replay_join"
    if status != "VALID":
        return "transition_status_not_valid"
    if bool(row.get("label_is_ambiguous")):
        return "label_ambiguous"
    if bool(row.get("is_censored")):
        return "is_censored"
    positive = _to_int(row.get("transition_positive_count"), _to_int(row.get("label_positive_count"), 0))
    negative = _to_int(row.get("transition_negative_count"), _to_int(row.get("label_negative_count"), 0))
    if positive <= 0 and negative <= 0:
        return "no_transition_counts"
    return "scorable"


def _value_counts(series: pd.Series, top: int = 12) -> dict[str, int]:
    if series.empty:
        return {}
    cleaned = series.fillna("").astype(str).str.strip()
    cleaned = cleaned[cleaned != ""]
    if cleaned.empty:
        return {}
    counts = cleaned.value_counts().head(top)
    return {str(key): int(value) for key, value in counts.items()}


def _value_counts_with_default(series: pd.Series, *, default_label: str, top: int = 12) -> dict[str, int]:
    if series.empty:
        return {}
    cleaned = series.fillna(default_label).astype(str).str.strip().replace("", default_label)
    counts = cleaned.value_counts().head(top)
    return {str(key): int(value) for key, value in counts.items()}


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _candidate_threshold_table(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    work = frame.copy()
    work["baseline_enter"] = work["baseline_enter"].astype(bool)
    scorable_mask = work["actual_positive"].notna()
    thresholds = (0.50, 0.55, 0.60, 0.65)
    rows: list[dict[str, Any]] = []
    entry_prob = pd.to_numeric(work.get("semantic_shadow_entry_quality_probability"), errors="coerce")
    timing_prob = pd.to_numeric(work.get("semantic_shadow_timing_probability"), errors="coerce")
    actual_positive = pd.to_numeric(work.get("actual_positive"), errors="coerce")

    for timing_threshold in thresholds:
        for entry_threshold in thresholds:
            semantic_enter = (
                (work["semantic_shadow_available"].astype(int) > 0)
                & timing_prob.ge(timing_threshold)
                & (entry_prob.ge(entry_threshold) | entry_prob.isna())
            )
            entered_count = int(semantic_enter.sum())
            true_positive = int((semantic_enter & actual_positive.eq(1)).sum())
            false_positive = int((semantic_enter & actual_positive.eq(0)).sum())
            scorable_rows = int((semantic_enter & scorable_mask).sum())
            earlier_count = int((semantic_enter & ~work["baseline_enter"]).sum())
            later_block_count = int((~semantic_enter & work["baseline_enter"]).sum())
            precision = _safe_ratio(true_positive, true_positive + false_positive)
            false_positive_rate = _safe_ratio(false_positive, scorable_rows)
            candidate_score = round(
                float(precision or 0.0)
                - (0.50 * float(false_positive_rate or 0.0))
                + (0.15 * float(_safe_ratio(earlier_count, len(work)) or 0.0))
                - (0.10 * float(_safe_ratio(later_block_count, len(work)) or 0.0)),
                6,
            )
            rows.append(
                {
                    "timing_threshold": float(timing_threshold),
                    "entry_quality_threshold": float(entry_threshold),
                    "entered_count": entered_count,
                    "scorable_rows": scorable_rows,
                    "precision": precision,
                    "false_positive_rate": false_positive_rate,
                    "earlier_count": earlier_count,
                    "later_block_count": later_block_count,
                    "candidate_score": candidate_score,
                }
            )
    return sorted(rows, key=lambda item: item["candidate_score"], reverse=True)


def _slice_summary(frame: pd.DataFrame, column: str) -> dict[str, dict[str, Any]]:
    if frame.empty or column not in frame.columns:
        return {}
    output: dict[str, dict[str, Any]] = {}
    for slice_key, group in frame.groupby(column, dropna=False):
        key = str(slice_key or "").strip() or "UNKNOWN"
        scorable_mask = group["actual_positive"].notna()
        true_positive = int((group["semantic_enter"] & group["actual_positive"].eq(1)).sum())
        false_positive = int((group["semantic_enter"] & group["actual_positive"].eq(0)).sum())
        scorable_rows = int((group["semantic_enter"] & scorable_mask).sum())
        output[key] = {
            "rows": int(len(group)),
            "baseline_entered_rows": int(group["baseline_enter"].sum()),
            "semantic_enter_rows": int(group["semantic_enter"].sum()),
            "scorable_shadow_rows": int(group["actual_positive"].notna().sum()),
            "compare_label_counts": _value_counts(group["semantic_shadow_compare_label"]),
            "trace_quality_counts": _value_counts(group["semantic_shadow_trace_quality"]),
            "scorable_exclusion_reason_counts": _value_counts(group["scorable_exclusion_reason"]),
            "precision": _safe_ratio(true_positive, true_positive + false_positive),
            "false_positive_rate": _safe_ratio(false_positive, scorable_rows),
            "earlier_count": int((group["semantic_enter"] & ~group["baseline_enter"]).sum()),
            "later_block_count": int((~group["semantic_enter"] & group["baseline_enter"]).sum()),
        }
    return output


def build_shadow_compare_report(
    entry_df: pd.DataFrame,
    *,
    replay_label_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    work = entry_df.copy() if isinstance(entry_df, pd.DataFrame) else pd.DataFrame()
    if work.empty:
        return {
            "generated_at": datetime.now().astimezone().isoformat(),
            "report_version": SHADOW_COMPARE_REPORT_VERSION,
            "summary": {"rows_total": 0},
            "candidate_threshold_table": [],
        }

    for column in READ_COLUMNS:
        if column not in work.columns:
            work[column] = ""

    work["join_key"] = (
        work["replay_row_key"].fillna("").astype(str).str.strip().replace("", pd.NA)
    ).fillna(work["decision_row_key"].fillna("").astype(str).str.strip())
    work["baseline_enter"] = work["outcome"].fillna("").astype(str).str.lower().eq("entered")
    work["semantic_shadow_available"] = pd.to_numeric(
        work["semantic_shadow_available"], errors="coerce"
    ).fillna(0).astype(int)
    work["semantic_shadow_should_enter"] = pd.to_numeric(
        work["semantic_shadow_should_enter"], errors="coerce"
    ).fillna(0).astype(int)
    work["semantic_shadow_timing_probability"] = pd.to_numeric(
        work["semantic_shadow_timing_probability"], errors="coerce"
    )
    work["semantic_shadow_entry_quality_probability"] = pd.to_numeric(
        work["semantic_shadow_entry_quality_probability"], errors="coerce"
    )
    work["semantic_shadow_trace_quality"] = (
        work["semantic_shadow_trace_quality"].fillna("").astype(str).str.strip().replace("", "unknown")
    )
    work["semantic_shadow_compare_label"] = (
        work["semantic_shadow_compare_label"].fillna("").astype(str).str.strip().replace("", "unavailable")
    )
    work["semantic_enter"] = (
        (work["semantic_shadow_available"] > 0)
        & (
            work["semantic_shadow_should_enter"] > 0
        )
    )

    replay_frame = replay_label_frame.copy() if isinstance(replay_label_frame, pd.DataFrame) else pd.DataFrame()
    if not replay_frame.empty:
        replay_frame = replay_frame.copy()
        if "join_key" not in replay_frame.columns:
            replay_frame["join_key"] = (
                replay_frame.get("replay_row_key", pd.Series(dtype=str)).fillna("").astype(str).str.strip().replace("", pd.NA)
            ).fillna(replay_frame.get("decision_row_key", pd.Series(dtype=str)).fillna("").astype(str).str.strip())
        replay_frame["actual_positive"] = replay_frame.apply(_actual_positive, axis=1)
        merge_columns = [
            "join_key",
            "transition_label_status",
            "management_label_status",
            "label_positive_count",
            "label_negative_count",
            "label_unknown_count",
            "label_is_ambiguous",
            "label_source_descriptor",
            "is_censored",
            "transition_positive_count",
            "transition_negative_count",
            "transition_unknown_count",
            "management_positive_count",
            "management_negative_count",
            "management_unknown_count",
            "actual_positive",
        ]
        replay_frame = replay_frame.reindex(columns=merge_columns).drop_duplicates(subset=["join_key"], keep="last")
        work = work.merge(replay_frame, on="join_key", how="left")
    else:
        work["actual_positive"] = pd.NA
        work["transition_label_status"] = ""
        work["management_label_status"] = ""
        work["label_positive_count"] = 0
        work["label_negative_count"] = 0
        work["label_unknown_count"] = 0
        work["label_is_ambiguous"] = False
        work["label_source_descriptor"] = ""
        work["is_censored"] = False
        work["transition_positive_count"] = 0
        work["transition_negative_count"] = 0
        work["transition_unknown_count"] = 0
        work["management_positive_count"] = 0
        work["management_negative_count"] = 0
        work["management_unknown_count"] = 0

    work["scorable_exclusion_reason"] = work.apply(_scorable_exclusion_reason, axis=1)

    shadow_rows = work[work["semantic_shadow_available"] > 0].copy()
    scorable_shadow_rows = shadow_rows[shadow_rows["actual_positive"].notna()].copy()
    true_positive = int((shadow_rows["semantic_enter"] & shadow_rows["actual_positive"].eq(1)).sum())
    false_positive = int((shadow_rows["semantic_enter"] & shadow_rows["actual_positive"].eq(0)).sum())
    missing_replay_join_rows = int((shadow_rows["scorable_exclusion_reason"] == "missing_replay_join").sum())
    matched_replay_rows = int(len(shadow_rows) - missing_replay_join_rows)

    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "report_version": SHADOW_COMPARE_REPORT_VERSION,
        "summary": {
            "rows_total": int(len(work)),
            "shadow_available_rows": int(len(shadow_rows)),
            "matched_replay_rows": matched_replay_rows,
            "missing_replay_join_rows": missing_replay_join_rows,
            "baseline_entered_rows": int(work["baseline_enter"].sum()),
            "semantic_enter_rows": int(shadow_rows["semantic_enter"].sum()),
            "scorable_shadow_rows": int(len(scorable_shadow_rows)),
            "unscorable_shadow_rows": int(len(shadow_rows) - len(scorable_shadow_rows)),
            "semantic_precision": _safe_ratio(true_positive, true_positive + false_positive),
            "semantic_false_positive_rate": _safe_ratio(false_positive, len(scorable_shadow_rows)),
            "semantic_earlier_enter_rows": int(
                (shadow_rows["semantic_shadow_compare_label"] == "semantic_earlier_enter").sum()
            ),
            "semantic_later_block_rows": int(
                (shadow_rows["semantic_shadow_compare_label"] == "semantic_later_block").sum()
            ),
        },
        "compare_label_counts": _value_counts(shadow_rows["semantic_shadow_compare_label"]),
        "trace_quality_counts": _value_counts(shadow_rows["semantic_shadow_trace_quality"]),
        "transition_label_status_counts": _value_counts_with_default(
            shadow_rows["transition_label_status"],
            default_label="UNKNOWN",
        ),
        "scorable_exclusion_reason_counts": _value_counts(shadow_rows["scorable_exclusion_reason"]),
        "by_symbol": _slice_summary(shadow_rows, "symbol"),
        "by_regime": _slice_summary(shadow_rows, "preflight_regime"),
        "by_setup": _slice_summary(shadow_rows, "setup_id"),
        "low_trace_quality": _slice_summary(
            shadow_rows[shadow_rows["semantic_shadow_trace_quality"] != "clean"],
            "semantic_shadow_trace_quality",
        ),
        "candidate_threshold_table": _candidate_threshold_table(shadow_rows)[:12],
        "recent_rows": shadow_rows.sort_values("time", ascending=False)
        .head(20)
        .reindex(
            columns=[
                "time",
                "symbol",
                "setup_id",
                "preflight_regime",
                "action",
                "outcome",
                "blocked_by",
                "semantic_shadow_compare_label",
                "semantic_shadow_trace_quality",
                "semantic_shadow_timing_probability",
                "semantic_shadow_entry_quality_probability",
                "semantic_shadow_should_enter",
                "actual_positive",
                "transition_label_status",
                "label_is_ambiguous",
                "is_censored",
                "scorable_exclusion_reason",
                "semantic_shadow_reason",
            ]
        )
        .to_dict(orient="records"),
    }
    return report


def _write_markdown(report: Mapping[str, Any], path: Path) -> None:
    summary = _coerce_mapping(report.get("summary"))
    source_scope = _coerce_mapping(report.get("source_scope"))
    lines = [
        "# Semantic Shadow Compare",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- report_version: `{report.get('report_version', '')}`",
        "",
        "## Summary",
        f"- rows_total: `{summary.get('rows_total', 0)}`",
        f"- shadow_available_rows: `{summary.get('shadow_available_rows', 0)}`",
        f"- matched_replay_rows: `{summary.get('matched_replay_rows', 0)}`",
        f"- missing_replay_join_rows: `{summary.get('missing_replay_join_rows', 0)}`",
        f"- baseline_entered_rows: `{summary.get('baseline_entered_rows', 0)}`",
        f"- semantic_enter_rows: `{summary.get('semantic_enter_rows', 0)}`",
        f"- scorable_shadow_rows: `{summary.get('scorable_shadow_rows', 0)}`",
        f"- unscorable_shadow_rows: `{summary.get('unscorable_shadow_rows', 0)}`",
        f"- semantic_earlier_enter_rows: `{summary.get('semantic_earlier_enter_rows', 0)}`",
        f"- semantic_later_block_rows: `{summary.get('semantic_later_block_rows', 0)}`",
        f"- semantic_precision: `{summary.get('semantic_precision', None)}`",
        f"- semantic_false_positive_rate: `{summary.get('semantic_false_positive_rate', None)}`",
        "",
        "## Source Scope",
        f"- entry_decisions_path: `{source_scope.get('entry_decisions_path', '')}`",
        f"- replay_source_path: `{source_scope.get('replay_source_path', '')}`",
        f"- entry_rows: `{source_scope.get('entry_rows', 0)}`",
        f"- entry_first_time: `{source_scope.get('entry_first_time', '')}`",
        f"- entry_last_time: `{source_scope.get('entry_last_time', '')}`",
        f"- aligned_entry_rows: `{source_scope.get('aligned_entry_rows', 0)}`",
        f"- aligned_entry_first_time: `{source_scope.get('aligned_entry_first_time', '')}`",
        f"- aligned_entry_last_time: `{source_scope.get('aligned_entry_last_time', '')}`",
        f"- selection_policy_version: `{source_scope.get('selection_policy_version', '')}`",
        f"- selection_mode: `{source_scope.get('selection_mode', '')}`",
        f"- explicit_source: `{source_scope.get('explicit_source', False)}`",
        f"- inventory_file_count: `{source_scope.get('inventory_file_count', 0)}`",
        f"- selected_file_count: `{source_scope.get('selected_file_count', 0)}`",
        f"- excluded_file_count: `{source_scope.get('excluded_file_count', 0)}`",
        f"- selected_source_class_counts: `{source_scope.get('selected_source_class_counts', {})}`",
        f"- excluded_source_class_counts: `{source_scope.get('excluded_source_class_counts', {})}`",
        f"- coverage_status: `{source_scope.get('coverage_status', '')}`",
        f"- replay_time_row_count: `{source_scope.get('replay_time_row_count', 0)}`",
        f"- replay_first_time: `{source_scope.get('replay_first_time', '')}`",
        f"- replay_last_time: `{source_scope.get('replay_last_time', '')}`",
        f"- alignment_status: `{source_scope.get('alignment_status', '')}`",
        f"- alignment_reason: `{source_scope.get('alignment_reason', '')}`",
        f"- compare_window_strategy: `{source_scope.get('compare_window_strategy', '')}`",
        f"- dropped_entry_rows: `{source_scope.get('dropped_entry_rows', 0)}`",
        f"- selected_replay_files: `{source_scope.get('selected_replay_files', [])}`",
        f"- excluded_replay_files: `{source_scope.get('excluded_replay_files', [])}`",
        "",
        "## Compare Labels",
    ]
    compare_counts = _coerce_mapping(report.get("compare_label_counts"))
    if compare_counts:
        for key, value in compare_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- no_rows: `0`")

    lines.extend(["", "## Scorable Exclusion Reasons"])
    exclusion_counts = _coerce_mapping(report.get("scorable_exclusion_reason_counts"))
    if exclusion_counts:
        for key, value in exclusion_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none: `0`")

    lines.extend(["", "## Transition Label Status"])
    status_counts = _coerce_mapping(report.get("transition_label_status_counts"))
    if status_counts:
        for key, value in status_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none: `0`")

    lines.extend(["", "## Top Threshold Candidates"])
    for row in list(report.get("candidate_threshold_table", []) or [])[:8]:
        lines.append(
            "- "
            f"timing>={row.get('timing_threshold')} / entry>={row.get('entry_quality_threshold')}"
            f" | score=`{row.get('candidate_score')}`"
            f" | precision=`{row.get('precision')}`"
            f" | false_positive_rate=`{row.get('false_positive_rate')}`"
            f" | earlier=`{row.get('earlier_count')}`"
            f" | later_block=`{row.get('later_block_count')}`"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_shadow_compare_report(
    *,
    entry_decisions_path: str | Path | None = None,
    replay_source: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    entry_path = Path(entry_decisions_path) if entry_decisions_path is not None else DEFAULT_ENTRY_DECISIONS_PATH
    replay_path = Path(replay_source) if replay_source is not None else _resolve_default_compare_replay_source()
    out_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    entry_df = _read_entry_decisions(entry_path)
    replay_frame, replay_bundle = _load_replay_label_frame_bundle(
        replay_path,
        explicit_source=replay_source is not None,
    )
    source_inventory = dict(replay_bundle.get("source_inventory", {}) or {})
    replay_coverage = dict(replay_bundle.get("replay_coverage", {}) or {})
    aligned_entry_df, alignment = _align_entry_frame_to_replay_coverage(
        entry_df,
        coverage=replay_coverage,
    )
    report = build_shadow_compare_report(aligned_entry_df, replay_label_frame=replay_frame)
    report["source_scope"] = _source_scope_summary(
        entry_df=entry_df,
        aligned_entry_df=aligned_entry_df,
        replay_source=replay_path,
        source_inventory=source_inventory,
        replay_coverage=replay_coverage,
        alignment=alignment,
    )
    report["source_scope"]["entry_decisions_path"] = str(entry_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"semantic_shadow_compare_report_{timestamp}.json"
    md_path = out_dir / f"semantic_shadow_compare_report_{timestamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    return {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-decisions", default=str(DEFAULT_ENTRY_DECISIONS_PATH))
    parser.add_argument("--replay-source", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    paths = write_shadow_compare_report(
        entry_decisions_path=args.entry_decisions,
        replay_source=args.replay_source,
        output_dir=args.output_dir,
    )
    print(paths["json_path"])
    print(paths["markdown_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
