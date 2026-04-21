from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.checkpoint_improvement_pa8_apply_handlers import (
    CheckpointImprovementPa8ApplyHandlerSet,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_closeout_review_writes_closeout_apply_artifact_and_runtime(tmp_path: Path, monkeypatch) -> None:
    shadow_auto_dir = tmp_path / "shadow_auto"
    activation_apply_path = (
        shadow_auto_dir / "checkpoint_pa8_btcusd_action_only_canary_activation_apply_latest.json"
    )
    closeout_path = shadow_auto_dir / "checkpoint_pa8_btcusd_action_only_canary_closeout_decision_latest.json"
    _write_json(
        activation_apply_path,
        {
            "summary": {
                "activation_apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                "approval_state": "MANUAL_ACTIVATION_APPROVED",
                "active": True,
            },
            "active_state": {
                "active": True,
                "window_status": "FIRST_CANARY_WINDOW_ACTIVE",
            },
        },
    )
    _write_json(
        closeout_path,
        {
            "summary": {
                "closeout_state": "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW",
                "live_observation_ready": True,
                "observed_window_row_count": 52,
                "sample_floor": 50,
                "active_trigger_count": 0,
                "recommended_next_action": "prepare_pa9_action_baseline_handoff_packet",
            }
        },
    )

    handler_set = CheckpointImprovementPa8ApplyHandlerSet(shadow_auto_dir=shadow_auto_dir)
    monkeypatch.setattr(handler_set, "_refresh_canary_outputs", lambda: None)
    monkeypatch.setattr(
        handler_set,
        "_refresh_pa8_closeout_runtime",
        lambda: {
            "summary": {
                "review_state": "READY_FOR_MANUAL_PA8_CLOSEOUT_REVIEW",
                "apply_state": "READY_FOR_MANUAL_PA8_CLOSEOUT_APPLY_REVIEW",
            },
            "artifact_paths": {
                "review_packet": str(tmp_path / "pa8_closeout_review.json"),
                "apply_packet": str(tmp_path / "pa8_closeout_apply_packet.json"),
            },
            "review_packet": {
                "summary": {"review_state": "READY_FOR_MANUAL_PA8_CLOSEOUT_REVIEW", "review_ready": True},
                "rows": [{"symbol": "BTCUSD", "closeout_review_candidate": True}],
            },
            "apply_packet": {
                "summary": {"apply_state": "READY_FOR_MANUAL_PA8_CLOSEOUT_APPLY_REVIEW", "allow_apply": True},
            },
        },
    )
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa8_apply_handlers.refresh_checkpoint_improvement_pa9_handoff_runtime",
        lambda: {"summary": {"handoff_state": "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW"}, "artifact_paths": {}},
    )

    payload = handler_set.handle_closeout_review(
        group={"symbol": "BTCUSD"},
        review_payload={"symbol": "BTCUSD"},
        approval_event_payload={"decision": "approve"},
        now_ts="2026-04-12T12:00:00+09:00",
    )

    closeout_apply_path = shadow_auto_dir / "checkpoint_pa8_btcusd_action_only_canary_closeout_apply_latest.json"
    assert closeout_apply_path.exists()
    closeout_apply = json.loads(closeout_apply_path.read_text(encoding="utf-8"))
    assert payload["summary"]["apply_state"] == "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY"
    assert closeout_apply["summary"]["review_state"] == "READY_FOR_MANUAL_PA8_CLOSEOUT_REVIEW"
    assert closeout_apply["summary"]["apply_packet_state"] == "READY_FOR_MANUAL_PA8_CLOSEOUT_APPLY_REVIEW"


def test_closeout_review_blocks_when_closeout_decision_is_not_ready(tmp_path: Path) -> None:
    shadow_auto_dir = tmp_path / "shadow_auto"
    _write_json(
        shadow_auto_dir / "checkpoint_pa8_btcusd_action_only_canary_closeout_decision_latest.json",
        {
            "summary": {
                "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                "live_observation_ready": False,
                "observed_window_row_count": 0,
                "sample_floor": 50,
                "active_trigger_count": 0,
            }
        },
    )
    handler_set = CheckpointImprovementPa8ApplyHandlerSet(shadow_auto_dir=shadow_auto_dir)

    with pytest.raises(ValueError, match="pa8_closeout_not_ready::HOLD_CLOSEOUT_PENDING_LIVE_WINDOW"):
        handler_set._assert_closeout_ready(
            symbol="BTCUSD",
            closeout_decision=json.loads(
                (shadow_auto_dir / "checkpoint_pa8_btcusd_action_only_canary_closeout_decision_latest.json").read_text(
                    encoding="utf-8"
                )
            ),
            closeout_runtime={},
        )
