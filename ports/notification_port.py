"""Notification port definitions."""

from __future__ import annotations

from collections.abc import Mapping
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
        row: Mapping[str, object] | None = None,
    ) -> str:
        ...

    def format_exit_message(
        self,
        symbol: str,
        profit: float,
        points: float,
        entry_price: float,
        exit_price: float,
        exit_reason: str | None = None,
        review_context: Mapping[str, object] | None = None,
    ) -> str:
        ...

    def format_wait_message(
        self,
        symbol: str,
        action: str,
        price: float,
        pos_count: int,
        max_pos: int,
        reason: str | None = None,
        row: Mapping[str, object] | None = None,
    ) -> str:
        ...

    def build_wait_message_signature(
        self,
        symbol: str,
        action: str,
        reason: str | None = None,
        row: Mapping[str, object] | None = None,
    ) -> str:
        ...

    def format_reverse_message(
        self,
        symbol: str,
        action: str,
        score: float,
        price: float,
        reasons: list[str],
        pos_count: int,
        max_pos: int,
        pending: bool = False,
        row: Mapping[str, object] | None = None,
    ) -> str:
        ...

    def build_reverse_message_signature(
        self,
        symbol: str,
        action: str,
        score: float,
        reasons: list[str] | tuple[str, ...] | None,
        pending: bool = False,
    ) -> str:
        ...
