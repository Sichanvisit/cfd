from __future__ import annotations

from backend.services.checkpoint_pa8_live_window_fill_lane import (
    build_checkpoint_pa8_live_window_fill_lane,
    render_checkpoint_pa8_live_window_fill_lane_markdown,
)


def test_pa8_live_window_fill_lane_builds_priority_and_progress_deltas() -> None:
    payload = build_checkpoint_pa8_live_window_fill_lane(
        master_board_payload={
            "summary": {
                "pa8_primary_focus_symbol": "NAS100",
            },
            "readiness_state": {
                "pa8_closeout_surface": {
                    "symbols": [
                        {
                            "symbol": "NAS100",
                            "closeout_state": "ROLLBACK_REQUIRED",
                            "first_window_status": "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE",
                            "live_observation_ready": True,
                            "observed_window_row_count": 3,
                            "active_trigger_count": 1,
                            "recommended_next_action": "disable_canary_and_return_to_baseline_action_behavior",
                        },
                        {
                            "symbol": "BTCUSD",
                            "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                            "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                            "live_observation_ready": False,
                            "observed_window_row_count": 0,
                            "active_trigger_count": 1,
                            "recommended_next_action": "wait_for_live_first_window_rows_before_pa8_closeout",
                        },
                    ]
                },
                "pa8_closeout_focus_surface": {
                    "primary_focus_symbol": "NAS100",
                    "symbols": [
                        {
                            "symbol": "NAS100",
                            "focus_status": "READY_FOR_REVIEW",
                            "sample_floor": 50,
                            "recommended_next_action": "disable_canary_and_return_to_baseline_action_behavior",
                        },
                        {
                            "symbol": "BTCUSD",
                            "focus_status": "WATCHLIST",
                            "sample_floor": 50,
                            "recommended_next_action": "keep_closeout_watchlist_on_btcusd",
                        },
                    ],
                },
            },
        },
        previous_payload={
            "rows": [
                {
                    "symbol": "NAS100",
                    "observed_window_row_count": 1,
                    "progress_pct": 2.0,
                },
                {
                    "symbol": "BTCUSD",
                    "observed_window_row_count": 0,
                    "progress_pct": 0.0,
                },
            ]
        },
        now_ts="2026-04-13T19:40:00+09:00",
    )

    summary = payload["summary"]
    rows = payload["rows"]
    nas_row = rows[0]
    btc_row = rows[1]

    assert summary["overall_fill_state"] == "ROLLBACK_REVIEW_PENDING"
    assert summary["primary_focus_symbol"] == "NAS100"
    assert summary["rollback_pending_count"] == 1
    assert nas_row["symbol"] == "NAS100"
    assert nas_row["fill_lane_state"] == "ROLLBACK_REVIEW_PENDING"
    assert nas_row["rows_remaining_to_floor"] == 47
    assert nas_row["progress_delta_rows"] == 2
    assert nas_row["velocity_state"] == "GAINING_ROWS"
    assert nas_row["fill_priority_rank"] == 1
    assert btc_row["fill_lane_state"] == "SEEDED_WAITING_ROWS"
    assert btc_row["velocity_state"] == "WAITING_FIRST_ROWS"


def test_pa8_live_window_fill_lane_markdown_renders_symbol_rows() -> None:
    markdown = render_checkpoint_pa8_live_window_fill_lane_markdown(
        {
            "summary": {
                "generated_at": "2026-04-13T19:40:00+09:00",
                "overall_fill_state": "ACTIVE_FILL",
                "primary_focus_symbol": "NAS100",
                "ready_for_review_count": 0,
                "rollback_pending_count": 0,
                "active_fill_count": 1,
                "waiting_first_rows_count": 2,
                "total_rows_remaining_to_floor": 72,
                "recommended_next_action": "continue_accumulating_post_activation_live_rows_until_sample_floor",
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "fill_lane_state": "ACTIVE_FILL",
                    "fill_lane_reason_ko": "live row가 누적 중이라 sample floor까지 계속 채우는 단계입니다.",
                    "observed_window_row_count": 3,
                    "sample_floor": 50,
                    "rows_remaining_to_floor": 47,
                    "progress_pct": 6.0,
                    "progress_delta_rows": 1,
                    "velocity_state": "GAINING_ROWS",
                    "velocity_reason_ko": "직전 스냅샷보다 live row가 늘었습니다.",
                    "active_trigger_count": 1,
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "recommended_next_action": "continue_accumulating_post_activation_live_rows_until_sample_floor",
                }
            ],
        }
    )

    assert "PA8 Live Window Fill Lane" in markdown
    assert "NAS100" in markdown
    assert "rows_remaining_to_floor: `47`" in markdown
    assert "velocity_state: `GAINING_ROWS`" in markdown
