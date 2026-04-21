import json

from backend.services.flow_shadow_display_surface import (
    attach_flow_shadow_display_surface_fields_v1,
    build_flow_shadow_display_surface_contract_v1,
    build_flow_shadow_display_surface_summary_v1,
    generate_and_write_flow_shadow_display_surface_summary_v1,
)


def test_flow_shadow_display_surface_contract_exposes_expected_fields():
    contract = build_flow_shadow_display_surface_contract_v1()

    assert contract["contract_version"] == "flow_shadow_display_surface_contract_v1"
    assert "flow_shadow_continuation_persistence_prob_v1" in contract["row_level_fields_v1"]
    assert "flow_shadow_entry_quality_prob_v1" in contract["row_level_fields_v1"]
    assert "flow_shadow_reversal_risk_prob_v1" in contract["row_level_fields_v1"]
    assert "flow_shadow_entry_zone_state_v1" in contract["row_level_fields_v1"]
    assert "flow_shadow_chart_event_final_kind_v1" in contract["row_level_fields_v1"]
    assert "flow_shadow_chart_event_emit_v1" in contract["row_level_fields_v1"]
    assert "flow_shadow_chart_event_emit_state_v1" in contract["row_level_fields_v1"]
    assert "flow_shadow_start_marker_event_kind_v1" in contract["row_level_fields_v1"]


def test_attach_flow_shadow_display_surface_fields_adds_shadow_axes_and_fallback_marker():
    rows = attach_flow_shadow_display_surface_fields_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "action": "BUY",
                "consumer_check_side": "BUY",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_reason": "lower_rebound_probe_observe",
                "flow_support_state_v1": "FLOW_OPPOSED",
                "flow_structure_gate_v1": "INELIGIBLE",
                "aggregate_conviction_v1": 0.0,
                "flow_persistence_v1": 0.26,
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
                "nas_btc_hard_opposed_truth_audit_state_v1": "MIXED_REVIEW",
                "bounded_candidate_feedback_loop_action_v1": "KEEP_REVIEW",
                "chart_event_kind_hint": "",
            },
            "NAS100": {
                "symbol": "NAS100",
                "action": "BUY",
                "consumer_check_side": "SELL",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_reason": "outer_band_reversal_support_required_observe",
                "flow_support_state_v1": "FLOW_OPPOSED",
                "flow_structure_gate_v1": "INELIGIBLE",
                "aggregate_conviction_v1": 0.0,
                "flow_persistence_v1": 0.24,
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
                "nas_btc_hard_opposed_truth_audit_state_v1": "MIXED_REVIEW",
                "bounded_candidate_feedback_loop_action_v1": "KEEP_REVIEW",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_side": "BUY",
                "directional_continuation_overlay_score": 0.64,
                "chart_event_kind_hint": "BUY_WATCH",
            },
        }
    )

    btc = rows["BTCUSD"]
    nas = rows["NAS100"]

    assert btc["flow_shadow_continuation_persistence_prob_v1"] >= 0.29
    assert btc["flow_shadow_entry_quality_prob_v1"] >= 0.0
    assert btc["flow_shadow_reversal_risk_prob_v1"] > 0.30
    assert btc["flow_shadow_start_marker_state_v1"] == "FALLBACK_START_WATCH"
    assert btc["flow_shadow_start_marker_event_kind_v1"] == "BUY_WATCH"
    assert btc["chart_event_kind_hint"] == "BUY_WATCH"

    assert nas["flow_shadow_direction_v1"] == "BUY"
    assert nas["flow_shadow_start_marker_state_v1"] == "EXISTING_WATCH"
    assert nas["flow_shadow_entry_zone_state_v1"] == "OPPOSITE_EDGE_CHASE"
    assert nas["flow_shadow_chart_event_override_state_v1"] == "OVERRIDDEN_TO_WAIT"
    assert nas["flow_shadow_chart_event_emit_v1"] is True
    assert nas["flow_shadow_chart_event_emit_state_v1"] == "TURN_WAIT"
    assert nas["chart_event_kind_hint"] == "BUY_WAIT"


def test_attach_flow_shadow_display_surface_fields_promotes_clean_breakout_watch_to_probe():
    rows = attach_flow_shadow_display_surface_fields_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "action": "BUY",
                "consumer_check_side": "BUY",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_reason": "breakout_probe_observe",
                "flow_support_state_v1": "FLOW_BUILDING",
                "flow_structure_gate_v1": "WEAK",
                "aggregate_conviction_v1": 0.41,
                "flow_persistence_v1": 0.72,
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
                "bounded_candidate_feedback_loop_action_v1": "KEEP_SHADOW",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_side": "BUY",
                "directional_continuation_overlay_direction": "UP",
                "directional_continuation_overlay_score": 0.88,
                "chart_event_kind_hint": "BUY_WATCH",
                "box_state": "MIDDLE",
                "position_snapshot_v2": json.dumps(
                    {
                        "zones": {
                            "box_zone": "MIDDLE",
                            "bb20_zone": "MIDDLE",
                            "bb44_zone": "MIDDLE",
                        }
                    }
                ),
                "previous_box_break_state": "BREAKOUT_HELD",
                "previous_box_relation": "ABOVE",
                "breakout_candidate_direction": "UP",
                "breakout_candidate_action_target": "PROBE_BREAKOUT",
                "late_chase_risk_state": "NONE",
            }
        }
    )

    nas = rows["NAS100"]
    assert nas["flow_shadow_entry_zone_state_v1"] == "BREAKOUT_CONTINUATION"
    assert nas["flow_shadow_chart_event_override_state_v1"] == "OVERRIDDEN_TO_PROBE"
    assert nas["flow_shadow_chart_event_emit_v1"] is True
    assert nas["flow_shadow_chart_event_emit_state_v1"] == "BREAKOUT_PROBE"
    assert nas["chart_event_kind_hint"] == "BUY_PROBE"
    assert nas["flow_shadow_entry_quality_prob_v1"] >= 0.24


def test_attach_flow_shadow_display_surface_emits_existing_probe_as_point_check():
    rows = attach_flow_shadow_display_surface_fields_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "action": "SELL",
                "consumer_check_side": "SELL",
                "consumer_check_stage": "PROBE",
                "consumer_check_reason": "upper_reject_probe_observe",
                "flow_support_state_v1": "FLOW_BUILDING",
                "flow_structure_gate_v1": "WEAK",
                "aggregate_conviction_v1": 0.34,
                "flow_persistence_v1": 0.55,
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_side": "SELL",
                "directional_continuation_overlay_direction": "DOWN",
                "directional_continuation_overlay_score": 0.60,
                "chart_event_kind_hint": "SELL_PROBE",
                "position_snapshot_v2": json.dumps(
                    {
                        "zones": {
                            "box_zone": "UPPER",
                            "bb20_zone": "UPPER",
                            "bb44_zone": "MIDDLE",
                        }
                    }
                ),
                "box_state": "UPPER",
                "bb_state": "UPPER",
                "late_chase_risk_state": "NONE",
            }
        }
    )

    btc = rows["BTCUSD"]
    assert btc["chart_event_kind_hint"] == "SELL_PROBE"
    assert btc["flow_shadow_chart_event_emit_v1"] is True
    assert btc["flow_shadow_chart_event_emit_state_v1"] == "POINT_CHECK"


def test_attach_flow_shadow_display_surface_suppresses_generic_existing_watch_without_point_trigger():
    rows = attach_flow_shadow_display_surface_fields_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "action": "BUY",
                "consumer_check_side": "BUY",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_reason": "middle_sr_anchor_required_observe",
                "flow_support_state_v1": "FLOW_UNCONFIRMED",
                "flow_structure_gate_v1": "INELIGIBLE",
                "aggregate_conviction_v1": 0.06,
                "flow_persistence_v1": 0.31,
                "flow_candidate_truth_state_v1": "REVIEW_PENDING",
                "flow_candidate_improvement_verdict_v1": "REVIEW_PENDING",
                "bounded_candidate_feedback_loop_action_v1": "KEEP_REVIEW",
                "chart_event_kind_hint": "BUY_WATCH",
                "position_snapshot_v2": json.dumps(
                    {
                        "zones": {
                            "box_zone": "MIDDLE",
                            "bb20_zone": "UPPER",
                            "bb44_zone": "MIDDLE",
                        }
                    }
                ),
                "box_state": "MIDDLE",
                "previous_box_break_state": "INSIDE",
                "previous_box_relation": "INSIDE",
                "late_chase_risk_state": "NONE",
            }
        }
    )

    btc = rows["BTCUSD"]
    assert btc["flow_shadow_chart_event_emit_v1"] is False
    assert btc["flow_shadow_chart_event_emit_state_v1"] == "SUPPRESSED"


def test_attach_flow_shadow_display_surface_suppresses_wait_emit_when_turn_signal_is_not_specific_enough():
    rows = attach_flow_shadow_display_surface_fields_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "action": "BUY",
                "consumer_check_side": "SELL",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_reason": "outer_band_reversal_support_required_observe",
                "flow_support_state_v1": "FLOW_OPPOSED",
                "flow_structure_gate_v1": "INELIGIBLE",
                "aggregate_conviction_v1": 0.0,
                "flow_persistence_v1": 0.01,
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
                "nas_btc_hard_opposed_truth_audit_state_v1": "FIXED_HARD_OPPOSED",
                "bounded_candidate_feedback_loop_action_v1": "KEEP_REVIEW",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_side": "BUY",
                "directional_continuation_overlay_direction": "UP",
                "directional_continuation_overlay_score": 0.55,
                "chart_event_kind_hint": "BUY_WATCH",
                "box_state": "UPPER",
                "late_chase_risk_state": "HIGH",
            }
        }
    )

    nas = rows["NAS100"]
    assert nas["chart_event_kind_hint"] == "BUY_WAIT"
    assert nas["flow_shadow_chart_event_emit_v1"] is False
    assert nas["flow_shadow_chart_event_emit_state_v1"] == "SUPPRESSED"


def test_attach_flow_shadow_display_surface_prefers_consumer_wait_over_weak_opposite_overlay():
    rows = attach_flow_shadow_display_surface_fields_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "consumer_check_side": "BUY",
                "consumer_check_stage": "PROBE",
                "consumer_check_reason": "lower_rebound_probe_observe",
                "consumer_check_state_v1": {
                    "check_side": "BUY",
                    "check_stage": "PROBE",
                    "entry_ready": False,
                    "chart_event_kind_hint": "WAIT",
                    "chart_display_reason": "btc_lower_probe_promotion_wait_as_wait_checks",
                },
                "flow_support_state_v1": "FLOW_UNCONFIRMED",
                "flow_structure_gate_v1": "INELIGIBLE",
                "aggregate_conviction_v1": 0.0,
                "flow_persistence_v1": 0.28,
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_improvement_verdict_v1": "MISSED_IMPROVEMENT",
                "bounded_candidate_feedback_loop_action_v1": "KEEP_SHADOW",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_side": "SELL",
                "directional_continuation_overlay_score": 0.48,
                "chart_event_kind_hint": "SELL_WATCH",
                "position_snapshot_v2": json.dumps(
                    {
                        "zones": {
                            "box_zone": "BELOW",
                            "bb20_zone": "LOWER_EDGE",
                            "bb44_zone": "MIDDLE",
                        }
                    }
                ),
                "box_state": "BELOW",
                "bb_state": "LOWER_EDGE",
                "previous_box_break_state": "BREAKDOWN_HELD",
                "previous_box_relation": "BELOW",
                "breakout_candidate_direction": "UP",
                "breakout_candidate_action_target": "PROBE_BREAKOUT",
            }
        }
    )

    btc = rows["BTCUSD"]
    assert btc["flow_shadow_direction_v1"] == "BUY"
    assert btc["flow_shadow_direction_source_v1"] == "CONSUMER_WAIT_OVERRIDE"
    assert btc["chart_event_kind_hint"] == "BUY_WAIT"
    assert "consumer_wait=BUY_WAIT" in btc["flow_shadow_display_reason_summary_v1"]


def test_build_flow_shadow_display_surface_summary_counts_marker_states():
    report = build_flow_shadow_display_surface_summary_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "action": "BUY",
                "consumer_check_side": "BUY",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_reason": "lower_rebound_probe_observe",
                "flow_support_state_v1": "FLOW_OPPOSED",
                "flow_structure_gate_v1": "INELIGIBLE",
                "aggregate_conviction_v1": 0.0,
                "flow_persistence_v1": 0.26,
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
                "nas_btc_hard_opposed_truth_audit_state_v1": "MIXED_REVIEW",
                "bounded_candidate_feedback_loop_action_v1": "KEEP_REVIEW",
            }
        }
    )

    summary = report["summary"]
    assert summary["status"] == "READY"
    assert summary["symbol_count"] == 1
    assert "FALLBACK_START_WATCH" in summary["flow_shadow_marker_state_count_summary"]
    assert "FAVORABLE_EDGE" in summary["flow_shadow_entry_zone_state_count_summary"]


def test_generate_and_write_flow_shadow_display_surface_summary(tmp_path):
    report = generate_and_write_flow_shadow_display_surface_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "action": "BUY",
                "consumer_check_side": "BUY",
                "consumer_check_stage": "BLOCKED",
                "consumer_check_reason": "lower_rebound_probe_observe",
                "flow_support_state_v1": "FLOW_OPPOSED",
                "flow_structure_gate_v1": "INELIGIBLE",
                "aggregate_conviction_v1": 0.0,
                "flow_persistence_v1": 0.18,
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
                "bounded_candidate_feedback_loop_action_v1": "KEEP_REVIEW",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    assert report["summary"]["symbol_count"] == 1
    assert report["artifact_paths"]["json_path"].endswith("flow_shadow_display_surface_latest.json")
    saved = json.loads((tmp_path / "flow_shadow_display_surface_latest.json").read_text(encoding="utf-8"))
    assert saved["summary"]["status"] == "READY"
