import pandas as pd

from backend.trading.scorer import Scorer


def test_level_retest_hold_score_buy():
    scorer = Scorer()
    m15 = pd.DataFrame(
        {
            "high": [100.2, 100.4, 100.8, 101.2, 101.5],
            "low": [99.8, 100.0, 100.1, 100.3, 100.6],
            "close": [100.0, 100.2, 100.6, 101.0, 101.3],
        }
    )
    add, reason = scorer._level_retest_hold_score(
        m15=m15,
        level=100.5,
        side="BUY",
        label="TEST",
        base_score=90,
        lookback=5,
        tol_ratio=0.001,
    )
    assert add == 90
    assert "돌파지지" in reason


def test_level_retest_hold_score_sell():
    scorer = Scorer()
    m15 = pd.DataFrame(
        {
            "high": [101.2, 101.0, 100.8, 100.6, 100.4],
            "low": [100.7, 100.4, 100.1, 99.9, 99.6],
            "close": [100.9, 100.6, 100.2, 100.0, 99.8],
        }
    )
    add, reason = scorer._level_retest_hold_score(
        m15=m15,
        level=100.3,
        side="SELL",
        label="TEST",
        base_score=80,
        lookback=5,
        tol_ratio=0.001,
    )
    assert add == 80
    assert "이탈저항" in reason

