from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.services.exit_partial_action_policy import (
    resolve_exit_partial_action_candidate_v1,
)


def test_exit_partial_action_candidate_builds_buy_partial_and_be():
    out = resolve_exit_partial_action_candidate_v1(
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        position_volume=0.30,
        favorable_move_pct=0.0042,
        dynamic_move_pct=0.0015,
        profit=0.92,
        min_net_guard=0.12,
        roundtrip_cost=0.02,
        partial_done=False,
    )

    assert out["contract_version"] == "exit_partial_action_candidate_v1"
    assert out["candidate_kind"] == "partial_close"
    assert out["should_execute"] is True
    assert 0.0 < float(out["partial_volume"]) < 0.30
    assert float(out["be_price"]) > 100.0


def test_exit_partial_action_candidate_builds_sell_be_on_other_side():
    out = resolve_exit_partial_action_candidate_v1(
        pos_type=ORDER_TYPE_SELL,
        entry_price=100.0,
        position_volume=0.40,
        favorable_move_pct=0.0050,
        dynamic_move_pct=0.0015,
        profit=1.05,
        min_net_guard=0.12,
        roundtrip_cost=0.02,
        partial_done=False,
    )

    assert out["should_execute"] is True
    assert float(out["be_price"]) < 100.0


def test_exit_partial_action_candidate_skips_when_partial_already_done():
    out = resolve_exit_partial_action_candidate_v1(
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        position_volume=0.30,
        favorable_move_pct=0.0100,
        dynamic_move_pct=0.0015,
        profit=0.90,
        min_net_guard=0.12,
        roundtrip_cost=0.02,
        partial_done=True,
    )

    assert out["should_execute"] is False
    assert out["skip_reason"] == "already_done"


def test_exit_partial_action_candidate_skips_when_volume_is_too_small():
    out = resolve_exit_partial_action_candidate_v1(
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        position_volume=0.01,
        favorable_move_pct=0.0100,
        dynamic_move_pct=0.0015,
        profit=0.90,
        min_net_guard=0.12,
        roundtrip_cost=0.02,
        partial_done=False,
    )

    assert out["should_execute"] is False
    assert out["skip_reason"] == "volume_too_small"
