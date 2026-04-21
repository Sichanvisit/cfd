"""AI2 candidate-surface coverage audit over fresh baseline-no-action rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


ENTRY_CANDIDATE_COVERAGE_AUDIT_CONTRACT_VERSION = "entry_candidate_coverage_audit_v1"
ENTRY_CANDIDATE_COVERAGE_AUDIT_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "rollout_mode",
    "recent_row_count",
    "baseline_no_action_row_count",
    "metric_group",
    "metric_value",
    "count",
    "share",
    "recommended_next_action",
]


def load_entry_candidate_coverage_audit_frame(path: str | Path) -> pd.DataFrame:
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
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _stable_join(values: pd.Series) -> str:
    seen: list[str] = []
    for raw in values.fillna("").astype(str):
        text = raw.strip()
        if not text or text in seen:
            continue
        seen.append(text)
    return ",".join(seen)


def _series_counts(values: pd.Series) -> dict[str, int]:
    series = values.fillna("").astype(str).str.strip()
    counts = (
        series.replace("", pd.NA)
        .dropna()
        .value_counts()
        .to_dict()
    )
    return {str(key): int(value) for key, value in counts.items()}


def _series_json_counts(values: pd.Series) -> str:
    counts = _series_counts(values)
    return json.dumps(counts, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _availability_mask(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([False] * len(frame), index=frame.index)
    return frame[column].fillna("").astype(str).str.strip().isin({"BUY", "SELL"})


def _normalize_bool_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame.columns:
        return {}
    values = frame[column].map(lambda value: "true" if _to_bool(value) else "false")
    return _series_counts(values)


def _append_metric_rows(
    rows: list[dict[str, Any]],
    *,
    base_payload: Mapping[str, Any],
    metric_group: str,
    counts: Mapping[str, int],
    denominator: int,
) -> None:
    total = max(1, int(denominator))
    for metric_value, count in counts.items():
        rows.append(
            {
                **dict(base_payload),
                "metric_group": metric_group,
                "metric_value": _to_text(metric_value),
                "count": int(count),
                "share": round(float(count) / float(total), 6),
            }
        )


def build_entry_candidate_coverage_audit(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    recent_limit: int = 200,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    semantic_live_config = dict(runtime.get("semantic_live_config", {}) or {})
    decisions = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()

    summary: dict[str, Any] = {
        "contract_version": ENTRY_CANDIDATE_COVERAGE_AUDIT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "rollout_mode": _to_text(semantic_live_config.get("mode"), "disabled"),
        "recent_row_count": 0,
        "baseline_no_action_row_count": 0,
        "bridge_available_count": 0,
        "bridge_selected_count": 0,
        "all_candidate_blank_count": 0,
        "semantic_candidate_available_count": 0,
        "shadow_candidate_available_count": 0,
        "state25_candidate_available_count": 0,
        "breakout_candidate_available_count": 0,
        "breakout_enter_now_count": 0,
        "breakout_wait_more_count": 0,
        "breakout_direction_none_count": 0,
        "breakout_direction_up_count": 0,
        "breakout_direction_down_count": 0,
        "recent_symbols": "",
        "bridge_source_counts": "{}",
        "breakout_action_target_counts": "{}",
        "breakout_direction_counts": "{}",
        "action_none_reason_counts": "{}",
        "blocked_by_counts": "{}",
        "core_reason_counts": "{}",
        "state25_binding_mode_counts": "{}",
        "state25_threshold_symbol_scope_hit_counts": "{}",
        "state25_threshold_stage_scope_hit_counts": "{}",
        "recommended_next_action": "collect_ai2_fresh_rows",
    }

    if decisions.empty:
        return pd.DataFrame(columns=ENTRY_CANDIDATE_COVERAGE_AUDIT_COLUMNS), summary

    decisions = decisions.copy()
    for column in (
        "time",
        "symbol",
        "action",
        "entry_authority_rejected_by",
        "entry_candidate_bridge_baseline_no_action",
        "entry_candidate_bridge_available",
        "entry_candidate_bridge_selected",
        "entry_candidate_bridge_source",
        "semantic_candidate_action",
        "shadow_candidate_action",
        "state25_candidate_action",
        "breakout_candidate_action",
        "breakout_candidate_action_target",
        "breakout_candidate_direction",
        "core_reason",
        "action_none_reason",
        "blocked_by",
        "state25_candidate_binding_mode",
        "state25_candidate_threshold_symbol_scope_hit",
        "state25_candidate_threshold_stage_scope_hit",
    ):
        if column not in decisions.columns:
            decisions[column] = ""

    decisions["__time_sort"] = pd.to_datetime(decisions["time"], errors="coerce")
    decisions = decisions.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    recent = decisions.head(max(1, int(recent_limit))).copy()

    baseline_mask = (
        recent["entry_authority_rejected_by"].fillna("").astype(str).str.strip() == "baseline_no_action"
    )
    if not baseline_mask.any():
        baseline_mask = recent["entry_candidate_bridge_baseline_no_action"].fillna(False).astype(bool)
    if not baseline_mask.any():
        baseline_mask = recent["action"].fillna("").astype(str).str.strip().eq("")
    baseline = recent.loc[baseline_mask].copy()

    summary["recent_row_count"] = int(len(recent))
    summary["baseline_no_action_row_count"] = int(len(baseline))
    if baseline.empty:
        summary["recommended_next_action"] = "retain_ai2_observation_window"
        return pd.DataFrame(columns=ENTRY_CANDIDATE_COVERAGE_AUDIT_COLUMNS), summary

    bridge_available_mask = baseline["entry_candidate_bridge_available"].fillna(False).astype(bool)
    bridge_selected_mask = baseline["entry_candidate_bridge_selected"].fillna(False).astype(bool)
    semantic_available_mask = _availability_mask(baseline, "semantic_candidate_action")
    shadow_available_mask = _availability_mask(baseline, "shadow_candidate_action")
    state25_available_mask = _availability_mask(baseline, "state25_candidate_action")
    breakout_available_mask = _availability_mask(baseline, "breakout_candidate_action")
    all_blank_mask = ~(semantic_available_mask | shadow_available_mask | state25_available_mask | breakout_available_mask)

    breakout_targets = baseline["breakout_candidate_action_target"].fillna("").astype(str).str.strip().replace("", "NONE")
    breakout_directions = baseline["breakout_candidate_direction"].fillna("").astype(str).str.strip().replace("", "NONE")

    summary.update(
        {
            "bridge_available_count": int(bridge_available_mask.sum()),
            "bridge_selected_count": int(bridge_selected_mask.sum()),
            "all_candidate_blank_count": int(all_blank_mask.sum()),
            "semantic_candidate_available_count": int(semantic_available_mask.sum()),
            "shadow_candidate_available_count": int(shadow_available_mask.sum()),
            "state25_candidate_available_count": int(state25_available_mask.sum()),
            "breakout_candidate_available_count": int(breakout_available_mask.sum()),
            "breakout_enter_now_count": int(breakout_targets.eq("ENTER_NOW").sum()),
            "breakout_wait_more_count": int(breakout_targets.eq("WAIT_MORE").sum()),
            "breakout_direction_none_count": int(breakout_directions.eq("NONE").sum()),
            "breakout_direction_up_count": int(breakout_directions.eq("UP").sum()),
            "breakout_direction_down_count": int(breakout_directions.eq("DOWN").sum()),
            "recent_symbols": _stable_join(baseline["symbol"]),
            "bridge_source_counts": _series_json_counts(baseline["entry_candidate_bridge_source"]),
            "breakout_action_target_counts": _series_json_counts(breakout_targets),
            "breakout_direction_counts": _series_json_counts(breakout_directions),
            "action_none_reason_counts": _series_json_counts(baseline["action_none_reason"]),
            "blocked_by_counts": _series_json_counts(baseline["blocked_by"]),
            "core_reason_counts": _series_json_counts(baseline["core_reason"]),
            "state25_binding_mode_counts": _series_json_counts(baseline["state25_candidate_binding_mode"]),
            "state25_threshold_symbol_scope_hit_counts": json.dumps(
                _normalize_bool_counts(baseline, "state25_candidate_threshold_symbol_scope_hit"),
                ensure_ascii=False,
                sort_keys=True,
            )
            if len(baseline)
            else "{}",
            "state25_threshold_stage_scope_hit_counts": json.dumps(
                _normalize_bool_counts(baseline, "state25_candidate_threshold_stage_scope_hit"),
                ensure_ascii=False,
                sort_keys=True,
            )
            if len(baseline)
            else "{}",
        }
    )

    if summary["breakout_candidate_available_count"] > 0:
        recommended_next_action = "inspect_breakout_candidate_selection_distribution"
    elif summary["breakout_enter_now_count"] == 0 and summary["breakout_wait_more_count"] > 0:
        recommended_next_action = "inspect_breakout_runtime_thresholds_and_scene_sensitivity"
    elif summary["all_candidate_blank_count"] == len(baseline):
        recommended_next_action = "widen_ai2_candidate_surface_or_add_source_specific_bridges"
    elif summary["state25_candidate_available_count"] == 0 and summary["shadow_candidate_available_count"] == 0:
        recommended_next_action = "retain_observation_window_and_compare_candidate_blockers"
    else:
        recommended_next_action = "continue_ai2_observation_window"
    summary["recommended_next_action"] = recommended_next_action

    base_payload = {
        "observation_event_id": "entry_candidate_coverage_audit::latest",
        "generated_at": generated_at,
        "runtime_updated_at": summary["runtime_updated_at"],
        "rollout_mode": summary["rollout_mode"],
        "recent_row_count": summary["recent_row_count"],
        "baseline_no_action_row_count": summary["baseline_no_action_row_count"],
        "recommended_next_action": summary["recommended_next_action"],
    }
    rows: list[dict[str, Any]] = []
    denominator = int(len(baseline))

    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="bridge_source",
        counts=_series_counts(baseline["entry_candidate_bridge_source"]),
        denominator=denominator,
    )
    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="breakout_action_target",
        counts=_series_counts(breakout_targets),
        denominator=denominator,
    )
    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="breakout_direction",
        counts=_series_counts(breakout_directions),
        denominator=denominator,
    )
    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="action_none_reason",
        counts=_series_counts(baseline["action_none_reason"]),
        denominator=denominator,
    )
    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="blocked_by",
        counts=_series_counts(baseline["blocked_by"]),
        denominator=denominator,
    )
    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="core_reason",
        counts=_series_counts(baseline["core_reason"]),
        denominator=denominator,
    )
    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="state25_binding_mode",
        counts=_series_counts(baseline["state25_candidate_binding_mode"]),
        denominator=denominator,
    )
    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="state25_threshold_symbol_scope_hit",
        counts=_normalize_bool_counts(baseline, "state25_candidate_threshold_symbol_scope_hit"),
        denominator=denominator,
    )
    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="state25_threshold_stage_scope_hit",
        counts=_normalize_bool_counts(baseline, "state25_candidate_threshold_stage_scope_hit"),
        denominator=denominator,
    )
    _append_metric_rows(
        rows,
        base_payload=base_payload,
        metric_group="candidate_presence",
        counts={
            "all_blank": int(all_blank_mask.sum()),
            "bridge_available": int(bridge_available_mask.sum()),
            "bridge_selected": int(bridge_selected_mask.sum()),
            "semantic_available": int(semantic_available_mask.sum()),
            "shadow_available": int(shadow_available_mask.sum()),
            "state25_available": int(state25_available_mask.sum()),
            "breakout_available": int(breakout_available_mask.sum()),
        },
        denominator=denominator,
    )

    frame = pd.DataFrame(rows, columns=ENTRY_CANDIDATE_COVERAGE_AUDIT_COLUMNS)
    return frame, summary


def render_entry_candidate_coverage_audit_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> str:
    row = dict(summary or {})
    lines = [
        "# Entry Candidate Coverage Audit",
        "",
        f"- generated_at: `{_to_text(row.get('generated_at'))}`",
        f"- rollout_mode: `{_to_text(row.get('rollout_mode'), 'disabled')}`",
        f"- recent_row_count: `{int(_to_float(row.get('recent_row_count'), 0.0))}`",
        f"- baseline_no_action_row_count: `{int(_to_float(row.get('baseline_no_action_row_count'), 0.0))}`",
        f"- bridge_available_count: `{int(_to_float(row.get('bridge_available_count'), 0.0))}`",
        f"- bridge_selected_count: `{int(_to_float(row.get('bridge_selected_count'), 0.0))}`",
        f"- all_candidate_blank_count: `{int(_to_float(row.get('all_candidate_blank_count'), 0.0))}`",
        f"- breakout_enter_now_count: `{int(_to_float(row.get('breakout_enter_now_count'), 0.0))}`",
        f"- breakout_wait_more_count: `{int(_to_float(row.get('breakout_wait_more_count'), 0.0))}`",
        f"- breakout_direction_none_count: `{int(_to_float(row.get('breakout_direction_none_count'), 0.0))}`",
        f"- recommended_next_action: `{_to_text(row.get('recommended_next_action'))}`",
        "",
        "## Distributions",
        "",
        f"- bridge_source_counts: `{_to_text(row.get('bridge_source_counts'), '{}')}`",
        f"- breakout_action_target_counts: `{_to_text(row.get('breakout_action_target_counts'), '{}')}`",
        f"- breakout_direction_counts: `{_to_text(row.get('breakout_direction_counts'), '{}')}`",
        f"- action_none_reason_counts: `{_to_text(row.get('action_none_reason_counts'), '{}')}`",
        f"- blocked_by_counts: `{_to_text(row.get('blocked_by_counts'), '{}')}`",
        f"- core_reason_counts: `{_to_text(row.get('core_reason_counts'), '{}')}`",
        f"- state25_binding_mode_counts: `{_to_text(row.get('state25_binding_mode_counts'), '{}')}`",
        f"- state25_threshold_symbol_scope_hit_counts: `{_to_text(row.get('state25_threshold_symbol_scope_hit_counts'), '{}')}`",
        f"- state25_threshold_stage_scope_hit_counts: `{_to_text(row.get('state25_threshold_stage_scope_hit_counts'), '{}')}`",
    ]
    if frame is None or frame.empty:
        lines.extend(["", "_No baseline-no-action coverage rows found._"])
    return "\n".join(lines) + "\n"
