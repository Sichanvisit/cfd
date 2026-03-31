"""Notification port definitions."""

from __future__ import annotations

from typing import Protocol


class NotificationPort(Protocol):
    """Abstract interface for outbound notifications."""

    def send(self, message: str) -> None:
        ...

    def shutdown(self, timeout: float = 2.0) -> None:
        ...

    def format_entry_message(
        self,
        symbol: str,
        action: str,
        score: int,
        price: float,
        lot: float,
        reasons: list[str],
        pos_count: int,
        max_pos: int,
    ) -> str:
        ...

    def format_exit_message(
        self,
        symbol: str,
        profit: float,
        points: float,
        entry_price: float,
        exit_price: float,
    ) -> str:
        ...
