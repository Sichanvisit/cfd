import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_checkpoint_open_trade_backfill.py"
spec = importlib.util.spec_from_file_location("build_checkpoint_open_trade_backfill", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


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
            INSERT INTO open_trades VALUES (
              '101','BTCUSD','BUY','0.01','2026-04-10 13:50:34','1775796634','71887.31','0.0',
              'decision_key_101','runtime_signal_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=1775796919.0|hint=BOTH',
              'trade_link_101','range_lower_reversal_buy','support_hold_profile','lower_support_fail','tight_protect','0.0','0.0','-0.03','runner_hold','runner_preservation_active','OPEN'
            )
            """
        )
        con.commit()
    finally:
        con.close()


def test_build_checkpoint_open_trade_backfill_script_writes_artifact(tmp_path: Path) -> None:
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
    json_output_path = tmp_path / "checkpoint_open_trade_backfill_latest.json"

    rc = module.main(
        [
            "--runtime-status-detail-path",
            str(runtime_status_detail_path),
            "--trade-db-path",
            str(trade_db_path),
            "--checkpoint-rows-path",
            str(checkpoint_rows_path),
            "--checkpoint-detail-path",
            str(detail_path),
            "--json-output-path",
            str(json_output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["appended_count"] == 1
