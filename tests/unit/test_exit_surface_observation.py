from pathlib import Path

from backend.services.exit_surface_observation import (
    build_exit_surface_observation_v1,
)


def test_exit_surface_observation_builds_runner_and_protective_counts(tmp_path: Path):
    open_path = tmp_path / "trade_history.csv"
    closed_path = tmp_path / "trade_closed_history.csv"

    open_path.write_text(
        "\n".join(
            [
                "ticket,symbol,status,exit_reason,policy_scope,exit_policy_stage,exit_wait_decision_family,exit_wait_bridge_status",
                "1001,XAUUSD,OPEN,,EXIT_SURFACE_CONTINUATION,continuation_hold_surface,PARTIAL_REDUCE,Runner Preserve",
                "1002,BTCUSD,OPEN,,EXIT_SURFACE_CONTINUATION,continuation_hold_surface,HOLD_RUNNER,Runner Preserve",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    closed_path.write_text(
        "\n".join(
            [
                "ticket,symbol,status,close_time,exit_reason,policy_scope,exit_policy_stage,exit_wait_decision_family,exit_wait_bridge_status",
                "2001,NAS100,CLOSED,2026-04-09 02:00:00,Protect Exit,EXIT_SURFACE_PROTECTIVE,protective_exit_surface,EXIT_PROTECT,Protect Exit",
                "2002,XAUUSD,CLOSED,2026-04-09 02:01:00,Target,EXIT_SURFACE_PROTECTIVE,protective_exit_surface,LOCK_PROFIT,Target",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_exit_surface_observation_v1(
        open_trades_path=open_path,
        closed_trades_path=closed_path,
        recent_limit=10,
    )

    assert payload["status"] == "runner_preservation_observed"
    assert payload["runner_preservation_total_count"] == 2
    assert payload["runner_preservation_live_count"] == 2
    assert payload["protective_surface_total_count"] == 2
    assert payload["surface_state_counts"]["PARTIAL_REDUCE"] == 1
    assert payload["surface_state_counts"]["HOLD_RUNNER"] == 1
    assert payload["surface_state_counts"]["EXIT_PROTECT"] == 1
    assert payload["surface_state_counts"]["LOCK_PROFIT"] == 1
