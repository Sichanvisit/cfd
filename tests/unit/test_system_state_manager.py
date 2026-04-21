from __future__ import annotations

import json
from datetime import datetime

import pytest

from backend.services.system_state_manager import (
    SystemStateManager,
)


def test_system_state_manager_bootstraps_default_state_when_file_missing(tmp_path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")

    state = manager.get_state()

    assert state["phase"] == "STARTING"
    assert state["row_count_since_boot"] == 0
    assert state["telegram_healthy"] is True
    assert set(state["pa8_symbols"]) == {"BTCUSD", "XAUUSD", "NAS100"}
    assert state["pa8_symbols"]["BTCUSD"]["canary_active"] is False


def test_system_state_manager_persists_transition_and_reloads_state(tmp_path) -> None:
    path = tmp_path / "system_state.json"
    manager = SystemStateManager(state_path=path)

    transitioned = manager.transition("RUNNING", reason="hot_path_ready")

    assert transitioned["phase"] == "RUNNING"
    assert transitioned["last_transition_reason"] == "hot_path_ready"
    assert path.exists()

    reloaded = SystemStateManager(state_path=path).get_state()
    assert reloaded["phase"] == "RUNNING"
    assert reloaded["last_transition_reason"] == "hot_path_ready"


def test_system_state_manager_rejects_invalid_transition(tmp_path) -> None:
    path = tmp_path / "system_state.json"
    manager = SystemStateManager(state_path=path)
    manager.transition("RUNNING", reason="ready")
    manager.transition("EMERGENCY", reason="db_failure")

    with pytest.raises(ValueError, match="invalid_phase_transition::EMERGENCY->RUNNING"):
        manager.transition("RUNNING", reason="not_allowed_direct_recovery")


def test_system_state_manager_records_row_and_cycle_updates(tmp_path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")

    state = manager.record_row_observation(
        last_row_ts="2026-04-11T10:00:00+09:00",
        row_count_increment=3,
    )
    state = manager.mark_cycle_run("light", run_at="2026-04-11T10:01:00+09:00")
    state = manager.mark_cycle_run("governance", run_at="2026-04-11T10:02:00+09:00")
    state = manager.mark_cycle_run("reconcile", run_at="2026-04-11T10:03:00+09:00")

    assert state["last_row_ts"] == "2026-04-11T10:00:00+09:00"
    assert state["row_count_since_boot"] == 3
    assert state["light_last_run"] == "2026-04-11T10:01:00+09:00"
    assert state["governance_last_run"] == "2026-04-11T10:02:00+09:00"
    assert state["reconcile_last_run"] == "2026-04-11T10:03:00+09:00"


def test_system_state_manager_updates_pa8_symbols_and_telegram_health(tmp_path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")

    state = manager.set_pa8_symbol_state("nas100", canary_active=True, live_window_ready=False)
    state = manager.set_telegram_health(False, error="telegram_poll_timeout")

    assert state["pa8_symbols"]["NAS100"]["canary_active"] is True
    assert state["pa8_symbols"]["NAS100"]["live_window_ready"] is False
    assert state["telegram_healthy"] is False
    assert state["last_error"] == "telegram_poll_timeout"


def test_system_state_manager_normalizes_partial_existing_snapshot(tmp_path) -> None:
    path = tmp_path / "system_state.json"
    path.write_text(
        json.dumps(
            {
                "phase": "RUNNING",
                "row_count_since_boot": 5,
                "pa8_symbols": {"BTCUSD": {"canary_active": True}},
                "telegram_healthy": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    state = SystemStateManager(state_path=path).get_state()

    assert state["phase"] == "RUNNING"
    assert state["row_count_since_boot"] == 5
    assert state["pa8_symbols"]["BTCUSD"]["canary_active"] is True
    assert state["pa8_symbols"]["BTCUSD"]["live_window_ready"] is False
    assert state["pa8_symbols"]["XAUUSD"]["canary_active"] is False
    assert state["telegram_healthy"] is False


def test_system_state_manager_accepts_datetime_row_timestamp(tmp_path) -> None:
    manager = SystemStateManager(state_path=tmp_path / "system_state.json")

    state = manager.record_row_observation(
        last_row_ts=datetime.fromisoformat("2026-04-11T10:00:00+09:00"),
        row_count_increment=1,
    )

    assert state["last_row_ts"].startswith("2026-04-11T10:00:00")
