from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

import backend.services.improvement_log_only_detector as detector_module
from backend.services.improvement_log_only_detector import (
    build_improvement_log_only_detector_snapshot,
)


KST = ZoneInfo("Asia/Seoul")


def _closed_frame() -> pd.DataFrame:
    rows = []
    for index in range(5):
        rows.append(
            {
                "trade_link_key": f"bad-{index}",
                "symbol": "BTCUSD",
                "close_time": f"2026-04-12 0{index}:10:00",
                "profit": -2.0,
                "gross_pnl": -1.4,
                "cost_total": 0.6,
                "net_pnl_after_cost": -2.0,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.8,
                "shock_score": 22.0 + float(index),
                "shock_reason": "opposite_score_spike|adverse_risk",
                "shock_action": "force_exit_candidate" if index < 3 else "hold",
            }
        )
    return pd.DataFrame(rows)


def test_p46e_snapshot_attaches_result_and_explanation_axes() -> None:
    runtime_status_payload = {
        "semantic_rollout_state": {
            "recent": [
                {
                    "domain": "entry",
                    "symbol": "BTCUSD",
                    "mode": "log_only",
                    "trace_quality_state": "unavailable",
                    "fallback_reason": "baseline_no_action",
                    "reason": "mode=log_only, trace=unavailable",
                }
                for _ in range(4)
            ]
        },
        "pending_reverse_by_symbol": {
            "BTCUSD": {
                "action": "BUY",
                "reasons": [
                    "opposite_score_spike",
                    "volatility_spike",
                    "plus_to_minus_protect",
                ],
                "reason_count": 3,
                "age_sec": 14,
                "expires_in_sec": 6,
            }
        },
    }
    runtime_status_detail_payload = {
        "latest_signal_by_symbol": {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "consumer_check_side": "BUY",
                "consumer_check_reason": "observe_default",
                "box_state": "LOWER",
                "micro_upper_wick_ratio_20": 0.07,
                "micro_lower_wick_ratio_20": 0.31,
                "micro_doji_ratio_20": 0.12,
                "micro_body_size_pct_20": 0.19,
                "micro_same_color_run_current": 3,
                "micro_same_color_run_max_20": 5,
                "micro_bull_ratio_20": 0.72,
                "micro_bear_ratio_20": 0.18,
                "position_energy_surface_v1": {
                    "energy": {
                        "lower_position_force": 0.20,
                        "upper_position_force": 0.00,
                        "middle_neutrality": 0.00,
                    }
                },
                "position_snapshot_v2": {
                    "energy": {"metadata": {"position_dominance": "LOWER"}}
                },
            }
        }
    }
    scene_disagreement_payload = {
        "summary": {
            "recommended_next_action": "keep_scene_candidate_log_only",
            "label_pull_profiles": [
                {
                    "candidate_selected_label": "trend_exhaustion",
                    "row_count": 6,
                    "runtime_unresolved_share": 1.0,
                    "hindsight_resolved_share": 0.10,
                    "expected_action_alignment_rate": 0.99,
                    "watch_state": "overpull_watch",
                    "top_slices": [
                        {
                            "symbol": "BTCUSD",
                            "surface_name": "continuation_hold_surface",
                            "checkpoint_type": "RUNNER_CHECK",
                            "count": 6,
                        }
                    ],
                }
            ],
        }
    }
    scene_bias_preview_payload = {
        "summary": {
            "preview_changed_row_count": 0,
            "improved_row_count": 0,
            "worsened_row_count": 0,
            "recommended_next_action": "keep_preview_only",
            "top_changed_slices": [],
        }
    }

    payload = build_improvement_log_only_detector_snapshot(
        runtime_status_payload=runtime_status_payload,
        runtime_status_detail_payload=runtime_status_detail_payload,
        readiness_surface_payload={},
        scene_disagreement_payload=scene_disagreement_payload,
        scene_bias_preview_payload=scene_bias_preview_payload,
        closed_frame=_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-12T21:30:00+09:00",
    )

    scene_rows = payload["scene_aware_detector"]["surfaced_rows"]
    candle_rows = payload["candle_weight_detector"]["surfaced_rows"]
    reverse_rows = payload["reverse_pattern_detector"]["surfaced_rows"]

    assert any(row["result_type"] == "result_unresolved" for row in scene_rows)
    assert any(row["explanation_type"] == "explanation_clear" for row in scene_rows)
    assert candle_rows[0]["result_type"] == "result_misread"
    assert candle_rows[0]["explanation_type"] == "explanation_clear"
    assert any(row["result_type"] == "result_unresolved" for row in reverse_rows)
    assert any(row["result_type"] == "result_misread" for row in reverse_rows)
    assert any("분류: 결과 오판 / 설명 명확" in line for line in payload["report_lines_ko"])


def test_p46e_candle_issue_is_classified_as_result_misread_and_clear() -> None:
    rows = detector_module._attach_misread_axes(
        [
            {
                "detector_key": "candle_weight",
                "summary_ko": "BTCUSD 캔들/박스 위치 대비 방향 해석 불일치 관찰",
                "why_now_ko": "반복 손실이 누적되었습니다.",
                "evidence_lines_ko": [
                    "- 위/아래 힘: 하단 우세",
                    "- 박스 위치: 상단 영역 (0.82 / state UPPER / proxy)",
                    "- 캔들 구조: 윗꼬리 0.44 / 아랫꼬리 0.05 / 몸통 0.18",
                ],
                "transition_lines_ko": [],
                "net_pnl": -7.0,
                "win_rate": 0.40,
            }
        ]
    )

    row = rows[0]
    assert row["result_type"] == "result_misread"
    assert row["explanation_type"] == "explanation_clear"
    assert row["misread_axes_ko"] == "결과 오판 / 설명 명확"


def test_p46e_scene_issue_is_unresolved_and_gap_when_evidence_is_thin() -> None:
    rows = detector_module._attach_misread_axes(
        [
            {
                "detector_key": "scene_aware",
                "summary_ko": "BTCUSD 상하단 방향 오판 가능성 관찰",
                "why_now_ko": "scene 불일치가 누적됐습니다.",
                "evidence_lines_ko": ["- 현재 체크 이유: upper_reject_probe_observe"],
                "transition_lines_ko": [],
            }
        ]
    )

    row = rows[0]
    assert row["result_type"] == "result_unresolved"
    assert row["explanation_type"] == "explanation_gap"
