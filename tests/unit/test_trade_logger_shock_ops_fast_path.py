from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from backend.trading.trade_logger_shock_ops import update_shock_event_progress


class _FakeShockTradeLogger:
    def __init__(self, tmp_path: Path):
        self.shock_event_filepath = str(tmp_path / "trade_shock_events.csv")
        self._shock_lock = object()
        self._shock_event_runtime_cache = {}
        self.write_count = 0
        self._ensure_shock_event_file()

    @staticmethod
    def _shock_columns():
        return [
            "ticket",
            "symbol",
            "direction",
            "lot",
            "event_time",
            "event_ts",
            "event_bucket",
            "event_price",
            "event_profit",
            "shock_score",
            "shock_level",
            "shock_reason",
            "shock_action",
            "pre_shock_stage",
            "post_shock_stage",
            "ticks_elapsed",
            "shock_hold_delta_10",
            "shock_hold_delta_30",
            "filled_10",
            "filled_30",
            "resolved",
            "close_time",
            "close_ts",
        ]

    def _normalize_shock_df(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = self._shock_columns()
        out = df.copy()
        for c in cols:
            if c not in out.columns:
                out[c] = 0 if c in {"ticket", "event_ts", "event_bucket", "ticks_elapsed", "filled_10", "filled_30", "resolved", "close_ts"} else ""
        for c in ["ticket", "event_ts", "event_bucket", "ticks_elapsed", "filled_10", "filled_30", "resolved", "close_ts"]:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
        for c in ["lot", "event_price", "event_profit", "shock_score", "shock_hold_delta_10", "shock_hold_delta_30"]:
            out[c] = pd.to_numeric(out[c], errors="coerce")
        for c in ["symbol", "direction", "event_time", "shock_level", "shock_reason", "shock_action", "pre_shock_stage", "post_shock_stage", "close_time"]:
            out[c] = out[c].fillna("").astype(str)
        return out[cols]

    def _ensure_shock_event_file(self):
        path = Path(self.shock_event_filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            pd.DataFrame(columns=self._shock_columns()).to_csv(path, index=False, encoding="utf-8-sig")

    def _read_shock_df_safe(self) -> pd.DataFrame:
        return self._normalize_shock_df(pd.read_csv(self.shock_event_filepath, encoding="utf-8-sig"))

    def _atomic_write_df(self, target_path: str, df: pd.DataFrame):
        self.write_count += 1
        df.to_csv(target_path, index=False, encoding="utf-8-sig")

    @contextmanager
    def _file_guard(self, _target_path: str, _lock):
        yield


def _seed_active_row(logger: _FakeShockTradeLogger) -> None:
    row = {
        "ticket": 1001,
        "symbol": "XAUUSD",
        "direction": "BUY",
        "lot": 0.1,
        "event_time": "2026-04-09 13:00:00",
        "event_ts": 1775707200,
        "event_bucket": 177570720,
        "event_price": 4700.0,
        "event_profit": 0.4,
        "shock_score": 65.0,
        "shock_level": "alert",
        "shock_reason": "opposite_score_spike",
        "shock_action": "downgrade_to_short",
        "pre_shock_stage": "mid",
        "post_shock_stage": "short",
        "ticks_elapsed": 0,
        "shock_hold_delta_10": float("nan"),
        "shock_hold_delta_30": float("nan"),
        "filled_10": 0,
        "filled_30": 0,
        "resolved": 0,
        "close_time": "",
        "close_ts": 0,
    }
    logger._shock_event_runtime_cache[1001] = dict(row)
    pd.DataFrame([row])[logger._shock_columns()].to_csv(logger.shock_event_filepath, index=False, encoding="utf-8-sig")


def test_update_shock_event_progress_skips_disk_write_when_no_threshold_fill(tmp_path: Path):
    logger = _FakeShockTradeLogger(tmp_path)
    _seed_active_row(logger)

    out = update_shock_event_progress(
        logger,
        ticket=1001,
        ticks_elapsed=5,
        delta_10=None,
        delta_30=None,
    )

    assert out == {"shock_hold_delta_10": None, "shock_hold_delta_30": None}
    assert logger.write_count == 0
    assert int(logger._shock_event_runtime_cache[1001]["ticks_elapsed"]) == 5


def test_update_shock_event_progress_writes_once_when_new_fill_arrives(tmp_path: Path):
    logger = _FakeShockTradeLogger(tmp_path)
    _seed_active_row(logger)

    out = update_shock_event_progress(
        logger,
        ticket=1001,
        ticks_elapsed=12,
        delta_10=0.42,
        delta_30=None,
    )

    assert logger.write_count == 1
    assert out["shock_hold_delta_10"] == 0.42
    assert out["shock_hold_delta_30"] is None
    assert int(logger._shock_event_runtime_cache[1001]["filled_10"]) == 1
