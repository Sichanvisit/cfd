from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "analysis" / "state_forecast_validation"
DEFAULT_SF1_REPORT = OUT_DIR / "state_forecast_validation_sf1_coverage_latest.json"
DEFAULT_SF2_REPORT = OUT_DIR / "state_forecast_validation_sf2_activation_latest.json"
DEFAULT_SF3_REPORT = OUT_DIR / "state_forecast_validation_sf3_usage_latest.json"
DEFAULT_SF4_REPORT = OUT_DIR / "state_forecast_validation_sf4_value_latest.json"
REPORT_VERSION = "state_forecast_validation_sf5_gap_matrix_bridge_review_v1"


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = _coerce_text(value)
        return float(text) if text else float(default)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        text = _coerce_text(value)
        return int(float(text)) if text else int(default)
    except Exception:
        return int(default)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_row(report: dict[str, Any], metric_name: str) -> dict[str, Any]:
    for row in list(report.get("metric_value_rows", []) or []):
        if _coerce_text(row.get("metric_name")) == metric_name:
            return dict(row)
    return {}


def _slice_row(report: dict[str, Any], metric_name: str, slice_kind: str, slice_key: str) -> dict[str, Any]:
    collections = {
        "symbol": list(report.get("symbol_slice_rows", []) or []),
        "regime": list(report.get("regime_slice_rows", []) or []),
        "activation": list(report.get("activation_slice_rows", []) or []),
    }
    for row in collections.get(slice_kind, []):
        if _coerce_text(row.get("metric_name")) == metric_name and _coerce_text(row.get("slice_key")) == slice_key:
            return dict(row)
    return {}


def _section_row(report: dict[str, Any], branch_role: str, harvest_section: str) -> dict[str, Any]:
    for row in list(report.get("harvest_section_value_rows", []) or []):
        if _coerce_text(row.get("branch_role")) == branch_role and _coerce_text(row.get("harvest_section")) == harvest_section:
            return dict(row)
    return {}


def _build_gap_matrix_rows(
    sf1: dict[str, Any],
    sf2: dict[str, Any],
    sf3: dict[str, Any],
    sf4: dict[str, Any],
) -> list[dict[str, Any]]:
    sf1_summary = dict(sf1.get("coverage_summary", {}) or {})
    sf2_summary = dict(sf2.get("activation_summary", {}) or {})
    sf3_summary = dict(sf3.get("usage_summary", {}) or {})
    sf4_summary = dict(sf4.get("value_summary", {}) or {})
    p_false_break = _metric_row(sf4, "p_false_break")
    p_continue_favor = _metric_row(sf4, "p_continue_favor")
    p_fail_now = _metric_row(sf4, "p_fail_now")
    range_continue = _slice_row(sf4, "p_continue_favor", "regime", "RANGE")
    trend_continue = _slice_row(sf4, "p_continue_favor", "regime", "TREND")
    secondary_transition = _section_row(sf4, "transition_branch", "secondary_harvest")

    return [
        {
            "gap_key": "state_raw_surface",
            "gap_type": "raw",
            "severity": "healthy",
            "current_state": "surface_present_default_heavy_watch_only",
            "evidence_a": _safe_float(sf1_summary.get("state_vector_present_ratio")),
            "evidence_b": _safe_int(sf1_summary.get("default_heavy_field_count")),
            "why_it_matters": "raw state is broadly present, so broad raw expansion is not the first lever",
            "recommended_action": "keep broad raw-add low priority; focus on activation/usage/value gaps first",
        },
        {
            "gap_key": "order_book_activation_gap",
            "gap_type": "activation",
            "severity": "high",
            "current_state": "collector_unavailable_most_of_time",
            "evidence_a": _safe_float(sf2_summary.get("order_book_state_active_like_ratio")),
            "evidence_b": _safe_float(sf2_summary.get("tick_state_active_like_ratio")),
            "why_it_matters": "order_book is almost never active while tick/event are alive, so secondary imbalance is collector-side not raw-surface-wide",
            "recommended_action": "treat order_book as targeted collector problem, not whole-state deficiency",
        },
        {
            "gap_key": "secondary_harvest_usage_gap",
            "gap_type": "usage",
            "severity": "critical",
            "current_state": "harvested_but_not_directly_used",
            "evidence_a": _safe_int(sf3_summary.get("secondary_harvest_direct_use_field_count")),
            "evidence_b": _safe_float(secondary_transition.get("section_used_ratio")),
            "why_it_matters": "secondary inputs can be active, but they still do not open a direct value path in branch math",
            "recommended_action": "bridge-first or branch-math-first; do not add more secondary raw until usage path exists",
        },
        {
            "gap_key": "transition_false_break_value_gap",
            "gap_type": "value",
            "severity": "high",
            "current_state": "wait_false_break_signal_flat",
            "evidence_a": _safe_float(p_false_break.get("separation_gap")),
            "evidence_b": _safe_float(p_false_break.get("high_low_rate_gap")),
            "why_it_matters": "transition false-break score is not separating WAIT/observe rows in a useful way",
            "recommended_action": "add act-vs-wait / false-break bridge rather than broad raw expansion",
        },
        {
            "gap_key": "management_value_gap",
            "gap_type": "value",
            "severity": "high",
            "current_state": "management_outcome_signal_weak_or_flat",
            "evidence_a": _safe_float(p_continue_favor.get("separation_gap")),
            "evidence_b": _safe_float(p_fail_now.get("separation_gap")),
            "why_it_matters": "management forecast is matched to real trades now, but hold/fail separation is still weak",
            "recommended_action": "introduce hold-reward / fast-cut bridge candidates before new raw fields",
        },
        {
            "gap_key": "trend_management_slice_gap",
            "gap_type": "bridge",
            "severity": "medium",
            "current_state": "trend_slice_weaker_than_range",
            "evidence_a": _safe_float(range_continue.get("separation_gap")),
            "evidence_b": _safe_float(trend_continue.get("separation_gap")),
            "why_it_matters": "trend regime management value is flatter than range, suggesting missing continuation maturity / exhaustion bridge",
            "recommended_action": "promote trend-specific management bridge summary instead of more generic raw inputs",
        },
        {
            "gap_key": "activation_slice_projection_gap",
            "gap_type": "bridge",
            "severity": "medium",
            "current_state": "csv_surface_loses_activation_slice",
            "evidence_a": _safe_int(len(list(sf4.get("activation_slice_rows", []) or []))),
            "evidence_b": _safe_int(sf4_summary.get("decision_row_count")),
            "why_it_matters": "full CSV keeps value coverage, but activation metadata is stripped so activation slice review cannot be projected directly",
            "recommended_action": "carry a small projected activation bridge or combine SF3 detail usage with SF4 value rows in SF6",
        },
    ]


def _build_bridge_candidate_rows(sf2: dict[str, Any], sf3: dict[str, Any], sf4: dict[str, Any]) -> list[dict[str, Any]]:
    sf2_summary = dict(sf2.get("activation_summary", {}) or {})
    sf3_summary = dict(sf3.get("usage_summary", {}) or {})
    p_false_break = _metric_row(sf4, "p_false_break")
    p_continue_favor = _metric_row(sf4, "p_continue_favor")
    p_fail_now = _metric_row(sf4, "p_fail_now")
    trend_continue = _slice_row(sf4, "p_continue_favor", "regime", "TREND")

    return [
        {
            "candidate_name": "act_vs_wait_bias_v1",
            "priority": "P1",
            "target_area": "transition_forecast + product_acceptance_chart_wait",
            "source_layers": "state + evidence + belief + barrier",
            "motivation": "p_false_break is flat, so WAIT/observe discrimination needs an explicit bridge",
            "candidate_outputs": "act_vs_wait_bias,false_break_risk,awareness_keep_allowed",
            "why_now": f"p_false_break separation_gap={_safe_float(p_false_break.get('separation_gap'))}",
        },
        {
            "candidate_name": "management_hold_reward_hint_v1",
            "priority": "P1",
            "target_area": "trade_management_forecast + hold/exit review",
            "source_layers": "belief + barrier + trend/range state",
            "motivation": "continue-favor is only weakly separating profitable trades",
            "candidate_outputs": "hold_reward_hint,recoverability_hint,continuation_tailwind",
            "why_now": f"p_continue_favor separation_gap={_safe_float(p_continue_favor.get('separation_gap'))}",
        },
        {
            "candidate_name": "management_fast_cut_risk_v1",
            "priority": "P1",
            "target_area": "trade_management_forecast + cut_now/exit caution",
            "source_layers": "state + barrier + event/friction",
            "motivation": "fail-now remains flat, so early-loss risk needs a more explicit bridge",
            "candidate_outputs": "fast_cut_risk,collision_risk,event_caution",
            "why_now": f"p_fail_now separation_gap={_safe_float(p_fail_now.get('separation_gap'))}",
        },
        {
            "candidate_name": "trend_continuation_maturity_v1",
            "priority": "P2",
            "target_area": "management trend slice",
            "source_layers": "state + belief persistence + exhaustion",
            "motivation": "trend management slice is weaker than range and likely misses maturity/exhaustion context",
            "candidate_outputs": "continuation_maturity,exhaustion_pressure,trend_hold_confidence",
            "why_now": f"trend_continue separation_gap={_safe_float(trend_continue.get('separation_gap'))}",
        },
        {
            "candidate_name": "advanced_input_reliability_v1",
            "priority": "P2",
            "target_area": "secondary_harvest projection + product display modifier",
            "source_layers": "advanced activation + collector availability",
            "motivation": "tick/event are alive but order_book is effectively unavailable, so raw secondary use needs a reliability bridge first",
            "candidate_outputs": "advanced_reliability,order_book_reliable,event_context_reliable",
            "why_now": f"order_book_active={_safe_float(sf2_summary.get('order_book_state_active_like_ratio'))}, secondary_direct_use={_safe_int(sf3_summary.get('secondary_harvest_direct_use_field_count'))}",
        },
        {
            "candidate_name": "detail_to_csv_activation_projection_v1",
            "priority": "P3",
            "target_area": "state_forecast_validation analysis surface",
            "source_layers": "detail usage trace + csv value rows",
            "motivation": "full CSV preserves value coverage but strips activation/usage trace, so SF audits need a projection bridge",
            "candidate_outputs": "activation_slice_projection,section_value_projection",
            "why_now": "activation slice unavailable in SF4 CSV surface",
        },
    ]


def build_state_forecast_validation_gap_matrix_bridge_candidate_report(
    *,
    sf1_report_path: Path = DEFAULT_SF1_REPORT,
    sf2_report_path: Path = DEFAULT_SF2_REPORT,
    sf3_report_path: Path = DEFAULT_SF3_REPORT,
    sf4_report_path: Path = DEFAULT_SF4_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    sf1 = _load_json(sf1_report_path)
    sf2 = _load_json(sf2_report_path)
    sf3 = _load_json(sf3_report_path)
    sf4 = _load_json(sf4_report_path)

    gap_matrix_rows = _build_gap_matrix_rows(sf1, sf2, sf3, sf4)
    bridge_candidate_rows = _build_bridge_candidate_rows(sf2, sf3, sf4)

    severity_counts: dict[str, int] = {}
    for row in gap_matrix_rows:
        severity = _coerce_text(row.get("severity")) or "unknown"
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    gap_summary = {
        "gap_row_count": int(len(gap_matrix_rows)),
        "bridge_candidate_count": int(len(bridge_candidate_rows)),
        "raw_gap_count": int(sum(1 for row in gap_matrix_rows if _coerce_text(row.get("gap_type")) == "raw" and _coerce_text(row.get("severity")) != "healthy")),
        "activation_gap_count": int(sum(1 for row in gap_matrix_rows if _coerce_text(row.get("gap_type")) == "activation")),
        "usage_gap_count": int(sum(1 for row in gap_matrix_rows if _coerce_text(row.get("gap_type")) == "usage")),
        "value_gap_count": int(sum(1 for row in gap_matrix_rows if _coerce_text(row.get("gap_type")) == "value")),
        "bridge_gap_count": int(sum(1 for row in gap_matrix_rows if _coerce_text(row.get("gap_type")) == "bridge")),
        "severity_counts": severity_counts,
        "recommended_next_step": "SF6_close_out_next_action_decision",
    }

    gap_assessment = {
        "primary_gap_family": "bridge_and_usage",
        "raw_addition_priority": "low",
        "collector_fix_priority": "targeted_order_book_only",
        "bridge_addition_priority": "high",
        "forecast_refinement_priority": "transition_wait_and_management_hold",
        "recommended_next_step": "SF6_close_out_next_action_decision",
        "main_call": "do not broadly add raw fields; bridge and value path gaps are the real bottleneck",
    }

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "state_forecast_validation_sf5_gap_matrix_bridge_review",
        "sf1_report_path": str(sf1_report_path),
        "sf2_report_path": str(sf2_report_path),
        "sf3_report_path": str(sf3_report_path),
        "sf4_report_path": str(sf4_report_path),
        "gap_summary": gap_summary,
        "gap_assessment": gap_assessment,
        "gap_matrix_rows": gap_matrix_rows,
        "bridge_candidate_rows": bridge_candidate_rows,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("gap_summary", {}) or {})
    assessment = dict(report.get("gap_assessment", {}) or {})
    gap_rows = list(report.get("gap_matrix_rows", []) or [])
    bridge_rows = list(report.get("bridge_candidate_rows", []) or [])
    lines = [
        "# State / Forecast Validation SF5 Gap Matrix / Bridge Candidate Review",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- primary_gap_family: `{assessment.get('primary_gap_family', '')}`",
        f"- main_call: `{assessment.get('main_call', '')}`",
        f"- recommended_next_step: `{assessment.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- gap_row_count: `{summary.get('gap_row_count', 0)}`",
        f"- bridge_candidate_count: `{summary.get('bridge_candidate_count', 0)}`",
        f"- raw_gap_count: `{summary.get('raw_gap_count', 0)}`",
        f"- activation_gap_count: `{summary.get('activation_gap_count', 0)}`",
        f"- usage_gap_count: `{summary.get('usage_gap_count', 0)}`",
        f"- value_gap_count: `{summary.get('value_gap_count', 0)}`",
        f"- bridge_gap_count: `{summary.get('bridge_gap_count', 0)}`",
        "",
        "## Gap Matrix",
        "",
        "| gap | type | severity | state | evidence_a | evidence_b | action |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in gap_rows:
        lines.append(
            "| {gap} | {gap_type} | {severity} | {state} | {evidence_a} | {evidence_b} | {action} |".format(
                gap=_coerce_text(row.get("gap_key")),
                gap_type=_coerce_text(row.get("gap_type")),
                severity=_coerce_text(row.get("severity")),
                state=_coerce_text(row.get("current_state")),
                evidence_a=row.get("evidence_a"),
                evidence_b=row.get("evidence_b"),
                action=_coerce_text(row.get("recommended_action")),
            )
        )
    lines.extend(
        [
            "",
            "## Bridge Candidates",
            "",
            "| candidate | priority | target | outputs | why_now |",
            "|---|---|---|---|---|",
        ]
    )
    for row in bridge_rows:
        lines.append(
            "| {candidate} | {priority} | {target} | {outputs} | {why_now} |".format(
                candidate=_coerce_text(row.get("candidate_name")),
                priority=_coerce_text(row.get("priority")),
                target=_coerce_text(row.get("target_area")),
                outputs=_coerce_text(row.get("candidate_outputs")),
                why_now=_coerce_text(row.get("why_now")),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = list(report.get("gap_matrix_rows", []) or [])
    fieldnames = [
        "gap_key",
        "gap_type",
        "severity",
        "current_state",
        "evidence_a",
        "evidence_b",
        "why_it_matters",
        "recommended_action",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_state_forecast_validation_gap_matrix_bridge_candidate_report(
    *,
    sf1_report_path: Path = DEFAULT_SF1_REPORT,
    sf2_report_path: Path = DEFAULT_SF2_REPORT,
    sf3_report_path: Path = DEFAULT_SF3_REPORT,
    sf4_report_path: Path = DEFAULT_SF4_REPORT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_state_forecast_validation_gap_matrix_bridge_candidate_report(
        sf1_report_path=sf1_report_path,
        sf2_report_path=sf2_report_path,
        sf3_report_path=sf3_report_path,
        sf4_report_path=sf4_report_path,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "state_forecast_validation_sf5_gap_matrix_latest.json"
    latest_csv = output_dir / "state_forecast_validation_sf5_gap_matrix_latest.csv"
    latest_md = output_dir / "state_forecast_validation_sf5_gap_matrix_latest.md"
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
    parser = argparse.ArgumentParser(description="Build SF5 gap matrix / bridge candidate review report.")
    parser.add_argument("--sf1-report-path", type=Path, default=DEFAULT_SF1_REPORT)
    parser.add_argument("--sf2-report-path", type=Path, default=DEFAULT_SF2_REPORT)
    parser.add_argument("--sf3-report-path", type=Path, default=DEFAULT_SF3_REPORT)
    parser.add_argument("--sf4-report-path", type=Path, default=DEFAULT_SF4_REPORT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    result = write_state_forecast_validation_gap_matrix_bridge_candidate_report(
        sf1_report_path=args.sf1_report_path,
        sf2_report_path=args.sf2_report_path,
        sf3_report_path=args.sf3_report_path,
        sf4_report_path=args.sf4_report_path,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
