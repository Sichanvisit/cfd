from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_nas100_action_only_canary_monitoring_packet_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_monitoring_packet_latest.json"
    )


def default_checkpoint_pa8_nas100_action_only_canary_monitoring_packet_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_monitoring_packet_latest.md"
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


def build_checkpoint_pa8_nas100_action_only_canary_monitoring_packet(
    *,
    activation_packet_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    packet = _mapping(activation_packet_payload)
    summary = _mapping(packet.get("summary"))
    monitoring_plan = _mapping(packet.get("monitoring_plan"))
    allow_activation = bool(summary.get("allow_activation"))
    blockers = list(summary.get("blockers", []) or [])

    monitoring_state = (
        "READY_TO_START_FIRST_CANARY_WINDOW"
        if allow_activation and not blockers
        else "HOLD_MONITORING_PACKET"
    )
    first_window_status = (
        "AWAIT_FIRST_CANARY_WINDOW_RESULTS"
        if monitoring_state == "READY_TO_START_FIRST_CANARY_WINDOW"
        else "MONITORING_NOT_READY"
    )
    recommended_next_action = (
        "start_collecting_first_canary_window_observations"
        if monitoring_state == "READY_TO_START_FIRST_CANARY_WINDOW"
        else "keep_monitoring_packet_in_hold"
    )

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_canary_monitoring_packet_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol": _to_text(summary.get("symbol"), "NAS100"),
            "activation_state": _to_text(summary.get("activation_state")),
            "monitoring_state": monitoring_state,
            "first_window_status": first_window_status,
            "recommended_next_action": recommended_next_action,
            "blockers": blockers,
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
            "observed_window_row_count": 0,
            "current_hold_precision": None,
            "current_runtime_proxy_match_rate": None,
            "current_partial_then_hold_quality": None,
            "new_worsened_rows": 0,
        },
        "tracked_metrics": list(monitoring_plan.get("compare_against_baseline_metrics", []) or []),
        "monitoring_questions": [
            "Does hold_precision remain above the baseline once the canary is observed live?",
            "Does runtime_proxy_match_rate remain above the baseline during the first window?",
            "Does partial_then_hold_quality stay at or above the preview expectation?",
            "Do any new worsened rows appear in the scoped family?",
        ],
        "success_criteria": [
            "hold_precision stays above baseline",
            "runtime_proxy_match_rate stays above baseline",
            "partial_then_hold_quality does not regress",
            "new_worsened_rows remains zero",
        ],
        "fail_fast_triggers": [
            "hold_precision_drop_below_baseline",
            "runtime_proxy_match_rate_drop_below_baseline",
            "partial_then_hold_quality_regression",
            "new_worsened_rows_detected",
        ],
    }


def render_checkpoint_pa8_nas100_action_only_canary_monitoring_packet_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    tracked_metrics = list(body.get("tracked_metrics", []) or [])
    monitoring_questions = list(body.get("monitoring_questions", []) or [])
    success_criteria = list(body.get("success_criteria", []) or [])
    fail_fast_triggers = list(body.get("fail_fast_triggers", []) or [])

    lines: list[str] = []
    lines.append("# PA8 NAS100 Action-Only Canary Monitoring Packet")
    lines.append("")
    lines.append(f"- monitoring_state: `{_to_text(summary.get('monitoring_state'))}`")
    lines.append(f"- first_window_status: `{_to_text(summary.get('first_window_status'))}`")
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
    lines.append("## Tracked Metrics")
    lines.append("")
    for item in tracked_metrics:
        lines.append(f"- `{_to_text(item)}`")
    lines.append("")
    lines.append("## Monitoring Questions")
    lines.append("")
    for item in monitoring_questions:
        lines.append(f"- [ ] {_to_text(item)}")
    lines.append("")
    lines.append("## Success Criteria")
    lines.append("")
    for item in success_criteria:
        lines.append(f"- `{_to_text(item)}`")
    lines.append("")
    lines.append("## Fail-Fast Triggers")
    lines.append("")
    for item in fail_fast_triggers:
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
