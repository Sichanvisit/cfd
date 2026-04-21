import json

from backend.services.bounded_rollout_signoff_criteria import (
    build_bounded_rollout_signoff_criteria,
    render_bounded_rollout_signoff_criteria_markdown,
)


def test_bounded_rollout_signoff_criteria_marks_btc_canary_ready_for_manual_signoff() -> None:
    review_manifest_payload = {
        "rows": [
            {
                "manifest_id": "bounded_rollout_review_manifest::BTCUSD::initial_entry_surface",
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "adapter_mode": "btc_observe_relief_adapter",
                "rollout_mode": "review_canary_only",
                "sample_row_count": 15,
                "strong_row_count": 7,
                "positive_count": 10,
                "negative_count": 5,
                "unlabeled_ratio": 0.0,
                "local_failure_burden": 0.333333,
                "guardrail_contract": json.dumps(
                    {
                        "allow_live_override": False,
                        "allowed_surface": "initial_entry_surface",
                        "allowed_symbol": "BTCUSD",
                        "max_canary_size_multiplier": 0.25,
                        "require_manual_signoff": True,
                        "require_no_unlabeled_rows": True,
                    }
                ),
            }
        ]
    }
    baseline_payload = {
        "baseline_locked": True,
        "reentry_elapsed_ms_threshold": 200.0,
        "symbol_metrics": [
            {
                "symbol": "BTCUSD",
                "elapsed_ms": 91.968,
            }
        ],
    }
    regression_payload = {
        "reentry_required": False,
        "comparisons": [
            {
                "symbol": "BTCUSD",
                "baseline_elapsed_ms": 91.968,
                "current_elapsed_ms": 91.968,
                "status": "healthy",
            }
        ],
    }

    frame, summary = build_bounded_rollout_signoff_criteria(
        bounded_rollout_review_manifest_payload=review_manifest_payload,
        entry_performance_baseline_payload=baseline_payload,
        entry_performance_regression_watch_payload=regression_payload,
    )
    markdown = render_bounded_rollout_signoff_criteria_markdown(summary, frame)

    assert summary["ready_for_manual_signoff_count"] == 1
    row = frame.iloc[0]
    assert row["dataset_gate_state"] == "PASS"
    assert row["performance_gate_state"] == "PASS"
    assert row["guardrail_gate_state"] == "PASS"
    assert row["signoff_state"] == "READY_FOR_MANUAL_SIGNOFF"
    assert row["recommended_decision"] == "APPROVE_REVIEW_CANARY_PENDING_MANUAL_SIGNOFF"
    assert "Bounded Rollout Signoff Criteria" in markdown


def test_bounded_rollout_signoff_criteria_holds_when_performance_regression_requires_reentry() -> None:
    review_manifest_payload = {
        "rows": [
            {
                "manifest_id": "bounded_rollout_review_manifest::BTCUSD::initial_entry_surface",
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "adapter_mode": "btc_observe_relief_adapter",
                "rollout_mode": "review_canary_only",
                "sample_row_count": 15,
                "strong_row_count": 7,
                "positive_count": 10,
                "negative_count": 5,
                "unlabeled_ratio": 0.0,
                "local_failure_burden": 0.333333,
                "guardrail_contract": json.dumps(
                    {
                        "allow_live_override": False,
                        "allowed_surface": "initial_entry_surface",
                        "allowed_symbol": "BTCUSD",
                        "max_canary_size_multiplier": 0.25,
                        "require_manual_signoff": True,
                        "require_no_unlabeled_rows": True,
                    }
                ),
            }
        ]
    }
    baseline_payload = {
        "baseline_locked": True,
        "reentry_elapsed_ms_threshold": 200.0,
        "symbol_metrics": [{"symbol": "BTCUSD", "elapsed_ms": 250.0}],
    }
    regression_payload = {
        "reentry_required": True,
        "comparisons": [
            {
                "symbol": "BTCUSD",
                "baseline_elapsed_ms": 91.968,
                "current_elapsed_ms": 250.0,
                "status": "regressed",
            }
        ],
    }

    frame, summary = build_bounded_rollout_signoff_criteria(
        bounded_rollout_review_manifest_payload=review_manifest_payload,
        entry_performance_baseline_payload=baseline_payload,
        entry_performance_regression_watch_payload=regression_payload,
    )

    assert summary["hold_count"] == 1
    row = frame.iloc[0]
    assert row["performance_gate_state"] == "HOLD"
    assert row["signoff_state"] == "HOLD_BEFORE_SIGNOFF"
    assert "performance_regression_reentry_required" in row["signoff_blockers"]


def test_bounded_rollout_signoff_criteria_uses_symbol_specific_reentry_requirement() -> None:
    review_manifest_payload = {
        "rows": [
            {
                "manifest_id": "bounded_rollout_review_manifest::XAUUSD::initial_entry_surface",
                "market_family": "XAUUSD",
                "surface_name": "initial_entry_surface",
                "adapter_mode": "xau_initial_entry_selective_adapter",
                "rollout_mode": "review_canary_only",
                "sample_row_count": 15,
                "strong_row_count": 8,
                "positive_count": 9,
                "negative_count": 6,
                "unlabeled_ratio": 0.0,
                "local_failure_burden": 0.2,
                "guardrail_contract": json.dumps(
                    {
                        "allow_live_override": False,
                        "allowed_surface": "initial_entry_surface",
                        "allowed_symbol": "XAUUSD",
                        "max_canary_size_multiplier": 0.25,
                        "require_manual_signoff": True,
                        "require_no_unlabeled_rows": True,
                    }
                ),
            }
        ]
    }
    baseline_payload = {
        "baseline_locked": True,
        "reentry_elapsed_ms_threshold": 200.0,
        "symbol_metrics": [{"symbol": "XAUUSD", "elapsed_ms": 105.902}],
    }
    regression_payload = {
        "reentry_required": True,
        "comparisons": [
            {
                "symbol": "XAUUSD",
                "baseline_elapsed_ms": 105.902,
                "current_elapsed_ms": 149.816,
                "status": "healthy",
                "reentry_required": False,
            }
        ],
    }

    frame, summary = build_bounded_rollout_signoff_criteria(
        bounded_rollout_review_manifest_payload=review_manifest_payload,
        entry_performance_baseline_payload=baseline_payload,
        entry_performance_regression_watch_payload=regression_payload,
    )

    assert summary["ready_for_manual_signoff_count"] == 1
    row = frame.iloc[0]
    assert row["performance_gate_state"] == "PASS"
    assert row["signoff_state"] == "READY_FOR_MANUAL_SIGNOFF"
