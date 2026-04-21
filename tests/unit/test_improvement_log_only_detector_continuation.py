from __future__ import annotations

import pandas as pd
from zoneinfo import ZoneInfo

import backend.services.improvement_log_only_detector as detector_module


KST = ZoneInfo("Asia/Seoul")


def test_scene_detector_surfaces_directional_continuation_candidates(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "build_directional_continuation_learning_candidates",
        lambda: [
            {
                "symbol": "XAUUSD",
                "repeat_count": 3,
                "summary_ko": "XAUUSD 하락 지속 누락 가능성 관찰",
                "why_now_ko": "반등처럼 읽었지만 실제로는 계속 내려가는 장면이 반복됐습니다.",
                "recommended_action_ko": "자동 관찰을 누적합니다.",
                "evidence_lines_ko": ["- 추세 힌트: 계속 내려갈 가능성 누락 관찰"],
                "misread_confidence": 0.73,
                "registry_key": "misread:directional_down_continuation_conflict",
                "extra_evidence_registry_keys": ["misread:directional_down_continuation_conflict"],
                "continuation_direction": "DOWN",
                "pattern_code": "continuation_gap_down",
                "pattern_label_ko": "하락 지속 누락",
                "primary_failure_label": "wrong_side_buy_pressure",
                "continuation_failure_label": "missed_down_continuation",
                "context_failure_label": "false_up_pressure_in_downtrend",
                "source_kind": "wrong_side_conflict_harvest",
                "source_kind_list": ["wrong_side_conflict_harvest", "market_family_entry_audit"],
                "source_labels_ko": ["wrong-side conflict", "market-family observe"],
                "dominant_observe_reason": "upper_reject_confirm",
            }
        ],
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
        runtime_status_detail_payload={"latest_signal_by_symbol": {}},
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-14T14:50:00+09:00",
    )

    rows = payload["scene_aware_detector"]["surfaced_rows"]
    assert any(row.get("continuation_direction") == "DOWN" for row in rows)
    row = next(row for row in rows if row.get("continuation_direction") == "DOWN")
    assert row["summary_ko"] == "XAUUSD 하락 지속 누락 가능성 관찰"
    assert row["registry_key"] == "misread:directional_down_continuation_conflict"
    assert row["source_kind"] == "wrong_side_conflict_harvest"
    assert row["dominant_observe_reason"] == "upper_reject_confirm"
