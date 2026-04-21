import json

from backend.services.forecast_state25_runtime_bridge import (
    FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_V1,
    build_forecast_state25_log_only_overlay_trace_v1,
    build_forecast_runtime_summary_v1,
    build_forecast_state25_runtime_bridge_v1,
    build_state25_runtime_hint_v1,
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
        "micro_reversal_risk_state": "HIGH_RISK",
        "micro_participation_state": "THIN_PARTICIPATION",
        "micro_upper_wick_ratio_20": 0.38,
        "micro_same_color_run_current": 2,
        "micro_same_color_run_max_20": 3,
        "micro_doji_ratio_20": 0.14,
        "micro_range_compression_ratio_20": 0.31,
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
    }


def test_scope_freeze_contract_separates_runtime_and_learning_fields():
    assert FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_V1["state25_role"] == "scene_owner"
    assert FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_V1["forecast_role"] == "branch_owner"
    assert "state25_runtime_hint_v1" in FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_V1["runtime_direct_use_fields"]
    assert "log_only_overlay_candidates_v1" in FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_V1["runtime_direct_use_fields"]
    assert "closed_history_teacher_labels" in FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_V1["learning_only_fields"]


def test_build_state25_runtime_hint_v1_uses_runtime_safe_teacher_hint():
    hint = build_state25_runtime_hint_v1(_runtime_bridge_row())

    assert hint["contract_version"] == "state25_runtime_hint_v1"
    assert hint["available"] is True
    assert hint["scene_pattern_id"] == 25
    assert hint["scene_group_hint"] == "D"
    assert hint["candidate_pattern_ids"] == [25]
    assert hint["wait_bias_hint"] != ""


def test_build_forecast_runtime_summary_v1_resolves_decision_hint():
    summary = build_forecast_runtime_summary_v1(_runtime_bridge_row())

    assert summary["contract_version"] == "forecast_runtime_summary_v1"
    assert summary["confirm_side"] == "SELL"
    assert summary["confirm_score"] == 0.74
    assert summary["wait_confirm_gap"] == 0.24
    assert summary["decision_hint"] == "CONFIRM_BIASED"


def test_runtime_bridge_survives_runtime_and_hot_payload_compaction():
    row = _runtime_bridge_row()
    row["forecast_state25_runtime_bridge_v1"] = build_forecast_state25_runtime_bridge_v1(row)
    row["forecast_state25_log_only_overlay_trace_v1"] = build_forecast_state25_log_only_overlay_trace_v1(
        row["forecast_state25_runtime_bridge_v1"],
        symbol="BTCUSD",
        entry_stage="READY",
        actual_effective_entry_threshold=45.0,
        actual_size_multiplier=1.0,
    )

    compact = compact_runtime_signal_row(row)
    hot = build_entry_decision_hot_payload(row, detail_row_key="forecast-state25-bridge")

    assert compact["forecast_state25_runtime_bridge_v1"]["state25_runtime_hint_v1"]["scene_pattern_id"] == 25
    assert (
        compact["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"]["decision_hint"]
        == "CONFIRM_BIASED"
    )
    assert compact["forecast_state25_runtime_bridge_v1"]["entry_wait_exit_bridge_v1"]["prefer_entry_now"] is True
    assert compact["forecast_state25_runtime_bridge_v1"]["log_only_overlay_candidates_v1"]["enabled"] is True
    assert compact["forecast_state25_log_only_overlay_trace_v1"]["overlay_enabled"] is True
    assert '"scene_pattern_id":25' in str(hot["forecast_state25_runtime_bridge_v1"])
    assert '"decision_hint":"CONFIRM_BIASED"' in str(hot["forecast_state25_runtime_bridge_v1"])
    assert '"candidate_wait_bias_action":"release_wait_bias"' in str(
        hot["forecast_state25_log_only_overlay_trace_v1"]
    )


def test_runtime_bridge_ignores_log_only_weight_overrides_in_live_hint():
    row = _runtime_bridge_row()
    row["state25_candidate_runtime_v1"] = {
        "current_binding_mode": "log_only",
        "desired_runtime_patch": {
            "state25_execution_symbol_allowlist": ["BTCUSD"],
            "state25_execution_entry_stage_allowlist": ["READY"],
            "state25_weight_log_only_enabled": True,
            "state25_teacher_weight_overrides": {
                "reversal_risk_weight": 0.75,
                "directional_bias_weight": 1.20,
            },
        },
    }

    bridge = build_forecast_state25_runtime_bridge_v1(row)

    assert bridge["state25_runtime_hint_v1"]["available"] is True
    assert bridge["state25_runtime_hint_v1"]["scene_pattern_id"] == 25


def test_runtime_bridge_uses_bounded_live_weight_overrides_in_live_hint():
    row = _runtime_bridge_row()
    row["state25_candidate_runtime_v1"] = {
        "current_binding_mode": "bounded_live",
        "desired_runtime_patch": {
            "state25_execution_symbol_allowlist": ["BTCUSD"],
            "state25_execution_entry_stage_allowlist": ["READY"],
            "state25_weight_bounded_live_enabled": True,
            "state25_teacher_weight_overrides": {
                "reversal_risk_weight": 0.75,
                "directional_bias_weight": 1.20,
            },
        },
    }

    bridge = build_forecast_state25_runtime_bridge_v1(row)

    assert bridge["state25_runtime_hint_v1"]["available"] is True
    assert bridge["state25_runtime_hint_v1"]["scene_pattern_id"] > 0
    assert bridge["state25_runtime_hint_v1"]["reason_summary"] != ""
