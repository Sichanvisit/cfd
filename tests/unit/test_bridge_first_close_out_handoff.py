import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "bridge_first_close_out_handoff.py"
)
spec = importlib.util.spec_from_file_location("bridge_first_close_out_handoff", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_bridge_first_close_out_handoff_report_summarizes_bf_inventory(tmp_path):
    sf6_path = tmp_path / "sf6.json"
    bf6_path = tmp_path / "bf6.json"

    _write_json(
        sf6_path,
        {
            "close_out_summary": {
                "sf_stage_closed_up_to": "SF5",
                "recommended_next_step": "BF1_act_vs_wait_bias_v1",
            },
            "close_out_assessment": {
                "raw_addition_call": "defer_broad_raw_addition",
                "collector_call": "only_targeted_order_book_fix_if_still_needed",
            },
            "next_action_decision": {
                "active_step_evidence": "p_false_break separation_gap=-0.0147",
            },
        },
    )
    _write_json(
        bf6_path,
        {
            "projection_summary": {
                "projection_match_ratio": 0.9916,
                "matched_projection_rows": 3664,
            },
            "projection_assessment": {
                "projection_state": "detail_to_csv_projection_ready",
                "activation_slice_projection_ready": True,
            },
        },
    )

    report = module.build_bridge_first_close_out_handoff_report(
        sf6_report_path=sf6_path,
        bf6_report_path=bf6_path,
        now=datetime(2026, 3, 31, 14, 0, 0),
    )

    summary = dict(report["close_out_summary"])
    assessment = dict(report["close_out_assessment"])
    bridge_rows = list(report["bridge_inventory_rows"])
    handoff_rows = list(report["handoff_rows"])

    assert summary["bf_stage_closed_up_to"] == "BF6"
    assert summary["implemented_bridge_count"] == 6
    assert summary["recommended_next_step"] == "product_acceptance_common_state_aware_display_modifier_v1"
    assert assessment["projection_call"] == "detail_to_csv_projection_ready"
    assert any(row["bridge_key"] == "BF6_detail_to_csv_activation_projection_v1" for row in bridge_rows)
    assert any(row["next_action_key"] == "common_state_aware_display_modifier_v1" for row in handoff_rows)


def test_write_bridge_first_close_out_handoff_report_emits_latest_files(tmp_path):
    sf6_path = tmp_path / "sf6.json"
    bf6_path = tmp_path / "bf6.json"
    out_dir = tmp_path / "analysis"
    _write_json(
        sf6_path,
        {
            "close_out_summary": {},
            "close_out_assessment": {},
            "next_action_decision": {},
        },
    )
    _write_json(
        bf6_path,
        {
            "projection_summary": {
                "projection_match_ratio": 1.0,
                "matched_projection_rows": 10,
            },
            "projection_assessment": {
                "projection_state": "detail_to_csv_projection_ready",
                "activation_slice_projection_ready": True,
            },
        },
    )

    result = module.write_bridge_first_close_out_handoff_report(
        sf6_report_path=sf6_path,
        bf6_report_path=bf6_path,
        output_dir=out_dir,
        now=datetime(2026, 3, 31, 14, 5, 0),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
