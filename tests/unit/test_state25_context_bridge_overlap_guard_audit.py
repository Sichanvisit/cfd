from __future__ import annotations

from backend.services.state25_context_bridge_overlap_guard_audit import (
    build_state25_context_bridge_overlap_guard_audit_from_runtime_payload,
    render_state25_context_bridge_overlap_guard_audit_markdown,
)


def test_overlap_guard_audit_builder_and_markdown_from_runtime_payload():
    runtime_payload = {
        "updated_at": "2026-04-14T12:20:39+09:00",
        "latest_signal_by_symbol": {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "consumer_check_side": "SELL",
                "consumer_check_reason": "outer_band_reversal_support_required_observe",
                "context_bundle_summary_ko": "직전 박스와 상위 추세 모두 역행 (약함)",
                "htf_alignment_state": "WITH_HTF",
                "previous_box_break_state": "BREAKOUT_HELD",
                "previous_box_relation": "ABOVE",
                "previous_box_confidence": "LOW",
                "previous_box_is_consolidation": True,
                "trend_1h_age_seconds": 120,
                "trend_4h_age_seconds": 120,
                "trend_1d_age_seconds": 120,
                "previous_box_age_seconds": 60,
                "state25_context_bridge_weight_requested_count": 2,
                "state25_context_bridge_weight_effective_count": 2,
                "forecast_state25_runtime_bridge_v1": {
                    "state25_runtime_hint_v1": {
                        "scene_pattern_id": 21,
                        "entry_bias_hint": "confirm",
                        "wait_bias_hint": "short_wait",
                        "exit_bias_hint": "range_take",
                        "transition_risk_hint": "mid",
                        "reason_summary": "갭필링 진행장|D|confirm|short_wait|mid",
                    }
                },
                "belief_state25_runtime_bridge_v1": {
                    "state25_runtime_hint_v1": {
                        "scene_pattern_id": 21,
                        "entry_bias_hint": "confirm",
                        "wait_bias_hint": "short_wait",
                        "exit_bias_hint": "range_take",
                        "transition_risk_hint": "mid",
                        "reason_summary": "갭필링 진행장|D|confirm|short_wait|mid",
                    }
                },
                "barrier_state25_runtime_bridge_v1": {
                    "state25_runtime_hint_v1": {
                        "scene_pattern_id": 21,
                        "entry_bias_hint": "confirm",
                        "wait_bias_hint": "short_wait",
                        "exit_bias_hint": "range_take",
                        "transition_risk_hint": "mid",
                        "reason_summary": "갭필링 진행장|D|confirm|short_wait|mid",
                    }
                },
                "state25_candidate_context_bridge_v1": {
                    "overlap_sources": [
                        "forecast_state25_runtime_bridge_v1",
                        "belief_state25_runtime_bridge_v1",
                        "barrier_state25_runtime_bridge_v1",
                    ],
                    "overlap_class": "RISK_DUPLICATE",
                    "overlap_guard_decision": "RELAXED_SAME_RUNTIME_HINT_DUPLICATE",
                    "overlap_same_runtime_hint_duplicate": True,
                    "double_counting_guard_active": False,
                    "failure_modes": [
                        "LOW_CONFIDENCE_CONTEXT",
                        "SIGNED_THRESHOLD_UNAVAILABLE",
                    ],
                    "guard_modes": [],
                    "trace_reason_codes": [
                        "WEIGHT_TRANSLATOR_READY",
                        "OVERLAP_GUARD_RELAXED_SAME_RUNTIME_HINT",
                    ],
                    "weight_adjustments_suppressed": {},
                },
            },
            "NAS100": {
                "symbol": "NAS100",
                "consumer_check_side": "BUY",
                "consumer_check_reason": "conflict_box_upper",
                "context_bundle_summary_ko": "",
                "htf_alignment_state": "WITH_HTF",
                "previous_box_break_state": "BREAKOUT_FAILED",
                "previous_box_confidence": "MEDIUM",
                "trend_1h_age_seconds": 120,
                "trend_4h_age_seconds": 120,
                "trend_1d_age_seconds": 120,
                "previous_box_age_seconds": 60,
                "state25_context_bridge_weight_requested_count": 0,
                "state25_context_bridge_weight_effective_count": 0,
                "forecast_state25_runtime_bridge_v1": {
                    "state25_runtime_hint_v1": {
                        "scene_pattern_id": 21,
                        "entry_bias_hint": "confirm",
                        "wait_bias_hint": "short_wait",
                        "exit_bias_hint": "range_take",
                        "transition_risk_hint": "mid",
                        "reason_summary": "갭필링 진행장|D|confirm|short_wait|mid",
                    }
                },
                "belief_state25_runtime_bridge_v1": {
                    "state25_runtime_hint_v1": {
                        "scene_pattern_id": 21,
                        "entry_bias_hint": "confirm",
                        "wait_bias_hint": "short_wait",
                        "exit_bias_hint": "range_take",
                        "transition_risk_hint": "mid",
                        "reason_summary": "갭필링 진행장|D|confirm|short_wait|mid",
                    }
                },
                "barrier_state25_runtime_bridge_v1": {
                    "state25_runtime_hint_v1": {
                        "scene_pattern_id": 21,
                        "entry_bias_hint": "confirm",
                        "wait_bias_hint": "short_wait",
                        "exit_bias_hint": "range_take",
                        "transition_risk_hint": "mid",
                        "reason_summary": "갭필링 진행장|D|confirm|short_wait|mid",
                    }
                },
                "state25_candidate_context_bridge_v1": {
                    "overlap_sources": [
                        "forecast_state25_runtime_bridge_v1",
                        "belief_state25_runtime_bridge_v1",
                        "barrier_state25_runtime_bridge_v1",
                    ],
                    "overlap_class": "RISK_DUPLICATE",
                    "overlap_guard_decision": "RELAXED_SAME_RUNTIME_HINT_DUPLICATE",
                    "overlap_same_runtime_hint_duplicate": True,
                    "double_counting_guard_active": False,
                    "failure_modes": ["SIGNED_THRESHOLD_UNAVAILABLE"],
                    "guard_modes": [],
                    "trace_reason_codes": ["WEIGHT_TRANSLATOR_NO_SIGNAL"],
                    "weight_adjustments_suppressed": {},
                },
            },
        },
    }

    audit = build_state25_context_bridge_overlap_guard_audit_from_runtime_payload(runtime_payload)

    assert audit["symbol_count"] == 2
    assert audit["guard_active_symbol_count"] == 0
    assert audit["requested_but_suppressed_symbol_count"] == 0
    assert audit["blanket_risk_duplicate_symbol_count"] == 2
    assert audit["relaxed_same_runtime_hint_symbol_count"] == 2
    assert audit["dominant_issue"] == "duplicate_runtime_hint_repetition_without_active_guard"
    assert (
        audit["recommended_next_step"]
        == "monitor_relaxed_duplicate_runtime_hint_effect"
    )

    xau = next(row for row in audit["symbol_rows"] if row["symbol"] == "XAUUSD")
    assert xau["blanket_risk_duplicate"] is True
    assert xau["requested_weight_count"] == 2
    assert xau["effective_weight_count"] == 2
    assert xau["recommended_next_action"] == "observe_relaxed_duplicate_runtime_hint_review_flow"

    md = render_state25_context_bridge_overlap_guard_audit_markdown(audit)
    assert "XAUUSD" in md
    assert "requested 2 / effective 2 / suppressed 0" in md
    assert "RISK_DUPLICATE" in md
