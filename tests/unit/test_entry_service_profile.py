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
            "entry_helper_prefront_profile_v1": {
                "total_ms": 88.9,
                "current_stage": "wait_routing",
                "exit_state": "observe_return",
            },
            "entry_helper_front_profile_v1": {"total_ms": 123.4},
            "entry_helper_back_profile_v1": {"total_ms": 67.8, "current_stage": "post_threshold_guards"},
            "entry_helper_payload_profile_v1": {"total_ms": 45.6},
            "entry_append_log_profile_v1": {"total_ms": 12.3},
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
    assert profile["helper_prefront_profile"]["total_ms"] == 88.9
    assert profile["helper_front_profile"]["total_ms"] == 123.4
    assert profile["helper_back_profile"]["total_ms"] == 67.8
    assert profile["helper_internal_profile"]["total_ms"] == 45.6
    assert profile["append_log_profile"]["total_ms"] == 12.3
    assert profile["snapshot"]["blocked_by"] == "forecast_guard"


def test_resolve_entry_eval_profile_path_uses_workspace_relative_path():
    path = _resolve_entry_eval_profile_path(
        SimpleNamespace(ENTRY_EVAL_PROFILE_PATH=r"data\analysis\entry_eval_profile_latest.json")
    )
    assert str(path).endswith(r"data\analysis\entry_eval_profile_latest.json")
