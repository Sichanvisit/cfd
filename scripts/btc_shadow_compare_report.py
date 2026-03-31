"""Compare BTC actual entry decisions against PRS shadow observe/confirm output."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.trade_csv_schema import now_kst_dt


ENTRY_DECISIONS = ROOT / "data" / "trades" / "entry_decisions.csv"
OUT_DIR = ROOT / "data" / "analysis"


def _read_entry_decisions(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig", engine="python", on_bad_lines="skip")
    except Exception:
        try:
            return pd.read_csv(path, encoding="utf-8", engine="python", on_bad_lines="skip")
        except Exception:
            return pd.DataFrame()


def _parse_json_cell(value) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _value_counts(df: pd.DataFrame, col: str, top: int = 10) -> dict[str, int]:
    if df.empty or col not in df.columns:
        return {}
    series = df[col].fillna("").astype(str).str.strip()
    series = series[series != ""]
    if series.empty:
        return {}
    counts = series.value_counts().head(top)
    return {str(k): int(v) for k, v in counts.items()}


def build_report(df: pd.DataFrame, *, symbol: str = "BTCUSD", since: str | None = None) -> dict:
    symbol_u = str(symbol or "BTCUSD").upper().strip()
    work = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    if work.empty:
        return {
            "generated_at": now_kst_dt().isoformat(),
            "symbol": symbol_u,
            "since": str(since or ""),
            "summary": {"rows_total": 0},
            "actual": {},
            "shadow": {},
            "compare": {},
            "recent_mismatches": [],
        }
    if "symbol" in work.columns:
        work = work[work["symbol"].astype(str).str.upper() == symbol_u].copy()
    if "time" in work.columns:
        work["time_dt"] = pd.to_datetime(work["time"], errors="coerce")
        if since:
            since_dt = pd.to_datetime(since, errors="coerce")
            if pd.notna(since_dt):
                work = work[work["time_dt"] >= since_dt].copy()
    if work.empty:
        return {
            "generated_at": now_kst_dt().isoformat(),
            "symbol": symbol_u,
            "since": str(since or ""),
            "summary": {"rows_total": 0},
            "actual": {},
            "shadow": {},
            "compare": {},
            "recent_mismatches": [],
        }

    if "shadow_state_v1" not in work.columns:
        work["shadow_state_v1"] = ""
    if "shadow_action_v1" not in work.columns:
        work["shadow_action_v1"] = ""
    if "shadow_reason_v1" not in work.columns:
        work["shadow_reason_v1"] = ""

    if "observe_confirm_v1" in work.columns:
        parsed_shadow = work["observe_confirm_v1"].fillna("").apply(_parse_json_cell)
    else:
        parsed_shadow = pd.Series([{} for _ in range(len(work))], index=work.index, dtype=object)

    def _fill_from_json(existing, parsed, key):
        out = []
        for cur, blob in zip(existing.tolist(), parsed.tolist(), strict=False):
            cur_text = str(cur or "").strip()
            if cur_text:
                out.append(cur_text)
            else:
                out.append(str(blob.get(key, "") or ""))
        return out

    work["shadow_state_v1"] = _fill_from_json(work["shadow_state_v1"], parsed_shadow, "state")
    work["shadow_action_v1"] = _fill_from_json(work["shadow_action_v1"], parsed_shadow, "action")
    work["shadow_reason_v1"] = _fill_from_json(work["shadow_reason_v1"], parsed_shadow, "reason")

    def _force_from_columns(col_name: str) -> pd.Series:
        if col_name in work.columns:
            return pd.to_numeric(work[col_name], errors="coerce").fillna(0.0)
        return pd.Series([0.0 for _ in range(len(work))], index=work.index, dtype=float)

    work["shadow_buy_force_v1"] = _force_from_columns("shadow_buy_force_v1")
    work["shadow_sell_force_v1"] = _force_from_columns("shadow_sell_force_v1")
    work["shadow_net_force_v1"] = _force_from_columns("shadow_net_force_v1")

    entered_df = work[work.get("outcome", pd.Series(dtype=str)).astype(str).str.lower() == "entered"].copy()
    shadow_confirm_df = work[work["shadow_action_v1"].astype(str).str.upper().isin({"BUY", "SELL"})].copy()
    shadow_wait_df = work[work["shadow_action_v1"].astype(str).str.upper().isin({"WAIT", "OBSERVE", ""})].copy()

    actual_action = work.get("action", pd.Series(dtype=str)).astype(str).str.upper().str.strip()
    shadow_action = work["shadow_action_v1"].astype(str).str.upper().str.strip()

    entered_with_shadow_agree = int(
        (
            (work.get("outcome", pd.Series(dtype=str)).astype(str).str.lower() == "entered")
            & actual_action.isin({"BUY", "SELL"})
            & (actual_action == shadow_action)
        ).sum()
    )
    entered_with_shadow_disagree = int(
        (
            (work.get("outcome", pd.Series(dtype=str)).astype(str).str.lower() == "entered")
            & actual_action.isin({"BUY", "SELL"})
            & shadow_action.isin({"BUY", "SELL"})
            & (actual_action != shadow_action)
        ).sum()
    )
    skipped_but_shadow_confirm = int(
        (
            (work.get("outcome", pd.Series(dtype=str)).astype(str).str.lower() != "entered")
            & shadow_action.isin({"BUY", "SELL"})
        ).sum()
    )
    entered_but_shadow_wait = int(
        (
            (work.get("outcome", pd.Series(dtype=str)).astype(str).str.lower() == "entered")
            & ~shadow_action.isin({"BUY", "SELL"})
        ).sum()
    )

    mismatch_df = work[
        (
            ((work.get("outcome", pd.Series(dtype=str)).astype(str).str.lower() == "entered") & (actual_action != shadow_action) & shadow_action.isin({"BUY", "SELL"}))
            | ((work.get("outcome", pd.Series(dtype=str)).astype(str).str.lower() != "entered") & shadow_action.isin({"BUY", "SELL"}))
        )
    ].copy()

    recent_cols = [
        "time",
        "action",
        "outcome",
        "blocked_by",
        "core_reason",
        "setup_id",
        "setup_reason",
        "box_state",
        "bb_state",
        "shadow_state_v1",
        "shadow_action_v1",
        "shadow_reason_v1",
        "shadow_buy_force_v1",
        "shadow_sell_force_v1",
        "shadow_net_force_v1",
    ]
    recent_cols = [c for c in recent_cols if c in mismatch_df.columns]

    report = {
        "generated_at": now_kst_dt().isoformat(),
        "symbol": symbol_u,
        "since": str(since or ""),
        "summary": {
            "rows_total": int(len(work)),
            "entered_rows": int(len(entered_df)),
            "shadow_confirm_rows": int(len(shadow_confirm_df)),
            "shadow_wait_rows": int(len(shadow_wait_df)),
        },
        "actual": {
            "outcome_counts": _value_counts(work, "outcome"),
            "blocked_by_counts": _value_counts(work, "blocked_by"),
            "setup_counts": _value_counts(work, "setup_id"),
            "actual_action_counts": _value_counts(work.assign(action=actual_action), "action"),
        },
        "shadow": {
            "shadow_state_counts": _value_counts(work, "shadow_state_v1"),
            "shadow_action_counts": _value_counts(work, "shadow_action_v1"),
            "shadow_reason_counts": _value_counts(work, "shadow_reason_v1"),
        },
        "compare": {
            "entered_with_shadow_agree": entered_with_shadow_agree,
            "entered_with_shadow_disagree": entered_with_shadow_disagree,
            "skipped_but_shadow_confirm": skipped_but_shadow_confirm,
            "entered_but_shadow_wait": entered_but_shadow_wait,
        },
        "recent_mismatches": mismatch_df.sort_values("time", ascending=False).head(20)[recent_cols].to_dict(orient="records")
        if recent_cols
        else [],
    }
    return report


def _write_markdown(report: dict, path: Path) -> None:
    lines = [
        f"# BTC Shadow Compare",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- symbol: `{report.get('symbol', '')}`",
        f"- since: `{report.get('since', '')}`",
        "",
        "## Summary",
        f"- rows_total: `{report.get('summary', {}).get('rows_total', 0)}`",
        f"- entered_rows: `{report.get('summary', {}).get('entered_rows', 0)}`",
        f"- shadow_confirm_rows: `{report.get('summary', {}).get('shadow_confirm_rows', 0)}`",
        f"- shadow_wait_rows: `{report.get('summary', {}).get('shadow_wait_rows', 0)}`",
        "",
        "## Compare",
        f"- entered_with_shadow_agree: `{report.get('compare', {}).get('entered_with_shadow_agree', 0)}`",
        f"- entered_with_shadow_disagree: `{report.get('compare', {}).get('entered_with_shadow_disagree', 0)}`",
        f"- skipped_but_shadow_confirm: `{report.get('compare', {}).get('skipped_but_shadow_confirm', 0)}`",
        f"- entered_but_shadow_wait: `{report.get('compare', {}).get('entered_but_shadow_wait', 0)}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSD")
    parser.add_argument("--since", default="")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = _read_entry_decisions(ENTRY_DECISIONS)
    report = build_report(df, symbol=args.symbol, since=(args.since or None))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = OUT_DIR / f"btc_shadow_compare_report_{ts}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    print(str(json_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
