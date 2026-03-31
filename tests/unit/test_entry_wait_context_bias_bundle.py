from backend.services.entry_wait_context_bias_bundle import (
    compact_entry_wait_bias_bundle_v1,
    resolve_entry_wait_bias_bundle_v1,
)
from backend.services.entry_wait_context_contract import build_entry_wait_context_v1
from backend.services.wait_engine import WaitEngine


def test_entry_wait_bias_bundle_keeps_neutral_thresholds_without_active_bias():
    context = build_entry_wait_context_v1(
        payload={
            "symbol": "BTCUSD",
            "action": "BUY",
            "core_allowed_action": "BUY_ONLY",
            "preflight_allowed_action": "BUY_ONLY",
        }
    )

    bundle = resolve_entry_wait_bias_bundle_v1(context)
    summary = compact_entry_wait_bias_bundle_v1(bundle)
    threshold_adjustment = bundle["threshold_adjustment_v1"]

    assert summary["release_bias_count"] == 0
    assert summary["wait_lock_bias_count"] == 0
    assert threshold_adjustment["base_soft_threshold"] == threshold_adjustment["effective_soft_threshold"]
    assert threshold_adjustment["base_hard_threshold"] == threshold_adjustment["effective_hard_threshold"]
    assert threshold_adjustment["combined_soft_multiplier"] == 1.0
    assert threshold_adjustment["combined_hard_multiplier"] == 1.0


def test_entry_wait_bias_bundle_stacks_belief_and_edge_release():
    context = build_entry_wait_context_v1(
        payload={
            "symbol": "BTCUSD",
            "action": "BUY",
            "core_allowed_action": "BUY_ONLY",
            "preflight_allowed_action": "BOTH",
            "belief_state_v1": {
                "buy_persistence": 0.62,
                "sell_persistence": 0.04,
                "belief_spread": 0.18,
                "dominant_side": "BUY",
                "dominant_mode": "continuation",
                "buy_streak": 3,
                "sell_streak": 0,
                "metadata": {"dominance_deadband": 0.05},
            },
            "edge_pair_law_v1": {
                "context_label": "LOWER_EDGE",
                "winner_side": "BUY",
                "winner_clear": True,
                "pair_gap": 0.22,
            },
        }
    )

    bundle = resolve_entry_wait_bias_bundle_v1(context)
    summary = compact_entry_wait_bias_bundle_v1(bundle)
    threshold_adjustment = bundle["threshold_adjustment_v1"]

    assert bundle["belief_wait_bias_v1"]["prefer_confirm_release"] is True
    assert bundle["edge_pair_wait_bias_v1"]["prefer_confirm_release"] is True
    assert "belief" in summary["active_release_sources"]
    assert "edge_pair" in summary["active_release_sources"]
    assert threshold_adjustment["effective_soft_threshold"] > threshold_adjustment["base_soft_threshold"]
    assert threshold_adjustment["effective_hard_threshold"] > threshold_adjustment["base_hard_threshold"]


def test_entry_wait_bias_bundle_keeps_helper_hints_separate_from_wait_lock_bias():
    context = build_entry_wait_context_v1(
        payload={
            "symbol": "XAUUSD",
            "action": "BUY",
            "core_allowed_action": "BUY_ONLY",
            "preflight_allowed_action": "BUY_ONLY",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_soft_block_reason": "energy_soft_block",
            "consumer_energy_soft_block_strength": 0.82,
            "consumer_energy_wait_vs_enter_hint": "prefer_wait",
            "belief_state_v1": {
                "buy_persistence": 0.10,
                "sell_persistence": 0.42,
                "belief_spread": -0.01,
                "dominant_side": "SELL",
                "dominant_mode": "reversal",
                "buy_streak": 1,
                "sell_streak": 3,
                "metadata": {"dominance_deadband": 0.05},
            },
        }
    )

    bundle = resolve_entry_wait_bias_bundle_v1(context)
    summary = compact_entry_wait_bias_bundle_v1(bundle)
    threshold_adjustment = bundle["threshold_adjustment_v1"]

    assert context["helper_hints"]["soft_block_active"] is True
    assert bundle["belief_wait_bias_v1"]["prefer_wait_lock"] is True
    assert summary["active_wait_lock_sources"] == ["belief"]
    assert threshold_adjustment["effective_soft_threshold"] < threshold_adjustment["base_soft_threshold"]
    assert threshold_adjustment["effective_hard_threshold"] < threshold_adjustment["base_hard_threshold"]


def test_wait_engine_metadata_includes_bias_bundle_summary():
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

    bundle_summary = wait_state.metadata["entry_wait_bias_bundle_v1"]
    compact_context = wait_state.metadata["entry_wait_context_v1"]

    assert bundle_summary["contract_version"] == "entry_wait_bias_bundle_v1"
    assert "probe" in bundle_summary["active_release_sources"]
    assert compact_context["bias"]["bundle"]["contract_version"] == "entry_wait_bias_bundle_v1"
    assert "probe" in compact_context["bias"]["bundle"]["active_release_sources"]
    assert (
        compact_context["bias"]["bundle"]["threshold_adjustment"]["effective_soft_threshold"]
        == wait_state.metadata["wait_soft_threshold"]
    )
