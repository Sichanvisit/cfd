from __future__ import annotations

from pathlib import Path

from backend.services.apply_executor import ApplyExecutor
from backend.services.approval_loop import ApprovalLoop
from backend.services.event_bus import EventBus
from backend.services.telegram_approval_bridge import TelegramApprovalBridge
from backend.services.telegram_notification_hub import TelegramNotificationHub
from backend.services.telegram_state_store import TelegramStateStore
from backend.services.telegram_update_poller import TelegramUpdatePoller


def test_update_poller_processes_bridge_approval_and_syncs_terminal_prompt(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    bus = EventBus()
    approval_loop = ApprovalLoop(
        telegram_state_store=store,
        event_bus=bus,
        allowed_user_ids={"1001"},
    )
    apply_executor = ApplyExecutor(telegram_state_store=store)
    apply_executor.register_handler(
        "CANARY_ACTIVATION_REVIEW",
        lambda **_: {
            "summary": {
                "apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                "recommended_next_action": "start_first_canary_window_observation",
            }
        },
    )
    send_calls: list[dict[str, object]] = []
    edit_calls: list[dict[str, object]] = []
    ack_calls: list[dict[str, object]] = []

    def _fake_send(message: str, **kwargs: object) -> dict[str, object]:
        send_calls.append({"message": message, **kwargs})
        return {
            "result": {
                "message_id": 321,
                "message_thread_id": 77,
                "chat": {"id": "chat-check"},
            }
        }

    def _fake_edit(**kwargs: object) -> dict[str, object]:
        edit_calls.append(dict(kwargs))
        return {
            "result": {
                "message_id": 321,
                "message_thread_id": 77,
                "chat": {"id": "chat-check"},
            }
        }

    def _fake_answer(callback_query_id: str, **kwargs: object) -> dict[str, object]:
        ack_calls.append({"callback_query_id": callback_query_id, **kwargs})
        return {"ok": True}

    hub = TelegramNotificationHub(
        telegram_state_store=store,
        send_sync=_fake_send,
        edit_text=_fake_edit,
    )
    bridge = TelegramApprovalBridge(
        telegram_state_store=store,
        event_bus=bus,
        approval_loop=approval_loop,
        apply_executor=apply_executor,
        dispatch_handler=hub.handle_dispatch_record,
    )
    bridge.handle_governance_action_needed(
        governance_payload={
            "review_type": "CANARY_ACTIVATION_REVIEW",
            "governance_action": "canary_activation_review",
            "scope_key": "BTCUSD::action_only_canary::activation",
            "symbol": "BTCUSD",
            "activation_apply_state": "HOLD_CANARY_ACTIVATION_APPLY",
            "first_window_status": "AWAIT_FIRST_CANARY_WINDOW_RESULTS",
            "live_observation_ready": False,
            "observed_window_row_count": 0,
            "active_trigger_count": 1,
        },
        trace_id="trace-bridge-1",
        occurred_at="2026-04-11T12:00:00+09:00",
    )
    group = store.get_check_group(group_key="BTCUSD::action_only_canary::activation")
    poller = TelegramUpdatePoller(
        telegram_state_store=store,
        telegram_approval_bridge=bridge,
        telegram_notification_hub=hub,
        answer_callback_query=_fake_answer,
    )

    result = poller.handle_callback_query(
        {
            "id": "cbq-1",
            "data": f"tgbridge:approve:{group['group_id']}:{group['approval_id']}",
            "from": {"id": 1001, "username": "ops_user"},
        },
        now_ts="2026-04-11T12:05:00+09:00",
    )
    actions = store.list_check_actions(group_id=int(group["group_id"]), limit=10)
    group_after = store.get_check_group(group_id=int(group["group_id"]))

    assert result["summary"]["trigger_state"] == "BRIDGE_CALLBACK_PROCESSED"
    assert group_after["status"] == "applied"
    assert [action["action"] for action in actions] == ["approve", "apply"]
    assert len(send_calls) == 2
    assert send_calls[0]["route"] == "report"
    assert send_calls[1]["route"] == "check"
    assert len(edit_calls) == 1
    assert ack_calls[0]["callback_query_id"] == "cbq-1"


def test_update_poller_poll_once_updates_offset_for_bridge_callbacks(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    poller = TelegramUpdatePoller(
        telegram_state_store=store,
        get_updates=lambda **_: [
            {"update_id": 11, "callback_query": {"id": "cbq-non", "data": "tgops:approve:card-1"}},
            {"update_id": 12, "callback_query": {"id": "cbq-bridge", "data": "tgbridge:approve:1:approval-1"}},
        ],
        answer_callback_query=lambda *args, **kwargs: {},
    )

    result = poller.poll_once(timeout_sec=0, now_ts="2026-04-11T12:00:00+09:00")
    offset_row = store.get_poller_offset(stream_key="checkpoint_improvement_bridge")

    assert result["summary"]["trigger_state"] == "POLL_COMPLETED"
    assert result["summary"]["processed_bridge_callback_count"] == 1
    assert offset_row["last_update_id"] == 12
