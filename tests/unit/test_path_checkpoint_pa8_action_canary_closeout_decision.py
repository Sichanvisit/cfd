from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_canary_closeout_decision import (
    build_checkpoint_pa8_nas100_action_only_canary_closeout_decision,
)


def test_build_checkpoint_pa8_action_canary_closeout_decision_holds_for_live_window() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_closeout_decision(
        activation_apply_payload={
            "summary": {
                "symbol": "NAS100",
                "active": True,
                "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
            },
            "active_state": {"guardrails": {"sample_floor": 50}},
        },
        first_window_observation_payload={
            "summary": {
                "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                "live_observation_ready": False,
                "observed_window_row_count": 0,
                "new_worsened_rows": 0,
            },
            "active_triggers": [],
        },
        rollback_review_payload={"summary": {"rollback_review_state": "READY_WITH_NO_TRIGGER_ACTIVE"}},
    )

    assert payload["summary"]["closeout_state"] == "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW"
    assert payload["summary"]["decision"] == "keep_canary_active_and_collect_live_rows"


def test_build_checkpoint_pa8_action_canary_closeout_decision_does_not_rollback_before_live_rows() -> None:
    payload = build_checkpoint_pa8_nas100_action_only_canary_closeout_decision(
        activation_apply_payload={
            "summary": {
                "symbol": "BTCUSD",
                "active": True,
                "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
            },
            "active_state": {"guardrails": {"sample_floor": 50}},
        },
        first_window_observation_payload={
            "summary": {
                "first_window_status": "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS",
                "live_observation_ready": False,
                "observed_window_row_count": 0,
                "new_worsened_rows": 0,
            },
            "active_triggers": ["runtime_proxy_match_rate_regressed"],
        },
        rollback_review_payload={"summary": {"rollback_review_state": "READY_WITH_TRIGGER_ACTIVE"}},
    )

    assert payload["summary"]["closeout_state"] == "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW"
    assert payload["summary"]["decision"] == "keep_canary_active_and_collect_live_rows"
