"""Broker port definitions."""

from __future__ import annotations

from typing import Any, Protocol


class BrokerPort(Protocol):
    """Abstract interface for broker-side I/O."""

    def terminal_info(self) -> Any:
        ...

    def account_info(self) -> Any:
        ...

    def symbol_info_tick(self, symbol: str) -> Any:
        ...

    def symbol_info(self, symbol: str) -> Any:
        ...

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start_pos: int, count: int) -> Any:
        ...

    def copy_ticks_from(self, symbol: str, date_from: Any, count: int, flags: Any = None) -> Any:
        ...

    def market_book_add(self, symbol: str) -> Any:
        ...

    def market_book_get(self, symbol: str) -> Any:
        ...

    def market_book_release(self, symbol: str) -> Any:
        ...

    def symbols_get(self) -> Any:
        ...

    def history_deals_get(self, *args: Any, **kwargs: Any) -> Any:
        ...

    def positions_get(self, **kwargs: Any) -> Any:
        ...

    def order_send(self, request: dict[str, Any]) -> Any:
        ...

    def last_error(self) -> Any:
        ...
