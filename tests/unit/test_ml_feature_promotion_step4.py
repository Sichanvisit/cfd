from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from backend.app.trading_application_reasoning import entry_features, exit_features
from ml.dataset_builder import build_datasets
from ml.feature_schema import ENTRY_FEATURE_COLS, EXIT_FEATURE_COLS
from ml.train import train


def _make_trade_row(index: int, *, symbol: str, direction: str, is_good: bool) -> dict[str, object]:
    profit = 6.0 if is_good else -3.0
    return {
        "ticket": 1000 + index,
        "symbol": symbol,
        "direction": direction,
        "lot": 0.1,
        "open_time": f"2026-03-18 09:{index:02d}:00",
        "open_price": 100.0 + index,
        "entry_score": 80 + index,
        "contra_score_at_entry": 30 + (index % 5),
        "entry_stage": "balanced" if index % 2 == 0 else "aggressive",
        "entry_setup_id": "range_lower_reversal_buy" if direction == "BUY" else "breakout_retest_sell",
        "management_profile_id": "range_lifecycle",
        "invalidation_id": "box_fail",
        "entry_wait_state": "READY",
        "entry_quality": 0.65 + (0.01 * index),
        "entry_model_confidence": 0.60 + (0.01 * index),
        "regime_at_entry": "RANGE" if index % 2 == 0 else "TREND",
        "entry_h1_context_score": 55 + index,
        "entry_m1_trigger_score": 42 + index,
        "entry_h1_gate_pass": 1,
        "entry_h1_gate_reason": "context_ok",
        "entry_topdown_gate_pass": 1,
        "entry_topdown_gate_reason": "align_ok",
        "entry_topdown_align_count": 3,
        "entry_topdown_conflict_count": 1,
        "entry_topdown_seen_count": 4,
        "entry_session_name": "ASIA" if index % 2 == 0 else "EUROPE",
        "entry_weekday": 2,
        "entry_session_threshold_mult": 0.95,
        "entry_atr_ratio": 1.1,
        "entry_atr_threshold_mult": 0.9,
        "entry_request_price": 100.0 + index,
        "entry_fill_price": 100.1 + index,
        "entry_slippage_points": 0.1,
        "close_time": f"2026-03-18 10:{index:02d}:00",
        "close_price": 101.0 + index,
        "profit": profit,
        "gross_pnl": profit + 0.2,
        "cost_total": 0.2,
        "net_pnl_after_cost": profit - 0.2,
        "points": 12.0 if is_good else -8.0,
        "entry_reason": "Range reversal",
        "exit_reason": "Lock Exit" if is_good else "Adverse Stop",
        "exit_score": 60 + index,
        "decision_winner": "exit_now" if is_good else "hold",
        "utility_exit_now": 1.5 if is_good else -1.2,
        "utility_hold": 0.7 if is_good else -0.4,
        "utility_reverse": 0.2 if is_good else 0.3,
        "utility_wait_exit": 0.1 if is_good else -0.2,
        "u_cut_now": 1.2 if is_good else -0.9,
        "u_wait_be": 0.5 if is_good else -0.3,
        "u_wait_tp1": 0.8 if is_good else -0.1,
        "u_reverse": 0.1 if is_good else 0.2,
        "exit_policy_stage": "mid",
        "exit_policy_profile": "neutral",
        "exit_profile": "neutral",
        "exit_wait_state": "WATCH",
        "exit_wait_selected": 1 if not is_good else 0,
        "exit_wait_decision": "wait" if not is_good else "exit_now",
        "p_recover_be": 0.4,
        "p_recover_tp1": 0.3,
        "p_deeper_loss": 0.2,
        "p_reverse_valid": 0.1,
        "exit_policy_regime": "RANGE",
        "exit_threshold_triplet": "65/75/55",
        "exit_confirm_ticks_applied": 2,
        "exit_route_ev": "protect=1.0,hold=0.5",
        "exit_confidence": 0.66,
        "exit_delay_ticks": index % 3,
        "peak_profit_at_exit": 7.5 if is_good else 1.2,
        "giveback_usd": 1.1 if is_good else 0.3,
        "shock_score": 0.2,
        "shock_hold_delta_30": 0.4,
        "status": "CLOSED",
        "regime_name": "RANGE",
        "regime_volume_ratio": 1.1,
        "regime_volatility_ratio": 1.05,
        "regime_spread_ratio": 0.9,
        "regime_buy_multiplier": 1.0,
        "regime_sell_multiplier": 1.0,
        "ind_rsi": 48.0 + index,
        "ind_adx": 22.0,
        "ind_disparity": 0.6,
        "ind_bb_20_up": 110.0,
        "ind_bb_20_dn": 90.0,
        "ind_bb_4_up": 108.0,
        "ind_bb_4_dn": 92.0,
        "post_exit_mfe": 9.0 if is_good else 1.0,
        "post_exit_mae": -1.5 if is_good else -4.0,
    }


def test_dataset_builder_promotes_live_feature_columns(tmp_path):
    source = tmp_path / "trade_history.csv"
    out_dir = tmp_path / "datasets"
    pd.DataFrame(
        [
            _make_trade_row(1, symbol="BTCUSD", direction="BUY", is_good=True),
            _make_trade_row(2, symbol="XAUUSD", direction="SELL", is_good=False),
        ]
    ).to_csv(source, index=False, encoding="utf-8-sig")

    entry_path, exit_path = build_datasets(source, out_dir, per_symbol_limit=10)
    entry_df = pd.read_csv(entry_path)
    exit_df = pd.read_csv(exit_path)

    assert "entry_stage" in entry_df.columns
    assert "entry_setup_id" in entry_df.columns
    assert "entry_h1_context_score" in entry_df.columns
    assert "entry_session_name" in entry_df.columns
    assert "decision_winner" in exit_df.columns
    assert "exit_policy_stage" in exit_df.columns
    assert "utility_exit_now" in exit_df.columns
    assert "shock_score" in exit_df.columns


def test_runtime_feature_helpers_emit_promoted_fields():
    entry_row = entry_features(
        symbol="BTCUSD",
        action="BUY",
        score=85,
        contra_score=30,
        reasons=["Range reversal"],
        regime={"name": "RANGE", "volume_ratio": 1.2, "volatility_ratio": 1.1, "spread_ratio": 0.9},
        indicators={"ind_rsi": 52, "ind_adx": 24, "ind_disparity": 0.7, "ind_bb_20_up": 1, "ind_bb_20_dn": -1, "ind_bb_4_up": 2, "ind_bb_4_dn": -2},
        metadata={
            "entry_stage": "aggressive",
            "entry_setup_id": "range_lower_reversal_buy",
            "management_profile_id": "range_lifecycle",
            "invalidation_id": "box_fail",
            "entry_h1_context_score": 61,
            "entry_m1_trigger_score": 47,
            "entry_h1_gate_pass": 1,
            "entry_h1_gate_reason": "context_ok",
            "entry_topdown_gate_pass": 1,
            "entry_topdown_gate_reason": "align_ok",
            "entry_topdown_align_count": 3,
            "entry_topdown_conflict_count": 1,
            "entry_topdown_seen_count": 4,
            "entry_session_name": "ASIA",
            "entry_weekday": 2,
            "entry_session_threshold_mult": 0.95,
            "entry_atr_ratio": 1.1,
            "entry_atr_threshold_mult": 0.9,
        },
    )
    assert entry_row["entry_stage"] == "aggressive"
    assert entry_row["entry_setup_id"] == "range_lower_reversal_buy"
    assert entry_row["entry_h1_context_score"] == 61.0
    assert entry_row["entry_session_name"] == "ASIA"

    exit_row = exit_features(
        symbol="BTCUSD",
        direction="BUY",
        open_time="2026-03-18 09:30:00",
        duration_sec=1800,
        entry_score=85,
        contra_score=30,
        exit_score=60,
        entry_reason="Range reversal",
        exit_reason="Lock Exit",
        regime={"name": "RANGE", "volume_ratio": 1.1, "volatility_ratio": 1.0, "spread_ratio": 0.8},
        trade_ctx={
            "entry_stage": "balanced",
            "entry_setup_id": "range_lower_reversal_buy",
            "management_profile_id": "range_lifecycle",
            "invalidation_id": "box_fail",
            "entry_wait_state": "READY",
            "entry_quality": 0.72,
            "entry_model_confidence": 0.68,
            "entry_h1_context_score": 59,
            "entry_m1_trigger_score": 45,
            "entry_h1_gate_pass": 1,
            "entry_h1_gate_reason": "context_ok",
            "entry_topdown_gate_pass": 1,
            "entry_topdown_gate_reason": "align_ok",
            "entry_topdown_align_count": 3,
            "entry_topdown_conflict_count": 1,
            "entry_topdown_seen_count": 4,
            "entry_session_name": "ASIA",
            "entry_weekday": 2,
            "entry_session_threshold_mult": 0.95,
            "entry_atr_ratio": 1.1,
            "entry_atr_threshold_mult": 0.9,
        },
        stage_inputs={"peak_profit": 7.5, "regime_now": "RANGE"},
        live_metrics={
            "decision_winner": "exit_now",
            "utility_exit_now": 1.3,
            "utility_hold": 0.8,
            "exit_policy_stage": "mid",
            "exit_profile": "neutral",
            "exit_wait_state": "WATCH",
            "exit_wait_selected": 1,
            "exit_wait_decision": "wait",
            "p_recover_be": 0.4,
            "p_recover_tp1": 0.3,
            "p_deeper_loss": 0.2,
            "p_reverse_valid": 0.1,
            "exit_policy_regime": "RANGE",
            "exit_threshold_triplet": "65/75/55",
            "exit_route_ev": "protect=1.0,hold=0.5",
            "exit_confidence": 0.66,
            "exit_delay_ticks": 2,
            "peak_profit_at_exit": 7.5,
            "giveback_usd": 1.1,
            "shock_score": 0.2,
            "shock_hold_delta_30": 0.4,
        },
    )
    assert exit_row["entry_quality"] == 0.72
    assert exit_row["decision_winner"] == "exit_now"
    assert exit_row["exit_policy_stage"] == "mid"
    assert exit_row["peak_profit_at_exit"] == 7.5


def test_train_uses_promoted_feature_schema(tmp_path):
    entry_csv = tmp_path / "entry_dataset.csv"
    exit_csv = tmp_path / "exit_dataset.csv"
    model_dir = tmp_path / "models"

    entry_rows = []
    exit_rows = []
    for idx in range(12):
        base = _make_trade_row(idx + 1, symbol="BTCUSD" if idx % 2 == 0 else "XAUUSD", direction="BUY" if idx % 2 == 0 else "SELL", is_good=(idx % 2 == 0))
        entry_row = {column: base.get(column, 0.0) for column in ENTRY_FEATURE_COLS}
        entry_row["event_time"] = base["open_time"]
        entry_row["is_win"] = 1 if idx % 2 == 0 else 0
        exit_row = {column: base.get(column, 0.0) for column in EXIT_FEATURE_COLS}
        exit_row["event_time"] = base["close_time"]
        exit_row["is_good_exit"] = 1 if idx % 2 == 0 else 0
        entry_rows.append(entry_row)
        exit_rows.append(exit_row)

    pd.DataFrame(entry_rows).to_csv(entry_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(exit_rows).to_csv(exit_csv, index=False, encoding="utf-8-sig")

    result = train(entry_csv, exit_csv, model_dir)
    bundle = joblib.load(result["model_path"])
    metrics = json.loads((model_dir / "metrics.json").read_text(encoding="utf-8"))

    assert bundle["entry_feature_cols"] == ENTRY_FEATURE_COLS
    assert bundle["exit_feature_cols"] == EXIT_FEATURE_COLS
    assert metrics["feature_pack_version"] == "live_ml_step4_v1"
    assert metrics["entry_feature_count"] == len(ENTRY_FEATURE_COLS)
    assert metrics["exit_feature_count"] == len(EXIT_FEATURE_COLS)
