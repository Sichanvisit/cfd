from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.trade_csv_schema import normalize_trade_df


CLOSED_TRADES = ROOT / "data" / "trades" / "trade_closed_history.csv"
OUT_DIR = ROOT / "data" / "analysis" / "r0_b_actual_entry_forensic"
REPORT_VERSION = "r0_b1_adverse_entry_samples_v1"


def _load_trade_df(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    last_error: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return pd.DataFrame()


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = _coerce_text(value)
        if not text:
            return float(default)
        return float(text)
    except Exception:
        return float(default)


def _normalize_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_open_dt"] = pd.to_datetime(out.get("open_time"), errors="coerce")
    out["_close_dt"] = pd.to_datetime(out.get("close_time"), errors="coerce")
    out["_row_dt"] = out["_close_dt"].where(out["_close_dt"].notna(), out["_open_dt"])
    return out


def _compute_hold_seconds(df: pd.DataFrame) -> pd.Series:
    dt_hold = (df["_close_dt"] - df["_open_dt"]).dt.total_seconds()
    ts_hold = (pd.to_numeric(df.get("close_ts"), errors="coerce") - pd.to_numeric(df.get("open_ts"), errors="coerce")).abs()
    hold = dt_hold.where(dt_hold.notna() & (dt_hold >= 0), ts_hold)
    return pd.to_numeric(hold, errors="coerce").fillna(0.0)


def _resolve_pnl(df: pd.DataFrame) -> pd.Series:
    net = pd.to_numeric(df.get("net_pnl_after_cost"), errors="coerce").fillna(0.0)
    profit = pd.to_numeric(df.get("profit"), errors="coerce").fillna(0.0)
    return net.where(net != 0.0, profit)


def _has_any_key(row: pd.Series) -> bool:
    return any(
        _coerce_text(row.get(key))
        for key in ("decision_row_key", "runtime_snapshot_key", "trade_link_key", "replay_row_key")
    )


def _is_forensic_ready(row: pd.Series) -> bool:
    return bool(_coerce_text(row.get("decision_row_key")) and _coerce_text(row.get("trade_link_key")))


def _build_adverse_signals(
    *,
    pnl: float,
    hold_seconds: float,
    short_hold_sec: float,
    loss_quality_label: str,
    loss_quality_reason: str,
    decision_winner: str,
    final_outcome: str,
    exit_wait_state: str,
) -> list[str]:
    signals: list[str] = []
    if pnl < 0:
        signals.append("loss_trade")
    if hold_seconds > 0 and hold_seconds <= short_hold_sec:
        signals.append("short_hold")
    if loss_quality_label == "bad_loss":
        signals.append("bad_loss_label")
    elif loss_quality_label == "neutral_loss":
        signals.append("neutral_loss_label")
    if "fast_exit" in loss_quality_reason:
        signals.append("fast_exit_loss_reason")
    if "large_loss" in loss_quality_reason:
        signals.append("large_loss_reason")
    if decision_winner == "cut_now" or final_outcome == "cut_now":
        signals.append("cut_now_winner")
    if decision_winner == "reverse_now" or final_outcome == "reverse_now":
        signals.append("reverse_now_winner")
    if exit_wait_state == "CUT_IMMEDIATE":
        signals.append("cut_immediate_state")
    if exit_wait_state == "REVERSE_READY":
        signals.append("reverse_ready_state")
    return signals


def _priority_score(
    *,
    pnl: float,
    hold_seconds: float,
    short_hold_sec: float,
    loss_quality_label: str,
    loss_quality_reason: str,
    decision_winner: str,
    final_outcome: str,
    exit_wait_state: str,
    forensic_ready: bool,
) -> float:
    score = 0.0
    if pnl < 0:
        score += 1.0 + min(abs(pnl) / 10.0, 2.5)
    if hold_seconds > 0 and hold_seconds <= short_hold_sec:
        score += 2.5
    elif hold_seconds > 0 and hold_seconds <= short_hold_sec * 3:
        score += 1.0
    if loss_quality_label == "bad_loss":
        score += 2.5
    elif loss_quality_label == "neutral_loss":
        score += 0.75
    if "fast_exit" in loss_quality_reason:
        score += 1.75
    if "large_loss" in loss_quality_reason:
        score += 1.5
    if decision_winner == "cut_now" or final_outcome == "cut_now":
        score += 1.25
    if decision_winner == "reverse_now" or final_outcome == "reverse_now":
        score += 1.5
    if exit_wait_state == "CUT_IMMEDIATE":
        score += 1.25
    if exit_wait_state == "REVERSE_READY":
        score += 1.0
    if forensic_ready:
        score += 0.5
    return round(score, 4)


def build_adverse_entry_sample_report(
    *,
    source_path: Path = CLOSED_TRADES,
    window_days: int = 7,
    top_n: int = 30,
    short_hold_sec: float = 180.0,
    exclude_snapshot_restored: bool = True,
    require_forensic_ready: bool = False,
    min_abs_loss: float = 0.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    raw = _load_trade_df(source_path)
    normalized = normalize_trade_df(raw)
    if normalized.empty:
        return {
            "report_version": REPORT_VERSION,
            "generated_at": current_now.isoformat(timespec="seconds"),
            "window_days": int(window_days),
            "window_start": (current_now - timedelta(days=int(window_days))).isoformat(timespec="seconds"),
            "source_path": str(source_path),
            "summary": {
                "source_rows": 0,
                "recent_closed_rows": 0,
                "eligible_loss_rows": 0,
                "adverse_candidate_rows": 0,
                "selected_rows": 0,
                "forensic_ready_rows": 0,
            },
            "top_samples": [],
            "symbol_counts": {},
            "setup_counts": {},
            "adverse_signal_counts": {},
            "loss_quality_counts": {},
        }

    df = _normalize_time_columns(normalized)
    df["status"] = df.get("status", "").fillna("").astype(str).str.upper()
    df = df[df["status"] == "CLOSED"].copy()
    if exclude_snapshot_restored:
        df = df[df.get("entry_setup_id", "").fillna("").astype(str).str.strip() != "snapshot_restored_auto"].copy()

    window_start = current_now - timedelta(days=int(window_days))
    df = df[df["_row_dt"].notna() & (df["_row_dt"] >= window_start)].copy()
    df["resolved_pnl"] = _resolve_pnl(df)
    df["hold_seconds"] = _compute_hold_seconds(df)
    df["has_any_linkage_key"] = df.apply(_has_any_key, axis=1)
    df["forensic_ready"] = df.apply(_is_forensic_ready, axis=1)

    eligible = df[df["resolved_pnl"] < -abs(float(min_abs_loss))].copy()
    signal_rows: list[dict[str, Any]] = []

    for row in eligible.to_dict(orient="records"):
        pnl = _safe_float(row.get("resolved_pnl"))
        hold_seconds = _safe_float(row.get("hold_seconds"))
        loss_quality_label = _coerce_text(row.get("loss_quality_label")).lower()
        loss_quality_reason = _coerce_text(row.get("loss_quality_reason")).lower()
        decision_winner = _coerce_text(row.get("decision_winner")).lower()
        final_outcome = _coerce_text(row.get("final_outcome")).lower()
        exit_wait_state = _coerce_text(row.get("exit_wait_state")).upper()
        forensic_ready = bool(row.get("forensic_ready", False))
        signals = _build_adverse_signals(
            pnl=pnl,
            hold_seconds=hold_seconds,
            short_hold_sec=float(short_hold_sec),
            loss_quality_label=loss_quality_label,
            loss_quality_reason=loss_quality_reason,
            decision_winner=decision_winner,
            final_outcome=final_outcome,
            exit_wait_state=exit_wait_state,
        )
        priority = _priority_score(
            pnl=pnl,
            hold_seconds=hold_seconds,
            short_hold_sec=float(short_hold_sec),
            loss_quality_label=loss_quality_label,
            loss_quality_reason=loss_quality_reason,
            decision_winner=decision_winner,
            final_outcome=final_outcome,
            exit_wait_state=exit_wait_state,
            forensic_ready=forensic_ready,
        )
        row["adverse_signals"] = signals
        row["priority_score"] = priority
        signal_rows.append(row)

    signal_df = pd.DataFrame(signal_rows)
    if signal_df.empty:
        adverse_df = signal_df
    else:
        adverse_df = signal_df[
            signal_df["adverse_signals"].map(
                lambda items: any(
                    signal in set(items)
                    for signal in {
                        "short_hold",
                        "bad_loss_label",
                        "fast_exit_loss_reason",
                        "cut_now_winner",
                        "reverse_now_winner",
                        "cut_immediate_state",
                        "reverse_ready_state",
                    }
                )
            )
        ].copy()
        if require_forensic_ready:
            adverse_df = adverse_df[adverse_df["forensic_ready"] == True].copy()
        adverse_df = adverse_df.sort_values(
            by=["priority_score", "_row_dt", "ticket"],
            ascending=[False, False, False],
        ).head(int(top_n))

    samples: list[dict[str, Any]] = []
    for row in adverse_df.to_dict(orient="records"):
        sample = {
            "ticket": int(_safe_float(row.get("ticket"), 0)),
            "symbol": _coerce_text(row.get("symbol")).upper(),
            "direction": _coerce_text(row.get("direction")).upper(),
            "open_time": _coerce_text(row.get("open_time")),
            "close_time": _coerce_text(row.get("close_time")),
            "hold_seconds": round(_safe_float(row.get("hold_seconds")), 3),
            "resolved_pnl": round(_safe_float(row.get("resolved_pnl")), 4),
            "profit": round(_safe_float(row.get("profit")), 4),
            "net_pnl_after_cost": round(_safe_float(row.get("net_pnl_after_cost")), 4),
            "points": round(_safe_float(row.get("points")), 4),
            "entry_setup_id": _coerce_text(row.get("entry_setup_id")),
            "loss_quality_label": _coerce_text(row.get("loss_quality_label")),
            "loss_quality_reason": _coerce_text(row.get("loss_quality_reason")),
            "decision_winner": _coerce_text(row.get("decision_winner")),
            "decision_reason": _coerce_text(row.get("decision_reason")),
            "final_outcome": _coerce_text(row.get("final_outcome")),
            "entry_wait_state": _coerce_text(row.get("entry_wait_state")),
            "exit_wait_state": _coerce_text(row.get("exit_wait_state")),
            "forensic_ready": bool(row.get("forensic_ready", False)),
            "has_any_linkage_key": bool(row.get("has_any_linkage_key", False)),
            "decision_row_key": _coerce_text(row.get("decision_row_key")),
            "runtime_snapshot_key": _coerce_text(row.get("runtime_snapshot_key")),
            "trade_link_key": _coerce_text(row.get("trade_link_key")),
            "replay_row_key": _coerce_text(row.get("replay_row_key")),
            "adverse_signals": list(row.get("adverse_signals", []) or []),
            "priority_score": round(_safe_float(row.get("priority_score")), 4),
        }
        samples.append(sample)

    symbol_counts = Counter(sample["symbol"] for sample in samples if sample["symbol"])
    setup_counts = Counter(sample["entry_setup_id"] for sample in samples if sample["entry_setup_id"])
    signal_counts = Counter(
        signal
        for sample in samples
        for signal in (sample.get("adverse_signals", []) or [])
    )
    loss_quality_counts = Counter(sample["loss_quality_label"] for sample in samples if sample["loss_quality_label"])

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "window_days": int(window_days),
        "window_start": window_start.isoformat(timespec="seconds"),
        "source_path": str(source_path),
        "filters": {
            "exclude_snapshot_restored": bool(exclude_snapshot_restored),
            "require_forensic_ready": bool(require_forensic_ready),
            "min_abs_loss": float(min_abs_loss),
            "short_hold_sec": float(short_hold_sec),
            "top_n": int(top_n),
        },
        "summary": {
            "source_rows": int(len(raw)),
            "normalized_closed_rows": int(len(normalized[normalized.get("status", "").fillna("").astype(str).str.upper() == "CLOSED"])),
            "recent_closed_rows": int(len(df)),
            "eligible_loss_rows": int(len(eligible)),
            "adverse_candidate_rows": int(len(signal_df[signal_df["priority_score"] > 0])) if not signal_df.empty else 0,
            "selected_rows": int(len(samples)),
            "forensic_ready_rows": int(sum(1 for sample in samples if sample["forensic_ready"])),
        },
        "symbol_counts": dict(symbol_counts.most_common()),
        "setup_counts": dict(setup_counts.most_common()),
        "adverse_signal_counts": dict(signal_counts.most_common()),
        "loss_quality_counts": dict(loss_quality_counts.most_common()),
        "top_samples": samples,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("summary", {}) or {})
    lines = [
        "# R0-B1 Adverse Entry Samples",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- window_days: `{report.get('window_days', 0)}`",
        f"- window_start: `{report.get('window_start', '')}`",
        f"- source_path: `{report.get('source_path', '')}`",
        f"- selected_rows: `{summary.get('selected_rows', 0)}`",
        f"- forensic_ready_rows: `{summary.get('forensic_ready_rows', 0)}`",
        "",
        "## Symbol Counts",
    ]
    symbol_counts = dict(report.get("symbol_counts", {}) or {})
    if symbol_counts:
        for key, value in symbol_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Top Samples"])
    for sample in list(report.get("top_samples", []) or [])[:10]:
        lines.append(
            "- "
            + " | ".join(
                [
                    f"ticket={sample.get('ticket', 0)}",
                    f"symbol={sample.get('symbol', '')}",
                    f"setup={sample.get('entry_setup_id', '')}",
                    f"pnl={sample.get('resolved_pnl', 0.0)}",
                    f"hold={sample.get('hold_seconds', 0.0)}s",
                    f"signals={','.join(sample.get('adverse_signals', []) or [])}",
                    f"forensic_ready={sample.get('forensic_ready', False)}",
                ]
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_adverse_entry_sample_report(
    *,
    source_path: Path = CLOSED_TRADES,
    output_dir: Path = OUT_DIR,
    window_days: int = 7,
    top_n: int = 30,
    short_hold_sec: float = 180.0,
    exclude_snapshot_restored: bool = True,
    require_forensic_ready: bool = False,
    min_abs_loss: float = 0.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_adverse_entry_sample_report(
        source_path=source_path,
        window_days=window_days,
        top_n=top_n,
        short_hold_sec=short_hold_sec,
        exclude_snapshot_restored=exclude_snapshot_restored,
        require_forensic_ready=require_forensic_ready,
        min_abs_loss=min_abs_loss,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "r0_b1_adverse_entry_samples_latest.json"
    latest_csv = output_dir / "r0_b1_adverse_entry_samples_latest.csv"
    latest_md = output_dir / "r0_b1_adverse_entry_samples_latest.md"

    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(report.get("top_samples", []) or []).to_csv(latest_csv, index=False, encoding="utf-8-sig")
    _write_markdown(report, latest_md)

    return {
        "latest_json_path": str(latest_json),
        "latest_csv_path": str(latest_csv),
        "latest_markdown_path": str(latest_md),
        "selected_rows": int(report.get("summary", {}).get("selected_rows", 0) or 0),
        "forensic_ready_rows": int(report.get("summary", {}).get("forensic_ready_rows", 0) or 0),
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--top-n", type=int, default=30)
    parser.add_argument("--short-hold-sec", type=float, default=180.0)
    parser.add_argument("--min-abs-loss", type=float, default=0.0)
    parser.add_argument("--include-snapshot-restored", action="store_true")
    parser.add_argument("--require-forensic-ready", action="store_true")
    parser.add_argument("--source", type=str, default=str(CLOSED_TRADES))
    parser.add_argument("--output-dir", type=str, default=str(OUT_DIR))
    args = parser.parse_args(argv)

    result = write_adverse_entry_sample_report(
        source_path=Path(args.source),
        output_dir=Path(args.output_dir),
        window_days=int(args.window_days),
        top_n=int(args.top_n),
        short_hold_sec=float(args.short_hold_sec),
        exclude_snapshot_restored=not bool(args.include_snapshot_restored),
        require_forensic_ready=bool(args.require_forensic_ready),
        min_abs_loss=float(args.min_abs_loss),
    )
    print(
        json.dumps(
            {
                "ok": True,
                "latest_json_path": result["latest_json_path"],
                "latest_csv_path": result["latest_csv_path"],
                "latest_markdown_path": result["latest_markdown_path"],
                "selected_rows": result["selected_rows"],
                "forensic_ready_rows": result["forensic_ready_rows"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
