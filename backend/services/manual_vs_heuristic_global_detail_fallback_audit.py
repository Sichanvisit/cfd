"""Audit recoverability from any entry_decisions detail JSONL, not just paired legacy files."""

from __future__ import annotations

import csv
import json
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.manual_vs_heuristic_detail_fallback_audit import (
    _detail_anchor_timestamp,
    _is_structured_present,
    _parse_local_timestamp,
    _recoverability_grade,
    _to_text,
)


GLOBAL_DETAIL_FALLBACK_AUDIT_COLUMNS = [
    "episode_id",
    "symbol",
    "anchor_time",
    "manual_wait_teacher_label",
    "heuristic_source_file",
    "global_detail_source_file",
    "global_detail_source_kind",
    "global_detail_row_found",
    "global_detail_match_gap_minutes",
    "global_detail_decision_row_key",
    "global_detail_core_reason",
    "global_detail_observe_reason",
    "global_detail_blocked_by",
    "global_detail_entry_wait_decision",
    "global_detail_entry_enter_value",
    "global_detail_entry_wait_value",
    "global_detail_barrier_state_present",
    "global_detail_belief_state_present",
    "global_detail_forecast_assist_present",
    "global_detail_forecast_policy_present",
    "global_detail_observe_confirm_present",
    "global_detail_recoverability_grade",
    "global_detail_recoverability_reason",
]


def load_matched_cases(path: str | Path) -> list[dict[str, Any]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _detail_kind_from_name(name: str) -> str:
    if ".detail.rotate_" in name:
        return "rotate_detail"
    return "current" if name == "entry_decisions.detail.jsonl" else "legacy"


def discover_detail_paths(trades_dir: str | Path) -> list[Path]:
    root = Path(trades_dir)
    if not root.exists():
        return []
    candidates = list(root.glob("entry_decisions*.detail.jsonl"))
    candidates.extend(root.glob("entry_decisions.detail.rotate_*.jsonl"))
    unique: dict[str, Path] = {}
    for path in candidates:
        unique[str(path.resolve())] = path
    return sorted(unique.values(), key=lambda item: item.name)


def _filter_detail_paths_by_archive_scan(
    detail_paths: list[Path],
    matched_cases: list[dict[str, Any]],
    *,
    archive_scan_path: str | Path | None = None,
    max_gap_minutes: int = 180,
) -> list[Path]:
    if not archive_scan_path:
        return detail_paths
    scan_path = Path(archive_scan_path)
    if not scan_path.exists():
        return detail_paths
    try:
        scan = pd.read_csv(scan_path)
    except Exception:
        return detail_paths
    if scan.empty or "archive_file" not in scan.columns:
        return detail_paths
    anchors = [
        _parse_local_timestamp(case.get("anchor_time", ""))
        for case in matched_cases
    ]
    anchors = [stamp for stamp in anchors if stamp is not None]
    if not anchors:
        return detail_paths
    start = min(anchors) - pd.Timedelta(minutes=max_gap_minutes)
    end = max(anchors) + pd.Timedelta(minutes=max_gap_minutes)
    scan = scan[scan["archive_format"].fillna("").eq("detail_jsonl")].copy()
    if "signal_bar_min" not in scan.columns or "signal_bar_max" not in scan.columns:
        return detail_paths
    scan["signal_bar_min"] = pd.to_datetime(scan["signal_bar_min"], errors="coerce")
    scan["signal_bar_max"] = pd.to_datetime(scan["signal_bar_max"], errors="coerce")
    scan = scan[
        scan["signal_bar_min"].notna()
        & scan["signal_bar_max"].notna()
        & (scan["signal_bar_max"] >= start)
        & (scan["signal_bar_min"] <= end)
    ].copy()
    if scan.empty:
        return detail_paths
    allowed = set(scan["archive_file"].astype(str))
    return [path for path in detail_paths if path.name in allowed]


def _build_global_detail_index(
    detail_paths: list[Path],
    *,
    allowed_symbols: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for detail_path in detail_paths:
        with detail_path.open("r", encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                payload = obj.get("payload", {}) if isinstance(obj, dict) else {}
                symbol = _to_text(payload.get("symbol", ""), "").upper()
                if not symbol:
                    continue
                if allowed_symbols and symbol not in allowed_symbols:
                    continue
                anchor_time = _detail_anchor_timestamp(payload)
                if anchor_time is None:
                    continue
                grouped[symbol].append(
                    {
                        "time": anchor_time,
                        "payload": payload,
                        "detail_source_file": detail_path.name,
                        "detail_source_kind": _detail_kind_from_name(detail_path.name),
                    }
                )
    index: dict[str, dict[str, Any]] = {}
    for symbol, records in grouped.items():
        ordered = sorted(
            records,
            key=lambda item: (
                pd.Timestamp(item["time"]).value,
                item["detail_source_kind"] != "current",
                item["detail_source_file"],
            ),
        )
        index[symbol] = {
            "times": [pd.Timestamp(item["time"]).value for item in ordered],
            "rows": ordered,
        }
    return index


def _nearest_global_detail_payload(
    index: dict[str, dict[str, Any]],
    *,
    symbol: str,
    anchor_time: object,
    preferred_source_file: str = "",
    max_gap_minutes: int = 180,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    stamp = _parse_local_timestamp(anchor_time)
    if stamp is None:
        return None, {"reason": "manual_anchor_missing"}
    bucket = index.get(_to_text(symbol, "").upper())
    if not bucket:
        return None, {"reason": "detail_symbol_missing"}
    times = bucket.get("times", []) or []
    rows = bucket.get("rows", []) or []
    if not times:
        return None, {"reason": "detail_symbol_empty"}
    target = pd.Timestamp(stamp).value
    pos = bisect_left(times, target)
    candidates: list[tuple[float, int]] = []
    for idx in range(max(0, pos - 3), min(len(times), pos + 3)):
        gap_minutes = abs(times[idx] - target) / 60_000_000_000
        candidates.append((gap_minutes, idx))
    if not candidates:
        return None, {"reason": "detail_time_missing"}
    preferred = _to_text(preferred_source_file, "")

    def _rank(item: tuple[float, int]) -> tuple[float, int, str]:
        gap_minutes, idx = item
        row = rows[idx]
        source_match_penalty = 0 if preferred and row.get("detail_source_file", "") == preferred else 1
        return (
            gap_minutes,
            source_match_penalty,
            _to_text(row.get("detail_source_file", ""), ""),
        )

    gap_minutes, best_idx = min(candidates, key=_rank)
    if gap_minutes > float(max_gap_minutes):
        return None, {"reason": "detail_gap_exceeds_limit", "gap_minutes": round(gap_minutes, 3)}
    row = rows[best_idx]
    return row["payload"], {
        "reason": "matched",
        "gap_minutes": round(gap_minutes, 3),
        "detail_source_file": row.get("detail_source_file", ""),
        "detail_source_kind": row.get("detail_source_kind", ""),
    }


def build_manual_vs_heuristic_global_detail_fallback_audit(
    matched_cases: list[dict[str, Any]],
    *,
    trades_dir: str | Path,
    archive_scan_path: str | Path | None = None,
    max_gap_minutes: int = 180,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not matched_cases:
        empty = pd.DataFrame(columns=GLOBAL_DETAIL_FALLBACK_AUDIT_COLUMNS)
        return empty, {
            "matched_case_count": 0,
            "global_detail_row_found_count": 0,
            "recoverability_grade_counts": {},
        }

    detail_paths = discover_detail_paths(trades_dir)
    detail_paths = _filter_detail_paths_by_archive_scan(
        detail_paths,
        matched_cases,
        archive_scan_path=archive_scan_path,
        max_gap_minutes=max_gap_minutes,
    )
    allowed_symbols = {_to_text(case.get("symbol", ""), "").upper() for case in matched_cases}
    detail_index = _build_global_detail_index(detail_paths, allowed_symbols=allowed_symbols)

    rows: list[dict[str, Any]] = []
    global_match_reason_counts: Counter[str] = Counter()
    source_case_counts: Counter[str] = Counter()
    global_source_recovered_counts: Counter[str] = Counter()
    recoverability_grade_counts: Counter[str] = Counter()
    source_kind_counts: Counter[str] = Counter()

    for case in matched_cases:
        source_case_counts[_to_text(case.get("heuristic_source_file", ""), "(unknown)")] += 1
        payload, meta = _nearest_global_detail_payload(
            detail_index,
            symbol=_to_text(case.get("symbol", ""), ""),
            anchor_time=case.get("anchor_time", ""),
            preferred_source_file=_to_text(case.get("heuristic_source_file", ""), ""),
            max_gap_minutes=max_gap_minutes,
        )
        reason = _to_text(meta.get("reason", "unknown"), "unknown")
        global_match_reason_counts[reason] += 1
        found = payload is not None
        detail_source_file = _to_text(meta.get("detail_source_file", ""), "")
        detail_source_kind = _to_text(meta.get("detail_source_kind", ""), "")
        if found and detail_source_file:
            global_source_recovered_counts[detail_source_file] += 1
        if found and detail_source_kind:
            source_kind_counts[detail_source_kind] += 1
        source = dict(payload or {})
        grade, recoverability_reason = _recoverability_grade(payload)
        recoverability_grade_counts[grade] += 1
        rows.append(
            {
                "episode_id": _to_text(case.get("episode_id", ""), ""),
                "symbol": _to_text(case.get("symbol", ""), "").upper(),
                "anchor_time": _to_text(case.get("anchor_time", ""), ""),
                "manual_wait_teacher_label": _to_text(case.get("manual_wait_teacher_label", ""), "").lower(),
                "heuristic_source_file": _to_text(case.get("heuristic_source_file", ""), ""),
                "global_detail_source_file": detail_source_file,
                "global_detail_source_kind": detail_source_kind,
                "global_detail_row_found": 1 if found else 0,
                "global_detail_match_gap_minutes": meta.get("gap_minutes", ""),
                "global_detail_decision_row_key": _to_text(source.get("decision_row_key", ""), ""),
                "global_detail_core_reason": _to_text(source.get("core_reason", ""), "").lower(),
                "global_detail_observe_reason": _to_text(source.get("observe_reason", ""), "").lower(),
                "global_detail_blocked_by": _to_text(source.get("blocked_by", ""), "").lower(),
                "global_detail_entry_wait_decision": _to_text(source.get("entry_wait_decision", ""), "").lower(),
                "global_detail_entry_enter_value": _to_text(source.get("entry_enter_value", ""), ""),
                "global_detail_entry_wait_value": _to_text(source.get("entry_wait_value", ""), ""),
                "global_detail_barrier_state_present": 1 if _is_structured_present(source.get("barrier_state_v1", "")) else 0,
                "global_detail_belief_state_present": 1 if _is_structured_present(source.get("belief_state_v1", "")) else 0,
                "global_detail_forecast_assist_present": 1 if _is_structured_present(source.get("forecast_assist_v1", "")) else 0,
                "global_detail_forecast_policy_present": 1 if _is_structured_present(source.get("forecast_effective_policy_v1", "")) else 0,
                "global_detail_observe_confirm_present": 1 if _is_structured_present(source.get("observe_confirm_v2", "")) else 0,
                "global_detail_recoverability_grade": grade,
                "global_detail_recoverability_reason": recoverability_reason,
            }
        )

    frame = pd.DataFrame(rows)
    for column in GLOBAL_DETAIL_FALLBACK_AUDIT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame = frame[GLOBAL_DETAIL_FALLBACK_AUDIT_COLUMNS].copy()
    summary = {
        "matched_case_count": int(len(frame)),
        "global_detail_files_scanned": len(detail_paths),
        "global_detail_row_found_count": int(frame["global_detail_row_found"].sum()) if not frame.empty else 0,
        "global_detail_match_reason_counts": dict(global_match_reason_counts),
        "source_case_counts": dict(source_case_counts),
        "global_source_recovered_counts": dict(global_source_recovered_counts),
        "global_source_kind_counts": dict(source_kind_counts),
        "recoverability_grade_counts": dict(recoverability_grade_counts),
        "barrier_state_present_count": int(frame["global_detail_barrier_state_present"].sum()) if not frame.empty else 0,
        "belief_state_present_count": int(frame["global_detail_belief_state_present"].sum()) if not frame.empty else 0,
        "forecast_assist_present_count": int(frame["global_detail_forecast_assist_present"].sum()) if not frame.empty else 0,
        "forecast_policy_present_count": int(frame["global_detail_forecast_policy_present"].sum()) if not frame.empty else 0,
        "observe_confirm_present_count": int(frame["global_detail_observe_confirm_present"].sum()) if not frame.empty else 0,
        "entry_wait_decision_present_count": int(
            frame["global_detail_entry_wait_decision"].fillna("").astype(str).str.strip().replace("nan", "").ne("").sum()
        )
        if not frame.empty
        else 0,
    }
    return frame, summary


def render_manual_vs_heuristic_global_detail_fallback_audit_markdown(summary: dict[str, Any]) -> str:
    def _fmt(key: str) -> str:
        data = dict(summary.get(key, {}) or {})
        return ", ".join(f"{name}={value}" for name, value in sorted(data.items(), key=lambda item: (-item[1], item[0]))) or "none"

    return "\n".join(
        [
            "# Manual vs Heuristic Global Detail Fallback Audit v0",
            "",
            f"- matched cases: `{summary.get('matched_case_count', 0)}`",
            f"- detail files scanned: `{summary.get('global_detail_files_scanned', 0)}`",
            f"- global detail row found: `{summary.get('global_detail_row_found_count', 0)}`",
            f"- global detail match reasons: `{_fmt('global_detail_match_reason_counts')}`",
            f"- global recovered source files: `{summary.get('global_source_recovered_counts', {})}`",
            f"- global recovered source kinds: `{summary.get('global_source_kind_counts', {})}`",
            f"- recoverability grades: `{_fmt('recoverability_grade_counts')}`",
            f"- barrier state present: `{summary.get('barrier_state_present_count', 0)}`",
            f"- belief state present: `{summary.get('belief_state_present_count', 0)}`",
            f"- forecast assist present: `{summary.get('forecast_assist_present_count', 0)}`",
            f"- forecast policy present: `{summary.get('forecast_policy_present_count', 0)}`",
            f"- observe confirm present: `{summary.get('observe_confirm_present_count', 0)}`",
            f"- entry_wait_decision present: `{summary.get('entry_wait_decision_present_count', 0)}`",
            "",
            "## Why This Matters",
            "",
            "- This audit checks whether semantic hints can be recovered from any historical detail archive, not only the detail file paired with the matched legacy CSV.",
            "- If global recoverability is materially higher than paired-source recoverability, the next step is a global fallback reconstruction path in the comparison layer.",
            "- If global recoverability is still low, the true bottleneck is historical semantic logging coverage, not comparison logic.",
        ]
    )
