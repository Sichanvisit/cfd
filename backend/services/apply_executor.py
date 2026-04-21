from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping

from backend.services.telegram_state_store import TelegramStateStore


APPLY_EXECUTOR_CONTRACT_VERSION = "apply_executor_v0"

ApplyHandler = Callable[..., Mapping[str, Any]]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _recommended_next_action(trigger_state: str) -> str:
    mapping = {
        "GROUP_NOT_FOUND": "inspect_approval_event_and_group_mapping",
        "GROUP_NOT_APPROVED": "wait_for_approved_group_before_apply",
        "DECISION_NOT_APPLICABLE": "skip_apply_until_approval_decision_is_approve",
        "NO_APPLY_HANDLER": "register_bounded_apply_handler_for_review_type",
        "DUPLICATE_APPLY_IGNORED": "keep_existing_apply_result_and_ignore_duplicate_dispatch",
        "APPLY_EXECUTED": "continue_governance_flow_after_apply_execution",
        "HANDLER_ERROR": "inspect_apply_handler_error_before_retry",
    }
    return _to_text(mapping.get(trigger_state), "inspect_apply_executor_result")


class ApplyExecutor:
    def __init__(
        self,
        *,
        telegram_state_store: TelegramStateStore | None = None,
        handlers: Mapping[str, ApplyHandler] | None = None,
    ) -> None:
        self._store = telegram_state_store or TelegramStateStore()
        self._handlers: dict[str, ApplyHandler] = {
            _to_text(review_type).upper(): handler
            for review_type, handler in dict(handlers or {}).items()
            if _to_text(review_type) and callable(handler)
        }

    @property
    def telegram_state_store(self) -> TelegramStateStore:
        return self._store

    def register_handler(self, review_type: str, handler: ApplyHandler) -> None:
        normalized = _to_text(review_type).upper()
        if not normalized:
            raise ValueError("review_type_required")
        self._handlers[normalized] = handler

    def execute_approval(
        self,
        *,
        approval_event_payload: Mapping[str, Any] | None,
        review_payload: Mapping[str, Any] | None = None,
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        event_payload = _mapping(approval_event_payload)
        run_at = _to_text(now_ts, _now_iso())
        trace_id = _to_text(event_payload.get("trace_id"))
        group_id_text = _to_text(event_payload.get("group_id"))
        review_type = _to_text(event_payload.get("review_type")).upper()
        decision = _to_text(event_payload.get("decision")).lower()
        approval_id = _to_text(event_payload.get("approval_id"))
        apply_job_key = _to_text(event_payload.get("apply_job_key"))

        group = self._store.get_check_group(group_id=int(group_id_text)) if group_id_text else {}
        payload = self._build_payload(
            trigger_state="",
            run_at=run_at,
            group=group,
            event_payload=event_payload,
            apply_result={},
        )

        if not group:
            payload["summary"]["trigger_state"] = "GROUP_NOT_FOUND"
            payload["summary"]["recommended_next_action"] = _recommended_next_action("GROUP_NOT_FOUND")
            return payload

        current_status = _to_text(group.get("status")).lower()
        actions = self._store.list_check_actions(group_id=int(group["group_id"]))
        duplicate_apply = next(
            (
                action
                for action in reversed(actions)
                if _to_text(action.get("action")) == "apply"
                and _to_text(action.get("approval_id")) == approval_id
            ),
            {},
        )
        if duplicate_apply or current_status == "applied":
            payload["summary"]["trigger_state"] = "DUPLICATE_APPLY_IGNORED"
            payload["summary"]["recommended_next_action"] = _recommended_next_action("DUPLICATE_APPLY_IGNORED")
            payload["apply_record"] = duplicate_apply
            payload["decision_result"] = {
                "decision": decision,
                "previous_status": current_status,
                "next_status": "applied" if current_status == "applied" else current_status,
                "approval_id": approval_id,
                "apply_job_key": apply_job_key or _to_text(group.get("apply_job_key")),
                "duplicate_apply": True,
            }
            return payload

        if current_status != "approved":
            payload["summary"]["trigger_state"] = "GROUP_NOT_APPROVED"
            payload["summary"]["recommended_next_action"] = _recommended_next_action("GROUP_NOT_APPROVED")
            payload["decision_result"] = {
                "decision": decision,
                "previous_status": current_status,
                "next_status": current_status,
                "approval_id": approval_id,
                "apply_job_key": apply_job_key or _to_text(group.get("apply_job_key")),
            }
            return payload

        if decision != "approve":
            payload["summary"]["trigger_state"] = "DECISION_NOT_APPLICABLE"
            payload["summary"]["recommended_next_action"] = _recommended_next_action("DECISION_NOT_APPLICABLE")
            return payload

        handler = self._handlers.get(review_type)
        if handler is None:
            payload["summary"]["trigger_state"] = "NO_APPLY_HANDLER"
            payload["summary"]["recommended_next_action"] = _recommended_next_action("NO_APPLY_HANDLER")
            return payload

        try:
            apply_result = dict(
                handler(
                    approval_event_payload=event_payload,
                    group=group,
                    review_payload=_mapping(review_payload),
                    now_ts=run_at,
                )
            )
        except Exception as exc:
            payload["summary"]["trigger_state"] = "HANDLER_ERROR"
            payload["summary"]["recommended_next_action"] = _recommended_next_action("HANDLER_ERROR")
            payload["apply_result"] = {
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
            }
            return payload

        apply_note = _to_text(
            _mapping(apply_result.get("summary")).get("recommended_next_action"),
            _to_text(apply_result.get("apply_state"), "apply_executed"),
        )
        apply_record = self._store.append_check_action(
            group_id=int(group["group_id"]),
            telegram_user_id="system_apply_executor",
            telegram_username="apply_executor",
            action="apply",
            note=apply_note,
            callback_query_id="",
            approval_id=approval_id,
            trace_id=trace_id,
        )
        group_after = self._store.update_check_group(
            group_id=int(group["group_id"]),
            status="applied",
            approval_id=approval_id or _to_text(group.get("approval_id")),
            pending_count=0,
            last_event_ts=run_at,
        )

        payload["summary"]["trigger_state"] = "APPLY_EXECUTED"
        payload["summary"]["recommended_next_action"] = _recommended_next_action("APPLY_EXECUTED")
        payload["group_after"] = group_after
        payload["apply_record"] = apply_record
        payload["apply_result"] = apply_result
        payload["decision_result"] = {
            "decision": decision,
            "previous_status": current_status,
            "next_status": "applied",
            "approval_id": approval_id,
            "apply_job_key": apply_job_key or _to_text(group.get("apply_job_key")),
            "duplicate_apply": False,
        }
        return payload

    def _build_payload(
        self,
        *,
        trigger_state: str,
        run_at: str,
        group: Mapping[str, Any] | None,
        event_payload: Mapping[str, Any] | None,
        apply_result: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        group_map = _mapping(group)
        approval_event = _mapping(event_payload)
        apply_map = _mapping(apply_result)
        current_status = _to_text(group_map.get("status"))
        return {
            "summary": {
                "contract_version": APPLY_EXECUTOR_CONTRACT_VERSION,
                "generated_at": run_at,
                "trigger_state": trigger_state,
                "recommended_next_action": "",
                "group_id": group_map.get("group_id"),
                "group_key": _to_text(group_map.get("group_key")),
                "review_type": _to_text(approval_event.get("review_type"), _to_text(group_map.get("review_type"))),
                "decision": _to_text(approval_event.get("decision")),
            },
            "group_before": group_map,
            "group_after": group_map,
            "approval_event": approval_event,
            "apply_record": {},
            "apply_result": apply_map,
            "decision_result": {
                "decision": _to_text(approval_event.get("decision")),
                "previous_status": current_status,
                "next_status": current_status,
                "approval_id": _to_text(approval_event.get("approval_id"), _to_text(group_map.get("approval_id"))),
                "apply_job_key": _to_text(approval_event.get("apply_job_key"), _to_text(group_map.get("apply_job_key"))),
            },
        }
