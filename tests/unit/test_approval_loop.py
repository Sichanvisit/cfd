from __future__ import annotations

from pathlib import Path

from backend.services.approval_loop import ApprovalLoop
from backend.services.event_bus import ApprovalReceived, EventBus
from backend.services.telegram_state_store import TelegramStateStore


def _build_store_with_group(tmp_path: Path, **overrides: object) -> tuple[TelegramStateStore, dict[str, object]]:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    base_kwargs: dict[str, object] = {
        "group_key": "BTCUSD::action_only_canary::activation",
        "status": "pending",
        "symbol": "BTCUSD",
        "check_kind": "activation_review",
        "review_type": "CANARY_ACTIVATION_REVIEW",
        "approval_id": "approval-1",
        "scope_key": "BTCUSD::action_only_canary::activation",
        "trace_id": "trace-activation-1",
        "apply_job_key": "apply-job-1",
        "decision_deadline_ts": "2026-04-11T13:00:00+09:00",
        "pending_count": 1,
    }
    base_kwargs.update(overrides)
    group = store.upsert_check_group(**base_kwargs)
    return store, group


def test_approval_loop_approves_pending_group_and_publishes_event(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path)
    bus = EventBus()
    seen_events: list[dict[str, object]] = []
    bus.subscribe(ApprovalReceived, lambda event: seen_events.append(dict(event.payload)))
    loop = ApprovalLoop(
        telegram_state_store=store,
        event_bus=bus,
        allowed_user_ids={"1001"},
    )

    payload = loop.process_callback(
        decision="approve",
        group_id=int(group["group_id"]),
        telegram_user_id="1001",
        telegram_username="ops_user",
        callback_query_id="cbq-approve-1",
        approval_id="approval-1",
        note="looks good",
        now_ts="2026-04-11T12:30:00+09:00",
    )

    stored_group = store.get_check_group(group_id=int(group["group_id"]))
    stored_actions = store.list_check_actions(group_id=int(group["group_id"]))

    assert payload["summary"]["trigger_state"] == "APPROVAL_RECORDED"
    assert stored_group["status"] == "approved"
    assert stored_group["approved_by"] == "1001"
    assert stored_group["approved_at"] == "2026-04-11T12:30:00+09:00"
    assert stored_group["pending_count"] == 0
    assert stored_actions[0]["action"] == "approve"
    assert bus.pending_count() == 1

    bus.drain()
    assert seen_events == [
        {
            "group_id": stored_group["group_id"],
            "group_key": stored_group["group_key"],
            "review_type": "CANARY_ACTIVATION_REVIEW",
            "scope_key": "BTCUSD::action_only_canary::activation",
            "approval_id": "approval-1",
            "apply_job_key": "apply-job-1",
            "decision": "approve",
            "previous_status": "pending",
            "next_status": "approved",
            "telegram_user_id": "1001",
            "telegram_username": "ops_user",
        }
    ]


def test_approval_loop_rejects_unauthorized_user_without_mutating_group(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path)
    bus = EventBus()
    loop = ApprovalLoop(
        telegram_state_store=store,
        event_bus=bus,
        allowed_user_ids={"1001"},
    )

    payload = loop.process_callback(
        decision="hold",
        group_key=str(group["group_key"]),
        telegram_user_id="9999",
        telegram_username="outsider",
        callback_query_id="cbq-hold-unauthorized",
        approval_id="approval-1",
        now_ts="2026-04-11T12:35:00+09:00",
    )

    stored_group = store.get_check_group(group_id=int(group["group_id"]))

    assert payload["summary"]["trigger_state"] == "UNAUTHORIZED_USER"
    assert stored_group["status"] == "pending"
    assert store.list_check_actions(group_id=int(group["group_id"])) == []
    assert bus.pending_count() == 0


def test_approval_loop_ignores_duplicate_callback_query_id_idempotently(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path)
    bus = EventBus()
    loop = ApprovalLoop(
        telegram_state_store=store,
        event_bus=bus,
        allowed_user_ids={"1001"},
    )

    first = loop.process_callback(
        decision="hold",
        group_key=str(group["group_key"]),
        telegram_user_id="1001",
        telegram_username="ops_user",
        callback_query_id="cbq-hold-1",
        approval_id="approval-1",
        note="wait a bit",
        now_ts="2026-04-11T12:20:00+09:00",
    )
    second = loop.process_callback(
        decision="approve",
        group_key=str(group["group_key"]),
        telegram_user_id="1001",
        telegram_username="ops_user",
        callback_query_id="cbq-hold-1",
        approval_id="approval-1",
        note="duplicate callback",
        now_ts="2026-04-11T12:21:00+09:00",
    )

    stored_actions = store.list_check_actions(group_id=int(group["group_id"]))
    stored_group = store.get_check_group(group_id=int(group["group_id"]))

    assert first["summary"]["trigger_state"] == "APPROVAL_RECORDED"
    assert second["summary"]["trigger_state"] == "DUPLICATE_CALLBACK_IGNORED"
    assert len(stored_actions) == 1
    assert stored_group["status"] == "held"
    assert bus.pending_count() == 1


def test_approval_loop_rejects_stale_approval_id_without_mutation(tmp_path: Path) -> None:
    store, group = _build_store_with_group(tmp_path, approval_id="approval-current")
    bus = EventBus()
    loop = ApprovalLoop(
        telegram_state_store=store,
        event_bus=bus,
        allowed_user_ids={"1001"},
    )

    payload = loop.process_callback(
        decision="reject",
        group_key=str(group["group_key"]),
        telegram_user_id="1001",
        telegram_username="ops_user",
        callback_query_id="cbq-stale-1",
        approval_id="approval-old",
        now_ts="2026-04-11T12:36:00+09:00",
    )

    stored_group = store.get_check_group(group_id=int(group["group_id"]))

    assert payload["summary"]["trigger_state"] == "APPROVAL_ID_MISMATCH"
    assert stored_group["status"] == "pending"
    assert stored_group["approval_id"] == "approval-current"
    assert store.list_check_actions(group_id=int(group["group_id"])) == []
    assert bus.pending_count() == 0


def test_approval_loop_expires_overdue_group_before_processing_decision(tmp_path: Path) -> None:
    store, group = _build_store_with_group(
        tmp_path,
        decision_deadline_ts="2026-04-11T11:59:00+09:00",
    )
    bus = EventBus()
    loop = ApprovalLoop(
        telegram_state_store=store,
        event_bus=bus,
        allowed_user_ids={"1001"},
    )

    payload = loop.process_callback(
        decision="approve",
        group_key=str(group["group_key"]),
        telegram_user_id="1001",
        telegram_username="ops_user",
        callback_query_id="cbq-expire-1",
        approval_id="approval-1",
        note="too late",
        now_ts="2026-04-11T12:10:00+09:00",
    )

    stored_group = store.get_check_group(group_id=int(group["group_id"]))
    stored_actions = store.list_check_actions(group_id=int(group["group_id"]))

    assert payload["summary"]["trigger_state"] == "APPROVAL_EXPIRED"
    assert stored_group["status"] == "expired"
    assert stored_group["expires_at"] == "2026-04-11T12:10:00+09:00"
    assert stored_actions[0]["action"] == "expire"
    assert bus.pending_count() == 0


def test_approval_loop_allows_held_group_to_be_approved_later(tmp_path: Path) -> None:
    store, group = _build_store_with_group(
        tmp_path,
        status="held",
        held_by="1001",
        held_at="2026-04-11T12:00:00+09:00",
    )
    bus = EventBus()
    loop = ApprovalLoop(
        telegram_state_store=store,
        event_bus=bus,
        allowed_user_ids={"1001"},
    )

    payload = loop.process_callback(
        decision="approve",
        group_key=str(group["group_key"]),
        telegram_user_id="1001",
        telegram_username="ops_user",
        callback_query_id="cbq-held-approve-1",
        approval_id="approval-1",
        now_ts="2026-04-11T12:40:00+09:00",
    )

    stored_group = store.get_check_group(group_id=int(group["group_id"]))

    assert payload["summary"]["trigger_state"] == "APPROVAL_RECORDED"
    assert payload["decision_result"]["previous_status"] == "held"
    assert stored_group["status"] == "approved"
    assert stored_group["approved_at"] == "2026-04-11T12:40:00+09:00"
