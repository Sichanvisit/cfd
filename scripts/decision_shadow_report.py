"""Summarize entry/exit shadow decisions for the latest local logs."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.trade_csv_schema import normalize_trade_df, now_kst_dt, read_csv_resilient


ENTRY_DECISIONS = ROOT / "data" / "trades" / "entry_decisions.csv"
TRADE_HISTORY = ROOT / "data" / "trades" / "trade_history.csv"
OUT_DIR = ROOT / "data" / "analysis"


def _read_entry_decisions() -> pd.DataFrame:
    if not ENTRY_DECISIONS.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(ENTRY_DECISIONS, encoding="utf-8-sig", engine="python", on_bad_lines="skip")
    except Exception:
        return pd.DataFrame()


def _value_counts(df: pd.DataFrame, col: str, top: int = 10) -> dict[str, int]:
    if df.empty or col not in df.columns:
        return {}
    series = df[col].fillna("").astype(str).str.strip()
    series = series[series != ""]
    if series.empty:
        return {}
    counts = series.value_counts().head(top)
    return {str(k): int(v) for k, v in counts.items()}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entry_df = _read_entry_decisions()
    trade_df, _ = read_csv_resilient(TRADE_HISTORY, expected_columns=[])
    trade_df = normalize_trade_df(trade_df)

    report = {
        "generated_at": now_kst_dt().isoformat(),
        "entry_shadow": {
            "rows_total": int(len(entry_df)),
            "outcome_counts": _value_counts(entry_df, "outcome"),
            "blocked_by_counts": _value_counts(entry_df, "blocked_by"),
            "entry_wait_decision_counts": _value_counts(entry_df, "entry_wait_decision"),
        },
        "exit_shadow": {
            "rows_total": int(len(trade_df)),
            "open_rows": int((trade_df.get("status", pd.Series(dtype=str)).astype(str).str.upper() == "OPEN").sum())
            if not trade_df.empty
            else 0,
            "decision_winner_counts": _value_counts(trade_df, "decision_winner"),
            "exit_wait_state_counts": _value_counts(trade_df, "exit_wait_state"),
            "final_outcome_counts": _value_counts(trade_df, "final_outcome"),
        },
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"decision_shadow_report_{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
