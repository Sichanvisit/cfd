import pandas as pd

from backend.services.path_checkpoint_position_side_observation import (
    build_checkpoint_position_side_observation,
)


def test_build_checkpoint_position_side_observation_summarizes_position_rows() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T14:30:00+09:00",
                "symbol": "NAS100",
                "source": "exit_manage_hold",
                "position_side": "SELL",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": False,
                "giveback_ratio": 0.18,
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "management_action_label": "PARTIAL_THEN_HOLD",
            },
            {
                "generated_at": "2026-04-10T14:31:00+09:00",
                "symbol": "BTCUSD",
                "source": "exit_manage_runner",
                "position_side": "BUY",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": True,
                "giveback_ratio": 0.12,
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "PARTIAL_THEN_HOLD",
            },
            {
                "generated_at": "2026-04-10T14:32:00+09:00",
                "symbol": "XAUUSD",
                "source": "exit_manage_hold",
                "position_side": "BUY",
                "unrealized_pnl_state": "OPEN_LOSS",
                "runner_secured": False,
                "giveback_ratio": 0.66,
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "WAIT",
            },
        ]
    )

    observation, summary = build_checkpoint_position_side_observation(frame)

    assert summary["position_side_row_count"] == 3
    assert summary["open_profit_row_count"] == 2
    assert summary["open_loss_row_count"] == 1
    assert summary["runner_secured_row_count"] == 1
    assert summary["live_runner_source_row_count"] == 1
    assert summary["hold_candidate_row_count"] == 2
    assert summary["full_exit_candidate_row_count"] == 1
    assert summary["giveback_heavy_row_count"] == 1
    assert summary["family_counts"]["active_open_loss"] == 1
    assert summary["recommended_next_action"] == "rebuild_pa5_dataset_with_richer_exit_manage_rows"
    assert int(observation.loc[observation["symbol"] == "BTCUSD", "live_runner_source_row_count"].iloc[0]) == 1
    assert set(observation["symbol"]) == {"BTCUSD", "NAS100", "XAUUSD"}
