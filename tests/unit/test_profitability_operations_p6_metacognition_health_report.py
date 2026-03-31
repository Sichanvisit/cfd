import json
import importlib.util
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p6_metacognition_health_report.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p6_metacognition_health_report", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_p6_health_report_builds_symbol_health_drift_and_sizing(tmp_path):
    p3_path = tmp_path / "p3.json"
    p4_path = tmp_path / "p4.json"
    p5_path = tmp_path / "p5.json"

    _write_json(
        p3_path,
        {
            "symbol_alert_summary": [
                {
                    "symbol": "XAUUSD",
                    "active_alert_count": 5,
                    "critical_count": 1,
                    "high_count": 2,
                    "medium_count": 2,
                    "top_alert_type": "fast_adverse_close_alert",
                },
                {
                    "symbol": "BTCUSD",
                    "active_alert_count": 1,
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 1,
                    "top_alert_type": "blocked_pressure_alert",
                },
            ],
            "active_alerts": [],
        },
    )
    _write_json(
        p4_path,
        {
            "overall_delta_summary": {
                "active_alert_delta": 8,
            },
            "p3_alert_type_deltas": [
                {"alert_type": "fast_adverse_close_alert", "delta": 3},
                {"alert_type": "blocked_pressure_alert", "delta": 1},
            ],
            "symbol_alert_deltas": [
                {
                    "symbol": "XAUUSD",
                    "active_alert_delta": 4,
                    "critical_delta": 1,
                    "high_delta": 1,
                },
                {
                    "symbol": "BTCUSD",
                    "active_alert_delta": -1,
                    "critical_delta": 0,
                    "high_delta": 0,
                },
            ],
            "worsening_signal_summary": [],
            "improving_signal_summary": [],
        },
    )
    _write_json(
        p5_path,
        {
            "worst_scene_candidates": [
                {
                    "symbol": "XAUUSD",
                    "setup_key": "legacy_trade_without_setup_id::BUY::balanced",
                    "candidate_type": "entry_exit_timing_review",
                    "worst_score": 700.0,
                    "information_gap_flag": False,
                },
                {
                    "symbol": "XAUUSD",
                    "setup_key": "legacy_trade_without_setup_id::SELL::balanced",
                    "candidate_type": "legacy_bucket_identity_restore",
                    "worst_score": 500.0,
                    "information_gap_flag": True,
                },
            ],
            "strength_scene_candidates": [
                {
                    "symbol": "BTCUSD",
                    "setup_key": "range_lower_reversal_buy",
                    "strength_score": 120.0,
                }
            ],
            "tuning_candidate_queue": [
                {"candidate_type": "legacy_bucket_identity_restore"},
                {"candidate_type": "entry_exit_timing_review"},
            ],
        },
    )

    report = module.build_profitability_operations_p6_metacognition_health_report(
        p3_anomaly_path=p3_path,
        p4_compare_path=p4_path,
        p5_casebook_path=p5_path,
        now=datetime.fromisoformat("2026-03-30T20:00:00"),
    )

    symbol_rows = {row["symbol"]: row for row in report["symbol_health_summary"]}
    setup_rows = {row["setup_key"]: row for row in report["archetype_health_summary"]}
    sizing_rows = {row["symbol"]: row for row in report["sizing_overlay_recommendations"]}

    assert report["report_version"] == module.REPORT_VERSION
    assert report["overall_health_summary"]["overall_drift_state"] == "worsening"
    assert symbol_rows["XAUUSD"]["health_state"] == "stressed"
    assert symbol_rows["BTCUSD"]["health_state"] in {"healthy", "watch"}
    assert sizing_rows["XAUUSD"]["size_multiplier"] < sizing_rows["BTCUSD"]["size_multiplier"]
    assert sizing_rows["XAUUSD"]["size_action"] in {"hard_reduce", "reduce"}
    assert "legacy_trade_without_setup_id::BUY::balanced" in setup_rows
    assert report["operator_review_queue"]


def test_write_p6_health_report_writes_outputs(tmp_path):
    p3_path = tmp_path / "p3.json"
    p4_path = tmp_path / "p4.json"
    p5_path = tmp_path / "p5.json"
    output_dir = tmp_path / "analysis"

    _write_json(
        p3_path,
        {
            "symbol_alert_summary": [
                {
                    "symbol": "BTCUSD",
                    "active_alert_count": 0,
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "top_alert_type": "",
                }
            ],
            "active_alerts": [],
        },
    )
    _write_json(
        p4_path,
        {
            "overall_delta_summary": {"active_alert_delta": -2},
            "p3_alert_type_deltas": [],
            "symbol_alert_deltas": [{"symbol": "BTCUSD", "active_alert_delta": -2, "critical_delta": 0, "high_delta": 0}],
            "worsening_signal_summary": [],
            "improving_signal_summary": [],
        },
    )
    _write_json(
        p5_path,
        {
            "worst_scene_candidates": [],
            "strength_scene_candidates": [
                {"symbol": "BTCUSD", "setup_key": "range_lower_reversal_buy", "strength_score": 100.0}
            ],
            "tuning_candidate_queue": [],
        },
    )

    result = module.write_profitability_operations_p6_metacognition_health_report(
        output_dir=output_dir,
        p3_anomaly_path=p3_path,
        p4_compare_path=p4_path,
        p5_casebook_path=p5_path,
        now=datetime.fromisoformat("2026-03-30T20:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["overall_health_summary"]["symbol_count"] == 1
    assert "Profitability / Operations P6 Meta-Cognition / Health / Drift / Sizing" in markdown
