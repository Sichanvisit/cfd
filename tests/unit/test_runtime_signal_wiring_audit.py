import json

from backend.trading.chart_painter import Painter
from backend.services.runtime_signal_wiring_audit import (
    build_runtime_signal_wiring_audit,
    generate_and_write_runtime_signal_wiring_audit,
)


def test_build_runtime_signal_wiring_audit_summarizes_symbol_surfaces(tmp_path):
    flow_path = tmp_path / "XAUUSD_flow_history.json"
    flow_path.write_text(
        json.dumps(
            {
                "history": [
                    {
                        "time": "2026-04-14T18:00:00+09:00",
                        "event_kind": "BUY_WATCH",
                        "reason": "directional_continuation_overlay",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report = build_runtime_signal_wiring_audit(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_direction": "UP",
                "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
                "directional_continuation_accuracy_horizon_bars": 20,
                "directional_continuation_accuracy_sample_count": 4,
                "directional_continuation_accuracy_measured_count": 3,
                "directional_continuation_accuracy_correct_rate": 0.6667,
                "directional_continuation_accuracy_last_state": "CORRECT",
                "execution_action_diff_v1": {
                    "original_action_side": "SELL",
                    "final_action_side": "BUY",
                },
                "execution_diff_original_action_side": "SELL",
                "execution_diff_final_action_side": "BUY",
            }
        },
        ai_entry_traces=[
            {
                "execution_diff_original_action_side": "SELL",
                "execution_diff_final_action_side": "BUY",
            }
        ],
        accuracy_report={
            "summary": {
                "primary_measured_count": 3,
                "primary_correct_rate": 0.6667,
            },
            "symbol_direction_primary_summary": {
                "XAUUSD|UP": {
                    "sample_count": 4,
                }
            },
        },
        flow_history_dir=tmp_path,
    )

    assert report["summary"]["symbol_count"] == 1
    assert report["summary"]["overlay_present_count"] == 1
    assert report["summary"]["execution_diff_surface_count"] == 1
    assert report["summary"]["accuracy_surface_count"] == 1
    assert report["summary"]["flow_sync_match_count"] == 1
    row = report["per_symbol"]["XAUUSD"]
    assert row["flow_history_sync_state"] == "MATCH"
    assert row["execution_diff_surface_complete"] is True
    assert row["accuracy_surface_present"] is True
    assert row["accuracy_summary_present"] is True


def test_build_runtime_signal_wiring_audit_uses_runtime_flow_resolution_when_hint_blank(tmp_path):
    flow_path = tmp_path / "NAS100_flow_history.json"
    flow_path.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "ts": 1776575148,
                        "event_kind": "SELL_READY",
                        "side": "SELL",
                        "reason": "upper_reject_probe_observe",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_runtime_signal_wiring_audit(
        {
            "NAS100": {
                "symbol": "NAS100",
                "directional_continuation_overlay_v1": {
                    "overlay_enabled": False,
                    "overlay_state": "DISABLED",
                },
                "observe_confirm_v2": {
                    "action": "SELL",
                    "side": "SELL",
                    "reason": "upper_reject_probe_observe",
                },
                "my_position_count": 0,
            }
        },
        flow_history_dir=tmp_path,
    )

    assert report["summary"]["overlay_present_count"] == 0
    assert report["summary"]["flow_sync_match_count"] == 1
    row = report["per_symbol"]["NAS100"]
    assert row["row_event_kind_hint"] == ""
    assert row["row_resolved_event_kind"] == "SELL_READY"
    assert row["row_event_kind_for_sync"] == "SELL_READY"
    assert row["flow_history_sync_state"] == "MATCH"


def test_build_runtime_signal_wiring_audit_treats_compacted_signature_as_synced(tmp_path):
    runtime_row = {
        "symbol": "XAUUSD",
        "flow_shadow_chart_event_ownership_v1": "SHADOW_DISPLAY",
        "flow_shadow_chart_event_emit_v1": True,
        "flow_shadow_chart_event_final_kind_v1": "BUY_WATCH",
        "flow_shadow_chart_event_emit_reason_v1": "fallback_watch_start",
    }
    flow_path = tmp_path / "XAUUSD_flow_history.json"
    flow_path.write_text(
        json.dumps(
            {
                "last_signature": Painter._flow_event_signature(runtime_row),
                "events": [
                    {
                        "ts": 1776753300,
                        "event_kind": "BUY_PROBE",
                        "side": "BUY",
                        "reason": "lower_rebound_confirm",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_runtime_signal_wiring_audit(
        {"XAUUSD": runtime_row},
        flow_history_dir=tmp_path,
    )

    assert report["summary"]["flow_sync_match_count"] == 1
    assert report["summary"]["flow_signature_match_count"] == 1
    row = report["per_symbol"]["XAUUSD"]
    assert row["row_event_kind_for_sync"] == "BUY_WATCH"
    assert row["flow_history_event_kind"] == "BUY_PROBE"
    assert row["flow_history_sync_state"] == "SIGNATURE_MATCH_EVENT_COMPACTED"


def test_build_runtime_signal_wiring_audit_marks_signature_drift_as_pending_sync(tmp_path):
    flow_path = tmp_path / "NAS100_flow_history.json"
    flow_path.write_text(
        json.dumps(
            {
                "last_signature": "previous_signature",
                "events": [
                    {
                        "ts": 1776753300,
                        "event_kind": "BUY_WATCH",
                        "side": "BUY",
                        "reason": "previous_watch",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_runtime_signal_wiring_audit(
        {
            "NAS100": {
                "symbol": "NAS100",
                "observe_confirm_v2": {
                    "action": "WAIT",
                    "side": "",
                    "reason": "observe_state_wait",
                },
            }
        },
        flow_history_dir=tmp_path,
    )

    assert report["summary"]["flow_pending_sync_count"] == 1
    row = report["per_symbol"]["NAS100"]
    assert row["row_event_kind_for_sync"] == "WAIT"
    assert row["flow_history_event_kind"] == "BUY_WATCH"
    assert row["flow_history_sync_state"] == "PENDING_SYNC"


def test_generate_and_write_runtime_signal_wiring_audit_writes_artifacts(tmp_path):
    report = generate_and_write_runtime_signal_wiring_audit(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "directional_continuation_overlay_enabled": False,
            }
        },
        shadow_auto_dir=tmp_path,
        flow_history_dir=tmp_path,
    )

    json_path = tmp_path / "runtime_signal_wiring_audit_latest.json"
    md_path = tmp_path / "runtime_signal_wiring_audit_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    assert report["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)


def test_generate_runtime_signal_wiring_audit_can_skip_artifact_write(tmp_path):
    report = generate_and_write_runtime_signal_wiring_audit(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "directional_continuation_overlay_enabled": False,
            }
        },
        shadow_auto_dir=tmp_path,
        flow_history_dir=tmp_path,
        write_artifacts=False,
    )

    assert report["summary"]["symbol_count"] == 1
    assert report["artifact_paths"] == {}
    assert not (tmp_path / "runtime_signal_wiring_audit_latest.json").exists()
    assert not (tmp_path / "runtime_signal_wiring_audit_latest.md").exists()


def test_generate_runtime_signal_wiring_audit_does_not_overwrite_latest_with_empty_rows(tmp_path):
    report = generate_and_write_runtime_signal_wiring_audit(
        {},
        shadow_auto_dir=tmp_path,
        flow_history_dir=tmp_path,
    )

    assert report["summary"]["symbol_count"] == 0
    assert report["artifact_paths"] == {}
    assert not (tmp_path / "runtime_signal_wiring_audit_latest.json").exists()
    assert not (tmp_path / "runtime_signal_wiring_audit_latest.md").exists()
