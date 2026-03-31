import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p2_zero_pnl_gap_audit.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p2_zero_pnl_gap_audit", SCRIPT_PATH)
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


def test_build_zero_pnl_gap_audit_classifies_patterns_and_metadata(tmp_path):
    closed_trades_path = tmp_path / "trade_closed_history.csv"
    _write_csv(
        closed_trades_path,
        [
            {
                "symbol": "BTCUSD",
                "direction": "BUY",
                "entry_setup_id": "",
                "regime_at_entry": "",
                "entry_stage": "balanced",
                "profit": "45.1",
                "gross_pnl": "0.0",
                "cost_total": "0.0",
                "net_pnl_after_cost": "0.0",
                "decision_winner": "",
                "decision_reason": "",
                "exit_wait_state": "",
                "close_time": "2026-03-30 01:00:00",
            },
            {
                "symbol": "BTCUSD",
                "direction": "BUY",
                "entry_setup_id": "",
                "regime_at_entry": "",
                "entry_stage": "balanced",
                "profit": "-10.0",
                "gross_pnl": "0.0",
                "cost_total": "0.0",
                "net_pnl_after_cost": "0.0",
                "decision_winner": "",
                "decision_reason": "",
                "exit_wait_state": "",
                "close_time": "2026-03-30 01:01:00",
            },
            {
                "symbol": "XAUUSD",
                "direction": "SELL",
                "entry_setup_id": "range_upper_reversal_sell",
                "regime_at_entry": "RANGE",
                "entry_stage": "balanced",
                "profit": "0.0",
                "gross_pnl": "0.0",
                "cost_total": "0.0",
                "net_pnl_after_cost": "0.0",
                "decision_winner": "cut_now",
                "decision_reason": "cut_now_best",
                "exit_wait_state": "CUT_IMMEDIATE",
                "close_time": "2026-03-30 01:02:00",
            },
            {
                "symbol": "NAS100",
                "direction": "SELL",
                "entry_setup_id": "range_upper_reversal_sell",
                "regime_at_entry": "RANGE",
                "entry_stage": "balanced",
                "profit": "3.0",
                "gross_pnl": "1.0",
                "cost_total": "0.5",
                "net_pnl_after_cost": "2.0",
                "decision_winner": "hold",
                "decision_reason": "hold_best",
                "exit_wait_state": "NONE",
                "close_time": "2026-03-30 01:03:00",
            },
        ],
    )

    report = module.build_profitability_operations_p2_zero_pnl_gap_audit(
        closed_trades_path=closed_trades_path,
        tail=100,
        now=datetime.fromisoformat("2026-03-30T15:00:00"),
    )

    pattern_rows = {row["pattern"]: row["count"] for row in report["pattern_summary"]}
    metadata_rows = {row["flag"]: row["count"] for row in report["metadata_gap_summary"]}
    bucket_rows = {
        (row["pattern"], row["symbol"], row["setup_key"]): row
        for row in report["bucket_summary"]
    }

    assert report["report_version"] == module.REPORT_VERSION
    assert report["audit_summary"]["zero_pnl_row_count"] == 3
    assert pattern_rows["net_zero_overrides_nonzero_profit"] == 2
    assert pattern_rows["all_pnl_fields_zero_or_missing"] == 1
    assert metadata_rows["missing_setup"] == 2
    assert metadata_rows["missing_regime"] == 2
    btc_bucket = bucket_rows[("net_zero_overrides_nonzero_profit", "BTCUSD", "legacy_trade_without_setup_id::BUY::balanced")]
    assert btc_bucket["zero_pnl_row_count"] == 2
    assert btc_bucket["avg_abs_profit"] == 27.55
    assert report["quick_read_summary"]["top_concerns"]


def test_write_zero_pnl_gap_audit_writes_outputs(tmp_path):
    closed_trades_path = tmp_path / "trade_closed_history.csv"
    output_dir = tmp_path / "analysis"
    _write_csv(
        closed_trades_path,
        [
            {
                "symbol": "BTCUSD",
                "direction": "BUY",
                "entry_setup_id": "",
                "regime_at_entry": "",
                "entry_stage": "balanced",
                "profit": "45.1",
                "gross_pnl": "0.0",
                "cost_total": "0.0",
                "net_pnl_after_cost": "0.0",
                "decision_winner": "",
                "decision_reason": "",
                "exit_wait_state": "",
                "close_time": "2026-03-30 01:00:00",
            },
        ],
    )

    result = module.write_profitability_operations_p2_zero_pnl_gap_audit(
        output_dir=output_dir,
        closed_trades_path=closed_trades_path,
        tail=100,
        now=datetime.fromisoformat("2026-03-30T15:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])
    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["audit_summary"]["zero_pnl_row_count"] == 1
    assert payload["pattern_summary"][0]["pattern"] == "net_zero_overrides_nonzero_profit"
    assert "Profitability / Operations P2 Zero PnL Gap Audit" in markdown
