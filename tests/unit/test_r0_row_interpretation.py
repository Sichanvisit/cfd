from backend.services.r0_row_interpretation import (
    build_r0_row_interpretation_v1,
    resolve_r0_non_action_family,
    resolve_r0_probe_state,
    resolve_r0_reason_triplet,
    resolve_r0_semantic_runtime,
)


def test_resolve_r0_reason_triplet_reads_nested_fallbacks():
    row = {
        "observe_confirm_v2": {
            "reason": "lower_rebound_probe_observe",
            "metadata": {
                "blocked_guard": "probe_promotion_gate",
            },
        },
        "entry_decision_result_v1": {
            "blocked_by": "probe_promotion_gate",
            "metrics": {
                "action_none_reason": "probe_not_promoted",
            },
        },
    }

    triplet = resolve_r0_reason_triplet(row)

    assert triplet["observe_reason"] == "lower_rebound_probe_observe"
    assert triplet["blocked_by"] == "probe_promotion_gate"
    assert triplet["action_none_reason"] == "probe_not_promoted"


def test_resolve_r0_probe_state_uses_quick_state_and_fallbacks():
    assert resolve_r0_probe_state({"quick_trace_state": "PROBE_WAIT"}) == "PROBE_WAIT"
    assert (
        resolve_r0_probe_state(
            {
                "entry_probe_plan_v1": {"active": True, "ready_for_entry": True},
            }
        )
        == "PROBE_READY"
    )
    assert (
        resolve_r0_probe_state(
            {
                "probe_candidate_v1": {"active": True},
                "blocked_by": "forecast_guard",
            }
        )
        == "PROBE_CANDIDATE_BLOCKED"
    )


def test_resolve_r0_non_action_family_maps_known_families():
    assert resolve_r0_non_action_family({"action_none_reason": "policy_hard_blocked"}) == "policy_hard_blocked"
    assert resolve_r0_non_action_family({"action_none_reason": "observe_state_wait"}) == "semantic_observe_wait"
    assert resolve_r0_non_action_family({"action_none_reason": "opposite_position_lock"}) == "position_lock_blocked"
    assert (
        resolve_r0_non_action_family(
            {
                "probe_candidate_v1": {"active": True},
                "entry_probe_plan_v1": {"active": True, "ready_for_entry": False},
            }
        )
        == "probe_not_promoted"
    )


def test_resolve_r0_semantic_runtime_classifies_live_and_fallback():
    fallback = resolve_r0_semantic_runtime(
        {
            "semantic_live_rollout_mode": "threshold_only",
            "semantic_live_fallback_reason": "baseline_no_action",
            "semantic_live_symbol_allowed": 1,
            "semantic_live_entry_stage_allowed": 1,
        }
    )
    live = resolve_r0_semantic_runtime(
        {
            "semantic_live_rollout_mode": "threshold_only",
            "semantic_live_reason": "mode=threshold_only",
            "semantic_live_symbol_allowed": 1,
            "semantic_live_entry_stage_allowed": 1,
        }
    )

    assert fallback["semantic_runtime_state"] == "FALLBACK"
    assert live["semantic_runtime_state"] == "LIVE"


def test_build_r0_row_interpretation_v1_returns_compact_contract():
    row = {
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "probe_promotion_gate",
        "action_none_reason": "probe_not_promoted",
        "quick_trace_state": "PROBE_WAIT",
        "quick_trace_reason": "probe_forecast_not_ready",
        "probe_candidate_v1": {"active": True},
        "entry_probe_plan_v1": {"active": True, "ready_for_entry": False},
        "semantic_live_rollout_mode": "threshold_only",
        "semantic_live_fallback_reason": "baseline_no_action",
    }

    interpretation = build_r0_row_interpretation_v1(row)

    assert interpretation["contract_version"] == "r0_row_interpretation_v1"
    assert interpretation["observe_reason"] == "upper_reject_probe_observe"
    assert interpretation["blocked_by"] == "probe_promotion_gate"
    assert interpretation["action_none_reason"] == "probe_not_promoted"
    assert interpretation["probe_state"] == "PROBE_WAIT"
    assert interpretation["quick_trace_reason"] == "probe_forecast_not_ready"
    assert interpretation["non_action_family"] == "probe_not_promoted"
    assert interpretation["semantic_runtime_state"] == "FALLBACK"
