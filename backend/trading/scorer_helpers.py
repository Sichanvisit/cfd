# 한글 설명: Scorer의 공통 결과 포맷과 타임프레임 행 수집 로직을 분리한 보조 모듈입니다.
"""Helper functions for scorer orchestration."""

from __future__ import annotations


def empty_score_result() -> dict:
    return {
        "buy": {"total": 0, "reasons": []},
        "sell": {"total": 0, "reasons": []},
        "wait": {"total": 0, "reasons": []},
        "components": {
            "h1_context_buy": 0,
            "h1_context_sell": 0,
            "m1_trigger_buy": 0,
            "m1_trigger_sell": 0,
            "wait_score": 0,
            "wait_conflict": 0,
            "wait_noise": 0,
        },
        "timeframe_stack": {},
        "regime": {
            "name": "N/A",
            "volume_ratio": 1.0,
            "volatility_ratio": 1.0,
            "spread_ratio": 0.0,
            "buy_multiplier": 1.0,
            "sell_multiplier": 1.0,
        },
    }


def collect_timeframe_rows(df_all: dict, trend_mgr) -> dict:
    tf_rows = {}
    for tf in ("1D", "4H", "2H", "1H", "30M", "15M", "5M", "1M"):
        frame = df_all.get(tf)
        if frame is None or frame.empty:
            continue
        try:
            frame_ind = trend_mgr.add_indicators(frame.copy())
            if frame_ind is None or frame_ind.empty:
                frame_ind = frame
        except Exception:
            frame_ind = frame
        if frame_ind is not None and not frame_ind.empty:
            tf_rows[tf] = frame_ind.iloc[-1]
    return tf_rows
