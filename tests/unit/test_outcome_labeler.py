import json

from backend.trading.engine.offline.outcome_labeler import (
    build_outcome_labels,
    label_management_outcomes,
    label_transition_outcomes,
)


def _decision_row(
    *,
    ticket: int = 7001,
    symbol: str = "NAS100",
    action: str = "BUY",
    signal_bar_ts: float = 100.0,
) -> dict[str, object]:
    return {
        "ticket": ticket,
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": signal_bar_ts,
        "symbol": symbol,
        "action": action,
        "setup_id": f"{action.lower()}_test_setup",
        "setup_side": action,
        "transition_forecast_v1": json.dumps(
            {
                "p_buy_confirm": 0.61,
                "p_sell_confirm": 0.61,
                "p_false_break": 0.44,
                "p_reversal_success": 0.52,
                "p_continuation_success": 0.53,
            }
        ),
        "trade_management_forecast_v1": json.dumps(
            {
                "p_continue_favor": 0.57,
                "p_fail_now": 0.49,
                "p_recover_after_pullback": 0.51,
                "p_reach_tp1": 0.46,
                "p_opposite_edge_reach": 0.45,
                "p_better_reentry_if_cut": 0.43,
            }
        ),
    }


def _closed_trade_rows(
    *,
    ticket: int = 7001,
    symbol: str = "NAS100",
    direction: str = "BUY",
    open_ts: float = 101.0,
    close_ts: float = 106.0,
    open_price: float = 100.0,
    close_price: float = 100.05,
    profit: float = 0.05,
    exit_reason: str = "Time Exit",
) -> list[dict[str, object]]:
    return [
        {
            "ticket": ticket,
            "symbol": symbol,
            "direction": direction,
            "open_ts": open_ts,
            "open_price": open_price,
            "close_ts": close_ts,
            "close_price": close_price,
            "profit": profit,
            "exit_reason": exit_reason,
            "status": "CLOSED",
        }
    ]


def _future_bars(*bars: tuple[float, float, float, float, float]) -> list[dict[str, float]]:
    return [
        {
            "time": time,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
        }
        for time, open_price, high, low, close in bars
    ]


def test_label_transition_outcomes_marks_buy_confirm_success():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.08, 99.99, 100.06),
        (102, 100.06, 100.12, 100.03, 100.10),
        (103, 100.10, 100.18, 100.06, 100.15),
    )

    labels = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=100.15),
    )

    assert labels.label_status == "VALID"
    assert labels.buy_confirm_success_label is True
    assert labels.sell_confirm_success_label is False
    assert labels.continuation_success_label is True
    assert labels.reversal_success_label is False
    assert labels.metadata["label_reasons"]["buy_confirm_success_label"]["reason_code"] == "same_side_confirmation_observed"


def test_label_transition_outcomes_marks_sell_confirm_success():
    decision_row = _decision_row(action="SELL")
    future_bars = _future_bars(
        (101, 100.0, 100.01, 99.94, 99.96),
        (102, 99.96, 99.98, 99.90, 99.92),
        (103, 99.92, 99.94, 99.84, 99.86),
    )

    labels = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="SELL", close_price=99.86),
    )

    assert labels.label_status == "VALID"
    assert labels.buy_confirm_success_label is False
    assert labels.sell_confirm_success_label is True
    assert labels.continuation_success_label is True
    assert labels.metadata["label_reasons"]["sell_confirm_success_label"]["reason_code"] == "same_side_confirmation_observed"


def test_label_transition_outcomes_marks_false_break_case():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.12, 99.98, 100.08),
        (102, 100.08, 100.09, 99.95, 99.97),
        (103, 99.97, 100.01, 99.80, 99.99),
    )

    labels = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=99.99),
    )

    assert labels.label_status == "VALID"
    assert labels.false_break_label is True
    assert labels.reversal_success_label is False
    assert labels.continuation_success_label is False
    assert labels.metadata["label_reasons"]["false_break_label"]["reason_code"] == "quick_invalidation_observed"


def test_label_transition_outcomes_marks_reversal_success_without_continuation():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.12, 99.99, 100.08),
        (102, 100.08, 100.09, 99.90, 99.94),
        (103, 99.94, 99.96, 99.70, 99.74),
    )

    labels = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=99.74),
    )

    assert labels.label_status == "VALID"
    assert labels.reversal_success_label is True
    assert labels.continuation_success_label is False
    assert labels.false_break_label is False
    assert labels.metadata["label_reasons"]["reversal_success_label"]["reason_code"] == "meaningful_reversal_observed"


def test_label_transition_outcomes_marks_continuation_success_without_reversal():
    decision_row = _decision_row(action="SELL")
    future_bars = _future_bars(
        (101, 100.0, 100.02, 99.92, 99.95),
        (102, 99.95, 99.97, 99.85, 99.88),
        (103, 99.88, 99.90, 99.76, 99.80),
    )

    labels = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="SELL", close_price=99.80),
    )

    assert labels.label_status == "VALID"
    assert labels.continuation_success_label is True
    assert labels.reversal_success_label is False
    assert labels.metadata["label_reasons"]["continuation_success_label"]["reason_code"] == "same_side_continuation_observed"


def test_label_management_outcomes_marks_continue_favor():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.04, 99.98, 100.02),
        (102, 100.02, 100.06, 99.99, 100.04),
        (103, 100.04, 100.07, 100.02, 100.05),
        (104, 100.05, 100.09, 100.03, 100.07),
        (105, 100.07, 100.10, 100.05, 100.08),
        (106, 100.08, 100.10, 100.06, 100.08),
    )

    labels = label_management_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=100.08),
    )

    assert labels.label_status == "VALID"
    assert labels.continue_favor_label is True
    assert labels.fail_now_label is False
    assert labels.recover_after_pullback_label is False
    assert labels.better_reentry_if_cut_label is False
    assert labels.metadata["label_reasons"]["continue_favor_label"]["reason_code"] == "hold_favor_observed"


def test_label_management_outcomes_marks_fail_now():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.01, 99.90, 99.94),
        (102, 99.94, 99.96, 99.84, 99.88),
        (103, 99.88, 99.91, 99.80, 99.86),
        (104, 99.86, 99.90, 99.79, 99.85),
        (105, 99.85, 99.89, 99.78, 99.84),
        (106, 99.84, 99.88, 99.77, 99.84),
    )

    labels = label_management_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=99.84),
    )

    assert labels.label_status == "VALID"
    assert labels.continue_favor_label is False
    assert labels.fail_now_label is True
    assert labels.recover_after_pullback_label is False
    assert labels.better_reentry_if_cut_label is False
    assert labels.metadata["label_reasons"]["fail_now_label"]["reason_code"] == "rapid_failure_observed"


def test_label_management_outcomes_marks_recover_and_reentry():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.03, 99.96, 99.98),
        (102, 99.98, 100.05, 99.97, 100.03),
        (103, 100.03, 100.07, 100.01, 100.05),
        (104, 100.05, 100.07, 100.03, 100.05),
        (105, 100.05, 100.06, 100.02, 100.04),
        (106, 100.04, 100.05, 100.01, 100.04),
    )

    labels = label_management_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=100.04),
    )

    assert labels.label_status == "VALID"
    assert labels.continue_favor_label is True
    assert labels.fail_now_label is False
    assert labels.recover_after_pullback_label is True
    assert labels.better_reentry_if_cut_label is True
    assert labels.metadata["label_reasons"]["recover_after_pullback_label"]["reason_code"] == "pullback_recovery_observed"
    assert labels.metadata["label_reasons"]["better_reentry_if_cut_label"]["reason_code"] == "better_reentry_than_hold_observed"


def test_label_transition_outcomes_marks_insufficient_future_bars():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.08, 99.99, 100.06),
        (102, 100.06, 100.12, 100.03, 100.10),
    )

    labels = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=100.10),
    )

    assert labels.label_status == "INSUFFICIENT_FUTURE_BARS"
    assert labels.buy_confirm_success_label is None
    assert labels.continuation_success_label is None
    assert labels.metadata["label_status_reason"]["reason_code"] == "insufficient_future_bars"


def test_label_transition_outcomes_marks_ambiguous_path():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.10, 99.90, 100.01),
        (102, 100.01, 100.11, 99.89, 100.00),
        (103, 100.00, 100.09, 99.91, 100.00),
    )

    labels = label_transition_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=100.00),
    )

    assert labels.label_status == "AMBIGUOUS"
    assert labels.buy_confirm_success_label is None
    assert labels.false_break_label is None
    assert labels.metadata["label_status_reason"]["reason_code"] == "ambiguous_future_path"


def test_label_management_outcomes_marks_censored_path():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.03, 99.96, 99.98),
        (102, 99.98, 100.05, 99.97, 100.03),
        (103, 100.03, 100.07, 100.01, 100.05),
        (104, 100.05, 100.07, 100.03, 100.05),
        (105, 100.05, 100.06, 100.02, 100.04),
        (106, 100.04, 100.05, 100.01, 100.04),
    )

    labels = label_management_outcomes(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=100.04),
        is_censored=True,
    )

    assert labels.label_status == "CENSORED"
    assert labels.continue_favor_label is None
    assert labels.recover_after_pullback_label is None
    assert labels.metadata["label_status_reason"]["reason_code"] == "censored_future_path"
    assert labels.metadata["label_reasons"]["continue_favor_label"]["reason_code"] == "unknown_due_to_censored"


def test_build_outcome_labels_is_deterministic_for_same_input():
    decision_row = _decision_row(action="BUY")
    future_bars = _future_bars(
        (101, 100.0, 100.03, 99.96, 99.98),
        (102, 99.98, 100.05, 99.97, 100.03),
        (103, 100.03, 100.07, 100.01, 100.05),
        (104, 100.05, 100.07, 100.03, 100.05),
        (105, 100.05, 100.06, 100.02, 100.04),
        (106, 100.04, 100.05, 100.01, 100.04),
    )
    closed_trade_rows = _closed_trade_rows(direction="BUY", close_price=100.04)

    bundle_one = build_outcome_labels(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=closed_trade_rows,
    )
    bundle_two = build_outcome_labels(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=closed_trade_rows,
    )

    assert bundle_one.to_dict() == bundle_two.to_dict()
    assert bundle_one.transition.label_status == "VALID"
    assert bundle_one.trade_management.label_status == "VALID"


def test_build_outcome_labels_exposes_forecast_branch_evaluation_metadata():
    decision_row = _decision_row(action="BUY")
    decision_row["forecast_gap_metrics_v1"] = json.dumps(
        {
            "transition_confirm_fake_gap": 0.18,
            "management_continue_fail_gap": 0.24,
            "management_recover_reentry_gap": -0.16,
        }
    )
    future_bars = _future_bars(
        (101, 100.0, 100.08, 99.99, 100.06),
        (102, 100.06, 100.12, 100.03, 100.10),
        (103, 100.10, 100.18, 100.06, 100.15),
        (104, 100.15, 100.22, 100.10, 100.18),
        (105, 100.18, 100.25, 100.14, 100.20),
        (106, 100.20, 100.26, 100.18, 100.22),
    )

    bundle = build_outcome_labels(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=_closed_trade_rows(direction="BUY", close_price=100.22, exit_reason="Recovery TP1"),
    )

    evaluation = bundle.metadata["forecast_branch_evaluation_v1"]

    assert evaluation["contract_version"] == "forecast_branch_evaluation_v1"
    assert evaluation["transition_forecast_vs_outcome"]["evaluations"]["p_buy_confirm"]["hit"] is True
    assert evaluation["management_forecast_vs_outcome"]["evaluations"]["p_continue_favor"]["hit"] is True
    assert evaluation["gap_signal_quality"]["evaluations"]["transition_confirm_fake_gap"]["quality_state"] == "aligned_positive"
    assert bundle.transition.metadata["forecast_vs_outcome_v1"]["summary"]["hit_count"] >= 1
    assert bundle.trade_management.metadata["forecast_vs_outcome_v1"]["summary"]["top_forecast_field"] == "p_continue_favor"
