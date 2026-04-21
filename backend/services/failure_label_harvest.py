"""Harvest confirmed and candidate failure labels across multi-surface execution."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt
from backend.services.wrong_side_conflict_harvest import (
    build_wrong_side_conflict_failure_rows,
)


FAILURE_LABEL_HARVEST_CONTRACT_VERSION = "failure_label_harvest_v1"

FAILURE_LABEL_HARVEST_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "harvest_strength",
    "harvest_source",
    "source_observation_id",
    "symbol",
    "market_family",
    "surface_label_family",
    "surface_label_state",
    "failure_label",
    "supervision_strength",
    "source_group",
    "source_reason",
    "source_focus",
    "event_time",
    "anchor_time",
    "time_axis_phase",
    "time_since_breakout_minutes",
    "time_since_entry_minutes",
    "bars_in_state",
    "momentum_decay",
    "outcome",
    "blocked_by",
    "action_none_reason",
    "observe_reason",
    "exit_reason",
    "evidence_summary",
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


def _slug_text(value: object) -> str:
    text = re.sub(r"[^0-9A-Za-z]+", "_", _to_text(value).lower())
    return text.strip("_")


def _series_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    series = frame[column].fillna("").astype(str).str.strip()
    series = series.replace("", pd.NA).dropna()
    counts = series.value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(key): int(value) for key, value in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _json_loads_dict(text: object) -> dict[str, Any]:
    raw = _to_text(text)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _payload_summary(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = dict(payload or {})
    summary = raw.get("summary")
    if isinstance(summary, Mapping):
        return dict(summary)
    return raw


def _time_axis_lookup(surface_time_axis_contract: pd.DataFrame | None) -> pd.DataFrame:
    frame = surface_time_axis_contract.copy() if surface_time_axis_contract is not None and not surface_time_axis_contract.empty else pd.DataFrame()
    if frame.empty:
        return frame
    for column in ("episode_id", "symbol", "surface_label_family", "surface_label_state"):
        if column not in frame.columns:
            frame[column] = ""
    keep_columns = [
        "episode_id",
        "symbol",
        "surface_label_family",
        "surface_label_state",
        "time_axis_phase",
        "time_since_breakout_minutes",
        "time_since_entry_minutes",
        "bars_in_state",
        "momentum_decay",
        "anchor_time",
    ]
    frame = frame.loc[:, keep_columns].copy()
    frame["__time_key"] = (
        frame["episode_id"].fillna("").astype(str).str.strip()
        + "::"
        + frame["symbol"].fillna("").astype(str).str.strip()
        + "::"
        + frame["surface_label_family"].fillna("").astype(str).str.strip()
        + "::"
        + frame["surface_label_state"].fillna("").astype(str).str.strip()
    )
    return frame.drop_duplicates("__time_key", keep="first")


def _confirmed_failure_rows(
    check_color_label_formalization: pd.DataFrame | None,
    surface_time_axis_contract: pd.DataFrame | None,
    *,
    generated_at: str,
) -> list[dict[str, Any]]:
    frame = (
        check_color_label_formalization.copy()
        if check_color_label_formalization is not None and not check_color_label_formalization.empty
        else pd.DataFrame()
    )
    if frame.empty or "failure_label" not in frame.columns:
        return []

    failure_frame = frame.loc[frame["failure_label"].fillna("").astype(str).str.strip() != ""].copy()
    if failure_frame.empty:
        return []

    time_lookup = _time_axis_lookup(surface_time_axis_contract)
    if not time_lookup.empty:
        failure_frame["__time_key"] = (
            failure_frame["episode_id"].fillna("").astype(str).str.strip()
            + "::"
            + failure_frame["symbol"].fillna("").astype(str).str.strip()
            + "::"
            + failure_frame["surface_label_family"].fillna("").astype(str).str.strip()
            + "::"
            + failure_frame["surface_label_state"].fillna("").astype(str).str.strip()
        )
        failure_frame = failure_frame.merge(
            time_lookup,
            on="__time_key",
            how="left",
            suffixes=("", "__time"),
        )

    rows: list[dict[str, Any]] = []
    for _, row in failure_frame.iterrows():
        episode_id = _to_text(row.get("episode_id") or row.get("annotation_id"))
        symbol = _to_text(row.get("symbol")).upper()
        failure_label = _to_text(row.get("failure_label"))
        rows.append(
            {
                "observation_event_id": f"{FAILURE_LABEL_HARVEST_CONTRACT_VERSION}:confirmed:{_slug_text(episode_id)}",
                "generated_at": generated_at,
                "harvest_strength": "confirmed",
                "harvest_source": "manual_surface_label",
                "source_observation_id": _to_text(row.get("observation_event_id")),
                "symbol": symbol,
                "market_family": symbol,
                "surface_label_family": _to_text(row.get("surface_label_family")),
                "surface_label_state": _to_text(row.get("surface_label_state")),
                "failure_label": failure_label,
                "supervision_strength": _to_text(row.get("supervision_strength"), "strong"),
                "source_group": _to_text(row.get("source_group")),
                "source_reason": _to_text(row.get("label_reason")),
                "source_focus": "",
                "event_time": _to_text(row.get("anchor_time")),
                "anchor_time": _to_text(row.get("anchor_time__time") or row.get("anchor_time")),
                "time_axis_phase": _to_text(row.get("time_axis_phase")),
                "time_since_breakout_minutes": round(_to_float(row.get("time_since_breakout_minutes")), 6),
                "time_since_entry_minutes": round(_to_float(row.get("time_since_entry_minutes")), 6),
                "bars_in_state": round(_to_float(row.get("bars_in_state")), 6),
                "momentum_decay": round(_to_float(row.get("momentum_decay")), 6),
                "outcome": "",
                "blocked_by": "",
                "action_none_reason": "",
                "observe_reason": "",
                "exit_reason": "",
                "evidence_summary": _to_text(row.get("visual_label_token"))
                + (" | " + _to_text(row.get("label_reason")) if _to_text(row.get("label_reason")) else ""),
            }
        )
    return rows


def _entry_candidate_label(row: pd.Series) -> tuple[str, str]:
    outcome = _to_text(row.get("outcome")).lower()
    if outcome not in {"wait", "skipped"}:
        return ("", "")

    blocked_by = _to_text(row.get("blocked_by")).lower()
    none_reason = _to_text(row.get("action_none_reason")).lower()
    observe_reason = _to_text(row.get("observe_reason")).lower()
    surface_family = _to_text(row.get("entry_candidate_surface_family"))
    surface_state = _to_text(row.get("entry_candidate_surface_state"))
    breakout_surface_family = _to_text(row.get("breakout_candidate_surface_family"))
    breakout_surface_state = _to_text(row.get("breakout_candidate_surface_state"))
    breakout_target = _to_text(row.get("breakout_candidate_action_target")).upper()

    if any(token in observe_reason for token in ("upper_reject", "break_fail", "fake_break", "false_break")):
        return ("false_breakout", "observe_reject_break_family")

    is_follow_through = surface_family == "follow_through_surface" or breakout_surface_family == "follow_through_surface"
    if is_follow_through and (
        none_reason in {"probe_not_promoted", "observe_state_wait", "preflight_blocked"}
        or blocked_by in {"outer_band_guard", "range_lower_buy_requires_lower_edge", "forecast_guard"}
        or breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT"}
        or breakout_surface_state in {"continuation_follow", "pullback_resume"}
    ):
        return ("failed_follow_through", "follow_through_candidate_blocked")

    is_initial = surface_family == "initial_entry_surface"
    if is_initial and (
        surface_state == "late_release"
        or "upper_edge" in observe_reason
        or blocked_by == "dynamic_threshold_not_met"
    ):
        return ("late_entry_chase_fail", "late_release_or_upper_edge_wait")

    if is_initial and surface_state in {"timing_better_entry", "initial_break"} and (
        blocked_by
        or none_reason in {"observe_state_wait", "probe_not_promoted", "preflight_blocked"}
    ):
        return ("missed_good_wait_release", "timing_better_entry_blocked")

    return ("", "")


def _entry_candidate_rows(
    entry_decisions: pd.DataFrame | None,
    market_family_entry_audit: Mapping[str, Any] | None,
    *,
    generated_at: str,
    recent_limit: int,
) -> list[dict[str, Any]]:
    frame = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()
    if frame.empty:
        return []

    summary = _payload_summary(market_family_entry_audit)
    focus_map = _json_loads_dict(summary.get("symbol_focus_map"))

    for column in (
        "time",
        "symbol",
        "outcome",
        "blocked_by",
        "action_none_reason",
        "observe_reason",
        "entry_candidate_surface_family",
        "entry_candidate_surface_state",
        "breakout_candidate_action_target",
        "breakout_candidate_surface_family",
        "breakout_candidate_surface_state",
    ):
        if column not in frame.columns:
            frame[column] = ""

    scoped = frame.tail(max(1, int(recent_limit))).copy()
    rows: list[dict[str, Any]] = []
    for _, row in scoped.iterrows():
        failure_label, source_reason = _entry_candidate_label(row)
        if not failure_label:
            continue
        symbol = _to_text(row.get("symbol")).upper()
        surface_label_family = _to_text(row.get("entry_candidate_surface_family"))
        surface_label_state = _to_text(row.get("entry_candidate_surface_state"))
        if not surface_label_family:
            surface_label_family = _to_text(row.get("breakout_candidate_surface_family"))
        if not surface_label_state:
            surface_label_state = _to_text(row.get("breakout_candidate_surface_state"))
        if not surface_label_family:
            surface_label_family = {
                "failed_follow_through": "follow_through_surface",
                "false_breakout": "initial_entry_surface",
                "late_entry_chase_fail": "initial_entry_surface",
                "missed_good_wait_release": "initial_entry_surface",
            }.get(failure_label, "")
        if not surface_label_state:
            surface_label_state = {
                "failed_follow_through": "continuation_follow",
                "false_breakout": "initial_break",
                "late_entry_chase_fail": "late_release",
                "missed_good_wait_release": "timing_better_entry",
            }.get(failure_label, "")
        evidence_tokens = [
            _to_text(row.get("blocked_by")),
            _to_text(row.get("action_none_reason")),
            _to_text(row.get("observe_reason")),
            _to_text(row.get("breakout_candidate_action_target")),
        ]
        evidence_summary = " | ".join(token for token in evidence_tokens if token)
        event_time = _to_text(row.get("time"))
        rows.append(
            {
                "observation_event_id": (
                    f"{FAILURE_LABEL_HARVEST_CONTRACT_VERSION}:entry:{_slug_text(symbol)}:{_slug_text(event_time)}:{failure_label}"
                ),
                "generated_at": generated_at,
                "harvest_strength": "candidate",
                "harvest_source": "runtime_entry_blocker",
                "source_observation_id": "",
                "symbol": symbol,
                "market_family": symbol,
                "surface_label_family": surface_label_family,
                "surface_label_state": surface_label_state,
                "failure_label": failure_label,
                "supervision_strength": "candidate",
                "source_group": "runtime_entry",
                "source_reason": source_reason,
                "source_focus": _to_text(focus_map.get(symbol)),
                "event_time": event_time,
                "anchor_time": "",
                "time_axis_phase": "",
                "time_since_breakout_minutes": 0.0,
                "time_since_entry_minutes": 0.0,
                "bars_in_state": 0.0,
                "momentum_decay": 0.0,
                "outcome": _to_text(row.get("outcome")),
                "blocked_by": _to_text(row.get("blocked_by")),
                "action_none_reason": _to_text(row.get("action_none_reason")),
                "observe_reason": _to_text(row.get("observe_reason")),
                "exit_reason": "",
                "evidence_summary": evidence_summary,
            }
        )
    return rows


def _wrong_side_conflict_rows(
    entry_decisions: pd.DataFrame | None,
    market_family_entry_audit: Mapping[str, Any] | None,
    *,
    generated_at: str,
    recent_limit: int,
) -> list[dict[str, Any]]:
    summary = _payload_summary(market_family_entry_audit)
    focus_map = _json_loads_dict(summary.get("symbol_focus_map"))
    return build_wrong_side_conflict_failure_rows(
        entry_decisions,
        generated_at=generated_at,
        recent_limit=recent_limit,
        focus_map=focus_map,
    )


def _exit_candidate_rows(
    market_family_exit_audit: Mapping[str, Any] | None,
    exit_surface_observation: Mapping[str, Any] | None,
    *,
    generated_at: str,
) -> list[dict[str, Any]]:
    exit_summary = _payload_summary(market_family_exit_audit)
    focus_map = _json_loads_dict(exit_summary.get("symbol_focus_map"))
    exit_reason_counts = _json_loads_dict(exit_summary.get("symbol_auto_exit_reason_counts"))
    observation = dict(exit_surface_observation or {})

    rows: list[dict[str, Any]] = []
    for symbol, focus in focus_map.items():
        symbol_text = _to_text(symbol).upper()
        focus_text = _to_text(focus)
        focus_lower = focus_text.lower()
        reason_counts = dict(exit_reason_counts.get(symbol_text) or exit_reason_counts.get(symbol) or {})
        if not reason_counts:
            continue

        harvest = False
        surface_family = ""
        surface_state = ""
        if "runner_preservation" in focus_lower:
            harvest = any("target" in _to_text(reason).lower() or "lock exit" in _to_text(reason).lower() for reason in reason_counts)
            surface_family = "continuation_hold_surface"
            surface_state = "runner_hold"
        elif "protective_exit_overfire" in focus_lower:
            harvest = any("protect exit" in _to_text(reason).lower() for reason in reason_counts)
            surface_family = "protective_exit_surface"
            surface_state = "protect_exit"

        if not harvest:
            continue

        top_reasons = sorted(reason_counts.items(), key=lambda item: int(item[1]), reverse=True)[:3]
        evidence_summary = json.dumps({str(key): int(value) for key, value in top_reasons}, ensure_ascii=False, sort_keys=True)
        rows.append(
            {
                "observation_event_id": f"{FAILURE_LABEL_HARVEST_CONTRACT_VERSION}:exit:{_slug_text(symbol_text)}:early_exit_regret",
                "generated_at": generated_at,
                "harvest_strength": "candidate",
                "harvest_source": "exit_focus_summary",
                "source_observation_id": "",
                "symbol": symbol_text,
                "market_family": symbol_text,
                "surface_label_family": surface_family,
                "surface_label_state": surface_state,
                "failure_label": "early_exit_regret",
                "supervision_strength": "candidate",
                "source_group": "runtime_exit",
                "source_reason": "market_family_exit_focus",
                "source_focus": focus_text,
                "event_time": _to_text(exit_summary.get("generated_at")),
                "anchor_time": "",
                "time_axis_phase": _to_text(observation.get("status")),
                "time_since_breakout_minutes": 0.0,
                "time_since_entry_minutes": 0.0,
                "bars_in_state": 0.0,
                "momentum_decay": 0.0,
                "outcome": "",
                "blocked_by": "",
                "action_none_reason": "",
                "observe_reason": "",
                "exit_reason": _to_text(top_reasons[0][0]) if top_reasons else "",
                "evidence_summary": evidence_summary,
            }
        )
    return rows


def build_failure_label_harvest(
    check_color_label_formalization: pd.DataFrame | None,
    surface_time_axis_contract: pd.DataFrame | None,
    entry_decisions: pd.DataFrame | None,
    market_family_entry_audit: Mapping[str, Any] | None,
    market_family_exit_audit: Mapping[str, Any] | None,
    exit_surface_observation: Mapping[str, Any] | None,
    *,
    recent_entry_limit: int = 240,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()

    rows: list[dict[str, Any]] = []
    rows.extend(
        _confirmed_failure_rows(
            check_color_label_formalization,
            surface_time_axis_contract,
            generated_at=generated_at,
        )
    )
    rows.extend(
        _entry_candidate_rows(
            entry_decisions,
            market_family_entry_audit,
            generated_at=generated_at,
            recent_limit=recent_entry_limit,
        )
    )
    rows.extend(
        _wrong_side_conflict_rows(
            entry_decisions,
            market_family_entry_audit,
            generated_at=generated_at,
            recent_limit=recent_entry_limit,
        )
    )
    rows.extend(
        _exit_candidate_rows(
            market_family_exit_audit,
            exit_surface_observation,
            generated_at=generated_at,
        )
    )

    frame = pd.DataFrame(rows, columns=FAILURE_LABEL_HARVEST_COLUMNS)
    if frame.empty:
        summary = {
            "contract_version": FAILURE_LABEL_HARVEST_CONTRACT_VERSION,
            "generated_at": generated_at,
            "row_count": 0,
            "confirmed_row_count": 0,
            "candidate_row_count": 0,
            "market_family_counts": "{}",
            "surface_label_family_counts": "{}",
            "failure_label_counts": "{}",
            "harvest_strength_counts": "{}",
            "harvest_source_counts": "{}",
            "confirmed_failure_label_counts": "{}",
            "candidate_failure_label_counts": "{}",
            "recommended_next_action": "collect_failure_label_inputs",
        }
        return frame, summary

    confirmed_frame = frame.loc[frame["harvest_strength"] == "confirmed"].copy()
    candidate_frame = frame.loc[frame["harvest_strength"] == "candidate"].copy()
    candidate_failure_counts = _series_counts(candidate_frame, "failure_label")
    top_candidate_label = next(iter(candidate_failure_counts.keys()), "")
    recommended_next_action = {
        "missed_good_wait_release": "implement_mf6_distribution_gate_baseline",
        "failed_follow_through": "extend_mf7_follow_through_bridge",
        "early_exit_regret": "observe_mf11_runner_preservation_and_market_adapter",
        "false_breakout": "implement_mf14_market_adapter_layer",
        "late_entry_chase_fail": "refine_initial_entry_timing_surface",
    }.get(top_candidate_label, "implement_mf6_distribution_gate_baseline")

    summary = {
        "contract_version": FAILURE_LABEL_HARVEST_CONTRACT_VERSION,
        "generated_at": generated_at,
        "row_count": int(len(frame)),
        "confirmed_row_count": int(len(confirmed_frame)),
        "candidate_row_count": int(len(candidate_frame)),
        "market_family_counts": _json_counts(_series_counts(frame, "market_family")),
        "surface_label_family_counts": _json_counts(_series_counts(frame, "surface_label_family")),
        "failure_label_counts": _json_counts(_series_counts(frame, "failure_label")),
        "harvest_strength_counts": _json_counts(_series_counts(frame, "harvest_strength")),
        "harvest_source_counts": _json_counts(_series_counts(frame, "harvest_source")),
        "confirmed_failure_label_counts": _json_counts(_series_counts(confirmed_frame, "failure_label")),
        "candidate_failure_label_counts": _json_counts(candidate_failure_counts),
        "recommended_next_action": recommended_next_action,
    }
    return frame, summary


def render_failure_label_harvest_markdown(summary: dict[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Failure Label Harvest",
        "",
        f"- generated_at: `{_to_text(summary.get('generated_at'))}`",
        f"- row_count: `{int(summary.get('row_count', 0) or 0)}`",
        f"- confirmed_row_count: `{int(summary.get('confirmed_row_count', 0) or 0)}`",
        f"- candidate_row_count: `{int(summary.get('candidate_row_count', 0) or 0)}`",
        f"- failure_label_counts: `{_to_text(summary.get('failure_label_counts'), '{}')}`",
        f"- harvest_strength_counts: `{_to_text(summary.get('harvest_strength_counts'), '{}')}`",
        f"- harvest_source_counts: `{_to_text(summary.get('harvest_source_counts'), '{}')}`",
        f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`",
        "",
        "## Preview",
        "",
    ]
    if frame.empty:
        lines.append("- no rows")
        return "\n".join(lines)

    preview_columns = [
        "harvest_strength",
        "harvest_source",
        "symbol",
        "surface_label_family",
        "surface_label_state",
        "failure_label",
        "source_focus",
        "evidence_summary",
    ]
    preview = frame.loc[:, preview_columns].head(15)
    header = "| " + " | ".join(preview_columns) + " |"
    divider = "| " + " | ".join(["---"] * len(preview_columns)) + " |"
    lines.append(header)
    lines.append(divider)
    for _, row in preview.iterrows():
        values = [_to_text(row.get(column)).replace("|", "/") for column in preview_columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)
