# session_manager.py
"""
Session box calculation helper.
"""

import os
import time
from datetime import datetime, timedelta

import pandas as pd
from zoneinfo import ZoneInfo

from backend.core.config import Config


class SessionManager:
    """Session box calculator."""

    def __init__(self):
        try:
            self._tz = ZoneInfo(str(getattr(Config, "TIMEZONE", "Asia/Seoul") or "Asia/Seoul"))
        except Exception:
            self._tz = ZoneInfo("Asia/Seoul")

    # KST 기준 [start, end)
    # - ASIA:   08:00 ~ 16:00
    # - EUROPE: 16:00 ~ 24:00
    # - USA:    00:00 ~ 08:00
    # (단순 8시간 블록, DST 반영 없음)
    SESSIONS = {
        "ASIA": {"start": 8, "end": 16, "color": 65535},
        "EUROPE": {"start": 16, "end": 24, "color": 65280},
        "USA": {"start": 0, "end": 8, "color": 255},
    }

    def get_session_range(self, df_h1, start_hour, end_hour):
        """해당 세션의 최근 일자 high/low/time range 반환."""
        if df_h1 is None or df_h1.empty:
            return None

        df = df_h1.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["time"]):
            # MT5 epoch seconds are UTC; convert to configured local timezone for session slicing.
            df["dt"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_convert(self._tz)
        else:
            dt = pd.to_datetime(df["time"], errors="coerce")
            if getattr(dt.dt, "tz", None) is None:
                dt = dt.dt.tz_localize("UTC")
            df["dt"] = dt.dt.tz_convert(self._tz)

        # Support normal and cross-midnight ranges.
        if int(start_hour) < int(end_hour):
            mask = (df["dt"].dt.hour >= int(start_hour)) & (df["dt"].dt.hour < int(end_hour))
        else:
            mask = (df["dt"].dt.hour >= int(start_hour)) | (df["dt"].dt.hour < int(end_hour))
        session_df = df[mask]
        if session_df.empty:
            return None

        last_date = session_df["dt"].dt.date.max()
        today_session = session_df[session_df["dt"].dt.date == last_date]
        if today_session.empty:
            return None

        t1 = today_session["time"].iloc[0]
        t2 = today_session["time"].iloc[-1]
        t1 = int(t1.timestamp()) if isinstance(t1, pd.Timestamp) else int(t1)
        t2 = int(t2.timestamp()) if isinstance(t2, pd.Timestamp) else int(t2)

        # Build exact session boundary in local timezone, then map to epoch.
        session_start_local = datetime(
            year=last_date.year,
            month=last_date.month,
            day=last_date.day,
            hour=int(start_hour),
            minute=0,
            second=0,
            tzinfo=self._tz,
        )
        start_h = int(start_hour)
        end_h = int(end_hour)
        if end_h >= 24:
            base_end = datetime(
                year=last_date.year,
                month=last_date.month,
                day=last_date.day,
                hour=0,
                minute=0,
                second=0,
                tzinfo=self._tz,
            )
            session_end_local = base_end + timedelta(days=1)
        else:
            end_date = last_date
            # Cross-midnight session ends on next local date.
            if end_h <= start_h:
                end_date = last_date + timedelta(days=1)
            session_end_local = datetime(
                year=end_date.year,
                month=end_date.month,
                day=end_date.day,
                hour=end_h,
                minute=0,
                second=0,
                tzinfo=self._tz,
            )
        planned_session_end = int(session_end_local.timestamp())

        # Optional clipping for in-progress session.
        # Default keeps fixed session boundaries for contiguous boxes.
        clip_to_now = str(os.getenv("SESSION_BOX_CLIP_TO_NOW", "0")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        now_local = datetime.now(self._tz)
        now_epoch = int(now_local.timestamp())
        same_date_as_now = (last_date == now_local.date())
        session_running = bool(same_date_as_now and (now_epoch < planned_session_end))
        if clip_to_now and session_running:
            t2_effective = max(t1, min(planned_session_end, now_epoch))
        else:
            t2_effective = planned_session_end

        return {
            "high": float(today_session["high"].max()),
            "low": float(today_session["low"].min()),
            "t1": max(int(session_start_local.timestamp()), int(t1)),
            "t2": int(t2_effective),
            "date": last_date,
        }

    def get_all_sessions(self, df_h1):
        """정의된 모든 세션의 박스 정보 반환."""
        sessions = {}
        for name, config in self.SESSIONS.items():
            data = self.get_session_range(df_h1, config["start"], config["end"])
            if data:
                data["color"] = config["color"]
                sessions[name] = data
        return sessions

    def get_expansion_target(self, session_data, current_price):
        """박스 돌파 시 1x 확장 타겟 계산."""
        if not session_data:
            return None

        high = session_data["high"]
        low = session_data["low"]
        box_height = high - low
        if box_height <= 0:
            return None

        if current_price > high:
            return high + box_height
        if current_price < low:
            return low - box_height
        return None

    def get_position_in_box(self, session_data, current_price):
        """현재가의 박스 내 위치 반환."""
        if not session_data:
            return "UNKNOWN"

        high = session_data["high"]
        low = session_data["low"]
        box_height = high - low

        if current_price > high:
            return "ABOVE"
        if current_price < low:
            return "BELOW"

        upper_zone = high - (box_height * 0.33)
        lower_zone = low + (box_height * 0.33)

        if current_price >= upper_zone:
            return "UPPER"
        if current_price <= lower_zone:
            return "LOWER"
        return "MIDDLE"
