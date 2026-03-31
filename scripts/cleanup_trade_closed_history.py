"""
Normalize/clean trade_closed_history.csv in-place with backup.

Usage:
  python scripts/cleanup_trade_closed_history.py --apply
  python scripts/cleanup_trade_closed_history.py --dry-run
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

import pandas as pd


def _read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write cleaned CSV (with backup).")
    parser.add_argument("--dry-run", action="store_true", help="Print summary only.")
    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        args.dry_run = True

    root = _repo_root()
    sys.path.insert(0, str(root))
    from backend.services.trade_csv_schema import normalize_trade_df  # noqa: WPS433

    closed_csv = root / "data" / "trades" / "trade_closed_history.csv"
    if not closed_csv.exists():
        print(f"[ERROR] not found: {closed_csv}")
        return 1

    raw = _read_csv(closed_csv)
    raw_rows = int(len(raw))
    raw_cols = int(len(raw.columns))
    norm = normalize_trade_df(raw)
    norm["status"] = "CLOSED"

    # Deduplicate by the same key pattern used by logger append path.
    merged = norm.copy()
    merged["ticket"] = pd.to_numeric(merged.get("ticket", 0), errors="coerce").fillna(0).astype(int)
    merged["close_ts"] = pd.to_numeric(merged.get("close_ts", 0), errors="coerce").fillna(0).astype(int)
    merged["close_price"] = pd.to_numeric(merged.get("close_price", 0.0), errors="coerce").fillna(0.0)
    merged["lot"] = pd.to_numeric(merged.get("lot", 0.0), errors="coerce").fillna(0.0)
    merged["profit"] = pd.to_numeric(merged.get("profit", 0.0), errors="coerce").fillna(0.0)
    merged["_symbol_upper"] = merged["symbol"].fillna("").astype(str).str.upper().str.strip()
    merged["_dedup_key"] = (
        merged["ticket"].astype(str)
        + "|"
        + merged["_symbol_upper"]
        + "|"
        + merged["close_ts"].astype(str)
        + "|"
        + merged["close_price"].round(6).astype(str)
        + "|"
        + merged["lot"].round(4).astype(str)
        + "|"
        + merged["profit"].round(2).astype(str)
    )
    merged = merged.sort_values(["_dedup_key", "close_ts"], ascending=[True, False]).drop_duplicates(
        subset=["_dedup_key"], keep="first"
    )
    merged = merged.drop(columns=["_symbol_upper", "_dedup_key"], errors="ignore")

    miss_wait = int(sum(1 for c in ("wait_quality_label", "wait_quality_score", "wait_quality_reason") if c not in raw.columns))
    bad_regime_rows = int(
        (
            raw.get("exit_policy_regime", pd.Series(dtype=str))
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .isin({"UNKNOWN", "NORMAL", "RANGE", "LOW_LIQUIDITY", "EXPANSION", "TREND", ""})
            .map(lambda ok: not bool(ok))
        ).sum()
    )
    print(
        "[SUMMARY] "
        f"rows:{raw_rows}->{len(merged)} cols:{raw_cols}->{len(merged.columns)} "
        f"missing_wait_cols={miss_wait} invalid_regime_rows={bad_regime_rows}"
    )

    if args.dry_run and not args.apply:
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = closed_csv.with_name(f"trade_closed_history.backup_cleanup_{stamp}.csv")
    shutil.copy2(closed_csv, backup)
    merged.to_csv(closed_csv, index=False, encoding="utf-8-sig")
    print(f"[OK] backup={backup}")
    print(f"[OK] written={closed_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

