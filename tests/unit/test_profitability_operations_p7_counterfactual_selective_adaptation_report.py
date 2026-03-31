import json
import importlib.util
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p7_counterfactual_selective_adaptation_report.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p7_counterfactual_selective_adaptation_report", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_p7_report_splits_guarded_review_only_and_no_go(tmp_path):
    p4_path = tmp_path / "p4.json"
    p5_path = tmp_path / "p5.json"
    p6_path = tmp_path / "p6.json"

    _write_json(
        p4_path,
        {
            "overall_delta_summary": {"active_alert_delta": 6},
            "p3_alert_type_deltas": [{"alert_type": "blocked_pressure_alert", "delta": 5}],
            "symbol_alert_deltas": [
                {"symbol": "BTCUSD", "active_alert_delta": 2},
                {"symbol": "XAUUSD", "active_alert_delta": 3},
            ],
        },
    )
    _write_json(
        p5_path,
        {
            "worst_scene_candidates": [
                {
                    "scene_key": "BTCUSD / upper_reject_sell / RANGE",
                    "symbol": "BTCUSD",
                    "setup_key": "upper_reject_sell",
                    "regime_key": "RANGE",
                    "candidate_type": "entry_exit_timing_review",
                    "top_alert_type": "fast_adverse_close_alert",
                    "worst_score": 240.0,
                    "closed_trade_count": 64,
                    "active_alert_count": 2,
                    "information_gap_flag": False,
                },
                {
                    "scene_key": "XAUUSD / legacy_trade_without_setup_id::BUY::balanced / NORMAL",
                    "symbol": "XAUUSD",
                    "setup_key": "legacy_trade_without_setup_id::BUY::balanced",
                    "regime_key": "NORMAL",
                    "candidate_type": "legacy_bucket_identity_restore",
                    "top_alert_type": "zero_pnl_information_gap_alert",
                    "worst_score": 320.0,
                    "closed_trade_count": 120,
                    "active_alert_count": 4,
                    "information_gap_flag": True,
                },
            ]
        },
    )
    _write_json(
        p6_path,
        {
            "overall_health_summary": {
                "stressed_symbol_count": 1,
            },
            "symbol_health_summary": [
                {
                    "symbol": "BTCUSD",
                    "health_state": "watch",
                    "size_action": "reduce",
                    "size_multiplier": 0.62,
                    "top_alert_type": "blocked_pressure_alert",
                    "top_setup_key": "upper_reject_sell",
                    "top_candidate_type": "entry_exit_timing_review",
                    "active_alert_count": 12,
                    "active_alert_delta": 2,
                    "worst_scene_count": 2,
                    "information_gap_scene_count": 0,
                    "health_score": 52.0,
                },
                {
                    "symbol": "XAUUSD",
                    "health_state": "stressed",
                    "size_action": "hard_reduce",
                    "size_multiplier": 0.25,
                    "top_alert_type": "zero_pnl_information_gap_alert",
                    "top_setup_key": "legacy_trade_without_setup_id::BUY::balanced",
                    "top_candidate_type": "legacy_bucket_identity_restore",
                    "active_alert_count": 20,
                    "active_alert_delta": 3,
                    "worst_scene_count": 5,
                    "information_gap_scene_count": 2,
                    "health_score": 10.0,
                },
            ],
            "quick_read_summary": {
                "top_drift_signals": [{"alert_type": "blocked_pressure_alert", "delta": 5.0}]
            },
        },
    )

    report = module.build_profitability_operations_p7_counterfactual_selective_adaptation_report(
        p4_compare_path=p4_path,
        p5_casebook_path=p5_path,
        p6_health_path=p6_path,
        now=datetime.fromisoformat("2026-03-30T21:00:00"),
    )

    proposals = report["selective_adaptation_proposal_queue"]
    guarded = [row for row in proposals if row["recommendation_state"] == "guarded_apply_candidate"]
    no_go = [row for row in proposals if row["recommendation_state"] == "no_go"]

    assert report["report_version"] == module.REPORT_VERSION
    assert report["overall_counterfactual_summary"]["proposal_count"] >= 3
    assert guarded
    assert no_go
    assert any(row["proposal_type"] == "entry_delay_review" for row in guarded)
    assert any(row["proposal_type"] == "legacy_identity_restore_first" for row in no_go)
    assert report["safety_gate_summary"]["guarded_apply_count"] >= 1


def test_write_p7_report_writes_outputs(tmp_path):
    p4_path = tmp_path / "p4.json"
    p5_path = tmp_path / "p5.json"
    p6_path = tmp_path / "p6.json"
    output_dir = tmp_path / "analysis"

    _write_json(p4_path, {"overall_delta_summary": {"active_alert_delta": 0}, "p3_alert_type_deltas": [], "symbol_alert_deltas": []})
    _write_json(
        p5_path,
        {
            "worst_scene_candidates": [
                {
                    "scene_key": "BTCUSD / upper_reject_sell / RANGE",
                    "symbol": "BTCUSD",
                    "setup_key": "upper_reject_sell",
                    "regime_key": "RANGE",
                    "candidate_type": "entry_exit_timing_review",
                    "top_alert_type": "fast_adverse_close_alert",
                    "worst_score": 120.0,
                    "closed_trade_count": 50,
                    "active_alert_count": 1,
                    "information_gap_flag": False,
                }
            ]
        },
    )
    _write_json(
        p6_path,
        {
            "overall_health_summary": {"stressed_symbol_count": 0},
            "symbol_health_summary": [
                {
                    "symbol": "BTCUSD",
                    "health_state": "watch",
                    "size_action": "reduce",
                    "size_multiplier": 0.7,
                    "top_alert_type": "fast_adverse_close_alert",
                    "top_setup_key": "upper_reject_sell",
                    "top_candidate_type": "entry_exit_timing_review",
                    "active_alert_count": 8,
                    "active_alert_delta": 0,
                    "worst_scene_count": 1,
                    "information_gap_scene_count": 0,
                    "health_score": 58.0,
                }
            ],
            "quick_read_summary": {"top_drift_signals": []},
        },
    )

    result = module.write_profitability_operations_p7_counterfactual_selective_adaptation_report(
        output_dir=output_dir,
        p4_compare_path=p4_path,
        p5_casebook_path=p5_path,
        p6_health_path=p6_path,
        now=datetime.fromisoformat("2026-03-30T21:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["overall_counterfactual_summary"]["proposal_count"] >= 1
    assert "Profitability / Operations P7 Controlled Counterfactual / Selective Adaptation" in markdown
