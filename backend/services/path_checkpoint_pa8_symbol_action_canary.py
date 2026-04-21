from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION = "checkpoint_pa8_symbol_action_canary_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_pa8_symbol_action_canary_artifact_path(
    symbol: str,
    artifact_name: str,
    *,
    markdown: bool = False,
) -> Path:
    suffix = ".md" if markdown else ".json"
    return (
        _repo_root()
        / "data"
        / "analysis"
        / "shadow_auto"
        / f"checkpoint_pa8_{str(symbol).lower()}_{artifact_name}_latest{suffix}"
    )


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _symbol_profile(symbol: str) -> dict[str, Any]:
    profiles: dict[str, dict[str, Any]] = {
        "BTCUSD": {
            "preview_slug": "protective_reclaim_wait",
            "surface_name": "protective_exit_surface",
            "checkpoint_type_allowlist": ["RECLAIM_CHECK"],
            "family_allowlist": ["active_open_loss"],
            "baseline_action_allowlist": ["PARTIAL_EXIT"],
            "candidate_action": "WAIT",
            "candidate_reason": "btcusd_protective_reclaim_loss_partial_exit_to_wait_preview",
            "source_allowlist": ["exit_manage_hold"],
            "unrealized_pnl_state_allowlist": ["OPEN_LOSS"],
            "position_side_allowlist": ["SELL"],
            "min_giveback_ratio": 0.95,
            "max_hold_quality": 0.46,
            "max_partial_exit_ev": 0.47,
            "min_continuation_odds": 0.79,
            "max_reversal_odds": 0.72,
            "sample_floor": 50,
            "candidate_action_precision_floor": 0.95,
            "runtime_proxy_match_rate_floor": 0.90,
            "target_metric_goal": "raise scoped WAIT precision and runtime proxy alignment for BTCUSD protective reclaim loss without scene bias changes",
        },
        "XAUUSD": {
            "preview_slug": "protective_reclaim_wait",
            "surface_name": "protective_exit_surface",
            "checkpoint_type_allowlist": ["RECLAIM_CHECK"],
            "family_allowlist": ["open_loss_protective", "active_open_loss"],
            "baseline_action_allowlist": ["PARTIAL_EXIT"],
            "candidate_action": "WAIT",
            "candidate_reason": "xauusd_protective_reclaim_loss_partial_exit_to_wait_preview",
            "source_allowlist": ["exit_manage_hold", "exit_manage_protective"],
            "unrealized_pnl_state_allowlist": ["OPEN_LOSS"],
            "position_side_allowlist": ["BUY"],
            "min_giveback_ratio": 0.95,
            "max_hold_quality": 0.48,
            "max_partial_exit_ev": 0.46,
            "min_continuation_odds": 0.76,
            "max_reversal_odds": 0.75,
            "sample_floor": 25,
            "candidate_action_precision_floor": 0.95,
            "runtime_proxy_match_rate_floor": 0.90,
            "target_metric_goal": "raise scoped WAIT precision and runtime proxy alignment for XAUUSD protective reclaim loss without scene bias changes",
        },
    }
    symbol_upper = _to_text(symbol).upper()
    if symbol_upper not in profiles:
        raise ValueError(f"unsupported symbol profile: {symbol_upper}")
    return {"symbol": symbol_upper, **profiles[symbol_upper]}


def _baseline_action(row: Mapping[str, Any]) -> str:
    return _to_text(row.get("runtime_proxy_management_action_label")).upper()


def _eligible_row(row: Mapping[str, Any], profile: Mapping[str, Any]) -> tuple[bool, str]:
    if _to_text(row.get("symbol")).upper() != _to_text(profile.get("symbol")).upper():
        return False, "preview_symbol_out_of_scope"
    if _to_text(row.get("surface_name")) != _to_text(profile.get("surface_name")):
        return False, "preview_surface_out_of_scope"
    if _to_text(row.get("checkpoint_type")).upper() not in set(profile.get("checkpoint_type_allowlist", []) or []):
        return False, "preview_checkpoint_out_of_scope"
    if _to_text(row.get("checkpoint_rule_family_hint")).lower() not in set(profile.get("family_allowlist", []) or []):
        return False, "preview_family_out_of_scope"
    if _baseline_action(row) not in set(profile.get("baseline_action_allowlist", []) or []):
        return False, "preview_baseline_action_out_of_scope"
    if _to_text(row.get("source")) not in set(profile.get("source_allowlist", []) or []):
        return False, "preview_source_out_of_scope"
    if _to_text(row.get("unrealized_pnl_state")).upper() not in set(profile.get("unrealized_pnl_state_allowlist", []) or []):
        return False, "preview_unrealized_state_out_of_scope"
    if _to_text(row.get("position_side")).upper() not in set(profile.get("position_side_allowlist", []) or []):
        return False, "preview_position_side_out_of_scope"
    if _to_float(row.get("giveback_ratio")) < _to_float(profile.get("min_giveback_ratio")):
        return False, "preview_giveback_too_low"
    if _to_float(row.get("runtime_hold_quality_score")) > _to_float(profile.get("max_hold_quality"), 1.0):
        return False, "preview_hold_quality_too_high"
    if _to_float(row.get("runtime_partial_exit_ev")) > _to_float(profile.get("max_partial_exit_ev"), 1.0):
        return False, "preview_partial_exit_ev_too_high"
    if _to_float(row.get("runtime_continuation_odds")) < _to_float(profile.get("min_continuation_odds")):
        return False, "preview_continuation_not_strong_enough"
    if _to_float(row.get("runtime_reversal_odds")) > _to_float(profile.get("max_reversal_odds"), 1.0):
        return False, "preview_reversal_too_high"
    return True, _to_text(profile.get("candidate_reason"))


def build_checkpoint_pa8_symbol_action_preview(
    resolved_dataset: pd.DataFrame | None,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    profile = _symbol_profile(symbol)
    frame = resolved_dataset.copy() if resolved_dataset is not None and not resolved_dataset.empty else pd.DataFrame()
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
        "generated_at": _now(),
        "symbol": profile["symbol"],
        "preview_slug": profile["preview_slug"],
        "candidate_action": profile["candidate_action"],
        "resolved_row_count": 0,
        "eligible_row_count": 0,
        "preview_changed_row_count": 0,
        "baseline_runtime_proxy_match_rate": 0.0,
        "preview_runtime_proxy_match_rate": 0.0,
        "baseline_action_precision": 0.0,
        "preview_action_precision": 0.0,
        "improved_row_count": 0,
        "worsened_row_count": 0,
        "unchanged_row_count": 0,
        "sample_floor": _to_int(profile.get("sample_floor")),
        "candidate_action_precision_floor": _to_float(profile.get("candidate_action_precision_floor")),
        "runtime_proxy_match_rate_floor": _to_float(profile.get("runtime_proxy_match_rate_floor")),
        "target_metric_goal": _to_text(profile.get("target_metric_goal")),
        "casebook_examples": [],
        "recommended_next_action": "collect_more_symbol_preview_rows",
    }
    if frame.empty:
        return pd.DataFrame(), summary

    scoped = frame.loc[frame["symbol"].fillna("").astype(str).str.upper() == profile["symbol"]].copy()
    summary["resolved_row_count"] = int(len(scoped))
    if scoped.empty:
        return pd.DataFrame(), summary

    rows: list[dict[str, Any]] = []
    for row in scoped.to_dict(orient="records"):
        baseline_action = _baseline_action(row)
        preview_action = baseline_action
        eligible, preview_reason = _eligible_row(row, profile)
        if eligible:
            preview_action = _to_text(profile.get("candidate_action")).upper()
        hindsight_action = _to_text(row.get("hindsight_best_management_action_label")).upper()
        rows.append(
            {
                "symbol": profile["symbol"],
                "checkpoint_id": _to_text(row.get("checkpoint_id")),
                "surface_name": _to_text(row.get("surface_name")),
                "checkpoint_type": _to_text(row.get("checkpoint_type")).upper(),
                "checkpoint_rule_family_hint": _to_text(row.get("checkpoint_rule_family_hint")).lower(),
                "baseline_action_label": baseline_action,
                "preview_action_label": preview_action,
                "preview_changed": bool(preview_action != baseline_action),
                "preview_reason": preview_reason,
                "hindsight_best_management_action_label": hindsight_action,
                "baseline_hindsight_match": bool(baseline_action and baseline_action == hindsight_action),
                "preview_hindsight_match": bool(preview_action and preview_action == hindsight_action),
                "current_profit": round(_to_float(row.get("current_profit"), 0.0), 6),
                "runtime_hold_quality_score": round(_to_float(row.get("runtime_hold_quality_score"), 0.0), 6),
                "runtime_partial_exit_ev": round(_to_float(row.get("runtime_partial_exit_ev"), 0.0), 6),
                "runtime_full_exit_risk": round(_to_float(row.get("runtime_full_exit_risk"), 0.0), 6),
                "runtime_continuation_odds": round(_to_float(row.get("runtime_continuation_odds"), 0.0), 6),
                "runtime_reversal_odds": round(_to_float(row.get("runtime_reversal_odds"), 0.0), 6),
                "giveback_ratio": round(_to_float(row.get("giveback_ratio"), 0.0), 6),
                "source": _to_text(row.get("source")),
            }
        )

    preview_frame = pd.DataFrame(rows)
    if preview_frame.empty:
        return pd.DataFrame(), summary

    eligible_mask = preview_frame["preview_changed"].astype(bool)
    candidate_rows = preview_frame.loc[eligible_mask].copy()
    total_rows = int(len(preview_frame))
    candidate_count = int(len(candidate_rows))
    summary["eligible_row_count"] = candidate_count
    summary["preview_changed_row_count"] = candidate_count
    summary["baseline_runtime_proxy_match_rate"] = _safe_rate(int(preview_frame["baseline_hindsight_match"].sum()), total_rows)
    summary["preview_runtime_proxy_match_rate"] = _safe_rate(int(preview_frame["preview_hindsight_match"].sum()), total_rows)
    candidate_action = _to_text(profile.get("candidate_action")).upper()
    summary["baseline_action_precision"] = _safe_rate(
        int((candidate_rows["hindsight_best_management_action_label"] == candidate_rows["baseline_action_label"]).sum()),
        candidate_count,
    )
    summary["preview_action_precision"] = _safe_rate(
        int((candidate_rows["hindsight_best_management_action_label"] == candidate_action).sum()),
        candidate_count,
    )
    improved = int(((preview_frame["preview_hindsight_match"]) & (~preview_frame["baseline_hindsight_match"])).sum())
    worsened = int(((~preview_frame["preview_hindsight_match"]) & (preview_frame["baseline_hindsight_match"])).sum())
    summary["improved_row_count"] = improved
    summary["worsened_row_count"] = worsened
    summary["unchanged_row_count"] = int(total_rows - improved - worsened)
    summary["casebook_examples"] = (
        preview_frame.loc[eligible_mask]
        .sort_values(by=["checkpoint_type", "checkpoint_rule_family_hint", "checkpoint_id"], ascending=[True, True, True])
        .head(20)
        .to_dict(orient="records")
    )
    if (
        candidate_count >= _to_int(profile.get("sample_floor"))
        and worsened == 0
        and summary["preview_action_precision"] >= _to_float(profile.get("candidate_action_precision_floor"))
        and summary["preview_runtime_proxy_match_rate"] >= _to_float(profile.get("runtime_proxy_match_rate_floor"))
        and summary["preview_runtime_proxy_match_rate"] > summary["baseline_runtime_proxy_match_rate"]
    ):
        summary["recommended_next_action"] = "review_symbol_action_only_preview_for_canary"
    elif (
        candidate_count > 0
        and worsened == 0
        and summary["preview_action_precision"] >= _to_float(profile.get("candidate_action_precision_floor"))
        and summary["preview_runtime_proxy_match_rate"] > summary["baseline_runtime_proxy_match_rate"]
    ):
        summary["recommended_next_action"] = "keep_preview_and_collect_more_symbol_rows"
    return preview_frame, summary


def _render_preview_markdown(summary: Mapping[str, Any]) -> str:
    rows = list(summary.get("casebook_examples", []) or [])
    lines: list[str] = []
    lines.append(f"# PA8 {_to_text(summary.get('symbol'))} Action Preview")
    lines.append("")
    for key in (
        "candidate_action",
        "baseline_runtime_proxy_match_rate",
        "preview_runtime_proxy_match_rate",
        "baseline_action_precision",
        "preview_action_precision",
        "eligible_row_count",
        "preview_changed_row_count",
        "improved_row_count",
        "worsened_row_count",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Changed Casebook")
    lines.append("")
    for index, row in enumerate(rows[:10], start=1):
        if not isinstance(row, Mapping):
            continue
        lines.append(f"### {index}. {_to_text(row.get('checkpoint_id'))}")
        lines.append("")
        lines.append(
            f"- action_path: `{_to_text(row.get('baseline_action_label'))} -> {_to_text(row.get('preview_action_label'))} -> {_to_text(row.get('hindsight_best_management_action_label'))}`"
        )
        lines.append(f"- family: `{_to_text(row.get('checkpoint_rule_family_hint'))}`")
        lines.append(f"- preview_reason: `{_to_text(row.get('preview_reason'))}`")
        lines.append("")
    return '\n'.join(lines).rstrip() + '\n'


def _find_symbol_row(pa8_action_review_packet_payload: Mapping[str, Any], symbol: str) -> dict[str, Any]:
    for row in list(_mapping(pa8_action_review_packet_payload).get("symbol_rows", []) or []):
        if isinstance(row, Mapping) and _to_text(row.get("symbol")).upper() == _to_text(symbol).upper():
            return dict(row)
    return {}


def _build_canary_review(profile: Mapping[str, Any], pa8_packet: Mapping[str, Any], symbol_review: Mapping[str, Any], preview_summary: Mapping[str, Any]) -> dict[str, Any]:
    symbol_row = _find_symbol_row(pa8_packet, _to_text(profile.get("symbol")))
    blockers: list[str] = []
    if not bool(_mapping(pa8_packet.get("summary")).get("action_baseline_review_ready")):
        blockers.append("pa8_action_baseline_review_not_ready")
    if _to_int(preview_summary.get("eligible_row_count")) < _to_int(profile.get("sample_floor")):
        blockers.append("preview_eligible_row_count_below_floor")
    if _to_int(preview_summary.get("preview_changed_row_count")) <= 0:
        blockers.append("preview_changed_row_count_zero")
    if _to_int(preview_summary.get("worsened_row_count")) > 0:
        blockers.append("preview_has_worsened_rows")
    if _to_float(preview_summary.get("preview_action_precision")) < _to_float(profile.get("candidate_action_precision_floor")):
        blockers.append("preview_action_precision_below_floor")
    if _to_float(preview_summary.get("preview_runtime_proxy_match_rate")) < _to_float(profile.get("runtime_proxy_match_rate_floor")):
        blockers.append("preview_runtime_proxy_match_rate_below_floor")
    if _to_float(preview_summary.get("preview_runtime_proxy_match_rate")) <= _to_float(preview_summary.get("baseline_runtime_proxy_match_rate")):
        blockers.append("preview_runtime_proxy_match_rate_not_improved")
    ready = len(blockers) == 0
    return {
        "summary": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "generated_at": _now(),
            "symbol": profile["symbol"],
            "preview_slug": profile["preview_slug"],
            "candidate_action": _to_text(profile.get("candidate_action")),
            "symbol_review_state": _to_text(symbol_row.get("review_state")),
            "symbol_review_result": _to_text(_mapping(symbol_review.get("summary")).get("review_result")),
            "canary_review_state": "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW" if ready else "HOLD_PREVIEW_ONLY_REVIEW",
            "provisional_canary_ready": ready,
            "blockers": blockers,
            "eligible_row_count": _to_int(preview_summary.get("eligible_row_count")),
            "preview_changed_row_count": _to_int(preview_summary.get("preview_changed_row_count")),
            "improved_row_count": _to_int(preview_summary.get("improved_row_count")),
            "worsened_row_count": _to_int(preview_summary.get("worsened_row_count")),
            "baseline_action_precision": round(_to_float(preview_summary.get("baseline_action_precision")), 6),
            "preview_action_precision": round(_to_float(preview_summary.get("preview_action_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(_to_float(preview_summary.get("baseline_runtime_proxy_match_rate")), 6),
            "preview_runtime_proxy_match_rate": round(_to_float(preview_summary.get("preview_runtime_proxy_match_rate")), 6),
            "target_metric_goal": _to_text(profile.get("target_metric_goal")),
            "recommended_next_action": "prepare_symbol_action_only_provisional_canary_scope" if ready else "keep_symbol_action_preview_only",
            "casebook_examples": list(preview_summary.get("casebook_examples", []) or [])[:10],
        },
        "candidate_scope": {
            "symbol_allowlist": [profile["symbol"]],
            "surface_allowlist": [_to_text(profile.get("surface_name"))],
            "checkpoint_type_allowlist": list(profile.get("checkpoint_type_allowlist", []) or []),
            "family_allowlist": list(profile.get("family_allowlist", []) or []),
            "baseline_action_allowlist": list(profile.get("baseline_action_allowlist", []) or []),
            "preview_action": _to_text(profile.get("candidate_action")),
            "preview_reason": _to_text(profile.get("candidate_reason")),
            "scene_bias_mode": "preview_only_excluded_from_canary_scope",
        },
        "canary_guardrails": {
            "sample_floor": _to_int(profile.get("sample_floor")),
            "worsened_row_count_ceiling": 0,
            "candidate_action_precision_floor": round(_to_float(profile.get("candidate_action_precision_floor")), 6),
            "runtime_proxy_match_rate_floor": round(_to_float(profile.get("runtime_proxy_match_rate_floor")), 6),
        },
    }


def _render_summary_markdown(title: str, summary: Mapping[str, Any], extra: Mapping[str, Any] | None = None) -> str:
    lines: list[str] = [f"# {title}", ""]
    for key, value in summary.items():
        if key == "casebook_examples":
            continue
        lines.append(f"- {key}: `{value}`")
    extras = dict(extra or {})
    for section, payload in extras.items():
        lines.append("")
        lines.append(f"## {section}")
        lines.append("")
        if isinstance(payload, Mapping):
            for key, value in payload.items():
                lines.append(f"- {key}: `{value}`")
        elif isinstance(payload, list):
            for item in payload:
                lines.append(f"- `{item}`")
        else:
            lines.append(f"- `{payload}`")
    return "\n".join(lines).rstrip() + "\n"


def _build_execution_checklist(canary_review: Mapping[str, Any]) -> dict[str, Any]:
    summary = _mapping(canary_review.get("summary"))
    ready = bool(summary.get("provisional_canary_ready"))
    return {
        "summary": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "generated_at": _now(),
            "symbol": _to_text(summary.get("symbol")),
            "candidate_action": _to_text(summary.get("candidate_action")),
            "execution_state": "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION" if ready else "HOLD_CANARY_EXECUTION_CHECKLIST",
            "provisional_canary_ready": ready,
            "blockers": list(summary.get("blockers", []) or []),
            "eligible_row_count": _to_int(summary.get("eligible_row_count")),
            "preview_changed_row_count": _to_int(summary.get("preview_changed_row_count")),
            "improved_row_count": _to_int(summary.get("improved_row_count")),
            "worsened_row_count": _to_int(summary.get("worsened_row_count")),
            "baseline_action_precision": round(_to_float(summary.get("baseline_action_precision")), 6),
            "preview_action_precision": round(_to_float(summary.get("preview_action_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(_to_float(summary.get("baseline_runtime_proxy_match_rate")), 6),
            "preview_runtime_proxy_match_rate": round(_to_float(summary.get("preview_runtime_proxy_match_rate")), 6),
            "target_metric_goal": _to_text(summary.get("target_metric_goal")),
            "recommended_next_action": "review_and_confirm_symbol_bounded_action_only_canary_execution" if ready else "keep_symbol_action_only_canary_in_review",
        },
        "scope_snapshot": _mapping(canary_review.get("candidate_scope")),
        "guardrail_snapshot": _mapping(canary_review.get("canary_guardrails")),
    }


def _build_activation_packet(execution_checklist: Mapping[str, Any]) -> dict[str, Any]:
    summary = _mapping(execution_checklist.get("summary"))
    blockers = list(summary.get("blockers", []) or [])
    ready = _to_text(summary.get("execution_state")) == "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION" and not blockers
    return {
        "summary": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "generated_at": _now(),
            "symbol": _to_text(summary.get("symbol")),
            "candidate_action": _to_text(summary.get("candidate_action")),
            "activation_state": "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW" if ready else "HOLD_ACTION_ONLY_CANARY_ACTIVATION_PACKET",
            "allow_activation": ready,
            "manual_activation_required": True,
            "blockers": blockers,
            "eligible_row_count": _to_int(summary.get("eligible_row_count")),
            "preview_changed_row_count": _to_int(summary.get("preview_changed_row_count")),
            "improved_row_count": _to_int(summary.get("improved_row_count")),
            "worsened_row_count": _to_int(summary.get("worsened_row_count")),
            "baseline_action_precision": round(_to_float(summary.get("baseline_action_precision")), 6),
            "preview_action_precision": round(_to_float(summary.get("preview_action_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(_to_float(summary.get("baseline_runtime_proxy_match_rate")), 6),
            "preview_runtime_proxy_match_rate": round(_to_float(summary.get("preview_runtime_proxy_match_rate")), 6),
            "target_metric_goal": _to_text(summary.get("target_metric_goal")),
            "recommended_next_action": "manually_review_and_confirm_symbol_action_only_canary_activation" if ready else "keep_symbol_action_only_canary_at_execution_checklist_stage",
        },
        "activation_scope": {
            "activation_id": f"pa8_canary::{_to_text(summary.get('symbol'))}::{_to_text(_mapping(execution_checklist.get('scope_snapshot')).get('preview_action')).lower()}",
            **_mapping(execution_checklist.get("scope_snapshot")),
            "scene_bias_excluded": True,
            "size_change_allowed": False,
            "new_entry_logic_allowed": False,
        },
        "activation_guardrails": _mapping(execution_checklist.get("guardrail_snapshot")),
    }


def _build_activation_review(activation_packet: Mapping[str, Any]) -> dict[str, Any]:
    summary = _mapping(activation_packet.get("summary"))
    blockers = list(summary.get("blockers", []) or [])
    ready = bool(summary.get("allow_activation")) and not blockers
    return {
        "summary": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "generated_at": _now(),
            "symbol": _to_text(summary.get("symbol")),
            "candidate_action": _to_text(summary.get("candidate_action")),
            "review_state": "READY_FOR_HUMAN_ACTIVATION_DECISION" if ready else "HOLD_HUMAN_ACTIVATION_DECISION",
            "allow_activation": ready,
            "blockers": blockers,
            "recommended_next_action": "approve_or_hold_symbol_action_only_canary_activation" if ready else "resolve_activation_packet_blockers_first",
            "baseline_action_precision": round(_to_float(summary.get("baseline_action_precision")), 6),
            "preview_action_precision": round(_to_float(summary.get("preview_action_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(_to_float(summary.get("baseline_runtime_proxy_match_rate")), 6),
            "preview_runtime_proxy_match_rate": round(_to_float(summary.get("preview_runtime_proxy_match_rate")), 6),
        },
        "scope_snapshot": _mapping(activation_packet.get("activation_scope")),
        "guardrail_snapshot": _mapping(activation_packet.get("activation_guardrails")),
    }


def _build_monitoring_packet(activation_packet: Mapping[str, Any]) -> dict[str, Any]:
    summary = _mapping(activation_packet.get("summary"))
    blockers = list(summary.get("blockers", []) or [])
    ready = bool(summary.get("allow_activation")) and not blockers
    return {
        "summary": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "generated_at": _now(),
            "symbol": _to_text(summary.get("symbol")),
            "candidate_action": _to_text(summary.get("candidate_action")),
            "monitoring_state": "READY_TO_START_FIRST_CANARY_WINDOW" if ready else "HOLD_MONITORING_PACKET",
            "first_window_status": "AWAIT_FIRST_CANARY_WINDOW_RESULTS" if ready else "MONITORING_NOT_READY",
            "blockers": blockers,
            "recommended_next_action": "start_collecting_first_canary_window_observations" if ready else "keep_monitoring_packet_in_hold",
            "baseline_action_precision": round(_to_float(summary.get("baseline_action_precision")), 6),
            "preview_action_precision": round(_to_float(summary.get("preview_action_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(_to_float(summary.get("baseline_runtime_proxy_match_rate")), 6),
            "preview_runtime_proxy_match_rate": round(_to_float(summary.get("preview_runtime_proxy_match_rate")), 6),
        },
    }


def _build_rollback_packet(activation_packet: Mapping[str, Any], monitoring_packet: Mapping[str, Any]) -> dict[str, Any]:
    activation_summary = _mapping(activation_packet.get("summary"))
    monitoring_summary = _mapping(monitoring_packet.get("summary"))
    blockers = list(activation_summary.get("blockers", []) or [])
    ready = bool(activation_summary.get("allow_activation")) and _to_text(monitoring_summary.get("monitoring_state")) == "READY_TO_START_FIRST_CANARY_WINDOW" and not blockers
    return {
        "summary": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "generated_at": _now(),
            "symbol": _to_text(activation_summary.get("symbol")),
            "rollback_review_state": "READY_WITH_NO_TRIGGER_ACTIVE" if ready else "HOLD_ROLLBACK_REVIEW_PACKET",
            "current_trigger_state": "no_active_trigger_detected",
            "blockers": blockers,
            "recommended_next_action": "keep_rollback_packet_ready_during_first_canary_window" if ready else "resolve_activation_or_monitoring_blockers_first",
        },
        "rollback_triggers": [
            "candidate_action_precision_drop_below_floor",
            "runtime_proxy_match_rate_drop_below_floor",
            "new_worsened_rows_detected",
        ],
    }


def _build_activation_apply(activation_review: Mapping[str, Any], activation_packet: Mapping[str, Any], *, approval_decision: str) -> dict[str, Any]:
    review_summary = _mapping(activation_review.get("summary"))
    activation_scope = _mapping(activation_review.get("scope_snapshot"))
    guardrail_snapshot = _mapping(activation_review.get("guardrail_snapshot"))
    blockers = list(review_summary.get("blockers", []) or [])
    decision = _to_text(approval_decision, "HOLD").upper()
    if decision not in {"APPROVE", "HOLD", "REJECT"}:
        decision = "HOLD"
    ready = _to_text(review_summary.get("review_state")) == "READY_FOR_HUMAN_ACTIVATION_DECISION" and bool(review_summary.get("allow_activation")) and not blockers
    if not ready:
        approval_state = "ACTIVATION_NOT_READY"
        activation_apply_state = "HOLD_CANARY_ACTIVATION_APPLY"
        active = False
        recommended_next_action = "resolve_activation_review_blockers_first"
    elif decision == "APPROVE":
        approval_state = "MANUAL_ACTIVATION_APPROVED"
        activation_apply_state = "ACTIVE_ACTION_ONLY_CANARY"
        active = True
        recommended_next_action = "start_first_canary_window_observation"
    elif decision == "REJECT":
        approval_state = "MANUAL_ACTIVATION_REJECTED"
        activation_apply_state = "REJECTED_ACTION_ONLY_CANARY"
        active = False
        recommended_next_action = "return_to_preview_only_and_collect_more_evidence"
    else:
        approval_state = "MANUAL_ACTIVATION_HELD"
        activation_apply_state = "HELD_ACTION_ONLY_CANARY"
        active = False
        recommended_next_action = "hold_canary_activation_and_revisit_later"
    generated_at = _now()
    return {
        "summary": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "generated_at": generated_at,
            "symbol": _to_text(review_summary.get("symbol")),
            "candidate_action": _to_text(review_summary.get("candidate_action")),
            "approval_decision": decision,
            "approval_state": approval_state,
            "activation_apply_state": activation_apply_state,
            "active": active,
            "blockers": blockers,
            "eligible_row_count": _to_int(_mapping(activation_packet.get("summary")).get("eligible_row_count")),
            "preview_changed_row_count": _to_int(_mapping(activation_packet.get("summary")).get("preview_changed_row_count")),
            "worsened_row_count": _to_int(_mapping(activation_packet.get("summary")).get("worsened_row_count")),
            "baseline_action_precision": round(_to_float(_mapping(activation_packet.get("summary")).get("baseline_action_precision")), 6),
            "preview_action_precision": round(_to_float(_mapping(activation_packet.get("summary")).get("preview_action_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(_to_float(_mapping(activation_packet.get("summary")).get("baseline_runtime_proxy_match_rate")), 6),
            "preview_runtime_proxy_match_rate": round(_to_float(_mapping(activation_packet.get("summary")).get("preview_runtime_proxy_match_rate")), 6),
            "recommended_next_action": recommended_next_action,
        },
        "active_state": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "activation_id": _to_text(activation_scope.get("activation_id")),
            "symbol": _to_text(review_summary.get("symbol")),
            "activation_apply_state": activation_apply_state,
            "approval_state": approval_state,
            "active": active,
            "activated_at": generated_at if active else "",
            "first_window_started_at": generated_at if active else "",
            "window_status": "FIRST_CANARY_WINDOW_ACTIVE" if active else "WINDOW_NOT_ACTIVE",
            "scope": activation_scope,
            "guardrails": guardrail_snapshot,
        },
    }


def _slice_post_activation_rows(resolved_dataset: pd.DataFrame | None, *, symbol: str, activated_at: str) -> pd.DataFrame:
    frame = resolved_dataset.copy() if resolved_dataset is not None and not resolved_dataset.empty else pd.DataFrame()
    if frame.empty or not activated_at:
        return pd.DataFrame()
    if "generated_at" not in frame.columns:
        frame["generated_at"] = ""
    times = pd.to_datetime(frame["generated_at"], errors="coerce", utc=True)
    threshold = pd.to_datetime(activated_at, errors="coerce", utc=True)
    if pd.isna(threshold):
        return pd.DataFrame()
    return frame.loc[(frame["symbol"].fillna("").astype(str).str.upper() == _to_text(symbol).upper()) & (times >= threshold)].copy()


def _build_first_window_observation(activation_apply: Mapping[str, Any], preview_summary: Mapping[str, Any], resolved_dataset: pd.DataFrame | None) -> dict[str, Any]:
    activation_summary = _mapping(activation_apply.get("summary"))
    active_state = _mapping(activation_apply.get("active_state"))
    guardrails = _mapping(active_state.get("guardrails"))
    symbol = _to_text(activation_summary.get("symbol"))
    active = bool(activation_summary.get("active")) and _to_text(activation_summary.get("activation_apply_state")) == "ACTIVE_ACTION_ONLY_CANARY"
    current_action_precision: float | None = None
    current_runtime_proxy_match_rate: float | None = None
    new_worsened_rows = 0
    observed_window_row_count = 0
    live_observation_ready = False
    observation_source = "no_active_canary"
    if active:
        post_activation_rows = _slice_post_activation_rows(resolved_dataset, symbol=symbol, activated_at=_to_text(active_state.get("activated_at")))
        if not post_activation_rows.empty:
            _, live_preview_summary = build_checkpoint_pa8_symbol_action_preview(post_activation_rows, symbol=symbol)
            observation_source = "post_activation_scoped_rows"
            observed_window_row_count = _to_int(live_preview_summary.get("preview_changed_row_count"))
            live_observation_ready = observed_window_row_count > 0
            current_action_precision = round(_to_float(live_preview_summary.get("preview_action_precision")), 6)
            current_runtime_proxy_match_rate = round(_to_float(live_preview_summary.get("preview_runtime_proxy_match_rate")), 6)
            new_worsened_rows = _to_int(live_preview_summary.get("worsened_row_count"))
        else:
            observation_source = "preview_seed_reference"
            current_action_precision = round(_to_float(preview_summary.get("preview_action_precision")), 6)
            current_runtime_proxy_match_rate = round(_to_float(preview_summary.get("preview_runtime_proxy_match_rate")), 6)
            new_worsened_rows = _to_int(preview_summary.get("worsened_row_count"))
    active_triggers: list[str] = []
    if current_action_precision is not None and current_action_precision < _to_float(guardrails.get("candidate_action_precision_floor")):
        active_triggers.append("candidate_action_precision_drop_below_floor")
    if current_runtime_proxy_match_rate is not None and current_runtime_proxy_match_rate < _to_float(guardrails.get("runtime_proxy_match_rate_floor")):
        active_triggers.append("runtime_proxy_match_rate_drop_below_floor")
    if new_worsened_rows > _to_int(guardrails.get("worsened_row_count_ceiling")):
        active_triggers.append("new_worsened_rows_detected")
    return {
        "summary": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "generated_at": _now(),
            "symbol": symbol,
            "candidate_action": _to_text(activation_summary.get("candidate_action")),
            "activation_apply_state": _to_text(activation_summary.get("activation_apply_state")),
            "first_window_status": "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE" if live_observation_ready else ("FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS" if active else "HOLD_WINDOW_NOT_ACTIVE"),
            "observation_source": observation_source,
            "live_observation_ready": live_observation_ready,
            "recommended_next_action": "continue_accumulating_live_first_window_rows" if live_observation_ready else ("keep_canary_active_and_wait_for_post_activation_rows" if active else "approve_and_apply_canary_before_observation"),
            "observed_window_row_count": observed_window_row_count,
            "seed_reference_row_count": _to_int(preview_summary.get("preview_changed_row_count")),
            "baseline_action_precision": round(_to_float(activation_summary.get("baseline_action_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(_to_float(activation_summary.get("baseline_runtime_proxy_match_rate")), 6),
            "current_action_precision": current_action_precision,
            "current_runtime_proxy_match_rate": current_runtime_proxy_match_rate,
            "new_worsened_rows": new_worsened_rows,
            "active_trigger_count": len(active_triggers),
        },
        "active_triggers": active_triggers,
    }


def _build_closeout_decision(activation_apply: Mapping[str, Any], first_window_observation: Mapping[str, Any], rollback_packet: Mapping[str, Any]) -> dict[str, Any]:
    activation_summary = _mapping(activation_apply.get("summary"))
    observation_summary = _mapping(first_window_observation.get("summary"))
    active_triggers = list(first_window_observation.get("active_triggers", []) or [])
    sample_floor = _to_int(_mapping(_mapping(activation_apply.get("active_state")).get("guardrails")).get("sample_floor"))
    active = bool(activation_summary.get("active"))
    observed_window_row_count = _to_int(observation_summary.get("observed_window_row_count"))
    live_observation_ready = bool(observation_summary.get("live_observation_ready"))
    if not active:
        closeout_state = "HOLD_CLOSEOUT_CANARY_NOT_ACTIVE"
        decision = "do_not_closeout_inactive_canary"
        next_action = "activate_canary_before_closeout_review"
    elif not live_observation_ready:
        closeout_state = "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW"
        decision = "keep_canary_active_and_collect_live_rows"
        next_action = "wait_for_live_first_window_rows_before_pa8_closeout"
    elif active_triggers:
        closeout_state = "ROLLBACK_REQUIRED"
        decision = "rollback_canary_scope_immediately"
        next_action = "disable_canary_and_return_to_baseline_action_behavior"
    elif observed_window_row_count < sample_floor:
        closeout_state = "HOLD_CLOSEOUT_PENDING_SAMPLE_FLOOR"
        decision = "keep_canary_active_until_sample_floor_reached"
        next_action = "continue_bounded_canary_until_sample_floor_is_met"
    else:
        closeout_state = "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW"
        decision = "promote_action_only_canary_results_to_pa9_review"
        next_action = "prepare_pa9_action_baseline_handoff_packet"
    return {
        "summary": {
            "contract_version": PATH_CHECKPOINT_PA8_SYMBOL_ACTION_CANARY_VERSION,
            "generated_at": _now(),
            "symbol": _to_text(activation_summary.get("symbol")),
            "candidate_action": _to_text(activation_summary.get("candidate_action")),
            "rollback_review_state": _to_text(_mapping(rollback_packet.get("summary")).get("rollback_review_state")),
            "closeout_state": closeout_state,
            "decision": decision,
            "recommended_next_action": next_action,
            "live_observation_ready": live_observation_ready,
            "observed_window_row_count": observed_window_row_count,
            "sample_floor": sample_floor,
            "current_action_precision": observation_summary.get("current_action_precision"),
            "current_runtime_proxy_match_rate": observation_summary.get("current_runtime_proxy_match_rate"),
            "new_worsened_rows": _to_int(observation_summary.get("new_worsened_rows")),
            "active_trigger_count": len(active_triggers),
        },
        "active_triggers": active_triggers,
    }


def build_checkpoint_pa8_symbol_action_canary_bundle(
    *,
    resolved_dataset: pd.DataFrame | None,
    pa8_action_review_packet_payload: Mapping[str, Any] | None,
    symbol_review_payload: Mapping[str, Any] | None,
    symbol: str,
    approval_decision: str = "APPROVE",
) -> dict[str, dict[str, Any]]:
    profile = _symbol_profile(symbol)
    _, preview_summary = build_checkpoint_pa8_symbol_action_preview(resolved_dataset, symbol=profile["symbol"])
    preview = {"summary": preview_summary}
    canary_review = _build_canary_review(profile, _mapping(pa8_action_review_packet_payload), _mapping(symbol_review_payload), preview_summary)
    execution_checklist = _build_execution_checklist(canary_review)
    activation_packet = _build_activation_packet(execution_checklist)
    activation_review = _build_activation_review(activation_packet)
    monitoring_packet = _build_monitoring_packet(activation_packet)
    rollback_packet = _build_rollback_packet(activation_packet, monitoring_packet)
    activation_apply = _build_activation_apply(activation_review, activation_packet, approval_decision=approval_decision)
    first_window_observation = _build_first_window_observation(activation_apply, preview_summary, resolved_dataset)
    closeout_decision = _build_closeout_decision(activation_apply, first_window_observation, rollback_packet)
    return {
        "preview": preview,
        "canary_review": canary_review,
        "execution_checklist": execution_checklist,
        "activation_packet": activation_packet,
        "activation_review": activation_review,
        "monitoring_packet": monitoring_packet,
        "rollback_packet": rollback_packet,
        "activation_apply": activation_apply,
        "first_window_observation": first_window_observation,
        "closeout_decision": closeout_decision,
    }


def render_checkpoint_pa8_symbol_action_canary_markdown(artifact_name: str, payload: Mapping[str, Any] | None) -> str:
    summary = _mapping(_mapping(payload).get("summary"))
    title_map = {
        "preview": f"PA8 {_to_text(summary.get('symbol'))} Action Preview",
        "canary_review": f"PA8 {_to_text(summary.get('symbol'))} Provisional Action-Only Canary Review",
        "execution_checklist": f"PA8 {_to_text(summary.get('symbol'))} Action-Only Canary Execution Checklist",
        "activation_packet": f"PA8 {_to_text(summary.get('symbol'))} Action-Only Canary Activation Packet",
        "activation_review": f"PA8 {_to_text(summary.get('symbol'))} Action-Only Canary Activation Human Review",
        "monitoring_packet": f"PA8 {_to_text(summary.get('symbol'))} Action-Only Canary Monitoring Packet",
        "rollback_packet": f"PA8 {_to_text(summary.get('symbol'))} Action-Only Canary Rollback Review Packet",
        "activation_apply": f"PA8 {_to_text(summary.get('symbol'))} Action-Only Canary Activation Apply",
        "first_window_observation": f"PA8 {_to_text(summary.get('symbol'))} Action-Only Canary First Window Observation",
        "closeout_decision": f"PA8 {_to_text(summary.get('symbol'))} Action-Only Canary Closeout Decision",
    }
    if artifact_name == "preview":
        return _render_preview_markdown(summary)
    extra_sections: dict[str, Any] = {}
    for key in ("candidate_scope", "canary_guardrails", "scope_snapshot", "guardrail_snapshot", "activation_scope", "activation_guardrails", "rollback_triggers", "active_triggers"):
        value = _mapping(payload).get(key)
        if value not in (None, {}, []):
            extra_sections[key] = value
    return _render_summary_markdown(title_map.get(artifact_name, artifact_name), summary, extra_sections)
