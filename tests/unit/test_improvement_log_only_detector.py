from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

import backend.services.improvement_log_only_detector as detector_module
from backend.services.improvement_detector_feedback_runtime import (
    build_detector_feedback_entry,
    build_detector_feedback_scope_key,
)
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


def test_improvement_log_only_detector_snapshot_surfaces_broadened_inputs() -> None:
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
            "NAS100": {
                "symbol": "NAS100",
                "consumer_check_side": "SELL",
                "consumer_check_reason": "upper_reject_probe_observe",
                "next_action_hint": "BOTH",
                "box_state": "UPPER",
                "micro_upper_wick_ratio_20": 0.41,
                "micro_lower_wick_ratio_20": 0.08,
                "micro_doji_ratio_20": 0.10,
                "micro_body_size_pct_20": 0.22,
                "micro_same_color_run_current": 3,
                "micro_same_color_run_max_20": 4,
                "micro_bull_ratio_20": 0.18,
                "micro_bear_ratio_20": 0.76,
                "position_energy_surface_v1": {
                    "energy": {
                        "lower_position_force": 0.00,
                        "upper_position_force": 0.48,
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
            },
            "XAUUSD": {
                "symbol": "XAUUSD",
                "consumer_check_side": "SELL",
                "consumer_check_reason": "middle_sr_anchor_required_observe",
                "blocked_by": "middle_sr_anchor_guard",
                "box_state": "UPPER",
                "micro_upper_wick_ratio_20": 0.18,
                "micro_lower_wick_ratio_20": 0.09,
                "micro_doji_ratio_20": 0.36,
                "micro_body_size_pct_20": 0.03,
                "micro_same_color_run_current": 2,
                "micro_same_color_run_max_20": 3,
                "micro_bull_ratio_20": 0.30,
                "micro_bear_ratio_20": 0.62,
                "position_energy_surface_v1": {
                    "energy": {
                        "lower_position_force": 0.05,
                        "upper_position_force": 0.34,
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
            },
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
                    "energy": {
                        "metadata": {
                            "position_dominance": "LOWER",
                        }
                    }
                },
            },
        }
    }
    readiness_surface_payload = {
        "reverse_surface": {
            "readiness_status": "BLOCKED",
            "blocking_reason": "system_phase_degraded",
        }
    }
    scene_disagreement_payload = {
        "summary": {
            "recommended_next_action": "keep_scene_candidate_log_only_and_patch_overpull_labels_before_sa6",
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
            "preview_changed_row_count": 2,
            "improved_row_count": 1,
            "worsened_row_count": 1,
            "recommended_next_action": "keep_trend_exhaustion_scene_bias_preview_only",
            "top_changed_slices": [
                {
                    "symbol": "BTCUSD",
                    "checkpoint_type": "RUNNER_CHECK",
                    "preview_action_label": "PARTIAL_THEN_HOLD",
                    "count": 1,
                }
            ],
        }
    }

    payload = build_improvement_log_only_detector_snapshot(
        runtime_status_payload=runtime_status_payload,
        runtime_status_detail_payload=runtime_status_detail_payload,
        readiness_surface_payload=readiness_surface_payload,
        scene_disagreement_payload=scene_disagreement_payload,
        scene_bias_preview_payload=scene_bias_preview_payload,
        closed_frame=_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-12T21:30:00+09:00",
    )

    assert payload["contract_version"] == "improvement_log_only_detector_v1"
    assert payload["proposal_envelope"]["proposal_stage"] == "OBSERVE"
    assert payload["proposal_envelope"]["readiness_status"] == "READY_FOR_REVIEW"
    assert payload["surfaced_detector_count"] == 6

    scene_rows = payload["scene_aware_detector"]["surfaced_rows"]
    candle_rows = payload["candle_weight_detector"]["surfaced_rows"]
    reverse_rows = payload["reverse_pattern_detector"]["surfaced_rows"]

    assert len(scene_rows) == 3
    assert any(
        any("semantic_shadow_trace_quality:" in line for line in row.get("evidence_lines_ko", []))
        for row in scene_rows
    )
    assert any("상하단 방향 오판 가능성 관찰" in row["summary_ko"] for row in scene_rows)
    assert payload["scene_aware_detector"]["candidate_count"] >= 3
    assert any(
        any("위/아래 힘" in line for line in row.get("evidence_lines_ko", []))
        for row in scene_rows
    )
    assert any(
        any("박스 위치:" in line for line in row.get("evidence_lines_ko", []))
        for row in scene_rows
    )
    assert any(
        any("캔들 구조:" in line for line in row.get("evidence_lines_ko", []))
        for row in scene_rows
    )
    assert any(
        any("최근 3봉 흐름:" in line for line in row.get("evidence_lines_ko", []))
        for row in scene_rows
    )

    assert len(candle_rows) == 1
    assert "캔들/박스 위치 대비 방향 해석 불일치 관찰" in candle_rows[0]["summary_ko"]
    assert candle_rows[0]["weight_patch_preview"]["review_type"] == "STATE25_WEIGHT_PATCH_REVIEW"
    assert any("위/아래 힘" in line for line in candle_rows[0].get("evidence_lines_ko", []))
    assert any("박스 위치:" in line for line in candle_rows[0].get("evidence_lines_ko", []))
    assert any("캔들 구조:" in line for line in candle_rows[0].get("evidence_lines_ko", []))
    assert any("최근 3봉 흐름:" in line for line in candle_rows[0].get("evidence_lines_ko", []))
    assert "현재 박스 위치는" in candle_rows[0]["why_now_ko"]
    assert "현재 캔들 구조는" in candle_rows[0]["why_now_ko"]
    assert "현재 최근 3봉 흐름은" in candle_rows[0]["why_now_ko"]

    assert len(reverse_rows) == 2
    assert any("missed reverse" in row["summary_ko"] for row in reverse_rows)
    assert all(row["symbol"] == "BTCUSD" for row in reverse_rows)
    assert "[detector" in payload["inbox_summary_ko"]
    assert payload["feedback_issue_refs"][0]["feedback_ref"] == "D1"
    assert any(str(line).startswith("D1.") for line in payload["report_lines_ko"])


def test_improvement_log_only_detector_uses_problem_pattern_fallback_for_candle_detector(
    monkeypatch,
) -> None:
    def _fake_proposal_snapshot(*args, **kwargs):
        return {
            "surfaced_problem_patterns": [],
            "problem_patterns": [
                {
                    "level": 3,
                    "entry_reason": "upper_reject_mixed_confirm",
                    "entry_reason_ko": "상단 거부 혼합 확인",
                    "trade_count": 5,
                    "net_pnl": -7.0,
                    "win_rate": 0.40,
                    "level_reason_ko": "관찰 중이지만 누적 손실이 이어집니다.",
                }
            ],
            "analyzed_trade_count": 5,
        }

    monkeypatch.setattr(
        detector_module,
        "build_manual_trade_proposal_snapshot",
        _fake_proposal_snapshot,
    )

    payload = build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-12T21:35:00+09:00",
    )

    candle_rows = payload["candle_weight_detector"]["surfaced_rows"]
    assert len(candle_rows) == 1
    assert candle_rows[0]["summary_ko"] == "상단 거부 혼합 확인 패턴 가중치 점검 제안"


def test_box_relative_context_uses_box_state_proxy_when_direct_value_missing() -> None:
    context = detector_module._resolve_box_relative_context(
        {
            "box_state": "UPPER",
        }
    )

    assert context["available"] is True
    assert context["source_mode"] == "proxy"
    assert context["box_zone"] == "UPPER"
    assert abs(float(context["box_relative_position"]) - 0.82) < 1e-9


def test_wick_body_context_marks_doji_and_structure_hint() -> None:
    context = detector_module._resolve_wick_body_context(
        {
            "micro_upper_wick_ratio_20": 0.52,
            "micro_lower_wick_ratio_20": 0.10,
            "micro_doji_ratio_20": 0.36,
            "micro_body_size_pct_20": 0.03,
        }
    )

    assert context["available"] is True
    assert context["candle_type"] == "DOJI"
    assert context["structure_hint"] == "상단 거부형 doji"


def test_recent_3bar_direction_context_marks_strong_down_and_run_hint() -> None:
    context = detector_module._resolve_recent_3bar_direction_context(
        {
            "micro_bull_ratio_20": 0.18,
            "micro_bear_ratio_20": 0.76,
            "micro_same_color_run_current": 3,
            "micro_same_color_run_max_20": 4,
        }
    )

    assert context["available"] is True
    assert context["recent_3bar_direction"] == "STRONG_DOWN"
    assert context["recent_3bar_direction_ko"] == "강하락"
    assert context["structure_hint"] == "하락 연속 3"
def test_improvement_log_only_detector_suppresses_repeated_oversensitive_scope() -> None:
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
                for _ in range(3)
            ]
        }
    }
    issue_ref = {
        "feedback_ref": "D1",
        "feedback_key": "detfb_seed",
        "feedback_scope_key": build_detector_feedback_scope_key(
            detector_key="scene_aware",
            symbol="BTCUSD",
            summary_ko="BTCUSD scene trace 누락 반복 감지",
        ),
        "detector_key": "scene_aware",
        "symbol": "BTCUSD",
        "summary_ko": "BTCUSD scene trace 누락 반복 감지",
    }
    feedback_history = [
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="oversensitive",
            user_id=1001,
            username="@ops_user",
            proposal_id="proposal-1",
            now_ts="2026-04-12T22:00:00+09:00",
        ),
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="oversensitive",
            user_id=1001,
            username="@ops_user",
            proposal_id="proposal-2",
            now_ts="2026-04-12T22:01:00+09:00",
        ),
    ]

    payload = build_improvement_log_only_detector_snapshot(
        runtime_status_payload=runtime_status_payload,
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        feedback_history=feedback_history,
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-12T22:05:00+09:00",
    )

    assert payload["narrowed_out_detector_count"] >= 1
    assert all(
        "scene trace" not in str(row.get("summary_ko", ""))
        for row in payload["scene_aware_detector"]["surfaced_rows"]
    )
    narrowed_rows = payload["scene_aware_detector"]["narrowed_out_rows"]
    assert len(narrowed_rows) == 1
    assert narrowed_rows[0]["narrowing_decision"] == "SUPPRESS"
