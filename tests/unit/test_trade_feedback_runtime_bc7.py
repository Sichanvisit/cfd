from __future__ import annotations

from zoneinfo import ZoneInfo

from backend.services.state25_context_bridge import build_state25_candidate_context_bridge_v1
from backend.services.state25_threshold_patch_review import (
    build_state25_threshold_patch_review_candidate_from_context_bridge_v1,
)
from backend.services.trade_feedback_runtime import build_manual_trade_proposal_snapshot
from tests.unit.test_trade_feedback_runtime import _sample_closed_frame


KST = ZoneInfo("Asia/Seoul")


def _bc7_issue_ref() -> dict[str, object]:
    runtime_row = {
        "symbol": "NAS100",
        "entry_stage": "balanced",
        "consumer_check_side": "SELL",
        "signal_timeframe": "15M",
        "context_bundle_summary_ko": "HTF 전체 상승 정렬 | 직전 박스 상단 돌파 유지 | 늦은 추격 위험 높음",
        "context_conflict_label_ko": "직전 박스와 상위 추세 모두 역행",
        "htf_alignment_state": "AGAINST_HTF",
        "htf_alignment_detail": "AGAINST_HTF_UP",
        "htf_against_severity": "HIGH",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_lifecycle": "RETESTED",
        "previous_box_confidence": "HIGH",
        "previous_box_is_consolidation": True,
        "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        "context_conflict_intensity": "HIGH",
        "late_chase_risk_state": "HIGH",
        "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
        "trend_1h_age_seconds": 120,
        "trend_4h_age_seconds": 120,
        "trend_1d_age_seconds": 120,
        "previous_box_age_seconds": 60,
        "effective_entry_threshold": 40,
        "final_score": 42,
    }
    runtime_row["state25_candidate_context_bridge_v1"] = build_state25_candidate_context_bridge_v1(
        runtime_row
    )
    preview = build_state25_threshold_patch_review_candidate_from_context_bridge_v1(runtime_row)
    return {
        "feedback_ref": "D7",
        "detector_key": "candle_weight_detector",
        "detector_label_ko": "candle/weight detector",
        "symbol": "NAS100",
        "summary_ko": "NAS100 state25 context bridge threshold review 후보",
        "context_bundle_summary_ko": runtime_row["context_bundle_summary_ko"],
        "context_conflict_label_ko": runtime_row["context_conflict_label_ko"],
        "threshold_patch_preview": preview,
    }


def test_bc7_proposal_snapshot_surfaces_state25_context_bridge_threshold_review_candidates() -> None:
    payload = build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-14T13:20:00+09:00",
        detector_latest_issue_refs=[_bc7_issue_ref()],
    )

    assert payload["state25_context_bridge_threshold_review_count"] == 1
    candidate = payload["state25_context_bridge_threshold_review_candidates"][0]
    assert candidate["bridge_source_lane"] == "STATE25_CONTEXT_BRIDGE_THRESHOLD_LOG_ONLY"
    assert candidate["bridge_threshold_requested_points"] > 0.0
    assert any(
        "state25 context bridge threshold review" in str(line).lower()
        for line in payload["report_lines_ko"]
    )
    assert (
        payload["proposal_envelope"]["evidence_snapshot"]["state25_context_bridge_threshold_review_count"]
        == 1
    )


def test_bc7_proposal_snapshot_falls_back_to_detector_snapshot_for_threshold_preview() -> None:
    full_issue = _bc7_issue_ref()
    slim_issue = {
        key: value
        for key, value in full_issue.items()
        if key not in {"threshold_patch_preview"}
    }
    detector_snapshot_payload = {
        "candle_weight_detector": {
            "surfaced_rows": [],
            "cooldown_suppressed_rows": [full_issue],
        }
    }

    payload = build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-14T13:27:00+09:00",
        detector_latest_issue_refs=[slim_issue],
        detector_snapshot_payload=detector_snapshot_payload,
    )

    assert payload["state25_context_bridge_threshold_review_count"] == 1
    candidate = payload["state25_context_bridge_threshold_review_candidates"][0]
    assert candidate["source_feedback_ref"] == "D7"
    assert candidate["bridge_threshold_requested_points"] > 0.0
