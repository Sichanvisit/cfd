from __future__ import annotations

import pandas as pd

from backend.services.path_checkpoint_pa8_symbol_action_canary import (
    build_checkpoint_pa8_symbol_action_canary_bundle,
    build_checkpoint_pa8_symbol_action_preview,
)


def test_build_checkpoint_pa8_symbol_action_preview_btcusd_wait_candidate_is_clean() -> None:
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "checkpoint_id": "CP1",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "checkpoint_rule_family_hint": "active_open_loss",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "unrealized_pnl_state": "OPEN_LOSS",
                "source": "exit_manage_hold",
                "position_side": "SELL",
                "current_profit": -0.3,
                "runtime_hold_quality_score": 0.39,
                "runtime_partial_exit_ev": 0.37,
                "runtime_full_exit_risk": 0.61,
                "runtime_continuation_odds": 0.87,
                "runtime_reversal_odds": 0.69,
                "giveback_ratio": 0.99,
            }
        ]
        * 60
    )

    _, summary = build_checkpoint_pa8_symbol_action_preview(frame, symbol="BTCUSD")

    assert summary["eligible_row_count"] == 60
    assert summary["worsened_row_count"] == 0
    assert summary["preview_action_precision"] == 1.0
    assert summary["recommended_next_action"] == "review_symbol_action_only_preview_for_canary"


def test_build_checkpoint_pa8_symbol_action_canary_bundle_xauusd_can_activate_when_scope_is_clean() -> None:
    rows = []
    for idx in range(31):
        rows.append(
            {
                "symbol": "XAUUSD",
                "checkpoint_id": f"CP{idx}",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "checkpoint_rule_family_hint": "open_loss_protective" if idx < 20 else "active_open_loss",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "unrealized_pnl_state": "OPEN_LOSS",
                "source": "exit_manage_hold",
                "position_side": "BUY",
                "current_profit": -0.57,
                "runtime_hold_quality_score": 0.44,
                "runtime_partial_exit_ev": 0.38,
                "runtime_full_exit_risk": 0.51,
                "runtime_continuation_odds": 0.91,
                "runtime_reversal_odds": 0.56,
                "giveback_ratio": 0.99,
                "generated_at": "",
            }
        )
    frame = pd.DataFrame(rows)

    bundle = build_checkpoint_pa8_symbol_action_canary_bundle(
        resolved_dataset=frame,
        pa8_action_review_packet_payload={"summary": {"action_baseline_review_ready": True}, "symbol_rows": [{"symbol": "XAUUSD", "review_state": "SUPPORT_REVIEW_ONLY"}]},
        symbol_review_payload={"summary": {"review_result": "narrow_wait_boundary_candidate_identified"}},
        symbol="XAUUSD",
        approval_decision="APPROVE",
    )

    assert bundle["canary_review"]["summary"]["provisional_canary_ready"] is True
    assert bundle["activation_packet"]["summary"]["allow_activation"] is True
    assert bundle["activation_apply"]["summary"]["active"] is True
    assert bundle["closeout_decision"]["summary"]["closeout_state"] == "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW"


def test_build_checkpoint_pa8_symbol_action_canary_bundle_btcusd_keeps_hold_before_live_rows_even_with_seed_trigger() -> None:
    rows = []
    for idx in range(88):
        rows.append(
            {
                "symbol": "BTCUSD",
                "checkpoint_id": f"CP{idx}",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "checkpoint_rule_family_hint": "active_open_loss",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "unrealized_pnl_state": "OPEN_LOSS",
                "source": "exit_manage_hold",
                "position_side": "SELL",
                "current_profit": -0.3,
                "runtime_hold_quality_score": 0.39,
                "runtime_partial_exit_ev": 0.37,
                "runtime_full_exit_risk": 0.61,
                "runtime_continuation_odds": 0.87,
                "runtime_reversal_odds": 0.69,
                "giveback_ratio": 0.99,
                "generated_at": "",
            }
        )
    frame = pd.DataFrame(rows)

    bundle = build_checkpoint_pa8_symbol_action_canary_bundle(
        resolved_dataset=frame,
        pa8_action_review_packet_payload={"summary": {"action_baseline_review_ready": True}, "symbol_rows": [{"symbol": "BTCUSD", "review_state": "PRIMARY_REVIEW"}]},
        symbol_review_payload={"summary": {"review_result": "narrow_wait_boundary_candidate_identified"}},
        symbol="BTCUSD",
        approval_decision="APPROVE",
    )

    assert bundle["activation_apply"]["summary"]["active"] is True
    assert bundle["first_window_observation"]["summary"]["live_observation_ready"] is False
    assert bundle["first_window_observation"]["summary"]["active_trigger_count"] >= 0
    assert bundle["closeout_decision"]["summary"]["closeout_state"] == "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW"
