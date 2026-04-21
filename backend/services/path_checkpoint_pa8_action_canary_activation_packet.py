from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_nas100_action_only_canary_activation_packet_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_activation_packet_latest.json"
    )


def default_checkpoint_pa8_nas100_action_only_canary_activation_packet_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_activation_packet_latest.md"
    )


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def build_checkpoint_pa8_nas100_action_only_canary_activation_packet(
    *,
    canary_execution_checklist_payload: Mapping[str, Any] | None,
    canary_review_packet_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    checklist = _mapping(canary_execution_checklist_payload)
    checklist_summary = _mapping(checklist.get("summary"))
    scope_snapshot = _mapping(checklist.get("scope_snapshot"))
    guardrail_snapshot = _mapping(checklist.get("guardrail_snapshot"))
    execution_steps = checklist.get("execution_steps")
    if not isinstance(execution_steps, list):
        execution_steps = []

    review_packet = _mapping(canary_review_packet_payload)
    review_summary = _mapping(review_packet.get("summary"))

    blockers = list(checklist_summary.get("blockers", []) or [])
    execution_ready = _to_text(checklist_summary.get("execution_state")) == "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION"
    review_ready = bool(review_summary.get("provisional_canary_ready"))
    allow_activation = execution_ready and review_ready and not blockers

    activation_state = (
        "READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW"
        if allow_activation
        else "HOLD_ACTION_ONLY_CANARY_ACTIVATION_PACKET"
    )
    recommended_next_action = (
        "manually_review_and_confirm_nas100_action_only_canary_activation"
        if allow_activation
        else "keep_nas100_action_only_canary_at_execution_checklist_stage"
    )

    activation_scope = {
        "activation_id": "pa8_canary::NAS100::continuation_hold_surface::RUNNER_CHECK::profit_hold_bias",
        "symbol_allowlist": scope_snapshot.get("symbol_allowlist", []),
        "surface_allowlist": scope_snapshot.get("surface_allowlist", []),
        "checkpoint_type_allowlist": scope_snapshot.get("checkpoint_type_allowlist", []),
        "family_allowlist": scope_snapshot.get("family_allowlist", []),
        "baseline_action_allowlist": scope_snapshot.get("baseline_action_allowlist", []),
        "candidate_action": _to_text(scope_snapshot.get("preview_action")),
        "candidate_reason": _to_text(scope_snapshot.get("preview_reason")),
        "change_mode": _to_text(scope_snapshot.get("change_mode"), "action_only_preview_candidate"),
        "manual_activation_required": True,
        "scene_bias_excluded": True,
        "size_change_allowed": False,
        "new_entry_logic_allowed": False,
    }

    activation_guardrails = {
        "sample_floor": _to_int(guardrail_snapshot.get("sample_floor")),
        "worsened_row_count_ceiling": _to_int(guardrail_snapshot.get("worsened_row_count_ceiling")),
        "hold_precision_floor": round(_to_float(guardrail_snapshot.get("hold_precision_floor")), 6),
        "runtime_proxy_match_rate_must_improve": bool(guardrail_snapshot.get("runtime_proxy_match_rate_must_improve")),
        "partial_then_hold_quality_must_not_regress": bool(
            guardrail_snapshot.get("partial_then_hold_quality_must_not_regress")
        ),
        "rollback_watch_metrics": list(guardrail_snapshot.get("rollback_watch_metrics", []) or []),
    }

    activation_checklist = [
        "Scope stays NAS100-only and family stays profit_hold_bias-only.",
        "Action change stays HOLD -> PARTIAL_THEN_HOLD only.",
        "Scene bias remains excluded from activation.",
        "No size change or new entry logic is introduced.",
        "Rollback immediately if hold precision drops below baseline or worsened rows appear.",
    ]

    monitoring_plan = {
        "monitor_only_scoped_family": True,
        "compare_against_baseline_metrics": [
            "hold_precision",
            "runtime_proxy_match_rate",
            "partial_then_hold_quality",
        ],
        "first_window_policy": "do_not_widen_scope_during_first_canary_window",
    }

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_canary_activation_packet_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol": _to_text(checklist_summary.get("symbol"), "NAS100"),
            "canary_review_state": _to_text(review_summary.get("canary_review_state")),
            "execution_state": _to_text(checklist_summary.get("execution_state")),
            "activation_state": activation_state,
            "allow_activation": allow_activation,
            "manual_activation_required": True,
            "blockers": blockers,
            "eligible_row_count": _to_int(checklist_summary.get("eligible_row_count")),
            "preview_changed_row_count": _to_int(checklist_summary.get("preview_changed_row_count")),
            "improved_row_count": _to_int(checklist_summary.get("improved_row_count")),
            "worsened_row_count": _to_int(checklist_summary.get("worsened_row_count")),
            "baseline_hold_precision": round(_to_float(checklist_summary.get("baseline_hold_precision")), 6),
            "preview_hold_precision": round(_to_float(checklist_summary.get("preview_hold_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(
                _to_float(checklist_summary.get("baseline_runtime_proxy_match_rate")),
                6,
            ),
            "preview_runtime_proxy_match_rate": round(
                _to_float(checklist_summary.get("preview_runtime_proxy_match_rate")),
                6,
            ),
            "baseline_partial_then_hold_quality": round(
                _to_float(checklist_summary.get("baseline_partial_then_hold_quality")),
                6,
            ),
            "preview_partial_then_hold_quality": round(
                _to_float(checklist_summary.get("preview_partial_then_hold_quality")),
                6,
            ),
            "target_metric_goal": _to_text(checklist_summary.get("target_metric_goal")),
            "recommended_next_action": recommended_next_action,
        },
        "activation_scope": activation_scope,
        "activation_guardrails": activation_guardrails,
        "activation_checklist": activation_checklist,
        "monitoring_plan": monitoring_plan,
        "execution_steps": execution_steps,
        "review_context": {
            "execution_checklist_summary": checklist_summary,
            "review_packet_summary": review_summary,
        },
    }


def render_checkpoint_pa8_nas100_action_only_canary_activation_packet_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    activation_scope = _mapping(body.get("activation_scope"))
    activation_guardrails = _mapping(body.get("activation_guardrails"))
    activation_checklist = body.get("activation_checklist")
    if not isinstance(activation_checklist, list):
        activation_checklist = []
    monitoring_plan = _mapping(body.get("monitoring_plan"))

    lines: list[str] = []
    lines.append("# PA8 NAS100 Action-Only Canary Activation Packet")
    lines.append("")
    lines.append(f"- activation_state: `{_to_text(summary.get('activation_state'))}`")
    lines.append(f"- allow_activation: `{summary.get('allow_activation', False)}`")
    lines.append(f"- manual_activation_required: `{summary.get('manual_activation_required', False)}`")
    lines.append(f"- canary_review_state: `{_to_text(summary.get('canary_review_state'))}`")
    lines.append(f"- execution_state: `{_to_text(summary.get('execution_state'))}`")
    lines.append(f"- target_metric_goal: `{_to_text(summary.get('target_metric_goal'))}`")
    lines.append(f"- baseline_hold_precision: `{_to_float(summary.get('baseline_hold_precision'))}`")
    lines.append(f"- preview_hold_precision: `{_to_float(summary.get('preview_hold_precision'))}`")
    lines.append(
        f"- baseline_runtime_proxy_match_rate: `{_to_float(summary.get('baseline_runtime_proxy_match_rate'))}`"
    )
    lines.append(
        f"- preview_runtime_proxy_match_rate: `{_to_float(summary.get('preview_runtime_proxy_match_rate'))}`"
    )
    lines.append(
        f"- baseline_partial_then_hold_quality: `{_to_float(summary.get('baseline_partial_then_hold_quality'))}`"
    )
    lines.append(
        f"- preview_partial_then_hold_quality: `{_to_float(summary.get('preview_partial_then_hold_quality'))}`"
    )
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append("")
    lines.append("## Activation Scope")
    lines.append("")
    for key in (
        "activation_id",
        "symbol_allowlist",
        "surface_allowlist",
        "checkpoint_type_allowlist",
        "family_allowlist",
        "baseline_action_allowlist",
        "candidate_action",
        "candidate_reason",
        "change_mode",
        "scene_bias_excluded",
        "size_change_allowed",
        "new_entry_logic_allowed",
    ):
        lines.append(f"- {key}: `{activation_scope.get(key)}`")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    for key in (
        "sample_floor",
        "worsened_row_count_ceiling",
        "hold_precision_floor",
        "runtime_proxy_match_rate_must_improve",
        "partial_then_hold_quality_must_not_regress",
    ):
        lines.append(f"- {key}: `{activation_guardrails.get(key)}`")
    rollback_metrics = activation_guardrails.get("rollback_watch_metrics")
    if isinstance(rollback_metrics, list):
        lines.append("- rollback_watch_metrics:")
        for item in rollback_metrics:
            lines.append(f"  - `{_to_text(item)}`")
    lines.append("")
    lines.append("## Activation Checklist")
    lines.append("")
    for item in activation_checklist:
        lines.append(f"- [ ] {_to_text(item)}")
    lines.append("")
    lines.append("## Monitoring Plan")
    lines.append("")
    lines.append(
        f"- monitor_only_scoped_family: `{monitoring_plan.get('monitor_only_scoped_family', False)}`"
    )
    compare_metrics = monitoring_plan.get("compare_against_baseline_metrics")
    if isinstance(compare_metrics, list):
        lines.append("- compare_against_baseline_metrics:")
        for item in compare_metrics:
            lines.append(f"  - `{_to_text(item)}`")
    lines.append(f"- first_window_policy: `{_to_text(monitoring_plan.get('first_window_policy'))}`")
    blockers = list(summary.get("blockers", []) or [])
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if blockers:
        for item in blockers:
            lines.append(f"- `{_to_text(item)}`")
    else:
        lines.append("- `none`")
    return "\n".join(lines).rstrip() + "\n"
