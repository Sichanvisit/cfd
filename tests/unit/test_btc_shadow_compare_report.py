import pandas as pd

from scripts.btc_shadow_compare_report import build_report


def test_build_report_summarizes_actual_vs_shadow():
    df = pd.DataFrame(
        [
            {
                "time": "2026-03-08T10:00:00",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "blocked_by": "",
                "setup_id": "range_lower_reversal_buy",
                "shadow_state_v1": "LOWER_REBOUND_CONFIRM",
                "shadow_action_v1": "BUY",
                "shadow_reason_v1": "lower_rebound_confirm",
                "shadow_buy_force_v1": 1.2,
                "shadow_sell_force_v1": 0.3,
                "shadow_net_force_v1": 0.9,
            },
            {
                "time": "2026-03-08T10:01:00",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "skipped",
                "blocked_by": "clustered_entry_price_zone",
                "setup_id": "range_lower_reversal_buy",
                "shadow_state_v1": "LOWER_REBOUND_CONFIRM",
                "shadow_action_v1": "BUY",
                "shadow_reason_v1": "lower_rebound_confirm",
                "shadow_buy_force_v1": 1.1,
                "shadow_sell_force_v1": 0.4,
                "shadow_net_force_v1": 0.7,
            },
            {
                "time": "2026-03-08T10:02:00",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "wait",
                "blocked_by": "edge_approach_observe",
                "setup_id": "",
                "shadow_state_v1": "LOWER_APPROACH_OBSERVE",
                "shadow_action_v1": "WAIT",
                "shadow_reason_v1": "lower_approach_observe",
                "shadow_buy_force_v1": 0.4,
                "shadow_sell_force_v1": 0.3,
                "shadow_net_force_v1": 0.1,
            },
        ]
    )

    report = build_report(df, symbol="BTCUSD", since="2026-03-08 09:59:00")

    assert report["summary"]["rows_total"] == 3
    assert report["summary"]["entered_rows"] == 1
    assert report["summary"]["shadow_confirm_rows"] == 2
    assert report["compare"]["entered_with_shadow_agree"] == 1
    assert report["compare"]["skipped_but_shadow_confirm"] == 1
