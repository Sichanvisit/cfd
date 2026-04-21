from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

import backend.services.improvement_log_only_detector as detector_module


KST = ZoneInfo("Asia/Seoul")


def _runtime_context_row(*, side: str = "SELL", conflict_state: str = "AGAINST_PREV_BOX_AND_HTF") -> dict[str, object]:
    return {
        "symbol": "NAS100",
        "consumer_check_side": side,
        "consumer_check_reason": "upper_break_fail_confirm",
        "position_energy_surface_v1": {
            "energy": {
                "lower_position_force": 0.02,
                "upper_position_force": 0.46,
                "middle_neutrality": 0.00,
            }
        },
        "position_snapshot_v2": {
            "energy": {
                "metadata": {
                    "position_dominance": "UPPER",
                }
            }
        },
        "box_state": "UPPER",
        "micro_upper_wick_ratio_20": 0.41,
        "micro_lower_wick_ratio_20": 0.08,
        "micro_doji_ratio_20": 0.09,
        "micro_body_size_pct_20": 0.18,
        "micro_same_color_run_current": 6,
        "micro_same_color_run_max_20": 7,
        "micro_bull_ratio_20": 0.18,
        "micro_bear_ratio_20": 0.76,
        "trend_15m_direction": "DOWNTREND" if side == "SELL" else "UPTREND",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "UPTREND",
        "trend_1h_strength_score": 2.4,
        "trend_4h_strength_score": 2.1,
        "trend_1d_strength_score": 2.2,
        "htf_alignment_state": "AGAINST_HTF" if side == "SELL" else "WITH_HTF",
        "htf_alignment_detail": "AGAINST_HTF_UP" if side == "SELL" else "ALL_ALIGNED_UP",
        "htf_against_severity": "HIGH" if side == "SELL" else "",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_confidence": "HIGH",
        "previous_box_lifecycle": "RETESTED",
        "distance_from_previous_box_high_pct": 2.2,
        "context_conflict_state": conflict_state,
        "context_conflict_flags": (
            ["AGAINST_HTF", "AGAINST_PREV_BOX", "LATE_CHASE_RISK"]
            if conflict_state == "AGAINST_PREV_BOX_AND_HTF"
            else ["LATE_CHASE_RISK"]
        ),
        "context_conflict_intensity": "HIGH",
        "context_conflict_score": 0.91,
        "context_conflict_label_ko": "직전 박스와 상위 추세 모두 역행 (강함)"
        if conflict_state == "AGAINST_PREV_BOX_AND_HTF"
        else "늦은 추격 위험 (강함)",
        "late_chase_risk_state": "HIGH",
        "late_chase_reason": "MULTI_BAR_RUN_AFTER_BREAK",
        "late_chase_confidence": 0.82,
        "late_chase_trigger_count": 3,
        "cluster_share_symbol": 0.88,
        "cluster_share_symbol_band": "DOMINANT",
        "share_context_label_ko": "내부 지배 장면",
        "context_state_version": "context_state_v1_2",
        "htf_context_version": "htf_context_v1",
        "previous_box_context_version": "previous_box_context_v1",
        "conflict_context_version": "conflict_context_v1_2",
    }


def _scene_source_row() -> dict[str, object]:
    return {
        "detector_key": detector_module.DETECTOR_SCENE_AWARE,
        "detector_label_ko": "scene-aware detector",
        "severity": 1,
        "proposal_stage": "OBSERVE",
        "readiness_status": "READY_FOR_REVIEW",
        "symbol": "NAS100",
        "repeat_count": 6,
        "summary_ko": "trend_exhaustion mismatch 관찰",
        "why_now_ko": "trend_exhaustion 장면이 반복됩니다.",
        "recommended_action_ko": "review topic에서 먼저 확인합니다.",
        "evidence_lines_ko": ["- runtime_unresolved_share: 0.80"],
        "transition_lines_ko": [],
    }


def _candle_source_row() -> dict[str, object]:
    return {
        "detector_key": detector_module.DETECTOR_CANDLE_WEIGHT,
        "detector_label_ko": "candle/weight detector",
        "severity": 1,
        "proposal_stage": "OBSERVE",
        "readiness_status": "READY_FOR_REVIEW",
        "symbol": "NAS100",
        "dominant_symbol": "NAS100",
        "entry_reason": "upper_reject_mixed_confirm",
        "entry_reason_ko": "상단 거부 혼합 확인",
        "trade_count": 7,
        "win_rate": 0.28,
        "net_pnl": -14.0,
        "repeat_count": 7,
        "summary_ko": "상단 거부 혼합 확인 패턴 가중치 점검 제안",
        "why_now_ko": "같은 패턴에서 반복 손실이 이어집니다.",
        "recommended_action_ko": "weight preview를 log-only로 확인합니다.",
        "evidence_lines_ko": ["- 표본: 7건"],
        "weight_patch_preview": {"state25_teacher_weight_overrides": {"upper_wick_weight": 0.75}},
    }


def test_st5_scene_detector_bridge_surfaces_context_bundle(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "_build_scene_aware_detector_rows",
        lambda *args, **kwargs: [_scene_source_row()],
    )
    monkeypatch.setattr(
        detector_module,
        "_build_candle_weight_detector_rows_v2",
        lambda *args, **kwargs: ([], {}),
    )
    monkeypatch.setattr(
        detector_module,
        "_build_reverse_pattern_detector_rows",
        lambda *args, **kwargs: [],
    )

    payload = detector_module.build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        runtime_status_detail_payload={"latest_signal_by_symbol": {"NAS100": _runtime_context_row()}},
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T23:40:00+09:00",
    )

    row = payload["scene_aware_detector"]["surfaced_rows"][0]
    evidence_lines = list(row.get("evidence_lines_ko") or [])

    assert row["context_conflict_state"] == "AGAINST_PREV_BOX_AND_HTF"
    assert row["htf_alignment_state"] == "AGAINST_HTF"
    assert row["previous_box_break_state"] == "BREAKOUT_HELD"
    assert row["late_chase_risk_state"] == "HIGH"
    assert row["context_bundle_summary_ko"]
    assert any("HTF:" in line for line in evidence_lines)
    assert any("직전 박스:" in line for line in evidence_lines)
    assert any("맥락 충돌:" in line for line in evidence_lines)
    assert any("늦은 추격:" in line for line in evidence_lines)
    assert row["registry_key"] == "misread:context_conflict_state"
    assert "misread:htf_alignment_state" in row["evidence_registry_keys"]
    assert "misread:previous_box_break_state" in row["evidence_registry_keys"]
    assert "misread:context_conflict_state" in row["evidence_registry_keys"]
    assert "misread:late_chase_risk_state" in row["evidence_registry_keys"]
    assert row["registry_binding_ready"] is True


def test_st5_candle_detector_bridge_surfaces_late_chase_context(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "_build_scene_aware_detector_rows_v2",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        detector_module,
        "_build_candle_weight_detector_rows",
        lambda *args, **kwargs: ([_candle_source_row()], {}),
    )
    monkeypatch.setattr(
        detector_module,
        "_build_reverse_pattern_detector_rows",
        lambda *args, **kwargs: [],
    )

    runtime_row = _runtime_context_row(side="BUY", conflict_state="LATE_CHASE_RISK")
    payload = detector_module.build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        runtime_status_detail_payload={"latest_signal_by_symbol": {"NAS100": runtime_row}},
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T23:50:00+09:00",
    )

    row = payload["candle_weight_detector"]["surfaced_rows"][0]
    evidence_lines = list(row.get("evidence_lines_ko") or [])

    assert row["context_conflict_state"] == "LATE_CHASE_RISK"
    assert row["late_chase_risk_state"] == "HIGH"
    assert row["late_chase_reason"] == "MULTI_BAR_RUN_AFTER_BREAK"
    assert row["late_chase_confidence"] > 0.7
    assert row["late_chase_trigger_count"] >= 1
    assert any("늦은 추격:" in line for line in evidence_lines)
    assert "맥락상" in str(row.get("why_now_ko"))
    assert row["registry_key"] in {
        "misread:composite_structure_mismatch",
        "misread:context_conflict_state",
        "misread:late_chase_risk_state",
    }
    assert row["registry_binding_ready"] is True
