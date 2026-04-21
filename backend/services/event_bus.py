from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Callable, TypeVar


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


@dataclass(slots=True)
class EventEnvelope:
    trace_id: str = ""
    occurred_at: str = field(default_factory=_now_iso)
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


@dataclass(slots=True)
class LightRefreshCompleted(EventEnvelope):
    pass


@dataclass(slots=True)
class GovernanceActionNeeded(EventEnvelope):
    pass


@dataclass(slots=True)
class ApprovalReceived(EventEnvelope):
    pass


@dataclass(slots=True)
class SystemPhaseChanged(EventEnvelope):
    pass


@dataclass(slots=True)
class WatchError(EventEnvelope):
    pass


EventT = TypeVar("EventT", bound=EventEnvelope)
EventHandler = Callable[[EventEnvelope], Any]


class EventBus:
    def __init__(self) -> None:
        self._queue: deque[EventEnvelope] = deque()
        self._subscribers: dict[type[EventEnvelope], list[EventHandler]] = defaultdict(list)
        self._dispatch_errors: list[dict[str, Any]] = []
        self._lock = Lock()

    def subscribe(self, event_type: type[EventT], handler: Callable[[EventT], Any]) -> None:
        with self._lock:
            handlers = self._subscribers[event_type]
            if handler not in handlers:
                handlers.append(handler)

    def publish(self, event: EventEnvelope) -> None:
        if not isinstance(event, EventEnvelope):
            raise TypeError("event_must_be_event_envelope")
        with self._lock:
            self._queue.append(event)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._queue)

    def drain(self, *, max_events: int | None = None) -> list[EventEnvelope]:
        drained: list[EventEnvelope] = []
        processed = 0
        while True:
            with self._lock:
                if not self._queue:
                    break
                if max_events is not None and processed >= max_events:
                    break
                event = self._queue.popleft()
                handlers = list(self._subscribers.get(type(event), []))
            drained.append(event)
            processed += 1
            for handler in handlers:
                try:
                    handler(event)
                except Exception as exc:
                    with self._lock:
                        self._dispatch_errors.append(
                            {
                                "event_type": event.event_type,
                                "trace_id": event.trace_id,
                                "handler_name": getattr(handler, "__name__", handler.__class__.__name__),
                                "error_type": exc.__class__.__name__,
                                "error_message": str(exc),
                                "occurred_at": _now_iso(),
                            }
                        )
        return drained

    def get_dispatch_errors(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._dispatch_errors)

    def clear_dispatch_errors(self) -> list[dict[str, Any]]:
        with self._lock:
            errors = deepcopy(self._dispatch_errors)
            self._dispatch_errors.clear()
            return errors
