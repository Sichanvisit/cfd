from backend.services.execution_service import ExecutionService


class _FakeBroker:
    def __init__(self):
        self.last_request = None

    def order_send(self, request):
        self.last_request = request
        return {"ok": True, "request": request}


def test_execution_service_sends_via_broker_port():
    broker = _FakeBroker()
    service = ExecutionService(broker)
    request = {"symbol": "BTCUSD", "type": "BUY", "volume": 0.1}

    result = service.send_order(request)

    assert broker.last_request == request
    assert result["ok"] is True

