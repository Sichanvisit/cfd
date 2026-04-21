from __future__ import annotations

from pathlib import Path

from backend.services.telegram_notification_hub import TelegramNotificationHub
from backend.services.telegram_state_store import TelegramStateStore


def _build_group(store: TelegramStateStore) -> dict[str, object]:
    return store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::activation",
        status="pending",
        symbol="BTCUSD",
        review_type="CANARY_ACTIVATION_REVIEW",
        reason_summary="BTC canary activation review needed",
        scope_note="BTCUSD activation scope",
        decision_deadline_ts="2026-04-11T12:10:00+09:00",
        approval_id="approval-btc-1",
    )


def test_notification_hub_sends_new_check_prompt_and_persists_message(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = _build_group(store)
    sent_calls: list[dict[str, object]] = []

    def _fake_send(message: str, **kwargs: object) -> dict[str, object]:
        sent_calls.append({"message": message, **kwargs})
        return {
            "result": {
                "message_id": 321,
                "message_thread_id": 77,
                "chat": {"id": "chat-check"},
            }
        }

    hub = TelegramNotificationHub(
        telegram_state_store=store,
        send_sync=_fake_send,
        edit_text=lambda **_: {},
    )

    result = hub.sync_check_group_prompt(group_id=int(group["group_id"]))
    message_row = store.get_telegram_message(
        entity_type="check_group",
        entity_id=str(group["group_id"]),
        route_key="check",
        message_kind="check_prompt",
    )
    refreshed_group = store.get_check_group(group_id=int(group["group_id"]))

    assert result["summary"]["trigger_state"] == "PROMPT_SENT"
    assert len(sent_calls) == 1
    assert sent_calls[0]["route"] == "check"
    assert "[개선안 체크]" in str(sent_calls[0]["message"])
    assert "결정 기한:" in str(sent_calls[0]["message"])
    assert message_row["telegram_message_id"] == "321"
    assert message_row["chat_id"] == "chat-check"
    assert refreshed_group["last_prompt_message_id"] == "321"
    assert refreshed_group["last_prompt_chat_id"] == "chat-check"


def test_notification_hub_edits_existing_prompt_when_group_changes(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = _build_group(store)
    edit_calls: list[dict[str, object]] = []

    def _fake_send(message: str, **kwargs: object) -> dict[str, object]:
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

    hub = TelegramNotificationHub(
        telegram_state_store=store,
        send_sync=_fake_send,
        edit_text=_fake_edit,
    )
    hub.sync_check_group_prompt(group_id=int(group["group_id"]))
    store.update_check_group(
        group_id=int(group["group_id"]),
        status="approved",
        approved_by="@ops",
        approved_at="2026-04-11T12:04:00+09:00",
    )

    result = hub.sync_check_group_prompt(group_id=int(group["group_id"]))
    refreshed_group = store.get_check_group(group_id=int(group["group_id"]))

    assert result["summary"]["trigger_state"] == "PROMPT_EDITED"
    assert len(edit_calls) == 1
    assert edit_calls[0]["chat_id"] == "chat-check"
    assert edit_calls[0]["message_id"] == 321
    assert edit_calls[0]["reply_markup"] is None
    assert refreshed_group["last_prompt_message_id"] == "321"


def test_notification_hub_dispatches_review_report_to_report_route(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = _build_group(store)
    sent_calls: list[dict[str, object]] = []

    def _fake_send(message: str, **kwargs: object) -> dict[str, object]:
        sent_calls.append({"message": message, **kwargs})
        return {
            "result": {
                "message_id": 654 if kwargs.get("route") == "report" else 321,
                "message_thread_id": 12 if kwargs.get("route") == "report" else 77,
                "chat": {"id": "chat-report" if kwargs.get("route") == "report" else "chat-check"},
            }
        }

    hub = TelegramNotificationHub(
        telegram_state_store=store,
        send_sync=_fake_send,
        edit_text=lambda **_: {},
    )

    result = hub.handle_dispatch_record(
        {
            "group_after": group,
            "report_envelope": {
                "title_ko": "학습 반영 제안 | 가중치 조정",
                "lines_ko": [
                    "관찰 장면: 윗꼬리 비중 과다",
                    "조정 항목:",
                    "- 윗꼬리 반응 비중: 기준 x1.00 -> 제안 x0.70 (하향 x0.70)",
                ],
            },
        }
    )
    report_row = store.get_telegram_message(
        entity_type="check_group",
        entity_id=str(group["group_id"]),
        route_key="report",
        message_kind="review_report",
    )

    assert len(sent_calls) == 2
    assert sent_calls[0]["route"] == "report"
    assert "[학습 반영 제안 | 가중치 조정]" in str(sent_calls[0]["message"])
    assert result["report_delivery"]["telegram_message_id"] == "654"
    assert report_row["telegram_message_id"] == "654"
