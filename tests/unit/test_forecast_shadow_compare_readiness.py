import importlib.util
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "forecast_shadow_compare_readiness.py"
spec = importlib.util.spec_from_file_location("forecast_shadow_compare_readiness", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_shadow_compare_readiness_report_marks_transition_ready_and_management_pending():
    entry_df = pd.DataFrame(
        [
            {
                "time": "2026-03-10T10:00:00",
                "symbol": "BTCUSD",
                "action": "SELL",
                "outcome": "entered",
                "observe_confirm_v1": '{"action":"SELL","state":"UPPER_REJECT_CONFIRM"}',
                "transition_forecast_v1": '{"p_buy_confirm":0.04,"p_sell_confirm":0.41,"p_false_break":0.18,"p_reversal_success":0.49,"p_continuation_success":0.12,"metadata":{"mapper_version":"transition_forecast_v1_fc10"}}',
                "trade_management_forecast_v1": '{"p_continue_favor":0.51,"p_fail_now":0.15,"p_recover_after_pullback":0.42,"p_reach_tp1":0.33,"p_opposite_edge_reach":0.18,"p_better_reentry_if_cut":0.14,"metadata":{"mapper_version":"trade_management_forecast_v1_fc5"}}',
                "transition_side_separation": "0.37",
                "transition_confirm_fake_gap": "0.23",
                "transition_reversal_continuation_gap": "0.37",
                "management_continue_fail_gap": "0.36",
                "management_recover_reentry_gap": "0.28",
            },
            {
                "time": "2026-03-10T10:02:00",
                "symbol": "BTCUSD",
                "action": "SELL",
                "outcome": "entered",
                "observe_confirm_v1": '{"action":"SELL","state":"UPPER_REJECT_CONFIRM"}',
                "transition_forecast_v1": '{"p_buy_confirm":0.03,"p_sell_confirm":0.36,"p_false_break":0.16,"p_reversal_success":0.46,"p_continuation_success":0.11,"metadata":{"mapper_version":"transition_forecast_v1_fc10"}}',
                "trade_management_forecast_v1": '{"p_continue_favor":0.44,"p_fail_now":0.13,"p_recover_after_pullback":0.37,"p_reach_tp1":0.29,"p_opposite_edge_reach":0.17,"p_better_reentry_if_cut":0.12,"metadata":{"mapper_version":"trade_management_forecast_v1_fc5"}}',
                "transition_side_separation": "0.33",
                "transition_confirm_fake_gap": "0.20",
                "transition_reversal_continuation_gap": "0.35",
                "management_continue_fail_gap": "0.31",
                "management_recover_reentry_gap": "0.25",
            },
            {
                "time": "2026-03-10T10:04:00",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "wait",
                "observe_confirm_v1": '{"action":"WAIT","state":"UPPER_EDGE_OBSERVE"}',
                "transition_forecast_v1": '{"p_buy_confirm":0.05,"p_sell_confirm":0.07,"p_false_break":0.31,"p_reversal_success":0.12,"p_continuation_success":0.09,"metadata":{"mapper_version":"transition_forecast_v1_fc10"}}',
                "trade_management_forecast_v1": '{"p_continue_favor":0.09,"p_fail_now":0.17,"p_recover_after_pullback":0.06,"p_reach_tp1":0.04,"p_opposite_edge_reach":0.03,"p_better_reentry_if_cut":0.10,"metadata":{"mapper_version":"trade_management_forecast_v1_fc5"}}',
                "transition_side_separation": "0.02",
                "transition_confirm_fake_gap": "-0.24",
                "transition_reversal_continuation_gap": "0.03",
                "management_continue_fail_gap": "-0.08",
                "management_recover_reentry_gap": "-0.04",
            },
        ]
    )
    runtime_status = {
        "latest_signal_by_symbol": {
            "BTCUSD": {
                "observe_confirm_v1": {"action": "WAIT", "state": "UPPER_EDGE_OBSERVE"},
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.04,
                    "p_sell_confirm": 0.08,
                    "metadata": {"mapper_version": "transition_forecast_v1_fc10"},
                },
            },
            "XAUUSD": {
                "observe_confirm_v1": {"action": "WAIT", "state": "MIDDLE_WAIT"},
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.03,
                    "p_sell_confirm": 0.04,
                    "metadata": {"mapper_version": "transition_forecast_v1_fc10"},
                },
            },
        }
    }

    report = module.build_shadow_compare_readiness_report(entry_df, pd.DataFrame(), runtime_status)

    assert report["baseline_contract"]["baseline_contract"] == "forecast_rule_baseline_v1"
    assert report["calibration_contract"]["contract_version"] == "forecast_calibration_v1"
    assert report["transition_readiness"]["overall_status"] == "READY_FOR_MODEL_COMPARE"
    assert report["management_readiness"]["overall_status"] == "PENDING_OUTCOME_LABELER"
    assert report["overall_status"] == "TRANSITION_READY_MANAGEMENT_PENDING"
    assert report["transition_readiness"]["current_runtime_wait_acceptance"]["wait_pass_rate"] == 1.0
    assert report["transition_readiness"]["recent_confirm_acceptance"]["confirm_gap_pass_rate"] == 1.0
