from __future__ import annotations

import pandas as pd

from backend.services import adaptive_profile_helpers as helpers


class _QueryOnlyTradeLogger:
    def __init__(self, frame: pd.DataFrame):
        self._frame = frame
        self.query_calls: list[tuple[str, int]] = []

    def query_latest_closed(self, symbol: str = "", limit: int = 1) -> pd.DataFrame:
        self.query_calls.append((str(symbol or ""), int(limit)))
        return self._frame.copy()

    def read_closed_df(self) -> pd.DataFrame:
        raise AssertionError("full closed CSV path should not be used")


def test_refresh_exit_profile_prefers_recent_query_path():
    frame = pd.DataFrame(
        [
            {"symbol": "XAUUSD", "profit": 5.0, "exit_reason": "Protect Exit"},
            {"symbol": "XAUUSD", "profit": 3.0, "exit_reason": "Lock Exit"},
            {"symbol": "XAUUSD", "profit": -1.0, "exit_reason": "Protect Exit"},
            {"symbol": "BTCUSD", "profit": 4.0, "exit_reason": "Lock Exit"},
            {"symbol": "BTCUSD", "profit": 2.0, "exit_reason": "Protect Exit"},
            {"symbol": "BTCUSD", "profit": -2.0, "exit_reason": "Hold Exit"},
        ]
        * 4
    )
    logger = _QueryOnlyTradeLogger(frame)

    out = helpers.refresh_exit_profile(
        current_profile={},
        trade_logger=logger,
        normalize_exit_reason=lambda value: str(value or "").strip().lower(),
        reason_to_stage={
            "protect exit": "protect",
            "lock exit": "lock",
            "hold exit": "hold",
        },
    )

    assert logger.query_calls
    assert out["n"] >= 20
    assert set(out["stage_quality"].keys()) == {"protect", "lock", "hold"}


def test_refresh_entry_profile_prefers_recent_query_path():
    frame = pd.DataFrame(
        [
            {
                "symbol": "NAS100",
                "profit": 4.0,
                "entry_score": 80.0,
                "contra_score_at_entry": 20.0,
                "direction": "BUY",
                "ind_bb_20_up": 110.0,
                "ind_bb_20_dn": 90.0,
                "ind_bb_20_mid": 100.0,
                "ind_ma_20": 101.0,
                "ind_ma_60": 99.0,
                "open_price": 108.0,
            },
            {
                "symbol": "NAS100",
                "profit": 2.0,
                "entry_score": 70.0,
                "contra_score_at_entry": 25.0,
                "direction": "BUY",
                "ind_bb_20_up": 110.0,
                "ind_bb_20_dn": 90.0,
                "ind_bb_20_mid": 100.0,
                "ind_ma_20": 101.0,
                "ind_ma_60": 99.0,
                "open_price": 106.0,
            },
            {
                "symbol": "BTCUSD",
                "profit": -1.0,
                "entry_score": 35.0,
                "contra_score_at_entry": 30.0,
                "direction": "SELL",
                "ind_bb_20_up": 110.0,
                "ind_bb_20_dn": 90.0,
                "ind_bb_20_mid": 100.0,
                "ind_ma_20": 99.0,
                "ind_ma_60": 101.0,
                "open_price": 92.0,
            },
            {
                "symbol": "XAUUSD",
                "profit": 1.0,
                "entry_score": 65.0,
                "contra_score_at_entry": 40.0,
                "direction": "BUY",
                "ind_bb_20_up": 110.0,
                "ind_bb_20_dn": 90.0,
                "ind_bb_20_mid": 100.0,
                "ind_ma_20": 101.0,
                "ind_ma_60": 99.0,
                "open_price": 104.0,
            },
        ]
        * 10
    )
    logger = _QueryOnlyTradeLogger(frame)
    original_enabled = getattr(helpers.Config, "ENABLE_ADAPTIVE_ENTRY_ROUTING", True)
    helpers.Config.ENABLE_ADAPTIVE_ENTRY_ROUTING = True
    try:
        out = helpers.refresh_entry_profile(current_profile={}, trade_logger=logger)
    finally:
        helpers.Config.ENABLE_ADAPTIVE_ENTRY_ROUTING = original_enabled

    assert logger.query_calls
    assert float(out.get("updated_at", 0.0)) >= 0.0
