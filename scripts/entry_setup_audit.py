"""
Audit post-D5 setup coverage and edge-direction entry quality from entry decision logs.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import Config
from backend.services.entry_engines import ENTRY_DECISION_LOG_COLUMNS


def _resolve_log_path() -> Path:
    path = Path(getattr(Config, "ENTRY_DECISION_LOG_PATH", r"data\trades\entry_decisions.csv"))
    if not path.is_absolute():
        path = ROOT / path
    return path


def _safe_ratio(num: int, den: int) -> float:
    return 0.0 if int(den) <= 0 else float(num) / float(den)


def _counts(series: pd.Series) -> dict[str, int]:
    if series is None or series.empty:
        return {}
    out = series.fillna("").astype(str).value_counts().to_dict()
    return {str(k): int(v) for k, v in out.items() if str(k)}


def main() -> int:
    path = _resolve_log_path()
    if not path.exists():
        print(json.dumps({"error": "entry_decision_log_missing", "path": str(path)}, ensure_ascii=False))
        return 1

    df = pd.read_csv(path, encoding="utf-8-sig", on_bad_lines="skip")
    for col in ENTRY_DECISION_LOG_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    for col in ("action", "outcome", "box_state", "setup_id", "setup_status", "setup_reason", "symbol"):
        df[col] = df[col].fillna("").astype(str)

    entered = df[df["outcome"].str.lower() == "entered"].copy()
    setup_present = df["setup_id"].str.strip() != ""
    entered_setup_present = entered["setup_id"].str.strip() != ""
    upper_buy_entered = entered[
        (entered["action"].str.upper() == "BUY") & (entered["box_state"].str.upper().isin(["UPPER", "ABOVE"]))
    ].copy()
    lower_sell_entered = entered[
        (entered["action"].str.upper() == "SELL") & (entered["box_state"].str.upper().isin(["LOWER", "BELOW"]))
    ].copy()

    summary = {
        "rows_total": int(len(df)),
        "entered_total": int(len(entered)),
        "setup_present_total": int(setup_present.sum()),
        "setup_coverage_ratio": round(_safe_ratio(int(setup_present.sum()), int(len(df))), 6),
        "entered_with_setup": int(entered_setup_present.sum()),
        "entered_with_setup_ratio": round(_safe_ratio(int(entered_setup_present.sum()), int(len(entered))), 6),
        "entered_without_setup": int((~entered_setup_present).sum()),
        "entered_without_setup_ratio": round(_safe_ratio(int((~entered_setup_present).sum()), int(len(entered))), 6),
        "upper_buy_entered": int(len(upper_buy_entered)),
        "upper_buy_entered_ratio": round(_safe_ratio(int(len(upper_buy_entered)), int(len(entered))), 6),
        "lower_sell_entered": int(len(lower_sell_entered)),
        "lower_sell_entered_ratio": round(_safe_ratio(int(len(lower_sell_entered)), int(len(entered))), 6),
    }
    detail = {
        "entered_by_symbol": _counts(entered["symbol"]),
        "entered_setup_counts": _counts(entered["setup_id"]),
        "entered_setup_status_counts": _counts(entered["setup_status"]),
        "upper_buy_setup_counts": _counts(upper_buy_entered["setup_id"]),
        "lower_sell_setup_counts": _counts(lower_sell_entered["setup_id"]),
        "rejected_setup_reason_counts": _counts(df.loc[df["setup_status"].str.lower() == "rejected", "setup_reason"]),
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = {
        "timestamp": ts,
        "path": str(path),
        "summary": summary,
        "detail": detail,
    }
    analysis_dir = ROOT / "data" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    out_path = analysis_dir / f"entry_setup_audit_{ts}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
