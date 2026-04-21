from __future__ import annotations

import pandas as pd

from backend.services.path_checkpoint_pa8_historical_replay import (
    build_checkpoint_pa8_historical_replay_board,
    render_checkpoint_pa8_historical_replay_board_markdown,
)


def test_render_checkpoint_pa8_historical_replay_board_markdown_contains_rows() -> None:
    markdown = render_checkpoint_pa8_historical_replay_board_markdown(
        {
            "summary": {
                "symbol_count": 3,
                "replay_ready_count": 2,
                "closeout_preview_state_counts": {"READY_FOR_PA9_REPLAY_PREVIEW": 2},
                "recommended_next_action": "use_replay_as_supporting_evidence_and_wait_for_live_window",
                "caveat": "historical_replay_does_not_replace_true_post_activation_live_observation",
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "candidate_action": "PARTIAL_THEN_HOLD",
                    "preview_changed_row_count": 82,
                    "sample_floor": 50,
                    "replay_window_row_count": 50,
                    "replay_window_first_generated_at": "2026-04-10T09:00:00+09:00",
                    "replay_window_last_generated_at": "2026-04-10T11:00:00+09:00",
                    "replay_action_precision": 0.94,
                    "replay_runtime_proxy_match_rate": 0.96,
                    "replay_worsened_rows": 0,
                    "replay_ready": True,
                    "closeout_preview_state": "READY_FOR_PA9_REPLAY_PREVIEW",
                    "recommended_next_action": "treat_replay_as_supporting_evidence_only_and_wait_for_live_window",
                }
            ],
        }
    )

    assert "# PA8 Historical Replay Board" in markdown
    assert "### NAS100" in markdown
    assert "- replay_window_row_count: `50`" in markdown
    assert "- replay_window_last_generated_at: `2026-04-10T11:00:00+09:00`" in markdown


def test_build_checkpoint_pa8_historical_replay_board_has_three_rows() -> None:
    payload = build_checkpoint_pa8_historical_replay_board(pd.DataFrame())

    assert payload["summary"]["symbol_count"] == 3
    assert len(payload["rows"]) == 3
    assert payload["summary"]["recommended_next_action"] == "use_replay_as_supporting_evidence_and_wait_for_live_window"
