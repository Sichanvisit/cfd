from backend.services.entry_wait_context_bias_bundle import resolve_entry_wait_bias_bundle_v1
from backend.services.entry_wait_context_contract import build_entry_wait_context_v1
from backend.services.entry_wait_state_policy import resolve_entry_wait_state_policy_v1
from backend.services.entry_wait_state_policy_contract import (
    build_entry_wait_state_policy_input_v1,
    compact_entry_wait_state_policy_input_v1,
    resolve_entry_wait_state_policy_from_context_v1,
)
from backend.services.wait_engine import WaitEngine


def _build_context_with_bias(payload: dict) -> tuple[dict, dict]:
    context = build_entry_wait_context_v1(payload=payload)
    bundle = resolve_entry_wait_bias_bundle_v1(context)
    thresholds = dict(context["thresholds"])
    thresholds["base_soft_threshold"] = bundle["threshold_adjustment_v1"]["base_soft_threshold"]
    thresholds["base_hard_threshold"] = bundle["threshold_adjustment_v1"]["base_hard_threshold"]
    thresholds["effective_soft_threshold"] = bundle["threshold_adjustment_v1"]["effective_soft_threshold"]
    thresholds["effective_hard_threshold"] = bundle["threshold_adjustment_v1"]["effective_hard_threshold"]
    context["thresholds"] = thresholds
    context["bias"] = {
        "state_wait_bias_v1": dict(bundle["state_wait_bias_v1"]),
        "belief_wait_bias_v1": dict(bundle["belief_wait_bias_v1"]),
        "edge_pair_wait_bias_v1": dict(bundle["edge_pair_wait_bias_v1"]),
        "symbol_probe_temperament_v1": dict(bundle["symbol_probe_temperament_v1"]),
        "threshold_adjustment_v1": dict(bundle["threshold_adjustment_v1"]),
        "bundle_summary_v1": dict(bundle["bundle_summary_v1"]),
    }
    return context, bundle


def test_entry_wait_state_policy_input_builder_captures_thresholds_and_special_scenes():
    context, bundle = _build_context_with_bias(
        {
            "symbol": "BTCUSD",
            "action": "BUY",
            "box_state": "LOWER",
            "bb_state": "MID",
            "blocked_by": "core_not_passed",
            "wait_score": 38.0,
            "wait_conflict": 4.0,
            "wait_noise": 12.0,
            "wait_penalty": 0.0,
            "core_allowed_action": "BUY_ONLY",
            "preflight_allowed_action": "BOTH",
            "consumer_energy_action_readiness": 0.28,
            "consumer_energy_wait_vs_enter_hint": "prefer_wait",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_soft_block_reason": "energy_soft_block",
            "consumer_energy_soft_block_strength": 0.72,
        }
    )

    policy_input = build_entry_wait_state_policy_input_v1(context)
    compact = compact_entry_wait_state_policy_input_v1(policy_input)

    assert policy_input["contract_version"] == "entry_wait_state_policy_input_v1"
    assert policy_input["identity"]["required_side"] == "BUY"
    assert policy_input["special_scenes"]["btc_lower_strong_score_soft_wait_candidate"] is True
    assert policy_input["thresholds"]["effective_soft_threshold"] == bundle["threshold_adjustment_v1"]["effective_soft_threshold"]
    assert policy_input["helper_hints"]["soft_block_active"] is True
    assert compact["bias_bundle"]["wait_lock_bias_count"] == 0
    assert compact["helper_hints"]["wait_vs_enter_hint"] == "prefer_wait"


def test_entry_wait_state_policy_context_adapter_matches_direct_policy_result():
    context, _ = _build_context_with_bias(
        {
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
        }
    )

    policy_input = build_entry_wait_state_policy_input_v1(context)
    resolution = resolve_entry_wait_state_policy_from_context_v1(context)
    direct = resolve_entry_wait_state_policy_v1(
        symbol=policy_input["identity"]["symbol"],
        action=policy_input["identity"]["action"],
        blocked_by=policy_input["reasons"]["blocked_by"],
        action_none_reason=policy_input["reasons"]["action_none_reason"],
        box_state=policy_input["market"]["box_state"],
        bb_state=policy_input["market"]["bb_state"],
        observe_reason=policy_input["reasons"]["observe_reason"],
        core_allowed_action=policy_input["identity"]["core_allowed_action"],
        preflight_allowed_action=policy_input["identity"]["preflight_allowed_action"],
        setup_reason=policy_input["setup"]["reason"],
        setup_trigger_state=policy_input["setup"]["trigger_state"],
        wait_score=policy_input["scores"]["wait_score"],
        wait_conflict=policy_input["scores"]["wait_conflict"],
        wait_noise=policy_input["scores"]["wait_noise"],
        wait_soft=policy_input["thresholds"]["effective_soft_threshold"],
        wait_hard=policy_input["thresholds"]["effective_hard_threshold"],
        action_readiness=policy_input["helper_hints"]["action_readiness"],
        wait_vs_enter_hint=policy_input["helper_hints"]["wait_vs_enter_hint"],
        soft_block_active=policy_input["helper_hints"]["soft_block_active"],
        soft_block_reason=policy_input["helper_hints"]["soft_block_reason"],
        soft_block_strength=policy_input["helper_hints"]["soft_block_strength"],
        policy_hard_block_active=policy_input["helper_hints"]["policy_hard_block_active"],
        policy_suppressed=policy_input["helper_hints"]["policy_suppressed"],
        observe_metadata=policy_input["market"]["observe_metadata"],
        state_wait_bias_v1=policy_input["bias"]["state_wait_bias_v1"],
        belief_wait_bias_v1=policy_input["bias"]["belief_wait_bias_v1"],
        edge_pair_wait_bias_v1=policy_input["bias"]["edge_pair_wait_bias_v1"],
        symbol_probe_temperament_v1=policy_input["bias"]["symbol_probe_temperament_v1"],
    )

    assert resolution["entry_wait_state_policy_v1"] == direct
    assert resolution["compact_entry_wait_state_policy_input_v1"]["special_scenes"]["probe_scene_id"] == "xau_upper_sell_probe"
    assert resolution["entry_wait_state_policy_v1"]["xau_upper_sell_probe"] is True


def test_wait_engine_metadata_includes_state_policy_input_summary():
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

    policy_input_summary = wait_state.metadata["entry_wait_state_policy_input_v1"]
    compact_context = wait_state.metadata["entry_wait_context_v1"]

    assert policy_input_summary["contract_version"] == "entry_wait_state_policy_input_v1"
    assert policy_input_summary["special_scenes"]["probe_scene_id"] == "xau_upper_sell_probe"
    assert "release_bias_count" in policy_input_summary["bias_bundle"]
    assert (
        compact_context["policy"]["entry_wait_state_policy_input_v1"]["thresholds"]["effective_soft_threshold"]
        == wait_state.metadata["wait_soft_threshold"]
    )
