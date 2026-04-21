from __future__ import annotations

from backend.services.state25_context_bridge import build_state25_candidate_context_bridge_v1
from backend.services.state25_context_bridge_bounded_live_readiness import (
    build_state25_context_bridge_bounded_live_readiness,
)


def _runtime_row(symbol: str, *, effective_entry_threshold: float, final_score: float) -> dict[str, object]:
    row = {
        "symbol": symbol,
        "entry_stage": "balanced",
        "consumer_check_side": "SELL",
        "signal_timeframe": "15M",
        "context_bundle_summary_ko": "HTF 대체로 상승 정렬 | 직전 박스 상단 돌파 유지 | 역행 SELL 경계",
        "context_conflict_label_ko": "상위 추세와 직전 박스 모두 역행",
        "htf_alignment_state": "AGAINST_HTF",
        "htf_alignment_detail": "AGAINST_HTF_UP",
        "htf_against_severity": "MEDIUM",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_lifecycle": "BROKEN",
        "previous_box_confidence": "HIGH",
        "previous_box_is_consolidation": True,
        "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        "context_conflict_intensity": "MEDIUM",
        "trend_1h_age_seconds": 60,
        "trend_4h_age_seconds": 60,
        "trend_1d_age_seconds": 60,
        "previous_box_age_seconds": 60,
        "effective_entry_threshold": effective_entry_threshold,
        "final_score": final_score,
    }
    row["state25_candidate_context_bridge_v1"] = build_state25_candidate_context_bridge_v1(row)
    return row


def test_bounded_live_readiness_blocks_cooldown_and_runtime_zero() -> None:
    runtime_row = _runtime_row("XAUUSD", effective_entry_threshold=40, final_score=41)
    detector_snapshot = {
        "candle_weight_detector": {
            "cooldown_suppressed_rows": [
                {
                    "symbol": "XAUUSD",
                    "feedback_scope_key": "candle_weight::XAUUSD::xauusd_state25_context_bridge_threshold_review",
                    "state25_candidate_context_bridge_v1": runtime_row["state25_candidate_context_bridge_v1"],
                    "threshold_patch_preview": {"review_type": "STATE25_THRESHOLD_PATCH_REVIEW"},
                }
            ]
        },
        "cooldown_state": {
            "rows_by_scope": {
                "candle_weight::XAUUSD::xauusd_state25_context_bridge_threshold_review": {
                    "last_surfaced_at": "2026-04-14T14:00:00+09:00",
                    "cooldown_window_min": 90,
                }
            }
        },
    }
    runtime_payload = {
        "latest_signal_by_symbol": {
            "XAUUSD": {
                **runtime_row,
                "state25_context_bridge_threshold_requested_points": 0.0,
                "state25_context_bridge_threshold_effective_points": 0.0,
            }
        }
    }

    report = build_state25_context_bridge_bounded_live_readiness(
        detector_snapshot_payload=detector_snapshot,
        runtime_status_detail_payload=runtime_payload,
        active_candidate_state_payload={"current_binding_mode": "log_only"},
        execute_apply=False,
        now_ts="2026-04-14T14:30:00+09:00",
    )

    assert report["summary"]["threshold_candidate_count"] == 1
    candidate = report["threshold_candidates"][0]
    assert candidate["cooldown_active"] is True
    assert candidate["apply_ready"] is False
    assert "COOLDOWN_ACTIVE" in candidate["apply_block_reasons"]
    assert "RUNTIME_BRIDGE_ZERO" in candidate["apply_block_reasons"]


def test_bounded_live_readiness_blocks_shared_threshold_delta_contract() -> None:
    btc_row = _runtime_row("BTCUSD", effective_entry_threshold=40, final_score=44)
    nas_row = _runtime_row("NAS100", effective_entry_threshold=40, final_score=43)
    btc_row["state25_candidate_context_bridge_v1"] = {
        **btc_row["state25_candidate_context_bridge_v1"],
        "threshold_adjustment_requested": {
            "threshold_delta_points": 4.0,
            "threshold_delta_pct": 0.1,
            "threshold_delta_direction": "HARDEN",
            "threshold_delta_reason_keys": ["AGAINST_HTF"],
            "threshold_base_points": 40.0,
            "threshold_candidate_points": 44.0,
        },
        "threshold_adjustment_effective": {
            "threshold_delta_points": 4.0,
            "threshold_delta_pct": 0.1,
            "threshold_delta_direction": "HARDEN",
            "threshold_delta_reason_keys": ["AGAINST_HTF"],
            "threshold_candidate_points": 44.0,
        },
    }
    nas_row["state25_candidate_context_bridge_v1"] = {
        **nas_row["state25_candidate_context_bridge_v1"],
        "threshold_adjustment_requested": {
            "threshold_delta_points": 3.0,
            "threshold_delta_pct": 0.075,
            "threshold_delta_direction": "HARDEN",
            "threshold_delta_reason_keys": ["AGAINST_PREV_BOX_AND_HTF"],
            "threshold_base_points": 40.0,
            "threshold_candidate_points": 43.0,
        },
        "threshold_adjustment_effective": {
            "threshold_delta_points": 3.0,
            "threshold_delta_pct": 0.075,
            "threshold_delta_direction": "HARDEN",
            "threshold_delta_reason_keys": ["AGAINST_PREV_BOX_AND_HTF"],
            "threshold_candidate_points": 43.0,
        },
    }
    detector_snapshot = {
        "candle_weight_detector": {
            "surfaced_rows": [
                {
                    "symbol": "BTCUSD",
                    "feedback_scope_key": "candle_weight::BTCUSD::bridge_threshold",
                    "state25_candidate_context_bridge_v1": btc_row["state25_candidate_context_bridge_v1"],
                    "threshold_patch_preview": {"review_type": "STATE25_THRESHOLD_PATCH_REVIEW"},
                },
                {
                    "symbol": "NAS100",
                    "feedback_scope_key": "candle_weight::NAS100::bridge_threshold",
                    "state25_candidate_context_bridge_v1": nas_row["state25_candidate_context_bridge_v1"],
                    "threshold_patch_preview": {"review_type": "STATE25_THRESHOLD_PATCH_REVIEW"},
                },
            ]
        },
        "cooldown_state": {
            "rows_by_scope": {
                "candle_weight::BTCUSD::bridge_threshold": {
                    "last_surfaced_at": "2026-04-14T12:00:00+09:00",
                    "cooldown_window_min": 30,
                },
                "candle_weight::NAS100::bridge_threshold": {
                    "last_surfaced_at": "2026-04-14T12:00:00+09:00",
                    "cooldown_window_min": 30,
                },
            }
        },
    }
    runtime_payload = {
        "latest_signal_by_symbol": {
            "BTCUSD": {
                **btc_row,
                "state25_context_bridge_threshold_requested_points": 4.0,
                "state25_context_bridge_threshold_effective_points": 4.0,
            },
            "NAS100": {
                **nas_row,
                "state25_context_bridge_threshold_requested_points": 3.0,
                "state25_context_bridge_threshold_effective_points": 3.0,
            },
        }
    }

    report = build_state25_context_bridge_bounded_live_readiness(
        detector_snapshot_payload=detector_snapshot,
        runtime_status_detail_payload=runtime_payload,
        active_candidate_state_payload={"current_binding_mode": "log_only"},
        execute_apply=False,
        now_ts="2026-04-14T14:30:00+09:00",
    )

    assert report["summary"]["threshold_shared_delta_blocked"] is True
    assert report["summary"]["threshold_apply_ready_count"] == 0
    assert report["summary"]["recommended_next_action"] == "split_threshold_bounded_live_by_symbol_before_apply"
