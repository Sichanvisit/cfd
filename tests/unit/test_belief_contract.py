import math

from backend.trading.engine.core.belief_engine import build_belief_state, get_belief_memory_snapshot, reset_belief_memory
from backend.trading.engine.core.models import BeliefState, EvidenceVector


def _buy_reversal_evidence(value: float) -> EvidenceVector:
    return EvidenceVector(
        buy_reversal_evidence=value,
        buy_total_evidence=value,
        metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
    )


def _sell_reversal_evidence(value: float) -> EvidenceVector:
    return EvidenceVector(
        sell_reversal_evidence=value,
        sell_total_evidence=value,
        metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
    )


def test_belief_state_exposes_exact_canonical_fields():
    payload = BeliefState().to_dict()

    assert set(payload.keys()) == {
        "buy_belief",
        "sell_belief",
        "buy_persistence",
        "sell_persistence",
        "belief_spread",
        "flip_readiness",
        "belief_instability",
        "dominant_side",
        "dominant_mode",
        "buy_streak",
        "sell_streak",
        "transition_age",
        "metadata",
    }


def test_belief_state_defaults_to_zero_strength_and_empty_metadata():
    belief = BeliefState()

    assert belief.buy_belief == 0.0
    assert belief.sell_belief == 0.0
    assert belief.buy_persistence == 0.0
    assert belief.sell_persistence == 0.0
    assert belief.belief_spread == 0.0
    assert belief.flip_readiness == 0.0
    assert belief.belief_instability == 0.0
    assert belief.dominant_side == "BALANCED"
    assert belief.dominant_mode == "balanced"
    assert belief.buy_streak == 0
    assert belief.sell_streak == 0
    assert belief.transition_age == 0
    assert belief.metadata == {}


def test_belief_builder_accumulates_same_side_evidence_over_new_bars():
    reset_belief_memory()

    first = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=100)
    second = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=101)
    third = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=102)

    assert second.buy_belief > first.buy_belief
    assert third.buy_belief > second.buy_belief
    assert second.buy_persistence > first.buy_persistence
    assert third.buy_persistence > second.buy_persistence
    assert third.transition_age > second.transition_age >= first.transition_age


def test_belief_builder_does_not_double_count_same_event_timestamp():
    reset_belief_memory()

    first = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.90), event_ts=200)
    repeated = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.90), event_ts=200)

    assert repeated.to_dict() == first.to_dict()


def test_belief_builder_exposes_internal_memory_contract_metadata():
    reset_belief_memory()

    belief = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.60), event_ts=250)
    contract = belief.metadata["memory_contract"]

    assert contract["store_scope"] == "per_symbol_timeframe"
    assert contract["key_fields"] == ["symbol", "timeframe"]
    assert contract["mode_belief_fields"] == [
        "buy_reversal_belief",
        "sell_reversal_belief",
        "buy_continuation_belief",
        "sell_continuation_belief",
    ]
    assert contract["streak_fields"] == ["buy_streak", "sell_streak"]
    assert contract["transition_fields"] == [
        "dominant_side",
        "dominant_mode",
        "transition_age",
        "recent_flip_side",
        "recent_flip_age",
    ]
    assert contract["duplicate_event_policy"] == "same_event_ts_returns_cached_output"
    assert belief.metadata["update_contract"] == {
        "belief_update_mode": "ema_rise_decay",
        "persistence_mode": "activation_streak_window",
        "side_dominance_mode": "belief_spread_deadband",
        "mode_dominance_mode": "per_side_max_component",
        "merge_mode": "capped_dominant_merge",
    }


def test_belief_builder_freezes_semantic_owner_contract_to_persistence_only():
    reset_belief_memory()

    belief = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.60), event_ts=251)

    assert belief.metadata["semantic_owner_contract"] == "belief_thesis_persistence_only_v1"
    assert belief.metadata["belief_freeze_phase"] == "B0"
    assert belief.metadata["canonical_belief_identity_fields_v1"] == [
        "buy_belief",
        "sell_belief",
        "buy_persistence",
        "sell_persistence",
        "belief_spread",
        "flip_readiness",
        "belief_instability",
        "dominant_side",
        "dominant_mode",
        "buy_streak",
        "sell_streak",
        "transition_age",
    ]
    assert belief.metadata["owner_boundaries_v1"] == {
        "position_owner_fields": [],
        "response_owner_fields": [],
        "state_owner_fields": [],
        "direct_side_identity_allowed": False,
        "direct_action_identity_allowed": False,
        "role": "thesis_persistence_and_reconfirmation_only",
        "ml_feature_usage_allowed": True,
        "ml_owner_override_allowed": False,
    }


def test_belief_builder_freezes_pre_ml_readiness_contract():
    reset_belief_memory()

    belief = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.60), event_ts=2511)
    contract = belief.metadata["pre_ml_readiness_contract_v1"]

    assert belief.metadata["belief_pre_ml_phase"] == "B6"
    assert contract == {
        "phase": "B6",
        "status": "READY",
        "required_feature_fields": [
            "buy_belief",
            "sell_belief",
            "buy_persistence",
            "sell_persistence",
            "belief_spread",
            "transition_age",
            "dominant_side",
            "dominant_mode",
        ],
        "recommended_feature_fields": [
            "flip_readiness",
            "belief_instability",
        ],
        "semantic_explainable_without_ml": True,
        "ml_usage_role": "feature_only_not_owner",
        "owner_collision_allowed": False,
        "owner_collision_boundary": (
            "Belief may be consumed by ML as a calibration feature, "
            "but ML must not redefine position identity, response event identity, "
            "state regime identity, or direct action ownership."
        ),
        "safe_ml_targets": [
            "wait_quality_calibration",
            "entry_quality_calibration",
            "hold_exit_patience_calibration",
            "flip_readiness_calibration",
        ],
    }


def test_belief_builder_exposes_required_and_recommended_pre_ml_features_as_first_class_fields():
    payload = BeliefState().to_dict()

    for field_name in [
        "buy_belief",
        "sell_belief",
        "buy_persistence",
        "sell_persistence",
        "belief_spread",
        "transition_age",
        "dominant_side",
        "dominant_mode",
        "flip_readiness",
        "belief_instability",
    ]:
        assert field_name in payload


def test_belief_builder_promotes_dominance_and_streak_outputs_to_first_class_fields():
    reset_belief_memory()

    belief = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=252)

    assert belief.dominant_side == "BUY"
    assert belief.dominant_mode == "reversal"
    assert belief.buy_streak == 1
    assert belief.sell_streak == 0
    assert belief.metadata["global_dominant_side"] == belief.dominant_side
    assert belief.metadata["global_dominant_mode"] == belief.dominant_mode
    assert belief.metadata["buy_streak"] == belief.buy_streak
    assert belief.metadata["sell_streak"] == belief.sell_streak


def test_belief_builder_counts_strong_reversal_probe_into_sell_streak_before_full_advantage_gap():
    reset_belief_memory()

    belief = build_belief_state(
        ("XAUUSD", "15M"),
        EvidenceVector(
            sell_reversal_evidence=0.18,
            sell_total_evidence=0.18,
            buy_total_evidence=0.17,
            metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
        ),
        event_ts=2521,
    )

    assert belief.sell_streak == 1
    assert belief.sell_persistence > 0.0
    assert belief.sell_belief > 0.0


def test_belief_builder_keeps_xau_buy_streak_alive_on_second_support_retest():
    reset_belief_memory()

    first = build_belief_state(("XAUUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=2522)
    second = build_belief_state(("XAUUSD", "15M"), _buy_reversal_evidence(0.10), event_ts=2523)

    assert first.buy_streak == 1
    assert second.buy_streak == 2
    assert second.buy_persistence > first.buy_persistence
    assert second.dominant_side == "BUY"


def test_belief_builder_promotes_flip_readiness_and_instability_outputs():
    reset_belief_memory()

    belief = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=253)

    assert belief.flip_readiness == belief.metadata["flip_readiness"]
    assert belief.belief_instability == belief.metadata["belief_instability"]
    assert "flip_components_v1" in belief.metadata
    assert "belief_instability_components_v1" in belief.metadata


def test_belief_builder_decays_more_slowly_than_it_rises_to_a_spike():
    reset_belief_memory()

    spike = build_belief_state(("XAUUSD", "15M"), _buy_reversal_evidence(1.0), event_ts=300)
    decay = build_belief_state(("XAUUSD", "15M"), _buy_reversal_evidence(0.0), event_ts=301)

    assert 0.0 < spike.buy_belief < 1.0
    assert 0.0 < decay.buy_belief < spike.buy_belief


def test_belief_builder_uses_alpha_rise_and_alpha_decay_contract():
    reset_belief_memory()

    rise = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(1.0), event_ts=310)
    decay = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.0), event_ts=311)

    assert math.isclose(rise.buy_belief, 0.45, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(decay.buy_belief, 0.3375, rel_tol=0.0, abs_tol=1e-9)
    assert rise.metadata["alpha_rise"] == 0.45
    assert rise.metadata["alpha_decay"] == 0.25


def test_belief_builder_is_symmetric_for_mirrored_buy_and_sell_cases():
    reset_belief_memory()

    buy = build_belief_state(("NAS100", "15M"), _buy_reversal_evidence(0.75), event_ts=400)
    reset_belief_memory()
    sell = build_belief_state(("NAS100", "15M"), _sell_reversal_evidence(0.75), event_ts=400)

    assert buy.buy_belief == sell.sell_belief
    assert buy.buy_persistence == sell.sell_persistence
    assert buy.belief_spread == -sell.belief_spread


def test_belief_builder_switches_mode_without_zeroing_side_belief():
    reset_belief_memory()

    reversal = EvidenceVector(
        buy_reversal_evidence=0.80,
        buy_total_evidence=0.80,
        metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
    )
    continuation = EvidenceVector(
        buy_continuation_evidence=0.90,
        buy_total_evidence=0.90,
        metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
    )

    first = build_belief_state(("BTCUSD", "15M"), reversal, event_ts=500)
    second = build_belief_state(("BTCUSD", "15M"), continuation, event_ts=501)

    assert first.metadata["global_dominant_mode"] == "reversal"
    assert second.metadata["global_dominant_mode"] == "continuation"
    assert second.buy_belief > 0.0
    assert second.transition_age == 1


def test_belief_builder_uses_capped_merge_for_side_belief():
    reset_belief_memory()

    first = build_belief_state(
        ("BTCUSD", "15M"),
        EvidenceVector(
            buy_reversal_evidence=0.80,
            buy_total_evidence=0.80,
            metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
        ),
        event_ts=520,
    )
    second = build_belief_state(
        ("BTCUSD", "15M"),
        EvidenceVector(
            buy_continuation_evidence=0.60,
            buy_total_evidence=0.60,
            metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
        ),
        event_ts=521,
    )

    rev = second.metadata["buy_reversal_belief"]
    cont = second.metadata["buy_continuation_belief"]
    dominant = max(rev, cont)
    support = min(rev, cont)

    assert first.metadata["merge_weight"] == 0.25
    assert math.isclose(second.buy_belief, dominant + (0.25 * support), rel_tol=0.0, abs_tol=1e-9)


def test_belief_builder_keeps_spread_small_when_sides_alternate():
    reset_belief_memory()

    build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.90), event_ts=600)
    balanced = build_belief_state(("BTCUSD", "15M"), _sell_reversal_evidence(0.90), event_ts=601)

    assert abs(balanced.belief_spread) < 0.50
    assert balanced.metadata["global_dominant_side"] in {"BALANCED", "BUY", "SELL"}


def test_belief_builder_uses_deadband_for_side_dominance():
    reset_belief_memory()

    build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.30), event_ts=610)
    balanced = build_belief_state(("BTCUSD", "15M"), _sell_reversal_evidence(0.30), event_ts=611)

    assert abs(balanced.belief_spread) < balanced.metadata["dominance_deadband"]
    assert balanced.metadata["global_dominant_side"] == "BALANCED"
    assert balanced.metadata["global_dominant_mode"] == "balanced"


def test_belief_builder_keeps_memory_isolated_per_symbol_and_timeframe():
    reset_belief_memory()

    build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.90), event_ts=700)
    build_belief_state(("BTCUSD", "1H"), _sell_reversal_evidence(0.80), event_ts=700)
    build_belief_state(("XAUUSD", "15M"), _buy_reversal_evidence(0.70), event_ts=700)

    btc_m15 = get_belief_memory_snapshot(("BTCUSD", "15M"))
    btc_h1 = get_belief_memory_snapshot(("BTCUSD", "1H"))
    xau_m15 = get_belief_memory_snapshot(("XAUUSD", "15M"))

    assert btc_m15["buy_reversal_belief"] > 0.0
    assert btc_m15["sell_reversal_belief"] == 0.0
    assert btc_h1["sell_reversal_belief"] > 0.0
    assert btc_h1["buy_reversal_belief"] == 0.0
    assert xau_m15["buy_reversal_belief"] > 0.0
    assert xau_m15["last_event_ts"] == 700


def test_belief_builder_resets_streak_when_signal_goes_inactive():
    reset_belief_memory()

    build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=800)
    build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=801)
    inactive = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.02), event_ts=802)
    memory = get_belief_memory_snapshot(("BTCUSD", "15M"))

    assert inactive.buy_persistence == 0.0
    assert memory["buy_streak"] == 0


def test_belief_builder_transition_age_increments_only_for_same_side_and_mode():
    reset_belief_memory()

    first = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=900)
    second = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.80), event_ts=901)
    third = build_belief_state(
        ("BTCUSD", "15M"),
        EvidenceVector(
            buy_continuation_evidence=0.90,
            buy_total_evidence=0.90,
            metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
        ),
        event_ts=902,
    )
    fourth = build_belief_state(
        ("BTCUSD", "15M"),
        EvidenceVector(
            buy_continuation_evidence=0.90,
            buy_total_evidence=0.90,
            metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
        ),
        event_ts=903,
    )

    assert first.transition_age == 1
    assert second.transition_age == 2
    assert third.transition_age == 3
    assert third.metadata["global_dominant_mode"] == "reversal"
    assert fourth.transition_age == 1
    assert fourth.metadata["global_dominant_mode"] == "continuation"


def test_belief_builder_flip_readiness_rises_after_confirmed_opposite_turn():
    reset_belief_memory()

    build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.90), event_ts=1000)
    build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.90), event_ts=1001)
    first_sell = build_belief_state(("BTCUSD", "15M"), _sell_reversal_evidence(0.90), event_ts=1002)
    second_sell = build_belief_state(("BTCUSD", "15M"), _sell_reversal_evidence(0.90), event_ts=1003)
    third_sell = build_belief_state(("BTCUSD", "15M"), _sell_reversal_evidence(0.90), event_ts=1004)

    assert second_sell.flip_readiness >= first_sell.flip_readiness
    assert third_sell.flip_readiness >= second_sell.flip_readiness
    assert third_sell.transition_age >= 2
    assert third_sell.flip_readiness >= 0.50


def test_belief_builder_instability_is_higher_inside_deadband_than_in_stable_trend():
    reset_belief_memory()

    build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.30), event_ts=1100)
    unstable = build_belief_state(("BTCUSD", "15M"), _sell_reversal_evidence(0.30), event_ts=1101)

    reset_belief_memory()
    build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.90), event_ts=1110)
    stable = build_belief_state(("BTCUSD", "15M"), _buy_reversal_evidence(0.90), event_ts=1111)

    assert unstable.belief_instability > stable.belief_instability
    assert unstable.belief_instability >= 0.50
