import pandas as pd

from backend.services.path_checkpoint_action_resolver import (
    build_checkpoint_management_action_snapshot,
    resolve_management_action,
    resolve_management_action_frame,
)

_BTC_ACTIVE_FLAT_PROFIT_ROW = {
    "symbol": "BTCUSD",
    "source": "open_trade_backfill",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "LATE_TREND_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "FLAT",
    "current_profit": 0.0,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.0,
    "runtime_continuation_odds": 0.4728,
    "runtime_reversal_odds": 0.6960,
    "runtime_hold_quality_score": 0.24516,
    "runtime_partial_exit_ev": 0.4120,
    "runtime_full_exit_risk": 0.377696,
    "runtime_rebuy_readiness": 0.21,
}

_NAS_ACTIVE_FLAT_PROFIT_ROW = {
    "symbol": "NAS100",
    "source": "open_trade_backfill",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "LATE_TREND_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "FLAT",
    "current_profit": 0.0,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.0,
    "runtime_continuation_odds": 0.5088,
    "runtime_reversal_odds": 0.5760,
    "runtime_hold_quality_score": 0.29856,
    "runtime_partial_exit_ev": 0.4024,
    "runtime_full_exit_risk": 0.305216,
    "runtime_rebuy_readiness": 0.22,
}

_XAU_BACKFILL_ACTIVE_POSITION_WAIT_ROW = {
    "symbol": "XAUUSD",
    "source": "open_trade_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "FLAT",
    "current_profit": 0.0,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.0,
    "checkpoint_rule_family_hint": "active_position",
    "runtime_continuation_odds": 0.718,
    "runtime_reversal_odds": 0.4715,
    "runtime_hold_quality_score": 0.44288,
    "runtime_partial_exit_ev": 0.34261,
    "runtime_full_exit_risk": 0.210085,
    "runtime_rebuy_readiness": 0.19,
}

_XAU_BACKFILL_ACTIVE_POSITION_HOLD_ROW = {
    "symbol": "XAUUSD",
    "source": "open_trade_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "FLAT",
    "current_profit": 0.0,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.0,
    "checkpoint_rule_family_hint": "active_position",
    "runtime_continuation_odds": 0.82,
    "runtime_reversal_odds": 0.47,
    "runtime_hold_quality_score": 0.52,
    "runtime_partial_exit_ev": 0.31,
    "runtime_full_exit_risk": 0.19,
    "runtime_rebuy_readiness": 0.19,
}

_NAS_LATE_ACTIVE_POSITION_WAIT_ROW = {
    "symbol": "NAS100",
    "source": "open_trade_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "LATE_TREND_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "FLAT",
    "current_profit": 0.0,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.0,
    "giveback_ratio": 0.0,
    "checkpoint_rule_family_hint": "active_position",
    "runtime_continuation_odds": 0.59,
    "runtime_reversal_odds": 0.3825,
    "runtime_hold_quality_score": 0.3974,
    "runtime_partial_exit_ev": 0.27155,
    "runtime_full_exit_risk": 0.184175,
    "runtime_rebuy_readiness": 0.12,
}

_BTC_RUNNERCHECK_WAIT_BIAS_WAIT_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_hold",
    "surface_name": "continuation_hold_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "FLAT",
    "current_profit": 0.0,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.0,
    "giveback_ratio": 0.0,
    "checkpoint_rule_family_hint": "wait_bias",
    "runtime_continuation_odds": 0.451,
    "runtime_reversal_odds": 0.824,
    "runtime_hold_quality_score": 0.19733,
    "runtime_partial_exit_ev": 0.33856,
    "runtime_full_exit_risk": 0.45202,
    "runtime_rebuy_readiness": 0.08,
}

_NAS_OPEN_PROFIT_CONTINUATION_ROW = {
    "symbol": "NAS100",
    "source": "open_trade_backfill",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_PROFIT",
    "current_profit": 0.27,
    "mfe_since_entry": 0.41,
    "mae_since_entry": 0.0,
    "runtime_continuation_odds": 0.6958,
    "runtime_reversal_odds": 0.4840,
    "runtime_hold_quality_score": 0.44317,
    "runtime_partial_exit_ev": 0.50692,
    "runtime_full_exit_risk": 0.220956,
    "runtime_rebuy_readiness": 0.29930,
}

_NAS_PROFIT_HOLD_MICRO_TRIM_ROW = {
    "symbol": "NAS100",
    "source": "exit_manage_hold",
    "surface_name": "follow_through_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "runner_secured": False,
    "realized_pnl_state": "NONE",
    "unrealized_pnl_state": "OPEN_PROFIT",
    "current_profit": 0.02,
    "mfe_since_entry": 0.02,
    "mae_since_entry": 0.0,
    "giveback_from_peak": 0.0,
    "giveback_ratio": 0.0,
    "checkpoint_rule_family_hint": "profit_hold_bias",
    "runtime_continuation_odds": 0.5888,
    "runtime_reversal_odds": 0.56,
    "runtime_hold_quality_score": 0.36304,
    "runtime_partial_exit_ev": 0.49616,
    "runtime_full_exit_risk": 0.282016,
    "runtime_rebuy_readiness": 0.135872,
}

_BTC_RUNNER_EARLY_TRIM_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_runner",
    "surface_name": "follow_through_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "runner_secured": True,
    "realized_pnl_state": "LOCKED",
    "unrealized_pnl_state": "OPEN_PROFIT",
    "current_profit": 0.86,
    "mfe_since_entry": 1.10,
    "mae_since_entry": 0.0,
    "giveback_from_peak": 0.0,
    "giveback_ratio": 0.0,
    "checkpoint_rule_family_hint": "runner_secured_continuation",
    "exit_stage_family": "runner",
    "runtime_continuation_odds": 0.5658,
    "runtime_reversal_odds": 0.74,
    "runtime_hold_quality_score": 0.31999,
    "runtime_partial_exit_ev": 0.54076,
    "runtime_full_exit_risk": 0.377156,
    "runtime_rebuy_readiness": 0.116237,
}

_NAS_RUNNER_EARLY_TRIM_ROW = {
    "symbol": "NAS100",
    "source": "exit_manage_runner",
    "surface_name": "follow_through_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "runner_secured": True,
    "realized_pnl_state": "LOCKED",
    "unrealized_pnl_state": "OPEN_PROFIT",
    "current_profit": 0.25,
    "mfe_since_entry": 0.37,
    "mae_since_entry": 0.0,
    "giveback_from_peak": 0.12,
    "giveback_ratio": 0.324324,
    "checkpoint_rule_family_hint": "runner_secured_continuation",
    "exit_stage_family": "runner",
    "runtime_continuation_odds": 0.5658,
    "runtime_reversal_odds": 0.74,
    "runtime_hold_quality_score": 0.31999,
    "runtime_partial_exit_ev": 0.54076,
    "runtime_full_exit_risk": 0.377156,
    "runtime_rebuy_readiness": 0.116237,
}

_BTC_RUNNER_HEALTHY_PARTIAL_THEN_HOLD_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_runner",
    "surface_name": "continuation_hold_surface",
    "position_side": "SELL",
    "position_size_fraction": 0.5,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": True,
    "realized_pnl_state": "LOCKED",
    "unrealized_pnl_state": "OPEN_PROFIT",
    "current_profit": 0.92,
    "mfe_since_entry": 1.12,
    "mae_since_entry": 0.0,
    "giveback_from_peak": 0.08,
    "giveback_ratio": 0.08,
    "checkpoint_rule_family_hint": "runner_secured_continuation",
    "exit_stage_family": "runner",
    "runtime_continuation_odds": 0.74,
    "runtime_reversal_odds": 0.46,
    "runtime_hold_quality_score": 0.43,
    "runtime_partial_exit_ev": 0.56,
    "runtime_full_exit_risk": 0.21,
    "runtime_rebuy_readiness": 0.18,
}

_BTC_EARLY_ACTIVE_OPEN_LOSS_WAIT_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_hold",
    "surface_name": "follow_through_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "INITIAL_PUSH",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.77,
    "mfe_since_entry": 0.01,
    "mae_since_entry": 0.77,
    "giveback_from_peak": 0.78,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "active_open_loss",
    "exit_stage_family": "hold",
    "runtime_continuation_odds": 0.653282,
    "runtime_reversal_odds": 0.526218,
    "runtime_hold_quality_score": 0.349964,
    "runtime_partial_exit_ev": 0.305865,
    "runtime_full_exit_risk": 0.491265,
    "runtime_rebuy_readiness": 0.12679,
}

_BTC_INITIAL_PUSH_ACTIVE_OPEN_LOSS_WAIT_BOUNDARY_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_hold",
    "surface_name": "follow_through_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "INITIAL_PUSH",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.49,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.49,
    "giveback_from_peak": 0.49,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "active_open_loss",
    "exit_stage_family": "hold",
    "runtime_continuation_odds": 0.783517,
    "runtime_reversal_odds": 0.375983,
    "runtime_hold_quality_score": 0.463659,
    "runtime_partial_exit_ev": 0.327962,
    "runtime_full_exit_risk": 0.356723,
    "runtime_rebuy_readiness": 0.12,
}

_BTC_EARLY_ACTIVE_OPEN_LOSS_TRIM_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_hold",
    "surface_name": "follow_through_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "INITIAL_PUSH",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.55,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.55,
    "giveback_from_peak": 0.55,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "active_open_loss",
    "exit_stage_family": "hold",
    "runtime_continuation_odds": 0.42511,
    "runtime_reversal_odds": 0.75589,
    "runtime_hold_quality_score": 0.160161,
    "runtime_partial_exit_ev": 0.295778,
    "runtime_full_exit_risk": 0.653001,
    "runtime_rebuy_readiness": 0.11,
}

_BTC_BACKFILL_RECLAIM_OPEN_LOSS_WAIT_ROW = {
    "symbol": "BTCUSD",
    "source": "open_trade_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RECLAIM_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.26,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.26,
    "giveback_from_peak": 0.24,
    "giveback_ratio": 0.923077,
    "checkpoint_rule_family_hint": "active_open_loss",
    "runtime_continuation_odds": 0.968,
    "runtime_reversal_odds": 0.3935,
    "runtime_hold_quality_score": 0.56022,
    "runtime_partial_exit_ev": 0.34869,
    "runtime_full_exit_risk": 0.364185,
    "runtime_rebuy_readiness": 0.16,
}

_BTC_BACKFILL_RECLAIM_OPEN_LOSS_HOLD_ROW = {
    "symbol": "BTCUSD",
    "source": "open_trade_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RECLAIM_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.18,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.18,
    "giveback_from_peak": 0.11,
    "giveback_ratio": 0.60,
    "checkpoint_rule_family_hint": "active_open_loss",
    "runtime_continuation_odds": 0.74,
    "runtime_reversal_odds": 0.50,
    "runtime_hold_quality_score": 0.56,
    "runtime_partial_exit_ev": 0.35,
    "runtime_full_exit_risk": 0.37,
    "runtime_rebuy_readiness": 0.16,
}

_BTC_EARLY_OPEN_LOSS_PROTECTIVE_WAIT_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_hold",
    "surface_name": "follow_through_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "INITIAL_PUSH",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.42,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.42,
    "giveback_from_peak": 0.42,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "open_loss_protective",
    "runtime_continuation_odds": 0.694667,
    "runtime_reversal_odds": 0.400833,
    "runtime_hold_quality_score": 0.407834,
    "runtime_partial_exit_ev": 0.30305,
    "runtime_full_exit_risk": 0.404085,
    "runtime_rebuy_readiness": 0.12,
}

_NAS_BACKFILL_OPEN_LOSS_PROTECTIVE_WAIT_ROW = {
    "symbol": "NAS100",
    "source": "open_trade_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.22,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.22,
    "giveback_from_peak": 0.22,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "open_loss_protective",
    "runtime_continuation_odds": 0.707647,
    "runtime_reversal_odds": 0.743853,
    "runtime_hold_quality_score": 0.318927,
    "runtime_partial_exit_ev": 0.459845,
    "runtime_full_exit_risk": 0.468449,
    "runtime_rebuy_readiness": 0.1,
}

_XAU_BACKFILL_OPEN_LOSS_PROTECTIVE_FULL_EXIT_ROW = {
    "symbol": "XAUUSD",
    "source": "closed_trade_hold_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -1.56,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 1.56,
    "giveback_from_peak": 0.56,
    "giveback_ratio": 0.358974,
    "checkpoint_rule_family_hint": "open_loss_protective",
    "runtime_continuation_odds": 0.666415,
    "runtime_reversal_odds": 0.785085,
    "runtime_hold_quality_score": 0.284704,
    "runtime_partial_exit_ev": 0.407893,
    "runtime_full_exit_risk": 0.581012,
    "runtime_rebuy_readiness": 0.08,
}

_NAS_BACKFILL_OPEN_LOSS_PROTECTIVE_MODERATE_WAIT_ROW = {
    "symbol": "NAS100",
    "source": "open_trade_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.49,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.49,
    "giveback_from_peak": 0.49,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "open_loss_protective",
    "runtime_continuation_odds": 0.695455,
    "runtime_reversal_odds": 0.756045,
    "runtime_hold_quality_score": 0.308808,
    "runtime_partial_exit_ev": 0.444483,
    "runtime_full_exit_risk": 0.501734,
    "runtime_rebuy_readiness": 0.1,
}

_XAU_BACKFILL_OPEN_LOSS_PROTECTIVE_MODERATE_WAIT_ROW = {
    "symbol": "XAUUSD",
    "source": "closed_trade_hold_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -1.22,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 1.22,
    "giveback_from_peak": 1.22,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "open_loss_protective",
    "runtime_continuation_odds": 0.694815,
    "runtime_reversal_odds": 0.756685,
    "runtime_hold_quality_score": 0.308276,
    "runtime_partial_exit_ev": 0.443677,
    "runtime_full_exit_risk": 0.50348,
    "runtime_rebuy_readiness": 0.08,
}

_NAS_OPEN_LOSS_PROTECTIVE_ROW = {
    "symbol": "NAS100",
    "source": "open_trade_backfill",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.33,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.33,
    "giveback_from_peak": 0.49,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "open_loss_protective",
    "exit_stage_family": "protective",
    "runtime_continuation_odds": 0.5508,
    "runtime_reversal_odds": 0.6425,
    "runtime_hold_quality_score": 0.26104,
    "runtime_partial_exit_ev": 0.30011,
    "runtime_full_exit_risk": 0.576231,
    "runtime_rebuy_readiness": 0.22744,
}

_BTC_OPEN_LOSS_BACKFILL_ROW = {
    "symbol": "BTCUSD",
    "source": "open_trade_backfill",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.06,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.06,
    "giveback_from_peak": 0.06,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "active_open_loss",
    "exit_stage_family": "backfill",
    "runtime_continuation_odds": 0.4738,
    "runtime_reversal_odds": 0.72,
    "runtime_hold_quality_score": 0.19699,
    "runtime_partial_exit_ev": 0.29556,
    "runtime_full_exit_risk": 0.632716,
    "runtime_rebuy_readiness": 0.18294,
}

_NAS_PROTECTIVE_RECLAIM_OPEN_LOSS_WAIT_ROW = {
    "symbol": "NAS100",
    "source": "exit_manage_hold",
    "surface_name": "protective_exit_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RECLAIM_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -1.13,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 1.13,
    "giveback_from_peak": 1.13,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "active_open_loss",
    "exit_stage_family": "hold",
    "runtime_continuation_odds": 0.905,
    "runtime_reversal_odds": 0.5735,
    "runtime_hold_quality_score": 0.43917,
    "runtime_partial_exit_ev": 0.36129,
    "runtime_full_exit_risk": 0.546525,
    "runtime_rebuy_readiness": 0.18,
}

_BTC_PROTECTIVE_RECLAIM_OPEN_LOSS_WAIT_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_hold",
    "surface_name": "protective_exit_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RECLAIM_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.15,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.15,
    "giveback_from_peak": 0.15,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "active_open_loss",
    "exit_stage_family": "hold",
    "runtime_continuation_odds": 0.869,
    "runtime_reversal_odds": 0.6935,
    "runtime_hold_quality_score": 0.38577,
    "runtime_partial_exit_ev": 0.37089,
    "runtime_full_exit_risk": 0.619005,
    "runtime_rebuy_readiness": 0.18,
}

_BTC_PROTECTIVE_RECLAIM_OPEN_LOSS_PROTECTIVE_WAIT_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_protective",
    "surface_name": "protective_exit_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RECLAIM_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.84,
    "mfe_since_entry": 0.0,
    "mae_since_entry": 0.84,
    "giveback_from_peak": 0.84,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "open_loss_protective",
    "exit_stage_family": "protective",
    "runtime_continuation_odds": 0.869,
    "runtime_reversal_odds": 0.6935,
    "runtime_hold_quality_score": 0.38577,
    "runtime_partial_exit_ev": 0.37089,
    "runtime_full_exit_risk": 0.619005,
    "runtime_rebuy_readiness": 0.18,
}

_XAU_PROTECTIVE_LATE_OPEN_LOSS_WAIT_ROW = {
    "symbol": "XAUUSD",
    "source": "exit_manage_hold",
    "surface_name": "protective_exit_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "LATE_TREND_CHECK",
    "runner_secured": False,
    "realized_pnl_state": "NONE",
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.06,
    "mfe_since_entry": 0.31,
    "mae_since_entry": 0.06,
    "giveback_from_peak": 0.37,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "active_open_loss",
    "runtime_continuation_odds": 0.736784,
    "runtime_reversal_odds": 0.707716,
    "runtime_hold_quality_score": 0.309071,
    "runtime_partial_exit_ev": 0.479978,
    "runtime_full_exit_risk": 0.483055,
    "runtime_rebuy_readiness": 0.029767,
}

_XAU_BACKFILL_RUNNER_WAIT_BOUNDARY_ROW = {
    "symbol": "XAUUSD",
    "source": "open_trade_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": True,
    "realized_pnl_state": "LOCKED",
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.19,
    "mfe_since_entry": 0.06,
    "mae_since_entry": 0.19,
    "giveback_ratio": 0.315789,
    "checkpoint_rule_family_hint": "runner_secured_continuation",
    "exit_stage_family": "runner",
    "runtime_continuation_odds": 0.74,
    "runtime_reversal_odds": 0.6675,
    "runtime_hold_quality_score": 0.3781,
    "runtime_partial_exit_ev": 0.42725,
    "runtime_full_exit_risk": 0.499925,
    "runtime_rebuy_readiness": 0.08,
}

_BTC_BACKFILL_RUNNER_WAIT_BOUNDARY_ROW = {
    "symbol": "BTCUSD",
    "source": "closed_trade_hold_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": True,
    "realized_pnl_state": "LOCKED",
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.76,
    "mfe_since_entry": 0.06,
    "mae_since_entry": 0.76,
    "giveback_ratio": 0.302632,
    "checkpoint_rule_family_hint": "runner_secured_continuation",
    "exit_stage_family": "runner",
    "runtime_continuation_odds": 0.711532,
    "runtime_reversal_odds": 0.779968,
    "runtime_hold_quality_score": 0.330952,
    "runtime_partial_exit_ev": 0.44634,
    "runtime_full_exit_risk": 0.551844,
    "runtime_rebuy_readiness": 0.08,
}

_NAS_BACKFILL_LATE_RUNNER_WAIT_BOUNDARY_ROW = {
    "symbol": "NAS100",
    "source": "closed_trade_hold_backfill",
    "surface_name": "continuation_hold_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "LATE_TREND_CHECK",
    "runner_secured": True,
    "realized_pnl_state": "LOCKED",
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.67,
    "mfe_since_entry": 0.02,
    "mae_since_entry": 0.67,
    "giveback_ratio": 0.029851,
    "checkpoint_rule_family_hint": "runner_secured_continuation",
    "exit_stage_family": "runner",
    "runtime_continuation_odds": 0.680719,
    "runtime_reversal_odds": 0.621781,
    "runtime_hold_quality_score": 0.358297,
    "runtime_partial_exit_ev": 0.409856,
    "runtime_full_exit_risk": 0.484012,
    "runtime_rebuy_readiness": 0.08,
}

_BTC_MICRO_OPEN_LOSS_PROTECTIVE_WAIT_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_hold",
    "surface_name": "follow_through_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.31,
    "mfe_since_entry": 0.03,
    "mae_since_entry": 0.31,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "open_loss_protective",
    "exit_stage_family": "protective",
    "runtime_continuation_odds": 0.659624,
    "runtime_reversal_odds": 0.598676,
    "runtime_hold_quality_score": 0.333164,
    "runtime_partial_exit_ev": 0.326328,
    "runtime_full_exit_risk": 0.514892,
    "runtime_rebuy_readiness": 0.08,
}

_BTC_MICRO_LATE_OPEN_LOSS_PROTECTIVE_WAIT_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_hold",
    "surface_name": "protective_exit_surface",
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "LATE_TREND_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "OPEN_LOSS",
    "current_profit": -0.31,
    "mfe_since_entry": 0.03,
    "mae_since_entry": 0.31,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "open_loss_protective",
    "exit_stage_family": "protective",
    "runtime_continuation_odds": 0.673824,
    "runtime_reversal_odds": 0.722676,
    "runtime_hold_quality_score": 0.270254,
    "runtime_partial_exit_ev": 0.346528,
    "runtime_full_exit_risk": 0.652536,
    "runtime_rebuy_readiness": 0.08,
}

_BTC_FLAT_ACTIVE_MICRO_WAIT_ROW = {
    "symbol": "BTCUSD",
    "source": "exit_manage_hold",
    "surface_name": "continuation_hold_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "FLAT",
    "realized_pnl_state": "NONE",
    "current_profit": 0.0,
    "mfe_since_entry": 0.09,
    "mae_since_entry": 0.0,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "active_flat_profit",
    "exit_stage_family": "hold",
    "runtime_continuation_odds": 0.782,
    "runtime_reversal_odds": 0.5915,
    "runtime_hold_quality_score": 0.44448,
    "runtime_partial_exit_ev": 0.49221,
    "runtime_full_exit_risk": 0.264565,
    "runtime_rebuy_readiness": 0.08,
}

_NAS_FLAT_ACTIVE_MICRO_WAIT_ROW = {
    "symbol": "NAS100",
    "source": "exit_manage_hold",
    "surface_name": "follow_through_surface",
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "runner_secured": False,
    "unrealized_pnl_state": "FLAT",
    "realized_pnl_state": "NONE",
    "current_profit": 0.0,
    "mfe_since_entry": 0.05,
    "mae_since_entry": 0.0,
    "giveback_ratio": 0.99,
    "checkpoint_rule_family_hint": "active_flat_profit",
    "exit_stage_family": "hold",
    "runtime_continuation_odds": 0.7568,
    "runtime_reversal_odds": 0.5075,
    "runtime_hold_quality_score": 0.45414,
    "runtime_partial_exit_ev": 0.44241,
    "runtime_full_exit_risk": 0.222901,
    "runtime_rebuy_readiness": 0.08,
}


def test_resolve_management_action_prefers_hold_for_secured_runner() -> None:
    payload = resolve_management_action(
        checkpoint_ctx={
            "position_side": "BUY",
            "position_size_fraction": 0.5,
            "checkpoint_type": "RUNNER_CHECK",
            "runner_secured": True,
            "checkpoint_rule_family_hint": "runner_secured_continuation",
            "exit_stage_family": "runner",
            "unrealized_pnl_state": "OPEN_PROFIT",
            "runtime_continuation_odds": 0.66,
            "runtime_reversal_odds": 0.28,
            "runtime_hold_quality_score": 0.61,
            "runtime_partial_exit_ev": 0.52,
            "runtime_full_exit_risk": 0.18,
            "runtime_rebuy_readiness": 0.21,
            "giveback_ratio": 0.10,
        }
    )

    assert payload["management_action_label"] == "HOLD"
    assert payload["management_action_reason"] == "runner_secured_hold_continue"


def test_resolve_management_action_prefers_hold_for_locked_runner_even_at_full_size() -> None:
    payload = resolve_management_action(
        checkpoint_ctx={
            "position_side": "BUY",
            "position_size_fraction": 1.0,
            "checkpoint_type": "RUNNER_CHECK",
            "runner_secured": True,
            "checkpoint_rule_family_hint": "runner_secured_continuation",
            "exit_stage_family": "runner",
            "realized_pnl_state": "LOCKED",
            "unrealized_pnl_state": "OPEN_PROFIT",
            "runtime_continuation_odds": 0.63,
            "runtime_reversal_odds": 0.34,
            "runtime_hold_quality_score": 0.46,
            "runtime_partial_exit_ev": 0.59,
            "runtime_full_exit_risk": 0.14,
            "runtime_rebuy_readiness": 0.19,
            "giveback_ratio": 0.08,
        }
    )

    assert payload["management_action_label"] == "HOLD"
    assert payload["management_action_reason"] == "runner_locked_hold_continue"


def test_resolve_management_action_marks_partial_exit_for_active_flat_profit_reversal_pressure() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_ACTIVE_FLAT_PROFIT_ROW)

    assert payload["management_action_label"] == "PARTIAL_EXIT"
    assert payload["management_action_reason"] == "flat_active_risk_trim"


def test_resolve_management_action_keeps_wait_for_balanced_active_flat_profit_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_ACTIVE_FLAT_PROFIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "flat_active_balanced_wait"


def test_resolve_management_action_uses_wait_for_backfill_flat_active_position_retest_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_XAU_BACKFILL_ACTIVE_POSITION_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "backfill_flat_active_wait_retest"


def test_resolve_management_action_keeps_hold_for_stronger_backfill_flat_active_position_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_XAU_BACKFILL_ACTIVE_POSITION_HOLD_ROW)

    assert payload["management_action_label"] == "HOLD"
    assert payload["management_action_reason"] == "flat_active_hold_retest"


def test_resolve_management_action_uses_wait_for_late_flat_active_position_wait_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_LATE_ACTIVE_POSITION_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "flat_late_wait_bias_wait_retest"


def test_resolve_management_action_uses_wait_for_flat_runnercheck_wait_bias_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_RUNNERCHECK_WAIT_BIAS_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "flat_backfill_wait_bias_wait_retest"


def test_resolve_management_action_keeps_partial_then_hold_for_open_profit_continuation_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_OPEN_PROFIT_CONTINUATION_ROW)

    assert payload["management_action_label"] == "PARTIAL_THEN_HOLD"
    assert payload["management_action_reason"] == "runner_lock_then_hold"


def test_resolve_management_action_prefers_partial_exit_for_runner_secured_early_trim_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_RUNNER_EARLY_TRIM_ROW)

    assert payload["management_action_label"] == "PARTIAL_EXIT"
    assert payload["management_action_reason"] == "runner_secured_early_trim_bias"


def test_resolve_management_action_does_not_force_early_trim_for_healthy_runner_capture_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_RUNNER_HEALTHY_PARTIAL_THEN_HOLD_ROW)

    assert payload["management_action_reason"] != "runner_secured_early_trim_bias"


def test_resolve_management_action_prefers_partial_exit_for_nas_runner_secured_early_trim_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_RUNNER_EARLY_TRIM_ROW)

    assert payload["management_action_label"] == "PARTIAL_EXIT"
    assert payload["management_action_reason"] == "runner_secured_early_trim_bias"


def test_resolve_management_action_prefers_partial_exit_for_profit_hold_micro_trim_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_PROFIT_HOLD_MICRO_TRIM_ROW)

    assert payload["management_action_label"] == "PARTIAL_EXIT"
    assert payload["management_action_reason"] == "profit_hold_micro_trim_bias"


def test_resolve_management_action_keeps_wait_for_early_active_open_loss_retest_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_EARLY_ACTIVE_OPEN_LOSS_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "early_open_loss_wait_retest"


def test_resolve_management_action_keeps_wait_for_initial_push_active_open_loss_wait_boundary_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_INITIAL_PUSH_ACTIVE_OPEN_LOSS_WAIT_BOUNDARY_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "initial_push_active_open_loss_wait_boundary_retest"


def test_resolve_management_action_keeps_partial_exit_for_true_early_active_open_loss_trim_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_EARLY_ACTIVE_OPEN_LOSS_TRIM_ROW)

    assert payload["management_action_label"] == "PARTIAL_EXIT"
    assert payload["management_action_reason"] in {"open_loss_risk_reduce", "full_exit_gate_not_met_trim_fallback"}


def test_resolve_management_action_uses_wait_for_backfill_reclaim_open_loss_retest_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_BACKFILL_RECLAIM_OPEN_LOSS_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "backfill_reclaim_open_loss_wait_retest"


def test_resolve_management_action_keeps_hold_for_weaker_backfill_reclaim_open_loss_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_BACKFILL_RECLAIM_OPEN_LOSS_HOLD_ROW)

    assert payload["management_action_label"] == "HOLD"
    assert payload["management_action_reason"] == "score_leader::hold"


def test_resolve_management_action_uses_wait_for_early_open_loss_protective_retest_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_EARLY_OPEN_LOSS_PROTECTIVE_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "early_open_loss_protective_wait_retest"


def test_resolve_management_action_uses_wait_for_backfill_open_loss_protective_runner_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_BACKFILL_OPEN_LOSS_PROTECTIVE_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "backfill_open_loss_protective_wait_retest"


def test_resolve_management_action_uses_wait_for_moderate_backfill_open_loss_protective_runner_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_BACKFILL_OPEN_LOSS_PROTECTIVE_MODERATE_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "backfill_open_loss_protective_wait_retest"


def test_resolve_management_action_uses_wait_for_moderate_xau_backfill_open_loss_protective_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_XAU_BACKFILL_OPEN_LOSS_PROTECTIVE_MODERATE_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "backfill_open_loss_protective_wait_retest"


def test_resolve_management_action_keeps_full_exit_for_stronger_backfill_open_loss_protective_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_XAU_BACKFILL_OPEN_LOSS_PROTECTIVE_FULL_EXIT_ROW)

    assert payload["management_action_label"] == "FULL_EXIT"
    assert payload["management_action_reason"] in {"open_loss_protective_exit", "open_loss_extreme_pressure_exit"}


def test_resolve_management_action_marks_full_exit_for_open_loss_protective_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_OPEN_LOSS_PROTECTIVE_ROW)

    assert payload["management_action_label"] == "FULL_EXIT"
    assert payload["management_action_reason"] == "open_loss_protective_exit"


def test_resolve_management_action_demotes_non_protective_open_loss_to_partial_exit() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_OPEN_LOSS_BACKFILL_ROW)

    assert payload["management_action_label"] == "PARTIAL_EXIT"
    assert payload["management_action_reason"] == "open_loss_risk_reduce"


def test_resolve_management_action_keeps_wait_for_protective_reclaim_open_loss_retest_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_PROTECTIVE_RECLAIM_OPEN_LOSS_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "protective_reclaim_open_loss_wait_retest"


def test_resolve_management_action_expands_wait_retest_to_weaker_protective_reclaim_open_loss_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_PROTECTIVE_RECLAIM_OPEN_LOSS_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "protective_reclaim_open_loss_wait_retest"


def test_resolve_management_action_keeps_wait_for_protective_reclaim_open_loss_protective_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_PROTECTIVE_RECLAIM_OPEN_LOSS_PROTECTIVE_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "protective_reclaim_open_loss_wait_retest"


def test_resolve_management_action_uses_wait_for_protective_late_open_loss_retest_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_XAU_PROTECTIVE_LATE_OPEN_LOSS_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "protective_late_open_loss_wait_retest"


def test_resolve_management_action_uses_wait_for_xau_backfill_runner_wait_boundary_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_XAU_BACKFILL_RUNNER_WAIT_BOUNDARY_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "xau_backfill_runner_wait_boundary_retest"


def test_resolve_management_action_uses_wait_for_btc_backfill_runner_wait_boundary_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_BACKFILL_RUNNER_WAIT_BOUNDARY_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "btc_backfill_runner_wait_boundary_retest"


def test_resolve_management_action_uses_wait_for_nas_backfill_late_runner_wait_boundary_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_BACKFILL_LATE_RUNNER_WAIT_BOUNDARY_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "nas_backfill_late_runner_wait_boundary_retest"


def test_resolve_management_action_uses_wait_for_btc_micro_open_loss_protective_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_MICRO_OPEN_LOSS_PROTECTIVE_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "protective_micro_open_loss_wait_retest"


def test_resolve_management_action_uses_wait_for_btc_micro_late_open_loss_protective_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_MICRO_LATE_OPEN_LOSS_PROTECTIVE_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "protective_micro_open_loss_wait_retest"


def test_resolve_management_action_uses_wait_for_btc_flat_active_micro_boundary_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_BTC_FLAT_ACTIVE_MICRO_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "flat_active_micro_wait_boundary"


def test_resolve_management_action_uses_wait_for_nas_flat_active_micro_boundary_row() -> None:
    payload = resolve_management_action(checkpoint_ctx=_NAS_FLAT_ACTIVE_MICRO_WAIT_ROW)

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_reason"] == "flat_active_micro_wait_boundary"


def test_resolve_management_action_prefers_wait_on_flat_initial_push() -> None:
    payload = resolve_management_action(
        checkpoint_ctx={
            "position_side": "FLAT",
            "position_size_fraction": 0.0,
            "checkpoint_type": "INITIAL_PUSH",
            "runtime_continuation_odds": 0.42,
            "runtime_reversal_odds": 0.39,
            "runtime_hold_quality_score": 0.08,
            "runtime_partial_exit_ev": 0.02,
            "runtime_full_exit_risk": 0.04,
            "runtime_rebuy_readiness": 0.18,
        }
    )

    assert payload["management_action_label"] == "WAIT"
    assert payload["management_action_confidence"] >= 0.3


def test_resolve_management_action_frame_backfills_blank_action_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "generated_at": "2026-04-10T14:30:00+09:00",
                "surface_name": "continuation_hold_surface",
                "checkpoint_id": "BTC_L1_CP003",
                "checkpoint_type": "RUNNER_CHECK",
                "position_side": "BUY",
                "position_size_fraction": 0.5,
                "runner_secured": True,
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "exit_stage_family": "runner",
                "giveback_ratio": 0.10,
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runtime_continuation_odds": 0.64,
                "runtime_reversal_odds": 0.26,
                "runtime_hold_quality_score": 0.59,
                "runtime_partial_exit_ev": 0.52,
                "runtime_full_exit_risk": 0.22,
                "runtime_rebuy_readiness": 0.22,
            }
        ]
    )

    resolved = resolve_management_action_frame(frame)

    assert resolved.iloc[0]["management_action_label"] == "HOLD"
    assert resolved.iloc[0]["management_action_reason"] == "runner_secured_hold_continue"


def test_build_checkpoint_management_action_snapshot_summarizes_symbol_actions() -> None:
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "generated_at": "2026-04-10T14:30:00+09:00",
                "surface_name": "continuation_hold_surface",
                "checkpoint_id": "BTC_L1_CP003",
                "checkpoint_type": "RUNNER_CHECK",
                "position_side": "BUY",
                "position_size_fraction": 0.5,
                "runner_secured": True,
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "exit_stage_family": "runner",
                "giveback_ratio": 0.10,
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runtime_continuation_odds": 0.64,
                "runtime_reversal_odds": 0.26,
                "runtime_hold_quality_score": 0.59,
                "runtime_partial_exit_ev": 0.52,
                "runtime_full_exit_risk": 0.22,
                "runtime_rebuy_readiness": 0.22,
            },
            {
                "symbol": "XAUUSD",
                "generated_at": "2026-04-10T14:31:00+09:00",
                "surface_name": "protective_exit_surface",
                "checkpoint_id": "XAU_L1_CP004",
                "checkpoint_type": "LATE_TREND_CHECK",
                "position_side": "BUY",
                "position_size_fraction": 1.0,
                "runner_secured": False,
                "unrealized_pnl_state": "OPEN_LOSS",
                "runtime_continuation_odds": 0.18,
                "runtime_reversal_odds": 0.82,
                "runtime_hold_quality_score": 0.14,
                "runtime_partial_exit_ev": 0.19,
                "runtime_full_exit_risk": 0.86,
                "runtime_rebuy_readiness": 0.08,
            },
        ]
    )

    snapshot, summary = build_checkpoint_management_action_snapshot(
        {"updated_at": "2026-04-10T14:35:00+09:00"},
        frame,
    )

    assert summary["resolved_row_count"] == 2
    assert summary["management_action_counts"]["HOLD"] == 1
    assert summary["management_action_counts"]["FULL_EXIT"] == 1
    assert set(snapshot["symbol"]) == {"BTCUSD", "NAS100", "XAUUSD"}
