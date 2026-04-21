import pandas as pd

from backend.services.path_checkpoint_backfill_value_normalization_audit import (
    build_checkpoint_backfill_value_normalization_audit,
)


def test_build_checkpoint_backfill_value_normalization_audit_detects_source_scale_mismatch() -> None:
    resolved = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T15:19:12+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "current_profit": -378.0,
                "giveback_ratio": 0.000026,
                "source": "closed_trade_hold_backfill",
                "checkpoint_id": "XAU_CP003",
            },
            {
                "generated_at": "2026-04-10T16:16:53+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "current_profit": -186.0,
                "giveback_ratio": 0.000054,
                "source": "closed_trade_hold_backfill",
                "checkpoint_id": "XAU_CP003",
            },
            {
                "generated_at": "2026-04-10T17:07:01+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "PARTIAL_THEN_HOLD",
                "runtime_proxy_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_best_management_action_label": "WAIT",
                "current_profit": -0.03,
                "giveback_ratio": 0.333333,
                "source": "open_trade_backfill",
                "checkpoint_id": "XAU_CP003",
            },
            {
                "generated_at": "2026-04-10T22:03:46+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "current_profit": 3.11,
                "giveback_ratio": 0.0,
                "source": "exit_manage_runner",
                "checkpoint_id": "XAU_CP004",
            },
        ]
    )
    review_payload = {
        "group_rows": [
            {
                "group_key": (
                    "XAUUSD | continuation_hold_surface | RUNNER_CHECK | "
                    "runner_secured_continuation | runner_secured_continuation | WAIT"
                ),
                "review_disposition": "mixed_backfill_value_scale_review",
            }
        ]
    }

    payload = build_checkpoint_backfill_value_normalization_audit(
        resolved,
        review_processor_payload=review_payload,
    )

    assert payload["summary"]["target_group_count"] == 1
    row = payload["group_rows"][0]
    assert row["audit_state"] == "source_scale_incompatibility_likely"
    assert row["scale_ratio_hint"] is not None
    assert row["scale_ratio_hint"] > 10.0
    assert row["backfill_source_share"] == 0.75
