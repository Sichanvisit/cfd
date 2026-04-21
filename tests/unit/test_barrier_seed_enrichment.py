import pandas as pd

from backend.services.barrier_seed_enrichment import (
    apply_barrier_seed_enrichment,
    build_barrier_seed_enrichment_plan,
)
from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df


def _closed_row(**overrides):
    row = {column: "" for column in TRADE_COLUMNS}
    row.update(
        {
            "ticket": 101,
            "symbol": "BTCUSD",
            "direction": "BUY",
            "open_ts": 1775195588,
            "open_price": 100.1,
            "profit": 1.8,
            "status": "CLOSED",
            "decision_row_key": "BTCUSD|1775195588|1",
            "barrier_anchor_side": "",
            "barrier_anchor_context": "",
            "barrier_horizon_bars": 0,
            "barrier_primary_component": "",
            "barrier_outcome_label": "",
            "barrier_label_confidence": "",
            "barrier_bridge_quality_status": "",
            "barrier_outcome_reason": "",
            "barrier_cost_loss_avoided_r": 0.0,
            "barrier_cost_profit_missed_r": 0.0,
            "barrier_cost_wait_value_r": 0.0,
        }
    )
    row.update(overrides)
    return row


def _bridge_row(
    *,
    ticket: int,
    decision_row_key: str,
    anchor_side: str,
    anchor_context: str,
    horizon_bars: int,
    primary_component: str,
    label: str,
    confidence: str,
    loss_avoided_r: float,
    profit_missed_r: float,
    wait_value_r: float,
    bridge_quality_status: str = "labeled",
):
    return {
        "row_key": decision_row_key,
        "time": 1775195588,
        "matched_closed_trade_row": {
            "ticket": str(ticket),
            "symbol": "BTCUSD",
            "open_ts": "1775195588",
            "decision_row_key": decision_row_key,
        },
        "barrier_outcome_bridge_v1": {
            "barrier_anchor_side": anchor_side,
            "barrier_anchor_context": anchor_context,
            "barrier_horizon_bars": horizon_bars,
            "barrier_primary_component": primary_component,
            "barrier_outcome_label": label,
            "barrier_label_confidence": confidence,
            "barrier_outcome_reason": label,
            "bridge_quality_status": bridge_quality_status,
            "barrier_cost_loss_avoided_r": loss_avoided_r,
            "barrier_cost_profit_missed_r": profit_missed_r,
            "barrier_cost_wait_value_r": wait_value_r,
            "barrier_conflict_resolver_v1": {
                "score_gap": 0.22,
            },
        },
    }


def test_barrier_seed_enrichment_applies_selected_bridge_values():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _closed_row(ticket=101, decision_row_key="BTCUSD|1775195588|1"),
                _closed_row(ticket=202, decision_row_key="BTCUSD|1775196600|2", open_ts=1775196600, open_price=100.5),
            ],
            columns=TRADE_COLUMNS,
        )
    )
    replay_report = {
        "rows": [
            _bridge_row(
                ticket=101,
                decision_row_key="BTCUSD|1775195588|1",
                anchor_side="BUY",
                anchor_context="blocked_entry",
                horizon_bars=6,
                primary_component="late_entry_barrier",
                label="avoided_loss",
                confidence="high",
                loss_avoided_r=1.4,
                profit_missed_r=0.1,
                wait_value_r=0.2,
            ),
            _bridge_row(
                ticket=202,
                decision_row_key="BTCUSD|1775196600|2",
                anchor_side="SELL",
                anchor_context="relief_release",
                horizon_bars=6,
                primary_component="conflict_barrier",
                label="relief_success",
                confidence="medium",
                loss_avoided_r=0.3,
                profit_missed_r=0.2,
                wait_value_r=0.8,
            ),
        ]
    }

    updated, report = apply_barrier_seed_enrichment(frame, replay_report=replay_report)

    first = updated.iloc[0]
    second = updated.iloc[1]

    assert first["barrier_anchor_side"] == "BUY"
    assert first["barrier_anchor_context"] == "blocked_entry"
    assert int(float(first["barrier_horizon_bars"])) == 6
    assert first["barrier_primary_component"] == "late_entry_barrier"
    assert first["barrier_outcome_label"] == "avoided_loss"
    assert first["barrier_label_confidence"] == "high"
    assert first["barrier_bridge_quality_status"] == "labeled"
    assert float(first["barrier_cost_loss_avoided_r"]) == 1.4
    assert "linked_bridge_rows=1" in first["barrier_outcome_reason"]

    assert second["barrier_anchor_side"] == "SELL"
    assert second["barrier_anchor_context"] == "relief_release"
    assert second["barrier_outcome_label"] == "relief_success"
    assert second["barrier_label_confidence"] == "medium"
    assert float(second["barrier_cost_wait_value_r"]) == 0.8

    assert report["matched_trade_rows"] == 2
    assert report["updated_rows"] == 2
    assert report["label_distribution"]["avoided_loss"] == 1
    assert report["confidence_distribution"]["medium"] == 1
    assert report["primary_component_distribution"]["conflict_barrier"] == 1


def test_barrier_seed_enrichment_respects_existing_columns_without_overwrite():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _closed_row(
                    ticket=101,
                    decision_row_key="BTCUSD|1775195588|1",
                    barrier_outcome_label="overblock",
                    barrier_label_confidence="high",
                    barrier_primary_component="middle_chop_barrier",
                ),
            ],
            columns=TRADE_COLUMNS,
        )
    )
    replay_report = {
        "rows": [
            _bridge_row(
                ticket=101,
                decision_row_key="BTCUSD|1775195588|1",
                anchor_side="BUY",
                anchor_context="blocked_entry",
                horizon_bars=6,
                primary_component="late_entry_barrier",
                label="avoided_loss",
                confidence="high",
                loss_avoided_r=1.4,
                profit_missed_r=0.1,
                wait_value_r=0.2,
            ),
        ]
    }

    plan = build_barrier_seed_enrichment_plan(
        frame,
        replay_report=replay_report,
        overwrite_existing=False,
    )
    updated, report = apply_barrier_seed_enrichment(
        frame,
        replay_report=replay_report,
        overwrite_existing=False,
    )

    assert plan["existing_enriched_rows"] == 1
    assert plan["skipped_existing_rows"] == 1
    assert report["updated_rows"] == 0
    assert updated.iloc[0]["barrier_outcome_label"] == "overblock"
