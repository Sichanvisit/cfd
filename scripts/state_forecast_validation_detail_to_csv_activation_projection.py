from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for candidate in (ROOT, SCRIPT_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


import state_forecast_validation_forecast_feature_value_slice_audit as sf4
import state_forecast_validation_forecast_harvest_usage_audit as sf3


OUT_DIR = ROOT / "data" / "analysis" / "state_forecast_validation"
DEFAULT_TRADES_ROOT = ROOT / "data" / "trades"
REPORT_VERSION = "state_forecast_validation_bf6_detail_to_csv_activation_projection_v1"


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = sf4._coerce_text(value).lower()
    if not text:
        return False
    return text in {"1", "true", "yes", "y", "on"}


def _raw_row_lookup_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        sf4._coerce_text(row.get("_source_path")),
        sf4._coerce_text(row.get("time")),
        sf4._coerce_text(row.get("symbol")).upper(),
        sf4._coerce_text(row.get("signal_timeframe")),
        sf4._coerce_text(row.get("outcome")).upper(),
    )


def _normalize_rows_with_projection_keys(
    entry_rows: list[dict[str, Any]],
    closed_trade_index: dict[tuple[str, str], tuple[list[float], list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    raw_lookup: dict[tuple[str, str, str, str, str], deque[dict[str, Any]]] = defaultdict(deque)
    for row in entry_rows:
        raw_lookup[_raw_row_lookup_key(row)].append(row)

    normalized_rows = sf4._normalize_rows(entry_rows, closed_trade_index)
    enriched: list[dict[str, Any]] = []
    for row in normalized_rows:
        lookup_key = (
            sf4._coerce_text(row.get("_source_path")),
            sf4._coerce_text(row.get("time")),
            sf4._coerce_text(row.get("symbol")).upper(),
            sf4._coerce_text(row.get("signal_timeframe")),
            sf4._coerce_text(row.get("outcome")).upper(),
        )
        raw_row = raw_lookup.get(lookup_key)
        matched_raw = raw_row.popleft() if raw_row else {}
        enriched.append(
            {
                **row,
                "decision_row_key": sf4._coerce_text(matched_raw.get("decision_row_key")),
                "replay_row_key": sf4._coerce_text(matched_raw.get("replay_row_key")),
                "runtime_snapshot_key": sf4._coerce_text(matched_raw.get("runtime_snapshot_key")),
                "trade_link_key": sf4._coerce_text(matched_raw.get("trade_link_key")),
            }
        )
    return enriched


def _sample_detail_projection_rows(
    paths: list[Path],
    *,
    max_files: int,
    max_rows_per_file: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sampled_rows: list[dict[str, Any]] = []
    sampled_sources: list[dict[str, Any]] = []
    for path in paths[: max(1, int(max_files))]:
        row_count = 0
        first_time = ""
        last_time = ""
        source_kind = sf3._source_kind(path)
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
                time_text = sf4._coerce_text(payload.get("time"))
                if not first_time:
                    first_time = time_text
                last_time = time_text or last_time

                forecast_features = sf4._decode_json_object(payload.get("forecast_features_v1"))
                feature_metadata = dict(forecast_features.get("metadata") or {})
                semantic_inputs = dict(feature_metadata.get("semantic_forecast_inputs_v2") or {})
                state_harvest = dict(semantic_inputs.get("state_harvest") or {})
                secondary_harvest = dict(semantic_inputs.get("secondary_harvest") or {})

                transition_forecast = sf4._decode_json_object(payload.get("transition_forecast_v1"))
                management_forecast = sf4._decode_json_object(payload.get("trade_management_forecast_v1"))
                transition_usage = dict(
                    (transition_forecast.get("metadata") or {}).get("semantic_forecast_inputs_v2_usage_v1") or {}
                )
                management_usage = dict(
                    (management_forecast.get("metadata") or {}).get("semantic_forecast_inputs_v2_usage_v1") or {}
                )
                transition_grouped = dict(transition_usage.get("grouped_usage") or {})
                management_grouped = dict(management_usage.get("grouped_usage") or {})

                detail_row = {
                    "source_kind": source_kind,
                    "source_path": str(path.resolve()),
                    "time": time_text,
                    "symbol": sf4._coerce_text(payload.get("symbol")).upper() or "UNKNOWN_SYMBOL",
                    "signal_timeframe": sf4._coerce_text(payload.get("signal_timeframe")) or "UNKNOWN_TIMEFRAME",
                    "decision_row_key": sf4._coerce_text(payload.get("decision_row_key")),
                    "replay_row_key": sf4._coerce_text(payload.get("replay_row_key")),
                    "runtime_snapshot_key": sf4._coerce_text(payload.get("runtime_snapshot_key")),
                    "trade_link_key": sf4._coerce_text(payload.get("trade_link_key")),
                    "session_regime_state": sf4._coerce_text(state_harvest.get("session_regime_state")) or "UNKNOWN_REGIME",
                    "projected_advanced_input_activation_state": (
                        sf4._coerce_text(secondary_harvest.get("advanced_input_activation_state"))
                        or "UNKNOWN_ACTIVATION"
                    ),
                    "projected_order_book_state": sf4._coerce_text(secondary_harvest.get("order_book_state")) or "UNKNOWN_ORDER_BOOK",
                    "projected_tick_flow_state": sf4._coerce_text(secondary_harvest.get("tick_flow_state")) or "UNKNOWN_TICK_FLOW",
                    "projected_event_risk_state": sf4._coerce_text(state_harvest.get("event_risk_state")) or "UNKNOWN_EVENT_RISK",
                }
                for branch_role, grouped_usage in (
                    ("transition_branch", transition_grouped),
                    ("trade_management_branch", management_grouped),
                ):
                    for section in sf4.HARVEST_SECTIONS:
                        section_usage = dict(grouped_usage.get(section) or {})
                        detail_row[f"{branch_role}__{section}__used_projected"] = any(
                            _bool(value) for value in section_usage.values()
                        )

                sampled_rows.append(detail_row)
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


def _build_projection_indices(rows: list[dict[str, Any]]) -> dict[str, dict[Any, deque[int]]]:
    decision_index: dict[str, deque[int]] = defaultdict(deque)
    replay_index: dict[str, deque[int]] = defaultdict(deque)
    time_index: dict[tuple[str, str, str], deque[int]] = defaultdict(deque)
    for idx, row in enumerate(rows):
        decision_key = sf4._coerce_text(row.get("decision_row_key"))
        replay_key = sf4._coerce_text(row.get("replay_row_key"))
        if decision_key:
            decision_index[decision_key].append(idx)
        if replay_key:
            replay_index[replay_key].append(idx)
        time_index[
            (
                sf4._coerce_text(row.get("symbol")).upper(),
                sf4._coerce_text(row.get("signal_timeframe")),
                sf4._coerce_text(row.get("time")),
            )
        ].append(idx)
    return {
        "decision_index": decision_index,
        "replay_index": replay_index,
        "time_index": time_index,
    }


def _pop_available(queue: deque[int], used_indices: set[int]) -> int | None:
    while queue:
        idx = queue[0]
        if idx in used_indices:
            queue.popleft()
            continue
        queue.popleft()
        return idx
    return None


def _match_detail_row_to_csv_row(
    detail_row: dict[str, Any],
    *,
    normalized_rows: list[dict[str, Any]],
    indices: dict[str, dict[Any, deque[int]]],
    used_indices: set[int],
) -> tuple[dict[str, Any] | None, str]:
    decision_key = sf4._coerce_text(detail_row.get("decision_row_key"))
    if decision_key:
        idx = _pop_available(indices["decision_index"].get(decision_key, deque()), used_indices)
        if idx is not None:
            used_indices.add(idx)
            return normalized_rows[idx], "exact_decision_row_key"

    replay_key = sf4._coerce_text(detail_row.get("replay_row_key"))
    if replay_key:
        idx = _pop_available(indices["replay_index"].get(replay_key, deque()), used_indices)
        if idx is not None:
            used_indices.add(idx)
            return normalized_rows[idx], "exact_replay_row_key"

    time_key = (
        sf4._coerce_text(detail_row.get("symbol")).upper(),
        sf4._coerce_text(detail_row.get("signal_timeframe")),
        sf4._coerce_text(detail_row.get("time")),
    )
    idx = _pop_available(indices["time_index"].get(time_key, deque()), used_indices)
    if idx is not None:
        used_indices.add(idx)
        return normalized_rows[idx], "fallback_time_tuple_exact"

    return None, "unmatched"


def _project_rows(
    detail_rows: list[dict[str, Any]],
    *,
    normalized_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    indices = _build_projection_indices(normalized_rows)
    used_indices: set[int] = set()
    projected_rows: list[dict[str, Any]] = []
    unmatched_rows: list[dict[str, Any]] = []
    match_type_counts: Counter[str] = Counter()

    for detail_row in detail_rows:
        matched_row, match_type = _match_detail_row_to_csv_row(
            detail_row,
            normalized_rows=normalized_rows,
            indices=indices,
            used_indices=used_indices,
        )
        match_type_counts[match_type] += 1
        if matched_row is None:
            unmatched_rows.append(
                {
                    "source_kind": detail_row.get("source_kind"),
                    "symbol": detail_row.get("symbol"),
                    "signal_timeframe": detail_row.get("signal_timeframe"),
                    "time": detail_row.get("time"),
                    "match_type": match_type,
                    "decision_row_key_present": bool(sf4._coerce_text(detail_row.get("decision_row_key"))),
                    "replay_row_key_present": bool(sf4._coerce_text(detail_row.get("replay_row_key"))),
                }
            )
            continue

        projected_rows.append(
            {
                **matched_row,
                "projection_match_type": match_type,
                "projection_source_kind": detail_row.get("source_kind"),
                "projected_session_regime_state": detail_row.get("session_regime_state"),
                "projected_advanced_input_activation_state": detail_row.get("projected_advanced_input_activation_state"),
                "projected_order_book_state": detail_row.get("projected_order_book_state"),
                "projected_tick_flow_state": detail_row.get("projected_tick_flow_state"),
                "projected_event_risk_state": detail_row.get("projected_event_risk_state"),
                **{
                    f"{branch_role}__{section}__used_projected": detail_row.get(
                        f"{branch_role}__{section}__used_projected", False
                    )
                    for branch_role in sf4.BRANCH_TO_METRICS
                    for section in sf4.HARVEST_SECTIONS
                },
            }
        )

    return projected_rows, unmatched_rows, match_type_counts


def _projected_harvest_section_value_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for branch_role, metrics in sf4.BRANCH_TO_METRICS.items():
        if branch_role == "transition_branch":
            branch_rows = [row for row in rows if row.get("transition_branch_present")]
        else:
            branch_rows = [row for row in rows if row.get("trade_management_branch_present")]
        for section in sf4.HARVEST_SECTIONS:
            used_key = f"{branch_role}__{section}__used_projected"
            used_rows = [row for row in branch_rows if row.get(used_key)]
            unused_rows = [row for row in branch_rows if not row.get(used_key)]
            used_separations: list[float] = []
            unused_separations: list[float] = []
            metric_rows_with_value = 0
            for metric_name in metrics:
                used_summary = sf4._summarize_metric(used_rows, metric_name=metric_name)
                unused_summary = sf4._summarize_metric(unused_rows, metric_name=metric_name)
                if used_summary["separation_gap"] is not None:
                    used_separations.append(float(used_summary["separation_gap"]))
                    metric_rows_with_value += 1
                if unused_summary["separation_gap"] is not None:
                    unused_separations.append(float(unused_summary["separation_gap"]))
            avg_used = sf4._safe_avg(used_separations)
            avg_unused = sf4._safe_avg(unused_separations)
            separation_delta = None
            if avg_used is not None and avg_unused is not None:
                separation_delta = round(avg_used - avg_unused, 4)
            output.append(
                {
                    "branch_role": branch_role,
                    "harvest_section": section,
                    "branch_rows": int(len(branch_rows)),
                    "section_used_rows": int(len(used_rows)),
                    "section_used_ratio": sf4._ratio(int(len(used_rows)), int(len(branch_rows))),
                    "metric_rows_with_value": int(metric_rows_with_value),
                    "avg_used_separation": avg_used,
                    "avg_unused_separation": avg_unused,
                    "separation_delta": separation_delta,
                }
            )
    return output


def build_state_forecast_validation_detail_to_csv_activation_projection_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    max_files: int = 96,
    max_rows_per_file: int = 40,
    min_labeled_rows: int = 15,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)

    entry_rows, entry_source_rows = sf4._load_entry_sources(trades_root)
    closed_trade_rows = sf4._load_closed_history(trades_root)
    closed_trade_index = sf4._build_closed_trade_index(closed_trade_rows)
    normalized_rows = _normalize_rows_with_projection_keys(entry_rows, closed_trade_index)

    detail_paths = sf3._detail_source_paths(trades_root)
    detail_rows, detail_source_rows = _sample_detail_projection_rows(
        detail_paths,
        max_files=max_files,
        max_rows_per_file=max_rows_per_file,
    )

    projected_rows, unmatched_rows, match_type_counts = _project_rows(
        detail_rows,
        normalized_rows=normalized_rows,
    )

    activation_slice_projection_rows = sf4._slice_rows(
        projected_rows,
        slice_kind="activation_projection",
        slice_field="projected_advanced_input_activation_state",
        min_labeled_rows=min_labeled_rows,
    )
    order_book_slice_projection_rows = sf4._slice_rows(
        projected_rows,
        slice_kind="order_book_projection",
        slice_field="projected_order_book_state",
        min_labeled_rows=min_labeled_rows,
    )
    section_value_projection_rows = _projected_harvest_section_value_rows(projected_rows)

    unmatched_counter: Counter[tuple[str, str]] = Counter(
        (
            sf4._coerce_text(row.get("source_kind")) or "UNKNOWN_SOURCE",
            sf4._coerce_text(row.get("symbol")) or "UNKNOWN_SYMBOL",
        )
        for row in unmatched_rows
    )
    projection_gap_rows = [
        {
            "source_kind": source_kind,
            "symbol": symbol,
            "unmatched_rows": int(count),
        }
        for (source_kind, symbol), count in sorted(unmatched_counter.items(), key=lambda item: (-item[1], item[0]))
    ]

    projection_summary = {
        "csv_value_row_count": int(len(normalized_rows)),
        "detail_source_count": int(len(detail_source_rows)),
        "sampled_detail_rows": int(len(detail_rows)),
        "matched_projection_rows": int(len(projected_rows)),
        "projection_match_ratio": sf4._ratio(int(len(projected_rows)), int(len(detail_rows))),
        "exact_decision_row_key_matches": int(match_type_counts.get("exact_decision_row_key", 0)),
        "exact_replay_row_key_matches": int(match_type_counts.get("exact_replay_row_key", 0)),
        "fallback_time_tuple_matches": int(match_type_counts.get("fallback_time_tuple_exact", 0)),
        "unmatched_projection_rows": int(len(unmatched_rows)),
        "activation_slice_projection_row_count": int(len(activation_slice_projection_rows)),
        "order_book_slice_projection_row_count": int(len(order_book_slice_projection_rows)),
        "section_value_projection_row_count": int(len(section_value_projection_rows)),
        "recommended_next_step": "BF7_close_out_and_handoff",
    }

    projection_assessment = {
        "projection_state": (
            "detail_to_csv_projection_ready"
            if len(projected_rows) > 0
            else "projection_match_missing"
        ),
        "activation_slice_projection_ready": bool(activation_slice_projection_rows),
        "section_value_projection_ready": bool(section_value_projection_rows),
        "primary_gap_call": (
            "projection_match_coverage_limited"
            if sf4._ratio(int(len(projected_rows)), int(len(detail_rows))) < 0.5
            else "projection_surface_ready"
        ),
        "recommended_next_step": "BF7_close_out_and_handoff",
    }

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "state_forecast_validation_bf6_detail_to_csv_activation_projection",
        "trades_root": str(trades_root),
        "projection_summary": projection_summary,
        "projection_assessment": projection_assessment,
        "entry_source_rows": entry_source_rows,
        "detail_source_rows": detail_source_rows,
        "activation_slice_projection_rows": activation_slice_projection_rows,
        "order_book_slice_projection_rows": order_book_slice_projection_rows,
        "section_value_projection_rows": section_value_projection_rows,
        "projection_gap_rows": projection_gap_rows,
        "match_type_counts": {str(key): int(value) for key, value in sorted(match_type_counts.items())},
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("projection_summary", {}) or {})
    assessment = dict(report.get("projection_assessment", {}) or {})
    activation_rows = list(report.get("activation_slice_projection_rows", []) or [])
    section_rows = list(report.get("section_value_projection_rows", []) or [])
    lines = [
        "# BF6 Detail-to-CSV Activation Projection",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- projection_state: `{assessment.get('projection_state', '')}`",
        f"- primary_gap_call: `{assessment.get('primary_gap_call', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- sampled_detail_rows: `{summary.get('sampled_detail_rows', 0)}`",
        f"- matched_projection_rows: `{summary.get('matched_projection_rows', 0)}`",
        f"- projection_match_ratio: `{summary.get('projection_match_ratio', 0.0)}`",
        f"- exact_decision_row_key_matches: `{summary.get('exact_decision_row_key_matches', 0)}`",
        f"- exact_replay_row_key_matches: `{summary.get('exact_replay_row_key_matches', 0)}`",
        f"- fallback_time_tuple_matches: `{summary.get('fallback_time_tuple_matches', 0)}`",
        f"- unmatched_projection_rows: `{summary.get('unmatched_projection_rows', 0)}`",
        "",
        "## Activation Slice Projection",
        "",
        "| metric | slice_key | labeled_rows | separation_gap | state |",
        "|---|---|---:|---:|---|",
    ]
    for row in activation_rows:
        lines.append(
            "| {metric_name} | {slice_key} | {labeled_rows} | {separation_gap} | {value_state} |".format(
                metric_name=sf4._coerce_text(row.get("metric_name")),
                slice_key=sf4._coerce_text(row.get("slice_key")),
                labeled_rows=int(row.get("labeled_rows", 0) or 0),
                separation_gap=row.get("separation_gap"),
                value_state=sf4._coerce_text(row.get("value_state")),
            )
        )
    lines.extend(
        [
            "",
            "## Section Value Projection",
            "",
            "| branch_role | harvest_section | section_used_rows | section_used_ratio | separation_delta |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in section_rows:
        lines.append(
            "| {branch_role} | {harvest_section} | {section_used_rows} | {section_used_ratio} | {separation_delta} |".format(
                branch_role=sf4._coerce_text(row.get("branch_role")),
                harvest_section=sf4._coerce_text(row.get("harvest_section")),
                section_used_rows=int(row.get("section_used_rows", 0) or 0),
                section_used_ratio=row.get("section_used_ratio"),
                separation_delta=row.get("separation_delta"),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for row in list(report.get("activation_slice_projection_rows", []) or []):
        rows.append(
            {
                "row_type": "activation_slice_projection",
                "branch_role": sf4.METRIC_SPECS[sf4._coerce_text(row.get("metric_name"))]["branch_role"],
                "metric_name": row.get("metric_name", ""),
                "slice_kind": row.get("slice_kind", ""),
                "slice_key": row.get("slice_key", ""),
                "labeled_rows": row.get("labeled_rows", ""),
                "separation_gap": row.get("separation_gap", ""),
                "high_low_rate_gap": row.get("high_low_rate_gap", ""),
                "value_state": row.get("value_state", ""),
                "harvest_section": "",
                "section_used_rows": "",
                "section_used_ratio": "",
                "separation_delta": "",
            }
        )
    for row in list(report.get("order_book_slice_projection_rows", []) or []):
        rows.append(
            {
                "row_type": "order_book_slice_projection",
                "branch_role": sf4.METRIC_SPECS[sf4._coerce_text(row.get("metric_name"))]["branch_role"],
                "metric_name": row.get("metric_name", ""),
                "slice_kind": row.get("slice_kind", ""),
                "slice_key": row.get("slice_key", ""),
                "labeled_rows": row.get("labeled_rows", ""),
                "separation_gap": row.get("separation_gap", ""),
                "high_low_rate_gap": row.get("high_low_rate_gap", ""),
                "value_state": row.get("value_state", ""),
                "harvest_section": "",
                "section_used_rows": "",
                "section_used_ratio": "",
                "separation_delta": "",
            }
        )
    for row in list(report.get("section_value_projection_rows", []) or []):
        rows.append(
            {
                "row_type": "section_value_projection",
                "branch_role": row.get("branch_role", ""),
                "metric_name": "",
                "slice_kind": "",
                "slice_key": "",
                "labeled_rows": "",
                "separation_gap": "",
                "high_low_rate_gap": "",
                "value_state": "",
                "harvest_section": row.get("harvest_section", ""),
                "section_used_rows": row.get("section_used_rows", ""),
                "section_used_ratio": row.get("section_used_ratio", ""),
                "separation_delta": row.get("separation_delta", ""),
            }
        )
    fieldnames = [
        "row_type",
        "branch_role",
        "metric_name",
        "slice_kind",
        "slice_key",
        "labeled_rows",
        "separation_gap",
        "high_low_rate_gap",
        "value_state",
        "harvest_section",
        "section_used_rows",
        "section_used_ratio",
        "separation_delta",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_state_forecast_validation_detail_to_csv_activation_projection_report(
    *,
    trades_root: Path = DEFAULT_TRADES_ROOT,
    output_dir: Path = OUT_DIR,
    max_files: int = 96,
    max_rows_per_file: int = 40,
    min_labeled_rows: int = 15,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_state_forecast_validation_detail_to_csv_activation_projection_report(
        trades_root=trades_root,
        max_files=max_files,
        max_rows_per_file=max_rows_per_file,
        min_labeled_rows=min_labeled_rows,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "state_forecast_validation_bf6_projection_latest.json"
    latest_csv = output_dir / "state_forecast_validation_bf6_projection_latest.csv"
    latest_md = output_dir / "state_forecast_validation_bf6_projection_latest.md"
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
    parser = argparse.ArgumentParser(description="Build BF6 detail-to-CSV activation projection report.")
    parser.add_argument("--trades-root", type=Path, default=DEFAULT_TRADES_ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--max-files", type=int, default=96)
    parser.add_argument("--max-rows-per-file", type=int, default=40)
    parser.add_argument("--min-labeled-rows", type=int, default=15)
    args = parser.parse_args(argv)

    result = write_state_forecast_validation_detail_to_csv_activation_projection_report(
        trades_root=args.trades_root,
        output_dir=args.output_dir,
        max_files=args.max_files,
        max_rows_per_file=args.max_rows_per_file,
        min_labeled_rows=args.min_labeled_rows,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
