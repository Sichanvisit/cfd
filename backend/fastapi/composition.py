"""Composition root helpers for FastAPI runtime dependencies."""

from __future__ import annotations

from pathlib import Path

from backend.core.config import Config
from backend.services.csv_history_service import CsvHistoryService
from backend.services.layout_service import LayoutService
from backend.services.mt5_snapshot_service import Mt5SnapshotService
from backend.services.trade_read_service import TradeReadService
from backend.trading.trade_logger import TradeLogger


def compose_runtime_components(project_root: Path, trade_csv: Path) -> dict:
    """Build application services in one place for consistent dependency wiring."""
    trade_logger = TradeLogger(filename=str(getattr(Config, "TRADE_HISTORY_CSV_PATH", str(trade_csv))))
    trade_read_service = TradeReadService(trade_csv, trade_logger=trade_logger)
    mt5_snapshot_service = Mt5SnapshotService(trade_csv, trade_logger=trade_logger)
    return {
        "trade_logger": trade_logger,
        "trade_read_service": trade_read_service,
        "mt5_snapshot_service": mt5_snapshot_service,
        "exit_service": getattr(mt5_snapshot_service, "exit_service", None),
        "csv_history_service": CsvHistoryService(trade_read_service),
        "layout_service": LayoutService(project_root),
    }
