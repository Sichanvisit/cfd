from __future__ import annotations

from backend.services.improvement_detector_policy import (
    DETECTOR_CANDLE_WEIGHT,
    DETECTOR_DAILY_SURFACE_LIMITS,
    DETECTOR_KEYS,
    DETECTOR_MIN_REPEAT_SAMPLES,
    DETECTOR_REVERSE_PATTERN,
    DETECTOR_SCENE_AWARE,
    DETECTOR_TOTAL_DAILY_SURFACE_LIMIT,
    build_improvement_detector_policy_baseline,
)


def test_improvement_detector_policy_baseline_contains_expected_limits() -> None:
    payload = build_improvement_detector_policy_baseline()

    assert payload["contract_version"] == "improvement_detector_policy_v1"
    assert payload["daily_surface_limit_total"] == DETECTOR_TOTAL_DAILY_SURFACE_LIMIT
    rows = {row["detector_key"]: row for row in payload["rows"]}

    assert set(rows) == set(DETECTOR_KEYS)
    assert rows[DETECTOR_SCENE_AWARE]["daily_surface_limit"] == DETECTOR_DAILY_SURFACE_LIMITS[DETECTOR_SCENE_AWARE]
    assert rows[DETECTOR_CANDLE_WEIGHT]["min_repeat_sample"] == DETECTOR_MIN_REPEAT_SAMPLES[DETECTOR_CANDLE_WEIGHT]
    assert rows[DETECTOR_REVERSE_PATTERN]["daily_surface_limit"] == DETECTOR_DAILY_SURFACE_LIMITS[DETECTOR_REVERSE_PATTERN]
