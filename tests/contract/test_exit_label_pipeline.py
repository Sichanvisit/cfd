from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml.dataset_builder import build_datasets


def test_exit_dataset_ev_columns_exist(tmp_path: Path):
    source = tmp_path / 'trade_history.csv'
    rows = [
        {
            'ticket': i + 1,
            'symbol': 'NAS100',
            'direction': 'BUY' if i % 2 == 0 else 'SELL',
            'open_time': f'2026-02-20 09:{i:02d}:00',
            'open_price': 100.0 + i,
            'entry_score': 150 + i,
            'contra_score_at_entry': 80,
            'close_time': f'2026-02-20 10:{i:02d}:00',
            'close_price': 101.0 + i,
            'profit': float((i % 5) - 2),
            'points': float((i % 7) - 3),
            'entry_reason': 'Rule',
            'exit_reason': 'Target' if i % 3 == 0 else 'Reversal',
            'exit_score': 120,
            'status': 'CLOSED',
            'regime_name': 'RANGE' if i % 2 == 0 else 'EXPANSION',
            'regime_volume_ratio': 1.0,
            'regime_volatility_ratio': 1.0,
            'regime_spread_ratio': 1.0,
            'regime_buy_multiplier': 1.0,
            'regime_sell_multiplier': 1.0,
            'mfe_30': 1.2 + (i % 3) * 0.1,
            'mae_30': 0.6 + (i % 2) * 0.1,
            'ind_rsi': 50.0,
            'ind_adx': 20.0,
            'ind_disparity': 100.0,
            'ind_bb_20_up': 0.0,
            'ind_bb_20_dn': 0.0,
            'ind_bb_4_up': 0.0,
            'ind_bb_4_dn': 0.0,
        }
        for i in range(30)
    ]
    pd.DataFrame(rows).to_csv(source, index=False, encoding='utf-8-sig')

    _, exit_path = build_datasets(source, tmp_path / 'datasets')
    exit_df = pd.read_csv(exit_path)

    for col in ['roundtrip_cost', 'spread_cost_mult', 'mfe_proxy', 'mae_proxy', 'ev_exit', 'ev_hold', 'ev_delta', 'is_good_exit']:
        assert col in exit_df.columns
    assert (exit_df['spread_cost_mult'] > 0).all()
    assert len(exit_df) == 30
    assert set(exit_df['is_good_exit'].dropna().astype(int).unique().tolist()).issubset({0, 1})


def test_dataset_builder_caps_rows_to_300_by_default(tmp_path: Path):
    source = tmp_path / "trade_history.csv"
    rows = []
    symbols = ["BTCUSD", "NAS100", "XAUUSD"]
    for s_idx, symbol in enumerate(symbols):
        for i in range(130):
            rows.append(
                {
                    "ticket": (s_idx + 1) * 10000 + i,
                    "symbol": symbol,
                    "direction": "BUY" if i % 2 == 0 else "SELL",
                    "open_time": f"2026-02-20 09:{i % 60:02d}:00",
                    "open_price": 100.0 + i,
                    "entry_score": 140 + (i % 20),
                    "contra_score_at_entry": 80 + (i % 10),
                    "close_time": f"2026-02-20 10:{i % 60:02d}:00",
                    "close_price": 101.0 + i,
                    "profit": float((i % 7) - 3),
                    "points": float((i % 9) - 4),
                    "entry_reason": "Rule",
                    "exit_reason": "Target",
                    "exit_score": 120,
                    "status": "CLOSED",
                    "regime_name": "RANGE",
                    "regime_volume_ratio": 1.0,
                    "regime_volatility_ratio": 1.0,
                    "regime_spread_ratio": 1.0,
                    "regime_buy_multiplier": 1.0,
                    "regime_sell_multiplier": 1.0,
                    "ind_rsi": 50.0,
                    "ind_adx": 20.0,
                    "ind_disparity": 100.0,
                    "ind_bb_20_up": 0.0,
                    "ind_bb_20_dn": 0.0,
                    "ind_bb_4_up": 0.0,
                    "ind_bb_4_dn": 0.0,
                }
            )
    pd.DataFrame(rows).to_csv(source, index=False, encoding="utf-8-sig")

    entry_path, exit_path = build_datasets(source, tmp_path / "datasets")
    entry_df = pd.read_csv(entry_path)
    exit_df = pd.read_csv(exit_path)

    assert len(entry_df) == 300
    assert len(exit_df) == 300
