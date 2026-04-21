from __future__ import annotations

import json
from pathlib import Path

from backend.services.checkpoint_improvement_master_board import (
    build_checkpoint_improvement_master_board,
    extract_checkpoint_improvement_orchestrator_contract,
)
from backend.services.system_state_manager import SystemStateManager
from backend.services.telegram_state_store import TelegramStateStore


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_master_board_builds_from_state_artifacts_and_store(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T13:00:00+09:00",
    )
    manager.record_row_observation(
        last_row_ts="2026-04-11T13:02:00+09:00",
        row_count_increment=120,
    )
    manager.mark_cycle_run("light", run_at="2026-04-11T13:03:00+09:00")
    manager.mark_cycle_run("governance", run_at="2026-04-11T13:04:00+09:00")
    manager.set_pa8_symbol_state("BTCUSD", canary_active=True, live_window_ready=False)

    watch_path = tmp_path / "watch.json"
    pa8_path = tmp_path / "pa8.json"
    pa78_path = tmp_path / "pa78.json"
    pa9_handoff_path = tmp_path / "pa9_handoff.json"
    pa9_review_path = tmp_path / "pa9_review.json"
    pa9_apply_path = tmp_path / "pa9_apply.json"
    board_path = tmp_path / "master_board.json"
    markdown_path = tmp_path / "master_board.md"
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    _write_json(
        watch_path,
        {
            "summary": {
                "cycle_name": "governance",
                "trigger_state": "GOVERNANCE_NO_ACTION_NEEDED",
                "recommended_next_action": "keep_canaries_running_until_review_candidates_appear",
                "generated_at": "2026-04-11T13:05:00+09:00",
            }
        },
    )
    _write_json(
        pa8_path,
        {
            "summary": {
                "active_symbol_count": 3,
                "live_observation_ready_count": 1,
                "recommended_next_action": "wait_for_market_reopen_and_refresh_canary_windows",
            },
            "rows": [],
        },
    )
    _write_json(
        pa78_path,
        {
            "summary": {
                "pa7_unresolved_review_group_count": 0,
                "pa7_review_state": "REVIEW_PACKET_PROCESSED",
                "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                "recommended_next_action": "prepare_pa8_action_baseline_review_and_keep_scene_bias_preview_only",
            }
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
                    "active_trigger_count": 0,
                    "closeout_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                    "closeout_recommended_next_action": "wait_for_pa8_closeout",
                }
            ],
        },
    )
    _write_json(
        pa9_review_path,
        {
            "summary": {
                "review_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                "recommended_next_action": "wait_for_pa8_closeout",
            }
        },
    )
    _write_json(
        pa9_apply_path,
        {
            "summary": {
                "apply_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                "recommended_next_action": "wait_for_pa8_closeout",
            }
        },
    )

    pending_group = store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::activation",
        status="pending",
        symbol="BTCUSD",
        review_type="CANARY_ACTIVATION_REVIEW",
        scope_key="BTCUSD::action_only_canary::activation",
        first_event_ts="2026-04-11T12:55:00+09:00",
        last_event_ts="2026-04-11T12:55:00+09:00",
        decision_deadline_ts="2026-04-11T13:10:00+09:00",
        pending_count=1,
    )
    applied_group = store.upsert_check_group(
        group_key="NAS100::action_only_canary::closeout",
        status="applied",
        symbol="NAS100",
        review_type="CANARY_CLOSEOUT_REVIEW",
        scope_key="NAS100::action_only_canary::closeout",
        first_event_ts="2026-04-11T12:30:00+09:00",
        last_event_ts="2026-04-11T12:58:00+09:00",
        pending_count=0,
    )

    assert pending_group["group_id"] != applied_group["group_id"]

    payload = build_checkpoint_improvement_master_board(
        system_state_manager=manager,
            telegram_state_store=store,
            watch_report_path=watch_path,
            pa8_board_path=pa8_path,
            pa78_review_packet_path=pa78_path,
            pa9_handoff_packet_path=pa9_handoff_path,
            pa9_review_packet_path=pa9_review_path,
            pa9_apply_packet_path=pa9_apply_path,
            output_json_path=board_path,
            output_markdown_path=markdown_path,
            now_ts="2026-04-11T13:05:00+09:00",
    )

    assert payload["summary"]["blocking_reason"] == "approval_backlog_pending"
    assert (
        payload["summary"]["next_required_action"]
        == "process_pending_or_held_governance_reviews_in_telegram"
    )
    assert payload["summary"]["field_policy_version"] == "improvement_board_field_policy_v1"
    assert payload["summary"]["pending_approval_count"] == 1
    assert payload["summary"]["approved_apply_backlog_count"] == 0
    assert payload["summary"]["pa8_closeout_readiness_status"] == "PENDING_EVIDENCE"
    assert payload["summary"]["pa8_closeout_focus_status"] == "PENDING_EVIDENCE"
    assert payload["summary"]["pa9_handoff_readiness_status"] == "PENDING_EVIDENCE"
    assert payload["summary"]["historical_cost_confidence_level"] == "LIMITED"
    assert payload["summary"]["oldest_pending_approval_age_sec"] == 600
    assert payload["summary"]["last_successful_apply_ts"] == "2026-04-11T12:58:00+09:00"
    assert payload["readiness_state"]["pa8_closeout_blocking_reason"] == "live_window_pending"
    assert payload["readiness_state"]["pa8_closeout_focus_next_required_action"] == "wait_for_market_reopen_and_refresh_canary_windows"
    assert payload["readiness_state"]["historical_cost_blocking_reason"] == "historical_cost_limited"
    assert payload["readiness_state"]["pa8_closeout_surface"]["active_symbol_count"] == 3
    assert payload["readiness_state"]["pa8_closeout_surface"]["pending_symbol_count"] == 2
    assert payload["readiness_state"]["pa8_closeout_focus_surface"]["focus_status"] == "PENDING_EVIDENCE"
    assert payload["readiness_state"]["pa9_handoff_surface"]["pending_symbol_count"] == 1
    assert payload["readiness_state"]["reverse_surface"]["pending_symbol_count"] == 0
    assert payload["approval_state"]["group_status_counts"]["pending"] == 1
    assert payload["approval_state"]["group_status_counts"]["applied"] == 1
    assert payload["artifacts"]["readiness_surface_path"] == str(
        (tmp_path / "improvement_readiness_surface_latest.json").resolve()
    )
    assert payload["artifacts"]["readiness_surface_markdown_path"] == str(
        (tmp_path / "improvement_readiness_surface_latest.md").resolve()
    )
    contract = extract_checkpoint_improvement_orchestrator_contract(payload)
    assert contract["approval_backlog_count"] == 1
    assert contract["apply_backlog_count"] == 0
    assert contract["blocking_reason"] == "approval_backlog_pending"
    assert board_path.exists()
    assert markdown_path.exists()
    assert (tmp_path / "improvement_readiness_surface_latest.json").exists()
    assert (tmp_path / "improvement_readiness_surface_latest.md").exists()


def test_master_board_prioritizes_degraded_phase_and_lists_components(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "DEGRADED",
        reason="heavy_cycle_error::RuntimeError",
        occurred_at="2026-04-11T14:00:00+09:00",
    )
    manager.set_telegram_health(False, error="telegram_poll_error")
    watch_path = tmp_path / "watch.json"
    pa8_path = tmp_path / "pa8.json"
    pa78_path = tmp_path / "pa78.json"

    _write_json(
        watch_path,
        {
            "summary": {
                "cycle_name": "heavy",
                "trigger_state": "WATCH_ERROR",
                "recommended_next_action": "inspect_watch_error_and_retry_heavy_cycle",
                "generated_at": "2026-04-11T14:01:00+09:00",
            }
        },
    )
    _write_json(
        pa8_path,
        {"summary": {"active_symbol_count": 0, "live_observation_ready_count": 0}},
    )
    _write_json(pa78_path, {"summary": {"pa7_unresolved_review_group_count": 0}})
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    payload = build_checkpoint_improvement_master_board(
        system_state_manager=manager,
        telegram_state_store=store,
        watch_report_path=watch_path,
        pa8_board_path=pa8_path,
        pa78_review_packet_path=pa78_path,
        output_json_path=tmp_path / "master_board.json",
        output_markdown_path=tmp_path / "master_board.md",
        now_ts="2026-04-11T14:02:00+09:00",
    )

    degraded_components = payload["summary"]["degraded_components"]
    assert payload["summary"]["blocking_reason"] == "system_phase_degraded"
    assert (
        payload["summary"]["next_required_action"]
        == "inspect_degraded_components_and_restore_dependencies"
    )
    assert payload["summary"]["reverse_readiness_status"] == "BLOCKED"
    assert "system_phase:degraded" in degraded_components
    assert "telegram" in degraded_components
    assert "watch:heavy" in degraded_components


def test_master_board_counts_apply_backlog_and_reconcile_backlog(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T15:00:00+09:00",
    )
    watch_path = tmp_path / "watch.json"
    pa8_path = tmp_path / "pa8.json"
    pa78_path = tmp_path / "pa78.json"
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    _write_json(
        watch_path,
        {
            "summary": {
                "cycle_name": "light",
                "trigger_state": "LIGHT_CYCLE_REFRESHED",
                "recommended_next_action": "continue_with_governance_cycle_when_ready",
                "generated_at": "2026-04-11T15:01:00+09:00",
            }
        },
    )
    _write_json(
        pa8_path,
        {
            "summary": {
                "active_symbol_count": 3,
                "live_observation_ready_count": 3,
                "recommended_next_action": "inspect_live_ready_symbol_windows_first",
            }
        },
    )
    _write_json(
        pa78_path,
        {
            "summary": {
                "pa7_unresolved_review_group_count": 0,
                "recommended_next_action": "prepare_pa8_action_baseline_review_and_keep_scene_bias_preview_only",
            }
        },
    )

    store.upsert_check_group(
        group_key="XAUUSD::action_only_canary::closeout",
        status="approved",
        symbol="XAUUSD",
        review_type="CANARY_CLOSEOUT_REVIEW",
        scope_key="XAUUSD::action_only_canary::closeout",
        first_event_ts="2026-04-11T14:40:00+09:00",
        last_event_ts="2026-04-11T14:50:00+09:00",
        decision_deadline_ts="2026-04-11T15:10:00+09:00",
        pending_count=0,
    )
    store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::rollback",
        status="held",
        symbol="BTCUSD",
        review_type="CANARY_ROLLBACK_REVIEW",
        scope_key="BTCUSD::action_only_canary::rollback",
        first_event_ts="2026-04-11T14:30:00+09:00",
        last_event_ts="2026-04-11T14:45:00+09:00",
        decision_deadline_ts="2026-04-11T14:55:00+09:00",
        pending_count=1,
    )
    store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::rollback::dup",
        status="pending",
        symbol="BTCUSD",
        review_type="CANARY_ROLLBACK_REVIEW",
        scope_key="BTCUSD::action_only_canary::rollback",
        first_event_ts="2026-04-11T14:35:00+09:00",
        last_event_ts="2026-04-11T14:50:00+09:00",
        decision_deadline_ts="2026-04-11T15:15:00+09:00",
        pending_count=1,
    )

    payload = build_checkpoint_improvement_master_board(
        system_state_manager=manager,
        telegram_state_store=store,
        watch_report_path=watch_path,
        pa8_board_path=pa8_path,
        pa78_review_packet_path=pa78_path,
        output_json_path=tmp_path / "master_board.json",
        output_markdown_path=tmp_path / "master_board.md",
        now_ts="2026-04-11T15:05:00+09:00",
    )

    assert payload["summary"]["blocking_reason"] == "approved_apply_backlog"
    assert payload["summary"]["approved_apply_backlog_count"] == 1
    assert payload["summary"]["held_approval_count"] == 1
    assert payload["summary"]["pending_approval_count"] == 1
    assert payload["summary"]["same_scope_conflict_count"] == 1
    assert payload["summary"]["reconcile_backlog_count"] == 3
    assert payload["approval_state"]["stale_actionable_count"] == 1
    assert payload["approval_state"]["same_scope_conflict_count"] == 1


def test_master_board_uses_flat_runtime_hint_for_pa8_live_window_pending(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T16:00:00+09:00",
    )
    watch_path = tmp_path / "watch.json"
    pa8_path = tmp_path / "pa8.json"
    pa78_path = tmp_path / "pa78.json"
    runtime_status_path = tmp_path / "runtime_status.json"
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    _write_json(
        watch_path,
        {
            "summary": {
                "cycle_name": "governance",
                "trigger_state": "SKIP_WATCH_DECISION",
                "recommended_next_action": "wait_for_active_canary_rows_or_governance_interval",
                "generated_at": "2026-04-11T16:01:00+09:00",
            }
        },
    )
    _write_json(
        pa8_path,
        {
            "summary": {
                "active_symbol_count": 3,
                "live_observation_ready_count": 0,
                "recommended_next_action": "wait_for_market_reopen_and_refresh_canary_windows",
            }
        },
    )
    _write_json(
        pa78_path,
        {
            "summary": {
                "pa7_unresolved_review_group_count": 0,
                "recommended_next_action": "record_resolved_by_current_policy_groups_and_continue_pa7",
            }
        },
    )
    _write_json(
        runtime_status_path,
        {
            "updated_at": "2026-04-11T16:01:30+09:00",
            "runtime_recycle": {
                "last_open_positions_count": 0,
                "last_owned_open_positions_count": 0,
                "flat_since": "2026-04-11T15:58:00+09:00",
            },
        },
    )

    payload = build_checkpoint_improvement_master_board(
        system_state_manager=manager,
        telegram_state_store=store,
        watch_report_path=watch_path,
        pa8_board_path=pa8_path,
        pa78_review_packet_path=pa78_path,
        runtime_status_path=runtime_status_path,
        output_json_path=tmp_path / "master_board.json",
        output_markdown_path=tmp_path / "master_board.md",
        now_ts="2026-04-11T16:02:00+09:00",
    )

    assert payload["summary"]["blocking_reason"] == "pa8_live_window_pending"
    assert (
        payload["summary"]["next_required_action"]
        == "wait_for_new_pa8_candidate_rows_or_market_reopen"
    )
    assert payload["summary"]["pa8_closeout_readiness_status"] == "PENDING_EVIDENCE"
    assert payload["summary"]["runtime_open_positions_count"] == 0
    assert payload["summary"]["runtime_flat_since"] == "2026-04-11T15:58:00+09:00"
    assert payload["runtime_state"]["open_positions_count"] == 0


def test_master_board_surfaces_pa9_review_ready_state(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T17:00:00+09:00",
    )
    watch_path = tmp_path / "watch.json"
    pa8_path = tmp_path / "pa8.json"
    pa78_path = tmp_path / "pa78.json"
    pa9_handoff_path = tmp_path / "pa9_handoff.json"
    pa9_review_path = tmp_path / "pa9_review.json"
    pa9_apply_path = tmp_path / "pa9_apply.json"
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    _write_json(
        watch_path,
        {
            "summary": {
                "cycle_name": "governance",
                "trigger_state": "GOVERNANCE_NO_ACTION_NEEDED",
                "recommended_next_action": "review_prepared_pa9_action_baseline_handoff_packet",
                "generated_at": "2026-04-11T17:01:00+09:00",
            }
        },
    )
    _write_json(pa8_path, {"summary": {"active_symbol_count": 3, "live_observation_ready_count": 3}})
    _write_json(pa78_path, {"summary": {"pa7_unresolved_review_group_count": 0}})
    _write_json(
        pa9_handoff_path,
        {
            "summary": {
                "handoff_state": "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW",
                "recommended_next_action": "review_prepared_pa9_action_baseline_handoff_packet",
                "prepared_symbol_count": 1,
            }
        },
    )
    _write_json(
        pa9_review_path,
        {
            "summary": {
                "review_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW",
                "recommended_next_action": "review_prepared_pa9_action_baseline_handoff_packet",
            }
        },
    )
    _write_json(
        pa9_apply_path,
        {
            "summary": {
                "apply_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_APPLY_REVIEW",
                "recommended_next_action": "approve_and_apply_pa9_action_baseline_handoff_when_review_is_confirmed",
            }
        },
    )

    payload = build_checkpoint_improvement_master_board(
        system_state_manager=manager,
        telegram_state_store=store,
        watch_report_path=watch_path,
        pa8_board_path=pa8_path,
        pa78_review_packet_path=pa78_path,
        pa9_handoff_packet_path=pa9_handoff_path,
        pa9_review_packet_path=pa9_review_path,
        pa9_apply_packet_path=pa9_apply_path,
        output_json_path=tmp_path / "master_board.json",
        output_markdown_path=tmp_path / "master_board.md",
        now_ts="2026-04-11T17:02:00+09:00",
    )

    assert payload["summary"]["blocking_reason"] == "pa9_handoff_review_ready"
    assert (
        payload["summary"]["next_required_action"]
        == "review_prepared_pa9_action_baseline_handoff_packet"
    )
    assert payload["summary"]["pa9_handoff_readiness_status"] == "READY_FOR_APPLY"
    assert payload["pa_state"]["pa9_handoff_state"] == "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW"
    assert (
        payload["pa_state"]["pa9_review_state"]
        == "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW"
    )
