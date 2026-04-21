from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_nas100_action_only_canary_activation_review_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_activation_review_latest.json"
    )


def default_checkpoint_pa8_nas100_action_only_canary_activation_review_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_activation_review_latest.md"
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


def build_checkpoint_pa8_nas100_action_only_canary_activation_review(
    *,
    activation_packet_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    packet = _mapping(activation_packet_payload)
    summary = _mapping(packet.get("summary"))
    activation_scope = _mapping(packet.get("activation_scope"))
    activation_guardrails = _mapping(packet.get("activation_guardrails"))

    allow_activation = bool(summary.get("allow_activation"))
    blockers = list(summary.get("blockers", []) or [])
    review_state = (
        "READY_FOR_HUMAN_ACTIVATION_DECISION"
        if allow_activation and not blockers
        else "HOLD_HUMAN_ACTIVATION_DECISION"
    )
    recommended_next_action = (
        "approve_or_hold_nas100_action_only_canary_activation"
        if review_state == "READY_FOR_HUMAN_ACTIVATION_DECISION"
        else "resolve_activation_packet_blockers_first"
    )

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_canary_activation_review_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol": _to_text(summary.get("symbol"), "NAS100"),
            "activation_state": _to_text(summary.get("activation_state")),
            "review_state": review_state,
            "allow_activation": allow_activation,
            "blockers": blockers,
            "review_question": "Should NAS100 bounded action-only canary activation be manually approved under the current narrow scope and rollback guards?",
            "recommended_next_action": recommended_next_action,
            "eligible_row_count": _to_int(summary.get("eligible_row_count")),
            "preview_changed_row_count": _to_int(summary.get("preview_changed_row_count")),
            "worsened_row_count": _to_int(summary.get("worsened_row_count")),
            "baseline_hold_precision": round(_to_float(summary.get("baseline_hold_precision")), 6),
            "preview_hold_precision": round(_to_float(summary.get("preview_hold_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(_to_float(summary.get("baseline_runtime_proxy_match_rate")), 6),
            "preview_runtime_proxy_match_rate": round(_to_float(summary.get("preview_runtime_proxy_match_rate")), 6),
        },
        "approval_conditions": [
            "Approve only if the scope remains NAS100 / continuation_hold_surface / RUNNER_CHECK / profit_hold_bias.",
            "Approve only if the action change stays HOLD -> PARTIAL_THEN_HOLD.",
            "Approve only if scene bias remains excluded.",
            "Approve only if size change and new entry logic remain disabled.",
            "Approve only if rollback triggers stay immediate and explicit.",
        ],
        "decision_options": [
            "approve_narrow_bounded_action_only_canary",
            "hold_and_collect_more_evidence",
            "reject_and_return_to_preview_only",
        ],
        "scope_snapshot": activation_scope,
        "guardrail_snapshot": activation_guardrails,
    }


def render_checkpoint_pa8_nas100_action_only_canary_activation_review_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    approval_conditions = list(body.get("approval_conditions", []) or [])
    decision_options = list(body.get("decision_options", []) or [])
    scope_snapshot = _mapping(body.get("scope_snapshot"))

    lines: list[str] = []
    lines.append("# PA8 NAS100 Action-Only Canary Activation Human Review")
    lines.append("")
    lines.append(f"- review_state: `{_to_text(summary.get('review_state'))}`")
    lines.append(f"- activation_state: `{_to_text(summary.get('activation_state'))}`")
    lines.append(f"- allow_activation: `{summary.get('allow_activation', False)}`")
    lines.append(f"- review_question: {_to_text(summary.get('review_question'))}")
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append(f"- baseline_hold_precision: `{_to_float(summary.get('baseline_hold_precision'))}`")
    lines.append(f"- preview_hold_precision: `{_to_float(summary.get('preview_hold_precision'))}`")
    lines.append(
        f"- baseline_runtime_proxy_match_rate: `{_to_float(summary.get('baseline_runtime_proxy_match_rate'))}`"
    )
    lines.append(
        f"- preview_runtime_proxy_match_rate: `{_to_float(summary.get('preview_runtime_proxy_match_rate'))}`"
    )
    lines.append("")
    lines.append("## Scope Snapshot")
    lines.append("")
    for key in ("symbol_allowlist", "surface_allowlist", "checkpoint_type_allowlist", "family_allowlist", "candidate_action"):
        lines.append(f"- {key}: `{scope_snapshot.get(key)}`")
    lines.append("")
    lines.append("## Approval Conditions")
    lines.append("")
    for item in approval_conditions:
        lines.append(f"- [ ] {_to_text(item)}")
    lines.append("")
    lines.append("## Decision Options")
    lines.append("")
    for item in decision_options:
        lines.append(f"- `{_to_text(item)}`")
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
