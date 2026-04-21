"""Entry authority trace extraction and latest summary outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


ENTRY_AUTHORITY_TRACE_CONTRACT_VERSION = "entry_authority_trace_v1"
ENTRY_AUTHORITY_TRACE_FIELDS = [
    "entry_authority_contract_version",
    "entry_authority_owner",
    "entry_candidate_action_source",
    "entry_candidate_action",
    "entry_candidate_rejected_by",
    "entry_authority_stage",
    "entry_authority_threshold_owner",
    "entry_authority_execution_owner",
    "entry_authority_reason_summary",
]
ENTRY_AUTHORITY_TRACE_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "rollout_mode",
    "shadow_runtime_state",
    "recent_row_count",
    "entered_count",
    "skipped_count",
    "recent_symbols",
    "recent_authority_owner_counts",
    "recent_candidate_action_source_counts",
    "recent_candidate_rejected_by_counts",
    "recent_authority_stage_counts",
    "recent_threshold_owner_counts",
    "recent_execution_owner_counts",
    "baseline_no_action_count",
    "semantic_threshold_veto_count",
    "utility_gate_veto_count",
    "post_entry_guard_veto_count",
    "broker_veto_count",
    "active_action_conflict_guard_count",
    "semantic_threshold_owner_count",
    "recommended_next_action",
]


def load_entry_authority_trace_frame(path: str | Path) -> pd.DataFrame:
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


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _to_bool(value: object) -> bool:
    text = _to_text(value).lower()
    return text in {"1", "true", "yes", "y", "on"}


def _stable_join(values: pd.Series) -> str:
    seen: list[str] = []
    for raw in values.fillna("").astype(str):
        text = raw.strip()
        if not text or text in seen:
            continue
        seen.append(text)
    return ",".join(seen)


def _series_json_counts(values: pd.Series) -> str:
    counts = (
        values.fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .to_dict()
    )
    return json.dumps(counts, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _resolve_candidate_action_source(record: Mapping[str, Any], candidate_action: str) -> str:
    if candidate_action not in {"BUY", "SELL"}:
        return "none"
    bridge_selected = _to_bool(record.get("entry_candidate_bridge_selected"))
    bridge_action = _to_text(record.get("entry_candidate_bridge_action")).upper()
    bridge_source = _to_text(record.get("entry_candidate_bridge_source")).lower()
    if bridge_selected and bridge_action == candidate_action and bridge_source:
        return bridge_source
    intended_source = _to_text(record.get("core_intended_action_source")).lower()
    core_reason = _to_text(record.get("core_reason")).lower()
    if "state25" in intended_source or "state25" in core_reason:
        return "state25_candidate"
    if "teacher_label_exploration" in intended_source or "teacher_label_exploration" in core_reason:
        return "teacher_label_exploration"
    if "semantic" in intended_source or "shadow" in intended_source:
        return "semantic_candidate"
    if "semantic_probe_bridge" in core_reason or ("shadow" in core_reason and "probe" in core_reason):
        return "semantic_candidate"
    if "teacher" in intended_source:
        return "teacher_label_exploration"
    return "baseline_score"


def _is_broker_failure(blocked_by: str) -> bool:
    return blocked_by in {"order_send_failed", "market_closed_session"}


def _is_utility_veto(record: Mapping[str, Any], blocked_by: str) -> bool:
    if blocked_by == "utility_not_ready" or blocked_by.startswith("utility_"):
        return True
    return _to_int(record.get("u_pass"), 1) <= 0


def _resolve_pre_entry_rejected_by(record: Mapping[str, Any], blocked_by: str) -> str:
    if isinstance(record.get("entry_blocked_guard_v1"), dict) and record.get("entry_blocked_guard_v1"):
        return "entry_blocked_guard"
    if blocked_by == "topdown_timeframe_gate_blocked":
        return "topdown_gate"
    if blocked_by == "h1_entry_gate_blocked":
        return "h1_gate"
    if blocked_by.startswith("hard_guard_"):
        return "hard_guard"
    if blocked_by == "max_positions_reached":
        return "position_limit_guard"
    if blocked_by == "entry_cooldown":
        return "cooldown_guard"
    if blocked_by.startswith("edge_direction_"):
        return "edge_direction_guard"
    if blocked_by.startswith("range_lower_buy_") or blocked_by.startswith("range_upper_"):
        return "setup_specific_guard"
    return ""


def _resolve_post_entry_rejected_by(record: Mapping[str, Any], blocked_by: str) -> str:
    if isinstance(record.get("probe_promotion_guard_v1"), dict) and record.get("probe_promotion_guard_v1"):
        return "probe_promotion_guard"
    if isinstance(record.get("consumer_open_guard_v1"), dict) and record.get("consumer_open_guard_v1"):
        return "consumer_open_guard"
    if blocked_by.startswith("cluster_"):
        return "cluster_guard"
    if "box_middle" in blocked_by:
        return "box_middle_guard"
    if blocked_by.startswith("pyramid_"):
        return "pyramid_guard"
    if blocked_by in {"market_closed_cooldown", "order_blocked"}:
        return "order_block_guard"
    if _to_int(record.get("order_block_remaining_sec"), 0) > 0:
        return "order_block_guard"
    if "consumer" in blocked_by:
        return "consumer_open_guard"
    if "probe" in blocked_by and ("promot" in blocked_by or "not_" in blocked_by):
        return "probe_promotion_guard"
    return ""


def build_entry_authority_fields(row: Mapping[str, Any] | None) -> dict[str, Any]:
    record = dict(row or {})
    candidate_action = _to_text(record.get("action") or record.get("action_selected")).upper()
    if candidate_action not in {"BUY", "SELL"} and _to_bool(record.get("entry_candidate_bridge_selected")):
        candidate_action = _to_text(record.get("entry_candidate_bridge_action")).upper()
    if candidate_action not in {"BUY", "SELL"}:
        candidate_action = ""
    outcome = _to_text(record.get("outcome"), "skipped").lower()
    blocked_by = _to_text(record.get("blocked_by"))
    threshold_owner = (
        "semantic_threshold_guard"
        if _to_bool(record.get("semantic_live_threshold_applied"))
        else "baseline_dynamic_threshold"
    )
    candidate_source = _resolve_candidate_action_source(record, candidate_action)

    owner = "baseline_score"
    rejected_by = ""
    stage = "baseline_action_selection"
    execution_owner = "none"

    if outcome == "entered":
        owner = "broker"
        stage = "broker_execution"
        execution_owner = "broker"
    elif _to_bool(record.get("active_action_conflict_guard_applied")) or blocked_by == "active_action_conflict_guard":
        owner = "active_action_conflict_guard"
        rejected_by = "active_action_conflict_guard"
        stage = "active_action_conflict_guard"
    elif not candidate_action:
        owner = "baseline_score"
        rejected_by = "baseline_no_action"
        stage = "baseline_action_selection"
    elif _is_broker_failure(blocked_by):
        owner = "broker"
        rejected_by = "broker_order_send"
        stage = "broker_execution"
        execution_owner = "broker"
    elif _is_utility_veto(record, blocked_by):
        owner = "utility_gate"
        rejected_by = "utility_gate"
        stage = "utility_gate"
    elif blocked_by == "dynamic_threshold_not_met":
        owner = "semantic_threshold_guard" if threshold_owner == "semantic_threshold_guard" else "score_threshold_gate"
        rejected_by = owner
        stage = "score_threshold_gate"
    elif blocked_by == "stage_min_prob_not_met":
        owner = "score_threshold_gate"
        rejected_by = "stage_min_prob_gate"
        stage = "score_threshold_gate"
    else:
        pre_entry = _resolve_pre_entry_rejected_by(record, blocked_by)
        post_entry = _resolve_post_entry_rejected_by(record, blocked_by)
        if pre_entry:
            owner = "pre_entry_guard"
            rejected_by = pre_entry
            stage = "pre_entry_guard"
        elif post_entry:
            owner = "post_entry_guard"
            rejected_by = post_entry
            stage = "post_entry_guard"
        elif blocked_by:
            owner = "pre_entry_guard"
            rejected_by = "unknown_blocker"
            stage = "pre_entry_guard"

    reason_summary = _to_text(blocked_by)
    if not reason_summary and rejected_by == "baseline_no_action":
        none_reason = _to_text(record.get("action_none_reason"), _to_text(record.get("core_reason"), "core_not_passed"))
        reason_summary = f"baseline_no_action::{none_reason}"
    if not reason_summary:
        reason_summary = outcome or "unknown"

    return {
        "entry_authority_contract_version": ENTRY_AUTHORITY_TRACE_CONTRACT_VERSION,
        "entry_authority_owner": owner,
        "entry_candidate_action_source": candidate_source,
        "entry_candidate_action": candidate_action,
        "entry_candidate_rejected_by": rejected_by,
        "entry_authority_stage": stage,
        "entry_authority_threshold_owner": threshold_owner,
        "entry_authority_execution_owner": execution_owner,
        "entry_authority_reason_summary": reason_summary,
    }


def build_entry_authority_trace(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    recent_limit: int = 200,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    now = now_kst_dt().isoformat()
    payload = dict(runtime_status or {})
    semantic_live_config = dict(payload.get("semantic_live_config", {}) or {})

    frame = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()
    if not frame.empty and "time" in frame.columns:
        frame["time_sort"] = pd.to_datetime(frame["time"], errors="coerce")
        frame = frame.sort_values(by=["time_sort"], ascending=[False], kind="stable").drop(columns=["time_sort"])
    if not frame.empty:
        frame = frame.head(max(1, int(recent_limit))).copy()
        enriched_rows: list[dict[str, Any]] = []
        for row in frame.to_dict(orient="records"):
            authority_fields = build_entry_authority_fields(row)
            merged = dict(row)
            merged.update(authority_fields)
            enriched_rows.append(merged)
        frame = pd.DataFrame(enriched_rows)

    recent_row_count = int(len(frame))
    entered_count = 0
    skipped_count = 0
    recent_symbols = ""
    recent_authority_owner_counts = "{}"
    recent_candidate_action_source_counts = "{}"
    recent_candidate_rejected_by_counts = "{}"
    recent_authority_stage_counts = "{}"
    recent_threshold_owner_counts = "{}"
    recent_execution_owner_counts = "{}"
    baseline_no_action_count = 0
    semantic_threshold_veto_count = 0
    utility_gate_veto_count = 0
    post_entry_guard_veto_count = 0
    broker_veto_count = 0
    active_action_conflict_guard_count = 0
    semantic_threshold_owner_count = 0

    if not frame.empty:
        entered_count = int(frame.get("outcome", pd.Series(dtype=object)).fillna("").astype(str).str.lower().eq("entered").sum())
        skipped_count = max(0, recent_row_count - entered_count)
        if "symbol" in frame.columns:
            recent_symbols = _stable_join(frame["symbol"])
        recent_authority_owner_counts = _series_json_counts(frame["entry_authority_owner"])
        recent_candidate_action_source_counts = _series_json_counts(frame["entry_candidate_action_source"])
        recent_candidate_rejected_by_counts = _series_json_counts(frame["entry_candidate_rejected_by"])
        recent_authority_stage_counts = _series_json_counts(frame["entry_authority_stage"])
        recent_threshold_owner_counts = _series_json_counts(frame["entry_authority_threshold_owner"])
        recent_execution_owner_counts = _series_json_counts(frame["entry_authority_execution_owner"])
        baseline_no_action_count = int(frame["entry_candidate_rejected_by"].fillna("").astype(str).eq("baseline_no_action").sum())
        semantic_threshold_veto_count = int(frame["entry_candidate_rejected_by"].fillna("").astype(str).eq("semantic_threshold_guard").sum())
        utility_gate_veto_count = int(frame["entry_authority_owner"].fillna("").astype(str).eq("utility_gate").sum())
        post_entry_guard_veto_count = int(frame["entry_authority_owner"].fillna("").astype(str).eq("post_entry_guard").sum())
        broker_veto_count = int(frame["entry_candidate_rejected_by"].fillna("").astype(str).eq("broker_order_send").sum())
        active_action_conflict_guard_count = int(
            frame["entry_authority_owner"].fillna("").astype(str).eq("active_action_conflict_guard").sum()
        )
        semantic_threshold_owner_count = int(frame["entry_authority_threshold_owner"].fillna("").astype(str).eq("semantic_threshold_guard").sum())

    if active_action_conflict_guard_count > 0:
        recommended_next_action = "validate_active_action_conflict_guard_precision"
    elif baseline_no_action_count > 0:
        recommended_next_action = "implement_ai2_baseline_no_action_candidate_bridge"
    elif utility_gate_veto_count > 0:
        recommended_next_action = "implement_ai3_utility_gate_recast"
    elif post_entry_guard_veto_count > 0:
        recommended_next_action = "inspect_post_entry_guard_bridge_design"
    elif broker_veto_count > 0:
        recommended_next_action = "inspect_broker_execution_failures"
    else:
        recommended_next_action = "continue_entry_authority_trace_collection"

    row = {
        "observation_event_id": f"entry_authority_trace::{now}",
        "generated_at": now,
        "runtime_updated_at": _to_text(payload.get("updated_at", ""), ""),
        "rollout_mode": _to_text(semantic_live_config.get("mode", ""), "disabled"),
        "shadow_runtime_state": _to_text(semantic_live_config.get("shadow_runtime_state", ""), ""),
        "recent_row_count": recent_row_count,
        "entered_count": entered_count,
        "skipped_count": skipped_count,
        "recent_symbols": recent_symbols,
        "recent_authority_owner_counts": recent_authority_owner_counts,
        "recent_candidate_action_source_counts": recent_candidate_action_source_counts,
        "recent_candidate_rejected_by_counts": recent_candidate_rejected_by_counts,
        "recent_authority_stage_counts": recent_authority_stage_counts,
        "recent_threshold_owner_counts": recent_threshold_owner_counts,
        "recent_execution_owner_counts": recent_execution_owner_counts,
        "baseline_no_action_count": baseline_no_action_count,
        "semantic_threshold_veto_count": semantic_threshold_veto_count,
        "utility_gate_veto_count": utility_gate_veto_count,
        "post_entry_guard_veto_count": post_entry_guard_veto_count,
        "broker_veto_count": broker_veto_count,
        "active_action_conflict_guard_count": active_action_conflict_guard_count,
        "semantic_threshold_owner_count": semantic_threshold_owner_count,
        "recommended_next_action": recommended_next_action,
    }
    summary = dict(row)
    return pd.DataFrame([row], columns=ENTRY_AUTHORITY_TRACE_COLUMNS), summary


def render_entry_authority_trace_markdown(summary: Mapping[str, Any], frame: pd.DataFrame) -> str:
    row = dict(summary or {})
    lines = [
        "# Entry Authority Trace",
        "",
        f"- generated_at: `{_to_text(row.get('generated_at'))}`",
        f"- rollout_mode: `{_to_text(row.get('rollout_mode'), 'disabled')}`",
        f"- shadow_runtime_state: `{_to_text(row.get('shadow_runtime_state'))}`",
        f"- recent_row_count: `{_to_int(row.get('recent_row_count'))}`",
        f"- entered_count: `{_to_int(row.get('entered_count'))}`",
        f"- skipped_count: `{_to_int(row.get('skipped_count'))}`",
        f"- baseline_no_action_count: `{_to_int(row.get('baseline_no_action_count'))}`",
        f"- utility_gate_veto_count: `{_to_int(row.get('utility_gate_veto_count'))}`",
        f"- semantic_threshold_veto_count: `{_to_int(row.get('semantic_threshold_veto_count'))}`",
        f"- post_entry_guard_veto_count: `{_to_int(row.get('post_entry_guard_veto_count'))}`",
        f"- broker_veto_count: `{_to_int(row.get('broker_veto_count'))}`",
        f"- active_action_conflict_guard_count: `{_to_int(row.get('active_action_conflict_guard_count'))}`",
        f"- semantic_threshold_owner_count: `{_to_int(row.get('semantic_threshold_owner_count'))}`",
        f"- recommended_next_action: `{_to_text(row.get('recommended_next_action'))}`",
        "",
        "## Counts",
        "",
        f"- authority_owner_counts: `{_to_text(row.get('recent_authority_owner_counts'), '{}')}`",
        f"- candidate_action_source_counts: `{_to_text(row.get('recent_candidate_action_source_counts'), '{}')}`",
        f"- candidate_rejected_by_counts: `{_to_text(row.get('recent_candidate_rejected_by_counts'), '{}')}`",
        f"- authority_stage_counts: `{_to_text(row.get('recent_authority_stage_counts'), '{}')}`",
        f"- threshold_owner_counts: `{_to_text(row.get('recent_threshold_owner_counts'), '{}')}`",
        f"- execution_owner_counts: `{_to_text(row.get('recent_execution_owner_counts'), '{}')}`",
    ]
    if not frame.empty:
        lines.extend(
            [
                "",
                "## Symbols",
                "",
                f"- recent_symbols: `{_to_text(row.get('recent_symbols'))}`",
            ]
        )
    return "\n".join(lines) + "\n"
