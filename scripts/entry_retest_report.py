"""
Entry retest signal contribution report.

Generates JSON/Markdown reports from closed trade history:
- per-symbol signal frequency
- win rate / avg pnl / total pnl
- uplift vs symbol baseline avg pnl
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLOSED = PROJECT_ROOT / "data" / "trades" / "trade_closed_history.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "reports"

SIGNAL_PATTERNS = {
    "box_breakout_up": ["structure: 박스 상단 돌파"],
    "box_breakout_down": ["structure: 박스 하단 돌파"],
    "box_retest_hold_up": ["structure: 박스 상단 돌파지지 확인"],
    "box_retest_hold_down": ["structure: 박스 하단 이탈저항 확인"],
    "bb20_retest_hold_up": ["flow: bb 20/2 상단 돌파지지 확인"],
    "bb20_retest_hold_down": ["flow: bb 20/2 하단 이탈저항 확인"],
    "bb20_mid_hold_up": ["flow: bb 20/2 중앙선 돌파지지 확인"],
    "bb20_mid_hold_down": ["flow: bb 20/2 중앙선 이탈저항 확인"],
    "bb20_touch": ["flow: bb 20/2 하단 터치", "flow: bb 20/2 상단 터치"],
    "bb4_touch": ["flow: bb 4/4 하단 터치", "flow: bb 4/4 상단 터치"],
}


def _read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path)


def _canonical_symbol(value: str) -> str:
    s = str(value or "").upper()
    if "BTC" in s:
        return "BTCUSD"
    if "XAU" in s or "GOLD" in s:
        return "XAUUSD"
    if "NAS" in s or "US100" in s or "USTEC" in s:
        return "NAS100"
    return s.strip()


def build_report(closed_csv: Path, out_dir: Path, days: int) -> tuple[Path, Path]:
    df = _read_csv(closed_csv)
    if df.empty:
        raise RuntimeError("closed trade history is empty")

    df["symbol_key"] = df.get("symbol_key", df.get("symbol", "")).fillna("").astype(str).map(_canonical_symbol)
    df["profit"] = pd.to_numeric(df.get("profit", 0.0), errors="coerce").fillna(0.0)
    df["entry_reason"] = df.get("entry_reason", "").fillna("").astype(str).str.lower()
    df["close_time"] = pd.to_datetime(df.get("close_time", ""), errors="coerce")
    df["open_time"] = pd.to_datetime(df.get("open_time", ""), errors="coerce")
    row_time = df["close_time"].fillna(df["open_time"])
    ref = row_time.dropna().max()
    if pd.isna(ref):
        ref = pd.Timestamp(datetime.now())
    start = ref - pd.Timedelta(days=max(1, int(days)))
    df = df[row_time >= start].copy()
    df = df[df["symbol_key"].isin(["NAS100", "XAUUSD", "BTCUSD"])].copy()
    if df.empty:
        raise RuntimeError("no rows in requested time window/symbols")

    baseline = (
        df.groupby("symbol_key", dropna=False)["profit"]
        .agg(n="count", win_rate=lambda s: float((s > 0).mean()), avg_pnl="mean", total_pnl="sum")
        .reset_index()
    )
    baseline_map = {r["symbol_key"]: float(r["avg_pnl"]) for _, r in baseline.iterrows()}

    signal_rows = []
    for signal, patterns in SIGNAL_PATTERNS.items():
        mask = df["entry_reason"].map(lambda x: any(p in x for p in patterns))
        part = df[mask].copy()
        if part.empty:
            continue
        for sym, g in part.groupby("symbol_key", dropna=False):
            avg = float(g["profit"].mean())
            base = float(baseline_map.get(sym, 0.0))
            signal_rows.append(
                {
                    "symbol": str(sym),
                    "signal": str(signal),
                    "samples": int(len(g)),
                    "signal_rate": float(len(g) / max(1, int((df["symbol_key"] == sym).sum()))),
                    "win_rate": float((g["profit"] > 0).mean()),
                    "avg_pnl": avg,
                    "total_pnl": float(g["profit"].sum()),
                    "baseline_avg_pnl": base,
                    "uplift_vs_baseline": float(avg - base),
                }
            )

    signal_df = pd.DataFrame(signal_rows)
    signal_df = signal_df.sort_values(["symbol", "samples", "uplift_vs_baseline"], ascending=[True, False, False])

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "window_days": int(days),
        "window_start": str(start),
        "window_end": str(ref),
        "rows": int(len(df)),
        "baseline_by_symbol": baseline.to_dict(orient="records"),
        "signal_contribution": signal_df.to_dict(orient="records"),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"entry_retest_signal_report_{stamp}.json"
    md_path = out_dir / f"entry_retest_signal_report_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Entry Retest Signal Report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- window_days: {report['window_days']}",
        f"- window_start: {report['window_start']}",
        f"- window_end: {report['window_end']}",
        f"- rows: {report['rows']}",
        "",
        "## Baseline By Symbol",
    ]
    for row in report["baseline_by_symbol"]:
        lines.append(
            f"- {row['symbol_key']}: n={row['n']}, win_rate={float(row['win_rate']):.3f}, "
            f"avg_pnl={float(row['avg_pnl']):.4f}, total_pnl={float(row['total_pnl']):.4f}"
        )
    lines.append("")
    lines.append("## Signal Contribution")
    if signal_df.empty:
        lines.append("- no matching signals in this window")
    else:
        for row in report["signal_contribution"]:
            lines.append(
                f"- {row['symbol']} | {row['signal']}: n={row['samples']}, rate={row['signal_rate']:.3f}, "
                f"win={row['win_rate']:.3f}, avg={row['avg_pnl']:.4f}, uplift={row['uplift_vs_baseline']:.4f}"
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closed-csv", type=str, default=str(DEFAULT_CLOSED))
    parser.add_argument("--out-dir", type=str, default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    json_path, md_path = build_report(
        closed_csv=Path(args.closed_csv),
        out_dir=Path(args.out_dir),
        days=int(args.days),
    )
    print(f"json={json_path}")
    print(f"md={md_path}")


if __name__ == "__main__":
    main()

