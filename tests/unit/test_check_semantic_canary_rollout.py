import csv
import json
from datetime import datetime
from pathlib import Path

from scripts.check_semantic_canary_rollout import build_canary_report, write_canary_report


def test_build_canary_report_summarizes_recent_rows():
    entry_rows = [
        {
            "time": "2026-03-21T10:00:00+09:00",
            "symbol": "BTCUSD",
            "entry_stage": "aggressive",
            "blocked_by": "",
            "semantic_shadow_available": "1",
            "semantic_shadow_trace_quality": "clean",
            "semantic_live_rollout_mode": "threshold_only",
            "semantic_live_alert": "0",
            "semantic_live_fallback_reason": "",
            "semantic_live_threshold_adjustment": "-4",
            "semantic_live_threshold_applied": "1",
            "semantic_shadow_compare_label": "agree_enter",
        },
        {
            "time": "2026-03-21T10:01:00+09:00",
            "symbol": "BTCUSD",
            "entry_stage": "aggressive",
            "blocked_by": "entry_wait",
            "semantic_shadow_available": "1",
            "semantic_shadow_trace_quality": "clean",
            "semantic_live_rollout_mode": "threshold_only",
            "semantic_live_alert": "1",
            "semantic_live_fallback_reason": "timing_probability_too_low",
            "semantic_live_threshold_adjustment": "0",
            "semantic_live_threshold_applied": "0",
            "semantic_shadow_compare_label": "agree_wait",
        },
    ]
    runtime_status = {
        "semantic_live_config": {
            "mode": "threshold_only",
            "symbol_allowlist": ["BTCUSD"],
        },
        "latest_signal_by_symbol": {"BTCUSD": {"semantic_live_rollout_mode": "threshold_only"}},
    }
    rollout_manifest = {"semantic_rollout_state": {"entry": {"events_total": 2}}}

    report = build_canary_report(
        entry_rows=entry_rows,
        runtime_status=runtime_status,
        rollout_manifest=rollout_manifest,
        symbol="BTCUSD",
        hours=24,
        now=datetime.fromisoformat("2026-03-21T12:00:00+09:00"),
    )

    assert report["summary"]["recent_rows"] == 2
    assert report["summary"]["threshold_applied_rows"] == 1
    assert report["summary"]["fallback_rows"] == 1
    assert report["fallback_reason_counts"]["timing_probability_too_low"] == 1
    assert report["trace_quality_counts"]["clean"] == 2
    assert report["semantic_live_reason_counts"] == {}
    assert report["window_start"] == "2026-03-20T12:00:00+09:00"


def test_write_canary_report_reads_recent_csv_and_writes_outputs(monkeypatch, tmp_path: Path):
    data_root = tmp_path
    entry_path = data_root / "entry_decisions.csv"
    runtime_status_path = data_root / "runtime_status.json"
    rollout_manifest_path = data_root / "semantic_live_rollout_latest.json"
    output_dir = data_root / "analysis"

    with entry_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "time",
                "symbol",
                "entry_stage",
                "outcome",
                "blocked_by",
                "semantic_shadow_available",
                "semantic_shadow_trace_quality",
                "semantic_live_rollout_mode",
                "semantic_live_alert",
                "semantic_live_fallback_reason",
                "semantic_live_symbol_allowed",
                "semantic_live_entry_stage_allowed",
                "semantic_live_threshold_before",
                "semantic_live_threshold_after",
                "semantic_live_threshold_adjustment",
                "semantic_live_threshold_applied",
                "semantic_live_partial_weight",
                "semantic_live_partial_live_applied",
                "semantic_live_reason",
                "semantic_shadow_compare_label",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "time": "2026-03-21T10:00:00+09:00",
                "symbol": "BTCUSD",
                "entry_stage": "aggressive",
                "outcome": "entered",
                "blocked_by": "",
                "semantic_shadow_available": "1",
                "semantic_shadow_trace_quality": "clean",
                "semantic_live_rollout_mode": "threshold_only",
                "semantic_live_alert": "0",
                "semantic_live_fallback_reason": "",
                "semantic_live_symbol_allowed": "1",
                "semantic_live_entry_stage_allowed": "1",
                "semantic_live_threshold_before": "300",
                "semantic_live_threshold_after": "296",
                "semantic_live_threshold_adjustment": "-4",
                "semantic_live_threshold_applied": "1",
                "semantic_live_partial_weight": "0.0",
                "semantic_live_partial_live_applied": "0",
                "semantic_live_reason": "mode=threshold_only",
                "semantic_shadow_compare_label": "agree_enter",
            }
        )

    runtime_status_path.write_text(
        json.dumps({"semantic_live_config": {"mode": "threshold_only"}, "latest_signal_by_symbol": {}}),
        encoding="utf-8",
    )
    rollout_manifest_path.write_text(
        json.dumps({"semantic_rollout_state": {"entry": {"events_total": 1}}}),
        encoding="utf-8",
    )

    monkeypatch.setattr("scripts.check_semantic_canary_rollout.ENTRY_DECISIONS", entry_path)
    monkeypatch.setattr("scripts.check_semantic_canary_rollout.RUNTIME_STATUS", runtime_status_path)
    monkeypatch.setattr("scripts.check_semantic_canary_rollout.ROLLOUT_MANIFEST", rollout_manifest_path)

    paths = write_canary_report(
        symbol="BTCUSD",
        hours=48,
        max_rows=100,
        output_dir=output_dir,
        now=datetime.fromisoformat("2026-03-21T12:00:00+09:00"),
    )

    assert Path(paths["latest_json_path"]).exists()
    assert Path(paths["latest_markdown_path"]).exists()
    latest = json.loads(Path(paths["latest_json_path"]).read_text(encoding="utf-8"))
    assert latest["summary"]["recent_rows"] == 1
    assert latest["window_start"] == "2026-03-19T12:00:00+09:00"
    assert latest["semantic_live_reason_counts"]["mode=threshold_only"] == 1
