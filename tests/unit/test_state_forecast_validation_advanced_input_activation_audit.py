import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "state_forecast_validation_advanced_input_activation_audit.py"
spec = importlib.util.spec_from_file_location("state_forecast_validation_advanced_input_activation_audit", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _wrap_payload(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _write_detail(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_build_activation_audit_detects_order_book_gap_and_activation_mix(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    baseline_path = out_dir / "state_forecast_validation_sf0_baseline_latest.json"
    sf1_path = out_dir / "state_forecast_validation_sf1_coverage_latest.json"
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)

    _write_json(baseline_path, {"baseline_summary": {"advanced_input_collector_count": 3}})
    _write_json(sf1_path, {"coverage_summary": {"sampled_row_count": 2}})

    detail_path = trades_root / "entry_decisions.detail.jsonl"
    rows = [
        {
            "payload": {
                "time": "2026-03-30T10:00:00",
                "signal_timeframe": "15M",
                "symbol": "BTCUSD",
                "state_vector_v2": _wrap_payload(
                    {
                        "metadata": {
                            "advanced_input_activation_state": "ADVANCED_PARTIAL",
                            "tick_flow_state": "BURST_UP_FLOW",
                            "order_book_state": "UNAVAILABLE",
                            "event_risk_state": "HIGH_EVENT_RISK",
                            "session_regime_state": "SESSION_EXPANSION",
                            "advanced_input_detail_v1": {
                                "activation_reasons": ["low_participation", "wait_noise"],
                                "advanced_execution_stress": 0.82,
                                "tick_sample_size": 96,
                                "order_book_levels": 0,
                                "event_risk_match_count": 7,
                            },
                        }
                    }
                ),
                "forecast_features_v1": _wrap_payload(
                    {
                        "metadata": {
                            "semantic_forecast_inputs_v2": {
                                "state_harvest": {"session_regime_state": "SESSION_EXPANSION", "event_risk_state": "HIGH_EVENT_RISK"},
                                "secondary_harvest": {
                                    "advanced_input_activation_state": "ADVANCED_PARTIAL",
                                    "tick_flow_state": "BURST_UP_FLOW",
                                    "order_book_state": "UNAVAILABLE",
                                },
                            }
                        }
                    }
                ),
            }
        },
        {
            "payload": {
                "time": "2026-03-30T10:15:00",
                "signal_timeframe": "15M",
                "symbol": "NAS100",
                "state_vector_v2": _wrap_payload(
                    {
                        "metadata": {
                            "advanced_input_activation_state": "ADVANCED_IDLE",
                            "tick_flow_state": "INACTIVE",
                            "order_book_state": "INACTIVE",
                            "event_risk_state": "INACTIVE",
                            "session_regime_state": "SESSION_BALANCED",
                            "advanced_input_detail_v1": {
                                "activation_reasons": [],
                                "advanced_execution_stress": 0.0,
                                "tick_sample_size": 0,
                                "order_book_levels": 0,
                                "event_risk_match_count": 0,
                            },
                        }
                    }
                ),
                "forecast_features_v1": _wrap_payload(
                    {
                        "metadata": {
                            "semantic_forecast_inputs_v2": {
                                "state_harvest": {"session_regime_state": "SESSION_BALANCED", "event_risk_state": "INACTIVE"},
                                "secondary_harvest": {
                                    "advanced_input_activation_state": "ADVANCED_IDLE",
                                    "tick_flow_state": "INACTIVE",
                                    "order_book_state": "INACTIVE",
                                },
                            }
                        }
                    }
                ),
            }
        },
    ]
    _write_detail(detail_path, rows)

    report = module.build_state_forecast_validation_advanced_input_activation_report(
        trades_root=trades_root,
        baseline_report_path=baseline_path,
        sf1_report_path=sf1_path,
        max_files=10,
        max_rows_per_file=10,
        now=datetime.fromisoformat("2026-03-30T20:30:00"),
    )

    summary = report["activation_summary"]
    assessment = report["activation_assessment"]
    reason_rows = {row["activation_reason"]: row for row in report["activation_reason_summary"]}
    suspicious = {row["collector_name"]: row for row in report["suspicious_collector_candidates"]}

    assert summary["sampled_row_count"] == 2
    assert summary["activation_partial_ratio"] == 0.5
    assert summary["activation_passive_ratio"] == 0.5
    assert summary["tick_state_active_like_ratio"] == 0.5
    assert summary["order_book_state_active_like_ratio"] == 0.0
    assert summary["order_book_levels_positive_ratio"] == 0.0
    assert summary["event_risk_match_positive_ratio"] == 0.5
    assert summary["advanced_execution_stress_signal_ratio"] == 0.5
    assert assessment["activation_state"] == "collector_activation_gap"
    assert assessment["order_book_gap_suspected"] is True
    assert assessment["recommended_next_step"] == "SF3_forecast_harvest_usage_audit"
    assert reason_rows["low_participation"]["sampled_rows"] == 1
    assert suspicious["order_book"]["positive_payload_ratio"] == 0.0


def test_write_activation_audit_writes_outputs(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    baseline_path = out_dir / "state_forecast_validation_sf0_baseline_latest.json"
    sf1_path = out_dir / "state_forecast_validation_sf1_coverage_latest.json"
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)

    _write_json(baseline_path, {"baseline_summary": {"advanced_input_collector_count": 3}})
    _write_json(sf1_path, {"coverage_summary": {"sampled_row_count": 1}})

    detail_path = trades_root / "entry_decisions.detail.jsonl"
    _write_detail(
        detail_path,
        [
            {
                "payload": {
                    "time": "2026-03-30T11:00:00",
                    "signal_timeframe": "15M",
                    "symbol": "XAUUSD",
                    "state_vector_v2": _wrap_payload(
                        {
                            "metadata": {
                                "advanced_input_activation_state": "ADVANCED_ACTIVE",
                                "tick_flow_state": "BALANCED_FLOW",
                                "order_book_state": "THIN_BOOK",
                                "event_risk_state": "LOW_EVENT_RISK",
                                "session_regime_state": "SESSION_EDGE_ROTATION",
                                "advanced_input_detail_v1": {
                                    "activation_reasons": ["shock_regime"],
                                    "advanced_execution_stress": 0.41,
                                    "tick_sample_size": 48,
                                    "order_book_levels": 5,
                                    "event_risk_match_count": 1,
                                },
                            }
                        }
                    ),
                    "forecast_features_v1": _wrap_payload(
                        {
                            "metadata": {
                                "semantic_forecast_inputs_v2": {
                                    "state_harvest": {"session_regime_state": "SESSION_EDGE_ROTATION", "event_risk_state": "LOW_EVENT_RISK"},
                                    "secondary_harvest": {
                                        "advanced_input_activation_state": "ADVANCED_ACTIVE",
                                        "tick_flow_state": "BALANCED_FLOW",
                                        "order_book_state": "THIN_BOOK",
                                    },
                                }
                            }
                        }
                    ),
                }
            }
        ],
    )

    result = module.write_state_forecast_validation_advanced_input_activation_report(
        trades_root=trades_root,
        baseline_report_path=baseline_path,
        sf1_report_path=sf1_path,
        output_dir=out_dir,
        max_files=5,
        max_rows_per_file=5,
        now=datetime.fromisoformat("2026-03-30T20:40:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["activation_summary"]["sampled_row_count"] == 1
    assert payload["activation_summary"]["activation_active_ratio"] == 1.0
    assert payload["activation_assessment"]["recommended_next_step"] == "SF3_forecast_harvest_usage_audit"

    markdown = md_path.read_text(encoding="utf-8")
    assert "State / Forecast Validation SF2 Activation Audit" in markdown

    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "collector_name" in csv_text
    assert "XAUUSD" in csv_text
