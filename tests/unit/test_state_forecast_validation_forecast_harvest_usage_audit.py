import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "state_forecast_validation_forecast_harvest_usage_audit.py"
spec = importlib.util.spec_from_file_location("state_forecast_validation_forecast_harvest_usage_audit", SCRIPT_PATH)
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


def test_build_usage_audit_detects_branch_trace_and_secondary_gap(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    sf2_path = out_dir / "state_forecast_validation_sf2_activation_latest.json"
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)

    _write_json(
        sf2_path,
        {
            "activation_summary": {
                "order_book_state_active_like_ratio": 0.0003,
                "tick_state_active_like_ratio": 0.8997,
            }
        },
    )

    detail_path = trades_root / "entry_decisions.detail.jsonl"
    rows = [
        {
            "payload": {
                "time": "2026-03-31T00:10:00",
                "signal_timeframe": "15M",
                "symbol": "BTCUSD",
                "forecast_features_v1": _wrap_payload(
                    {
                        "metadata": {
                            "semantic_forecast_inputs_v2": {
                                "state_harvest": {"session_regime_state": "SESSION_EDGE_ROTATION"}
                            }
                        }
                    }
                ),
                "transition_forecast_v1": _wrap_payload(
                    {
                        "metadata": {
                            "mapper_version": "transition_forecast_v1_fc11",
                            "score_formula_version": "transition_fc11_scene_transition_refinement_v1",
                            "semantic_forecast_inputs_v2_usage_v1": {
                                "branch_role": "transition_branch",
                                "usage_status": "harvested_with_usage_trace",
                                "direct_math_used_fields": [
                                    "session_regime_state",
                                    "event_risk_state",
                                    "dominant_side",
                                    "edge_turn_relief_v1",
                                    "advanced_input_activation_state",
                                    "tick_flow_state",
                                    "order_book_state",
                                ],
                                "harvest_only_fields": [],
                                "grouped_usage": {
                                    "state_harvest": {
                                        "session_regime_state": True,
                                        "event_risk_state": True,
                                    },
                                    "belief_harvest": {
                                        "dominant_side": True,
                                    },
                                    "barrier_harvest": {
                                        "edge_turn_relief_v1": True,
                                    },
                                    "secondary_harvest": {
                                        "advanced_input_activation_state": True,
                                        "tick_flow_state": True,
                                        "order_book_state": True,
                                    },
                                },
                            },
                        }
                    }
                ),
                "trade_management_forecast_v1": _wrap_payload(
                    {
                        "metadata": {
                            "mapper_version": "trade_management_forecast_v1_fc9",
                            "score_formula_version": "management_fc9_scene_hold_cut_trend_reliability_bridge_v1",
                            "semantic_forecast_inputs_v2_usage_v1": {
                                "branch_role": "trade_management_branch",
                                "usage_status": "harvested_with_usage_trace",
                                "direct_math_used_fields": [
                                    "execution_friction_state",
                                    "dominant_side",
                                    "flip_readiness",
                                    "middle_chop_barrier_v2",
                                    "advanced_input_activation_state",
                                    "tick_flow_state",
                                    "order_book_state",
                                ],
                                "harvest_only_fields": [],
                                "grouped_usage": {
                                    "state_harvest": {
                                        "execution_friction_state": True,
                                    },
                                    "belief_harvest": {
                                        "dominant_side": True,
                                        "flip_readiness": True,
                                    },
                                    "barrier_harvest": {
                                        "middle_chop_barrier_v2": True,
                                    },
                                    "secondary_harvest": {
                                        "advanced_input_activation_state": True,
                                        "tick_flow_state": True,
                                        "order_book_state": True,
                                    },
                                },
                            },
                        }
                    }
                ),
                "forecast_gap_metrics_v1": _wrap_payload(
                    {
                        "metadata": {
                            "semantic_forecast_inputs_v2_usage_v1": {
                                "usage_status": "derived_from_branch_outputs_only"
                            }
                        }
                    }
                ),
            }
        },
        {
            "payload": {
                "time": "2026-03-31T00:15:00",
                "signal_timeframe": "15M",
                "symbol": "NAS100",
                "forecast_features_v1": _wrap_payload(
                    {
                        "metadata": {
                            "semantic_forecast_inputs_v2": {
                                "state_harvest": {"session_regime_state": "SESSION_BALANCED"}
                            }
                        }
                    }
                ),
                "transition_forecast_v1": _wrap_payload(
                    {
                        "metadata": {
                            "mapper_version": "transition_forecast_v1_fc11",
                            "score_formula_version": "transition_fc11_scene_transition_refinement_v1",
                        }
                    }
                ),
            }
        },
    ]
    _write_detail(detail_path, rows)

    report = module.build_state_forecast_validation_forecast_harvest_usage_report(
        trades_root=trades_root,
        sf2_report_path=sf2_path,
        max_files=10,
        max_rows_per_file=10,
        now=datetime.fromisoformat("2026-03-31T00:30:00"),
    )

    summary = report["usage_summary"]
    assessment = report["usage_assessment"]
    branch_rows = {row["branch_role"]: row for row in report["branch_summary_rows"]}
    field_rows = {
        (row["branch_role"], row["harvest_section"], row["harvest_field"]): row
        for row in report["field_usage_rows"]
    }
    suspicious = {row["candidate_type"]: row for row in report["suspicious_usage_candidates"]}

    assert summary["sampled_row_count"] == 2
    assert summary["transition_forecast_present_ratio"] == 1.0
    assert summary["trade_management_forecast_present_ratio"] == 0.5
    assert summary["transition_usage_trace_present_ratio"] == 0.5
    assert summary["trade_management_usage_trace_present_ratio"] == 0.5
    assert summary["gap_metrics_usage_trace_present_ratio"] == 0.5
    assert summary["secondary_harvest_direct_use_field_count"] == 6
    assert assessment["secondary_harvest_direct_gap_suspected"] is False
    assert assessment["recommended_next_step"] == "SF4_forecast_feature_value_slice_audit"
    assert branch_rows["transition_branch"]["direct_math_field_unique_count"] == 7
    assert branch_rows["trade_management_branch"]["direct_math_field_unique_count"] == 7
    assert field_rows[("transition_branch", "state_harvest", "session_regime_state")]["used_ratio"] == 1.0
    assert field_rows[("transition_branch", "secondary_harvest", "order_book_state")]["used_ratio"] == 1.0
    assert field_rows[("trade_management_branch", "state_harvest", "execution_friction_state")]["used_ratio"] == 1.0
    assert suspicious["secondary_harvest_direct_usage_gap"]["used_field_count"] == 6


def test_write_usage_audit_writes_outputs(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    sf2_path = out_dir / "state_forecast_validation_sf2_activation_latest.json"
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)

    _write_json(
        sf2_path,
        {
            "activation_summary": {
                "order_book_state_active_like_ratio": 0.0,
                "tick_state_active_like_ratio": 1.0,
            }
        },
    )

    detail_path = trades_root / "entry_decisions.detail.jsonl"
    _write_detail(
        detail_path,
        [
            {
                "payload": {
                    "time": "2026-03-31T01:00:00",
                    "signal_timeframe": "15M",
                    "symbol": "XAUUSD",
                    "forecast_features_v1": _wrap_payload(
                        {"metadata": {"semantic_forecast_inputs_v2": {"state_harvest": {"session_regime_state": "SESSION_EXPANSION"}}}}
                    ),
                    "transition_forecast_v1": _wrap_payload(
                        {
                            "metadata": {
                                "mapper_version": "transition_forecast_v1_fc11",
                                "score_formula_version": "transition_fc11_scene_transition_refinement_v1",
                                "semantic_forecast_inputs_v2_usage_v1": {
                                    "branch_role": "transition_branch",
                                    "usage_status": "harvested_with_usage_trace",
                                    "direct_math_used_fields": ["session_regime_state"],
                                    "harvest_only_fields": [],
                                    "grouped_usage": {
                                        "state_harvest": {"session_regime_state": True},
                                        "belief_harvest": {},
                                        "barrier_harvest": {},
                                        "secondary_harvest": {},
                                    },
                                },
                            }
                        }
                    ),
                }
            }
        ],
    )

    result = module.write_state_forecast_validation_forecast_harvest_usage_report(
        trades_root=trades_root,
        sf2_report_path=sf2_path,
        output_dir=out_dir,
        max_files=5,
        max_rows_per_file=5,
        now=datetime.fromisoformat("2026-03-31T00:40:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["usage_summary"]["sampled_row_count"] == 1
    assert payload["usage_assessment"]["recommended_next_step"] == "SF4_forecast_feature_value_slice_audit"

    markdown = md_path.read_text(encoding="utf-8")
    assert "State / Forecast Validation SF3 Harvest Usage Audit" in markdown

    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "transition_branch" in csv_text
    assert "session_regime_state" in csv_text
