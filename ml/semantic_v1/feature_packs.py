from __future__ import annotations

from dataclasses import dataclass


SEMANTIC_FEATURE_CONTRACT_VERSION = "semantic_feature_contract_v1"


@dataclass(frozen=True)
class FeaturePack:
    key: str
    label: str
    description: str
    columns: tuple[str, ...]


POSITION_PACK = FeaturePack(
    key="position_pack",
    label="position pack",
    description="가격의 상대 위치와 위치 해석, 위치 에너지 요약 스칼라",
    columns=(
        "position_x_box",
        "position_x_bb20",
        "position_x_bb44",
        "position_x_ma20",
        "position_x_ma60",
        "position_x_sr",
        "position_x_trendline",
        "position_pos_composite",
        "position_alignment_label",
        "position_bias_label",
        "position_conflict_kind",
        "position_lower_force",
        "position_upper_force",
        "position_middle_neutrality",
        "position_conflict_score",
    ),
)

RESPONSE_PACK = FeaturePack(
    key="response_pack",
    label="response pack",
    description="하단, 중단, 상단에서 가격 반응을 요약한 스칼라",
    columns=(
        "response_lower_break_down",
        "response_lower_hold_up",
        "response_mid_lose_down",
        "response_mid_reclaim_up",
        "response_upper_break_up",
        "response_upper_reject_down",
    ),
)

STATE_PACK = FeaturePack(
    key="state_pack",
    label="state pack",
    description="정렬, 브레이크아웃, 반전, 노이즈, 페널티 상태 스칼라",
    columns=(
        "state_alignment_gain",
        "state_breakout_continuation_gain",
        "state_trend_pullback_gain",
        "state_range_reversal_gain",
        "state_conflict_damp",
        "state_noise_damp",
        "state_liquidity_penalty",
        "state_volatility_penalty",
        "state_countertrend_penalty",
    ),
)

EVIDENCE_PACK = FeaturePack(
    key="evidence_pack",
    label="evidence pack",
    description="매수 and 매도 증거 강도를 요약한 스칼라",
    columns=(
        "evidence_buy_total",
        "evidence_buy_continuation",
        "evidence_buy_reversal",
        "evidence_sell_total",
        "evidence_sell_continuation",
        "evidence_sell_reversal",
    ),
)

FORECAST_SUMMARY_PACK = FeaturePack(
    key="forecast_summary_pack",
    label="forecast summary pack",
    description="forecast에서 직접 학습 가능한 요약 컨텍스트 스칼라",
    columns=(
        "forecast_position_primary_label",
        "forecast_position_secondary_context_label",
        "forecast_position_conflict_score",
        "forecast_middle_neutrality",
        "forecast_management_horizon_bars",
        "forecast_signal_timeframe",
    ),
)

TRACE_QUALITY_PACK = FeaturePack(
    key="trace_quality_pack",
    label="trace and quality pack",
    description="row provenance, freshness, latency, completeness, payload health 요약",
    columns=(
        "decision_row_key",
        "runtime_snapshot_key",
        "trade_link_key",
        "replay_row_key",
        "observe_reason",
        "blocked_by",
        "action_none_reason",
        "probe_candidate_active",
        "probe_direction",
        "probe_scene_id",
        "probe_candidate_support",
        "probe_pair_gap",
        "probe_plan_active",
        "probe_plan_ready",
        "probe_plan_reason",
        "probe_plan_scene",
        "probe_promotion_bias",
        "probe_temperament_source",
        "probe_entry_style",
        "probe_temperament_note",
        "edge_execution_scene_id",
        "quick_trace_state",
        "quick_trace_reason",
        "semantic_shadow_available",
        "semantic_shadow_reason",
        "semantic_shadow_activation_state",
        "semantic_shadow_activation_reason",
        "semantic_live_threshold_applied",
        "semantic_live_threshold_state",
        "semantic_live_threshold_reason",
        "signal_age_sec",
        "bar_age_sec",
        "decision_latency_ms",
        "order_submit_latency_ms",
        "missing_feature_count",
        "data_completeness_ratio",
        "used_fallback_count",
        "compatibility_mode",
        "detail_blob_bytes",
        "snapshot_payload_bytes",
        "row_payload_bytes",
    ),
)

SEMANTIC_INPUT_PACKS: tuple[FeaturePack, ...] = (
    POSITION_PACK,
    RESPONSE_PACK,
    STATE_PACK,
    EVIDENCE_PACK,
    FORECAST_SUMMARY_PACK,
)

SUPPORT_PACKS: tuple[FeaturePack, ...] = (
    TRACE_QUALITY_PACK,
)

ALL_FEATURE_PACKS: tuple[FeaturePack, ...] = (*SEMANTIC_INPUT_PACKS, *SUPPORT_PACKS)

SEMANTIC_INPUT_COLUMNS: tuple[str, ...] = tuple(
    column
    for pack in SEMANTIC_INPUT_PACKS
    for column in pack.columns
)

TRACE_QUALITY_COLUMNS: tuple[str, ...] = TRACE_QUALITY_PACK.columns

ALL_CONTRACT_COLUMNS: tuple[str, ...] = tuple(
    column
    for pack in ALL_FEATURE_PACKS
    for column in pack.columns
)


def get_feature_pack_map() -> dict[str, FeaturePack]:
    return {pack.key: pack for pack in ALL_FEATURE_PACKS}


def feature_pack_rows() -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "pack_key": pack.key,
            "pack_label": pack.label,
            "description": pack.description,
            "columns": list(pack.columns),
            "column_count": len(pack.columns),
        }
        for pack in ALL_FEATURE_PACKS
    )
