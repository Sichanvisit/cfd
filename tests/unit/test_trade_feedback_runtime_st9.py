from zoneinfo import ZoneInfo

from backend.services.improvement_detector_feedback_runtime import (
    build_detector_feedback_entry,
    build_detector_feedback_scope_key,
)
from backend.services.trade_feedback_runtime import build_manual_trade_proposal_snapshot
from tests.unit.test_trade_feedback_runtime import _sample_closed_frame


KST = ZoneInfo("Asia/Seoul")


def _st9_issue_ref() -> dict[str, object]:
    summary_ko = "BTCUSD upper_reject_mixed_confirm 맥락 충돌 관찰"
    return {
        "feedback_ref": "D9",
        "feedback_key": "detfb_st9_context",
        "feedback_scope_key": build_detector_feedback_scope_key(
            detector_key="scene_aware_detector",
            symbol="BTCUSD",
            summary_ko=summary_ko,
        ),
        "detector_key": "scene_aware_detector",
        "symbol": "BTCUSD",
        "summary_ko": summary_ko,
        "registry_key": "misread:context_conflict_state",
        "registry_label_ko": "맥락 충돌",
        "registry_binding_mode": "exact",
        "evidence_registry_keys": [
            "misread:context_conflict_state",
            "misread:htf_alignment_state",
            "misread:previous_box_break_state",
            "misread:late_chase_risk_state",
        ],
        "target_registry_keys": [
            "state25_weight:reversal_risk_weight",
        ],
        "hindsight_status": "confirmed_misread",
        "hindsight_status_ko": "사후 확정 오판",
        "misread_confidence": 0.88,
        "context_bundle_summary_ko": "HTF 전체 상승 정렬 | 직전 박스 상단 돌파 유지 | 늦은 추격 위험 높음",
        "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        "context_conflict_label_ko": "직전 박스와 상위 추세 모두 역행 (강함)",
        "context_conflict_intensity": "HIGH",
        "late_chase_risk_state": "HIGH",
        "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
        "htf_alignment_state": "AGAINST_HTF",
        "htf_alignment_detail": "AGAINST_HTF_UP",
        "htf_against_severity": "HIGH",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
    }


def _st9_feedback_entries(issue_ref: dict[str, object]) -> list[dict[str, object]]:
    timestamps = [
        "2026-04-10T09:10:00+09:00",
        "2026-04-10T09:20:00+09:00",
        "2026-04-11T10:10:00+09:00",
        "2026-04-12T11:10:00+09:00",
        "2026-04-12T11:20:00+09:00",
    ]
    verdicts = ["confirmed", "missed", "confirmed", "missed", "confirmed"]
    return [
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict=verdict,
            user_id=1001,
            username="ops",
            now_ts=ts,
        )
        for verdict, ts in zip(verdicts, timestamps, strict=True)
    ]


def test_st9_feedback_rows_carry_context_and_hindsight_summary() -> None:
    issue_ref = _st9_issue_ref()
    payload = build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T13:10:00+09:00",
        detector_feedback_entries=_st9_feedback_entries(issue_ref),
        detector_latest_issue_refs=[issue_ref],
    )

    row = payload["feedback_promotion_rows"][0]
    assert row["context_bundle_summary_ko"] == issue_ref["context_bundle_summary_ko"]
    assert "사후: 사후 확정 오판" in row["proposal_context_summary_ko"]
    assert row["context_conflict_state"] == "AGAINST_PREV_BOX_AND_HTF"


def test_st9_proposal_snapshot_surfaces_context_and_hindsight_in_report() -> None:
    issue_ref = _st9_issue_ref()
    payload = build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T13:20:00+09:00",
        detector_feedback_entries=_st9_feedback_entries(issue_ref),
        detector_latest_issue_refs=[issue_ref],
    )

    top_issue = payload["surfaced_problem_patterns"][0]
    assert "HTF 전체 상승 정렬" in top_issue["feedback_priority_context_summary_ko"]
    assert top_issue["feedback_priority_hindsight_status_ko"] == "사후 확정 오판"
    assert "HTF 전체 상승 정렬" in payload["proposal_envelope"]["why_now_ko"]
    assert payload["proposal_envelope"]["evidence_snapshot"]["feedback_context_summaries"]
    assert payload["proposal_envelope"]["evidence_snapshot"]["feedback_hindsight_labels"] == ["사후 확정 오판"]
    assert any("맥락/사후:" in line for line in payload["report_lines_ko"])
