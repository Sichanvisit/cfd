from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.services.telegram_state_store import TelegramStateStore


def test_state_store_bootstraps_core_tables(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    with sqlite3.connect(store.db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }

    assert "check_groups" in table_names
    assert "check_events" in table_names
    assert "check_actions" in table_names
    assert "telegram_messages" in table_names
    assert "poller_offsets" in table_names


def test_upsert_check_group_inserts_and_updates_same_group_key(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    created = store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::rollback",
        status="pending",
        symbol="BTCUSD",
        check_kind="rollback_review",
        review_type="CANARY_ROLLBACK_REVIEW",
        scope_key="BTCUSD::action_only_canary::rollback",
        trace_id="trace-1",
        reason_summary="rollback candidate detected",
        pending_count=1,
    )
    updated = store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::rollback",
        status="held",
        symbol="BTCUSD",
        check_kind="rollback_review",
        review_type="CANARY_ROLLBACK_REVIEW",
        scope_key="BTCUSD::action_only_canary::rollback",
        trace_id="trace-2",
        reason_summary="operator hold",
        pending_count=3,
        held_by="ops-user",
        held_at="2026-04-11T12:00:00+09:00",
    )

    fetched = store.get_check_group(group_key="BTCUSD::action_only_canary::rollback")

    assert created["group_id"] == updated["group_id"] == fetched["group_id"]
    assert fetched["status"] == "held"
    assert fetched["trace_id"] == "trace-2"
    assert fetched["pending_count"] == 3
    assert fetched["held_by"] == "ops-user"


def test_append_check_event_updates_pending_count_and_last_event_ts(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = store.upsert_check_group(
        group_key="NAS100::action_only_canary::closeout",
        status="pending",
        symbol="NAS100",
        review_type="CANARY_CLOSEOUT_REVIEW",
        scope_key="NAS100::action_only_canary::closeout",
    )

    event = store.append_check_event(
        group_id=group["group_id"],
        source_type="governance_cycle",
        source_ref="watch-governance-1",
        symbol="NAS100",
        payload={"closeout_state": "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW"},
        event_ts="2026-04-11T12:10:00+09:00",
        trace_id="trace-closeout",
    )

    fetched = store.get_check_group(group_id=group["group_id"])

    assert event["group_id"] == group["group_id"]
    assert event["source_type"] == "governance_cycle"
    assert fetched["pending_count"] == 1
    assert fetched["last_event_ts"] == "2026-04-11T12:10:00+09:00"


def test_append_check_action_records_callback_history(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = store.upsert_check_group(
        group_key="XAUUSD::action_only_canary::activation",
        status="pending",
        symbol="XAUUSD",
        review_type="CANARY_ACTIVATION_REVIEW",
        scope_key="XAUUSD::action_only_canary::activation",
    )

    action = store.append_check_action(
        group_id=group["group_id"],
        telegram_user_id=123456,
        telegram_username="codex_ops",
        action="approve",
        note="looks safe",
        callback_query_id="cbq-1",
        approval_id="approval-1",
        trace_id="trace-approve",
    )

    assert action["group_id"] == group["group_id"]
    assert action["telegram_user_id"] == "123456"
    assert action["action"] == "approve"
    assert action["approval_id"] == "approval-1"


def test_list_recent_check_actions_filters_by_action_descending(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    group = store.upsert_check_group(
        group_key="BTCUSD::action_only_canary::rollback",
        status="approved",
        symbol="BTCUSD",
        review_type="CANARY_ROLLBACK_REVIEW",
        scope_key="BTCUSD::action_only_canary::rollback",
    )

    store.append_check_action(
        group_id=group["group_id"],
        telegram_user_id="1001",
        telegram_username="ops",
        action="approve",
        note="ok",
        callback_query_id="cbq-1",
        approval_id="approval-1",
    )
    apply_record = store.append_check_action(
        group_id=group["group_id"],
        telegram_user_id="system_apply_executor",
        telegram_username="apply_executor",
        action="apply",
        note="done",
        approval_id="approval-1",
    )

    recent_apply = store.list_recent_check_actions(action="apply", limit=5)

    assert len(recent_apply) == 1
    assert recent_apply[0]["action_id"] == apply_record["action_id"]
    assert recent_apply[0]["action"] == "apply"


def test_upsert_telegram_message_reuses_same_entity_route_key(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    first = store.upsert_telegram_message(
        entity_type="check_group",
        entity_id="42",
        route_key="check",
        chat_id="-1001",
        topic_id="7",
        telegram_message_id="100",
        message_kind="check_prompt",
        content_hash="hash-a",
        is_editable=True,
    )
    second = store.upsert_telegram_message(
        entity_type="check_group",
        entity_id="42",
        route_key="check",
        chat_id="-1001",
        topic_id="7",
        telegram_message_id="101",
        message_kind="check_prompt",
        content_hash="hash-b",
        is_editable=False,
    )

    fetched = store.get_telegram_message(
        entity_type="check_group",
        entity_id="42",
        route_key="check",
        message_kind="check_prompt",
    )

    assert first["message_row_id"] == second["message_row_id"] == fetched["message_row_id"]
    assert fetched["telegram_message_id"] == "101"
    assert fetched["content_hash"] == "hash-b"
    assert fetched["is_editable"] is False


def test_set_and_get_poller_offset_round_trips(tmp_path: Path) -> None:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")

    store.set_poller_offset(stream_key="telegram-main", last_update_id=100)
    updated = store.set_poller_offset(stream_key="telegram-main", last_update_id=125)
    fetched = store.get_poller_offset(stream_key="telegram-main")

    assert updated["last_update_id"] == 125
    assert fetched["stream_key"] == "telegram-main"
    assert fetched["last_update_id"] == 125
