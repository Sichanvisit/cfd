from __future__ import annotations

from backend.services.state25_context_bridge import (
    build_state25_candidate_context_bridge_v1,
)
from backend.services.state25_weight_patch_review import (
    build_state25_weight_patch_review_candidate_from_context_bridge_v1,
    build_state25_weight_patch_review_candidate_v1,
)


def test_state25_weight_patch_review_candidate_builds_envelope_and_scope() -> None:
    payload = build_state25_weight_patch_review_candidate_v1(
        concern_summary_ko="상단 꼬리 해석이 과하게 작동합니다.",
        current_behavior_ko="상단 꼬리 반응을 너무 강하게 읽고 있습니다.",
        proposed_behavior_ko="상단 꼬리 비중을 줄이고 방향 비중을 상대적으로 올립니다.",
        evidence_summary_ko="BTC 최근 장면에서 상방 추세 대비 과한 반전 해석이 반복됐습니다.",
        state25_teacher_weight_overrides={
            "upper_wick_weight": 0.6,
            "directional_bias_weight": 1.1,
        },
        state25_execution_symbol_allowlist=["BTCUSD"],
        state25_execution_entry_stage_allowlist=["READY"],
        trace_id="trace-weight-btc",
    )

    envelope = payload["proposal_envelope"]

    assert payload["review_type"] == "STATE25_WEIGHT_PATCH_REVIEW"
    assert payload["action_target"] == "state25_weight_patch_log_only"
    assert payload["scope_key"].startswith("STATE25_WEIGHT_PATCH::BTCUSD::READY")
    assert payload["proposal_id"] == envelope["proposal_id"]
    assert envelope["proposal_type"] == "STATE25_WEIGHT_PATCH_REVIEW"
    assert envelope["trace_id"] == "trace-weight-btc"
    assert envelope["recommended_action_ko"] == "bounded log-only 가중치 조정을 시험 반영합니다."
    assert payload["weight_patch"]["state25_weight_log_only_enabled"] is True
    assert payload["weight_patch"]["state25_weight_bounded_live_enabled"] is False


def test_state25_weight_patch_review_candidate_supports_bounded_live_contract() -> None:
    payload = build_state25_weight_patch_review_candidate_v1(
        concern_summary_ko="상위 추세 역행 해석이 과합니다.",
        current_behavior_ko="반전 위험을 과하게 읽고 있습니다.",
        proposed_behavior_ko="bounded live로 reversal risk를 낮추고 directional bias를 높입니다.",
        evidence_summary_ko="XAUUSD에서 bounded live weight canary를 점검합니다.",
        state25_teacher_weight_overrides={
            "reversal_risk_weight": 0.8,
            "directional_bias_weight": 1.12,
        },
        state25_execution_symbol_allowlist=["XAUUSD"],
        state25_execution_entry_stage_allowlist=["READY"],
        state25_execution_bind_mode="bounded_live",
        trace_id="trace-weight-live",
    )

    assert payload["action_target"] == "state25_weight_patch_bounded_live"
    assert payload["state25_execution_bind_mode"] == "bounded_live"
    assert payload["weight_patch"]["state25_weight_log_only_enabled"] is False
    assert payload["weight_patch"]["state25_weight_bounded_live_enabled"] is True
    assert (
        payload["recommended_next_action"]
        == "review_state25_weight_patch_and_activate_bounded_live_if_safe"
    )


def test_state25_weight_patch_review_candidate_attaches_direct_binding_fields() -> None:
    payload = build_state25_weight_patch_review_candidate_v1(
        concern_summary_ko="상단 꼬리 해석이 과합니다.",
        current_behavior_ko="상단 꼬리 반응을 과하게 읽고 있습니다.",
        proposed_behavior_ko="상단 꼬리 비중을 줄여 log-only로 봅니다.",
        evidence_summary_ko="BTCUSD에서 상단 꼬리 반응 과해석이 반복됐습니다.",
        state25_teacher_weight_overrides={
            "upper_wick_weight": 0.6,
        },
        evidence_registry_keys=[
            "misread:upper_wick_ratio",
            "misread:result_type",
        ],
        trace_id="trace-db2-single",
    )

    assert payload["registry_key"] == "state25_weight:upper_wick_weight"
    assert payload["registry_binding_mode"] == "exact"
    assert payload["registry_binding_ready"] is True
    assert payload["target_registry_keys"] == ["state25_weight:upper_wick_weight"]
    assert payload["evidence_registry_keys"] == [
        "misread:upper_wick_ratio",
        "misread:result_type",
    ]


def test_state25_weight_patch_review_candidate_marks_multi_weight_binding_as_derived() -> None:
    payload = build_state25_weight_patch_review_candidate_v1(
        concern_summary_ko="상단 거부와 반전 위험을 같이 줄여야 합니다.",
        current_behavior_ko="여러 반전 신호를 동시에 과하게 읽고 있습니다.",
        proposed_behavior_ko="두 가중치를 같이 조정해 log-only로 봅니다.",
        evidence_summary_ko="XAUUSD에서 상단 거부 복합 패턴이 반복됐습니다.",
        state25_teacher_weight_overrides={
            "upper_wick_weight": 0.7,
            "reversal_risk_weight": 1.15,
        },
        trace_id="trace-db2-multi",
    )

    assert payload["registry_binding_mode"] == "derived"
    assert set(payload["target_registry_keys"]) == {
        "state25_weight:upper_wick_weight",
        "state25_weight:reversal_risk_weight",
    }
    assert payload["weight_patch"]["target_registry_keys"] == payload["target_registry_keys"]
    assert len(payload["target_bindings"]) == 2


def test_state25_weight_patch_review_candidate_from_context_bridge_carries_bridge_trace() -> None:
    runtime_row = {
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
        "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        "context_conflict_intensity": "HIGH",
        "late_chase_risk_state": "HIGH",
        "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
        "trend_1h_age_seconds": 120,
        "trend_4h_age_seconds": 120,
        "trend_1d_age_seconds": 120,
        "previous_box_age_seconds": 60,
    }
    runtime_row["state25_candidate_context_bridge_v1"] = build_state25_candidate_context_bridge_v1(
        runtime_row
    )

    payload = build_state25_weight_patch_review_candidate_from_context_bridge_v1(runtime_row)

    assert payload["review_type"] == "STATE25_WEIGHT_PATCH_REVIEW"
    assert payload["bridge_source_lane"] == "STATE25_CONTEXT_BRIDGE_WEIGHT_ONLY_LOG_ONLY"
    assert payload["bridge_weight_requested_count"] >= 1
    assert payload["bridge_weight_effective_count"] >= 1
    assert payload["bridge_context_summary_ko"]
    assert "misread:htf_alignment_state" in payload["evidence_registry_keys"]
    assert payload["proposal_envelope"]["evidence_snapshot"]["bridge_weight_requested_count"] >= 1


def test_state25_weight_patch_review_candidate_from_context_bridge_supports_bounded_live() -> None:
    runtime_row = {
        "symbol": "XAUUSD",
        "entry_stage": "balanced",
        "consumer_check_side": "SELL",
        "signal_timeframe": "15M",
        "context_bundle_summary_ko": "HTF 대체로 상승 정렬 | 직전 박스 상단 돌파 유지 | 역행 SELL 경계",
        "context_conflict_label_ko": "상위 추세와 직전 박스 모두 역행",
        "htf_alignment_state": "AGAINST_HTF",
        "htf_alignment_detail": "AGAINST_HTF_UP",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_lifecycle": "BROKEN",
        "previous_box_confidence": "HIGH",
        "previous_box_is_consolidation": True,
        "trend_1h_age_seconds": 60,
        "trend_4h_age_seconds": 60,
        "trend_1d_age_seconds": 60,
        "previous_box_age_seconds": 60,
    }
    runtime_row["state25_candidate_context_bridge_v1"] = build_state25_candidate_context_bridge_v1(
        runtime_row
    )

    payload = build_state25_weight_patch_review_candidate_from_context_bridge_v1(
        runtime_row,
        state25_execution_bind_mode="bounded_live",
    )

    assert payload["state25_execution_bind_mode"] == "bounded_live"
    assert payload["action_target"] == "state25_weight_patch_bounded_live"
    assert payload["bridge_source_lane"] == "STATE25_CONTEXT_BRIDGE_WEIGHT_ONLY_BOUNDED_LIVE"


def test_state25_weight_patch_review_candidate_from_low_confidence_relief_surfaces_requested_review() -> None:
    runtime_row = {
        "symbol": "BTCUSD",
        "entry_stage": "balanced",
        "consumer_check_side": "SELL",
        "signal_timeframe": "15M",
        "context_bundle_summary_ko": "HTF 대체로 상승 정렬 | 직전 박스 상단 돌파 유지 | 역행 SELL 경계",
        "context_conflict_label_ko": "직전 박스와 상위 추세를 거스르는 SELL 경계",
        "htf_alignment_state": "WITH_HTF",
        "htf_alignment_detail": "MOSTLY_ALIGNED_UP",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_lifecycle": "BROKEN",
        "previous_box_confidence": "LOW",
        "previous_box_is_consolidation": False,
        "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        "context_conflict_flags": ["AGAINST_HTF", "AGAINST_PREV_BOX"],
        "context_conflict_intensity": "MEDIUM",
        "trend_1h_age_seconds": 120,
        "trend_4h_age_seconds": 120,
        "trend_1d_age_seconds": 120,
        "previous_box_age_seconds": 60,
        "forecast_state25_runtime_bridge_v1": {"enabled": True},
    }
    runtime_row["state25_candidate_context_bridge_v1"] = build_state25_candidate_context_bridge_v1(
        runtime_row
    )

    payload = build_state25_weight_patch_review_candidate_from_context_bridge_v1(runtime_row)

    assert payload["bridge_weight_requested_count"] >= 1
    assert payload["bridge_weight_effective_count"] == 0
    assert payload["bridge_weight_suppressed_count"] >= 1
    assert "LOW_CONFIDENCE_CONTEXT" in payload["bridge_failure_modes"]
    assert "DOUBLE_COUNTING_SUPPRESSED" in payload["bridge_guard_modes"]


def test_state25_weight_patch_review_candidate_rebuilds_bridge_when_nested_payload_is_stale() -> None:
    runtime_row = {
        "symbol": "BTCUSD",
        "entry_stage": "balanced",
        "consumer_check_side": "SELL",
        "signal_timeframe": "15M",
        "context_bundle_summary_ko": "HTF 대체로 상승 정렬 | 직전 박스 상단 돌파 유지 | 역행 SELL 경계",
        "context_conflict_label_ko": "직전 박스와 상위 추세를 거스르는 SELL 경계",
        "htf_alignment_state": "WITH_HTF",
        "htf_alignment_detail": "MOSTLY_ALIGNED_UP",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_lifecycle": "BROKEN",
        "previous_box_confidence": "LOW",
        "previous_box_is_consolidation": False,
        "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        "context_conflict_flags": ["AGAINST_HTF", "AGAINST_PREV_BOX"],
        "context_conflict_intensity": "MEDIUM",
        "trend_1h_age_seconds": 120,
        "trend_4h_age_seconds": 120,
        "trend_1d_age_seconds": 120,
        "previous_box_age_seconds": 60,
        "forecast_state25_runtime_bridge_v1": {"enabled": True},
        "state25_candidate_context_bridge_v1": {
            "weight_adjustments_requested": {},
            "weight_adjustments_effective": {},
            "weight_adjustments_suppressed": {},
        },
    }

    payload = build_state25_weight_patch_review_candidate_from_context_bridge_v1(runtime_row)

    assert payload["bridge_weight_requested_count"] >= 1
    assert payload["bridge_weight_effective_count"] == 0
    assert payload["bridge_context_bias_side"] == "BUY"


def test_state25_weight_patch_review_candidate_keeps_effective_weights_when_overlap_guard_relaxed() -> None:
    shared_hint = {
        "scene_pattern_id": 21,
        "entry_bias_hint": "confirm",
        "wait_bias_hint": "short_wait",
        "exit_bias_hint": "range_take",
        "transition_risk_hint": "mid",
        "reason_summary": "갭 메움 진행장|D|confirm|short_wait|mid",
    }
    runtime_row = {
        "symbol": "XAUUSD",
        "entry_stage": "balanced",
        "consumer_check_side": "SELL",
        "signal_timeframe": "15M",
        "context_bundle_summary_ko": "직전 박스와 상위 추세 모두 역행 (약함)",
        "htf_alignment_state": "WITH_HTF",
        "htf_alignment_detail": "MOSTLY_ALIGNED_UP",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_lifecycle": "BROKEN",
        "previous_box_confidence": "HIGH",
        "previous_box_is_consolidation": True,
        "trend_1h_age_seconds": 120,
        "trend_4h_age_seconds": 120,
        "trend_1d_age_seconds": 120,
        "previous_box_age_seconds": 60,
        "forecast_state25_runtime_bridge_v1": {"state25_runtime_hint_v1": shared_hint},
        "belief_state25_runtime_bridge_v1": {"state25_runtime_hint_v1": shared_hint},
        "barrier_state25_runtime_bridge_v1": {"state25_runtime_hint_v1": shared_hint},
    }
    runtime_row["state25_candidate_context_bridge_v1"] = build_state25_candidate_context_bridge_v1(
        runtime_row
    )

    payload = build_state25_weight_patch_review_candidate_from_context_bridge_v1(runtime_row)

    assert payload["bridge_weight_requested_count"] >= 1
    assert payload["bridge_weight_effective_count"] >= 1
    assert payload["bridge_guard_modes"] == []
    assert payload["bridge_stage"] == "BC6_THRESHOLD_LOG_ONLY"
