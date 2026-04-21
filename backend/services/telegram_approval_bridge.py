from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping
from uuid import uuid4

from backend.services.apply_executor import ApplyExecutor
from backend.services.approval_loop import ApprovalLoop
from backend.services.event_bus import ApprovalReceived, EventBus, GovernanceActionNeeded
from backend.services.improvement_proposal_policy import (
    ensure_improvement_proposal_envelope,
)
from backend.services.improvement_status_policy import APPROVAL_ACTIONABLE_STATUSES
from backend.services.teacher_pattern_active_candidate_runtime import (
    render_state25_teacher_weight_override_lines_ko,
)
from backend.services.telegram_state_store import TelegramStateStore


TELEGRAM_APPROVAL_BRIDGE_CONTRACT_VERSION = "telegram_approval_bridge_v0"
ACTIONABLE_GROUP_STATUSES = APPROVAL_ACTIONABLE_STATUSES
DEFAULT_DEADLINE_MINUTES_BY_REVIEW_TYPE = {
    "CANARY_ACTIVATION_REVIEW": 10,
    "CANARY_ROLLBACK_REVIEW": 5,
    "CANARY_CLOSEOUT_REVIEW": 15,
    "PA9_ACTION_BASELINE_HANDOFF_REVIEW": 20,
    "STATE25_WEIGHT_PATCH_REVIEW": 30,
}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


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


def _recommended_next_action(trigger_state: str) -> str:
    mapping = {
        "REVIEW_REQUEST_CREATED": "send_check_prompt_to_telegram_ops_console",
        "REVIEW_REQUEST_REFRESHED": "edit_or_repost_existing_check_prompt_for_same_scope",
        "REVIEW_REQUEST_REOPENED": "send_new_check_prompt_for_reopened_scope",
        "APPROVAL_PROCESSED": "drain_event_bus_and_wait_for_apply_executor_if_needed",
        "APPLY_RECORDED": "continue_with_bounded_canary_governance_after_apply",
    }
    return _to_text(
        mapping.get(trigger_state),
        "inspect_telegram_approval_bridge_result",
    )


class TelegramApprovalBridge:
    def __init__(
        self,
        *,
        telegram_state_store: TelegramStateStore | None = None,
        event_bus: EventBus | None = None,
        approval_loop: ApprovalLoop | None = None,
        apply_executor: ApplyExecutor | None = None,
        dispatch_handler: Callable[[Mapping[str, Any] | None], Mapping[str, Any] | None]
        | None = None,
        auto_subscribe: bool = True,
    ) -> None:
        self._store = telegram_state_store or TelegramStateStore()
        self._event_bus = event_bus or EventBus()
        self._approval_loop = approval_loop or ApprovalLoop(
            telegram_state_store=self._store,
            event_bus=self._event_bus,
        )
        self._apply_executor = apply_executor or ApplyExecutor(
            telegram_state_store=self._store,
        )
        self._dispatch_handler = dispatch_handler
        self._dispatch_records: list[dict[str, Any]] = []
        self._apply_records: list[dict[str, Any]] = []
        self._subscriptions_registered = False
        if auto_subscribe:
            self.register_event_subscriptions()

    @property
    def telegram_state_store(self) -> TelegramStateStore:
        return self._store

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def approval_loop(self) -> ApprovalLoop:
        return self._approval_loop

    @property
    def apply_executor(self) -> ApplyExecutor:
        return self._apply_executor

    @property
    def dispatch_handler(
        self,
    ) -> Callable[[Mapping[str, Any] | None], Mapping[str, Any] | None] | None:
        return self._dispatch_handler

    def register_event_subscriptions(self) -> None:
        if self._subscriptions_registered:
            return
        self._event_bus.subscribe(
            GovernanceActionNeeded,
            self._handle_governance_action_needed_event,
        )
        self._event_bus.subscribe(
            ApprovalReceived,
            self._handle_approval_received_event,
        )
        self._subscriptions_registered = True

    def handle_governance_action_needed(
        self,
        *,
        governance_payload: Mapping[str, Any] | None,
        trace_id: str = "",
        occurred_at: str = "",
        now_ts: object | None = None,
    ) -> dict[str, Any]:
        candidate = _mapping(governance_payload)
        run_at = _to_text(now_ts, occurred_at or _now_iso())
        effective_trace_id = _to_text(trace_id, f"bridge-{uuid4().hex[:12]}")
        symbol = _to_text(candidate.get("symbol")).upper()
        review_type = _to_text(candidate.get("review_type")).upper()
        scope_key = _to_text(candidate.get("scope_key"))
        governance_action = _to_text(candidate.get("governance_action"))

        if not scope_key:
            raise ValueError("scope_key_required")
        if not review_type:
            raise ValueError("review_type_required")

        proposal_envelope = ensure_improvement_proposal_envelope(
            candidate,
            proposal_type=review_type,
            trace_id=effective_trace_id,
        )
        reason_summary = self._build_reason_summary(
            candidate,
            proposal_envelope=proposal_envelope,
        )
        scope_note = self._build_scope_note(
            candidate,
            proposal_envelope=proposal_envelope,
        )

        existing_group = self._store.get_check_group(group_key=scope_key)
        existing_status = _to_text(existing_group.get("status")).lower()
        existing_deadline = _parse_iso(existing_group.get("decision_deadline_ts"))
        run_dt = _parse_iso(run_at) or datetime.now().astimezone()
        existing_is_fresh = (
            existing_status in ACTIONABLE_GROUP_STATUSES
            and (existing_deadline is None or existing_deadline >= run_dt)
        )

        previous_approval_id = _to_text(existing_group.get("approval_id"))
        approval_id = (
            previous_approval_id if existing_is_fresh else f"approval-{uuid4().hex[:12]}"
        )
        apply_job_key = (
            _to_text(existing_group.get("apply_job_key"))
            if existing_is_fresh and _to_text(existing_group.get("apply_job_key"))
            else f"{scope_key}::{review_type.lower()}::{approval_id}"
        )
        decision_deadline_ts = (
            _to_text(existing_group.get("decision_deadline_ts"))
            if existing_is_fresh and _to_text(existing_group.get("decision_deadline_ts"))
            else self._build_decision_deadline(review_type=review_type, now_ts=run_at)
        )
        group_status = existing_status if existing_is_fresh else "pending"
        trigger_state = (
            "REVIEW_REQUEST_REFRESHED"
            if existing_is_fresh
            else ("REVIEW_REQUEST_REOPENED" if existing_group else "REVIEW_REQUEST_CREATED")
        )

        group = self._store.upsert_check_group(
            group_key=scope_key,
            status=group_status,
            priority=self._priority_for_review_type(review_type),
            symbol=symbol,
            check_kind=governance_action or review_type.lower(),
            action_target=self._build_action_target(candidate, review_type=review_type),
            reason_fingerprint=f"{scope_key}::{review_type.lower()}",
            reason_summary=reason_summary,
            review_type=review_type,
            approval_id=approval_id,
            scope_key=scope_key,
            trace_id=effective_trace_id,
            scope_note=scope_note,
            decision_deadline_ts=decision_deadline_ts,
            apply_job_key=apply_job_key,
            supersedes_approval_id=(
                previous_approval_id
                if previous_approval_id and previous_approval_id != approval_id
                else ""
            ),
            first_event_ts=_to_text(existing_group.get("first_event_ts"), run_at),
            last_event_ts=run_at,
            pending_count=_to_int(existing_group.get("pending_count"))
            if existing_is_fresh
            else 0,
            expires_at="",
        )
        event_payload = dict(candidate)
        event_payload["proposal_envelope"] = deepcopy(proposal_envelope)
        event_record = self._store.append_check_event(
            group_id=int(group["group_id"]),
            source_type="governance_action_needed",
            source_ref=review_type.lower(),
            symbol=symbol,
            side="",
            payload=event_payload,
            event_ts=run_at,
            trace_id=effective_trace_id,
            increment_pending=True,
        )
        group_after = self._store.get_check_group(group_id=int(group["group_id"]))

        dispatch_record = {
            "summary": {
                "contract_version": TELEGRAM_APPROVAL_BRIDGE_CONTRACT_VERSION,
                "generated_at": run_at,
                "trigger_state": trigger_state,
                "recommended_next_action": _recommended_next_action(trigger_state),
                "group_id": group_after.get("group_id"),
                "group_key": _to_text(group_after.get("group_key")),
                "review_type": review_type,
                "approval_id": approval_id,
                "scope_key": scope_key,
                "proposal_id": proposal_envelope.get("proposal_id"),
                "proposal_stage": proposal_envelope.get("proposal_stage"),
                "readiness_status": proposal_envelope.get("readiness_status"),
            },
            "group_after": group_after,
            "event_record": event_record,
            "proposal_envelope": proposal_envelope,
            "dispatch_envelope": {
                "route_key": "check",
                "message_kind": "check_prompt",
                "entity_type": "check_group",
                "entity_id": str(group_after.get("group_id")),
                "group_id": group_after.get("group_id"),
                "group_key": _to_text(group_after.get("group_key")),
                "symbol": symbol,
                "review_type": review_type,
                "approval_id": approval_id,
                "scope_key": scope_key,
                "scope_note": _to_text(group_after.get("scope_note")),
                "decision_deadline_ts": _to_text(group_after.get("decision_deadline_ts")),
                "recommended_next_action": _to_text(candidate.get("recommended_next_action")),
                "trigger_summary": reason_summary,
                "trace_id": effective_trace_id,
                "proposal_id": proposal_envelope.get("proposal_id"),
                "proposal_stage": proposal_envelope.get("proposal_stage"),
                "readiness_status": proposal_envelope.get("readiness_status"),
                "summary_ko": proposal_envelope.get("summary_ko"),
                "why_now_ko": proposal_envelope.get("why_now_ko"),
                "recommended_action_ko": proposal_envelope.get("recommended_action_ko"),
                "blocking_reason": proposal_envelope.get("blocking_reason"),
                "confidence_level": proposal_envelope.get("confidence_level"),
                "expected_effect_ko": proposal_envelope.get("expected_effect_ko"),
            },
            "report_envelope": self._build_report_envelope(
                group_after=group_after,
                candidate=candidate,
                proposal_envelope=proposal_envelope,
                trace_id=effective_trace_id,
            ),
        }
        if self._dispatch_handler is not None:
            dispatch_result = self._dispatch_handler(dispatch_record)
            if isinstance(dispatch_result, Mapping):
                dispatch_record["dispatch_result"] = dict(dispatch_result)
        self._dispatch_records.append(deepcopy(dispatch_record))
        return dispatch_record

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
        auto_drain: bool = True,
    ) -> dict[str, Any]:
        approval_result = self._approval_loop.process_callback(
            decision=decision,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            callback_query_id=callback_query_id,
            approval_id=approval_id,
            group_id=group_id,
            group_key=group_key,
            note=note,
            now_ts=now_ts,
        )
        drained_events = self.drain_pending_events() if auto_drain else []
        return {
            "summary": {
                "contract_version": TELEGRAM_APPROVAL_BRIDGE_CONTRACT_VERSION,
                "generated_at": _to_text(now_ts, _now_iso()),
                "trigger_state": "APPROVAL_PROCESSED",
                "recommended_next_action": _recommended_next_action(
                    "APPROVAL_PROCESSED"
                ),
                "drained_event_count": len(drained_events),
                "apply_record_count": len(self._apply_records),
            },
            "approval_result": approval_result,
            "drained_event_types": [event.event_type for event in drained_events],
            "latest_apply_record": deepcopy(self._apply_records[-1])
            if self._apply_records
            else {},
        }

    def drain_pending_events(self, *, max_events: int | None = None) -> list[Any]:
        return self._event_bus.drain(max_events=max_events)

    def get_dispatch_records(self) -> list[dict[str, Any]]:
        return deepcopy(self._dispatch_records)

    def get_apply_records(self) -> list[dict[str, Any]]:
        return deepcopy(self._apply_records)

    def _handle_governance_action_needed_event(
        self,
        event: GovernanceActionNeeded,
    ) -> None:
        self.handle_governance_action_needed(
            governance_payload=event.payload,
            trace_id=event.trace_id,
            occurred_at=event.occurred_at,
        )

    def _handle_approval_received_event(self, event: ApprovalReceived) -> None:
        approval_payload = _mapping(event.payload)
        if _to_text(approval_payload.get("decision")).lower() != "approve":
            return
        group_id = _to_int(approval_payload.get("group_id"))
        review_payload = self._load_latest_review_payload(group_id=group_id)
        executor_payload = dict(approval_payload)
        executor_payload["trace_id"] = _to_text(
            approval_payload.get("trace_id"),
            event.trace_id,
        )
        apply_result = self._apply_executor.execute_approval(
            approval_event_payload=executor_payload,
            review_payload=review_payload,
            now_ts=event.occurred_at,
        )
        record = {
            "summary": {
                "contract_version": TELEGRAM_APPROVAL_BRIDGE_CONTRACT_VERSION,
                "generated_at": _to_text(event.occurred_at, _now_iso()),
                "trigger_state": "APPLY_RECORDED",
                "recommended_next_action": _recommended_next_action(
                    "APPLY_RECORDED"
                ),
                "group_id": approval_payload.get("group_id"),
                "group_key": approval_payload.get("group_key"),
                "review_type": approval_payload.get("review_type"),
                "approval_id": approval_payload.get("approval_id"),
            },
            "approval_event": executor_payload,
            "review_payload": review_payload,
            "apply_execution": apply_result,
        }
        self._apply_records.append(record)

    def _load_latest_review_payload(self, *, group_id: int) -> dict[str, Any]:
        if group_id <= 0:
            return {}
        events = self._store.list_check_events(group_id=group_id, limit=1)
        if not events:
            return {}
        payload_json = _to_text(events[0].get("payload_json"))
        if not payload_json:
            return {}
        try:
            parsed = json.loads(payload_json)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _build_decision_deadline(self, *, review_type: str, now_ts: str) -> str:
        base_dt = _parse_iso(now_ts) or datetime.now().astimezone()
        minutes = DEFAULT_DEADLINE_MINUTES_BY_REVIEW_TYPE.get(review_type, 10)
        return (base_dt + timedelta(minutes=minutes)).isoformat()

    def _priority_for_review_type(self, review_type: str) -> str:
        if review_type == "CANARY_ROLLBACK_REVIEW":
            return "high"
        if review_type in {"CANARY_CLOSEOUT_REVIEW", "STATE25_WEIGHT_PATCH_REVIEW"}:
            return "normal"
        return "normal"

    def _build_reason_summary(
        self,
        candidate: Mapping[str, Any],
        *,
        proposal_envelope: Mapping[str, Any] | None = None,
    ) -> str:
        envelope = _mapping(proposal_envelope)
        if _to_text(envelope.get("summary_ko")):
            return _to_text(envelope.get("summary_ko"))

        symbol = _to_text(candidate.get("symbol")).upper()
        review_type = _to_text(candidate.get("review_type")).upper()
        if review_type == "STATE25_WEIGHT_PATCH_REVIEW":
            return _to_text(
                candidate.get("proposal_summary_ko"),
                candidate.get("reason_summary_ko"),
            ) or self._build_state25_weight_patch_reason_summary(candidate)

        activation_state = _to_text(candidate.get("activation_apply_state"))
        closeout_state = _to_text(candidate.get("closeout_state"))
        first_window_status = _to_text(candidate.get("first_window_status"))
        if review_type == "CANARY_ROLLBACK_REVIEW":
            return f"{symbol} canary 롤백 검토가 필요합니다 ({closeout_state or 'ROLLBACK_REQUIRED'})"
        if review_type == "CANARY_CLOSEOUT_REVIEW":
            return f"{symbol} canary closeout 검토가 준비됐습니다 ({closeout_state or first_window_status})"
        return f"{symbol} canary activation 검토가 필요합니다 ({activation_state or 'activation_hold'})"

    def _build_scope_note(
        self,
        candidate: Mapping[str, Any],
        *,
        proposal_envelope: Mapping[str, Any] | None = None,
    ) -> str:
        envelope = _mapping(proposal_envelope)
        if _to_text(envelope.get("scope_note_ko")):
            return _to_text(envelope.get("scope_note_ko"))

        symbol = _to_text(candidate.get("symbol")).upper()
        review_type = _to_text(candidate.get("review_type")).upper()
        if review_type == "STATE25_WEIGHT_PATCH_REVIEW":
            return _to_text(
                candidate.get("scope_note_ko"),
                self._build_state25_weight_patch_scope_note(candidate),
            )

        activation_state = _to_text(candidate.get("activation_apply_state"))
        closeout_state = _to_text(candidate.get("closeout_state"))
        first_window_status = _to_text(candidate.get("first_window_status"))
        live_ready = _to_bool(candidate.get("live_observation_ready"))
        observed_rows = _to_int(candidate.get("observed_window_row_count"))
        active_triggers = _to_int(candidate.get("active_trigger_count"))
        return (
            f"{symbol} | activation={activation_state or '-'} | closeout={closeout_state or '-'} "
            f"| first_window={first_window_status or '-'} | live_ready={str(live_ready).lower()} "
            f"| observed_rows={observed_rows} | active_triggers={active_triggers}"
        )

    def _build_action_target(
        self,
        candidate: Mapping[str, Any],
        *,
        review_type: str,
    ) -> str:
        explicit = _to_text(candidate.get("action_target"))
        if explicit:
            return explicit
        if review_type == "STATE25_WEIGHT_PATCH_REVIEW":
            return "state25_weight_patch_log_only"
        return "bounded_action_only_canary"

    def _build_report_envelope(
        self,
        *,
        group_after: Mapping[str, Any],
        candidate: Mapping[str, Any],
        proposal_envelope: Mapping[str, Any] | None,
        trace_id: str,
    ) -> dict[str, Any]:
        review_type = _to_text(
            candidate.get("review_type"),
            _to_text(group_after.get("review_type")),
        ).upper()
        return {
            "route_key": "report",
            "message_kind": "review_report",
            "entity_type": "check_group",
            "entity_id": str(group_after.get("group_id")),
            "group_id": group_after.get("group_id"),
            "group_key": _to_text(group_after.get("group_key")),
            "review_type": review_type,
            "title_ko": self._build_report_title_ko(candidate, review_type=review_type),
            "lines_ko": self._build_report_lines_ko(
                candidate,
                review_type=review_type,
                proposal_envelope=proposal_envelope,
            ),
            "trace_id": trace_id,
            "proposal_envelope": _mapping(proposal_envelope),
        }

    def _build_report_title_ko(
        self,
        candidate: Mapping[str, Any],
        *,
        review_type: str,
    ) -> str:
        if review_type == "STATE25_WEIGHT_PATCH_REVIEW":
            return _to_text(
                candidate.get("report_title_ko"),
                "학습 반영 제안 | 가중치 조정",
            )
        symbol = _to_text(candidate.get("symbol")).upper()
        if review_type == "CANARY_ROLLBACK_REVIEW":
            return f"개선안 검토 | {symbol} 롤백 검토"
        if review_type == "CANARY_CLOSEOUT_REVIEW":
            return f"개선안 검토 | {symbol} closeout 검토"
        return f"개선안 검토 | {symbol} canary 반영"

    def _build_report_lines_ko(
        self,
        candidate: Mapping[str, Any],
        *,
        review_type: str,
        proposal_envelope: Mapping[str, Any] | None = None,
    ) -> list[str]:
        envelope = _mapping(proposal_envelope)
        manual_lines = candidate.get("report_lines_ko")
        if isinstance(manual_lines, list) and manual_lines:
            return [str(line) for line in manual_lines if _to_text(line)]
        if review_type == "STATE25_WEIGHT_PATCH_REVIEW":
            return self._build_state25_weight_patch_report_lines(candidate)

        summary_ko = _to_text(
            envelope.get("summary_ko"),
            self._build_reason_summary(candidate),
        )
        why_now_ko = _to_text(envelope.get("why_now_ko"))
        recommended_action_ko = _to_text(
            envelope.get("recommended_action_ko"),
            _to_text(
                candidate.get("recommended_action_note"),
                _to_text(candidate.get("recommended_next_action"), "-"),
            ),
        )
        scope_note = _to_text(
            envelope.get("scope_note_ko"),
            self._build_scope_note(candidate),
        )
        lines = [
            f"대상 심볼: {_to_text(candidate.get('symbol')).upper() or '-'}",
            f"검토 유형: {review_type or '-'}",
            f"제안 요약: {summary_ko or '-'}",
        ]
        if why_now_ko:
            lines.append(f"왜 지금: {why_now_ko}")
        lines.extend(
            [
                f"권장 조치: {recommended_action_ko or '-'}",
                f"범위: {scope_note or '-'}",
            ]
        )
        if _to_text(envelope.get("proposal_stage")):
            lines.append(
                f"제안 단계: {_to_text(envelope.get('proposal_stage'))} / readiness: {_to_text(envelope.get('readiness_status'))}"
            )
        if _to_text(envelope.get("decision_deadline_ts")):
            lines.append(f"결정 기한: {_to_text(envelope.get('decision_deadline_ts'))}")
        return lines

    def _build_state25_weight_patch_reason_summary(
        self,
        candidate: Mapping[str, Any],
    ) -> str:
        target = _to_text(candidate.get("target_component_ko"), "state25 해석 가중치")
        concern = _to_text(
            candidate.get("concern_summary_ko"),
            "특정 장면에서 해석 비중 조정이 필요합니다.",
        )
        return f"{target} 조정 제안: {concern}"

    def _build_state25_weight_patch_scope_note(
        self,
        candidate: Mapping[str, Any],
    ) -> str:
        symbol_scope = ",".join(
            [
                item
                for item in (
                    str(symbol or "").upper().strip()
                    for symbol in list(
                        candidate.get("state25_execution_symbol_allowlist", []) or []
                    )
                )
                if item
            ]
        ) or "전체 심볼"
        stage_scope = ",".join(
            [
                item
                for item in (
                    str(stage or "").upper().strip()
                    for stage in list(
                        candidate.get(
                            "state25_execution_entry_stage_allowlist",
                            [],
                        )
                        or []
                    )
                )
                if item
            ]
        ) or "전체 단계"
        return (
            f"symbol={symbol_scope} | entry_stage={stage_scope} | "
            f"binding_mode={_to_text(candidate.get('state25_execution_bind_mode'), 'log_only')}"
        )

    def _build_state25_weight_patch_report_lines(
        self,
        candidate: Mapping[str, Any],
    ) -> list[str]:
        concern = _to_text(candidate.get("concern_summary_ko"))
        current_behavior = _to_text(candidate.get("current_behavior_ko"))
        proposed_behavior = _to_text(candidate.get("proposed_behavior_ko"))
        evidence = _to_text(candidate.get("evidence_summary_ko"))
        scope_note = self._build_scope_note(
            {
                **dict(candidate),
                "review_type": "STATE25_WEIGHT_PATCH_REVIEW",
            }
        )
        overrides = candidate.get("state25_teacher_weight_overrides") or _mapping(
            candidate.get("weight_patch")
        ).get("state25_teacher_weight_overrides")
        lines = [
            f"관찰 장면: {concern or '특정 장면에서 해석 비중 조정이 필요합니다.'}",
            f"현재 해석: {current_behavior or '기존 state25 teacher 비중 그대로 사용'}",
            f"제안 해석: {proposed_behavior or '문제 특성의 가중치를 줄이고 다른 근거 비중을 상대적으로 높입니다.'}",
            f"근거 요약: {evidence or 'runtime 장면과 사후 결과를 기준으로 bounded log-only 조정을 제안합니다.'}",
            f"적용 범위: {scope_note}",
            "조정 항목:",
        ]
        override_lines = render_state25_teacher_weight_override_lines_ko(overrides)
        if override_lines:
            lines.extend(override_lines)
        else:
            lines.append("- 아직 조정 항목이 채워지지 않았습니다.")
        return lines
