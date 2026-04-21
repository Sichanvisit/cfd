from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_nas100_action_only_canary_closeout_decision_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_closeout_decision_latest.json"
    )


def default_checkpoint_pa8_nas100_action_only_canary_closeout_decision_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_closeout_decision_latest.md"
    )


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def build_checkpoint_pa8_nas100_action_only_canary_closeout_decision(
    *,
    activation_apply_payload: Mapping[str, Any] | None,
    first_window_observation_payload: Mapping[str, Any] | None,
    rollback_review_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    activation = _mapping(activation_apply_payload)
    activation_summary = _mapping(activation.get("summary"))
    observation = _mapping(first_window_observation_payload)
    observation_summary = _mapping(observation.get("summary"))
    active_triggers = list(observation.get("active_triggers", []) or [])
    rollback = _mapping(rollback_review_payload)
    rollback_summary = _mapping(rollback.get("summary"))

    active = bool(activation_summary.get("active"))
    live_observation_ready = bool(observation_summary.get("live_observation_ready"))
    observed_window_row_count = _to_int(observation_summary.get("observed_window_row_count"))
    sample_floor = _to_int(_mapping(activation.get("active_state")).get("guardrails", {}).get("sample_floor"), 0)

    if not active:
        closeout_state = "HOLD_CLOSEOUT_CANARY_NOT_ACTIVE"
        decision = "do_not_closeout_inactive_canary"
        recommended_next_action = "activate_canary_before_closeout_review"
    elif not live_observation_ready:
        closeout_state = "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW"
        decision = "keep_canary_active_and_collect_live_rows"
        recommended_next_action = "wait_for_live_first_window_rows_before_pa8_closeout"
    elif active_triggers:
        closeout_state = "ROLLBACK_REQUIRED"
        decision = "rollback_canary_scope_immediately"
        recommended_next_action = "disable_canary_and_return_to_baseline_action_behavior"
    elif observed_window_row_count < sample_floor:
        closeout_state = "HOLD_CLOSEOUT_PENDING_SAMPLE_FLOOR"
        decision = "keep_canary_active_until_sample_floor_reached"
        recommended_next_action = "continue_bounded_canary_until_sample_floor_is_met"
    else:
        closeout_state = "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW"
        decision = "promote_action_only_canary_results_to_pa9_review"
        recommended_next_action = "prepare_pa9_action_baseline_handoff_packet"

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_canary_closeout_decision_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol": _to_text(activation_summary.get("symbol"), "NAS100"),
            "activation_apply_state": _to_text(activation_summary.get("activation_apply_state")),
            "first_window_status": _to_text(observation_summary.get("first_window_status")),
            "rollback_review_state": _to_text(rollback_summary.get("rollback_review_state")),
            "closeout_state": closeout_state,
            "decision": decision,
            "recommended_next_action": recommended_next_action,
            "live_observation_ready": live_observation_ready,
            "observed_window_row_count": observed_window_row_count,
            "sample_floor": sample_floor,
            "current_hold_precision": observation_summary.get("current_hold_precision"),
            "current_runtime_proxy_match_rate": observation_summary.get("current_runtime_proxy_match_rate"),
            "current_partial_then_hold_quality": observation_summary.get("current_partial_then_hold_quality"),
            "new_worsened_rows": _to_int(observation_summary.get("new_worsened_rows")),
            "active_trigger_count": len(active_triggers),
        },
        "active_triggers": active_triggers,
        "closeout_questions": [
            "Are there enough post-activation live rows to close the first canary window?",
            "Did hold_precision stay above the baseline during the observed window?",
            "Did runtime_proxy_match_rate improve without introducing worsened rows?",
            "Should PA8 stay open because the current window is still preview-seeded only?",
        ],
    }


def render_checkpoint_pa8_nas100_action_only_canary_closeout_decision_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    active_triggers = list(body.get("active_triggers", []) or [])
    closeout_questions = list(body.get("closeout_questions", []) or [])

    lines: list[str] = []
    lines.append("# PA8 NAS100 Action-Only Canary Closeout Decision")
    lines.append("")
    lines.append(f"- closeout_state: `{_to_text(summary.get('closeout_state'))}`")
    lines.append(f"- decision: `{_to_text(summary.get('decision'))}`")
    lines.append(f"- first_window_status: `{_to_text(summary.get('first_window_status'))}`")
    lines.append(f"- live_observation_ready: `{summary.get('live_observation_ready', False)}`")
    lines.append(f"- observed_window_row_count: `{_to_int(summary.get('observed_window_row_count'))}`")
    lines.append(f"- sample_floor: `{_to_int(summary.get('sample_floor'))}`")
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append("")
    lines.append("## Active Triggers")
    lines.append("")
    if active_triggers:
        for item in active_triggers:
            lines.append(f"- `{_to_text(item)}`")
    else:
        lines.append("- `none`")
    lines.append("")
    lines.append("## Closeout Questions")
    lines.append("")
    for item in closeout_questions:
        lines.append(f"- [ ] {_to_text(item)}")
    return "\n".join(lines).rstrip() + "\n"
