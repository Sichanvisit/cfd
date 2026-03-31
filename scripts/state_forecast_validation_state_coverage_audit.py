from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from backend.trading.engine.core.forecast_engine import FORECAST_HARVEST_TARGETS_V1
from backend.trading.engine.core.models import StateVectorV2


OUT_DIR = ROOT / "data" / "analysis" / "state_forecast_validation"
DEFAULT_TRADES_ROOT = ROOT / "data" / "trades"
DEFAULT_BASELINE_REPORT = OUT_DIR / "state_forecast_validation_sf0_baseline_latest.json"
REPORT_VERSION = "state_forecast_validation_sf1_coverage_audit_v1"

UNKNOWN_LABELS = {"", "UNKNOWN", "UNAVAILABLE", "INACTIVE", "NONE", "NULL", "N/A"}
STATE_VECTOR_CORE_FIELDS = [item.name for item in fields(StateVectorV2) if item.name != "metadata"]
POSITION_ENERGY_FIELDS = [
    "middle_neutrality",
    "position_conflict_score",
    "lower_position_force",
    "upper_position_force",
]
STATE_METADATA_FIELDS = [
    "patience_state_label",
    "topdown_state_label",
    "quality_state_label",
    "execution_friction_state",
    "session_exhaustion_state",
    "event_risk_state",
    "session_regime_state",
    "session_expansion_state",
    "advanced_input_activation_state",
    "tick_flow_state",
    "order_book_state",
    "source_current_rsi",
    "source_current_adx",
    "source_current_plus_di",
    "source_current_minus_di",
    "source_recent_range_mean",
    "source_recent_body_mean",
    "source_sr_level_rank",
    "source_sr_touch_count",
]


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


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _is_meaningful(value: Any) -> bool:
    if not _is_present(value):
        return False
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, (int, float)):
        return abs(float(value)) > 1e-9
    if isinstance(value, str):
        return value.strip().upper() not in UNKNOWN_LABELS
    if isinstance(value, dict):
        return any(_is_meaningful(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_is_meaningful(item) for item in value)
    return True


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


def _sample_detail_rows(paths: list[Path], *, max_files: int, max_rows_per_file: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sampled_rows: list[dict[str, Any]] = []
    sampled_sources: list[dict[str, Any]] = []
    for path in paths[: max(1, int(max_files))]:
        row_count = 0
        source_kind = _source_kind(path)
        first_time = ""
        last_time = ""
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
                sampled_rows.append(
                    {
                        "source_path": str(path.resolve()),
                        "source_kind": source_kind,
                        "time": time_text,
                        "signal_timeframe": _coerce_text(payload.get("signal_timeframe")),
                        "symbol": _coerce_text(payload.get("symbol")).upper(),
                        "state_vector_v2": _decode_json_object(payload.get("state_vector_v2")),
                        "position_snapshot_v2": _decode_json_object(payload.get("position_snapshot_v2")),
                        "forecast_features_v1": _decode_json_object(payload.get("forecast_features_v1")),
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


def _empty_field_stats(field_group: str, field_name: str) -> dict[str, Any]:
    return {
        "field_group": field_group,
        "field_name": field_name,
        "sample_rows": 0,
        "present_rows": 0,
        "meaningful_rows": 0,
        "present_ratio": 0.0,
        "meaningful_ratio": 0.0,
        "coverage_status": "unmeasured",
    }


def _finalize_field_stats(stats: dict[str, Any], total_rows: int) -> dict[str, Any]:
    present_rows = int(stats.get("present_rows", 0))
    meaningful_rows = int(stats.get("meaningful_rows", 0))
    present_ratio = round(present_rows / total_rows, 4) if total_rows > 0 else 0.0
    meaningful_ratio = round(meaningful_rows / total_rows, 4) if total_rows > 0 else 0.0
    coverage_status = "healthy"
    if present_ratio < 0.5:
        coverage_status = "sparse"
    elif meaningful_ratio < 0.1:
        coverage_status = "default_heavy"
    elif meaningful_ratio < 0.3:
        coverage_status = "light_signal"
    return {
        **stats,
        "sample_rows": int(total_rows),
        "present_ratio": present_ratio,
        "meaningful_ratio": meaningful_ratio,
        "coverage_status": coverage_status,
    }


def _increment_stats(stats_map: dict[tuple[str, str], dict[str, Any]], field_group: str, field_name: str, value: Any) -> None:
    key = (field_group, field_name)
    stats = stats_map.setdefault(key, _empty_field_stats(field_group, field_name))
    if _is_present(value):
        stats["present_rows"] = int(stats.get("present_rows", 0)) + 1
    if _is_meaningful(value):
        stats["meaningful_rows"] = int(stats.get("meaningful_rows", 0)) + 1


def build_state_forecast_validation_state_coverage_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    max_files: int = 96,
    max_rows_per_file: int = 40,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    baseline_report = _load_json(baseline_report_path)
    baseline_summary = dict(baseline_report.get("baseline_summary", {}) or {})

    source_paths = _detail_source_paths(trades_root)
    sampled_rows, sampled_sources = _sample_detail_rows(
        source_paths,
        max_files=max_files,
        max_rows_per_file=max_rows_per_file,
    )
    total_rows = len(sampled_rows)

    surface_presence = Counter()
    symbol_counts = Counter()
    timeframe_counts = Counter()
    regime_counts = Counter()
    advanced_activation_counts = Counter()
    source_kind_counts = Counter(row.get("source_kind", "") for row in sampled_rows)
    stats_map: dict[tuple[str, str], dict[str, Any]] = {}

    state_harvest_fields = list(FORECAST_HARVEST_TARGETS_V1.get("state_harvest", []) or [])
    secondary_harvest_fields = list(FORECAST_HARVEST_TARGETS_V1.get("secondary_harvest", []) or [])

    for row in sampled_rows:
        symbol = _coerce_text(row.get("symbol")).upper() or "UNKNOWN_SYMBOL"
        timeframe = _coerce_text(row.get("signal_timeframe")) or "UNKNOWN_TIMEFRAME"
        symbol_counts[symbol] += 1
        timeframe_counts[timeframe] += 1

        position_snapshot = dict(row.get("position_snapshot_v2") or {})
        state_vector = dict(row.get("state_vector_v2") or {})
        forecast_features = dict(row.get("forecast_features_v1") or {})
        state_metadata = dict(state_vector.get("metadata") or {})
        position_energy = dict(position_snapshot.get("energy") or {})
        semantic_inputs = dict((forecast_features.get("metadata") or {}).get("semantic_forecast_inputs_v2") or {})
        state_harvest = dict(semantic_inputs.get("state_harvest") or {})
        secondary_harvest = dict(semantic_inputs.get("secondary_harvest") or {})

        if position_snapshot:
            surface_presence["position_snapshot_v2"] += 1
        if state_vector:
            surface_presence["state_vector_v2"] += 1
        if forecast_features:
            surface_presence["forecast_features_v1"] += 1
        if semantic_inputs:
            surface_presence["semantic_forecast_inputs_v2"] += 1
        if state_harvest:
            surface_presence["state_harvest"] += 1
        if secondary_harvest:
            surface_presence["secondary_harvest"] += 1

        regime_label = (
            _coerce_text(state_metadata.get("session_regime_state"))
            or _coerce_text(state_harvest.get("session_regime_state"))
            or "UNKNOWN_REGIME"
        )
        regime_counts[regime_label] += 1

        activation_state = (
            _coerce_text(state_metadata.get("advanced_input_activation_state"))
            or _coerce_text(secondary_harvest.get("advanced_input_activation_state"))
            or "UNKNOWN"
        )
        advanced_activation_counts[activation_state] += 1

        for field_name in POSITION_ENERGY_FIELDS:
            _increment_stats(stats_map, "position_snapshot_v2.energy", field_name, position_energy.get(field_name))
        for field_name in STATE_VECTOR_CORE_FIELDS:
            _increment_stats(stats_map, "state_vector_v2", field_name, state_vector.get(field_name))
        for field_name in STATE_METADATA_FIELDS:
            _increment_stats(stats_map, "state_vector_v2.metadata", field_name, state_metadata.get(field_name))
        for field_name in state_harvest_fields:
            _increment_stats(stats_map, "state_harvest", field_name, state_harvest.get(field_name))
        for field_name in secondary_harvest_fields:
            _increment_stats(stats_map, "secondary_harvest", field_name, secondary_harvest.get(field_name))

    field_coverage_rows = [
        _finalize_field_stats(stats, total_rows)
        for _, stats in sorted(stats_map.items(), key=lambda item: (item[0][0], item[0][1]))
    ]
    sparse_fields = [row for row in field_coverage_rows if _coerce_text(row.get("coverage_status")) == "sparse"]
    default_heavy_fields = [row for row in field_coverage_rows if _coerce_text(row.get("coverage_status")) == "default_heavy"]
    light_signal_fields = [row for row in field_coverage_rows if _coerce_text(row.get("coverage_status")) == "light_signal"]

    coverage_summary = {
        "sample_strategy": "detail_jsonl_per_file_head_sample",
        "available_detail_source_count": int(len(source_paths)),
        "sampled_source_count": int(len(sampled_sources)),
        "sampled_row_count": int(total_rows),
        "max_rows_per_file": int(max_rows_per_file),
        "source_kind_counts": {str(key): int(value) for key, value in sorted(source_kind_counts.items())},
        "position_snapshot_present_ratio": round(surface_presence.get("position_snapshot_v2", 0) / total_rows, 4) if total_rows else 0.0,
        "state_vector_present_ratio": round(surface_presence.get("state_vector_v2", 0) / total_rows, 4) if total_rows else 0.0,
        "forecast_features_present_ratio": round(surface_presence.get("forecast_features_v1", 0) / total_rows, 4) if total_rows else 0.0,
        "semantic_forecast_inputs_present_ratio": round(surface_presence.get("semantic_forecast_inputs_v2", 0) / total_rows, 4) if total_rows else 0.0,
        "state_harvest_present_ratio": round(surface_presence.get("state_harvest", 0) / total_rows, 4) if total_rows else 0.0,
        "secondary_harvest_present_ratio": round(surface_presence.get("secondary_harvest", 0) / total_rows, 4) if total_rows else 0.0,
        "sparse_field_count": int(len(sparse_fields)),
        "default_heavy_field_count": int(len(default_heavy_fields)),
        "light_signal_field_count": int(len(light_signal_fields)),
        "baseline_state_raw_snapshot_field_count": _safe_int(baseline_summary.get("state_raw_snapshot_field_count")),
        "baseline_state_vector_v2_field_count": _safe_int(baseline_summary.get("state_vector_v2_field_count")),
        "baseline_forecast_harvest_field_count": _safe_int(baseline_summary.get("forecast_harvest_field_count")),
    }
    coverage_assessment = {
        "coverage_state": "state_surface_sparse" if total_rows == 0 or len(sparse_fields) > 0 else "state_surface_present",
        "state_surface_present": bool(total_rows > 0 and coverage_summary["state_vector_present_ratio"] > 0.9),
        "semantic_harvest_present": bool(total_rows > 0 and coverage_summary["state_harvest_present_ratio"] > 0.9),
        "advanced_activation_signal_seen": bool(any(key not in {"UNKNOWN", "INACTIVE", ""} for key in advanced_activation_counts)),
        "recommended_next_step": "SF2_advanced_input_activation_audit",
        "coverage_focus": "identify sparse versus default-heavy fields before activation/value review",
    }
    suspicious_fields = sorted(
        [*sparse_fields, *default_heavy_fields, *light_signal_fields],
        key=lambda row: (
            {"sparse": 0, "default_heavy": 1, "light_signal": 2}.get(_coerce_text(row.get("coverage_status")), 9),
            float(row.get("meaningful_ratio", 0.0)),
            _coerce_text(row.get("field_group")),
            _coerce_text(row.get("field_name")),
        ),
    )[:20]

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "state_forecast_validation_sf1_coverage_audit",
        "baseline_report_path": str(baseline_report_path),
        "trades_root": str(trades_root),
        "coverage_summary": coverage_summary,
        "coverage_assessment": coverage_assessment,
        "sampled_sources": sampled_sources,
        "symbol_summary": [{"symbol": str(key), "sampled_rows": int(value)} for key, value in sorted(symbol_counts.items())],
        "timeframe_summary": [{"signal_timeframe": str(key), "sampled_rows": int(value)} for key, value in sorted(timeframe_counts.items())],
        "session_regime_summary": [{"session_regime_state": str(key), "sampled_rows": int(value)} for key, value in sorted(regime_counts.items())],
        "advanced_input_activation_summary": [{"advanced_input_activation_state": str(key), "sampled_rows": int(value)} for key, value in sorted(advanced_activation_counts.items())],
        "field_coverage_rows": field_coverage_rows,
        "suspicious_field_candidates": suspicious_fields,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("coverage_summary", {}) or {})
    assessment = dict(report.get("coverage_assessment", {}) or {})
    suspicious = list(report.get("suspicious_field_candidates", []) or [])
    lines = [
        "# State / Forecast Validation SF1 Coverage Audit",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- coverage_state: `{assessment.get('coverage_state', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- sample_strategy: `{summary.get('sample_strategy', '')}`",
        f"- available_detail_source_count: `{summary.get('available_detail_source_count', 0)}`",
        f"- sampled_source_count: `{summary.get('sampled_source_count', 0)}`",
        f"- sampled_row_count: `{summary.get('sampled_row_count', 0)}`",
        f"- state_vector_present_ratio: `{summary.get('state_vector_present_ratio', 0.0)}`",
        f"- state_harvest_present_ratio: `{summary.get('state_harvest_present_ratio', 0.0)}`",
        f"- secondary_harvest_present_ratio: `{summary.get('secondary_harvest_present_ratio', 0.0)}`",
        f"- sparse_field_count: `{summary.get('sparse_field_count', 0)}`",
        f"- default_heavy_field_count: `{summary.get('default_heavy_field_count', 0)}`",
        f"- light_signal_field_count: `{summary.get('light_signal_field_count', 0)}`",
        "",
        "## Suspicious Field Candidates",
        "",
        "| field_group | field_name | present_ratio | meaningful_ratio | coverage_status |",
        "|---|---|---|---|---|",
    ]
    for row in suspicious:
        lines.append(
            "| {group} | {name} | {present:.4f} | {meaningful:.4f} | {status} |".format(
                group=_coerce_text(row.get("field_group")),
                name=_coerce_text(row.get("field_name")),
                present=float(row.get("present_ratio", 0.0)),
                meaningful=float(row.get("meaningful_ratio", 0.0)),
                status=_coerce_text(row.get("coverage_status")),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = list(report.get("field_coverage_rows", []) or [])
    fieldnames = [
        "field_group",
        "field_name",
        "sample_rows",
        "present_rows",
        "meaningful_rows",
        "present_ratio",
        "meaningful_ratio",
        "coverage_status",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_state_forecast_validation_state_coverage_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    baseline_report_path: Path = DEFAULT_BASELINE_REPORT,
    output_dir: Path = OUT_DIR,
    max_files: int = 96,
    max_rows_per_file: int = 40,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_state_forecast_validation_state_coverage_report(
        trades_root=trades_root,
        baseline_report_path=baseline_report_path,
        max_files=max_files,
        max_rows_per_file=max_rows_per_file,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "state_forecast_validation_sf1_coverage_latest.json"
    latest_csv = output_dir / "state_forecast_validation_sf1_coverage_latest.csv"
    latest_md = output_dir / "state_forecast_validation_sf1_coverage_latest.md"
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
    parser = argparse.ArgumentParser(description="Build SF1 state coverage audit report.")
    parser.add_argument("--trades-root", type=Path, default=DEFAULT_TRADES_ROOT)
    parser.add_argument("--baseline-report-path", type=Path, default=DEFAULT_BASELINE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--max-files", type=int, default=96)
    parser.add_argument("--max-rows-per-file", type=int, default=40)
    args = parser.parse_args(argv)

    result = write_state_forecast_validation_state_coverage_report(
        trades_root=args.trades_root,
        baseline_report_path=args.baseline_report_path,
        output_dir=args.output_dir,
        max_files=args.max_files,
        max_rows_per_file=args.max_rows_per_file,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
