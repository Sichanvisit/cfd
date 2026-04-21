"""Bridge breakout manual annotations into entry and continuation learning cases."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.services.breakout_event_replay import (
    BREAKOUT_ACTION_TARGET_ENTER_NOW,
    BREAKOUT_ACTION_TARGET_EXIT_PROTECT,
    BREAKOUT_ACTION_TARGET_WAIT_MORE,
    build_breakout_action_target_v1,
    build_breakout_manual_alignment_v1,
)
from backend.services.breakout_event_runtime import build_breakout_event_runtime_v1
from backend.services.manual_wait_teacher_annotation_schema import (
    MANUAL_WAIT_TEACHER_ANNOTATION_COLUMNS,
    normalize_manual_wait_teacher_annotation_df,
)


BREAKOUT_MANUAL_LEARNING_BRIDGE_VERSION = "breakout_manual_learning_bridge_v1"
BREAKOUT_CONTINUATION_TARGET_VERSION = "breakout_continuation_target_v1"
BREAKOUT_MANUAL_LEARNING_COLUMNS = [
    "episode_id",
    "symbol",
    "anchor_time",
    "ideal_entry_time",
    "ideal_exit_time",
    "ideal_entry_price",
    "ideal_exit_price",
    "scene_id",
    "chart_context",
    "box_regime_scope",
    "review_status",
    "annotation_source",
    "manual_wait_teacher_label",
    "match_status",
    "matched_decision_time",
    "coverage_state",
    "action_target",
    "target_source",
    "provisional_target",
    "continuation_target",
    "continuation_source",
    "continuation_confidence",
    "breakout_state",
    "breakout_direction",
    "breakout_confidence",
    "ideal_move_abs",
    "reason_summary",
    "recommended_next_step",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


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


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def load_manual_wait_teacher_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return normalize_manual_wait_teacher_annotation_df(pd.DataFrame())
    try:
        frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        frame = pd.read_csv(csv_path, low_memory=False)
    return normalize_manual_wait_teacher_annotation_df(frame)


def merge_breakout_manual_sources(
    base_manual: pd.DataFrame | None,
    supplemental_manual: pd.DataFrame | None,
) -> pd.DataFrame:
    base = normalize_manual_wait_teacher_annotation_df(base_manual if base_manual is not None else pd.DataFrame())
    supplemental = normalize_manual_wait_teacher_annotation_df(supplemental_manual if supplemental_manual is not None else pd.DataFrame())
    if base.empty:
        return supplemental
    if supplemental.empty:
        return base

    merged_rows = []
    by_episode: dict[str, dict[str, Any]] = {}
    for _, row in base.iterrows():
        payload = row.to_dict()
        by_episode[_to_text(payload.get("episode_id"), "")] = payload
    for _, row in supplemental.iterrows():
        payload = row.to_dict()
        by_episode[_to_text(payload.get("episode_id"), "")] = payload
    merged_rows.extend(by_episode.values())
    return normalize_manual_wait_teacher_annotation_df(pd.DataFrame(merged_rows))


def load_entry_decision_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        frame = pd.read_csv(csv_path, low_memory=False)
    frame["symbol"] = frame.get("symbol", "").fillna("").astype(str).str.upper().str.strip()
    frame["time_parsed"] = frame.get("time", "").apply(_parse_local_timestamp)
    return frame


def _entry_rows_by_symbol(frame: pd.DataFrame | None) -> dict[str, pd.DataFrame]:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    if dataset.empty:
        return {}
    grouped: dict[str, pd.DataFrame] = {}
    for symbol, group in dataset.groupby(dataset["symbol"].fillna("").astype(str).str.upper(), sort=False):
        symbol_key = _to_text(symbol, "").upper()
        if not symbol_key:
            continue
        grouped[symbol_key] = group.sort_values("time_parsed", kind="stable").copy()
    return grouped


def _nearest_decision_row(
    entry_by_symbol: Mapping[str, pd.DataFrame],
    *,
    symbol: str,
    anchor_time: pd.Timestamp | None,
    tolerance_sec: float,
) -> dict[str, Any] | None:
    if anchor_time is None:
        return None
    symbol_rows = entry_by_symbol.get(symbol.upper())
    if symbol_rows is None or symbol_rows.empty:
        return None
    working = symbol_rows.copy()
    working = working[working["time_parsed"].notna()].copy()
    if working.empty:
        return None
    working["time_gap_sec"] = (working["time_parsed"] - anchor_time).abs().dt.total_seconds()
    matched = working.sort_values(["time_gap_sec", "time_parsed"], kind="stable").head(1)
    if matched.empty:
        return None
    row = matched.iloc[0].to_dict()
    if _to_float(row.get("time_gap_sec"), 999999.0) > float(tolerance_sec):
        return None
    return row


def _manual_label_action_target(manual_label: str) -> tuple[str, str, bool]:
    label = _to_text(manual_label, "").lower()
    if label in {"good_wait_better_entry", "bad_wait_missed_move"}:
        return BREAKOUT_ACTION_TARGET_ENTER_NOW, "manual_label_fallback", True
    if label == "good_wait_protective_exit":
        return BREAKOUT_ACTION_TARGET_EXIT_PROTECT, "manual_label_fallback", True
    return BREAKOUT_ACTION_TARGET_WAIT_MORE, "manual_label_fallback", True


def _scene_text(manual_row: Mapping[str, Any]) -> str:
    return " ".join(
        part
        for part in (
            _to_text(manual_row.get("scene_id"), ""),
            _to_text(manual_row.get("chart_context"), ""),
            _to_text(manual_row.get("wait_outcome_reason_summary"), ""),
        )
        if part
    ).lower()


def _ideal_move_abs(manual_row: Mapping[str, Any]) -> float:
    entry_price = _to_float(manual_row.get("ideal_entry_price"), 0.0)
    exit_price = _to_float(manual_row.get("ideal_exit_price"), 0.0)
    if entry_price <= 0.0 or exit_price <= 0.0:
        return 0.0
    return round(abs(exit_price - entry_price), 6)


def _continuation_target(
    *,
    manual_row: Mapping[str, Any],
    action_target: str,
    breakout_state: str,
    matched: bool,
) -> tuple[str, str, float]:
    manual_label = _to_text(manual_row.get("manual_wait_teacher_label"), "").lower()
    scene_text = _scene_text(manual_row)
    if manual_label == "good_wait_protective_exit":
        return "CONTINUE_THEN_PROTECT", "manual_label", 0.82 if matched else 0.62
    if "pullback" in scene_text or "reclaim" in scene_text:
        return "PULLBACK_THEN_CONTINUE", "scene_inference", 0.76 if matched else 0.58
    if manual_label == "bad_wait_missed_move" or action_target == BREAKOUT_ACTION_TARGET_ENTER_NOW:
        return "CONTINUE_AFTER_BREAK", "manual_label", 0.74 if matched else 0.56
    if breakout_state == "failed_breakout":
        return "FAIL_OR_FADE", "runtime_alignment", 0.78
    return "WAIT_OR_UNCLEAR", "manual_label", 0.45


def build_breakout_manual_learning_bridge(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]] | None,
    manual_rows: Sequence[Mapping[str, Any]] | None,
    match_tolerance_sec: float = 300.0,
) -> dict[str, Any]:
    entry_frame = pd.DataFrame(list(entry_decision_rows or []))
    if not entry_frame.empty:
        entry_frame["symbol"] = entry_frame.get("symbol", "").fillna("").astype(str).str.upper().str.strip()
        entry_frame["time_parsed"] = entry_frame.get("time", "").apply(_parse_local_timestamp)
    manual_frame = normalize_manual_wait_teacher_annotation_df(pd.DataFrame(list(manual_rows or [])))
    entry_by_symbol = _entry_rows_by_symbol(entry_frame)

    rows: list[dict[str, Any]] = []
    for _, manual_row in manual_frame.iterrows():
        manual = manual_row.to_dict()
        symbol = _to_text(manual.get("symbol"), "").upper()
        anchor_time = _parse_local_timestamp(manual.get("anchor_time"))
        matched_row = _nearest_decision_row(
            entry_by_symbol,
            symbol=symbol,
            anchor_time=anchor_time,
            tolerance_sec=match_tolerance_sec,
        )

        if matched_row is not None:
            runtime = build_breakout_event_runtime_v1(matched_row)
            alignment = build_breakout_manual_alignment_v1(
                decision_row=matched_row,
                breakout_event_runtime_v1=runtime,
                manual_wait_teacher_row=manual,
            )
            action_target_row = build_breakout_action_target_v1(alignment)
            action_target = _to_text(action_target_row.get("target"), "")
            target_source = _to_text(action_target_row.get("target_source"), "")
            provisional_target = bool(action_target_row.get("provisional_target", False))
            breakout_state = _to_text(alignment.get("breakout_state"), "")
            breakout_direction = _to_text(alignment.get("breakout_direction"), "")
            breakout_confidence = _to_float(alignment.get("breakout_confidence"), 0.0)
            match_status = "matched"
            coverage_state = "runtime_aligned"
            matched_decision_time = _to_text(matched_row.get("time"), "")
            reason_summary = _to_text(alignment.get("reason_summary"), "")
            recommended_next_step = "use_in_breakout_shadow_preview"
        else:
            action_target, target_source, provisional_target = _manual_label_action_target(_to_text(manual.get("manual_wait_teacher_label"), ""))
            breakout_state = ""
            breakout_direction = ""
            breakout_confidence = 0.0
            match_status = "unmatched"
            coverage_state = "manual_only_review_case" if _to_text(manual.get("annotation_source"), "").startswith("assistant_breakout_chart") else "manual_unmatched"
            matched_decision_time = ""
            reason_summary = "manual_only_case"
            recommended_next_step = "create_runtime_overlap_or_backfill_window"

        continuation_target, continuation_source, continuation_confidence = _continuation_target(
            manual_row=manual,
            action_target=action_target,
            breakout_state=breakout_state,
            matched=matched_row is not None,
        )

        rows.append(
            {
                "episode_id": _to_text(manual.get("episode_id"), ""),
                "symbol": symbol,
                "anchor_time": _to_text(manual.get("anchor_time"), ""),
                "ideal_entry_time": _to_text(manual.get("ideal_entry_time"), ""),
                "ideal_exit_time": _to_text(manual.get("ideal_exit_time"), ""),
                "ideal_entry_price": round(_to_float(manual.get("ideal_entry_price"), 0.0), 6),
                "ideal_exit_price": round(_to_float(manual.get("ideal_exit_price"), 0.0), 6),
                "scene_id": _to_text(manual.get("scene_id"), ""),
                "chart_context": _to_text(manual.get("chart_context"), ""),
                "box_regime_scope": _to_text(manual.get("box_regime_scope"), ""),
                "review_status": _to_text(manual.get("review_status"), ""),
                "annotation_source": _to_text(manual.get("annotation_source"), ""),
                "manual_wait_teacher_label": _to_text(manual.get("manual_wait_teacher_label"), ""),
                "match_status": match_status,
                "matched_decision_time": matched_decision_time,
                "coverage_state": coverage_state,
                "action_target": action_target,
                "target_source": target_source,
                "provisional_target": bool(provisional_target),
                "continuation_target": continuation_target,
                "continuation_source": continuation_source,
                "continuation_confidence": round(float(continuation_confidence), 6),
                "breakout_state": breakout_state,
                "breakout_direction": breakout_direction,
                "breakout_confidence": round(float(breakout_confidence), 6),
                "ideal_move_abs": _ideal_move_abs(manual),
                "reason_summary": reason_summary,
                "recommended_next_step": recommended_next_step,
            }
        )

    summary = {
        "contract_version": BREAKOUT_MANUAL_LEARNING_BRIDGE_VERSION,
        "continuation_target_version": BREAKOUT_CONTINUATION_TARGET_VERSION,
        "row_count": int(len(rows)),
        "matched_count": int(sum(1 for row in rows if _to_text(row.get("match_status")) == "matched")),
        "unmatched_count": int(sum(1 for row in rows if _to_text(row.get("match_status")) != "matched")),
        "action_target_counts": {},
        "continuation_target_counts": {},
        "coverage_state_counts": {},
    }
    for row in rows:
        for key, column in (
            ("action_target_counts", "action_target"),
            ("continuation_target_counts", "continuation_target"),
            ("coverage_state_counts", "coverage_state"),
        ):
            value = _to_text(row.get(column), "")
            summary[key][value] = int(summary[key].get(value, 0)) + 1

    return {
        "summary": summary,
        "rows": rows,
    }


def render_breakout_manual_learning_bridge_markdown(report: Mapping[str, Any]) -> str:
    summary = dict(report.get("summary", {}) or {})
    rows = list(report.get("rows", []) or [])
    lines = [
        "# Breakout Manual Learning Bridge",
        "",
        f"- version: `{_to_text(summary.get('contract_version'), '')}`",
        f"- rows: `{int(summary.get('row_count', 0) or 0)}`",
        f"- matched: `{int(summary.get('matched_count', 0) or 0)}`",
        f"- unmatched: `{int(summary.get('unmatched_count', 0) or 0)}`",
        "",
    ]
    for row in rows[:12]:
        lines.extend(
            [
                f"## {_to_text(row.get('episode_id'), '')}",
                "",
                f"- symbol: `{_to_text(row.get('symbol'), '')}`",
                f"- anchor_time: `{_to_text(row.get('anchor_time'), '')}`",
                f"- action_target: `{_to_text(row.get('action_target'), '')}`",
                f"- continuation_target: `{_to_text(row.get('continuation_target'), '')}`",
                f"- coverage_state: `{_to_text(row.get('coverage_state'), '')}`",
                f"- recommended_next_step: `{_to_text(row.get('recommended_next_step'), '')}`",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def write_breakout_manual_learning_bridge(
    *,
    manual_path: str | Path | None = None,
    supplemental_manual_path: str | Path | None = None,
    entry_decision_path: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    md_output_path: str | Path | None = None,
    match_tolerance_sec: float = 300.0,
) -> dict[str, Any]:
    base_manual_path = _resolve_project_path(manual_path, Path("data/manual_annotations/manual_wait_teacher_annotations.csv"))
    supplemental_path = _resolve_project_path(supplemental_manual_path, Path("data/manual_annotations/breakout_manual_overlap_seed_review_entries.csv"))
    entry_path = _resolve_project_path(entry_decision_path, Path("data/trades/entry_decisions.csv"))
    csv_out = _resolve_project_path(csv_output_path, Path("data/analysis/breakout_event/breakout_manual_learning_bridge_latest.csv"))
    json_out = _resolve_project_path(json_output_path, Path("data/analysis/breakout_event/breakout_manual_learning_bridge_latest.json"))
    md_out = _resolve_project_path(md_output_path, Path("data/analysis/breakout_event/breakout_manual_learning_bridge_latest.md"))

    base_manual = load_manual_wait_teacher_frame(base_manual_path)
    supplemental_manual = load_manual_wait_teacher_frame(supplemental_path)
    merged_manual = merge_breakout_manual_sources(base_manual, supplemental_manual)
    entry_frame = load_entry_decision_frame(entry_path)

    report = build_breakout_manual_learning_bridge(
        entry_decision_rows=entry_frame.to_dict("records"),
        manual_rows=merged_manual.to_dict("records"),
        match_tolerance_sec=float(match_tolerance_sec),
    )
    report["summary"]["manual_path"] = str(base_manual_path)
    report["summary"]["supplemental_manual_path"] = str(supplemental_path)
    report["summary"]["entry_decision_path"] = str(entry_path)

    csv_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(report["rows"], columns=BREAKOUT_MANUAL_LEARNING_COLUMNS).to_csv(csv_out, index=False, encoding="utf-8-sig")
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_out.write_text(render_breakout_manual_learning_bridge_markdown(report), encoding="utf-8")
    return report
