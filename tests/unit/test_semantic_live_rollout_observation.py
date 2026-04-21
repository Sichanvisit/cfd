import pandas as pd

from backend.services.semantic_live_rollout_observation import (
    build_semantic_live_rollout_observation,
)


def test_rollout_observation_suggests_enabling_log_only_when_disabled() -> None:
    runtime_status = {
        "updated_at": "2026-04-08T19:11:22+09:00",
        "semantic_shadow_loaded": True,
        "semantic_live_config": {
            "mode": "disabled",
            "shadow_runtime_state": "active",
            "shadow_runtime_reason": "loaded",
        },
        "semantic_rollout_state": {
            "entry": {
                "events_total": 10,
                "alerts_total": 0,
                "threshold_applied_total": 0,
                "fallback_total": 10,
                "partial_live_total": 0,
            }
        },
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T19:15:05",
                "symbol": "NAS100",
                "semantic_live_rollout_mode": "disabled",
                "semantic_live_threshold_applied": 0,
                "semantic_live_partial_live_applied": 0,
                "semantic_shadow_available": 1,
                "trace_quality_state": "fallback_heavy",
                "semantic_live_fallback_reason": "rollout_disabled",
            }
        ]
    )

    frame, _summary = build_semantic_live_rollout_observation(runtime_status, entry_decisions, recent_limit=20)
    row = frame.iloc[0]
    assert row["rollout_mode"] == "disabled"
    assert bool(row["shadow_loaded"]) is True
    assert row["recommended_next_action"] == "enable_log_only_rollout_and_restart_core"


def test_rollout_observation_tracks_log_only_recent_rows() -> None:
    runtime_status = {
        "updated_at": "2026-04-08T19:20:00+09:00",
        "semantic_shadow_loaded": True,
        "semantic_live_config": {
            "mode": "log_only",
            "shadow_runtime_state": "active",
            "shadow_runtime_reason": "loaded",
        },
        "semantic_rollout_state": {
            "entry": {
                "events_total": 12,
                "alerts_total": 0,
                "threshold_applied_total": 2,
                "fallback_total": 8,
                "partial_live_total": 0,
            }
        },
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T19:20:01",
                "symbol": "BTCUSD",
                "action": "BUY",
                "entry_stage": "balanced",
                "semantic_live_rollout_mode": "log_only",
                "semantic_live_threshold_applied": 0,
                "semantic_live_partial_live_applied": 0,
                "semantic_shadow_available": 1,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_timing_probability": 0.81,
                "semantic_shadow_timing_threshold": 0.55,
                "semantic_shadow_entry_quality_probability": 0.79,
                "semantic_shadow_entry_quality_threshold": 0.55,
                "semantic_shadow_trace_quality": "clean",
                "semantic_shadow_activation_state": "active",
                "trace_quality_state": "clean",
                "semantic_live_fallback_reason": "",
            },
            {
                "time": "2026-04-08T19:19:01",
                "symbol": "NAS100",
                "action": "SELL",
                "entry_stage": "balanced",
                "semantic_live_rollout_mode": "log_only",
                "semantic_live_threshold_applied": 0,
                "semantic_live_partial_live_applied": 0,
                "semantic_shadow_available": 1,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_timing_probability": 0.80,
                "semantic_shadow_timing_threshold": 0.55,
                "semantic_shadow_entry_quality_probability": 0.77,
                "semantic_shadow_entry_quality_threshold": 0.55,
                "semantic_shadow_trace_quality": "clean",
                "semantic_shadow_activation_state": "active",
                "trace_quality_state": "clean",
                "semantic_live_fallback_reason": "",
            },
        ]
    )

    frame, _summary = build_semantic_live_rollout_observation(runtime_status, entry_decisions, recent_limit=20)
    row = frame.iloc[0]
    assert row["rollout_mode"] == "log_only"
    assert int(row["recent_log_only_count"]) == 2
    assert int(row["recent_threshold_applied_count"]) == 0
    assert int(row["recent_threshold_would_apply_count"]) == 2
    assert int(row["recent_partial_live_would_apply_count"]) == 2
    assert row["rollout_promotion_readiness"] == "candidate_partial_live"
    assert row["recommended_next_action"] == "review_partial_live_candidate_from_log_only_counterfactuals"
