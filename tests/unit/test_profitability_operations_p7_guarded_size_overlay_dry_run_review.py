import csv
import json
import importlib.util
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "profitability_operations_p7_guarded_size_overlay_dry_run_review.py"
spec = importlib.util.spec_from_file_location("profitability_operations_p7_guarded_size_overlay_dry_run_review", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_p7_dry_run_review_marks_pre_schema_when_columns_missing(tmp_path):
    entry_path = tmp_path / "entry_decisions.csv"
    overlay_path = tmp_path / "overlay.json"
    _write_csv(
        entry_path,
        [{"time": "2026-03-30T10:00:00", "symbol": "BTCUSD", "action": "BUY", "outcome": "entered"}],
    )
    _write_json(overlay_path, {"guarded_size_overlay_candidates": [{"symbol": "BTCUSD"}]})

    report = module.build_profitability_operations_p7_guarded_size_overlay_dry_run_review(
        entry_decisions_path=entry_path,
        overlay_path=overlay_path,
        now=datetime.fromisoformat("2026-03-30T22:10:00"),
    )

    assert report["overall_summary"]["p7_schema_present"] is False
    assert report["overall_summary"]["review_state"] == "pre_p7_schema_header"
    assert report["overall_summary"]["recommended_next_step"] == "restart_runtime_and_wait_for_new_entry_rows"


def test_build_p7_dry_run_review_summarizes_symbol_rows(tmp_path):
    entry_path = tmp_path / "entry_decisions.csv"
    overlay_path = tmp_path / "overlay.json"
    _write_csv(
        entry_path,
        [
            {
                "time": "2026-03-30T10:00:00",
                "symbol": "BTCUSD",
                "action": "SELL",
                "outcome": "entered",
                "p7_guarded_size_overlay_v1": json.dumps(
                    {"mode": "dry_run", "matched": True, "gate_reason": "dry_run_only", "target_multiplier": 0.57, "effective_multiplier": 1.0},
                    ensure_ascii=False,
                ),
                "p7_size_overlay_mode": "dry_run",
                "p7_size_overlay_gate_reason": "dry_run_only",
                "p7_size_overlay_matched": "1",
                "p7_size_overlay_apply_allowed": "0",
                "p7_size_overlay_applied": "0",
                "p7_size_overlay_target_multiplier": "0.57",
                "p7_size_overlay_effective_multiplier": "1.0",
            }
        ],
    )
    _write_json(
        overlay_path,
        {"guarded_size_overlay_candidates": [{"symbol": "BTCUSD", "target_multiplier": 0.57, "size_action": "reduce"}]},
    )

    report = module.build_profitability_operations_p7_guarded_size_overlay_dry_run_review(
        entry_decisions_path=entry_path,
        overlay_path=overlay_path,
        now=datetime.fromisoformat("2026-03-30T22:10:00"),
    )

    assert report["overall_summary"]["p7_schema_present"] is True
    assert report["overall_summary"]["p7_trace_row_count"] == 1
    assert report["overall_summary"]["review_state"] == "dry_run_rows_accumulating"
    assert report["symbol_dry_run_summary"][0]["symbol"] == "BTCUSD"
    assert report["symbol_dry_run_summary"][0]["matched_count"] == 1
    assert report["symbol_dry_run_summary"][0]["top_gate_reason"] == "dry_run_only"
