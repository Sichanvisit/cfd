from zoneinfo import ZoneInfo

from backend.services.improvement_detector_feedback_runtime import (
    build_detector_feedback_entry,
    build_detector_feedback_scope_key,
)
from backend.services.trade_feedback_runtime import build_manual_trade_proposal_snapshot
from tests.unit.test_trade_feedback_runtime import _sample_closed_frame


KST = ZoneInfo("Asia/Seoul")


def test_build_manual_trade_proposal_snapshot_fast_promotes_confirmed_hindsight_scope() -> None:
    summary_ko = "BTCUSD 상하단 방향 오판 가능성 관찰"
    issue_ref = {
        "feedback_ref": "D1",
        "feedback_key": "detfb_fast_promotion",
        "feedback_scope_key": build_detector_feedback_scope_key(
            detector_key="scene_aware_detector",
            symbol="BTCUSD",
            summary_ko=summary_ko,
        ),
        "detector_key": "scene_aware_detector",
        "symbol": "BTCUSD",
        "summary_ko": summary_ko,
        "hindsight_status": "confirmed_misread",
        "hindsight_status_ko": "사후 확정 오판",
        "misread_confidence": 0.82,
    }
    feedback_entries = [
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="confirmed",
            user_id=1001,
            username="ops",
            now_ts="2026-04-10T09:10:00+09:00",
        ),
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="missed",
            user_id=1001,
            username="ops",
            now_ts="2026-04-10T09:20:00+09:00",
        ),
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="confirmed",
            user_id=1001,
            username="ops",
            now_ts="2026-04-11T10:10:00+09:00",
        ),
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="missed",
            user_id=1001,
            username="ops",
            now_ts="2026-04-12T11:10:00+09:00",
        ),
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="confirmed",
            user_id=1001,
            username="ops",
            now_ts="2026-04-12T11:20:00+09:00",
        ),
    ]

    payload = build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T12:30:00+09:00",
        detector_feedback_entries=feedback_entries,
        detector_latest_issue_refs=[issue_ref],
    )

    assert payload["feedback_promotion_count"] == 1
    assert payload["fast_promotion_count"] == 1
    assert payload["proposal_envelope"]["readiness_status"] == "READY_FOR_REVIEW"
    assert payload["feedback_promotion_rows"][0]["fast_promotion_eligible"] is True
    assert payload["feedback_promotion_rows"][0]["feedback_trade_day_count"] == 3
    assert payload["feedback_promotion_rows"][0]["hindsight_status"] == "confirmed_misread"
    assert "빠른 승격" in payload["feedback_promotion_rows"][0]["report_line_ko"]
    assert any("빠른 승격 근거:" in line for line in payload["report_lines_ko"])
