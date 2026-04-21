from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.services.context_state_builder import build_context_state_v12

KST = ZoneInfo("Asia/Seoul")


def test_context_state_builder_marks_against_prev_box_and_htf_primary():
    payload = build_context_state_v12(
        symbol="NAS100",
        consumer_check_side="SELL",
        htf_state={
            "trend_15m_direction": "DOWNTREND",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "UPTREND",
            "trend_1d_direction": "UPTREND",
            "trend_1h_strength_score": 2.4,
            "trend_4h_strength_score": 2.1,
            "trend_1d_strength_score": 2.2,
            "htf_context_version": "htf_context_v1",
        },
        previous_box_state={
            "previous_box_relation": "ABOVE",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_confidence": "HIGH",
            "previous_box_context_version": "previous_box_context_v1",
        },
        built_at=datetime(2026, 4, 13, 23, 10, tzinfo=KST),
    )

    assert payload["context_conflict_state"] == "AGAINST_PREV_BOX_AND_HTF"
    assert "AGAINST_HTF" in payload["context_conflict_flags"]
    assert "AGAINST_PREV_BOX" in payload["context_conflict_flags"]
    assert payload["context_conflict_intensity"] == "HIGH"
    assert payload["context_conflict_score"] > 0.8


def test_context_state_builder_marks_late_chase_risk_for_buy_after_breakout_run():
    payload = build_context_state_v12(
        symbol="NAS100",
        consumer_check_side="BUY",
        htf_state={
            "trend_15m_direction": "UPTREND",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "UPTREND",
            "trend_1d_direction": "UPTREND",
            "trend_1h_strength_score": 2.6,
        },
        previous_box_state={
            "previous_box_relation": "ABOVE",
            "previous_box_break_state": "BREAKOUT_HELD",
            "distance_from_previous_box_high_pct": 2.4,
            "previous_box_confidence": "MEDIUM",
        },
        proxy_state={
            "same_color_run_current": 6,
            "pullback_ratio": 0.2,
        },
        built_at=datetime(2026, 4, 13, 23, 10, tzinfo=KST),
    )

    assert payload["late_chase_risk_state"] == "HIGH"
    assert payload["late_chase_trigger_count"] >= 2
    assert payload["late_chase_confidence"] > 0.7
    assert "LATE_CHASE_RISK" in payload["context_conflict_flags"]
    assert payload["context_conflict_state"] == "LATE_CHASE_RISK"


def test_context_state_builder_marks_context_mixed_when_side_is_none_and_htf_is_mixed():
    payload = build_context_state_v12(
        symbol="BTCUSD",
        consumer_check_side=None,
        htf_state={
            "htf_alignment_state": "MIXED_HTF",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "MIXED",
            "trend_1d_direction": "UPTREND",
        },
        previous_box_state={
            "previous_box_confidence": "LOW",
            "previous_box_lifecycle": "INVALIDATED",
        },
        built_at=datetime(2026, 4, 13, 23, 10, tzinfo=KST),
    )

    assert payload["context_conflict_state"] == "CONTEXT_MIXED"
    assert payload["context_conflict_flags"] == ["CONTEXT_MIXED"]


def test_context_state_builder_infers_share_band_and_label():
    payload = build_context_state_v12(
        symbol="XAUUSD",
        consumer_check_side="WAIT",
        share_state={
            "cluster_share_symbol": 0.91,
        },
        built_at=datetime(2026, 4, 13, 23, 10, tzinfo=KST),
    )

    assert payload["cluster_share_symbol_band"] == "DOMINANT"
    assert payload["share_context_label_ko"] == "내부 지배 장면"
    assert payload["context_state_version"] == "context_state_v1_2"
