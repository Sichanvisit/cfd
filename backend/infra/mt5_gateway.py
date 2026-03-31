"""Backward-compatible gateway shim.

Prefer `adapters.mt5_broker_adapter.MT5BrokerAdapter`.
"""

from adapters.mt5_broker_adapter import MT5BrokerAdapter


class MT5Gateway(MT5BrokerAdapter):
    """Compatibility alias for legacy imports."""

    pass
