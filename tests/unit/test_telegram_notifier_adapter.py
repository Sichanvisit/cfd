from adapters.telegram_notifier_adapter import TelegramNotifierAdapter


def test_telegram_notifier_adapter_formats_messages():
    adapter = TelegramNotifierAdapter()

    entry_msg = adapter.format_entry_message(
        symbol="BTCUSD",
        action="BUY",
        score=123,
        price=50000.0,
        lot=0.1,
        reasons=["reason-a", "reason-b"],
        pos_count=1,
        max_pos=3,
    )
    exit_msg = adapter.format_exit_message(
        symbol="BTCUSD",
        profit=12.34,
        points=56,
        entry_price=49900.0,
        exit_price=50020.0,
    )

    assert isinstance(entry_msg, str)
    assert isinstance(exit_msg, str)
    assert "BTCUSD" in entry_msg
    assert "BTCUSD" in exit_msg

