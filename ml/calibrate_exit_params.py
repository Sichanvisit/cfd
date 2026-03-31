from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_COST_BY_SYMBOL = {
    "NAS100": 0.6,
    "XAUUSD": 0.5,
    "BTCUSD": 1.2,
    "DEFAULT": 0.5,
}
PROFIT_GUARD_BY_SYMBOL = {
    "NAS100": 1.6,
    "XAUUSD": 1.5,
    "BTCUSD": 2.4,
    "DEFAULT": 1.5,
}


def _safe_float(value, default: float = 0.0) -> float:
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return float(default)
    return float(num)


def _symbol_map_value(symbol: str, table: dict[str, float]) -> float:
    upper = str(symbol or "").upper()
    for key, value in table.items():
        if key == "DEFAULT":
            continue
        if key in upper:
            return float(value)
    return float(table["DEFAULT"])


def _load_closed(source_csv: Path) -> pd.DataFrame:
    raw = pd.read_csv(source_csv)
    closed_csv = source_csv.parent / "trade_closed_history.csv"
    if closed_csv.exists():
        try:
            add = pd.read_csv(closed_csv)
            if not add.empty:
                add = add.dropna(how="all")
                if raw is None or raw.empty:
                    raw = add.copy()
                else:
                    raw = pd.concat([raw, add], ignore_index=True)
        except Exception:
            pass
    if "status" not in raw.columns:
        raw["status"] = "CLOSED"
    out = raw[raw["status"].astype(str).str.upper() == "CLOSED"].copy()
    for col in ["profit", "regime_spread_ratio", "mfe_30", "mae_30"]:
        if col not in out.columns:
            out[col] = np.nan
    out["profit"] = pd.to_numeric(out["profit"], errors="coerce").fillna(0.0)
    out["regime_spread_ratio"] = pd.to_numeric(out["regime_spread_ratio"], errors="coerce")
    out["open_dt"] = pd.to_datetime(out.get("open_time", ""), errors="coerce")
    out["close_dt"] = pd.to_datetime(out.get("close_time", ""), errors="coerce")
    out["duration_sec"] = (out["close_dt"] - out["open_dt"]).dt.total_seconds().fillna(0.0).clip(lower=0.0)
    out = out.sort_values(["close_dt", "ticket"], na_position="last").reset_index(drop=True)
    return out


def _extract_stage_scores(exit_reason: pd.Series) -> pd.DataFrame:
    text = exit_reason.astype(str).fillna("")
    return pd.DataFrame(
        {
            "protect": pd.to_numeric(text.str.extract(r"protect=(\d+)")[0], errors="coerce"),
            "lock": pd.to_numeric(text.str.extract(r"lock=(\d+)")[0], errors="coerce"),
            "hold": pd.to_numeric(text.str.extract(r"hold=(\d+)")[0], errors="coerce"),
        }
    )


def _recommend_exit_thresholds(closed: pd.DataFrame) -> dict[str, int]:
    stage = _extract_stage_scores(closed.get("exit_reason", pd.Series(dtype=str)))
    merged = closed.join(stage)
    defaults = {"protect": 180, "lock": 160, "hold": 140}
    out: dict[str, int] = {}

    protect_loss = merged[(merged["profit"] <= 0) & merged["protect"].notna()]["protect"]
    lock_win = merged[(merged["profit"] > 0) & merged["lock"].notna()]["lock"]
    hold_win = merged[(merged["profit"] > 0) & merged["hold"].notna()]["hold"]

    out["EXIT_PROTECT_THRESHOLD"] = int(np.clip(protect_loss.quantile(0.55), 120, 260)) if len(protect_loss) >= 20 else defaults["protect"]
    out["EXIT_LOCK_THRESHOLD"] = int(np.clip(lock_win.quantile(0.45), 100, 240)) if len(lock_win) >= 20 else defaults["lock"]
    out["EXIT_HOLD_THRESHOLD"] = int(np.clip(hold_win.quantile(0.60), 90, 260)) if len(hold_win) >= 20 else defaults["hold"]
    return out


def _recommend_confirm_ticks(closed: pd.DataFrame) -> dict[str, int]:
    spread = pd.to_numeric(closed.get("regime_spread_ratio", pd.Series(dtype=float)), errors="coerce")
    spread_recent = float(spread[spread > 0].tail(80).median()) if not spread.empty else 1.0
    duration_med = float(pd.to_numeric(closed.get("duration_sec", 0.0), errors="coerce").median())

    normal = 2
    if spread_recent >= 1.25 or duration_med < 600:
        normal = 3
    elif spread_recent <= 0.95 and duration_med > 1800:
        normal = 2

    return {
        "EXIT_CONFIRM_TICKS": int(np.clip(normal, 1, 4)),
        "EXIT_CONFIRM_TICKS_RANGE": int(np.clip(normal, 1, 4)),
        "EXIT_CONFIRM_TICKS_NORMAL": int(np.clip(normal, 1, 4)),
        "EXIT_CONFIRM_TICKS_EXPANSION": int(np.clip(normal + 1, 2, 5)),
    }


def _build_ev_inputs(closed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for idx, row in closed.iterrows():
        hist = closed.iloc[:idx]
        hist_sd = hist[
            (hist.get("symbol", "").astype(str) == str(row.get("symbol", "")))
            & (hist.get("direction", "").astype(str) == str(row.get("direction", "")))
        ]
        symbol = str(row.get("symbol", ""))
        spread_ratio = _safe_float(row.get("regime_spread_ratio", 1.0), default=1.0)
        base_cost = _symbol_map_value(symbol, BASE_COST_BY_SYMBOL)
        cost = float(base_cost * np.clip(spread_ratio if spread_ratio > 0 else 1.0, 0.8, 2.2))
        profit = _safe_float(row.get("profit", 0.0), default=0.0)
        mfe_direct = pd.to_numeric(row.get("mfe_30", np.nan), errors="coerce")
        mae_direct = pd.to_numeric(row.get("mae_30", np.nan), errors="coerce")
        if pd.notna(mfe_direct):
            mfe_val = float(mfe_direct)
        else:
            pos_hist = hist_sd[pd.to_numeric(hist_sd.get("profit", 0.0), errors="coerce") > 0]["profit"]
            mfe_val = float(pos_hist.quantile(0.75)) if len(pos_hist) >= 5 else max(0.0, profit)
        if pd.notna(mae_direct):
            mae_val = abs(float(mae_direct))
        else:
            neg_hist = hist_sd[pd.to_numeric(hist_sd.get("profit", 0.0), errors="coerce") < 0]["profit"].abs()
            mae_val = float(neg_hist.quantile(0.75)) if len(neg_hist) >= 5 else abs(min(0.0, profit))
        baseline = float(hist_sd["profit"].tail(40).median()) if len(hist_sd) >= 10 else 0.0
        guard = _symbol_map_value(symbol, PROFIT_GUARD_BY_SYMBOL)
        ev_exit = profit - cost
        rows.append((profit, cost, mfe_val, mae_val, max(0.0, baseline), guard, ev_exit))
    return pd.DataFrame(
        rows,
        columns=["profit", "cost", "mfe_proxy", "mae_proxy", "baseline", "guard", "ev_exit"],
    )


def _compute_ev_grid_score(ev_inputs: pd.DataFrame, ev_k: float) -> float:
    if ev_inputs.empty:
        return -1e9
    eval_df = ev_inputs.copy()
    eval_df["ev_hold"] = (eval_df["mfe_proxy"] - eval_df["cost"]) - (float(ev_k) * (eval_df["mae_proxy"] + eval_df["cost"]))
    eval_df["ev_delta"] = eval_df["ev_hold"] - eval_df["ev_exit"]
    threshold = np.maximum(eval_df["baseline"], eval_df["guard"])
    eval_df["is_good"] = ((eval_df["ev_delta"] <= 0.0) & (eval_df["profit"] >= threshold)).astype(int)
    pos = eval_df[eval_df["is_good"] == 1]["profit"]
    neg = eval_df[eval_df["is_good"] == 0]["profit"]
    if pos.empty or neg.empty:
        return -1e9
    profit_sep = float(pos.median() - neg.median())
    good_rate = float(eval_df["is_good"].mean())
    balance = max(0.2, 1.0 - abs(good_rate - 0.35) * 1.4)
    return profit_sep * balance


def _recommend_ev_k(closed: pd.DataFrame) -> float:
    ev_inputs = _build_ev_inputs(closed)
    best_k = 1.2
    best_score = -1e9
    for k in np.arange(0.80, 2.01, 0.05):
        score = _compute_ev_grid_score(ev_inputs, float(k))
        if score > best_score:
            best_score = score
            best_k = float(k)
    return round(best_k, 2)


def calibrate(source_csv: Path, max_rows: int = 6000) -> dict[str, object]:
    closed = _load_closed(source_csv)
    if max_rows > 0 and len(closed) > max_rows:
        closed = closed.tail(int(max_rows)).reset_index(drop=True)
    if len(closed) < 30:
        raise ValueError(f"Not enough closed rows for calibration: {len(closed)}")
    out = {}
    out.update(_recommend_exit_thresholds(closed))
    out.update(_recommend_confirm_ticks(closed))
    out["EXIT_EV_K"] = _recommend_ev_k(closed)
    spread_recent = pd.to_numeric(closed["regime_spread_ratio"], errors="coerce")
    out["DYNAMIC_COST_RECENT_SPREAD_MEDIAN"] = round(float(spread_recent[spread_recent > 0].tail(80).median()), 4)
    out["sample_size"] = int(len(closed))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate exit thresholds and EV parameter from trade history.")
    parser.add_argument("--source", default=str(PROJECT_ROOT / "data" / "trades" / "trade_history.csv"))
    parser.add_argument("--out-json", default=str(PROJECT_ROOT / "models" / "exit_calibration.json"))
    parser.add_argument("--max-rows", type=int, default=6000, help="Use only recent closed rows for fast calibration.")
    parser.add_argument("--print-env", action="store_true", help="Print env snippet to apply recommendations.")
    args = parser.parse_args()

    source = Path(args.source)
    result = calibrate(source, max_rows=int(args.max_rows))
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"calibration_json: {out_json}")
    if args.print_env:
        keys = [
            "EXIT_PROTECT_THRESHOLD",
            "EXIT_LOCK_THRESHOLD",
            "EXIT_HOLD_THRESHOLD",
            "EXIT_CONFIRM_TICKS",
            "EXIT_CONFIRM_TICKS_RANGE",
            "EXIT_CONFIRM_TICKS_NORMAL",
            "EXIT_CONFIRM_TICKS_EXPANSION",
            "EXIT_EV_K",
        ]
        print("\n# .env snippet")
        for k in keys:
            print(f"{k}={result[k]}")


if __name__ == "__main__":
    main()
