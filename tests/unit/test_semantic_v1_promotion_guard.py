from backend.core.config import Config
from ml.semantic_v1.promotion_guard import SemanticPromotionGuard, normalize_rollout_mode


def test_normalize_rollout_mode_handles_unknown_values():
    assert normalize_rollout_mode("threshold_only") == "threshold_only"
    assert normalize_rollout_mode("weird") == "disabled"


def test_entry_rollout_guard_keeps_log_only_without_adjustment(monkeypatch):
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "log_only", raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_KILL_SWITCH", False, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_REQUIRE_CLEAN_TRACE", True, raising=False)

    decision = SemanticPromotionGuard.evaluate_entry_rollout(
        symbol="BTCUSD",
        baseline_action="BUY",
        entry_stage="aggressive",
        current_threshold=300,
        semantic_prediction={
            "available": True,
            "should_enter": True,
            "trace_quality_state": "clean",
            "timing": {"probability": 0.72, "threshold": 0.55},
            "entry_quality": {"probability": 0.66, "threshold": 0.55},
        },
        runtime_snapshot_row={
            "missing_feature_count": 0,
            "data_completeness_ratio": 1.0,
            "used_fallback_count": 0,
            "compatibility_mode": "",
        },
    )

    assert decision["mode"] == "log_only"
    assert decision["fallback_applied"] is False
    assert decision["threshold_applied"] is False
    assert decision["threshold_state"] == "mode_no_threshold"
    assert decision["threshold_inactive_reason"] == "mode_log_only"
    assert decision["threshold_after"] == 300


def test_entry_rollout_guard_applies_threshold_relief_in_threshold_mode(monkeypatch):
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "threshold_only", raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_KILL_SWITCH", False, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_REQUIRE_CLEAN_TRACE", True, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_MAX_MISSING_FEATURES", 2, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_THRESHOLD_RELIEF_GAIN", 100.0, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_THRESHOLD_RELIEF_MAX_PTS", 18, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_THRESHOLD_MIN_ADJUST_PTS", 2, raising=False)

    decision = SemanticPromotionGuard.evaluate_entry_rollout(
        symbol="BTCUSD",
        baseline_action="BUY",
        entry_stage="aggressive",
        current_threshold=300,
        semantic_prediction={
            "available": True,
            "should_enter": True,
            "trace_quality_state": "clean",
            "timing": {"probability": 0.78, "threshold": 0.55},
            "entry_quality": {"probability": 0.70, "threshold": 0.55},
        },
        runtime_snapshot_row={
            "missing_feature_count": 0,
            "data_completeness_ratio": 1.0,
            "used_fallback_count": 0,
            "compatibility_mode": "",
        },
    )

    assert decision["fallback_applied"] is False
    assert decision["threshold_applied"] is True
    assert decision["threshold_state"] == "applied"
    assert decision["threshold_inactive_reason"] == ""
    assert decision["threshold_adjustment_points"] < 0
    assert decision["threshold_after"] < 300


def test_entry_rollout_guard_falls_back_on_bad_quality(monkeypatch):
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "threshold_only", raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_KILL_SWITCH", False, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_REQUIRE_CLEAN_TRACE", True, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_MAX_MISSING_FEATURES", 1, raising=False)

    decision = SemanticPromotionGuard.evaluate_entry_rollout(
        symbol="BTCUSD",
        baseline_action="BUY",
        entry_stage="aggressive",
        current_threshold=300,
        semantic_prediction={
            "available": True,
            "should_enter": True,
            "trace_quality_state": "degraded",
            "timing": {"probability": 0.78, "threshold": 0.55},
            "entry_quality": {"probability": 0.70, "threshold": 0.55},
        },
        runtime_snapshot_row={
            "missing_feature_count": 3,
            "data_completeness_ratio": 0.91,
            "used_fallback_count": 0,
            "compatibility_mode": "",
        },
    )

    assert decision["fallback_applied"] is True
    assert decision["fallback_reason"] == "missing_feature_count_high"
    assert decision["threshold_applied"] is False
    assert decision["threshold_state"] == "fallback_blocked"
    assert decision["threshold_inactive_reason"] == "missing_feature_count_high"
    assert decision["threshold_after"] == 300


def test_entry_rollout_guard_respects_symbol_and_stage_allowlists(monkeypatch):
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "threshold_only", raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_KILL_SWITCH", False, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_SYMBOL_ALLOWLIST", ("BTCUSD",), raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_ENTRY_STAGE_ALLOWLIST", ("aggressive",), raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_MIN_TIMING_PROB", 0.58, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_MIN_ENTRY_QUALITY_PROB", 0.58, raising=False)

    symbol_blocked = SemanticPromotionGuard.evaluate_entry_rollout(
        symbol="XAUUSD",
        baseline_action="BUY",
        entry_stage="aggressive",
        current_threshold=300,
        semantic_prediction={
            "available": True,
            "should_enter": True,
            "trace_quality_state": "clean",
            "timing": {"probability": 0.80, "threshold": 0.55},
            "entry_quality": {"probability": 0.72, "threshold": 0.55},
        },
        runtime_snapshot_row={"missing_feature_count": 0, "data_completeness_ratio": 1.0},
    )
    stage_blocked = SemanticPromotionGuard.evaluate_entry_rollout(
        symbol="BTCUSD",
        baseline_action="BUY",
        entry_stage="balanced",
        current_threshold=300,
        semantic_prediction={
            "available": True,
            "should_enter": True,
            "trace_quality_state": "clean",
            "timing": {"probability": 0.80, "threshold": 0.55},
            "entry_quality": {"probability": 0.72, "threshold": 0.55},
        },
        runtime_snapshot_row={"missing_feature_count": 0, "data_completeness_ratio": 1.0},
    )

    assert symbol_blocked["fallback_reason"] == "symbol_not_in_allowlist"
    assert symbol_blocked["symbol_allowed"] is False
    assert stage_blocked["fallback_reason"] == "entry_stage_not_in_allowlist"
    assert stage_blocked["entry_stage_allowed"] is False


def test_entry_rollout_guard_requires_minimum_probabilities(monkeypatch):
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "threshold_only", raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_KILL_SWITCH", False, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_SYMBOL_ALLOWLIST", tuple(), raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_ENTRY_STAGE_ALLOWLIST", tuple(), raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_MIN_TIMING_PROB", 0.62, raising=False)
    monkeypatch.setattr(Config, "SEMANTIC_LIVE_MIN_ENTRY_QUALITY_PROB", 0.64, raising=False)

    decision = SemanticPromotionGuard.evaluate_entry_rollout(
        symbol="BTCUSD",
        baseline_action="BUY",
        entry_stage="aggressive",
        current_threshold=300,
        semantic_prediction={
            "available": True,
            "should_enter": True,
            "trace_quality_state": "clean",
            "timing": {"probability": 0.61, "threshold": 0.55},
            "entry_quality": {"probability": 0.63, "threshold": 0.55},
        },
        runtime_snapshot_row={"missing_feature_count": 0, "data_completeness_ratio": 1.0},
    )

    assert decision["fallback_applied"] is True
    assert decision["fallback_reason"] == "timing_probability_too_low"
    assert decision["threshold_applied"] is False
