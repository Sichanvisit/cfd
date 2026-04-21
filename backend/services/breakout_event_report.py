"""Breakout event reporting and roadmap helpers."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.services.breakout_event_overlay import (
    BREAKOUT_EVENT_OVERLAY_CANDIDATES_CONTRACT_VERSION,
    BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_V1,
    BREAKOUT_EVENT_OVERLAY_TRACE_CONTRACT_VERSION,
)
from backend.services.breakout_event_replay import (
    BREAKOUT_ACTION_TARGET_CONTRACT_VERSION,
    BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_V1,
    BREAKOUT_MANUAL_ALIGNMENT_CONTRACT_VERSION,
    build_breakout_action_target_v1,
    build_breakout_manual_alignment_v1,
)
from backend.services.breakout_event_runtime import (
    BREAKOUT_EVENT_RUNTIME_CONTRACT_VERSION,
    BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1,
    build_breakout_event_runtime_v1,
)
from backend.services.entry_wait_quality_replay_bridge import resolve_default_future_bar_path
from backend.services.storage_compaction import (
    resolve_entry_decision_detail_path,
    resolve_entry_decision_row_key,
)


BREAKOUT_EVENT_PHASE0_REPORT_VERSION = "breakout_event_phase0_report_v1"
BREAKOUT_EVENT_PHASE0_ROADMAP_VERSION = "breakout_event_phase0_roadmap_v1"
BREAKOUT_MANUAL_ALIGNMENT_REPORT_VERSION = "breakout_manual_alignment_report_v1"
BREAKOUT_MANUAL_ALIGNMENT_REPORT_ROW_VERSION = "breakout_manual_alignment_report_row_v1"
DEFAULT_OUTPUT_DIR = Path("data") / "analysis" / "breakout_event"
DEFAULT_ENTRY_DECISION_PATH = Path("data/trades/entry_decisions.csv")
DEFAULT_MANUAL_PATH = Path("data/manual_annotations/manual_wait_teacher_annotations.csv")
DEFAULT_MATCH_TOLERANCE_SEC = 300.0
DEFAULT_MAX_FUTURE_BARS = 8


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = _project_root() / path
    return path


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


def _to_epoch(value: object) -> float | None:
    if value in ("", None):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _to_str(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader if isinstance(row, Mapping)]


def _load_detail_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    detail_index: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = _to_str(raw_line)
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, Mapping):
                continue
            row_key = _to_str(record.get("row_key"))
            payload = record.get("payload", {})
            if row_key and isinstance(payload, Mapping):
                detail_index[row_key] = dict(payload)
    return detail_index


def _merge_detail_payload(
    row: Mapping[str, Any] | None,
    *,
    detail_index: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    merged = dict(row or {})
    if not detail_index:
        return merged
    candidate_keys: list[str] = []
    for key in ("detail_row_key", "decision_row_key", "replay_row_key"):
        value = _to_str(merged.get(key))
        if value and value not in candidate_keys:
            candidate_keys.append(value)
    for candidate_key in candidate_keys:
        payload = _as_mapping(detail_index.get(candidate_key))
        if payload:
            merged.update(payload)
            merged["detail_row_key"] = candidate_key
            return merged
    return merged


def build_breakout_event_phase0_report_v1() -> dict[str, Any]:
    contract_inventory = [
        {
            "name": BREAKOUT_EVENT_RUNTIME_CONTRACT_VERSION,
            "file": "backend/services/breakout_event_runtime.py",
            "owner": "runtime_event_owner",
            "allowed_inputs": BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1["runtime_feature_sources"],
            "forbidden_inputs": BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1["forbidden_runtime_inputs"],
        },
        {
            "name": BREAKOUT_EVENT_OVERLAY_CANDIDATES_CONTRACT_VERSION,
            "file": "backend/services/breakout_event_overlay.py",
            "owner": "log_only_overlay_owner",
            "allowed_inputs": BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_V1["runtime_direct_use_fields"],
            "forbidden_inputs": BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_V1["replay_only_fields"],
        },
        {
            "name": BREAKOUT_EVENT_OVERLAY_TRACE_CONTRACT_VERSION,
            "file": "backend/services/breakout_event_overlay.py",
            "owner": "log_only_trace_owner",
            "allowed_inputs": [BREAKOUT_EVENT_OVERLAY_CANDIDATES_CONTRACT_VERSION],
            "forbidden_inputs": BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_V1["replay_only_fields"],
        },
        {
            "name": BREAKOUT_MANUAL_ALIGNMENT_CONTRACT_VERSION,
            "file": "backend/services/breakout_event_replay.py",
            "owner": "replay_alignment_owner",
            "allowed_inputs": BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_V1["replay_only_fields"],
            "forbidden_inputs": BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_V1["forbidden_runtime_exports"],
        },
        {
            "name": BREAKOUT_ACTION_TARGET_CONTRACT_VERSION,
            "file": "backend/services/breakout_event_replay.py",
            "owner": "shadow_target_owner",
            "allowed_inputs": [
                BREAKOUT_MANUAL_ALIGNMENT_CONTRACT_VERSION,
            ],
            "forbidden_inputs": BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_V1["forbidden_runtime_exports"],
        },
    ]

    roadmap = [
        {
            "phase": "P0",
            "status": "ready",
            "name": "interface_freeze",
            "deliverables": [
                "Freeze runtime, overlay, replay, and target contracts",
                "Document no-leakage boundaries",
                "Keep breakout work isolated in new service files",
            ],
            "success_criteria": [
                "Runtime and replay-only fields are explicitly separated",
                "Manual and future labels are forbidden in runtime builders",
                "Single future runtime injection point is identified before live wiring",
            ],
            "collision_risk": "low",
        },
        {
            "phase": "P1",
            "status": "next",
            "name": "detect_only_runtime_injection",
            "deliverables": [
                "Call breakout_event_runtime_v1 from entry_try_open_entry",
                "Store detail payload only",
                "Do not alter live action selection",
            ],
            "success_criteria": [
                "Live behavior remains unchanged",
                "Breakout event rows are inspectable in detail payloads",
            ],
            "collision_risk": "medium",
        },
        {
            "phase": "P2",
            "status": "next",
            "name": "manual_alignment_and_shadow_preview",
            "deliverables": [
                "Build replay alignment rows against manual truth",
                "Generate breakout action targets for preview/shadow only",
                "Measure divergence before any bounded apply",
            ],
            "success_criteria": [
                "Manual anchor coverage is measurable",
                "Preview targets are available without leaking into runtime",
            ],
            "collision_risk": "low",
        },
    ]

    return {
        "contract_version": BREAKOUT_EVENT_PHASE0_REPORT_VERSION,
        "roadmap_version": BREAKOUT_EVENT_PHASE0_ROADMAP_VERSION,
        "phase": "P0",
        "goal": "Freeze breakout event interfaces before detect-only runtime wiring.",
        "single_runtime_injection_point": "backend/services/entry_try_open_entry.py",
        "suggested_runtime_injection_order": [
            "forecast_state25_runtime_bridge_v1",
            BREAKOUT_EVENT_RUNTIME_CONTRACT_VERSION,
            "belief_state25_runtime_bridge_v1",
            "barrier_state25_runtime_bridge_v1",
            BREAKOUT_EVENT_OVERLAY_CANDIDATES_CONTRACT_VERSION,
            BREAKOUT_EVENT_OVERLAY_TRACE_CONTRACT_VERSION,
        ],
        "scope_freeze_contracts": {
            "runtime": BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1,
            "overlay": BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_V1,
            "replay": BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_V1,
        },
        "contract_inventory": contract_inventory,
        "roadmap": roadmap,
        "no_leakage_summary": [
            BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1["no_leakage_rule"],
            BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_V1["no_leakage_rule"],
            BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_V1["no_leakage_rule"],
        ],
    }


def render_breakout_event_phase0_markdown(report: Mapping[str, Any] | None = None) -> str:
    payload = _as_mapping(report) or build_breakout_event_phase0_report_v1()
    lines = [
        "# Breakout Event Phase 0",
        "",
        f"- Goal: {payload.get('goal', '')}",
        f"- Runtime injection point: `{payload.get('single_runtime_injection_point', '')}`",
        "",
        "## Contract Inventory",
    ]
    for contract in list(payload.get("contract_inventory", []) or []):
        mapped = _as_mapping(contract)
        lines.append(
            f"- `{mapped.get('name', '')}` -> `{mapped.get('file', '')}` ({mapped.get('owner', '')})"
        )
    lines.extend(["", "## Roadmap"])
    for item in list(payload.get("roadmap", []) or []):
        mapped = _as_mapping(item)
        lines.append(
            f"- `{mapped.get('phase', '')}` `{mapped.get('name', '')}` [{mapped.get('status', '')}]"
        )
    lines.extend(["", "## No-Leakage"])
    for rule in list(payload.get("no_leakage_summary", []) or []):
        if str(rule or "").strip():
            lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def write_breakout_event_phase0_report(
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    report = build_breakout_event_phase0_report_v1()
    resolved_dir = _resolve_project_path(output_dir, DEFAULT_OUTPUT_DIR)
    resolved_dir.mkdir(parents=True, exist_ok=True)
    json_path = resolved_dir / "breakout_phase0_report_latest.json"
    markdown_path = resolved_dir / "breakout_phase0_report_latest.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_breakout_event_phase0_markdown(report), encoding="utf-8")
    return {
        "json_path": json_path,
        "markdown_path": markdown_path,
    }


def _row_time(row: Mapping[str, Any] | None) -> float:
    mapped = _as_mapping(row)
    for key in ("time", "signal_bar_ts", "anchor_time"):
        resolved = _to_epoch(mapped.get(key))
        if resolved is not None:
            return float(resolved)
    return 0.0


def _future_bar_index(rows: Sequence[Mapping[str, Any]] | None) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for raw_row in rows or []:
        row = _as_mapping(raw_row)
        symbol = _to_str(row.get("symbol")).upper()
        if symbol:
            index.setdefault(symbol, []).append(row)
    for symbol, symbol_rows in index.items():
        index[symbol] = sorted(symbol_rows, key=_row_time)
    return index


def _time_bounds(rows: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    timestamps = [float(_row_time(row)) for row in rows or [] if _row_time(row) > 0.0]
    if not timestamps:
        return {"min_ts": 0.0, "max_ts": 0.0, "count": 0}
    return {
        "min_ts": float(min(timestamps)),
        "max_ts": float(max(timestamps)),
        "count": int(len(timestamps)),
    }


def _temporal_overlap_status(
    manual_bounds: Mapping[str, Any] | None,
    entry_bounds: Mapping[str, Any] | None,
) -> str:
    manual_min = _to_float(_as_mapping(manual_bounds).get("min_ts"))
    manual_max = _to_float(_as_mapping(manual_bounds).get("max_ts"))
    entry_min = _to_float(_as_mapping(entry_bounds).get("min_ts"))
    entry_max = _to_float(_as_mapping(entry_bounds).get("max_ts"))
    if manual_min <= 0.0 or entry_min <= 0.0:
        return "insufficient_bounds"
    if manual_max < entry_min:
        return "manual_before_entry_window"
    if entry_max < manual_min:
        return "entry_before_manual_window"
    return "overlap"


def _entry_rows_by_symbol(rows: Sequence[Mapping[str, Any]] | None) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for raw_row in rows or []:
        row = _as_mapping(raw_row)
        symbol = _to_str(row.get("symbol")).upper()
        if symbol:
            index.setdefault(symbol, []).append(row)
    for symbol, symbol_rows in index.items():
        index[symbol] = sorted(symbol_rows, key=_row_time)
    return index


def _manual_wait_rows(
    rows: Sequence[Mapping[str, Any]] | None,
    *,
    accepted_only: bool,
    symbols: Sequence[str] | None,
) -> list[dict[str, Any]]:
    symbol_filter = {_to_str(item).upper() for item in list(symbols or []) if _to_str(item)}
    selected: list[dict[str, Any]] = []
    for raw_row in rows or []:
        row = _as_mapping(raw_row)
        manual_label = _to_str(row.get("manual_wait_teacher_label")).lower()
        if not manual_label:
            continue
        if accepted_only and not _to_str(row.get("review_status")).lower().startswith("accepted"):
            continue
        symbol = _to_str(row.get("symbol")).upper()
        if symbol_filter and symbol not in symbol_filter:
            continue
        selected.append(row)
    return sorted(selected, key=_row_time)


def _is_wait_like_row(row: Mapping[str, Any] | None) -> bool:
    mapped = _as_mapping(row)
    outcome = _to_str(mapped.get("outcome")).lower()
    entry_wait_decision = _to_str(mapped.get("entry_wait_decision")).lower()
    entry_wait_state = _to_str(mapped.get("entry_wait_state")).upper()
    observe_reason = _to_str(mapped.get("observe_reason"))
    blocked_by = _to_str(mapped.get("blocked_by"))
    return bool(
        outcome == "wait"
        or entry_wait_decision.startswith("wait")
        or entry_wait_state
        or observe_reason
        or blocked_by
    )


def _nearest_decision_row(
    manual_row: Mapping[str, Any] | None,
    *,
    entry_rows_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    match_tolerance_sec: float,
) -> tuple[dict[str, Any], float, str]:
    manual = _as_mapping(manual_row)
    symbol = _to_str(manual.get("symbol")).upper()
    anchor_ts = _row_time(manual)
    if not symbol or anchor_ts <= 0.0:
        return {}, 0.0, "missing_symbol_or_anchor_time"
    candidates = list((entry_rows_by_symbol or {}).get(symbol, []) or [])
    if not candidates:
        return {}, 0.0, "no_symbol_rows"

    best_row: dict[str, Any] = {}
    best_score: tuple[int, float] | None = None
    best_delta = 0.0
    for candidate in candidates:
        candidate_ts = _row_time(candidate)
        if candidate_ts <= 0.0:
            continue
        delta = abs(candidate_ts - anchor_ts)
        if delta > float(match_tolerance_sec):
            continue
        wait_penalty = 0 if _is_wait_like_row(candidate) else 1
        score = (wait_penalty, float(delta))
        if best_score is None or score < best_score:
            best_score = score
            best_row = dict(candidate)
            best_delta = float(delta)
    if not best_row:
        return {}, 0.0, "no_row_within_tolerance"
    match_quality = "wait_like_exactish" if _is_wait_like_row(best_row) else "nearest_any_decision"
    return best_row, best_delta, match_quality


def _candidate_future_bars(
    *,
    symbol: str,
    anchor_ts: float,
    future_bar_index: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    max_future_bars: int,
) -> list[dict[str, Any]]:
    if anchor_ts <= 0.0 or not symbol:
        return []
    rows = list((future_bar_index or {}).get(symbol.upper(), []) or [])
    filtered = [dict(row) for row in rows if _row_time(row) >= anchor_ts]
    return filtered[: max(0, int(max_future_bars))]


def _future_move_summary(
    *,
    side: str,
    anchor_price: float,
    future_bars: Sequence[Mapping[str, Any]] | None,
) -> dict[str, float]:
    if anchor_price <= 0.0 or side not in {"BUY", "SELL"}:
        return {
            "future_favorable_move_ratio": 0.0,
            "future_adverse_move_ratio": 0.0,
        }
    highs = [_to_float(_as_mapping(bar).get("high", _as_mapping(bar).get("close", 0.0))) for bar in future_bars or []]
    lows = [_to_float(_as_mapping(bar).get("low", _as_mapping(bar).get("close", 0.0))) for bar in future_bars or []]
    highs = [value for value in highs if value > 0.0]
    lows = [value for value in lows if value > 0.0]
    if not highs or not lows:
        return {
            "future_favorable_move_ratio": 0.0,
            "future_adverse_move_ratio": 0.0,
        }
    if side == "BUY":
        favorable = max(0.0, (max(highs) - anchor_price) / anchor_price)
        adverse = max(0.0, (anchor_price - min(lows)) / anchor_price)
    else:
        favorable = max(0.0, (anchor_price - min(lows)) / anchor_price)
        adverse = max(0.0, (max(highs) - anchor_price) / anchor_price)
    return {
        "future_favorable_move_ratio": round(float(favorable), 6),
        "future_adverse_move_ratio": round(float(adverse), 6),
    }


def build_breakout_manual_alignment_report_v1(
    *,
    entry_decision_rows: Sequence[Mapping[str, Any]] | None = None,
    manual_rows: Sequence[Mapping[str, Any]] | None = None,
    future_bar_rows: Sequence[Mapping[str, Any]] | None = None,
    accepted_only: bool = False,
    symbols: Sequence[str] | None = None,
    match_tolerance_sec: float = DEFAULT_MATCH_TOLERANCE_SEC,
    max_future_bars: int = DEFAULT_MAX_FUTURE_BARS,
) -> dict[str, Any]:
    manual_wait_rows = _manual_wait_rows(manual_rows, accepted_only=accepted_only, symbols=symbols)
    entry_by_symbol = _entry_rows_by_symbol(entry_decision_rows)
    future_index = _future_bar_index(future_bar_rows)

    rows: list[dict[str, Any]] = []
    symbol_counts: dict[str, int] = {}
    manual_label_counts: dict[str, int] = {}
    review_status_counts: dict[str, int] = {}
    alignment_counts: dict[str, int] = {}
    target_counts: dict[str, int] = {}
    match_status_counts: dict[str, int] = {}
    matched_decision_count = 0
    future_bar_covered_count = 0
    aligned_count = 0

    for manual_row in manual_wait_rows:
        symbol = _to_str(manual_row.get("symbol")).upper()
        manual_label = _to_str(manual_row.get("manual_wait_teacher_label")).lower()
        review_status = _to_str(manual_row.get("review_status")).lower()
        anchor_side = _to_str(manual_row.get("anchor_side")).upper()
        anchor_time = _to_str(manual_row.get("anchor_time"))
        anchor_ts = _row_time(manual_row)
        anchor_price = _to_float(manual_row.get("anchor_price"))

        matched_row, decision_time_delta_sec, match_quality = _nearest_decision_row(
            manual_row,
            entry_rows_by_symbol=entry_by_symbol,
            match_tolerance_sec=match_tolerance_sec,
        )
        future_bars = _candidate_future_bars(
            symbol=symbol,
            anchor_ts=anchor_ts,
            future_bar_index=future_index,
            max_future_bars=max_future_bars,
        )
        future_summary = _future_move_summary(
            side=anchor_side,
            anchor_price=anchor_price,
            future_bars=future_bars,
        )
        if future_bars:
            future_bar_covered_count += 1

        if matched_row:
            matched_decision_count += 1
            breakout_runtime = _as_mapping(matched_row.get(BREAKOUT_EVENT_RUNTIME_CONTRACT_VERSION))
            if not breakout_runtime:
                breakout_runtime = build_breakout_event_runtime_v1(matched_row)
            alignment = build_breakout_manual_alignment_v1(
                decision_row=matched_row,
                breakout_event_runtime_v1=breakout_runtime,
                manual_wait_teacher_row=manual_row,
                future_outcome_row=future_summary,
            )
            target = build_breakout_action_target_v1(alignment)
            match_status = "matched"
        else:
            breakout_runtime = {}
            alignment = {
                "available": False,
                "aligned": False,
                "alignment_class": "no_decision_match",
                "reason_summary": match_quality,
            }
            target = {
                "available": False,
                "target": "",
                "target_source": "",
                "provisional_target": False,
                "reason_summary": "no_decision_match",
            }
            match_status = "manual_only"

        if alignment.get("aligned", False):
            aligned_count += 1

        row = {
            "contract_version": BREAKOUT_MANUAL_ALIGNMENT_REPORT_ROW_VERSION,
            "annotation_id": _to_str(manual_row.get("annotation_id")),
            "episode_id": _to_str(manual_row.get("episode_id")),
            "symbol": symbol,
            "anchor_side": anchor_side,
            "anchor_time": anchor_time,
            "anchor_price": round(float(anchor_price), 6),
            "manual_wait_teacher_label": manual_label,
            "review_status": review_status,
            "match_status": match_status,
            "match_quality": match_quality,
            "matched_decision_row_key": _to_str(
                matched_row.get("decision_row_key") or matched_row.get("detail_row_key") or resolve_entry_decision_row_key(matched_row)
            ),
            "matched_decision_time": _to_str(matched_row.get("time")),
            "decision_time_delta_sec": round(float(decision_time_delta_sec), 3),
            "future_bar_count": int(len(future_bars)),
            "future_favorable_move_ratio": float(future_summary.get("future_favorable_move_ratio", 0.0)),
            "future_adverse_move_ratio": float(future_summary.get("future_adverse_move_ratio", 0.0)),
            "breakout_detected": bool(breakout_runtime.get("breakout_detected", False)),
            "breakout_direction": _to_str(breakout_runtime.get("breakout_direction")).upper(),
            "breakout_state": _to_str(breakout_runtime.get("breakout_state")).lower(),
            "breakout_confidence": round(_to_float(breakout_runtime.get("breakout_confidence")), 6),
            "breakout_failure_risk": round(_to_float(breakout_runtime.get("breakout_failure_risk")), 6),
            "alignment_class": _to_str(alignment.get("alignment_class")).lower(),
            "aligned": bool(alignment.get("aligned", False)),
            "target": _to_str(target.get("target")).upper(),
            "target_source": _to_str(target.get("target_source")).lower(),
            "provisional_target": bool(target.get("provisional_target", False)),
            "reason_summary": "|".join(
                token
                for token in (
                    _to_str(alignment.get("reason_summary")).lower(),
                    _to_str(target.get("reason_summary")).lower(),
                )
                if token
            ),
        }
        rows.append(row)

        symbol_counts[symbol] = int(symbol_counts.get(symbol, 0)) + 1
        manual_label_counts[manual_label] = int(manual_label_counts.get(manual_label, 0)) + 1
        review_status_counts[review_status] = int(review_status_counts.get(review_status, 0)) + 1
        alignment_key = _to_str(row.get("alignment_class")).lower() or "unknown"
        alignment_counts[alignment_key] = int(alignment_counts.get(alignment_key, 0)) + 1
        target_key = _to_str(row.get("target")).upper() or "UNSET"
        target_counts[target_key] = int(target_counts.get(target_key, 0)) + 1
        match_status_counts[match_status] = int(match_status_counts.get(match_status, 0)) + 1

    manual_row_count = len(manual_wait_rows)
    unmatched_manual_count = max(0, manual_row_count - matched_decision_count)
    accepted_manual_count = sum(
        1 for row in manual_wait_rows if _to_str(_as_mapping(row).get("review_status")).lower().startswith("accepted")
    )
    manual_bounds = _time_bounds(manual_wait_rows)
    entry_bounds = _time_bounds(entry_decision_rows)
    temporal_overlap_status = _temporal_overlap_status(manual_bounds, entry_bounds)

    recommended_action = ""
    if manual_row_count <= 0:
        recommended_action = "Add manual wait annotations before breakout alignment review."
    elif temporal_overlap_status == "manual_before_entry_window":
        recommended_action = "Accepted manual anchors end before the available entry decision window starts; annotate a newer window or replay older entry decisions."
    elif temporal_overlap_status == "entry_before_manual_window":
        recommended_action = "Entry decision window ends before the accepted manual anchors begin; regenerate entry decisions for the annotated period."
    elif matched_decision_count <= 0:
        recommended_action = "Check symbol/time matching and ensure entry_decisions detail rows exist for the annotated window."
    elif future_bar_covered_count < manual_row_count:
        recommended_action = "Backfill future bars for uncovered manual anchors before trusting breakout action targets."
    elif aligned_count <= 0:
        recommended_action = "Review breakout runtime state mapping because manual anchors are present but no aligned breakout cases were found."
    else:
        recommended_action = "Use aligned breakout rows as the first seed set for breakout shadow targets."

    return {
        "contract_version": BREAKOUT_MANUAL_ALIGNMENT_REPORT_VERSION,
        "phase": "P2",
        "coverage": {
            "manual_row_count": int(manual_row_count),
            "accepted_manual_count": int(accepted_manual_count),
            "matched_decision_count": int(matched_decision_count),
            "unmatched_manual_count": int(unmatched_manual_count),
            "future_bar_covered_count": int(future_bar_covered_count),
            "aligned_count": int(aligned_count),
            "accepted_only": bool(accepted_only),
            "match_tolerance_sec": float(match_tolerance_sec),
            "max_future_bars": int(max_future_bars),
            "manual_window": dict(manual_bounds),
            "entry_window": dict(entry_bounds),
            "temporal_overlap_status": temporal_overlap_status,
            "symbol_counts": dict(symbol_counts),
            "manual_label_counts": dict(manual_label_counts),
            "review_status_counts": dict(review_status_counts),
            "alignment_counts": dict(alignment_counts),
            "target_counts": dict(target_counts),
            "match_status_counts": dict(match_status_counts),
            "recommended_action": recommended_action,
        },
        "rows": rows,
    }


def render_breakout_manual_alignment_markdown(report: Mapping[str, Any] | None = None) -> str:
    payload = _as_mapping(report)
    coverage = _as_mapping(payload.get("coverage"))
    lines = [
        "# Breakout Manual Alignment Report",
        "",
        f"- manual_row_count: {int(_to_int(coverage.get('manual_row_count'), 0))}",
        f"- accepted_manual_count: {int(_to_int(coverage.get('accepted_manual_count'), 0))}",
        f"- matched_decision_count: {int(_to_int(coverage.get('matched_decision_count'), 0))}",
        f"- unmatched_manual_count: {int(_to_int(coverage.get('unmatched_manual_count'), 0))}",
        f"- future_bar_covered_count: {int(_to_int(coverage.get('future_bar_covered_count'), 0))}",
        f"- aligned_count: {int(_to_int(coverage.get('aligned_count'), 0))}",
        f"- match_tolerance_sec: {float(_to_float(coverage.get('match_tolerance_sec'), 0.0))}",
        f"- max_future_bars: {int(_to_int(coverage.get('max_future_bars'), 0))}",
        f"- temporal_overlap_status: {_to_str(coverage.get('temporal_overlap_status'))}",
        "",
        "## Recommended Action",
        f"- {_to_str(coverage.get('recommended_action'))}",
        "",
        "## Manual Label Counts",
    ]
    for key, value in sorted(_as_mapping(coverage.get("manual_label_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "## Alignment Counts"])
    for key, value in sorted(_as_mapping(coverage.get("alignment_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "## Target Counts"])
    for key, value in sorted(_as_mapping(coverage.get("target_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.extend(["", "## Match Status Counts"])
    for key, value in sorted(_as_mapping(coverage.get("match_status_counts")).items()):
        lines.append(f"- {key}: {int(_to_int(value, 0))}")
    lines.append("")
    return "\n".join(lines)


def write_breakout_manual_alignment_report(
    *,
    entry_decision_path: str | Path | None = None,
    manual_path: str | Path | None = None,
    future_bar_path: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
    accepted_only: bool = False,
    symbols: Sequence[str] | None = None,
    match_tolerance_sec: float = DEFAULT_MATCH_TOLERANCE_SEC,
    max_future_bars: int = DEFAULT_MAX_FUTURE_BARS,
) -> dict[str, Any]:
    entry_path = _resolve_project_path(entry_decision_path, DEFAULT_ENTRY_DECISION_PATH)
    manual_file = _resolve_project_path(manual_path, DEFAULT_MANUAL_PATH)
    future_path = _resolve_project_path(future_bar_path, Path("")) if future_bar_path is not None else None
    future_bar_resolution = "explicit" if future_path is not None else "none"
    if future_path is None:
        resolved_future = resolve_default_future_bar_path(entry_path)
        if resolved_future is not None:
            future_path = resolved_future
            future_bar_resolution = "auto_companion"

    csv_output_file = _resolve_project_path(
        csv_output_path,
        DEFAULT_OUTPUT_DIR / "breakout_manual_alignment_latest.csv",
    )
    json_output_file = _resolve_project_path(
        json_output_path,
        DEFAULT_OUTPUT_DIR / "breakout_manual_alignment_latest.json",
    )
    markdown_output_file = _resolve_project_path(
        markdown_output_path,
        DEFAULT_OUTPUT_DIR / "breakout_manual_alignment_latest.md",
    )

    detail_index = _load_detail_index(resolve_entry_decision_detail_path(entry_path))
    entry_rows = [_merge_detail_payload(row, detail_index=detail_index) for row in _load_csv_rows(entry_path)]
    manual_rows = _load_csv_rows(manual_file)
    future_rows = _load_csv_rows(future_path) if future_path is not None and future_path.exists() else []

    report = build_breakout_manual_alignment_report_v1(
        entry_decision_rows=entry_rows,
        manual_rows=manual_rows,
        future_bar_rows=future_rows,
        accepted_only=accepted_only,
        symbols=symbols,
        match_tolerance_sec=match_tolerance_sec,
        max_future_bars=max_future_bars,
    )
    report["entry_decision_path"] = str(entry_path)
    report["manual_path"] = str(manual_file)
    report["future_bar_path"] = str(future_path) if future_path is not None else ""
    report["future_bar_resolution"] = str(future_bar_resolution)
    report["csv_output_path"] = str(csv_output_file)
    report["json_output_path"] = str(json_output_file)
    report["markdown_output_path"] = str(markdown_output_file)

    csv_output_file.parent.mkdir(parents=True, exist_ok=True)
    rows = list(report.get("rows", []) or [])
    if rows:
        fieldnames: list[str] = []
        for row in rows:
            for key in list(_as_mapping(row).keys()):
                if key not in fieldnames:
                    fieldnames.append(str(key))
        with csv_output_file.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(_as_mapping(row))
    else:
        with csv_output_file.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["contract_version"])

    json_output_file.parent.mkdir(parents=True, exist_ok=True)
    json_output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_file.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_file.write_text(render_breakout_manual_alignment_markdown(report), encoding="utf-8")
    return report
