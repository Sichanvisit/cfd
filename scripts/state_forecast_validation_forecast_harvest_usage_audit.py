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


from backend.trading.engine.core.forecast_engine import FORECAST_HARVEST_TARGETS_V1


OUT_DIR = ROOT / "data" / "analysis" / "state_forecast_validation"
DEFAULT_TRADES_ROOT = ROOT / "data" / "trades"
DEFAULT_SF2_REPORT = OUT_DIR / "state_forecast_validation_sf2_activation_latest.json"
REPORT_VERSION = "state_forecast_validation_sf3_usage_audit_v1"
MAIN_BRANCH_FIELDS = {
    "transition_branch": "transition_forecast_v1",
    "trade_management_branch": "trade_management_forecast_v1",
}
GAP_METRICS_FIELD = "forecast_gap_metrics_v1"


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


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator > 0 else 0.0


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
                forecast_features = _decode_json_object(payload.get("forecast_features_v1"))
                forecast_features_metadata = dict(forecast_features.get("metadata") or {})
                semantic_inputs = dict(forecast_features_metadata.get("semantic_forecast_inputs_v2") or {})
                state_harvest = dict(semantic_inputs.get("state_harvest") or {})
                sampled_rows.append(
                    {
                        "source_kind": source_kind,
                        "source_path": str(path.resolve()),
                        "time": time_text,
                        "symbol": _coerce_text(payload.get("symbol")).upper() or "UNKNOWN_SYMBOL",
                        "signal_timeframe": _coerce_text(payload.get("signal_timeframe")) or "UNKNOWN_TIMEFRAME",
                        "session_regime_state": (
                            _coerce_text(state_harvest.get("session_regime_state"))
                            or "UNKNOWN_REGIME"
                        ),
                        "transition_forecast_v1": _decode_json_object(payload.get("transition_forecast_v1")),
                        "trade_management_forecast_v1": _decode_json_object(payload.get("trade_management_forecast_v1")),
                        "forecast_gap_metrics_v1": _decode_json_object(payload.get(GAP_METRICS_FIELD)),
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


def _empty_field_usage_row(branch_role: str, harvest_section: str, harvest_field: str) -> dict[str, Any]:
    return {
        "branch_role": branch_role,
        "harvest_section": harvest_section,
        "harvest_field": harvest_field,
        "trace_present_rows": 0,
        "used_rows": 0,
        "harvest_only_rows": 0,
        "used_ratio": 0.0,
        "harvest_only_ratio": 0.0,
    }


def _usage_field_rows(
    field_usage: dict[tuple[str, str, str], dict[str, Any]],
    *,
    branch_trace_counts: Counter[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, stats in sorted(field_usage.items()):
        branch_role = _coerce_text(stats.get("branch_role"))
        trace_present_rows = int(branch_trace_counts.get(branch_role, 0))
        used_rows = int(stats.get("used_rows", 0))
        harvest_only_rows = int(stats.get("harvest_only_rows", 0))
        rows.append(
            {
                **stats,
                "trace_present_rows": trace_present_rows,
                "used_ratio": _ratio(used_rows, trace_present_rows),
                "harvest_only_ratio": _ratio(harvest_only_rows, trace_present_rows),
            }
        )
    return rows


def build_state_forecast_validation_forecast_harvest_usage_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    sf2_report_path: Path = DEFAULT_SF2_REPORT,
    max_files: int = 96,
    max_rows_per_file: int = 40,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    sf2_report = _load_json(sf2_report_path)
    sf2_summary = dict(sf2_report.get("activation_summary", {}) or {})

    source_paths = _detail_source_paths(trades_root)
    sampled_rows, sampled_sources = _sample_rows(
        source_paths,
        max_files=max_files,
        max_rows_per_file=max_rows_per_file,
    )
    total_rows = len(sampled_rows)

    source_kind_counts = Counter(row.get("source_kind", "") for row in sampled_rows)
    symbol_counts = Counter()
    timeframe_counts = Counter()
    regime_counts = Counter()
    branch_present_counts = Counter()
    branch_trace_counts = Counter()
    gap_metrics_present_count = 0
    gap_metrics_trace_count = 0
    branch_role_version_counts: dict[str, Counter[str]] = defaultdict(Counter)
    branch_role_formula_counts: dict[str, Counter[str]] = defaultdict(Counter)
    branch_usage_status_counts: dict[str, Counter[str]] = defaultdict(Counter)
    gap_metrics_usage_status_counts = Counter()
    direct_math_field_sets: dict[str, set[str]] = defaultdict(set)
    harvest_only_field_sets: dict[str, set[str]] = defaultdict(set)
    symbol_branch_trace_counts: dict[tuple[str, str], int] = defaultdict(int)
    field_usage: dict[tuple[str, str, str], dict[str, Any]] = {}
    section_any_use_rows: dict[tuple[str, str], int] = defaultdict(int)

    for row in sampled_rows:
        symbol = _coerce_text(row.get("symbol")).upper() or "UNKNOWN_SYMBOL"
        timeframe = _coerce_text(row.get("signal_timeframe")) or "UNKNOWN_TIMEFRAME"
        regime_state = _coerce_text(row.get("session_regime_state")) or "UNKNOWN_REGIME"
        symbol_counts[symbol] += 1
        timeframe_counts[timeframe] += 1
        regime_counts[regime_state] += 1

        for branch_role, payload_field in MAIN_BRANCH_FIELDS.items():
            forecast_payload = dict(row.get(payload_field) or {})
            if not forecast_payload:
                continue
            branch_present_counts[branch_role] += 1
            metadata = dict(forecast_payload.get("metadata") or {})
            usage = dict(metadata.get("semantic_forecast_inputs_v2_usage_v1") or {})
            if not usage:
                continue

            branch_trace_counts[branch_role] += 1
            symbol_branch_trace_counts[(symbol, branch_role)] += 1

            mapper_version = _coerce_text(metadata.get("mapper_version")) or "UNKNOWN_MAPPER"
            score_formula_version = _coerce_text(metadata.get("score_formula_version")) or "UNKNOWN_FORMULA"
            usage_status = _coerce_text(usage.get("usage_status")) or "UNKNOWN_STATUS"
            branch_role_version_counts[branch_role][mapper_version] += 1
            branch_role_formula_counts[branch_role][score_formula_version] += 1
            branch_usage_status_counts[branch_role][usage_status] += 1

            direct_math_fields = set(_coerce_text(item) for item in (usage.get("direct_math_used_fields") or []) if _coerce_text(item))
            harvest_only_fields = set(_coerce_text(item) for item in (usage.get("harvest_only_fields") or []) if _coerce_text(item))
            direct_math_field_sets[branch_role].update(direct_math_fields)
            harvest_only_field_sets[branch_role].update(harvest_only_fields)

            grouped_usage = dict(usage.get("grouped_usage") or {})
            for harvest_section, fields in FORECAST_HARVEST_TARGETS_V1.items():
                section_usage = dict(grouped_usage.get(harvest_section) or {})
                section_used = False
                for harvest_field in fields:
                    key = (branch_role, harvest_section, harvest_field)
                    stats = field_usage.setdefault(
                        key,
                        _empty_field_usage_row(branch_role, harvest_section, harvest_field),
                    )
                    used = bool(section_usage.get(harvest_field, False))
                    if used:
                        stats["used_rows"] = int(stats.get("used_rows", 0)) + 1
                        section_used = True
                    else:
                        stats["harvest_only_rows"] = int(stats.get("harvest_only_rows", 0)) + 1
                if section_used:
                    section_any_use_rows[(branch_role, harvest_section)] += 1

        gap_metrics_payload = dict(row.get(GAP_METRICS_FIELD) or {})
        if gap_metrics_payload:
            gap_metrics_present_count += 1
            usage = dict((gap_metrics_payload.get("metadata") or {}).get("semantic_forecast_inputs_v2_usage_v1") or {})
            if usage:
                gap_metrics_trace_count += 1
                gap_metrics_usage_status_counts[_coerce_text(usage.get("usage_status")) or "UNKNOWN_STATUS"] += 1

    field_usage_rows = _usage_field_rows(field_usage, branch_trace_counts=branch_trace_counts)

    branch_summary_rows: list[dict[str, Any]] = []
    section_summary_rows: list[dict[str, Any]] = []
    for branch_role in MAIN_BRANCH_FIELDS:
        trace_rows = int(branch_trace_counts.get(branch_role, 0))
        present_rows = int(branch_present_counts.get(branch_role, 0))
        branch_summary_rows.append(
            {
                "branch_role": branch_role,
                "present_rows": present_rows,
                "present_ratio": _ratio(present_rows, total_rows),
                "trace_present_rows": trace_rows,
                "trace_present_ratio": _ratio(trace_rows, total_rows),
                "direct_math_field_unique_count": int(len(direct_math_field_sets.get(branch_role, set()))),
                "harvest_only_field_unique_count": int(len(harvest_only_field_sets.get(branch_role, set()))),
                "top_mapper_version": branch_role_version_counts[branch_role].most_common(1)[0][0] if branch_role_version_counts[branch_role] else "",
                "top_score_formula_version": branch_role_formula_counts[branch_role].most_common(1)[0][0] if branch_role_formula_counts[branch_role] else "",
                "top_usage_status": branch_usage_status_counts[branch_role].most_common(1)[0][0] if branch_usage_status_counts[branch_role] else "",
            }
        )
        for harvest_section, fields in FORECAST_HARVEST_TARGETS_V1.items():
            used_field_count = sum(
                1
                for row_stats in field_usage_rows
                if _coerce_text(row_stats.get("branch_role")) == branch_role
                and _coerce_text(row_stats.get("harvest_section")) == harvest_section
                and float(row_stats.get("used_ratio", 0.0)) > 0.0
            )
            section_summary_rows.append(
                {
                    "branch_role": branch_role,
                    "harvest_section": harvest_section,
                    "field_count": int(len(fields)),
                    "ever_used_field_count": int(used_field_count),
                    "ever_used_field_ratio": _ratio(int(used_field_count), int(len(fields))),
                    "rows_with_any_direct_use": int(section_any_use_rows.get((branch_role, harvest_section), 0)),
                    "rows_with_any_direct_use_ratio": _ratio(int(section_any_use_rows.get((branch_role, harvest_section), 0)), trace_rows),
                }
            )

    symbol_branch_trace_rows = [
        {
            "symbol": symbol,
            "branch_role": branch_role,
            "sampled_rows": int(symbol_counts.get(symbol, 0)),
            "trace_present_rows": int(count),
            "trace_present_ratio": _ratio(int(count), int(symbol_counts.get(symbol, 0))),
        }
        for (symbol, branch_role), count in sorted(symbol_branch_trace_counts.items())
    ]

    secondary_direct_use_count = sum(
        1
        for row_stats in field_usage_rows
        if _coerce_text(row_stats.get("harvest_section")) == "secondary_harvest"
        and float(row_stats.get("used_ratio", 0.0)) > 0.0
    )
    suspicious_candidates = [
        {
            "candidate_type": "secondary_harvest_direct_usage_gap",
            "reason": "secondary_harvest fields are harvested but not directly used in transition/management branch math",
            "used_field_count": int(secondary_direct_use_count),
            "field_count": int(len(FORECAST_HARVEST_TARGETS_V1.get("secondary_harvest", []) or [])),
        },
        {
            "candidate_type": "management_state_harvest_narrow_usage",
            "reason": "trade_management branch uses a very small subset of state_harvest fields directly",
            "used_field_count": int(
                next(
                    (
                        row["ever_used_field_count"]
                        for row in section_summary_rows
                        if row["branch_role"] == "trade_management_branch" and row["harvest_section"] == "state_harvest"
                    ),
                    0,
                )
            ),
            "field_count": int(len(FORECAST_HARVEST_TARGETS_V1.get("state_harvest", []) or [])),
        },
        {
            "candidate_type": "gap_metrics_derived_only",
            "reason": (
                "gap metrics usage trace is not persisted in sampled rows; even by contract it is derived from branch outputs, "
                "not direct semantic harvest usage"
            ),
            "trace_present_ratio": _ratio(gap_metrics_trace_count, total_rows),
            "top_usage_status": gap_metrics_usage_status_counts.most_common(1)[0][0] if gap_metrics_usage_status_counts else "",
        },
    ]

    usage_summary = {
        "sample_strategy": "detail_jsonl_per_file_head_sample",
        "available_detail_source_count": int(len(source_paths)),
        "sampled_source_count": int(len(sampled_sources)),
        "sampled_row_count": int(total_rows),
        "max_rows_per_file": int(max_rows_per_file),
        "source_kind_counts": {str(key): int(value) for key, value in sorted(source_kind_counts.items())},
        "transition_forecast_present_ratio": _ratio(int(branch_present_counts.get("transition_branch", 0)), total_rows),
        "trade_management_forecast_present_ratio": _ratio(int(branch_present_counts.get("trade_management_branch", 0)), total_rows),
        "transition_usage_trace_present_ratio": _ratio(int(branch_trace_counts.get("transition_branch", 0)), total_rows),
        "trade_management_usage_trace_present_ratio": _ratio(int(branch_trace_counts.get("trade_management_branch", 0)), total_rows),
        "gap_metrics_present_ratio": _ratio(gap_metrics_present_count, total_rows),
        "gap_metrics_usage_trace_present_ratio": _ratio(gap_metrics_trace_count, total_rows),
        "transition_direct_math_field_unique_count": int(len(direct_math_field_sets.get("transition_branch", set()))),
        "trade_management_direct_math_field_unique_count": int(len(direct_math_field_sets.get("trade_management_branch", set()))),
        "secondary_harvest_direct_use_field_count": int(secondary_direct_use_count),
        "sf2_order_book_state_active_like_ratio": float(sf2_summary.get("order_book_state_active_like_ratio", 0.0) or 0.0),
        "sf2_tick_state_active_like_ratio": float(sf2_summary.get("tick_state_active_like_ratio", 0.0) or 0.0),
        "recommended_next_step": "SF4_forecast_feature_value_slice_audit",
    }

    usage_assessment = {
        "usage_state": (
            "usage_trace_present"
            if usage_summary["transition_usage_trace_present_ratio"] > 0.9
            and usage_summary["trade_management_usage_trace_present_ratio"] > 0.9
            else "usage_trace_partial"
        ),
        "secondary_harvest_direct_gap_suspected": bool(secondary_direct_use_count == 0),
        "transition_branch_trace_working": bool(usage_summary["transition_usage_trace_present_ratio"] > 0.9),
        "trade_management_branch_trace_working": bool(usage_summary["trade_management_usage_trace_present_ratio"] > 0.9),
        "recommended_next_step": "SF4_forecast_feature_value_slice_audit",
        "usage_focus": "measure value of currently active harvests before adding new bridges",
    }

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "state_forecast_validation_sf3_usage_audit",
        "sf2_report_path": str(sf2_report_path),
        "trades_root": str(trades_root),
        "usage_summary": usage_summary,
        "usage_assessment": usage_assessment,
        "sampled_sources": sampled_sources,
        "branch_summary_rows": branch_summary_rows,
        "harvest_section_usage_summary": section_summary_rows,
        "field_usage_rows": field_usage_rows,
        "symbol_branch_trace_summary": symbol_branch_trace_rows,
        "symbol_summary": [{"symbol": str(key), "sampled_rows": int(value)} for key, value in sorted(symbol_counts.items())],
        "timeframe_summary": [{"signal_timeframe": str(key), "sampled_rows": int(value)} for key, value in sorted(timeframe_counts.items())],
        "session_regime_summary": [{"session_regime_state": str(key), "sampled_rows": int(value)} for key, value in sorted(regime_counts.items())],
        "gap_metrics_usage_status_summary": [
            {"usage_status": str(key), "sampled_rows": int(value), "sample_ratio": _ratio(int(value), total_rows)}
            for key, value in sorted(gap_metrics_usage_status_counts.items())
        ],
        "suspicious_usage_candidates": suspicious_candidates,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("usage_summary", {}) or {})
    assessment = dict(report.get("usage_assessment", {}) or {})
    suspicious = list(report.get("suspicious_usage_candidates", []) or [])
    lines = [
        "# State / Forecast Validation SF3 Harvest Usage Audit",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- usage_state: `{assessment.get('usage_state', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- sampled_row_count: `{summary.get('sampled_row_count', 0)}`",
        f"- transition_usage_trace_present_ratio: `{summary.get('transition_usage_trace_present_ratio', 0.0)}`",
        f"- trade_management_usage_trace_present_ratio: `{summary.get('trade_management_usage_trace_present_ratio', 0.0)}`",
        f"- gap_metrics_usage_trace_present_ratio: `{summary.get('gap_metrics_usage_trace_present_ratio', 0.0)}`",
        f"- transition_direct_math_field_unique_count: `{summary.get('transition_direct_math_field_unique_count', 0)}`",
        f"- trade_management_direct_math_field_unique_count: `{summary.get('trade_management_direct_math_field_unique_count', 0)}`",
        f"- secondary_harvest_direct_use_field_count: `{summary.get('secondary_harvest_direct_use_field_count', 0)}`",
        "",
        "## Suspicious Usage Candidates",
        "",
        "| candidate | reason | value_a | value_b |",
        "|---|---|---|---|",
    ]
    for row in suspicious:
        value_a = row.get("used_field_count", row.get("trace_present_ratio", ""))
        value_b = row.get("field_count", row.get("top_usage_status", ""))
        lines.append(
            "| {candidate} | {reason} | {value_a} | {value_b} |".format(
                candidate=_coerce_text(row.get("candidate_type")),
                reason=_coerce_text(row.get("reason")),
                value_a=value_a,
                value_b=value_b,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = list(report.get("field_usage_rows", []) or [])
    fieldnames = [
        "branch_role",
        "harvest_section",
        "harvest_field",
        "trace_present_rows",
        "used_rows",
        "harvest_only_rows",
        "used_ratio",
        "harvest_only_ratio",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_state_forecast_validation_forecast_harvest_usage_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    sf2_report_path: Path = DEFAULT_SF2_REPORT,
    output_dir: Path = OUT_DIR,
    max_files: int = 96,
    max_rows_per_file: int = 40,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_state_forecast_validation_forecast_harvest_usage_report(
        trades_root=trades_root,
        sf2_report_path=sf2_report_path,
        max_files=max_files,
        max_rows_per_file=max_rows_per_file,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "state_forecast_validation_sf3_usage_latest.json"
    latest_csv = output_dir / "state_forecast_validation_sf3_usage_latest.csv"
    latest_md = output_dir / "state_forecast_validation_sf3_usage_latest.md"
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
    parser = argparse.ArgumentParser(description="Build SF3 forecast harvest usage audit report.")
    parser.add_argument("--trades-root", type=Path, default=DEFAULT_TRADES_ROOT)
    parser.add_argument("--sf2-report-path", type=Path, default=DEFAULT_SF2_REPORT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--max-files", type=int, default=96)
    parser.add_argument("--max-rows-per-file", type=int, default=40)
    args = parser.parse_args(argv)

    result = write_state_forecast_validation_forecast_harvest_usage_report(
        trades_root=args.trades_root,
        sf2_report_path=args.sf2_report_path,
        output_dir=args.output_dir,
        max_files=args.max_files,
        max_rows_per_file=args.max_rows_per_file,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
