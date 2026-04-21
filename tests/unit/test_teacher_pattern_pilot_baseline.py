from pathlib import Path

import pandas as pd

from backend.services.teacher_pattern_pilot_baseline import build_teacher_pattern_pilot_baseline_report


def _row(
    index: int,
    *,
    symbol: str,
    group: str,
    pattern_id: int,
    direction: str,
    setup: str,
    entry_wait_quality_label: str = "",
    entry_wait_quality_score: float = 0.0,
    learning_total_label: str = "",
    learning_total_score: float = 0.0,
    loss_quality_label: str = "neutral_loss",
    forecast_transition_outcome_status: str = "",
    forecast_management_outcome_status: str = "",
    belief_outcome_label: str = "",
    belief_label_confidence: str = "",
    belief_anchor_context: str = "",
    belief_break_signature: str = "",
    barrier_outcome_label: str = "",
    barrier_label_confidence: str = "",
    barrier_anchor_context: str = "",
    barrier_primary_component: str = "",
    signed_exit_score: float = 0.0,
) -> dict:
    return {
        "ticket": 1000 + index,
        "symbol": symbol,
        "direction": direction,
        "entry_stage": "READY",
        "entry_setup_id": setup,
        "entry_wait_state": "NONE",
        "regime_at_entry": "NORMAL",
        "entry_session_name": "LONDON",
        "entry_weekday": 2,
        "regime_name": "NORMAL",
        "micro_breakout_readiness_state": "READY_BREAKOUT" if pattern_id in {12, 14} else "QUIET",
        "micro_reversal_risk_state": "HIGH" if pattern_id == 5 else "LOW",
        "micro_participation_state": "ACTIVE" if pattern_id in {12, 14} else "THIN",
        "micro_gap_context_state": "NO_GAP",
        "entry_score": 0.8 if pattern_id in {12, 14} else 0.2,
        "contra_score_at_entry": 0.1 if pattern_id in {12, 14} else 0.7,
        "entry_model_confidence": 0.8,
        "entry_h1_context_score": 0.7,
        "entry_m1_trigger_score": 0.7,
        "entry_topdown_align_count": 3,
        "entry_topdown_conflict_count": 0 if pattern_id in {12, 14} else 2,
        "entry_topdown_seen_count": 3,
        "entry_session_threshold_mult": 1.0,
        "entry_atr_ratio": 1.2 if pattern_id in {12, 14} else 0.8,
        "entry_atr_threshold_mult": 1.0,
        "ind_rsi": 65 if pattern_id in {12, 14} else 45,
        "ind_adx": 28 if pattern_id in {12, 14} else 14,
        "ind_plus_di": 24,
        "ind_minus_di": 18,
        "ind_disparity": 1.1,
        "regime_volume_ratio": 1.8 if pattern_id in {12, 14} else 0.9,
        "regime_volatility_ratio": 1.5 if pattern_id in {12, 14} else 0.8,
        "regime_spread_ratio": 1.0,
        "regime_buy_multiplier": 1.0,
        "regime_sell_multiplier": 1.0,
        "micro_body_size_pct_20": 0.25 if pattern_id in {12, 14} else 0.08,
        "micro_doji_ratio_20": 0.10 if pattern_id in {12, 14} else 0.45,
        "micro_same_color_run_current": 5 if pattern_id in {12, 14} else 1,
        "micro_same_color_run_max_20": 6 if pattern_id in {12, 14} else 2,
        "micro_range_compression_ratio_20": 0.75 if pattern_id in {12, 14} else 0.20,
        "micro_volume_burst_ratio_20": 2.4 if pattern_id in {12, 14} else 1.0,
        "micro_volume_burst_decay_20": 0.20 if pattern_id in {12, 14} else 0.70,
        "micro_gap_fill_progress": None,
        "signal_age_sec": 30,
        "bar_age_sec": 10,
        "missing_feature_count": 0,
        "data_completeness_ratio": 1.0,
        "used_fallback_count": 0,
        "teacher_pattern_id": pattern_id,
        "teacher_pattern_group": group,
        "teacher_pattern_secondary_id": 23 if pattern_id == 12 else 0,
        "teacher_label_confidence": 0.82,
        "teacher_label_source": "rule_v2_backfill",
        "teacher_label_review_status": "backfilled_unreviewed",
        "teacher_lookback_bars": 20,
        "teacher_label_version": "state25_v2",
        "entry_wait_quality_label": entry_wait_quality_label,
        "entry_wait_quality_score": entry_wait_quality_score,
        "entry_wait_quality_reason": "",
        "learning_total_label": learning_total_label,
        "learning_total_score": learning_total_score,
        "loss_quality_label": loss_quality_label,
        "loss_quality_score": 0.0,
        "signed_exit_score": signed_exit_score,
        "forecast_transition_outcome_status": forecast_transition_outcome_status,
        "forecast_management_outcome_status": forecast_management_outcome_status,
        "belief_outcome_label": belief_outcome_label,
        "belief_label_confidence": belief_label_confidence,
        "belief_anchor_context": belief_anchor_context,
        "belief_break_signature": belief_break_signature,
        "barrier_outcome_label": barrier_outcome_label,
        "barrier_label_confidence": barrier_label_confidence,
        "barrier_anchor_context": barrier_anchor_context,
        "barrier_primary_component": barrier_primary_component,
        "profit": 0.0,
    }


def test_teacher_pattern_pilot_baseline_builds_group_and_pattern_tasks(tmp_path: Path):
    rows = []
    for i in range(12):
        rows.append(_row(i, symbol="BTCUSD", group="A", pattern_id=1, direction="BUY", setup="range_idle"))
        rows.append(_row(100 + i, symbol="XAUUSD", group="A", pattern_id=14, direction="BUY", setup="morning_breakout"))
        rows.append(_row(200 + i, symbol="NAS100", group="D", pattern_id=5, direction="SELL", setup="range_reject"))
        rows.append(_row(300 + i, symbol="BTCUSD", group="E", pattern_id=9, direction="BUY", setup="golden_cross"))

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=20,
        pattern_min_support=5,
        output_dir=tmp_path,
    )

    assert report["baseline_ready"] is True
    assert "group_task" in report["tasks"]
    assert report["tasks"]["pattern_task"]["supported_pattern_ids"] == [1, 5, 9, 14]
    assert (tmp_path / "teacher_pattern_pilot_baseline.joblib").exists()
    assert (tmp_path / "teacher_pattern_pilot_baseline_metrics.json").exists()


def test_teacher_pattern_pilot_baseline_marks_shortfall_warning():
    frame = pd.DataFrame([_row(i, symbol="BTCUSD", group="A", pattern_id=1, direction="BUY", setup="range_idle") for i in range(8)])
    report = build_teacher_pattern_pilot_baseline_report(frame, min_seed_rows=20, pattern_min_support=5)

    assert report["baseline_ready"] is False
    assert "pilot_seed_shortfall" in report["baseline_warnings"]


def test_teacher_pattern_pilot_baseline_skips_pattern_task_when_support_too_low():
    rows = []
    for i in range(6):
        rows.append(_row(i, symbol="BTCUSD", group="A", pattern_id=1, direction="BUY", setup="range_idle"))
    for i in range(3):
        rows.append(_row(100 + i, symbol="XAUUSD", group="E", pattern_id=9, direction="BUY", setup="golden_cross"))
    frame = pd.DataFrame(rows)

    report = build_teacher_pattern_pilot_baseline_report(frame, min_seed_rows=5, pattern_min_support=5)

    assert report["tasks"]["pattern_task"]["skipped"] is True
    assert "insufficient_supported_pattern_classes" in report["baseline_warnings"]


def test_teacher_pattern_pilot_baseline_reports_wait_quality_auxiliary_task():
    rows = []
    for i in range(12):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                entry_wait_quality_label="better_entry_after_wait",
                entry_wait_quality_score=0.8,
            )
        )
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
                entry_wait_quality_label="delayed_loss_after_wait",
                entry_wait_quality_score=-0.7,
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        wait_quality_min_support=5,
    )

    assert report["wait_quality_integration"]["mode"] == "auxiliary_target"
    assert report["wait_quality_integration"]["ready"] is True
    assert report["wait_quality_integration"]["supported_labels"] == [
        "better_entry_after_wait",
        "delayed_loss_after_wait",
    ]
    assert report["tasks"]["wait_quality_task"]["skipped"] is False
    assert report["tasks"]["wait_quality_task"]["supported_labels"] == [
        "better_entry_after_wait",
        "delayed_loss_after_wait",
    ]
    assert report["tasks"]["wait_quality_task"]["feature_columns"]["categorical"] == report["feature_columns"]["categorical"]
    assert report["tasks"]["wait_quality_task"]["feature_columns"]["numeric"] == report["feature_columns"]["numeric"]


def test_teacher_pattern_pilot_baseline_wait_quality_integration_stays_non_blocking_when_sparse():
    rows = []
    for i in range(8):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                entry_wait_quality_label="better_entry_after_wait" if i == 0 else "",
                entry_wait_quality_score=0.9 if i == 0 else 0.0,
            )
        )
    for i in range(8):
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        wait_quality_min_support=3,
    )

    assert report["baseline_ready"] is True
    assert report["wait_quality_integration"]["ready"] is False
    assert "insufficient_entry_wait_quality_classes" in report["wait_quality_integration"]["notes"]
    assert report["tasks"]["wait_quality_task"]["skipped"] is True


def test_teacher_pattern_pilot_baseline_reports_economic_auxiliary_task():
    rows = []
    for i in range(12):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                learning_total_label="positive",
                learning_total_score=0.42,
                loss_quality_label="non_loss",
                signed_exit_score=0.42,
            )
        )
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
                learning_total_label="negative",
                learning_total_score=-0.33,
                loss_quality_label="bad_loss",
                signed_exit_score=-0.33,
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        economic_target_min_support=5,
    )

    assert report["economic_target_integration"]["mode"] == "auxiliary_target"
    assert report["economic_target_integration"]["ready"] is True
    assert report["economic_target_integration"]["supported_labels"] == ["negative", "positive"]
    assert report["tasks"]["economic_total_task"]["skipped"] is False
    assert report["tasks"]["economic_total_task"]["supported_labels"] == ["negative", "positive"]


def test_teacher_pattern_pilot_baseline_economic_integration_stays_non_blocking_when_sparse():
    rows = []
    for i in range(8):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                learning_total_label="positive" if i == 0 else "",
                learning_total_score=0.51 if i == 0 else 0.0,
                loss_quality_label="non_loss" if i == 0 else "neutral_loss",
                signed_exit_score=0.51 if i == 0 else 0.0,
            )
        )
    for i in range(8):
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        economic_target_min_support=3,
    )

    assert report["baseline_ready"] is True
    assert report["economic_target_integration"]["ready"] is False
    assert "insufficient_learning_total_classes" in report["economic_target_integration"]["notes"]
    assert report["tasks"]["economic_total_task"]["skipped"] is True


def test_teacher_pattern_pilot_baseline_reports_forecast_auxiliary_tasks():
    rows = []
    for i in range(12):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                forecast_transition_outcome_status="confirm_success",
                forecast_management_outcome_status="hold_rewarded",
            )
        )
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
                forecast_transition_outcome_status="confirm_failed",
                forecast_management_outcome_status="cut_was_better",
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        forecast_outcome_min_support=5,
    )

    assert report["forecast_transition_integration"]["mode"] == "auxiliary_target"
    assert report["forecast_transition_integration"]["ready"] is True
    assert report["forecast_transition_integration"]["supported_labels"] == [
        "confirm_failed",
        "confirm_success",
    ]
    assert report["tasks"]["forecast_transition_task"]["skipped"] is False
    assert report["tasks"]["forecast_transition_task"]["supported_labels"] == [
        "confirm_failed",
        "confirm_success",
    ]
    assert report["forecast_management_integration"]["mode"] == "auxiliary_target"
    assert report["forecast_management_integration"]["ready"] is True
    assert report["forecast_management_integration"]["supported_labels"] == [
        "cut_was_better",
        "hold_rewarded",
    ]
    assert report["tasks"]["forecast_management_task"]["skipped"] is False
    assert report["tasks"]["forecast_management_task"]["supported_labels"] == [
        "cut_was_better",
        "hold_rewarded",
    ]
    assert report["tasks"]["forecast_transition_task"]["feature_columns"]["categorical"] == report["feature_columns"]["categorical"]
    assert report["tasks"]["forecast_management_task"]["feature_columns"]["numeric"] == report["feature_columns"]["numeric"]


def test_teacher_pattern_pilot_baseline_forecast_integration_stays_non_blocking_when_sparse():
    rows = []
    for i in range(8):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                forecast_transition_outcome_status="confirm_success" if i == 0 else "insufficient_future_bars",
                forecast_management_outcome_status="hold_rewarded" if i == 0 else "",
            )
        )
    for i in range(8):
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        forecast_outcome_min_support=3,
    )

    assert report["baseline_ready"] is True
    assert report["forecast_transition_integration"]["ready"] is False
    assert "insufficient_forecast_transition_classes" in report["forecast_transition_integration"]["notes"]
    assert report["tasks"]["forecast_transition_task"]["skipped"] is True
    assert report["forecast_management_integration"]["ready"] is False
    assert "insufficient_forecast_management_classes" in report["forecast_management_integration"]["notes"]
    assert report["tasks"]["forecast_management_task"]["skipped"] is True


def test_teacher_pattern_pilot_baseline_reports_belief_auxiliary_task():
    rows = []
    for i in range(20):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                belief_outcome_label="correct_hold",
                belief_label_confidence="high",
                belief_anchor_context="hold_thesis",
                belief_break_signature="thesis_persistence_valid",
            )
        )
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
                belief_outcome_label="wrong_hold",
                belief_label_confidence="medium",
                belief_anchor_context="hold_thesis",
                belief_break_signature="belief_decay_hold_failure",
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        belief_outcome_min_support=8,
        belief_outcome_min_rows=40,
    )

    assert report["belief_outcome_integration"]["mode"] == "auxiliary_target"
    assert report["belief_outcome_integration"]["ready"] is True
    assert report["belief_outcome_integration"]["supported_labels"] == ["correct_hold", "wrong_hold"]
    assert report["belief_outcome_integration"]["high_medium_confidence_rows"] == 40
    assert report["tasks"]["belief_outcome_task"]["skipped"] is False
    assert report["tasks"]["belief_outcome_task"]["supported_labels"] == ["correct_hold", "wrong_hold"]
    assert report["tasks"]["belief_outcome_task"]["feature_columns"]["categorical"] == report["feature_columns"]["categorical"]
    assert report["tasks"]["belief_outcome_task"]["feature_columns"]["numeric"] == report["feature_columns"]["numeric"]


def test_teacher_pattern_pilot_baseline_belief_integration_stays_non_blocking_when_sparse():
    rows = []
    for i in range(16):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                belief_outcome_label="correct_hold",
                belief_label_confidence="high",
                belief_anchor_context="hold_thesis",
                belief_break_signature="thesis_persistence_valid",
            )
        )
    for i in range(8):
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
                belief_outcome_label="wrong_hold" if i == 0 else "",
                belief_label_confidence="medium" if i == 0 else "",
                belief_anchor_context="hold_thesis" if i == 0 else "",
                belief_break_signature="belief_decay_hold_failure" if i == 0 else "",
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        belief_outcome_min_support=8,
        belief_outcome_min_rows=40,
    )

    assert report["baseline_ready"] is True
    assert report["belief_outcome_integration"]["ready"] is False
    assert "insufficient_belief_high_medium_rows" in report["belief_outcome_integration"]["notes"]
    assert report["tasks"]["belief_outcome_task"]["skipped"] is True


def test_teacher_pattern_pilot_baseline_reports_barrier_auxiliary_task():
    rows = []
    for i in range(20):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                barrier_outcome_label="avoided_loss",
                barrier_label_confidence="high",
                barrier_anchor_context="blocked_entry",
                barrier_primary_component="late_entry_barrier",
            )
        )
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
                barrier_outcome_label="overblock",
                barrier_label_confidence="medium",
                barrier_anchor_context="blocked_entry",
                barrier_primary_component="middle_chop_barrier",
            )
        )
    for i in range(4):
        rows.append(
            _row(
                200 + i,
                symbol="XAUUSD",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
                barrier_outcome_label="overblock",
                barrier_label_confidence="weak_usable",
                barrier_anchor_context="blocked_entry",
                barrier_primary_component="middle_chop_barrier",
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        barrier_outcome_min_support=8,
        barrier_outcome_min_rows=40,
    )

    assert report["barrier_outcome_integration"]["mode"] == "auxiliary_target"
    assert report["barrier_outcome_integration"]["ready"] is True
    assert report["barrier_outcome_integration"]["supported_labels"] == ["avoided_loss", "overblock"]
    assert report["barrier_outcome_integration"]["high_medium_confidence_rows"] == 40
    assert report["barrier_outcome_integration"]["usable_confidence_rows"] == 44
    assert report["barrier_outcome_integration"]["weak_usable_rows"] == 4
    assert report["barrier_outcome_integration"]["weak_usable_share"] == 0.090909
    assert report["barrier_outcome_integration"]["weak_to_medium_conversion_rate"] == 0.909091
    assert report["tasks"]["barrier_outcome_task"]["skipped"] is False
    assert report["tasks"]["barrier_outcome_task"]["rows"] == 44
    assert report["tasks"]["barrier_outcome_task"]["usable_confidence_rows"] == 44
    assert report["tasks"]["barrier_outcome_task"]["supported_labels"] == ["avoided_loss", "overblock"]
    assert report["tasks"]["barrier_outcome_task"]["feature_columns"]["categorical"] == report["feature_columns"]["categorical"]
    assert report["tasks"]["barrier_outcome_task"]["feature_columns"]["numeric"] == report["feature_columns"]["numeric"]


def test_teacher_pattern_pilot_baseline_barrier_integration_stays_non_blocking_when_sparse():
    rows = []
    for i in range(16):
        rows.append(
            _row(
                i,
                symbol="BTCUSD",
                group="A",
                pattern_id=1,
                direction="BUY",
                setup="range_idle",
                barrier_outcome_label="avoided_loss",
                barrier_label_confidence="high",
                barrier_anchor_context="blocked_entry",
                barrier_primary_component="late_entry_barrier",
            )
        )
    for i in range(8):
        rows.append(
            _row(
                100 + i,
                symbol="NAS100",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
                barrier_outcome_label="overblock" if i == 0 else "",
                barrier_label_confidence="medium" if i == 0 else "",
                barrier_anchor_context="blocked_entry" if i == 0 else "",
                barrier_primary_component="middle_chop_barrier" if i == 0 else "",
            )
        )
    for i in range(6):
        rows.append(
            _row(
                200 + i,
                symbol="XAUUSD",
                group="D",
                pattern_id=5,
                direction="SELL",
                setup="range_reject",
                barrier_outcome_label="overblock",
                barrier_label_confidence="weak_usable",
                barrier_anchor_context="blocked_entry",
                barrier_primary_component="middle_chop_barrier",
            )
        )

    frame = pd.DataFrame(rows)
    report = build_teacher_pattern_pilot_baseline_report(
        frame,
        min_seed_rows=10,
        pattern_min_support=5,
        barrier_outcome_min_support=8,
        barrier_outcome_min_rows=40,
    )

    assert report["baseline_ready"] is True
    assert report["barrier_outcome_integration"]["ready"] is False
    assert report["barrier_outcome_integration"]["usable_confidence_rows"] == 23
    assert report["barrier_outcome_integration"]["weak_usable_rows"] == 6
    assert "insufficient_barrier_high_medium_rows" in report["barrier_outcome_integration"]["notes"]
    assert report["tasks"]["barrier_outcome_task"]["skipped"] is True
    assert report["tasks"]["barrier_outcome_task"]["usable_confidence_rows"] == 23
