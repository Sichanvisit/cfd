import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_mf17_runtime_guard_watch.py"
spec = importlib.util.spec_from_file_location("build_mf17_runtime_guard_watch", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _profile_row(symbol: str, elapsed_ms: float) -> dict:
    return {
        "symbol": symbol,
        "elapsed_ms": elapsed_ms,
        "append_total_ms": 18.0,
        "append_log_profile": {
            "total_ms": 18.0,
            "recorder_total_ms": 17.0,
            "runtime_snapshot_mode": "lean_no_action_direct_row",
            "runtime_snapshot_store_calls": 0,
            "recorder_stage_timings_ms": {
                "detail_payload_build": 9.0,
                "file_write": 8.0,
            },
            "detail_payload_stage_timings_ms": {
                "compact_runtime_row": 3.0,
                "detail_record_json": 0.6,
                "hot_payload_build": 1.1,
                "payload_size_metrics": 0.4,
            },
            "file_write_stage_timings_ms": {
                "rollover": 0.2,
                "detail_append": 4.0,
                "csv_append": 1.2,
            },
        },
    }


def test_build_mf17_runtime_guard_watch_summarizes_guard_state(tmp_path: Path) -> None:
    entry_eval_profile_path = tmp_path / "entry_eval_profile_latest.json"
    runtime_status_path = tmp_path / "runtime_status.json"
    runtime_loop_debug_path = tmp_path / "runtime_loop_debug.json"
    baseline_json_path = tmp_path / "entry_performance_baseline_latest.json"
    regression_json_output_path = tmp_path / "entry_performance_regression_watch_latest.json"
    preview_path = tmp_path / "symbol_surface_preview_evaluation_latest.json"
    candidate_path = tmp_path / "bounded_rollout_candidate_gate_latest.json"
    manifest_path = tmp_path / "bounded_rollout_review_manifest_latest.json"
    signoff_path = tmp_path / "bounded_rollout_signoff_criteria_latest.json"
    packet_path = tmp_path / "symbol_surface_canary_signoff_packet_latest.json"
    manual_path = tmp_path / "symbol_surface_manual_signoff_apply_latest.json"
    activation_contract_path = tmp_path / "bounded_symbol_surface_activation_contract_latest.json"
    activation_csv_output_path = tmp_path / "bounded_symbol_surface_activation_apply_latest.csv"
    activation_json_output_path = tmp_path / "bounded_symbol_surface_activation_apply_latest.json"
    resolved_contract_output_path = tmp_path / "bounded_symbol_surface_activation_contract_applied.csv"
    diagnostic_json_output_path = tmp_path / "mf17_rollout_pending_diagnostic_latest.json"
    watch_output_path = tmp_path / "mf17_runtime_guard_watch_latest.json"

    entry_eval_profile_path.write_text(
        json.dumps(
            {
                "latest_by_symbol": {
                    "NAS100": _profile_row("NAS100", 221.0),
                    "BTCUSD": _profile_row("BTCUSD", 120.0),
                    "XAUUSD": _profile_row("XAUUSD", 150.0),
                }
            }
        ),
        encoding="utf-8",
    )
    runtime_status_path.write_text(
        json.dumps({"updated_at": "2026-04-10T17:00:00+09:00", "runtime_recycle": {"last_open_positions_count": 1}}),
        encoding="utf-8",
    )
    runtime_loop_debug_path.write_text(
        json.dumps({"runtime_loop_updated_at": "2026-04-10T17:00:01+09:00", "runtime_loop_stage": "symbol_start", "runtime_loop_symbol": "NAS100"}),
        encoding="utf-8",
    )
    baseline_json_path.write_text(
        json.dumps(
            {
                "reentry_elapsed_ms_threshold": 200.0,
                "symbol_metrics": [
                    {"symbol": "NAS100", "elapsed_ms": 120.0, "append_total_ms": 15.0},
                    {"symbol": "BTCUSD", "elapsed_ms": 100.0, "append_total_ms": 14.0},
                    {"symbol": "XAUUSD", "elapsed_ms": 110.0, "append_total_ms": 14.0},
                ]
            }
        ),
        encoding="utf-8",
    )
    preview_path.write_text(
        json.dumps(
            {"rows": [
                {"market_family": "NAS100", "surface_name": "initial_entry_surface", "readiness_state": "preview_eval_ready"},
                {"market_family": "XAUUSD", "surface_name": "initial_entry_surface", "readiness_state": "preview_eval_ready"},
            ]}
        ),
        encoding="utf-8",
    )
    candidate_path.write_text(
        json.dumps(
            {"rows": [
                {"market_family": "NAS100", "surface_name": "initial_entry_surface", "rollout_candidate_state": "REVIEW_CANARY_CANDIDATE"},
                {"market_family": "XAUUSD", "surface_name": "initial_entry_surface", "rollout_candidate_state": "REVIEW_CANARY_CANDIDATE"},
            ]}
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {"rows": [
                {"market_family": "NAS100", "surface_name": "initial_entry_surface", "review_status": "review_ready"},
                {"market_family": "XAUUSD", "surface_name": "initial_entry_surface", "review_status": "review_ready"},
            ]}
        ),
        encoding="utf-8",
    )
    signoff_path.write_text(
        json.dumps(
            {"rows": [
                {"market_family": "NAS100", "surface_name": "initial_entry_surface", "signoff_state": "HOLD_BEFORE_SIGNOFF"},
                {"market_family": "XAUUSD", "surface_name": "initial_entry_surface", "signoff_state": "READY_FOR_MANUAL_SIGNOFF"},
            ]}
        ),
        encoding="utf-8",
    )
    packet_path.write_text(
        json.dumps(
            {"rows": [
                {"market_family": "NAS100", "surface_name": "initial_entry_surface", "packet_status": "PACKET_NOT_READY"},
                {"market_family": "XAUUSD", "surface_name": "initial_entry_surface", "packet_status": "REVIEW_PACKET_READY"},
            ]}
        ),
        encoding="utf-8",
    )
    manual_path.write_text(
        json.dumps(
            {"rows": [
                {"market_family": "NAS100", "surface_name": "initial_entry_surface", "approval_state": "PACKET_NOT_READY"},
                {"market_family": "XAUUSD", "surface_name": "initial_entry_surface", "approval_state": "MANUAL_SIGNOFF_APPROVED"},
            ]}
        ),
        encoding="utf-8",
    )
    activation_contract_path.write_text(
        json.dumps(
            {"rows": [
                {"market_family": "NAS100", "surface_name": "initial_entry_surface", "contract_status": "PENDING_MANUAL_SIGNOFF"},
                {"market_family": "XAUUSD", "surface_name": "initial_entry_surface", "contract_status": "PENDING_MANUAL_SIGNOFF"},
            ]}
        ),
        encoding="utf-8",
    )

    rc = module.main(
        [
            "--entry-eval-profile-path", str(entry_eval_profile_path),
            "--runtime-status-path", str(runtime_status_path),
            "--runtime-loop-debug-path", str(runtime_loop_debug_path),
            "--baseline-json-path", str(baseline_json_path),
            "--regression-json-output-path", str(regression_json_output_path),
            "--preview-evaluation-path", str(preview_path),
            "--candidate-gate-path", str(candidate_path),
            "--review-manifest-path", str(manifest_path),
            "--signoff-criteria-path", str(signoff_path),
            "--signoff-packet-path", str(packet_path),
            "--manual-signoff-apply-path", str(manual_path),
            "--activation-contract-path", str(activation_contract_path),
            "--activation-csv-output-path", str(activation_csv_output_path),
            "--activation-json-output-path", str(activation_json_output_path),
            "--resolved-contract-output-path", str(resolved_contract_output_path),
            "--diagnostic-json-output-path", str(diagnostic_json_output_path),
            "--json-output-path", str(watch_output_path),
            "--iterations", "2",
            "--sleep-seconds", "0",
        ]
    )

    assert rc == 0
    payload = json.loads(watch_output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["iterations"] == 2
    assert payload["summary"]["nas_reentry_required"] is True
    assert payload["summary"]["xau_activation_state"] == "HOLD_RUNTIME_NOT_IDLE"
    assert payload["summary"]["pending_stage"] == "signoff"
    assert len(payload["iteration_summaries"]) == 2
