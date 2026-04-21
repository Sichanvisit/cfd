import pandas as pd

from backend.services.path_checkpoint_pa7_review_processor import (
    _build_normalized_review_handoff,
    build_checkpoint_pa7_review_processor,
)


def test_build_checkpoint_pa7_review_processor_separates_policy_gap_and_confidence_groups() -> None:
    rows = [
                {
                    "generated_at": "2026-04-11T00:00:00+09:00",
                    "symbol": "NAS100",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                    "runtime_continuation_odds": 0.31,
                    "runtime_reversal_odds": 0.46,
                    "runtime_hold_quality_score": 0.28,
                    "runtime_partial_exit_ev": 0.36,
                    "runtime_full_exit_risk": 0.54,
                "current_profit": -0.6,
                    "giveback_ratio": 0.99,
                    "source": "exit_manage_hold",
                },
    ]
    rows.append(
        {
            "generated_at": "2026-04-11T00:00:04+09:00",
            "symbol": "NAS100",
            "surface_name": "follow_through_surface",
            "checkpoint_type": "INITIAL_PUSH",
            "management_row_family": "active_open_loss",
            "checkpoint_rule_family_hint": "active_open_loss",
            "management_action_label": "PARTIAL_EXIT",
            "runtime_proxy_management_action_label": "PARTIAL_EXIT",
            "hindsight_best_management_action_label": "WAIT",
            "hindsight_quality_tier": "manual_exception",
            "hindsight_manual_exception_required": True,
            "runtime_continuation_odds": 0.31,
            "runtime_reversal_odds": 0.46,
            "runtime_hold_quality_score": 0.28,
            "runtime_partial_exit_ev": 0.36,
            "runtime_full_exit_risk": 0.54,
            "current_profit": -0.7,
            "giveback_ratio": 0.99,
            "source": "exit_manage_hold",
        }
    )
    for idx in range(10):
        rows.append(
            {
                "generated_at": f"2026-04-11T00:01:{idx:02d}+09:00",
                    "symbol": "BTCUSD",
                    "surface_name": "continuation_hold_surface",
                    "checkpoint_type": "RUNNER_CHECK",
                    "management_row_family": "runner_secured_continuation",
                    "checkpoint_rule_family_hint": "runner_secured_continuation",
                    "management_action_label": "WAIT",
                    "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.32,
                "runtime_partial_exit_ev": 0.44,
                "runtime_full_exit_risk": 0.49,
                "current_profit": 1.1 - (idx * 0.01),
                "giveback_ratio": 0.08,
                "source": "exit_manage_runner",
            }
        )
    frame = pd.DataFrame(rows)

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=5, sample_rows_per_group=2)
    groups = {row["group_key"]: row for row in payload["group_rows"]}

    policy_row = next(row for row in groups.values() if row["symbol"] == "NAS100")
    assert policy_row["review_disposition"] == "mixed_wait_boundary_review"
    assert policy_row["review_priority"] == "medium"
    assert policy_row["resolved_baseline_action_label"] == "PARTIAL_EXIT"

    confidence_row = next(row for row in groups.values() if row["symbol"] == "BTCUSD")
    assert confidence_row["review_disposition"] == "resolved_by_current_policy"
    assert confidence_row["review_priority"] == "low"
    assert confidence_row["resolved_baseline_action_label"] == "WAIT"


def test_build_checkpoint_pa7_review_processor_marks_groups_resolved_by_current_policy() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-11T00:03:00+09:00",
                "symbol": "NAS100",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_continuation_odds": 0.905,
                "runtime_reversal_odds": 0.5735,
                "runtime_hold_quality_score": 0.43917,
                "runtime_partial_exit_ev": 0.36129,
                "runtime_full_exit_risk": 0.546525,
                "current_profit": -1.13,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-11T00:03:05+09:00",
                "symbol": "NAS100",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_continuation_odds": 0.905,
                "runtime_reversal_odds": 0.5735,
                "runtime_hold_quality_score": 0.43917,
                "runtime_partial_exit_ev": 0.36129,
                "runtime_full_exit_risk": 0.546525,
                "current_profit": -1.21,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "resolved_by_current_policy"
    assert row["policy_replay_action_label"] == "WAIT"
    assert row["policy_replay_match_rate"] == 1.0


def test_build_checkpoint_pa7_review_processor_marks_singleton_groups_resolved_by_current_policy() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-11T00:17:19.394584+09:00",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "LATE_TREND_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "PARTIAL_THEN_HOLD",
                "runtime_proxy_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_best_management_action_label": "PARTIAL_EXIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_continuation_odds": 0.643,
                "runtime_reversal_odds": 0.684,
                "runtime_hold_quality_score": 0.37813,
                "runtime_partial_exit_ev": 0.54836,
                "runtime_full_exit_risk": 0.33246,
                "current_profit": 0.66,
                "giveback_ratio": 0.0,
                "source": "exit_manage_runner",
                "position_side": "SELL",
                "position_size_fraction": 1.0,
                "runner_secured": True,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_PROFIT",
            }
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "resolved_by_current_policy"
    assert row["policy_replay_action_label"] == "PARTIAL_EXIT"
    assert row["policy_replay_match_rate"] == 1.0


def test_build_checkpoint_pa7_review_processor_marks_hydration_gap_groups() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-11T00:02:00+09:00",
                "symbol": "XAUUSD",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "FULL_EXIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": None,
                "runtime_partial_exit_ev": None,
                "runtime_full_exit_risk": None,
                "current_profit": -0.4,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-11T00:02:05+09:00",
                "symbol": "XAUUSD",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "FULL_EXIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": None,
                "runtime_partial_exit_ev": None,
                "runtime_full_exit_risk": None,
                "current_profit": -0.5,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "baseline_hydration_gap"
    assert row["review_priority"] == "medium"
    assert row["blank_baseline_share"] == 1.0
    assert row["missing_score_share"] == 1.0


def test_build_checkpoint_pa7_review_processor_marks_resolved_hydration_gap_groups() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-11T00:02:00+09:00",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": None,
                "runtime_partial_exit_ev": None,
                "runtime_full_exit_risk": None,
                "current_profit": 1.2,
                "giveback_ratio": 0.1,
                "source": "exit_manage_runner",
            },
            {
                "generated_at": "2026-04-11T00:02:05+09:00",
                "symbol": "BTCUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": None,
                "runtime_partial_exit_ev": None,
                "runtime_full_exit_risk": None,
                "current_profit": 1.1,
                "giveback_ratio": 0.08,
                "source": "exit_manage_runner",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "hydration_gap_confirmed_cluster"
    assert row["review_priority"] == "low"
    assert row["blank_baseline_share"] == 1.0
    assert row["missing_score_share"] == 1.0


def test_build_checkpoint_pa7_review_processor_marks_confirmed_hydration_clusters() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-11T00:02:00+09:00",
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "active_flat_profit",
                "checkpoint_rule_family_hint": "active_flat_profit",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": None,
                "runtime_partial_exit_ev": None,
                "runtime_full_exit_risk": None,
                "current_profit": 0.0,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-11T00:02:05+09:00",
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "active_flat_profit",
                "checkpoint_rule_family_hint": "active_flat_profit",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": None,
                "runtime_partial_exit_ev": None,
                "runtime_full_exit_risk": None,
                "current_profit": 0.0,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-11T00:02:10+09:00",
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "active_flat_profit",
                "checkpoint_rule_family_hint": "active_flat_profit",
                "management_action_label": "WAIT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.41,
                "runtime_partial_exit_ev": 0.36,
                "runtime_full_exit_risk": 0.22,
                "current_profit": 0.0,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "hydration_gap_confirmed_cluster"
    assert row["review_priority"] == "low"


def test_build_checkpoint_pa7_review_processor_marks_mixed_backfill_value_scale_groups() -> None:
    frame = pd.DataFrame(
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
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.358182,
                "runtime_partial_exit_ev": 0.397013,
                "runtime_full_exit_risk": 0.565438,
                "current_profit": -378.0,
                "giveback_ratio": 0.000026,
                "source": "closed_trade_hold_backfill",
                "position_side": "BUY",
                "runner_secured": True,
                "position_size_fraction": 1.0,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_LOSS",
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
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.358184,
                "runtime_partial_exit_ev": 0.397017,
                "runtime_full_exit_risk": 0.565431,
                "current_profit": -186.0,
                "giveback_ratio": 0.000054,
                "source": "closed_trade_hold_backfill",
                "position_side": "BUY",
                "runner_secured": True,
                "position_size_fraction": 1.0,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_LOSS",
            },
            {
                "generated_at": "2026-04-10T16:53:42+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.358183,
                "runtime_partial_exit_ev": 0.397015,
                "runtime_full_exit_risk": 0.565434,
                "current_profit": -237.0,
                "giveback_ratio": 0.000042,
                "source": "closed_trade_hold_backfill",
                "position_side": "BUY",
                "runner_secured": True,
                "position_size_fraction": 1.0,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_LOSS",
            },
            {
                "generated_at": "2026-04-10T17:07:01.045546+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "PARTIAL_THEN_HOLD",
                "runtime_proxy_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.37893,
                "runtime_partial_exit_ev": 0.42851,
                "runtime_full_exit_risk": 0.497195,
                "current_profit": -0.03,
                "giveback_ratio": 0.333333,
                "source": "open_trade_backfill",
                "position_side": "BUY",
                "runner_secured": True,
                "position_size_fraction": 1.0,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_LOSS",
            },
            {
                "generated_at": "2026-04-10T17:19:23.772372+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "PARTIAL_THEN_HOLD",
                "runtime_proxy_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.3781,
                "runtime_partial_exit_ev": 0.42725,
                "runtime_full_exit_risk": 0.499925,
                "current_profit": -0.19,
                "giveback_ratio": 0.315789,
                "source": "open_trade_backfill",
                "position_side": "BUY",
                "runner_secured": True,
                "position_size_fraction": 1.0,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_LOSS",
            },
            {
                "generated_at": "2026-04-10T22:03:46.134140+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": None,
                "runtime_partial_exit_ev": None,
                "runtime_full_exit_risk": None,
                "current_profit": 3.11,
                "giveback_ratio": 0.0,
                "source": "exit_manage_runner",
                "position_side": "SELL",
                "runner_secured": True,
                "position_size_fraction": 1.0,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_PROFIT",
            },
            {
                "generated_at": "2026-04-10T22:03:53.548122+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": None,
                "runtime_partial_exit_ev": None,
                "runtime_full_exit_risk": None,
                "current_profit": 3.21,
                "giveback_ratio": 0.0,
                "source": "exit_manage_runner",
                "position_side": "SELL",
                "runner_secured": True,
                "position_size_fraction": 1.0,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_PROFIT",
            },
            {
                "generated_at": "2026-04-10T22:04:00.687216+09:00",
                "symbol": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "management_row_family": "runner_secured_continuation",
                "checkpoint_rule_family_hint": "runner_secured_continuation",
                "management_action_label": "",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": None,
                "runtime_partial_exit_ev": None,
                "runtime_full_exit_risk": None,
                "current_profit": 3.17,
                "giveback_ratio": 0.012461,
                "source": "exit_manage_runner",
                "position_side": "SELL",
                "runner_secured": True,
                "position_size_fraction": 1.0,
                "realized_pnl_state": "LOCKED",
                "unrealized_pnl_state": "OPEN_PROFIT",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "resolved_by_current_policy"
    assert row["review_priority"] == "low"
    assert row["policy_replay_action_label"] == "WAIT"
    assert row["policy_replay_match_rate"] == 1.0
    assert row["normalized_preview_state"] == "not_applicable"


def test_build_normalized_review_handoff_marks_wait_boundary_ready() -> None:
    payload = _build_normalized_review_handoff(
        disposition="mixed_backfill_value_scale_review",
        normalization_preview={
            "normalized_preview_review_disposition": "mixed_wait_boundary_review",
        },
    )

    assert payload["normalized_review_handoff_state"] == "ready"
    assert payload["normalized_review_handoff_disposition"] == "mixed_wait_boundary_review"
    assert payload["normalized_review_handoff_priority"] == "medium"
    assert payload["raw_rule_patch_blocked_by_backfill_scale"] is True


def test_build_checkpoint_pa7_review_processor_marks_mixed_wait_boundary_groups() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-11T00:06:00+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "FIRST_PULLBACK_CHECK",
                "management_row_family": "open_loss_protective",
                "checkpoint_rule_family_hint": "open_loss_protective",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.333164,
                "runtime_partial_exit_ev": 0.326328,
                "runtime_full_exit_risk": 0.514892,
                "current_profit": -0.31,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-11T00:06:05+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "FIRST_PULLBACK_CHECK",
                "management_row_family": "open_loss_protective",
                "checkpoint_rule_family_hint": "open_loss_protective",
                "management_action_label": "WAIT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "runtime_hold_quality_score": 0.284684,
                "runtime_partial_exit_ev": 0.312568,
                "runtime_full_exit_risk": 0.538092,
                "current_profit": -0.31,
                "giveback_ratio": 0.99,
                "source": "exit_manage_hold",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "resolved_by_current_policy"
    assert row["review_priority"] == "low"


def test_build_checkpoint_pa7_review_processor_resolves_near_flat_wait_boundary_as_safe_partial_exit(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "backend.services.path_checkpoint_pa7_review_processor._resolve_policy_replay_action",
        lambda row: "PARTIAL_EXIT",
    )
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-12T20:37:45.057734+09:00",
                "symbol": "BTCUSD",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "LATE_TREND_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.07,
                "giveback_ratio": 0.99,
                "runtime_hold_quality_score": 0.26293,
                "runtime_partial_exit_ev": 0.33541,
                "runtime_full_exit_risk": 0.676625,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-12T20:37:49.639092+09:00",
                "symbol": "BTCUSD",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "LATE_TREND_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.07,
                "giveback_ratio": 0.99,
                "runtime_hold_quality_score": 0.26293,
                "runtime_partial_exit_ev": 0.33541,
                "runtime_full_exit_risk": 0.676625,
                "source": "exit_manage_hold",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "resolved_by_current_policy"
    assert row["review_priority"] == "low"
    assert row["review_reason"] == "near_flat_wait_boundary_already_safely_de_risked_by_partial_exit"


def test_build_checkpoint_pa7_review_processor_resolves_near_flat_first_pullback_wait_cluster(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "backend.services.path_checkpoint_pa7_review_processor._resolve_policy_replay_action",
        lambda row: (
            "PARTIAL_EXIT"
            if str(row.get("generated_at")) == "2026-04-12T18:49:33.463564+09:00"
            else "WAIT"
        ),
    )
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-12T18:32:13.952971+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "FIRST_PULLBACK_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "WAIT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.08,
                "giveback_ratio": 0.99,
                "runtime_hold_quality_score": 0.29344,
                "runtime_partial_exit_ev": 0.30766,
                "runtime_full_exit_risk": 0.557606,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-12T18:32:29.091744+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "FIRST_PULLBACK_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "WAIT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.08,
                "giveback_ratio": 0.99,
                "runtime_hold_quality_score": 0.29344,
                "runtime_partial_exit_ev": 0.30766,
                "runtime_full_exit_risk": 0.557606,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-12T18:49:33.463564+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "FIRST_PULLBACK_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "PARTIAL_EXIT",
                "runtime_proxy_management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.46,
                "giveback_ratio": 0.99,
                "runtime_hold_quality_score": 0.339422,
                "runtime_partial_exit_ev": 0.335828,
                "runtime_full_exit_risk": 0.494308,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-12T19:00:10.000000+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "FIRST_PULLBACK_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "WAIT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.24,
                "giveback_ratio": 0.99,
                "runtime_hold_quality_score": 0.301,
                "runtime_partial_exit_ev": 0.31,
                "runtime_full_exit_risk": 0.52,
                "source": "exit_manage_hold",
            },
            {
                "generated_at": "2026-04-12T19:02:10.000000+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "FIRST_PULLBACK_CHECK",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "WAIT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.25,
                "giveback_ratio": 0.99,
                "runtime_hold_quality_score": 0.305,
                "runtime_partial_exit_ev": 0.31,
                "runtime_full_exit_risk": 0.51,
                "source": "exit_manage_hold",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "resolved_by_current_policy"
    assert row["review_priority"] == "low"
    assert row["review_reason"] == "near_flat_first_pullback_wait_cluster_already_safely_aligned"


def test_build_checkpoint_pa7_review_processor_resolves_initial_push_active_open_loss_wait_boundary_cluster() -> None:
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-12T12:14:29.818652+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "HOLD",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.28,
                "giveback_ratio": 0.99,
                "runtime_continuation_odds": 0.768,
                "runtime_reversal_odds": 0.3915,
                "runtime_hold_quality_score": 0.45078,
                "runtime_partial_exit_ev": 0.30841,
                "runtime_full_exit_risk": 0.399085,
                "source": "exit_manage_hold",
                "position_side": "BUY",
                "position_size_fraction": 1.0,
                "unrealized_pnl_state": "OPEN_LOSS",
                "exit_stage_family": "hold",
            },
            {
                "generated_at": "2026-04-12T18:48:28.366483+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "HOLD",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.49,
                "giveback_ratio": 0.99,
                "runtime_continuation_odds": 0.783517,
                "runtime_reversal_odds": 0.375983,
                "runtime_hold_quality_score": 0.463659,
                "runtime_partial_exit_ev": 0.327962,
                "runtime_full_exit_risk": 0.356723,
                "source": "exit_manage_hold",
                "position_side": "BUY",
                "position_size_fraction": 1.0,
                "unrealized_pnl_state": "OPEN_LOSS",
                "exit_stage_family": "hold",
            },
            {
                "generated_at": "2026-04-12T19:53:35.275243+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "HOLD",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.61,
                "giveback_ratio": 0.99,
                "runtime_continuation_odds": 0.780857,
                "runtime_reversal_odds": 0.378643,
                "runtime_hold_quality_score": 0.461451,
                "runtime_partial_exit_ev": 0.32461,
                "runtime_full_exit_risk": 0.363985,
                "source": "exit_manage_hold",
                "position_side": "BUY",
                "position_size_fraction": 1.0,
                "unrealized_pnl_state": "OPEN_LOSS",
                "exit_stage_family": "hold",
            },
            {
                "generated_at": "2026-04-12T21:04:50+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "WAIT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.10,
                "giveback_ratio": 0.99,
                "runtime_continuation_odds": 0.534,
                "runtime_reversal_odds": 0.5625,
                "runtime_hold_quality_score": 0.2742,
                "runtime_partial_exit_ev": 0.28555,
                "runtime_full_exit_risk": 0.535255,
                "source": "exit_manage_hold",
                "position_side": "BUY",
                "position_size_fraction": 1.0,
                "unrealized_pnl_state": "OPEN_LOSS",
                "exit_stage_family": "hold",
            },
            {
                "generated_at": "2026-04-12T21:29:35+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "WAIT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -0.07,
                "giveback_ratio": 0.99,
                "runtime_continuation_odds": 0.638,
                "runtime_reversal_odds": 0.425,
                "runtime_hold_quality_score": 0.3699,
                "runtime_partial_exit_ev": 0.2871,
                "runtime_full_exit_risk": 0.44091,
                "source": "exit_manage_hold",
                "position_side": "BUY",
                "position_size_fraction": 1.0,
                "unrealized_pnl_state": "OPEN_LOSS",
                "exit_stage_family": "hold",
            },
            {
                "generated_at": "2026-04-12T23:49:51+09:00",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "management_row_family": "active_open_loss",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "WAIT",
                "runtime_proxy_management_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "hindsight_quality_tier": "manual_exception",
                "hindsight_manual_exception_required": True,
                "current_profit": -1.13,
                "giveback_ratio": 0.99,
                "runtime_continuation_odds": 0.652,
                "runtime_reversal_odds": 0.5275,
                "runtime_hold_quality_score": 0.3489,
                "runtime_partial_exit_ev": 0.30425,
                "runtime_full_exit_risk": 0.494765,
                "source": "exit_manage_hold",
                "position_side": "BUY",
                "position_size_fraction": 1.0,
                "unrealized_pnl_state": "OPEN_LOSS",
                "exit_stage_family": "hold",
            },
        ]
    )

    payload = build_checkpoint_pa7_review_processor(frame, top_n_groups=3, sample_rows_per_group=2)
    row = payload["group_rows"][0]

    assert row["review_disposition"] == "resolved_by_current_policy"
    assert row["review_priority"] == "low"
    assert row["policy_replay_action_label"] == "WAIT"
    assert row["policy_replay_match_rate"] == 1.0
