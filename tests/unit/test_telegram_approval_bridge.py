from __future__ import annotations

from pathlib import Path

from backend.services.apply_executor import ApplyExecutor
from backend.services.approval_loop import ApprovalLoop
from backend.services.event_bus import EventBus, GovernanceActionNeeded
from backend.services.telegram_approval_bridge import TelegramApprovalBridge
from backend.services.telegram_state_store import TelegramStateStore


def _build_bridge(tmp_path: Path) -> tuple[TelegramApprovalBridge, TelegramStateStore, EventBus]:
    store = TelegramStateStore(db_path=tmp_path / "telegram_hub.db")
    bus = EventBus()
    approval_loop = ApprovalLoop(
        telegram_state_store=store,
        event_bus=bus,
        allowed_user_ids={"1001"},
    )
    apply_executor = ApplyExecutor(telegram_state_store=store)
    bridge = TelegramApprovalBridge(
        telegram_state_store=store,
        event_bus=bus,
        approval_loop=approval_loop,
        apply_executor=apply_executor,
    )
    return bridge, store, bus


def _publish_governance_event(
    *,
    bus: EventBus,
    trace_id: str,
    occurred_at: str = "2026-04-11T12:00:00+09:00",
    review_type: str = "CANARY_ACTIVATION_REVIEW",
    scope_key: str = "BTCUSD::action_only_canary::activation",
    symbol: str = "BTCUSD",
    closeout_state: str = "",
    activation_apply_state: str = "HOLD_CANARY_ACTIVATION_APPLY",
) -> None:
    bus.publish(
        GovernanceActionNeeded(
            trace_id=trace_id,
            occurred_at=occurred_at,
            payload={
                "review_type": review_type,
                "governance_action": review_type.lower(),
                "scope_key": scope_key,
                "symbol": symbol,
                "activation_apply_state": activation_apply_state,
                "closeout_state": closeout_state,
                "first_window_status": "AWAIT_FIRST_CANARY_WINDOW_RESULTS",
                "live_observation_ready": False,
                "observed_window_row_count": 0,
                "active_trigger_count": 1,
                "recommended_next_action": "review_canary_candidate_in_ops_console",
            },
        )
    )


def test_bridge_creates_pending_review_request_from_governance_event(tmp_path: Path) -> None:
    bridge, store, bus = _build_bridge(tmp_path)
    _publish_governance_event(bus=bus, trace_id="trace-gov-1")

    drained = bridge.drain_pending_events()
    group = store.get_check_group(group_key="BTCUSD::action_only_canary::activation")
    events = store.list_check_events(group_id=int(group["group_id"]))
    dispatch_records = bridge.get_dispatch_records()

    assert len(drained) == 1
    assert group["status"] == "pending"
    assert group["review_type"] == "CANARY_ACTIVATION_REVIEW"
    assert group["pending_count"] == 1
    assert group["approval_id"].startswith("approval-")
    assert events[0]["source_type"] == "governance_action_needed"
    assert dispatch_records[0]["summary"]["trigger_state"] == "REVIEW_REQUEST_CREATED"
    assert dispatch_records[0]["summary"]["proposal_stage"] == "REPORT_READY"
    assert dispatch_records[0]["summary"]["readiness_status"] == "READY_FOR_REVIEW"
    assert dispatch_records[0]["proposal_envelope"]["proposal_type"] == "CANARY_ACTIVATION_REVIEW"
    assert dispatch_records[0]["dispatch_envelope"]["route_key"] == "check"
    assert dispatch_records[0]["dispatch_envelope"]["message_kind"] == "check_prompt"


def test_bridge_refreshes_same_actionable_group_for_repeated_scope(tmp_path: Path) -> None:
    bridge, store, bus = _build_bridge(tmp_path)
    _publish_governance_event(bus=bus, trace_id="trace-gov-1")
    bridge.drain_pending_events()
    first_group = store.get_check_group(group_key="BTCUSD::action_only_canary::activation")

    _publish_governance_event(
        bus=bus,
        trace_id="trace-gov-2",
        occurred_at="2026-04-11T12:03:00+09:00",
    )
    bridge.drain_pending_events()
    second_group = store.get_check_group(group_key="BTCUSD::action_only_canary::activation")
    events = store.list_check_events(group_id=int(second_group["group_id"]), limit=10)
    dispatch_records = bridge.get_dispatch_records()

    assert first_group["group_id"] == second_group["group_id"]
    assert first_group["approval_id"] == second_group["approval_id"]
    assert second_group["pending_count"] == 2
    assert len(events) == 2
    assert dispatch_records[-1]["summary"]["trigger_state"] == "REVIEW_REQUEST_REFRESHED"


def test_bridge_approve_callback_flows_into_apply_executor(tmp_path: Path) -> None:
    bridge, store, bus = _build_bridge(tmp_path)

    def _activation_handler(**_: object) -> dict[str, object]:
        return {
            "summary": {
                "apply_state": "ACTIVE_ACTION_ONLY_CANARY",
                "recommended_next_action": "start_first_canary_window_observation",
            }
        }

    bridge.apply_executor.register_handler("CANARY_ACTIVATION_REVIEW", _activation_handler)
    _publish_governance_event(bus=bus, trace_id="trace-gov-1")
    bridge.drain_pending_events()
    group = store.get_check_group(group_key="BTCUSD::action_only_canary::activation")

    result = bridge.process_callback(
        decision="approve",
        group_key=str(group["group_key"]),
        telegram_user_id="1001",
        telegram_username="ops_user",
        callback_query_id="cbq-approve-1",
        approval_id=str(group["approval_id"]),
        note="activate bounded canary",
        now_ts="2026-04-11T12:05:00+09:00",
        auto_drain=True,
    )

    stored_group = store.get_check_group(group_id=int(group["group_id"]))
    actions = store.list_check_actions(group_id=int(group["group_id"]))
    apply_records = bridge.get_apply_records()

    assert result["approval_result"]["summary"]["trigger_state"] == "APPROVAL_RECORDED"
    assert "ApprovalReceived" in result["drained_event_types"]
    assert stored_group["status"] == "applied"
    assert [action["action"] for action in actions] == ["approve", "apply"]
    assert len(apply_records) == 1
    assert apply_records[0]["apply_execution"]["summary"]["trigger_state"] == "APPLY_EXECUTED"


def test_bridge_hold_callback_does_not_invoke_apply_executor(tmp_path: Path) -> None:
    bridge, store, bus = _build_bridge(tmp_path)
    _publish_governance_event(bus=bus, trace_id="trace-gov-1")
    bridge.drain_pending_events()
    group = store.get_check_group(group_key="BTCUSD::action_only_canary::activation")

    result = bridge.process_callback(
        decision="hold",
        group_key=str(group["group_key"]),
        telegram_user_id="1001",
        telegram_username="ops_user",
        callback_query_id="cbq-hold-1",
        approval_id=str(group["approval_id"]),
        note="need more observation",
        now_ts="2026-04-11T12:06:00+09:00",
        auto_drain=True,
    )

    stored_group = store.get_check_group(group_id=int(group["group_id"]))
    actions = store.list_check_actions(group_id=int(group["group_id"]))

    assert result["approval_result"]["summary"]["trigger_state"] == "APPROVAL_RECORDED"
    assert stored_group["status"] == "held"
    assert [action["action"] for action in actions] == ["hold"]
    assert bridge.get_apply_records() == []


def test_bridge_builds_korean_weight_patch_review_dispatch(tmp_path: Path) -> None:
    bridge, store, bus = _build_bridge(tmp_path)
    bus.publish(
        GovernanceActionNeeded(
            trace_id="trace-weight-1",
            occurred_at="2026-04-12T02:10:00+09:00",
            payload={
                "review_type": "STATE25_WEIGHT_PATCH_REVIEW",
                "governance_action": "state25_weight_patch_review",
                "action_target": "state25_weight_patch_log_only",
                "scope_key": "STATE25_WEIGHT_PATCH::BTCUSD::READY::upper_wick_weight",
                "symbol": "BTCUSD",
                "proposal_summary_ko": "윗꼬리 비중 과다로 상단 힘을 덜 읽는 문제를 조정합니다.",
                "scope_note_ko": "symbol=BTCUSD | entry_stage=READY | binding_mode=log_only",
                "report_title_ko": "학습 반영 제안 | 가중치 조정",
                "report_lines_ko": [
                    "관찰 장면: 윗꼬리 비중 과다",
                    "조정 항목:",
                    "- 윗꼬리 반응 비중: 기존 x1.00 -> 제안 x0.70 (하향 x0.70)",
                ],
                "weight_patch": {
                    "state25_execution_bind_mode": "log_only",
                    "state25_execution_symbol_allowlist": ["BTCUSD"],
                    "state25_execution_entry_stage_allowlist": ["READY"],
                    "state25_teacher_weight_overrides": {"upper_wick_weight": 0.7},
                },
            },
        )
    )

    bridge.drain_pending_events()
    group = store.get_check_group(
        group_key="STATE25_WEIGHT_PATCH::BTCUSD::READY::upper_wick_weight"
    )
    dispatch_records = bridge.get_dispatch_records()

    assert group["review_type"] == "STATE25_WEIGHT_PATCH_REVIEW"
    assert group["action_target"] == "state25_weight_patch_log_only"
    assert dispatch_records[0]["report_envelope"]["title_ko"] == "학습 반영 제안 | 가중치 조정"
    assert "윗꼬리 비중 과다" in dispatch_records[0]["dispatch_envelope"]["trigger_summary"]
    assert dispatch_records[0]["proposal_envelope"]["proposal_type"] == "STATE25_WEIGHT_PATCH_REVIEW"
    assert (
        dispatch_records[0]["proposal_envelope"]["scope_key"]
        == "STATE25_WEIGHT_PATCH::BTCUSD::READY::upper_wick_weight"
    )
