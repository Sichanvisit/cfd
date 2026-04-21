from __future__ import annotations

import json
from pathlib import Path

from backend.services.checkpoint_improvement_master_board import (
    build_checkpoint_improvement_master_board,
)
from backend.services.system_state_manager import SystemStateManager
from backend.services.telegram_state_store import TelegramStateStore


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_master_board_promotes_pa8_focus_next_action_when_closeout_is_concentrated(
    tmp_path: Path,
) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-12T10:00:00+09:00",
    )

    watch_path = tmp_path / "watch.json"
    pa8_path = tmp_path / "pa8.json"
    pa78_path = tmp_path / "pa78.json"
    pa9_handoff_path = tmp_path / "pa9_handoff.json"
    pa9_review_path = tmp_path / "pa9_review.json"
    pa9_apply_path = tmp_path / "pa9_apply.json"

    _write_json(
        watch_path,
        {
            "summary": {
                "cycle_name": "governance",
                "trigger_state": "GOVERNANCE_NO_ACTION_NEEDED",
                "recommended_next_action": "keep_canaries_running_until_review_candidates_appear",
                "generated_at": "2026-04-12T10:01:00+09:00",
            }
        },
    )
    _write_json(
        pa8_path,
        {
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
    )
    _write_json(pa78_path, {"summary": {"pa7_unresolved_review_group_count": 0}})
    _write_json(
        pa9_handoff_path,
        {
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
    )
    _write_json(
        pa9_review_path,
        {"summary": {"review_state": "HOLD_PENDING_PA8_LIVE_WINDOW", "recommended_next_action": "wait_for_pa8_closeout"}},
    )
    _write_json(
        pa9_apply_path,
        {"summary": {"apply_state": "HOLD_PENDING_PA8_LIVE_WINDOW", "recommended_next_action": "wait_for_pa8_closeout"}},
    )

    payload = build_checkpoint_improvement_master_board(
        system_state_manager=manager,
        telegram_state_store=TelegramStateStore(db_path=tmp_path / "telegram_hub.db"),
        watch_report_path=watch_path,
        pa8_board_path=pa8_path,
        pa78_review_packet_path=pa78_path,
        pa9_handoff_packet_path=pa9_handoff_path,
        pa9_review_packet_path=pa9_review_path,
        pa9_apply_packet_path=pa9_apply_path,
        output_json_path=tmp_path / "master_board.json",
        output_markdown_path=tmp_path / "master_board.md",
        now_ts="2026-04-12T10:02:00+09:00",
    )

    assert payload["summary"]["blocking_reason"] == "pa8_live_window_pending"
    assert payload["summary"]["pa8_closeout_focus_status"] == "CONCENTRATED"
    assert payload["summary"]["pa8_primary_focus_symbol"] == "BTCUSD"
    assert payload["summary"]["next_required_action"].startswith(
        "concentrate_closeout_monitoring_on_btcusd"
    )
    assert payload["readiness_state"]["pa8_closeout_focus_status"] == "CONCENTRATED"
    assert payload["readiness_state"]["pa8_closeout_focus_surface"]["concentrated_symbol_count"] == 1


def test_master_board_surfaces_first_symbol_and_pa7_narrow_review_lane(
    tmp_path: Path,
) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-13T00:30:00+09:00",
    )

    watch_path = tmp_path / "watch.json"
    pa8_path = tmp_path / "pa8.json"
    pa78_path = tmp_path / "pa78.json"
    pa7_processor_path = tmp_path / "pa7_processor.json"
    pa9_handoff_path = tmp_path / "pa9_handoff.json"
    pa9_review_path = tmp_path / "pa9_review.json"
    pa9_apply_path = tmp_path / "pa9_apply.json"

    _write_json(
        watch_path,
        {
            "summary": {
                "cycle_name": "governance",
                "trigger_state": "GOVERNANCE_NO_ACTION_NEEDED",
                "recommended_next_action": "keep_canaries_running_until_review_candidates_appear",
                "generated_at": "2026-04-13T00:31:00+09:00",
            }
        },
    )
    _write_json(
        pa8_path,
        {
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
    )
    _write_json(pa78_path, {"summary": {"pa7_unresolved_review_group_count": 0}})
    _write_json(
        pa7_processor_path,
        {
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
    )
    _write_json(
        pa9_handoff_path,
        {
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
    )
    _write_json(
        pa9_review_path,
        {"summary": {"review_state": "HOLD_PENDING_PA8_LIVE_WINDOW", "recommended_next_action": "wait_for_pa8_closeout"}},
    )
    _write_json(
        pa9_apply_path,
        {"summary": {"apply_state": "HOLD_PENDING_PA8_LIVE_WINDOW", "recommended_next_action": "wait_for_pa8_closeout"}},
    )

    payload = build_checkpoint_improvement_master_board(
        system_state_manager=manager,
        telegram_state_store=TelegramStateStore(db_path=tmp_path / "telegram_hub.db"),
        watch_report_path=watch_path,
        pa8_board_path=pa8_path,
        pa78_review_packet_path=pa78_path,
        pa7_review_processor_path=pa7_processor_path,
        pa9_handoff_packet_path=pa9_handoff_path,
        pa9_review_packet_path=pa9_review_path,
        pa9_apply_packet_path=pa9_apply_path,
        output_json_path=tmp_path / "master_board.json",
        output_markdown_path=tmp_path / "master_board.md",
        now_ts="2026-04-13T00:32:00+09:00",
    )

    assert payload["summary"]["first_symbol_closeout_handoff_status"] == "CONCENTRATED"
    assert payload["summary"]["first_symbol_closeout_handoff_symbol"] == "BTCUSD"
    assert payload["summary"]["pa7_narrow_review_status"] == "REVIEW_NEEDED"
    assert payload["summary"]["pa7_narrow_review_group_count"] == 2
    assert payload["readiness_state"]["first_symbol_closeout_handoff_stage"] == "PA8_CLOSEOUT"
    assert (
        payload["readiness_state"]["pa7_narrow_review_next_required_action"]
        == "review_remaining_mixed_wait_boundary_groups_before_first_closeout"
    )
    assert payload["pa_state"]["pa7_narrow_review_primary_group_key"].startswith("BTCUSD |")


def test_master_board_prefers_narrow_pa7_clear_over_raw_pa78_backlog(
    tmp_path: Path,
) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-13T01:10:00+09:00",
    )

    watch_path = tmp_path / "watch.json"
    pa8_path = tmp_path / "pa8.json"
    pa78_path = tmp_path / "pa78.json"
    pa7_processor_path = tmp_path / "pa7_processor.json"
    pa9_handoff_path = tmp_path / "pa9_handoff.json"
    pa9_review_path = tmp_path / "pa9_review.json"
    pa9_apply_path = tmp_path / "pa9_apply.json"

    _write_json(
        watch_path,
        {
            "summary": {
                "cycle_name": "governance",
                "trigger_state": "GOVERNANCE_NO_ACTION_NEEDED",
                "recommended_next_action": "keep_canaries_running_until_review_candidates_appear",
                "generated_at": "2026-04-13T01:11:00+09:00",
            }
        },
    )
    _write_json(
        pa8_path,
        {
            "summary": {
                "active_symbol_count": 1,
                "live_observation_ready_count": 0,
                "recommended_next_action": "wait_for_more_live_rows",
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "live_observation_ready": False,
                    "observed_window_row_count": 0,
                    "active_trigger_count": 1,
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "first_window_status": "PENDING",
                    "recommended_next_action": "wait_for_more_live_rows",
                }
            ],
        },
    )
    _write_json(pa78_path, {"summary": {"pa7_unresolved_review_group_count": 2, "recommended_next_action": "inspect_mixed_wait_boundary_groups"}})
    _write_json(
        pa7_processor_path,
        {
            "summary": {
                "recommended_next_action": "record_resolved_by_current_policy_groups_and_continue_pa7",
            },
            "group_rows": [],
        },
    )
    _write_json(
        pa9_handoff_path,
        {
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
                    "observed_window_row_count": 0,
                    "sample_floor": 30,
                    "active_trigger_count": 1,
                    "closeout_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                    "closeout_recommended_next_action": "wait_for_pa8_closeout",
                }
            ],
        },
    )
    _write_json(
        pa9_review_path,
        {"summary": {"review_state": "HOLD_PENDING_PA8_LIVE_WINDOW", "recommended_next_action": "wait_for_pa8_closeout"}},
    )
    _write_json(
        pa9_apply_path,
        {"summary": {"apply_state": "HOLD_PENDING_PA8_LIVE_WINDOW", "recommended_next_action": "wait_for_pa8_closeout"}},
    )

    payload = build_checkpoint_improvement_master_board(
        system_state_manager=manager,
        telegram_state_store=TelegramStateStore(db_path=tmp_path / "telegram_hub.db"),
        watch_report_path=watch_path,
        pa8_board_path=pa8_path,
        pa78_review_packet_path=pa78_path,
        pa7_review_processor_path=pa7_processor_path,
        pa9_handoff_packet_path=pa9_handoff_path,
        pa9_review_packet_path=pa9_review_path,
        pa9_apply_packet_path=pa9_apply_path,
        output_json_path=tmp_path / "master_board.json",
        output_markdown_path=tmp_path / "master_board.md",
        now_ts="2026-04-13T01:12:00+09:00",
    )

    assert payload["summary"]["pa7_narrow_review_status"] == "CLEAR"
    assert payload["summary"]["pa7_narrow_review_group_count"] == 0
    assert payload["summary"]["blocking_reason"] == "pa8_live_window_pending"
