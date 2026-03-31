from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "analysis" / "state_forecast_validation"
DEFAULT_SF6_REPORT = OUT_DIR / "state_forecast_validation_sf6_close_out_latest.json"
DEFAULT_BF6_REPORT = OUT_DIR / "state_forecast_validation_bf6_projection_latest.json"
REPORT_VERSION = "bridge_first_bf7_close_out_handoff_v1"


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


def _bridge_inventory_rows(sf6: dict[str, Any], bf6: dict[str, Any]) -> list[dict[str, Any]]:
    sf6_next = dict(sf6.get("next_action_decision", {}) or {})
    bf6_summary = dict(bf6.get("projection_summary", {}) or {})
    return [
        {
            "bridge_key": "BF1_act_vs_wait_bias_v1",
            "status": "implemented",
            "target_area": "transition_forecast + product_acceptance_chart_wait",
            "output_surface": "act_vs_wait_bias,false_break_risk,awareness_keep_allowed",
            "evidence": _coerce_text(sf6_next.get("active_step_evidence")),
            "handoff_role": "chart wait awareness + transition false-break discrimination",
        },
        {
            "bridge_key": "BF2_management_hold_reward_hint_v1",
            "status": "implemented",
            "target_area": "trade_management_forecast",
            "output_surface": "hold_reward_hint,edge_to_edge_tailwind,hold_patience_allowed",
            "evidence": "management positive hold hint bridge is wired into management branch metadata",
            "handoff_role": "hold/continue favor review",
        },
        {
            "bridge_key": "BF3_management_fast_cut_risk_v1",
            "status": "implemented",
            "target_area": "trade_management_forecast",
            "output_surface": "fast_cut_risk,collision_risk,event_caution,cut_now_allowed",
            "evidence": "management fast-cut bridge is wired into fail-now / reentry side",
            "handoff_role": "exit caution + cut-now review",
        },
        {
            "bridge_key": "BF4_trend_continuation_maturity_v1",
            "status": "implemented",
            "target_area": "trade_management_forecast trend slice",
            "output_surface": "continuation_maturity,exhaustion_pressure,trend_hold_confidence",
            "evidence": "trend continuation maturity bridge is wired into continue/reach path",
            "handoff_role": "trend hold maturity review",
        },
        {
            "bridge_key": "BF5_advanced_input_reliability_v1",
            "status": "implemented",
            "target_area": "transition_forecast + trade_management_forecast",
            "output_surface": "advanced_reliability,order_book_reliable,event_context_reliable",
            "evidence": "secondary_harvest direct-use trace is now emitted on fresh BF5 rows",
            "handoff_role": "advanced input reliability gating",
        },
        {
            "bridge_key": "BF6_detail_to_csv_activation_projection_v1",
            "status": "implemented",
            "target_area": "state_forecast_validation review surface",
            "output_surface": "activation_slice_projection,section_value_projection",
            "evidence": (
                f"projection_match_ratio={_safe_float(bf6_summary.get('projection_match_ratio'))}, "
                f"matched_projection_rows={_safe_int(bf6_summary.get('matched_projection_rows'))}"
            ),
            "handoff_role": "detail usage -> csv value projection restoration",
        },
    ]


def build_bridge_first_close_out_handoff_report(
    *,
    sf6_report_path: Path = DEFAULT_SF6_REPORT,
    bf6_report_path: Path = DEFAULT_BF6_REPORT,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_now = _resolve_now(now)
    sf6 = _load_json(sf6_report_path)
    bf6 = _load_json(bf6_report_path)

    sf6_summary = dict(sf6.get("close_out_summary", {}) or {})
    sf6_assessment = dict(sf6.get("close_out_assessment", {}) or {})
    bf6_summary = dict(bf6.get("projection_summary", {}) or {})
    bf6_assessment = dict(bf6.get("projection_assessment", {}) or {})

    bridge_rows = _bridge_inventory_rows(sf6, bf6)
    handoff_rows = [
        {
            "handoff_lane": "product_acceptance",
            "next_action_key": "common_state_aware_display_modifier_v1",
            "priority": "P1",
            "why": "BF bridges now exist, so all-symbol chart display should reuse the same state/evidence/belief/barrier/forecast modifiers instead of symbol-by-symbol ad hoc wiring",
            "evidence": "user-facing chart acceptance is now the highest-leverage consumer of BF bridge outputs",
        },
        {
            "handoff_lane": "forecast_validation",
            "next_action_key": "rerun_sf3_sf4_with_fresh_bf5_rows",
            "priority": "P1",
            "why": "BF5 secondary direct-use and BF6 projection need fresh runtime rows to show their real latest value path",
            "evidence": "historical rows still understate BF5/BF6 effect because pre-BF5 metadata remains in older detail rows",
        },
        {
            "handoff_lane": "collector_followup",
            "next_action_key": "targeted_order_book_availability_review_only_if_gap_persists",
            "priority": "P2",
            "why": "order_book is still the only targeted activation outlier, but BF does not justify a broad collector rebuild",
            "evidence": _coerce_text(sf6_assessment.get("collector_call")) or "only_targeted_order_book_fix_if_still_needed",
        },
    ]

    close_out_summary = {
        "bf_stage_closed_up_to": "BF6",
        "bf7_close_out_ready": True,
        "implemented_bridge_count": int(len(bridge_rows)),
        "analysis_projection_ready": bool(bf6_assessment.get("activation_slice_projection_ready")),
        "projection_match_ratio": _safe_float(bf6_summary.get("projection_match_ratio")),
        "product_handoff_count": int(sum(1 for row in handoff_rows if row["handoff_lane"] == "product_acceptance")),
        "forecast_handoff_count": int(sum(1 for row in handoff_rows if row["handoff_lane"] == "forecast_validation")),
        "collector_handoff_count": int(sum(1 for row in handoff_rows if row["handoff_lane"] == "collector_followup")),
        "recommended_next_step": "product_acceptance_common_state_aware_display_modifier_v1",
    }

    close_out_assessment = {
        "close_out_state": "bridge_first_closed_product_and_forecast_handoff_ready",
        "main_call": "BF1~BF6 are implemented; next leverage is product acceptance common state-aware display wiring, not broad raw addition",
        "raw_addition_call": _coerce_text(sf6_assessment.get("raw_addition_call")) or "defer_broad_raw_addition",
        "collector_call": _coerce_text(sf6_assessment.get("collector_call")) or "only_targeted_order_book_fix_if_still_needed",
        "projection_call": (
            "detail_to_csv_projection_ready"
            if _coerce_text(bf6_assessment.get("projection_state")) == "detail_to_csv_projection_ready"
            else _coerce_text(bf6_assessment.get("projection_state"))
        ),
        "product_acceptance_call": "reuse BF bridges in all-symbol common display modifier instead of per-symbol ad hoc state wiring",
        "forecast_followup_call": "rerun SF3/SF4 after fresh BF5/BF6 rows accumulate",
        "recommended_next_step": "product_acceptance_common_state_aware_display_modifier_v1",
    }

    return {
        "report_version": REPORT_VERSION,
        "generated_at": current_now.isoformat(timespec="seconds"),
        "report_kind": "bridge_first_bf7_close_out_handoff",
        "sf6_report_path": str(sf6_report_path),
        "bf6_report_path": str(bf6_report_path),
        "close_out_summary": close_out_summary,
        "close_out_assessment": close_out_assessment,
        "bridge_inventory_rows": bridge_rows,
        "handoff_rows": handoff_rows,
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("close_out_summary", {}) or {})
    assessment = dict(report.get("close_out_assessment", {}) or {})
    bridge_rows = list(report.get("bridge_inventory_rows", []) or [])
    handoff_rows = list(report.get("handoff_rows", []) or [])
    lines = [
        "# BF7 Close-Out and Handoff",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- close_out_state: `{assessment.get('close_out_state', '')}`",
        f"- main_call: `{assessment.get('main_call', '')}`",
        f"- recommended_next_step: `{summary.get('recommended_next_step', '')}`",
        "",
        "## Summary",
        "",
        f"- implemented_bridge_count: `{summary.get('implemented_bridge_count', 0)}`",
        f"- projection_match_ratio: `{summary.get('projection_match_ratio', 0.0)}`",
        f"- analysis_projection_ready: `{summary.get('analysis_projection_ready', False)}`",
        "",
        "## Bridge Inventory",
        "",
        "| bridge | status | target_area | output_surface | handoff_role |",
        "|---|---|---|---|---|",
    ]
    for row in bridge_rows:
        lines.append(
            "| {bridge_key} | {status} | {target_area} | {output_surface} | {handoff_role} |".format(
                **{k: _coerce_text(v) for k, v in row.items()}
            )
        )
    lines.extend(
        [
            "",
            "## Handoff Rows",
            "",
            "| lane | next_action | priority | why |",
            "|---|---|---|---|",
        ]
    )
    for row in handoff_rows:
        lines.append(
            "| {handoff_lane} | {next_action_key} | {priority} | {why} |".format(
                **{k: _coerce_text(v) for k, v in row.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for row in list(report.get("bridge_inventory_rows", []) or []):
        rows.append(
            {
                "row_type": "bridge_inventory",
                "bridge_key": row.get("bridge_key", ""),
                "status": row.get("status", ""),
                "target_area": row.get("target_area", ""),
                "output_surface": row.get("output_surface", ""),
                "handoff_lane": "",
                "next_action_key": "",
                "priority": "",
                "why": row.get("handoff_role", ""),
                "evidence": row.get("evidence", ""),
            }
        )
    for row in list(report.get("handoff_rows", []) or []):
        rows.append(
            {
                "row_type": "handoff",
                "bridge_key": "",
                "status": "",
                "target_area": "",
                "output_surface": "",
                "handoff_lane": row.get("handoff_lane", ""),
                "next_action_key": row.get("next_action_key", ""),
                "priority": row.get("priority", ""),
                "why": row.get("why", ""),
                "evidence": row.get("evidence", ""),
            }
        )
    fieldnames = [
        "row_type",
        "bridge_key",
        "status",
        "target_area",
        "output_surface",
        "handoff_lane",
        "next_action_key",
        "priority",
        "why",
        "evidence",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_bridge_first_close_out_handoff_report(
    *,
    sf6_report_path: Path = DEFAULT_SF6_REPORT,
    bf6_report_path: Path = DEFAULT_BF6_REPORT,
    output_dir: Path = OUT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_bridge_first_close_out_handoff_report(
        sf6_report_path=sf6_report_path,
        bf6_report_path=bf6_report_path,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "bridge_first_bf7_close_out_latest.json"
    latest_csv = output_dir / "bridge_first_bf7_close_out_latest.csv"
    latest_md = output_dir / "bridge_first_bf7_close_out_latest.md"
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
    parser = argparse.ArgumentParser(description="Build BF7 close-out and handoff report.")
    parser.add_argument("--sf6-report-path", type=Path, default=DEFAULT_SF6_REPORT)
    parser.add_argument("--bf6-report-path", type=Path, default=DEFAULT_BF6_REPORT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    result = write_bridge_first_close_out_handoff_report(
        sf6_report_path=args.sf6_report_path,
        bf6_report_path=args.bf6_report_path,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
