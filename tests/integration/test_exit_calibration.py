from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml.calibrate_exit_params import calibrate


def test_calibrate_exit_params_smoke(tmp_path: Path):
    source = tmp_path / "trade_history.csv"
    rows = []
    for i in range(60):
        profit = float((i % 9) - 4)
        reason = "Protect Exit, protect=190 lock=120 hold=80" if profit <= 0 else "Lock Exit, protect=80 lock=170 hold=155"
        rows.append(
            {
                "ticket": i + 1,
                "symbol": "NAS100",
                "direction": "BUY" if i % 2 == 0 else "SELL",
                "open_time": f"2026-02-20 09:{i%60:02d}:00",
                "close_time": f"2026-02-20 10:{i%60:02d}:00",
                "profit": profit,
                "status": "CLOSED",
                "exit_reason": reason,
                "regime_spread_ratio": 1.15 if i % 3 == 0 else 1.0,
            }
        )
    pd.DataFrame(rows).to_csv(source, index=False, encoding="utf-8-sig")
    out = calibrate(source, max_rows=200)

    assert out["sample_size"] == 60
    assert 100 <= int(out["EXIT_PROTECT_THRESHOLD"]) <= 260
    assert 80 <= int(out["EXIT_LOCK_THRESHOLD"]) <= 240
    assert 80 <= int(out["EXIT_HOLD_THRESHOLD"]) <= 260
    assert 1 <= int(out["EXIT_CONFIRM_TICKS"]) <= 4
    assert 0.8 <= float(out["EXIT_EV_K"]) <= 2.0
