from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping
from uuid import uuid4

from backend.services.event_bus import ApprovalReceived, EventBus
from backend.services.improvement_status_policy import (
    APPROVAL_ACTIONABLE_STATUSES,
    APPROVAL_ACTION_TO_STATUS,
    APPROVAL_TERMINAL_STATUSES,
)
from backend.services.telegram_state_store import TelegramStateStore


APPROVAL_LOOP_CONTRACT_VERSION = "approval_loop_v0"
APPROVAL_ACTIONS = ("approve", "hold", "reject")
ACTIONABLE_GROUP_STATUSES = APPROVAL_ACTIONABLE_STATUSES
TERMINAL_GROUP_STATUSES = APPROVAL_TERMINAL_STATUSES


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _parse_iso(value: object) -> datetime | None:
    text = _to_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _normalize_decision(value: object) -> str:
    decision = _to_text(value).lower()
    if decision not in APPROVAL_ACTIONS:
        raise ValueError(f"unsupported_approval_decision::{decision or 'empty'}")
    return decision


def _recommended_next_action(trigger_state: str, decision: str = "") -> str:
    mapping = {
        "GROUP_NOT_FOUND": "inspect_callback_payload_or_state_store_group_mapping",
        "UNAUTHORIZED_USER": "ignore_callback_and_keep_group_pending",
        "DUPLICATE_CALLBACK_IGNORED": "ignore_duplicate_callback_and_keep_existing_transition",
        "APPROVAL_ID_MISMATCH": "ignore_stale_callback_and_wait_for_current_active_approval",
        "GROUP_STATUS_NOT_ACTIONABLE": "ignore_callback_for_terminal_or_non_actionable_group",
        "APPROVAL_EXPIRED": "mark_group_expired_and_wait_for_new_review_if_needed",
        "APPROVAL_RECORDED": {
            "approve": "queue_apply_executor_for_approved_scope",
            "hold": "keep_scope_held_until_followup_decision_or_expiry",
            "reject": "keep_baseline_behavior_and_record_rejection",
        },
    }
    if trigger_state == "APPROVAL_RECORDED":
        return mapping["APPROVAL_RECORDED"].get(decision, "inspect_approval_transition")
    return _to_text(mapping.get(trigger_state), "inspect_approval_loop_result")


class ApprovalLoop:
    def __init__(
        self,
        *,
        telegram_state_store: TelegramStateStore | None = None,
        event_bus: EventBus | None = None,
        allowed_user_ids: Iterable[str | int] | None = None,
    ) -> None:
        self._store = telegram_state_store or TelegramStateStore()
        self._event_bus = event_bus or EventBus()
        self._allowed_user_ids = {
            _to_text(user_id)
            for user_id in (allowed_user_ids or [])
            if _to_text(user_id)
        }

    @property
    def telegram_state_store(self) -> TelegramStateStore:
        return self._store

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    def process_callback(
        self,
        *,
        decision: str,
        telegram_user_id: str | int,
        telegram_username: str = "",
        callback_query_id: str = "",
        approval_id: str = "",
        group_id: int | None = None,
        group_key: str = "",
        note: str = "",
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        normalized_decision = _normalize_decision(decision)
        run_at = _to_text(now_ts, _now_iso())
        user_id = _to_text(telegram_user_id)
        normalized_group_key = _to_text(group_key)
        normalized_callback_id = _to_text(callback_query_id)
        requested_approval_id = _to_text(approval_id)
        group = self._resolve_group(group_id=group_id, group_key=normalized_group_key)
        trace_id = _to_text(group.get("trace_id"), f"approval-loop-{uuid4().hex[:12]}")

        payload = self._build_payload(
            trigger_state="",
            decision=normalized_decision,
            run_at=run_at,
            group=group,
            action={},
            event_count=self._event_bus.pending_count(),
        )

        if not group:
            payload["summary"]["trigger_state"] = "GROUP_NOT_FOUND"
            payload["summary"]["recommended_next_action"] = _recommended_next_action("GROUP_NOT_FOUND")
            return payload

        if normalized_callback_id:
            existing_action = self._store.get_check_action_by_callback_query_id(
                callback_query_id=normalized_callback_id
            )
            if existing_action:
                payload["summary"]["trigger_state"] = "DUPLICATE_CALLBACK_IGNORED"
                payload["summary"]["recommended_next_action"] = _recommended_next_action(
                    "DUPLICATE_CALLBACK_IGNORED"
                )
                payload["action_record"] = existing_action
                payload["decision_result"] = {
                    "decision": normalized_decision,
                    "duplicate_callback": True,
                    "callback_query_id": normalized_callback_id,
                    "approval_id": _to_text(existing_action.get("approval_id")),
                    "previous_status": _to_text(group.get("status")),
                    "next_status": _to_text(group.get("status")),
                }
                return payload

        if not self._is_allowed_user(user_id):
            payload["summary"]["trigger_state"] = "UNAUTHORIZED_USER"
            payload["summary"]["recommended_next_action"] = _recommended_next_action("UNAUTHORIZED_USER")
            payload["decision_result"] = {
                "decision": normalized_decision,
                "allowed_user": False,
                "callback_query_id": normalized_callback_id,
                "approval_id": requested_approval_id,
                "previous_status": _to_text(group.get("status")),
                "next_status": _to_text(group.get("status")),
            }
            return payload

        expired_group = self.expire_group_if_needed(
            group=group,
            now_ts=run_at,
            telegram_user_id=user_id,
            telegram_username=telegram_username,
            callback_query_id=normalized_callback_id,
            note=note,
        )
        if expired_group:
            payload["summary"]["trigger_state"] = "APPROVAL_EXPIRED"
            payload["summary"]["recommended_next_action"] = _recommended_next_action("APPROVAL_EXPIRED")
            payload["group_after"] = expired_group["group_after"]
            payload["action_record"] = expired_group["action_record"]
            payload["decision_result"] = expired_group["decision_result"]
            return payload

        current_status = _to_text(group.get("status")).lower()
        if current_status not in ACTIONABLE_GROUP_STATUSES:
            payload["summary"]["trigger_state"] = "GROUP_STATUS_NOT_ACTIONABLE"
            payload["summary"]["recommended_next_action"] = _recommended_next_action(
                "GROUP_STATUS_NOT_ACTIONABLE"
            )
            payload["decision_result"] = {
                "decision": normalized_decision,
                "allowed_user": True,
                "callback_query_id": normalized_callback_id,
                "approval_id": requested_approval_id or _to_text(group.get("approval_id")),
                "previous_status": current_status,
                "next_status": current_status,
            }
            return payload

        active_approval_id = _to_text(group.get("approval_id"))
        if active_approval_id and requested_approval_id and requested_approval_id != active_approval_id:
            payload["summary"]["trigger_state"] = "APPROVAL_ID_MISMATCH"
            payload["summary"]["recommended_next_action"] = _recommended_next_action(
                "APPROVAL_ID_MISMATCH"
            )
            payload["decision_result"] = {
                "decision": normalized_decision,
                "allowed_user": True,
                "callback_query_id": normalized_callback_id,
                "approval_id": requested_approval_id,
                "active_approval_id": active_approval_id,
                "previous_status": current_status,
                "next_status": current_status,
            }
            return payload

        effective_approval_id = requested_approval_id or active_approval_id or f"approval-{uuid4().hex[:12]}"
        next_status = APPROVAL_ACTION_TO_STATUS[normalized_decision]
        action_record = self._store.append_check_action(
            group_id=int(group["group_id"]),
            telegram_user_id=user_id,
            telegram_username=telegram_username,
            action=normalized_decision,
            note=note,
            callback_query_id=normalized_callback_id,
            approval_id=effective_approval_id,
            trace_id=trace_id,
        )
        group_after = self._transition_group_after_decision(
            group=group,
            next_status=next_status,
            approval_id=effective_approval_id,
            user_id=user_id,
            run_at=run_at,
        )

        self._event_bus.publish(
            ApprovalReceived(
                trace_id=trace_id,
                occurred_at=run_at,
                payload={
                    "group_id": group_after["group_id"],
                    "group_key": group_after["group_key"],
                    "review_type": _to_text(group_after.get("review_type")),
                    "scope_key": _to_text(group_after.get("scope_key")),
                    "approval_id": effective_approval_id,
                    "apply_job_key": _to_text(group_after.get("apply_job_key")),
                    "decision": normalized_decision,
                    "previous_status": current_status,
                    "next_status": next_status,
                    "telegram_user_id": user_id,
                    "telegram_username": _to_text(telegram_username),
                },
            )
        )

        payload["summary"]["trigger_state"] = "APPROVAL_RECORDED"
        payload["summary"]["recommended_next_action"] = _recommended_next_action(
            "APPROVAL_RECORDED",
            normalized_decision,
        )
        payload["summary"]["event_count"] = self._event_bus.pending_count()
        payload["group_after"] = group_after
        payload["action_record"] = action_record
        payload["decision_result"] = {
            "decision": normalized_decision,
            "allowed_user": True,
            "callback_query_id": normalized_callback_id,
            "approval_id": effective_approval_id,
            "previous_status": current_status,
            "next_status": next_status,
            "duplicate_callback": False,
        }
        return payload

    def expire_group_if_needed(
        self,
        *,
        group: Mapping[str, Any] | None,
        now_ts: object | None = None,
        telegram_user_id: str | int = "",
        telegram_username: str = "",
        callback_query_id: str = "",
        note: str = "",
    ) -> dict[str, Any]:
        group_map = _mapping(group)
        if not group_map:
            return {}
        current_status = _to_text(group_map.get("status")).lower()
        if current_status not in ACTIONABLE_GROUP_STATUSES:
            return {}
        deadline = _parse_iso(group_map.get("decision_deadline_ts"))
        now_dt = _parse_iso(now_ts) or datetime.now().astimezone()
        if deadline is None or deadline >= now_dt:
            return {}

        user_id = _to_text(telegram_user_id, "system")
        effective_callback_id = _to_text(callback_query_id)
        approval_id = _to_text(group_map.get("approval_id"), f"approval-{uuid4().hex[:12]}")
        trace_id = _to_text(group_map.get("trace_id"), f"approval-loop-{uuid4().hex[:12]}")
        action_record = self._store.append_check_action(
            group_id=int(group_map["group_id"]),
            telegram_user_id=user_id,
            telegram_username=telegram_username,
            action="expire",
            note=_to_text(note, "decision_deadline_elapsed"),
            callback_query_id=effective_callback_id,
            approval_id=approval_id,
            trace_id=trace_id,
        )
        group_after = self._store.update_check_group(
            group_id=int(group_map["group_id"]),
            status="expired",
            approval_id=approval_id,
            pending_count=0,
            expires_at=_to_text(now_ts, _now_iso()),
            last_event_ts=_to_text(now_ts, _now_iso()),
        )
        return {
            "group_after": group_after,
            "action_record": action_record,
            "decision_result": {
                "decision": "expire",
                "allowed_user": True,
                "callback_query_id": effective_callback_id,
                "approval_id": approval_id,
                "previous_status": current_status,
                "next_status": "expired",
                "expired": True,
            },
        }

    def _resolve_group(self, *, group_id: int | None, group_key: str) -> dict[str, Any]:
        if group_id is not None:
            return self._store.get_check_group(group_id=int(group_id))
        if group_key:
            return self._store.get_check_group(group_key=group_key)
        return {}

    def _is_allowed_user(self, user_id: str) -> bool:
        if not self._allowed_user_ids:
            return True
        return user_id in self._allowed_user_ids

    def _transition_group_after_decision(
        self,
        *,
        group: Mapping[str, Any],
        next_status: str,
        approval_id: str,
        user_id: str,
        run_at: str,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "group_id": int(group["group_id"]),
            "status": next_status,
            "approval_id": approval_id,
            "pending_count": 0,
            "last_event_ts": run_at,
        }
        if next_status == "approved":
            kwargs["approved_by"] = user_id
            kwargs["approved_at"] = run_at
        elif next_status == "held":
            kwargs["held_by"] = user_id
            kwargs["held_at"] = run_at
        elif next_status == "rejected":
            kwargs["rejected_by"] = user_id
            kwargs["rejected_at"] = run_at
        return self._store.update_check_group(**kwargs)

    def _build_payload(
        self,
        *,
        trigger_state: str,
        decision: str,
        run_at: str,
        group: Mapping[str, Any] | None,
        action: Mapping[str, Any] | None,
        event_count: int,
    ) -> dict[str, Any]:
        group_map = _mapping(group)
        action_map = _mapping(action)
        current_status = _to_text(group_map.get("status"))
        return {
            "summary": {
                "contract_version": APPROVAL_LOOP_CONTRACT_VERSION,
                "generated_at": run_at,
                "trigger_state": trigger_state,
                "recommended_next_action": "",
                "group_id": group_map.get("group_id"),
                "group_key": _to_text(group_map.get("group_key")),
                "decision": decision,
                "event_count": int(event_count),
            },
            "group_before": group_map,
            "group_after": group_map,
            "action_record": action_map,
            "decision_result": {
                "decision": decision,
                "previous_status": current_status,
                "next_status": current_status,
            },
        }
