"""Phase 8 validation checklist report.

Checks:
1. recovery winner sample coverage
2. wait_be quality
3. wait_tp1 hang risk
4. reverse_now overfire
5. setup-aware recovery policy consistency
6. exit metadata preservation
7. no major regression on entry quality
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import Config
from backend.services.trade_csv_schema import normalize_trade_df, now_kst_dt, read_csv_resilient, text_to_kst_epoch


ENTRY_DECISIONS = ROOT / "data" / "trades" / "entry_decisions.csv"
TRADE_HISTORY = ROOT / "data" / "trades" / "trade_history.csv"
CLOSED_HISTORY = ROOT / "data" / "trades" / "trade_closed_history.csv"
OUT_DIR = ROOT / "data" / "analysis"

TARGET_WINNERS = ("wait_be", "wait_tp1", "cut_now", "reverse_now")


@dataclass
class CheckResult:
    status: str
    summary: str
    detail: dict

    def to_dict(self) -> dict:
        return {
            "status": str(self.status),
            "summary": str(self.summary),
            "detail": dict(self.detail or {}),
        }


def _read_entry_decisions() -> pd.DataFrame:
    if not ENTRY_DECISIONS.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(ENTRY_DECISIONS, encoding="utf-8-sig", engine="python", on_bad_lines="skip")
    except Exception:
        return pd.DataFrame()
    if "time" not in df.columns:
        df["time"] = ""
    df["event_time"] = pd.to_datetime(df["time"], errors="coerce")
    return df


def _read_trade_df(path: Path) -> pd.DataFrame:
    df, _ = read_csv_resilient(path, expected_columns=[])
    df = normalize_trade_df(df)
    if df.empty:
        return df
    if "open_time" not in df.columns:
        df["open_time"] = ""
    if "close_time" not in df.columns:
        df["close_time"] = ""
    status = df.get("status", pd.Series(dtype=str)).fillna("").astype(str).str.upper()
    event_text = df["close_time"].where(status == "CLOSED", df["open_time"])
    df["event_time"] = pd.to_datetime(event_text, errors="coerce")
    return df


def _recent(df: pd.DataFrame, *, cutoff: pd.Timestamp) -> pd.DataFrame:
    if df.empty or "event_time" not in df.columns:
        return df.iloc[0:0].copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    out = df[df["event_time"] >= cutoff].copy()
    return out


def _nonempty(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _value_counts(series: pd.Series) -> dict[str, int]:
    clean = _nonempty(series)
    clean = clean[clean != ""]
    if clean.empty:
        return {}
    out = clean.value_counts().to_dict()
    return {str(k): int(v) for k, v in out.items()}


def _status(pass_cond: bool, *, inconclusive: bool = False) -> str:
    if inconclusive:
        return "inconclusive"
    return "pass" if bool(pass_cond) else "fail"


def _max_consecutive_reverse(df: pd.DataFrame) -> dict[str, int]:
    if df.empty:
        return {}
    out: dict[str, int] = {}
    work = df.copy()
    work["symbol"] = _nonempty(work.get("symbol", pd.Series(dtype=str)))
    work["decision_winner"] = _nonempty(work.get("decision_winner", pd.Series(dtype=str))).str.lower()
    work = work.sort_values("event_time")
    for symbol, part in work.groupby("symbol"):
        current = 0
        best = 0
        for winner in part["decision_winner"].tolist():
            if winner == "reverse_now":
                current += 1
                best = max(best, current)
            else:
                current = 0
        out[str(symbol)] = int(best)
    return out


def check_1_recovery_winner_sample(recent_trades: pd.DataFrame) -> CheckResult:
    winners = _nonempty(recent_trades.get("decision_winner", pd.Series(dtype=str))).str.lower()
    counts = {k: int((winners == k).sum()) for k in TARGET_WINNERS}
    observed = [k for k, v in counts.items() if int(v) > 0]
    ok = len(observed) >= 3
    return CheckResult(
        status=_status(ok),
        summary=f"observed={len(observed)}/4 ({', '.join(observed) if observed else 'none'})",
        detail={"counts": counts, "observed": observed, "required_min": 3},
    )


def check_2_wait_be_quality(recent_closed: pd.DataFrame) -> CheckResult:
    work = recent_closed.copy()
    if work.empty:
        return CheckResult("inconclusive", "no closed rows", {"sample_count": 0})
    work["decision_winner"] = _nonempty(work.get("decision_winner", pd.Series(dtype=str))).str.lower()
    work = work[work["decision_winner"] == "wait_be"].copy()
    if work.empty:
        return CheckResult("inconclusive", "no wait_be sample", {"sample_count": 0})
    be_floor = -float(getattr(Config, "EXIT_RECOVERY_BE_CLOSE_USD", 0.02))
    work["profit"] = pd.to_numeric(work.get("profit", 0.0), errors="coerce").fillna(0.0)
    success = (work["profit"] >= be_floor).sum()
    rate = float(success) / float(len(work))
    ok = len(work) >= 1 and rate >= 0.60
    return CheckResult(
        status=_status(ok),
        summary=f"sample={len(work)}, success_rate={rate:.3f}, floor={be_floor:.4f}",
        detail={
            "sample_count": int(len(work)),
            "success_count": int(success),
            "success_rate": round(rate, 6),
            "profit_floor": float(be_floor),
            "profits": [round(float(x), 6) for x in work["profit"].tail(10).tolist()],
        },
    )


def check_3_wait_tp1_hang(recent_open: pd.DataFrame, recent_closed: pd.DataFrame) -> CheckResult:
    max_wait = int(getattr(Config, "EXIT_RECOVERY_WAIT_MAX_SECONDS", 240))
    long_rows: list[dict] = []
    if not recent_open.empty:
        work = recent_open.copy()
        work["decision_winner"] = _nonempty(work.get("decision_winner", pd.Series(dtype=str))).str.lower()
        work["open_ts"] = pd.to_numeric(work.get("open_ts", 0), errors="coerce").fillna(0).astype(int)
        missing = work["open_ts"] <= 0
        if missing.any():
            work.loc[missing, "open_ts"] = work.loc[missing, "open_time"].map(text_to_kst_epoch)
        now_epoch = int(now_kst_dt().timestamp())
        work["age_sec"] = (now_epoch - work["open_ts"]).clip(lower=0)
        over = work[(work["decision_winner"] == "wait_tp1") & (work["age_sec"] > max_wait)].copy()
        for _, row in over.iterrows():
            long_rows.append(
                {
                    "ticket": int(row.get("ticket", 0) or 0),
                    "symbol": str(row.get("symbol", "") or ""),
                    "age_sec": int(row.get("age_sec", 0) or 0),
                    "profit": float(pd.to_numeric(row.get("profit", 0.0), errors="coerce") or 0.0),
                }
            )
    tp1_closed = recent_closed.copy()
    tp1_closed["decision_winner"] = _nonempty(tp1_closed.get("decision_winner", pd.Series(dtype=str))).str.lower()
    tp1_closed = tp1_closed[tp1_closed["decision_winner"] == "wait_tp1"]
    ok = len(long_rows) == 0
    summary = f"open_too_long={len(long_rows)}, closed_samples={len(tp1_closed)}"
    return CheckResult(
        status=_status(ok, inconclusive=(len(long_rows) == 0 and len(tp1_closed) == 0)),
        summary=summary,
        detail={
            "open_too_long_count": int(len(long_rows)),
            "closed_sample_count": int(len(tp1_closed)),
            "too_long_rows": long_rows,
        },
    )


def check_4_reverse_now_overfire(recent_trades: pd.DataFrame) -> CheckResult:
    work = recent_trades.copy()
    if work.empty:
        return CheckResult("inconclusive", "no trade rows", {"sample_count": 0})
    work["decision_winner"] = _nonempty(work.get("decision_winner", pd.Series(dtype=str))).str.lower()
    domain = work[work["decision_winner"].isin(TARGET_WINNERS)].copy()
    if domain.empty:
        return CheckResult("inconclusive", "no recovery-domain winner sample", {"sample_count": 0})
    reverse_count = int((domain["decision_winner"] == "reverse_now").sum())
    ratio = float(reverse_count) / float(len(domain))
    streaks = _max_consecutive_reverse(work)
    max_streak = max(streaks.values()) if streaks else 0
    ok = ratio <= 0.45 and max_streak <= 3
    return CheckResult(
        status=_status(ok),
        summary=f"reverse_ratio={ratio:.3f}, max_consecutive={max_streak}",
        detail={
            "sample_count": int(len(domain)),
            "reverse_count": int(reverse_count),
            "reverse_ratio": round(ratio, 6),
            "max_consecutive_by_symbol": streaks,
        },
    )


def check_5_setup_policy_consistency(recent_trades: pd.DataFrame) -> CheckResult:
    work = recent_trades.copy()
    if work.empty:
        return CheckResult("inconclusive", "no trade rows", {"sample_count": 0})
    work["entry_setup_id"] = _nonempty(work.get("entry_setup_id", pd.Series(dtype=str))).str.lower()
    work["decision_winner"] = _nonempty(work.get("decision_winner", pd.Series(dtype=str))).str.lower()
    work = work[(work["entry_setup_id"] != "") & (work["decision_winner"] != "")]
    if work.empty:
        return CheckResult("inconclusive", "no setup-aware trade sample", {"sample_count": 0})

    range_setups = {"range_lower_reversal_buy", "range_upper_reversal_sell"}
    breakout_setups = {"breakout_retest_buy", "breakout_retest_sell"}
    range_part = work[work["entry_setup_id"].isin(range_setups)].copy()
    breakout_part = work[work["entry_setup_id"].isin(breakout_setups)].copy()

    range_preferred = int(range_part["decision_winner"].isin({"wait_be", "wait_tp1"}).sum())
    range_bad = int(range_part["decision_winner"].isin({"reverse_now", "cut_now"}).sum())
    breakout_preferred = int(breakout_part["decision_winner"].isin({"reverse_now", "cut_now", "exit_now"}).sum())
    breakout_bad = int(breakout_part["decision_winner"].isin({"wait_be", "wait_tp1"}).sum())
    ok = bool((len(range_part) == 0 or range_preferred >= range_bad) and (len(breakout_part) == 0 or breakout_preferred >= breakout_bad))
    inconclusive = len(range_part) == 0 and len(breakout_part) == 0
    return CheckResult(
        status=_status(ok, inconclusive=inconclusive),
        summary=(
            f"range(preferred={range_preferred},bad={range_bad},n={len(range_part)}), "
            f"breakout(preferred={breakout_preferred},bad={breakout_bad},n={len(breakout_part)})"
        ),
        detail={
            "range_rows": int(len(range_part)),
            "range_preferred": int(range_preferred),
            "range_bad": int(range_bad),
            "breakout_rows": int(len(breakout_part)),
            "breakout_preferred": int(breakout_preferred),
            "breakout_bad": int(breakout_bad),
            "winner_by_setup": {
                str(setup): {str(k): int(v) for k, v in part["decision_winner"].value_counts().to_dict().items()}
                for setup, part in work.groupby("entry_setup_id")
            },
        },
    )


def check_6_metadata_preservation(recent_trades: pd.DataFrame) -> CheckResult:
    work = recent_trades.copy()
    if work.empty:
        return CheckResult("inconclusive", "no trade rows", {"sample_count": 0})
    relevant = work[
        (_nonempty(work.get("decision_winner", pd.Series(dtype=str))) != "")
        | (_nonempty(work.get("exit_wait_state", pd.Series(dtype=str))) != "")
    ].copy()
    if relevant.empty:
        return CheckResult("inconclusive", "no exit metadata sample", {"sample_count": 0})

    required = ["entry_setup_id", "exit_profile", "exit_wait_state", "decision_winner"]
    fill_ratio: dict[str, float] = {}
    for col in required:
        if col not in relevant.columns:
            fill_ratio[col] = 0.0
            continue
        clean = _nonempty(relevant[col])
        fill_ratio[col] = round(float((clean != "").sum()) / float(len(relevant)), 6)
    ok = all(v >= 0.80 for v in fill_ratio.values())
    return CheckResult(
        status=_status(ok),
        summary=", ".join([f"{k}={v:.2%}" for k, v in fill_ratio.items()]),
        detail={"sample_count": int(len(relevant)), "fill_ratio": fill_ratio},
    )


def check_7_no_regression(recent_entries: pd.DataFrame) -> CheckResult:
    work = recent_entries.copy()
    if work.empty:
        return CheckResult("inconclusive", "no recent entry decisions", {"sample_count": 0})
    for col in ["outcome", "setup_id", "box_state", "bb_state", "action", "symbol", "entry_wait_state"]:
        if col not in work.columns:
            work[col] = ""
        work[col] = work[col].fillna("").astype(str)
    entered = work[work["outcome"].str.lower() == "entered"].copy()
    if entered.empty:
        return CheckResult("inconclusive", "no entered rows", {"sample_count": 0})

    entered_without_setup = int((entered["setup_id"].str.strip() == "").sum())
    upper_buy_entered = int(
        ((entered["action"].str.upper() == "BUY") & (entered["box_state"].str.upper().isin({"UPPER", "ABOVE"}))).sum()
    )
    range_lower_non_edge = int(
        (
            (entered["setup_id"].str.lower() == "range_lower_reversal_buy")
            & (entered["bb_state"].str.upper() != "LOWER_EDGE")
        ).sum()
    )
    btc_conflict_range_buy = int(
        (
            (entered["symbol"].str.upper() == "BTCUSD")
            & (entered["setup_id"].str.lower() == "range_lower_reversal_buy")
            & (entered.get("entry_wait_state", pd.Series(dtype=str)).fillna("").astype(str).str.upper() == "CONFLICT")
        ).sum()
    )
    ok = all(v == 0 for v in [entered_without_setup, upper_buy_entered, range_lower_non_edge, btc_conflict_range_buy])
    return CheckResult(
        status=_status(ok),
        summary=(
            f"entered_without_setup={entered_without_setup}, upper_buy={upper_buy_entered}, "
            f"range_lower_non_edge={range_lower_non_edge}, btc_conflict_range_buy={btc_conflict_range_buy}"
        ),
        detail={
            "entered_total": int(len(entered)),
            "entered_without_setup": int(entered_without_setup),
            "upper_buy_entered": int(upper_buy_entered),
            "range_lower_non_edge": int(range_lower_non_edge),
            "btc_conflict_range_buy": int(btc_conflict_range_buy),
        },
    )


def _render_markdown(report: dict) -> str:
    lines = []
    lines.append(f"# Phase 8 Validation Report")
    lines.append("")
    lines.append(f"- Generated: {report['generated_at']}")
    if report.get("since"):
        lines.append(f"- Since: {report['since']}")
    else:
        lines.append(f"- Lookback hours: {report['lookback_hours']}")
    lines.append(f"- Overall: {report['overall_status']}")
    lines.append("")
    for key, item in report["checks"].items():
        lines.append(f"## {key}")
        lines.append(f"- Status: {item['status']}")
        lines.append(f"- Summary: {item['summary']}")
        lines.append(f"- Detail: `{json.dumps(item['detail'], ensure_ascii=False)}`")
        lines.append("")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 8 recovery/exit behavior.")
    parser.add_argument("lookback_hours", nargs="?", type=int, default=24)
    parser.add_argument("--since", dest="since", default="", help="KST timestamp or ISO datetime. Overrides lookback hours.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    lookback_hours = int(args.lookback_hours or 24)
    since_text = str(args.since or "").strip()
    cutoff = None
    if since_text:
        try:
            cutoff = pd.Timestamp(since_text)
            if cutoff.tzinfo is not None:
                cutoff = cutoff.tz_convert("Asia/Seoul").tz_localize(None)
            else:
                cutoff = cutoff.tz_localize(None) if getattr(cutoff, "tzinfo", None) is not None else cutoff
        except Exception:
            cutoff = None
    if cutoff is None:
        cutoff = pd.Timestamp((now_kst_dt() - timedelta(hours=max(1, lookback_hours))).replace(tzinfo=None))
        since_text = ""

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    entry_df = _recent(_read_entry_decisions(), cutoff=cutoff)
    open_df = _recent(_read_trade_df(TRADE_HISTORY), cutoff=cutoff)
    closed_df = _recent(_read_trade_df(CLOSED_HISTORY), cutoff=cutoff)
    trade_df = pd.concat([open_df, closed_df], ignore_index=True, sort=False) if (not open_df.empty or not closed_df.empty) else pd.DataFrame()

    checks = {
        "1_recovery_winner_sample": check_1_recovery_winner_sample(trade_df).to_dict(),
        "2_wait_be_quality": check_2_wait_be_quality(closed_df).to_dict(),
        "3_wait_tp1_hang": check_3_wait_tp1_hang(open_df, closed_df).to_dict(),
        "4_reverse_now_overfire": check_4_reverse_now_overfire(trade_df).to_dict(),
        "5_setup_policy_consistency": check_5_setup_policy_consistency(trade_df).to_dict(),
        "6_metadata_preservation": check_6_metadata_preservation(trade_df).to_dict(),
        "7_no_regression": check_7_no_regression(entry_df).to_dict(),
    }

    statuses = [item["status"] for item in checks.values()]
    overall = "pass"
    if any(s == "fail" for s in statuses):
        overall = "fail"
    elif any(s == "inconclusive" for s in statuses):
        overall = "inconclusive"

    report = {
        "generated_at": now_kst_dt().isoformat(),
        "lookback_hours": int(lookback_hours),
        "since": str(since_text),
        "cutoff": str(cutoff),
        "overall_status": overall,
        "sample_sizes": {
            "entry_rows": int(len(entry_df)),
            "open_trade_rows": int(len(open_df)),
            "closed_trade_rows": int(len(closed_df)),
            "trade_rows_total": int(len(trade_df)),
        },
        "checks": checks,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUT_DIR / f"phase8_validation_report_{ts}.json"
    md_path = OUT_DIR / f"phase8_validation_report_{ts}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    print(str(json_path))
    print(str(md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
