from __future__ import annotations

import json
from pathlib import Path

from backend.services.apply_executor import ApplyExecutor
from backend.services.state25_weight_patch_apply_handlers import (
    register_default_state25_weight_patch_apply_handlers,
)
from backend.services.telegram_state_store import TelegramStateStore


def test_state25_weight_patch_apply_handler_writes_active_candidate_state(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = store.upsert_check_group(
        group_key="STATE25_WEIGHT_PATCH::BTCUSD::READY",
        status="approved",
        symbol="BTCUSD",
        check_kind="state25_weight_patch_review",
        action_target="state25_weight_patch_log_only",
        review_type="STATE25_WEIGHT_PATCH_REVIEW",
        approval_id="approval-weight-1",
        scope_key="STATE25_WEIGHT_PATCH::BTCUSD::READY",
        trace_id="trace-weight-1",
        decision_deadline_ts="2026-04-12T02:30:00+09:00",
    )
    executor = ApplyExecutor(telegram_state_store=store)
    active_state_path = tmp_path / "models" / "teacher_pattern_state25_candidates" / "active_candidate_state.json"
    shadow_auto_dir = tmp_path / "shadow_auto"
    register_default_state25_weight_patch_apply_handlers(
        executor,
        active_candidate_state_path=active_state_path,
        shadow_auto_dir=shadow_auto_dir,
    )

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "STATE25_WEIGHT_PATCH_REVIEW",
            "decision": "approve",
            "approval_id": "approval-weight-1",
            "apply_job_key": "apply-job-weight-1",
            "scope_key": "STATE25_WEIGHT_PATCH::BTCUSD::READY",
        },
        review_payload={
            "candidate_id": "weight-candidate-1",
            "weight_patch": {
                "state25_execution_bind_mode": "log_only",
                "state25_execution_symbol_allowlist": ["BTCUSD"],
                "state25_execution_entry_stage_allowlist": ["READY"],
                "state25_teacher_weight_overrides": {
                    "upper_wick_weight": 0.7,
                    "compression_weight": 1.2,
                },
            },
        },
        now_ts="2026-04-12T02:00:00+09:00",
    )

    active_state = json.loads(active_state_path.read_text(encoding="utf-8"))
    assert payload["summary"]["trigger_state"] == "APPLY_EXECUTED"
    assert active_state["current_binding_mode"] == "log_only"
    assert active_state["desired_runtime_patch"]["state25_weight_log_only_enabled"] is True
    assert active_state["desired_runtime_patch"]["state25_teacher_weight_overrides"] == {
        "upper_wick_weight": 0.7,
        "compression_weight": 1.2,
    }
    assert (shadow_auto_dir / "checkpoint_state25_weight_patch_apply_latest.json").exists()


def test_state25_weight_patch_apply_handler_supports_bounded_live(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = store.upsert_check_group(
        group_key="STATE25_WEIGHT_PATCH::XAUUSD::READY",
        status="approved",
        symbol="XAUUSD",
        check_kind="state25_weight_patch_review",
        action_target="state25_weight_patch_bounded_live",
        review_type="STATE25_WEIGHT_PATCH_REVIEW",
        approval_id="approval-weight-live-1",
        scope_key="STATE25_WEIGHT_PATCH::XAUUSD::READY",
        trace_id="trace-weight-live-1",
        decision_deadline_ts="2026-04-12T02:30:00+09:00",
    )
    executor = ApplyExecutor(telegram_state_store=store)
    active_state_path = (
        tmp_path / "models" / "teacher_pattern_state25_candidates" / "active_candidate_state.json"
    )
    shadow_auto_dir = tmp_path / "shadow_auto"
    register_default_state25_weight_patch_apply_handlers(
        executor,
        active_candidate_state_path=active_state_path,
        shadow_auto_dir=shadow_auto_dir,
    )

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "STATE25_WEIGHT_PATCH_REVIEW",
            "decision": "approve",
            "approval_id": "approval-weight-live-1",
            "apply_job_key": "apply-job-weight-live-1",
            "scope_key": "STATE25_WEIGHT_PATCH::XAUUSD::READY",
        },
        review_payload={
            "candidate_id": "weight-candidate-live-1",
            "weight_patch": {
                "state25_execution_bind_mode": "bounded_live",
                "state25_execution_symbol_allowlist": ["XAUUSD"],
                "state25_execution_entry_stage_allowlist": ["READY"],
                "state25_weight_bounded_live_enabled": True,
                "state25_teacher_weight_overrides": {
                    "reversal_risk_weight": 0.8,
                    "directional_bias_weight": 1.15,
                },
            },
        },
        now_ts="2026-04-12T02:10:00+09:00",
    )

    active_state = json.loads(active_state_path.read_text(encoding="utf-8"))
    patch = active_state["desired_runtime_patch"]
    assert payload["summary"]["trigger_state"] == "APPLY_EXECUTED"
    assert active_state["current_binding_mode"] == "bounded_live"
    assert active_state["current_rollout_phase"] == "bounded_live"
    assert patch["state25_weight_log_only_enabled"] is False
    assert patch["state25_weight_bounded_live_enabled"] is True
    assert patch["state25_teacher_weight_overrides"] == {
        "reversal_risk_weight": 0.8,
        "directional_bias_weight": 1.15,
    }
