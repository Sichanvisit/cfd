import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p4_time_series_comparison_report.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p4_time_series_comparison_report", SCRIPT_PATH)
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


def _decision_row(symbol: str, time_text: str) -> dict:
    return {
        "time": time_text,
        "symbol": symbol,
        "outcome": "entered",
        "consumer_archetype_id": "trend_pullback_buy",
        "preflight_regime": "LOW_LIQUIDITY",
        "observe_reason": "trend_pullback_confirm",
        "observe_side": "BUY",
    }


def _closed_trade(
    *,
    symbol: str,
    direction: str,
    entry_setup_id: str,
    regime_at_entry: str,
    profit: str,
    net_pnl_after_cost: str = "",
    gross_pnl: str = "",
    cost_total: str = "",
    decision_winner: str = "cut_now",
    decision_reason: str = "cut_now_best",
    exit_wait_state: str = "CUT_IMMEDIATE",
    entry_stage: str = "balanced",
    exit_policy_stage: str = "short",
    exit_policy_profile: str = "conservative",
    open_ts: int = 1000,
    close_ts: int = 1100,
) -> dict:
    return {
        "symbol": symbol,
        "direction": direction,
        "entry_setup_id": entry_setup_id,
        "regime_at_entry": regime_at_entry,
        "entry_stage": entry_stage,
        "exit_policy_stage": exit_policy_stage,
        "exit_policy_profile": exit_policy_profile,
        "decision_winner": decision_winner,
        "decision_reason": decision_reason,
        "exit_wait_state": exit_wait_state,
        "profit": profit,
        "net_pnl_after_cost": net_pnl_after_cost,
        "gross_pnl": gross_pnl,
        "cost_total": cost_total,
        "open_ts": str(open_ts),
        "close_ts": str(close_ts),
        "open_time": "2026-03-30 00:00:00",
        "close_time": "2026-03-30 00:01:40",
    }


def test_build_p4_compare_report_detects_recent_worsening(tmp_path):
    decisions_path = tmp_path / "entry_decisions.csv"
    decision_detail_path = tmp_path / "entry_decisions.detail.jsonl"
    open_trades_path = tmp_path / "trade_history.csv"
    closed_trades_path = tmp_path / "trade_closed_history.csv"

    decision_rows = []
    closed_rows = []

    for i in range(30):
        decision_rows.append(_decision_row("NAS100", f"2026-03-29T00:{i:02d}:00"))
        closed_rows.append(
            _closed_trade(
                symbol="NAS100",
                direction="BUY",
                entry_setup_id="",
                regime_at_entry="LOW_LIQUIDITY",
                profit="-2.0",
                open_ts=1000 + i,
                close_ts=1060 + i,
            )
        )

    for i in range(10):
        decision_rows.append(_decision_row("NAS100", f"2026-03-30T00:{i:02d}:00"))
        closed_rows.append(
            _closed_trade(
                symbol="NAS100",
                direction="BUY",
                entry_setup_id="",
                regime_at_entry="LOW_LIQUIDITY",
                profit="-2.0",
                open_ts=2000 + i,
                close_ts=2060 + i,
            )
        )
    for i in range(10):
        decision_rows.append(_decision_row("XAUUSD", f"2026-03-30T01:{i:02d}:00"))
        closed_rows.append(
            _closed_trade(
                symbol="XAUUSD",
                direction="SELL",
                entry_setup_id="",
                regime_at_entry="LOW_LIQUIDITY",
                profit="-4.0",
                open_ts=3000 + i,
                close_ts=3060 + i,
            )
        )
    for i in range(10):
        decision_rows.append(_decision_row("BTCUSD", f"2026-03-30T02:{i:02d}:00"))
        closed_rows.append(
            _closed_trade(
                symbol="BTCUSD",
                direction="SELL",
                entry_setup_id="range_upper_reversal_sell",
                regime_at_entry="NORMAL",
                profit="25.0",
                net_pnl_after_cost="0.0",
                gross_pnl="0.0",
                cost_total="0.0",
                decision_winner="hold",
                decision_reason="hold_best",
                exit_wait_state="NONE",
                open_ts=4000 + i,
                close_ts=4060 + i,
            )
        )

    _write_csv(decisions_path, decision_rows)
    decision_detail_path.write_text("", encoding="utf-8")
    _write_csv(open_trades_path, [])
    _write_csv(closed_trades_path, closed_rows)

    report = module.build_profitability_operations_p4_time_series_comparison_report(
        decisions_path=decisions_path,
        decision_detail_path=decision_detail_path,
        open_trades_path=open_trades_path,
        closed_trades_path=closed_trades_path,
        window_size=30,
        now=datetime.fromisoformat("2026-03-30T18:00:00"),
    )

    alert_type_rows = {row["alert_type"]: row for row in report["p3_alert_type_deltas"]}
    symbol_rows = {row["symbol"]: row for row in report["symbol_alert_deltas"]}

    assert report["report_version"] == module.REPORT_VERSION
    assert report["overall_delta_summary"]["active_alert_delta"] > 0
    assert alert_type_rows["negative_expectancy_alert"]["delta"] > 0
    assert alert_type_rows["zero_pnl_information_gap_alert"]["delta"] > 0
    assert symbol_rows["XAUUSD"]["active_alert_delta"] > 0
    assert symbol_rows["BTCUSD"]["active_alert_delta"] > 0
    assert report["quick_read_summary"]["top_worsening_signals"]


def test_write_p4_compare_report_writes_outputs(tmp_path):
    decisions_path = tmp_path / "entry_decisions.csv"
    decision_detail_path = tmp_path / "entry_decisions.detail.jsonl"
    open_trades_path = tmp_path / "trade_history.csv"
    closed_trades_path = tmp_path / "trade_closed_history.csv"
    output_dir = tmp_path / "analysis"

    _write_csv(
        decisions_path,
        [
            _decision_row("NAS100", "2026-03-29T00:00:00"),
            _decision_row("NAS100", "2026-03-30T00:00:00"),
        ],
    )
    decision_detail_path.write_text("", encoding="utf-8")
    _write_csv(open_trades_path, [])
    _write_csv(
        closed_trades_path,
        [
            _closed_trade(symbol="NAS100", direction="BUY", entry_setup_id="", regime_at_entry="LOW_LIQUIDITY", profit="-2.0"),
            _closed_trade(symbol="NAS100", direction="BUY", entry_setup_id="", regime_at_entry="LOW_LIQUIDITY", profit="-3.0"),
        ],
    )

    result = module.write_profitability_operations_p4_time_series_comparison_report(
        output_dir=output_dir,
        decisions_path=decisions_path,
        decision_detail_path=decision_detail_path,
        open_trades_path=open_trades_path,
        closed_trades_path=closed_trades_path,
        window_size=1,
        now=datetime.fromisoformat("2026-03-30T18:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["compare_scope"]["window_size"] == 1
    assert "Profitability / Operations P4 Time-Series Comparison" in markdown
