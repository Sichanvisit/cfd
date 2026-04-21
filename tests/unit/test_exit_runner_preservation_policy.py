from backend.core.trade_constants import ORDER_TYPE_BUY
from backend.services.exit_runner_preservation_policy import (
    resolve_exit_runner_preservation_candidate_v1,
)


def test_exit_runner_preservation_candidate_builds_partial_then_runner_hold_for_supportive_xau():
    out = resolve_exit_runner_preservation_candidate_v1(
        symbol="XAUUSD",
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        position_volume=0.50,
        selected_candidate_kind="target_exit",
        selected_reason="Target",
        profit=1.30,
        peak_profit=1.60,
        giveback_usd=0.30,
        min_net_guard=0.20,
        roundtrip_cost=0.02,
        favorable_move_pct=0.0035,
        dynamic_move_pct=0.0012,
        hold_score=150,
        lock_score=165,
        hold_threshold=140,
        partial_done=False,
        be_moved=False,
        profit_stop_target_sl=100.12,
    )

    assert out["contract_version"] == "exit_runner_preservation_candidate_v1"
    assert out["should_execute"] is True
    assert out["skip_full_exit"] is True
    assert out["candidate_kind"] == "partial_then_runner_hold"
    assert float(out["lock_price"]) > 100.0
    partial = dict(out["partial_candidate"])
    assert partial["should_execute"] is True
    assert float(partial["partial_volume"]) > 0.0


def test_exit_runner_preservation_candidate_builds_runner_lock_only_when_partial_already_done():
    out = resolve_exit_runner_preservation_candidate_v1(
        symbol="BTCUSD",
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        position_volume=0.40,
        selected_candidate_kind="lock_exit",
        selected_reason="Lock Exit",
        profit=1.10,
        peak_profit=1.40,
        giveback_usd=0.20,
        min_net_guard=0.20,
        roundtrip_cost=0.02,
        favorable_move_pct=0.0030,
        dynamic_move_pct=0.0010,
        hold_score=165,
        lock_score=160,
        hold_threshold=140,
        partial_done=True,
        be_moved=True,
        profit_stop_target_sl=100.18,
    )

    assert out["should_execute"] is True
    assert out["candidate_kind"] == "runner_lock_only"
    assert float(out["lock_price"]) > 100.0


def test_exit_runner_preservation_candidate_skips_when_giveback_is_too_large():
    out = resolve_exit_runner_preservation_candidate_v1(
        symbol="XAUUSD",
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        position_volume=0.50,
        selected_candidate_kind="lock_exit",
        selected_reason="Lock Exit",
        profit=0.55,
        peak_profit=1.70,
        giveback_usd=1.15,
        min_net_guard=0.20,
        roundtrip_cost=0.02,
        favorable_move_pct=0.0035,
        dynamic_move_pct=0.0012,
        hold_score=170,
        lock_score=150,
        hold_threshold=140,
        partial_done=False,
        be_moved=False,
        profit_stop_target_sl=0.0,
    )

    assert out["should_execute"] is False
    assert out["skip_reason"] == "giveback_too_large"
