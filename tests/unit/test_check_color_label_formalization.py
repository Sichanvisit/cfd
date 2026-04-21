import pandas as pd

from backend.services.check_color_label_formalization import (
    build_check_color_label_formalization,
)


def test_check_color_label_formalization_maps_initial_followthrough_and_protective_surfaces() -> None:
    manual_wait = pd.DataFrame(
        [
            {
                "annotation_id": "nas_breakout_001",
                "episode_id": "nas_breakout_001",
                "symbol": "NAS100",
                "timeframe": "M1",
                "anchor_side": "BUY",
                "scene_id": "nas_breakout_chart_20260408_open_box_release",
                "chart_context": "screenshot_nas_breakout_case_20260408",
                "box_regime_scope": "upper_box_breakout",
                "anchor_time": "2026-04-08T06:50:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_confidence": "low",
                "manual_wait_teacher_family": "failed_wait",
                "manual_wait_teacher_subtype": "wait_but_missed_move",
                "manual_wait_teacher_usage_bucket": "usable",
                "manual_wait_teacher_polarity": "bad",
                "barrier_main_label_hint": "enter_now",
                "annotation_source": "assistant_breakout_chart_inferred",
                "review_status": "needs_manual_recheck",
                "manual_teacher_confidence": "low",
            },
            {
                "annotation_id": "nas_breakout_002",
                "episode_id": "nas_breakout_002",
                "symbol": "NAS100",
                "timeframe": "M1",
                "anchor_side": "BUY",
                "scene_id": "nas_breakout_chart_20260408_first_pullback_reclaim",
                "chart_context": "screenshot_nas_breakout_case_20260408",
                "box_regime_scope": "upper_box_breakout_pullback",
                "anchor_time": "2026-04-08T07:44:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "low",
                "manual_wait_teacher_family": "timing_improvement",
                "manual_wait_teacher_subtype": "better_entry_after_wait",
                "manual_wait_teacher_usage_bucket": "usable",
                "manual_wait_teacher_polarity": "good",
                "barrier_main_label_hint": "wait_then_enter",
                "annotation_source": "assistant_breakout_chart_inferred",
                "review_status": "needs_manual_recheck",
                "manual_teacher_confidence": "low",
            },
            {
                "annotation_id": "nas_breakout_003",
                "episode_id": "nas_breakout_003",
                "symbol": "NAS100",
                "timeframe": "M1",
                "anchor_side": "SELL",
                "scene_id": "nas_breakout_chart_20260408_final_extension_protective_exit",
                "chart_context": "screenshot_nas_breakout_case_20260408",
                "box_regime_scope": "upper_box_breakout_continuation",
                "anchor_time": "2026-04-08T11:22:00+09:00",
                "manual_wait_teacher_label": "good_wait_protective_exit",
                "manual_wait_teacher_confidence": "low",
                "manual_wait_teacher_family": "protective_exit",
                "manual_wait_teacher_subtype": "profitable_wait_then_exit",
                "manual_wait_teacher_usage_bucket": "usable",
                "manual_wait_teacher_polarity": "good",
                "barrier_main_label_hint": "exit_protect",
                "annotation_source": "assistant_breakout_chart_inferred",
                "review_status": "needs_manual_recheck",
                "manual_teacher_confidence": "low",
            },
            {
                "annotation_id": "xau_runner_001",
                "episode_id": "xau_runner_001",
                "symbol": "XAUUSD",
                "timeframe": "M1",
                "anchor_side": "BUY",
                "scene_id": "xau_runner_hold_extension",
                "chart_context": "runner_hold_extension",
                "box_regime_scope": "trend_extension",
                "anchor_time": "2026-04-09T00:29:12+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "medium",
                "manual_wait_teacher_family": "timing_improvement",
                "manual_wait_teacher_subtype": "better_entry_after_wait",
                "manual_wait_teacher_usage_bucket": "usable",
                "manual_wait_teacher_polarity": "good",
                "barrier_main_label_hint": "wait_then_enter",
                "annotation_source": "chart_annotated",
                "review_status": "accepted_coarse",
                "manual_teacher_confidence": "medium",
            },
        ]
    )
    aligned_seed = pd.DataFrame(
        [
            {
                "episode_id": "nas_breakout_002",
                "symbol": "NAS100",
                "action_target": "ENTER_NOW",
                "continuation_target": "PULLBACK_THEN_CONTINUE",
                "seed_status": "promoted_canonical",
                "seed_grade": "strict",
            },
            {
                "episode_id": "xau_runner_001",
                "symbol": "XAUUSD",
                "action_target": "ENTER_NOW",
                "continuation_target": "CONTINUE_AFTER_BREAK",
                "seed_status": "promoted_canonical",
                "seed_grade": "strict",
            },
        ]
    )

    frame, summary = build_check_color_label_formalization(
        manual_wait,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        aligned_seed,
    )

    assert summary["row_count"] == 4
    assert "initial_entry_surface" in summary["surface_label_family_counts"]
    assert "follow_through_surface" in summary["surface_label_family_counts"]
    assert "protective_exit_surface" in summary["surface_label_family_counts"]
    assert "continuation_hold_surface" in summary["surface_label_family_counts"]
    assert "missed_good_wait_release" in summary["failure_label_counts"]

    initial_row = frame.loc[frame["episode_id"] == "nas_breakout_001"].iloc[0]
    assert initial_row["surface_label_family"] == "initial_entry_surface"
    assert initial_row["surface_label_state"] == "initial_break"
    assert initial_row["surface_action_bias"] == "ENTER_NOW"
    assert initial_row["failure_label"] == "missed_good_wait_release"
    assert initial_row["visual_check_family"] == "check_enter_now"

    follow_row = frame.loc[frame["episode_id"] == "nas_breakout_002"].iloc[0]
    assert follow_row["surface_label_family"] == "follow_through_surface"
    assert follow_row["surface_label_state"] == "pullback_resume"
    assert follow_row["aligned_continuation_target"] == "PULLBACK_THEN_CONTINUE"
    assert follow_row["supervision_strength"] == "strong"

    protect_row = frame.loc[frame["episode_id"] == "nas_breakout_003"].iloc[0]
    assert protect_row["surface_label_family"] == "protective_exit_surface"
    assert protect_row["surface_label_state"] == "protect_exit"
    assert protect_row["surface_action_bias"] == "EXIT_PROTECT"

    runner_row = frame.loc[frame["episode_id"] == "xau_runner_001"].iloc[0]
    assert runner_row["surface_label_family"] == "continuation_hold_surface"
    assert runner_row["surface_label_state"] == "runner_hold"
    assert runner_row["surface_action_bias"] == "HOLD_RUNNER"


def test_check_color_label_formalization_prefers_stronger_duplicate_episode() -> None:
    weaker = pd.DataFrame(
        [
            {
                "annotation_id": "dup_episode_weak",
                "episode_id": "dup_episode",
                "symbol": "BTCUSD",
                "timeframe": "M1",
                "anchor_side": "BUY",
                "chart_context": "current_rich_window_seed",
                "anchor_time": "2026-04-09T03:30:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_family": "failed_wait",
                "manual_wait_teacher_subtype": "wait_but_missed_move",
                "manual_wait_teacher_usage_bucket": "usable",
                "manual_wait_teacher_polarity": "bad",
                "manual_wait_teacher_confidence": "low",
                "barrier_main_label_hint": "block_bias",
                "annotation_source": "assistant_current_rich_seed",
                "review_status": "needs_manual_recheck",
                "manual_teacher_confidence": "low",
            }
        ]
    )
    stronger = pd.DataFrame(
        [
            {
                "annotation_id": "dup_episode_strong",
                "episode_id": "dup_episode",
                "symbol": "BTCUSD",
                "timeframe": "M1",
                "anchor_side": "BUY",
                "chart_context": "first_clean_upside_launch",
                "anchor_time": "2026-04-09T03:31:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_family": "failed_wait",
                "manual_wait_teacher_subtype": "wait_but_missed_move",
                "manual_wait_teacher_usage_bucket": "usable",
                "manual_wait_teacher_polarity": "bad",
                "manual_wait_teacher_confidence": "medium",
                "barrier_main_label_hint": "enter_now",
                "annotation_source": "chart_annotated",
                "review_status": "accepted_coarse",
                "manual_teacher_confidence": "medium",
            }
        ]
    )

    frame, summary = build_check_color_label_formalization(
        stronger,
        pd.DataFrame(),
        weaker,
        pd.DataFrame(),
        pd.DataFrame(),
    )

    assert summary["row_count"] == 1
    row = frame.iloc[0]
    assert row["annotation_id"] == "dup_episode_strong"
    assert row["source_group"] == "manual_chart"
    assert row["supervision_strength"] == "strong"
