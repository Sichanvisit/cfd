from pathlib import Path

from backend.fastapi import composition


def test_compose_runtime_components_uses_one_resolved_trade_csv(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class FakeTradeLogger:
        def __init__(self, *, filename: str):
            captured["logger_filename"] = filename

    class FakeTradeReadService:
        def __init__(self, trade_csv: Path, *, trade_logger):
            captured["read_trade_csv"] = Path(trade_csv)
            captured["read_trade_logger"] = trade_logger

    class FakeMt5SnapshotService:
        def __init__(self, trade_csv: Path, *, trade_logger):
            captured["snapshot_trade_csv"] = Path(trade_csv)
            captured["snapshot_trade_logger"] = trade_logger

    monkeypatch.setattr(composition.Config, "TRADE_HISTORY_CSV_PATH", r"data\trades\trade_history.csv", raising=False)
    monkeypatch.setattr(composition, "TradeLogger", FakeTradeLogger)
    monkeypatch.setattr(composition, "TradeReadService", FakeTradeReadService)
    monkeypatch.setattr(composition, "Mt5SnapshotService", FakeMt5SnapshotService)

    components = composition.compose_runtime_components(tmp_path, tmp_path / "trade_history.csv")

    expected = tmp_path / "data" / "trades" / "trade_history.csv"
    assert Path(captured["logger_filename"]) == expected
    assert captured["read_trade_csv"] == expected
    assert captured["snapshot_trade_csv"] == expected
    assert captured["read_trade_logger"] is components["trade_logger"]
    assert captured["snapshot_trade_logger"] is components["trade_logger"]
