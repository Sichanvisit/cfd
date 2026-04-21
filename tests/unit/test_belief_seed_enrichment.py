import pandas as pd

from backend.services.belief_seed_enrichment import (
    apply_belief_seed_enrichment,
    build_belief_seed_enrichment_plan,
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
            "belief_anchor_side": "",
            "belief_anchor_context": "",
            "belief_horizon_bars": 0,
            "belief_outcome_label": "",
            "belief_label_confidence": "",
            "belief_break_signature": "",
            "belief_bridge_quality_status": "",
            "belief_outcome_reason": "",
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
    label: str,
    confidence: str,
    break_signature: str,
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
        "belief_outcome_bridge_v1": {
            "belief_anchor_side": anchor_side,
            "belief_anchor_context": anchor_context,
            "belief_horizon_bars": horizon_bars,
            "belief_outcome_label": label,
            "belief_label_confidence": confidence,
            "belief_break_signature": break_signature,
            "belief_outcome_reason": label,
            "bridge_quality_status": bridge_quality_status,
            "belief_conflict_resolver_v1": {
                "score_gap": 0.22,
            },
        },
    }


def test_belief_seed_enrichment_applies_selected_bridge_values():
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
                anchor_context="hold_thesis",
                horizon_bars=6,
                label="correct_hold",
                confidence="high",
                break_signature="thesis_persistence_valid",
            ),
            _bridge_row(
                ticket=202,
                decision_row_key="BTCUSD|1775196600|2",
                anchor_side="SELL",
                anchor_context="flip_thesis",
                horizon_bars=6,
                label="premature_flip",
                confidence="medium",
                break_signature="flip_reclaim_failure",
            ),
        ]
    }

    updated, report = apply_belief_seed_enrichment(frame, replay_report=replay_report)

    first = updated.iloc[0]
    second = updated.iloc[1]

    assert first["belief_anchor_side"] == "BUY"
    assert first["belief_anchor_context"] == "hold_thesis"
    assert int(float(first["belief_horizon_bars"])) == 6
    assert first["belief_outcome_label"] == "correct_hold"
    assert first["belief_label_confidence"] == "high"
    assert first["belief_break_signature"] == "thesis_persistence_valid"
    assert first["belief_bridge_quality_status"] == "labeled"
    assert "linked_bridge_rows=1" in first["belief_outcome_reason"]

    assert second["belief_anchor_side"] == "SELL"
    assert second["belief_anchor_context"] == "flip_thesis"
    assert second["belief_outcome_label"] == "premature_flip"
    assert second["belief_label_confidence"] == "medium"

    assert report["matched_trade_rows"] == 2
    assert report["updated_rows"] == 2
    assert report["label_distribution"]["correct_hold"] == 1
    assert report["confidence_distribution"]["medium"] == 1


def test_belief_seed_enrichment_respects_existing_columns_without_overwrite():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _closed_row(
                    ticket=101,
                    decision_row_key="BTCUSD|1775195588|1",
                    belief_outcome_label="wrong_hold",
                    belief_label_confidence="high",
                    belief_break_signature="belief_decay_hold_failure",
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
                anchor_context="hold_thesis",
                horizon_bars=6,
                label="correct_hold",
                confidence="high",
                break_signature="thesis_persistence_valid",
            ),
        ]
    }

    plan = build_belief_seed_enrichment_plan(
        frame,
        replay_report=replay_report,
        overwrite_existing=False,
    )
    updated, report = apply_belief_seed_enrichment(
        frame,
        replay_report=replay_report,
        overwrite_existing=False,
    )

    assert plan["existing_enriched_rows"] == 1
    assert plan["skipped_existing_rows"] == 1
    assert report["updated_rows"] == 0
    assert updated.iloc[0]["belief_outcome_label"] == "wrong_hold"
