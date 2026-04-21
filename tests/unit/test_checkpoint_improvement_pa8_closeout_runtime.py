from __future__ import annotations

from backend.services.checkpoint_improvement_pa8_closeout_apply_packet import (
    build_checkpoint_improvement_pa8_closeout_apply_packet,
)
from backend.services.checkpoint_improvement_pa8_closeout_review_packet import (
    build_checkpoint_improvement_pa8_closeout_review_packet,
)


def test_pa8_closeout_review_packet_becomes_ready_when_symbol_is_ready() -> None:
    payload = build_checkpoint_improvement_pa8_closeout_review_packet(
        board_payload={
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "closeout_state": "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW",
                    "live_observation_ready": True,
                    "observed_window_row_count": 55,
                    "sample_floor": 50,
                    "active_trigger_count": 0,
                    "recommended_next_action": "prepare_pa9_action_baseline_handoff_packet",
                }
            ]
        }
    )

    assert payload["summary"]["review_state"] == "READY_FOR_MANUAL_PA8_CLOSEOUT_REVIEW"
    assert payload["summary"]["review_ready"] is True
    assert payload["summary"]["review_candidate_symbol_count"] == 1
    assert payload["rows"][0]["closeout_review_candidate"] is True


def test_pa8_closeout_review_packet_holds_for_rollback_before_review() -> None:
    payload = build_checkpoint_improvement_pa8_closeout_review_packet(
        board_payload={
            "rows": [
                {
                    "symbol": "XAUUSD",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "closeout_state": "ROLLBACK_REQUIRED",
                    "live_observation_ready": True,
                    "observed_window_row_count": 20,
                    "sample_floor": 20,
                    "active_trigger_count": 2,
                    "recommended_next_action": "disable_canary_and_return_to_baseline_action_behavior",
                }
            ]
        }
    )

    assert payload["summary"]["review_state"] == "HOLD_PENDING_PA8_ROLLBACK"
    assert payload["summary"]["review_ready"] is False
    assert payload["summary"]["rollback_required_symbol_count"] == 1


def test_pa8_closeout_apply_packet_becomes_ready_when_review_is_ready() -> None:
    payload = build_checkpoint_improvement_pa8_closeout_apply_packet(
        review_payload={
            "summary": {
                "review_state": "READY_FOR_MANUAL_PA8_CLOSEOUT_REVIEW",
                "review_ready": True,
                "review_candidate_symbol_count": 1,
                "rollback_required_symbol_count": 0,
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "closeout_review_candidate": True,
                }
            ],
        }
    )

    assert payload["summary"]["apply_state"] == "READY_FOR_MANUAL_PA8_CLOSEOUT_APPLY_REVIEW"
    assert payload["summary"]["allow_apply"] is True
    assert payload["rows"][0]["closeout_apply_candidate"] is True
