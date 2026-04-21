import json

from backend.services.belief_state25_runtime_bridge import (
    BELIEF_SCOPE_FREEZE_CONTRACT_V1,
    build_belief_action_hint_v1,
    build_belief_runtime_summary_v1,
    build_belief_state25_runtime_bridge_v1,
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
        },
    }


def test_scope_freeze_contract_separates_runtime_and_learning_fields():
    assert BELIEF_SCOPE_FREEZE_CONTRACT_V1["belief_role"] == "thesis_persistence_owner"
    assert BELIEF_SCOPE_FREEZE_CONTRACT_V1["scene_role"] == "scene_owner"
    assert "belief_runtime_summary_v1" in BELIEF_SCOPE_FREEZE_CONTRACT_V1["runtime_direct_use_fields"]
    assert "belief_input_trace_v1" in BELIEF_SCOPE_FREEZE_CONTRACT_V1["learning_only_fields"]
    assert "belief_action_hint_v1" in BELIEF_SCOPE_FREEZE_CONTRACT_V1["learning_only_fields"]


def test_build_belief_runtime_summary_v1_resolves_hold_thesis_and_persistence_hint():
    summary = build_belief_runtime_summary_v1(_runtime_bridge_row())

    assert summary["contract_version"] == "belief_runtime_summary_v1"
    assert summary["available"] is True
    assert summary["acting_side"] == "SELL"
    assert summary["anchor_context"] == "hold_thesis"
    assert summary["dominant_side"] == "SELL"
    assert summary["active_persistence"] == 0.46
    assert summary["flip_readiness"] == 0.22
    assert summary["persistence_hint"] == "STABLE"


def test_build_belief_action_hint_v1_emits_hold_bias_for_stable_hold_scene():
    hint = build_belief_action_hint_v1(_runtime_bridge_row())

    assert hint["available"] is True
    assert hint["enabled"] is True
    assert hint["hint_mode"] == "log_only"
    assert hint["recommended_family"] == "hold_bias"
    assert hint["supporting_label_candidate"] == "correct_hold"


def test_build_belief_action_hint_v1_emits_flip_alert_for_flip_ready_scene():
    row = _runtime_bridge_row()
    row["action"] = "BUY"
    row["my_position_count"] = 1
    row["belief_state_v1"] = {
        **dict(row["belief_state_v1"]),
        "buy_belief": 0.62,
        "sell_belief": 0.31,
        "buy_persistence": 0.36,
        "sell_persistence": 0.22,
        "flip_readiness": 0.73,
        "belief_instability": 0.52,
        "dominant_side": "SELL",
        "dominant_mode": "reversal",
    }
    row["evidence_vector_v1"] = {
        **dict(row["evidence_vector_v1"]),
        "buy_continuation_evidence": 0.22,
        "buy_reversal_evidence": 0.41,
        "buy_total_evidence": 0.63,
    }
    row["barrier_state_v1"] = {
        **dict(row["barrier_state_v1"]),
        "buy_barrier": 0.18,
        "conflict_barrier": 0.17,
        "liquidity_barrier": 0.21,
    }

    hint = build_belief_action_hint_v1(row)

    assert hint["available"] is True
    assert hint["enabled"] is True
    assert hint["recommended_family"] == "flip_alert"
    assert hint["supporting_label_candidate"] == "correct_flip"
    assert hint["overlay_confidence"] in {"medium", "high"}


def test_runtime_bridge_survives_runtime_and_hot_payload_compaction():
    row = _runtime_bridge_row()
    row["belief_state25_runtime_bridge_v1"] = build_belief_state25_runtime_bridge_v1(row)

    compact = compact_runtime_signal_row(row)
    hot = build_entry_decision_hot_payload(row, detail_row_key="belief-state25-bridge")

    assert compact["belief_state25_runtime_bridge_v1"]["state25_runtime_hint_v1"]["scene_pattern_id"] > 0
    assert compact["belief_state25_runtime_bridge_v1"]["belief_runtime_summary_v1"]["anchor_context"] == "hold_thesis"
    assert (
        compact["belief_state25_runtime_bridge_v1"]["belief_input_trace_v1"]["dominant_evidence_family"]
        == "CONTINUATION"
    )
    assert (
        compact["belief_state25_runtime_bridge_v1"]["belief_input_trace_v1"]["barrier_primary_component"]
        == "liquidity_barrier"
    )
    assert (
        compact["belief_state25_runtime_bridge_v1"]["belief_action_hint_v1"]["recommended_family"]
        == "hold_bias"
    )
    assert '"anchor_context":"hold_thesis"' in str(hot["belief_state25_runtime_bridge_v1"])
    assert '"dominant_evidence_family":"CONTINUATION"' in str(hot["belief_state25_runtime_bridge_v1"])
