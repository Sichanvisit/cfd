import pandas as pd

from backend.services.forecast_state25_seed_enrichment import (
    apply_forecast_state25_seed_enrichment,
    build_forecast_state25_seed_enrichment_plan,
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
            "forecast_state25_scene_family": "",
            "forecast_state25_group_hint": "",
            "forecast_confirm_side": "",
            "forecast_decision_hint": "",
            "forecast_wait_confirm_gap": 0.0,
            "forecast_hold_exit_gap": 0.0,
            "forecast_same_side_flip_gap": 0.0,
            "forecast_belief_barrier_tension_gap": 0.0,
            "forecast_transition_outcome_status": "",
            "forecast_management_outcome_status": "",
            "forecast_state25_bridge_quality_status": "",
            "forecast_state25_bridge_reason": "",
        }
    )
    row.update(overrides)
    return row


def _bridge_row(
    *,
    ticket: int,
    decision_row_key: str,
    scene_family: str,
    group_hint: str,
    decision_hint: str,
    confirm_side: str,
    wait_confirm_gap: float,
    hold_exit_gap: float,
    same_side_flip_gap: float,
    belief_barrier_tension_gap: float,
    transition_status: str,
    management_status: str,
    bridge_quality_status: str,
):
    return {
        "row_key": decision_row_key,
        "signal_bar_ts": 1775195588,
        "matched_closed_trade_row": {
            "ticket": str(ticket),
            "symbol": "BTCUSD",
            "open_ts": "1775195588",
            "decision_row_key": decision_row_key,
        },
        "state25_runtime_hint_v1": {
            "scene_family": scene_family,
            "scene_group_hint": group_hint,
        },
        "forecast_runtime_summary_v1": {
            "confirm_side": confirm_side,
            "decision_hint": decision_hint,
            "wait_confirm_gap": wait_confirm_gap,
            "hold_exit_gap": hold_exit_gap,
            "same_side_flip_gap": same_side_flip_gap,
            "belief_barrier_tension_gap": belief_barrier_tension_gap,
        },
        "outcome_label_compact_summary_v1": {
            "transition_label_status": transition_status,
            "management_label_status": management_status,
        },
        "bridge_quality_status": bridge_quality_status,
        "economic_target_summary": {
            "available": True,
            "position_key": ticket,
            "learning_total_score": 0.62,
        },
        "entry_wait_quality_label": "better_entry_after_wait",
        "entry_wait_quality_result_v1": {
            "quality_score": 1.0,
        },
    }


def test_forecast_state25_seed_enrichment_applies_selected_bridge_values():
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
                scene_family="pattern_12",
                group_hint="C",
                decision_hint="CONFIRM_BIASED",
                confirm_side="BUY",
                wait_confirm_gap=0.24,
                hold_exit_gap=0.16,
                same_side_flip_gap=0.09,
                belief_barrier_tension_gap=0.12,
                transition_status="VALID",
                management_status="VALID",
                bridge_quality_status="full_outcome_bridge",
            ),
            _bridge_row(
                ticket=202,
                decision_row_key="BTCUSD|1775196600|2",
                scene_family="pattern_14",
                group_hint="A",
                decision_hint="WAIT_BIASED",
                confirm_side="SELL",
                wait_confirm_gap=-0.18,
                hold_exit_gap=-0.11,
                same_side_flip_gap=-0.03,
                belief_barrier_tension_gap=-0.08,
                transition_status="INSUFFICIENT_FUTURE_BARS",
                management_status="VALID",
                bridge_quality_status="partial_outcome_bridge",
            ),
        ]
    }

    updated, report = apply_forecast_state25_seed_enrichment(frame, replay_report=replay_report)

    first = updated.iloc[0]
    second = updated.iloc[1]

    assert first["forecast_state25_scene_family"] == "pattern_12"
    assert first["forecast_state25_group_hint"] == "C"
    assert first["forecast_confirm_side"] == "BUY"
    assert first["forecast_decision_hint"] == "CONFIRM_BIASED"
    assert float(first["forecast_wait_confirm_gap"]) == 0.24
    assert first["forecast_transition_outcome_status"] == "valid"
    assert first["forecast_management_outcome_status"] == "valid"
    assert first["forecast_state25_bridge_quality_status"] == "full_outcome_bridge"
    assert "linked_bridge_rows=1" in first["forecast_state25_bridge_reason"]

    assert second["forecast_state25_scene_family"] == "pattern_14"
    assert second["forecast_decision_hint"] == "WAIT_BIASED"
    assert second["forecast_transition_outcome_status"] == "insufficient_future_bars"
    assert second["forecast_management_outcome_status"] == "valid"

    assert report["matched_trade_rows"] == 2
    assert report["updated_rows"] == 2
    assert report["scene_family_distribution"]["pattern_12"] == 1
    assert report["decision_hint_distribution"]["WAIT_BIASED"] == 1


def test_forecast_state25_seed_enrichment_respects_existing_columns_without_overwrite():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _closed_row(
                    ticket=101,
                    decision_row_key="BTCUSD|1775195588|1",
                    forecast_state25_scene_family="pattern_5",
                    forecast_decision_hint="BALANCED",
                    forecast_transition_outcome_status="valid",
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
                scene_family="pattern_12",
                group_hint="C",
                decision_hint="CONFIRM_BIASED",
                confirm_side="BUY",
                wait_confirm_gap=0.24,
                hold_exit_gap=0.16,
                same_side_flip_gap=0.09,
                belief_barrier_tension_gap=0.12,
                transition_status="VALID",
                management_status="VALID",
                bridge_quality_status="full_outcome_bridge",
            ),
        ]
    }

    plan = build_forecast_state25_seed_enrichment_plan(
        frame,
        replay_report=replay_report,
        overwrite_existing=False,
    )
    updated, report = apply_forecast_state25_seed_enrichment(
        frame,
        replay_report=replay_report,
        overwrite_existing=False,
    )

    assert plan["existing_enriched_rows"] == 1
    assert plan["skipped_existing_rows"] == 1
    assert report["updated_rows"] == 0
    assert updated.iloc[0]["forecast_state25_scene_family"] == "pattern_5"
