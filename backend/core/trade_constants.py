"""Broker-agnostic trade constants used by service/domain layers."""

from __future__ import annotations

try:
    import MetaTrader5 as _mt5

    ORDER_TYPE_BUY = int(_mt5.ORDER_TYPE_BUY)
    ORDER_TYPE_SELL = int(_mt5.ORDER_TYPE_SELL)
    TRADE_ACTION_DEAL = int(_mt5.TRADE_ACTION_DEAL)
    TRADE_ACTION_SLTP = int(_mt5.TRADE_ACTION_SLTP)
    ORDER_TIME_GTC = int(_mt5.ORDER_TIME_GTC)
    ORDER_FILLING_IOC = int(_mt5.ORDER_FILLING_IOC)
    TRADE_RETCODE_DONE = int(_mt5.TRADE_RETCODE_DONE)
    TIMEFRAME_M1 = int(_mt5.TIMEFRAME_M1)
    TIMEFRAME_M5 = int(_mt5.TIMEFRAME_M5)
    TIMEFRAME_M15 = int(_mt5.TIMEFRAME_M15)
    TIMEFRAME_M30 = int(_mt5.TIMEFRAME_M30)
    TIMEFRAME_H1 = int(_mt5.TIMEFRAME_H1)
    TIMEFRAME_H4 = int(_mt5.TIMEFRAME_H4)
    TIMEFRAME_D1 = int(_mt5.TIMEFRAME_D1)
    TIMEFRAME_W1 = int(_mt5.TIMEFRAME_W1)
    DEAL_ENTRY_OUT = int(_mt5.DEAL_ENTRY_OUT)
    DEAL_ENTRY_OUT_BY = int(_mt5.DEAL_ENTRY_OUT_BY)
    DEAL_TYPE_BUY = int(_mt5.DEAL_TYPE_BUY)
    DEAL_TYPE_SELL = int(_mt5.DEAL_TYPE_SELL)
except Exception:
    # MT5 fallback constants for test/runtime environments without SDK.
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_SLTP = 6
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_RETCODE_DONE = 10009
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 16385
    TIMEFRAME_H4 = 16388
    TIMEFRAME_D1 = 16408
    TIMEFRAME_W1 = 32769
    DEAL_ENTRY_OUT = 1
    DEAL_ENTRY_OUT_BY = 3
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1
