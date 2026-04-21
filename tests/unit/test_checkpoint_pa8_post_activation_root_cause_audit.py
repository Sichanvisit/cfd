import pandas as pd

from backend.services.checkpoint_pa8_post_activation_root_cause_audit import (
    build_checkpoint_pa8_post_activation_root_cause_audit,
    render_checkpoint_pa8_post_activation_root_cause_audit_markdown,
)


def test_pa8_post_activation_root_cause_audit_marks_filter_rejection_when_rows_exist_but_no_preview_change():
    dataset = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-13T11:45:56+09:00",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "HOLD",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "current_profit": 0.2,
                "giveback_ratio": 0.0,
                "runtime_hold_quality_score": 0.4,
                "runtime_partial_exit_ev": 0.5,
                "runtime_full_exit_risk": 0.1,
                "runtime_continuation_odds": 0.9,
                "runtime_reversal_odds": 0.2,
                "position_side": "BUY",
                "source": "exit_manage_hold",
                "checkpoint_id": "BTC_TEST_001",
            }
        ]
    )
    payload = build_checkpoint_pa8_post_activation_root_cause_audit(
        resolved_dataset=dataset,
        activation_payloads={
            "BTCUSD": {"active_state": {"activated_at": "2026-04-13T10:00:00+09:00"}},
            "NAS100": {"active_state": {"activated_at": "2026-04-13T10:00:00+09:00"}},
            "XAUUSD": {"active_state": {"activated_at": "2026-04-13T10:00:00+09:00"}},
        },
    )

    btc_row = next(row for row in payload["rows"] if row["symbol"] == "BTCUSD")
    assert btc_row["post_activation_row_count"] == 1
    assert btc_row["preview_changed_row_count"] == 0
    assert btc_row["root_cause_code"] == "preview_filter_rejection_dominant"


def test_pa8_post_activation_root_cause_markdown_renders_counts():
    markdown = render_checkpoint_pa8_post_activation_root_cause_audit_markdown(
        {
            "summary": {
                "generated_at": "2026-04-13T17:00:00+09:00",
                "dominant_root_cause_ko": "활성화 이후 row는 있으나 preview 후보 규칙에 거의 걸리지 않음",
                "recommended_next_action": "inspect_preview_filter_scope_before_lowering_pa8_thresholds",
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "activated_at": "2026-04-11T13:16:03+09:00",
                    "post_activation_row_count": 1486,
                    "preview_changed_row_count": 0,
                    "eligible_row_count": 0,
                    "root_cause_ko": "활성화 이후 row는 있으나 preview 후보 규칙에 거의 걸리지 않음",
                    "preview_reason_counts": {"preview_surface_out_of_scope": 814},
                    "recommended_next_action": "collect_more_symbol_preview_rows",
                }
            ],
        }
    )

    assert "PA8 Post-Activation Root Cause Audit" in markdown
    assert "preview_surface_out_of_scope" in markdown
    assert "BTCUSD" in markdown
