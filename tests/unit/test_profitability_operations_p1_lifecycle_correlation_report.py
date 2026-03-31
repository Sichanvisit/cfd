import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p1_lifecycle_correlation_report.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p1_lifecycle_correlation_report", SCRIPT_PATH)
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


def test_build_p1_lifecycle_report_applies_coverage_split_and_emits_clusters(tmp_path):
    decisions_path = tmp_path / "entry_decisions.csv"
    decision_detail_path = tmp_path / "entry_decisions.detail.jsonl"
    open_trades_path = tmp_path / "trade_history.csv"
    closed_trades_path = tmp_path / "trade_closed_history.csv"

    _write_csv(
        decisions_path,
        [
            {
                "time": "2026-03-30T01:00:00",
                "symbol": "XAUUSD",
                "outcome": "skipped",
                "consumer_setup_id": "range_upper_reversal_sell",
                "preflight_regime": "RANGE",
                "observe_reason": "upper_reject_observe",
                "blocked_by": "energy_soft_block",
                "action_none_reason": "execution_soft_blocked",
                "consumer_check_stage": "BLOCKED",
                "r0_non_action_family": "decision_log_coverage_gap",
            },
            {
                "time": "2026-03-30T01:01:00",
                "symbol": "XAUUSD",
                "outcome": "skipped",
                "consumer_setup_id": "range_upper_reversal_sell",
                "preflight_regime": "RANGE",
                "observe_reason": "upper_reject_observe",
                "blocked_by": "energy_soft_block",
                "action_none_reason": "execution_soft_blocked",
                "consumer_check_stage": "BLOCKED",
                "r0_non_action_family": "decision_log_coverage_gap",
            },
            {
                "time": "2026-03-30T01:02:00",
                "symbol": "XAUUSD",
                "outcome": "skipped",
                "consumer_setup_id": "range_upper_reversal_sell",
                "preflight_regime": "RANGE",
                "observe_reason": "upper_reject_observe",
                "blocked_by": "energy_soft_block",
                "action_none_reason": "execution_soft_blocked",
                "consumer_check_stage": "BLOCKED",
                "r0_non_action_family": "decision_log_coverage_gap",
            },
            {
                "time": "2026-03-30T01:03:00",
                "symbol": "BTCUSD",
                "outcome": "wait",
                "consumer_archetype_id": "lower_hold_buy",
                "preflight_regime": "RANGE",
                "observe_reason": "lower_rebound_probe_observe",
                "action_none_reason": "probe_not_promoted",
                "observe_side": "BUY",
                "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1774811700.0|hint=BOTH",
            },
            {
                "time": "2026-03-30T01:04:00",
                "symbol": "NAS100",
                "outcome": "entered",
                "consumer_archetype_id": "trend_pullback_buy",
                "preflight_regime": "EXPANSION",
                "observe_reason": "trend_pullback_confirm",
                "observe_side": "BUY",
            },
        ],
    )
    decision_detail_path.write_text("", encoding="utf-8")
    _write_csv(
        open_trades_path,
        [
            {
                "symbol": "BTCUSD",
                "direction": "BUY",
                "entry_setup_id": "lower_hold_buy",
                "regime_at_entry": "RANGE",
                "open_time": "2026-03-30 01:03:30",
                "open_ts": "1774803810",
            }
        ],
    )
    _write_csv(
        closed_trades_path,
        [
            {
                "symbol": "XAUUSD",
                "direction": "SELL",
                "entry_setup_id": "range_upper_reversal_sell",
                "regime_at_entry": "RANGE",
                "open_time": "2026-03-30 00:50:00",
                "close_time": "2026-03-30 00:51:30",
                "open_ts": "1774803000",
                "close_ts": "1774803090",
                "profit": "-12.5",
                "decision_winner": "cut_now",
                "decision_reason": "cut_now_best",
                "exit_wait_state": "CUT_IMMEDIATE",
            },
            {
                "symbol": "XAUUSD",
                "direction": "SELL",
                "entry_setup_id": "range_upper_reversal_sell",
                "regime_at_entry": "RANGE",
                "open_time": "2026-03-30 00:55:00",
                "close_time": "2026-03-30 00:56:00",
                "open_ts": "1774803300",
                "close_ts": "1774803360",
                "profit": "-7.0",
                "decision_winner": "cut_now",
                "decision_reason": "cut_now_best",
                "exit_wait_state": "CUT_IMMEDIATE",
            },
            {
                "symbol": "BTCUSD",
                "direction": "BUY",
                "entry_setup_id": "lower_hold_buy",
                "regime_at_entry": "RANGE",
                "open_time": "2026-03-30 00:40:00",
                "close_time": "2026-03-30 01:10:00",
                "open_ts": "1774802400",
                "close_ts": "1774804200",
                "profit": "15.0",
                "decision_winner": "hold",
                "decision_reason": "hold_best",
                "exit_wait_state": "NONE",
            },
        ],
    )

    report = module.build_profitability_operations_p1_lifecycle_correlation_report(
        decisions_path=decisions_path,
        decision_detail_path=decision_detail_path,
        open_trades_path=open_trades_path,
        closed_trades_path=closed_trades_path,
        tail=100,
        now=datetime.fromisoformat("2026-03-30T02:00:00"),
    )

    family_rows = {
        (row.get("symbol"), row.get("setup_key"), row.get("regime_key"), row.get("side_key")): row
        for row in report["lifecycle_family_summary"]
    }
    xau_row = family_rows[("XAUUSD", "range_upper_reversal_sell", "RANGE", "SELL")]
    btc_row = family_rows[("BTCUSD", "lower_hold_buy", "RANGE", "BUY")]
    side_rows = {row.get("side_key"): row for row in report["side_summary"]}
    clusters = {cluster["cluster_type"] for cluster in report["suspicious_clusters"]}

    assert report["report_version"] == module.REPORT_VERSION
    assert report["coverage_summary"]["outside_coverage"] == 3
    assert report["coverage_summary"]["coverage_in_scope"] == 1
    assert report["coverage_summary"]["unknown_coverage"] == 1
    assert xau_row["decision_rows"] == 3
    assert xau_row["outside_coverage_decision_rows"] == 3
    assert xau_row["fast_adverse_close_count"] == 2
    assert xau_row["top_decision_winner"] == "cut_now"
    assert btc_row["in_scope_decision_rows"] == 1
    assert btc_row["open_trade_count"] == 1
    assert side_rows["BUY"]["decision_rows"] == 2
    assert "coverage_blind_spot_cluster" in clusters
    assert "fast_adverse_close_cluster" in clusters
    assert "wait_to_forced_exit_cluster" not in clusters
    assert report["quick_read_summary"]["top_concerns"]
    assert report["suspicious_cluster_type_summary"]


def test_write_p1_lifecycle_report_writes_json_csv_and_markdown(tmp_path):
    decisions_path = tmp_path / "entry_decisions.csv"
    decision_detail_path = tmp_path / "entry_decisions.detail.jsonl"
    open_trades_path = tmp_path / "trade_history.csv"
    closed_trades_path = tmp_path / "trade_closed_history.csv"
    output_dir = tmp_path / "analysis"

    _write_csv(
        decisions_path,
        [
            {
                "time": "2026-03-30T01:00:00",
                "symbol": "BTCUSD",
                "outcome": "wait",
                "consumer_archetype_id": "lower_hold_buy",
                "preflight_regime": "RANGE",
                "observe_reason": "lower_rebound_probe_observe",
                "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1774811700.0|hint=BOTH",
            }
        ],
    )
    decision_detail_path.write_text("", encoding="utf-8")
    _write_csv(open_trades_path, [])
    _write_csv(
        closed_trades_path,
        [
            {
                "symbol": "BTCUSD",
                "direction": "BUY",
                "entry_setup_id": "lower_hold_buy",
                "regime_at_entry": "RANGE",
                "open_time": "2026-03-30 00:40:00",
                "close_time": "2026-03-30 01:10:00",
                "open_ts": "1774802400",
                "close_ts": "1774804200",
                "profit": "15.0",
                "decision_winner": "hold",
                "decision_reason": "hold_best",
                "exit_wait_state": "NONE",
            },
        ],
    )

    result = module.write_profitability_operations_p1_lifecycle_correlation_report(
        output_dir=output_dir,
        decisions_path=decisions_path,
        decision_detail_path=decision_detail_path,
        open_trades_path=open_trades_path,
        closed_trades_path=closed_trades_path,
        tail=100,
        now=datetime.fromisoformat("2026-03-30T02:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["coverage_summary"]["coverage_in_scope"] == 1
    assert result["family_row_count"] >= 1
    assert "Profitability / Operations P1 Lifecycle Correlation" in markdown
    assert "`coverage_in_scope`" in markdown


def test_p1_clusters_include_wait_to_forced_exit_and_reverse_now_patterns(tmp_path):
    decisions_path = tmp_path / "entry_decisions.csv"
    decision_detail_path = tmp_path / "entry_decisions.detail.jsonl"
    open_trades_path = tmp_path / "trade_history.csv"
    closed_trades_path = tmp_path / "trade_closed_history.csv"

    _write_csv(
        decisions_path,
        [
            {
                "time": "2026-03-30T01:00:00",
                "symbol": "NAS100",
                "outcome": "wait",
                "consumer_archetype_id": "trend_pullback_sell",
                "preflight_regime": "EXPANSION",
                "observe_side": "SELL",
                "runtime_snapshot_key": "runtime_signal_row_v1|symbol=NAS100|anchor_field=signal_bar_ts|anchor_value=1774811700.0|hint=BOTH",
            },
            {
                "time": "2026-03-30T01:01:00",
                "symbol": "NAS100",
                "outcome": "wait",
                "consumer_archetype_id": "trend_pullback_sell",
                "preflight_regime": "EXPANSION",
                "observe_side": "SELL",
                "runtime_snapshot_key": "runtime_signal_row_v1|symbol=NAS100|anchor_field=signal_bar_ts|anchor_value=1774811701.0|hint=BOTH",
            },
            {
                "time": "2026-03-30T01:02:00",
                "symbol": "NAS100",
                "outcome": "wait",
                "consumer_archetype_id": "trend_pullback_sell",
                "preflight_regime": "EXPANSION",
                "observe_side": "SELL",
                "runtime_snapshot_key": "runtime_signal_row_v1|symbol=NAS100|anchor_field=signal_bar_ts|anchor_value=1774811702.0|hint=BOTH",
            },
        ],
    )
    decision_detail_path.write_text("", encoding="utf-8")
    _write_csv(open_trades_path, [])
    _write_csv(
        closed_trades_path,
        [
            {
                "symbol": "NAS100",
                "direction": "SELL",
                "entry_setup_id": "trend_pullback_sell",
                "regime_at_entry": "EXPANSION",
                "open_time": "2026-03-30 00:50:00",
                "close_time": "2026-03-30 00:56:00",
                "open_ts": "1774803000",
                "close_ts": "1774803360",
                "profit": "-3.0",
                "decision_winner": "exit_now",
                "decision_reason": "exit_now_best",
                "exit_wait_state": "GREEN_CLOSE",
            },
            {
                "symbol": "NAS100",
                "direction": "SELL",
                "entry_setup_id": "trend_pullback_sell",
                "regime_at_entry": "EXPANSION",
                "open_time": "2026-03-30 00:57:00",
                "close_time": "2026-03-30 01:04:00",
                "open_ts": "1774803420",
                "close_ts": "1774803840",
                "profit": "-2.0",
                "decision_winner": "reverse_now",
                "decision_reason": "reverse_now_best",
                "exit_wait_state": "REVERSE_READY",
            },
            {
                "symbol": "NAS100",
                "direction": "SELL",
                "entry_setup_id": "trend_pullback_sell",
                "regime_at_entry": "EXPANSION",
                "open_time": "2026-03-30 01:05:00",
                "close_time": "2026-03-30 01:11:00",
                "open_ts": "1774803900",
                "close_ts": "1774804260",
                "profit": "-1.0",
                "decision_winner": "exit_now",
                "decision_reason": "exit_now_best",
                "exit_wait_state": "GREEN_CLOSE",
            },
        ],
    )

    report = module.build_profitability_operations_p1_lifecycle_correlation_report(
        decisions_path=decisions_path,
        decision_detail_path=decision_detail_path,
        open_trades_path=open_trades_path,
        closed_trades_path=closed_trades_path,
        tail=100,
        now=datetime.fromisoformat("2026-03-30T02:00:00"),
    )

    clusters = {cluster["cluster_type"] for cluster in report["suspicious_clusters"]}
    cluster_type_rows = {row["cluster_type"]: row for row in report["suspicious_cluster_type_summary"]}

    assert "wait_to_forced_exit_cluster" in clusters
    assert "reverse_now_cluster" in clusters
    assert cluster_type_rows["wait_to_forced_exit_cluster"]["count"] >= 1
