import pandas as pd

from backend.services.teacher_pattern_experiment_seed import build_teacher_pattern_experiment_seed_report


def _row(**overrides):
    row = {
        "symbol": "BTCUSD",
        "teacher_pattern_id": 12,
        "teacher_pattern_group": "C",
        "teacher_pattern_secondary_id": 23,
        "teacher_entry_bias": "breakout",
        "teacher_wait_bias": "short_wait",
        "teacher_exit_bias": "hold_runner",
        "teacher_label_confidence": 0.82,
        "teacher_label_source": "rule_v2_backfill",
        "teacher_label_review_status": "backfilled_unreviewed",
        "teacher_lookback_bars": 20,
        "teacher_label_version": "state25_v2",
        "entry_wait_quality_label": "",
        "entry_wait_quality_score": 0.0,
        "entry_wait_quality_reason": "",
        "loss_quality_label": "neutral_loss",
        "loss_quality_score": 0.0,
        "signed_exit_score": 0.0,
        "learning_total_score": 0.0,
        "learning_total_label": "",
        "profit": 0.0,
    }
    row.update(overrides)
    return row


def test_teacher_pattern_experiment_seed_report_marks_ready_when_seed_threshold_met():
    frame = pd.DataFrame(
        [
            _row(symbol="BTCUSD", teacher_pattern_id=12, teacher_pattern_group="C"),
            _row(symbol="XAUUSD", teacher_pattern_id=14, teacher_pattern_group="A", teacher_pattern_secondary_id=0, teacher_entry_bias="breakout", teacher_wait_bias="short_wait", teacher_exit_bias="range_take", teacher_label_confidence=0.65),
            _row(symbol="NAS100", teacher_pattern_id=9, teacher_pattern_group="E", teacher_pattern_secondary_id=0, teacher_entry_bias="early", teacher_wait_bias="hold", teacher_exit_bias="hold_runner", teacher_label_confidence=0.71),
        ]
    )

    report = build_teacher_pattern_experiment_seed_report(frame, min_seed_rows=3)

    assert report["seed_readiness"]["seed_ready"] is True
    assert report["seed_readiness"]["shortfall_rows"] == 0
    assert report["symbol_distribution"]["BTCUSD"]["count"] == 1
    assert report["pattern_distribution"][12]["count"] == 1
    assert report["group_distribution"]["C"]["count"] == 1
    assert report["source_distribution"]["rule_v2_backfill"]["count"] == 3
    assert report["entry_wait_quality_coverage"]["rows_with_entry_wait_quality"] == 0


def test_teacher_pattern_experiment_seed_report_reports_shortfall():
    frame = pd.DataFrame(
        [
            _row(symbol="BTCUSD", teacher_pattern_id=1, teacher_pattern_group="A", teacher_pattern_secondary_id=0, teacher_entry_bias="avoid", teacher_wait_bias="wait", teacher_exit_bias="range_take", teacher_label_confidence=0.65),
            _row(symbol="BTCUSD", teacher_pattern_id=14, teacher_pattern_group="A", teacher_pattern_secondary_id=0, teacher_entry_bias="breakout", teacher_wait_bias="short_wait", teacher_exit_bias="range_take", teacher_label_confidence=0.61),
        ]
    )

    report = build_teacher_pattern_experiment_seed_report(frame, min_seed_rows=5)

    assert report["seed_readiness"]["seed_ready"] is False
    assert report["seed_readiness"]["shortfall_rows"] == 3
    assert report["seed_readiness"]["recommended_split"]["train"] == 1
    assert report["seed_readiness"]["recommended_split"]["val"] == 0
    assert report["seed_readiness"]["recommended_split"]["test"] == 1


def test_teacher_pattern_experiment_seed_report_includes_entry_wait_quality_coverage():
    frame = pd.DataFrame(
        [
            _row(entry_wait_quality_label="better_entry_after_wait", entry_wait_quality_score=0.82),
            _row(symbol="XAUUSD", teacher_pattern_id=14, teacher_pattern_group="A", entry_wait_quality_label="neutral_wait", entry_wait_quality_score=0.0),
            _row(symbol="NAS100", teacher_pattern_id=9, teacher_pattern_group="E", entry_wait_quality_label="insufficient_evidence", entry_wait_quality_score=0.0),
        ]
    )

    report = build_teacher_pattern_experiment_seed_report(frame, min_seed_rows=1)

    assert report["entry_wait_quality_distribution"]["better_entry_after_wait"]["count"] == 1
    assert report["entry_wait_quality_distribution"]["neutral_wait"]["count"] == 1
    assert report["entry_wait_quality_distribution"]["insufficient_evidence"]["count"] == 1
    assert report["entry_wait_quality_coverage"]["rows_with_entry_wait_quality"] == 3
    assert report["entry_wait_quality_coverage"]["valid_rows"] == 2
    assert report["entry_wait_quality_coverage"]["positive_rows"] == 1
    assert report["entry_wait_quality_coverage"]["negative_rows"] == 0
    assert report["entry_wait_quality_coverage"]["insufficient_rows"] == 1


def test_teacher_pattern_experiment_seed_report_includes_economic_target_summary():
    frame = pd.DataFrame(
        [
            _row(learning_total_label="positive", learning_total_score=0.62, signed_exit_score=44.0, exit_score=44.0, profit=3.2, loss_quality_label="non_loss"),
            _row(symbol="XAUUSD", teacher_pattern_id=14, teacher_pattern_group="A", learning_total_label="positive", learning_total_score=0.31, signed_exit_score=18.0, exit_score=18.0, profit=1.1, loss_quality_label="non_loss"),
            _row(symbol="NAS100", teacher_pattern_id=9, teacher_pattern_group="E", learning_total_label="negative", learning_total_score=-0.38, signed_exit_score=-52.0, exit_score=52.0, profit=-4.0, loss_quality_label="bad_loss"),
        ]
    )

    report = build_teacher_pattern_experiment_seed_report(frame, min_seed_rows=1)

    economic = report["economic_target_summary"]
    assert economic["primary_target"]["target_rows"] == 3
    assert economic["primary_target"]["distribution"]["positive"]["count"] == 2
    assert economic["primary_target"]["distribution"]["negative"]["count"] == 1
    assert economic["secondary_targets"]["loss_quality_label"]["distribution"]["non_loss"]["count"] == 2
    assert economic["coverage"]["rows_with_nonzero_signed_exit_score"] == 3


def test_teacher_pattern_experiment_seed_report_includes_forecast_state25_coverage():
    frame = pd.DataFrame(
        [
            _row(
                forecast_state25_scene_family="pattern_12",
                forecast_state25_group_hint="C",
                forecast_confirm_side="BUY",
                forecast_decision_hint="CONFIRM_BIASED",
                forecast_wait_confirm_gap=0.21,
                forecast_hold_exit_gap=0.16,
                forecast_same_side_flip_gap=0.07,
                forecast_belief_barrier_tension_gap=0.11,
                forecast_transition_outcome_status="valid",
                forecast_management_outcome_status="valid",
                forecast_state25_bridge_quality_status="full_outcome_bridge",
            ),
            _row(
                symbol="XAUUSD",
                teacher_pattern_id=14,
                teacher_pattern_group="A",
                forecast_state25_scene_family="pattern_14",
                forecast_state25_group_hint="A",
                forecast_confirm_side="SELL",
                forecast_decision_hint="WAIT_BIASED",
                forecast_wait_confirm_gap=-0.18,
                forecast_hold_exit_gap=-0.04,
                forecast_same_side_flip_gap=-0.02,
                forecast_belief_barrier_tension_gap=-0.05,
                forecast_transition_outcome_status="insufficient_future_bars",
                forecast_management_outcome_status="valid",
                forecast_state25_bridge_quality_status="partial_outcome_bridge",
            ),
            _row(symbol="NAS100", teacher_pattern_id=9, teacher_pattern_group="E"),
        ]
    )

    report = build_teacher_pattern_experiment_seed_report(frame, min_seed_rows=1)

    coverage = report["forecast_state25_coverage"]
    assert coverage["rows_with_forecast_state25_total"] == 2
    assert coverage["rows_with_forecast_state25"] == 2
    assert coverage["valid_transition_rows"] == 1
    assert coverage["valid_management_rows"] == 2
    assert coverage["scene_family_distribution"]["pattern_12"]["count"] == 1
    assert coverage["decision_hint_distribution"]["WAIT_BIASED"]["count"] == 1
    assert coverage["bridge_quality_status_distribution"]["full_outcome_bridge"]["count"] == 1


def test_teacher_pattern_experiment_seed_report_includes_belief_outcome_coverage():
    frame = pd.DataFrame(
        [
            _row(
                belief_anchor_side="BUY",
                belief_anchor_context="hold_thesis",
                belief_horizon_bars=6,
                belief_outcome_label="correct_hold",
                belief_label_confidence="high",
                belief_break_signature="thesis_persistence_valid",
                belief_bridge_quality_status="labeled",
            ),
            _row(
                symbol="XAUUSD",
                teacher_pattern_id=14,
                teacher_pattern_group="A",
                belief_anchor_side="SELL",
                belief_anchor_context="flip_thesis",
                belief_horizon_bars=6,
                belief_outcome_label="premature_flip",
                belief_label_confidence="low",
                belief_break_signature="flip_reclaim_failure",
                belief_bridge_quality_status="labeled",
            ),
            _row(symbol="NAS100", teacher_pattern_id=9, teacher_pattern_group="E"),
        ]
    )

    report = build_teacher_pattern_experiment_seed_report(frame, min_seed_rows=1)

    coverage = report["belief_outcome_coverage"]
    assert coverage["rows_with_belief_outcome_total"] == 2
    assert coverage["rows_with_belief_outcome"] == 2
    assert coverage["high_or_medium_confidence_rows"] == 1
    assert coverage["label_distribution"]["correct_hold"]["count"] == 1
    assert coverage["confidence_distribution"]["low"]["count"] == 1
    assert coverage["anchor_context_distribution"]["hold_thesis"]["count"] == 1


def test_teacher_pattern_experiment_seed_report_includes_barrier_outcome_coverage():
    frame = pd.DataFrame(
        [
            _row(
                barrier_anchor_side="BUY",
                barrier_anchor_context="blocked_entry",
                barrier_horizon_bars=6,
                barrier_primary_component="late_entry_barrier",
                barrier_outcome_label="avoided_loss",
                barrier_label_confidence="high",
                barrier_bridge_quality_status="labeled",
                barrier_cost_loss_avoided_r=1.2,
                barrier_cost_profit_missed_r=0.1,
                barrier_cost_wait_value_r=0.3,
            ),
            _row(
                symbol="XAUUSD",
                teacher_pattern_id=14,
                teacher_pattern_group="A",
                barrier_anchor_side="SELL",
                barrier_anchor_context="relief_release",
                barrier_horizon_bars=6,
                barrier_primary_component="conflict_barrier",
                barrier_outcome_label="relief_success",
                barrier_label_confidence="weak_usable",
                barrier_bridge_quality_status="weak_usable",
                barrier_cost_loss_avoided_r=0.2,
                barrier_cost_profit_missed_r=0.5,
                barrier_cost_wait_value_r=0.7,
            ),
            _row(
                symbol="NAS100",
                teacher_pattern_id=9,
                teacher_pattern_group="E",
                barrier_anchor_side="BUY",
                barrier_anchor_context="blocked_entry",
                barrier_horizon_bars=6,
                barrier_primary_component="middle_chop_barrier",
                barrier_outcome_label="overblock",
                barrier_label_confidence="low_skip",
                barrier_bridge_quality_status="skip",
                barrier_cost_loss_avoided_r=0.3,
                barrier_cost_profit_missed_r=0.3,
                barrier_cost_wait_value_r=0.5,
            ),
            _row(symbol="NAS100", teacher_pattern_id=9, teacher_pattern_group="E"),
        ]
    )

    report = build_teacher_pattern_experiment_seed_report(frame, min_seed_rows=1)

    coverage = report["barrier_outcome_coverage"]
    assert coverage["rows_with_barrier_outcome_total"] == 3
    assert coverage["rows_with_barrier_outcome"] == 3
    assert coverage["high_or_medium_confidence_rows"] == 1
    assert coverage["usable_confidence_rows"] == 2
    assert coverage["weak_usable_rows"] == 1
    assert coverage["weak_usable_share"] == 0.5
    assert coverage["weak_to_medium_conversion_rate"] == 0.5
    assert coverage["label_distribution"]["avoided_loss"]["count"] == 1
    assert coverage["confidence_distribution"]["low_skip"]["count"] == 1
    assert coverage["anchor_context_distribution"]["blocked_entry"]["count"] == 2
    assert coverage["primary_component_distribution"]["conflict_barrier"]["count"] == 1
    assert coverage["loss_avoided_r_mean"] == 0.5666666666666667
    assert coverage["profit_missed_r_mean"] == 0.3
    assert coverage["wait_value_r_mean"] == 0.5
