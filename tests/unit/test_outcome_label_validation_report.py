import json

from backend.trading.engine.offline.outcome_label_validation_report import (
    build_outcome_label_validation_report,
    build_outcome_label_validation_report_from_file,
    iter_replay_dataset_rows_from_file,
    write_outcome_label_validation_report,
    write_outcome_label_validation_report_from_file,
)


def _family_payload(*, label_status: str, horizon_bars: int, label_values: dict[str, bool | None], label_polarities: dict[str, str]) -> dict:
    payload = dict(label_values)
    payload["label_status"] = label_status
    payload["metadata"] = {
        "horizon_bars": horizon_bars,
        "label_polarities": dict(label_polarities),
    }
    return payload


def _replay_row(*, symbol: str, transition: dict, management: dict, forecast_branch_evaluation: dict | None = None) -> dict:
    return {
        "row_type": "replay_dataset_row_v1",
        "row_key": f"replay_dataset_row_v1|symbol={symbol}",
        "row_identity": {
            "symbol": symbol,
            "anchor_time_field": "signal_bar_ts",
            "anchor_time_value": 1773149400.0,
        },
        "decision_row": {
            "symbol": symbol,
        },
        "semantic_snapshots": {},
        "forecast_snapshots": {},
        "forecast_branch_evaluation_v1": forecast_branch_evaluation or {},
        "outcome_labels_v1": {
            "transition": transition,
            "trade_management": management,
        },
    }


def test_build_outcome_label_validation_report_summarizes_family_counts_and_alerts():
    forecast_eval_positive = {
        "contract_version": "forecast_branch_evaluation_v1",
        "transition_forecast_vs_outcome": {
            "evaluations": {
                "p_buy_confirm": {
                    "has_forecast": True,
                    "probability": 0.72,
                    "predicted_positive": True,
                    "actual_positive": True,
                    "scorable": True,
                    "hit": True,
                },
            },
        },
        "management_forecast_vs_outcome": {
            "evaluations": {
                "p_continue_favor": {
                    "has_forecast": True,
                    "probability": 0.61,
                    "predicted_positive": True,
                    "actual_positive": True,
                    "scorable": True,
                    "hit": True,
                },
            },
        },
        "gap_signal_quality": {
            "evaluations": {
                "management_continue_fail_gap": {
                    "gap_value": 0.21,
                    "signal_active": True,
                    "predicted_positive": True,
                    "actual_positive": True,
                    "scorable": True,
                    "hit": True,
                },
            },
        },
    }
    forecast_eval_negative = {
        "contract_version": "forecast_branch_evaluation_v1",
        "transition_forecast_vs_outcome": {
            "evaluations": {
                "p_buy_confirm": {
                    "has_forecast": True,
                    "probability": 0.65,
                    "predicted_positive": True,
                    "actual_positive": False,
                    "scorable": True,
                    "hit": False,
                },
            },
        },
        "management_forecast_vs_outcome": {
            "evaluations": {
                "p_continue_favor": {
                    "has_forecast": True,
                    "probability": 0.41,
                    "predicted_positive": False,
                    "actual_positive": False,
                    "scorable": True,
                    "hit": True,
                },
            },
        },
        "gap_signal_quality": {
            "evaluations": {
                "management_continue_fail_gap": {
                    "gap_value": -0.26,
                    "signal_active": True,
                    "predicted_positive": False,
                    "actual_positive": False,
                    "scorable": True,
                    "hit": True,
                },
            },
        },
    }
    rows = [
        _replay_row(
            symbol="NAS100",
            transition=_family_payload(
                label_status="VALID",
                horizon_bars=3,
                label_values={
                    "buy_confirm_success_label": True,
                    "sell_confirm_success_label": False,
                    "false_break_label": False,
                    "reversal_success_label": False,
                    "continuation_success_label": True,
                },
                label_polarities={
                    "buy_confirm_success_label": "POSITIVE",
                    "sell_confirm_success_label": "NEGATIVE",
                    "false_break_label": "NEGATIVE",
                    "reversal_success_label": "NEGATIVE",
                    "continuation_success_label": "POSITIVE",
                },
            ),
            management=_family_payload(
                label_status="VALID",
                horizon_bars=6,
                label_values={
                    "continue_favor_label": True,
                    "fail_now_label": False,
                    "recover_after_pullback_label": False,
                    "reach_tp1_label": True,
                    "opposite_edge_reach_label": True,
                    "better_reentry_if_cut_label": False,
                },
                label_polarities={
                    "continue_favor_label": "POSITIVE",
                    "fail_now_label": "NEGATIVE",
                    "recover_after_pullback_label": "NEGATIVE",
                    "reach_tp1_label": "POSITIVE",
                    "opposite_edge_reach_label": "POSITIVE",
                    "better_reentry_if_cut_label": "NEGATIVE",
                },
            ),
            forecast_branch_evaluation=forecast_eval_positive,
        ),
        _replay_row(
            symbol="NAS100",
            transition=_family_payload(
                label_status="VALID",
                horizon_bars=3,
                label_values={
                    "buy_confirm_success_label": False,
                    "sell_confirm_success_label": True,
                    "false_break_label": True,
                    "reversal_success_label": False,
                    "continuation_success_label": False,
                },
                label_polarities={
                    "buy_confirm_success_label": "NEGATIVE",
                    "sell_confirm_success_label": "POSITIVE",
                    "false_break_label": "POSITIVE",
                    "reversal_success_label": "NEGATIVE",
                    "continuation_success_label": "NEGATIVE",
                },
            ),
            management=_family_payload(
                label_status="VALID",
                horizon_bars=6,
                label_values={
                    "continue_favor_label": False,
                    "fail_now_label": True,
                    "recover_after_pullback_label": False,
                    "reach_tp1_label": False,
                    "opposite_edge_reach_label": False,
                    "better_reentry_if_cut_label": True,
                },
                label_polarities={
                    "continue_favor_label": "NEGATIVE",
                    "fail_now_label": "POSITIVE",
                    "recover_after_pullback_label": "NEGATIVE",
                    "reach_tp1_label": "NEGATIVE",
                    "opposite_edge_reach_label": "NEGATIVE",
                    "better_reentry_if_cut_label": "POSITIVE",
                },
            ),
            forecast_branch_evaluation=forecast_eval_negative,
        ),
        _replay_row(
            symbol="BTCUSD",
            transition=_family_payload(
                label_status="AMBIGUOUS",
                horizon_bars=3,
                label_values={
                    "buy_confirm_success_label": None,
                    "sell_confirm_success_label": None,
                    "false_break_label": None,
                    "reversal_success_label": None,
                    "continuation_success_label": None,
                },
                label_polarities={
                    "buy_confirm_success_label": "UNKNOWN",
                    "sell_confirm_success_label": "UNKNOWN",
                    "false_break_label": "UNKNOWN",
                    "reversal_success_label": "UNKNOWN",
                    "continuation_success_label": "UNKNOWN",
                },
            ),
            management=_family_payload(
                label_status="NO_POSITION_CONTEXT",
                horizon_bars=6,
                label_values={
                    "continue_favor_label": None,
                    "fail_now_label": None,
                    "recover_after_pullback_label": None,
                    "reach_tp1_label": None,
                    "opposite_edge_reach_label": None,
                    "better_reentry_if_cut_label": None,
                },
                label_polarities={
                    "continue_favor_label": "UNKNOWN",
                    "fail_now_label": "UNKNOWN",
                    "recover_after_pullback_label": "UNKNOWN",
                    "reach_tp1_label": "UNKNOWN",
                    "opposite_edge_reach_label": "UNKNOWN",
                    "better_reentry_if_cut_label": "UNKNOWN",
                },
            ),
        ),
        _replay_row(
            symbol="BTCUSD",
            transition=_family_payload(
                label_status="CENSORED",
                horizon_bars=3,
                label_values={
                    "buy_confirm_success_label": None,
                    "sell_confirm_success_label": None,
                    "false_break_label": None,
                    "reversal_success_label": None,
                    "continuation_success_label": None,
                },
                label_polarities={
                    "buy_confirm_success_label": "UNKNOWN",
                    "sell_confirm_success_label": "UNKNOWN",
                    "false_break_label": "UNKNOWN",
                    "reversal_success_label": "UNKNOWN",
                    "continuation_success_label": "UNKNOWN",
                },
            ),
            management=_family_payload(
                label_status="VALID",
                horizon_bars=6,
                label_values={
                    "continue_favor_label": False,
                    "fail_now_label": True,
                    "recover_after_pullback_label": False,
                    "reach_tp1_label": False,
                    "opposite_edge_reach_label": False,
                    "better_reentry_if_cut_label": False,
                },
                label_polarities={
                    "continue_favor_label": "NEGATIVE",
                    "fail_now_label": "POSITIVE",
                    "recover_after_pullback_label": "NEGATIVE",
                    "reach_tp1_label": "NEGATIVE",
                    "opposite_edge_reach_label": "NEGATIVE",
                    "better_reentry_if_cut_label": "NEGATIVE",
                },
            ),
        ),
    ]

    report = build_outcome_label_validation_report(rows)

    assert report["report_type"] == "outcome_label_validation_report_v1"
    assert report["report_contract"] == "validation_report_v1"
    assert report["rows_total"] == 4
    assert report["symbols"] == ["BTCUSD", "NAS100"]
    assert report["label_quality_summary_v1"]["rows_total"] == 4
    assert report["label_quality_summary_v1"]["ambiguous_rows"] == 1
    assert report["label_quality_summary_v1"]["censored_rows"] == 1

    assert report["transition"]["rows_total"] == 4
    assert report["transition"]["scorable_rows"] == 2
    assert report["transition"]["unknown_ratio"] == 0.5
    assert report["transition"]["censored_ratio"] == 0.25
    assert report["transition"]["status_counts"] == {
        "AMBIGUOUS": 1,
        "CENSORED": 1,
        "VALID": 2,
    }
    assert report["transition"]["label_counts"]["buy_confirm_success_label"]["positive"] == 1
    assert report["transition"]["label_counts"]["buy_confirm_success_label"]["negative"] == 1
    assert report["transition"]["label_counts"]["buy_confirm_success_label"]["unknown"] == 2
    assert report["transition"]["symbol_distribution"]["BTCUSD"]["rows"] == 2
    assert report["transition"]["symbol_distribution"]["BTCUSD"]["unknown_ratio"] == 1.0
    assert report["transition"]["horizon_distribution"]["3"]["rows"] == 4
    assert any(alert["code"] == "high_unknown_ratio" for alert in report["transition"]["alerts"])
    assert any(alert["code"] == "symbol_low_scorable_coverage" and alert["target"] == "BTCUSD" for alert in report["transition"]["alerts"])

    assert report["management"]["rows_total"] == 4
    assert report["management"]["scorable_rows"] == 3
    assert report["management"]["unknown_ratio"] == 0.25
    assert report["management"]["label_counts"]["continue_favor_label"]["positive"] == 1
    assert report["management"]["label_counts"]["continue_favor_label"]["negative"] == 2
    assert report["management"]["label_counts"]["continue_favor_label"]["unknown"] == 1
    assert report["management"]["status_counts"]["NO_POSITION_CONTEXT"] == 1
    assert report["management"]["horizon_distribution"]["6"]["rows"] == 4
    assert any(alert["code"] == "symbol_low_scorable_coverage" and alert["target"] == "BTCUSD" for alert in report["management"]["alerts"])
    assert report["forecast_branch_performance_v1"]["transition_forecast_vs_outcome"]["p_buy_confirm"]["rows"] == 2
    assert report["forecast_branch_performance_v1"]["transition_forecast_vs_outcome"]["p_buy_confirm"]["hit_count"] == 1
    assert report["forecast_branch_performance_v1"]["management_forecast_vs_outcome"]["p_continue_favor"]["hit_count"] == 2
    assert report["forecast_branch_performance_v1"]["gap_signal_quality"]["management_continue_fail_gap"]["hit_count"] == 2


def test_write_outcome_label_validation_report_writes_json(tmp_path):
    rows = [
        _replay_row(
            symbol="NAS100",
            transition=_family_payload(
                label_status="VALID",
                horizon_bars=3,
                label_values={
                    "buy_confirm_success_label": True,
                    "sell_confirm_success_label": False,
                    "false_break_label": False,
                    "reversal_success_label": False,
                    "continuation_success_label": True,
                },
                label_polarities={
                    "buy_confirm_success_label": "POSITIVE",
                    "sell_confirm_success_label": "NEGATIVE",
                    "false_break_label": "NEGATIVE",
                    "reversal_success_label": "NEGATIVE",
                    "continuation_success_label": "POSITIVE",
                },
            ),
            management=_family_payload(
                label_status="VALID",
                horizon_bars=6,
                label_values={
                    "continue_favor_label": True,
                    "fail_now_label": False,
                    "recover_after_pullback_label": False,
                    "reach_tp1_label": True,
                    "opposite_edge_reach_label": True,
                    "better_reentry_if_cut_label": False,
                },
                label_polarities={
                    "continue_favor_label": "POSITIVE",
                    "fail_now_label": "NEGATIVE",
                    "recover_after_pullback_label": "NEGATIVE",
                    "reach_tp1_label": "POSITIVE",
                    "opposite_edge_reach_label": "POSITIVE",
                    "better_reentry_if_cut_label": "NEGATIVE",
                },
            ),
        ),
    ]

    out_path = write_outcome_label_validation_report(rows, output_dir=tmp_path)

    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["report_type"] == "outcome_label_validation_report_v1"
    assert payload["transition"]["rows_total"] == 1
    assert payload["management"]["rows_total"] == 1


def test_validation_report_file_helpers_load_jsonl_and_write_report(tmp_path):
    replay_path = tmp_path / "rows.jsonl"
    replay_path.write_text(
        json.dumps(
            _replay_row(
                symbol="NAS100",
                transition=_family_payload(
                    label_status="VALID",
                    horizon_bars=3,
                    label_values={
                        "buy_confirm_success_label": True,
                        "sell_confirm_success_label": False,
                        "false_break_label": False,
                        "reversal_success_label": False,
                        "continuation_success_label": True,
                    },
                    label_polarities={
                        "buy_confirm_success_label": "POSITIVE",
                        "sell_confirm_success_label": "NEGATIVE",
                        "false_break_label": "NEGATIVE",
                        "reversal_success_label": "NEGATIVE",
                        "continuation_success_label": "POSITIVE",
                    },
                ),
                management=_family_payload(
                    label_status="VALID",
                    horizon_bars=6,
                    label_values={
                        "continue_favor_label": True,
                        "fail_now_label": False,
                        "recover_after_pullback_label": False,
                        "reach_tp1_label": True,
                        "opposite_edge_reach_label": True,
                        "better_reentry_if_cut_label": False,
                    },
                    label_polarities={
                        "continue_favor_label": "POSITIVE",
                        "fail_now_label": "NEGATIVE",
                        "recover_after_pullback_label": "NEGATIVE",
                        "reach_tp1_label": "POSITIVE",
                        "opposite_edge_reach_label": "POSITIVE",
                        "better_reentry_if_cut_label": "NEGATIVE",
                    },
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    rows = iter_replay_dataset_rows_from_file(replay_path)
    assert len(rows) == 1
    report = build_outcome_label_validation_report_from_file(replay_path)
    assert report["rows_total"] == 1
    out_path = write_outcome_label_validation_report_from_file(replay_path, output_dir=tmp_path)
    assert out_path.exists()
