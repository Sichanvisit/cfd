from __future__ import annotations

from backend.services.checkpoint_improvement_pa9_handoff_review_packet import (
    build_checkpoint_improvement_pa9_handoff_review_packet,
)


def test_pa9_handoff_review_packet_becomes_ready_when_symbol_is_prepared() -> None:
    payload = build_checkpoint_improvement_pa9_handoff_review_packet(
        handoff_payload={
            "summary": {
                "handoff_state": "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW",
                "prepared_symbol_count": 1,
                "ready_closeout_symbol_count": 0,
                "active_canary_symbol_count": 3,
                "live_window_ready_count": 1,
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "activation_apply_state": "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
                    "closeout_state": "CLOSEOUT_APPLIED",
                    "live_observation_ready": True,
                }
            ],
        }
    )

    assert payload["summary"]["review_state"] == "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW"
    assert payload["summary"]["review_ready"] is True
    assert payload["summary"]["review_candidate_symbol_count"] == 1
    assert payload["rows"][0]["handoff_review_candidate"] is True


def test_pa9_handoff_review_packet_waits_for_closeout_apply_when_ready_closeout_exists() -> None:
    payload = build_checkpoint_improvement_pa9_handoff_review_packet(
        handoff_payload={
            "summary": {
                "handoff_state": "WAIT_FOR_CLOSEOUT_APPROVAL_APPLICATION",
                "prepared_symbol_count": 0,
                "ready_closeout_symbol_count": 1,
                "active_canary_symbol_count": 3,
                "live_window_ready_count": 1,
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                    "closeout_state": "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW",
                    "live_observation_ready": True,
                }
            ],
        }
    )

    assert payload["summary"]["review_state"] == "HOLD_PENDING_PA8_CLOSEOUT_APPLICATION"
    assert payload["summary"]["review_ready"] is False


def test_pa9_handoff_review_packet_marks_already_applied_state() -> None:
    payload = build_checkpoint_improvement_pa9_handoff_review_packet(
        handoff_payload={
            "summary": {
                "handoff_state": "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED",
                "applied_symbol_count": 1,
                "prepared_symbol_count": 0,
                "ready_closeout_symbol_count": 0,
                "active_canary_symbol_count": 0,
                "live_window_ready_count": 0,
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "activation_apply_state": "PA9_ACTION_BASELINE_HANDOFF_APPLIED",
                    "handoff_apply_state": "PA9_ACTION_BASELINE_HANDOFF_APPLIED",
                    "live_observation_ready": True,
                }
            ],
        }
    )

    assert payload["summary"]["review_state"] == "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED"
    assert payload["summary"]["review_ready"] is False
    assert payload["rows"][0]["handoff_review_candidate"] is False
