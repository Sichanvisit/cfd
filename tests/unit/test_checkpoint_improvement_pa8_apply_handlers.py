from __future__ import annotations

import json
from pathlib import Path

from backend.services.checkpoint_improvement_pa8_apply_handlers import (
    CheckpointImprovementPa8ApplyHandlerSet,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_closeout_review_builds_pa9_handoff_scaffold(tmp_path: Path, monkeypatch) -> None:
    shadow_auto_dir = tmp_path / "shadow_auto"
    activation_apply_path = (
        shadow_auto_dir / "checkpoint_pa8_btcusd_action_only_canary_activation_apply_latest.json"
    )
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
        shadow_auto_dir / "checkpoint_pa8_btcusd_action_only_canary_closeout_decision_latest.json",
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

    seen: dict[str, object] = {}

    def _refresh_stub() -> None:
        seen["refreshed"] = True

    handler_set = CheckpointImprovementPa8ApplyHandlerSet(shadow_auto_dir=shadow_auto_dir)
    monkeypatch.setattr(handler_set, "_refresh_canary_outputs", _refresh_stub)
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
                "summary": {
                    "review_state": "READY_FOR_MANUAL_PA8_CLOSEOUT_REVIEW",
                    "review_ready": True,
                },
                "rows": [
                    {
                        "symbol": "BTCUSD",
                        "closeout_review_candidate": True,
                    }
                ],
            },
            "apply_packet": {
                "summary": {
                    "apply_state": "READY_FOR_MANUAL_PA8_CLOSEOUT_APPLY_REVIEW",
                    "allow_apply": True,
                }
            },
        },
    )
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa8_apply_handlers.refresh_checkpoint_improvement_pa9_handoff_runtime",
        lambda: {
            "summary": {
                "handoff_state": "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW",
                "review_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW",
                "apply_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_APPLY_REVIEW",
            },
            "artifact_paths": {
                "handoff_packet": str(tmp_path / "pa9_handoff.json"),
                "review_packet": str(tmp_path / "pa9_review.json"),
                "apply_packet": str(tmp_path / "pa9_apply.json"),
            },
        },
    )

    payload = handler_set.handle_closeout_review(
        group={"symbol": "BTCUSD"},
        review_payload={"symbol": "BTCUSD"},
        approval_event_payload={"decision": "approve"},
        now_ts="2026-04-11T21:00:00+09:00",
    )

    updated = json.loads(activation_apply_path.read_text(encoding="utf-8"))
    assert payload["summary"]["apply_state"] == "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY"
    assert updated["summary"]["activation_apply_state"] == "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY"
    assert seen["refreshed"] is True
    assert payload["pa9_handoff_runtime"]["summary"]["handoff_state"] == "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW"
    assert payload["artifact_paths"]["review_packet"] == str(tmp_path / "pa9_review.json")
