import json
from types import SimpleNamespace

from backend.app.trading_application_runner import (
    _build_symbol_loop_profile,
    _record_symbol_stage_timing,
    _resolve_symbol_loop_profile_path,
    _snapshot_exit_fields,
    _write_symbol_loop_profile,
)


def test_build_symbol_loop_profile_summarizes_dominant_stage():
    profile = _build_symbol_loop_profile(
        loop_count=7,
        symbol="XAUUSD",
        elapsed_sec=4.25,
        stage_timings_ms={
            "fetch_data": 120.5,
            "context_build": 1840.2,
            "entry_eval": 33.0,
        },
        snapshot_row={
            "observe_reason": "upper_reject_mixed_confirm",
            "observe_action": "SELL",
            "observe_side": "SELL",
            "blocked_by": "energy_soft_block",
            "quick_trace_state": "BLOCKED",
        },
    )

    assert profile["symbol"] == "XAUUSD"
    assert profile["is_slow"] is True
    assert profile["dominant_stage"] == "context_build"
    assert profile["dominant_stage_ms"] == 1840.2
    assert profile["snapshot"]["observe_reason"] == "upper_reject_mixed_confirm"
    assert profile["snapshot"]["blocked_by"] == "energy_soft_block"


def test_record_symbol_stage_timing_captures_elapsed(monkeypatch):
    timings = {}
    monkeypatch.setattr("backend.app.trading_application_runner.time.perf_counter", lambda: 10.25)
    _record_symbol_stage_timing(timings, "fetch_data", 10.0)
    assert timings["fetch_data"] == 250.0


def test_write_symbol_loop_profile_persists_latest_and_recent(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "backend.app.trading_application_runner._resolve_symbol_loop_profile_path",
        lambda config: tmp_path / "symbol_loop_profile_latest.json",
    )
    monkeypatch.setattr(
        "backend.app.trading_application_runner.Config",
        SimpleNamespace(
            SYMBOL_LOOP_PROFILE_ENABLED=True,
            SYMBOL_LOOP_SLOW_WARN_SEC=3.0,
        ),
    )
    app = SimpleNamespace(symbol_loop_profile_state={})
    slow_profile = _build_symbol_loop_profile(
        loop_count=1,
        symbol="BTCUSD",
        elapsed_sec=3.5,
        stage_timings_ms={"fetch_data": 250.0},
        snapshot_row={"observe_reason": "btc_midline_sell_watch"},
    )
    _write_symbol_loop_profile(app, slow_profile)

    payload = json.loads((tmp_path / "symbol_loop_profile_latest.json").read_text(encoding="utf-8"))
    assert payload["latest_by_symbol"]["BTCUSD"]["dominant_stage"] == "fetch_data"
    assert len(payload["recent_slow_events"]) == 1

    fast_profile = _build_symbol_loop_profile(
        loop_count=2,
        symbol="BTCUSD",
        elapsed_sec=0.8,
        stage_timings_ms={"entry_eval": 50.0},
        snapshot_row={"observe_reason": "btc_midline_sell_watch"},
    )
    _write_symbol_loop_profile(app, fast_profile)
    payload = json.loads((tmp_path / "symbol_loop_profile_latest.json").read_text(encoding="utf-8"))
    assert payload["latest_by_symbol"]["BTCUSD"]["dominant_stage"] == "entry_eval"
    assert len(payload["recent_slow_events"]) == 1


def test_resolve_symbol_loop_profile_path_uses_workspace_relative_path():
    path = _resolve_symbol_loop_profile_path(
        SimpleNamespace(SYMBOL_LOOP_PROFILE_PATH=r"data\analysis\symbol_loop_profile_latest.json")
    )
    assert str(path).endswith(r"data\analysis\symbol_loop_profile_latest.json")


def test_snapshot_exit_fields_clears_exit_payload_when_flat():
    payload = _snapshot_exit_fields(
        {
            "exit_decision_context_v1": {"phase": "exit"},
            "exit_decision_result_v1": {"outcome": "evaluated"},
            "exit_prediction_v1": {"score": 1},
            "exit_recovery_prediction_v1": {"score": 2},
            "exit_utility_v1": {"exit_now": 0.7},
            "exit_wait_state_v1": {"state": "CUT_IMMEDIATE", "reason": "adverse_loss_expand"},
            "exit_decision_winner": "exit_now",
            "exit_decision_reason": "adverse_loss_expand",
        },
        pos_count=0,
    )

    assert payload["exit_decision_context_v1"] == {}
    assert payload["exit_decision_result_v1"] == {}
    assert payload["exit_prediction_v1"] == {}
    assert payload["exit_recovery_prediction_v1"] == {}
    assert payload["exit_utility_v1"] == {}
    assert payload["exit_wait_state_v1"] == {}
    assert payload["exit_decision_winner"] == ""
    assert payload["exit_decision_reason"] == ""
