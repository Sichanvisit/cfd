from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_latest.json"
    )


def default_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_latest.md"
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


def build_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet(
    *,
    activation_packet_payload: Mapping[str, Any] | None,
    monitoring_packet_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    activation = _mapping(activation_packet_payload)
    activation_summary = _mapping(activation.get("summary"))
    activation_guardrails = _mapping(activation.get("activation_guardrails"))
    monitoring = _mapping(monitoring_packet_payload)
    monitoring_summary = _mapping(monitoring.get("summary"))

    blockers = list(activation_summary.get("blockers", []) or [])
    activation_ready = bool(activation_summary.get("allow_activation"))
    monitoring_ready = _to_text(monitoring_summary.get("monitoring_state")) == "READY_TO_START_FIRST_CANARY_WINDOW"

    rollback_review_state = (
        "READY_WITH_NO_TRIGGER_ACTIVE"
        if activation_ready and monitoring_ready and not blockers
        else "HOLD_ROLLBACK_REVIEW_PACKET"
    )
    recommended_next_action = (
        "keep_rollback_packet_ready_during_first_canary_window"
        if rollback_review_state == "READY_WITH_NO_TRIGGER_ACTIVE"
        else "resolve_activation_or_monitoring_blockers_first"
    )

    rollback_triggers = list(activation_guardrails.get("rollback_watch_metrics", []) or [])
    current_trigger_state = "no_active_trigger_detected"

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_canary_rollback_review_packet_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol": _to_text(activation_summary.get("symbol"), "NAS100"),
            "activation_state": _to_text(activation_summary.get("activation_state")),
            "monitoring_state": _to_text(monitoring_summary.get("monitoring_state")),
            "rollback_review_state": rollback_review_state,
            "current_trigger_state": current_trigger_state,
            "recommended_next_action": recommended_next_action,
            "blockers": blockers,
            "baseline_hold_precision": round(_to_float(activation_summary.get("baseline_hold_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(
                _to_float(activation_summary.get("baseline_runtime_proxy_match_rate")),
                6,
            ),
            "baseline_partial_then_hold_quality": round(
                _to_float(activation_summary.get("baseline_partial_then_hold_quality")),
                6,
            ),
        },
        "rollback_triggers": rollback_triggers,
        "rollback_actions": [
            "disable_nas100_action_only_canary_scope",
            "return_to_baseline_action_behavior",
            "record_rollback_reason_and_window_metrics",
        ],
        "rollback_questions": [
            "Did hold_precision drop below baseline?",
            "Did runtime_proxy_match_rate drop below baseline?",
            "Did partial_then_hold_quality regress below baseline?",
            "Did any new worsened rows appear in the scoped family?",
        ],
    }


def render_checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rollback_triggers = list(body.get("rollback_triggers", []) or [])
    rollback_actions = list(body.get("rollback_actions", []) or [])
    rollback_questions = list(body.get("rollback_questions", []) or [])

    lines: list[str] = []
    lines.append("# PA8 NAS100 Action-Only Canary Rollback Review Packet")
    lines.append("")
    lines.append(f"- rollback_review_state: `{_to_text(summary.get('rollback_review_state'))}`")
    lines.append(f"- current_trigger_state: `{_to_text(summary.get('current_trigger_state'))}`")
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append(f"- baseline_hold_precision: `{_to_float(summary.get('baseline_hold_precision'))}`")
    lines.append(
        f"- baseline_runtime_proxy_match_rate: `{_to_float(summary.get('baseline_runtime_proxy_match_rate'))}`"
    )
    lines.append(
        f"- baseline_partial_then_hold_quality: `{_to_float(summary.get('baseline_partial_then_hold_quality'))}`"
    )
    lines.append("")
    lines.append("## Rollback Triggers")
    lines.append("")
    for item in rollback_triggers:
        lines.append(f"- `{_to_text(item)}`")
    lines.append("")
    lines.append("## Rollback Questions")
    lines.append("")
    for item in rollback_questions:
        lines.append(f"- [ ] {_to_text(item)}")
    lines.append("")
    lines.append("## Rollback Actions")
    lines.append("")
    for item in rollback_actions:
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
