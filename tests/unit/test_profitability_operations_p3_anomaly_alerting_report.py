import json
import importlib.util
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p3_anomaly_alerting_report.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p3_anomaly_alerting_report", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_p3_anomaly_report_merges_p1_p2_and_zero_gap_sources(tmp_path):
    p1_path = tmp_path / "p1.json"
    p2_path = tmp_path / "p2.json"
    zero_path = tmp_path / "p2_zero.json"

    _write_json(
        p1_path,
        {
            "report_version": "p1-test",
            "suspicious_clusters": [
                {
                    "cluster_type": "fast_adverse_close_cluster",
                    "severity": "high",
                    "symbol": "XAUUSD",
                    "setup_key": "legacy_trade_without_setup_id::BUY::balanced",
                    "regime_key": "LOW_LIQUIDITY",
                    "side_key": "BUY",
                    "count": 60,
                    "score": 120.0,
                    "reason": "closed trades are quickly turning into losses after entry",
                    "family_key": "XAUUSD / legacy_trade_without_setup_id::BUY::balanced / LOW_LIQUIDITY / BUY",
                }
            ],
        },
    )
    _write_json(
        p2_path,
        {
            "report_version": "p2-test",
            "negative_expectancy_clusters": [
                {
                    "cluster_type": "negative_expectancy_cluster",
                    "severity": "medium",
                    "setup_bucket": "legacy_without_setup",
                    "symbol": "NAS100",
                    "setup_key": "legacy_trade_without_setup_id::BUY::balanced",
                    "regime_key": "LOW_LIQUIDITY",
                    "count": 124,
                    "score": 61.1,
                    "reason": "average pnl is negative across a meaningful number of closed trades",
                },
                {
                    "cluster_type": "zero_pnl_information_gap_cluster",
                    "severity": "medium",
                    "setup_bucket": "explicit_setup",
                    "symbol": "BTCUSD",
                    "setup_key": "range_upper_reversal_sell",
                    "regime_key": "NORMAL",
                    "count": 388,
                    "score": 388.0,
                    "reason": "skip direct cluster, prefer audit source",
                },
            ],
        },
    )
    _write_json(
        zero_path,
        {
            "report_version": "p2-zero-test",
            "suspicious_zero_pnl_buckets": [
                {
                    "pattern": "net_zero_overrides_nonzero_profit",
                    "setup_bucket": "explicit_setup",
                    "symbol": "BTCUSD",
                    "setup_key": "range_upper_reversal_sell",
                    "regime_key": "NORMAL",
                    "zero_pnl_row_count": 387,
                    "missing_setup_ratio": 0.0,
                    "missing_regime_ratio": 0.0,
                    "missing_decision_winner_ratio": 0.0,
                    "profit_abs_sum": 221.86,
                    "avg_abs_profit": 0.5733,
                }
            ],
        },
    )

    report = module.build_profitability_operations_p3_anomaly_alerting_report(
        p1_lifecycle_path=p1_path,
        p2_expectancy_path=p2_path,
        p2_zero_pnl_audit_path=zero_path,
        now=datetime.fromisoformat("2026-03-30T17:00:00"),
    )

    active_alerts = report["active_alerts"]
    alert_types = {row["alert_type"] for row in active_alerts}
    symbol_rows = {row["symbol"]: row for row in report["symbol_alert_summary"]}

    assert report["report_version"] == module.REPORT_VERSION
    assert report["overall_alert_summary"]["active_alert_count"] == 3
    assert "fast_adverse_close_alert" in alert_types
    assert "negative_expectancy_alert" in alert_types
    assert "zero_pnl_information_gap_alert" in alert_types
    assert symbol_rows["XAUUSD"]["critical_count"] == 1
    assert symbol_rows["NAS100"]["high_count"] == 1
    assert report["quick_read_summary"]["top_alerts"]
    assert report["operator_review_queue"]
    assert report["alert_type_summary"]


def test_write_p3_anomaly_report_writes_outputs(tmp_path):
    p1_path = tmp_path / "p1.json"
    p2_path = tmp_path / "p2.json"
    zero_path = tmp_path / "p2_zero.json"
    output_dir = tmp_path / "analysis"

    _write_json(
        p1_path,
        {
            "report_version": "p1-test",
            "suspicious_clusters": [
                {
                    "cluster_type": "blocked_pressure_cluster",
                    "severity": "medium",
                    "symbol": "BTCUSD",
                    "setup_key": "lower_hold_buy",
                    "regime_key": "RANGE",
                    "side_key": "BUY",
                    "count": 220,
                    "score": 220.0,
                    "reason": "blocked lifecycle is concentrated",
                    "family_key": "BTCUSD / lower_hold_buy / RANGE / BUY",
                }
            ],
        },
    )
    _write_json(p2_path, {"report_version": "p2-test", "negative_expectancy_clusters": []})
    _write_json(zero_path, {"report_version": "p2-zero-test", "suspicious_zero_pnl_buckets": []})

    result = module.write_profitability_operations_p3_anomaly_alerting_report(
        output_dir=output_dir,
        p1_lifecycle_path=p1_path,
        p2_expectancy_path=p2_path,
        p2_zero_pnl_audit_path=zero_path,
        now=datetime.fromisoformat("2026-03-30T17:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["overall_alert_summary"]["active_alert_count"] == 1
    assert payload["active_alerts"][0]["alert_type"] == "blocked_pressure_alert"
    assert "Profitability / Operations P3 Anomaly / Alerting" in markdown
