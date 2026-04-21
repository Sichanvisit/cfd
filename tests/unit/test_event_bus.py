from __future__ import annotations

from backend.services.event_bus import (
    ApprovalReceived,
    EventBus,
    GovernanceActionNeeded,
    LightRefreshCompleted,
    SystemPhaseChanged,
    WatchError,
)


def test_event_bus_publish_and_pending_count() -> None:
    bus = EventBus()

    bus.publish(LightRefreshCompleted(trace_id="t1", payload={"row_delta": 10}))

    assert bus.pending_count() == 1


def test_event_bus_dispatches_to_subscribed_handler() -> None:
    bus = EventBus()
    received: list[dict[str, object]] = []

    def handler(event: LightRefreshCompleted) -> None:
        received.append({"event_type": event.event_type, "trace_id": event.trace_id})

    bus.subscribe(LightRefreshCompleted, handler)
    bus.publish(LightRefreshCompleted(trace_id="trace-light"))
    drained = bus.drain()

    assert len(drained) == 1
    assert received == [{"event_type": "LightRefreshCompleted", "trace_id": "trace-light"}]
    assert bus.pending_count() == 0


def test_event_bus_dispatches_to_multiple_handlers() -> None:
    bus = EventBus()
    calls: list[str] = []

    def first(event: GovernanceActionNeeded) -> None:
        calls.append(f"first::{event.trace_id}")

    def second(event: GovernanceActionNeeded) -> None:
        calls.append(f"second::{event.trace_id}")

    bus.subscribe(GovernanceActionNeeded, first)
    bus.subscribe(GovernanceActionNeeded, second)
    bus.publish(GovernanceActionNeeded(trace_id="trace-governance"))
    bus.drain()

    assert calls == ["first::trace-governance", "second::trace-governance"]


def test_event_bus_isolates_handler_errors_and_continues_dispatch() -> None:
    bus = EventBus()
    calls: list[str] = []

    def broken(event: ApprovalReceived) -> None:
        raise RuntimeError(f"boom::{event.trace_id}")

    def healthy(event: ApprovalReceived) -> None:
        calls.append(event.trace_id)

    bus.subscribe(ApprovalReceived, broken)
    bus.subscribe(ApprovalReceived, healthy)
    bus.publish(ApprovalReceived(trace_id="trace-approval"))
    bus.drain()

    assert calls == ["trace-approval"]
    errors = bus.get_dispatch_errors()
    assert len(errors) == 1
    assert errors[0]["event_type"] == "ApprovalReceived"
    assert errors[0]["handler_name"] == "broken"
    assert errors[0]["error_type"] == "RuntimeError"
    assert "boom::trace-approval" in errors[0]["error_message"]


def test_event_bus_clear_dispatch_errors_returns_and_resets_errors() -> None:
    bus = EventBus()

    def broken(event: WatchError) -> None:
        raise ValueError("watch_failed")

    bus.subscribe(WatchError, broken)
    bus.publish(WatchError(trace_id="trace-watch"))
    bus.drain()

    cleared = bus.clear_dispatch_errors()

    assert len(cleared) == 1
    assert cleared[0]["event_type"] == "WatchError"
    assert bus.get_dispatch_errors() == []


def test_event_bus_drain_preserves_fifo_event_order() -> None:
    bus = EventBus()

    first = LightRefreshCompleted(trace_id="trace-1")
    second = SystemPhaseChanged(trace_id="trace-2")
    third = GovernanceActionNeeded(trace_id="trace-3")

    bus.publish(first)
    bus.publish(second)
    bus.publish(third)

    drained = bus.drain()

    assert [event.trace_id for event in drained] == ["trace-1", "trace-2", "trace-3"]


def test_event_bus_drains_event_without_subscribers() -> None:
    bus = EventBus()
    bus.publish(SystemPhaseChanged(trace_id="phase-trace", payload={"phase": "RUNNING"}))

    drained = bus.drain()

    assert len(drained) == 1
    assert drained[0].event_type == "SystemPhaseChanged"
    assert bus.get_dispatch_errors() == []
