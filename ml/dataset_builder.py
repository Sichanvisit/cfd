"""
Build supervised datasets from trade_history.csv for entry/exit modeling.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.trade_csv_schema import normalize_trade_df
from ml.feature_schema import (
    ENTRY_FEATURE_COLS,
    ENTRY_PROMOTED_NUMERIC_COLS,
    ENTRY_PROMOTED_TEXT_COLS,
    EXIT_FEATURE_COLS,
    EXIT_PROMOTED_NUMERIC_COLS,
    EXIT_PROMOTED_TEXT_COLS,
)

NET_PROFIT_GUARD_BY_SYMBOL = {
    "NAS100": 1.6,  # min_net(1.0) + fee_buffer(0.2) + roundtrip_cost(0.6)
    "XAUUSD": 1.5,  # min_net(1.0) + fee_buffer(0.2) + roundtrip_cost(0.5)
    "BTCUSD": 2.4,  # min_net(1.0) + fee_buffer(0.2) + roundtrip_cost(1.2)
    "DEFAULT": 1.5,
}
ROUNDTRIP_COST_BY_SYMBOL = {
    "NAS100": 0.6,
    "XAUUSD": 0.5,
    "BTCUSD": 1.2,
    "DEFAULT": 0.5,
}
EV_K = float(os.getenv("EXIT_EV_K", "1.20"))
SPREAD_COST_MIN_MULT = float(os.getenv("DYNAMIC_COST_SPREAD_MIN_MULT", "0.80"))
SPREAD_COST_MAX_MULT = float(os.getenv("DYNAMIC_COST_SPREAD_MAX_MULT", "2.20"))
SPREAD_COST_RECENT_WINDOW = int(os.getenv("DYNAMIC_COST_RECENT_TRADES", "40"))
ENTRY_EXTRA_NUMERIC = [
    "regime_volume_ratio",
    "regime_volatility_ratio",
    "regime_spread_ratio",
    "regime_buy_multiplier",
    "regime_sell_multiplier",
    "ind_rsi",
    "ind_adx",
    "ind_disparity",
    "ind_bb_20_up",
    "ind_bb_20_dn",
    "ind_bb_4_up",
    "ind_bb_4_dn",
    *ENTRY_PROMOTED_NUMERIC_COLS,
    *EXIT_PROMOTED_NUMERIC_COLS,
]
ENTRY_EXTRA_TEXT = list(dict.fromkeys(ENTRY_PROMOTED_TEXT_COLS + EXIT_PROMOTED_TEXT_COLS))


def _canonical_symbol(value: str) -> str:
    text = str(value or "").upper()
    if "BTC" in text:
        return "BTCUSD"
    if "NAS" in text or "US100" in text or "USTEC" in text:
        return "NAS100"
    if "XAU" in text or "GOLD" in text:
        return "XAUUSD"
    return ""


def _limit_closed_rows_by_symbol(
    closed: pd.DataFrame,
    per_symbol_limit: int,
    symbols: tuple[str, ...],
) -> pd.DataFrame:
    if closed.empty:
        return closed
    n = max(1, int(per_symbol_limit))
    allowed = {_canonical_symbol(s) for s in symbols}
    allowed.discard("")
    out = closed.copy()
    out["canonical_symbol"] = out.get("symbol", "").map(_canonical_symbol)
    out = out[out["canonical_symbol"].isin(allowed)].copy()
    if out.empty:
        return out
    out["_event_dt"] = out.get("close_dt")
    out["_event_dt"] = out["_event_dt"].fillna(out.get("open_dt"))
    out = out.sort_values(["canonical_symbol", "_event_dt"], ascending=[True, False])
    out = out.groupby("canonical_symbol", group_keys=False).head(n)
    return out.drop(columns=["canonical_symbol", "_event_dt"], errors="ignore")


def _safe_float(value, default: float = 0.0) -> float:
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return float(default)
    return float(num)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_trade_df(df if df is not None else pd.DataFrame())
    rename_map = {
        "entry_time": "open_time",
        "entry_price": "open_price",
        "reason": "entry_reason",
        "buy_score": "entry_score",
        "sell_score": "contra_score_at_entry",
    }
    for old, new in rename_map.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    required = [
        "ticket",
        "symbol",
        "direction",
        "open_time",
        "open_price",
        "entry_score",
        "contra_score_at_entry",
        "close_time",
        "close_price",
        "profit",
        "points",
        "entry_reason",
        "exit_reason",
        "exit_score",
        "status",
        "regime_name",
        "regime_volume_ratio",
        "regime_volatility_ratio",
        "regime_spread_ratio",
        "regime_buy_multiplier",
        "regime_sell_multiplier",
        "ind_rsi",
        "ind_adx",
        "ind_disparity",
        "ind_bb_20_up",
        "ind_bb_20_dn",
        "ind_bb_4_up",
        "ind_bb_4_dn",
        *ENTRY_PROMOTED_TEXT_COLS,
        *ENTRY_PROMOTED_NUMERIC_COLS,
        *EXIT_PROMOTED_TEXT_COLS,
        *EXIT_PROMOTED_NUMERIC_COLS,
        "cost_total",
        "net_pnl_after_cost",
    ]
    optional = [
        "mfe_30",
        "mae_30",
        "post_exit_mfe",
        "post_exit_mae",
    ]

    for col in required:
        if col not in df.columns:
            if col in ("symbol", "direction", "open_time", "close_time", "entry_reason", "exit_reason"):
                df[col] = ""
            elif col == "status":
                df[col] = "OPEN"
            else:
                df[col] = 0.0
    keep = list(dict.fromkeys(required + [c for c in optional if c in df.columns]))
    return df[keep]


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["open_dt"] = pd.to_datetime(out["open_time"], errors="coerce")
    out["close_dt"] = pd.to_datetime(out["close_time"], errors="coerce")
    out["open_hour"] = out["open_dt"].dt.hour.fillna(-1).astype(int)
    out["open_weekday"] = out["open_dt"].dt.weekday.fillna(-1).astype(int)
    out["close_hour"] = out["close_dt"].dt.hour.fillna(-1).astype(int)
    out["duration_sec"] = (out["close_dt"] - out["open_dt"]).dt.total_seconds()
    out["duration_sec"] = out["duration_sec"].replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
    out["entry_reason"] = out["entry_reason"].astype(str)
    # Remove legacy synthetic placeholders that hurt model signal quality.
    out["entry_reason"] = out["entry_reason"].str.replace(r"\s*,?\s*기타 근거\s*\([^)]+\)", "", regex=True)
    out["entry_reason"] = out["entry_reason"].str.replace(r"\s*,?\s*점수 보정\s*\([^)]+\)", "", regex=True)
    out["entry_reason"] = out["entry_reason"].str.replace(r"\s*,\s*,", ", ", regex=True).str.strip(" ,")
    out["entry_reason"] = out["entry_reason"].replace({"": "UNKNOWN", "nan": "UNKNOWN"})
    out["exit_reason"] = out["exit_reason"].astype(str).replace({"": "UNKNOWN", "nan": "UNKNOWN"})
    out["regime_name"] = out["regime_name"].astype(str).replace({"": "UNKNOWN", "nan": "UNKNOWN"})
    for col in ENTRY_EXTRA_TEXT:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str)
    for col in ENTRY_EXTRA_NUMERIC:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    return out


def _symbol_profit_guard(symbol: str) -> float:
    upper = str(symbol or "").upper()
    for key, value in NET_PROFIT_GUARD_BY_SYMBOL.items():
        if key == "DEFAULT":
            continue
        if key in upper:
            return float(value)
    return float(NET_PROFIT_GUARD_BY_SYMBOL["DEFAULT"])


def _symbol_roundtrip_cost(symbol: str) -> float:
    upper = str(symbol or "").upper()
    for key, value in ROUNDTRIP_COST_BY_SYMBOL.items():
        if key == "DEFAULT":
            continue
        if key in upper:
            return float(value)
    return float(ROUNDTRIP_COST_BY_SYMBOL["DEFAULT"])


def _dynamic_roundtrip_cost(
    symbol: str,
    row_spread_ratio: float,
    hist_sd: pd.DataFrame,
) -> tuple[float, float]:
    base = _symbol_roundtrip_cost(symbol)
    row_val = _safe_float(row_spread_ratio, default=0.0)
    hist_med = np.nan
    if hist_sd is not None and not hist_sd.empty and "regime_spread_ratio" in hist_sd.columns:
        hist_ratio = pd.to_numeric(hist_sd["regime_spread_ratio"], errors="coerce")
        hist_ratio = hist_ratio[hist_ratio > 0]
        if not hist_ratio.empty:
            hist_med = float(hist_ratio.tail(max(10, SPREAD_COST_RECENT_WINDOW)).median())
    spread_mult = 1.0
    if row_val > 0 and np.isfinite(hist_med) and hist_med > 0:
        spread_mult = float(row_val / hist_med)
    spread_mult = float(np.clip(spread_mult, SPREAD_COST_MIN_MULT, SPREAD_COST_MAX_MULT))
    return float(base * spread_mult), float(spread_mult)


def _canonical_exit_reason(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "UNKNOWN"
    lower = text.lower()
    if "adverse reversal" in lower:
        return "Adverse Reversal"
    if "adverse stop" in lower:
        return "Adverse Stop"
    if "target" in lower:
        return "Target"
    if "rsi scalp" in lower:
        return "RSI Scalp"
    if "bb scalp" in lower:
        return "BB Scalp"
    if "reversal" in lower:
        return "Reversal"
    if "mt5 history" in lower:
        return "MT5 History"
    return text


def build_datasets(
    source_csv: Path,
    out_dir: Path,
    per_symbol_limit: int = 100,
    symbols: tuple[str, ...] = ("BTCUSD", "NAS100", "XAUUSD"),
) -> tuple[Path, Path]:
    raw = pd.read_csv(source_csv)
    closed_csv = source_csv.parent / "trade_closed_history.csv"
    if closed_csv.exists():
        try:
            closed_raw = pd.read_csv(closed_csv)
            if not closed_raw.empty:
                if raw is None or raw.empty:
                    raw = closed_raw.copy()
                else:
                    raw = pd.concat([raw, closed_raw], ignore_index=True)
        except Exception:
            pass
    df = _normalize_columns(raw)
    df = _add_time_features(df)

    closed = df[df["status"].astype(str).str.upper() == "CLOSED"].copy()
    closed["profit"] = pd.to_numeric(closed["profit"], errors="coerce").fillna(0.0)
    closed["points"] = pd.to_numeric(closed["points"], errors="coerce").fillna(0.0)
    closed["entry_score"] = pd.to_numeric(closed["entry_score"], errors="coerce").fillna(0.0)
    closed["contra_score_at_entry"] = pd.to_numeric(closed["contra_score_at_entry"], errors="coerce").fillna(0.0)
    closed["exit_score"] = pd.to_numeric(closed["exit_score"], errors="coerce").fillna(0.0)
    closed["score_gap"] = closed["entry_score"] - closed["contra_score_at_entry"]
    closed["abs_score_gap"] = closed["score_gap"].abs()
    closed["is_win"] = (closed["profit"] > 0).astype(int)
    closed = _limit_closed_rows_by_symbol(closed, per_symbol_limit=per_symbol_limit, symbols=symbols)

    # Entry dataset: predict win probability and expected profit from entry snapshot.
    entry_ds = closed[
        [
            "ticket",
            *ENTRY_FEATURE_COLS,
            "open_dt",
            "duration_sec",
            "points",
            "profit",
            "cost_total",
            "net_pnl_after_cost",
            "is_win",
        ]
    ].copy()
    entry_ds = entry_ds.rename(columns={"open_dt": "event_time"})

    # Exit dataset: quality label relative to rolling historical baseline.
    computed_exit_feature_cols = {
        "roundtrip_cost",
        "spread_cost_mult",
        "mfe_proxy",
        "mae_proxy",
        "ev_exit",
        "ev_hold",
        "ev_delta",
    }
    exit_cols = [
        "ticket",
        "close_dt",
        *[column for column in EXIT_FEATURE_COLS if column not in computed_exit_feature_cols],
        "points",
        "profit",
        "cost_total",
        "net_pnl_after_cost",
        "is_win",
    ]
    for opt in ["mfe_30", "mae_30", "post_exit_mfe", "post_exit_mae"]:
        if opt in closed.columns:
            exit_cols.append(opt)
    exit_ds = closed[exit_cols].copy()
    exit_ds = exit_ds.rename(columns={"close_dt": "event_time"})
    exit_ds = exit_ds.sort_values("event_time").reset_index(drop=True)
    exit_ds["exit_reason"] = exit_ds["exit_reason"].map(_canonical_exit_reason)

    # EV label redesign: compare "exit now" vs "hold" using MFE/MAE + cost.
    # If direct MFE/MAE columns are missing, use history-based proxy per symbol/direction.
    mfe_direct_col = "mfe_30" if "mfe_30" in exit_ds.columns else ("post_exit_mfe" if "post_exit_mfe" in exit_ds.columns else None)
    mae_direct_col = "mae_30" if "mae_30" in exit_ds.columns else ("post_exit_mae" if "post_exit_mae" in exit_ds.columns else None)
    cost_cols = []
    mfe_cols = []
    mae_cols = []
    ev_exit_cols = []
    ev_hold_cols = []
    ev_delta_cols = []
    spread_mult_cols = []
    baseline_cols = []
    guard_cols = []
    ev_k = float(EV_K)
    for idx, row in exit_ds.iterrows():
        hist = exit_ds.iloc[:idx]
        hist_sd = hist[(hist["symbol"] == row["symbol"]) & (hist["direction"] == row["direction"])]
        if len(hist_sd) >= 10:
            baseline = float(hist_sd["profit"].tail(40).median())
        elif idx > 10:
            baseline = float(hist["profit"].median())
        else:
            baseline = 0.0
        profit_guard = _symbol_profit_guard(row["symbol"])
        cost, spread_mult = _dynamic_roundtrip_cost(
            symbol=row["symbol"],
            row_spread_ratio=_safe_float(row.get("regime_spread_ratio", 0.0), default=0.0),
            hist_sd=hist_sd,
        )

        if mfe_direct_col:
            mfe_val = float(pd.to_numeric(row.get(mfe_direct_col, 0.0), errors="coerce") or 0.0)
        else:
            pos_hist = hist_sd[hist_sd["profit"] > 0]["profit"] if len(hist_sd) > 0 else pd.Series(dtype=float)
            mfe_val = float(pos_hist.quantile(0.75)) if len(pos_hist) >= 5 else max(0.0, float(row.get("profit", 0.0)))
        if mae_direct_col:
            mae_raw = float(pd.to_numeric(row.get(mae_direct_col, 0.0), errors="coerce") or 0.0)
            mae_val = abs(mae_raw)
        else:
            neg_hist = hist_sd[hist_sd["profit"] < 0]["profit"].abs() if len(hist_sd) > 0 else pd.Series(dtype=float)
            mae_val = float(neg_hist.quantile(0.75)) if len(neg_hist) >= 5 else max(0.0, abs(float(min(0.0, row.get("profit", 0.0)))))

        ev_exit = float(row["profit"]) - cost
        ev_hold = (mfe_val - cost) - (ev_k * (mae_val + cost))
        ev_delta = ev_hold - ev_exit

        baseline_cols.append(max(0.0, baseline))
        guard_cols.append(profit_guard)
        cost_cols.append(cost)
        spread_mult_cols.append(spread_mult)
        mfe_cols.append(float(mfe_val))
        mae_cols.append(float(mae_val))
        ev_exit_cols.append(float(ev_exit))
        ev_hold_cols.append(float(ev_hold))
        ev_delta_cols.append(float(ev_delta))

    exit_ds["profit_baseline"] = baseline_cols
    exit_ds["profit_guard"] = guard_cols
    exit_ds["roundtrip_cost"] = cost_cols
    exit_ds["spread_cost_mult"] = spread_mult_cols
    exit_ds["mfe_proxy"] = mfe_cols
    exit_ds["mae_proxy"] = mae_cols
    exit_ds["ev_exit"] = ev_exit_cols
    exit_ds["ev_hold"] = ev_hold_cols
    exit_ds["ev_delta"] = ev_delta_cols
    # Good exit if exiting now is not worse than holding, and it passes minimal net-profit guard.
    label_threshold = np.maximum(exit_ds["profit_baseline"], exit_ds["profit_guard"])
    exit_ds["is_good_exit"] = ((exit_ds["ev_delta"] <= 0.0) & (exit_ds["profit"] >= label_threshold)).astype(int)

    out_dir.mkdir(parents=True, exist_ok=True)
    entry_path = out_dir / "entry_dataset.csv"
    exit_path = out_dir / "exit_dataset.csv"
    entry_ds.to_csv(entry_path, index=False, encoding="utf-8-sig")
    exit_ds.to_csv(exit_path, index=False, encoding="utf-8-sig")
    return entry_path, exit_path


def main():
    parser = argparse.ArgumentParser(description="Build AI datasets from trade history.")
    parser.add_argument("--source", default=str(PROJECT_ROOT / "data" / "trades" / "trade_history.csv"), help="Path to trade history CSV")
    parser.add_argument("--out-dir", default=str(PROJECT_ROOT / "data" / "datasets"), help="Output directory for datasets")
    parser.add_argument("--per-symbol-limit", type=int, default=100, help="Max rows per symbol for BTCUSD/NAS100/XAUUSD")
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out_dir)
    entry_path, exit_path = build_datasets(source, out_dir, per_symbol_limit=int(args.per_symbol_limit))
    print(f"entry_dataset: {entry_path}")
    print(f"exit_dataset : {exit_path}")


if __name__ == "__main__":
    main()
