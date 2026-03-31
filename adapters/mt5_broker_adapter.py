"""MetaTrader5 adapter implementing the broker port."""

from __future__ import annotations

from typing import Any

import MetaTrader5 as mt5

from ports.broker_port import BrokerPort


class MT5BrokerAdapter(BrokerPort):
    def terminal_info(self) -> Any:
        return mt5.terminal_info()

    def account_info(self) -> Any:
        return mt5.account_info()

    def symbol_info_tick(self, symbol: str) -> Any:
        return mt5.symbol_info_tick(symbol)

    def symbol_info(self, symbol: str) -> Any:
        return mt5.symbol_info(symbol)

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start_pos: int, count: int) -> Any:
        return mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)

    def copy_ticks_from(self, symbol: str, date_from: Any, count: int, flags: Any = None) -> Any:
        tick_flags = mt5.COPY_TICKS_ALL if flags is None else flags
        return mt5.copy_ticks_from(symbol, date_from, count, tick_flags)

    def market_book_add(self, symbol: str) -> Any:
        return mt5.market_book_add(symbol)

    def market_book_get(self, symbol: str) -> Any:
        return mt5.market_book_get(symbol)

    def market_book_release(self, symbol: str) -> Any:
        return mt5.market_book_release(symbol)

    def symbols_get(self) -> Any:
        return mt5.symbols_get()

    def history_deals_get(self, *args: Any, **kwargs: Any) -> Any:
        return mt5.history_deals_get(*args, **kwargs)

    def positions_get(self, **kwargs: Any) -> Any:
        return mt5.positions_get(**kwargs)

    def order_send(self, request: dict[str, Any]) -> Any:
        return mt5.order_send(request)

    def last_error(self) -> Any:
        return mt5.last_error()
