from types import SimpleNamespace
from pathlib import Path

import pandas as pd

from backend.services.exit_manage_positions import (
    _ensure_exit_checkpoint_assignment,
    _record_exit_manage_checkpoint,
    _resolve_hold_checkpoint_recording,
)


class _DummyRuntime:
    def __init__(self):
        self.latest_signal_by_symbol = {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "time": 1775808600.0,
                "timestamp": "2026-04-10T14:30:00+09:00",
                "observe_action": "WAIT",
                "observe_side": "BUY",
                "action": "BUY",
                "buy_score": 248.0,
                "sell_score": 112.0,
                "wait_score": 28.0,
            }
        }
        self.path_leg_state_by_symbol = {}
        self.path_checkpoint_state_by_symbol = {}


class _DummyService:
    def __init__(self):
        self.runtime = _DummyRuntime()
        self.partial_done = {}
        self.be_moved = {}


def test_record_exit_manage_checkpoint_captures_runner_secured_profit_row(tmp_path: Path) -> None:
    service = _DummyService()
    service.partial_done[101] = True
    service.be_moved[101] = True
    latest_signal_row, checkpoint_state = _ensure_exit_checkpoint_assignment(
        service,
        symbol="XAUUSD",
        runtime_row=service.runtime.latest_signal_by_symbol["XAUUSD"],
    )

    payload = _record_exit_manage_checkpoint(
        service,
        symbol="XAUUSD",
        latest_signal_row=latest_signal_row,
        checkpoint_state=checkpoint_state,
        direction="BUY",
        ticket_i=101,
        pos=SimpleNamespace(volume=0.02, price_open=2301.5),
        trade_ctx={
            "lot": 0.02,
            "decision_row_key": "decision_key_101",
            "runtime_snapshot_key": "runtime_signal_row_v1|symbol=XAUUSD|anchor_field=time|anchor_value=1775808600.0|hint=BOTH",
            "trade_link_key": "trade_link_101",
        },
        profit=1.25,
        peak_profit=1.75,
        source="exit_manage_runner",
        final_stage="runner_preservation:partial_then_runner_hold",
        reason="runner_preservation_active",
        outcome="runner_hold",
        csv_path=tmp_path / "checkpoint_rows.csv",
        detail_path=tmp_path / "checkpoint_rows.detail.jsonl",
    )

    frame = pd.read_csv(tmp_path / "checkpoint_rows.csv", encoding="utf-8-sig")
    latest = frame.iloc[-1]
    assert payload["payload"]["row"]["source"] == "exit_manage_runner"
    assert latest["position_side"] == "BUY"
    assert latest["unrealized_pnl_state"] == "OPEN_PROFIT"
    assert str(latest["runner_secured"]).lower() in {"true", "1"}
    assert float(latest["current_profit"]) == 1.25
    assert latest["checkpoint_rule_family_hint"] == "runner_secured_continuation"
    assert latest["exit_stage_family"] == "runner"
    assert float(latest["giveback_from_peak"]) > 0.0
    assert str(latest["management_action_label"]).strip() != ""


def test_record_exit_manage_checkpoint_captures_open_loss_hold_row(tmp_path: Path) -> None:
    service = _DummyService()
    latest_signal_row, checkpoint_state = _ensure_exit_checkpoint_assignment(
        service,
        symbol="XAUUSD",
        runtime_row=service.runtime.latest_signal_by_symbol["XAUUSD"],
    )

    _record_exit_manage_checkpoint(
        service,
        symbol="XAUUSD",
        latest_signal_row=latest_signal_row,
        checkpoint_state=checkpoint_state,
        direction="BUY",
        ticket_i=202,
        pos=SimpleNamespace(volume=0.02, price_open=2301.5),
        trade_ctx={"lot": 0.02},
        profit=-0.62,
        peak_profit=0.18,
        source="exit_manage_hold",
        final_stage="adverse_wait_delay",
        reason="adverse_wait_delay",
        outcome="hold",
        csv_path=tmp_path / "checkpoint_rows.csv",
        detail_path=tmp_path / "checkpoint_rows.detail.jsonl",
    )

    frame = pd.read_csv(tmp_path / "checkpoint_rows.csv", encoding="utf-8-sig")
    latest = frame.iloc[-1]
    assert latest["source"] == "exit_manage_hold"
    assert latest["unrealized_pnl_state"] == "OPEN_LOSS"
    assert str(latest["runner_secured"]).lower() in {"false", "0"}
    assert float(latest["mae_since_entry"]) == 0.62
    assert latest["checkpoint_rule_family_hint"] == "active_open_loss"
    assert latest["exit_stage_family"] == "hold"
    assert float(latest["giveback_from_peak"]) >= 0.8


def test_resolve_hold_checkpoint_recording_promotes_secured_hold_to_runner_source() -> None:
    service = _DummyService()
    service.partial_done[303] = True
    service.be_moved[303] = True

    payload = _resolve_hold_checkpoint_recording(
        service,
        latest_signal_row={
            "exit_wait_decision_family": "hold_continue",
            "exit_wait_bridge_status": "aligned_hold_continue",
            "exit_wait_state_family": "active_hold",
        },
        ticket_i=303,
        final_stage="no_exit",
        reason="no_exit",
        outcome="hold",
    )

    assert payload["source"] == "exit_manage_runner"
    assert payload["final_stage"] == "runner_observe:no_exit"
    assert payload["outcome"] == "runner_hold"
