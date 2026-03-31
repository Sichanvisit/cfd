"""Observability port definitions."""

from __future__ import annotations

from typing import Any, Protocol


class ObservabilityPort(Protocol):
    """Abstract interface for runtime observability sinks."""

    def incr(self, name: str, amount: int = 1) -> None:
        ...

    def event(self, name: str, *, level: str = "info", payload: dict[str, Any] | None = None) -> None:
        ...

    def snapshot(self, last_n: int = 50) -> dict[str, Any]:
        ...

