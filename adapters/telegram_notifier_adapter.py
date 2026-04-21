"""Telegram adapter implementing the notification port."""

from __future__ import annotations

from collections.abc import Mapping

from ports.notification_port import NotificationPort

from backend.integrations import notifier
from backend.services.telegram_route_ownership_policy import (
    OWNER_RUNTIME_EXECUTION,
    validate_telegram_route_ownership,
)


class TelegramNotifierAdapter(NotificationPort):
    def send(self, message: str) -> None:
        validate_telegram_route_ownership(
            owner_key=OWNER_RUNTIME_EXECUTION,
            route="runtime",
        )
        notifier.send_telegram(message)

    def shutdown(self, timeout: float = 2.0) -> None:
        notifier.shutdown(timeout=timeout)

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
        return notifier.format_entry_message(
            symbol,
            action,
            score,
            price,
            lot,
            reasons,
            pos_count,
            max_pos,
            row=row,
        )

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
        return notifier.format_exit_message(
            symbol,
            profit,
            points,
            entry_price,
            exit_price,
            exit_reason=exit_reason,
            review_context=review_context,
        )

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
        return notifier.format_wait_message(
            symbol,
            action,
            price,
            pos_count,
            max_pos,
            reason=reason,
            row=row,
        )

    def build_wait_message_signature(
        self,
        symbol: str,
        action: str,
        reason: str | None = None,
        row: Mapping[str, object] | None = None,
    ) -> str:
        return notifier.build_wait_message_signature(
            symbol,
            action,
            reason=reason,
            row=row,
        )

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
        return notifier.format_reverse_message(
            symbol,
            action,
            score,
            price,
            reasons,
            pos_count,
            max_pos,
            pending=pending,
            row=row,
        )

    def build_reverse_message_signature(
        self,
        symbol: str,
        action: str,
        score: float,
        reasons: list[str] | tuple[str, ...] | None,
        pending: bool = False,
    ) -> str:
        return notifier.build_reverse_message_signature(
            symbol,
            action,
            score,
            reasons,
            pending=pending,
        )
