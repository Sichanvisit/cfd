import json

from backend.services.barrier_state25_runtime_bridge import (
    BARRIER_SCOPE_FREEZE_CONTRACT_V1,
    build_barrier_action_hint_v1,
    build_barrier_input_trace_v1,
    build_barrier_runtime_summary_v1,
    build_barrier_state25_runtime_bridge_v1,
)
from backend.services.storage_compaction import (
    build_entry_decision_hot_payload,
    compact_runtime_signal_row,
)


def _runtime_bridge_row() -> dict:
    return {
        "symbol": "BTCUSD",
        "action": "SELL",
        "direction": "SELL",
        "my_position_count": 1,
        "entry_setup_id": "range_upper_reversal_sell",
        "entry_session_name": "LONDON",
        "entry_wait_state": "CENTER",
        "entry_wait_decision": "wait_lock",
        "observe_reason": "barrier_guard",
        "blocked_by": "barrier_guard",
        "entry_score": 58.0,
        "contra_score_at_entry": 19.0,
        "prediction_bundle": json.dumps(
            {
                "p_continuation_success": 0.28,
                "p_false_break": 0.79,
            },
            ensure_ascii=False,
        ),
        "transition_forecast_v1": {
            "p_buy_confirm": 0.11,
            "p_sell_confirm": 0.74,
            "p_false_break": 0.49,
            "p_continuation_success": 0.58,
            "metadata": {
                "mapper_version": "transition_mapper_v1",
                "side_separation": 0.42,
            },
        },
        "trade_management_forecast_v1": {
            "p_continue_favor": 0.68,
            "p_fail_now": 0.21,
            "metadata": {
                "mapper_version": "management_mapper_v1",
            },
        },
        "forecast_gap_metrics_v1": {
            "wait_confirm_gap": 0.24,
            "hold_exit_gap": 0.18,
            "same_side_flip_gap": 0.12,
            "belief_barrier_tension_gap": 0.09,
        },
        "belief_state_v1": {
            "buy_belief": 0.18,
            "sell_belief": 0.74,
            "buy_persistence": 0.15,
            "sell_persistence": 0.46,
            "belief_spread": 0.56,
            "flip_readiness": 0.22,
            "belief_instability": 0.18,
            "dominant_side": "SELL",
            "dominant_mode": "continuation",
            "buy_streak": 1,
            "sell_streak": 4,
            "transition_age": 3,
        },
        "evidence_vector_v1": {
            "buy_total_evidence": 0.19,
            "sell_total_evidence": 0.64,
            "buy_continuation_evidence": 0.08,
            "sell_continuation_evidence": 0.46,
            "buy_reversal_evidence": 0.11,
            "sell_reversal_evidence": 0.14,
        },
        "barrier_state_v1": {
            "buy_barrier": 0.38,
            "sell_barrier": 0.14,
            "conflict_barrier": 0.28,
            "middle_chop_barrier": 0.11,
            "direction_policy_barrier": 0.18,
            "liquidity_barrier": 0.52,
            "metadata": {
                "edge_turn_relief_score": 0.17,
                "breakout_fade_barrier_score": 0.33,
                "execution_friction_barrier_score": 0.29,
                "event_risk_barrier_score": 0.21,
                "barrier_reasons": {
                    "liquidity_barrier": "thin_liquidity_friction",
                },
                "policy_side_barriers": {
                    "sell_policy": "allow",
                    "buy_policy": "restrict",
                },
                "edge_turn_relief_v1": {
                    "buy_relief": 0.08,
                    "sell_relief": 0.19,
                },
            },
        },
    }


def test_scope_freeze_contract_separates_runtime_and_learning_fields():
    assert BARRIER_SCOPE_FREEZE_CONTRACT_V1["barrier_role"] == "blocking_owner"
    assert BARRIER_SCOPE_FREEZE_CONTRACT_V1["scene_role"] == "scene_owner"
    assert "barrier_runtime_summary_v1" in BARRIER_SCOPE_FREEZE_CONTRACT_V1["runtime_direct_use_fields"]
    assert "barrier_input_trace_v1" in BARRIER_SCOPE_FREEZE_CONTRACT_V1["learning_only_fields"]
    assert "barrier_action_hint_v1" in BARRIER_SCOPE_FREEZE_CONTRACT_V1["learning_only_fields"]
    assert "barrier_outcome_label" in BARRIER_SCOPE_FREEZE_CONTRACT_V1["learning_only_fields"]


def test_build_barrier_runtime_summary_v1_resolves_top_component_and_blocking_bias():
    summary = build_barrier_runtime_summary_v1(_runtime_bridge_row())

    assert summary["contract_version"] == "barrier_runtime_summary_v1"
    assert summary["available"] is True
    assert summary["acting_side"] == "SELL"
    assert summary["anchor_context"] == "wait_block"
    assert summary["top_component"] == "liquidity_barrier"
    assert summary["top_component_reason"] == "thin_liquidity_friction"
    assert summary["blocking_bias"] == "WAIT_BLOCK"
    assert summary["barrier_blocked_flag"] is True


def test_build_barrier_runtime_summary_v1_accepts_json_string_barrier_state():
    row = _runtime_bridge_row()
    row["barrier_state_v1"] = json.dumps(row["barrier_state_v1"], ensure_ascii=False)

    summary = build_barrier_runtime_summary_v1(row)

    assert summary["available"] is True
    assert summary["top_component"] == "liquidity_barrier"
    assert summary["top_component_reason"] == "thin_liquidity_friction"


def test_build_barrier_input_trace_v1_carries_scene_forecast_and_belief_context():
    trace = build_barrier_input_trace_v1(_runtime_bridge_row())

    assert trace["contract_version"] == "barrier_input_trace_v1"
    assert trace["available"] is True
    assert trace["forecast_decision_hint"] in {
        "SELL_CONFIRM",
        "WAIT",
        "OBSERVE",
        "SELL",
        "CONFIRM_BIASED",
    }
    assert trace["belief_dominant_side"] == "SELL"
    assert trace["belief_persistence_hint"] == "STABLE"
    assert trace["top_component"] == "liquidity_barrier"
    assert trace["event_risk_barrier_score"] == 0.21


def test_build_barrier_action_hint_v1_returns_wait_bias_for_blocked_wait_scene():
    hint = build_barrier_action_hint_v1(_runtime_bridge_row())

    assert hint["contract_version"] == "barrier_action_hint_v1"
    assert hint["available"] is True
    assert hint["enabled"] is True
    assert hint["hint_mode"] == "log_only"
    assert hint["recommended_family"] == "wait_bias"
    assert hint["supporting_label_candidate"] == "correct_wait"
    assert hint["overlay_cost_hint"] == "wait_value_balance"


def test_build_barrier_runtime_summary_v1_marks_pre_context_skip_when_barrier_not_evaluated_yet():
    summary = build_barrier_runtime_summary_v1(
        {
            "symbol": "BTCUSD",
            "outcome": "skipped",
            "blocked_by": "max_positions_reached",
            "barrier_state_v1": {},
        }
    )

    assert summary["available"] is False
    assert summary["availability_stage"] == "pre_context_skip"
    assert summary["availability_reason"] == "max_positions_reached"
    assert summary["reason_summary"] == "pre_context|max_positions_reached"


def test_runtime_bridge_survives_runtime_and_hot_payload_compaction():
    row = _runtime_bridge_row()
    row["barrier_state25_runtime_bridge_v1"] = build_barrier_state25_runtime_bridge_v1(row)

    compact = compact_runtime_signal_row(row)
    hot = build_entry_decision_hot_payload(row, detail_row_key="barrier-state25-bridge")

    assert compact["barrier_state25_runtime_bridge_v1"]["state25_runtime_hint_v1"]["scene_pattern_id"] > 0
    assert (
        compact["barrier_state25_runtime_bridge_v1"]["barrier_runtime_summary_v1"]["top_component"]
        == "liquidity_barrier"
    )
    assert (
        compact["barrier_state25_runtime_bridge_v1"]["barrier_input_trace_v1"]["belief_dominant_side"]
        == "SELL"
    )
    assert (
        compact["barrier_state25_runtime_bridge_v1"]["barrier_action_hint_v1"]["recommended_family"]
        == "wait_bias"
    )
    assert '"top_component":"liquidity_barrier"' in str(hot["barrier_state25_runtime_bridge_v1"])
    assert '"belief_dominant_side":"SELL"' in str(hot["barrier_state25_runtime_bridge_v1"])
    assert '"recommended_family":"wait_bias"' in str(hot["barrier_state25_runtime_bridge_v1"])
