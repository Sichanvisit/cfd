"""Audit whether legacy entry_decisions detail JSONL can recover heuristic hints."""

from __future__ import annotations

import csv
import json
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


DETAIL_FALLBACK_AUDIT_COLUMNS = [
    "episode_id",
    "symbol",
    "anchor_time",
    "manual_wait_teacher_label",
    "heuristic_source_file",
    "detail_source_file",
    "detail_row_found",
    "detail_match_gap_minutes",
    "detail_decision_row_key",
    "detail_core_reason",
    "detail_observe_reason",
    "detail_blocked_by",
    "detail_entry_wait_decision",
    "detail_entry_enter_value",
    "detail_entry_wait_value",
    "detail_barrier_state_present",
    "detail_belief_state_present",
    "detail_forecast_assist_present",
    "detail_forecast_policy_present",
    "detail_observe_confirm_present",
    "detail_recoverability_grade",
    "detail_recoverability_reason",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


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


def _utc_epoch_to_local_timestamp(value: object) -> pd.Timestamp | None:
    try:
        if value in ("", None):
            return None
        return (
            pd.to_datetime(float(value), unit="s", utc=True)
            .tz_convert("Asia/Seoul")
            .tz_localize(None)
        )
    except (TypeError, ValueError, OverflowError):
        return None


def _is_structured_present(value: object) -> bool:
    text = _to_text(value, "")
    if not text:
        return False
    if text[:1] in "{[":
        try:
            parsed = json.loads(text)
            return bool(parsed)
        except Exception:
            return False
    return True


def load_matched_cases(path: str | Path) -> list[dict[str, Any]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _detail_path_for_source(trades_dir: str | Path, source_file: str) -> Path:
    return Path(trades_dir) / source_file.replace(".csv", ".detail.jsonl")


def _detail_anchor_timestamp(payload: dict[str, Any]) -> pd.Timestamp | None:
    stamp = _utc_epoch_to_local_timestamp(payload.get("signal_bar_ts", ""))
    if stamp is not None:
        return stamp
    return _parse_local_timestamp(payload.get("time", ""))


def _build_detail_index(
    detail_path: str | Path,
    *,
    allowed_symbols: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    path = Path(detail_path)
    if not path.exists():
        return {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig") as fh:
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
            time_value = _detail_anchor_timestamp(payload)
            if time_value is None:
                continue
            grouped[symbol].append(
                {
                    "time": time_value,
                    "payload": payload,
                }
            )
    index: dict[str, dict[str, Any]] = {}
    for symbol, records in grouped.items():
        ordered = sorted(records, key=lambda item: pd.Timestamp(item["time"]).value)
        index[symbol] = {
            "times": [pd.Timestamp(item["time"]).value for item in ordered],
            "rows": ordered,
        }
    return index


def _nearest_detail_payload(
    index: dict[str, dict[str, Any]],
    *,
    symbol: str,
    anchor_time: object,
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
    for idx in (pos - 1, pos):
        if 0 <= idx < len(times):
            gap_minutes = abs(times[idx] - target) / 60_000_000_000
            candidates.append((gap_minutes, idx))
    if not candidates:
        return None, {"reason": "detail_time_missing"}
    gap_minutes, best_idx = min(candidates, key=lambda item: (item[0], item[1]))
    if gap_minutes > float(max_gap_minutes):
        return None, {"reason": "detail_gap_exceeds_limit", "gap_minutes": round(gap_minutes, 3)}
    return rows[best_idx]["payload"], {"reason": "matched", "gap_minutes": round(gap_minutes, 3)}


def _recoverability_grade(payload: dict[str, Any] | None) -> tuple[str, str]:
    source = dict(payload or {})
    barrier_present = _is_structured_present(source.get("barrier_state_v1", ""))
    belief_present = _is_structured_present(source.get("belief_state_v1", ""))
    forecast_assist_present = _is_structured_present(source.get("forecast_assist_v1", ""))
    forecast_policy_present = _is_structured_present(source.get("forecast_effective_policy_v1", ""))
    observe_present = _is_structured_present(source.get("observe_confirm_v2", ""))
    entry_wait_decision_present = bool(_to_text(source.get("entry_wait_decision", ""), ""))
    if barrier_present and observe_present and entry_wait_decision_present:
        return "high", "barrier+observe+wait_decision_present"
    if barrier_present and (forecast_assist_present or forecast_policy_present or belief_present):
        return "medium", "barrier_plus_semantic_support_present"
    if observe_present or entry_wait_decision_present or belief_present:
        return "low", "partial_semantic_payload_present"
    return "none", "detail_semantic_payload_missing"


def build_manual_vs_heuristic_detail_fallback_audit(
    matched_cases: list[dict[str, Any]],
    *,
    trades_dir: str | Path,
    max_gap_minutes: int = 180,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not matched_cases:
        empty = pd.DataFrame(columns=DETAIL_FALLBACK_AUDIT_COLUMNS)
        return empty, {
            "matched_case_count": 0,
            "detail_row_found_count": 0,
            "recoverability_grade_counts": {},
        }

    cases_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in matched_cases:
        cases_by_source[_to_text(case.get("heuristic_source_file", ""), "")].append(case)

    rows: list[dict[str, Any]] = []
    source_case_counts: Counter[str] = Counter()
    source_recovered_counts: Counter[str] = Counter()
    recoverability_grade_counts: Counter[str] = Counter()
    detail_match_reason_counts: Counter[str] = Counter()

    for source_file, cases in cases_by_source.items():
        detail_path = _detail_path_for_source(trades_dir, source_file)
        allowed_symbols = {_to_text(case.get("symbol", ""), "").upper() for case in cases}
        detail_index = _build_detail_index(detail_path, allowed_symbols=allowed_symbols)
        for case in cases:
            source_case_counts[source_file or "(unknown)"] += 1
            payload, meta = _nearest_detail_payload(
                detail_index,
                symbol=_to_text(case.get("symbol", ""), ""),
                anchor_time=case.get("anchor_time", ""),
                max_gap_minutes=max_gap_minutes,
            )
            reason = _to_text(meta.get("reason", "unknown"), "unknown")
            detail_match_reason_counts[reason] += 1
            found = payload is not None
            if found:
                source_recovered_counts[source_file or "(unknown)"] += 1
            grade, recoverability_reason = _recoverability_grade(payload)
            recoverability_grade_counts[grade] += 1
            source = dict(payload or {})
            rows.append(
                {
                    "episode_id": _to_text(case.get("episode_id", ""), ""),
                    "symbol": _to_text(case.get("symbol", ""), "").upper(),
                    "anchor_time": _to_text(case.get("anchor_time", ""), ""),
                    "manual_wait_teacher_label": _to_text(case.get("manual_wait_teacher_label", ""), "").lower(),
                    "heuristic_source_file": source_file,
                    "detail_source_file": detail_path.name if detail_path.exists() else "",
                    "detail_row_found": 1 if found else 0,
                    "detail_match_gap_minutes": meta.get("gap_minutes", ""),
                    "detail_decision_row_key": _to_text(source.get("decision_row_key", ""), ""),
                    "detail_core_reason": _to_text(source.get("core_reason", ""), "").lower(),
                    "detail_observe_reason": _to_text(source.get("observe_reason", ""), "").lower(),
                    "detail_blocked_by": _to_text(source.get("blocked_by", ""), "").lower(),
                    "detail_entry_wait_decision": _to_text(source.get("entry_wait_decision", ""), "").lower(),
                    "detail_entry_enter_value": _to_text(source.get("entry_enter_value", ""), ""),
                    "detail_entry_wait_value": _to_text(source.get("entry_wait_value", ""), ""),
                    "detail_barrier_state_present": 1 if _is_structured_present(source.get("barrier_state_v1", "")) else 0,
                    "detail_belief_state_present": 1 if _is_structured_present(source.get("belief_state_v1", "")) else 0,
                    "detail_forecast_assist_present": 1 if _is_structured_present(source.get("forecast_assist_v1", "")) else 0,
                    "detail_forecast_policy_present": 1 if _is_structured_present(source.get("forecast_effective_policy_v1", "")) else 0,
                    "detail_observe_confirm_present": 1 if _is_structured_present(source.get("observe_confirm_v2", "")) else 0,
                    "detail_recoverability_grade": grade,
                    "detail_recoverability_reason": recoverability_reason,
                }
            )

    frame = pd.DataFrame(rows)
    for column in DETAIL_FALLBACK_AUDIT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame = frame[DETAIL_FALLBACK_AUDIT_COLUMNS].copy()
    summary = {
        "matched_case_count": int(len(frame)),
        "detail_row_found_count": int(frame["detail_row_found"].sum()) if not frame.empty else 0,
        "detail_match_reason_counts": dict(detail_match_reason_counts),
        "source_case_counts": dict(source_case_counts),
        "source_recovered_counts": dict(source_recovered_counts),
        "recoverability_grade_counts": dict(recoverability_grade_counts),
        "barrier_state_present_count": int(frame["detail_barrier_state_present"].sum()) if not frame.empty else 0,
        "belief_state_present_count": int(frame["detail_belief_state_present"].sum()) if not frame.empty else 0,
        "forecast_assist_present_count": int(frame["detail_forecast_assist_present"].sum()) if not frame.empty else 0,
        "forecast_policy_present_count": int(frame["detail_forecast_policy_present"].sum()) if not frame.empty else 0,
        "observe_confirm_present_count": int(frame["detail_observe_confirm_present"].sum()) if not frame.empty else 0,
        "entry_wait_decision_present_count": int(
            frame["detail_entry_wait_decision"].fillna("").astype(str).str.strip().replace("nan", "").ne("").sum()
        )
        if not frame.empty
        else 0,
    }
    return frame, summary


def render_manual_vs_heuristic_detail_fallback_audit_markdown(summary: dict[str, Any]) -> str:
    def _fmt(key: str) -> str:
        data = dict(summary.get(key, {}) or {})
        return ", ".join(f"{name}={value}" for name, value in sorted(data.items(), key=lambda item: (-item[1], item[0]))) or "none"

    lines = [
        "# Manual vs Heuristic Detail Fallback Audit v0",
        "",
        f"- matched cases: `{summary.get('matched_case_count', 0)}`",
        f"- detail row found: `{summary.get('detail_row_found_count', 0)}`",
        f"- detail match reasons: `{_fmt('detail_match_reason_counts')}`",
        f"- source case counts: `{summary.get('source_case_counts', {})}`",
        f"- source recovered counts: `{summary.get('source_recovered_counts', {})}`",
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
        "- This audit checks whether legacy detail JSONL still carries enough semantic state to reconstruct barrier/wait hints even when the legacy CSV schema does not.",
        "- If recoverability is high, the next step is fallback reconstruction, not more manual labeling or schema archaeology.",
        "- If recoverability is low, then the true gap is historical logging coverage.",
    ]
    return "\n".join(lines) + "\n"
