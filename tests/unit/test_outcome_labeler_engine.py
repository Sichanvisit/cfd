import json

from backend.trading.engine.offline.outcome_labeler import (
    build_outcome_labels,
    build_outcome_label_shadow_row,
    label_management_outcomes,
    label_transition_outcomes,
    write_outcome_label_shadow_output,
)


def test_build_outcome_labels_generates_bundle_for_single_decision_row():
    decision_row = {
        "ticket": 7001,
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 100.0,
        "signal_timeframe": "15M",
        "symbol": "NAS100",
        "action": "BUY",
        "setup_id": "range_lower_reversal_buy",
        "setup_side": "BUY",
        "transition_forecast_v1": '{"p_buy_confirm":0.72}',
        "trade_management_forecast_v1": '{"p_continue_favor":0.61}',
        "forecast_gap_metrics_v1": '{"management_continue_fail_gap":0.21,"transition_confirm_fake_gap":0.18}',
    }
    future_bars = [
        {"time": 101, "open": 100.0, "high": 101.2, "low": 99.9, "close": 101.0},
        {"time": 102, "open": 101.0, "high": 101.6, "low": 100.8, "close": 101.5},
        {"time": 103, "open": 101.5, "high": 102.0, "low": 101.2, "close": 101.8},
        {"time": 104, "open": 101.8, "high": 102.1, "low": 101.6, "close": 101.9},
    ]
    closed_rows = [
        {
            "ticket": 7001,
            "symbol": "NAS100",
            "direction": "BUY",
            "open_ts": 101,
            "open_price": 100.0,
            "close_ts": 104,
            "close_price": 101.8,
            "profit": 0.25,
            "exit_reason": "Recovery TP1",
            "status": "CLOSED",
        },
        {
            "ticket": 7002,
            "symbol": "NAS100",
            "direction": "BUY",
            "open_ts": 101,
            "open_price": 100.0,
            "close_ts": 104,
            "close_price": 100.2,
            "profit": -0.10,
            "exit_reason": "Protect Exit",
            "status": "CLOSED",
        },
    ]

    bundle = build_outcome_labels(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=closed_rows,
    )

    assert bundle.metadata["offline_only"] is True
    assert bundle.metadata["label_contract"] == "OutcomeLabelsV1"
    assert bundle.metadata["labeler_version"] == "outcome_labeler_engine_v1"
    assert bundle.metadata["symbol"] == "NAS100"
    assert bundle.metadata["source_files"]["anchor"] == ["data/trades/entry_decisions.csv"]
    assert bundle.transition.label_status == "VALID"
    assert bundle.transition.buy_confirm_success_label is True
    assert bundle.transition.sell_confirm_success_label is False
    assert bundle.transition.false_break_label is False
    assert bundle.transition.reversal_success_label is False
    assert bundle.transition.continuation_success_label is True
    assert bundle.transition.metadata["label_contract"] == "TransitionOutcomeLabelsV1"
    assert bundle.transition.metadata["labeler_version"] == "outcome_labeler_engine_v1"
    assert bundle.transition.metadata["horizon_bars"] == 3
    assert bundle.transition.metadata["future_window_start"] == 101
    assert bundle.transition.metadata["future_window_end"] == 103
    assert bundle.transition.metadata["source_files"]["future_outcome"] == [
        "data/trades/trade_closed_history.csv",
        "trade_closed_history.csv",
    ]
    assert bundle.transition.metadata["matched_outcome_rows"]["future_bars"]["count"] == 3
    assert bundle.transition.metadata["label_status_reason"]["reason_code"] == "valid_complete_horizon"
    assert bundle.transition.metadata["label_reasons"]["buy_confirm_success_label"]["reason_code"] == "same_side_confirmation_observed"
    assert "Buy side stayed dominant" in bundle.transition.metadata["label_reasons"]["buy_confirm_success_label"]["reason_text"]
    assert bundle.transition.metadata["position_context"]["match_meta"]["match_method"] == "exact_position_key"
    assert bundle.trade_management.label_status == "VALID"
    assert bundle.trade_management.continue_favor_label is True
    assert bundle.trade_management.fail_now_label is False
    assert bundle.trade_management.recover_after_pullback_label is False
    assert bundle.trade_management.reach_tp1_label is True
    assert bundle.trade_management.opposite_edge_reach_label is True
    assert bundle.trade_management.better_reentry_if_cut_label is False
    assert bundle.trade_management.metadata["label_contract"] == "TradeManagementOutcomeLabelsV1"
    assert bundle.trade_management.metadata["horizon_bars"] == 6
    assert bundle.trade_management.metadata["future_window_start"] == 101
    assert bundle.trade_management.metadata["future_window_end"] == 104
    assert bundle.trade_management.metadata["matched_outcome_rows"]["closed_trade_context"]["position_key"] == 7001
    assert bundle.trade_management.metadata["label_status_reason"]["reason_code"] == "valid_complete_horizon"
    assert bundle.trade_management.metadata["label_reasons"]["reach_tp1_label"]["reason_code"] == "tp1_reached"
    assert "TP1 observable" in bundle.trade_management.metadata["label_reasons"]["reach_tp1_label"]["reason_text"]
    assert bundle.metadata["forecast_branch_evaluation_v1"]["transition_forecast_vs_outcome"]["summary"]["top_forecast_field"] == "p_buy_confirm"
    assert bundle.metadata["forecast_branch_evaluation_v1"]["management_forecast_vs_outcome"]["summary"]["top_forecast_field"] == "p_continue_favor"
    assert bundle.metadata["forecast_branch_evaluation_v1"]["gap_signal_quality"]["evaluations"]["management_continue_fail_gap"]["quality_state"] == "aligned_positive"
    assert bundle.transition.metadata["forecast_vs_outcome_v1"]["evaluations"]["p_buy_confirm"]["hit"] is True
    assert bundle.trade_management.metadata["forecast_vs_outcome_v1"]["evaluations"]["p_continue_favor"]["hit"] is True


def test_label_transition_outcomes_marks_ambiguous_path_unknown():
    decision_row = {
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 200.0,
        "symbol": "BTCUSD",
        "action": "BUY",
        "transition_forecast_v1": '{"p_false_break":0.44}',
        "trade_management_forecast_v1": '{"p_fail_now":0.33}',
    }
    future_bars = [
        {"time": 201, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.1},
        {"time": 202, "open": 100.1, "high": 101.1, "low": 98.9, "close": 100.0},
        {"time": 203, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.02},
    ]

    labels = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
    )

    assert labels.label_status == "AMBIGUOUS"
    assert labels.buy_confirm_success_label is None
    assert labels.sell_confirm_success_label is None
    assert labels.false_break_label is None
    assert labels.reversal_success_label is None
    assert labels.continuation_success_label is None
    assert labels.metadata["label_status_reason"]["reason_code"] == "ambiguous_future_path"
    assert labels.metadata["label_reasons"]["buy_confirm_success_label"]["reason_code"] == "unknown_due_to_ambiguous"
    assert labels.metadata["label_polarities"]["buy_confirm_success_label"] == "UNKNOWN"


def test_label_management_outcomes_requires_position_context():
    decision_row = {
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 300.0,
        "symbol": "XAUUSD",
        "action": "SELL",
        "transition_forecast_v1": '{"p_sell_confirm":0.63}',
        "trade_management_forecast_v1": '{"p_fail_now":0.51}',
    }
    future_bars = [
        {"time": 301, "open": 100.0, "high": 100.2, "low": 99.5, "close": 99.7},
        {"time": 302, "open": 99.7, "high": 99.9, "low": 99.3, "close": 99.5},
        {"time": 303, "open": 99.5, "high": 99.8, "low": 99.1, "close": 99.3},
        {"time": 304, "open": 99.3, "high": 99.6, "low": 99.0, "close": 99.2},
        {"time": 305, "open": 99.2, "high": 99.4, "low": 98.9, "close": 99.1},
        {"time": 306, "open": 99.1, "high": 99.3, "low": 98.8, "close": 99.0},
    ]

    labels = label_management_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=[],
    )

    assert labels.label_status == "NO_POSITION_CONTEXT"
    assert labels.continue_favor_label is None
    assert labels.fail_now_label is None
    assert labels.reach_tp1_label is None
    assert labels.metadata["label_status_reason"]["reason_code"] == "no_position_context"
    assert labels.metadata["label_reasons"]["continue_favor_label"]["reason_code"] == "unknown_due_to_no_position_context"
    assert labels.metadata["position_context"]["match_meta"]["match_method"] == "no_match"
    assert labels.metadata["matched_outcome_rows"]["position_context"]["match_method"] == "no_match"


def test_label_transition_outcomes_marks_incomplete_future_window():
    decision_row = {
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 400.0,
        "symbol": "NAS100",
        "action": "BUY",
        "transition_forecast_v1": '{"p_buy_confirm":0.55}',
        "trade_management_forecast_v1": '{"p_continue_favor":0.42}',
    }
    future_bars = [
        {"time": 401, "open": 100.0, "high": 100.5, "low": 99.9, "close": 100.4},
        {"time": 402, "open": 100.4, "high": 100.8, "low": 100.1, "close": 100.7},
    ]

    labels = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
    )

    assert labels.label_status == "INSUFFICIENT_FUTURE_BARS"
    assert labels.buy_confirm_success_label is None
    assert labels.continuation_success_label is None
    assert labels.metadata["future_window_start"] == 401
    assert labels.metadata["future_window_end"] == 402
    assert labels.metadata["label_status_reason"]["reason_code"] == "insufficient_future_bars"
    assert labels.metadata["label_reasons"]["continuation_success_label"]["reason_code"] == "unknown_due_to_insufficient_future_bars"


def test_build_outcome_label_shadow_row_generates_reviewable_output():
    decision_row = {
        "ticket": 7001,
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 100.0,
        "signal_timeframe": "15M",
        "symbol": "NAS100",
        "action": "BUY",
        "setup_id": "range_lower_reversal_buy",
        "setup_side": "BUY",
        "transition_forecast_v1": '{"p_buy_confirm":0.72,"p_continuation_success":0.52}',
        "trade_management_forecast_v1": '{"p_continue_favor":0.61,"p_reach_tp1":0.56}',
        "forecast_gap_metrics_v1": '{"transition_side_separation":0.22}',
    }
    future_bars = [
        {"time": 101, "open": 100.0, "high": 101.2, "low": 99.9, "close": 101.0},
        {"time": 102, "open": 101.0, "high": 101.6, "low": 100.8, "close": 101.5},
        {"time": 103, "open": 101.5, "high": 102.0, "low": 101.2, "close": 101.8},
        {"time": 104, "open": 101.8, "high": 102.1, "low": 101.6, "close": 101.9},
    ]
    closed_rows = [
        {
            "ticket": 7001,
            "symbol": "NAS100",
            "direction": "BUY",
            "open_ts": 101,
            "open_price": 100.0,
            "close_ts": 104,
            "close_price": 101.8,
            "profit": 0.25,
            "exit_reason": "Recovery TP1",
            "status": "CLOSED",
        },
    ]

    shadow_row = build_outcome_label_shadow_row(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=closed_rows,
    )

    assert shadow_row["row_type"] == "outcome_labels_v1"
    assert shadow_row["shadow_output_contract"] == "shadow_label_output_v1"
    assert shadow_row["decision_context"]["symbol"] == "NAS100"
    assert shadow_row["row_key"].startswith("replay_dataset_row_v1|symbol=NAS100")
    assert shadow_row["forecast_snapshot"]["transition_forecast_v1"]["p_buy_confirm"] == 0.72
    assert shadow_row["forecast_snapshot"]["forecast_gap_metrics_v1"]["transition_side_separation"] == 0.22
    assert shadow_row["outcome_labels_v1"]["transition"]["label_status"] == "VALID"
    assert shadow_row["forecast_branch_evaluation_v1"]["contract_version"] == "forecast_branch_evaluation_v1"
    assert shadow_row["label_quality_summary_v1"]["label_positive_count"] == 5
    assert shadow_row["transition_label_summary"]["positive_labels"] == [
        "buy_confirm_success_label",
        "continuation_success_label",
    ]
    assert shadow_row["transition_label_summary"]["top_forecast_probability_field"] == "p_buy_confirm"
    assert shadow_row["transition_label_summary"]["forecast_vs_outcome_v1"]["summary"]["top_forecast_field"] == "p_buy_confirm"
    assert shadow_row["management_label_summary"]["positive_labels"] == [
        "continue_favor_label",
        "reach_tp1_label",
        "opposite_edge_reach_label",
    ]
    assert shadow_row["management_label_summary"]["top_forecast_probability_field"] == "p_continue_favor"
    assert shadow_row["management_label_summary"]["reason_codes"]["reach_tp1_label"] == "tp1_reached"


def test_write_outcome_label_shadow_output_writes_analysis_json(tmp_path):
    decision_row = {
        "ticket": 7001,
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 100.0,
        "signal_timeframe": "15M",
        "symbol": "NAS100",
        "action": "BUY",
        "setup_id": "range_lower_reversal_buy",
        "setup_side": "BUY",
        "transition_forecast_v1": '{"p_buy_confirm":0.72}',
        "trade_management_forecast_v1": '{"p_continue_favor":0.61}',
    }
    future_bars = [
        {"time": 101, "open": 100.0, "high": 101.2, "low": 99.9, "close": 101.0},
        {"time": 102, "open": 101.0, "high": 101.6, "low": 100.8, "close": 101.5},
        {"time": 103, "open": 101.5, "high": 102.0, "low": 101.2, "close": 101.8},
        {"time": 104, "open": 101.8, "high": 102.1, "low": 101.6, "close": 101.9},
    ]
    closed_rows = [
        {
            "ticket": 7001,
            "symbol": "NAS100",
            "direction": "BUY",
            "open_ts": 101,
            "open_price": 100.0,
            "close_ts": 104,
            "close_price": 101.8,
            "profit": 0.25,
            "exit_reason": "Recovery TP1",
            "status": "CLOSED",
        },
    ]

    out_path = write_outcome_label_shadow_output(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=closed_rows,
        output_dir=tmp_path,
    )

    assert out_path.exists()
    assert out_path.parent == tmp_path
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["row_type"] == "outcome_labels_v1"
    assert payload["decision_context"]["setup_id"] == "range_lower_reversal_buy"
    assert payload["transition_label_summary"]["label_status"] == "VALID"
