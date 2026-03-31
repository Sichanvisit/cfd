import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p2_expectancy_attribution_report.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p2_expectancy_attribution_report", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_build_p2_expectancy_report_splits_buckets_and_builds_attribution(tmp_path):
    closed_trades_path = tmp_path / "trade_closed_history.csv"
    _write_csv(
        closed_trades_path,
        [
            {
                "symbol": "XAUUSD",
                "direction": "SELL",
                "entry_setup_id": "range_upper_reversal_sell",
                "regime_at_entry": "RANGE",
                "entry_stage": "balanced",
                "exit_policy_stage": "short",
                "exit_policy_profile": "conservative",
                "decision_winner": "cut_now",
                "decision_reason": "cut_now_best",
                "exit_wait_state": "CUT_IMMEDIATE",
                "profit": "-10.0",
                "open_ts": "100",
                "close_ts": "220",
            },
            {
                "symbol": "XAUUSD",
                "direction": "SELL",
                "entry_setup_id": "range_upper_reversal_sell",
                "regime_at_entry": "RANGE",
                "entry_stage": "balanced",
                "exit_policy_stage": "short",
                "exit_policy_profile": "conservative",
                "decision_winner": "exit_now",
                "decision_reason": "exit_now_best",
                "exit_wait_state": "GREEN_CLOSE",
                "profit": "-8.0",
                "open_ts": "200",
                "close_ts": "320",
            },
            {
                "symbol": "XAUUSD",
                "direction": "SELL",
                "entry_setup_id": "range_upper_reversal_sell",
                "regime_at_entry": "RANGE",
                "entry_stage": "balanced",
                "exit_policy_stage": "mid",
                "exit_policy_profile": "neutral",
                "decision_winner": "hold",
                "decision_reason": "hold_best",
                "exit_wait_state": "NONE",
                "profit": "5.0",
                "open_ts": "300",
                "close_ts": "700",
            },
            {
                "symbol": "XAUUSD",
                "direction": "SELL",
                "entry_setup_id": "range_upper_reversal_sell",
                "regime_at_entry": "RANGE",
                "entry_stage": "balanced",
                "exit_policy_stage": "mid",
                "exit_policy_profile": "neutral",
                "decision_winner": "hold",
                "decision_reason": "hold_best",
                "exit_wait_state": "NONE",
                "profit": "-4.0",
                "open_ts": "400",
                "close_ts": "900",
            },
            {
                "symbol": "XAUUSD",
                "direction": "SELL",
                "entry_setup_id": "range_upper_reversal_sell",
                "regime_at_entry": "RANGE",
                "entry_stage": "balanced",
                "exit_policy_stage": "short",
                "exit_policy_profile": "conservative",
                "decision_winner": "cut_now",
                "decision_reason": "cut_now_best",
                "exit_wait_state": "CUT_IMMEDIATE",
                "profit": "-3.0",
                "open_ts": "500",
                "close_ts": "620",
            },
            {
                "symbol": "NAS100",
                "direction": "BUY",
                "entry_setup_id": "",
                "regime_at_entry": "LOW_LIQUIDITY",
                "entry_stage": "balanced",
                "exit_policy_stage": "short",
                "exit_policy_profile": "conservative",
                "decision_winner": "reverse_now",
                "decision_reason": "reverse_now_best",
                "exit_wait_state": "REVERSE_READY",
                "profit": "-6.0",
                "open_ts": "1000",
                "close_ts": "1120",
            },
            {
                "symbol": "NAS100",
                "direction": "BUY",
                "entry_setup_id": "",
                "regime_at_entry": "LOW_LIQUIDITY",
                "entry_stage": "balanced",
                "exit_policy_stage": "short",
                "exit_policy_profile": "conservative",
                "decision_winner": "reverse_now",
                "decision_reason": "reverse_now_best",
                "exit_wait_state": "REVERSE_READY",
                "profit": "-5.0",
                "open_ts": "1100",
                "close_ts": "1210",
            },
            {
                "symbol": "NAS100",
                "direction": "BUY",
                "entry_setup_id": "",
                "regime_at_entry": "LOW_LIQUIDITY",
                "entry_stage": "balanced",
                "exit_policy_stage": "mid",
                "exit_policy_profile": "neutral",
                "decision_winner": "hold",
                "decision_reason": "hold_best",
                "exit_wait_state": "NONE",
                "profit": "-4.0",
                "open_ts": "1200",
                "close_ts": "1800",
            },
            {
                "symbol": "NAS100",
                "direction": "BUY",
                "entry_setup_id": "",
                "regime_at_entry": "LOW_LIQUIDITY",
                "entry_stage": "balanced",
                "exit_policy_stage": "mid",
                "exit_policy_profile": "neutral",
                "decision_winner": "exit_now",
                "decision_reason": "exit_now_best",
                "exit_wait_state": "GREEN_CLOSE",
                "profit": "-2.0",
                "open_ts": "1300",
                "close_ts": "1500",
            },
            {
                "symbol": "NAS100",
                "direction": "BUY",
                "entry_setup_id": "",
                "regime_at_entry": "LOW_LIQUIDITY",
                "entry_stage": "balanced",
                "exit_policy_stage": "mid",
                "exit_policy_profile": "neutral",
                "decision_winner": "wait_be",
                "decision_reason": "wait_be_recovery",
                "exit_wait_state": "RECOVERY_BE",
                "profit": "1.0",
                "open_ts": "1400",
                "close_ts": "2100",
            },
            {
                "symbol": "BTCUSD",
                "direction": "BUY",
                "entry_setup_id": "snapshot_restored_auto",
                "regime_at_entry": "RANGE",
                "entry_stage": "balanced",
                "exit_policy_stage": "auto",
                "exit_policy_profile": "neutral",
                "decision_winner": "",
                "decision_reason": "",
                "exit_wait_state": "",
                "profit": "2.0",
                "open_ts": "2000",
                "close_ts": "2600",
            },
        ],
    )

    report = module.build_profitability_operations_p2_expectancy_attribution_report(
        closed_trades_path=closed_trades_path,
        tail=100,
        now=datetime.fromisoformat("2026-03-30T14:00:00"),
    )

    setup_rows = {
        (row.get("setup_bucket"), row.get("setup_key")): row
        for row in report["setup_expectancy_summary"]
    }
    winner_rows = {row.get("decision_winner"): row for row in report["decision_winner_attribution_summary"]}
    bucket_rows = {row.get("setup_bucket"): row for row in report["bucket_expectancy_summary"]}
    direction_rows = {row.get("direction"): row for row in report["direction_expectancy_summary"]}
    clusters = {cluster["cluster_type"] for cluster in report["negative_expectancy_clusters"]}
    cluster_type_rows = {row["cluster_type"]: row for row in report["negative_expectancy_cluster_type_summary"]}

    explicit_row = setup_rows[("explicit_setup", "range_upper_reversal_sell")]
    legacy_row = setup_rows[("legacy_without_setup", "legacy_trade_without_setup_id::BUY::balanced")]

    assert report["report_version"] == module.REPORT_VERSION
    assert report["overall_expectancy_summary"]["closed_trade_count"] == 11
    assert report["attribution_readiness_summary"]["explicit_setup_rows"] == 5
    assert report["attribution_readiness_summary"]["legacy_without_setup_rows"] == 5
    assert report["attribution_readiness_summary"]["snapshot_restored_auto_rows"] == 1
    assert explicit_row["closed_trade_count"] == 5
    assert explicit_row["forced_exit_count"] == 3
    assert round(explicit_row["avg_pnl"], 4) == -4.0
    assert legacy_row["closed_trade_count"] == 5
    assert legacy_row["reverse_count"] == 2
    assert round(legacy_row["avg_pnl"], 4) == -3.2
    assert winner_rows["cut_now"]["closed_trade_count"] == 2
    assert winner_rows["reverse_now"]["closed_trade_count"] == 2
    assert bucket_rows["snapshot_restored_auto"]["closed_trade_count"] == 1
    assert direction_rows["SELL"]["closed_trade_count"] == 5
    assert "negative_expectancy_cluster" in clusters
    assert "forced_exit_drag_cluster" in clusters
    assert "legacy_bucket_blind_cluster" in clusters
    assert cluster_type_rows["negative_expectancy_cluster"]["count"] >= 1
    assert report["quick_read_summary"]["top_negative_concerns"]
    assert len(report["quick_read_summary"]["next_review_queue"]) == len(set(report["quick_read_summary"]["next_review_queue"]))


def test_write_p2_expectancy_report_writes_outputs(tmp_path):
    closed_trades_path = tmp_path / "trade_closed_history.csv"
    output_dir = tmp_path / "analysis"

    _write_csv(
        closed_trades_path,
        [
            {
                "symbol": "BTCUSD",
                "direction": "BUY",
                "entry_setup_id": "range_lower_reversal_buy",
                "regime_at_entry": "RANGE",
                "entry_stage": "balanced",
                "exit_policy_stage": "mid",
                "exit_policy_profile": "neutral",
                "decision_winner": "hold",
                "decision_reason": "hold_best",
                "exit_wait_state": "NONE",
                "profit": "5.0",
                "open_ts": "100",
                "close_ts": "300",
            }
        ],
    )

    result = module.write_profitability_operations_p2_expectancy_attribution_report(
        output_dir=output_dir,
        closed_trades_path=closed_trades_path,
        tail=100,
        now=datetime.fromisoformat("2026-03-30T14:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["overall_expectancy_summary"]["closed_trade_count"] == 1
    assert payload["setup_expectancy_summary"][0]["avg_pnl"] == 5.0
    assert payload["direction_expectancy_summary"][0]["direction"] == "BUY"
    assert "Profitability / Operations P2 Expectancy / Attribution" in markdown
    assert "Cluster Type Summary" in markdown
