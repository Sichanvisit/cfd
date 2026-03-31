"""
Preflight 24h diagnostics report.

Outputs JSON/Markdown with:
- blocked_by distribution
- preflight_* block/enter rates
- entered trades win-rate proxy by preflight group (matched via symbol/action/time)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.trade_csv_schema import read_csv_resilient

DEFAULT_DECISIONS = PROJECT_ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_CLOSED = PROJECT_ROOT / "data" / "trades" / "trade_closed_history.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "reports"


def _read_csv(path: Path) -> pd.DataFrame:
    frame, ok = read_csv_resilient(path)
    if ok:
        return frame
    raise RuntimeError(f"failed_to_read_csv: {path}")


def _canon_symbol(value: str) -> str:
    s = str(value or "").upper()
    if "BTC" in s:
        return "BTCUSD"
    if "XAU" in s or "GOLD" in s:
        return "XAUUSD"
    if "NAS" in s or "US100" in s or "USTEC" in s:
        return "NAS100"
    return s.strip()


def _canon_action(value: str) -> str:
    s = str(value or "").upper().strip()
    if s in {"BUY", "LONG"}:
        return "BUY"
    if s in {"SELL", "SHORT"}:
        return "SELL"
    return s


def _ensure_cols(df: pd.DataFrame, cols: list[str], default: str = "UNKNOWN") -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = default
        out[c] = out[c].fillna(default).astype(str).str.strip()
        out.loc[out[c] == "", c] = default
    return out


def build_report(
    decisions_csv: Path,
    closed_csv: Path,
    out_dir: Path,
    hours: int,
    match_tolerance_sec: int,
) -> tuple[Path, Path]:
    dec = _read_csv(decisions_csv)
    if dec.empty:
        raise RuntimeError("entry decisions csv is empty")
    dec = _ensure_cols(
        dec,
        cols=[
            "preflight_regime",
            "preflight_liquidity",
            "preflight_allowed_action",
            "preflight_approach_mode",
            "preflight_reason",
            "blocked_by",
            "outcome",
            "symbol",
            "action",
            "entry_decision_mode",
            "decision_rule_version",
            "utility_u",
            "utility_p_raw",
            "utility_p_calibrated",
        ],
    )
    # Preserve semantics for block/outcome even if legacy files miss columns.
    dec["blocked_by"] = dec["blocked_by"].replace("UNKNOWN", "")
    dec["outcome"] = dec["outcome"].replace("UNKNOWN", "")
    dec["time"] = pd.to_datetime(dec.get("time", ""), errors="coerce")
    dec = dec[dec["time"].notna()].copy()
    if dec.empty:
        raise RuntimeError("entry decisions have no valid timestamps")
    dec["symbol_key"] = dec["symbol"].map(_canon_symbol)
    dec["action_key"] = dec["action"].map(_canon_action)
    end_ts = dec["time"].max()
    start_ts = end_ts - pd.Timedelta(hours=max(1, int(hours)))
    dec = dec[dec["time"] >= start_ts].copy()
    if dec.empty:
        raise RuntimeError("no decision rows in requested window")

    dec["blocked_by"] = dec["blocked_by"].fillna("").astype(str).str.strip()
    dec["is_blocked"] = dec["blocked_by"].str.len() > 0
    dec["is_entered"] = dec["outcome"].fillna("").astype(str).str.lower().eq("entered")

    blocked_dist = (
        dec.assign(blocked_key=dec["blocked_by"].where(dec["blocked_by"].str.len() > 0, "entered_or_not_blocked"))
        .groupby("blocked_key", dropna=False)
        .size()
        .reset_index(name="n")
        .sort_values("n", ascending=False)
    )
    blocked_dist["rate"] = blocked_dist["n"] / max(1, len(dec))
    blocked_top10 = blocked_dist.head(10).copy()

    dec["utility_u"] = pd.to_numeric(dec.get("utility_u", 0.0), errors="coerce")
    dec["utility_p_raw"] = pd.to_numeric(dec.get("utility_p_raw", pd.NA), errors="coerce")
    dec["utility_p_calibrated"] = pd.to_numeric(dec.get("utility_p_calibrated", pd.NA), errors="coerce")

    mode_stats = (
        dec.groupby(["entry_decision_mode", "decision_rule_version"], dropna=False)
        .size()
        .reset_index(name="n")
        .sort_values("n", ascending=False)
    )
    mode_stats["rate"] = mode_stats["n"] / max(1, len(dec))
    fallback_n = int(
        mode_stats[
            mode_stats["decision_rule_version"].fillna("").astype(str).str.contains("fallback", case=False, regex=False)
        ]["n"].sum()
    )
    fallback_ratio = float(fallback_n / max(1, len(dec)))

    entered = dec[dec["is_entered"]].copy()
    symbol_entered = (
        entered.groupby("symbol_key", dropna=False).size().reset_index(name="entered_n").sort_values("entered_n", ascending=False)
    )
    symbol_entered["entered_rate_vs_decisions"] = symbol_entered["entered_n"] / max(1, len(dec))

    pre_cols = ["preflight_regime", "preflight_liquidity", "preflight_allowed_action", "preflight_approach_mode"]
    pre_rows = []
    for c in pre_cols:
        grp = dec.groupby(c, dropna=False)
        for k, g in grp:
            n = int(len(g))
            blocked_n = int(g["is_blocked"].sum())
            entered_n = int(g["is_entered"].sum())
            pre_rows.append(
                {
                    "field": c,
                    "value": str(k),
                    "n": n,
                    "blocked_n": blocked_n,
                    "blocked_rate": float(blocked_n / max(1, n)),
                    "entered_n": entered_n,
                    "entered_rate": float(entered_n / max(1, n)),
                }
            )
    pre_stats = pd.DataFrame(pre_rows).sort_values(["field", "n"], ascending=[True, False])

    closed_symbol_perf = pd.DataFrame(columns=["symbol_key", "n", "win_rate", "avg_profit", "max_loss", "total_profit"])
    preflight_pnl = pd.DataFrame(columns=["field", "value", "closed_matched_n", "win_rate", "avg_profit", "total_profit"])
    win_rows = []
    try:
        closed = _read_csv(closed_csv)
        if not closed.empty:
            closed = _ensure_cols(closed, cols=["symbol", "direction"], default="")
            closed["open_ts"] = pd.to_datetime(closed.get("open_ts", closed.get("open_time", "")), errors="coerce")
            closed["profit"] = pd.to_numeric(closed.get("profit", 0.0), errors="coerce").fillna(0.0)
            closed = closed[closed["open_ts"].notna()].copy()
            if not closed.empty:
                closed["symbol_key"] = closed["symbol"].map(_canon_symbol)
                closed["action_key"] = closed["direction"].map(_canon_action)
                # symbol-level pnl/win summary in the same time window
                close_ts = pd.to_datetime(closed.get("close_ts", pd.NaT), errors="coerce")
                in_window = close_ts.notna() & (close_ts >= start_ts) & (close_ts <= end_ts)
                close_window = closed[in_window].copy()
                if close_window.empty:
                    close_window = closed.copy()
                if not close_window.empty:
                    closed_symbol_perf = (
                        close_window.groupby("symbol_key", dropna=False)["profit"]
                        .agg(
                            n="count",
                            win_rate=lambda s: float((s > 0).mean()),
                            avg_profit="mean",
                            max_loss="min",
                            total_profit="sum",
                        )
                        .reset_index()
                        .sort_values("n", ascending=False)
                    )
                entered = dec[dec["is_entered"]].copy()
                if not entered.empty:
                    entered = entered.sort_values(["symbol_key", "action_key", "time"])
                    closed = closed.sort_values(["symbol_key", "action_key", "open_ts"])
                    matched = pd.merge_asof(
                        left=closed,
                        right=entered[
                            [
                                "time",
                                "symbol_key",
                                "action_key",
                                "preflight_regime",
                                "preflight_liquidity",
                                "preflight_allowed_action",
                                "preflight_approach_mode",
                            ]
                        ],
                        left_on="open_ts",
                        right_on="time",
                        by=["symbol_key", "action_key"],
                        direction="nearest",
                        tolerance=pd.Timedelta(seconds=max(10, int(match_tolerance_sec))),
                    )
                    matched = matched[matched["time"].notna()].copy()
                    if not matched.empty:
                        for c in pre_cols:
                            g = matched.groupby(c, dropna=False)
                            for k, part in g:
                                n = int(len(part))
                                wr = float((part["profit"] > 0).mean()) if n else 0.0
                                avg = float(part["profit"].mean()) if n else 0.0
                                win_rows.append(
                                    {
                                        "field": c,
                                        "value": str(k),
                                        "closed_matched_n": n,
                                        "win_rate": wr,
                                        "avg_profit": avg,
                                        "total_profit": float(part["profit"].sum()),
                                    }
                                )
                        # compact view requested: regime/liquidity only
                        compact_rows = []
                        for c in ("preflight_regime", "preflight_liquidity"):
                            g2 = matched.groupby(c, dropna=False)
                            for k, part in g2:
                                n2 = int(len(part))
                                compact_rows.append(
                                    {
                                        "field": c,
                                        "value": str(k),
                                        "closed_matched_n": n2,
                                        "win_rate": float((part["profit"] > 0).mean()) if n2 else 0.0,
                                        "avg_profit": float(part["profit"].mean()) if n2 else 0.0,
                                        "total_profit": float(part["profit"].sum()) if n2 else 0.0,
                                    }
                                )
                        preflight_pnl = pd.DataFrame(compact_rows).sort_values(
                            ["field", "closed_matched_n"], ascending=[True, False]
                        )
    except Exception:
        win_rows = []

    win_stats = pd.DataFrame(win_rows)
    if not win_stats.empty:
        win_stats = win_stats.sort_values(["field", "closed_matched_n"], ascending=[True, False])

    btc_dec = dec[dec["symbol_key"] == "BTCUSD"].copy()
    btc_entered = btc_dec[btc_dec["is_entered"]].copy()
    btc_u = pd.to_numeric(btc_entered.get("utility_u", pd.Series(dtype=float)), errors="coerce").dropna()
    btc_utility_dist = {}
    if not btc_u.empty:
        btc_utility_dist = {
            "n": int(len(btc_u)),
            "p5": float(btc_u.quantile(0.05)),
            "p50": float(btc_u.quantile(0.50)),
            "p95": float(btc_u.quantile(0.95)),
            "mean": float(btc_u.mean()),
        }
    btc_closed = closed_symbol_perf[closed_symbol_perf["symbol_key"] == "BTCUSD"].copy()
    btc_summary = {
        "entered_n": int(len(btc_entered)),
        "decision_n": int(len(btc_dec)),
        "entered_rate": float(len(btc_entered) / max(1, len(btc_dec))),
        "utility_u_distribution": btc_utility_dist,
    }
    if not btc_closed.empty:
        row = btc_closed.iloc[0]
        btc_summary.update(
            {
                "closed_n": int(row.get("n", 0)),
                "win_rate": float(row.get("win_rate", 0.0)),
                "avg_profit": float(row.get("avg_profit", 0.0)),
                "max_loss": float(row.get("max_loss", 0.0)),
                "total_profit": float(row.get("total_profit", 0.0)),
            }
        )

    p_dist = {}
    p_raw = pd.to_numeric(dec.get("utility_p_raw", pd.Series(dtype=float)), errors="coerce").dropna()
    p_cal = pd.to_numeric(dec.get("utility_p_calibrated", pd.Series(dtype=float)), errors="coerce").dropna()
    if not p_raw.empty:
        p_dist["raw"] = {
            "n": int(len(p_raw)),
            "p5": float(p_raw.quantile(0.05)),
            "p50": float(p_raw.quantile(0.50)),
            "p95": float(p_raw.quantile(0.95)),
        }
    if not p_cal.empty:
        p_dist["calibrated"] = {
            "n": int(len(p_cal)),
            "p5": float(p_cal.quantile(0.05)),
            "p50": float(p_cal.quantile(0.50)),
            "p95": float(p_cal.quantile(0.95)),
        }

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "window_hours": int(hours),
        "window_start": str(start_ts),
        "window_end": str(end_ts),
        "rows_decisions": int(len(dec)),
        "decision_mode_stats": mode_stats.to_dict(orient="records"),
        "fallback_ratio": float(fallback_ratio),
        "blocked_by_distribution": blocked_dist.to_dict(orient="records"),
        "blocked_by_top10": blocked_top10.to_dict(orient="records"),
        "symbol_entered_count": symbol_entered.to_dict(orient="records"),
        "symbol_pnl_summary": closed_symbol_perf.to_dict(orient="records"),
        "preflight_block_enter_stats": pre_stats.to_dict(orient="records"),
        "preflight_entry_pnl_summary": preflight_pnl.to_dict(orient="records"),
        "preflight_winrate_proxy": win_stats.to_dict(orient="records"),
        "btc_summary": btc_summary,
        "p_distribution": p_dist,
        "match_tolerance_sec": int(match_tolerance_sec),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"preflight_24h_report_{stamp}.json"
    md_path = out_dir / f"preflight_24h_report_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Preflight 24h Report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- window_hours: {report['window_hours']}",
        f"- window_start: {report['window_start']}",
        f"- window_end: {report['window_end']}",
        f"- rows_decisions: {report['rows_decisions']}",
        f"- match_tolerance_sec: {report['match_tolerance_sec']}",
        f"- fallback_ratio: {report['fallback_ratio']:.3f}",
        "",
        "## decision_mode / decision_rule_version",
    ]
    for row in report["decision_mode_stats"][:20]:
        lines.append(
            f"- mode={row['entry_decision_mode']}, rule={row['decision_rule_version']}: n={row['n']}, rate={row['rate']:.3f}"
        )
    lines.extend(
        [
            "",
            "## blocked_by Top10",
        ]
    )
    for row in report["blocked_by_top10"]:
        lines.append(f"- {row['blocked_key']}: n={row['n']}, rate={float(row['rate']):.3f}")
    lines.extend(
        [
            "",
            "## symbol entered count",
        ]
    )
    for row in report["symbol_entered_count"]:
        lines.append(
            f"- {row['symbol_key']}: entered_n={row['entered_n']}, entered_rate_vs_decisions={row['entered_rate_vs_decisions']:.3f}"
        )
    lines.extend(
        [
            "",
            "## symbol pnl summary",
        ]
    )
    for row in report["symbol_pnl_summary"]:
        lines.append(
            f"- {row['symbol_key']}: n={row['n']}, win_rate={row['win_rate']:.3f}, avg_profit={row['avg_profit']:.4f}, "
            f"max_loss={row['max_loss']:.4f}, total_profit={row['total_profit']:.4f}"
        )
    lines.extend(
        [
            "",
            "## preflight regime/liquidity entry+pnl",
        ]
    )
    for row in report["preflight_entry_pnl_summary"]:
        lines.append(
            f"- {row['field']}={row['value']}: n={row['closed_matched_n']}, win_rate={row['win_rate']:.3f}, "
            f"avg_profit={row['avg_profit']:.4f}, total_profit={row['total_profit']:.4f}"
        )
    lines.extend(
        [
            "",
            "## BTC summary",
            f"- entered_n={report['btc_summary'].get('entered_n', 0)}, decision_n={report['btc_summary'].get('decision_n', 0)}, "
            f"entered_rate={float(report['btc_summary'].get('entered_rate', 0.0)):.3f}",
        ]
    )
    if report["btc_summary"].get("closed_n") is not None:
        lines.append(
            f"- closed_n={report['btc_summary'].get('closed_n', 0)}, win_rate={float(report['btc_summary'].get('win_rate', 0.0)):.3f}, "
            f"avg_profit={float(report['btc_summary'].get('avg_profit', 0.0)):.4f}, "
            f"max_loss={float(report['btc_summary'].get('max_loss', 0.0)):.4f}, "
            f"total_profit={float(report['btc_summary'].get('total_profit', 0.0)):.4f}"
        )
    ud = report["btc_summary"].get("utility_u_distribution", {}) or {}
    if ud:
        lines.append(
            f"- utility_u: n={ud.get('n', 0)}, p5={float(ud.get('p5', 0.0)):.4f}, p50={float(ud.get('p50', 0.0)):.4f}, "
            f"p95={float(ud.get('p95', 0.0)):.4f}, mean={float(ud.get('mean', 0.0)):.4f}"
        )
    lines.extend(
        [
            "",
            "## p distribution",
        ]
    )
    if report["p_distribution"].get("raw"):
        r = report["p_distribution"]["raw"]
        lines.append(f"- raw: n={r['n']}, p5={r['p5']:.3f}, p50={r['p50']:.3f}, p95={r['p95']:.3f}")
    if report["p_distribution"].get("calibrated"):
        c = report["p_distribution"]["calibrated"]
        lines.append(f"- calibrated: n={c['n']}, p5={c['p5']:.3f}, p50={c['p50']:.3f}, p95={c['p95']:.3f}")
    lines.extend(
        [
            "",
            "## preflight block/enter stats",
        ]
    )
    for row in report["preflight_block_enter_stats"][:60]:
        lines.append(
            f"- {row['field']}={row['value']}: n={row['n']}, blocked={row['blocked_n']} ({row['blocked_rate']:.3f}), "
            f"entered={row['entered_n']} ({row['entered_rate']:.3f})"
        )
    lines.append("")
    lines.append("## preflight winrate proxy (matched closed trades)")
    if not report["preflight_winrate_proxy"]:
        lines.append("- no matched closed trades in window/tolerance")
    else:
        for row in report["preflight_winrate_proxy"][:60]:
            lines.append(
                f"- {row['field']}={row['value']}: n={row['closed_matched_n']}, "
                f"win_rate={row['win_rate']:.3f}, avg_profit={row['avg_profit']:.4f}"
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decisions-csv", type=str, default=str(DEFAULT_DECISIONS))
    parser.add_argument("--closed-csv", type=str, default=str(DEFAULT_CLOSED))
    parser.add_argument("--out-dir", type=str, default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--match-tolerance-sec", type=int, default=300)
    args = parser.parse_args()
    json_path, md_path = build_report(
        decisions_csv=Path(args.decisions_csv),
        closed_csv=Path(args.closed_csv),
        out_dir=Path(args.out_dir),
        hours=int(args.hours),
        match_tolerance_sec=int(args.match_tolerance_sec),
    )
    print(f"json={json_path}")
    print(f"md={md_path}")


if __name__ == "__main__":
    main()
