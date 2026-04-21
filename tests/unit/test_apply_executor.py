from __future__ import annotations

from pathlib import Path

from backend.services.apply_executor import ApplyExecutor
from backend.services.telegram_state_store import TelegramStateStore


def _build_store_with_group(tmp_path: Path, **overrides: object) -> tuple[TelegramStateStore, dict[str, object]]:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    base_kwargs: dict[str, object] = {
        "group_key": "BTCUSD::action_only_canary::activation",
        "status": "approved",
        "symbol": "BTCUSD",
        "check_kind": "activation_review",
        "review_type": "CANARY_ACTIVATION_REVIEW",
        "approval_id": "approval-1",
        "scope_key": "BTCUSD::action_only_canary::activation",
        "trace_id": "trace-apply-1",
        "apply_job_key": "apply-job-1",
        "decision_deadline_ts": "2026-04-11T13:00:00+09:00",
        "pending_count": 0,
        "approved_by": "1001",
        "approved_at": "2026-04-11T12:30:00+09:00",
    }
    base_kwargs.update(overrides)
    group = store.upsert_check_group(**base_kwargs)
    return store, group


def test_apply_executor_executes_handler_and_marks_group_applied(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path)

    def _handler(**_: object) -> dict[str, object]:
        return {
            "summary": {
                "apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                "recommended_next_action": "start_first_canary_window_observation",
            }
        }

    executor = ApplyExecutor(
        telegram_state_store=store,
        handlers={"CANARY_ACTIVATION_REVIEW": _handler},
    )

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "CANARY_ACTIVATION_REVIEW",
            "decision": "approve",
            "approval_id": "approval-1",
            "apply_job_key": "apply-job-1",
            "trace_id": "trace-apply-1",
        },
        now_ts="2026-04-11T12:40:00+09:00",
    )

    stored_group = store.get_check_group(group_id=int(group["group_id"]))
    stored_actions = store.list_check_actions(group_id=int(group["group_id"]))

    assert payload["summary"]["trigger_state"] == "APPLY_EXECUTED"
    assert stored_group["status"] == "applied"
    assert stored_actions[0]["action"] == "apply"
    assert stored_actions[0]["approval_id"] == "approval-1"
    assert payload["apply_result"]["summary"]["apply_state"] == "ACTIVE_ACTION_ONLY_CANARY"


def test_apply_executor_rejects_non_approved_group(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path, status="held", held_by="1001", held_at="2026-04-11T12:31:00+09:00")
    executor = ApplyExecutor(telegram_state_store=store, handlers={})

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "CANARY_ACTIVATION_REVIEW",
            "decision": "approve",
            "approval_id": "approval-1",
        }
    )

    assert payload["summary"]["trigger_state"] == "GROUP_NOT_APPROVED"
    assert store.get_check_group(group_id=int(group["group_id"]))["status"] == "held"


def test_apply_executor_ignores_non_approve_decisions(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path)
    executor = ApplyExecutor(telegram_state_store=store, handlers={})

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "CANARY_ACTIVATION_REVIEW",
            "decision": "hold",
            "approval_id": "approval-1",
        }
    )

    assert payload["summary"]["trigger_state"] == "DECISION_NOT_APPLICABLE"
    assert store.get_check_group(group_id=int(group["group_id"]))["status"] == "approved"


def test_apply_executor_requires_registered_handler(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path, review_type="CANARY_CLOSEOUT_REVIEW")
    executor = ApplyExecutor(telegram_state_store=store, handlers={})

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "CANARY_CLOSEOUT_REVIEW",
            "decision": "approve",
            "approval_id": "approval-1",
        }
    )

    assert payload["summary"]["trigger_state"] == "NO_APPLY_HANDLER"
    assert store.get_check_group(group_id=int(group["group_id"]))["status"] == "approved"


def test_apply_executor_ignores_duplicate_apply_for_same_approval_id(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path)

    def _handler(**_: object) -> dict[str, object]:
        return {"summary": {"apply_state": "ACTIVE_ACTION_ONLY_CANARY"}}

    executor = ApplyExecutor(
        telegram_state_store=store,
        handlers={"CANARY_ACTIVATION_REVIEW": _handler},
    )

    first = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "CANARY_ACTIVATION_REVIEW",
            "decision": "approve",
            "approval_id": "approval-1",
            "apply_job_key": "apply-job-1",
        }
    )
    second = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "CANARY_ACTIVATION_REVIEW",
            "decision": "approve",
            "approval_id": "approval-1",
            "apply_job_key": "apply-job-1",
        }
    )

    stored_actions = store.list_check_actions(group_id=int(group["group_id"]))

    assert first["summary"]["trigger_state"] == "APPLY_EXECUTED"
    assert second["summary"]["trigger_state"] == "DUPLICATE_APPLY_IGNORED"
    assert len(stored_actions) == 1


def test_apply_executor_reports_handler_error_without_marking_applied(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path)

    def _handler(**_: object) -> dict[str, object]:
        raise RuntimeError("apply failed")

    executor = ApplyExecutor(
        telegram_state_store=store,
        handlers={"CANARY_ACTIVATION_REVIEW": _handler},
    )

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "CANARY_ACTIVATION_REVIEW",
            "decision": "approve",
            "approval_id": "approval-1",
            "apply_job_key": "apply-job-1",
        }
    )

    assert payload["summary"]["trigger_state"] == "HANDLER_ERROR"
    assert store.get_check_group(group_id=int(group["group_id"]))["status"] == "approved"
    assert store.list_check_actions(group_id=int(group["group_id"])) == []


def test_apply_executor_supports_registered_non_canary_review_type(tmp_path: Path) -> None:
    store, group = _build_store_with_group(
        tmp_path,
        group_key="STATE25_WEIGHT_PATCH::BTCUSD::READY",
        review_type="STATE25_WEIGHT_PATCH_REVIEW",
        check_kind="state25_weight_patch_review",
        action_target="state25_weight_patch_log_only",
        symbol="BTCUSD",
    )

    def _handler(**_: object) -> dict[str, object]:
        return {
            "summary": {
                "apply_state": "STATE25_WEIGHT_PATCH_LOG_ONLY_ACTIVE",
                "recommended_next_action": "collect_state25_log_only_weight_patch_evidence",
            }
        }

    executor = ApplyExecutor(
        telegram_state_store=store,
        handlers={"STATE25_WEIGHT_PATCH_REVIEW": _handler},
    )

    payload = executor.execute_approval(
        approval_event_payload={
            "group_id": group["group_id"],
            "review_type": "STATE25_WEIGHT_PATCH_REVIEW",
            "decision": "approve",
            "approval_id": "approval-1",
            "apply_job_key": "apply-job-1",
        }
    )

    assert payload["summary"]["trigger_state"] == "APPLY_EXECUTED"
    assert payload["apply_result"]["summary"]["apply_state"] == "STATE25_WEIGHT_PATCH_LOG_ONLY_ACTIVE"
