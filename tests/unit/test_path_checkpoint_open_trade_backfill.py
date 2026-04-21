import json
import sqlite3
from pathlib import Path

import pandas as pd

from backend.services.path_checkpoint_open_trade_backfill import (
    backfill_open_trade_checkpoint_rows,
)


def _make_open_trade_db(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(
            """
            CREATE TABLE open_trades (
              ticket TEXT,
              symbol TEXT,
              direction TEXT,
              lot TEXT,
              open_time TEXT,
              open_ts TEXT,
              open_price TEXT,
              profit TEXT,
              decision_row_key TEXT,
              runtime_snapshot_key TEXT,
              trade_link_key TEXT,
              entry_setup_id TEXT,
              management_profile_id TEXT,
              invalidation_id TEXT,
              exit_profile TEXT,
              peak_profit_at_exit TEXT,
              giveback_usd TEXT,
              shock_at_profit TEXT,
              exit_wait_decision_family TEXT,
              exit_wait_bridge_status TEXT,
              status TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE closed_trades (
              ticket TEXT,
              symbol TEXT,
              direction TEXT,
              lot TEXT,
              open_time TEXT,
              open_ts TEXT,
              open_price TEXT,
              profit TEXT,
              decision_row_key TEXT,
              runtime_snapshot_key TEXT,
              trade_link_key TEXT,
              entry_setup_id TEXT,
              management_profile_id TEXT,
              invalidation_id TEXT,
              exit_profile TEXT,
              exit_policy_stage TEXT,
              exit_wait_state_family TEXT,
              exit_wait_hold_class TEXT,
              peak_profit_at_exit TEXT,
              giveback_usd TEXT,
              shock_at_profit TEXT,
              exit_wait_decision_family TEXT,
              exit_wait_bridge_status TEXT,
              exit_reason TEXT,
              close_ts TEXT,
              updated_at TEXT,
              status TEXT
            )
            """
        )
        con.execute(
            """
            INSERT INTO open_trades VALUES (
              '101',
              'BTCUSD',
              'BUY',
              '0.01',
              '2026-04-10 13:50:34',
              '1775796634',
              '71887.31',
              '0.0',
              'decision_key_101',
              'runtime_signal_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=1775796919.0|hint=BOTH',
              'trade_link_101',
              'range_lower_reversal_buy',
              'support_hold_profile',
              'lower_support_fail',
              'tight_protect',
              '0.0',
              '0.0',
              '-0.03',
              'runner_hold',
              'runner_preservation_active',
              'OPEN'
            )
            """
        )
        con.commit()
    finally:
        con.close()


def _insert_closed_trade_runner_row(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(
            """
            INSERT INTO closed_trades VALUES (
              '202',
              'BTCUSD',
              'BUY',
              '0.01',
              '2026-04-10 13:40:34',
              '1775796034',
              '71880.10',
              '0.17',
              'decision_key_202',
              'runtime_signal_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=1775797019.0|hint=BOTH',
              'trade_link_202',
              'range_lower_reversal_buy',
              'support_hold_profile',
              'lower_support_fail',
              'tight_protect',
              'mid',
              'active_hold',
              'soft_hold',
              '0.29',
              '0.04',
              '0.17',
              'hold_continue',
              'aligned_hold_continue',
              'Lock Exit, runner hold continue',
              '1775797234',
              '1775797240',
              'CLOSED'
            )
            """
        )
        con.commit()
    finally:
        con.close()


def test_backfill_open_trade_checkpoint_rows_appends_position_side_row(tmp_path: Path) -> None:
    runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    runtime_status_detail_path.write_text(
        json.dumps(
            {
                "updated_at": "2026-04-10T13:55:20+09:00",
                "latest_signal_by_symbol": {
                    "BTCUSD": {
                        "symbol": "BTCUSD",
                        "time": 1775796919.9469345,
                        "timestamp": "2026-04-10T13:55:19.946934",
                        "action": "SELL",
                        "observe_action": "WAIT",
                        "observe_side": "SELL",
                        "blocked_by": "pyramid_chase_lower_blocked",
                        "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=1775796919.0|hint=BOTH",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T13:22:18.261542+09:00",
                "source": "bootstrap_runtime",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "leg_id": "BTCUSD_UP_20260410T132218_L0001",
                "leg_direction": "UP",
                "checkpoint_id": "BTCUSD_UP_20260410T132218_L0001_CP001",
                "checkpoint_type": "INITIAL_PUSH",
                "checkpoint_index_in_leg": 1,
                "checkpoint_transition_reason": "leg_start_checkpoint_opened",
                "bars_since_leg_start": 0,
                "bars_since_last_push": 0,
                "bars_since_last_checkpoint": 0,
                "position_side": "FLAT",
                "position_size_fraction": 0.0,
                "avg_entry_price": 0.0,
                "realized_pnl_state": "NONE",
                "unrealized_pnl_state": "FLAT",
                "runner_secured": False,
                "mfe_since_entry": 0.0,
                "mae_since_entry": 0.0,
                "current_profit": 0.0,
                "runtime_continuation_odds": 0.63,
                "runtime_reversal_odds": 0.22,
                "runtime_hold_quality_score": 0.42,
                "runtime_partial_exit_ev": 0.19,
                "runtime_full_exit_risk": 0.08,
                "runtime_rebuy_readiness": 0.34,
                "runtime_score_reason": "follow_through_surface::continuation_hold_bias",
                "ticket": 0,
                "action": "",
                "outcome": "",
                "blocked_by": "forecast_guard",
                "observe_action": "WAIT",
                "observe_side": "BUY",
                "decision_row_key": "",
                "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=1775794938.261542|hint=BOTH",
                "trade_link_key": "",
            }
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    detail_path = tmp_path / "checkpoint_rows.detail.jsonl"
    detail_path.write_text("", encoding="utf-8")
    trade_db_path = tmp_path / "trades.db"
    _make_open_trade_db(trade_db_path)

    payload = backfill_open_trade_checkpoint_rows(
        runtime_status_detail_path=runtime_status_detail_path,
        trade_db_path=trade_db_path,
        checkpoint_rows_path=checkpoint_rows_path,
        checkpoint_detail_path=detail_path,
    )

    assert payload["summary"]["appended_count"] == 1
    frame = pd.read_csv(checkpoint_rows_path, encoding="utf-8-sig")
    latest = frame.iloc[-1]
    assert latest["source"] == "open_trade_backfill"
    assert latest["position_side"] == "BUY"
    assert latest["unrealized_pnl_state"] == "OPEN_LOSS"
    assert str(latest["runner_secured"]).lower() in {"true", "1"}
    assert latest["checkpoint_rule_family_hint"] == "runner_secured_continuation"
    assert latest["exit_stage_family"] == "runner"
    assert float(latest["giveback_from_peak"]) >= 0.03
    assert int(latest["ticket"]) == 101


def test_backfill_open_trade_checkpoint_rows_carries_forward_runner_context(tmp_path: Path) -> None:
    runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    runtime_status_detail_path.write_text(
        json.dumps(
            {
                "updated_at": "2026-04-10T13:55:20+09:00",
                "latest_signal_by_symbol": {
                    "BTCUSD": {
                        "symbol": "BTCUSD",
                        "time": 1775796919.9469345,
                        "timestamp": "2026-04-10T13:55:19.946934",
                        "action": "SELL",
                        "observe_action": "WAIT",
                        "observe_side": "SELL",
                        "blocked_by": "pyramid_chase_lower_blocked",
                        "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=1775796919.0|hint=BOTH",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T13:22:18.261542+09:00",
                "source": "exit_manage_runner",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "leg_id": "BTCUSD_UP_20260410T132218_L0001",
                "leg_direction": "UP",
                "checkpoint_id": "BTCUSD_UP_20260410T132218_L0001_CP002",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_index_in_leg": 2,
                "checkpoint_transition_reason": "checkpoint_progression",
                "bars_since_leg_start": 1,
                "bars_since_last_push": 0,
                "bars_since_last_checkpoint": 0,
                "position_side": "BUY",
                "position_size_fraction": 0.5,
                "avg_entry_price": 71887.31,
                "realized_pnl_state": "PARTIAL_LOCKED",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "runner_secured": True,
                "mfe_since_entry": 0.12,
                "mae_since_entry": 0.0,
                "current_profit": 0.08,
                "giveback_from_peak": 0.04,
                "giveback_ratio": 0.33,
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "exit_stage_family": "runner",
                "runtime_continuation_odds": 0.63,
                "runtime_reversal_odds": 0.22,
                "runtime_hold_quality_score": 0.52,
                "runtime_partial_exit_ev": 0.29,
                "runtime_full_exit_risk": 0.08,
                "runtime_rebuy_readiness": 0.34,
                "runtime_score_reason": "continuation_hold_surface::runner_lock_bias",
                "ticket": 101,
                "action": "BUY",
                "outcome": "runner_hold",
                "blocked_by": "",
                "observe_action": "WAIT",
                "observe_side": "BUY",
                "decision_row_key": "decision_key_101",
                "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=1775794938.261542|hint=BOTH",
                "trade_link_key": "trade_link_101",
            }
        ]
    ).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    detail_path = tmp_path / "checkpoint_rows.detail.jsonl"
    detail_path.write_text("", encoding="utf-8")
    trade_db_path = tmp_path / "trades.db"
    _make_open_trade_db(trade_db_path)

    payload = backfill_open_trade_checkpoint_rows(
        runtime_status_detail_path=runtime_status_detail_path,
        trade_db_path=trade_db_path,
        checkpoint_rows_path=checkpoint_rows_path,
        checkpoint_detail_path=detail_path,
    )

    assert payload["summary"]["appended_count"] == 1
    frame = pd.read_csv(checkpoint_rows_path, encoding="utf-8-sig")
    latest = frame.iloc[-1]
    assert latest["checkpoint_rule_family_hint"] == "runner_secured_continuation"
    assert latest["exit_stage_family"] == "runner"
    assert str(latest["runner_secured"]).lower() in {"true", "1"}


def test_backfill_open_trade_checkpoint_rows_appends_closed_trade_runner_bootstrap_row(tmp_path: Path) -> None:
    runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    runtime_status_detail_path.write_text(
        json.dumps(
            {
                "updated_at": "2026-04-10T14:05:20+09:00",
                "latest_signal_by_symbol": {
                    "BTCUSD": {
                        "symbol": "BTCUSD",
                        "time": 1775797319.9469345,
                        "timestamp": "2026-04-10T14:01:59.946934",
                        "action": "BUY",
                        "observe_action": "WAIT",
                        "observe_side": "BUY",
                        "blocked_by": "hold_continue",
                        "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=1775797319.0|hint=BOTH",
                        "exit_wait_decision_family": "hold_continue",
                        "exit_wait_bridge_status": "aligned_hold_continue",
                        "exit_wait_state_family": "active_hold",
                        "exit_wait_hold_class": "soft_hold",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    checkpoint_rows_path = tmp_path / "checkpoint_rows.csv"
    pd.DataFrame([], columns=["generated_at"]).to_csv(checkpoint_rows_path, index=False, encoding="utf-8-sig")
    detail_path = tmp_path / "checkpoint_rows.detail.jsonl"
    detail_path.write_text("", encoding="utf-8")
    trade_db_path = tmp_path / "trades.db"
    _make_open_trade_db(trade_db_path)
    _insert_closed_trade_runner_row(trade_db_path)

    payload = backfill_open_trade_checkpoint_rows(
        runtime_status_detail_path=runtime_status_detail_path,
        trade_db_path=trade_db_path,
        checkpoint_rows_path=checkpoint_rows_path,
        checkpoint_detail_path=detail_path,
    )

    assert payload["summary"]["closed_candidate_count"] >= 1
    assert payload["summary"]["closed_appended_count"] >= 1
    assert payload["summary"]["runner_secured_row_count_after"] >= 1
    frame = pd.read_csv(checkpoint_rows_path, encoding="utf-8-sig")
    closed_rows = frame.loc[frame["source"] == "closed_trade_runner_backfill"].copy()
    assert not closed_rows.empty
    latest = closed_rows.iloc[-1]
    assert latest["checkpoint_rule_family_hint"] == "runner_secured_continuation"
    assert latest["exit_stage_family"] == "runner"
    assert str(latest["runner_secured"]).lower() in {"true", "1"}
