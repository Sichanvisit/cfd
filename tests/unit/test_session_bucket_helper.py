from datetime import datetime
from zoneinfo import ZoneInfo

from backend.services.session_bucket_helper import (
    SESSION_BUCKET_HELPER_VERSION,
    build_runtime_row_session_bucket_surface_v1,
    build_session_bucket_contract_v1,
    resolve_session_bucket_v1,
)


KST = ZoneInfo("Asia/Seoul")


def test_resolve_session_bucket_v1_boundary_cases():
    assert resolve_session_bucket_v1(datetime(2026, 4, 15, 0, 0, tzinfo=KST)) == "US"
    assert resolve_session_bucket_v1(datetime(2026, 4, 15, 5, 59, tzinfo=KST)) == "US"
    assert resolve_session_bucket_v1(datetime(2026, 4, 15, 6, 0, tzinfo=KST)) == "ASIA"
    assert resolve_session_bucket_v1(datetime(2026, 4, 15, 14, 59, tzinfo=KST)) == "ASIA"
    assert resolve_session_bucket_v1(datetime(2026, 4, 15, 15, 0, tzinfo=KST)) == "EU"
    assert resolve_session_bucket_v1(datetime(2026, 4, 15, 20, 59, tzinfo=KST)) == "EU"
    assert resolve_session_bucket_v1(datetime(2026, 4, 15, 21, 0, tzinfo=KST)) == "EU_US_OVERLAP"
    assert resolve_session_bucket_v1(datetime(2026, 4, 15, 23, 59, tzinfo=KST)) == "EU_US_OVERLAP"


def test_build_runtime_row_session_bucket_surface_v1_uses_runtime_timestamp():
    surface = build_runtime_row_session_bucket_surface_v1(
        {"timestamp": "2026-04-15T15:00:00+09:00"}
    )

    assert surface["contract_version"] == SESSION_BUCKET_HELPER_VERSION
    assert surface["session_bucket"] == "EU"
    assert surface["timestamp_source"] == "timestamp"


def test_build_runtime_row_session_bucket_surface_v1_falls_back_to_now():
    surface = build_runtime_row_session_bucket_surface_v1(
        {},
        default_now=datetime(2026, 4, 15, 21, 30, tzinfo=KST),
    )

    assert surface["session_bucket"] == "EU_US_OVERLAP"
    assert surface["timestamp_source"] == "now"


def test_build_session_bucket_contract_v1_is_fixed_four_bucket_contract():
    contract = build_session_bucket_contract_v1()

    assert contract["contract_version"] == SESSION_BUCKET_HELPER_VERSION
    assert contract["uses_dst_adjustment"] is False
    assert contract["transition_buckets_enabled"] is False
    assert [row["bucket"] for row in contract["buckets"]] == [
        "ASIA",
        "EU",
        "EU_US_OVERLAP",
        "US",
    ]
