import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "state_forecast_validation_state_coverage_audit.py"
spec = importlib.util.spec_from_file_location("state_forecast_validation_state_coverage_audit", SCRIPT_PATH)
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


def test_build_state_coverage_report_detects_sparse_and_meaningful_fields(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    baseline_path = out_dir / "state_forecast_validation_sf0_baseline_latest.json"
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)
    _write_json(
        baseline_path,
        {
            "baseline_summary": {
                "state_raw_snapshot_field_count": 39,
                "state_vector_v2_field_count": 17,
                "forecast_harvest_field_count": 34,
            }
        },
    )
    detail_path = trades_root / "entry_decisions.detail.jsonl"
    rows = [
        {
            "payload": {
                "time": "2026-03-30T10:00:00",
                "signal_timeframe": "15M",
                "symbol": "XAUUSD",
                "position_snapshot_v2": _wrap_payload(
                    {"energy": {"middle_neutrality": 0.2, "position_conflict_score": 0.0, "lower_position_force": 0.8, "upper_position_force": 0.0}}
                ),
                "state_vector_v2": _wrap_payload(
                    {
                        "range_reversal_gain": 1.2,
                        "trend_pullback_gain": 1.0,
                        "breakout_continuation_gain": 0.9,
                        "noise_damp": 1.0,
                        "conflict_damp": 0.8,
                        "alignment_gain": 1.1,
                        "topdown_bull_bias": 0.2,
                        "topdown_bear_bias": 0.0,
                        "big_map_alignment_gain": 1.0,
                        "wait_patience_gain": 1.2,
                        "confirm_aggression_gain": 1.0,
                        "hold_patience_gain": 1.1,
                        "fast_exit_risk_penalty": 0.2,
                        "countertrend_penalty": 0.0,
                        "liquidity_penalty": 0.0,
                        "volatility_penalty": 0.1,
                        "metadata": {
                            "patience_state_label": "PATIENT",
                            "topdown_state_label": "BULLISH_TOPDOWN",
                            "quality_state_label": "GOOD_QUALITY",
                            "execution_friction_state": "LOW_FRICTION",
                            "session_exhaustion_state": "FRESH",
                            "event_risk_state": "LOW_EVENT_RISK",
                            "session_regime_state": "SESSION_EXPANSION",
                            "session_expansion_state": "UP_ACTIVE_EXPANSION",
                            "advanced_input_activation_state": "ACTIVE",
                            "tick_flow_state": "BURST_UP_FLOW",
                            "order_book_state": "BALANCED_BOOK",
                            "source_current_rsi": 62.0,
                            "source_current_adx": 28.0,
                            "source_current_plus_di": 32.0,
                            "source_current_minus_di": 11.0,
                            "source_recent_range_mean": 1.4,
                            "source_recent_body_mean": 0.7,
                            "source_sr_level_rank": 0.8,
                            "source_sr_touch_count": 3.0,
                        },
                    }
                ),
                "forecast_features_v1": _wrap_payload(
                    {
                        "position_primary_label": "ALIGNED_LOWER_STRONG",
                        "position_bias_label": "LOWER_BIAS",
                        "position_secondary_context_label": "LOWER_CONTEXT",
                        "position_conflict_score": 0.0,
                        "middle_neutrality": 0.2,
                        "metadata": {
                            "semantic_forecast_inputs_v2": {
                                "state_harvest": {
                                    "session_regime_state": "SESSION_EXPANSION",
                                    "session_expansion_state": "UP_ACTIVE_EXPANSION",
                                    "session_exhaustion_state": "FRESH",
                                    "topdown_spacing_state": "SPACED",
                                    "topdown_slope_state": "UP_SLOPE_ALIGNED",
                                    "topdown_confluence_state": "TOPDOWN_ALIGNED",
                                    "spread_stress_state": "NORMAL_SPREAD",
                                    "volume_participation_state": "ACTIVE_PARTICIPATION",
                                    "execution_friction_state": "LOW_FRICTION",
                                    "event_risk_state": "LOW_EVENT_RISK",
                                },
                                "secondary_harvest": {
                                    "advanced_input_activation_state": "ACTIVE",
                                    "tick_flow_state": "BURST_UP_FLOW",
                                    "order_book_state": "BALANCED_BOOK",
                                    "source_current_rsi": 62.0,
                                    "source_current_adx": 28.0,
                                    "source_current_plus_di": 32.0,
                                    "source_current_minus_di": 11.0,
                                    "source_recent_range_mean": 1.4,
                                    "source_recent_body_mean": 0.7,
                                    "source_sr_level_rank": 0.8,
                                    "source_sr_touch_count": 3.0,
                                },
                            }
                        },
                    }
                ),
            }
        },
        {
            "payload": {
                "time": "2026-03-30T10:15:00",
                "signal_timeframe": "15M",
                "symbol": "NAS100",
                "position_snapshot_v2": _wrap_payload(
                    {"energy": {"middle_neutrality": 0.0, "position_conflict_score": 0.0, "lower_position_force": 0.0, "upper_position_force": 0.0}}
                ),
                "state_vector_v2": _wrap_payload(
                    {
                        "range_reversal_gain": 1.0,
                        "trend_pullback_gain": 1.0,
                        "breakout_continuation_gain": 1.0,
                        "noise_damp": 1.0,
                        "conflict_damp": 1.0,
                        "alignment_gain": 1.0,
                        "topdown_bull_bias": 0.0,
                        "topdown_bear_bias": 0.0,
                        "big_map_alignment_gain": 1.0,
                        "wait_patience_gain": 1.0,
                        "confirm_aggression_gain": 1.0,
                        "hold_patience_gain": 1.0,
                        "fast_exit_risk_penalty": 0.0,
                        "countertrend_penalty": 0.0,
                        "liquidity_penalty": 0.0,
                        "volatility_penalty": 0.0,
                        "metadata": {
                            "patience_state_label": "UNKNOWN",
                            "topdown_state_label": "UNKNOWN",
                            "quality_state_label": "UNKNOWN",
                            "execution_friction_state": "UNKNOWN",
                            "session_exhaustion_state": "UNKNOWN",
                            "event_risk_state": "UNKNOWN",
                            "session_regime_state": "UNKNOWN",
                            "session_expansion_state": "UNKNOWN",
                            "advanced_input_activation_state": "INACTIVE",
                            "tick_flow_state": "INACTIVE",
                            "order_book_state": "INACTIVE",
                            "source_current_rsi": 0.0,
                            "source_current_adx": 0.0,
                            "source_current_plus_di": 0.0,
                            "source_current_minus_di": 0.0,
                            "source_recent_range_mean": 0.0,
                            "source_recent_body_mean": 0.0,
                            "source_sr_level_rank": 0.0,
                            "source_sr_touch_count": 0.0,
                        },
                    }
                ),
                "forecast_features_v1": _wrap_payload(
                    {
                        "metadata": {
                            "semantic_forecast_inputs_v2": {
                                "state_harvest": {
                                    "session_regime_state": "UNKNOWN",
                                    "session_expansion_state": "UNKNOWN",
                                    "session_exhaustion_state": "UNKNOWN",
                                    "topdown_spacing_state": "UNKNOWN",
                                    "topdown_slope_state": "UNKNOWN",
                                    "topdown_confluence_state": "UNKNOWN",
                                    "spread_stress_state": "UNKNOWN",
                                    "volume_participation_state": "UNKNOWN",
                                    "execution_friction_state": "UNKNOWN",
                                    "event_risk_state": "UNKNOWN",
                                },
                                "secondary_harvest": {
                                    "advanced_input_activation_state": "INACTIVE",
                                    "tick_flow_state": "INACTIVE",
                                    "order_book_state": "INACTIVE",
                                    "source_current_rsi": 0.0,
                                    "source_current_adx": 0.0,
                                    "source_current_plus_di": 0.0,
                                    "source_current_minus_di": 0.0,
                                    "source_recent_range_mean": 0.0,
                                    "source_recent_body_mean": 0.0,
                                    "source_sr_level_rank": 0.0,
                                    "source_sr_touch_count": 0.0,
                                },
                            }
                        },
                    }
                ),
            }
        },
    ]
    _write_detail(detail_path, rows)

    report = module.build_state_forecast_validation_state_coverage_report(
        trades_root=trades_root,
        baseline_report_path=baseline_path,
        max_files=10,
        max_rows_per_file=10,
        now=datetime.fromisoformat("2026-03-30T20:00:00"),
    )

    summary = report["coverage_summary"]
    assessment = report["coverage_assessment"]
    field_rows = {(row["field_group"], row["field_name"]): row for row in report["field_coverage_rows"]}

    assert summary["sampled_row_count"] == 2
    assert summary["state_vector_present_ratio"] == 1.0
    assert summary["state_harvest_present_ratio"] == 1.0
    assert summary["secondary_harvest_present_ratio"] == 1.0
    assert assessment["recommended_next_step"] == "SF2_advanced_input_activation_audit"
    assert field_rows[("state_vector_v2", "range_reversal_gain")]["meaningful_ratio"] == 1.0
    assert field_rows[("state_vector_v2.metadata", "advanced_input_activation_state")]["meaningful_ratio"] == 0.5
    assert field_rows[("state_harvest", "session_regime_state")]["meaningful_ratio"] == 0.5
    assert any(row["advanced_input_activation_state"] == "ACTIVE" for row in report["advanced_input_activation_summary"])


def test_write_state_coverage_report_writes_outputs(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    baseline_path = out_dir / "state_forecast_validation_sf0_baseline_latest.json"
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)
    _write_json(
        baseline_path,
        {
            "baseline_summary": {
                "state_raw_snapshot_field_count": 39,
                "state_vector_v2_field_count": 17,
                "forecast_harvest_field_count": 34,
            }
        },
    )
    detail_path = trades_root / "entry_decisions.detail.jsonl"
    _write_detail(
        detail_path,
        [
            {
                "payload": {
                    "time": "2026-03-30T10:00:00",
                    "signal_timeframe": "15M",
                    "symbol": "BTCUSD",
                    "position_snapshot_v2": _wrap_payload({"energy": {"middle_neutrality": 0.1}}),
                    "state_vector_v2": _wrap_payload({"range_reversal_gain": 1.0, "metadata": {"session_regime_state": "SESSION_EXPANSION"}}),
                    "forecast_features_v1": _wrap_payload(
                        {
                            "metadata": {
                                "semantic_forecast_inputs_v2": {
                                    "state_harvest": {"session_regime_state": "SESSION_EXPANSION"},
                                    "secondary_harvest": {"advanced_input_activation_state": "ACTIVE"},
                                }
                            }
                        }
                    ),
                }
            }
        ],
    )

    result = module.write_state_forecast_validation_state_coverage_report(
        trades_root=trades_root,
        baseline_report_path=baseline_path,
        output_dir=out_dir,
        max_files=5,
        max_rows_per_file=5,
        now=datetime.fromisoformat("2026-03-30T20:10:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["coverage_summary"]["sampled_row_count"] == 1
    assert payload["coverage_assessment"]["recommended_next_step"] == "SF2_advanced_input_activation_audit"

    markdown = md_path.read_text(encoding="utf-8")
    assert "State / Forecast Validation SF1 Coverage Audit" in markdown

    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "state_vector_v2" in csv_text
