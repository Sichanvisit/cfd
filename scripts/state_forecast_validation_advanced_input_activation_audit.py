from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUT_DIR = ROOT / "data" / "analysis" / "state_forecast_validation"
DEFAULT_TRADES_ROOT = ROOT / "data" / "trades"
DEFAULT_BASELINE_REPORT = OUT_DIR / "state_forecast_validation_sf0_baseline_latest.json"
DEFAULT_SF1_REPORT = OUT_DIR / "state_forecast_validation_sf1_coverage_latest.json"
REPORT_VERSION = "state_forecast_validation_sf2_activation_audit_v1"

INACTIVE_STATES = {"", "UNKNOWN", "INACTIVE", "UNAVAILABLE", "PASSIVE_ONLY"}


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        text = _coerce_text(value)
        if not text:
            return int(default)
        return int(float(text))
    except Exception:
        return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = _coerce_text(value)
        if not text:
            return float(default)
        return float(text)
    except Exception:
        return float(default)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _decode_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _detail_source_paths(trades_root: Path) -> list[Path]:
    patterns = [
        trades_root / "entry_decisions.detail.jsonl",
        *sorted(trades_root.glob("entry_decisions.legacy_*.detail.jsonl")),
        *sorted(trades_root.glob("entry_decisions.detail.rotate_*.jsonl")),
    ]
    output: list[Path] = []
    seen: set[str] = set()
    for path in patterns:
        if not path.exists():
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        output.append(path)
    return output


def _source_kind(path: Path) -> str:
    name = path.name
    if name == "entry_decisions.detail.jsonl":
        return "active_detail"
    if ".legacy_" in name:
        return "legacy_detail"
    if ".rotate_" in name:
        return "rotated_detail"
    return "unknown"


def _sample_rows(paths: list[Path], *, max_files: int, max_rows_per_file: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sampled_rows: list[dict[str, Any]] = []
    sampled_sources: list[dict[str, Any]] = []
    for path in paths[: max(1, int(max_files))]:
        row_count = 0
        first_time = ""
        last_time = ""
        source_kind = _source_kind(path)
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if row_count >= max(1, int(max_rows_per_file)):
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                payload = dict(record.get("payload") or {})
                time_text = _coerce_text(payload.get("time"))
                if not first_time:
                    first_time = time_text
                last_time = time_text or last_time
                state_vector = _decode_json_object(payload.get("state_vector_v2"))
                forecast_features = _decode_json_object(payload.get("forecast_features_v1"))
                state_metadata = dict(state_vector.get("metadata") or {})
                advanced_detail = dict(state_metadata.get("advanced_input_detail_v1") or {})
                semantic_inputs = dict((forecast_features.get("metadata") or {}).get("semantic_forecast_inputs_v2") or {})
                state_harvest = dict(semantic_inputs.get("state_harvest") or {})
                secondary_harvest = dict(semantic_inputs.get("secondary_harvest") or {})
                sampled_rows.append(
                    {
                        "source_kind": source_kind,
                        "source_path": str(path.resolve()),
                        "time": time_text,
                        "symbol": _coerce_text(payload.get("symbol")).upper(),
                        "signal_timeframe": _coerce_text(payload.get("signal_timeframe")),
                        "state_metadata": state_metadata,
                        "advanced_detail": advanced_detail,
                        "state_harvest": state_harvest,
                        "secondary_harvest": secondary_harvest,
                    }
                )
                row_count += 1
        sampled_sources.append(
            {
                "path": str(path.resolve()),
                "file_name": path.name,
                "source_kind": source_kind,
                "sampled_rows": row_count,
                "first_sample_time": first_time,
                "last_sample_time": last_time,
            }
        )
    return sampled_rows, sampled_sources


def _collector_signal_state(value: str) -> bool:
    return _coerce_text(value).upper() not in INACTIVE_STATES


def _activation_bucket(value: str) -> str:
    state = _coerce_text(value).upper()
    if not state or state == "UNKNOWN":
        return "unknown"
    if "PARTIAL" in state:
        return "partial"
    if state.endswith("_ACTIVE") or state == "ACTIVE":
        return "active"
    if "PASSIVE" in state or state.endswith("_IDLE") or state == "DISABLED":
        return "passive"
    if "INACTIVE" in state or "UNAVAILABLE" in state:
        return "inactive"
    return "unknown"


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator > 0 else 0.0


def _collector_summary_rows(counter: Counter[str], total_rows: int, *, collector_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for state_name, count in sorted(counter.items()):
        rows.append(
            {
                "collector_name": collector_name,
                "collector_state": str(state_name),
                "sampled_rows": int(count),
                "sample_ratio": _ratio(int(count), total_rows),
            }
        )
    return rows


def _symbol_matrix_rows(matrix: dict[tuple[str, str], Counter[str]], *, total_rows_by_symbol: Counter[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (symbol, collector_name), counter in sorted(matrix.items()):
        total_rows = int(total_rows_by_symbol.get(symbol, 0))
        active_rows = sum(count for state_name, count in counter.items() if _collector_signal_state(state_name))
        rows.append(
            {
                "symbol": symbol,
                "collector_name": collector_name,
                "sampled_rows": total_rows,
                "active_like_rows": int(active_rows),
                "active_like_ratio": _ratio(int(active_rows), total_rows),
                "top_state": counter.most_common(1)[0][0] if counter else "",
            }
        )
    return rows


def build_state_forecast_validation_advanced_input_activation_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    sf1_report_path: Path = DEFAULT_SF1_REPORT,
    max_files: int = 96,
    max_rows_per_file: int = 40,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    baseline_report = _load_json(baseline_report_path)
    sf1_report = _load_json(sf1_report_path)
    baseline_summary = dict(baseline_report.get("baseline_summary", {}) or {})
    sf1_summary = dict(sf1_report.get("coverage_summary", {}) or {})

    source_paths = _detail_source_paths(trades_root)
    sampled_rows, sampled_sources = _sample_rows(
        source_paths,
        max_files=max_files,
        max_rows_per_file=max_rows_per_file,
    )
    total_rows = len(sampled_rows)

    activation_state_counts = Counter()
    reason_counts = Counter()
    tick_state_counts = Counter()
    order_book_state_counts = Counter()
    event_risk_state_counts = Counter()
    symbol_counts = Counter()
    timeframe_counts = Counter()
    regime_counts = Counter()
    source_kind_counts = Counter()
    total_rows_by_symbol = Counter()
    collector_matrix: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    tick_sample_positive_rows = 0
    order_book_level_positive_rows = 0
    event_match_positive_rows = 0
    activation_reason_present_rows = 0
    advanced_detail_present_rows = 0
    advanced_stress_signal_rows = 0

    for row in sampled_rows:
        source_kind = _coerce_text(row.get("source_kind"))
        symbol = _coerce_text(row.get("symbol")).upper() or "UNKNOWN_SYMBOL"
        timeframe = _coerce_text(row.get("signal_timeframe")) or "UNKNOWN_TIMEFRAME"
        state_metadata = dict(row.get("state_metadata") or {})
        advanced_detail = dict(row.get("advanced_detail") or {})
        state_harvest = dict(row.get("state_harvest") or {})
        secondary_harvest = dict(row.get("secondary_harvest") or {})

        activation_state = (
            _coerce_text(state_metadata.get("advanced_input_activation_state"))
            or _coerce_text(secondary_harvest.get("advanced_input_activation_state"))
            or "UNKNOWN"
        ).upper()
        tick_state = (
            _coerce_text(state_metadata.get("tick_flow_state"))
            or _coerce_text(secondary_harvest.get("tick_flow_state"))
            or "UNKNOWN"
        ).upper()
        order_book_state = (
            _coerce_text(state_metadata.get("order_book_state"))
            or _coerce_text(secondary_harvest.get("order_book_state"))
            or "UNKNOWN"
        ).upper()
        event_risk_state = (
            _coerce_text(state_metadata.get("event_risk_state"))
            or _coerce_text(state_harvest.get("event_risk_state"))
            or "UNKNOWN"
        ).upper()
        regime_state = (
            _coerce_text(state_metadata.get("session_regime_state"))
            or _coerce_text(state_harvest.get("session_regime_state"))
            or "UNKNOWN_REGIME"
        )

        activation_state_counts[activation_state] += 1
        tick_state_counts[tick_state] += 1
        order_book_state_counts[order_book_state] += 1
        event_risk_state_counts[event_risk_state] += 1
        symbol_counts[symbol] += 1
        timeframe_counts[timeframe] += 1
        regime_counts[regime_state] += 1
        source_kind_counts[source_kind] += 1
        total_rows_by_symbol[symbol] += 1

        collector_matrix[(symbol, "tick_flow")][tick_state] += 1
        collector_matrix[(symbol, "order_book")][order_book_state] += 1
        collector_matrix[(symbol, "event_risk")][event_risk_state] += 1

        reasons = list(advanced_detail.get("activation_reasons", []) or [])
        if reasons:
            activation_reason_present_rows += 1
        for reason in reasons:
            reason_counts[_coerce_text(reason)] += 1

        if advanced_detail:
            advanced_detail_present_rows += 1
        if _safe_float(advanced_detail.get("advanced_execution_stress"), 0.0) > 0.0:
            advanced_stress_signal_rows += 1
        if _safe_int(advanced_detail.get("tick_sample_size"), 0) > 0:
            tick_sample_positive_rows += 1
        if _safe_int(advanced_detail.get("order_book_levels"), 0) > 0:
            order_book_level_positive_rows += 1
        if _safe_int(advanced_detail.get("event_risk_match_count"), 0) > 0:
            event_match_positive_rows += 1

    activation_summary = {
        "sample_strategy": "detail_jsonl_per_file_head_sample",
        "available_detail_source_count": int(len(source_paths)),
        "sampled_source_count": int(len(sampled_sources)),
        "sampled_row_count": int(total_rows),
        "max_rows_per_file": int(max_rows_per_file),
        "source_kind_counts": {str(key): int(value) for key, value in sorted(source_kind_counts.items())},
        "activation_active_ratio": _ratio(
            sum(count for state_name, count in activation_state_counts.items() if _activation_bucket(state_name) == "active"),
            total_rows,
        ),
        "activation_partial_ratio": _ratio(
            sum(count for state_name, count in activation_state_counts.items() if _activation_bucket(state_name) == "partial"),
            total_rows,
        ),
        "activation_passive_ratio": _ratio(
            sum(count for state_name, count in activation_state_counts.items() if _activation_bucket(state_name) == "passive"),
            total_rows,
        ),
        "activation_inactive_ratio": _ratio(
            sum(count for state_name, count in activation_state_counts.items() if _activation_bucket(state_name) == "inactive"),
            total_rows,
        ),
        "tick_state_active_like_ratio": _ratio(sum(count for state_name, count in tick_state_counts.items() if _collector_signal_state(state_name)), total_rows),
        "order_book_state_active_like_ratio": _ratio(sum(count for state_name, count in order_book_state_counts.items() if _collector_signal_state(state_name)), total_rows),
        "event_risk_state_active_like_ratio": _ratio(sum(count for state_name, count in event_risk_state_counts.items() if _collector_signal_state(state_name)), total_rows),
        "activation_reason_present_ratio": _ratio(activation_reason_present_rows, total_rows),
        "advanced_detail_present_ratio": _ratio(advanced_detail_present_rows, total_rows),
        "tick_sample_positive_ratio": _ratio(tick_sample_positive_rows, total_rows),
        "order_book_levels_positive_ratio": _ratio(order_book_level_positive_rows, total_rows),
        "event_risk_match_positive_ratio": _ratio(event_match_positive_rows, total_rows),
        "advanced_execution_stress_signal_ratio": _ratio(advanced_stress_signal_rows, total_rows),
        "sf1_sampled_row_count": _safe_int(sf1_summary.get("sampled_row_count")),
        "baseline_advanced_input_collector_count": _safe_int(baseline_summary.get("advanced_input_collector_count")),
    }

    activation_assessment = {
        "activation_state": (
            "collector_activation_gap"
            if activation_summary["order_book_state_active_like_ratio"] < 0.1
            else "activation_surface_present"
        ),
        "tick_history_working": bool(activation_summary["tick_sample_positive_ratio"] > 0.7),
        "order_book_gap_suspected": bool(activation_summary["order_book_levels_positive_ratio"] < 0.1),
        "event_risk_working": bool(activation_summary["event_risk_state_active_like_ratio"] > 0.7),
        "recommended_next_step": "SF3_forecast_harvest_usage_audit",
        "activation_focus": "verify collector imbalance before forecasting value audit",
    }

    suspicious_collectors = [
        {
            "collector_name": "order_book",
            "reason": "order_book_state is almost always inactive/unavailable and order_book_levels rarely > 0",
            "active_like_ratio": activation_summary["order_book_state_active_like_ratio"],
            "positive_payload_ratio": activation_summary["order_book_levels_positive_ratio"],
        },
        {
            "collector_name": "tick_history",
            "reason": "tick sample presence should stay materially above passive/inactive baseline",
            "active_like_ratio": activation_summary["tick_state_active_like_ratio"],
            "positive_payload_ratio": activation_summary["tick_sample_positive_ratio"],
        },
        {
            "collector_name": "event_risk",
            "reason": "event_risk_state can be present while event match count stays low; needs separation from low-risk default",
            "active_like_ratio": activation_summary["event_risk_state_active_like_ratio"],
            "positive_payload_ratio": activation_summary["event_risk_match_positive_ratio"],
        },
    ]

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "state_forecast_validation_sf2_activation_audit",
        "baseline_report_path": str(baseline_report_path),
        "sf1_report_path": str(sf1_report_path),
        "trades_root": str(trades_root),
        "activation_summary": activation_summary,
        "activation_assessment": activation_assessment,
        "sampled_sources": sampled_sources,
        "activation_state_summary": [
            {"advanced_input_activation_state": str(key), "sampled_rows": int(value), "sample_ratio": _ratio(int(value), total_rows)}
            for key, value in sorted(activation_state_counts.items())
        ],
        "activation_reason_summary": [
            {"activation_reason": str(key), "sampled_rows": int(value), "sample_ratio": _ratio(int(value), total_rows)}
            for key, value in sorted(reason_counts.items())
        ],
        "collector_state_summary": {
            "tick_flow": _collector_summary_rows(tick_state_counts, total_rows, collector_name="tick_flow"),
            "order_book": _collector_summary_rows(order_book_state_counts, total_rows, collector_name="order_book"),
            "event_risk": _collector_summary_rows(event_risk_state_counts, total_rows, collector_name="event_risk"),
        },
        "symbol_activation_matrix": _symbol_matrix_rows(collector_matrix, total_rows_by_symbol=total_rows_by_symbol),
        "symbol_summary": [{"symbol": str(key), "sampled_rows": int(value)} for key, value in sorted(symbol_counts.items())],
        "timeframe_summary": [{"signal_timeframe": str(key), "sampled_rows": int(value)} for key, value in sorted(timeframe_counts.items())],
        "session_regime_summary": [{"session_regime_state": str(key), "sampled_rows": int(value)} for key, value in sorted(regime_counts.items())],
        "suspicious_collector_candidates": suspicious_collectors,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("activation_summary", {}) or {})
    assessment = dict(report.get("activation_assessment", {}) or {})
    suspicious = list(report.get("suspicious_collector_candidates", []) or [])
    lines = [
        "# State / Forecast Validation SF2 Activation Audit",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- activation_state: `{assessment.get('activation_state', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- sampled_row_count: `{summary.get('sampled_row_count', 0)}`",
        f"- activation_active_ratio: `{summary.get('activation_active_ratio', 0.0)}`",
        f"- activation_partial_ratio: `{summary.get('activation_partial_ratio', 0.0)}`",
        f"- activation_inactive_ratio: `{summary.get('activation_inactive_ratio', 0.0)}`",
        f"- tick_state_active_like_ratio: `{summary.get('tick_state_active_like_ratio', 0.0)}`",
        f"- order_book_state_active_like_ratio: `{summary.get('order_book_state_active_like_ratio', 0.0)}`",
        f"- event_risk_state_active_like_ratio: `{summary.get('event_risk_state_active_like_ratio', 0.0)}`",
        f"- tick_sample_positive_ratio: `{summary.get('tick_sample_positive_ratio', 0.0)}`",
        f"- order_book_levels_positive_ratio: `{summary.get('order_book_levels_positive_ratio', 0.0)}`",
        f"- event_risk_match_positive_ratio: `{summary.get('event_risk_match_positive_ratio', 0.0)}`",
        "",
        "## Suspicious Collectors",
        "",
        "| collector | active_like_ratio | positive_payload_ratio | reason |",
        "|---|---|---|---|",
    ]
    for row in suspicious:
        lines.append(
            "| {name} | {active:.4f} | {payload:.4f} | {reason} |".format(
                name=_coerce_text(row.get("collector_name")),
                active=float(row.get("active_like_ratio", 0.0)),
                payload=float(row.get("positive_payload_ratio", 0.0)),
                reason=_coerce_text(row.get("reason")),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = list(report.get("symbol_activation_matrix", []) or [])
    fieldnames = ["symbol", "collector_name", "sampled_rows", "active_like_rows", "active_like_ratio", "top_state"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_state_forecast_validation_advanced_input_activation_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    sf1_report_path: Path = DEFAULT_SF1_REPORT,
    output_dir: Path = OUT_DIR,
    max_files: int = 96,
    max_rows_per_file: int = 40,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_state_forecast_validation_advanced_input_activation_report(
        trades_root=trades_root,
        baseline_report_path=baseline_report_path,
        sf1_report_path=sf1_report_path,
        max_files=max_files,
        max_rows_per_file=max_rows_per_file,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "state_forecast_validation_sf2_activation_latest.json"
    latest_csv = output_dir / "state_forecast_validation_sf2_activation_latest.csv"
    latest_md = output_dir / "state_forecast_validation_sf2_activation_latest.md"
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(report, latest_csv)
    _write_markdown(report, latest_md)
    return {
        "latest_json_path": str(latest_json),
        "latest_csv_path": str(latest_csv),
        "latest_markdown_path": str(latest_md),
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SF2 advanced input activation audit report.")
    parser.add_argument("--trades-root", type=Path, default=DEFAULT_TRADES_ROOT)
    parser.add_argument("--baseline-report-path", type=Path, default=DEFAULT_BASELINE_REPORT)
    parser.add_argument("--sf1-report-path", type=Path, default=DEFAULT_SF1_REPORT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--max-files", type=int, default=96)
    parser.add_argument("--max-rows-per-file", type=int, default=40)
    args = parser.parse_args(argv)

    result = write_state_forecast_validation_advanced_input_activation_report(
        trades_root=args.trades_root,
        baseline_report_path=args.baseline_report_path,
        sf1_report_path=args.sf1_report_path,
        output_dir=args.output_dir,
        max_files=args.max_files,
        max_rows_per_file=args.max_rows_per_file,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
