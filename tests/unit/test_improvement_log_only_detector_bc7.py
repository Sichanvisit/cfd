from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

import backend.services.improvement_log_only_detector as detector_module
from backend.services.state25_context_bridge import build_state25_candidate_context_bridge_v1


KST = ZoneInfo("Asia/Seoul")


def _runtime_row_with_threshold_bridge() -> dict[str, object]:
    row: dict[str, object] = {
        "symbol": "NAS100",
        "entry_stage": "balanced",
        "consumer_check_side": "SELL",
        "consumer_check_reason": "upper_break_fail_confirm",
        "signal_timeframe": "15M",
        "trend_15m_direction": "DOWNTREND",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "UPTREND",
        "trend_1h_strength_score": 2.2,
        "trend_4h_strength_score": 1.9,
        "trend_1d_strength_score": 2.0,
        "trend_1h_age_seconds": 90,
        "trend_4h_age_seconds": 120,
        "trend_1d_age_seconds": 180,
        "htf_alignment_state": "AGAINST_HTF",
        "htf_alignment_detail": "AGAINST_HTF_UP",
        "htf_against_severity": "HIGH",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_lifecycle": "RETESTED",
        "previous_box_confidence": "HIGH",
        "previous_box_is_consolidation": True,
        "previous_box_age_seconds": 60,
        "context_bundle_summary_ko": "HTF 전체 상승 정렬 | 직전 박스 상단 돌파 유지 | 늦은 추격 위험 높음",
        "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        "context_conflict_flags": ["AGAINST_HTF", "AGAINST_PREV_BOX"],
        "context_conflict_intensity": "HIGH",
        "context_conflict_score": 0.88,
        "context_conflict_label_ko": "직전 박스와 상위 추세 모두 역행",
        "late_chase_risk_state": "HIGH",
        "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
        "late_chase_confidence": 0.81,
        "late_chase_trigger_count": 3,
        "effective_entry_threshold": 40,
        "final_score": 42,
    }
    row["state25_candidate_context_bridge_v1"] = build_state25_candidate_context_bridge_v1(
        row
    )
    return row


def test_bc7_detector_surfaces_state25_context_bridge_threshold_review(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "_build_scene_aware_detector_rows_v2",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        detector_module,
        "_build_candle_weight_detector_rows",
        lambda *args, **kwargs: ([], {}),
    )
    monkeypatch.setattr(
        detector_module,
        "_build_reverse_pattern_detector_rows",
        lambda *args, **kwargs: [],
    )

    payload = detector_module.build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        runtime_status_detail_payload={"latest_signal_by_symbol": {"NAS100": _runtime_row_with_threshold_bridge()}},
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-14T13:10:00+09:00",
    )

    surfaced = payload["candle_weight_detector"]["surfaced_rows"]
    row = next(
        raw for raw in surfaced if "threshold review" in str(raw.get("summary_ko", "")).lower()
    )
    preview = row["threshold_patch_preview"]

    assert preview["bridge_source_lane"] == "STATE25_CONTEXT_BRIDGE_THRESHOLD_LOG_ONLY"
    assert preview["bridge_threshold_requested_points"] > 0.0
    assert row["registry_binding_ready"] is True
    issue_ref = next(
        raw
        for raw in payload["feedback_issue_refs"]
        if "threshold review" in str(raw.get("summary_ko", "")).lower()
    )
    assert issue_ref["threshold_patch_preview"]["bridge_source_lane"] == "STATE25_CONTEXT_BRIDGE_THRESHOLD_LOG_ONLY"
