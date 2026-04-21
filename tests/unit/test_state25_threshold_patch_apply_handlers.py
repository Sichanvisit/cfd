from __future__ import annotations

import json
from pathlib import Path

from backend.services.apply_executor import ApplyExecutor
from backend.services.state25_threshold_patch_apply_handlers import (
    register_default_state25_threshold_patch_apply_handlers,
)
from backend.services.telegram_state_store import TelegramStateStore


def test_state25_threshold_patch_apply_handler_writes_log_only_state(
    tmp_path: Path,
) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = store.upsert_check_group(
        group_key="STATE25_THRESHOLD_PATCH::BTCUSD::READY",
        status="approved",
        symbol="BTCUSD",
        check_kind="state25_threshold_patch_review",
        action_target="state25_threshold_patch_log_only",
        review_type="STATE25_THRESHOLD_PATCH_REVIEW",
        approval_id="approval-threshold-1",
        scope_key="STATE25_THRESHOLD_PATCH::BTCUSD::READY",
        trace_id="trace-threshold-1",
        decision_deadline_ts="2026-04-12T02:30:00+09:00",
    )
    executor = ApplyExecutor(telegram_state_store=store)
    active_state_path = (
        tmp_path / "models" / "teacher_pattern_state25_candidates" / "active_candidate_state.json"
    )
    shadow_auto_dir = tmp_path / "shadow_auto"
    register_default_state25_threshold_patch_apply_handlers(
        executor,
        active_candidate_state_path=active_state_path,
        shadow_auto_dir=shadow_auto_dir,
    )

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "STATE25_THRESHOLD_PATCH_REVIEW",
            "decision": "approve",
            "approval_id": "approval-threshold-1",
            "apply_job_key": "apply-job-threshold-1",
            "scope_key": "STATE25_THRESHOLD_PATCH::BTCUSD::READY",
        },
        review_payload={
            "candidate_id": "threshold-candidate-1",
            "threshold_patch": {
                "state25_execution_bind_mode": "log_only",
                "state25_execution_symbol_allowlist": ["BTCUSD"],
                "state25_execution_entry_stage_allowlist": ["READY"],
                "state25_threshold_log_only_requested_points": 4.0,
                "state25_threshold_log_only_effective_points": 3.6,
                "state25_threshold_log_only_direction": "HARDEN",
                "state25_threshold_log_only_reason_keys": ["AGAINST_HTF"],
            },
        },
        now_ts="2026-04-12T02:00:00+09:00",
    )

    active_state = json.loads(active_state_path.read_text(encoding="utf-8"))
    patch = active_state["desired_runtime_patch"]

    assert payload["summary"]["trigger_state"] == "APPLY_EXECUTED"
    assert active_state["current_binding_mode"] == "log_only"
    assert patch["state25_threshold_log_only_enabled"] is True
    assert patch["state25_threshold_log_only_delta_points"] == 4
    assert patch["state25_threshold_log_only_max_adjustment_abs"] == 4
    assert patch["state25_threshold_log_only_direction"] == "HARDEN"
    assert patch["state25_threshold_log_only_reason_keys"] == ["AGAINST_HTF"]
    assert patch["state25_threshold_bounded_live_enabled"] is False
    assert (shadow_auto_dir / "checkpoint_state25_threshold_patch_apply_latest.json").exists()


def test_state25_threshold_patch_apply_handler_writes_bounded_live_state(
    tmp_path: Path,
) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = store.upsert_check_group(
        group_key="STATE25_THRESHOLD_PATCH::NAS100::PROBE",
        status="approved",
        symbol="NAS100",
        check_kind="state25_threshold_patch_review",
        action_target="state25_threshold_patch_bounded_live",
        review_type="STATE25_THRESHOLD_PATCH_REVIEW",
        approval_id="approval-threshold-live-1",
        scope_key="STATE25_THRESHOLD_PATCH::NAS100::PROBE",
        trace_id="trace-threshold-live-1",
        decision_deadline_ts="2026-04-12T02:30:00+09:00",
    )
    executor = ApplyExecutor(telegram_state_store=store)
    active_state_path = (
        tmp_path / "models" / "teacher_pattern_state25_candidates" / "active_candidate_state.json"
    )
    shadow_auto_dir = tmp_path / "shadow_auto"
    register_default_state25_threshold_patch_apply_handlers(
        executor,
        active_candidate_state_path=active_state_path,
        shadow_auto_dir=shadow_auto_dir,
    )

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "STATE25_THRESHOLD_PATCH_REVIEW",
            "decision": "approve",
            "approval_id": "approval-threshold-live-1",
            "apply_job_key": "apply-job-threshold-live-1",
            "scope_key": "STATE25_THRESHOLD_PATCH::NAS100::PROBE",
        },
        review_payload={
            "candidate_id": "threshold-candidate-live-1",
            "threshold_patch": {
                "state25_execution_bind_mode": "bounded_live",
                "state25_execution_symbol_allowlist": ["NAS100"],
                "state25_execution_entry_stage_allowlist": ["PROBE"],
                "state25_threshold_log_only_requested_points": 3.2,
                "state25_threshold_log_only_effective_points": 3.2,
                "state25_threshold_log_only_direction": "HARDEN",
                "state25_threshold_log_only_reason_keys": [
                    "AGAINST_PREV_BOX_AND_HTF"
                ],
            },
        },
        now_ts="2026-04-12T02:05:00+09:00",
    )

    active_state = json.loads(active_state_path.read_text(encoding="utf-8"))
    patch = active_state["desired_runtime_patch"]

    assert payload["summary"]["trigger_state"] == "APPLY_EXECUTED"
    assert active_state["current_binding_mode"] == "bounded_live"
    assert active_state["current_rollout_phase"] == "bounded_live"
    assert patch["state25_threshold_log_only_enabled"] is False
    assert patch["state25_threshold_bounded_live_enabled"] is True
    assert patch["state25_threshold_bounded_live_delta_points"] == 3
    assert patch["state25_threshold_bounded_live_direction"] == "HARDEN"
    assert patch["state25_threshold_bounded_live_reason_keys"] == [
        "AGAINST_PREV_BOX_AND_HTF"
    ]
