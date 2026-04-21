from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_nas100_action_only_canary_execution_checklist_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_execution_checklist_latest.json"
    )


def default_checkpoint_pa8_nas100_action_only_canary_execution_checklist_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_execution_checklist_latest.md"
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


def _format_metric(value: object) -> str:
    return f"{_to_float(value):.6f}".rstrip("0").rstrip(".")


def _execution_steps(*, canary_ready: bool) -> list[dict[str, Any]]:
    steps = [
        {
            "step_id": "preflight",
            "title": "Preflight Freeze",
            "goal": "Freeze scope to NAS100 action-only changes and keep scene bias excluded.",
            "check_items": [
                "Confirm the candidate scope is still NAS100 / continuation_hold_surface / RUNNER_CHECK / profit_hold_bias.",
                "Confirm baseline action allowlist remains HOLD only.",
                "Confirm scene bias remains preview-only and excluded from canary scope.",
            ],
        },
        {
            "step_id": "bounded_activation",
            "title": "Bounded Activation Gate",
            "goal": "Decide whether the preview can be turned into a bounded canary candidate.",
            "check_items": [
                "Confirm preview_changed_row_count stays above the sample floor.",
                "Confirm worsened_row_count remains zero.",
                "Confirm preview hold precision remains above the canary floor.",
            ],
        },
        {
            "step_id": "monitoring",
            "title": "Monitoring Window",
            "goal": "Observe live or replay behavior without widening scope.",
            "check_items": [
                "Track hold precision against baseline during the canary window.",
                "Track partial_then_hold_quality for any regression.",
                "Track whether any new worsened rows appear in the scoped family.",
            ],
        },
        {
            "step_id": "rollback",
            "title": "Rollback Trigger Review",
            "goal": "Define the exact signals that immediately end the canary.",
            "check_items": [
                "Rollback if hold_precision drops below baseline.",
                "Rollback if partial_then_hold_quality regresses below baseline.",
                "Rollback if any new worsened rows appear inside the scoped family.",
            ],
        },
    ]
    if not canary_ready:
        for step in steps:
            step["status"] = "hold"
        return steps

    for index, step in enumerate(steps):
        step["status"] = "ready" if index == 0 else "pending"
    return steps


def build_checkpoint_pa8_nas100_action_only_canary_execution_checklist(
    *,
    canary_review_packet_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    packet = _mapping(canary_review_packet_payload)
    summary = _mapping(packet.get("summary"))
    candidate_scope = _mapping(packet.get("candidate_scope"))
    guardrails = _mapping(packet.get("canary_guardrails"))
    review_context = _mapping(packet.get("review_context"))

    canary_ready = bool(summary.get("provisional_canary_ready"))
    blockers = list(summary.get("blockers", []) or [])
    execution_state = (
        "READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION"
        if canary_ready
        else "HOLD_CANARY_EXECUTION_CHECKLIST"
    )
    recommended_next_action = (
        "review_and_confirm_nas100_bounded_action_only_canary_execution"
        if canary_ready
        else "keep_nas100_action_only_canary_in_review"
    )

    checklist_rows = [
        {
            "phase": "scope",
            "goal": "Freeze the canary to a narrow NAS100 action-only slice.",
            "checks": [
                "Symbol allowlist is NAS100 only.",
                "Surface allowlist is continuation_hold_surface only.",
                "Checkpoint type allowlist is RUNNER_CHECK only.",
                "Family allowlist is profit_hold_bias only.",
                "Baseline action allowlist is HOLD only.",
                "Scene bias remains excluded from the canary.",
            ],
        },
        {
            "phase": "entry_gate",
            "goal": "Confirm the packet still meets entry conditions before any bounded rollout.",
            "checks": [
                f"Eligible rows remain at or above `{_to_int(guardrails.get('sample_floor'))}`.",
                f"Worsened rows remain at or below `{_to_int(guardrails.get('worsened_row_count_ceiling'))}`.",
                f"Preview hold precision remains at or above `{_format_metric(guardrails.get('hold_precision_floor'))}`.",
                "Preview runtime proxy match rate remains above baseline.",
                "Preview partial_then_hold_quality does not regress.",
            ],
        },
        {
            "phase": "monitoring",
            "goal": "Observe only the scoped family while the canary is active.",
            "checks": [
                "Track hold precision against baseline on the NAS100 scoped family.",
                "Track partial_then_hold_quality against baseline on the scoped family.",
                "Track new worsened rows inside the scoped family.",
                "Do not widen the symbol/family scope during the first canary window.",
            ],
        },
        {
            "phase": "rollback",
            "goal": "Keep rollback conditions explicit and immediate.",
            "checks": [
                "Rollback if hold precision drops below baseline.",
                "Rollback if partial_then_hold_quality regresses below baseline.",
                "Rollback if any new worsened rows appear in the scoped family.",
            ],
        },
    ]

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_canary_execution_checklist_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol": _to_text(summary.get("symbol"), "NAS100"),
            "canary_review_state": _to_text(summary.get("canary_review_state")),
            "execution_state": execution_state,
            "provisional_canary_ready": canary_ready,
            "recommended_next_action": recommended_next_action,
            "blockers": blockers,
            "target_metric_goal": _to_text(summary.get("target_metric_goal")),
            "baseline_hold_precision": round(_to_float(summary.get("baseline_hold_precision")), 6),
            "preview_hold_precision": round(_to_float(summary.get("preview_hold_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(_to_float(summary.get("baseline_runtime_proxy_match_rate")), 6),
            "preview_runtime_proxy_match_rate": round(_to_float(summary.get("preview_runtime_proxy_match_rate")), 6),
            "baseline_partial_then_hold_quality": round(
                _to_float(summary.get("baseline_partial_then_hold_quality")),
                6,
            ),
            "preview_partial_then_hold_quality": round(
                _to_float(summary.get("preview_partial_then_hold_quality")),
                6,
            ),
            "eligible_row_count": _to_int(summary.get("eligible_row_count")),
            "preview_changed_row_count": _to_int(summary.get("preview_changed_row_count")),
            "improved_row_count": _to_int(summary.get("improved_row_count")),
            "worsened_row_count": _to_int(summary.get("worsened_row_count")),
        },
        "scope_snapshot": candidate_scope,
        "guardrail_snapshot": guardrails,
        "execution_steps": _execution_steps(canary_ready=canary_ready),
        "checklist_rows": checklist_rows,
        "review_context": review_context,
    }


def render_checkpoint_pa8_nas100_action_only_canary_execution_checklist_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    scope_snapshot = _mapping(body.get("scope_snapshot"))
    guardrail_snapshot = _mapping(body.get("guardrail_snapshot"))
    execution_steps = body.get("execution_steps")
    if not isinstance(execution_steps, list):
        execution_steps = []
    checklist_rows = body.get("checklist_rows")
    if not isinstance(checklist_rows, list):
        checklist_rows = []

    lines: list[str] = []
    lines.append("# PA8 NAS100 Action-Only Canary Execution Checklist")
    lines.append("")
    lines.append(f"- canary_review_state: `{_to_text(summary.get('canary_review_state'))}`")
    lines.append(f"- execution_state: `{_to_text(summary.get('execution_state'))}`")
    lines.append(f"- provisional_canary_ready: `{summary.get('provisional_canary_ready', False)}`")
    lines.append(f"- target_metric_goal: `{_to_text(summary.get('target_metric_goal'))}`")
    lines.append(f"- baseline_hold_precision: `{_format_metric(summary.get('baseline_hold_precision'))}`")
    lines.append(f"- preview_hold_precision: `{_format_metric(summary.get('preview_hold_precision'))}`")
    lines.append(
        f"- baseline_runtime_proxy_match_rate: `{_format_metric(summary.get('baseline_runtime_proxy_match_rate'))}`"
    )
    lines.append(
        f"- preview_runtime_proxy_match_rate: `{_format_metric(summary.get('preview_runtime_proxy_match_rate'))}`"
    )
    lines.append(
        f"- baseline_partial_then_hold_quality: `{_format_metric(summary.get('baseline_partial_then_hold_quality'))}`"
    )
    lines.append(
        f"- preview_partial_then_hold_quality: `{_format_metric(summary.get('preview_partial_then_hold_quality'))}`"
    )
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append("")
    lines.append("## Scope Snapshot")
    lines.append("")
    for key in (
        "symbol_allowlist",
        "surface_allowlist",
        "checkpoint_type_allowlist",
        "family_allowlist",
        "baseline_action_allowlist",
        "preview_action",
        "scene_bias_mode",
    ):
        lines.append(f"- {key}: `{scope_snapshot.get(key)}`")
    lines.append("")
    lines.append("## Guardrail Snapshot")
    lines.append("")
    for key in (
        "sample_floor",
        "worsened_row_count_ceiling",
        "hold_precision_floor",
        "runtime_proxy_match_rate_must_improve",
        "partial_then_hold_quality_must_not_regress",
    ):
        lines.append(f"- {key}: `{guardrail_snapshot.get(key)}`")
    lines.append("")
    lines.append("## Execution Steps")
    lines.append("")
    for step in execution_steps:
        if not isinstance(step, Mapping):
            continue
        lines.append(f"### {_to_text(step.get('step_id'))}")
        lines.append("")
        lines.append(f"- title: {_to_text(step.get('title'))}")
        lines.append(f"- status: `{_to_text(step.get('status'))}`")
        lines.append(f"- goal: {_to_text(step.get('goal'))}")
        check_items = step.get("check_items")
        if isinstance(check_items, list):
            for item in check_items:
                lines.append(f"- [ ] {_to_text(item)}")
        lines.append("")
    lines.append("## Review Checklist")
    lines.append("")
    for row in checklist_rows:
        if not isinstance(row, Mapping):
            continue
        lines.append(f"### {_to_text(row.get('phase'))}")
        lines.append("")
        lines.append(f"- goal: {_to_text(row.get('goal'))}")
        checks = row.get("checks")
        if isinstance(checks, list):
            for item in checks:
                lines.append(f"- [ ] {_to_text(item)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
