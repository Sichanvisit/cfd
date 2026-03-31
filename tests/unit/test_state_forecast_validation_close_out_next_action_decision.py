import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "state_forecast_validation_close_out_next_action_decision.py"
)
spec = importlib.util.spec_from_file_location(
    "state_forecast_validation_close_out_next_action_decision",
    SCRIPT_PATH,
)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_close_out_report_selects_act_vs_wait_as_single_active_step(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    sf5_path = out_dir / "sf5.json"

    _write_json(
        sf5_path,
        {
            "gap_summary": {
                "gap_row_count": 7,
                "bridge_candidate_count": 6,
            },
            "gap_assessment": {
                "raw_addition_priority": "low",
                "collector_fix_priority": "targeted_order_book_only",
                "forecast_refinement_priority": "transition_wait_and_management_hold",
            },
            "gap_matrix_rows": [
                {"gap_key": "secondary_harvest_usage_gap", "severity": "critical", "evidence_a": 0, "evidence_b": 0.0},
                {"gap_key": "transition_false_break_value_gap", "severity": "high", "evidence_a": -0.0147, "evidence_b": -0.0039},
                {"gap_key": "management_value_gap", "severity": "high", "evidence_a": 0.0475, "evidence_b": 0.0055},
                {"gap_key": "activation_slice_projection_gap", "severity": "medium", "evidence_a": 0, "evidence_b": 34775},
            ],
            "bridge_candidate_rows": [
                {
                    "candidate_name": "management_hold_reward_hint_v1",
                    "priority": "P1",
                    "target_area": "trade_management_forecast + hold/exit review",
                    "source_layers": "belief + barrier + trend/range state",
                    "candidate_outputs": "hold_reward_hint,recoverability_hint,continuation_tailwind",
                    "motivation": "continue-favor is only weakly separating profitable trades",
                    "why_now": "p_continue_favor separation_gap=0.0475",
                },
                {
                    "candidate_name": "act_vs_wait_bias_v1",
                    "priority": "P1",
                    "target_area": "transition_forecast + product_acceptance_chart_wait",
                    "source_layers": "state + evidence + belief + barrier",
                    "candidate_outputs": "act_vs_wait_bias,false_break_risk,awareness_keep_allowed",
                    "motivation": "p_false_break is flat, so WAIT/observe discrimination needs an explicit bridge",
                    "why_now": "p_false_break separation_gap=-0.0147",
                },
                {
                    "candidate_name": "management_fast_cut_risk_v1",
                    "priority": "P1",
                    "target_area": "trade_management_forecast + cut_now/exit caution",
                    "source_layers": "state + barrier + event/friction",
                    "candidate_outputs": "fast_cut_risk,collision_risk,event_caution",
                    "motivation": "fail-now remains flat, so early-loss risk needs a more explicit bridge",
                    "why_now": "p_fail_now separation_gap=0.0055",
                },
                {
                    "candidate_name": "trend_continuation_maturity_v1",
                    "priority": "P2",
                    "target_area": "management trend slice",
                    "source_layers": "state + belief persistence + exhaustion",
                    "candidate_outputs": "continuation_maturity,exhaustion_pressure,trend_hold_confidence",
                    "motivation": "trend management slice is weaker than range and likely misses maturity/exhaustion context",
                    "why_now": "trend_continue separation_gap=-0.0216",
                },
            ],
        },
    )

    report = module.build_state_forecast_validation_close_out_next_action_decision_report(
        sf5_report_path=sf5_path,
        now=datetime.fromisoformat("2026-03-31T14:00:00"),
    )

    summary = report["close_out_summary"]
    assessment = report["close_out_assessment"]
    decision = report["next_action_decision"]

    assert summary["single_active_step"] == "act_vs_wait_bias_v1"
    assert summary["recommended_next_step"] == "BF1_act_vs_wait_bias_v1"
    assert assessment["raw_addition_call"] == "defer_broad_raw_addition"
    assert decision["active_step_candidate"] == "act_vs_wait_bias_v1"
    assert "false-break" in decision["why_this_first"]


def test_write_close_out_report_outputs_files(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    sf5_path = out_dir / "sf5.json"

    _write_json(
        sf5_path,
        {
            "gap_summary": {
                "gap_row_count": 7,
                "bridge_candidate_count": 6,
            },
            "gap_assessment": {
                "raw_addition_priority": "low",
                "collector_fix_priority": "targeted_order_book_only",
                "forecast_refinement_priority": "transition_wait_and_management_hold",
            },
            "gap_matrix_rows": [
                {"gap_key": "secondary_harvest_usage_gap", "severity": "critical", "evidence_a": 0, "evidence_b": 0.0},
                {"gap_key": "transition_false_break_value_gap", "severity": "high", "evidence_a": -0.0147, "evidence_b": -0.0039},
                {"gap_key": "management_value_gap", "severity": "high", "evidence_a": 0.0475, "evidence_b": 0.0055},
                {"gap_key": "activation_slice_projection_gap", "severity": "medium", "evidence_a": 0, "evidence_b": 34775},
            ],
            "bridge_candidate_rows": [
                {
                    "candidate_name": "act_vs_wait_bias_v1",
                    "priority": "P1",
                    "target_area": "transition_forecast + product_acceptance_chart_wait",
                    "source_layers": "state + evidence + belief + barrier",
                    "candidate_outputs": "act_vs_wait_bias,false_break_risk,awareness_keep_allowed",
                    "motivation": "p_false_break is flat, so WAIT/observe discrimination needs an explicit bridge",
                    "why_now": "p_false_break separation_gap=-0.0147",
                },
                {
                    "candidate_name": "management_hold_reward_hint_v1",
                    "priority": "P1",
                    "target_area": "trade_management_forecast + hold/exit review",
                    "source_layers": "belief + barrier + trend/range state",
                    "candidate_outputs": "hold_reward_hint,recoverability_hint,continuation_tailwind",
                    "motivation": "continue-favor is only weakly separating profitable trades",
                    "why_now": "p_continue_favor separation_gap=0.0475",
                },
                {
                    "candidate_name": "management_fast_cut_risk_v1",
                    "priority": "P1",
                    "target_area": "trade_management_forecast + cut_now/exit caution",
                    "source_layers": "state + barrier + event/friction",
                    "candidate_outputs": "fast_cut_risk,collision_risk,event_caution",
                    "motivation": "fail-now remains flat, so early-loss risk needs a more explicit bridge",
                    "why_now": "p_fail_now separation_gap=0.0055",
                },
                {
                    "candidate_name": "advanced_input_reliability_v1",
                    "priority": "P2",
                    "target_area": "secondary_harvest projection + product display modifier",
                    "source_layers": "advanced activation + collector availability",
                    "candidate_outputs": "advanced_reliability,order_book_reliable,event_context_reliable",
                    "motivation": "tick/event are alive but order_book is effectively unavailable, so raw secondary use needs a reliability bridge first",
                    "why_now": "order_book_active=0.0003, secondary_direct_use=0",
                },
                {
                    "candidate_name": "trend_continuation_maturity_v1",
                    "priority": "P2",
                    "target_area": "management trend slice",
                    "source_layers": "state + belief persistence + exhaustion",
                    "candidate_outputs": "continuation_maturity,exhaustion_pressure,trend_hold_confidence",
                    "motivation": "trend management slice is weaker than range and likely misses maturity/exhaustion context",
                    "why_now": "trend_continue separation_gap=-0.0216",
                },
                {
                    "candidate_name": "detail_to_csv_activation_projection_v1",
                    "priority": "P3",
                    "target_area": "state_forecast_validation analysis surface",
                    "source_layers": "detail usage trace + csv value rows",
                    "candidate_outputs": "activation_slice_projection,section_value_projection",
                    "motivation": "full CSV preserves value coverage but strips activation/usage trace, so SF audits need a projection bridge",
                    "why_now": "activation slice unavailable in SF4 CSV surface",
                },
            ],
        },
    )

    result = module.write_state_forecast_validation_close_out_next_action_decision_report(
        sf5_report_path=sf5_path,
        output_dir=out_dir,
        now=datetime.fromisoformat("2026-03-31T14:30:00"),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
