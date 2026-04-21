from __future__ import annotations

from backend.services.checkpoint_pa8_rollback_approval_cleanup_lane import (
    build_checkpoint_pa8_rollback_approval_cleanup_lane,
    render_checkpoint_pa8_rollback_approval_cleanup_lane_markdown,
)


def test_cleanup_lane_marks_pending_rollback_approval_for_primary_symbol() -> None:
    payload = build_checkpoint_pa8_rollback_approval_cleanup_lane(
        master_board_payload={
            "summary": {
                "pa8_primary_focus_symbol": "NAS100",
            },
            "approval_state": {
                "approval_backlog_count": 1,
                "apply_backlog_count": 0,
                "stale_actionable_count": 0,
                "oldest_pending_approval_age_sec": 3600,
            },
            "readiness_state": {
                "pa8_closeout_surface": {
                    "symbols": [
                        {"symbol": "NAS100"},
                        {"symbol": "BTCUSD"},
                    ]
                }
            },
        },
        pa8_closeout_runtime_payload={
            "review_packet": {
                "summary": {
                    "rollback_required_symbol_count": 1,
                    "review_candidate_symbol_count": 0,
                },
                "rows": [
                    {
                        "symbol": "NAS100",
                        "closeout_state": "ROLLBACK_REQUIRED",
                        "first_window_status": "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE",
                        "live_observation_ready": True,
                        "observed_window_row_count": 3,
                        "sample_floor": 50,
                        "active_trigger_count": 1,
                        "rollback_required": True,
                        "closeout_review_candidate": False,
                        "recommended_next_action": "disable_canary_and_return_to_baseline_action_behavior",
                    },
                    {
                        "symbol": "BTCUSD",
                        "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                        "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                        "live_observation_ready": False,
                        "observed_window_row_count": 0,
                        "sample_floor": 50,
                        "active_trigger_count": 1,
                        "rollback_required": False,
                        "closeout_review_candidate": False,
                        "recommended_next_action": "wait_for_live_first_window_rows_before_pa8_closeout",
                    },
                ],
            },
            "apply_packet": {
                "summary": {
                    "apply_candidate_symbol_count": 0,
                },
                "rows": [],
            },
        },
        actionable_groups=[
            {
                "group_id": 7,
                "status": "pending",
                "review_type": "CANARY_ROLLBACK_REVIEW",
                "symbol": "NAS100",
                "scope_key": "NAS100::action_only_canary::rollback",
                "reason_summary": "NAS100 canary rollback review",
                "decision_deadline_ts": "2026-04-13T20:00:00+09:00",
                "first_event_ts": "2026-04-13T19:00:00+09:00",
            }
        ],
        now_ts="2026-04-13T19:30:00+09:00",
    )

    summary = payload["summary"]
    rows = payload["rows"]

    assert summary["overall_cleanup_state"] == "ROLLBACK_APPROVAL_PENDING"
    assert summary["primary_cleanup_symbol"] == "NAS100"
    assert summary["rollback_approval_pending_count"] == 1
    assert rows[0]["symbol"] == "NAS100"
    assert rows[0]["cleanup_lane_state"] == "ROLLBACK_APPROVAL_PENDING"
    assert rows[0]["primary_review_type"] == "CANARY_ROLLBACK_REVIEW"
    assert rows[1]["cleanup_lane_state"] == "WAITING_LIVE_WINDOW"


def test_cleanup_lane_markdown_renders_groups_and_rows() -> None:
    markdown = render_checkpoint_pa8_rollback_approval_cleanup_lane_markdown(
        {
            "summary": {
                "generated_at": "2026-04-13T19:30:00+09:00",
                "overall_cleanup_state": "ROLLBACK_APPROVAL_PENDING",
                "primary_focus_symbol": "NAS100",
                "primary_cleanup_symbol": "NAS100",
                "approval_backlog_count": 1,
                "relevant_actionable_group_count": 1,
                "rollback_approval_pending_count": 1,
                "closeout_review_candidate_count": 0,
                "recommended_next_action": "review_pending_pa8_canary_rollback_prompt_in_telegram",
            },
            "approval_groups": [
                {
                    "symbol": "NAS100",
                    "review_type": "CANARY_ROLLBACK_REVIEW",
                    "status": "pending",
                    "approval_age_sec": 1800,
                    "reason_summary": "NAS100 canary rollback review",
                }
            ],
            "rows": [
                {
                    "symbol": "NAS100",
                    "cleanup_lane_state": "ROLLBACK_APPROVAL_PENDING",
                    "closeout_state": "ROLLBACK_REQUIRED",
                    "first_window_status": "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE",
                    "live_observation_ready": True,
                    "observed_window_row_count": 3,
                    "approval_group_count": 1,
                    "primary_group_status": "pending",
                    "primary_review_type": "CANARY_ROLLBACK_REVIEW",
                    "approval_age_sec": 1800,
                    "recommended_next_action": "review_pending_pa8_canary_rollback_prompt_in_telegram",
                    "cleanup_reason_ko": "rollback review가 pending 상태입니다.",
                }
            ],
        }
    )

    assert "PA8 Rollback / Approval Cleanup Lane" in markdown
    assert "CANARY_ROLLBACK_REVIEW" in markdown
    assert "approval_backlog_count: `1`" in markdown
    assert "cleanup_lane_state: `ROLLBACK_APPROVAL_PENDING`" in markdown
