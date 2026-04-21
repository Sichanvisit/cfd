from __future__ import annotations

import json
from pathlib import Path

from backend.services.checkpoint_improvement_pa9_handoff_packet import (
    build_checkpoint_improvement_pa9_handoff_packet,
    render_checkpoint_improvement_pa9_handoff_packet_markdown,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_symbol_artifacts(
    shadow_auto_dir: Path,
    symbol: str,
    *,
    activation_apply_state: str,
    closeout_state: str,
    live_ready: bool,
) -> None:
    symbol_key = symbol.lower()
    _write_json(
        shadow_auto_dir / f"checkpoint_pa8_{symbol_key}_action_only_canary_activation_apply_latest.json",
        {
            "summary": {
                "activation_apply_state": activation_apply_state,
                "approval_state": (
                    "MANUAL_CLOSEOUT_APPROVED"
                    if "PA9_HANDOFF_PREPARED" in activation_apply_state
                    else "MANUAL_ACTIVATION_APPROVED"
                ),
            }
        },
    )
    _write_json(
        shadow_auto_dir / f"checkpoint_pa8_{symbol_key}_action_only_canary_closeout_decision_latest.json",
        {
            "summary": {
                "closeout_state": closeout_state,
                "live_observation_ready": live_ready,
                "observed_window_row_count": 24,
                "sample_floor": 20,
                "active_trigger_count": 0,
                "recommended_next_action": (
                    "prepare_pa9_action_baseline_handoff_packet"
                    if "READY_FOR_PA9" in closeout_state
                    else "wait_for_live_first_window_rows_before_pa8_closeout"
                ),
            }
        },
    )
    _write_json(
        shadow_auto_dir / f"checkpoint_pa8_{symbol_key}_action_only_canary_first_window_observation_latest.json",
        {
            "summary": {
                "first_window_status": (
                    "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE"
                    if live_ready
                    else "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS"
                ),
            }
        },
    )


def test_pa9_handoff_packet_becomes_ready_when_a_symbol_is_prepared(tmp_path: Path, monkeypatch) -> None:
    shadow_auto_dir = tmp_path / "data" / "analysis" / "shadow_auto"
    for symbol in ("NAS100", "BTCUSD", "XAUUSD"):
        _write_symbol_artifacts(
            shadow_auto_dir,
            symbol,
            activation_apply_state="ACTIVE_ACTION_ONLY_CANARY",
            closeout_state="HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
            live_ready=False,
        )
    _write_symbol_artifacts(
        shadow_auto_dir,
        "NAS100",
        activation_apply_state="PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY",
        closeout_state="READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW",
        live_ready=True,
    )

    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa9_handoff_packet._repo_root",
        lambda: tmp_path,
    )

    payload = build_checkpoint_improvement_pa9_handoff_packet()

    assert payload["summary"]["handoff_state"] == "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW"
    assert payload["summary"]["prepared_symbol_count"] == 1
    assert payload["summary"]["ready_closeout_symbol_count"] == 1
    markdown = render_checkpoint_improvement_pa9_handoff_packet_markdown(payload)
    assert "PA9 Action Baseline Handoff Packet" in markdown


def test_pa9_handoff_packet_waits_for_closeout_approval_when_symbol_is_ready(tmp_path: Path, monkeypatch) -> None:
    shadow_auto_dir = tmp_path / "data" / "analysis" / "shadow_auto"
    for symbol in ("NAS100", "BTCUSD", "XAUUSD"):
        _write_symbol_artifacts(
            shadow_auto_dir,
            symbol,
            activation_apply_state="ACTIVE_ACTION_ONLY_CANARY",
            closeout_state="HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
            live_ready=False,
        )
    _write_symbol_artifacts(
        shadow_auto_dir,
        "BTCUSD",
        activation_apply_state="ACTIVE_ACTION_ONLY_CANARY",
        closeout_state="READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW",
        live_ready=True,
    )

    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa9_handoff_packet._repo_root",
        lambda: tmp_path,
    )

    payload = build_checkpoint_improvement_pa9_handoff_packet()

    assert payload["summary"]["handoff_state"] == "WAIT_FOR_CLOSEOUT_APPROVAL_APPLICATION"
    assert payload["summary"]["prepared_symbol_count"] == 0
    assert payload["summary"]["ready_closeout_symbol_count"] == 1


def test_pa9_handoff_packet_marks_applied_state_when_symbol_already_handed_off(tmp_path: Path, monkeypatch) -> None:
    shadow_auto_dir = tmp_path / "data" / "analysis" / "shadow_auto"
    for symbol in ("NAS100", "BTCUSD", "XAUUSD"):
        _write_symbol_artifacts(
            shadow_auto_dir,
            symbol,
            activation_apply_state="ACTIVE_ACTION_ONLY_CANARY",
            closeout_state="HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
            live_ready=False,
        )
    _write_json(
        shadow_auto_dir / "checkpoint_pa9_nas100_action_baseline_handoff_apply_latest.json",
        {
            "summary": {
                "apply_state": "PA9_ACTION_BASELINE_HANDOFF_APPLIED",
                "generated_at": "2026-04-12T23:30:00+09:00",
                "recommended_next_action": "monitor_post_handoff_action_baseline_runtime",
            }
        },
    )

    monkeypatch.setattr(
        "backend.services.checkpoint_improvement_pa9_handoff_packet._repo_root",
        lambda: tmp_path,
    )

    payload = build_checkpoint_improvement_pa9_handoff_packet()

    assert payload["summary"]["handoff_state"] == "HOLD_PENDING_PA8_LIVE_WINDOW"
    assert payload["summary"]["applied_symbol_count"] == 1
    assert payload["rows"][0]["handoff_apply_state"] == "PA9_ACTION_BASELINE_HANDOFF_APPLIED"
