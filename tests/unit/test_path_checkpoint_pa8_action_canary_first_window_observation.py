from __future__ import annotations

import pandas as pd

from backend.services.path_checkpoint_pa8_action_canary_first_window_observation import (
    build_checkpoint_pa8_nas100_action_only_canary_first_window_observation,
)


def test_build_checkpoint_pa8_action_canary_first_window_observation_seeds_when_no_live_rows() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_first_window_observation(
        activation_apply_payload={
            "summary": {
                "symbol": "NAS100",
                "active": True,
                "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                "baseline_hold_precision": 0.759036,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "baseline_partial_then_hold_quality": 0.971302,
            },
            "active_state": {
                "activated_at": "2026-04-11T10:00:00+09:00",
                "guardrails": {
                    "sample_floor": 50,
                    "worsened_row_count_ceiling": 0,
                    "partial_then_hold_quality_must_not_regress": True,
                },
            },
        },
        preview_payload={
            "summary": {
                "preview_changed_row_count": 82,
                "preview_hold_precision": 0.945946,
                "preview_runtime_proxy_match_rate": 0.964195,
                "preview_partial_then_hold_quality": 0.975701,
                "worsened_row_count": 0,
            }
        },
        resolved_dataset=pd.DataFrame(),
    )

    assert payload["summary"]["first_window_status"] == "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS"
    assert payload["summary"]["observation_source"] == "preview_seed_reference"
    assert payload["summary"]["live_observation_ready"] is False
    assert payload["summary"]["seed_reference_row_count"] == 82
    assert payload["active_triggers"] == []
