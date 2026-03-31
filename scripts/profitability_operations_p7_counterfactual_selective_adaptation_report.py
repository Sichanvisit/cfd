from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "profitability_operations_p7_counterfactual_selective_adaptation_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "profitability_operations"
DEFAULT_P4_COMPARE_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p4_compare_latest.json"
DEFAULT_P5_CASEBOOK_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p5_casebook_latest.json"
DEFAULT_P6_HEALTH_PATH = DEFAULT_OUTPUT_DIR / "profitability_operations_p6_health_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _symbol_health_map(p6_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _coerce_text(row.get("symbol")): row
        for row in p6_payload.get("symbol_health_summary", [])
        if _coerce_text(row.get("symbol"))
    }


def _proposal_priority_rank(state: str) -> int:
    mapping = {
        "guarded_apply_candidate": 2,
        "review_only": 1,
        "no_go": 0,
    }
    return mapping.get(_coerce_text(state), -1)


def _coverage_state(scene_row: dict[str, Any]) -> str:
    if bool(scene_row.get("information_gap_flag")):
        return "coverage_mixed"
    candidate_type = _coerce_text(scene_row.get("candidate_type"))
    if candidate_type == "legacy_bucket_identity_restore":
        return "identity_gap"
    return "in_scope"


def _scene_primary_proposal_type(scene_row: dict[str, Any], symbol_row: dict[str, Any]) -> str:
    candidate_type = _coerce_text(scene_row.get("candidate_type"))
    top_alert_type = _coerce_text(scene_row.get("top_alert_type"))
    size_action = _coerce_text(symbol_row.get("size_action"))

    if candidate_type == "legacy_bucket_identity_restore" or top_alert_type in {
        "zero_pnl_information_gap_alert",
        "legacy_bucket_blind_alert",
    }:
        return "legacy_identity_restore_first"
    if candidate_type == "entry_exit_timing_review" or top_alert_type in {
        "fast_adverse_close_alert",
        "reverse_now_alert",
    }:
        return "entry_delay_review"
    if top_alert_type == "cut_now_concentration_alert":
        return "exit_profile_review"
    if candidate_type == "consumer_gate_pressure_review" or top_alert_type in {
        "blocked_pressure_alert",
        "skip_heavy_alert",
        "wait_heavy_alert",
    }:
        return "counterfactual_hold_for_more_evidence"
    if size_action in {"hard_reduce", "reduce"}:
        return "size_overlay_guarded_apply"
    return "exit_profile_review"


def _max_change_suggestion(proposal_type: str, size_multiplier: float) -> str:
    if proposal_type == "entry_delay_review":
        return "delay_entry_by_1_bar_max"
    if proposal_type == "exit_profile_review":
        return "single_exit_profile_swap_dry_run"
    if proposal_type == "size_overlay_guarded_apply":
        return f"size_step_toward_{round(size_multiplier, 2)}_cap_0.10"
    if proposal_type == "legacy_identity_restore_first":
        return "no_live_change_before_identity_restore"
    return "no_change_collect_more_evidence"


def _gate_scene_proposal(
    proposal_type: str,
    *,
    coverage_state: str,
    evidence_count: int,
    health_state: str,
) -> tuple[str, str]:
    if proposal_type == "legacy_identity_restore_first":
        return "no_go", "identity_first_gate"
    if coverage_state != "in_scope":
        return "review_only", "coverage_gate"
    if evidence_count < 30:
        return "review_only", "low_evidence_gate"
    if proposal_type == "counterfactual_hold_for_more_evidence":
        return "review_only", "hold_for_more_evidence_gate"
    if health_state == "stressed" and proposal_type in {"entry_delay_review", "exit_profile_review"}:
        return "review_only", "stressed_symbol_review_only"
    return "guarded_apply_candidate", "passed"


def _gate_symbol_size_proposal(
    *,
    evidence_count: int,
    health_state: str,
    coverage_pressure: int,
) -> tuple[str, str]:
    if evidence_count < 10:
        return "review_only", "low_evidence_gate"
    if health_state not in {"stressed", "watch"}:
        return "review_only", "healthy_symbol_no_need"
    if coverage_pressure >= 4:
        return "review_only", "coverage_pressure_gate"
    return "guarded_apply_candidate", "passed"


def _build_counterfactual_review_queue(
    p5_payload: dict[str, Any],
    p6_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    symbol_map = _symbol_health_map(p6_payload)
    rows: list[dict[str, Any]] = []
    for scene_row in p5_payload.get("worst_scene_candidates", []):
        symbol = _coerce_text(scene_row.get("symbol"))
        symbol_row = symbol_map.get(symbol, {})
        coverage_state = _coverage_state(scene_row)
        evidence_count = _coerce_int(scene_row.get("closed_trade_count"))
        proposal_type = _scene_primary_proposal_type(scene_row, symbol_row)
        evidence_score = round(
            _clamp(
                evidence_count * 0.5
                + min(40.0, _coerce_float(scene_row.get("worst_score")) / 40.0)
                + _coerce_int(scene_row.get("active_alert_count")) * 5.0,
                0.0,
                100.0,
            ),
            2,
        )
        recommendation_state, gate_reason = _gate_scene_proposal(
            proposal_type,
            coverage_state=coverage_state,
            evidence_count=evidence_count,
            health_state=_coerce_text(symbol_row.get("health_state")),
        )

        rows.append(
            {
                "review_group": "scene_counterfactual",
                "scene_key": _coerce_text(scene_row.get("scene_key")),
                "symbol": symbol,
                "setup_key": _coerce_text(scene_row.get("setup_key")),
                "regime_key": _coerce_text(scene_row.get("regime_key")),
                "proposal_type": proposal_type,
                "coverage_state": coverage_state,
                "health_state": _coerce_text(symbol_row.get("health_state")),
                "size_action": _coerce_text(symbol_row.get("size_action")),
                "size_multiplier": round(_coerce_float(symbol_row.get("size_multiplier")), 2),
                "top_alert_type": _coerce_text(scene_row.get("top_alert_type")),
                "candidate_type": _coerce_text(scene_row.get("candidate_type")),
                "evidence_count": evidence_count,
                "evidence_score": evidence_score,
                "priority_score": round(_coerce_float(scene_row.get("worst_score")), 4),
                "information_gap_flag": bool(scene_row.get("information_gap_flag")),
                "recommendation_state": recommendation_state,
                "gate_reason": gate_reason,
                "max_change_suggestion": _max_change_suggestion(
                    proposal_type,
                    _coerce_float(symbol_row.get("size_multiplier")),
                ),
                "rationale": (
                    f"worst_score={_coerce_float(scene_row.get('worst_score'))}, "
                    f"top_alert={_coerce_text(scene_row.get('top_alert_type'))}, "
                    f"health_state={_coerce_text(symbol_row.get('health_state'))}, "
                    f"size_action={_coerce_text(symbol_row.get('size_action'))}"
                ),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            -_proposal_priority_rank(row["recommendation_state"]),
            -_coerce_float(row["priority_score"]),
            row["scene_key"],
        ),
    )


def _build_symbol_size_proposals(p6_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in p6_payload.get("symbol_health_summary", []):
        size_action = _coerce_text(row.get("size_action"))
        if size_action not in {"hard_reduce", "reduce"}:
            continue
        coverage_pressure = _coerce_int(row.get("information_gap_scene_count"))
        evidence_count = _coerce_int(row.get("active_alert_count")) + _coerce_int(row.get("worst_scene_count"))
        recommendation_state, gate_reason = _gate_symbol_size_proposal(
            evidence_count=evidence_count,
            health_state=_coerce_text(row.get("health_state")),
            coverage_pressure=coverage_pressure,
        )
        rows.append(
            {
                "review_group": "symbol_size_overlay",
                "scene_key": _coerce_text(row.get("symbol")),
                "symbol": _coerce_text(row.get("symbol")),
                "setup_key": _coerce_text(row.get("top_setup_key")),
                "regime_key": "",
                "proposal_type": "size_overlay_guarded_apply",
                "coverage_state": "coverage_mixed" if coverage_pressure > 0 else "in_scope",
                "health_state": _coerce_text(row.get("health_state")),
                "size_action": size_action,
                "size_multiplier": round(_coerce_float(row.get("size_multiplier")), 2),
                "top_alert_type": _coerce_text(row.get("top_alert_type")),
                "candidate_type": _coerce_text(row.get("top_candidate_type")),
                "evidence_count": evidence_count,
                "evidence_score": round(_clamp(evidence_count * 2.0, 0.0, 100.0), 2),
                "priority_score": round(
                    100.0
                    - _coerce_float(row.get("health_score"))
                    + _coerce_int(row.get("active_alert_delta")) * 5.0,
                    4,
                ),
                "information_gap_flag": coverage_pressure > 0,
                "recommendation_state": recommendation_state,
                "gate_reason": gate_reason,
                "max_change_suggestion": _max_change_suggestion(
                    "size_overlay_guarded_apply",
                    _coerce_float(row.get("size_multiplier")),
                ),
                "rationale": (
                    f"health_score={_coerce_float(row.get('health_score'))}, "
                    f"alerts={_coerce_int(row.get('active_alert_count'))}, "
                    f"worst_scenes={_coerce_int(row.get('worst_scene_count'))}, "
                    f"size_action={size_action}"
                ),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            -_proposal_priority_rank(row["recommendation_state"]),
            -_coerce_float(row["priority_score"]),
            row["symbol"],
        ),
    )


def _build_safety_gate_summary(proposal_rows: list[dict[str, Any]]) -> dict[str, Any]:
    gate_counter = Counter(_coerce_text(row.get("gate_reason")) for row in proposal_rows)
    state_counter = Counter(_coerce_text(row.get("recommendation_state")) for row in proposal_rows)
    return {
        "proposal_count": len(proposal_rows),
        "guarded_apply_count": state_counter.get("guarded_apply_candidate", 0),
        "review_only_count": state_counter.get("review_only", 0),
        "no_go_count": state_counter.get("no_go", 0),
        "top_gate_reasons": [
            {"gate_reason": reason, "count": count}
            for reason, count in gate_counter.most_common(5)
            if reason
        ],
    }


def build_profitability_operations_p7_counterfactual_selective_adaptation_report(
    *,
    p4_compare_path: Path = DEFAULT_P4_COMPARE_PATH,
    p5_casebook_path: Path = DEFAULT_P5_CASEBOOK_PATH,
    p6_health_path: Path = DEFAULT_P6_HEALTH_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = now or datetime.now()
    p4_payload = _read_json(p4_compare_path)
    p5_payload = _read_json(p5_casebook_path)
    p6_payload = _read_json(p6_health_path)

    scene_review_rows = _build_counterfactual_review_queue(p5_payload, p6_payload)
    symbol_size_rows = _build_symbol_size_proposals(p6_payload)
    proposal_rows = scene_review_rows + symbol_size_rows
    proposal_rows = sorted(
        proposal_rows,
        key=lambda row: (
            -_proposal_priority_rank(row["recommendation_state"]),
            -_coerce_float(row["priority_score"]),
            row["scene_key"],
        ),
    )
    guarded_rows = [row for row in proposal_rows if _coerce_text(row.get("recommendation_state")) == "guarded_apply_candidate"]
    safety_summary = _build_safety_gate_summary(proposal_rows)
    proposal_counter = Counter(_coerce_text(row.get("proposal_type")) for row in proposal_rows)

    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "p4_compare_path": str(p4_compare_path),
            "p5_casebook_path": str(p5_casebook_path),
            "p6_health_path": str(p6_health_path),
        },
        "overall_counterfactual_summary": {
            "scene_review_count": len(scene_review_rows),
            "proposal_count": len(proposal_rows),
            "guarded_apply_count": safety_summary["guarded_apply_count"],
            "review_only_count": safety_summary["review_only_count"],
            "no_go_count": safety_summary["no_go_count"],
            "stressed_symbol_count": _coerce_int(p6_payload.get("overall_health_summary", {}).get("stressed_symbol_count")),
            "top_proposal_type": proposal_counter.most_common(1)[0][0] if proposal_counter else "",
        },
        "counterfactual_review_queue": scene_review_rows,
        "selective_adaptation_proposal_queue": proposal_rows,
        "safety_gate_summary": safety_summary,
        "guarded_application_queue": guarded_rows,
        "quick_read_summary": {
            "top_guarded_apply_scenes": [row["scene_key"] for row in guarded_rows[:5]],
            "top_review_only_scenes": [
                row["scene_key"]
                for row in proposal_rows
                if _coerce_text(row.get("recommendation_state")) == "review_only"
            ][:5],
            "top_no_go_scenes": [
                row["scene_key"]
                for row in proposal_rows
                if _coerce_text(row.get("recommendation_state")) == "no_go"
            ][:5],
            "top_proposal_types": [
                {"proposal_type": proposal_type, "count": count}
                for proposal_type, count in proposal_counter.most_common(5)
            ],
            "top_drift_signals": p6_payload.get("quick_read_summary", {}).get("top_drift_signals", [])[:3],
        },
    }


def write_profitability_operations_p7_counterfactual_selective_adaptation_report(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    p4_compare_path: Path = DEFAULT_P4_COMPARE_PATH,
    p5_casebook_path: Path = DEFAULT_P5_CASEBOOK_PATH,
    p6_health_path: Path = DEFAULT_P6_HEALTH_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_profitability_operations_p7_counterfactual_selective_adaptation_report(
        p4_compare_path=p4_compare_path,
        p5_casebook_path=p5_casebook_path,
        p6_health_path=p6_health_path,
        now=now,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "profitability_operations_p7_counterfactual_latest.json"
    latest_csv_path = output_dir / "profitability_operations_p7_counterfactual_latest.csv"
    latest_markdown_path = output_dir / "profitability_operations_p7_counterfactual_latest.md"

    latest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_rows = report["selective_adaptation_proposal_queue"]
    fieldnames = list(csv_rows[0].keys()) if csv_rows else [
        "review_group",
        "scene_key",
        "symbol",
        "setup_key",
        "proposal_type",
        "recommendation_state",
        "gate_reason",
        "priority_score",
    ]
    with latest_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    summary = report["overall_counterfactual_summary"]
    markdown_lines = [
        "# Profitability / Operations P7 Controlled Counterfactual / Selective Adaptation",
        "",
        f"- `report_version`: `{report['report_version']}`",
        f"- `generated_at`: `{report['generated_at']}`",
        f"- `proposal_count`: `{summary['proposal_count']}`",
        f"- `guarded_apply_count`: `{summary['guarded_apply_count']}`",
        f"- `review_only_count`: `{summary['review_only_count']}`",
        f"- `no_go_count`: `{summary['no_go_count']}`",
        "",
        "## Top Guarded Apply Scenes",
    ]
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_guarded_apply_scenes"] or ["(none)"])])
    markdown_lines.extend(["", "## Top Review Only Scenes"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_review_only_scenes"] or ["(none)"])])
    markdown_lines.extend(["", "## Top No-Go Scenes"])
    markdown_lines.extend([f"- {item}" for item in (report["quick_read_summary"]["top_no_go_scenes"] or ["(none)"])])
    latest_markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "proposal_count": summary["proposal_count"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = write_profitability_operations_p7_counterfactual_selective_adaptation_report(
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
