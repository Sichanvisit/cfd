"""
Learning KPI comparison report (pre vs post) on recent closed trades.

Usage:
  python scripts/learning_kpi_report.py --n 400
  python scripts/learning_kpi_report.py --n 600 --mode feature
  python scripts/learning_kpi_report.py --n 600 --mode time
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = PROJECT_ROOT / "data" / "trades" / "trade_closed_history.csv"


def _safe_div(a: float, b: float) -> float:
    b = float(b)
    if abs(b) <= 1e-12:
        return 0.0
    return float(a) / b


def _metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {
            "n": 0,
            "win_rate": 0.0,
            "expectancy": 0.0,
            "median_pnl": 0.0,
            "profit_factor": 0.0,
            "avg_entry_slippage_points": 0.0,
            "avg_exit_slippage_points": 0.0,
            "avg_giveback_usd": 0.0,
            "avg_post_exit_mae": 0.0,
            "avg_post_exit_mfe": 0.0,
            "avg_entry_score": 0.0,
            "avg_exit_score": 0.0,
        }
    pnl = pd.to_numeric(df.get("profit", 0.0), errors="coerce").fillna(0.0)
    wins = float((pnl > 0).mean()) if len(pnl) else 0.0
    pos_sum = float(pnl[pnl > 0].sum())
    neg_sum = float(pnl[pnl < 0].sum())
    pf = _safe_div(pos_sum, abs(neg_sum)) if abs(neg_sum) > 1e-12 else (999.0 if pos_sum > 0 else 0.0)
    return {
        "n": int(len(df)),
        "win_rate": float(wins),
        "expectancy": float(pnl.mean()),
        "median_pnl": float(pnl.median()),
        "profit_factor": float(pf),
        "avg_entry_slippage_points": float(pd.to_numeric(df.get("entry_slippage_points", 0.0), errors="coerce").fillna(0.0).mean()),
        "avg_exit_slippage_points": float(pd.to_numeric(df.get("exit_slippage_points", 0.0), errors="coerce").fillna(0.0).mean()),
        "avg_giveback_usd": float(pd.to_numeric(df.get("giveback_usd", 0.0), errors="coerce").fillna(0.0).mean()),
        "avg_post_exit_mae": float(pd.to_numeric(df.get("post_exit_mae", 0.0), errors="coerce").fillna(0.0).mean()),
        "avg_post_exit_mfe": float(pd.to_numeric(df.get("post_exit_mfe", 0.0), errors="coerce").fillna(0.0).mean()),
        "avg_entry_score": float(pd.to_numeric(df.get("entry_score", 0.0), errors="coerce").fillna(0.0).mean()),
        "avg_exit_score": float(pd.to_numeric(df.get("exit_score", 0.0), errors="coerce").fillna(0.0).mean()),
    }


def _choose_split(frame: pd.DataFrame, mode: str) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    if frame.empty:
        return frame.iloc[0:0].copy(), frame.iloc[0:0].copy(), "empty"

    mode = str(mode or "auto").strip().lower()
    idx = np.arange(len(frame))
    half_mask = idx >= (len(frame) // 2)

    if mode in {"time", "half"}:
        return frame.loc[~half_mask].copy(), frame.loc[half_mask].copy(), "time_half"

    has_reason = frame.get("entry_reason", "").fillna("").astype(str).str.contains("FeatureLearn:", case=False, na=False)
    sess_dev = (pd.to_numeric(frame.get("entry_session_threshold_mult", 1.0), errors="coerce").fillna(1.0) - 1.0).abs() > 1e-9
    atr_dev = (pd.to_numeric(frame.get("entry_atr_ratio", 1.0), errors="coerce").fillna(1.0) - 1.0).abs() > 1e-9
    slip_pos = pd.to_numeric(frame.get("entry_slippage_points", 0.0), errors="coerce").fillna(0.0) > 0.0
    feature_mask = (has_reason | sess_dev | atr_dev | slip_pos)

    if mode == "feature":
        return frame.loc[~feature_mask].copy(), frame.loc[feature_mask].copy(), "feature_flag"

    # auto
    pre = frame.loc[~feature_mask].copy()
    post = frame.loc[feature_mask].copy()
    min_side = max(20, int(len(frame) * 0.15))
    if len(pre) >= min_side and len(post) >= min_side:
        return pre, post, "feature_flag_auto"
    return frame.loc[~half_mask].copy(), frame.loc[half_mask].copy(), "time_half_auto"


def _load_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(path, encoding="cp949")


def _sort_and_recent(df: pd.DataFrame, n: int) -> pd.DataFrame:
    work = df.copy()
    work["status"] = work.get("status", "").fillna("").astype(str).str.upper()
    work = work[work["status"] == "CLOSED"].copy()
    if work.empty:
        return work
    for c in ("close_ts", "open_ts"):
        work[c] = pd.to_numeric(work.get(c, 0), errors="coerce").fillna(0).astype(int)
    sort_col = "close_ts" if "close_ts" in work.columns else "open_ts"
    work = work.sort_values(sort_col, ascending=True).copy()
    return work.tail(max(20, int(n))).copy()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--mode", choices=["auto", "time", "feature"], default="auto")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    csv_path = Path(str(args.csv))
    if not csv_path.exists():
        print(f"[ERR] file not found: {csv_path}")
        return 1

    raw = _load_csv(csv_path)
    recent = _sort_and_recent(raw, int(args.n))
    if recent.empty:
        print("[ERR] no CLOSED rows")
        return 2

    pre, post, split_mode = _choose_split(recent, args.mode)
    pre_m = _metrics(pre)
    post_m = _metrics(post)
    delta = {}
    for k in post_m.keys():
        if k == "n":
            delta[k] = int(post_m[k]) - int(pre_m.get(k, 0))
        else:
            delta[k] = float(post_m[k]) - float(pre_m.get(k, 0.0))

    report = {
        "csv": str(csv_path),
        "recent_n": int(len(recent)),
        "split_mode": split_mode,
        "pre": pre_m,
        "post": post_m,
        "delta_post_minus_pre": delta,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"[KPI] csv={csv_path}")
    print(f"[KPI] recent_n={len(recent)} split_mode={split_mode}")
    keys = [
        "n",
        "win_rate",
        "expectancy",
        "median_pnl",
        "profit_factor",
        "avg_entry_slippage_points",
        "avg_exit_slippage_points",
        "avg_giveback_usd",
        "avg_post_exit_mae",
        "avg_post_exit_mfe",
        "avg_entry_score",
        "avg_exit_score",
    ]
    for k in keys:
        pv = pre_m.get(k, 0.0)
        qv = post_m.get(k, 0.0)
        dv = delta.get(k, 0.0)
        if k == "n":
            print(f"- {k}: pre={int(pv)} post={int(qv)} delta={int(dv)}")
        else:
            print(f"- {k}: pre={float(pv):.6f} post={float(qv):.6f} delta={float(dv):+.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

