from __future__ import annotations

from pathlib import Path

from backend.services.checkpoint_improvement_orchestrator_watch_runner import (
    CheckpointImprovementOrchestratorWatchRunner,
)
from backend.services.system_state_manager import SystemStateManager


class _FakeLoop:
    def __init__(self, manager: SystemStateManager) -> None:
        self.system_state_manager = manager
        self.run_tick_calls = 0

    def run_tick(self, *, now_ts: object | None = None) -> dict[str, object]:
        self.run_tick_calls += 1
        return {
            "summary": {
                "trigger_state": "ORCHESTRATOR_TICK_COMPLETED",
                "recommended_next_action": "continue_checkpoint_improvement_orchestrator_ticks",
                "phase_after": "RUNNING",
                "generated_at": str(now_ts or ""),
            },
            "tick": {},
        }


def _health_builder(**_: object) -> dict[str, object]:
    return {
        "summary": {
            "overall_status": "GREEN",
            "recovery_state": "HEALTHY_CONTINUE",
            "recommended_next_action": "continue_checkpoint_improvement_orchestrator_ticks",
            "blocking_reason": "none",
        }
    }


def _p5_builder(**_: object) -> dict[str, object]:
    return {
        "summary": {
            "trigger_state": "NO_P5_5_EVENT",
            "recommended_next_action": "continue_observing_first_symbol_closeout_handoff",
            "first_symbol_status": "WATCHLIST",
            "first_symbol_symbol": "BTCUSD",
            "pa7_narrow_review_status": "CLEAR",
        }
    }


def _focus_builder(**_: object) -> dict[str, object]:
    return {
        "summary": {
            "trigger_state": "FIRST_SYMBOL_PROGRESS_STABLE",
            "symbol": "BTCUSD",
            "status": "WATCHLIST",
            "progress_pct": 20.0,
            "progress_delta_pct": 0.0,
            "progress_bucket": "EARLY",
        }
    }


def _pa7_builder(**_: object) -> dict[str, object]:
    return {
        "summary": {
            "trigger_state": "PA7_NARROW_REVIEW_ANALYZED",
            "status": "REVIEW_NEEDED",
            "group_count": 2,
            "primary_symbol": "BTCUSD",
            "recommended_next_action": "review_remaining_mixed_wait_boundary_groups_before_first_closeout",
        }
    }


def _pa8_fill_builder(**_: object) -> dict[str, object]:
    return {
        "summary": {
            "trigger_state": "PA8_LIVE_WINDOW_FILL_REFRESHED",
            "overall_fill_state": "ACTIVE_FILL",
            "primary_focus_symbol": "NAS100",
            "ready_for_review_count": 0,
            "rollback_pending_count": 0,
            "active_fill_count": 2,
            "recommended_next_action": "continue_accumulating_post_activation_live_rows_until_sample_floor",
        }
    }


def _pa8_cleanup_builder(**_: object) -> dict[str, object]:
    return {
        "summary": {
            "trigger_state": "PA8_ROLLBACK_APPROVAL_CLEANUP_REFRESHED",
            "overall_cleanup_state": "ROLLBACK_APPROVAL_PENDING",
            "primary_cleanup_symbol": "NAS100",
            "approval_backlog_count": 1,
            "rollback_approval_pending_count": 1,
            "closeout_review_candidate_count": 0,
            "recommended_next_action": "review_pending_pa8_canary_rollback_prompt_in_telegram",
        }
    }


def test_watch_runner_executes_orchestrator_cycle_when_runtime_gate_is_open(tmp_path: Path) -> None:
    runtime_status_path = tmp_path / "runtime_status.json"
    runtime_status_path.write_text("{}", encoding="utf-8")
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    manager.transition(
        "RUNNING",
        reason="light_cycle_first_refresh_completed",
        occurred_at="2026-04-11T18:00:00+09:00",
    )
    loop = _FakeLoop(manager)
    runner = CheckpointImprovementOrchestratorWatchRunner(
        orchestrator_loop=loop,  # type: ignore[arg-type]
        recovery_health_builder=_health_builder,
        p5_observation_builder=_p5_builder,
        first_symbol_focus_builder=_focus_builder,
        pa7_narrow_review_builder=_pa7_builder,
        pa8_live_window_fill_builder=_pa8_fill_builder,
        pa8_rollback_approval_cleanup_builder=_pa8_cleanup_builder,
        runtime_status_path=runtime_status_path,
    )

    payload = runner.run_cycle(
        cycle_index=1,
        require_runtime_fresh=True,
        runtime_max_age_sec=180.0,
        now_ts="2026-04-11T18:05:00+09:00",
        report_path=tmp_path / "watch.json",
        markdown_path=tmp_path / "watch.md",
    )

    assert loop.run_tick_calls == 1
    assert payload["summary"]["trigger_state"] == "ORCHESTRATOR_TICK_COMPLETED"
    assert payload["summary"]["overall_health_status"] == "GREEN"
    assert payload["summary"]["p5_trigger_state"] == "NO_P5_5_EVENT"
    assert payload["summary"]["first_symbol_focus_trigger_state"] == "FIRST_SYMBOL_PROGRESS_STABLE"
    assert payload["summary"]["pa7_narrow_review_trigger_state"] == "PA7_NARROW_REVIEW_ANALYZED"
    assert payload["summary"]["pa8_live_window_fill_trigger_state"] == "PA8_LIVE_WINDOW_FILL_REFRESHED"
    assert (
        payload["summary"]["pa8_rollback_cleanup_trigger_state"]
        == "PA8_ROLLBACK_APPROVAL_CLEANUP_REFRESHED"
    )
    assert (tmp_path / "watch.json").exists()
    assert (tmp_path / "watch.md").exists()


def test_watch_runner_skips_orchestrator_tick_when_runtime_status_is_stale(tmp_path: Path) -> None:
    runtime_status_path = tmp_path / "runtime_status.json"
    runtime_status_path.write_text("{}", encoding="utf-8")
    old_time = 1_000_000_000
    runtime_status_path.touch()
    import os

    os.utime(runtime_status_path, (old_time, old_time))

    manager = SystemStateManager(state_path=tmp_path / "system_state.json")
    loop = _FakeLoop(manager)
    runner = CheckpointImprovementOrchestratorWatchRunner(
        orchestrator_loop=loop,  # type: ignore[arg-type]
        recovery_health_builder=_health_builder,
        p5_observation_builder=_p5_builder,
        first_symbol_focus_builder=_focus_builder,
        pa7_narrow_review_builder=_pa7_builder,
        pa8_live_window_fill_builder=_pa8_fill_builder,
        pa8_rollback_approval_cleanup_builder=_pa8_cleanup_builder,
        runtime_status_path=runtime_status_path,
    )

    payload = runner.run_cycle(
        cycle_index=1,
        require_runtime_fresh=True,
        runtime_max_age_sec=10.0,
        now_ts="2026-04-11T18:05:00+09:00",
        report_path=tmp_path / "watch.json",
        markdown_path=tmp_path / "watch.md",
    )

    assert loop.run_tick_calls == 0
    assert payload["summary"]["trigger_state"] == "RUNTIME_STATUS_STALE_WAIT"
    assert payload["runtime_gate"]["fresh"] is False
