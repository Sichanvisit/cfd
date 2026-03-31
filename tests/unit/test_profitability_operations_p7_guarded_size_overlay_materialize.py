import json
import importlib.util
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p7_guarded_size_overlay_materialize.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p7_guarded_size_overlay_materialize", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_p7_guarded_size_overlay_materialization_filters_size_guarded_apply(tmp_path):
    p7_path = tmp_path / "p7.json"
    _write_json(
        p7_path,
        {
            "report_version": "profitability_operations_p7_counterfactual_selective_adaptation_v1",
            "guarded_application_queue": [
                {
                    "proposal_type": "size_overlay_guarded_apply",
                    "recommendation_state": "guarded_apply_candidate",
                    "symbol": "XAUUSD",
                    "scene_key": "XAUUSD",
                    "setup_key": "legacy_trade_without_setup_id::BUY::balanced",
                    "health_state": "stressed",
                    "size_action": "hard_reduce",
                    "size_multiplier": 0.25,
                    "priority_score": 91.0,
                    "evidence_count": 22,
                    "gate_reason": "passed",
                },
                {
                    "proposal_type": "entry_delay_review",
                    "recommendation_state": "guarded_apply_candidate",
                    "symbol": "BTCUSD",
                },
            ],
        },
    )

    payload = module.build_profitability_operations_p7_guarded_size_overlay_materialization(
        p7_counterfactual_path=p7_path,
        now=datetime.fromisoformat("2026-03-30T22:00:00"),
    )

    assert payload["report_version"] == module.REPORT_VERSION
    assert payload["overall_summary"]["candidate_count"] == 1
    assert payload["guarded_size_overlay_candidates"][0]["symbol"] == "XAUUSD"
    assert payload["guarded_size_overlay_by_symbol"]["XAUUSD"]["target_multiplier"] == 0.25


def test_write_p7_guarded_size_overlay_materialization_outputs_files(tmp_path):
    p7_path = tmp_path / "p7.json"
    out_dir = tmp_path / "analysis"
    _write_json(
        p7_path,
        {
            "report_version": "profitability_operations_p7_counterfactual_selective_adaptation_v1",
            "guarded_application_queue": [
                {
                    "proposal_type": "size_overlay_guarded_apply",
                    "recommendation_state": "guarded_apply_candidate",
                    "symbol": "BTCUSD",
                    "scene_key": "BTCUSD",
                    "setup_key": "legacy_trade_without_setup_id::SELL::balanced",
                    "health_state": "watch",
                    "size_action": "reduce",
                    "size_multiplier": 0.57,
                    "priority_score": 48.0,
                    "evidence_count": 18,
                    "gate_reason": "passed",
                }
            ],
        },
    )

    result = module.write_profitability_operations_p7_guarded_size_overlay_materialization(
        output_dir=out_dir,
        p7_counterfactual_path=p7_path,
        now=datetime.fromisoformat("2026-03-30T22:00:00"),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
