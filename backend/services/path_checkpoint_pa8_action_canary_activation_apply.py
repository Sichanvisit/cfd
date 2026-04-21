from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_nas100_action_only_canary_activation_apply_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_activation_apply_latest.json"
    )


def default_checkpoint_pa8_nas100_action_only_canary_activation_apply_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_activation_apply_latest.md"
    )


def default_checkpoint_pa8_nas100_action_only_canary_active_state_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_active_state_latest.json"
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


def _normalize_decision(value: object) -> str:
    decision = str(value or "").strip().upper()
    if decision in {"APPROVE", "HOLD", "REJECT"}:
        return decision
    return "HOLD"


def build_checkpoint_pa8_nas100_action_only_canary_activation_apply(
    *,
    activation_review_payload: Mapping[str, Any] | None,
    activation_packet_payload: Mapping[str, Any] | None = None,
    approval_decision: str = "APPROVE",
    approval_actor: str = "user_requested_manual_activation",
    approval_reason: str = "explicit_user_request_to_start_pa8_nas100_action_only_canary",
) -> dict[str, Any]:
    review = _mapping(activation_review_payload)
    review_summary = _mapping(review.get("summary"))
    activation_packet = _mapping(activation_packet_payload)
    activation_packet_summary = _mapping(activation_packet.get("summary"))
    scope_snapshot = _mapping(review.get("scope_snapshot"))
    guardrail_snapshot = _mapping(review.get("guardrail_snapshot"))

    decision = _normalize_decision(approval_decision)
    review_ready = _to_text(review_summary.get("review_state")) == "READY_FOR_HUMAN_ACTIVATION_DECISION"
    allow_activation = bool(review_summary.get("allow_activation"))
    blockers = list(review_summary.get("blockers", []) or [])
    generated_at = datetime.now().astimezone().isoformat()

    if not review_ready or not allow_activation or blockers:
        activation_apply_state = "HOLD_CANARY_ACTIVATION_APPLY"
        approval_state = "ACTIVATION_NOT_READY"
        active = False
        recommended_next_action = "resolve_activation_review_blockers_first"
    elif decision == "APPROVE":
        activation_apply_state = "ACTIVE_ACTION_ONLY_CANARY"
        approval_state = "MANUAL_ACTIVATION_APPROVED"
        active = True
        recommended_next_action = "start_first_canary_window_observation"
    elif decision == "REJECT":
        activation_apply_state = "REJECTED_ACTION_ONLY_CANARY"
        approval_state = "MANUAL_ACTIVATION_REJECTED"
        active = False
        recommended_next_action = "return_to_preview_only_and_collect_more_evidence"
    else:
        activation_apply_state = "HELD_ACTION_ONLY_CANARY"
        approval_state = "MANUAL_ACTIVATION_HELD"
        active = False
        recommended_next_action = "hold_canary_activation_and_revisit_later"

    active_state = {
        "contract_version": "checkpoint_pa8_action_canary_active_state_v1",
        "activation_id": _to_text(scope_snapshot.get("activation_id")),
        "symbol": _to_text(review_summary.get("symbol"), "NAS100"),
        "activation_apply_state": activation_apply_state,
        "approval_state": approval_state,
        "active": active,
        "activated_at": generated_at if active else "",
        "first_window_started_at": generated_at if active else "",
        "window_status": "FIRST_CANARY_WINDOW_ACTIVE" if active else "WINDOW_NOT_ACTIVE",
        "scope": {
            "symbol_allowlist": list(scope_snapshot.get("symbol_allowlist", []) or []),
            "surface_allowlist": list(scope_snapshot.get("surface_allowlist", []) or []),
            "checkpoint_type_allowlist": list(scope_snapshot.get("checkpoint_type_allowlist", []) or []),
            "family_allowlist": list(scope_snapshot.get("family_allowlist", []) or []),
            "baseline_action_allowlist": list(scope_snapshot.get("baseline_action_allowlist", []) or []),
            "candidate_action": _to_text(scope_snapshot.get("candidate_action")),
            "candidate_reason": _to_text(scope_snapshot.get("candidate_reason")),
            "scene_bias_excluded": bool(scope_snapshot.get("scene_bias_excluded", True)),
        },
        "guardrails": {
            "sample_floor": _to_int(guardrail_snapshot.get("sample_floor")),
            "worsened_row_count_ceiling": _to_int(guardrail_snapshot.get("worsened_row_count_ceiling")),
            "hold_precision_floor": round(_to_float(guardrail_snapshot.get("hold_precision_floor")), 6),
            "runtime_proxy_match_rate_must_improve": bool(
                guardrail_snapshot.get("runtime_proxy_match_rate_must_improve")
            ),
            "partial_then_hold_quality_must_not_regress": bool(
                guardrail_snapshot.get("partial_then_hold_quality_must_not_regress")
            ),
            "rollback_watch_metrics": list(guardrail_snapshot.get("rollback_watch_metrics", []) or []),
        },
    }

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_canary_activation_apply_v1",
            "generated_at": generated_at,
            "symbol": _to_text(review_summary.get("symbol"), "NAS100"),
            "review_state": _to_text(review_summary.get("review_state")),
            "approval_decision": decision,
            "approval_actor": approval_actor,
            "approval_reason": approval_reason,
            "approval_state": approval_state,
            "activation_apply_state": activation_apply_state,
            "active": active,
            "eligible_row_count": _to_int(review_summary.get("eligible_row_count")),
            "preview_changed_row_count": _to_int(review_summary.get("preview_changed_row_count")),
            "worsened_row_count": _to_int(review_summary.get("worsened_row_count")),
            "baseline_hold_precision": round(_to_float(review_summary.get("baseline_hold_precision")), 6),
            "preview_hold_precision": round(_to_float(review_summary.get("preview_hold_precision")), 6),
            "baseline_runtime_proxy_match_rate": round(
                _to_float(review_summary.get("baseline_runtime_proxy_match_rate")),
                6,
            ),
            "preview_runtime_proxy_match_rate": round(
                _to_float(review_summary.get("preview_runtime_proxy_match_rate")),
                6,
            ),
            "baseline_partial_then_hold_quality": round(
                _to_float(
                    review_summary.get("baseline_partial_then_hold_quality"),
                    _to_float(activation_packet_summary.get("baseline_partial_then_hold_quality")),
                ),
                6,
            ),
            "preview_partial_then_hold_quality": round(
                _to_float(
                    review_summary.get("preview_partial_then_hold_quality"),
                    _to_float(activation_packet_summary.get("preview_partial_then_hold_quality")),
                ),
                6,
            ),
            "blockers": blockers,
            "recommended_next_action": recommended_next_action,
        },
        "scope_snapshot": scope_snapshot,
        "guardrail_snapshot": guardrail_snapshot,
        "active_state": active_state,
    }


def render_checkpoint_pa8_nas100_action_only_canary_activation_apply_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    active_state = _mapping(body.get("active_state"))
    scope = _mapping(active_state.get("scope"))

    lines: list[str] = []
    lines.append("# PA8 NAS100 Action-Only Canary Activation Apply")
    lines.append("")
    lines.append(f"- review_state: `{_to_text(summary.get('review_state'))}`")
    lines.append(f"- approval_decision: `{_to_text(summary.get('approval_decision'))}`")
    lines.append(f"- approval_state: `{_to_text(summary.get('approval_state'))}`")
    lines.append(f"- activation_apply_state: `{_to_text(summary.get('activation_apply_state'))}`")
    lines.append(f"- active: `{summary.get('active', False)}`")
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append(f"- preview_hold_precision: `{_to_float(summary.get('preview_hold_precision'))}`")
    lines.append(f"- preview_runtime_proxy_match_rate: `{_to_float(summary.get('preview_runtime_proxy_match_rate'))}`")
    lines.append("")
    lines.append("## Active Scope")
    lines.append("")
    lines.append(f"- symbol_allowlist: `{scope.get('symbol_allowlist', [])}`")
    lines.append(f"- surface_allowlist: `{scope.get('surface_allowlist', [])}`")
    lines.append(f"- checkpoint_type_allowlist: `{scope.get('checkpoint_type_allowlist', [])}`")
    lines.append(f"- family_allowlist: `{scope.get('family_allowlist', [])}`")
    lines.append(f"- baseline_action_allowlist: `{scope.get('baseline_action_allowlist', [])}`")
    lines.append(f"- candidate_action: `{_to_text(scope.get('candidate_action'))}`")
    lines.append(f"- candidate_reason: `{_to_text(scope.get('candidate_reason'))}`")
    lines.append("")
    blockers = list(summary.get("blockers", []) or [])
    lines.append("## Blockers")
    lines.append("")
    if blockers:
        for item in blockers:
            lines.append(f"- `{_to_text(item)}`")
    else:
        lines.append("- `none`")
    return "\n".join(lines).rstrip() + "\n"
