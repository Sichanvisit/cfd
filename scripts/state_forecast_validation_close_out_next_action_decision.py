from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "analysis" / "state_forecast_validation"
DEFAULT_SF5_REPORT = OUT_DIR / "state_forecast_validation_sf5_gap_matrix_latest.json"
REPORT_VERSION = "state_forecast_validation_sf6_close_out_next_action_decision_v1"


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


def _priority_rank(priority: str) -> int:
    normalized = _coerce_text(priority).upper()
    order = {"P1": 1, "P2": 2, "P3": 3}
    return order.get(normalized, 99)


def _candidate_row(report: dict[str, Any], candidate_name: str) -> dict[str, Any]:
    for row in list(report.get("bridge_candidate_rows", []) or []):
        if _coerce_text(row.get("candidate_name")) == candidate_name:
            return dict(row)
    return {}


def _gap_row(report: dict[str, Any], gap_key: str) -> dict[str, Any]:
    for row in list(report.get("gap_matrix_rows", []) or []):
        if _coerce_text(row.get("gap_key")) == gap_key:
            return dict(row)
    return {}


def _build_do_not_do_rows(sf5: dict[str, Any]) -> list[dict[str, Any]]:
    assessment = dict(sf5.get("gap_assessment", {}) or {})
    return [
        {
            "decision_key": "broad_raw_addition_now",
            "decision_type": "do_not_do_now",
            "status": "defer",
            "why": "state raw surface is already broadly present; broad raw expansion is not the bottleneck",
            "evidence": f"raw_addition_priority={_coerce_text(assessment.get('raw_addition_priority'))}",
        },
        {
            "decision_key": "broad_secondary_raw_expansion_now",
            "decision_type": "do_not_do_now",
            "status": "defer",
            "why": "secondary_harvest direct-use path is missing, so more secondary raw would not fix value separation first",
            "evidence": "secondary_harvest_usage_gap=critical",
        },
        {
            "decision_key": "broad_collector_rebuild_now",
            "decision_type": "do_not_do_now",
            "status": "defer",
            "why": "collector work is not globally broken; only order_book shows a targeted availability gap",
            "evidence": f"collector_fix_priority={_coerce_text(assessment.get('collector_fix_priority'))}",
        },
        {
            "decision_key": "forecast_threshold_tuning_first",
            "decision_type": "do_not_do_now",
            "status": "defer",
            "why": "threshold tuning before bridge/value-path repair would tune around missing signal instead of fixing it",
            "evidence": f"forecast_refinement_priority={_coerce_text(assessment.get('forecast_refinement_priority'))}",
        },
    ]


def _build_immediate_action_rows(sf5: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = list(sf5.get("bridge_candidate_rows", []) or [])
    selected_names = {
        "act_vs_wait_bias_v1",
        "management_hold_reward_hint_v1",
        "management_fast_cut_risk_v1",
    }
    immediate = [dict(row) for row in candidates if _coerce_text(row.get("candidate_name")) in selected_names]
    immediate.sort(key=lambda row: (_priority_rank(_coerce_text(row.get("priority"))), _coerce_text(row.get("candidate_name"))))

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(immediate):
        name = _coerce_text(row.get("candidate_name"))
        rows.append(
            {
                "decision_key": name,
                "decision_type": "immediate_action",
                "status": "active_now" if index == 0 else "queue_next",
                "priority": _coerce_text(row.get("priority")),
                "target_area": _coerce_text(row.get("target_area")),
                "source_layers": _coerce_text(row.get("source_layers")),
                "candidate_outputs": _coerce_text(row.get("candidate_outputs")),
                "why": _coerce_text(row.get("motivation")),
                "evidence": _coerce_text(row.get("why_now")),
            }
        )
    return rows


def _build_followup_action_rows(sf5: dict[str, Any]) -> list[dict[str, Any]]:
    followup_names = [
        "trend_continuation_maturity_v1",
        "advanced_input_reliability_v1",
        "detail_to_csv_activation_projection_v1",
    ]
    rows: list[dict[str, Any]] = []
    for name in followup_names:
        row = _candidate_row(sf5, name)
        if not row:
            continue
        rows.append(
            {
                "decision_key": name,
                "decision_type": "followup_action",
                "status": "after_p1",
                "priority": _coerce_text(row.get("priority")),
                "target_area": _coerce_text(row.get("target_area")),
                "source_layers": _coerce_text(row.get("source_layers")),
                "candidate_outputs": _coerce_text(row.get("candidate_outputs")),
                "why": _coerce_text(row.get("motivation")),
                "evidence": _coerce_text(row.get("why_now")),
            }
        )
    return rows


def build_state_forecast_validation_close_out_next_action_decision_report(
    *,
    sf5_report_path: Path = DEFAULT_SF5_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    sf5 = _load_json(sf5_report_path)
    gap_summary = dict(sf5.get("gap_summary", {}) or {})
    gap_assessment = dict(sf5.get("gap_assessment", {}) or {})

    do_not_do_rows = _build_do_not_do_rows(sf5)
    immediate_action_rows = _build_immediate_action_rows(sf5)
    followup_action_rows = _build_followup_action_rows(sf5)

    active_row = dict(immediate_action_rows[0]) if immediate_action_rows else {}
    false_break_gap = _gap_row(sf5, "transition_false_break_value_gap")
    management_gap = _gap_row(sf5, "management_value_gap")
    secondary_gap = _gap_row(sf5, "secondary_harvest_usage_gap")
    activation_projection_gap = _gap_row(sf5, "activation_slice_projection_gap")

    close_out_summary = {
        "sf_stage_closed_up_to": "SF5",
        "sf6_close_out_ready": True,
        "gap_row_count": _safe_int(gap_summary.get("gap_row_count")),
        "bridge_candidate_count": _safe_int(gap_summary.get("bridge_candidate_count")),
        "do_not_do_count": int(len(do_not_do_rows)),
        "immediate_action_count": int(len(immediate_action_rows)),
        "followup_action_count": int(len(followup_action_rows)),
        "single_active_step": _coerce_text(active_row.get("decision_key")),
        "recommended_next_step": "BF1_act_vs_wait_bias_v1",
    }

    close_out_assessment = {
        "close_out_state": "validation_closed_bridge_first",
        "main_call": "do not broadly add raw fields; close SF with bridge-first next action",
        "raw_addition_call": "defer_broad_raw_addition",
        "collector_call": "only_targeted_order_book_fix_if_still_needed",
        "usage_call": "secondary_harvest_usage_gap_is_real",
        "value_call": "transition_wait_and_management_hold_need_bridge",
        "product_acceptance_link": "act_vs_wait bridge should connect forecast refinement and chart/wait display",
        "single_active_step": _coerce_text(active_row.get("decision_key")),
        "single_active_step_reason": (
            "false-break separation is flat, and act_vs_wait_bias_v1 is the smallest high-leverage bridge "
            "that can improve both transition forecast and product acceptance wait/chart interpretation"
        ),
        "recommended_next_step": "BF1_act_vs_wait_bias_v1",
    }

    next_action_decision = {
        "active_step_key": "BF1_act_vs_wait_bias_v1",
        "active_step_candidate": _coerce_text(active_row.get("decision_key")),
        "active_step_target_area": _coerce_text(active_row.get("target_area")),
        "active_step_outputs": _coerce_text(active_row.get("candidate_outputs")),
        "active_step_reason": _coerce_text(active_row.get("why")),
        "active_step_evidence": _coerce_text(active_row.get("evidence")),
        "why_this_first": (
            "transition false-break value gap is the flattest high-priority problem and it also feeds directly "
            "into chart awareness / wait interpretation, so this bridge has the fastest path to both forecast and product acceptance improvement"
        ),
        "what_comes_after": [
            "BF2_management_hold_reward_hint_v1",
            "BF3_management_fast_cut_risk_v1",
            "P2 trend_continuation_maturity_v1",
        ],
    }

    handoff_notes = [
        {
            "note_key": "raw_surface_sufficient",
            "detail": "SF0~SF2 show state/raw presence is already broad enough; the bottleneck is not missing raw surface.",
        },
        {
            "note_key": "order_book_targeted_only",
            "detail": (
                "order_book remains the only clear activation outlier, so collector work should stay narrowly targeted "
                "and should not block bridge work."
            ),
        },
        {
            "note_key": "secondary_usage_gap_real",
            "detail": (
                "tick/event contexts can activate, but secondary_harvest still has no direct-use/value path, so bridge "
                "summaries are needed before any broader secondary expansion."
            ),
        },
        {
            "note_key": "product_acceptance_alignment",
            "detail": (
                "BF1_act_vs_wait_bias_v1 should be designed so product acceptance tracks can reuse the same summary for "
                "chart wait awareness, not just forecast branch math."
            ),
        },
    ]

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "state_forecast_validation_sf6_close_out_next_action_decision",
        "sf5_report_path": str(sf5_report_path),
        "close_out_summary": close_out_summary,
        "close_out_assessment": close_out_assessment,
        "next_action_decision": next_action_decision,
        "do_not_do_rows": do_not_do_rows,
        "immediate_action_rows": immediate_action_rows,
        "followup_action_rows": followup_action_rows,
        "handoff_notes": handoff_notes,
        "evidence_snapshot": {
            "secondary_usage_gap": {
                "severity": _coerce_text(secondary_gap.get("severity")),
                "evidence_a": secondary_gap.get("evidence_a"),
                "evidence_b": secondary_gap.get("evidence_b"),
            },
            "transition_false_break_value_gap": {
                "severity": _coerce_text(false_break_gap.get("severity")),
                "evidence_a": false_break_gap.get("evidence_a"),
                "evidence_b": false_break_gap.get("evidence_b"),
            },
            "management_value_gap": {
                "severity": _coerce_text(management_gap.get("severity")),
                "evidence_a": management_gap.get("evidence_a"),
                "evidence_b": management_gap.get("evidence_b"),
            },
            "activation_slice_projection_gap": {
                "severity": _coerce_text(activation_projection_gap.get("severity")),
                "evidence_a": activation_projection_gap.get("evidence_a"),
                "evidence_b": activation_projection_gap.get("evidence_b"),
            },
        },
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("close_out_summary", {}) or {})
    assessment = dict(report.get("close_out_assessment", {}) or {})
    decision = dict(report.get("next_action_decision", {}) or {})
    do_not_do_rows = list(report.get("do_not_do_rows", []) or [])
    immediate_rows = list(report.get("immediate_action_rows", []) or [])
    followup_rows = list(report.get("followup_action_rows", []) or [])
    lines = [
        "# State / Forecast Validation SF6 Close-Out / Next-Action Decision",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- close_out_state: `{assessment.get('close_out_state', '')}`",
        f"- main_call: `{assessment.get('main_call', '')}`",
        f"- single_active_step: `{summary.get('single_active_step', '')}`",
        "",
        "## Summary",
        "",
        f"- gap_row_count: `{summary.get('gap_row_count', 0)}`",
        f"- bridge_candidate_count: `{summary.get('bridge_candidate_count', 0)}`",
        f"- do_not_do_count: `{summary.get('do_not_do_count', 0)}`",
        f"- immediate_action_count: `{summary.get('immediate_action_count', 0)}`",
        f"- followup_action_count: `{summary.get('followup_action_count', 0)}`",
        f"- recommended_next_step: `{summary.get('recommended_next_step', '')}`",
        "",
        "## Next Action",
        "",
        f"- active_step_key: `{decision.get('active_step_key', '')}`",
        f"- target_area: `{decision.get('active_step_target_area', '')}`",
        f"- outputs: `{decision.get('active_step_outputs', '')}`",
        f"- why_this_first: `{decision.get('why_this_first', '')}`",
        "",
        "## Do Not Do Now",
        "",
        "| decision | status | evidence | why |",
        "|---|---|---|---|",
    ]
    for row in do_not_do_rows:
        lines.append(
            "| {decision} | {status} | {evidence} | {why} |".format(
                decision=_coerce_text(row.get("decision_key")),
                status=_coerce_text(row.get("status")),
                evidence=_coerce_text(row.get("evidence")),
                why=_coerce_text(row.get("why")),
            )
        )
    lines.extend(
        [
            "",
            "## Immediate Actions",
            "",
            "| action | status | priority | target | outputs | evidence |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in immediate_rows:
        lines.append(
            "| {action} | {status} | {priority} | {target} | {outputs} | {evidence} |".format(
                action=_coerce_text(row.get("decision_key")),
                status=_coerce_text(row.get("status")),
                priority=_coerce_text(row.get("priority")),
                target=_coerce_text(row.get("target_area")),
                outputs=_coerce_text(row.get("candidate_outputs")),
                evidence=_coerce_text(row.get("evidence")),
            )
        )
    lines.extend(
        [
            "",
            "## Follow-up Queue",
            "",
            "| action | priority | target | outputs | evidence |",
            "|---|---|---|---|---|",
        ]
    )
    for row in followup_rows:
        lines.append(
            "| {action} | {priority} | {target} | {outputs} | {evidence} |".format(
                action=_coerce_text(row.get("decision_key")),
                priority=_coerce_text(row.get("priority")),
                target=_coerce_text(row.get("target_area")),
                outputs=_coerce_text(row.get("candidate_outputs")),
                evidence=_coerce_text(row.get("evidence")),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for collection_name in ("do_not_do_rows", "immediate_action_rows", "followup_action_rows"):
        for row in list(report.get(collection_name, []) or []):
            rows.append(
                {
                    "decision_type": _coerce_text(row.get("decision_type")),
                    "decision_key": _coerce_text(row.get("decision_key")),
                    "status": _coerce_text(row.get("status")),
                    "priority": _coerce_text(row.get("priority")),
                    "target_area": _coerce_text(row.get("target_area")),
                    "source_layers": _coerce_text(row.get("source_layers")),
                    "candidate_outputs": _coerce_text(row.get("candidate_outputs")),
                    "evidence": _coerce_text(row.get("evidence")),
                    "why": _coerce_text(row.get("why")),
                }
            )
    fieldnames = [
        "decision_type",
        "decision_key",
        "status",
        "priority",
        "target_area",
        "source_layers",
        "candidate_outputs",
        "evidence",
        "why",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_state_forecast_validation_close_out_next_action_decision_report(
    *,
    sf5_report_path: Path = DEFAULT_SF5_REPORT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_state_forecast_validation_close_out_next_action_decision_report(
        sf5_report_path=sf5_report_path,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "state_forecast_validation_sf6_close_out_latest.json"
    latest_csv = output_dir / "state_forecast_validation_sf6_close_out_latest.csv"
    latest_md = output_dir / "state_forecast_validation_sf6_close_out_latest.md"
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
    parser = argparse.ArgumentParser(description="Build SF6 close-out and next-action decision report.")
    parser.add_argument("--sf5-report-path", type=Path, default=DEFAULT_SF5_REPORT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    result = write_state_forecast_validation_close_out_next_action_decision_report(
        sf5_report_path=args.sf5_report_path,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
