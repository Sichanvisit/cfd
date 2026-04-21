from __future__ import annotations

from pathlib import Path

from backend.services.checkpoint_improvement_recovery_health import (
    build_checkpoint_improvement_recovery_health,
)
from backend.services.system_state_manager import SystemStateManager


def _board(
    *,
    phase: str = "RUNNING",
    blocking_reason: str = "none",
    next_required_action: str = "continue_checkpoint_improvement_orchestrator_ticks",
    pending: int = 0,
    held: int = 0,
    approved: int = 0,
    reconcile_backlog: int = 0,
    degraded_components: list[str] | None = None,
    generated_at: str = "2026-04-11T18:00:00+09:00",
) -> dict[str, object]:
    return {
        "summary": {
            "generated_at": generated_at,
            "phase": phase,
            "blocking_reason": blocking_reason,
            "next_required_action": next_required_action,
            "pending_approval_count": pending,
            "held_approval_count": held,
            "approved_apply_backlog_count": approved,
            "reconcile_backlog_count": reconcile_backlog,
        },
        "health_state": {
            "degraded_components": degraded_components or [],
            "telegram_healthy": True,
            "last_error": "",
        },
    }


def _orchestrator(
    *,
    trigger_state: str = "ORCHESTRATOR_TICK_COMPLETED",
    generated_at: str = "2026-04-11T18:00:00+09:00",
) -> dict[str, object]:
    return {
        "summary": {
            "generated_at": generated_at,
            "trigger_state": trigger_state,
            "recommended_next_action": "continue_checkpoint_improvement_orchestrator_ticks",
            "phase_after": "RUNNING",
        },
        "tick": {
            "light_trigger_state": "LIGHT_CYCLE_REFRESHED",
            "governance_trigger_state": "SKIP_WATCH_DECISION",
            "heavy_trigger_state": "SKIP_WATCH_DECISION",
            "reconcile_trigger_state": "SKIP_WATCH_DECISION",
        },
    }


def test_recovery_health_reports_green_continue_for_running_system(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T18:00:00+09:00",
    )

    payload = build_checkpoint_improvement_recovery_health(
        system_state_manager=manager,
        master_board_payload=_board(),
        orchestrator_payload=_orchestrator(),
        output_json_path=tmp_path / "health.json",
        output_markdown_path=tmp_path / "health.md",
        now_ts="2026-04-11T18:05:00+09:00",
    )

    assert payload["summary"]["overall_status"] == "GREEN"
    assert payload["summary"]["recovery_state"] == "HEALTHY_CONTINUE"
    assert payload["recovery_state"]["retry_recommended"] is False
    assert (tmp_path / "health.json").exists()
    assert (tmp_path / "health.md").exists()


def test_recovery_health_reports_wait_for_live_window_without_degrading(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T18:00:00+09:00",
    )

    payload = build_checkpoint_improvement_recovery_health(
        system_state_manager=manager,
        master_board_payload=_board(
            blocking_reason="pa8_live_window_pending",
            next_required_action="wait_for_live_first_window_rows_and_refresh_canary_board",
        ),
        orchestrator_payload=_orchestrator(),
        output_json_path=tmp_path / "health.json",
        output_markdown_path=tmp_path / "health.md",
        now_ts="2026-04-11T18:05:00+09:00",
    )

    assert payload["summary"]["overall_status"] == "GREEN"
    assert payload["summary"]["recovery_state"] == "WAIT_FOR_PA8_LIVE_WINDOW"
    assert payload["recovery_state"]["operator_action_required"] is False


def test_recovery_health_reports_wait_for_new_pa8_rows_when_runtime_is_flat(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T18:00:00+09:00",
    )

    payload = build_checkpoint_improvement_recovery_health(
        system_state_manager=manager,
        master_board_payload=_board(
            blocking_reason="pa8_live_window_pending",
            next_required_action="wait_for_new_pa8_candidate_rows_or_market_reopen",
        ),
        orchestrator_payload=_orchestrator(),
        output_json_path=tmp_path / "health.json",
        output_markdown_path=tmp_path / "health.md",
        now_ts="2026-04-11T18:05:00+09:00",
    )

    assert payload["summary"]["overall_status"] == "GREEN"
    assert payload["summary"]["recovery_state"] == "WAIT_FOR_PA8_LIVE_WINDOW"
    assert (
        payload["recovery_state"]["recovery_reason"]
        == "keep_runner_active_and_wait_for_new_pa8_candidate_rows_or_market_reopen"
    )


def test_recovery_health_reports_retry_for_degraded_watch_state(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "DEGRADED",
        reason="orchestrator_tick_error::RuntimeError",
        occurred_at="2026-04-11T18:00:00+09:00",
    )

    payload = build_checkpoint_improvement_recovery_health(
        system_state_manager=manager,
        master_board_payload=_board(
            phase="DEGRADED",
            blocking_reason="dependency_degraded",
            degraded_components=["watch:heavy"],
        ),
        orchestrator_payload=_orchestrator(trigger_state="WATCH_ERROR"),
        output_json_path=tmp_path / "health.json",
        output_markdown_path=tmp_path / "health.md",
        now_ts="2026-04-11T18:05:00+09:00",
    )

    assert payload["summary"]["overall_status"] == "YELLOW"
    assert payload["summary"]["recovery_state"] == "RETRY_ORCHESTRATOR_NEXT_TICK"
    assert payload["recovery_state"]["retry_recommended"] is True


def test_recovery_health_reports_escalation_for_emergency_phase(tmp_path: Path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "EMERGENCY",
        reason="hot_path_unhealthy",
        occurred_at="2026-04-11T18:00:00+09:00",
    )

    payload = build_checkpoint_improvement_recovery_health(
        system_state_manager=manager,
        master_board_payload=_board(
            phase="EMERGENCY",
            blocking_reason="system_phase_emergency",
        ),
        orchestrator_payload=_orchestrator(),
        output_json_path=tmp_path / "health.json",
        output_markdown_path=tmp_path / "health.md",
        now_ts="2026-04-11T18:05:00+09:00",
    )

    assert payload["summary"]["overall_status"] == "RED"
    assert payload["summary"]["recovery_state"] == "ESCALATE_OPERATOR_ACTION"
    assert payload["recovery_state"]["operator_action_required"] is True
