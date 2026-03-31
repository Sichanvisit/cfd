from backend.trading.engine.core.evidence_engine import build_evidence_vector
from backend.trading.engine.core.models import (
    EvidenceVector,
    PositionEnergySnapshot,
    PositionInterpretation,
    PositionSnapshot,
    ResponseVectorV2,
    StateVectorV2,
)


def test_evidence_vector_exposes_exact_canonical_fields():
    payload = EvidenceVector().to_dict()

    assert set(payload.keys()) == {
        "buy_reversal_evidence",
        "sell_reversal_evidence",
        "buy_continuation_evidence",
        "sell_continuation_evidence",
        "buy_total_evidence",
        "sell_total_evidence",
        "metadata",
    }


def test_evidence_vector_defaults_to_zero_strength_and_empty_metadata():
    vector = EvidenceVector()

    assert vector.buy_reversal_evidence == 0.0
    assert vector.sell_reversal_evidence == 0.0
    assert vector.buy_continuation_evidence == 0.0
    assert vector.sell_continuation_evidence == 0.0
    assert vector.buy_total_evidence == 0.0
    assert vector.sell_total_evidence == 0.0
    assert vector.metadata == {}


def test_evidence_builder_prefers_buy_reversal_for_lower_hold_range_context():
    position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_LOWER_STRONG",
            secondary_context_label="LOWER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )
    response = ResponseVectorV2(lower_hold_up=1.0, mid_reclaim_up=0.6)
    state = StateVectorV2(
        range_reversal_gain=1.18,
        trend_pullback_gain=0.94,
        breakout_continuation_gain=0.90,
        noise_damp=0.95,
        conflict_damp=0.90,
        alignment_gain=1.20,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    vector = build_evidence_vector(position, response, state)

    assert vector.buy_reversal_evidence > vector.sell_reversal_evidence
    assert vector.buy_reversal_evidence > vector.buy_continuation_evidence
    assert vector.buy_total_evidence == vector.buy_reversal_evidence
    assert vector.metadata["dominant_side"] == "BUY"
    assert vector.metadata["dominant_mode_by_side"]["BUY"] == "reversal"


def test_evidence_builder_prefers_buy_continuation_for_upper_break_trend_context():
    position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_UPPER_STRONG",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )
    response = ResponseVectorV2(upper_break_up=1.0)
    state = StateVectorV2(
        range_reversal_gain=0.88,
        trend_pullback_gain=1.18,
        breakout_continuation_gain=1.12,
        noise_damp=0.92,
        conflict_damp=0.95,
        alignment_gain=1.20,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    vector = build_evidence_vector(position, response, state)

    assert vector.buy_continuation_evidence > vector.buy_reversal_evidence
    assert vector.buy_total_evidence == vector.buy_continuation_evidence
    assert vector.metadata["dominant_side"] == "BUY"
    assert vector.metadata["dominant_mode_by_side"]["BUY"] == "continuation"


def test_evidence_builder_prefers_sell_reversal_for_upper_reject_range_context():
    position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_UPPER_STRONG",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )
    response = ResponseVectorV2(upper_reject_down=1.0, mid_lose_down=0.6)
    state = StateVectorV2(
        range_reversal_gain=1.18,
        trend_pullback_gain=0.94,
        breakout_continuation_gain=0.90,
        noise_damp=0.95,
        conflict_damp=0.90,
        alignment_gain=1.20,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    vector = build_evidence_vector(position, response, state)

    assert vector.sell_reversal_evidence > vector.buy_reversal_evidence
    assert vector.sell_reversal_evidence > vector.sell_continuation_evidence
    assert vector.sell_total_evidence == vector.sell_reversal_evidence
    assert vector.metadata["dominant_side"] == "SELL"
    assert vector.metadata["dominant_mode_by_side"]["SELL"] == "reversal"


def test_evidence_builder_prefers_sell_continuation_for_lower_break_trend_context():
    position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_LOWER_STRONG",
            secondary_context_label="LOWER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )
    response = ResponseVectorV2(lower_break_down=1.0)
    state = StateVectorV2(
        range_reversal_gain=0.88,
        trend_pullback_gain=1.18,
        breakout_continuation_gain=1.12,
        noise_damp=0.92,
        conflict_damp=0.95,
        alignment_gain=1.20,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    vector = build_evidence_vector(position, response, state)

    assert vector.sell_continuation_evidence > vector.sell_reversal_evidence
    assert vector.sell_total_evidence == vector.sell_continuation_evidence
    assert vector.metadata["dominant_side"] == "SELL"
    assert vector.metadata["dominant_mode_by_side"]["SELL"] == "continuation"


def test_evidence_builder_applies_countertrend_penalty_by_side():
    position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_UPPER_STRONG",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )
    response = ResponseVectorV2(upper_reject_down=1.0, mid_lose_down=0.5)
    neutral_state = StateVectorV2(
        range_reversal_gain=1.18,
        noise_damp=1.0,
        conflict_damp=1.0,
        alignment_gain=1.20,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )
    buy_only_state = StateVectorV2(
        range_reversal_gain=1.18,
        noise_damp=1.0,
        conflict_damp=1.0,
        alignment_gain=1.20,
        countertrend_penalty=0.25,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BUY_ONLY"},
    )

    neutral_vector = build_evidence_vector(position, response, neutral_state)
    penalized_vector = build_evidence_vector(position, response, buy_only_state)

    assert penalized_vector.sell_reversal_evidence < neutral_vector.sell_reversal_evidence
    assert penalized_vector.metadata["policy_multipliers"]["SELL"] == 0.75
    assert penalized_vector.metadata["policy_reasons"]["SELL"] == "countertrend_sell_penalty"


def test_evidence_builder_uses_capped_dominant_merge_for_total_evidence():
    position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_MIDDLE",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )
    response = ResponseVectorV2(upper_break_up=1.0, lower_hold_up=0.7, mid_reclaim_up=0.7)
    state = StateVectorV2(
        range_reversal_gain=1.10,
        trend_pullback_gain=1.15,
        breakout_continuation_gain=1.10,
        noise_damp=1.0,
        conflict_damp=1.0,
        alignment_gain=1.0,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    vector = build_evidence_vector(position, response, state)
    dominant = max(vector.buy_reversal_evidence, vector.buy_continuation_evidence)
    support = min(vector.buy_reversal_evidence, vector.buy_continuation_evidence)
    simple_sum = vector.buy_reversal_evidence + vector.buy_continuation_evidence

    assert support > 0.0
    assert vector.buy_total_evidence == dominant + (0.35 * support)
    assert vector.buy_total_evidence < simple_sum
    assert vector.metadata["merge_mode"] == "capped_dominant_merge"


def test_evidence_builder_damps_total_evidence_for_unresolved_high_conflict_position():
    low_conflict_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="UNRESOLVED_POSITION",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.10),
    )
    high_conflict_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="UNRESOLVED_POSITION",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.95),
    )
    response = ResponseVectorV2(upper_break_up=0.9, upper_reject_down=0.6)
    state = StateVectorV2(
        range_reversal_gain=1.05,
        trend_pullback_gain=1.10,
        breakout_continuation_gain=1.08,
        noise_damp=0.85,
        conflict_damp=0.80,
        alignment_gain=1.0,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    low_conflict_vector = build_evidence_vector(low_conflict_position, response, state)
    high_conflict_vector = build_evidence_vector(high_conflict_position, response, state)

    assert high_conflict_vector.buy_total_evidence < low_conflict_vector.buy_total_evidence
    assert high_conflict_vector.sell_total_evidence < low_conflict_vector.sell_total_evidence
    assert high_conflict_vector.metadata["archetype_fit"]["buy_continuation"]["fit"] < low_conflict_vector.metadata["archetype_fit"]["buy_continuation"]["fit"]


def test_evidence_builder_is_symmetric_for_mirrored_reversal_cases():
    lower_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_LOWER_STRONG",
            secondary_context_label="LOWER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )
    upper_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_UPPER_STRONG",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )
    buy_response = ResponseVectorV2(lower_hold_up=1.0, mid_reclaim_up=0.5)
    sell_response = ResponseVectorV2(upper_reject_down=1.0, mid_lose_down=0.5)
    state = StateVectorV2(
        range_reversal_gain=1.18,
        noise_damp=0.90,
        conflict_damp=0.95,
        alignment_gain=1.20,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    buy_vector = build_evidence_vector(lower_position, buy_response, state)
    sell_vector = build_evidence_vector(upper_position, sell_response, state)

    assert buy_vector.buy_reversal_evidence == sell_vector.sell_reversal_evidence
    assert buy_vector.buy_total_evidence == sell_vector.sell_total_evidence


def test_evidence_builder_position_fit_contract_uses_only_allowed_position_inputs():
    position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_UPPER_WEAK",
            bias_label="UPPER_BIAS",
            secondary_context_label="UPPER_CONTEXT",
            dominance_label="UPPER_DOMINANT_CONFLICT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.20),
    )
    response = ResponseVectorV2(upper_break_up=0.9)
    state = StateVectorV2(
        trend_pullback_gain=1.18,
        breakout_continuation_gain=1.12,
        noise_damp=1.0,
        conflict_damp=1.0,
        alignment_gain=1.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    vector = build_evidence_vector(position, response, state)
    contract = vector.metadata["position_fit_contract"]

    assert contract["inputs"] == [
        "PositionInterpretation.primary_label",
        "PositionInterpretation.bias_label",
        "PositionInterpretation.secondary_context_label",
        "PositionEnergySnapshot.position_conflict_score",
    ]
    assert contract["direction_source_used"] is False


def test_evidence_builder_does_not_depend_on_position_dominance_label():
    base_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="UNRESOLVED_POSITION",
            secondary_context_label="LOWER_CONTEXT",
            dominance_label="LOWER_DOMINANT_CONFLICT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.30),
    )
    changed_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="UNRESOLVED_POSITION",
            secondary_context_label="LOWER_CONTEXT",
            dominance_label="BALANCED_CONFLICT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.30),
    )
    response = ResponseVectorV2(lower_hold_up=0.8, mid_reclaim_up=0.4)
    state = StateVectorV2(
        range_reversal_gain=1.18,
        noise_damp=1.0,
        conflict_damp=1.0,
        alignment_gain=1.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    base_vector = build_evidence_vector(base_position, response, state)
    changed_vector = build_evidence_vector(changed_position, response, state)

    assert base_vector.buy_reversal_evidence == changed_vector.buy_reversal_evidence
    assert base_vector.buy_total_evidence == changed_vector.buy_total_evidence
    assert "dominance_label" not in base_vector.metadata["archetype_fit"]["buy_reversal"]


def test_evidence_builder_position_conflict_score_only_dampens_fit():
    clean_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_UPPER_STRONG",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.0),
    )
    conflicted_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_UPPER_STRONG",
            secondary_context_label="UPPER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.8),
    )
    response = ResponseVectorV2(upper_break_up=1.0)
    state = StateVectorV2(
        trend_pullback_gain=1.18,
        breakout_continuation_gain=1.12,
        noise_damp=1.0,
        conflict_damp=1.0,
        alignment_gain=1.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    clean_vector = build_evidence_vector(clean_position, response, state)
    conflicted_vector = build_evidence_vector(conflicted_position, response, state)

    assert conflicted_vector.buy_continuation_evidence < clean_vector.buy_continuation_evidence
    assert conflicted_vector.metadata["archetype_fit"]["buy_continuation"]["fit"] < clean_vector.metadata["archetype_fit"]["buy_continuation"]["fit"]


def test_evidence_builder_hands_middle_locations_off_to_response_more_than_edge_locations():
    edge_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_LOWER_WEAK",
            secondary_context_label="LOWER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(
            lower_position_force=0.92,
            upper_position_force=0.0,
            middle_neutrality=0.0,
            position_conflict_score=0.0,
        ),
    )
    middle_position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_LOWER_WEAK",
            secondary_context_label="LOWER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(
            lower_position_force=0.28,
            upper_position_force=0.0,
            middle_neutrality=0.78,
            position_conflict_score=0.0,
        ),
    )
    response = ResponseVectorV2(lower_hold_up=0.9, mid_reclaim_up=0.4)
    state = StateVectorV2(
        range_reversal_gain=1.18,
        trend_pullback_gain=0.94,
        breakout_continuation_gain=0.90,
        noise_damp=0.92,
        conflict_damp=1.0,
        alignment_gain=1.08,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    edge_vector = build_evidence_vector(edge_position, response, state)
    middle_vector = build_evidence_vector(middle_position, response, state)

    edge_fit = edge_vector.metadata["archetype_fit"]["buy_reversal"]
    middle_fit = middle_vector.metadata["archetype_fit"]["buy_reversal"]

    assert edge_fit["position_authority"]["location_role"] == "edge_anchor"
    assert middle_fit["position_authority"]["location_role"] == "middle_handoff"
    assert edge_fit["position_authority"]["position_authority"] > middle_fit["position_authority"]["position_authority"]
    assert edge_vector.buy_reversal_evidence > middle_vector.buy_reversal_evidence


def test_evidence_builder_exposes_explanatory_metadata_contract():
    position = PositionSnapshot(
        interpretation=PositionInterpretation(
            primary_label="ALIGNED_LOWER_WEAK",
            bias_label="LOWER_BIAS",
            secondary_context_label="LOWER_CONTEXT",
        ),
        energy=PositionEnergySnapshot(position_conflict_score=0.18),
    )
    response = ResponseVectorV2(lower_hold_up=0.9, mid_reclaim_up=0.4, upper_break_up=0.2)
    state = StateVectorV2(
        range_reversal_gain=1.18,
        trend_pullback_gain=0.94,
        breakout_continuation_gain=0.90,
        noise_damp=0.88,
        conflict_damp=0.83,
        alignment_gain=1.16,
        countertrend_penalty=0.0,
        metadata={"state_contract": "canonical_v2", "mapper_version": "state_vector_v2_s3", "source_direction_policy": "BOTH"},
    )

    vector = build_evidence_vector(position, response, state)
    meta = vector.metadata
    reasons = meta["evidence_reasons"]

    assert meta["evidence_contract"] == "canonical_v1"
    assert meta["mapper_version"] == "evidence_vector_v1_e4"
    assert meta["position_contract"] == "position_snapshot_v2"
    assert meta["response_contract"] == "response_vector_v2"
    assert meta["state_contract"] == "canonical_v2"
    assert meta["merge_mode"] == "capped_dominant_merge"
    assert set(meta["archetype_fit"].keys()) == {
        "buy_reversal",
        "sell_reversal",
        "buy_continuation",
        "sell_continuation",
    }
    assert "buy_reversal_base" in meta["component_scores"]
    assert "buy_dominant_component" in meta["component_scores"]
    assert meta["dominant_side"] == "BUY"
    assert "BUY" in meta["dominant_mode_by_side"]
    assert set(reasons.keys()) == {
        "buy_reversal_evidence",
        "sell_reversal_evidence",
        "buy_continuation_evidence",
        "sell_continuation_evidence",
        "buy_total_evidence",
        "sell_total_evidence",
    }
    assert "lower_hold_up + mid_reclaim_up" in reasons["buy_reversal_evidence"]
    assert "range_reversal_gain" in reasons["buy_reversal_evidence"]
    assert "upper_break_up" in reasons["buy_continuation_evidence"]
    assert "breakout_continuation_gain" in reasons["buy_continuation_evidence"]
    assert "capped dominant merge" in reasons["buy_total_evidence"]
