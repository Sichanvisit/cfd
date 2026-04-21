from backend.services.path_checkpoint_scoring import (
    apply_checkpoint_scores_to_runtime_row,
    build_passive_checkpoint_scores,
)


def test_build_passive_checkpoint_scores_favors_continuation_on_reclaim_follow_through() -> None:
    payload = build_passive_checkpoint_scores(
        symbol="BTCUSD",
        runtime_row={
            "observe_action": "BUY",
            "observe_side": "BUY",
            "entry_candidate_bridge_action": "BUY",
            "blocked_by": "active_action_conflict_guard",
        },
        checkpoint_row={
            "symbol": "BTCUSD",
            "surface_name": "follow_through_surface",
            "leg_direction": "UP",
            "checkpoint_type": "RECLAIM_CHECK",
            "bars_since_last_checkpoint": 1,
            "position_side": "BUY",
            "position_size_fraction": 0.5,
            "unrealized_pnl_state": "OPEN_PROFIT",
            "runner_secured": True,
            "mfe_since_entry": 12.0,
            "mae_since_entry": 2.0,
        },
    )

    row = payload["row"]
    assert row["runtime_continuation_odds"] > row["runtime_reversal_odds"]
    assert row["runtime_hold_quality_score"] >= 0.5
    assert "continuation" in row["runtime_score_reason"] or "reentry" in row["runtime_score_reason"]


def test_build_passive_checkpoint_scores_raises_full_exit_risk_for_protective_loss() -> None:
    payload = build_passive_checkpoint_scores(
        symbol="XAUUSD",
        runtime_row={
            "observe_action": "SELL",
            "observe_side": "SELL",
            "blocked_by": "protective_exit fast_cut adverse_reject",
        },
        checkpoint_row={
            "symbol": "XAUUSD",
            "surface_name": "protective_exit_surface",
            "leg_direction": "UP",
            "checkpoint_type": "LATE_TREND_CHECK",
            "bars_since_last_checkpoint": 3,
            "position_side": "BUY",
            "position_size_fraction": 1.0,
            "unrealized_pnl_state": "OPEN_LOSS",
            "runner_secured": False,
            "mfe_since_entry": 1.0,
            "mae_since_entry": 9.0,
        },
    )

    row = payload["row"]
    assert row["runtime_full_exit_risk"] > row["runtime_hold_quality_score"]
    assert row["runtime_reversal_odds"] > row["runtime_continuation_odds"]
    assert row["runtime_full_exit_risk"] >= 0.6


def test_apply_checkpoint_scores_to_runtime_row_sets_prefixed_fields() -> None:
    runtime_row = apply_checkpoint_scores_to_runtime_row(
        {"symbol": "NAS100"},
        {
            "runtime_continuation_odds": 0.61,
            "runtime_reversal_odds": 0.27,
            "runtime_hold_quality_score": 0.59,
            "runtime_partial_exit_ev": 0.42,
            "runtime_full_exit_risk": 0.31,
            "runtime_rebuy_readiness": 0.55,
            "runtime_score_reason": "follow_through_surface::continuation_hold_bias",
        },
    )

    assert runtime_row["checkpoint_runtime_continuation_odds"] == 0.61
    assert runtime_row["checkpoint_runtime_full_exit_risk"] == 0.31
    assert runtime_row["path_checkpoint_scoring_contract_version"] == "path_checkpoint_scoring_v1"
