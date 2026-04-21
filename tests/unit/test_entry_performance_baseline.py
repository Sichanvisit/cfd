from __future__ import annotations

from backend.services.entry_performance_baseline import (
    build_entry_performance_baseline_lock,
    build_entry_performance_regression_watch,
)


def _profile_row(*, elapsed_ms: float, append_total_ms: float, detail_ms: float, compact_ms: float, hot_ms: float) -> dict:
    return {
        "symbol": "X",
        "elapsed_ms": elapsed_ms,
        "dominant_stage": "helper_try_open_entry",
        "append_log_profile": {
            "total_ms": append_total_ms,
            "recorder_total_ms": append_total_ms - 1.0,
            "runtime_snapshot_mode": "lean_no_action_direct_row",
            "runtime_snapshot_store_calls": 0,
            "recorder_stage_timings_ms": {
                "detail_payload_build": detail_ms,
                "file_write": 3.0,
            },
            "detail_payload_stage_timings_ms": {
                "compact_runtime_row": compact_ms,
                "detail_record_json": 0.6,
                "hot_payload_build": hot_ms,
                "payload_size_metrics": 0.4,
            },
            "file_write_stage_timings_ms": {
                "rollover": 0.2,
                "detail_append": 0.7,
                "csv_append": 1.1,
            },
        },
    }


def test_build_entry_performance_baseline_lock_uses_current_latest_by_symbol():
    profile_collection = {
        "latest_by_symbol": {
            "NAS100": _profile_row(elapsed_ms=138.8, append_total_ms=15.4, detail_ms=9.3, compact_ms=3.8, hot_ms=0.9),
            "BTCUSD": _profile_row(elapsed_ms=108.4, append_total_ms=14.0, detail_ms=8.3, compact_ms=3.2, hot_ms=0.8),
            "XAUUSD": _profile_row(elapsed_ms=122.3, append_total_ms=16.3, detail_ms=10.2, compact_ms=3.8, hot_ms=2.0),
        }
    }

    baseline = build_entry_performance_baseline_lock(profile_collection, reentry_elapsed_ms=200.0)

    assert baseline["baseline_locked"] is True
    assert baseline["symbol_count"] == 3
    assert baseline["recommended_next_action"] == "resume_market_family_roadmap"
    assert baseline["max_elapsed_ms"] == 138.8
    assert baseline["symbol_metrics"][0]["symbol"] == "NAS100"


def test_build_entry_performance_regression_watch_requests_reentry_when_elapsed_crosses_threshold():
    baseline = build_entry_performance_baseline_lock(
        {
            "latest_by_symbol": {
                "NAS100": _profile_row(elapsed_ms=140.0, append_total_ms=15.0, detail_ms=9.0, compact_ms=3.7, hot_ms=1.0),
                "BTCUSD": _profile_row(elapsed_ms=110.0, append_total_ms=14.0, detail_ms=8.0, compact_ms=3.2, hot_ms=0.9),
                "XAUUSD": _profile_row(elapsed_ms=120.0, append_total_ms=16.0, detail_ms=10.0, compact_ms=3.8, hot_ms=1.9),
            }
        },
        reentry_elapsed_ms=200.0,
    )
    current = {
        "latest_by_symbol": {
            "NAS100": _profile_row(elapsed_ms=220.0, append_total_ms=19.0, detail_ms=12.0, compact_ms=5.0, hot_ms=1.5),
            "BTCUSD": _profile_row(elapsed_ms=111.0, append_total_ms=14.2, detail_ms=8.1, compact_ms=3.1, hot_ms=0.8),
            "XAUUSD": _profile_row(elapsed_ms=118.0, append_total_ms=16.1, detail_ms=9.8, compact_ms=3.7, hot_ms=1.8),
        }
    }

    watch = build_entry_performance_regression_watch(current, baseline)

    assert watch["reentry_required"] is True
    assert watch["recommended_next_action"] == "reenter_entry_performance_optimization"
    assert watch["reentry_symbols"] == ["NAS100"]
    nas_row = next(row for row in watch["comparisons"] if row["symbol"] == "NAS100")
    assert nas_row["status"] == "reentry_required"
    assert nas_row["elapsed_delta_ms"] == 80.0
