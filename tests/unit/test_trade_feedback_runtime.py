from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from backend.services.improvement_detector_feedback_runtime import build_detector_feedback_entry
from backend.services.trade_feedback_runtime import (
    build_manual_trade_proposal_snapshot,
    build_pnl_lesson_comment_lines,
)


KST = ZoneInfo("Asia/Seoul")


def _sample_closed_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "trade_link_key": "t1",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 09:10:00",
                "profit": -3.0,
                "gross_pnl": -2.4,
                "cost_total": 0.6,
                "net_pnl_after_cost": -3.0,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.8,
            },
            {
                "trade_link_key": "t2",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 09:30:00",
                "profit": -2.0,
                "gross_pnl": -1.4,
                "cost_total": 0.6,
                "net_pnl_after_cost": -2.0,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.7,
            },
            {
                "trade_link_key": "t3",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 10:00:00",
                "profit": -1.5,
                "gross_pnl": -0.9,
                "cost_total": 0.6,
                "net_pnl_after_cost": -1.5,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.9,
            },
            {
                "trade_link_key": "t4",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 11:00:00",
                "profit": 0.5,
                "gross_pnl": 1.1,
                "cost_total": 0.6,
                "net_pnl_after_cost": 0.5,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "runner",
                "peak_profit_at_exit": 1.8,
            },
            {
                "trade_link_key": "t5",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 11:30:00",
                "profit": -1.0,
                "gross_pnl": -0.4,
                "cost_total": 0.6,
                "net_pnl_after_cost": -1.0,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.6,
            },
            {
                "trade_link_key": "t6",
                "symbol": "XAUUSD",
                "close_time": "2026-04-11 14:00:00",
                "profit": 4.0,
                "gross_pnl": 4.5,
                "cost_total": 0.5,
                "net_pnl_after_cost": 4.0,
                "lot": 0.02,
                "entry_reason": "reclaim",
                "exit_reason": "target",
                "peak_profit_at_exit": 5.0,
            },
        ]
    )


def test_build_manual_trade_proposal_snapshot_surfaces_problem_patterns() -> None:
    payload = build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-12T02:10:00+09:00",
    )

    assert payload["analyzed_trade_count"] == 6
    assert payload["level1_count"] >= 1
    assert payload["proposal_envelope"]["proposal_type"] == "MANUAL_TRADE_PATTERN_REVIEW"
    assert payload["proposal_envelope"]["readiness_status"] == "READY_FOR_REVIEW"
    assert payload["surfaced_problem_patterns"][0]["entry_reason"] == "upper_reject_mixed_confirm"
    assert len(payload["report_lines_ko"]) >= 4


def test_build_manual_trade_proposal_snapshot_promotes_feedback_aware_candidates() -> None:
    issue_ref = {
        "feedback_ref": "D1",
        "feedback_key": "detfb_feedback_aware",
        "detector_key": "candle_weight_detector",
        "symbol": "BTCUSD",
        "summary_ko": "BTCUSD upper_reject_mixed_confirm candle overweight",
    }
    feedback_entries = [
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="confirmed",
            user_id=1001,
            username="ops",
            now_ts="2026-04-12T02:10:00+09:00",
        ),
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="missed",
            user_id=1001,
            username="ops",
            now_ts="2026-04-12T02:20:00+09:00",
        ),
    ]

    payload = build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-12T02:30:00+09:00",
        detector_feedback_entries=feedback_entries,
        detector_latest_issue_refs=[issue_ref],
    )

    assert payload["feedback_promotion_count"] == 1
    assert payload["proposal_envelope"]["readiness_status"] == "READY_FOR_REVIEW"
    assert any("feedback-aware" in line for line in payload["report_lines_ko"])
    assert payload["feedback_promotion_rows"][0]["narrowing_decision"] == "PROMOTE"
    assert payload["surfaced_problem_patterns"][0]["feedback_priority_score"] >= 1


def test_build_manual_trade_proposal_snapshot_emits_time_observations_in_korean() -> None:
    frame = pd.DataFrame(
        [
            {
                "trade_link_key": "n1",
                "symbol": "NAS100",
                "close_time": "2026-04-11 18:10:00",
                "profit": -3.0,
                "gross_pnl": -2.0,
                "cost_total": 1.0,
                "net_pnl_after_cost": -3.0,
                "lot": 0.01,
                "entry_reason": "night_reversal",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.4,
            },
            {
                "trade_link_key": "n2",
                "symbol": "NAS100",
                "close_time": "2026-04-11 18:20:00",
                "profit": -2.0,
                "gross_pnl": -1.0,
                "cost_total": 1.0,
                "net_pnl_after_cost": -2.0,
                "lot": 0.01,
                "entry_reason": "night_reversal",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.3,
            },
            {
                "trade_link_key": "n3",
                "symbol": "NAS100",
                "close_time": "2026-04-11 18:40:00",
                "profit": -1.0,
                "gross_pnl": 0.0,
                "cost_total": 1.0,
                "net_pnl_after_cost": -1.0,
                "lot": 0.01,
                "entry_reason": "night_reversal",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.2,
            },
            {
                "trade_link_key": "d1",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 09:10:00",
                "profit": 2.0,
                "gross_pnl": 2.5,
                "cost_total": 0.5,
                "net_pnl_after_cost": 2.0,
                "lot": 0.01,
                "entry_reason": "trend_follow",
                "exit_reason": "target",
                "peak_profit_at_exit": 2.8,
            },
            {
                "trade_link_key": "d2",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 09:30:00",
                "profit": 2.5,
                "gross_pnl": 3.0,
                "cost_total": 0.5,
                "net_pnl_after_cost": 2.5,
                "lot": 0.01,
                "entry_reason": "trend_follow",
                "exit_reason": "target",
                "peak_profit_at_exit": 3.3,
            },
            {
                "trade_link_key": "d3",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 10:00:00",
                "profit": 3.0,
                "gross_pnl": 3.6,
                "cost_total": 0.6,
                "net_pnl_after_cost": 3.0,
                "lot": 0.01,
                "entry_reason": "trend_follow",
                "exit_reason": "target",
                "peak_profit_at_exit": 3.8,
            },
        ]
    )

    payload = build_manual_trade_proposal_snapshot(
        frame,
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-12T02:10:00+09:00",
    )

    assert "시간대 관찰:" in payload["report_lines_ko"]
    assert any("승률" in line and "전체 대비" in line for line in payload["report_lines_ko"])


def test_build_pnl_lesson_comment_lines_emits_lessons_only_when_needed() -> None:
    lines = build_pnl_lesson_comment_lines(
        _sample_closed_frame(),
        start=datetime(2026, 4, 11, 0, 0, tzinfo=KST),
        end=datetime(2026, 4, 12, 0, 0, tzinfo=KST),
        timezone=KST,
    )

    assert len(lines) >= 2
    assert any("MFE" in line for line in lines)
