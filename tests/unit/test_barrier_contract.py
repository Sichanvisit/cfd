import math
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.trading.engine.core.barrier_engine import build_barrier_state
from backend.trading.engine.core.models import (
    BeliefState,
    EvidenceVector,
    PositionEnergySnapshot,
    PositionInterpretation,
    PositionSnapshot,
    StateVectorV2,
)


def _position_snapshot(
    *,
    primary_label: str,
    bias_label: str = "",
    secondary_context_label: str = "NEUTRAL_CONTEXT",
    conflict_kind: str = "",
    dominance_label: str = "",
    position_conflict_score: float = 0.0,
    middle_neutrality: float = 0.0,
) -> PositionSnapshot:
    snapshot = PositionSnapshot()
    snapshot.interpretation = PositionInterpretation(
        primary_label=primary_label,
        bias_label=bias_label,
        secondary_context_label=secondary_context_label,
        conflict_kind=conflict_kind,
        dominance_label=dominance_label,
    )
    snapshot.energy = PositionEnergySnapshot(
        position_conflict_score=position_conflict_score,
        middle_neutrality=middle_neutrality,
    )
    return snapshot


def _state_vector(
    *,
    direction_policy: str = "BOTH",
    liquidity_penalty: float = 0.0,
    volatility_penalty: float = 0.0,
    session_regime_state: str = "SESSION_EDGE_ROTATION",
    session_expansion_state: str = "IN_SESSION_BOX",
    session_exhaustion_state: str = "LOW_EXHAUSTION_RISK",
    topdown_spacing_state: str = "WIDE_SPACING",
    topdown_slope_state: str = "UP_SLOPE_ALIGNED",
    topdown_confluence_state: str = "WEAK_CONFLUENCE",
    spread_stress_state: str = "NORMAL_SPREAD",
    volume_participation_state: str = "NORMAL_PARTICIPATION",
    execution_friction_state: str = "LOW_FRICTION",
    event_risk_state: str = "LOW_EVENT_RISK",
    advanced_input_activation_state: str = "ADVANCED_PARTIAL",
    tick_flow_state: str = "BALANCED_FLOW",
    order_book_state: str = "UNAVAILABLE",
    source_symbol: str = "BTCUSD",
    source_price: float = 100.0,
    source_signal_timeframe: str = "15M",
    source_signal_bar_ts: int = 0,
    source_session_state_source: str = "ASIA",
    source_position_in_session_box: str = "MIDDLE",
    source_event_risk_score: float = 0.0,
    source_event_risk_match_count: int = 0,
    source_current_rsi: float = 54.0,
    source_current_adx: float = 21.0,
    source_current_plus_di: float = 24.0,
    source_current_minus_di: float = 19.0,
    source_recent_range_mean: float = 1.8,
    source_recent_body_mean: float = 0.9,
    source_sr_level_rank: float = 1.0,
    source_sr_touch_count: float = 3.0,
) -> StateVectorV2:
    return StateVectorV2(
        liquidity_penalty=liquidity_penalty,
        volatility_penalty=volatility_penalty,
        metadata={
            "state_contract": "canonical_v2",
            "mapper_version": "state_vector_v2_s9",
            "source_direction_policy": direction_policy,
            "source_symbol": source_symbol,
            "source_price": source_price,
            "source_signal_timeframe": source_signal_timeframe,
            "source_signal_bar_ts": source_signal_bar_ts,
            "source_session_state_source": source_session_state_source,
            "source_position_in_session_box": source_position_in_session_box,
            "source_event_risk_score": source_event_risk_score,
            "session_regime_state": session_regime_state,
            "session_expansion_state": session_expansion_state,
            "session_exhaustion_state": session_exhaustion_state,
            "topdown_spacing_state": topdown_spacing_state,
            "topdown_slope_state": topdown_slope_state,
            "topdown_confluence_state": topdown_confluence_state,
            "spread_stress_state": spread_stress_state,
            "volume_participation_state": volume_participation_state,
            "execution_friction_state": execution_friction_state,
            "event_risk_state": event_risk_state,
            "advanced_input_activation_state": advanced_input_activation_state,
            "tick_flow_state": tick_flow_state,
            "order_book_state": order_book_state,
            "advanced_input_detail_v1": {
                "event_risk_match_count": source_event_risk_match_count,
            },
            "source_current_rsi": source_current_rsi,
            "source_current_adx": source_current_adx,
            "source_current_plus_di": source_current_plus_di,
            "source_current_minus_di": source_current_minus_di,
            "source_recent_range_mean": source_recent_range_mean,
            "source_recent_body_mean": source_recent_body_mean,
            "source_sr_level_rank": source_sr_level_rank,
            "source_sr_touch_count": source_sr_touch_count,
        },
    )


def _evidence_vector(
    *,
    buy_reversal: float = 0.0,
    sell_reversal: float = 0.0,
    buy_continuation: float = 0.0,
    sell_continuation: float = 0.0,
    buy_total: float = 0.0,
    sell_total: float = 0.0,
) -> EvidenceVector:
    return EvidenceVector(
        buy_reversal_evidence=buy_reversal,
        sell_reversal_evidence=sell_reversal,
        buy_continuation_evidence=buy_continuation,
        sell_continuation_evidence=sell_continuation,
        buy_total_evidence=buy_total,
        sell_total_evidence=sell_total,
        metadata={"evidence_contract": "canonical_v1", "mapper_version": "evidence_vector_v1_e4"},
    )


def _belief_state(
    *,
    buy_belief: float = 0.0,
    sell_belief: float = 0.0,
    buy_persistence: float = 0.0,
    sell_persistence: float = 0.0,
    belief_spread: float = 0.0,
    global_dominant_side: str = "BALANCED",
    global_dominant_mode: str = "balanced",
) -> BeliefState:
    return BeliefState(
        buy_belief=buy_belief,
        sell_belief=sell_belief,
        buy_persistence=buy_persistence,
        sell_persistence=sell_persistence,
        belief_spread=belief_spread,
        metadata={
            "belief_contract": "canonical_v1",
            "mapper_version": "belief_state_v1_b4",
            "dominance_deadband": 0.05,
            "global_dominant_side": global_dominant_side,
            "global_dominant_mode": global_dominant_mode,
        },
    )


def test_barrier_state_exposes_exact_canonical_fields():
    payload = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE"),
        _state_vector(),
        _evidence_vector(),
        _belief_state(),
    ).to_dict()

    assert set(payload.keys()) == {
        "buy_barrier",
        "sell_barrier",
        "conflict_barrier",
        "middle_chop_barrier",
        "direction_policy_barrier",
        "liquidity_barrier",
        "metadata",
    }


def test_barrier_builder_raises_conflict_barrier_for_explicit_conflict():
    barrier = build_barrier_state(
        _position_snapshot(
            primary_label="CONFLICT_BOX_UPPER_BB20_LOWER",
            conflict_kind="CONFLICT_BOX_UPPER_BB20_LOWER",
            position_conflict_score=0.72,
            middle_neutrality=0.25,
        ),
        _state_vector(),
        _evidence_vector(buy_total=0.10, sell_total=0.11),
        _belief_state(buy_belief=0.10, sell_belief=0.11, belief_spread=-0.01),
    )

    assert barrier.conflict_barrier >= 0.72


def test_barrier_builder_raises_middle_chop_for_middle_low_spread_low_persistence():
    barrier = build_barrier_state(
        _position_snapshot(
            primary_label="ALIGNED_MIDDLE",
            middle_neutrality=0.95,
        ),
        _state_vector(),
        _evidence_vector(buy_total=0.18, sell_total=0.17),
        _belief_state(buy_belief=0.18, sell_belief=0.16, belief_spread=0.02),
    )

    assert barrier.middle_chop_barrier > 0.80


def test_barrier_builder_raises_sell_side_policy_barrier_for_buy_only_state():
    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_LOWER_STRONG", middle_neutrality=0.10),
        _state_vector(direction_policy="BUY_ONLY"),
        _evidence_vector(buy_reversal=0.80, buy_total=0.80),
        _belief_state(buy_belief=0.70, buy_persistence=0.60, belief_spread=0.65),
    )

    assert barrier.direction_policy_barrier >= 0.40
    assert barrier.sell_barrier > barrier.buy_barrier


def test_barrier_builder_raises_buy_side_policy_barrier_for_sell_only_state():
    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_UPPER_STRONG", middle_neutrality=0.10),
        _state_vector(direction_policy="SELL_ONLY"),
        _evidence_vector(sell_reversal=0.80, sell_total=0.80),
        _belief_state(sell_belief=0.70, sell_persistence=0.60, belief_spread=-0.65),
    )

    assert barrier.direction_policy_barrier >= 0.40
    assert barrier.buy_barrier > barrier.sell_barrier


def test_barrier_builder_raises_liquidity_barrier_for_bad_execution_quality():
    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_UPPER_STRONG", middle_neutrality=0.10),
        _state_vector(liquidity_penalty=0.45, volatility_penalty=0.50),
        _evidence_vector(buy_continuation=0.60, buy_total=0.60),
        _belief_state(buy_belief=0.55, buy_persistence=0.40, belief_spread=0.55),
    )

    assert barrier.liquidity_barrier >= 0.45


def test_barrier_builder_is_symmetric_for_mirrored_buy_and_sell_cases():
    buy_barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_LOWER_STRONG", secondary_context_label="LOWER_CONTEXT", middle_neutrality=0.10),
        _state_vector(),
        _evidence_vector(buy_reversal=0.82, buy_total=0.82),
        _belief_state(buy_belief=0.66, buy_persistence=0.60, belief_spread=0.66),
    )
    sell_barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_UPPER_STRONG", secondary_context_label="UPPER_CONTEXT", middle_neutrality=0.10),
        _state_vector(),
        _evidence_vector(sell_reversal=0.82, sell_total=0.82),
        _belief_state(sell_belief=0.66, sell_persistence=0.60, belief_spread=-0.66),
    )

    assert math.isclose(buy_barrier.buy_barrier, sell_barrier.sell_barrier, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(buy_barrier.conflict_barrier, sell_barrier.conflict_barrier, rel_tol=0.0, abs_tol=1e-9)


def test_barrier_builder_keeps_relevant_side_low_when_aligned_and_belief_is_strong():
    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_LOWER_STRONG", secondary_context_label="LOWER_CONTEXT", middle_neutrality=0.08),
        _state_vector(),
        _evidence_vector(buy_reversal=0.90, buy_total=0.90),
        _belief_state(buy_belief=0.80, buy_persistence=0.80, belief_spread=0.80),
    )

    assert barrier.buy_barrier < 0.10


def test_barrier_builder_raises_middle_chop_when_spread_is_low():
    low_spread = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.88),
        _state_vector(),
        _evidence_vector(buy_total=0.24, sell_total=0.23),
        _belief_state(buy_belief=0.25, sell_belief=0.24, belief_spread=0.01),
    )
    high_spread = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.88),
        _state_vector(),
        _evidence_vector(buy_total=0.24, sell_total=0.23),
        _belief_state(buy_belief=0.42, sell_belief=0.08, belief_spread=0.34),
    )

    assert low_spread.middle_chop_barrier > high_spread.middle_chop_barrier


def test_barrier_builder_keeps_action_barrier_higher_when_persistence_is_low():
    weak_persistence = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", secondary_context_label="LOWER_CONTEXT", middle_neutrality=0.72),
        _state_vector(),
        _evidence_vector(buy_total=0.60),
        _belief_state(buy_belief=0.55, buy_persistence=0.0, belief_spread=0.55),
    )
    strong_persistence = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", secondary_context_label="LOWER_CONTEXT", middle_neutrality=0.72),
        _state_vector(),
        _evidence_vector(buy_total=0.60),
        _belief_state(buy_belief=0.55, buy_persistence=0.80, belief_spread=0.55),
    )

    assert weak_persistence.buy_barrier > strong_persistence.buy_barrier


def test_barrier_builder_exposes_metadata_contract_and_component_reasons():
    barrier = build_barrier_state(
        _position_snapshot(
            primary_label="UNRESOLVED_POSITION",
            secondary_context_label="UPPER_CONTEXT",
            middle_neutrality=0.65,
            position_conflict_score=0.18,
        ),
        _state_vector(direction_policy="BOTH", liquidity_penalty=0.10, volatility_penalty=0.15),
        _evidence_vector(buy_total=0.22, sell_total=0.20),
        _belief_state(buy_belief=0.24, sell_belief=0.19, belief_spread=0.03),
    )

    assert barrier.metadata["barrier_contract"] == "canonical_v1"
    assert barrier.metadata["mapper_version"] == "barrier_state_v1_br11"
    assert barrier.metadata["semantic_owner_contract"] == "barrier_blocking_only_v1"
    assert barrier.metadata["barrier_freeze_phase"] == "BR0"
    assert barrier.metadata["barrier_pre_ml_phase"] == "BR6"
    assert (
        barrier.metadata["barrier_role_statement"]
        == "Barrier is not the layer that finds entries. Barrier decides whether the current candidate should be blocked now."
    )
    assert barrier.metadata["owner_boundaries_v1"] == {
        "position_owner_claim_allowed": False,
        "response_owner_claim_allowed": False,
        "state_owner_claim_allowed": False,
        "evidence_owner_claim_allowed": False,
        "belief_owner_claim_allowed": False,
        "direct_side_creator_allowed": False,
        "direct_action_creator_allowed": False,
        "semantic_direction_creation_allowed": False,
        "semantic_confirmation_creation_allowed": False,
        "role": "blocking_and_relief_only",
    }
    assert barrier.metadata["semantic_owner_scope"] == {
        "allowed_domains": [
            "entry_blocking",
            "execution_risk_blocking",
            "scene_relief_scaling",
        ],
        "forbidden_domains": [
            "position_location_identity",
            "response_event_identity",
            "state_regime_identity",
            "evidence_strength_identity",
            "belief_persistence_identity",
            "direct_buy_sell_side_identity",
            "direct_action_identity",
        ],
        "identity_override_allowed": False,
    }
    assert barrier.metadata["position_barrier_contract"]["direction_source_used"] is False
    assert barrier.metadata["semantic_barrier_contract"]["semantic_reinterpretation_used"] is False
    assert barrier.metadata["semantic_barrier_contract"]["state_v2_harvest_used"] is True
    assert barrier.metadata["semantic_barrier_contract"]["state_v2_harvest_math_used"] is True
    assert barrier.metadata["semantic_barrier_contract"]["advanced_input_gating_used"] is True
    assert barrier.metadata["semantic_barrier_contract"]["missing_barrier_inputs_v1_used"] is True
    assert barrier.metadata["position_structure_inputs"]["secondary_context_label"] == "UPPER_CONTEXT"
    assert barrier.metadata["semantic_barrier_inputs"]["global_dominant_mode"] == "balanced"
    assert barrier.metadata["semantic_barrier_inputs_v2"]["primary_state_labels"]["session_regime_state"] == "SESSION_EDGE_ROTATION"
    assert barrier.metadata["semantic_barrier_inputs_v2"]["primary_state_labels"]["topdown_confluence_state"] == "WEAK_CONFLUENCE"
    assert barrier.metadata["semantic_barrier_inputs_v2"]["secondary_state_labels"]["advanced_input_activation_state"] == "ADVANCED_PARTIAL"
    assert barrier.metadata["semantic_barrier_inputs_v2"]["secondary_source_inputs"]["source_current_rsi"] == 54.0
    assert barrier.metadata["semantic_barrier_inputs_v2"]["secondary_source_inputs"]["source_sr_touch_count"] == 3.0
    assert barrier.metadata["breakout_fade_barrier_score"] == 0.0
    assert barrier.metadata["execution_friction_barrier_score"] == 0.0
    assert barrier.metadata["event_risk_barrier_score"] == 0.0
    assert set(barrier.metadata["pre_ml_feature_snapshot_v1"].keys()) == {"required", "recommended"}
    assert set(barrier.metadata["dominant_component_by_side"].keys()) == {"BUY", "SELL"}
    assert "conflict_barrier" in barrier.metadata["barrier_reasons"]
    assert "middle_chop_barrier" in barrier.metadata["barrier_reasons"]
    assert "edge_turn_relief_v1" in barrier.metadata["barrier_reasons"]
    assert "breakout_fade_barrier_v1" in barrier.metadata["barrier_reasons"]
    assert "middle_chop_barrier_v2" in barrier.metadata["barrier_reasons"]
    assert "advanced_input_gating_v1" in barrier.metadata["barrier_reasons"]
    assert "session_open_shock_barrier_v1" in barrier.metadata["barrier_reasons"]
    assert "duplicate_edge_barrier_v1" in barrier.metadata["barrier_reasons"]
    assert "micro_trap_barrier_v1" in barrier.metadata["barrier_reasons"]
    assert "vp_collision_barrier_v1" in barrier.metadata["barrier_reasons"]
    assert "post_event_cooldown_barrier_v1" in barrier.metadata["barrier_reasons"]
    assert "UNRESOLVED_POSITION" in barrier.metadata["barrier_reasons"]["middle_chop_barrier"]
    assert "buy barrier dominated by" in barrier.metadata["barrier_reasons"]["buy_barrier"]
    assert "sell barrier dominated by" in barrier.metadata["barrier_reasons"]["sell_barrier"]


def test_barrier_builder_freezes_pre_ml_readiness_contract():
    barrier = build_barrier_state(
        _position_snapshot(
            primary_label="ALIGNED_UPPER_STRONG",
            secondary_context_label="UPPER_CONTEXT",
            middle_neutrality=0.12,
            position_conflict_score=0.08,
        ),
        _state_vector(
            execution_friction_state="MEDIUM_FRICTION",
            event_risk_state="WATCH_EVENT_RISK",
        ),
        _evidence_vector(sell_total=0.44, buy_total=0.12),
        _belief_state(sell_belief=0.41, sell_persistence=0.29, belief_spread=-0.24),
    )

    contract = barrier.metadata["pre_ml_readiness_contract_v1"]

    assert barrier.metadata["barrier_pre_ml_phase"] == "BR6"
    assert contract == {
        "phase": "BR6",
        "status": "READY",
        "required_feature_fields": [
            "buy_barrier",
            "sell_barrier",
            "conflict_barrier",
            "middle_chop_barrier",
            "direction_policy_barrier",
            "liquidity_barrier",
        ],
        "recommended_feature_fields": [
            "edge_turn_relief_score",
            "breakout_fade_barrier_score",
            "execution_friction_barrier_score",
            "event_risk_barrier_score",
        ],
        "semantic_explainable_without_ml": True,
        "ml_usage_role": "feature_only_not_owner",
        "owner_collision_allowed": False,
        "owner_collision_boundary": (
            "Barrier may be consumed by ML as a calibration feature, "
            "but ML must not redefine position identity, response event identity, "
            "state regime identity, evidence strength identity, belief persistence identity, "
            "or direct action ownership."
        ),
        "safe_ml_targets": [
            "entry_block_threshold_calibration",
            "scene_relief_calibration",
            "execution_friction_calibration",
            "event_risk_block_calibration",
        ],
    }


def test_barrier_builder_exposes_recommended_pre_ml_scores_in_metadata():
    barrier = build_barrier_state(
        _position_snapshot(
            primary_label="ALIGNED_MIDDLE",
            secondary_context_label="UPPER_CONTEXT",
            middle_neutrality=0.70,
            position_conflict_score=0.16,
        ),
        _state_vector(
            session_regime_state="SESSION_EDGE_ROTATION",
            topdown_confluence_state="TOPDOWN_CONFLICT",
            execution_friction_state="HIGH_FRICTION",
            event_risk_state="WATCH_EVENT_RISK",
            volume_participation_state="LOW_PARTICIPATION",
        ),
        _evidence_vector(sell_total=0.33, buy_total=0.22),
        _belief_state(sell_belief=0.28, sell_persistence=0.24, belief_spread=-0.11),
    )

    assert barrier.metadata["edge_turn_relief_score"] >= 0.0
    assert barrier.metadata["breakout_fade_barrier_score"] >= 0.0
    assert barrier.metadata["execution_friction_barrier_score"] > 0.0
    assert barrier.metadata["event_risk_barrier_score"] > 0.0
    assert barrier.metadata["pre_ml_feature_snapshot_v1"]["required"]["buy_barrier"] == barrier.buy_barrier
    assert barrier.metadata["pre_ml_feature_snapshot_v1"]["required"]["sell_barrier"] == barrier.sell_barrier
    assert (
        barrier.metadata["pre_ml_feature_snapshot_v1"]["recommended"]["execution_friction_barrier_score"]
        == barrier.metadata["execution_friction_barrier_score"]
    )


def test_barrier_builder_freeze_contract_keeps_barrier_as_blocking_only_layer():
    barrier = build_barrier_state(
        _position_snapshot(
            primary_label="ALIGNED_UPPER_STRONG",
            secondary_context_label="UPPER_CONTEXT",
            middle_neutrality=0.10,
            position_conflict_score=0.06,
        ),
        _state_vector(direction_policy="BOTH"),
        _evidence_vector(sell_total=0.54, buy_total=0.10),
        _belief_state(sell_belief=0.48, sell_persistence=0.32, belief_spread=-0.41),
    )

    owner_boundaries = barrier.metadata["owner_boundaries_v1"]
    assert owner_boundaries["direct_side_creator_allowed"] is False
    assert owner_boundaries["direct_action_creator_allowed"] is False
    assert owner_boundaries["position_owner_claim_allowed"] is False
    assert owner_boundaries["response_owner_claim_allowed"] is False
    assert barrier.metadata["position_structure_inputs"]["secondary_context_label"] == "UPPER_CONTEXT"
    assert "dominant_side" in barrier.metadata
    assert barrier.metadata["dominant_side"] in {"BUY", "SELL", "BALANCED"}


def test_barrier_builder_harvests_state_v2_idle_inputs_without_mixing_core_inputs():
    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_LOWER_STRONG", secondary_context_label="LOWER_CONTEXT", middle_neutrality=0.12),
        _state_vector(direction_policy="BOTH", liquidity_penalty=0.08, volatility_penalty=0.14),
        _evidence_vector(buy_total=0.48, sell_total=0.14),
        _belief_state(buy_belief=0.51, buy_persistence=0.44, belief_spread=0.37),
    )

    harvest = barrier.metadata["semantic_barrier_inputs_v2"]
    assert set(harvest.keys()) == {
        "primary_state_labels",
        "secondary_state_labels",
        "secondary_source_inputs",
        "runtime_source_inputs",
    }
    assert harvest["primary_state_labels"]["session_expansion_state"] == "IN_SESSION_BOX"
    assert harvest["primary_state_labels"]["execution_friction_state"] == "LOW_FRICTION"
    assert harvest["secondary_state_labels"]["tick_flow_state"] == "BALANCED_FLOW"
    assert harvest["secondary_source_inputs"]["source_current_adx"] == 21.0
    assert harvest["secondary_source_inputs"]["source_recent_body_mean"] == 0.9
    assert "direction_policy" in barrier.metadata["semantic_barrier_inputs"]
    assert "session_expansion_state" not in barrier.metadata["semantic_barrier_inputs"]


def test_barrier_builder_relieves_edge_turn_reversal_at_edge_rotation():
    edge_turn = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_LOWER_STRONG", secondary_context_label="LOWER_CONTEXT", middle_neutrality=0.18),
        _state_vector(
            session_regime_state="SESSION_EDGE_ROTATION",
            topdown_confluence_state="WEAK_CONFLUENCE",
            execution_friction_state="LOW_FRICTION",
            volume_participation_state="NORMAL_PARTICIPATION",
        ),
        _evidence_vector(buy_reversal=0.72, buy_total=0.72, sell_total=0.10),
        _belief_state(buy_belief=0.64, buy_persistence=0.56, belief_spread=0.52),
    )
    non_edge = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_LOWER_STRONG", secondary_context_label="LOWER_CONTEXT", middle_neutrality=0.18),
        _state_vector(
            session_regime_state="SESSION_BALANCED",
            topdown_confluence_state="BULL_CONFLUENCE",
            execution_friction_state="LOW_FRICTION",
            volume_participation_state="NORMAL_PARTICIPATION",
        ),
        _evidence_vector(buy_reversal=0.72, buy_total=0.72, sell_total=0.10),
        _belief_state(buy_belief=0.64, buy_persistence=0.56, belief_spread=0.52),
    )

    assert edge_turn.metadata["edge_turn_relief_v1"]["buy_relief"] > 0.0
    assert edge_turn.middle_chop_barrier < non_edge.middle_chop_barrier


def test_barrier_builder_raises_countertrend_fade_barrier_in_up_breakout_continuation():
    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_UPPER_STRONG", secondary_context_label="UPPER_CONTEXT", middle_neutrality=0.08),
        _state_vector(
            session_regime_state="SESSION_EDGE_ROTATION",
            session_expansion_state="UP_EARLY_EXPANSION",
            topdown_slope_state="UP_SLOPE_ALIGNED",
            topdown_confluence_state="BULL_CONFLUENCE",
        ),
        _evidence_vector(buy_continuation=0.66, buy_total=0.66, sell_total=0.08),
        _belief_state(buy_belief=0.58, buy_persistence=0.52, belief_spread=0.44),
    )

    assert barrier.metadata["breakout_fade_barrier_v1"]["sell_fade_barrier"] > 0.0
    assert barrier.sell_barrier > barrier.buy_barrier


def test_barrier_builder_strengthens_middle_chop_with_friction_and_thin_participation():
    thin_middle = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.52),
        _state_vector(
            execution_friction_state="HIGH_FRICTION",
            volume_participation_state="LOW_PARTICIPATION",
        ),
        _evidence_vector(buy_total=0.25, sell_total=0.24),
        _belief_state(buy_belief=0.22, sell_belief=0.20, belief_spread=0.01),
    )
    clean_middle = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.52),
        _state_vector(
            execution_friction_state="LOW_FRICTION",
            volume_participation_state="NORMAL_PARTICIPATION",
        ),
        _evidence_vector(buy_total=0.25, sell_total=0.24),
        _belief_state(buy_belief=0.22, sell_belief=0.20, belief_spread=0.01),
    )

    assert thin_middle.metadata["middle_chop_barrier_v2"]["scene_boost"] > 0.0
    assert (
        thin_middle.metadata["middle_chop_barrier_v2"]["scene_boost"]
        > clean_middle.metadata["middle_chop_barrier_v2"]["scene_boost"]
    )


def test_barrier_builder_keeps_advanced_inputs_neutral_when_unavailable():
    unavailable = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.50),
        _state_vector(
            advanced_input_activation_state="ADVANCED_UNAVAILABLE",
            tick_flow_state="BURST_DOWN_FLOW",
            order_book_state="ASK_IMBALANCE",
            event_risk_state="HIGH_EVENT_RISK",
        ),
        _evidence_vector(buy_total=0.28, sell_total=0.24),
        _belief_state(buy_belief=0.24, sell_belief=0.18, belief_spread=0.02),
    )

    gating = unavailable.metadata["advanced_input_gating_v1"]
    assert gating["activation_weight"] == 0.0
    assert gating["common_boost"] == 0.0
    assert gating["buy_side_boost"] == 0.0
    assert gating["sell_side_boost"] == 0.0
    assert gating["active"] is False


def test_barrier_builder_uses_partial_active_advanced_inputs_as_weak_barrier_support():
    partial = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.48),
        _state_vector(
            advanced_input_activation_state="ADVANCED_PARTIAL",
            tick_flow_state="QUIET_FLOW",
            order_book_state="THIN_BOOK",
            event_risk_state="WATCH_EVENT_RISK",
        ),
        _evidence_vector(buy_total=0.26, sell_total=0.24),
        _belief_state(buy_belief=0.22, sell_belief=0.20, belief_spread=0.01),
    )
    active = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.48),
        _state_vector(
            advanced_input_activation_state="ADVANCED_ACTIVE",
            tick_flow_state="QUIET_FLOW",
            order_book_state="THIN_BOOK",
            event_risk_state="WATCH_EVENT_RISK",
        ),
        _evidence_vector(buy_total=0.26, sell_total=0.24),
        _belief_state(buy_belief=0.22, sell_belief=0.20, belief_spread=0.01),
    )

    partial_gating = partial.metadata["advanced_input_gating_v1"]
    active_gating = active.metadata["advanced_input_gating_v1"]
    assert partial_gating["common_boost"] > 0.0
    assert active_gating["common_boost"] > partial_gating["common_boost"]
    assert active.metadata["component_scores"]["advanced_common_barrier"] > partial.metadata["component_scores"]["advanced_common_barrier"]
    assert active.buy_barrier > partial.buy_barrier


def test_barrier_builder_applies_directional_advanced_side_boost_only_when_active():
    active = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.35),
        _state_vector(
            advanced_input_activation_state="ADVANCED_ACTIVE",
            tick_flow_state="BURST_UP_FLOW",
            order_book_state="BID_IMBALANCE",
            event_risk_state="LOW_EVENT_RISK",
        ),
        _evidence_vector(buy_total=0.30, sell_total=0.14),
        _belief_state(buy_belief=0.28, sell_belief=0.12, belief_spread=0.06),
    )
    unavailable = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.35),
        _state_vector(
            advanced_input_activation_state="ADVANCED_UNAVAILABLE",
            tick_flow_state="BURST_UP_FLOW",
            order_book_state="BID_IMBALANCE",
            event_risk_state="LOW_EVENT_RISK",
        ),
        _evidence_vector(buy_total=0.30, sell_total=0.14),
        _belief_state(buy_belief=0.28, sell_belief=0.12, belief_spread=0.06),
    )

    assert active.metadata["advanced_input_gating_v1"]["sell_side_boost"] > 0.0
    assert unavailable.metadata["advanced_input_gating_v1"]["sell_side_boost"] == 0.0
    assert active.sell_barrier > unavailable.sell_barrier


def test_barrier_builder_does_not_use_position_dominance_as_direction_source():
    common_kwargs = {
        "state_vector_v2": _state_vector(),
        "evidence_vector_v1": _evidence_vector(buy_total=0.30, sell_total=0.18),
        "belief_state_v1": _belief_state(buy_belief=0.32, sell_belief=0.19, belief_spread=0.04),
    }
    with_buy_dominance = build_barrier_state(
        _position_snapshot(
            primary_label="ALIGNED_MIDDLE",
            secondary_context_label="UPPER_CONTEXT",
            dominance_label="UPPER_DOMINANT_CONFLICT",
            middle_neutrality=0.78,
            position_conflict_score=0.12,
        ),
        **common_kwargs,
    )
    with_sell_dominance = build_barrier_state(
        _position_snapshot(
            primary_label="ALIGNED_MIDDLE",
            secondary_context_label="UPPER_CONTEXT",
            dominance_label="LOWER_DOMINANT_CONFLICT",
            middle_neutrality=0.78,
            position_conflict_score=0.12,
        ),
        **common_kwargs,
    )

    assert with_buy_dominance.to_dict() == with_sell_dominance.to_dict()


def test_barrier_builder_uses_position_only_for_structure_quality_not_side_direction():
    common_state = _state_vector(
        session_regime_state="SESSION_BALANCED",
        topdown_confluence_state="BULL_CONFLUENCE",
        source_sr_touch_count=1.0,
        source_current_adx=28.0,
        source_current_plus_di=20.0,
        source_current_minus_di=20.0,
        source_recent_range_mean=1.5,
        source_recent_body_mean=1.0,
    )
    common_evidence = _evidence_vector(buy_total=0.34, sell_total=0.12)
    common_belief = _belief_state(buy_belief=0.30, sell_belief=0.12, belief_spread=0.03)

    lower = build_barrier_state(
        _position_snapshot(
            primary_label="ALIGNED_LOWER_STRONG",
            secondary_context_label="LOWER_CONTEXT",
            middle_neutrality=0.12,
            position_conflict_score=0.08,
        ),
        common_state,
        common_evidence,
        common_belief,
    )
    upper = build_barrier_state(
        _position_snapshot(
            primary_label="ALIGNED_UPPER_STRONG",
            secondary_context_label="UPPER_CONTEXT",
            middle_neutrality=0.12,
            position_conflict_score=0.08,
        ),
        common_state,
        common_evidence,
        common_belief,
    )

    assert math.isclose(lower.buy_barrier, upper.buy_barrier, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(lower.sell_barrier, upper.sell_barrier, rel_tol=0.0, abs_tol=1e-9)


def test_barrier_builder_applies_session_open_shock_barrier_near_session_open():
    signal_ts = int(datetime(2026, 3, 16, 8, 5, tzinfo=ZoneInfo("Asia/Seoul")).timestamp())
    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_LOWER_STRONG", secondary_context_label="LOWER_CONTEXT", middle_neutrality=0.18),
        _state_vector(
            session_expansion_state="UP_EARLY_EXPANSION",
            execution_friction_state="MEDIUM_FRICTION",
            spread_stress_state="ELEVATED_SPREAD_STRESS",
            source_signal_bar_ts=signal_ts,
            source_session_state_source="ASIA",
        ),
        _evidence_vector(buy_total=0.44, sell_total=0.10),
        _belief_state(buy_belief=0.34, buy_persistence=0.22, belief_spread=0.24),
    )

    session_open = barrier.metadata["session_open_shock_barrier_v1"]
    assert session_open["active"] is True
    assert session_open["common_boost"] > 0.0
    assert barrier.metadata["component_scores"]["session_open_shock_barrier"] > 0.0


def test_barrier_builder_applies_duplicate_edge_barrier_for_repeated_lower_edge_stabs():
    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_LOWER_STRONG", secondary_context_label="LOWER_CONTEXT", middle_neutrality=0.16),
        _state_vector(
            source_sr_level_rank=1.0,
            source_sr_touch_count=5.0,
        ),
        _evidence_vector(buy_total=0.22, sell_total=0.14),
        _belief_state(buy_belief=0.16, buy_persistence=0.08, belief_spread=0.02),
    )

    duplicate_edge = barrier.metadata["duplicate_edge_barrier_v1"]
    assert duplicate_edge["buy_side_boost"] > 0.0
    assert barrier.buy_barrier > barrier.sell_barrier


def test_barrier_builder_applies_micro_trap_sell_side_boost_against_strong_up_micro():
    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_UPPER_STRONG", secondary_context_label="UPPER_CONTEXT", middle_neutrality=0.12),
        _state_vector(
            volume_participation_state="LOW_PARTICIPATION",
            tick_flow_state="BALANCED_FLOW",
            source_current_adx=11.0,
            source_current_plus_di=24.0,
            source_current_minus_di=14.0,
            source_recent_range_mean=2.0,
            source_recent_body_mean=0.20,
        ),
        _evidence_vector(buy_total=0.30, sell_total=0.18),
        _belief_state(buy_belief=0.24, sell_belief=0.18, belief_spread=0.01),
    )

    micro_trap = barrier.metadata["micro_trap_barrier_v1"]
    assert micro_trap["common_boost"] > 0.0
    assert micro_trap["sell_side_boost"] > 0.0
    assert barrier.sell_barrier > barrier.buy_barrier


def test_barrier_builder_reads_vp_collision_barrier_when_vp_file_is_available(tmp_path, monkeypatch):
    vp_path = tmp_path / "BTCUSD_vp_data.csv"
    vp_path.write_text("poc,vah,val\n100.2,102.0,98.0\n", encoding="utf-8")
    monkeypatch.setattr("backend.trading.engine.core.barrier_engine.Config.VP_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("backend.trading.engine.core.barrier_engine.Config.VP_FILENAME_SUFFIX", "_vp_data.csv")

    barrier = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.44),
        _state_vector(
            source_symbol="BTCUSD",
            source_price=100.15,
        ),
        _evidence_vector(buy_total=0.26, sell_total=0.22),
        _belief_state(buy_belief=0.22, sell_belief=0.20, belief_spread=0.01),
    )

    vp_collision = barrier.metadata["vp_collision_barrier_v1"]
    assert vp_collision["available"] is True
    assert vp_collision["inside_value_area"] is True
    assert vp_collision["common_boost"] > 0.0


def test_barrier_builder_applies_post_event_cooldown_only_when_aftershock_features_exist():
    cooldown = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.40),
        _state_vector(
            event_risk_state="WATCH_EVENT_RISK",
            advanced_input_activation_state="ADVANCED_ACTIVE",
            execution_friction_state="HIGH_FRICTION",
            volume_participation_state="LOW_PARTICIPATION",
            tick_flow_state="QUIET_FLOW",
            source_event_risk_score=0.46,
            source_event_risk_match_count=2,
        ),
        _evidence_vector(buy_total=0.24, sell_total=0.20),
        _belief_state(buy_belief=0.20, sell_belief=0.18, belief_spread=0.01),
    )
    neutral = build_barrier_state(
        _position_snapshot(primary_label="ALIGNED_MIDDLE", middle_neutrality=0.40),
        _state_vector(
            event_risk_state="LOW_EVENT_RISK",
            advanced_input_activation_state="ADVANCED_ACTIVE",
            execution_friction_state="LOW_FRICTION",
            volume_participation_state="NORMAL_PARTICIPATION",
            tick_flow_state="BALANCED_FLOW",
            source_event_risk_score=0.10,
            source_event_risk_match_count=0,
        ),
        _evidence_vector(buy_total=0.24, sell_total=0.20),
        _belief_state(buy_belief=0.20, sell_belief=0.18, belief_spread=0.01),
    )

    assert cooldown.metadata["post_event_cooldown_barrier_v1"]["common_boost"] > 0.0
    assert neutral.metadata["post_event_cooldown_barrier_v1"]["common_boost"] == 0.0
