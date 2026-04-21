from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping

from backend.integrations import notifier
from backend.services.telegram_approval_bridge import TelegramApprovalBridge
from backend.services.telegram_notification_hub import TelegramNotificationHub
from backend.services.telegram_state_store import TelegramStateStore


TELEGRAM_UPDATE_POLLER_CONTRACT_VERSION = "telegram_update_poller_v0"
BRIDGE_CALLBACK_PREFIX = "tgbridge"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


class TelegramUpdatePoller:
    def __init__(
        self,
        *,
        telegram_state_store: TelegramStateStore | None = None,
        telegram_approval_bridge: TelegramApprovalBridge | None = None,
        telegram_notification_hub: TelegramNotificationHub | None = None,
        get_updates: Callable[..., list[dict[str, Any]]] = notifier.get_telegram_updates,
        answer_callback_query: Callable[..., dict[str, Any] | None] = notifier.answer_callback_query,
        stream_key: str = "checkpoint_improvement_bridge",
    ) -> None:
        self._store = telegram_state_store or TelegramStateStore()
        self._bridge = telegram_approval_bridge or TelegramApprovalBridge(
            telegram_state_store=self._store,
        )
        self._hub = telegram_notification_hub or TelegramNotificationHub(
            telegram_state_store=self._store,
        )
        self._get_updates = get_updates
        self._answer_callback_query = answer_callback_query
        self._stream_key = _to_text(stream_key, "checkpoint_improvement_bridge")

    def is_bridge_callback_data(self, callback_data: str) -> bool:
        return _to_text(callback_data).startswith(f"{BRIDGE_CALLBACK_PREFIX}:")

    def parse_bridge_callback_data(self, callback_data: str) -> dict[str, Any]:
        text = _to_text(callback_data)
        parts = text.split(":", 3)
        if len(parts) != 4 or parts[0] != BRIDGE_CALLBACK_PREFIX:
            return {}
        decision = _to_text(parts[1]).lower()
        if decision not in {"approve", "hold", "reject"}:
            return {}
        group_id = _to_int(parts[2])
        approval_id = _to_text(parts[3])
        if group_id <= 0 or not approval_id:
            return {}
        return {
            "decision": decision,
            "group_id": group_id,
            "approval_id": approval_id,
        }

    def handle_callback_query(
        self,
        callback_query: Mapping[str, Any] | None,
        *,
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        callback = _mapping(callback_query)
        callback_id = _to_text(callback.get("id"))
        parsed = self.parse_bridge_callback_data(_to_text(callback.get("data")))
        if not parsed:
            return {
                "summary": {
                    "contract_version": TELEGRAM_UPDATE_POLLER_CONTRACT_VERSION,
                    "generated_at": _to_text(now_ts, _now_iso()),
                    "trigger_state": "IGNORED_NON_BRIDGE_CALLBACK",
                    "handled": False,
                }
            }

        from_user = _mapping(callback.get("from"))
        telegram_username = _to_text(from_user.get("username"))
        if telegram_username and not telegram_username.startswith("@"):
            telegram_username = f"@{telegram_username}"
        bridge_result = self._bridge.process_callback(
            decision=_to_text(parsed.get("decision")),
            telegram_user_id=_to_text(from_user.get("id")),
            telegram_username=telegram_username or _to_text(from_user.get("first_name")),
            callback_query_id=callback_id,
            approval_id=_to_text(parsed.get("approval_id")),
            group_id=_to_int(parsed.get("group_id")),
            now_ts=now_ts,
            auto_drain=True,
        )
        group = self._store.get_check_group(group_id=_to_int(parsed.get("group_id")))
        sync_result = self._hub.sync_check_group_prompt(group_id=_to_int(parsed.get("group_id"))) if group else {}
        ack_text, show_alert = self._ack_text(bridge_result=bridge_result, group=group)
        if callback_id:
            self._answer_callback_query(
                callback_id,
                text=ack_text,
                show_alert=show_alert,
            )
        return {
            "summary": {
                "contract_version": TELEGRAM_UPDATE_POLLER_CONTRACT_VERSION,
                "generated_at": _to_text(now_ts, _now_iso()),
                "trigger_state": "BRIDGE_CALLBACK_PROCESSED",
                "handled": True,
                "group_id": _to_int(parsed.get("group_id")),
                "decision": _to_text(parsed.get("decision")),
            },
            "bridge_result": bridge_result,
            "group_after": group,
            "sync_result": sync_result,
        }

    def poll_once(
        self,
        *,
        timeout_sec: int = 25,
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        offset_row = self._store.get_poller_offset(stream_key=self._stream_key)
        offset = _to_int(offset_row.get("last_update_id")) + 1 if offset_row else None
        updates = self._get_updates(
            offset=offset,
            timeout=max(0, int(timeout_sec)),
            allowed_updates=["callback_query"],
        )
        processed_count = 0
        max_update_id = _to_int(offset_row.get("last_update_id"), 0)
        for update in updates:
            update_map = _mapping(update)
            max_update_id = max(max_update_id, _to_int(update_map.get("update_id"), max_update_id))
            callback_query = _mapping(update_map.get("callback_query"))
            if not self.is_bridge_callback_data(_to_text(callback_query.get("data"))):
                continue
            self.handle_callback_query(callback_query, now_ts=now_ts)
            processed_count += 1
        if max_update_id > _to_int(offset_row.get("last_update_id"), 0):
            self._store.set_poller_offset(
                stream_key=self._stream_key,
                last_update_id=max_update_id,
            )
        return {
            "summary": {
                "contract_version": TELEGRAM_UPDATE_POLLER_CONTRACT_VERSION,
                "generated_at": _to_text(now_ts, _now_iso()),
                "trigger_state": "POLL_COMPLETED",
                "processed_bridge_callback_count": processed_count,
                "last_update_id": max_update_id,
            }
        }

    def _ack_text(
        self,
        *,
        bridge_result: Mapping[str, Any] | None,
        group: Mapping[str, Any] | None,
    ) -> tuple[str, bool]:
        approval_summary = _mapping(_mapping(bridge_result).get("approval_result")).get("summary")
        trigger_state = _to_text(_mapping(approval_summary).get("trigger_state"))
        status = _to_text(_mapping(group).get("status")).lower()
        if trigger_state == "UNAUTHORIZED_USER":
            return "이 버튼을 누를 권한이 없습니다.", True
        if trigger_state == "GROUP_NOT_FOUND":
            return "이미 만료됐거나 찾을 수 없는 카드입니다.", True
        if trigger_state == "APPROVAL_ID_MISMATCH":
            return "이 버튼은 이전 승인 버전이라 더 이상 쓸 수 없습니다.", True
        if trigger_state == "DUPLICATE_CALLBACK_IGNORED":
            return "이미 처리된 버튼입니다.", False
        if status == "applied":
            return "승인과 적용까지 기록했습니다.", False
        if status == "approved":
            return "승인을 기록했습니다.", False
        if status == "held":
            return "보류를 기록했습니다.", False
        if status == "rejected":
            return "거부를 기록했습니다.", False
        if status == "expired":
            return "이미 만료된 승인입니다.", True
        return "처리를 기록했습니다.", False
