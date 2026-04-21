from backend.services.entry_wait_quality_audit import (
    ENTRY_WAIT_QUALITY_LABEL_AVOIDED_LOSS,
    ENTRY_WAIT_QUALITY_LABEL_BETTER_ENTRY,
    ENTRY_WAIT_QUALITY_LABEL_DELAYED_LOSS,
    ENTRY_WAIT_QUALITY_LABEL_INSUFFICIENT,
    ENTRY_WAIT_QUALITY_LABEL_MISSED_MOVE,
    build_entry_wait_quality_summary_v1,
    evaluate_entry_wait_quality_v1,
    render_entry_wait_quality_markdown,
)


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


def test_entry_wait_quality_marks_better_entry_after_wait_for_buy():
    result = evaluate_entry_wait_quality_v1(
        decision_row={
            "symbol": "NAS100",
            "action": "BUY",
            "entry_wait_selected": 1,
            "entry_wait_decision": "wait_soft_edge_approach",
            "anchor_price": 100.0,
        },
        future_bars=_future_bars(
            (101, 100.0, 100.02, 99.72, 99.80),
            (102, 99.80, 100.20, 99.78, 100.12),
        ),
        next_entry_row={
            "time": "2026-04-03T10:05:00+09:00",
            "action": "BUY",
            "entry_fill_price": 99.76,
            "outcome": "entered",
        },
        next_closed_trade_row={
            "profit": 1.2,
            "exit_reason": "tp1",
        },
    )

    assert result["label_status"] == "VALID"
    assert result["quality_label"] == ENTRY_WAIT_QUALITY_LABEL_BETTER_ENTRY
    assert result["quality_score"] > 0.0


def test_entry_wait_quality_marks_avoided_loss_when_no_reentry_and_adverse_move_hits():
    result = evaluate_entry_wait_quality_v1(
        decision_row={
            "symbol": "BTCUSD",
            "action": "BUY",
            "entry_wait_selected": 1,
            "entry_wait_decision": "wait_policy_suppressed",
            "anchor_price": 100.0,
        },
        future_bars=_future_bars(
            (101, 100.0, 100.01, 99.55, 99.60),
            (102, 99.60, 99.70, 99.40, 99.50),
        ),
    )

    assert result["quality_label"] == ENTRY_WAIT_QUALITY_LABEL_AVOIDED_LOSS
    assert "adverse_move_avoided" in result["reason_codes"]


def test_entry_wait_quality_marks_missed_move_when_market_runs_without_better_reentry():
    result = evaluate_entry_wait_quality_v1(
        decision_row={
            "symbol": "XAUUSD",
            "action": "BUY",
            "entry_wait_selected": 1,
            "entry_wait_decision": "wait_soft_conflict_observe",
            "anchor_price": 100.0,
        },
        future_bars=_future_bars(
            (101, 100.0, 100.40, 99.99, 100.32),
            (102, 100.32, 100.70, 100.20, 100.60),
        ),
    )

    assert result["quality_label"] == ENTRY_WAIT_QUALITY_LABEL_MISSED_MOVE
    assert result["quality_score"] < 0.0


def test_entry_wait_quality_marks_delayed_loss_when_reentry_gets_worse_price_and_loses():
    result = evaluate_entry_wait_quality_v1(
        decision_row={
            "symbol": "NAS100",
            "action": "BUY",
            "entry_wait_selected": 1,
            "entry_wait_decision": "wait_soft_helper_block",
            "anchor_price": 100.0,
        },
        future_bars=_future_bars(
            (101, 100.0, 100.28, 99.98, 100.24),
            (102, 100.24, 100.34, 99.70, 99.78),
        ),
        next_entry_row={
            "time": "2026-04-03T10:06:00+09:00",
            "action": "BUY",
            "entry_fill_price": 100.28,
            "outcome": "entered",
        },
        next_closed_trade_row={
            "profit": -1.5,
            "exit_reason": "fail_now",
        },
    )

    assert result["quality_label"] == ENTRY_WAIT_QUALITY_LABEL_DELAYED_LOSS
    assert result["quality_score"] < 0.0


def test_entry_wait_quality_allows_reentry_label_without_future_bars_when_trade_is_linked():
    result = evaluate_entry_wait_quality_v1(
        decision_row={
            "symbol": "NAS100",
            "action": "BUY",
            "entry_wait_selected": 1,
            "entry_wait_decision": "wait_soft_helper_block",
            "anchor_price": 100.0,
        },
        future_bars=[],
        next_entry_row={
            "time": "2026-04-03T10:06:00+09:00",
            "action": "BUY",
            "entry_fill_price": 99.76,
            "outcome": "entered",
        },
        next_closed_trade_row={
            "profit": 1.5,
            "exit_reason": "tp1",
        },
    )

    assert result["quality_label"] == ENTRY_WAIT_QUALITY_LABEL_BETTER_ENTRY
    assert result["label_status"] == "VALID"


def test_entry_wait_quality_marks_insufficient_without_anchor_or_future():
    result = evaluate_entry_wait_quality_v1(
        decision_row={
            "symbol": "NAS100",
            "action": "BUY",
            "entry_wait_selected": 1,
        },
        future_bars=[],
    )

    assert result["quality_label"] == ENTRY_WAIT_QUALITY_LABEL_INSUFFICIENT
    assert result["label_status"] == "INSUFFICIENT_EVIDENCE"


def test_entry_wait_quality_summary_and_markdown_render():
    summary = build_entry_wait_quality_summary_v1(
        [
            {"label_status": "VALID", "quality_label": ENTRY_WAIT_QUALITY_LABEL_BETTER_ENTRY, "quality_score": 0.6},
            {"label_status": "VALID", "quality_label": ENTRY_WAIT_QUALITY_LABEL_DELAYED_LOSS, "quality_score": -0.7},
            {"label_status": "INSUFFICIENT_EVIDENCE", "quality_label": ENTRY_WAIT_QUALITY_LABEL_INSUFFICIENT, "quality_score": 0.0},
        ]
    )

    markdown = render_entry_wait_quality_markdown(summary)

    assert summary["rows_total"] == 3
    assert summary["rows_valid"] == 2
    assert summary["positive_rows"] == 1
    assert summary["negative_rows"] == 1
    assert "better_entry_after_wait: 1" in markdown
    assert "delayed_loss_after_wait: 1" in markdown
