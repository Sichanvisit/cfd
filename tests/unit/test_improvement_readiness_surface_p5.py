from __future__ import annotations

from pathlib import Path

from backend.services.improvement_readiness_surface import (
    build_improvement_readiness_surface,
    build_pnl_readiness_digest_lines,
)


def test_readiness_surface_marks_pa8_focus_as_concentrated_near_sample_floor(tmp_path: Path) -> None:
    payload = build_improvement_readiness_surface(
        phase="RUNNING",
        degraded_components=[],
        runtime_status_detail_payload={},
        pa8_payload={
            "summary": {
                "active_symbol_count": 1,
                "live_observation_ready_count": 0,
                "recommended_next_action": "wait_for_more_live_rows",
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "live_observation_ready": False,
                    "observed_window_row_count": 24,
                    "active_trigger_count": 1,
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "first_window_status": "PENDING",
                    "recommended_next_action": "wait_for_more_live_rows",
                }
            ],
        },
        pa9_handoff_payload={
            "summary": {
                "handoff_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                "recommended_next_action": "wait_for_pa8_closeout",
                "prepared_symbol_count": 0,
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "handoff_review_candidate": False,
                    "handoff_apply_candidate": False,
                    "live_observation_ready": False,
                    "observed_window_row_count": 24,
                    "sample_floor": 30,
                    "active_trigger_count": 1,
                    "closeout_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                    "closeout_recommended_next_action": "wait_for_pa8_closeout",
                }
            ],
        },
        now_ts="2026-04-12T10:07:00+09:00",
    )

    focus_surface = payload["pa8_closeout_focus_surface"]
    assert focus_surface["focus_status"] == "CONCENTRATED"
    assert focus_surface["primary_focus_symbol"] == "BTCUSD"
    assert focus_surface["concentrated_symbol_count"] == 1
    assert focus_surface["recommended_next_action"].startswith(
        "concentrate_closeout_monitoring_on_btcusd"
    )


def test_readiness_digest_lines_include_first_symbol_and_pa7_narrow_review() -> None:
    lines = build_pnl_readiness_digest_lines(
        {
            "pa8_closeout_surface": {
                "readiness_status": "PENDING_EVIDENCE",
                "ready_symbol_count": 1,
                "active_symbol_count": 3,
            },
            "pa8_closeout_focus_surface": {
                "focus_status": "CONCENTRATED",
                "focus_symbol_count": 1,
                "watchlist_symbol_count": 1,
                "primary_focus_symbol": "BTCUSD",
            },
            "first_symbol_closeout_handoff_surface": {
                "observation_status": "READY_FOR_CLOSEOUT_REVIEW",
                "primary_symbol": "BTCUSD",
                "observation_stage": "PA8_CLOSEOUT",
            },
            "pa9_handoff_surface": {
                "readiness_status": "READY_FOR_REVIEW",
                "ready_for_review_symbol_count": 1,
                "ready_for_apply_symbol_count": 0,
            },
            "pa7_narrow_review_surface": {
                "status": "REVIEW_NEEDED",
                "group_count": 2,
                "primary_symbol": "BTCUSD",
            },
            "reverse_surface": {
                "readiness_status": "BLOCKED",
                "pending_symbol_count": 0,
                "blocked_symbol_count": 1,
                "ready_symbol_count": 0,
            },
            "historical_cost_surface": {
                "confidence_level": "LOW",
                "recent_safe_trade_count": 4,
                "recent_trade_count": 9,
            },
        }
    )

    joined = "\n".join(lines)
    assert "PA8 closeout: PENDING_EVIDENCE" in joined
    assert "PA8 focus: CONCENTRATED" in joined
    assert "first symbol: READY_FOR_CLOSEOUT_REVIEW (BTCUSD / PA8_CLOSEOUT)" in joined
    assert "PA9 handoff: READY_FOR_REVIEW" in joined
    assert "PA7 narrow review: REVIEW_NEEDED (remaining 2 / primary BTCUSD)" in joined
    assert "reverse readiness: BLOCKED" in joined
    assert "historical cost: LOW" in joined


def test_readiness_surface_surfaces_first_symbol_and_pa7_narrow_review_lane() -> None:
    payload = build_improvement_readiness_surface(
        phase="RUNNING",
        degraded_components=[],
        pa8_payload={
            "summary": {
                "active_symbol_count": 1,
                "live_observation_ready_count": 0,
                "recommended_next_action": "wait_for_more_live_rows",
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "live_observation_ready": False,
                    "observed_window_row_count": 24,
                    "active_trigger_count": 1,
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "first_window_status": "PENDING",
                    "recommended_next_action": "wait_for_more_live_rows",
                }
            ],
        },
        pa9_handoff_payload={
            "summary": {
                "handoff_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                "recommended_next_action": "wait_for_pa8_closeout",
                "prepared_symbol_count": 0,
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "handoff_review_candidate": False,
                    "handoff_apply_candidate": False,
                    "live_observation_ready": False,
                    "observed_window_row_count": 24,
                    "sample_floor": 30,
                    "active_trigger_count": 1,
                    "closeout_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                    "closeout_recommended_next_action": "wait_for_pa8_closeout",
                }
            ],
        },
        pa7_review_processor_payload={
            "summary": {
                "recommended_next_action": "inspect_mixed_wait_boundary_groups",
            },
            "group_rows": [
                {
                    "group_key": "BTCUSD | follow_through_surface | INITIAL_PUSH | active_open_loss | active_open_loss | WAIT",
                    "symbol": "BTCUSD",
                    "review_disposition": "mixed_wait_boundary_review",
                    "review_reason": "group_clusters_around_wait_boundary_but_current_policy_still_disagrees",
                    "row_count": 3,
                    "avg_abs_current_profit": 0.43,
                    "resolved_baseline_action_label": "WAIT",
                    "policy_replay_action_label": "WAIT",
                    "hindsight_best_management_action_label": "WAIT",
                },
                {
                    "group_key": "BTCUSD | follow_through_surface | FIRST_PULLBACK_CHECK | open_loss_protective | open_loss_protective | WAIT",
                    "symbol": "BTCUSD",
                    "review_disposition": "mixed_review",
                    "review_reason": "group_contains_mixed_confidence_or_partial_alignment_signals",
                    "row_count": 2,
                    "avg_abs_current_profit": 0.22,
                    "resolved_baseline_action_label": "WAIT",
                    "policy_replay_action_label": "WAIT",
                    "hindsight_best_management_action_label": "WAIT",
                },
            ],
        },
        now_ts="2026-04-13T00:30:00+09:00",
    )

    assert payload["summary"]["first_symbol_closeout_handoff_status"] == "CONCENTRATED"
    assert payload["summary"]["first_symbol_closeout_handoff_symbol"] == "BTCUSD"
    assert payload["first_symbol_closeout_handoff_surface"]["observation_stage"] == "PA8_CLOSEOUT"
    assert payload["summary"]["pa7_narrow_review_status"] == "REVIEW_NEEDED"
    assert payload["summary"]["pa7_narrow_review_group_count"] == 2
    assert payload["pa7_narrow_review_surface"]["primary_symbol"] == "BTCUSD"
    assert (
        payload["pa7_narrow_review_surface"]["recommended_next_action"]
        == "review_remaining_mixed_wait_boundary_groups_before_first_closeout"
    )


def test_readiness_surface_marks_pa7_narrow_review_lane_clear_when_only_resolved_groups_remain() -> None:
    payload = build_improvement_readiness_surface(
        phase="RUNNING",
        degraded_components=[],
        pa7_review_processor_payload={
            "summary": {
                "recommended_next_action": "record_resolved_by_current_policy_groups_and_continue_pa7",
            },
            "group_rows": [
                {
                    "group_key": "BTCUSD | protective_exit_surface | RECLAIM_CHECK | active_open_loss | active_open_loss | WAIT",
                    "symbol": "BTCUSD",
                    "review_disposition": "resolved_by_current_policy",
                }
            ],
        },
        now_ts="2026-04-13T00:32:00+09:00",
    )

    assert payload["summary"]["pa7_narrow_review_status"] == "CLEAR"
    assert payload["summary"]["pa7_narrow_review_group_count"] == 0
    assert payload["pa7_narrow_review_surface"]["primary_group_key"] == ""
