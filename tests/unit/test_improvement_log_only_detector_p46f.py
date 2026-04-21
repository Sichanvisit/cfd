from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

import backend.services.improvement_log_only_detector as detector_module
from backend.services.improvement_log_only_detector import (
    build_improvement_log_only_detector_snapshot,
)


KST = ZoneInfo("Asia/Seoul")


def _closed_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "trade_link_key": "t1",
                "symbol": "BTCUSD",
                "close_time": "2026-04-12 01:10:00",
                "profit": -2.0,
                "gross_pnl": -1.4,
                "cost_total": 0.6,
                "net_pnl_after_cost": -2.0,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.8,
            }
        ]
    )


def test_p46f_reason_token_profile_marks_manual_h1_default_as_generic_only() -> None:
    profile = detector_module._reason_token_profile("manual_h1_default")

    assert profile["generic_only"] is True
    assert "manual" in profile["generic_tokens"]
    assert profile["specific_tokens"] == []


def test_p46f_reason_token_profile_keeps_specific_when_mixed_present() -> None:
    profile = detector_module._reason_token_profile("upper_reject_mixed_confirm")

    assert profile["generic_only"] is False
    assert "mixed" in profile["generic_tokens"]
    assert "upper" in profile["specific_tokens"]
    assert "reject" in profile["specific_tokens"]


def test_p46f_generic_only_candle_issue_is_not_surfaced(monkeypatch) -> None:
    def _fake_proposal_snapshot(*args, **kwargs):
        return {
            "surfaced_problem_patterns": [],
            "problem_patterns": [
                {
                    "level": 2,
                    "entry_reason": "manual_h1_default",
                    "entry_reason_ko": "수동 H1 기본",
                    "trade_count": 6,
                    "net_pnl": -8.0,
                    "win_rate": 0.33,
                    "level_reason_ko": "generic-only reason이라 detector surface 가치가 낮습니다.",
                }
            ],
            "analyzed_trade_count": 6,
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
        now_ts="2026-04-12T22:15:00+09:00",
    )

    assert payload["candle_weight_detector"]["surfaced_rows"] == []


def test_p46f_generic_runtime_reason_is_hidden_from_evidence() -> None:
    payload = build_improvement_log_only_detector_snapshot(
        runtime_status_payload={
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
        },
        runtime_status_detail_payload={
            "latest_signal_by_symbol": {
                "BTCUSD": {
                    "symbol": "BTCUSD",
                    "consumer_check_side": "BUY",
                    "consumer_check_reason": "observe_default",
                    "box_state": "LOWER",
                    "position_energy_surface_v1": {
                        "energy": {
                            "lower_position_force": 0.30,
                            "upper_position_force": 0.05,
                            "middle_neutrality": 0.00,
                        }
                    },
                    "position_snapshot_v2": {
                        "energy": {"metadata": {"position_dominance": "LOWER"}}
                    },
                }
            }
        },
        readiness_surface_payload={},
        scene_disagreement_payload={
            "summary": {
                "label_pull_profiles": [
                    {
                        "candidate_selected_label": "trend_exhaustion",
                        "row_count": 5,
                        "runtime_unresolved_share": 1.0,
                        "hindsight_resolved_share": 0.2,
                        "expected_action_alignment_rate": 0.9,
                        "watch_state": "overpull_watch",
                        "top_slices": [{"symbol": "BTCUSD", "count": 5}],
                    }
                ]
            }
        },
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-12T22:20:00+09:00",
    )

    scene_rows = payload["scene_aware_detector"]["surfaced_rows"]
    assert scene_rows
    combined_lines = "\n".join(str(line) for line in scene_rows[0].get("evidence_lines_ko", []))
    assert "현재 체크 이유:" not in combined_lines
