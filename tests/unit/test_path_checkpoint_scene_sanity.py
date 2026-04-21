import pandas as pd

from backend.services.path_checkpoint_scene_sanity import (
    build_checkpoint_scene_sanity,
    replay_checkpoint_scene_frame,
)


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T13:00:00+09:00",
                "symbol": "NAS100",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "runtime_continuation_odds": 0.74,
                "runtime_reversal_odds": 0.44,
                "runtime_hold_quality_score": 0.50,
                "runtime_partial_exit_ev": 0.35,
                "runtime_full_exit_risk": 0.20,
                "runtime_rebuy_readiness": 0.42,
                "runtime_score_reason": "continuation_hold_surface::continuation_hold_bias",
                "setup_reason": "breakout retest reclaim hold",
                "observe_action": "BUY",
                "observe_side": "BUY",
            },
            {
                "generated_at": "2026-04-10T13:05:00+09:00",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "source": "exit_manage_runner",
                "checkpoint_type": "RUNNER_CHECK",
                "bars_since_leg_start": 12,
                "runner_secured": True,
                "giveback_ratio": 0.30,
                "runtime_continuation_odds": 0.71,
                "runtime_reversal_odds": 0.63,
                "runtime_hold_quality_score": 0.49,
                "runtime_partial_exit_ev": 0.64,
                "runtime_full_exit_risk": 0.42,
                "runtime_rebuy_readiness": 0.16,
                "runtime_score_reason": "continuation_hold_surface::runner_lock_bias",
                "blocked_by": "allow_long_blocked",
            },
            {
                "generated_at": "2026-04-10T13:10:00+09:00",
                "symbol": "NAS100",
                "trade_link_key": "trade-1",
                "leg_id": "leg-b",
                "surface_name": "continuation_hold_surface",
                "source": "exit_manage_runner",
                "checkpoint_type": "RUNNER_CHECK",
                "bars_since_leg_start": 18,
                "position_side": "BUY",
                "unrealized_pnl_state": "FLAT",
                "current_profit": 0.0,
                "mfe_since_entry": 0.10,
                "mae_since_entry": 0.08,
                "runtime_continuation_odds": 0.40,
                "runtime_reversal_odds": 0.47,
                "runtime_hold_quality_score": 0.24,
                "runtime_partial_exit_ev": 0.26,
                "runtime_full_exit_risk": 0.34,
                "runtime_rebuy_readiness": 0.12,
                "runtime_score_reason": "continuation_hold_surface::balanced_checkpoint_state",
            },
        ]
    )


def test_replay_checkpoint_scene_frame_recreates_scene_columns() -> None:
    replay = replay_checkpoint_scene_frame(_sample_frame())

    assert len(replay) == 3
    assert "runtime_scene_fine_label" in replay.columns
    by_symbol = {
        symbol: frame.reset_index(drop=True)
        for symbol, frame in replay.groupby("symbol")
    }
    assert by_symbol["NAS100"].iloc[0]["runtime_scene_fine_label"] == "breakout_retest_hold"
    assert by_symbol["BTCUSD"].iloc[0]["runtime_scene_fine_label"] == "trend_exhaustion"
    assert by_symbol["NAS100"].iloc[1]["runtime_scene_fine_label"] == "time_decay_risk"


def test_build_checkpoint_scene_sanity_summarizes_distribution_and_transitions() -> None:
    observation, summary, replay = build_checkpoint_scene_sanity(_sample_frame())

    assert len(observation) == 3
    assert summary["row_count"] == 3
    assert summary["scene_filled_row_count"] == 3
    assert summary["fine_resolved_row_count"] == 3
    assert summary["alignment_counts"]["aligned"] >= 2
    assert summary["transition_pair_counts"] == {}
    assert summary["unexpected_transition_pair_counts"] == {}
    nas_replay = replay.loc[replay["symbol"] == "NAS100"].reset_index(drop=True)
    assert nas_replay.iloc[-1]["runtime_scene_transition_from"] == "unresolved"


def test_build_checkpoint_scene_sanity_splits_trade_path_when_leg_changes() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T13:00:00+09:00",
                "symbol": "NAS100",
                "trade_link_key": "trade-2",
                "leg_id": "leg-a",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "bars_since_leg_start": 18,
                "position_side": "BUY",
                "unrealized_pnl_state": "FLAT",
                "current_profit": 0.0,
                "mfe_since_entry": 0.10,
                "mae_since_entry": 0.0,
                "giveback_ratio": 0.99,
                "runtime_continuation_odds": 0.551,
                "runtime_reversal_odds": 0.824,
                "runtime_hold_quality_score": 0.25233,
                "runtime_partial_exit_ev": 0.47856,
                "runtime_full_exit_risk": 0.71,
                "runtime_rebuy_readiness": 0.12,
                "runtime_score_reason": "continuation_hold_surface::balanced_checkpoint_state",
            },
            {
                "generated_at": "2026-04-10T13:05:00+09:00",
                "symbol": "NAS100",
                "trade_link_key": "trade-2",
                "leg_id": "leg-b",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "runtime_continuation_odds": 0.74,
                "runtime_reversal_odds": 0.44,
                "runtime_hold_quality_score": 0.50,
                "runtime_partial_exit_ev": 0.35,
                "runtime_full_exit_risk": 0.20,
                "runtime_rebuy_readiness": 0.42,
                "runtime_score_reason": "continuation_hold_surface::continuation_hold_bias",
                "setup_reason": "breakout retest reclaim hold",
                "observe_action": "BUY",
                "observe_side": "BUY",
            },
        ]
    )

    _, summary, replay = build_checkpoint_scene_sanity(frame)

    assert "time_decay_risk->breakout_retest_hold" not in summary["transition_pair_counts"]
    assert "time_decay_risk->breakout_retest_hold" not in summary["unexpected_transition_pair_counts"]
    nas_replay = replay.loc[replay["symbol"] == "NAS100"].reset_index(drop=True)
    assert nas_replay.iloc[1]["runtime_scene_transition_from"] == "unresolved"


def test_build_checkpoint_scene_sanity_tracks_watchlist_transition_separately() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T13:00:00+09:00",
                "symbol": "NAS100",
                "trade_link_key": "trade-3",
                "leg_id": "leg-z",
                "runtime_scene_coarse_family": "ENTRY_INITIATION",
                "runtime_scene_fine_label": "breakout_retest_hold",
                "runtime_scene_gate_label": "none",
                "runtime_scene_source": "manual_resolution",
                "runtime_scene_confidence_band": "high",
                "runtime_scene_maturity": "confirmed",
            },
            {
                "generated_at": "2026-04-10T13:05:00+09:00",
                "symbol": "NAS100",
                "trade_link_key": "trade-3",
                "leg_id": "leg-z",
                "runtime_scene_coarse_family": "DEFENSIVE_EXIT",
                "runtime_scene_fine_label": "trend_exhaustion",
                "runtime_scene_gate_label": "none",
                "runtime_scene_source": "manual_resolution",
                "runtime_scene_confidence_band": "medium",
                "runtime_scene_maturity": "probable",
            },
        ]
    )

    observation, summary, replay = build_checkpoint_scene_sanity(frame)

    assert summary["transition_pair_counts"]["breakout_retest_hold->trend_exhaustion"] == 1
    assert summary["watchlist_transition_pair_counts"]["breakout_retest_hold->trend_exhaustion"] == 1
    assert summary["unexpected_transition_pair_counts"] == {}
    assert summary["recommended_next_action"] == "keep_watchlist_transition_monitoring_before_sa3"
    nas_row = observation.loc[observation["symbol"] == "NAS100"].iloc[0]
    assert nas_row["watchlist_transition_count"] == 1
    assert nas_row["unexpected_transition_count"] == 0
    assert nas_row["recommended_focus"] == "monitor_nas100_watchlist_scene_transitions"
