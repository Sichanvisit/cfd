from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

import backend.services.improvement_log_only_detector as detector_module


KST = ZoneInfo("Asia/Seoul")


def _scene_bound_row() -> dict[str, object]:
    return {
        "detector_key": detector_module.DETECTOR_SCENE_AWARE,
        "detector_label_ko": "scene-aware detector",
        "severity": 1,
        "proposal_stage": "OBSERVE",
        "readiness_status": "READY_FOR_REVIEW",
        "symbol": "BTCUSD",
        "repeat_count": 4,
        "summary_ko": "BTCUSD 상하단 방향 오판 가능성 관찰",
        "why_now_ko": "BTCUSD에서 상단 과열 구간에서 구조 엇갈림 가능성이 보입니다.",
        "recommended_action_ko": "feedback으로 먼저 확인합니다.",
        "evidence_lines_ko": [
            "- 위/아래 힘: 하단 우세",
            "- 박스 위치: 하단 영역",
            "- 캔들 구조: 아랫꼬리 우세",
            "- 최근 3봉 흐름: 약상승",
        ],
        "transition_lines_ko": [],
        "consumer_check_side": "BUY",
        "consumer_check_reason": "pullback_continuation",
        "position_dominance": "LOWER",
        "structure_alignment_mode": "REVERSION",
        "structure_alignment": "MATCH",
        "box_relative_position": 0.18,
        "box_zone": "LOWER",
        "range_too_narrow": False,
        "upper_wick_ratio": 0.08,
        "lower_wick_ratio": 0.42,
        "doji_ratio": 0.05,
        "recent_3bar_direction": "WEAK_UP",
    }


def _candle_bound_row() -> dict[str, object]:
    return {
        "detector_key": detector_module.DETECTOR_CANDLE_WEIGHT,
        "detector_label_ko": "candle/weight detector",
        "severity": 1,
        "proposal_stage": "OBSERVE",
        "readiness_status": "READY_FOR_REVIEW",
        "symbol": "XAUUSD",
        "dominant_symbol": "XAUUSD",
        "entry_reason": "upper_reject_mixed_confirm",
        "entry_reason_ko": "상단 거부 혼합 확인",
        "trade_count": 6,
        "win_rate": 0.25,
        "net_pnl": -18.5,
        "repeat_count": 6,
        "summary_ko": "XAUUSD 구조 복합 불일치 관찰",
        "why_now_ko": "박스 상단에서 롱이 반복되어 방향 해석 불일치가 보입니다.",
        "recommended_action_ko": "log-only preview로 확인합니다.",
        "evidence_lines_ko": [
            "- 구조 복합 불일치: 박스상단 82% + 윗꼬리 과다 + 3봉 하락",
        ],
        "transition_lines_ko": [],
        "consumer_check_side": "BUY",
        "consumer_check_reason": "upper_reject_mixed_confirm",
        "position_dominance": "UPPER",
        "structure_alignment_mode": "REVERSION",
        "structure_alignment": "MISMATCH",
        "box_relative_position": 0.82,
        "box_zone": "UPPER",
        "range_too_narrow": False,
        "upper_wick_ratio": 0.45,
        "lower_wick_ratio": 0.06,
        "doji_ratio": 0.08,
        "recent_3bar_direction": "STRONG_DOWN",
        "composite_structure_mismatch": True,
        "weight_patch_preview": {
            "state25_teacher_weight_overrides": {
                "upper_wick_weight": 0.75,
                "reversal_risk_weight": 1.10,
            }
        },
    }


def _reverse_bound_row() -> dict[str, object]:
    return {
        "detector_key": detector_module.DETECTOR_REVERSE_PATTERN,
        "detector_label_ko": "reverse pattern detector",
        "severity": 2,
        "proposal_stage": "OBSERVE",
        "readiness_status": "READY_FOR_REVIEW",
        "symbol": "NAS100",
        "repeat_count": 3,
        "summary_ko": "NAS100 missed reverse / shock 패턴 관찰",
        "why_now_ko": "NAS100에서 reverse missed로 읽을 수 있는 shock 패턴이 반복됐습니다.",
        "recommended_action_ko": "즉시 반영하지 않고 관찰합니다.",
        "evidence_lines_ko": [
            "- avg_shock_score: 28.1",
            "- dominant_shock_reason: opposite_score_spike",
        ],
        "transition_lines_ko": [],
    }


def test_db1_detector_direct_binding_attaches_scene_registry_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "_build_scene_aware_detector_rows_v2",
        lambda *args, **kwargs: [_scene_bound_row()],
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
        runtime_status_detail_payload={},
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T19:00:00+09:00",
    )

    row = payload["scene_aware_detector"]["surfaced_rows"][0]
    assert row["registry_key"] == "misread:structure_alignment"
    assert row["registry_binding_ready"] is True
    assert "misread:position_dominance" in row["evidence_registry_keys"]
    assert "misread:structure_alignment" in row["evidence_registry_keys"]
    assert "misread:result_type" in row["evidence_registry_keys"]
    assert "misread:cooldown_window_min" in row["evidence_registry_keys"]
    assert payload["feedback_issue_refs"][0]["registry_key"] == "misread:structure_alignment"


def test_db1_detector_direct_binding_attaches_target_registry_keys(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "_build_scene_aware_detector_rows_v2",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        detector_module,
        "_build_candle_weight_detector_rows_v2",
        lambda *args, **kwargs: ([_candle_bound_row()], {}),
    )
    monkeypatch.setattr(
        detector_module,
        "_build_reverse_pattern_detector_rows",
        lambda *args, **kwargs: [],
    )

    payload = detector_module.build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        runtime_status_detail_payload={},
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T19:10:00+09:00",
    )

    row = payload["candle_weight_detector"]["surfaced_rows"][0]
    assert row["registry_key"] == "misread:composite_structure_mismatch"
    assert row["registry_binding_mode"] == detector_module.LEARNING_REGISTRY_BINDING_MODE_DERIVED
    assert set(row["target_registry_keys"]) == {
        "state25_weight:upper_wick_weight",
        "state25_weight:reversal_risk_weight",
    }
    assert row["registry_binding_ready"] is True


def test_db1_detector_direct_binding_uses_fallback_for_reverse_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "_build_scene_aware_detector_rows_v2",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        detector_module,
        "_build_candle_weight_detector_rows_v2",
        lambda *args, **kwargs: ([], {}),
    )
    monkeypatch.setattr(
        detector_module,
        "_build_reverse_pattern_detector_rows",
        lambda *args, **kwargs: [_reverse_bound_row()],
    )

    payload = detector_module.build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        runtime_status_detail_payload={},
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T19:20:00+09:00",
    )

    row = payload["reverse_pattern_detector"]["surfaced_rows"][0]
    assert row["registry_key"] == "misread:result_type"
    assert row["registry_binding_mode"] == detector_module.LEARNING_REGISTRY_BINDING_MODE_FALLBACK
    assert row["target_registry_keys"] == []
    assert "misread:result_type" in row["evidence_registry_keys"]
