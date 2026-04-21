from __future__ import annotations

import json
from pathlib import Path

from backend.services.checkpoint_improvement_pa9_apply_handlers import (
    CheckpointImprovementPa9ApplyHandlerSet,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_pa9_handoff_review_writes_apply_artifact_and_updates_activation_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    shadow_auto_dir = tmp_path / "shadow_auto"
    _write_json(
        shadow_auto_dir / "checkpoint_pa8_nas100_action_only_canary_activation_apply_latest.json",
        {
            "summary": {
                "activation_apply_state": "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
                "approval_state": "MANUAL_CLOSEOUT_APPROVED",
                "active": False,
            },
            "active_state": {
                "activation_apply_state": "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
                "approval_state": "MANUAL_CLOSEOUT_APPROVED",
                "active": False,
            },
        },
    )
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa9_apply_handlers.refresh_checkpoint_improvement_pa9_handoff_runtime",
        lambda: {
            "summary": {
                "review_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW",
                "apply_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_APPLY_REVIEW",
            },
            "review_packet": {
                "rows": [
                    {
                        "symbol": "NAS100",
                        "handoff_review_candidate": True,
                    }
                ]
            },
            "apply_packet": {
                "rows": [
                    {
                        "symbol": "NAS100",
                        "handoff_apply_candidate": True,
                        "activation_apply_state": "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
                    }
                ]
            },
            "artifact_paths": {
                "handoff_packet": str(tmp_path / "handoff.json"),
            },
        },
    )
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa9_apply_handlers.load_checkpoint_pa8_canary_refresh_resolved_dataset",
        lambda path: [],
    )
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa9_apply_handlers.build_checkpoint_pa8_canary_refresh_board",
        lambda resolved_dataset: {"summary": {"contract_version": "checkpoint_pa8_canary_refresh_board_v1"}, "rows": []},
    )
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa9_apply_handlers.write_checkpoint_pa8_canary_refresh_outputs",
        lambda payload: None,
    )

    handler_set = CheckpointImprovementPa9ApplyHandlerSet(shadow_auto_dir=shadow_auto_dir)
    payload = handler_set.handle_handoff_review(
        approval_event_payload={},
        group={"symbol": "NAS100"},
        review_payload={},
        now_ts="2026-04-12T23:40:00+09:00",
    )

    assert payload["summary"]["apply_state"] == "PA9_ACTION_BASELINE_HANDOFF_APPLIED"
    updated = json.loads(
        (shadow_auto_dir / "checkpoint_pa8_nas100_action_only_canary_activation_apply_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert updated["summary"]["activation_apply_state"] == "PA9_ACTION_BASELINE_HANDOFF_APPLIED"
    assert updated["summary"]["approval_state"] == "MANUAL_PA9_HANDOFF_APPROVED"
    handoff_apply = json.loads(
        (shadow_auto_dir / "checkpoint_pa9_nas100_action_baseline_handoff_apply_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert handoff_apply["summary"]["apply_state"] == "PA9_ACTION_BASELINE_HANDOFF_APPLIED"


def test_pa9_handoff_review_blocks_when_runtime_is_not_ready(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa9_apply_handlers.refresh_checkpoint_improvement_pa9_handoff_runtime",
        lambda: {
            "summary": {
                "review_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                "apply_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
            },
            "review_packet": {"rows": []},
            "apply_packet": {"rows": []},
        },
    )
    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa9_apply_handlers.load_checkpoint_pa8_canary_refresh_resolved_dataset",
        lambda path: [],
    )
    handler_set = CheckpointImprovementPa9ApplyHandlerSet(shadow_auto_dir=tmp_path / "shadow_auto")

    try:
        handler_set.handle_handoff_review(
            approval_event_payload={},
            group={"symbol": "BTCUSD"},
            review_payload={},
            now_ts="2026-04-12T23:41:00+09:00",
        )
    except ValueError as exc:
        assert "pa9_handoff_review_not_ready" in str(exc)
    else:
        raise AssertionError("expected ValueError for not-ready handoff runtime")
