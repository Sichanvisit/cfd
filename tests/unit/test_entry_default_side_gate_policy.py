from backend.services.entry_default_side_gate_policy import resolve_entry_default_side_gate_v1


def test_default_side_gate_blocks_upper_edge_buy_without_override_package():
    out = resolve_entry_default_side_gate_v1(
        edge_pair_law_v1={
            "context_label": "UPPER_EDGE",
            "winner_side": "BUY",
            "winner_archetype": "upper_break_buy",
            "winner_clear": False,
            "pair_gap": 0.09,
        },
        consumer_archetype_id="upper_break_buy",
        shadow_action="BUY",
        shadow_side="BUY",
        belief_payload={
            "dominant_side": "BALANCED",
            "dominant_mode": "mixed",
            "buy_belief": 0.49,
            "buy_persistence": 0.18,
            "buy_streak": 1,
        },
        barrier_payload={"buy_barrier": 0.18},
        forecast_assist_v1={
            "action_confirm_score": 0.40,
            "confirm_fake_gap": 0.05,
            "wait_confirm_gap": 0.01,
            "continue_fail_gap": 0.0,
        },
    )

    assert out["blocked"] is True
    assert out["reason"] == "upper_edge_buy_requires_break_override"
    assert out["override_package_satisfied"] is False


def test_default_side_gate_allows_upper_edge_buy_with_complete_override_package():
    out = resolve_entry_default_side_gate_v1(
        edge_pair_law_v1={
            "context_label": "UPPER_EDGE",
            "winner_side": "BUY",
            "winner_archetype": "upper_break_buy",
            "winner_clear": True,
            "pair_gap": 0.13,
        },
        consumer_archetype_id="upper_break_buy",
        shadow_action="BUY",
        shadow_side="BUY",
        belief_payload={
            "dominant_side": "BUY",
            "dominant_mode": "continuation",
            "buy_belief": 0.67,
            "buy_persistence": 0.41,
            "buy_streak": 3,
        },
        barrier_payload={"buy_barrier": 0.18},
        forecast_assist_v1={
            "action_confirm_score": 0.74,
            "confirm_fake_gap": 0.19,
            "wait_confirm_gap": 0.09,
            "continue_fail_gap": 0.15,
        },
    )

    assert out["blocked"] is False
    assert out["override_package_satisfied"] is True


def test_default_side_gate_allows_lower_conflict_upper_reject_override_when_complete():
    out = resolve_entry_default_side_gate_v1(
        edge_pair_law_v1={
            "context_label": "LOWER_EDGE",
            "winner_side": "SELL",
            "winner_archetype": "upper_reject_sell",
            "winner_clear": True,
            "pair_gap": 0.08,
        },
        consumer_archetype_id="upper_reject_sell",
        shadow_action="SELL",
        shadow_side="SELL",
        shadow_reason="upper_reject_confirm",
        box_state="LOWER",
        bb_state="UPPER_EDGE",
        belief_payload={
            "dominant_side": "SELL",
            "dominant_mode": "reversal",
            "sell_belief": 0.68,
            "sell_persistence": 0.44,
            "sell_streak": 2,
        },
        barrier_payload={"sell_barrier": 0.22},
        forecast_assist_v1={
            "action_confirm_score": 0.63,
            "confirm_fake_gap": 0.16,
            "wait_confirm_gap": 0.08,
            "continue_fail_gap": 0.12,
        },
    )

    assert out["blocked"] is False
    assert out["override_package_satisfied"] is True
    assert out["conflict_local_upper_override"] is True
    assert "upper_reject_sell" in out["allowed_override_archetypes"]


def test_default_side_gate_clears_block_when_probe_override_is_pending():
    out = resolve_entry_default_side_gate_v1(
        edge_pair_law_v1={
            "context_label": "LOWER_EDGE",
            "winner_side": "SELL",
            "winner_archetype": "upper_reject_sell",
            "winner_clear": False,
            "pair_gap": 0.05,
        },
        consumer_archetype_id="upper_reject_sell",
        shadow_action="SELL",
        shadow_side="SELL",
        shadow_reason="upper_reject_probe_observe",
        shadow_stage="CONFLICT_OBSERVE",
        box_state="LOWER",
        bb_state="MID",
        belief_payload={
            "dominant_side": "BALANCED",
            "dominant_mode": "mixed",
            "sell_belief": 0.23,
            "sell_persistence": 0.0,
            "sell_streak": 0,
        },
        barrier_payload={"sell_barrier": 0.20},
        forecast_assist_v1={
            "action_confirm_score": 0.24,
            "confirm_fake_gap": 0.04,
            "wait_confirm_gap": -0.01,
            "continue_fail_gap": -0.10,
        },
        observe_metadata={
            "probe_candidate_v1": {
                "active": True,
            }
        },
    )

    assert out["observe_probe_override_pending"] is True
    assert out["blocked"] is False
    assert out["reason"] == ""
