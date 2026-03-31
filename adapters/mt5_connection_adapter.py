"""Adapter-level wrappers for MT5 terminal lifecycle."""

from __future__ import annotations

from backend.integrations.mt5_connection import connect_to_mt5, disconnect_mt5

__all__ = ["connect_to_mt5", "disconnect_mt5"]

