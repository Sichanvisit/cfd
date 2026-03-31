from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
REPORT_VERSION = "profitability_operations_p4_time_series_comparison_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_DECISIONS_PATH = ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_DECISION_DETAIL_PATH = ROOT / "data" / "trades" / "entry_decisions.detail.jsonl"
DEFAULT_OPEN_TRADES_PATH = ROOT / "data" / "trades" / "trade_history.csv"
DEFAULT_CLOSED_TRADES_PATH = ROOT / "data" / "trades" / "trade_closed_history.csv"


def _load_script_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P1_MODULE = _load_script_module(
    "profitability_operations_p1_lifecycle_correlation_report_for_p4",
    SCRIPTS_DIR / "profitability_operations_p1_lifecycle_correlation_report.py",
)
P2_MODULE = _load_script_module(
    "profitability_operations_p2_expectancy_attribution_report_for_p4",
    SCRIPTS_DIR / "profitability_operations_p2_expectancy_attribution_report.py",
)
P2_ZERO_MODULE = _load_script_module(
    "profitability_operations_p2_zero_pnl_gap_audit_for_p4",
    SCRIPTS_DIR / "profitability_operations_p2_zero_pnl_gap_audit.py",
)
P3_MODULE = _load_script_module(
    "profitability_operations_p3_anomaly_alerting_report_for_p4",
    SCRIPTS_DIR / "profitability_operations_p3_anomaly_alerting_report.py",
)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except Exception:
            continue
    return []


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_float(value: Any) -> float:
    text = _coerce_text(value)
    if not text:
        return 0.0
    try:
        return float(text)
    except Exception:
        return 0.0


def _coerce_int(value: Any) -> int:
    text = _coerce_text(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except Exception:
        return 0


def _severity_rank(severity: str) -> int:
    mapping = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    return mapping.get(_coerce_text(severity).lower(), 0)


def _split_recent_previous(rows: list[dict[str, Any]], window_size: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if window_size <= 0:
        return [], rows
    current = rows[-window_size:] if len(rows) >= window_size else rows[:]
    previous_end = max(0, len(rows) - window_size)
    previous_start = max(0, previous_end - window_size)
    previous = rows[previous_start:previous_end]
    return previous, current


def _summary_rows_to_map(rows: list[dict[str, Any]], key_field: str, value_field: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in rows:
        key = _coerce_text(row.get(key_field))
        if key:
            out[key] = _coerce_float(row.get(value_field))
    return out


def _build_delta_rows(current_map: dict[str, float], previous_map: dict[str, float], *, key_name: str) -> list[dict[str, Any]]:
    keys = sorted(set(current_map) | set(previous_map))
    rows: list[dict[str, Any]] = []
    for key in keys:
        current = current_map.get(key, 0.0)
        previous = previous_map.get(key, 0.0)
        rows.append(
            {
                key_name: key,
                "current_count": round(current, 4),
                "previous_count": round(previous, 4),
                "delta": round(current - previous, 4),
            }
        )
    return sorted(rows, key=lambda row: (-float(row["delta"]), row[key_name]))


def _build_symbol_alert_delta_rows(current_rows: list[dict[str, Any]], previous_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current_map = { _coerce_text(row.get("symbol")): row for row in current_rows }
    previous_map = { _coerce_text(row.get("symbol")): row for row in previous_rows }
    rows: list[dict[str, Any]] = []
    for symbol in sorted(set(current_map) | set(previous_map)):
        current = current_map.get(symbol, {})
        previous = previous_map.get(symbol, {})
        rows.append(
            {
                "symbol": symbol,
                "current_active_alert_count": _coerce_int(current.get("active_alert_count")),
                "previous_active_alert_count": _coerce_int(previous.get("active_alert_count")),
                "active_alert_delta": _coerce_int(current.get("active_alert_count")) - _coerce_int(previous.get("active_alert_count")),
                "current_critical_count": _coerce_int(current.get("critical_count")),
                "previous_critical_count": _coerce_int(previous.get("critical_count")),
                "critical_delta": _coerce_int(current.get("critical_count")) - _coerce_int(previous.get("critical_count")),
                "current_high_count": _coerce_int(current.get("high_count")),
                "previous_high_count": _coerce_int(previous.get("high_count")),
                "high_delta": _coerce_int(current.get("high_count")) - _coerce_int(previous.get("high_count")),
                "current_top_alert_type": _coerce_text(current.get("top_alert_type")),
                "previous_top_alert_type": _coerce_text(previous.get("top_alert_type")),
            }
        )
    return sorted(
        rows,
        key=lambda row: (-int(row["critical_delta"]), -int(row["high_delta"]), -int(row["active_alert_delta"]), row["symbol"]),
    )


def _build_signal_queue(delta_rows: list[dict[str, Any]], *, key_name: str, positive_only: bool) -> list[str]:
    queue: list[str] = []
    for row in delta_rows:
        delta = _coerce_float(row.get("delta") or row.get("active_alert_delta"))
        if positive_only and delta <= 0:
            continue
        if not positive_only and delta >= 0:
            continue
        key = _coerce_text(row.get(key_name))
        if not key:
            continue
        queue.append(f"{key} | delta={delta}")
        if len(queue) >= 5:
            break
    return queue


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_window_payloads(
    *,
    decisions_rows: list[dict[str, Any]],
    open_trade_rows: list[dict[str, Any]],
    closed_trade_rows: list[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        decisions_path = tmp / "entry_decisions.csv"
        decision_detail_path = tmp / "entry_decisions.detail.jsonl"
        open_trades_path = tmp / "trade_history.csv"
        closed_trades_path = tmp / "trade_closed_history.csv"
        p1_path = tmp / "p1.json"
        p2_path = tmp / "p2.json"
        p2_zero_path = tmp / "p2_zero.json"

        _write_csv(decisions_path, decisions_rows)
        decision_detail_path.write_text("", encoding="utf-8")
        _write_csv(open_trades_path, open_trade_rows)
        _write_csv(closed_trades_path, closed_trade_rows)

        p1_payload = P1_MODULE.build_profitability_operations_p1_lifecycle_correlation_report(
            decisions_path=decisions_path,
            decision_detail_path=decision_detail_path,
            open_trades_path=open_trades_path,
            closed_trades_path=closed_trades_path,
            tail=max(len(decisions_rows), len(closed_trade_rows), 1),
            now=now,
        )
        p2_payload = P2_MODULE.build_profitability_operations_p2_expectancy_attribution_report(
            closed_trades_path=closed_trades_path,
            tail=max(len(closed_trade_rows), 1),
            now=now,
        )
        p2_zero_payload = P2_ZERO_MODULE.build_profitability_operations_p2_zero_pnl_gap_audit(
            closed_trades_path=closed_trades_path,
            tail=max(len(closed_trade_rows), 1),
            now=now,
        )

        _write_json(p1_path, p1_payload)
        _write_json(p2_path, p2_payload)
        _write_json(p2_zero_path, p2_zero_payload)

        p3_payload = P3_MODULE.build_profitability_operations_p3_anomaly_alerting_report(
            p1_lifecycle_path=p1_path,
            p2_expectancy_path=p2_path,
            p2_zero_pnl_audit_path=p2_zero_path,
            now=now,
        )

    return {
        "p1": p1_payload,
        "p2": p2_payload,
        "p2_zero": p2_zero_payload,
        "p3": p3_payload,
    }


def build_profitability_operations_p4_time_series_comparison_report(
    *,
    decisions_path: Path = DEFAULT_DECISIONS_PATH,
    decision_detail_path: Path = DEFAULT_DECISION_DETAIL_PATH,
    open_trades_path: Path = DEFAULT_OPEN_TRADES_PATH,
    closed_trades_path: Path = DEFAULT_CLOSED_TRADES_PATH,
    window_size: int = 250,
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()

    all_decisions = _read_csv(decisions_path)
    all_open_trades = _read_csv(open_trades_path)
    all_closed_trades = _read_csv(closed_trades_path)

    previous_decisions, current_decisions = _split_recent_previous(all_decisions, window_size)
    previous_open_trades, current_open_trades = _split_recent_previous(all_open_trades, window_size)
    previous_closed_trades, current_closed_trades = _split_recent_previous(all_closed_trades, window_size)

    previous_payloads = _build_window_payloads(
        decisions_rows=previous_decisions,
        open_trade_rows=previous_open_trades,
        closed_trade_rows=previous_closed_trades,
        now=report_now,
    )
    current_payloads = _build_window_payloads(
        decisions_rows=current_decisions,
        open_trade_rows=current_open_trades,
        closed_trade_rows=current_closed_trades,
        now=report_now,
    )

    p1_delta_rows = _build_delta_rows(
        _summary_rows_to_map(current_payloads["p1"].get("suspicious_cluster_type_summary", []), "cluster_type", "count"),
        _summary_rows_to_map(previous_payloads["p1"].get("suspicious_cluster_type_summary", []), "cluster_type", "count"),
        key_name="cluster_type",
    )
    p2_delta_rows = _build_delta_rows(
        _summary_rows_to_map(current_payloads["p2"].get("negative_expectancy_cluster_type_summary", []), "cluster_type", "count"),
        _summary_rows_to_map(previous_payloads["p2"].get("negative_expectancy_cluster_type_summary", []), "cluster_type", "count"),
        key_name="cluster_type",
    )
    p3_delta_rows = _build_delta_rows(
        _summary_rows_to_map(current_payloads["p3"].get("alert_type_summary", []), "alert_type", "count"),
        _summary_rows_to_map(previous_payloads["p3"].get("alert_type_summary", []), "alert_type", "count"),
        key_name="alert_type",
    )
    symbol_delta_rows = _build_symbol_alert_delta_rows(
        current_payloads["p3"].get("symbol_alert_summary", []),
        previous_payloads["p3"].get("symbol_alert_summary", []),
    )

    current_alert_summary = current_payloads["p3"].get("overall_alert_summary", {})
    previous_alert_summary = previous_payloads["p3"].get("overall_alert_summary", {})
    current_expectancy = current_payloads["p2"].get("overall_expectancy_summary", {})
    previous_expectancy = previous_payloads["p2"].get("overall_expectancy_summary", {})
    current_zero = current_payloads["p2_zero"].get("audit_summary", {})
    previous_zero = previous_payloads["p2_zero"].get("audit_summary", {})

    worsening_signals = (
        [f"symbol::{item}" for item in _build_signal_queue(symbol_delta_rows, key_name="symbol", positive_only=True)]
        + [f"alert::{item}" for item in _build_signal_queue(p3_delta_rows, key_name="alert_type", positive_only=True)]
    )[:10]
    improving_signals = (
        [f"symbol::{item}" for item in _build_signal_queue(symbol_delta_rows, key_name="symbol", positive_only=False)]
        + [f"alert::{item}" for item in _build_signal_queue(p3_delta_rows, key_name="alert_type", positive_only=False)]
    )[:10]

    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "compare_scope": {
            "window_kind": "row_window_recent_vs_previous",
            "window_size": window_size,
            "decisions_path": str(decisions_path),
            "decision_detail_path": str(decision_detail_path),
            "open_trades_path": str(open_trades_path),
            "closed_trades_path": str(closed_trades_path),
        },
        "window_source_summary": {
            "previous_decision_rows": len(previous_decisions),
            "current_decision_rows": len(current_decisions),
            "previous_open_trade_rows": len(previous_open_trades),
            "current_open_trade_rows": len(current_open_trades),
            "previous_closed_trade_rows": len(previous_closed_trades),
            "current_closed_trade_rows": len(current_closed_trades),
        },
        "overall_delta_summary": {
            "current_active_alert_count": _coerce_int(current_alert_summary.get("active_alert_count")),
            "previous_active_alert_count": _coerce_int(previous_alert_summary.get("active_alert_count")),
            "active_alert_delta": _coerce_int(current_alert_summary.get("active_alert_count")) - _coerce_int(previous_alert_summary.get("active_alert_count")),
            "current_critical_count": _coerce_int(current_alert_summary.get("critical_count")),
            "previous_critical_count": _coerce_int(previous_alert_summary.get("critical_count")),
            "critical_delta": _coerce_int(current_alert_summary.get("critical_count")) - _coerce_int(previous_alert_summary.get("critical_count")),
            "current_high_count": _coerce_int(current_alert_summary.get("high_count")),
            "previous_high_count": _coerce_int(previous_alert_summary.get("high_count")),
            "high_delta": _coerce_int(current_alert_summary.get("high_count")) - _coerce_int(previous_alert_summary.get("high_count")),
            "current_avg_pnl": _coerce_float(current_expectancy.get("avg_pnl")),
            "previous_avg_pnl": _coerce_float(previous_expectancy.get("avg_pnl")),
            "avg_pnl_delta": round(_coerce_float(current_expectancy.get("avg_pnl")) - _coerce_float(previous_expectancy.get("avg_pnl")), 4),
            "current_zero_pnl_row_count": _coerce_int(current_zero.get("zero_pnl_row_count")),
            "previous_zero_pnl_row_count": _coerce_int(previous_zero.get("zero_pnl_row_count")),
            "zero_pnl_row_delta": _coerce_int(current_zero.get("zero_pnl_row_count")) - _coerce_int(previous_zero.get("zero_pnl_row_count")),
        },
        "p1_cluster_type_deltas": p1_delta_rows,
        "p2_cluster_type_deltas": p2_delta_rows,
        "p3_alert_type_deltas": p3_delta_rows,
        "symbol_alert_deltas": symbol_delta_rows,
        "worsening_signal_summary": worsening_signals,
        "improving_signal_summary": improving_signals,
        "quick_read_summary": {
            "top_worsening_signals": worsening_signals[:5],
            "top_improving_signals": improving_signals[:5],
            "current_review_queue": current_payloads["p3"].get("operator_review_queue", [])[:5],
        },
    }


def write_profitability_operations_p4_time_series_comparison_report(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    decisions_path: Path = DEFAULT_DECISIONS_PATH,
    decision_detail_path: Path = DEFAULT_DECISION_DETAIL_PATH,
    open_trades_path: Path = DEFAULT_OPEN_TRADES_PATH,
    closed_trades_path: Path = DEFAULT_CLOSED_TRADES_PATH,
    window_size: int = 250,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_profitability_operations_p4_time_series_comparison_report(
        decisions_path=decisions_path,
        decision_detail_path=decision_detail_path,
        open_trades_path=open_trades_path,
        closed_trades_path=closed_trades_path,
        window_size=window_size,
        now=now,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p4_compare_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p4_compare_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p4_compare_latest.md"

    latest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_rows = report["symbol_alert_deltas"]
    fieldnames = list(csv_rows[0].keys()) if csv_rows else [
        "symbol", "current_active_alert_count", "previous_active_alert_count", "active_alert_delta",
        "current_critical_count", "previous_critical_count", "critical_delta",
        "current_high_count", "previous_high_count", "high_delta",
        "current_top_alert_type", "previous_top_alert_type",
    ]
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    overall = report["overall_delta_summary"]
    markdown_lines = [
        "# Profitability / Operations P4 Time-Series Comparison",
        "",
        f"- `report_version`: `{report['report_version']}`",
        f"- `generated_at`: `{report['generated_at']}`",
        f"- `window_size`: `{report['compare_scope']['window_size']}`",
        f"- `active_alert_delta`: `{overall['active_alert_delta']}`",
        f"- `critical_delta`: `{overall['critical_delta']}`",
        f"- `high_delta`: `{overall['high_delta']}`",
        f"- `avg_pnl_delta`: `{overall['avg_pnl_delta']}`",
        f"- `zero_pnl_row_delta`: `{overall['zero_pnl_row_delta']}`",
        "",
        "## Top Worsening Signals",
    ]
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_worsening_signals"] or ["(none)"])])
    markdown_lines.extend(["", "## Top Improving Signals"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_improving_signals"] or ["(none)"])])
    markdown_lines.extend(["", "## Current Review Queue"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["current_review_queue"] or ["(none)"])])
    latest_markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "active_alert_delta": overall["active_alert_delta"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-size", type=int, default=250)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = write_profitability_operations_p4_time_series_comparison_report(
        output_dir=args.output_dir,
        window_size=args.window_size,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
