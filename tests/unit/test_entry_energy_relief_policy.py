from backend.services.entry_energy_relief_policy import resolve_entry_energy_soft_block_policy_v1


def test_energy_relief_policy_blocks_without_relief():
    out = resolve_entry_energy_soft_block_policy_v1(
        symbol="BTCUSD",
        shadow_action="SELL",
        shadow_reason="upper_reject_confirm",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        default_side_gate_v1={
            "context_label": "UPPER_EDGE",
            "acting_against_default": False,
            "same_side_barrier": 0.42,
        },
        forecast_assist_v1={
            "action_confirm_score": 0.08,
            "wait_confirm_gap": -0.26,
            "continue_fail_gap": -0.31,
        },
        energy_soft_block_active=True,
        energy_soft_block_reason="forecast_gap_wait_bias",
        energy_soft_block_strength=0.33,
        energy_action_readiness=0.18,
        effective_priority_rank=0,
        adjusted_core_score=0.58,
    )

    assert out["confirm_energy_relief"] is False
    assert out["relief_flags"] == []
    assert out["energy_soft_block_should_block"] is True


def test_energy_relief_policy_applies_confirm_relief():
    out = resolve_entry_energy_soft_block_policy_v1(
        symbol="BTCUSD",
        shadow_action="SELL",
        shadow_reason="upper_reject_confirm",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        default_side_gate_v1={
            "context_label": "UPPER_EDGE",
            "acting_against_default": False,
            "same_side_barrier": 0.22,
        },
        observe_metadata={
            "forecast_upper_reject_relief_v1": {
                "applied": True,
                "reason": "upper_reject_confirm",
            }
        },
        forecast_assist_v1={
            "action_confirm_score": 0.19,
            "wait_confirm_gap": -0.12,
            "continue_fail_gap": -0.16,
        },
        energy_soft_block_active=True,
        energy_soft_block_reason="forecast_gap_wait_bias",
        energy_soft_block_strength=0.25,
        energy_action_readiness=0.0,
        effective_priority_rank=0,
        adjusted_core_score=0.74,
    )

    assert out["confirm_energy_relief_local_ready"] is True
    assert out["confirm_energy_relief"] is True
    assert out["relief_flags"] == ["confirm_energy_relief"]
    assert out["energy_soft_block_should_block"] is False


def test_energy_relief_policy_applies_xau_second_support_probe_relief():
    out = resolve_entry_energy_soft_block_policy_v1(
        symbol="XAUUSD",
        shadow_action="BUY",
        shadow_reason="lower_support_probe_observe",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        probe_plan_v1={
            "ready_for_entry": True,
            "symbol_scene_relief": "xau_second_support_buy_probe",
            "intended_action": "BUY",
            "candidate_support": 0.46,
            "pair_gap": 0.20,
            "same_side_barrier": 0.52,
        },
        energy_soft_block_active=True,
        energy_soft_block_reason="barrier_soft_block",
        energy_soft_block_strength=0.81,
        energy_action_readiness=0.20,
        effective_priority_rank=0,
        adjusted_core_score=0.41,
    )

    assert out["xau_second_support_energy_relief"] is True
    assert out["relief_flags"] == ["xau_second_support_energy_relief"]
    assert out["energy_soft_block_should_block"] is False


def test_energy_relief_policy_applies_xau_upper_mixed_confirm_relief():
    out = resolve_entry_energy_soft_block_policy_v1(
        symbol="XAUUSD",
        shadow_action="SELL",
        shadow_reason="upper_reject_mixed_confirm",
        consumer_archetype_id="upper_reject_sell",
        box_state="MIDDLE",
        bb_state="UPPER_EDGE",
        default_side_gate_v1={
            "default_side": "SELL",
            "context_label": "UPPER_EDGE",
            "same_side_barrier": 0.28,
            "acting_archetype": "upper_reject_sell",
        },
        forecast_assist_v1={
            "action_confirm_score": 0.18,
            "wait_confirm_gap": -0.07,
            "continue_fail_gap": -0.15,
        },
        energy_soft_block_active=True,
        energy_soft_block_reason="forecast_wait_bias",
        energy_soft_block_strength=0.66,
        energy_action_readiness=0.22,
        effective_priority_rank=1,
        adjusted_core_score=0.58,
    )

    assert out["xau_upper_mixed_confirm_energy_relief"] is True
    assert out["relief_flags"] == ["xau_upper_mixed_confirm_energy_relief"]
    assert out["energy_soft_block_should_block"] is False
