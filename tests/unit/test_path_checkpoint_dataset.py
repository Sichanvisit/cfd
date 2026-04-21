import pandas as pd

from backend.services.path_checkpoint_dataset import (
    build_checkpoint_action_eval,
    build_checkpoint_dataset_artifacts,
    build_checkpoint_scene_dataset_artifacts,
    build_checkpoint_scene_eval,
    derive_hindsight_bootstrap_label,
    derive_hindsight_scene_bootstrap,
    derive_runtime_proxy_management_action,
)

_BTC_ACTIVE_FLAT_PROFIT_ROW = {
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "LATE_TREND_CHECK",
    "source": "open_trade_backfill",
    "runner_secured": False,
    "current_profit": 0.0,
    "unrealized_pnl_state": "FLAT",
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
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "LATE_TREND_CHECK",
    "source": "open_trade_backfill",
    "runner_secured": False,
    "current_profit": 0.0,
    "unrealized_pnl_state": "FLAT",
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
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "source": "open_trade_backfill",
    "runner_secured": False,
    "current_profit": 0.0,
    "unrealized_pnl_state": "FLAT",
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
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "source": "open_trade_backfill",
    "runner_secured": False,
    "current_profit": 0.0,
    "unrealized_pnl_state": "FLAT",
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
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "LATE_TREND_CHECK",
    "source": "open_trade_backfill",
    "surface_name": "continuation_hold_surface",
    "runner_secured": False,
    "current_profit": 0.0,
    "unrealized_pnl_state": "FLAT",
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
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RUNNER_CHECK",
    "source": "exit_manage_hold",
    "surface_name": "continuation_hold_surface",
    "runner_secured": False,
    "current_profit": 0.0,
    "unrealized_pnl_state": "FLAT",
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

_NAS_OPEN_LOSS_PROTECTIVE_ROW = {
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "source": "open_trade_backfill",
    "runner_secured": False,
    "current_profit": -0.33,
    "unrealized_pnl_state": "OPEN_LOSS",
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

_BTC_OPEN_LOSS_BACKFILL_ROW = {
    "position_side": "SELL",
    "position_size_fraction": 1.0,
    "checkpoint_type": "FIRST_PULLBACK_CHECK",
    "source": "open_trade_backfill",
    "runner_secured": False,
    "current_profit": -0.06,
    "unrealized_pnl_state": "OPEN_LOSS",
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
    "position_side": "BUY",
    "position_size_fraction": 1.0,
    "checkpoint_type": "RECLAIM_CHECK",
    "source": "exit_manage_hold",
    "surface_name": "protective_exit_surface",
    "runner_secured": False,
    "current_profit": -1.13,
    "unrealized_pnl_state": "OPEN_LOSS",
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


def test_derive_runtime_proxy_management_action_prefers_full_exit_on_protective_break() -> None:
    payload = derive_runtime_proxy_management_action(
        {
            "position_side": "BUY",
            "position_size_fraction": 1.0,
            "checkpoint_type": "LATE_TREND_CHECK",
            "runner_secured": False,
            "unrealized_pnl_state": "OPEN_LOSS",
            "runtime_continuation_odds": 0.22,
            "runtime_reversal_odds": 0.82,
            "runtime_hold_quality_score": 0.18,
            "runtime_partial_exit_ev": 0.21,
            "runtime_full_exit_risk": 0.84,
            "runtime_rebuy_readiness": 0.11,
        }
    )

    assert payload["runtime_proxy_management_action_label"] == "FULL_EXIT"
    assert payload["runtime_proxy_action_confidence"] >= 0.8


def test_derive_hindsight_bootstrap_label_marks_rebuy_window_on_flat_reclaim() -> None:
    payload = derive_hindsight_bootstrap_label(
        {
            "position_side": "FLAT",
            "position_size_fraction": 0.0,
            "checkpoint_type": "RECLAIM_CHECK",
            "runtime_continuation_odds": 0.74,
            "runtime_reversal_odds": 0.24,
            "runtime_hold_quality_score": 0.18,
            "runtime_partial_exit_ev": 0.05,
            "runtime_full_exit_risk": 0.08,
            "runtime_rebuy_readiness": 0.79,
        }
    )

    assert payload["hindsight_best_management_action_label"] == "REBUY"
    assert payload["hindsight_label_source"] == "bootstrap_proxy_v1"


def test_derive_hindsight_bootstrap_label_marks_partial_exit_for_active_flat_profit_reversal_row() -> None:
    payload = derive_hindsight_bootstrap_label(_BTC_ACTIVE_FLAT_PROFIT_ROW)

    assert payload["hindsight_best_management_action_label"] == "PARTIAL_EXIT"
    assert payload["hindsight_label_reason"] == "bootstrap_flat_active_risk_trim"
    assert payload["hindsight_manual_exception_required"] is False


def test_derive_hindsight_bootstrap_label_keeps_wait_for_balanced_active_flat_profit_row() -> None:
    payload = derive_hindsight_bootstrap_label(_NAS_ACTIVE_FLAT_PROFIT_ROW)

    assert payload["hindsight_best_management_action_label"] == "WAIT"
    assert payload["hindsight_label_reason"] == "bootstrap_flat_active_wait"


def test_derive_hindsight_bootstrap_label_marks_full_exit_for_open_loss_protective_row() -> None:
    payload = derive_hindsight_bootstrap_label(_NAS_OPEN_LOSS_PROTECTIVE_ROW)

    assert payload["hindsight_best_management_action_label"] == "FULL_EXIT"
    assert payload["hindsight_label_reason"] == "bootstrap_open_loss_protective_exit"
    assert payload["hindsight_manual_exception_required"] is False


def test_derive_hindsight_bootstrap_label_marks_partial_exit_for_non_protective_open_loss_row() -> None:
    payload = derive_hindsight_bootstrap_label(_BTC_OPEN_LOSS_BACKFILL_ROW)

    assert payload["hindsight_best_management_action_label"] == "PARTIAL_EXIT"
    assert payload["hindsight_label_reason"] == "bootstrap_open_loss_risk_reduce"


def test_derive_runtime_proxy_management_action_keeps_wait_for_protective_reclaim_open_loss_retest_row() -> None:
    payload = derive_runtime_proxy_management_action(_NAS_PROTECTIVE_RECLAIM_OPEN_LOSS_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "protective_reclaim_open_loss_wait_retest"


def test_derive_runtime_proxy_management_action_expands_wait_retest_to_weaker_protective_reclaim_open_loss_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_PROTECTIVE_RECLAIM_OPEN_LOSS_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "protective_reclaim_open_loss_wait_retest"


def test_derive_runtime_proxy_management_action_keeps_wait_for_protective_reclaim_open_loss_protective_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_PROTECTIVE_RECLAIM_OPEN_LOSS_PROTECTIVE_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "protective_reclaim_open_loss_wait_retest"


def test_derive_runtime_proxy_management_action_uses_wait_for_protective_late_open_loss_retest_row() -> None:
    payload = derive_runtime_proxy_management_action(_XAU_PROTECTIVE_LATE_OPEN_LOSS_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "protective_late_open_loss_wait_retest"


def test_derive_hindsight_bootstrap_label_marks_partial_then_hold_for_open_profit_runner_bias() -> None:
    payload = derive_hindsight_bootstrap_label(
        {
            "position_side": "SELL",
            "position_size_fraction": 1.0,
            "checkpoint_type": "FIRST_PULLBACK_CHECK",
            "current_profit": 0.27,
            "unrealized_pnl_state": "OPEN_PROFIT",
            "runner_secured": False,
            "mfe_since_entry": 0.41,
            "runtime_continuation_odds": 0.6958,
            "runtime_reversal_odds": 0.484,
            "runtime_hold_quality_score": 0.44317,
            "runtime_partial_exit_ev": 0.50692,
            "runtime_full_exit_risk": 0.220956,
            "runtime_rebuy_readiness": 0.29930,
        }
    )

    assert payload["hindsight_best_management_action_label"] == "PARTIAL_THEN_HOLD"
    assert payload["hindsight_label_reason"] == "bootstrap_profit_runner_capture"


def test_derive_runtime_proxy_management_action_prefers_partial_exit_for_runner_secured_early_trim_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_RUNNER_EARLY_TRIM_ROW)

    assert payload["runtime_proxy_management_action_label"] == "PARTIAL_EXIT"
    assert payload["runtime_proxy_action_reason"] == "runner_secured_early_trim_bias"


def test_derive_runtime_proxy_management_action_does_not_force_early_trim_for_healthy_runner_capture_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_RUNNER_HEALTHY_PARTIAL_THEN_HOLD_ROW)

    assert payload["runtime_proxy_action_reason"] != "runner_secured_early_trim_bias"


def test_derive_runtime_proxy_management_action_prefers_partial_exit_for_nas_runner_secured_early_trim_row() -> None:
    payload = derive_runtime_proxy_management_action(_NAS_RUNNER_EARLY_TRIM_ROW)

    assert payload["runtime_proxy_management_action_label"] == "PARTIAL_EXIT"
    assert payload["runtime_proxy_action_reason"] == "runner_secured_early_trim_bias"


def test_derive_runtime_proxy_management_action_prefers_partial_exit_for_profit_hold_micro_trim_row() -> None:
    payload = derive_runtime_proxy_management_action(_NAS_PROFIT_HOLD_MICRO_TRIM_ROW)

    assert payload["runtime_proxy_management_action_label"] == "PARTIAL_EXIT"
    assert payload["runtime_proxy_action_reason"] == "profit_hold_micro_trim_bias"


def test_derive_runtime_proxy_management_action_keeps_wait_for_early_active_open_loss_retest_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_EARLY_ACTIVE_OPEN_LOSS_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "early_open_loss_wait_retest"


def test_derive_runtime_proxy_management_action_keeps_partial_exit_for_true_early_active_open_loss_trim_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_EARLY_ACTIVE_OPEN_LOSS_TRIM_ROW)

    assert payload["runtime_proxy_management_action_label"] == "PARTIAL_EXIT"
    assert payload["runtime_proxy_action_reason"] in {"open_loss_risk_reduce", "full_exit_gate_not_met_trim_fallback"}


def test_derive_runtime_proxy_management_action_uses_wait_for_backfill_reclaim_open_loss_retest_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_BACKFILL_RECLAIM_OPEN_LOSS_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "backfill_reclaim_open_loss_wait_retest"


def test_derive_runtime_proxy_management_action_keeps_hold_for_weaker_backfill_reclaim_open_loss_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_BACKFILL_RECLAIM_OPEN_LOSS_HOLD_ROW)

    assert payload["runtime_proxy_management_action_label"] == "HOLD"
    assert payload["runtime_proxy_action_reason"] == "score_leader::hold"


def test_derive_runtime_proxy_management_action_uses_wait_for_early_open_loss_protective_retest_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_EARLY_OPEN_LOSS_PROTECTIVE_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "early_open_loss_protective_wait_retest"


def test_derive_runtime_proxy_management_action_uses_wait_for_backfill_open_loss_protective_runner_row() -> None:
    payload = derive_runtime_proxy_management_action(_NAS_BACKFILL_OPEN_LOSS_PROTECTIVE_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "backfill_open_loss_protective_wait_retest"


def test_derive_runtime_proxy_management_action_uses_wait_for_moderate_backfill_open_loss_protective_runner_row() -> None:
    payload = derive_runtime_proxy_management_action(_NAS_BACKFILL_OPEN_LOSS_PROTECTIVE_MODERATE_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "backfill_open_loss_protective_wait_retest"


def test_derive_runtime_proxy_management_action_uses_wait_for_moderate_xau_backfill_open_loss_protective_row() -> None:
    payload = derive_runtime_proxy_management_action(_XAU_BACKFILL_OPEN_LOSS_PROTECTIVE_MODERATE_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "backfill_open_loss_protective_wait_retest"


def test_derive_runtime_proxy_management_action_keeps_full_exit_for_stronger_backfill_open_loss_protective_row() -> None:
    payload = derive_runtime_proxy_management_action(_XAU_BACKFILL_OPEN_LOSS_PROTECTIVE_FULL_EXIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "FULL_EXIT"
    assert payload["runtime_proxy_action_reason"] in {"open_loss_protective_exit", "open_loss_extreme_pressure_exit"}


def test_derive_runtime_proxy_management_action_uses_wait_for_backfill_flat_active_position_retest_row() -> None:
    payload = derive_runtime_proxy_management_action(_XAU_BACKFILL_ACTIVE_POSITION_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "backfill_flat_active_wait_retest"


def test_derive_runtime_proxy_management_action_keeps_hold_for_stronger_backfill_flat_active_position_row() -> None:
    payload = derive_runtime_proxy_management_action(_XAU_BACKFILL_ACTIVE_POSITION_HOLD_ROW)

    assert payload["runtime_proxy_management_action_label"] == "HOLD"
    assert payload["runtime_proxy_action_reason"] == "flat_active_hold_retest"


def test_derive_runtime_proxy_management_action_uses_wait_for_late_flat_active_position_wait_row() -> None:
    payload = derive_runtime_proxy_management_action(_NAS_LATE_ACTIVE_POSITION_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "flat_late_wait_bias_wait_retest"


def test_derive_runtime_proxy_management_action_uses_wait_for_flat_runnercheck_wait_bias_row() -> None:
    payload = derive_runtime_proxy_management_action(_BTC_RUNNERCHECK_WAIT_BIAS_WAIT_ROW)

    assert payload["runtime_proxy_management_action_label"] == "WAIT"
    assert payload["runtime_proxy_action_reason"] == "flat_backfill_wait_bias_wait_retest"


def test_derive_hindsight_bootstrap_label_marks_hold_for_secured_runner_row() -> None:
    payload = derive_hindsight_bootstrap_label(
        {
            "position_side": "SELL",
            "position_size_fraction": 0.5,
            "checkpoint_type": "RUNNER_CHECK",
            "current_profit": 0.27,
            "unrealized_pnl_state": "OPEN_PROFIT",
            "runner_secured": True,
            "checkpoint_rule_family_hint": "runner_secured_continuation",
            "exit_stage_family": "runner",
            "mfe_since_entry": 0.41,
            "giveback_ratio": 0.10,
            "runtime_continuation_odds": 0.6958,
            "runtime_reversal_odds": 0.484,
            "runtime_hold_quality_score": 0.56317,
            "runtime_partial_exit_ev": 0.46692,
            "runtime_full_exit_risk": 0.220956,
            "runtime_rebuy_readiness": 0.29930,
        }
    )

    assert payload["hindsight_best_management_action_label"] == "HOLD"
    assert payload["hindsight_label_reason"] == "bootstrap_runner_secured_hold_continue"
    assert payload["hindsight_manual_exception_required"] is False


def test_derive_hindsight_bootstrap_label_marks_hold_for_locked_runner_row() -> None:
    payload = derive_hindsight_bootstrap_label(
        {
            "position_side": "SELL",
            "position_size_fraction": 1.0,
            "checkpoint_type": "RUNNER_CHECK",
            "current_profit": 0.19,
            "realized_pnl_state": "LOCKED",
            "unrealized_pnl_state": "OPEN_PROFIT",
            "runner_secured": True,
            "checkpoint_rule_family_hint": "runner_secured_continuation",
            "exit_stage_family": "runner",
            "mfe_since_entry": 0.27,
            "giveback_ratio": 0.08,
            "runtime_continuation_odds": 0.63,
            "runtime_reversal_odds": 0.34,
            "runtime_hold_quality_score": 0.46,
            "runtime_partial_exit_ev": 0.59,
            "runtime_full_exit_risk": 0.14,
            "runtime_rebuy_readiness": 0.19,
        }
    )

    assert payload["hindsight_best_management_action_label"] == "HOLD"
    assert payload["hindsight_label_reason"] == "bootstrap_runner_locked_hold_continue"


def test_derive_hindsight_scene_bootstrap_confirms_breakout_retest_hold() -> None:
    payload = derive_hindsight_scene_bootstrap(
        {
            "checkpoint_type": "RECLAIM_CHECK",
            "position_side": "FLAT",
            "runtime_scene_fine_label": "breakout_retest_hold",
            "runtime_scene_gate_label": "none",
            "runtime_scene_confidence": 0.82,
            "runtime_scene_confidence_band": "high",
            "runtime_scene_maturity": "confirmed",
            "runtime_continuation_odds": 0.74,
            "runtime_reversal_odds": 0.32,
            "runtime_hold_quality_score": 0.41,
            "runtime_partial_exit_ev": 0.29,
            "runtime_full_exit_risk": 0.14,
            "runtime_rebuy_readiness": 0.78,
            "hindsight_best_management_action_label": "REBUY",
            "runtime_score_reason": "follow_through_surface::continuation_hold_bias",
        }
    )

    assert payload["hindsight_scene_fine_label"] == "breakout_retest_hold"
    assert payload["hindsight_scene_quality_tier"] == "auto_high"


def test_derive_hindsight_scene_bootstrap_confirms_trend_exhaustion() -> None:
    payload = derive_hindsight_scene_bootstrap(
        {
            "checkpoint_type": "RUNNER_CHECK",
            "position_side": "BUY",
            "runtime_scene_fine_label": "trend_exhaustion",
            "runtime_scene_gate_label": "none",
            "runtime_scene_confidence": 0.68,
            "runtime_scene_confidence_band": "medium",
            "runtime_scene_maturity": "probable",
            "runtime_continuation_odds": 0.86,
            "runtime_reversal_odds": 0.55,
            "runtime_hold_quality_score": 0.48,
            "runtime_partial_exit_ev": 0.61,
            "giveback_ratio": 0.18,
            "current_profit": 0.47,
            "mfe_since_entry": 0.62,
            "mae_since_entry": 0.0,
            "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
        }
    )

    assert payload["hindsight_scene_fine_label"] == "trend_exhaustion"
    assert payload["hindsight_scene_quality_tier"] == "auto_medium"


def test_derive_hindsight_scene_bootstrap_confirms_time_decay_risk() -> None:
    payload = derive_hindsight_scene_bootstrap(
        {
            "checkpoint_type": "RUNNER_CHECK",
            "position_side": "BUY",
            "runtime_scene_fine_label": "time_decay_risk",
            "runtime_scene_gate_label": "none",
            "runtime_scene_confidence": 0.61,
            "runtime_scene_confidence_band": "medium",
            "runtime_scene_maturity": "probable",
            "runtime_continuation_odds": 0.56,
            "runtime_reversal_odds": 0.81,
            "runtime_hold_quality_score": 0.24,
            "runtime_partial_exit_ev": 0.46,
            "current_profit": 0.0,
            "mfe_since_entry": 0.10,
            "mae_since_entry": 0.0,
            "hindsight_best_management_action_label": "WAIT",
        }
    )

    assert payload["hindsight_scene_fine_label"] == "time_decay_risk"
    assert payload["hindsight_scene_quality_tier"] == "auto_medium"


def test_derive_hindsight_scene_bootstrap_fallback_confirms_trend_exhaustion_for_late_unresolved_runner_trim() -> None:
    payload = derive_hindsight_scene_bootstrap(
        {
            "checkpoint_type": "RUNNER_CHECK",
            "position_side": "BUY",
            "unrealized_pnl_state": "OPEN_PROFIT",
            "runner_secured": True,
            "runtime_scene_fine_label": "unresolved",
            "runtime_scene_gate_label": "none",
            "runtime_scene_confidence": 0.0,
            "runtime_scene_confidence_band": "low",
            "runtime_scene_maturity": "provisional",
            "runtime_continuation_odds": 0.86,
            "runtime_reversal_odds": 0.54,
            "runtime_hold_quality_score": 0.49,
            "runtime_partial_exit_ev": 0.62,
            "runtime_full_exit_risk": 0.22,
            "giveback_ratio": 0.24,
            "current_profit": 0.21,
            "mfe_since_entry": 0.39,
            "mae_since_entry": 0.0,
            "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
            "runtime_score_reason": "continuation_hold_surface::runner_lock_bias",
        }
    )

    assert payload["hindsight_scene_fine_label"] == "trend_exhaustion"
    assert payload["hindsight_scene_reason"] == "scene_bootstrap_late_exhaustion_fallback"


def test_derive_hindsight_scene_bootstrap_fallback_confirms_time_decay_for_late_unresolved_balanced_row() -> None:
    payload = derive_hindsight_scene_bootstrap(
        {
            "checkpoint_type": "LATE_TREND_CHECK",
            "position_side": "BUY",
            "unrealized_pnl_state": "FLAT",
            "runner_secured": False,
            "runtime_scene_fine_label": "unresolved",
            "runtime_scene_gate_label": "none",
            "runtime_scene_confidence": 0.0,
            "runtime_scene_confidence_band": "low",
            "runtime_scene_maturity": "provisional",
            "runtime_continuation_odds": 0.58,
            "runtime_reversal_odds": 0.62,
            "runtime_hold_quality_score": 0.28,
            "runtime_partial_exit_ev": 0.39,
            "runtime_full_exit_risk": 0.44,
            "current_profit": 0.04,
            "mfe_since_entry": 0.12,
            "mae_since_entry": 0.09,
            "hindsight_best_management_action_label": "WAIT",
            "runtime_score_reason": "continuation_hold_surface::balanced_checkpoint_state",
        }
    )

    assert payload["hindsight_scene_fine_label"] == "time_decay_risk"
    assert payload["hindsight_scene_reason"] == "scene_bootstrap_late_time_decay_fallback"


def test_build_checkpoint_dataset_artifacts_resolves_runtime_proxy_and_hindsight() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T14:00:00+09:00",
                "source": "exit_manage",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "leg_id": "BTC_L1",
                "leg_direction": "UP",
                "checkpoint_id": "BTC_L1_CP003",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_index_in_leg": 3,
                "position_side": "BUY",
                "position_size_fraction": 0.5,
                "avg_entry_price": 100.0,
                "realized_pnl_state": "PARTIAL_LOCKED",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": True,
                "mfe_since_entry": 12.0,
                "mae_since_entry": 2.0,
                "current_profit": 8.0,
                "giveback_ratio": 0.10,
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "exit_stage_family": "runner",
                "runtime_scene_coarse_family": "POSITION_MANAGEMENT",
                "runtime_scene_fine_label": "runner_healthy",
                "runtime_scene_gate_label": "none",
                "runtime_scene_modifier_json": "{\"late_trend\":false}",
                "runtime_scene_confidence": 0.88,
                "runtime_scene_confidence_band": "high",
                "runtime_scene_action_bias_strength": "medium",
                "runtime_scene_source": "heuristic_v1",
                "runtime_scene_maturity": "confirmed",
                "runtime_scene_transition_from": "pullback_continuation",
                "runtime_scene_transition_bars": 2,
                "runtime_scene_transition_speed": "normal",
                "runtime_scene_family_alignment": "aligned",
                "runtime_scene_gate_block_level": "none",
                "hindsight_scene_fine_label": "",
                "hindsight_scene_quality_tier": "",
                "runtime_continuation_odds": 0.64,
                "runtime_reversal_odds": 0.31,
                "runtime_hold_quality_score": 0.57,
                "runtime_partial_exit_ev": 0.46,
                "runtime_full_exit_risk": 0.22,
                "runtime_rebuy_readiness": 0.24,
                "runtime_score_reason": "continuation_hold_surface::runner_lock_bias",
            },
            {
                "generated_at": "2026-04-10T14:01:00+09:00",
                "source": "exit_manage",
                "symbol": "XAUUSD",
                "surface_name": "protective_exit_surface",
                "leg_id": "XAU_L1",
                "leg_direction": "UP",
                "checkpoint_id": "XAU_L1_CP004",
                "checkpoint_type": "LATE_TREND_CHECK",
                "checkpoint_index_in_leg": 4,
                "position_side": "BUY",
                "position_size_fraction": 1.0,
                "avg_entry_price": 200.0,
                "realized_pnl_state": "NONE",
                "unrealized_pnl_state": "OPEN_LOSS",
                "runner_secured": False,
                "mfe_since_entry": 1.0,
                "mae_since_entry": 9.0,
                "current_profit": -6.0,
                "runtime_continuation_odds": 0.21,
                "runtime_reversal_odds": 0.83,
                "runtime_hold_quality_score": 0.17,
                "runtime_partial_exit_ev": 0.19,
                "runtime_full_exit_risk": 0.86,
                "runtime_rebuy_readiness": 0.07,
                "runtime_score_reason": "protective_exit_surface::protective_pressure_dominant",
            },
            {
                "generated_at": "2026-04-10T14:02:00+09:00",
                "source": "entry_runtime",
                "symbol": "NAS100",
                "surface_name": "follow_through_surface",
                "leg_id": "NAS_L1",
                "leg_direction": "UP",
                "checkpoint_id": "NAS_L1_CP002",
                "checkpoint_type": "RECLAIM_CHECK",
                "checkpoint_index_in_leg": 2,
                "position_side": "FLAT",
                "position_size_fraction": 0.0,
                "avg_entry_price": 0.0,
                "realized_pnl_state": "NONE",
                "unrealized_pnl_state": "FLAT",
                "runner_secured": False,
                "mfe_since_entry": 0.0,
                "mae_since_entry": 0.0,
                "current_profit": 0.0,
                "runtime_continuation_odds": 0.71,
                "runtime_reversal_odds": 0.24,
                "runtime_hold_quality_score": 0.16,
                "runtime_partial_exit_ev": 0.04,
                "runtime_full_exit_risk": 0.08,
                "runtime_rebuy_readiness": 0.77,
                "runtime_score_reason": "follow_through_surface::pullback_reentry_ready",
            },
        ]
    )

    base, resolved, summary = build_checkpoint_dataset_artifacts(frame)

    assert len(base) == 3
    assert len(resolved) == 3
    assert summary["dataset_row_count"] == 3
    assert "runtime_scene_fine_label" in base.columns
    assert "runtime_scene_maturity" in base.columns
    assert "runtime_scene_gate_block_level" in base.columns
    assert resolved.iloc[0]["runtime_scene_fine_label"] == "runner_healthy"
    assert resolved.iloc[0]["runtime_scene_confidence_band"] == "high"
    assert set(resolved["hindsight_best_management_action_label"]) == {"HOLD", "FULL_EXIT", "REBUY"}


def test_build_checkpoint_dataset_artifacts_keeps_collect_recommendation_until_position_rows_are_richer() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T14:30:00+09:00",
                "source": "open_trade_backfill",
                "symbol": "NAS100",
                "surface_name": "follow_through_surface",
                "leg_id": "NAS_L1",
                "leg_direction": "UP",
                "checkpoint_id": "NAS_L1_CP002",
                "checkpoint_type": "FIRST_PULLBACK_CHECK",
                "checkpoint_index_in_leg": 2,
                "position_side": "SELL",
                "position_size_fraction": 1.0,
                "avg_entry_price": 25130.62,
                "realized_pnl_state": "NONE",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": False,
                "mfe_since_entry": 0.41,
                "mae_since_entry": 0.0,
                "current_profit": 0.27,
                "runtime_continuation_odds": 0.6958,
                "runtime_reversal_odds": 0.484,
                "runtime_hold_quality_score": 0.44317,
                "runtime_partial_exit_ev": 0.50692,
                "runtime_full_exit_risk": 0.220956,
                "runtime_rebuy_readiness": 0.29930,
                "runtime_score_reason": "follow_through_surface::continuation_hold_bias",
            }
        ]
    )

    _, resolved, summary = build_checkpoint_dataset_artifacts(frame)

    assert resolved.iloc[0]["hindsight_best_management_action_label"] == "PARTIAL_THEN_HOLD"
    assert summary["recommended_next_action"] == "collect_more_scene_resolved_rows_before_sa4"


def test_build_checkpoint_action_eval_computes_proxy_kpis() -> None:
    resolved = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "position_side": "BUY",
                "runtime_proxy_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_manual_exception_required": False,
                "runtime_hindsight_match": True,
                "runner_capture_eligible": True,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "auto_high",
            },
            {
                "symbol": "XAUUSD",
                "surface_name": "protective_exit_surface",
                "position_side": "BUY",
                "runtime_proxy_management_action_label": "FULL_EXIT",
                "hindsight_best_management_action_label": "FULL_EXIT",
                "hindsight_manual_exception_required": False,
                "runtime_hindsight_match": True,
                "runner_capture_eligible": False,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "auto_high",
            },
            {
                "symbol": "NAS100",
                "surface_name": "follow_through_surface",
                "position_side": "FLAT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "REBUY",
                "hindsight_manual_exception_required": True,
                "runtime_hindsight_match": False,
                "runner_capture_eligible": False,
                "missed_rebuy_eligible": True,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "manual_exception",
            },
            {
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "position_side": "BUY",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "HOLD",
                "hindsight_manual_exception_required": False,
                "runtime_hindsight_match": True,
                "runner_capture_eligible": False,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "auto_high",
            },
            {
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "position_side": "SELL",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_manual_exception_required": True,
                "runtime_hindsight_match": False,
                "runner_capture_eligible": False,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "manual_exception",
            },
        ]
    )

    eval_frame, summary = build_checkpoint_action_eval(resolved)

    assert summary["resolved_row_count"] == 5
    assert summary["full_exit_precision"] == 1.0
    assert summary["partial_then_hold_quality"] == 1.0
    assert summary["missed_rebuy_rate"] == 1.0
    assert summary["recommended_next_action"] == "proceed_to_pa7_review_queue"
    assert set(eval_frame["symbol"]) == {"BTCUSD", "NAS100", "XAUUSD"}


def test_build_checkpoint_action_eval_proceeds_to_pa8_when_manual_exceptions_are_cleared() -> None:
    resolved = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "position_side": "BUY",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "HOLD",
                "hindsight_manual_exception_required": False,
                "runtime_hindsight_match": True,
                "runner_capture_eligible": False,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "auto_high",
            },
            {
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "position_side": "BUY",
                "runtime_proxy_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_manual_exception_required": False,
                "runtime_hindsight_match": True,
                "runner_capture_eligible": True,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "auto_high",
            },
            {
                "symbol": "XAUUSD",
                "surface_name": "protective_exit_surface",
                "position_side": "BUY",
                "runtime_proxy_management_action_label": "FULL_EXIT",
                "hindsight_best_management_action_label": "FULL_EXIT",
                "hindsight_manual_exception_required": False,
                "runtime_hindsight_match": True,
                "runner_capture_eligible": False,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "auto_high",
            },
            {
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "position_side": "SELL",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "HOLD",
                "hindsight_manual_exception_required": False,
                "runtime_hindsight_match": True,
                "runner_capture_eligible": False,
                "missed_rebuy_eligible": False,
                "premature_full_exit_flag": False,
                "hindsight_quality_tier": "auto_high",
            },
        ]
    )

    _, summary = build_checkpoint_action_eval(resolved)

    assert summary["manual_exception_count"] == 0
    assert summary["recommended_next_action"] == "proceed_to_pa8_action_baseline_review"


def test_build_checkpoint_scene_dataset_artifacts_and_eval_exports_scene_resolution() -> None:
    resolved = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T14:00:00+09:00",
                "source": "entry_runtime",
                "symbol": "NAS100",
                "surface_name": "follow_through_surface",
                "leg_id": "NAS_L1",
                "leg_direction": "UP",
                "checkpoint_id": "NAS_L1_CP002",
                "checkpoint_type": "RECLAIM_CHECK",
                "checkpoint_index_in_leg": 2,
                "position_side": "FLAT",
                "unrealized_pnl_state": "FLAT",
                "runner_secured": False,
                "current_profit": 0.0,
                "mfe_since_entry": 0.0,
                "mae_since_entry": 0.0,
                "giveback_ratio": 0.0,
                "runtime_scene_coarse_family": "ENTRY_INITIATION",
                "runtime_scene_fine_label": "breakout_retest_hold",
                "runtime_scene_gate_label": "none",
                "runtime_scene_modifier_json": "{\"reclaim\": true}",
                "runtime_scene_confidence": 0.82,
                "runtime_scene_confidence_band": "high",
                "runtime_scene_action_bias_strength": "medium",
                "runtime_scene_source": "heuristic_v1",
                "runtime_scene_maturity": "confirmed",
                "runtime_scene_transition_from": "unresolved",
                "runtime_scene_transition_bars": 0,
                "runtime_scene_transition_speed": "fast",
                "runtime_scene_family_alignment": "aligned",
                "runtime_scene_gate_block_level": "none",
                "hindsight_scene_fine_label": "breakout_retest_hold",
                "hindsight_scene_quality_tier": "auto_high",
                "hindsight_scene_label_source": "scene_bootstrap_v1",
                "hindsight_scene_confidence": 0.82,
                "hindsight_scene_reason": "scene_bootstrap_breakout_retest_confirmation",
                "hindsight_scene_resolution_state": "bootstrap_confirmed",
                "runtime_hindsight_scene_match": True,
                "runtime_proxy_management_action_label": "REBUY",
                "hindsight_best_management_action_label": "REBUY",
            },
            {
                "generated_at": "2026-04-10T14:05:00+09:00",
                "source": "exit_manage_runner",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "leg_id": "BTC_L1",
                "leg_direction": "UP",
                "checkpoint_id": "BTC_L1_CP003",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_index_in_leg": 3,
                "position_side": "BUY",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": True,
                "current_profit": 0.47,
                "mfe_since_entry": 0.62,
                "mae_since_entry": 0.0,
                "giveback_ratio": 0.18,
                "runtime_scene_coarse_family": "DEFENSIVE_EXIT",
                "runtime_scene_fine_label": "trend_exhaustion",
                "runtime_scene_gate_label": "none",
                "runtime_scene_modifier_json": "{\"late_trend\": true}",
                "runtime_scene_confidence": 0.68,
                "runtime_scene_confidence_band": "medium",
                "runtime_scene_action_bias_strength": "medium",
                "runtime_scene_source": "heuristic_v1",
                "runtime_scene_maturity": "probable",
                "runtime_scene_transition_from": "runner_hold",
                "runtime_scene_transition_bars": 1,
                "runtime_scene_transition_speed": "normal",
                "runtime_scene_family_alignment": "upgrade",
                "runtime_scene_gate_block_level": "none",
                "hindsight_scene_fine_label": "trend_exhaustion",
                "hindsight_scene_quality_tier": "auto_medium",
                "hindsight_scene_label_source": "scene_bootstrap_v1",
                "hindsight_scene_confidence": 0.68,
                "hindsight_scene_reason": "scene_bootstrap_late_exhaustion_confirmation",
                "hindsight_scene_resolution_state": "bootstrap_confirmed",
                "runtime_hindsight_scene_match": True,
                "runtime_proxy_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
            },
        ]
    )

    scene_dataset, summary = build_checkpoint_scene_dataset_artifacts(resolved)
    scene_eval, eval_summary = build_checkpoint_scene_eval(scene_dataset)

    assert len(scene_dataset) == 2
    assert summary["runtime_scene_filled_row_count"] == 2
    assert summary["hindsight_scene_resolved_row_count"] == 2
    assert scene_eval.loc[scene_eval["symbol"] == "NAS100", "runtime_hindsight_scene_match_rate"].iloc[0] == 1.0
    assert eval_summary["runtime_hindsight_scene_match_rate"] == 1.0
