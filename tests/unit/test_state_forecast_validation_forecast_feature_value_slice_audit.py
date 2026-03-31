import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "state_forecast_validation_forecast_feature_value_slice_audit.py"
)
spec = importlib.util.spec_from_file_location(
    "state_forecast_validation_forecast_feature_value_slice_audit",
    SCRIPT_PATH,
)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _wrap(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _entry_fieldnames() -> list[str]:
    return [
        "time",
        "symbol",
        "signal_timeframe",
        "outcome",
        "consumer_check_side",
        "consumer_check_stage",
        "observe_confirm_v1",
        "forecast_features_v1",
        "transition_forecast_v1",
        "trade_management_forecast_v1",
        "forecast_gap_metrics_v1",
    ]


def _closed_fieldnames() -> list[str]:
    return ["symbol", "direction", "open_time", "profit"]


def test_build_value_slice_audit_measures_transition_and_management_value(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    sf3_path = out_dir / "state_forecast_validation_sf3_usage_latest.json"
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)

    _write_json(
        sf3_path,
        {
            "usage_summary": {
                "secondary_harvest_direct_use_field_count": 0,
            }
        },
    )

    entry_rows = [
        {
            "time": "2026-03-31 10:00:00",
            "symbol": "BTCUSD",
            "signal_timeframe": "15M",
            "outcome": "WAIT",
            "consumer_check_side": "BUY",
            "consumer_check_stage": "PROBE",
            "observe_confirm_v1": _wrap({"action": "BUY", "state": "CONFIRM"}),
            "forecast_features_v1": _wrap(
                {
                    "metadata": {
                        "semantic_forecast_inputs_v2": {
                            "state_harvest": {"session_regime_state": "SESSION_EXPANSION"},
                            "secondary_harvest": {
                                "advanced_input_activation_state": "ADVANCED_PARTIAL",
                                "order_book_state": "UNAVAILABLE",
                            },
                        }
                    }
                }
            ),
            "transition_forecast_v1": _wrap(
                {
                    "p_buy_confirm": 0.85,
                    "p_sell_confirm": 0.04,
                    "p_false_break": 0.06,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {},
                                "barrier_harvest": {},
                                "secondary_harvest": {},
                            }
                        }
                    },
                }
            ),
            "trade_management_forecast_v1": _wrap(
                {
                    "p_continue_favor": 0.81,
                    "p_fail_now": 0.08,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {"dominant_side": True},
                                "barrier_harvest": {},
                                "secondary_harvest": {},
                            }
                        }
                    },
                }
            ),
            "forecast_gap_metrics_v1": "{}",
        },
        {
            "time": "2026-03-31 10:05:00",
            "symbol": "BTCUSD",
            "signal_timeframe": "15M",
            "outcome": "SKIPPED",
            "consumer_check_side": "SELL",
            "consumer_check_stage": "OBSERVE",
            "observe_confirm_v1": _wrap({"action": "WAIT", "state": "OBSERVE"}),
            "forecast_features_v1": _wrap(
                {
                    "metadata": {
                        "semantic_forecast_inputs_v2": {
                            "state_harvest": {"session_regime_state": "SESSION_EXPANSION"},
                            "secondary_harvest": {
                                "advanced_input_activation_state": "ADVANCED_PARTIAL",
                                "order_book_state": "UNAVAILABLE",
                            },
                        }
                    }
                }
            ),
            "transition_forecast_v1": _wrap(
                {
                    "p_buy_confirm": 0.05,
                    "p_sell_confirm": 0.07,
                    "p_false_break": 0.72,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {},
                                "barrier_harvest": {},
                                "secondary_harvest": {},
                            }
                        }
                    },
                }
            ),
            "trade_management_forecast_v1": _wrap(
                {
                    "p_continue_favor": 0.31,
                    "p_fail_now": 0.44,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {"dominant_side": True},
                                "barrier_harvest": {},
                                "secondary_harvest": {},
                            }
                        }
                    },
                }
            ),
            "forecast_gap_metrics_v1": "{}",
        },
        {
            "time": "2026-03-31 10:10:00",
            "symbol": "XAUUSD",
            "signal_timeframe": "15M",
            "outcome": "ENTERED",
            "consumer_check_side": "BUY",
            "consumer_check_stage": "READY",
            "observe_confirm_v1": _wrap({"action": "BUY", "state": "CONFIRM"}),
            "forecast_features_v1": _wrap(
                {
                    "metadata": {
                        "semantic_forecast_inputs_v2": {
                            "state_harvest": {"session_regime_state": "SESSION_BALANCED"},
                            "secondary_harvest": {
                                "advanced_input_activation_state": "ADVANCED_ACTIVE",
                                "order_book_state": "UNAVAILABLE",
                            },
                        }
                    }
                }
            ),
            "transition_forecast_v1": _wrap(
                {
                    "p_buy_confirm": 0.78,
                    "p_sell_confirm": 0.05,
                    "p_false_break": 0.08,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {},
                                "barrier_harvest": {},
                                "secondary_harvest": {},
                            }
                        }
                    },
                }
            ),
            "trade_management_forecast_v1": _wrap(
                {
                    "p_continue_favor": 0.82,
                    "p_fail_now": 0.12,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {"dominant_side": True},
                                "barrier_harvest": {"edge_turn_relief_v1": True},
                                "secondary_harvest": {},
                            }
                        }
                    },
                }
            ),
            "forecast_gap_metrics_v1": "{}",
        },
        {
            "time": "2026-03-31 10:20:00",
            "symbol": "XAUUSD",
            "signal_timeframe": "15M",
            "outcome": "ENTERED",
            "consumer_check_side": "SELL",
            "consumer_check_stage": "READY",
            "observe_confirm_v1": _wrap({"action": "SELL", "state": "CONFIRM"}),
            "forecast_features_v1": _wrap(
                {
                    "metadata": {
                        "semantic_forecast_inputs_v2": {
                            "state_harvest": {"session_regime_state": "SESSION_BALANCED"},
                            "secondary_harvest": {
                                "advanced_input_activation_state": "ADVANCED_ACTIVE",
                                "order_book_state": "UNAVAILABLE",
                            },
                        }
                    }
                }
            ),
            "transition_forecast_v1": _wrap(
                {
                    "p_buy_confirm": 0.09,
                    "p_sell_confirm": 0.83,
                    "p_false_break": 0.06,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {},
                                "barrier_harvest": {},
                                "secondary_harvest": {},
                            }
                        }
                    },
                }
            ),
            "trade_management_forecast_v1": _wrap(
                {
                    "p_continue_favor": 0.11,
                    "p_fail_now": 0.88,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {"dominant_side": True},
                                "barrier_harvest": {"edge_turn_relief_v1": True},
                                "secondary_harvest": {},
                            }
                        }
                    },
                }
            ),
            "forecast_gap_metrics_v1": "{}",
        },
    ]
    _write_csv(trades_root / "entry_decisions.csv", _entry_fieldnames(), entry_rows)
    _write_csv(
        trades_root / "trade_closed_history.csv",
        _closed_fieldnames(),
        [
            {
                "symbol": "XAUUSD",
                "direction": "BUY",
                "open_time": "2026-03-31 10:10:30",
                "profit": "12.5",
            },
            {
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-03-31 10:20:20",
                "profit": "-9.5",
            },
        ],
    )

    report = module.build_state_forecast_validation_forecast_feature_value_slice_report(
        trades_root=trades_root,
        sf3_report_path=sf3_path,
        now=datetime.fromisoformat("2026-03-31T12:00:00"),
    )

    summary = report["value_summary"]
    metric_rows = {row["metric_name"]: row for row in report["metric_value_rows"]}
    suspicious = {row["candidate_type"]: row for row in report["suspicious_value_candidates"]}
    harvest_rows = {
        (row["branch_role"], row["harvest_section"]): row
        for row in report["harvest_section_value_rows"]
    }

    assert summary["decision_row_count"] == 4
    assert summary["entered_rows"] == 2
    assert summary["matched_trade_rows"] == 2
    assert summary["management_actual_labeled_rows"] == 2
    assert metric_rows["p_buy_confirm"]["separation_gap"] > 0.0
    assert metric_rows["p_false_break"]["separation_gap"] > 0.0
    assert metric_rows["p_continue_favor"]["separation_gap"] > 0.0
    assert metric_rows["p_fail_now"]["separation_gap"] > 0.0
    assert suspicious["secondary_harvest_value_unmeasurable"]["sf3_secondary_harvest_direct_use_field_count"] == 0
    assert suspicious["management_actual_label_coverage"]["actual_labeled_rows"] == 2
    assert harvest_rows[("transition_branch", "state_harvest")]["section_used_ratio"] == 1.0
    assert harvest_rows[("transition_branch", "secondary_harvest")]["section_used_ratio"] == 0.0


def test_write_value_slice_audit_writes_outputs(tmp_path):
    out_dir = tmp_path / "analysis"
    out_dir.mkdir(parents=True)
    sf3_path = out_dir / "state_forecast_validation_sf3_usage_latest.json"
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)

    _write_json(sf3_path, {"usage_summary": {"secondary_harvest_direct_use_field_count": 0}})
    _write_csv(
        trades_root / "entry_decisions.csv",
        _entry_fieldnames(),
        [
            {
                "time": "2026-03-31 10:00:00",
                "symbol": "BTCUSD",
                "signal_timeframe": "15M",
                "outcome": "WAIT",
                "consumer_check_side": "BUY",
                "consumer_check_stage": "PROBE",
                "observe_confirm_v1": _wrap({"action": "BUY", "state": "CONFIRM"}),
                "forecast_features_v1": _wrap(
                    {
                        "metadata": {
                            "semantic_forecast_inputs_v2": {
                                "state_harvest": {"session_regime_state": "SESSION_EXPANSION"},
                                "secondary_harvest": {"advanced_input_activation_state": "ADVANCED_PARTIAL"},
                            }
                        }
                    }
                ),
                "transition_forecast_v1": _wrap({"p_buy_confirm": 0.8, "p_sell_confirm": 0.1, "p_false_break": 0.1}),
                "trade_management_forecast_v1": _wrap({"p_continue_favor": 0.7, "p_fail_now": 0.2}),
                "forecast_gap_metrics_v1": "{}",
            }
        ],
    )
    _write_csv(trades_root / "trade_closed_history.csv", _closed_fieldnames(), [])

    result = module.write_state_forecast_validation_forecast_feature_value_slice_report(
        trades_root=trades_root,
        sf3_report_path=sf3_path,
        output_dir=out_dir,
        now=datetime.fromisoformat("2026-03-31T12:30:00"),
    )

    assert Path(result["latest_json_path"]).exists()
    assert Path(result["latest_csv_path"]).exists()
    assert Path(result["latest_markdown_path"]).exists()
