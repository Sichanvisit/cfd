import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "state_forecast_validation_detail_to_csv_activation_projection.py"
)
spec = importlib.util.spec_from_file_location(
    "state_forecast_validation_detail_to_csv_activation_projection",
    SCRIPT_PATH,
)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


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
        "decision_row_key",
        "replay_row_key",
        "runtime_snapshot_key",
        "trade_link_key",
    ]


def _write_detail(path: Path, payloads: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(
                json.dumps(
                    {
                        "record_type": "entry_decision_detail",
                        "schema_version": "entry_decision_detail_v1",
                        "row_key": payload.get("decision_row_key") or payload.get("replay_row_key") or "",
                        "payload": payload,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def test_build_bf6_projection_report_matches_detail_rows_and_projects_sections(tmp_path):
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)

    entry_csv = trades_root / "entry_decisions.csv"
    detail_jsonl = trades_root / "entry_decisions.detail.jsonl"

    matched_key = "decision|BTCUSD|1"
    common_features = {
        "metadata": {
            "semantic_forecast_inputs_v2": {
                "state_harvest": {"session_regime_state": "SESSION_EXPANSION"},
                "secondary_harvest": {
                    "advanced_input_activation_state": "ADVANCED_ACTIVE",
                    "order_book_state": "ORDER_BOOK_ACTIVE",
                    "tick_flow_state": "TICK_FLOW_ACTIVE",
                },
            }
        }
    }
    entry_rows = [
        {
            "time": "2026-03-31T10:00:00",
            "symbol": "BTCUSD",
            "signal_timeframe": "15M",
            "outcome": "ENTERED",
            "consumer_check_side": "BUY",
            "consumer_check_stage": "READY",
            "observe_confirm_v1": _wrap({"action": "BUY", "state": "CONFIRM"}),
            "forecast_features_v1": _wrap(common_features),
            "transition_forecast_v1": _wrap({"p_buy_confirm": 0.84, "p_sell_confirm": 0.04, "p_false_break": 0.08}),
            "trade_management_forecast_v1": _wrap({"p_continue_favor": 0.79, "p_fail_now": 0.12}),
            "forecast_gap_metrics_v1": "{}",
            "decision_row_key": matched_key,
            "replay_row_key": matched_key,
            "runtime_snapshot_key": "runtime|btc|1",
            "trade_link_key": "",
        }
    ]
    _write_csv(entry_csv, _entry_fieldnames(), entry_rows)

    detail_payloads = [
        {
            "time": "2026-03-31T10:00:00",
            "symbol": "BTCUSD",
            "signal_timeframe": "15M",
            "decision_row_key": matched_key,
            "replay_row_key": matched_key,
            "runtime_snapshot_key": "runtime|btc|1",
            "trade_link_key": "",
            "forecast_features_v1": _wrap(common_features),
            "transition_forecast_v1": _wrap(
                {
                    "p_buy_confirm": 0.84,
                    "p_sell_confirm": 0.04,
                    "p_false_break": 0.08,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {},
                                "barrier_harvest": {},
                                "secondary_harvest": {"advanced_input_activation_state": True},
                            }
                        }
                    },
                }
            ),
            "trade_management_forecast_v1": _wrap(
                {
                    "p_continue_favor": 0.79,
                    "p_fail_now": 0.12,
                    "metadata": {
                        "semantic_forecast_inputs_v2_usage_v1": {
                            "grouped_usage": {
                                "state_harvest": {"session_regime_state": True},
                                "belief_harvest": {"dominant_side": True},
                                "barrier_harvest": {},
                                "secondary_harvest": {"advanced_input_activation_state": True},
                            }
                        }
                    },
                }
            ),
        }
    ]
    _write_detail(detail_jsonl, detail_payloads)

    report = module.build_state_forecast_validation_detail_to_csv_activation_projection_report(
        trades_root=trades_root,
        max_files=1,
        max_rows_per_file=10,
        min_labeled_rows=1,
        now=datetime(2026, 3, 31, 12, 0, 0),
    )

    summary = dict(report["projection_summary"])
    assert summary["sampled_detail_rows"] == 1
    assert summary["matched_projection_rows"] == 1
    assert summary["exact_decision_row_key_matches"] == 1
    assert summary["recommended_next_step"] == "BF7_close_out_and_handoff"

    activation_rows = list(report["activation_slice_projection_rows"])
    assert any(
        row["slice_key"] == "ADVANCED_ACTIVE" and row["metric_name"] == "p_buy_confirm"
        for row in activation_rows
    )

    section_rows = list(report["section_value_projection_rows"])
    transition_secondary = next(
        row
        for row in section_rows
        if row["branch_role"] == "transition_branch" and row["harvest_section"] == "secondary_harvest"
    )
    assert transition_secondary["section_used_rows"] == 1
    assert transition_secondary["section_used_ratio"] == 1.0


def test_build_bf6_projection_report_tracks_unmatched_detail_rows(tmp_path):
    trades_root = tmp_path / "trades"
    trades_root.mkdir(parents=True)

    entry_csv = trades_root / "entry_decisions.csv"
    detail_jsonl = trades_root / "entry_decisions.detail.jsonl"

    entry_rows = [
        {
            "time": "2026-03-31T10:00:00",
            "symbol": "NAS100",
            "signal_timeframe": "15M",
            "outcome": "WAIT",
            "consumer_check_side": "BUY",
            "consumer_check_stage": "OBSERVE",
            "observe_confirm_v1": _wrap({"action": "WAIT", "state": "OBSERVE"}),
            "forecast_features_v1": _wrap(
                {
                    "metadata": {
                        "semantic_forecast_inputs_v2": {
                            "state_harvest": {"session_regime_state": "SESSION_BALANCED"},
                            "secondary_harvest": {
                                "advanced_input_activation_state": "ADVANCED_PARTIAL",
                                "order_book_state": "ORDER_BOOK_UNAVAILABLE",
                            },
                        }
                    }
                }
            ),
            "transition_forecast_v1": _wrap({"p_buy_confirm": 0.12, "p_sell_confirm": 0.07, "p_false_break": 0.66}),
            "trade_management_forecast_v1": _wrap({"p_continue_favor": 0.21, "p_fail_now": 0.31}),
            "forecast_gap_metrics_v1": "{}",
            "decision_row_key": "decision|NAS100|1",
            "replay_row_key": "decision|NAS100|1",
            "runtime_snapshot_key": "runtime|nas|1",
            "trade_link_key": "",
        }
    ]
    _write_csv(entry_csv, _entry_fieldnames(), entry_rows)

    _write_detail(
        detail_jsonl,
        [
            {
                "time": "2026-03-31T10:10:00",
                "symbol": "XAUUSD",
                "signal_timeframe": "15M",
                "decision_row_key": "decision|XAUUSD|missing",
                "replay_row_key": "decision|XAUUSD|missing",
                "forecast_features_v1": _wrap({"metadata": {"semantic_forecast_inputs_v2": {"state_harvest": {}, "secondary_harvest": {}}}}),
                "transition_forecast_v1": _wrap({"p_buy_confirm": 0.55, "p_sell_confirm": 0.21, "p_false_break": 0.15}),
                "trade_management_forecast_v1": _wrap({"p_continue_favor": 0.41, "p_fail_now": 0.18}),
            }
        ],
    )

    report = module.build_state_forecast_validation_detail_to_csv_activation_projection_report(
        trades_root=trades_root,
        max_files=1,
        max_rows_per_file=10,
        min_labeled_rows=1,
        now=datetime(2026, 3, 31, 12, 0, 0),
    )

    summary = dict(report["projection_summary"])
    assert summary["matched_projection_rows"] == 0
    assert summary["unmatched_projection_rows"] == 1
    assert report["match_type_counts"]["unmatched"] == 1
    assert report["projection_gap_rows"][0]["symbol"] == "XAUUSD"
    assert report["projection_assessment"]["primary_gap_call"] == "projection_match_coverage_limited"
