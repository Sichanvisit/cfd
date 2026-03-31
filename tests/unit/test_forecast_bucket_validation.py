import importlib.util
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "forecast_bucket_validation.py"
spec = importlib.util.spec_from_file_location("forecast_bucket_validation", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_bucket_label_respects_configured_boundaries():
    assert module.bucket_label(0.00) == "0.00~0.05"
    assert module.bucket_label(0.0499) == "0.00~0.05"
    assert module.bucket_label(0.05) == "0.05~0.10"
    assert module.bucket_label(0.10) == "0.10~0.20"
    assert module.bucket_label(0.20) == "0.20~0.35"
    assert module.bucket_label(0.35) == "0.35+"


def test_build_bucket_validation_report_computes_monotonic_transition_proxy_rates():
    entry_df = pd.DataFrame(
        [
            {
                "time": "2026-03-10T10:00:00",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "wait",
                "observe_confirm_v1": '{"action":"WAIT","state":"OBSERVE"}',
                "transition_forecast_v1": '{"p_buy_confirm":0.03,"p_sell_confirm":0.01,"p_false_break":0.40,"p_reversal_success":0.01,"p_continuation_success":0.01}',
                "trade_management_forecast_v1": '{"p_continue_favor":0.04,"p_fail_now":0.08,"p_recover_after_pullback":0.03,"p_reach_tp1":0.02,"p_opposite_edge_reach":0.01,"p_better_reentry_if_cut":0.05}',
                "transition_side_separation": "0.02",
                "transition_confirm_fake_gap": "-0.37",
                "transition_reversal_continuation_gap": "0.0",
                "management_continue_fail_gap": "-0.04",
                "management_recover_reentry_gap": "-0.02",
            },
            {
                "time": "2026-03-10T10:01:00",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "observe_confirm_v1": '{"action":"BUY","state":"LOWER_REBOUND_CONFIRM"}',
                "transition_forecast_v1": '{"p_buy_confirm":0.12,"p_sell_confirm":0.01,"p_false_break":0.06,"p_reversal_success":0.20,"p_continuation_success":0.05}',
                "trade_management_forecast_v1": '{"p_continue_favor":0.18,"p_fail_now":0.06,"p_recover_after_pullback":0.20,"p_reach_tp1":0.16,"p_opposite_edge_reach":0.08,"p_better_reentry_if_cut":0.07}',
                "transition_side_separation": "0.11",
                "transition_confirm_fake_gap": "0.06",
                "transition_reversal_continuation_gap": "0.15",
                "management_continue_fail_gap": "0.12",
                "management_recover_reentry_gap": "0.13",
            },
            {
                "time": "2026-03-10T10:02:00",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "observe_confirm_v1": '{"action":"BUY","state":"LOWER_REBOUND_CONFIRM"}',
                "transition_forecast_v1": '{"p_buy_confirm":0.38,"p_sell_confirm":0.02,"p_false_break":0.05,"p_reversal_success":0.45,"p_continuation_success":0.08}',
                "trade_management_forecast_v1": '{"p_continue_favor":0.42,"p_fail_now":0.09,"p_recover_after_pullback":0.36,"p_reach_tp1":0.35,"p_opposite_edge_reach":0.22,"p_better_reentry_if_cut":0.10}',
                "transition_side_separation": "0.36",
                "transition_confirm_fake_gap": "0.33",
                "transition_reversal_continuation_gap": "0.37",
                "management_continue_fail_gap": "0.33",
                "management_recover_reentry_gap": "0.26",
            },
        ]
    )
    closed_history = pd.DataFrame()

    report = module.build_bucket_validation_report(entry_df, closed_history)

    buy_confirm = report["transition"]["p_buy_confirm"]
    false_break = report["transition"]["p_false_break"]

    assert buy_confirm["label_kind"] == "decision_proxy"
    assert buy_confirm["monotonic_non_decreasing"] is True
    assert false_break["labeled_rows"] == 3
    assert report["management"]["p_continue_favor"]["labeled_rows"] == 0
