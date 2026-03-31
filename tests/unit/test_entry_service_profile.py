from types import SimpleNamespace

from backend.services.entry_service import (
    _build_entry_eval_profile,
    _resolve_entry_eval_profile_path,
)


def test_build_entry_eval_profile_summarizes_dominant_stage():
    profile = _build_entry_eval_profile(
        symbol="BTCUSD",
        elapsed_ms=1280.4,
        stage_timings_ms={
            "active_ticket_snapshot_before": 0.2,
            "helper_try_open_entry": 1100.8,
            "handoff_backfill": 120.0,
        },
        snapshot_row={
            "observe_reason": "lower_rebound_probe_observe",
            "blocked_by": "forecast_guard",
            "quick_trace_state": "PROBE_WAIT",
        },
        new_ticket_count=1,
        newest_ticket=12345,
    )

    assert profile["symbol"] == "BTCUSD"
    assert profile["is_slow"] is True
    assert profile["dominant_stage"] == "helper_try_open_entry"
    assert profile["dominant_stage_ms"] == 1100.8
    assert profile["new_ticket_count"] == 1
    assert profile["newest_ticket"] == 12345
    assert profile["snapshot"]["blocked_by"] == "forecast_guard"


def test_resolve_entry_eval_profile_path_uses_workspace_relative_path():
    path = _resolve_entry_eval_profile_path(
        SimpleNamespace(ENTRY_EVAL_PROFILE_PATH=r"data\analysis\entry_eval_profile_latest.json")
    )
    assert str(path).endswith(r"data\analysis\entry_eval_profile_latest.json")
