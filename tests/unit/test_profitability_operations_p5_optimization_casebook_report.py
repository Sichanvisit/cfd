import json
import importlib.util
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p5_optimization_casebook_report.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p5_optimization_casebook_report", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_p5_casebook_report_builds_worst_strength_and_tuning_queue(tmp_path):
    p2_path = tmp_path / "p2.json"
    p3_path = tmp_path / "p3.json"
    p4_path = tmp_path / "p4.json"

    _write_json(
        p2_path,
        {
            "symbol_setup_regime_expectancy_summary": [
                {
                    "symbol": "NAS100",
                    "setup_bucket": "legacy_without_setup",
                    "setup_key": "legacy_trade_without_setup_id::BUY::balanced",
                    "regime_key": "LOW_LIQUIDITY",
                    "closed_trade_count": 100,
                    "avg_pnl": -0.5,
                    "profit_factor": 0.8,
                    "nonzero_pnl_ratio": 0.2,
                },
                {
                    "symbol": "BTCUSD",
                    "setup_bucket": "explicit_setup",
                    "setup_key": "range_upper_reversal_sell",
                    "regime_key": "NORMAL",
                    "closed_trade_count": 120,
                    "avg_pnl": 0.0,
                    "profit_factor": 0.0,
                    "nonzero_pnl_ratio": 0.0,
                },
                {
                    "symbol": "XAUUSD",
                    "setup_bucket": "explicit_setup",
                    "setup_key": "range_lower_reversal_buy",
                    "regime_key": "RANGE",
                    "closed_trade_count": 80,
                    "avg_pnl": 0.3,
                    "profit_factor": 1.5,
                    "nonzero_pnl_ratio": 0.4,
                },
            ]
        },
    )
    _write_json(
        p3_path,
        {
            "active_alerts": [
                {
                    "alert_type": "negative_expectancy_alert",
                    "severity": "high",
                    "symbol": "NAS100",
                    "setup_key": "legacy_trade_without_setup_id::BUY::balanced",
                    "regime_key": "LOW_LIQUIDITY",
                    "score": 50.0,
                },
                {
                    "alert_type": "zero_pnl_information_gap_alert",
                    "severity": "high",
                    "symbol": "BTCUSD",
                    "setup_key": "range_upper_reversal_sell",
                    "regime_key": "NORMAL",
                    "score": 200.0,
                },
            ],
            "symbol_alert_summary": [],
        },
    )
    _write_json(
        p4_path,
        {
            "symbol_alert_deltas": [
                {"symbol": "NAS100", "active_alert_delta": 3},
                {"symbol": "BTCUSD", "active_alert_delta": 1},
                {"symbol": "XAUUSD", "active_alert_delta": -2},
            ],
            "p3_alert_type_deltas": [
                {"alert_type": "negative_expectancy_alert", "delta": 2},
                {"alert_type": "zero_pnl_information_gap_alert", "delta": 4},
            ],
        },
    )

    report = module.build_profitability_operations_p5_optimization_casebook_report(
        p2_expectancy_path=p2_path,
        p3_anomaly_path=p3_path,
        p4_compare_path=p4_path,
        now=datetime.fromisoformat("2026-03-30T19:00:00"),
    )

    worst_scenes = {row["scene_key"]: row for row in report["worst_scene_candidates"]}
    strength_scenes = {row["scene_key"]: row for row in report["strength_scene_candidates"]}
    tuning_types = {row["candidate_type"] for row in report["tuning_candidate_queue"]}

    assert report["report_version"] == module.REPORT_VERSION
    assert "NAS100 / legacy_trade_without_setup_id::BUY::balanced / LOW_LIQUIDITY" in worst_scenes
    assert "BTCUSD / range_upper_reversal_sell / NORMAL" in worst_scenes
    assert "XAUUSD / range_lower_reversal_buy / RANGE" in strength_scenes
    assert "legacy_bucket_identity_restore" in tuning_types or "pnl_lineage_attribution_audit" in tuning_types
    assert report["casebook_review_queue"]
    assert report["quick_read_summary"]["top_caution_scenes"]


def test_write_p5_casebook_report_writes_outputs(tmp_path):
    p2_path = tmp_path / "p2.json"
    p3_path = tmp_path / "p3.json"
    p4_path = tmp_path / "p4.json"
    output_dir = tmp_path / "analysis"

    _write_json(
        p2_path,
        {
            "symbol_setup_regime_expectancy_summary": [
                {
                    "symbol": "BTCUSD",
                    "setup_bucket": "explicit_setup",
                    "setup_key": "range_lower_reversal_buy",
                    "regime_key": "RANGE",
                    "closed_trade_count": 80,
                    "avg_pnl": 0.4,
                    "profit_factor": 1.8,
                    "nonzero_pnl_ratio": 0.3,
                }
            ]
        },
    )
    _write_json(p3_path, {"active_alerts": [], "symbol_alert_summary": []})
    _write_json(p4_path, {"symbol_alert_deltas": [], "p3_alert_type_deltas": []})

    result = module.write_profitability_operations_p5_optimization_casebook_report(
        output_dir=output_dir,
        p2_expectancy_path=p2_path,
        p3_anomaly_path=p3_path,
        p4_compare_path=p4_path,
        now=datetime.fromisoformat("2026-03-30T19:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["overall_casebook_summary"]["strength_scene_count"] == 1
    assert "Profitability / Operations P5 Optimization / Casebook" in markdown
