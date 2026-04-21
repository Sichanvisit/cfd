from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

import backend.services.improvement_log_only_detector as detector_module


KST = ZoneInfo("Asia/Seoul")


def _base_row(*, result_type: str) -> dict[str, object]:
    return {
        "detector_key": detector_module.DETECTOR_SCENE_AWARE,
        "symbol": "BTCUSD",
        "summary_ko": "BTCUSD 상하단 방향 오판 가능성 관찰",
        "why_now_ko": "상단 구간에서 구조 엇갈림 가능성이 관찰됩니다.",
        "evidence_lines_ko": [
            "- 위/아래 힘: 상단 우세 (하단 0.05 / 상단 0.34 / 중립 0.00)",
            "- 박스 위치: 상단 영역 (0.82 / state UPPER / proxy)",
        ],
        "transition_lines_ko": [],
        "result_type": result_type,
        "explanation_type": detector_module.EXPLANATION_TYPE_CLEAR,
        "severity": 1,
        "repeat_count": 2,
    }


def test_p46g_attaches_hindsight_status_from_result_type() -> None:
    rows = detector_module._attach_hindsight_validator(
        [
            _base_row(result_type=detector_module.RESULT_TYPE_MISREAD),
            _base_row(result_type=detector_module.RESULT_TYPE_TIMING),
            _base_row(result_type=detector_module.RESULT_TYPE_CORRECT),
            _base_row(result_type=detector_module.RESULT_TYPE_UNRESOLVED),
        ]
    )

    assert rows[0]["hindsight_status"] == detector_module.HINDSIGHT_STATUS_CONFIRMED_MISREAD
    assert rows[1]["hindsight_status"] == detector_module.HINDSIGHT_STATUS_PARTIAL_MISREAD
    assert rows[2]["hindsight_status"] == detector_module.HINDSIGHT_STATUS_FALSE_ALARM
    assert rows[3]["hindsight_status"] == detector_module.HINDSIGHT_STATUS_UNRESOLVED


def test_p46g_snapshot_exposes_hindsight_summary_and_feedback_refs(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "_build_scene_aware_detector_rows_v2",
        lambda *args, **kwargs: [_base_row(result_type=detector_module.RESULT_TYPE_MISREAD)],
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
    monkeypatch.setattr(
        detector_module,
        "_attach_misread_axes",
        lambda rows: rows,
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
        now_ts="2026-04-13T12:00:00+09:00",
    )

    assert payload["hindsight_summary"][detector_module.HINDSIGHT_STATUS_CONFIRMED_MISREAD] == 1
    assert payload["surfaced_detector_count"] == 1
    assert payload["feedback_issue_refs"][0]["hindsight_status"] == detector_module.HINDSIGHT_STATUS_CONFIRMED_MISREAD
    assert payload["feedback_issue_refs"][0]["hindsight_status_ko"] == "사후 확정 오판"
