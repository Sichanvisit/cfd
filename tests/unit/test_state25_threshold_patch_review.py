from __future__ import annotations

from backend.services.state25_context_bridge import (
    build_state25_candidate_context_bridge_v1,
)
from backend.services.state25_threshold_patch_review import (
    build_state25_threshold_patch_review_candidate_from_context_bridge_v1,
    build_state25_threshold_patch_review_candidate_v1,
)


def _threshold_runtime_row() -> dict[str, object]:
    return {
        "symbol": "NAS100",
        "entry_stage": "balanced",
        "consumer_check_side": "SELL",
        "signal_timeframe": "15M",
        "context_bundle_summary_ko": "HTF 전체 상승 정렬 | 직전 박스 상단 돌파 유지 | 늦은 추격 위험 높음",
        "context_conflict_label_ko": "직전 박스와 상위 추세 모두 역행",
        "htf_alignment_state": "AGAINST_HTF",
        "htf_alignment_detail": "AGAINST_HTF_UP",
        "htf_against_severity": "HIGH",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_lifecycle": "RETESTED",
        "previous_box_confidence": "HIGH",
        "previous_box_is_consolidation": True,
        "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        "context_conflict_intensity": "HIGH",
        "late_chase_risk_state": "HIGH",
        "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
        "late_chase_confidence": 0.82,
        "trend_1h_age_seconds": 60,
        "trend_4h_age_seconds": 60,
        "trend_1d_age_seconds": 60,
        "previous_box_age_seconds": 60,
        "effective_entry_threshold": 40,
        "final_score": 42,
    }


def test_state25_threshold_patch_review_candidate_builds_log_only_envelope() -> None:
    payload = build_state25_threshold_patch_review_candidate_v1(
        concern_summary_ko="NAS100 SELL 진입에서 상위 추세 역행 맥락이 관찰됩니다.",
        current_behavior_ko="현재는 SELL 진입을 그대로 유지하고 있습니다.",
        proposed_behavior_ko="threshold harden을 먼저 log-only로 관찰합니다.",
        evidence_summary_ko="AGAINST_HTF 기준 requested +3.20pt가 계산됐습니다.",
        threshold_delta_points_requested=3.2,
        threshold_delta_points_effective=3.2,
        threshold_delta_pct_requested=0.08,
        threshold_delta_pct_effective=0.08,
        threshold_delta_direction="HARDEN",
        threshold_delta_reason_keys=["AGAINST_HTF"],
        state25_execution_symbol_allowlist=["NAS100"],
        state25_execution_entry_stage_allowlist=["balanced"],
        state25_execution_bind_mode="log_only",
        candidate_id="threshold-review-1",
        trace_id="trace-threshold-review-1",
    )

    assert payload["review_type"] == "STATE25_THRESHOLD_PATCH_REVIEW"
    assert payload["action_target"] == "state25_threshold_patch_log_only"
    assert payload["threshold_patch"]["state25_threshold_log_only_enabled"] is True
    assert payload["threshold_patch"]["state25_threshold_bounded_live_enabled"] is False
    assert (
        payload["recommended_action_ko"]
        == "bounded log-only threshold harden review를 먼저 backlog에 올립니다."
    )


def test_state25_threshold_patch_review_candidate_supports_bounded_live_contract() -> None:
    payload = build_state25_threshold_patch_review_candidate_v1(
        concern_summary_ko="XAUUSD SELL 진입에서 직전 박스와 상위 추세 모두 역행입니다.",
        current_behavior_ko="현재는 SELL 해석을 그대로 유지하고 있습니다.",
        proposed_behavior_ko="threshold harden을 bounded live로 아주 좁게 시험합니다.",
        evidence_summary_ko="AGAINST_PREV_BOX_AND_HTF 기준 requested +3.40pt가 계산됐습니다.",
        threshold_delta_points_requested=3.4,
        threshold_delta_points_effective=3.4,
        threshold_delta_pct_requested=0.1,
        threshold_delta_pct_effective=0.1,
        threshold_delta_direction="HARDEN",
        threshold_delta_reason_keys=["AGAINST_PREV_BOX_AND_HTF"],
        state25_execution_symbol_allowlist=["XAUUSD"],
        state25_execution_entry_stage_allowlist=["balanced"],
        state25_execution_bind_mode="bounded_live",
        candidate_id="threshold-review-live-1",
        trace_id="trace-threshold-review-live-1",
    )

    assert payload["action_target"] == "state25_threshold_patch_bounded_live"
    assert payload["state25_execution_bind_mode"] == "bounded_live"
    assert payload["threshold_patch"]["state25_threshold_log_only_enabled"] is False
    assert payload["threshold_patch"]["state25_threshold_bounded_live_enabled"] is True
    assert (
        payload["recommended_next_action"]
        == "review_state25_threshold_patch_and_activate_bounded_live_if_safe"
    )


def test_state25_threshold_patch_review_candidate_from_context_bridge_builds_preview() -> None:
    runtime_row = _threshold_runtime_row()
    runtime_row["state25_candidate_context_bridge_v1"] = build_state25_candidate_context_bridge_v1(
        runtime_row
    )

    payload = build_state25_threshold_patch_review_candidate_from_context_bridge_v1(
        runtime_row
    )

    assert payload["review_type"] == "STATE25_THRESHOLD_PATCH_REVIEW"
    assert payload["bridge_source_lane"] == "STATE25_CONTEXT_BRIDGE_THRESHOLD_LOG_ONLY"
    assert payload["bridge_threshold_requested_points"] > 0.0
    assert payload["bridge_threshold_changed_decision"] is True
    assert payload["registry_key"] == "state25_threshold:entry_harden_delta_points"
    assert (
        payload["proposal_envelope"]["evidence_snapshot"]["bridge_threshold_changed_decision"]
        is True
    )


def test_state25_threshold_patch_review_candidate_from_context_bridge_supports_bounded_live() -> None:
    runtime_row = _threshold_runtime_row()
    runtime_row["state25_candidate_context_bridge_v1"] = build_state25_candidate_context_bridge_v1(
        runtime_row
    )

    payload = build_state25_threshold_patch_review_candidate_from_context_bridge_v1(
        runtime_row,
        state25_execution_bind_mode="bounded_live",
    )

    assert payload["state25_execution_bind_mode"] == "bounded_live"
    assert payload["action_target"] == "state25_threshold_patch_bounded_live"
    assert payload["bridge_source_lane"] == "STATE25_CONTEXT_BRIDGE_THRESHOLD_BOUNDED_LIVE"


def test_state25_threshold_patch_review_candidate_rebuilds_stale_nested_bridge() -> None:
    runtime_row = _threshold_runtime_row()
    runtime_row["state25_candidate_context_bridge_v1"] = {
        "threshold_adjustment_requested": {"threshold_delta_points": 0.0},
        "threshold_adjustment_effective": {"threshold_delta_points": 0.0},
        "threshold_adjustment_suppressed": {},
    }

    payload = build_state25_threshold_patch_review_candidate_from_context_bridge_v1(
        runtime_row
    )

    assert payload["bridge_threshold_requested_points"] > 0.0
    assert payload["bridge_without_bridge_decision"] == "ENTER"
    assert payload["bridge_with_bridge_decision"] == "SKIP"
