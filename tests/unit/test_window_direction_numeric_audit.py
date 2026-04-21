import json

from backend.services.window_direction_numeric_audit import (
    build_window_direction_numeric_audit,
    generate_and_write_window_direction_numeric_audit,
)


def test_build_window_direction_numeric_audit_reports_continuation_under_veto(tmp_path):
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    rows = [
        {
            "record_type": "entry_decision_detail_v1",
            "payload": {
                "time": "2026-04-15T00:30:00",
                "symbol": "NAS100",
                "leg_direction": "UP",
                "breakout_candidate_direction": "UP",
                "checkpoint_transition_reason": "checkpoint_continuation",
                "core_reason": "directional_continuation_overlay_structural_promotion",
                "box_state": "ABOVE",
                "bb_state": "UPPER_EDGE",
                "consumer_check_side": "SELL",
                "consumer_check_reason": "upper_break_fail_confirm",
                "forecast_state25_candidate_wait_bias_action": "reinforce_wait_bias",
                "belief_candidate_recommended_family": "reduce_alert",
                "barrier_candidate_recommended_family": "block_bias",
            },
        },
        {
            "record_type": "entry_decision_detail_v1",
            "payload": {
                "time": "2026-04-15T00:31:00",
                "symbol": "NAS100",
                "leg_direction": "UP",
                "breakout_candidate_direction": "UP",
                "checkpoint_transition_reason": "checkpoint_continuation",
                "core_reason": "directional_continuation_overlay_structural_promotion",
                "box_state": "ABOVE",
                "bb_state": "BREAKOUT",
                "consumer_check_side": "SELL",
                "consumer_check_reason": "upper_reject_confirm",
                "forecast_state25_candidate_wait_bias_action": "reinforce_wait_bias",
                "belief_candidate_recommended_family": "reduce_alert",
                "barrier_candidate_recommended_family": "wait_bias",
            },
        },
    ]
    detail_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

    report = build_window_direction_numeric_audit(
        detail_path,
        [
            {
                "window_id": "nas_test",
                "symbol": "NAS100",
                "label": "NAS continuation sample",
                "expected_direction": "UP",
                "start": "2026-04-15T00:30:00",
                "end": "2026-04-15T00:39:59",
            }
        ],
    )

    window = report["windows"][0]
    metrics = window["metric_rates_v1"]
    hints = window["candidate_threshold_hints_v1"]
    assert metrics["leg_direction_match_rate"] == 1.0
    assert metrics["breakout_candidate_direction_match_rate"] == 1.0
    assert metrics["consumer_opposite_side_rate"] == 1.0
    assert hints["consumer_veto_tier_hint"] == "FRICTION_ONLY"
    assert hints["caution_discount_candidate"] is True


def test_generate_and_write_window_direction_numeric_audit_writes_artifacts(tmp_path):
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "payload": {
                    "time": "2026-04-15T02:00:00",
                    "symbol": "XAUUSD",
                    "leg_direction": "DOWN",
                    "breakout_candidate_direction": "DOWN",
                    "checkpoint_transition_reason": "checkpoint_continuation",
                    "core_reason": "directional_continuation_overlay_structural_promotion",
                    "box_state": "BELOW",
                    "bb_state": "LOWER_EDGE",
                    "consumer_check_side": "BUY",
                    "consumer_check_reason": "lower_break_fail_confirm",
                    "forecast_state25_candidate_wait_bias_action": "reinforce_wait_bias",
                    "belief_candidate_recommended_family": "reduce_alert",
                    "barrier_candidate_recommended_family": "block_bias",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = generate_and_write_window_direction_numeric_audit(
        detail_path,
        [
            {
                "window_id": "xau_test",
                "symbol": "XAUUSD",
                "label": "XAU continuation sample",
                "expected_direction": "DOWN",
                "start": "2026-04-15T01:59:00",
                "end": "2026-04-15T02:05:00",
            }
        ],
        shadow_auto_dir=tmp_path,
        output_stem="window_direction_numeric_audit_test",
    )

    assert (tmp_path / "window_direction_numeric_audit_test.json").exists()
    assert (tmp_path / "window_direction_numeric_audit_test.md").exists()
    assert result["artifact_paths"]["json_path"].endswith("window_direction_numeric_audit_test.json")
