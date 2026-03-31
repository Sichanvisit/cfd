"""Bucket validation report for forecast calibration.

This is a calibration/scaffolding report, not a final outcome-label evaluator.
Until OutcomeLabeler exists, transition metrics use decision-time proxy labels and
management metrics use resolved trade proxies when available.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRY_DECISIONS = PROJECT_ROOT / "data" / "trades" / "entry_decisions.csv"
TRADE_CLOSED_HISTORY = PROJECT_ROOT / "trade_closed_history.csv"
OUT_DIR = PROJECT_ROOT / "data" / "analysis"

BUCKETS: list[tuple[float, float | None, str]] = [
    (0.00, 0.05, "0.00~0.05"),
    (0.05, 0.10, "0.05~0.10"),
    (0.10, 0.20, "0.10~0.20"),
    (0.20, 0.35, "0.20~0.35"),
    (0.35, None, "0.35+"),
]

TRANSITION_METRICS = {
    "p_buy_confirm": {
        "label": "buy_confirm_proxy",
        "gaps": ["transition_side_separation", "transition_confirm_fake_gap"],
        "positive_definition": "observe_confirm/action resolved to BUY at decision time",
        "label_kind": "decision_proxy",
    },
    "p_sell_confirm": {
        "label": "sell_confirm_proxy",
        "gaps": ["transition_side_separation", "transition_confirm_fake_gap"],
        "positive_definition": "observe_confirm/action resolved to SELL at decision time",
        "label_kind": "decision_proxy",
    },
    "p_false_break": {
        "label": "false_break_proxy",
        "gaps": ["transition_confirm_fake_gap", "transition_reversal_continuation_gap"],
        "positive_definition": "observe_confirm remained WAIT/OBSERVE at decision time",
        "label_kind": "decision_proxy",
    },
}

MANAGEMENT_METRICS = {
    "p_continue_favor": {
        "label": "continue_favor_proxy",
        "gaps": ["management_continue_fail_gap", "management_recover_reentry_gap"],
        "positive_definition": "matched resolved trade finished profitable (profit > 0)",
        "label_kind": "resolved_trade_proxy",
    },
    "p_fail_now": {
        "label": "fail_now_proxy",
        "gaps": ["management_continue_fail_gap", "management_recover_reentry_gap"],
        "positive_definition": "matched resolved trade finished losing (profit < 0)",
        "label_kind": "resolved_trade_proxy",
    },
}


@dataclass(frozen=True)
class MetricSpec:
    score_col: str
    label_col: str
    gap_cols: list[str]
    positive_definition: str
    label_kind: str


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float):
        if pd.isna(value):
            return None
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _parse_json_dict(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def bucket_label(score: float | None) -> str | None:
    if score is None:
        return None
    for lo, hi, label in BUCKETS:
        if hi is None:
            if score >= lo:
                return label
            continue
        if lo <= score < hi:
            return label
    if score < 0.0:
        return BUCKETS[0][2]
    return BUCKETS[-1][2]


def _monotonic_non_decreasing(values: list[float]) -> bool | None:
    if len(values) < 2:
        return None
    return all(curr >= prev for prev, curr in zip(values, values[1:]))


def _load_entry_decisions(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", engine="python", on_bad_lines="skip")


def _load_closed_history(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", engine="python", on_bad_lines="skip")


def _coerce_forecast_scores(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    transition = df.get("transition_forecast_v1", pd.Series(dtype=str)).apply(_parse_json_dict)
    management = df.get("trade_management_forecast_v1", pd.Series(dtype=str)).apply(_parse_json_dict)
    observe = df.get("observe_confirm_v1", pd.Series(dtype=str)).apply(_parse_json_dict)

    for col in ("p_buy_confirm", "p_sell_confirm", "p_false_break", "p_reversal_success", "p_continuation_success"):
        df[col] = transition.apply(lambda payload, key=col: _safe_float(payload.get(key)))
    for col in (
        "p_continue_favor",
        "p_fail_now",
        "p_recover_after_pullback",
        "p_reach_tp1",
        "p_opposite_edge_reach",
        "p_better_reentry_if_cut",
    ):
        df[col] = management.apply(lambda payload, key=col: _safe_float(payload.get(key)))

    gap_columns = [
        "transition_side_separation",
        "transition_confirm_fake_gap",
        "transition_reversal_continuation_gap",
        "management_continue_fail_gap",
        "management_recover_reentry_gap",
    ]
    for col in gap_columns:
        df[col] = df.get(col, pd.Series(dtype=float)).apply(_safe_float)

    df["obs_action"] = observe.apply(lambda payload: str(payload.get("action", "")).upper().strip())
    df["obs_state"] = observe.apply(lambda payload: str(payload.get("state", "")).upper().strip())
    df["action_upper"] = df.get("action", pd.Series(dtype=str)).fillna("").astype(str).str.upper().str.strip()
    df["outcome_upper"] = df.get("outcome", pd.Series(dtype=str)).fillna("").astype(str).str.upper().str.strip()
    df["time_dt"] = pd.to_datetime(df.get("time"), errors="coerce")
    return df


def _derive_transition_proxy_labels(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df["buy_confirm_proxy"] = ((df["obs_action"] == "BUY") | (df["action_upper"] == "BUY")).astype(int)
    df["sell_confirm_proxy"] = ((df["obs_action"] == "SELL") | (df["action_upper"] == "SELL")).astype(int)
    df["false_break_proxy"] = (
        (df["obs_action"] == "WAIT")
        | df["obs_state"].str.endswith("OBSERVE")
        | ((df["action_upper"] == "") & df["outcome_upper"].isin({"WAIT", "SKIPPED"}))
    ).astype(int)
    return df


def _derive_management_proxy_labels(frame: pd.DataFrame, closed_history: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df["continue_favor_proxy"] = pd.NA
    df["fail_now_proxy"] = pd.NA
    if df.empty or closed_history.empty:
        return df

    trades = closed_history.copy()
    trades["symbol_upper"] = trades.get("symbol", "").fillna("").astype(str).str.upper().str.strip()
    trades["direction_upper"] = trades.get("direction", "").fillna("").astype(str).str.upper().str.strip()
    trades["open_time_dt"] = pd.to_datetime(trades.get("open_time"), errors="coerce")
    trades["profit_proxy"] = trades.get("profit", pd.Series(dtype=float)).apply(_safe_float)
    trades = trades.dropna(subset=["open_time_dt"]).copy()

    for idx, row in df[df["outcome_upper"] == "ENTERED"].iterrows():
        if pd.isna(row["time_dt"]):
            continue
        subset = trades[
            (trades["symbol_upper"] == str(row.get("symbol", "")).upper().strip())
            & (trades["direction_upper"] == str(row.get("action_upper", "")).upper().strip())
        ].copy()
        if subset.empty:
            continue
        subset["delta_sec"] = (subset["open_time_dt"] - row["time_dt"]).abs().dt.total_seconds()
        subset = subset.sort_values("delta_sec", ascending=True)
        best = subset.iloc[0]
        if float(best["delta_sec"]) > 300.0:
            continue
        profit = _safe_float(best.get("profit_proxy"))
        if profit is None or abs(profit) <= 1e-12:
            continue
        df.at[idx, "continue_favor_proxy"] = int(profit > 0.0)
        df.at[idx, "fail_now_proxy"] = int(profit < 0.0)
    return df


def _bucket_report(df: pd.DataFrame, spec: MetricSpec) -> dict[str, Any]:
    work = df.copy()
    work = work[work[spec.score_col].notna()].copy()
    work["bucket"] = work[spec.score_col].apply(bucket_label)

    bucket_rows: list[dict[str, Any]] = []
    monotonic_values: list[float] = []

    for _lo, _hi, label in BUCKETS:
        sub = work[work["bucket"] == label].copy()
        row: dict[str, Any] = {
            "bucket": label,
            "rows": int(len(sub)),
            "avg_score": float(sub[spec.score_col].mean()) if not sub.empty else 0.0,
        }
        for gap_col in spec.gap_cols:
            row[f"avg_{gap_col}"] = float(sub[gap_col].mean()) if not sub.empty and gap_col in sub.columns else None

        labeled = sub[sub[spec.label_col].notna()].copy()
        row["labeled_rows"] = int(len(labeled))
        if not labeled.empty:
            positive_rate = float(pd.to_numeric(labeled[spec.label_col], errors="coerce").fillna(0.0).mean())
            row["positive_rate"] = positive_rate
            row["positive_rows"] = int(pd.to_numeric(labeled[spec.label_col], errors="coerce").fillna(0.0).sum())
            monotonic_values.append(positive_rate)
        else:
            row["positive_rate"] = None
            row["positive_rows"] = 0
        bucket_rows.append(row)

    labeled_total = int(work[spec.label_col].notna().sum())
    positive_total = int(pd.to_numeric(work[spec.label_col], errors="coerce").fillna(0.0).sum()) if labeled_total else 0
    return {
        "rows_total": int(len(work)),
        "labeled_rows": labeled_total,
        "positive_rows": positive_total,
        "positive_definition": spec.positive_definition,
        "label_kind": spec.label_kind,
        "monotonic_non_decreasing": _monotonic_non_decreasing(monotonic_values),
        "bucket_rows": bucket_rows,
    }


def build_bucket_validation_report(entry_decisions: pd.DataFrame, closed_history: pd.DataFrame) -> dict[str, Any]:
    df = _coerce_forecast_scores(entry_decisions)
    df = _derive_transition_proxy_labels(df)
    df = _derive_management_proxy_labels(df, closed_history)

    transition_reports = {}
    for metric, config in TRANSITION_METRICS.items():
        transition_reports[metric] = _bucket_report(
            df,
            MetricSpec(
                score_col=metric,
                label_col=config["label"],
                gap_cols=config["gaps"],
                positive_definition=config["positive_definition"],
                label_kind=config["label_kind"],
            ),
        )

    management_reports = {}
    for metric, config in MANAGEMENT_METRICS.items():
        management_reports[metric] = _bucket_report(
            df,
            MetricSpec(
                score_col=metric,
                label_col=config["label"],
                gap_cols=config["gaps"],
                positive_definition=config["positive_definition"],
                label_kind=config["label_kind"],
            ),
        )

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "bucket_spec": [label for *_rest, label in BUCKETS],
        "notes": {
            "transition_labels": "decision_proxy_until_outcome_labeler_v1",
            "management_labels": "resolved_trade_proxy_until_outcome_labeler_v1",
            "management_proxy_requires_matched_closed_trade": True,
        },
        "transition": transition_reports,
        "management": management_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-csv", default=str(ENTRY_DECISIONS))
    parser.add_argument("--closed-history-csv", default=str(TRADE_CLOSED_HISTORY))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    entry_df = _load_entry_decisions(Path(str(args.entry_csv)))
    closed_df = _load_closed_history(Path(str(args.closed_history_csv)))
    report = build_bucket_validation_report(entry_df, closed_df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"forecast_bucket_validation_{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
