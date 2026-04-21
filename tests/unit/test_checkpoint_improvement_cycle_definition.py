from __future__ import annotations

from backend.services.checkpoint_improvement_cycle_definition import (
    active_pa8_symbol_count,
    build_default_cycle_definitions,
    evaluate_cycle_decision,
)


def test_build_default_cycle_definitions_contains_all_cycles() -> None:
    definitions = build_default_cycle_definitions()

    assert set(definitions) == {"light", "heavy", "governance", "reconcile"}
    assert definitions["light"]["row_delta_floor"] == 25
    assert definitions["heavy"]["sample_floor"] == 100
    assert definitions["governance"]["min_interval_seconds"] == 60


def test_active_pa8_symbol_count_counts_only_active_symbols() -> None:
    count = active_pa8_symbol_count(
        {
            "pa8_symbols": {
                "BTCUSD": {"canary_active": True},
                "NAS100": {"canary_active": False},
                "XAUUSD": {"canary_active": True},
            }
        }
    )

    assert count == 2


def test_light_cycle_first_run_is_due_when_rows_exist() -> None:
    decision = evaluate_cycle_decision(
        "light",
        system_state={},
        row_delta=3,
    )

    assert decision["due"] is True
    assert decision["decision_reason"] == "first_cycle_run"


def test_light_cycle_skips_during_cooldown() -> None:
    decision = evaluate_cycle_decision(
        "light",
        system_state={"light_last_run": "2026-04-11T10:00:00+09:00"},
        row_delta=30,
        now_ts="2026-04-11T10:02:00+09:00",
    )

    assert decision["due"] is False
    assert decision["skip_reason"] == "cooldown_active"


def test_governance_cycle_skips_without_active_canary_or_backlog() -> None:
    decision = evaluate_cycle_decision(
        "governance",
        system_state={"pa8_symbols": {"BTCUSD": {"canary_active": False}}},
        row_delta=5,
    )

    assert decision["due"] is False
    assert decision["skip_reason"] == "no_active_canary_or_backlog"


def test_governance_cycle_runs_for_first_active_canary_tick() -> None:
    decision = evaluate_cycle_decision(
        "governance",
        system_state={"pa8_symbols": {"BTCUSD": {"canary_active": True}}},
        row_delta=1,
    )

    assert decision["due"] is True
    assert decision["decision_reason"] == "first_cycle_run"


def test_heavy_cycle_skips_when_hot_path_is_unhealthy() -> None:
    decision = evaluate_cycle_decision(
        "heavy",
        system_state={"heavy_last_run": "2026-04-11T10:00:00+09:00"},
        row_delta=120,
        recent_sample_count=120,
        hot_path_healthy=False,
        now_ts="2026-04-11T10:30:00+09:00",
    )

    assert decision["due"] is False
    assert decision["skip_reason"] == "hot_path_unhealthy"


def test_heavy_cycle_runs_when_sample_and_row_floor_are_met() -> None:
    decision = evaluate_cycle_decision(
        "heavy",
        system_state={"heavy_last_run": "2026-04-11T10:00:00+09:00"},
        row_delta=120,
        recent_sample_count=150,
        hot_path_healthy=True,
        now_ts="2026-04-11T10:20:00+09:00",
    )

    assert decision["due"] is True
    assert decision["decision_reason"] == "row_delta_and_sample_floor_met"


def test_reconcile_cycle_skips_without_signal() -> None:
    decision = evaluate_cycle_decision(
        "reconcile",
        system_state={},
        reconcile_signal=False,
        approval_backlog_count=0,
        apply_backlog_count=0,
    )

    assert decision["due"] is False
    assert decision["skip_reason"] == "no_reconcile_signal"


def test_reconcile_cycle_runs_when_signal_is_present() -> None:
    decision = evaluate_cycle_decision(
        "reconcile",
        system_state={"reconcile_last_run": "2026-04-11T10:00:00+09:00"},
        reconcile_signal=True,
        now_ts="2026-04-11T10:10:00+09:00",
    )

    assert decision["due"] is True
    assert decision["decision_reason"] == "reconcile_signal_detected"
