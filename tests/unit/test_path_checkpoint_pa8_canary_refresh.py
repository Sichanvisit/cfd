from __future__ import annotations

import pandas as pd

from backend.services.path_checkpoint_pa8_canary_refresh import (
    build_checkpoint_pa8_canary_refresh_board,
    render_checkpoint_pa8_canary_refresh_board_markdown,
)


def test_render_checkpoint_pa8_canary_refresh_board_markdown_contains_rows() -> None:
    markdown = render_checkpoint_pa8_canary_refresh_board_markdown(
        {
            "summary": {
                "active_symbol_count": 3,
                "live_observation_ready_count": 0,
                "closeout_state_counts": {"HOLD_CLOSEOUT_PENDING_LIVE_WINDOW": 3},
                "recommended_next_action": "wait_for_market_reopen_and_refresh_canary_windows",
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "live_observation_ready": False,
                    "observed_window_row_count": 0,
                    "active_trigger_count": 0,
                    "recommended_next_action": "wait_for_live_first_window_rows_before_pa8_closeout",
                }
            ],
        }
    )

    assert "# PA8 Canary Refresh Board" in markdown
    assert "### NAS100" in markdown
    assert "- closeout_state: `HOLD_CLOSEOUT_PENDING_LIVE_WINDOW`" in markdown


def test_build_checkpoint_pa8_canary_refresh_board_has_three_rows() -> None:
    frame = pd.DataFrame(columns=["symbol", "generated_at"])
    payload = build_checkpoint_pa8_canary_refresh_board(frame)

    assert payload["summary"]["active_symbol_count"] == 3
    assert len(payload["rows"]) == 3
