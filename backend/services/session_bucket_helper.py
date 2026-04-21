from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo


SESSION_BUCKET_HELPER_VERSION = "session_bucket_helper_v1"
SESSION_BUCKET_TIMEZONE = "Asia/Seoul"
SESSION_BUCKET_ENUM_V1 = ("ASIA", "EU", "EU_US_OVERLAP", "US")
SESSION_BUCKET_WINDOWS_V1: tuple[dict[str, str], ...] = (
    {"bucket": "ASIA", "start_kst": "06:00", "end_kst": "15:00"},
    {"bucket": "EU", "start_kst": "15:00", "end_kst": "21:00"},
    {"bucket": "EU_US_OVERLAP", "start_kst": "21:00", "end_kst": "00:00"},
    {"bucket": "US", "start_kst": "00:00", "end_kst": "06:00"},
)
_KST = ZoneInfo(SESSION_BUCKET_TIMEZONE)
_RUNTIME_ROW_TIME_KEYS = (
    "timestamp",
    "time",
    "generated_at",
    "bar_time",
    "current_bar_time",
    "last_bar_time",
    "ts",
)


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        raw = float(value)
        if abs(raw) > 1_000_000_000_000:
            raw = raw / 1000.0
        try:
            dt = datetime.fromtimestamp(raw, tz=_KST)
        except Exception:
            return None
    else:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_KST)
    return dt.astimezone(_KST)


def _resolve_bucket_for_minutes(minutes: int) -> str:
    if 0 <= minutes < 360:
        return "US"
    if 360 <= minutes < 900:
        return "ASIA"
    if 900 <= minutes < 1260:
        return "EU"
    return "EU_US_OVERLAP"


def resolve_session_bucket_v1(value: Any = None) -> str:
    dt = _coerce_datetime(value) or datetime.now(_KST)
    minutes = int(dt.hour) * 60 + int(dt.minute)
    return _resolve_bucket_for_minutes(minutes)


def build_session_bucket_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": SESSION_BUCKET_HELPER_VERSION,
        "timezone": SESSION_BUCKET_TIMEZONE,
        "uses_dst_adjustment": False,
        "transition_buckets_enabled": False,
        "buckets": [dict(row) for row in SESSION_BUCKET_WINDOWS_V1],
    }


def build_session_bucket_surface_v1(value: Any = None) -> dict[str, Any]:
    dt = _coerce_datetime(value) or datetime.now(_KST)
    bucket = resolve_session_bucket_v1(dt)
    return {
        "contract_version": SESSION_BUCKET_HELPER_VERSION,
        "session_bucket": bucket,
        "timezone": SESSION_BUCKET_TIMEZONE,
        "uses_dst_adjustment": False,
        "transition_buckets_enabled": False,
        "resolved_at_kst": dt.isoformat(timespec="seconds"),
    }


def build_runtime_row_session_bucket_surface_v1(
    row: Mapping[str, Any] | None,
    *,
    default_now: datetime | None = None,
) -> dict[str, Any]:
    payload = dict(row or {}) if isinstance(row, Mapping) else {}
    resolved_value: Any = None
    resolved_source = "now"
    for key in _RUNTIME_ROW_TIME_KEYS:
        candidate = payload.get(key)
        if _coerce_datetime(candidate) is not None:
            resolved_value = candidate
            resolved_source = str(key)
            break
    if resolved_value is None:
        resolved_value = default_now or datetime.now(_KST)
    surface = build_session_bucket_surface_v1(resolved_value)
    surface["timestamp_source"] = resolved_source
    return surface
