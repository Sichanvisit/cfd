"""
Execution service interface draft.
"""

from __future__ import annotations

from typing import Any

from ports.broker_port import BrokerPort


class ExecutionService:
    """Application service that sends execution requests through a broker port."""

    def __init__(self, broker: BrokerPort):
        self.broker = broker

    def send_order(self, request: dict[str, Any]) -> Any:
        return self.broker.order_send(request)
