"""Shared live feature schema for current entry/exit tabular ML."""

from __future__ import annotations

ENTRY_PROMOTED_TEXT_COLS = [
    "entry_stage",
    "entry_setup_id",
    "management_profile_id",
    "invalidation_id",
    "regime_at_entry",
    "entry_h1_gate_reason",
    "entry_topdown_gate_reason",
    "entry_session_name",
]

ENTRY_PROMOTED_NUMERIC_COLS = [
    "entry_h1_context_score",
    "entry_m1_trigger_score",
    "entry_h1_gate_pass",
    "entry_topdown_gate_pass",
    "entry_topdown_align_count",
    "entry_topdown_conflict_count",
    "entry_topdown_seen_count",
    "entry_weekday",
    "entry_session_threshold_mult",
    "entry_atr_ratio",
    "entry_atr_threshold_mult",
]

ENTRY_FEATURE_COLS = [
    "symbol",
    "direction",
    "open_hour",
    "open_weekday",
    "entry_score",
    "contra_score_at_entry",
    "score_gap",
    "abs_score_gap",
    "entry_reason",
    "regime_name",
    "regime_volume_ratio",
    "regime_volatility_ratio",
    "regime_spread_ratio",
    "regime_buy_multiplier",
    "regime_sell_multiplier",
    "ind_rsi",
    "ind_adx",
    "ind_disparity",
    "ind_bb_20_up",
    "ind_bb_20_dn",
    "ind_bb_4_up",
    "ind_bb_4_dn",
    *ENTRY_PROMOTED_TEXT_COLS,
    *ENTRY_PROMOTED_NUMERIC_COLS,
]

ENTRY_CATEGORICAL_COLS = [
    "symbol",
    "direction",
    "entry_reason",
    "regime_name",
    *ENTRY_PROMOTED_TEXT_COLS,
]

EXIT_PROMOTED_TEXT_COLS = [
    "entry_stage",
    "entry_setup_id",
    "regime_at_entry",
    "decision_winner",
    "exit_policy_stage",
]

EXIT_PROMOTED_NUMERIC_COLS = [
    "entry_quality",
    "entry_model_confidence",
    "entry_h1_context_score",
    "entry_topdown_align_count",
    "entry_atr_ratio",
    "utility_exit_now",
    "utility_hold",
    "exit_confidence",
    "exit_delay_ticks",
    "peak_profit_at_exit",
    "giveback_usd",
    "shock_score",
]

EXIT_FEATURE_COLS = [
    "symbol",
    "direction",
    "close_hour",
    "open_hour",
    "open_weekday",
    "duration_sec",
    "entry_score",
    "contra_score_at_entry",
    "exit_score",
    "entry_reason",
    "exit_reason",
    "regime_name",
    "regime_volume_ratio",
    "regime_volatility_ratio",
    "regime_spread_ratio",
    "regime_buy_multiplier",
    "regime_sell_multiplier",
    "roundtrip_cost",
    "spread_cost_mult",
    "mfe_proxy",
    "mae_proxy",
    "ev_exit",
    "ev_hold",
    "ev_delta",
    *EXIT_PROMOTED_TEXT_COLS,
    *EXIT_PROMOTED_NUMERIC_COLS,
]

EXIT_CATEGORICAL_COLS = [
    "symbol",
    "direction",
    "entry_reason",
    "exit_reason",
    "regime_name",
    *EXIT_PROMOTED_TEXT_COLS,
]
