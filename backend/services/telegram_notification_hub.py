from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Callable, Mapping

from backend.integrations import notifier
from backend.services.telegram_route_ownership_policy import (
    OWNER_IMPROVEMENT_CHECK_INBOX,
    OWNER_IMPROVEMENT_REPORT_TOPIC,
    validate_telegram_route_ownership,
)
from backend.services.telegram_state_store import TelegramStateStore


TELEGRAM_NOTIFICATION_HUB_CONTRACT_VERSION = "telegram_notification_hub_v0"
ACTIONABLE_GROUP_STATUSES = {"pending", "held"}


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


def _content_hash(text: str, reply_markup: object | None) -> str:
    markup_text = ""
    if reply_markup not in (None, "", {}, []):
        try:
            markup_text = json.dumps(reply_markup, ensure_ascii=False, sort_keys=True)
        except Exception:
            markup_text = str(reply_markup)
    digest = hashlib.sha1(f"{text}\n{markup_text}".encode("utf-8")).hexdigest()
    return digest


class TelegramNotificationHub:
    def __init__(
        self,
        *,
        telegram_state_store: TelegramStateStore | None = None,
        send_sync: Callable[..., dict[str, Any] | None] = notifier.send_telegram_sync,
        edit_text: Callable[..., dict[str, Any] | None] = notifier.edit_telegram_message_text,
    ) -> None:
        self._store = telegram_state_store or TelegramStateStore()
        self._send_sync = send_sync
        self._edit_text = edit_text

    @property
    def telegram_state_store(self) -> TelegramStateStore:
        return self._store

    def handle_dispatch_record(self, dispatch_record: Mapping[str, Any] | None) -> dict[str, Any]:
        record = _mapping(dispatch_record)
        group_after = _mapping(record.get("group_after"))
        group_id = _to_int(group_after.get("group_id"))
        report_result = {}
        report_envelope = _mapping(record.get("report_envelope"))
        if group_id > 0 and report_envelope:
            report_result = self.sync_review_report(
                group_id=group_id,
                report_envelope=report_envelope,
            )
        check_result = self.sync_check_group_prompt(group_id=group_id)
        return {
            "summary": dict(_mapping(check_result.get("summary"))),
            "group": _mapping(check_result.get("group")),
            "delivery": _mapping(check_result.get("delivery")),
            "report_delivery": _mapping(report_result.get("delivery")),
        }

    def sync_check_group_prompt(self, *, group_id: int) -> dict[str, Any]:
        group = self._store.get_check_group(group_id=group_id)
        if not group:
            return self._build_result(
                trigger_state="GROUP_NOT_FOUND",
                group=group,
                delivery={},
            )

        text = self.render_check_group_text(group)
        reply_markup = self.build_check_group_reply_markup(group)
        content_hash = _content_hash(text, reply_markup)
        entity_id = str(group_id)
        existing_message = self._store.get_telegram_message(
            entity_type="check_group",
            entity_id=entity_id,
            route_key="check",
            message_kind="check_prompt",
        )
        existing_message_id = _to_text(existing_message.get("telegram_message_id"))
        existing_chat_id = _to_text(existing_message.get("chat_id"))
        existing_topic_id = _to_text(existing_message.get("topic_id"))
        existing_hash = _to_text(existing_message.get("content_hash"))

        if existing_message_id and existing_chat_id and existing_hash == content_hash:
            return self._build_result(
                trigger_state="PROMPT_ALREADY_CURRENT",
                group=group,
                delivery={
                    "chat_id": existing_chat_id,
                    "topic_id": existing_topic_id,
                    "telegram_message_id": existing_message_id,
                    "content_hash": content_hash,
                    "delivery_mode": "noop",
                },
            )

        delivery_response: dict[str, Any] = {}
        trigger_state = "PROMPT_SENT"
        validate_telegram_route_ownership(
            owner_key=OWNER_IMPROVEMENT_CHECK_INBOX,
            route="check",
        )
        if existing_message_id and existing_chat_id:
            edit_response = self._edit_text(
                chat_id=existing_chat_id,
                message_id=_to_int(existing_message_id),
                text=text,
                thread_id=existing_topic_id,
                parse_mode=None,
                reply_markup=reply_markup,
            )
            if isinstance(edit_response, Mapping):
                delivery_response = dict(edit_response)
                trigger_state = "PROMPT_EDITED"

        if not delivery_response:
            send_response = self._send_sync(
                text,
                route="check",
                parse_mode=None,
                reply_markup=reply_markup,
            )
            if isinstance(send_response, Mapping):
                delivery_response = dict(send_response)
                trigger_state = "PROMPT_SENT"

        delivery = self._extract_delivery(
            response=delivery_response,
            fallback_chat_id=existing_chat_id,
            fallback_topic_id=existing_topic_id,
            fallback_message_id=existing_message_id,
            content_hash=content_hash,
        )
        if not delivery.get("telegram_message_id") or not delivery.get("chat_id"):
            return self._build_result(
                trigger_state="PROMPT_DELIVERY_FAILED",
                group=group,
                delivery=delivery,
            )

        self._store.upsert_telegram_message(
            entity_type="check_group",
            entity_id=entity_id,
            route_key="check",
            chat_id=delivery["chat_id"],
            topic_id=delivery["topic_id"],
            telegram_message_id=delivery["telegram_message_id"],
            message_kind="check_prompt",
            content_hash=content_hash,
            is_editable=True,
        )
        self._store.update_check_group(
            group_id=group_id,
            last_prompt_message_id=delivery["telegram_message_id"],
            last_prompt_chat_id=delivery["chat_id"],
            last_prompt_topic_id=delivery["topic_id"],
        )
        return self._build_result(
            trigger_state=trigger_state,
            group=self._store.get_check_group(group_id=group_id),
            delivery=delivery,
        )

    def sync_review_report(
        self,
        *,
        group_id: int,
        report_envelope: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        group = self._store.get_check_group(group_id=group_id)
        if not group:
            return self._build_result(
                trigger_state="GROUP_NOT_FOUND",
                group=group,
                delivery={},
            )

        envelope = _mapping(report_envelope)
        text = self.render_review_report_text(group, envelope)
        content_hash = _content_hash(text, None)
        entity_id = str(group_id)
        existing_message = self._store.get_telegram_message(
            entity_type="check_group",
            entity_id=entity_id,
            route_key="report",
            message_kind="review_report",
        )
        existing_message_id = _to_text(existing_message.get("telegram_message_id"))
        existing_chat_id = _to_text(existing_message.get("chat_id"))
        existing_topic_id = _to_text(existing_message.get("topic_id"))
        existing_hash = _to_text(existing_message.get("content_hash"))

        if existing_message_id and existing_chat_id and existing_hash == content_hash:
            return self._build_result(
                trigger_state="REPORT_ALREADY_CURRENT",
                group=group,
                delivery={
                    "chat_id": existing_chat_id,
                    "topic_id": existing_topic_id,
                    "telegram_message_id": existing_message_id,
                    "content_hash": content_hash,
                    "delivery_mode": "noop",
                },
            )

        delivery_response: dict[str, Any] = {}
        trigger_state = "REPORT_SENT"
        validate_telegram_route_ownership(
            owner_key=OWNER_IMPROVEMENT_REPORT_TOPIC,
            route="report",
        )
        if existing_message_id and existing_chat_id:
            edit_response = self._edit_text(
                chat_id=existing_chat_id,
                message_id=_to_int(existing_message_id),
                text=text,
                thread_id=existing_topic_id,
                parse_mode=None,
                reply_markup=None,
            )
            if isinstance(edit_response, Mapping):
                delivery_response = dict(edit_response)
                trigger_state = "REPORT_EDITED"

        if not delivery_response:
            send_response = self._send_sync(
                text,
                route="report",
                parse_mode=None,
                reply_markup=None,
            )
            if isinstance(send_response, Mapping):
                delivery_response = dict(send_response)
                trigger_state = "REPORT_SENT"

        delivery = self._extract_delivery(
            response=delivery_response,
            fallback_chat_id=existing_chat_id,
            fallback_topic_id=existing_topic_id,
            fallback_message_id=existing_message_id,
            content_hash=content_hash,
        )
        if not delivery.get("telegram_message_id") or not delivery.get("chat_id"):
            return self._build_result(
                trigger_state="REPORT_DELIVERY_FAILED",
                group=group,
                delivery=delivery,
            )

        self._store.upsert_telegram_message(
            entity_type="check_group",
            entity_id=entity_id,
            route_key="report",
            chat_id=delivery["chat_id"],
            topic_id=delivery["topic_id"],
            telegram_message_id=delivery["telegram_message_id"],
            message_kind="review_report",
            content_hash=content_hash,
            is_editable=True,
        )
        return self._build_result(
            trigger_state=trigger_state,
            group=group,
            delivery=delivery,
        )

    def render_check_group_text(self, group: Mapping[str, Any] | None) -> str:
        row = _mapping(group)
        status_raw = _to_text(row.get("status"), "pending").lower()
        review_type = _to_text(row.get("review_type")).upper()
        lines = [
            f"[개선안 체크] {self._review_type_title_ko(review_type)}",
            f"상태: {self._status_ko(status_raw)}",
            f"대상: {_to_text(row.get('symbol')).upper() or '-'}",
            f"요약: {_to_text(row.get('reason_summary'), '-')}",
            f"범위: {_to_text(row.get('scope_note'), '-')}",
            f"결정 기한: {_to_text(row.get('decision_deadline_ts'), '-')}",
        ]
        approved_by = _to_text(row.get("approved_by"))
        approved_at = _to_text(row.get("approved_at"))
        rejected_by = _to_text(row.get("rejected_by"))
        rejected_at = _to_text(row.get("rejected_at"))
        held_by = _to_text(row.get("held_by"))
        held_at = _to_text(row.get("held_at"))
        if status_raw == "approved":
            lines.append(f"승인자: {approved_by or '-'}")
            lines.append(f"승인 시각: {approved_at or '-'}")
        elif status_raw == "held":
            lines.append(f"보류자: {held_by or '-'}")
            lines.append(f"보류 시각: {held_at or '-'}")
        elif status_raw == "rejected":
            lines.append(f"거부자: {rejected_by or '-'}")
            lines.append(f"거부 시각: {rejected_at or '-'}")
        elif status_raw == "applied":
            lines.append(f"승인자: {approved_by or '-'}")
            lines.append(f"승인 시각: {approved_at or '-'}")
            lines.append("적용 상태: 반영 완료")
        return "\n".join(lines)

    def render_review_report_text(
        self,
        group: Mapping[str, Any] | None,
        report_envelope: Mapping[str, Any] | None,
    ) -> str:
        row = _mapping(group)
        envelope = _mapping(report_envelope)
        title = _to_text(envelope.get("title_ko"), "개선안 보고서")
        lines = [f"[{title}]"]
        for raw_line in list(envelope.get("lines_ko", []) or []):
            text = _to_text(raw_line)
            if text:
                lines.append(text)
        if len(lines) == 1:
            lines.extend(
                [
                    f"요약: {_to_text(row.get('reason_summary'), '-')}",
                    f"범위: {_to_text(row.get('scope_note'), '-')}",
                    f"결정 기한: {_to_text(row.get('decision_deadline_ts'), '-')}",
                ]
            )
        return "\n".join(lines)

    def build_check_group_reply_markup(self, group: Mapping[str, Any] | None) -> dict[str, Any] | None:
        row = _mapping(group)
        if _to_text(row.get("status")).lower() not in ACTIONABLE_GROUP_STATUSES:
            return None
        group_id = _to_int(row.get("group_id"))
        approval_id = _to_text(row.get("approval_id"))
        if group_id <= 0 or not approval_id:
            return None
        return {
            "inline_keyboard": [
                [
                    {"text": "승인", "callback_data": f"tgbridge:approve:{group_id}:{approval_id}"},
                    {"text": "보류", "callback_data": f"tgbridge:hold:{group_id}:{approval_id}"},
                    {"text": "거부", "callback_data": f"tgbridge:reject:{group_id}:{approval_id}"},
                ]
            ]
        }

    def _status_ko(self, status: str) -> str:
        mapping = {
            "pending": "미검토",
            "approved": "승인",
            "held": "보류",
            "rejected": "거부",
            "expired": "만료",
            "applied": "적용 완료",
            "cancelled": "취소",
        }
        return _to_text(mapping.get(status), status or "-")

    def _review_type_title_ko(self, review_type: str) -> str:
        mapping = {
            "CANARY_ACTIVATION_REVIEW": "시험 반영 검토",
            "CANARY_ROLLBACK_REVIEW": "롤백 검토",
            "CANARY_CLOSEOUT_REVIEW": "클로즈아웃 검토",
            "STATE25_WEIGHT_PATCH_REVIEW": "가중치 조정 검토",
        }
        return _to_text(mapping.get(review_type), review_type or "개선안 검토")

    def _extract_delivery(
        self,
        *,
        response: Mapping[str, Any] | None,
        fallback_chat_id: str,
        fallback_topic_id: str,
        fallback_message_id: str,
        content_hash: str,
    ) -> dict[str, Any]:
        result = _mapping(_mapping(response).get("result"))
        chat = _mapping(result.get("chat"))
        return {
            "chat_id": _to_text(chat.get("id"), fallback_chat_id),
            "topic_id": _to_text(result.get("message_thread_id"), fallback_topic_id),
            "telegram_message_id": _to_text(result.get("message_id"), fallback_message_id),
            "content_hash": content_hash,
            "delivery_mode": "edit" if fallback_message_id and result else "send",
        }

    def _build_result(
        self,
        *,
        trigger_state: str,
        group: Mapping[str, Any] | None,
        delivery: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "summary": {
                "contract_version": TELEGRAM_NOTIFICATION_HUB_CONTRACT_VERSION,
                "generated_at": _now_iso(),
                "trigger_state": trigger_state,
                "group_id": _mapping(group).get("group_id"),
                "group_key": _to_text(_mapping(group).get("group_key")),
            },
            "group": _mapping(group),
            "delivery": _mapping(delivery),
        }
