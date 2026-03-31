import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "state_forecast_validation_gap_matrix_bridge_candidate_review.py"
)
spec = importlib.util.spec_from_file_location(
    "state_forecast_validation_gap_matrix_bridge_candidate_review",
    SCRIPT_PATH,
)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_gap_matrix_review_classifies_bridge_and_usage_first(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    sf1_path = out_dir / "sf1.json"
    sf2_path = out_dir / "sf2.json"
    sf3_path = out_dir / "sf3.json"
    sf4_path = out_dir / "sf4.json"

    _write_json(
        sf1_path,
        {
            "coverage_summary": {
                "state_vector_present_ratio": 0.9944,
                "default_heavy_field_count": 5,
            }
        },
    )
    _write_json(
        sf2_path,
        {
            "activation_summary": {
                "order_book_state_active_like_ratio": 0.0003,
                "tick_state_active_like_ratio": 0.8997,
            }
        },
    )
    _write_json(
        sf3_path,
        {
            "usage_summary": {
                "secondary_harvest_direct_use_field_count": 0,
            }
        },
    )
    _write_json(
        sf4_path,
        {
            "value_summary": {
                "decision_row_count": 34775,
            },
            "metric_value_rows": [
                {"metric_name": "p_false_break", "separation_gap": -0.0147, "high_low_rate_gap": -0.0039},
                {"metric_name": "p_continue_favor", "separation_gap": 0.0475},
                {"metric_name": "p_fail_now", "separation_gap": 0.0055},
            ],
            "regime_slice_rows": [
                {"metric_name": "p_continue_favor", "slice_key": "RANGE", "separation_gap": 0.0537},
                {"metric_name": "p_continue_favor", "slice_key": "TREND", "separation_gap": -0.0216},
            ],
            "activation_slice_rows": [],
            "harvest_section_value_rows": [
                {"branch_role": "transition_branch", "harvest_section": "secondary_harvest", "section_used_ratio": 0.0}
            ],
        },
    )

    report = module.build_state_forecast_validation_gap_matrix_bridge_candidate_report(
        sf1_report_path=sf1_path,
        sf2_report_path=sf2_path,
        sf3_report_path=sf3_path,
        sf4_report_path=sf4_path,
        now=datetime.fromisoformat("2026-03-31T13:00:00"),
    )

    summary = report["gap_summary"]
    assessment = report["gap_assessment"]
    gap_rows = {row["gap_key"]: row for row in report["gap_matrix_rows"]}
    bridge_rows = {row["candidate_name"]: row for row in report["bridge_candidate_rows"]}

    assert summary["gap_row_count"] == 7
    assert assessment["primary_gap_family"] == "bridge_and_usage"
    assert assessment["raw_addition_priority"] == "low"
    assert gap_rows["state_raw_surface"]["severity"] == "healthy"
    assert gap_rows["secondary_harvest_usage_gap"]["severity"] == "critical"
    assert gap_rows["transition_false_break_value_gap"]["gap_type"] == "value"
    assert bridge_rows["act_vs_wait_bias_v1"]["priority"] == "P1"
    assert bridge_rows["advanced_input_reliability_v1"]["priority"] == "P2"


def test_write_gap_matrix_review_outputs(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    sf1_path = out_dir / "sf1.json"
    sf2_path = out_dir / "sf2.json"
    sf3_path = out_dir / "sf3.json"
    sf4_path = out_dir / "sf4.json"

    for path, payload in [
        (sf1_path, {"coverage_summary": {"state_vector_present_ratio": 1.0, "default_heavy_field_count": 0}}),
        (sf2_path, {"activation_summary": {"order_book_state_active_like_ratio": 0.1, "tick_state_active_like_ratio": 0.8}}),
        (sf3_path, {"usage_summary": {"secondary_harvest_direct_use_field_count": 1}}),
        (
            sf4_path,
            {
                "value_summary": {"decision_row_count": 100},
                "metric_value_rows": [
                    {"metric_name": "p_false_break", "separation_gap": 0.1, "high_low_rate_gap": 0.2},
                    {"metric_name": "p_continue_favor", "separation_gap": 0.12},
                    {"metric_name": "p_fail_now", "separation_gap": 0.09},
                ],
                "regime_slice_rows": [
                    {"metric_name": "p_continue_favor", "slice_key": "RANGE", "separation_gap": 0.2},
                    {"metric_name": "p_continue_favor", "slice_key": "TREND", "separation_gap": 0.15},
                ],
                "activation_slice_rows": [{"metric_name": "p_buy_confirm", "slice_key": "ADVANCED_PARTIAL"}],
                "harvest_section_value_rows": [
                    {"branch_role": "transition_branch", "harvest_section": "secondary_harvest", "section_used_ratio": 0.6}
                ],
            },
        ),
    ]:
        _write_json(path, payload)

    result = module.write_state_forecast_validation_gap_matrix_bridge_candidate_report(
        sf1_report_path=sf1_path,
        sf2_report_path=sf2_path,
        sf3_report_path=sf3_path,
        sf4_report_path=sf4_path,
        output_dir=out_dir,
        now=datetime.fromisoformat("2026-03-31T13:30:00"),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
