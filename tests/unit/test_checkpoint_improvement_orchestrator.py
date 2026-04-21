from __future__ import annotations

from pathlib import Path

from backend.services.checkpoint_improvement_orchestrator import (
    CheckpointImprovementOrchestratorLoop,
    run_checkpoint_improvement_orchestrator_tick,
)
from backend.services.event_bus import EventBus, GovernanceActionNeeded
from backend.services.system_state_manager import SystemStateManager
from backend.services.telegram_approval_bridge import TelegramApprovalBridge
from backend.services.telegram_state_store import TelegramStateStore


def test_orchestrator_tick_runs_cycles_in_order_and_builds_board_twice(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T17:00:00+09:00",
    )
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    bus = EventBus()
    bridge = TelegramApprovalBridge(
        telegram_state_store=store,
        event_bus=bus,
    )
    calls: list[str] = []

    def _light(**_: object) -> dict[str, object]:
        calls.append("light")
        return {"summary": {"trigger_state": "LIGHT_CYCLE_REFRESHED", "row_delta": 30}}

    def _governance(**_: object) -> dict[str, object]:
        calls.append("governance")
        return {"summary": {"trigger_state": "GOVERNANCE_NO_ACTION_NEEDED"}}

    def _heavy(**_: object) -> dict[str, object]:
        calls.append("heavy")
        return {"summary": {"trigger_state": "HEAVY_CYCLE_REFRESHED"}}

    def _board(**_: object) -> dict[str, object]:
        calls.append("board")
        board_count = calls.count("board")
        return {
            "summary": {
                "phase": "RUNNING",
                "blocking_reason": "none",
                "next_required_action": "continue_checkpoint_improvement_watch_cycles",
                "pending_approval_count": 0,
                "held_approval_count": 0,
                "approved_apply_backlog_count": 0,
                "reconcile_backlog_count": 0,
                "active_pa8_symbol_count": 0,
                "live_window_ready_count": 0,
            },
            "health_state": {"degraded_components": [], "telegram_healthy": True},
            "watch_state": {
                "cycle_name": "heavy" if board_count == 1 else "reconcile",
                "trigger_state": "HEAVY_CYCLE_REFRESHED",
            },
            "orchestrator_contract": {
                "phase": "RUNNING",
                "phase_allows_progress": True,
                "reconcile_signal": False,
                "approval_backlog_count": 0,
                "apply_backlog_count": 0,
                "reconcile_backlog_count": 0,
                "blocking_reason": "none",
                "next_required_action": "continue_checkpoint_improvement_watch_cycles",
                "degraded_components": [],
                "telegram_healthy": True,
                "watch_cycle_name": "reconcile",
                "watch_trigger_state": "RECONCILE_PLACEHOLDER_REFRESHED",
                "active_pa8_symbol_count": 0,
                "live_window_ready_count": 0,
            },
        }

    def _reconcile(**_: object) -> dict[str, object]:
        calls.append("reconcile")
        return {"summary": {"trigger_state": "RECONCILE_PLACEHOLDER_REFRESHED"}}

    payload = run_checkpoint_improvement_orchestrator_tick(
        system_state_manager=manager,
        telegram_state_store=store,
        event_bus=bus,
        telegram_approval_bridge=bridge,
        light_cycle_runner=_light,
        governance_cycle_runner=_governance,
        heavy_cycle_runner=_heavy,
        master_board_builder=_board,
        reconcile_cycle_runner=_reconcile,
        now_ts="2026-04-11T17:05:00+09:00",
        report_path=tmp_path / "orchestrator.json",
        markdown_path=tmp_path / "orchestrator.md",
    )

    assert calls == ["light", "governance", "heavy", "board", "reconcile", "board"]
    assert payload["summary"]["trigger_state"] == "ORCHESTRATOR_TICK_COMPLETED"
    assert payload["summary"]["total_drained_event_count"] == 0
    assert (tmp_path / "orchestrator.json").exists()
    assert (tmp_path / "orchestrator.md").exists()


def test_orchestrator_tick_routes_governance_event_into_pending_group(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T17:00:00+09:00",
    )
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    bus = EventBus()
    bridge = TelegramApprovalBridge(
        telegram_state_store=store,
        event_bus=bus,
    )

    def _light(**_: object) -> dict[str, object]:
        return {"summary": {"trigger_state": "LIGHT_CYCLE_REFRESHED", "row_delta": 25}}

    def _governance(**kwargs: object) -> dict[str, object]:
        event_bus = kwargs["event_bus"]
        event_bus.publish(
            GovernanceActionNeeded(
                trace_id="trace-gov-1",
                occurred_at="2026-04-11T17:05:00+09:00",
                payload={
                    "review_type": "CANARY_ACTIVATION_REVIEW",
                    "governance_action": "activation_review",
                    "scope_key": "BTCUSD::action_only_canary::activation",
                    "symbol": "BTCUSD",
                    "activation_apply_state": "HOLD_CANARY_ACTIVATION_APPLY",
                    "closeout_state": "",
                    "first_window_status": "AWAIT_FIRST_CANARY_WINDOW_RESULTS",
                    "live_observation_ready": False,
                    "observed_window_row_count": 0,
                    "active_trigger_count": 1,
                    "recommended_next_action": "review_canary_candidate_in_ops_console",
                },
            )
        )
        return {"summary": {"trigger_state": "GOVERNANCE_CANDIDATES_EMITTED"}}

    def _heavy(**_: object) -> dict[str, object]:
        return {"summary": {"trigger_state": "SKIP_WATCH_DECISION"}}

    def _board(**_: object) -> dict[str, object]:
        groups = store.list_check_groups(limit=1000)
        pending_count = sum(1 for group in groups if group["status"] == "pending")
        return {
            "summary": {
                "phase": "RUNNING",
                "blocking_reason": "approval_backlog_pending" if pending_count else "none",
                "next_required_action": "process_pending_or_held_governance_reviews_in_telegram" if pending_count else "continue_checkpoint_improvement_watch_cycles",
                "pending_approval_count": pending_count,
                "held_approval_count": 0,
                "approved_apply_backlog_count": 0,
                "reconcile_backlog_count": 0,
                "active_pa8_symbol_count": 1,
                "live_window_ready_count": 0,
            },
            "health_state": {"degraded_components": [], "telegram_healthy": True},
            "watch_state": {"cycle_name": "governance", "trigger_state": "GOVERNANCE_CANDIDATES_EMITTED"},
            "orchestrator_contract": {
                "phase": "RUNNING",
                "phase_allows_progress": True,
                "reconcile_signal": False,
                "approval_backlog_count": pending_count,
                "apply_backlog_count": 0,
                "reconcile_backlog_count": 0,
                "blocking_reason": "approval_backlog_pending" if pending_count else "none",
                "next_required_action": "process_pending_or_held_governance_reviews_in_telegram" if pending_count else "continue_checkpoint_improvement_watch_cycles",
                "degraded_components": [],
                "telegram_healthy": True,
                "watch_cycle_name": "governance",
                "watch_trigger_state": "GOVERNANCE_CANDIDATES_EMITTED",
                "active_pa8_symbol_count": 1,
                "live_window_ready_count": 0,
            },
        }

    def _reconcile(**_: object) -> dict[str, object]:
        return {"summary": {"trigger_state": "SKIP_WATCH_DECISION"}}

    payload = run_checkpoint_improvement_orchestrator_tick(
        system_state_manager=manager,
        telegram_state_store=store,
        event_bus=bus,
        telegram_approval_bridge=bridge,
        light_cycle_runner=_light,
        governance_cycle_runner=_governance,
        heavy_cycle_runner=_heavy,
        master_board_builder=_board,
        reconcile_cycle_runner=_reconcile,
        now_ts="2026-04-11T17:05:00+09:00",
    )

    groups = store.list_check_groups(limit=10)

    assert len(groups) == 1
    assert groups[0]["status"] == "pending"
    assert payload["tick"]["approval_backlog_count"] == 1
    assert payload["summary"]["total_drained_event_count"] >= 1


def test_orchestrator_tick_degrades_on_unexpected_exception(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T17:00:00+09:00",
    )
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    bus = EventBus()
    bridge = TelegramApprovalBridge(
        telegram_state_store=store,
        event_bus=bus,
    )

    def _light(**_: object) -> dict[str, object]:
        return {"summary": {"trigger_state": "LIGHT_CYCLE_REFRESHED", "row_delta": 25}}

    def _governance(**_: object) -> dict[str, object]:
        return {"summary": {"trigger_state": "GOVERNANCE_NO_ACTION_NEEDED"}}

    def _heavy(**_: object) -> dict[str, object]:
        raise RuntimeError("heavy_crash")

    payload = run_checkpoint_improvement_orchestrator_tick(
        system_state_manager=manager,
        telegram_state_store=store,
        event_bus=bus,
        telegram_approval_bridge=bridge,
        light_cycle_runner=_light,
        governance_cycle_runner=_governance,
        heavy_cycle_runner=_heavy,
        now_ts="2026-04-11T17:05:00+09:00",
        report_path=tmp_path / "orchestrator.json",
        markdown_path=tmp_path / "orchestrator.md",
    )

    assert payload["summary"]["trigger_state"] == "WATCH_ERROR"
    assert manager.get_state()["phase"] == "DEGRADED"
    assert (tmp_path / "orchestrator.json").exists()


def test_orchestrator_loop_instance_runs_tick(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    loop = CheckpointImprovementOrchestratorLoop(
        system_state_manager=manager,
        telegram_state_store=store,
        light_cycle_runner=lambda **_: {"summary": {"trigger_state": "SKIP_WATCH_DECISION", "row_delta": 0}},
        governance_cycle_runner=lambda **_: {"summary": {"trigger_state": "SKIP_WATCH_DECISION"}},
        heavy_cycle_runner=lambda **_: {"summary": {"trigger_state": "SKIP_WATCH_DECISION"}},
        master_board_builder=lambda **_: {
            "summary": {
                "phase": "STARTING",
                "blocking_reason": "none",
                "next_required_action": "continue_checkpoint_improvement_watch_cycles",
                "pending_approval_count": 0,
                "held_approval_count": 0,
                "approved_apply_backlog_count": 0,
                "reconcile_backlog_count": 0,
                "active_pa8_symbol_count": 0,
                "live_window_ready_count": 0,
            },
            "health_state": {"degraded_components": [], "telegram_healthy": True},
            "watch_state": {"cycle_name": "light", "trigger_state": "SKIP_WATCH_DECISION"},
            "orchestrator_contract": {
                "phase": "STARTING",
                "phase_allows_progress": True,
                "reconcile_signal": False,
                "approval_backlog_count": 0,
                "apply_backlog_count": 0,
                "reconcile_backlog_count": 0,
                "blocking_reason": "none",
                "next_required_action": "continue_checkpoint_improvement_watch_cycles",
                "degraded_components": [],
                "telegram_healthy": True,
                "watch_cycle_name": "light",
                "watch_trigger_state": "SKIP_WATCH_DECISION",
                "active_pa8_symbol_count": 0,
                "live_window_ready_count": 0,
            },
        },
        reconcile_cycle_runner=lambda **_: {"summary": {"trigger_state": "SKIP_WATCH_DECISION"}},
    )

    payload = loop.run_tick(
        now_ts="2026-04-11T17:05:00+09:00",
        report_path=tmp_path / "orchestrator.json",
        markdown_path=tmp_path / "orchestrator.md",
    )

    assert payload["summary"]["trigger_state"] == "ORCHESTRATOR_TICK_COMPLETED"
