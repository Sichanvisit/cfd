"""Telegram adapter implementing the notification port."""

from __future__ import annotations

from ports.notification_port import NotificationPort

from backend.integrations import notifier


class TelegramNotifierAdapter(NotificationPort):
    def send(self, message: str) -> None:
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
    ) -> str:
        return notifier.format_entry_message(symbol, action, score, price, lot, reasons, pos_count, max_pos)

    def format_exit_message(
        self,
        symbol: str,
        profit: float,
        points: float,
        entry_price: float,
        exit_price: float,
    ) -> str:
        return notifier.format_exit_message(symbol, profit, points, entry_price, exit_price)
