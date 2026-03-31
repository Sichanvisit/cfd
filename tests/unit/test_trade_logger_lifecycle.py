import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from backend.trading.trade_logger_lifecycle import reconcile_open_trades


class _DummyBroker:
    def __init__(self, *, positions=None, history=None):
        self._positions = list(positions or [])
        self._history = list(history or [])
        self.positions_get_calls = 0
        self.history_deals_get_calls = 0

    def positions_get(self):
        self.positions_get_calls += 1
        return list(self._positions)

    def history_deals_get(self, date_from=None, date_to=None):
        self.history_deals_get_calls += 1
        return list(self._history)


class _DummyTradeLogger:
    def __init__(self, *, df, broker, profile_path: Path):
        self._df = df
        self.broker = broker
        self.startup_reconcile_profile_path = str(profile_path)
        self.filepath = str(profile_path.with_name("trade_history.csv"))
        self.active_tickets = {int(v) for v in pd.to_numeric(df.get("ticket", pd.Series(dtype=int)), errors="coerce").fillna(0).astype(int).tolist() if int(v) > 0}
        self.update_calls = []

    def _read_open_df_safe(self):
        return self._df.copy()

    def _normalize_dataframe(self, df):
        return df.copy()

    def _find_latest_exit_deal(self, history, ticket):
        for deal in history:
            if int(getattr(deal, "ticket", 0) or 0) == int(ticket):
                return deal
        return None

    def _find_latest_exit_deal_direct(self, ticket):
        return None

    def _update_closed_trade(self, ticket, deal, fallback_reason="Manual/Unknown"):
        self.update_calls.append((int(ticket), fallback_reason))
        return {"ticket": int(ticket)}


def test_reconcile_open_trades_profiles_no_open_rows(tmp_path):
    profile_path = tmp_path / "startup_reconcile_latest.json"
    logger = _DummyTradeLogger(
        df=pd.DataFrame(columns=["ticket", "status", "open_time"]),
        broker=_DummyBroker(),
        profile_path=profile_path,
    )

    result = reconcile_open_trades(logger, lookback_days=30, light_mode=True, profile=True)

    assert result == (0, 0, 0)
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    assert payload["status"] == "no_open_rows"
    assert payload["light_mode_requested"] is True
    assert payload["light_mode_applied"] is True
    assert payload["counts"]["open_rows"] == 0
    assert payload["timings_ms"]["total"] >= 0.0


def test_reconcile_open_trades_profiles_closed_ticket_with_history(tmp_path):
    profile_path = tmp_path / "startup_reconcile_latest.json"
    df = pd.DataFrame(
        [
            {"ticket": 1, "status": "OPEN", "open_time": "2026-03-24 09:00:00"},
            {"ticket": 2, "status": "OPEN", "open_time": "2026-03-24 09:05:00"},
        ]
    )
    broker = _DummyBroker(
        positions=[SimpleNamespace(ticket=1)],
        history=[SimpleNamespace(ticket=2)],
    )
    logger = _DummyTradeLogger(df=df, broker=broker, profile_path=profile_path)

    result = reconcile_open_trades(logger, lookback_days=30, light_mode=False, profile=True)

    assert result == (2, 1, 0)
    assert logger.update_calls == [(2, "Manual/Unknown")]
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["counts"]["open_rows"] == 2
    assert payload["counts"]["live_positions"] == 1
    assert payload["counts"]["history_deals"] == 1
    assert payload["counts"]["closed_with_deal"] == 1


def test_reconcile_open_trades_light_mode_defers_closed_updates(tmp_path):
    profile_path = tmp_path / "startup_reconcile_latest.json"
    trade_csv = tmp_path / "trade_history.csv"
    pd.DataFrame(
        [
            {"ticket": 11, "status": "OPEN", "open_time": "2026-03-24 09:00:00", "symbol": "XAUUSD"},
            {"ticket": 12, "status": "OPEN", "open_time": "2026-03-24 09:05:00", "symbol": "XAUUSD"},
        ]
    ).to_csv(trade_csv, index=False, encoding="utf-8-sig")
    broker = _DummyBroker(
        positions=[SimpleNamespace(ticket=11)],
        history=[SimpleNamespace(ticket=12)],
    )
    logger = _DummyTradeLogger(df=pd.DataFrame(), broker=broker, profile_path=profile_path)
    logger.filepath = str(trade_csv)

    result = reconcile_open_trades(logger, lookback_days=30, light_mode=True, profile=True)

    assert result == (2, 0, 0)
    assert logger.update_calls == []
    assert broker.positions_get_calls == 1
    assert broker.history_deals_get_calls == 0
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok_light"
    assert payload["light_mode_applied"] is True
    assert payload["counts"]["open_rows"] == 2
    assert payload["counts"]["live_positions"] == 1
    assert payload["counts"]["deferred_non_live_open_rows"] == 1
