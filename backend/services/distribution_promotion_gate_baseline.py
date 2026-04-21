"""Distribution-based promotion gate baseline over recent entry candidate rows."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


DISTRIBUTION_PROMOTION_GATE_BASELINE_CONTRACT_VERSION = "distribution_promotion_gate_baseline_v1"

DISTRIBUTION_PROMOTION_GATE_BASELINE_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "symbol",
    "market_family",
    "surface_family",
    "surface_state",
    "scene_cluster",
    "candidate_source",
    "action_hint",
    "current_gate_state",
    "promotion_score",
    "cluster_size",
    "cluster_percentile",
    "market_surface_size",
    "market_surface_percentile",
    "absolute_probe_pass",
    "relative_probe_pass",
    "absolute_enter_pass",
    "relative_enter_pass",
    "combined_gate_state",
    "promotion_gap_note",
    "blocked_by",
    "action_none_reason",
    "observe_reason",
    "setup_id",
    "setup_reason",
]


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


def _to_bool(value: object, default: bool = False) -> bool:
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _series_counts(values: pd.Series) -> dict[str, int]:
    if values.empty:
        return {}
    series = values.fillna("").astype(str).str.strip().replace("", pd.NA).dropna()
    counts = series.value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _pick_candidate_source(row: Mapping[str, Any]) -> str:
    source = _to_text(row.get("entry_candidate_bridge_source"))
    if source:
        return source
    directional_state = _to_text(row.get("countertrend_action_state")).upper()
    if directional_state and directional_state != "DO_NOTHING":
        return "countertrend_candidate"
    breakout_target = _to_text(row.get("breakout_candidate_action_target")).upper()
    breakout_direction = _to_text(row.get("breakout_candidate_direction")).upper()
    if breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"} and breakout_direction in {"UP", "DOWN"}:
        return "breakout_candidate"
    return ""


def _pick_surface_fields(row: Mapping[str, Any], source: str) -> tuple[str, str]:
    source_text = _to_text(source)
    if source_text == "countertrend_candidate":
        family = _to_text(row.get("countertrend_continuation_surface_family"), "follow_through_surface")
        state = _to_text(row.get("countertrend_continuation_surface_state"), "continuation_follow")
        return family, state
    if source_text == "breakout_candidate":
        family = _to_text(row.get("breakout_candidate_surface_family"), "follow_through_surface")
        state = _to_text(row.get("breakout_candidate_surface_state"), "continuation_follow")
        return family, state
    return (
        _to_text(row.get("entry_candidate_surface_family"), "initial_entry_surface"),
        _to_text(row.get("entry_candidate_surface_state"), "timing_better_entry"),
    )


def _pick_action_hint(row: Mapping[str, Any], source: str) -> str:
    source_text = _to_text(source)
    if source_text == "countertrend_candidate":
        action = _to_text(row.get("countertrend_directional_candidate_action")).upper()
        if action in {"BUY", "SELL"}:
            return action
    action = _to_text(row.get("entry_candidate_bridge_action")).upper()
    if action in {"BUY", "SELL"}:
        return action
    breakout_direction = _to_text(row.get("breakout_candidate_direction")).upper()
    if breakout_direction == "UP":
        return "BUY"
    if breakout_direction == "DOWN":
        return "SELL"
    return ""


def _pick_scene_cluster(row: Mapping[str, Any]) -> str:
    setup_id = _to_text(row.get("setup_id"))
    if setup_id:
        return setup_id
    observe_reason = _to_text(row.get("observe_reason"))
    if observe_reason:
        return observe_reason
    setup_reason = _to_text(row.get("setup_reason"))
    if setup_reason:
        return setup_reason
    bridge_source = _to_text(row.get("entry_candidate_bridge_source"))
    if bridge_source:
        return bridge_source
    return "unknown_cluster"


def _pick_current_gate_state(row: Mapping[str, Any]) -> str:
    directional_state = _to_text(row.get("countertrend_action_state")).upper()
    if directional_state:
        return directional_state
    breakout_target = _to_text(row.get("breakout_candidate_action_target")).upper()
    if breakout_target == "WATCH_BREAKOUT":
        return "BREAKOUT_WATCH"
    if breakout_target == "PROBE_BREAKOUT":
        return "BREAKOUT_PROBE"
    if breakout_target == "ENTER_NOW":
        return "BREAKOUT_ENTER"
    if _to_bool(row.get("entry_candidate_bridge_selected")):
        return "CANDIDATE_SELECTED"
    if _to_bool(row.get("entry_candidate_bridge_available")):
        return "CANDIDATE_AVAILABLE"
    return "DO_NOTHING"


def _pick_promotion_score(row: Mapping[str, Any], source: str, action_hint: str) -> float:
    source_text = _to_text(source)
    action_text = _to_text(action_hint).upper()
    candidates: list[float] = []
    entry_conf = _to_float(row.get("entry_candidate_bridge_confidence"))
    breakout_conf = _to_float(row.get("breakout_candidate_confidence"))
    countertrend_conf = _to_float(row.get("countertrend_candidate_confidence"))
    if source_text == "countertrend_candidate":
        candidates.append(countertrend_conf)
        if action_text == "BUY":
            candidates.append(_to_float(row.get("countertrend_directional_up_bias_score")))
            candidates.append(_to_float(row.get("countertrend_pro_up_score")))
            candidates.append(_to_float(row.get("countertrend_anti_short_score")))
        elif action_text == "SELL":
            candidates.append(_to_float(row.get("countertrend_directional_down_bias_score")))
            candidates.append(_to_float(row.get("countertrend_pro_down_score")))
            candidates.append(_to_float(row.get("countertrend_anti_long_score")))
    elif source_text == "breakout_candidate":
        candidates.append(breakout_conf)
    else:
        candidates.append(entry_conf)
    candidates.extend([entry_conf, breakout_conf, countertrend_conf])
    return round(max([value for value in candidates if value > 0.0], default=0.0), 6)


def _row_is_relevant(row: Mapping[str, Any]) -> bool:
    source = _pick_candidate_source(row)
    if not source:
        return False
    return _pick_action_hint(row, source) in {"BUY", "SELL"}


def _gate_rank(state: str) -> int:
    state_text = _to_text(state).upper()
    if state_text in {"UP_ENTER", "DOWN_ENTER", "BREAKOUT_ENTER", "ENTER_ELIGIBLE"}:
        return 3
    if state_text in {"UP_PROBE", "DOWN_PROBE", "BREAKOUT_PROBE", "PROBE_ELIGIBLE"}:
        return 2
    if state_text in {"UP_WATCH", "DOWN_WATCH", "BREAKOUT_WATCH", "WATCH_ONLY"}:
        return 1
    return 0


def _combined_gate_state(
    *,
    score: float,
    cluster_size: int,
    cluster_percentile: float,
    market_surface_size: int,
    market_surface_percentile: float,
    absolute_probe_threshold: float,
    absolute_enter_threshold: float,
    relative_probe_threshold: float,
    relative_enter_threshold: float,
    min_relative_sample_size: int,
) -> tuple[bool, bool, bool, bool, str]:
    absolute_probe_pass = score >= absolute_probe_threshold
    absolute_enter_pass = score >= absolute_enter_threshold
    relative_probe_pass = (
        (cluster_size >= min_relative_sample_size and cluster_percentile >= relative_probe_threshold)
        or (market_surface_size >= min_relative_sample_size and market_surface_percentile >= relative_probe_threshold)
    )
    relative_enter_pass = (
        (cluster_size >= min_relative_sample_size and cluster_percentile >= relative_enter_threshold)
        or (market_surface_size >= min_relative_sample_size and market_surface_percentile >= relative_enter_threshold)
    )
    if absolute_enter_pass and relative_enter_pass:
        return absolute_probe_pass, relative_probe_pass, absolute_enter_pass, relative_enter_pass, "ENTER_ELIGIBLE"
    if absolute_probe_pass and relative_probe_pass:
        return absolute_probe_pass, relative_probe_pass, absolute_enter_pass, relative_enter_pass, "PROBE_ELIGIBLE"
    if absolute_probe_pass:
        return absolute_probe_pass, relative_probe_pass, absolute_enter_pass, relative_enter_pass, "ABSOLUTE_ONLY_HOLD"
    if score > 0.0:
        return absolute_probe_pass, relative_probe_pass, absolute_enter_pass, relative_enter_pass, "WATCH_ONLY"
    return absolute_probe_pass, relative_probe_pass, absolute_enter_pass, relative_enter_pass, "DO_NOTHING"


def build_distribution_promotion_gate_baseline(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    recent_limit: int = 480,
    min_relative_sample_size: int = 3,
    absolute_probe_threshold: float = 0.55,
    absolute_enter_threshold: float = 0.8,
    relative_probe_threshold: float = 0.7,
    relative_enter_threshold: float = 0.9,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    frame = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()
    summary: dict[str, Any] = {
        "contract_version": DISTRIBUTION_PROMOTION_GATE_BASELINE_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "recent_row_count": 0,
        "relevant_row_count": 0,
        "cluster_count": 0,
        "symbol_counts": "{}",
        "surface_counts": "{}",
        "source_counts": "{}",
        "combined_gate_state_counts": "{}",
        "promotion_gap_note_counts": "{}",
        "underfired_row_count": 0,
        "overfired_row_count": 0,
        "relative_sample_small_row_count": 0,
        "recommended_next_action": "collect_more_distribution_rows",
    }
    if frame.empty:
        return pd.DataFrame(columns=DISTRIBUTION_PROMOTION_GATE_BASELINE_COLUMNS), summary

    decisions = frame.copy()
    for column in (
        "time",
        "symbol",
        "setup_id",
        "setup_reason",
        "observe_reason",
        "blocked_by",
        "action_none_reason",
        "entry_candidate_bridge_source",
        "entry_candidate_bridge_action",
        "entry_candidate_bridge_confidence",
        "entry_candidate_bridge_selected",
        "entry_candidate_bridge_available",
        "entry_candidate_surface_family",
        "entry_candidate_surface_state",
        "breakout_candidate_action_target",
        "breakout_candidate_direction",
        "breakout_candidate_confidence",
        "breakout_candidate_surface_family",
        "breakout_candidate_surface_state",
        "countertrend_action_state",
        "countertrend_directional_candidate_action",
        "countertrend_directional_execution_action",
        "countertrend_directional_up_bias_score",
        "countertrend_directional_down_bias_score",
        "countertrend_candidate_confidence",
        "countertrend_pro_up_score",
        "countertrend_pro_down_score",
        "countertrend_anti_long_score",
        "countertrend_anti_short_score",
        "countertrend_continuation_surface_family",
        "countertrend_continuation_surface_state",
    ):
        if column not in decisions.columns:
            decisions[column] = ""

    decisions["__time_sort"] = pd.to_datetime(decisions["time"], errors="coerce")
    decisions = decisions.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    recent = decisions.head(max(1, int(recent_limit))).copy()
    summary["recent_row_count"] = int(len(recent))

    enriched_rows: list[dict[str, Any]] = []
    for _, raw_row in recent.iterrows():
        row = raw_row.to_dict()
        if not _row_is_relevant(row):
            continue
        source = _pick_candidate_source(row)
        action_hint = _pick_action_hint(row, source)
        surface_family, surface_state = _pick_surface_fields(row, source)
        enriched_rows.append(
            {
                "time": _to_text(row.get("time")),
                "symbol": _to_text(row.get("symbol")).upper(),
                "market_family": _to_text(row.get("symbol")).upper(),
                "surface_family": surface_family,
                "surface_state": surface_state,
                "scene_cluster": _pick_scene_cluster(row),
                "candidate_source": source,
                "action_hint": action_hint,
                "current_gate_state": _pick_current_gate_state(row),
                "promotion_score": _pick_promotion_score(row, source, action_hint),
                "blocked_by": _to_text(row.get("blocked_by")),
                "action_none_reason": _to_text(row.get("action_none_reason")),
                "observe_reason": _to_text(row.get("observe_reason")),
                "setup_id": _to_text(row.get("setup_id")),
                "setup_reason": _to_text(row.get("setup_reason")),
            }
        )

    relevant = pd.DataFrame(enriched_rows)
    summary["relevant_row_count"] = int(len(relevant))
    if relevant.empty:
        return pd.DataFrame(columns=DISTRIBUTION_PROMOTION_GATE_BASELINE_COLUMNS), summary

    relevant["cluster_key"] = (
        relevant["market_family"].fillna("").astype(str)
        + "::"
        + relevant["surface_family"].fillna("").astype(str)
        + "::"
        + relevant["scene_cluster"].fillna("").astype(str)
        + "::"
        + relevant["action_hint"].fillna("").astype(str)
    )
    relevant["market_surface_key"] = (
        relevant["market_family"].fillna("").astype(str)
        + "::"
        + relevant["surface_family"].fillna("").astype(str)
        + "::"
        + relevant["action_hint"].fillna("").astype(str)
    )
    relevant["cluster_size"] = relevant.groupby("cluster_key")["promotion_score"].transform("size").astype(int)
    relevant["market_surface_size"] = relevant.groupby("market_surface_key")["promotion_score"].transform("size").astype(int)
    relevant["cluster_percentile"] = relevant.groupby("cluster_key")["promotion_score"].rank(method="average", pct=True).astype(float)
    relevant["market_surface_percentile"] = relevant.groupby("market_surface_key")["promotion_score"].rank(method="average", pct=True).astype(float)

    absolute_probe_list: list[bool] = []
    relative_probe_list: list[bool] = []
    absolute_enter_list: list[bool] = []
    relative_enter_list: list[bool] = []
    combined_state_list: list[str] = []
    gap_note_list: list[str] = []

    for _, row in relevant.iterrows():
        absolute_probe_pass, relative_probe_pass, absolute_enter_pass, relative_enter_pass, combined_gate_state = _combined_gate_state(
            score=_to_float(row.get("promotion_score")),
            cluster_size=int(row.get("cluster_size") or 0),
            cluster_percentile=_to_float(row.get("cluster_percentile")),
            market_surface_size=int(row.get("market_surface_size") or 0),
            market_surface_percentile=_to_float(row.get("market_surface_percentile")),
            absolute_probe_threshold=absolute_probe_threshold,
            absolute_enter_threshold=absolute_enter_threshold,
            relative_probe_threshold=relative_probe_threshold,
            relative_enter_threshold=relative_enter_threshold,
            min_relative_sample_size=min_relative_sample_size,
        )
        current_rank = _gate_rank(_to_text(row.get("current_gate_state")))
        combined_rank = _gate_rank(combined_gate_state)
        cluster_small = int(row.get("cluster_size") or 0) < min_relative_sample_size
        market_small = int(row.get("market_surface_size") or 0) < min_relative_sample_size
        if combined_rank > current_rank:
            note = "underfired_vs_distribution"
        elif combined_rank < current_rank:
            note = "overfired_vs_distribution"
        elif cluster_small and market_small:
            note = "relative_sample_small"
        else:
            note = "aligned_with_distribution"
        absolute_probe_list.append(bool(absolute_probe_pass))
        relative_probe_list.append(bool(relative_probe_pass))
        absolute_enter_list.append(bool(absolute_enter_pass))
        relative_enter_list.append(bool(relative_enter_pass))
        combined_state_list.append(combined_gate_state)
        gap_note_list.append(note)

    relevant["absolute_probe_pass"] = absolute_probe_list
    relevant["relative_probe_pass"] = relative_probe_list
    relevant["absolute_enter_pass"] = absolute_enter_list
    relevant["relative_enter_pass"] = relative_enter_list
    relevant["combined_gate_state"] = combined_state_list
    relevant["promotion_gap_note"] = gap_note_list

    rows: list[dict[str, Any]] = []
    for _, row in relevant.iterrows():
        rows.append(
            {
                "observation_event_id": f"{DISTRIBUTION_PROMOTION_GATE_BASELINE_CONTRACT_VERSION}:{_to_text(row.get('market_family'))}:{_to_text(row.get('time')).replace(':', '').replace('-', '')}",
                "generated_at": generated_at,
                "runtime_updated_at": _to_text(runtime.get("updated_at")),
                "symbol": _to_text(row.get("symbol")),
                "market_family": _to_text(row.get("market_family")),
                "surface_family": _to_text(row.get("surface_family")),
                "surface_state": _to_text(row.get("surface_state")),
                "scene_cluster": _to_text(row.get("scene_cluster")),
                "candidate_source": _to_text(row.get("candidate_source")),
                "action_hint": _to_text(row.get("action_hint")).upper(),
                "current_gate_state": _to_text(row.get("current_gate_state")),
                "promotion_score": round(_to_float(row.get("promotion_score")), 6),
                "cluster_size": int(row.get("cluster_size") or 0),
                "cluster_percentile": round(_to_float(row.get("cluster_percentile")), 6),
                "market_surface_size": int(row.get("market_surface_size") or 0),
                "market_surface_percentile": round(_to_float(row.get("market_surface_percentile")), 6),
                "absolute_probe_pass": bool(row.get("absolute_probe_pass")),
                "relative_probe_pass": bool(row.get("relative_probe_pass")),
                "absolute_enter_pass": bool(row.get("absolute_enter_pass")),
                "relative_enter_pass": bool(row.get("relative_enter_pass")),
                "combined_gate_state": _to_text(row.get("combined_gate_state")),
                "promotion_gap_note": _to_text(row.get("promotion_gap_note")),
                "blocked_by": _to_text(row.get("blocked_by")),
                "action_none_reason": _to_text(row.get("action_none_reason")),
                "observe_reason": _to_text(row.get("observe_reason")),
                "setup_id": _to_text(row.get("setup_id")),
                "setup_reason": _to_text(row.get("setup_reason")),
            }
        )

    output = pd.DataFrame(rows, columns=DISTRIBUTION_PROMOTION_GATE_BASELINE_COLUMNS)
    summary["cluster_count"] = int(relevant["cluster_key"].nunique())
    summary["symbol_counts"] = _json_counts(_series_counts(output["symbol"]))
    summary["surface_counts"] = _json_counts(_series_counts(output["surface_family"]))
    summary["source_counts"] = _json_counts(_series_counts(output["candidate_source"]))
    summary["combined_gate_state_counts"] = _json_counts(_series_counts(output["combined_gate_state"]))
    summary["promotion_gap_note_counts"] = _json_counts(_series_counts(output["promotion_gap_note"]))
    summary["underfired_row_count"] = int((output["promotion_gap_note"] == "underfired_vs_distribution").sum())
    summary["overfired_row_count"] = int((output["promotion_gap_note"] == "overfired_vs_distribution").sum())
    summary["relative_sample_small_row_count"] = int((output["promotion_gap_note"] == "relative_sample_small").sum())
    if summary["underfired_row_count"] > max(2, summary["overfired_row_count"]):
        summary["recommended_next_action"] = "inspect_distribution_gate_underfire_clusters"
    elif summary["overfired_row_count"] > max(2, summary["underfired_row_count"]):
        summary["recommended_next_action"] = "inspect_distribution_gate_overfire_clusters"
    elif summary["relative_sample_small_row_count"] >= max(3, int(len(output) * 0.5)):
        summary["recommended_next_action"] = "collect_more_cluster_samples_before_live_gate"
    else:
        summary["recommended_next_action"] = "proceed_to_market_adapter_layer"
    return output, summary


def render_distribution_promotion_gate_baseline_markdown(
    summary: Mapping[str, Any] | None,
    frame: pd.DataFrame | None,
) -> str:
    payload = dict(summary or {})
    rows = frame.copy() if frame is not None and not frame.empty else pd.DataFrame()
    lines = [
        "# Distribution-Based Promotion Gate Baseline",
        "",
        f"- generated_at: `{_to_text(payload.get('generated_at'))}`",
        f"- runtime_updated_at: `{_to_text(payload.get('runtime_updated_at'))}`",
        f"- recent_row_count: `{int(payload.get('recent_row_count') or 0)}`",
        f"- relevant_row_count: `{int(payload.get('relevant_row_count') or 0)}`",
        f"- cluster_count: `{int(payload.get('cluster_count') or 0)}`",
        f"- underfired_row_count: `{int(payload.get('underfired_row_count') or 0)}`",
        f"- overfired_row_count: `{int(payload.get('overfired_row_count') or 0)}`",
        f"- relative_sample_small_row_count: `{int(payload.get('relative_sample_small_row_count') or 0)}`",
        f"- recommended_next_action: `{_to_text(payload.get('recommended_next_action'))}`",
        "",
        "## Counts",
        "",
        f"- symbol_counts: `{_to_text(payload.get('symbol_counts'), '{}')}`",
        f"- surface_counts: `{_to_text(payload.get('surface_counts'), '{}')}`",
        f"- source_counts: `{_to_text(payload.get('source_counts'), '{}')}`",
        f"- combined_gate_state_counts: `{_to_text(payload.get('combined_gate_state_counts'), '{}')}`",
        f"- promotion_gap_note_counts: `{_to_text(payload.get('promotion_gap_note_counts'), '{}')}`",
    ]
    if rows.empty:
        lines.extend(["", "## Recent Rows", "", "- no relevant rows materialized"])
        return "\n".join(lines) + "\n"
    lines.extend(["", "## Recent Rows", ""])
    for _, row in rows.head(12).iterrows():
        lines.append(
            "- "
            + f"{_to_text(row.get('symbol'))} | "
            + f"`{_to_text(row.get('surface_family'))}/{_to_text(row.get('surface_state'))}` | "
            + f"`{_to_text(row.get('scene_cluster'))}` | "
            + f"action={_to_text(row.get('action_hint')) or 'NONE'} | "
            + f"score={round(_to_float(row.get('promotion_score')), 3)} | "
            + f"cluster_pct={round(_to_float(row.get('cluster_percentile')), 3)} | "
            + f"market_pct={round(_to_float(row.get('market_surface_percentile')), 3)} | "
            + f"combined={_to_text(row.get('combined_gate_state'))} | "
            + f"gap={_to_text(row.get('promotion_gap_note'))}"
        )
    return "\n".join(lines) + "\n"
