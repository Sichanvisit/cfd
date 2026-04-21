from backend.services.belief_outcome_bridge import (
    build_belief_outcome_bridge_report,
    build_belief_outcome_bridge_rows,
)
from backend.services.belief_state25_runtime_bridge import build_belief_state25_runtime_bridge_v1


def _base_row(*, ts: int, action: str, dominant_side: str, outcome: str, pos_count: int, flip_readiness: float, instability: float, persistence: float) -> dict:
    row = {
        "symbol": "BTCUSD",
        "time": ts,
        "signal_bar_ts": ts,
        "outcome": outcome,
        "direction": action,
        "action": action,
        "setup_side": action,
        "my_position_count": pos_count,
        "entry_setup_id": "range_lower_reversal_buy" if action == "BUY" else "range_upper_reversal_sell",
        "entry_wait_state": "CENTER",
        "entry_wait_decision": "wait_soft_conflict",
        "entry_fill_price": 100.0,
        "transition_forecast_v1": {
            "p_buy_confirm": 0.82 if action == "BUY" else 0.18,
            "p_sell_confirm": 0.18 if action == "BUY" else 0.82,
            "p_false_break": 0.14,
            "p_continuation_success": 0.68,
            "metadata": {
                "mapper_version": "transition_mapper_v1",
                "side_separation": 0.44,
            },
        },
        "trade_management_forecast_v1": {
            "p_continue_favor": 0.71,
            "p_fail_now": 0.16,
            "metadata": {
                "mapper_version": "management_mapper_v1",
            },
        },
        "forecast_gap_metrics_v1": {
            "wait_confirm_gap": 0.18,
            "hold_exit_gap": 0.14,
            "same_side_flip_gap": 0.09,
            "belief_barrier_tension_gap": 0.08,
        },
        "belief_state_v1": {
            "buy_belief": 0.74 if dominant_side == "BUY" else 0.18,
            "sell_belief": 0.74 if dominant_side == "SELL" else 0.18,
            "buy_persistence": persistence if dominant_side == "BUY" else 0.12,
            "sell_persistence": persistence if dominant_side == "SELL" else 0.12,
            "belief_spread": 0.56 if dominant_side in {"BUY", "SELL"} else 0.0,
            "flip_readiness": flip_readiness,
            "belief_instability": instability,
            "dominant_side": dominant_side,
            "dominant_mode": "continuation" if dominant_side in {"BUY", "SELL"} else "balanced",
            "buy_streak": 3 if dominant_side == "BUY" else 0,
            "sell_streak": 3 if dominant_side == "SELL" else 0,
            "transition_age": 3,
        },
        "evidence_vector_v1": {
            "buy_total_evidence": 0.66 if action == "BUY" else 0.19,
            "sell_total_evidence": 0.66 if action == "SELL" else 0.19,
            "buy_continuation_evidence": 0.46 if action == "BUY" else 0.08,
            "sell_continuation_evidence": 0.46 if action == "SELL" else 0.08,
            "buy_reversal_evidence": 0.14,
            "sell_reversal_evidence": 0.14,
        },
        "barrier_state_v1": {
            "buy_barrier": 0.18,
            "sell_barrier": 0.18,
            "conflict_barrier": 0.12,
            "middle_chop_barrier": 0.08,
            "direction_policy_barrier": 0.11,
            "liquidity_barrier": 0.22,
        },
    }
    row["belief_state25_runtime_bridge_v1"] = build_belief_state25_runtime_bridge_v1(row)
    return row


def _hold_future_bars() -> list[dict]:
    prices = [
        (1060, 100.00, 100.12, 99.95, 100.10),
        (1120, 100.10, 100.20, 100.03, 100.18),
        (1180, 100.18, 100.31, 100.10, 100.28),
        (1240, 100.28, 100.46, 100.24, 100.42),
        (1300, 100.42, 100.62, 100.38, 100.58),
        (1360, 100.58, 100.82, 100.55, 100.78),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def _premature_flip_future_bars() -> list[dict]:
    prices = [
        (2060, 100.00, 100.06, 99.96, 100.02),
        (2120, 100.02, 100.09, 99.98, 100.06),
        (2180, 100.06, 100.22, 100.04, 100.18),
        (2240, 100.18, 100.44, 100.16, 100.40),
        (2300, 100.40, 100.70, 100.38, 100.66),
        (2360, 100.66, 101.02, 100.62, 100.98),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def _weak_usable_future_bars() -> list[dict]:
    prices = [
        (3060, 100.00, 100.28, 99.96, 100.24),
        (3120, 100.24, 100.46, 100.18, 100.40),
        (3180, 100.40, 100.68, 100.34, 100.60),
        (3240, 100.60, 100.96, 100.56, 100.88),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def test_belief_outcome_bridge_rows_label_correct_hold():
    anchor = _base_row(
        ts=1000,
        action="BUY",
        dominant_side="BUY",
        outcome="entered",
        pos_count=1,
        flip_readiness=0.18,
        instability=0.18,
        persistence=0.46,
    )

    rows = build_belief_outcome_bridge_rows(
        entry_decision_rows=[anchor],
        future_bar_rows=_hold_future_bars(),
    )

    assert len(rows) == 1
    outcome = rows[0]["belief_outcome_bridge_v1"]
    assert outcome["belief_anchor_context"] == "hold_thesis"
    assert outcome["belief_outcome_label"] == "correct_hold"
    assert outcome["belief_label_confidence"] in {"high", "medium"}


def test_belief_outcome_bridge_rows_label_premature_flip():
    flip_anchor = _base_row(
        ts=2000,
        action="SELL",
        dominant_side="BUY",
        outcome="skipped",
        pos_count=1,
        flip_readiness=0.72,
        instability=0.52,
        persistence=0.44,
    )
    flip_entered = _base_row(
        ts=2060,
        action="SELL",
        dominant_side="SELL",
        outcome="entered",
        pos_count=1,
        flip_readiness=0.41,
        instability=0.26,
        persistence=0.43,
    )
    flip_entered["entry_fill_price"] = 100.0

    rows = build_belief_outcome_bridge_rows(
        entry_decision_rows=[flip_anchor, flip_entered],
        future_bar_rows=_premature_flip_future_bars(),
    )

    assert len(rows) == 2
    anchor_row = next(row for row in rows if int(row["time"]) == 2000)
    outcome = anchor_row["belief_outcome_bridge_v1"]
    assert outcome["belief_anchor_context"] == "flip_thesis"
    assert outcome["belief_flip_executed"] is True
    assert outcome["belief_outcome_label"] == "premature_flip"


def test_belief_outcome_bridge_rows_label_weak_usable_when_coverage_is_partial():
    anchor = _base_row(
        ts=3000,
        action="BUY",
        dominant_side="BUY",
        outcome="entered",
        pos_count=1,
        flip_readiness=0.18,
        instability=0.18,
        persistence=0.46,
    )

    rows = build_belief_outcome_bridge_rows(
        entry_decision_rows=[anchor],
        future_bar_rows=_weak_usable_future_bars(),
    )

    assert len(rows) == 1
    outcome = rows[0]["belief_outcome_bridge_v1"]
    assert outcome["belief_outcome_label"] == "correct_hold"
    assert outcome["belief_label_confidence"] == "weak_usable"
    assert outcome["bridge_quality_status"] == "labeled"


def test_belief_outcome_bridge_report_summarizes_label_counts():
    hold_anchor = _base_row(
        ts=1000,
        action="BUY",
        dominant_side="BUY",
        outcome="entered",
        pos_count=1,
        flip_readiness=0.18,
        instability=0.18,
        persistence=0.46,
    )
    flip_anchor = _base_row(
        ts=2000,
        action="SELL",
        dominant_side="BUY",
        outcome="skipped",
        pos_count=1,
        flip_readiness=0.72,
        instability=0.52,
        persistence=0.44,
    )
    flip_entered = _base_row(
        ts=2060,
        action="SELL",
        dominant_side="SELL",
        outcome="entered",
        pos_count=1,
        flip_readiness=0.41,
        instability=0.26,
        persistence=0.43,
    )
    report = build_belief_outcome_bridge_report(
        entry_decision_rows=[hold_anchor, flip_anchor, flip_entered],
        future_bar_rows=(_hold_future_bars() + _premature_flip_future_bars()),
    )

    assert report["summary"]["raw_bridge_candidate_count"] == 3
    assert report["summary"]["bridged_row_count"] == 3
    assert report["coverage"]["label_counts"]["correct_hold"] >= 1
    assert report["coverage"]["label_counts"]["premature_flip"] >= 1
    assert report["summary"]["usable_rows"] >= report["summary"]["eligible_rows"]
