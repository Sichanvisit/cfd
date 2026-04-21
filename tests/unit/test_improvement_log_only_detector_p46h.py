from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

import backend.services.improvement_log_only_detector as detector_module


KST = ZoneInfo("Asia/Seoul")


def _proposal_issue_payload() -> dict[str, object]:
    issue = {
        "level": 1,
        "entry_reason": "upper_reject_mixed_confirm",
        "entry_reason_ko": "상단 거부 혼합 확인",
        "trade_count": 5,
        "win_rate": 0.20,
        "net_pnl": -6.0,
        "level_reason_ko": "반복 손실이 관찰됩니다.",
        "dominant_symbol": "BTCUSD",
        "symbol": "BTCUSD",
    }
    return {
        "surfaced_problem_patterns": [issue],
        "problem_patterns": [issue],
        "analyzed_trade_count": 5,
    }


def test_p46h_surfaces_composite_structure_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "build_manual_trade_proposal_snapshot",
        lambda *args, **kwargs: _proposal_issue_payload(),
    )

    payload = detector_module.build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        runtime_status_detail_payload={
            "latest_signal_by_symbol": {
                "BTCUSD": {
                    "symbol": "BTCUSD",
                    "consumer_check_side": "BUY",
                    "consumer_check_reason": "upper_reject_mixed_confirm",
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
                }
            }
        },
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T14:00:00+09:00",
    )

    candle_rows = payload["candle_weight_detector"]["surfaced_rows"]
    assert len(candle_rows) == 1
    row = candle_rows[0]
    assert row["summary_ko"] == "BTCUSD 구조 복합 불일치 관찰"
    assert row["composite_structure_mismatch"] is True
    assert row["structure_mismatch_component_count"] >= 2
    assert any("구조 복합 불일치:" in line for line in row["evidence_lines_ko"])
    assert "구조 복합 불일치" in row["why_now_ko"]


def test_p46h_keeps_single_mismatch_as_normal_row(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "build_manual_trade_proposal_snapshot",
        lambda *args, **kwargs: _proposal_issue_payload(),
    )

    payload = detector_module.build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        runtime_status_detail_payload={
            "latest_signal_by_symbol": {
                "BTCUSD": {
                    "symbol": "BTCUSD",
                    "consumer_check_side": "BUY",
                    "consumer_check_reason": "lower_rebound_confirm",
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
                }
            }
        },
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T14:05:00+09:00",
    )

    candle_rows = payload["candle_weight_detector"]["surfaced_rows"]
    assert len(candle_rows) == 1
    row = candle_rows[0]
    assert row["composite_structure_mismatch"] is False
    assert row["summary_ko"] == "BTCUSD 캔들/박스 위치 대비 방향 해석 불일치 관찰"
