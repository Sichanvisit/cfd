import json

from backend.services.p0_decision_trace import build_p0_decision_trace_v1


def test_build_p0_decision_trace_marks_semantic_legacy_shared_relation():
    trace = build_p0_decision_trace_v1(
        {
            "action": "BUY",
            "outcome": "entered",
            "observe_reason": "lower_rebound_confirm",
            "consumer_archetype_id": "lower_hold_buy",
            "decision_rule_version": "entry_rule_v2",
            "runtime_snapshot_key": "runtime_signal_row_v1|symbol=XAUUSD|anchor_field=signal_bar_ts|anchor_value=1773149400.0",
        }
    )

    assert trace["identity_owner"] == "semantic"
    assert trace["execution_gate_owner"] == "shared"
    assert trace["decision_owner_relation"] == "semantic_identity_with_legacy_execution_gate"
    assert trace["coverage_state"] == "in_scope_runtime"
    assert trace["lifecycle_stage_hint"] == "entry_opened"


def test_build_p0_decision_trace_marks_outside_coverage_from_r0_family_and_guard_failure():
    trace = build_p0_decision_trace_v1(
        {
            "action": "SELL",
            "outcome": "skipped",
            "observe_reason": "upper_reject_probe_observe",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "r0_non_action_family": "decision_log_coverage_gap",
            "probe_promotion_guard_v1": {
                "guard_active": True,
                "allows_open": False,
                "failure_code": "probe_promotion_gate",
            },
        }
    )

    assert trace["coverage_state"] == "outside_coverage"
    assert trace["coverage_source"] == "r0_non_action_family"
    assert trace["dominant_guard_failure"] == "probe_promotion_gate"
    assert trace["guard_failures"] == ["probe_promotion_gate"]
    assert trace["lifecycle_stage_hint"] == "entry_blocked"


def test_build_p0_decision_trace_serializes_cleanly():
    trace = build_p0_decision_trace_v1(
        {
            "action": "BUY",
            "observe_reason": "lower_hold_buy",
            "runtime_snapshot_key": "runtime_signal_row_v1|symbol=NAS100|anchor_field=signal_bar_ts|anchor_value=1773149400.0",
        }
    )
    dumped = json.dumps(trace, ensure_ascii=False, separators=(",", ":"))
    assert '"contract_version":"p0_decision_trace_v1"' in dumped
