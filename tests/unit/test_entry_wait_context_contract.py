from backend.services.entry_wait_context_contract import (
    build_entry_wait_context_v1,
    compact_entry_wait_context_v1,
    extract_entry_wait_hints_v1,
)
from backend.services.wait_engine import WaitEngine


def test_entry_wait_context_contract_builds_reason_and_threshold_context():
    context = build_entry_wait_context_v1(
        symbol="BTCUSD",
        payload={
            "blocked_by": "setup_rejected",
            "action_none_reason": "edge_approach_observe",
            "action": "BUY",
            "box_state": "LOWER",
            "bb_state": "MID",
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "BUY",
                "reason": "lower_approach_observe",
                "metadata": {"xau_second_support_probe_relief": True},
            },
            "core_allowed_action": "BUY_ONLY",
            "preflight_allowed_action": "BOTH",
            "setup_status": "pending",
            "setup_reason": "lower_approach_observe_wait",
            "setup_trigger_state": "watching",
            "wait_score": 38.0,
            "wait_conflict": 4.0,
            "wait_noise": 12.0,
            "wait_penalty": 0.0,
        },
    )

    assert context["contract_version"] == "entry_wait_context_v1"
    assert context["identity"]["symbol"] == "BTCUSD"
    assert context["identity"]["action"] == "BUY"
    assert context["reasons"]["observe_reason"] == "lower_approach_observe"
    assert context["reasons"]["reason_split_v1"]["blocked_by"] == "setup_rejected"
    assert context["market"]["observe_state"] == "OBSERVE"
    assert context["thresholds"]["base_soft_threshold"] > 0.0
    assert context["thresholds"]["base_hard_threshold"] > 0.0
    assert context["thresholds"]["effective_soft_threshold"] == context["thresholds"]["base_soft_threshold"]
    assert context["observe_probe"]["xau_second_support_probe_relief"] is True


def test_entry_wait_context_contract_extracts_helper_hints_with_sources():
    helper_hints = extract_entry_wait_hints_v1(
        {
            "energy_helper_v2": {
                "action_readiness": 0.42,
                "soft_block_hint": {
                    "active": True,
                    "reason": "energy_soft_block",
                    "strength": 0.66,
                },
                "metadata": {
                    "utility_hints": {
                        "wait_vs_enter_hint": "prefer_wait",
                    }
                },
            },
            "layer_mode_policy_v1": {
                "hard_blocks": [{"layer": "forecast", "effect": "blocked"}],
            },
        }
    )

    assert helper_hints["action_readiness"] == 0.42
    assert helper_hints["has_action_readiness_hint"] is True
    assert helper_hints["action_readiness_source"] == "energy_helper"
    assert helper_hints["wait_vs_enter_hint"] == "prefer_wait"
    assert helper_hints["wait_vs_enter_hint_source"] == "energy_helper"
    assert helper_hints["soft_block_active"] is True
    assert helper_hints["soft_block_reason"] == "energy_soft_block"
    assert helper_hints["soft_block_hint_source"] == "energy_helper"
    assert helper_hints["policy_hard_block_active"] is True
    assert helper_hints["policy_block_layer"] == "forecast"


def test_entry_wait_context_contract_compacts_probe_and_policy_summary():
    context = build_entry_wait_context_v1(
        payload={
            "symbol": "XAUUSD",
            "action": "SELL",
            "box_state": "UPPER",
            "bb_state": "MID",
            "blocked_by": "outer_band_reversal_guard",
            "wait_score": 34.0,
            "entry_probe_plan_v1": {
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_upper_sell_probe",
                },
                "active": True,
                "ready_for_entry": False,
                "trigger_branch": "upper_reject",
            },
        },
    )
    context["bias"] = {
        "state_wait_bias_v1": {"prefer_confirm_release": False, "prefer_wait_lock": False},
        "belief_wait_bias_v1": {"prefer_confirm_release": False, "prefer_wait_lock": False},
        "edge_pair_wait_bias_v1": {"present": False},
        "symbol_probe_temperament_v1": {
            "present": True,
            "scene_id": "xau_upper_sell_probe",
            "active": True,
            "ready_for_entry": False,
            "prefer_confirm_release": True,
            "prefer_wait_lock": False,
        },
    }
    context["policy"] = {
        "state": "ACTIVE",
        "reason": "upper_reject_probe_observe",
        "hard_wait": False,
        "xau_upper_sell_probe": True,
    }

    compact = compact_entry_wait_context_v1(context)

    assert compact["observe_probe"]["probe_scene_id"] == "xau_upper_sell_probe"
    assert compact["observe_probe"]["probe_active"] is True
    assert compact["bias"]["probe"]["scene_id"] == "xau_upper_sell_probe"
    assert compact["bias"]["probe"]["prefer_confirm_release"] is True
    assert compact["policy"]["state"] == "ACTIVE"
    assert compact["policy"]["xau_upper_sell_probe"] is True


def test_wait_engine_metadata_includes_compact_entry_wait_context():
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "SELL",
            "box_state": "UPPER",
            "bb_state": "MID",
            "blocked_by": "outer_band_reversal_guard",
            "wait_score": 34.0,
            "wait_conflict": 0.0,
            "wait_noise": 12.0,
            "wait_penalty": 0.0,
            "entry_probe_plan_v1": {
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_upper_sell_probe",
                },
                "active": True,
                "trigger_branch": "upper_reject",
            },
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "metadata": {},
            },
        },
    )

    compact_context = wait_state.metadata["entry_wait_context_v1"]

    assert compact_context["contract_version"] == "entry_wait_context_v1"
    assert compact_context["identity"]["symbol"] == "XAUUSD"
    assert compact_context["reasons"]["observe_reason"] == "upper_reject_probe_observe"
    assert compact_context["observe_probe"]["probe_scene_id"] == "xau_upper_sell_probe"
    assert compact_context["policy"]["state"] == "ACTIVE"
    assert compact_context["thresholds"]["effective_soft_threshold"] == wait_state.metadata["wait_soft_threshold"]
