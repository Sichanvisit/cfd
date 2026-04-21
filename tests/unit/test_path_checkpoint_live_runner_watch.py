import pandas as pd

from backend.services.path_checkpoint_live_runner_watch import (
    build_checkpoint_live_runner_watch,
)


def test_build_checkpoint_live_runner_watch_summarizes_live_runner_rows() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T15:56:00+09:00",
                "symbol": "BTCUSD",
                "source": "exit_manage_runner",
                "outcome": "runner_hold",
                "blocked_by": "runner_observe:no_exit",
            },
            {
                "generated_at": "2026-04-10T15:57:00+09:00",
                "symbol": "NAS100",
                "source": "exit_manage_runner",
                "outcome": "runner_hold",
                "blocked_by": "runner_observe:recovery_wait_hold",
            },
            {
                "generated_at": "2026-04-10T15:57:30+09:00",
                "symbol": "XAUUSD",
                "source": "exit_manage_hold",
                "outcome": "hold",
                "blocked_by": "no_exit",
            },
        ]
    )

    rows, summary = build_checkpoint_live_runner_watch(
        {"updated_at": "2026-04-10T15:58:00+09:00"},
        frame,
        previous_summary={"live_runner_source_row_count": 1},
        recent_minutes=60,
    )

    assert summary["live_runner_source_row_count"] == 2
    assert summary["live_runner_hold_row_count"] == 2
    assert summary["live_runner_source_delta"] == 1
    assert summary["last_live_runner_symbol"] == "NAS100"
    assert summary["recommended_next_action"] == "inspect_new_live_runner_rows_and_rebuild_pa5_artifacts"
    assert set(rows["symbol"]) == {"BTCUSD", "NAS100", "XAUUSD"}


def test_build_checkpoint_live_runner_watch_handles_no_live_runner_rows() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T15:57:30+09:00",
                "symbol": "XAUUSD",
                "source": "exit_manage_hold",
                "outcome": "hold",
                "blocked_by": "no_exit",
            },
        ]
    )

    rows, summary = build_checkpoint_live_runner_watch(
        {"updated_at": "2026-04-10T15:58:00+09:00"},
        frame,
        previous_summary={"live_runner_source_row_count": 0},
        recent_minutes=60,
    )

    assert summary["live_runner_source_row_count"] == 0
    assert summary["recommended_next_action"] == "keep_runtime_running_until_exit_manage_runner_rows_appear"
    assert int(rows.loc[rows["symbol"] == "BTCUSD", "live_runner_source_row_count"].iloc[0]) == 0
