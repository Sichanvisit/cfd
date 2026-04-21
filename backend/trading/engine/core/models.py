from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

POSITION_PRIMARY_AXES = ("x_box", "x_bb20", "x_bb44")
POSITION_SECONDARY_AXES = ("x_ma20", "x_ma60", "x_sr", "x_trendline")
POSITION_FALLBACK_LABELS = ("raw_box_state", "raw_bb_state")
POSITION_ZONE_LABELS = ("BELOW", "LOWER_EDGE", "LOWER", "MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE")
POSITION_SECONDARY_CONTEXT_LABELS = ("LOWER_CONTEXT", "UPPER_CONTEXT", "MIXED_CONTEXT", "NEUTRAL_CONTEXT")
POSITION_ALIGNMENT_LABELS = (
    "ALIGNED_LOWER_STRONG",
    "ALIGNED_LOWER_WEAK",
    "ALIGNED_UPPER_STRONG",
    "ALIGNED_UPPER_WEAK",
    "ALIGNED_MIDDLE",
)
POSITION_BIAS_LABELS = (
    "LOWER_BIAS",
    "UPPER_BIAS",
    "MIDDLE_LOWER_BIAS",
    "MIDDLE_UPPER_BIAS",
)
POSITION_CONFLICT_LABELS = (
    "CONFLICT_BOX_UPPER_BB20_LOWER",
    "CONFLICT_BOX_LOWER_BB20_UPPER",
    "CONFLICT_BB20_UPPER_BB44_LOWER",
    "CONFLICT_BB20_LOWER_BB44_UPPER",
    "CONFLICT_MIDDLE_MIXED",
)
POSITION_DOMINANCE_LABELS = ("UPPER_DOMINANT_CONFLICT", "LOWER_DOMINANT_CONFLICT", "BALANCED_CONFLICT")
POSITION_PRIMARY_LABELS = POSITION_ALIGNMENT_LABELS + POSITION_BIAS_LABELS + POSITION_CONFLICT_LABELS + ("UNRESOLVED_POSITION",)


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return str(value)


@dataclass
class EngineContext:
    symbol: str
    price: float
    market_mode: str = "UNKNOWN"
    direction_policy: str = "UNKNOWN"
    box_state: str = "UNKNOWN"
    bb_state: str = "UNKNOWN"
    box_low: float | None = None
    box_high: float | None = None
    bb20_up: float | None = None
    bb20_mid: float | None = None
    bb20_dn: float | None = None
    bb44_up: float | None = None
    bb44_mid: float | None = None
    bb44_dn: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    ma120: float | None = None
    ma240: float | None = None
    ma480: float | None = None
    support: float | None = None
    resistance: float | None = None
    trendline_value: float | None = None
    volatility_scale: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class PositionVector:
    x_box: float = 0.0
    x_bb20: float = 0.0
    x_bb44: float = 0.0
    x_ma20: float = 0.0
    x_ma60: float = 0.0
    x_sr: float = 0.0
    x_trendline: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class PositionZones:
    box_zone: str = "MIDDLE"
    bb20_zone: str = "MIDDLE"
    bb44_zone: str = "MIDDLE"
    ma20_zone: str = "MIDDLE"
    ma60_zone: str = "MIDDLE"
    sr_zone: str = "MIDDLE"
    trendline_zone: str = "MIDDLE"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class PositionInterpretation:
    primary_label: str = "UNRESOLVED_POSITION"
    alignment_label: str = ""
    bias_label: str = ""
    conflict_kind: str = ""
    dominance_label: str = ""
    secondary_context_label: str = "NEUTRAL_CONTEXT"
    pos_composite: float = 0.0
    used_raw_fallback: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class PositionEnergySnapshot:
    upper_position_force: float = 0.0
    lower_position_force: float = 0.0
    middle_neutrality: float = 0.0
    position_conflict_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class PositionSnapshot:
    vector: PositionVector = field(default_factory=PositionVector)
    zones: PositionZones = field(default_factory=PositionZones)
    interpretation: PositionInterpretation = field(default_factory=PositionInterpretation)
    energy: PositionEnergySnapshot = field(default_factory=PositionEnergySnapshot)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class ResponseRawSnapshot:
    bb20_lower_hold: float = 0.0
    bb20_lower_break: float = 0.0
    bb20_mid_hold: float = 0.0
    bb20_mid_reclaim: float = 0.0
    bb20_mid_reject: float = 0.0
    bb20_mid_lose: float = 0.0
    bb20_upper_reject: float = 0.0
    bb20_upper_break: float = 0.0
    bb44_lower_hold: float = 0.0
    bb44_upper_reject: float = 0.0
    box_lower_bounce: float = 0.0
    box_lower_break: float = 0.0
    box_mid_hold: float = 0.0
    box_mid_reject: float = 0.0
    box_upper_reject: float = 0.0
    box_upper_break: float = 0.0
    candle_lower_reject: float = 0.0
    candle_upper_reject: float = 0.0
    pattern_double_bottom: float = 0.0
    pattern_inverse_head_shoulders: float = 0.0
    pattern_double_top: float = 0.0
    pattern_head_shoulders: float = 0.0
    sr_support_touch: float = 0.0
    sr_support_hold: float = 0.0
    sr_support_reclaim: float = 0.0
    sr_support_break: float = 0.0
    sr_resistance_touch: float = 0.0
    sr_resistance_reject: float = 0.0
    sr_resistance_reclaim: float = 0.0
    sr_resistance_break: float = 0.0
    trend_support_touch_m1: float = 0.0
    trend_support_hold_m1: float = 0.0
    trend_support_break_m1: float = 0.0
    trend_resistance_touch_m1: float = 0.0
    trend_resistance_reject_m1: float = 0.0
    trend_resistance_break_m1: float = 0.0
    trend_support_touch_m15: float = 0.0
    trend_support_hold_m15: float = 0.0
    trend_support_break_m15: float = 0.0
    trend_resistance_touch_m15: float = 0.0
    trend_resistance_reject_m15: float = 0.0
    trend_resistance_break_m15: float = 0.0
    trend_support_touch_h1: float = 0.0
    trend_support_hold_h1: float = 0.0
    trend_support_break_h1: float = 0.0
    trend_resistance_touch_h1: float = 0.0
    trend_resistance_reject_h1: float = 0.0
    trend_resistance_break_h1: float = 0.0
    trend_support_touch_h4: float = 0.0
    trend_support_hold_h4: float = 0.0
    trend_support_break_h4: float = 0.0
    trend_resistance_touch_h4: float = 0.0
    trend_resistance_reject_h4: float = 0.0
    trend_resistance_break_h4: float = 0.0
    micro_bull_reject: float = 0.0
    micro_bear_reject: float = 0.0
    micro_bull_break: float = 0.0
    micro_bear_break: float = 0.0
    micro_indecision: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class ResponseVector:
    r_bb20_lower_hold: float = 0.0
    r_bb20_lower_break: float = 0.0
    r_bb20_mid_hold: float = 0.0
    r_bb20_mid_reclaim: float = 0.0
    r_bb20_mid_reject: float = 0.0
    r_bb20_mid_lose: float = 0.0
    r_bb20_upper_reject: float = 0.0
    r_bb20_upper_break: float = 0.0
    r_bb44_lower_hold: float = 0.0
    r_bb44_upper_reject: float = 0.0
    r_box_lower_bounce: float = 0.0
    r_box_lower_break: float = 0.0
    r_box_mid_hold: float = 0.0
    r_box_mid_reject: float = 0.0
    r_box_upper_reject: float = 0.0
    r_box_upper_break: float = 0.0
    r_candle_lower_reject: float = 0.0
    r_candle_upper_reject: float = 0.0
    r_sr_support_touch: float = 0.0
    r_sr_support_hold: float = 0.0
    r_sr_support_reclaim: float = 0.0
    r_sr_support_break: float = 0.0
    r_sr_resistance_touch: float = 0.0
    r_sr_resistance_reject: float = 0.0
    r_sr_resistance_reclaim: float = 0.0
    r_sr_resistance_break: float = 0.0
    r_trend_support_touch_m1: float = 0.0
    r_trend_support_hold_m1: float = 0.0
    r_trend_support_break_m1: float = 0.0
    r_trend_resistance_touch_m1: float = 0.0
    r_trend_resistance_reject_m1: float = 0.0
    r_trend_resistance_break_m1: float = 0.0
    r_trend_support_touch_m15: float = 0.0
    r_trend_support_hold_m15: float = 0.0
    r_trend_support_break_m15: float = 0.0
    r_trend_resistance_touch_m15: float = 0.0
    r_trend_resistance_reject_m15: float = 0.0
    r_trend_resistance_break_m15: float = 0.0
    r_trend_support_touch_h1: float = 0.0
    r_trend_support_hold_h1: float = 0.0
    r_trend_support_break_h1: float = 0.0
    r_trend_resistance_touch_h1: float = 0.0
    r_trend_resistance_reject_h1: float = 0.0
    r_trend_resistance_break_h1: float = 0.0
    r_trend_support_touch_h4: float = 0.0
    r_trend_support_hold_h4: float = 0.0
    r_trend_support_break_h4: float = 0.0
    r_trend_resistance_touch_h4: float = 0.0
    r_trend_resistance_reject_h4: float = 0.0
    r_trend_resistance_break_h4: float = 0.0
    r_micro_bull_reject: float = 0.0
    r_micro_bear_reject: float = 0.0
    r_micro_bull_break: float = 0.0
    r_micro_bear_break: float = 0.0
    r_micro_indecision: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class ResponseVectorV2:
    lower_hold_up: float = 0.0
    lower_break_down: float = 0.0
    mid_reclaim_up: float = 0.0
    mid_lose_down: float = 0.0
    upper_reject_down: float = 0.0
    upper_break_up: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class StateRawSnapshot:
    market_mode: str = "UNKNOWN"
    direction_policy: str = "UNKNOWN"
    liquidity_state: str = "UNKNOWN"
    s_noise: float = 0.0
    s_conflict: float = 0.0
    s_alignment: float = 0.0
    s_disparity: float = 0.0
    s_volatility: float = 0.0
    s_topdown_bias: float = 0.0
    s_topdown_agreement: float = 0.0
    s_compression: float = 0.0
    s_expansion: float = 0.0
    s_middle_neutrality: float = 0.0
    s_current_rsi: float = 50.0
    s_current_adx: float = 0.0
    s_current_plus_di: float = 0.0
    s_current_minus_di: float = 0.0
    s_recent_range_mean: float = 0.0
    s_recent_body_mean: float = 0.0
    s_body_size_pct_20: float = 0.0
    s_upper_wick_ratio_20: float = 0.0
    s_lower_wick_ratio_20: float = 0.0
    s_doji_ratio_20: float = 0.0
    s_same_color_run_current: float = 0.0
    s_same_color_run_max_20: float = 0.0
    s_bull_ratio_20: float = 0.0
    s_bear_ratio_20: float = 0.0
    s_range_compression_ratio_20: float = 0.0
    s_volume_burst_ratio_20: float = 0.0
    s_volume_burst_decay_20: float = 0.0
    s_swing_high_retest_count_20: float = 0.0
    s_swing_low_retest_count_20: float = 0.0
    s_gap_fill_progress: float | None = None
    s_sr_level_rank: float = 0.0
    s_sr_touch_count: float = 0.0
    s_session_box_height_ratio: float = 0.0
    s_session_expansion_progress: float = 0.0
    s_session_position_bias: float = 0.0
    s_topdown_spacing_score: float = 0.0
    s_topdown_slope_bias: float = 0.0
    s_topdown_slope_agreement: float = 0.0
    s_topdown_confluence_bias: float = 0.0
    s_topdown_conflict_score: float = 0.0
    s_tick_spread_ratio: float = 0.0
    s_rate_spread_ratio: float = 0.0
    s_tick_volume_ratio: float = 0.0
    s_real_volume_ratio: float = 0.0
    s_tick_flow_bias: float = 0.0
    s_tick_flow_burst: float = 0.0
    s_order_book_imbalance: float = 0.0
    s_order_book_thinness: float = 0.0
    s_event_risk_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class StateVectorV2:
    range_reversal_gain: float = 1.0
    trend_pullback_gain: float = 1.0
    breakout_continuation_gain: float = 1.0
    noise_damp: float = 1.0
    conflict_damp: float = 1.0
    alignment_gain: float = 1.0
    topdown_bull_bias: float = 0.0
    topdown_bear_bias: float = 0.0
    big_map_alignment_gain: float = 1.0
    wait_patience_gain: float = 1.0
    confirm_aggression_gain: float = 1.0
    hold_patience_gain: float = 1.0
    fast_exit_risk_penalty: float = 0.0
    countertrend_penalty: float = 0.0
    liquidity_penalty: float = 0.0
    volatility_penalty: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class StateVector:
    market_mode: str = "UNKNOWN"
    direction_policy: str = "UNKNOWN"
    s_noise: float = 0.0
    s_conflict: float = 0.0
    s_alignment: float = 0.0
    s_disparity: float = 0.0
    s_volatility: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class EvidenceVector:
    buy_reversal_evidence: float = 0.0
    sell_reversal_evidence: float = 0.0
    buy_continuation_evidence: float = 0.0
    sell_continuation_evidence: float = 0.0
    buy_total_evidence: float = 0.0
    sell_total_evidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class BeliefState:
    buy_belief: float = 0.0
    sell_belief: float = 0.0
    buy_persistence: float = 0.0
    sell_persistence: float = 0.0
    belief_spread: float = 0.0
    flip_readiness: float = 0.0
    belief_instability: float = 0.0
    dominant_side: str = "BALANCED"
    dominant_mode: str = "balanced"
    buy_streak: int = 0
    sell_streak: int = 0
    transition_age: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class BarrierState:
    buy_barrier: float = 0.0
    sell_barrier: float = 0.0
    conflict_barrier: float = 0.0
    middle_chop_barrier: float = 0.0
    direction_policy_barrier: float = 0.0
    liquidity_barrier: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class ForecastFeaturesV1:
    position_primary_label: str = "UNRESOLVED_POSITION"
    position_bias_label: str = ""
    position_secondary_context_label: str = "NEUTRAL_CONTEXT"
    position_conflict_score: float = 0.0
    middle_neutrality: float = 0.0
    response_vector_v2: ResponseVectorV2 = field(default_factory=ResponseVectorV2)
    state_vector_v2: StateVectorV2 = field(default_factory=StateVectorV2)
    evidence_vector_v1: EvidenceVector = field(default_factory=EvidenceVector)
    belief_state_v1: BeliefState = field(default_factory=BeliefState)
    barrier_state_v1: BarrierState = field(default_factory=BarrierState)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class TransitionForecast:
    p_buy_confirm: float = 0.0
    p_sell_confirm: float = 0.0
    p_false_break: float = 0.0
    p_reversal_success: float = 0.0
    p_continuation_success: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class TradeManagementForecast:
    p_continue_favor: float = 0.0
    p_fail_now: float = 0.0
    p_recover_after_pullback: float = 0.0
    p_reach_tp1: float = 0.0
    p_opposite_edge_reach: float = 0.0
    p_better_reentry_if_cut: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class TransitionOutcomeLabelsV1:
    buy_confirm_success_label: bool | None = None
    sell_confirm_success_label: bool | None = None
    false_break_label: bool | None = None
    reversal_success_label: bool | None = None
    continuation_success_label: bool | None = None
    label_status: str = "INVALID"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class TradeManagementOutcomeLabelsV1:
    continue_favor_label: bool | None = None
    fail_now_label: bool | None = None
    recover_after_pullback_label: bool | None = None
    reach_tp1_label: bool | None = None
    opposite_edge_reach_label: bool | None = None
    better_reentry_if_cut_label: bool | None = None
    label_status: str = "INVALID"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class OutcomeLabelsV1:
    transition: TransitionOutcomeLabelsV1 = field(default_factory=TransitionOutcomeLabelsV1)
    trade_management: TradeManagementOutcomeLabelsV1 = field(default_factory=TradeManagementOutcomeLabelsV1)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class EnergySnapshot:
    buy_position_force: float = 0.0
    sell_position_force: float = 0.0
    buy_response_force: float = 0.0
    sell_response_force: float = 0.0
    state_damping: float = 1.0
    regime_multiplier: float = 1.0
    buy_force: float = 0.0
    sell_force: float = 0.0
    net_force: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass
class ObserveConfirmSnapshot:
    state: str = "NO_TRADE"
    action: str = "NONE"
    side: str = ""
    confidence: float = 0.0
    reason: str = ""
    archetype_id: str = ""
    invalidation_id: str = ""
    management_profile_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.state = str(self.state or "NO_TRADE").upper()
        self.action = str(self.action or "NONE").upper()
        self.side = str(self.side or "").upper()
        if self.action == "NONE":
            self.side = ""
        metadata = dict(self.metadata or {})
        metadata.setdefault("raw_contributions", {})
        metadata.setdefault("effective_contributions", {})
        metadata.setdefault("winning_evidence", [])
        metadata.setdefault("blocked_reason", "")
        self.metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))
