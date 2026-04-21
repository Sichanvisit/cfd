import json

from backend.services.forecast_state25_outcome_bridge import (
    build_forecast_state25_outcome_bridge_report,
    build_forecast_state25_outcome_bridge_rows,
)
from backend.services.forecast_state25_runtime_bridge import build_forecast_state25_runtime_bridge_v1


def _base_row(*, ts: int, outcome: str, side: str, ticket: int = 0) -> dict:
    row = {
        "symbol": "BTCUSD",
        "time": ts,
        "signal_bar_ts": ts,
        "outcome": outcome,
        "direction": side,
        "action": side,
        "setup_side": side,
        "entry_setup_id": "range_lower_reversal_buy" if side == "BUY" else "range_upper_reversal_sell",
        "entry_session_name": "LONDON",
        "entry_wait_state": "CENTER",
        "entry_wait_decision": "wait_soft_conflict",
        "entry_wait_selected": outcome == "wait",
        "entry_score": 56.0,
        "contra_score_at_entry": 19.0,
        "prediction_bundle": json.dumps(
            {
                "p_buy_confirm": 0.82 if side == "BUY" else 0.12,
                "p_sell_confirm": 0.12 if side == "BUY" else 0.82,
                "p_false_break": 0.18,
                "p_continuation_success": 0.66,
            },
            ensure_ascii=False,
        ),
        "micro_breakout_readiness_state": "READY",
        "micro_reversal_risk_state": "MEDIUM_RISK",
        "micro_participation_state": "STEADY_PARTICIPATION",
        "micro_gap_context_state": "NONE",
        "transition_forecast_v1": {
            "p_buy_confirm": 0.82 if side == "BUY" else 0.10,
            "p_sell_confirm": 0.10 if side == "BUY" else 0.82,
            "p_false_break": 0.18,
            "p_reversal_success": 0.22,
            "p_continuation_success": 0.73,
            "metadata": {
                "mapper_version": "transition_mapper_v1",
                "side_separation": 0.44,
            },
        },
        "trade_management_forecast_v1": {
            "p_continue_favor": 0.76,
            "p_fail_now": 0.14,
            "p_recover_after_pullback": 0.41,
            "p_reach_tp1": 0.64,
            "p_opposite_edge_reach": 0.36,
            "p_better_reentry_if_cut": 0.19,
            "metadata": {
                "mapper_version": "management_mapper_v1",
                "continue_fail_gap": 0.22,
                "recover_reentry_gap": 0.15,
            },
        },
        "forecast_gap_metrics_v1": {
            "transition_confirm_fake_gap": 0.24,
            "transition_reversal_continuation_gap": -0.18,
            "management_continue_fail_gap": 0.22,
            "management_recover_reentry_gap": 0.15,
            "wait_confirm_gap": 0.19,
            "hold_exit_gap": 0.16,
            "same_side_flip_gap": 0.09,
            "belief_barrier_tension_gap": 0.12,
        },
    }
    if ticket > 0:
        row["ticket"] = ticket
        row["position_id"] = ticket
        row["entry_fill_price"] = 100.10
        row["open_ts"] = ts
    row["forecast_state25_runtime_bridge_v1"] = build_forecast_state25_runtime_bridge_v1(row)
    return row


def _future_bars() -> list[dict]:
    prices = [
        (1061, 100.00, 100.20, 99.95, 100.18),
        (1121, 100.18, 100.34, 100.12, 100.31),
        (1181, 100.31, 100.48, 100.24, 100.44),
        (1241, 100.44, 100.63, 100.37, 100.58),
        (1301, 100.58, 100.78, 100.52, 100.73),
        (1361, 100.73, 100.96, 100.66, 100.91),
    ]
    return [
        {
            "symbol": "BTCUSD",
            "time": ts,
            "open": op,
            "high": hi,
            "low": lo,
            "close": cl,
        }
        for ts, op, hi, lo, cl in prices
    ]


def _closed_trade_rows() -> list[dict]:
    return [
        {
            "symbol": "BTCUSD",
            "ticket": 101,
            "position_id": 101,
            "direction": "BUY",
            "status": "CLOSED",
            "open_ts": 1060,
            "close_ts": 1400,
            "open_price": 100.10,
            "profit": 18.0,
            "net_pnl_after_cost": 17.5,
            "exit_reason": "RECOVERY TP1",
            "learning_total_label": "positive",
            "learning_total_score": 0.62,
            "loss_quality_label": "non_loss",
            "signed_exit_score": 85.0,
        }
    ]


def test_forecast_state25_outcome_bridge_rows_link_outcomes_wait_and_economic():
    wait_row = _base_row(ts=1000, outcome="wait", side="BUY")
    entered_row = _base_row(ts=1060, outcome="entered", side="BUY", ticket=101)

    rows = build_forecast_state25_outcome_bridge_rows(
        entry_decision_rows=[wait_row, entered_row],
        closed_trade_rows=_closed_trade_rows(),
        future_bar_rows=_future_bars(),
    )

    assert len(rows) == 2

    assert any(str(row.get("entry_wait_quality_label", "")).strip() for row in rows)
    assert any(bool((row.get("economic_target_summary", {}) or {}).get("available", False)) for row in rows)
    assert any(
        (row.get("outcome_label_compact_summary_v1", {}) or {}).get("transition_label_status") == "VALID"
        for row in rows
    )
    assert any(
        (row.get("outcome_label_compact_summary_v1", {}) or {}).get("management_label_status") == "VALID"
        for row in rows
    )


def test_forecast_state25_outcome_bridge_report_summarizes_bridge_quality():
    wait_row = _base_row(ts=1000, outcome="wait", side="BUY")
    entered_row = _base_row(ts=1060, outcome="entered", side="BUY", ticket=101)

    report = build_forecast_state25_outcome_bridge_report(
        entry_decision_rows=[wait_row, entered_row],
        closed_trade_rows=_closed_trade_rows(),
        future_bar_rows=_future_bars(),
    )

    summary = report["summary"]
    coverage = report["coverage"]

    assert summary["raw_bridge_candidate_count"] == 2
    assert summary["bridged_row_count"] == 2
    assert summary["transition_valid_rows"] >= 1
    assert summary["management_valid_rows"] >= 1
    assert summary["full_outcome_eligible_rows"] >= 1
    assert summary["partial_outcome_eligible_rows"] >= 0
    assert summary["insufficient_future_bars_rows"] == 0
    assert summary["rows_with_wait_quality"] >= 1
    assert summary["rows_with_economic_target"] >= 1
    assert coverage["bridge_quality_status_counts"]
    assert summary["scene_family_stats"]
