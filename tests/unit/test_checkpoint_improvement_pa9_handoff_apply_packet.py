from __future__ import annotations

from backend.services.checkpoint_improvement_pa9_handoff_apply_packet import (
    build_checkpoint_improvement_pa9_handoff_apply_packet,
)


def test_pa9_handoff_apply_packet_becomes_ready_when_review_ready() -> None:
    payload = build_checkpoint_improvement_pa9_handoff_apply_packet(
        review_payload={
            "summary": {
                "review_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW",
                "review_ready": True,
                "review_candidate_symbol_count": 1,
                "prepared_symbol_count": 1,
                "handoff_state": "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW",
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "handoff_review_candidate": True,
                }
            ],
        }
    )

    assert payload["summary"]["apply_state"] == "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_APPLY_REVIEW"
    assert payload["summary"]["allow_apply"] is True
    assert payload["summary"]["apply_candidate_symbol_count"] == 1
    assert payload["rows"][0]["handoff_apply_candidate"] is True


def test_pa9_handoff_apply_packet_holds_when_review_is_not_ready() -> None:
    payload = build_checkpoint_improvement_pa9_handoff_apply_packet(
        review_payload={
            "summary": {
                "review_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                "review_ready": False,
                "review_candidate_symbol_count": 0,
                "prepared_symbol_count": 0,
                "handoff_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
            },
            "rows": [],
        }
    )

    assert payload["summary"]["apply_state"] == "HOLD_PENDING_PA8_LIVE_WINDOW"
    assert payload["summary"]["allow_apply"] is False


def test_pa9_handoff_apply_packet_marks_already_applied_state() -> None:
    payload = build_checkpoint_improvement_pa9_handoff_apply_packet(
        review_payload={
            "summary": {
                "review_state": "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED",
                "review_ready": False,
                "applied_symbol_count": 1,
                "review_candidate_symbol_count": 0,
                "prepared_symbol_count": 0,
                "handoff_state": "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED",
            },
            "rows": [
                {
                    "symbol": "NAS100",
                    "handoff_review_candidate": False,
                    "handoff_apply_state": "PA9_ACTION_BASELINE_HANDOFF_APPLIED",
                }
            ],
        }
    )

    assert payload["summary"]["apply_state"] == "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED"
    assert payload["summary"]["allow_apply"] is False
    assert payload["rows"][0]["handoff_apply_candidate"] is False
