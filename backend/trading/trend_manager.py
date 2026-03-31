# trend_manager.py
"""
기술지표 계산 및 추세/구조 판정 유틸리티.
"""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema


class TrendManager:
    """지표 생성 및 단순 추세 판정."""

    def add_indicators(self, df):
        """
        OHLCV DataFrame에 전략에서 사용하는 핵심 지표를 추가합니다.
        """
        if df is None or df.empty:
            return df

        df = df.copy()

        # 이동평균
        for period in [20, 40, 60, 120, 240, 480]:
            df[f"ma_{period}"] = df["close"].rolling(window=period).mean()

        # 볼린저밴드 20/2
        ma20 = df["close"].rolling(20).mean()
        std20 = df["close"].rolling(20).std()
        df["bb_20_up"] = ma20 + (2 * std20)
        df["bb_20_mid"] = ma20
        df["bb_20_dn"] = ma20 - (2 * std20)

        # 볼린저밴드 4/4
        ma4 = df["close"].rolling(4).mean()
        std4 = df["close"].rolling(4).std()
        df["bb_4_up"] = ma4 + (4 * std4)
        df["bb_4_dn"] = ma4 - (4 * std4)

        # 보조 볼린저밴드 4/3 (4/4 대비 터치 빈도 확보용)
        df["bb_4_3_up"] = ma4 + (3 * std4)
        df["bb_4_3_mid"] = ma4
        df["bb_4_3_dn"] = ma4 - (3 * std4)

        # 이격도(20MA 기준)
        df["disparity"] = (df["close"] / df["ma_20"]) * 100

        # RSI(14)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        loss = loss.replace(0, 0.00001)
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # ADX 구성요소
        df["h-l"] = df["high"] - df["low"]
        df["h-pc"] = abs(df["high"] - df["close"].shift(1))
        df["l-pc"] = abs(df["low"] - df["close"].shift(1))
        df["tr"] = df[["h-l", "h-pc", "l-pc"]].max(axis=1)

        df["up_move"] = df["high"] - df["high"].shift(1)
        df["down_move"] = df["low"].shift(1) - df["low"]
        df["plus_dm"] = np.where(
            (df["up_move"] > df["down_move"]) & (df["up_move"] > 0), df["up_move"], 0
        )
        df["minus_dm"] = np.where(
            (df["down_move"] > df["up_move"]) & (df["down_move"] > 0), df["down_move"], 0
        )

        tr14 = df["tr"].rolling(14).mean().replace(0, 1)
        plus_dm14 = df["plus_dm"].rolling(14).mean()
        minus_dm14 = df["minus_dm"].rolling(14).mean()
        df["plus_di"] = 100 * (plus_dm14 / tr14)
        df["minus_di"] = 100 * (minus_dm14 / tr14)

        di_sum = (df["plus_di"] + df["minus_di"]).replace(0, np.nan)
        dx = ((df["plus_di"] - df["minus_di"]).abs() / di_sum) * 100
        df["adx"] = dx.rolling(14).mean()

        return df

    def get_pivots(self, df, order=5):
        """
        국소 고점/저점 인덱스를 반환합니다.
        """
        if df is None or len(df) < order * 2:
            return [], []

        highs = df["high"].values
        lows = df["low"].values
        high_idx = argrelextrema(highs, np.greater, order=order)[0]
        low_idx = argrelextrema(lows, np.less, order=order)[0]
        return high_idx, low_idx

    def check_rule_of_4(self, df, current_price, tolerance_pips=10):
        """
        현재가 근처에 반복 터치된 지지/저항 횟수를 계산합니다.
        """
        if df is None or df.empty:
            return 0, 0

        high_idx, low_idx = self.get_pivots(df, order=5)

        # 자산 가격대에 따라 허용 오차 스케일 조정
        scale = 1.0 if current_price > 500 else 0.01
        tolerance = tolerance_pips * scale

        cnt_resistance = 0
        if len(high_idx) > 0:
            highs = df["high"].iloc[high_idx].values
            cnt_resistance = np.sum(np.abs(highs - current_price) < tolerance)

        cnt_support = 0
        if len(low_idx) > 0:
            lows = df["low"].iloc[low_idx].values
            cnt_support = np.sum(np.abs(lows - current_price) < tolerance)

        return int(cnt_resistance), int(cnt_support)

    def get_ma_alignment(self, candle):
        """
        MA 정렬 상태를 반환합니다.
        - BULL: ma_20 > ma_60 > ma_120 > ma_240 > ma_480
        - BEAR: 위의 역순
        - MIXED: 그 외
        """
        ma_keys = ["ma_20", "ma_60", "ma_120", "ma_240", "ma_480"]
        if not all(key in candle for key in ma_keys):
            return "MIXED"

        ma_vals = [candle[key] for key in ma_keys]
        if any(pd.isna(ma_vals)):
            return "MIXED"

        if ma_vals == sorted(ma_vals, reverse=True):
            return "BULL"
        if ma_vals == sorted(ma_vals):
            return "BEAR"
        return "MIXED"
