from __future__ import annotations

import backend.services.improvement_log_only_detector as detector_module


def _base_row() -> dict[str, object]:
    return {
        "detector_key": "scene_aware",
        "symbol": "BTCUSD",
        "summary_ko": "BTCUSD breakout retest structure mismatch 관찰",
        "why_now_ko": "breakout retest 구간에서 structure mismatch 가능성을 관찰합니다.",
        "evidence_lines_ko": [
            "- 위/아래 힘: 상단 우세 (하단 0.05 / 상단 0.34 / 중립 0.00)",
            "- 박스 위치: 상단 영역 (0.82 / state UPPER / proxy)",
            "- 캔들 구조: 윗꼬리 0.44 / 아랫꼬리 0.05 / 몸통 0.18 / 윗꼬리 거부 우세",
            "- 최근 3봉 흐름: 약하락 (상승 0.18 / 하락 0.76 / 연속 3)",
            "- 현재 체크 이유: breakout_retest_hold",
        ],
        "transition_lines_ko": ["- next_action_hint: HOLD"],
        "result_type": "result_unresolved",
        "explanation_type": "explanation_clear",
        "severity": 1,
        "repeat_count": 4,
    }


def test_p46i_attaches_context_confidence_and_explainability_snapshot() -> None:
    row = detector_module._attach_detector_operational_hints([_base_row()])[0]

    assert row["feedback_scope_key"].startswith("scene_aware::BTCUSD::")
    assert row["context_flag"] == "breakout_context"
    assert float(row["context_confidence"]) >= 0.40
    assert row["context_confidence_label_ko"] in {"높음", "주의"}
    assert float(row["misread_confidence"]) > 0.0
    snapshot = dict(row["explainability_snapshot"])
    assert snapshot["context"] == "breakout_context"
    assert "위/아래 힘" in snapshot["force"]
    assert "박스 위치:" in snapshot["box"]
    assert "캔들 구조:" in snapshot["candle"]
    assert "최근 3봉 흐름:" in snapshot["recent_3bar"]


def test_p46i_cooldown_suppresses_same_scope_within_window() -> None:
    row = detector_module._attach_detector_operational_hints([_base_row()])[0]
    scope_key = str(row["feedback_scope_key"])
    previous_snapshot_payload = {
        "cooldown_state": {
            "rows_by_scope": {
                scope_key: {
                    "feedback_scope_key": scope_key,
                    "detector_key": row["detector_key"],
                    "symbol": row["symbol"],
                    "summary_ko": row["summary_ko"],
                    "last_surfaced_at": "2026-04-13T10:00:00+09:00",
                    "misread_confidence": row["misread_confidence"],
                    "severity": row["severity"],
                    "repeat_count": row["repeat_count"],
                    "result_type": row["result_type"],
                    "cooldown_window_min": 45,
                }
            }
        }
    }

    surfaced, suppressed, summary, cooldown_state = detector_module._apply_detector_cooldown(
        [row],
        previous_snapshot_payload=previous_snapshot_payload,
        now_ts="2026-04-13T10:10:00+09:00",
    )

    assert surfaced == []
    assert len(suppressed) == 1
    assert suppressed[0]["cooldown_state"] == "SUPPRESSED"
    assert summary["suppressed"] == 1
    assert scope_key in dict(cooldown_state["rows_by_scope"])


def test_p46i_cooldown_bypasses_when_evidence_gets_stronger() -> None:
    row = detector_module._attach_detector_operational_hints([_base_row()])[0]
    scope_key = str(row["feedback_scope_key"])
    previous_snapshot_payload = {
        "cooldown_state": {
            "rows_by_scope": {
                scope_key: {
                    "feedback_scope_key": scope_key,
                    "detector_key": row["detector_key"],
                    "symbol": row["symbol"],
                    "summary_ko": row["summary_ko"],
                    "last_surfaced_at": "2026-04-13T10:00:00+09:00",
                    "misread_confidence": 0.20,
                    "severity": 2,
                    "repeat_count": 1,
                    "result_type": "result_unresolved",
                    "cooldown_window_min": 45,
                }
            }
        }
    }

    surfaced, suppressed, summary, _ = detector_module._apply_detector_cooldown(
        [row],
        previous_snapshot_payload=previous_snapshot_payload,
        now_ts="2026-04-13T10:10:00+09:00",
    )

    assert len(surfaced) == 1
    assert suppressed == []
    assert surfaced[0]["cooldown_state"] == "BYPASS"
    assert summary["bypassed"] == 1
