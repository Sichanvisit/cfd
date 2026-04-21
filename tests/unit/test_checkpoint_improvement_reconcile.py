from __future__ import annotations

import json
from pathlib import Path

from backend.services.checkpoint_improvement_reconcile import (
    run_checkpoint_improvement_reconcile_cycle,
)
from backend.services.event_bus import EventBus, SystemPhaseChanged, WatchError
from backend.services.system_state_manager import SystemStateManager
from backend.services.telegram_state_store import TelegramStateStore


def _write_board(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_reconcile_cycle_skips_without_signal_or_backlog(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T16:00:00+09:00",
    )
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    board_payload = {
        "summary": {
            "phase": "RUNNING",
            "blocking_reason": "none",
            "next_required_action": "continue_checkpoint_improvement_watch_cycles",
            "pending_approval_count": 0,
            "held_approval_count": 0,
            "approved_apply_backlog_count": 0,
            "reconcile_backlog_count": 0,
        },
        "health_state": {"degraded_components": [], "telegram_healthy": True},
        "watch_state": {"cycle_name": "light", "trigger_state": "LIGHT_CYCLE_REFRESHED"},
    }

    payload = run_checkpoint_improvement_reconcile_cycle(
        system_state_manager=manager,
        telegram_state_store=store,
        master_board_payload=board_payload,
        report_path=tmp_path / "reconcile.json",
        markdown_path=tmp_path / "reconcile.md",
        now_ts="2026-04-11T16:05:00+09:00",
    )

    assert payload["summary"]["trigger_state"] == "SKIP_WATCH_DECISION"
    assert payload["cycle_decision"]["skip_reason"] == "no_reconcile_signal"
    assert manager.get_state()["reconcile_last_run"] == ""


def test_reconcile_cycle_marks_run_and_reports_backlog_groups(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T16:00:00+09:00",
    )
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::rollback",
        status="held",
        symbol="BTCUSD",
        review_type="CANARY_ROLLBACK_REVIEW",
        scope_key="BTCUSD::action_only_canary::rollback",
        first_event_ts="2026-04-11T15:30:00+09:00",
        last_event_ts="2026-04-11T15:45:00+09:00",
        decision_deadline_ts="2026-04-11T15:55:00+09:00",
        pending_count=1,
        approval_id="approval-held-1",
    )
    store.upsert_check_group(
        group_key="XAUUSD::action_only_canary::closeout",
        status="approved",
        symbol="XAUUSD",
        review_type="CANARY_CLOSEOUT_REVIEW",
        scope_key="XAUUSD::action_only_canary::closeout",
        first_event_ts="2026-04-11T15:20:00+09:00",
        last_event_ts="2026-04-11T15:50:00+09:00",
        decision_deadline_ts="2026-04-11T16:10:00+09:00",
        pending_count=0,
        approval_id="approval-approved-1",
        apply_job_key="apply-job-1",
    )

    board_payload = {
        "summary": {
            "phase": "RUNNING",
            "blocking_reason": "approved_apply_backlog",
            "next_required_action": "drain_approved_apply_backlog_before_new_governance_reviews",
            "pending_approval_count": 0,
            "held_approval_count": 1,
            "approved_apply_backlog_count": 1,
            "reconcile_backlog_count": 2,
        },
        "health_state": {"degraded_components": [], "telegram_healthy": True},
        "watch_state": {"cycle_name": "governance", "trigger_state": "GOVERNANCE_CANDIDATES_EMITTED"},
    }

    payload = run_checkpoint_improvement_reconcile_cycle(
        system_state_manager=manager,
        telegram_state_store=store,
        master_board_payload=board_payload,
        report_path=tmp_path / "reconcile.json",
        markdown_path=tmp_path / "reconcile.md",
        now_ts="2026-04-11T16:05:00+09:00",
    )

    state = manager.get_state()

    assert payload["summary"]["trigger_state"] == "RECONCILE_PLACEHOLDER_REFRESHED"
    assert state["reconcile_last_run"] == "2026-04-11T16:05:00+09:00"
    assert payload["reconcile_summary"]["stale_actionable_count"] == 1
    assert payload["reconcile_summary"]["approved_not_applied_count"] == 1
    assert (
        payload["summary"]["recommended_next_action"]
        == "inspect_apply_backlog_and_drain_executor_before_new_reviews"
    )


def test_reconcile_cycle_detects_same_scope_conflict_and_late_callback_invalidation(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T16:00:00+09:00",
    )
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    older_group = store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::activation::older",
        status="held",
        symbol="BTCUSD",
        review_type="CANARY_ACTIVATION_REVIEW",
        scope_key="BTCUSD::action_only_canary::activation",
        first_event_ts="2026-04-11T15:20:00+09:00",
        last_event_ts="2026-04-11T15:40:00+09:00",
        decision_deadline_ts="2026-04-11T16:20:00+09:00",
        pending_count=1,
        approval_id="approval-old",
    )
    newer_group = store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::activation::newer",
        status="pending",
        symbol="BTCUSD",
        review_type="CANARY_ACTIVATION_REVIEW",
        scope_key="BTCUSD::action_only_canary::activation",
        first_event_ts="2026-04-11T15:30:00+09:00",
        last_event_ts="2026-04-11T15:55:00+09:00",
        decision_deadline_ts="2026-04-11T16:25:00+09:00",
        pending_count=1,
        approval_id="approval-new",
    )
    store.append_check_action(
        group_id=int(newer_group["group_id"]),
        telegram_user_id="111",
        telegram_username="ops",
        action="approve",
        note="late stale callback",
        callback_query_id="cb-late-1",
        approval_id="approval-stale",
        trace_id="trace-late-1",
    )

    board_payload = {
        "summary": {
            "phase": "RUNNING",
            "blocking_reason": "approval_backlog_pending",
            "next_required_action": "process_pending_or_held_governance_reviews_in_telegram",
            "pending_approval_count": 1,
            "held_approval_count": 1,
            "approved_apply_backlog_count": 0,
            "reconcile_backlog_count": 1,
        },
        "health_state": {"degraded_components": [], "telegram_healthy": True},
        "watch_state": {"cycle_name": "governance", "trigger_state": "GOVERNANCE_CANDIDATES_EMITTED"},
    }

    payload = run_checkpoint_improvement_reconcile_cycle(
        system_state_manager=manager,
        telegram_state_store=store,
        master_board_payload=board_payload,
        report_path=tmp_path / "reconcile.json",
        markdown_path=tmp_path / "reconcile.md",
        now_ts="2026-04-11T16:05:00+09:00",
    )

    older_group_after = store.get_check_group(group_id=int(older_group["group_id"]))

    assert payload["reconcile_summary"]["same_scope_conflict_count"] == 1
    assert payload["reconcile_summary"]["late_callback_invalidation_count"] == 1
    assert payload["reconcile_summary"]["same_scope_resolution_count"] == 1
    assert older_group_after["status"] == "cancelled"
    assert (
        payload["summary"]["recommended_next_action"]
        == "resolve_same_scope_governance_conflicts_before_new_reviews"
    )


def test_reconcile_cycle_degrades_on_master_board_error(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T16:00:00+09:00",
    )
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    bus = EventBus()
    seen_events: list[str] = []
    bus.subscribe(WatchError, lambda event: seen_events.append(event.event_type))
    bus.subscribe(SystemPhaseChanged, lambda event: seen_events.append(event.event_type))

    def _builder(**_: object) -> dict[str, object]:
        raise RuntimeError("board_boom")

    payload = run_checkpoint_improvement_reconcile_cycle(
        system_state_manager=manager,
        telegram_state_store=store,
        event_bus=bus,
        master_board_builder=_builder,
        report_path=tmp_path / "reconcile.json",
        markdown_path=tmp_path / "reconcile.md",
        now_ts="2026-04-11T16:05:00+09:00",
    )

    assert payload["summary"]["trigger_state"] == "WATCH_ERROR"
    assert manager.get_state()["phase"] == "DEGRADED"
    assert bus.pending_count() == 2
    bus.drain()
    assert seen_events == ["WatchError", "SystemPhaseChanged"]
