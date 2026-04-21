import pandas as pd

from backend.services.manual_vs_heuristic_comparison import (
    build_manual_vs_heuristic_comparison_report,
)


def test_manual_vs_heuristic_comparison_builds_partial_match_from_nearby_entry_decision() -> None:
    annotations = pd.DataFrame(
        [
            {
                "episode_id": "btc_episode_001",
                "symbol": "BTCUSD",
                "timeframe": "M1",
                "anchor_side": "BUY",
                "anchor_time": "2026-04-06T10:00:00+09:00",
                "anchor_price": 100.0,
                "ideal_entry_time": "2026-04-06T10:03:00+09:00",
                "ideal_entry_price": 99.5,
                "ideal_exit_time": "2026-04-06T10:20:00+09:00",
                "ideal_exit_price": 101.0,
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "medium",
                "annotation_note": "manual answer key sample",
                "annotation_source": "chart_annotated",
            }
        ]
    )
    heuristic = pd.DataFrame(
        [
            {
                "time": "2026-04-06T10:01:00+09:00",
                "signal_bar_ts": "",
                "symbol": "BTCUSD",
                "action": "",
                "observe_action": "BUY",
                "observe_side": "BUY",
                "observe_reason": "reclaim_confirm",
                "blocked_by": "",
                "core_reason": "wait_bias_hold",
                "entry_wait_decision": "prefer_wait",
                "barrier_candidate_recommended_family": "wait_bias",
                "barrier_candidate_supporting_label": "correct_wait",
                "barrier_action_hint_confidence": "medium",
                "barrier_action_hint_reason_summary": "wait_for_cleaner_entry",
                "forecast_decision_hint": "observe_favor",
                "forecast_state25_scene_family": "box_reclaim",
                "belief_candidate_recommended_family": "reduce_alert",
                "belief_action_hint_reason_summary": "fragile_thesis",
                "heuristic_time": pd.Timestamp("2026-04-06 10:01:00"),
            }
        ]
    )

    report, summary = build_manual_vs_heuristic_comparison_report(
        annotations,
        heuristic,
        max_gap_minutes=30,
        created_at="2026-04-06T12:00:00+09:00",
        review_owner="test",
    )

    assert len(report) == 1
    row = report.iloc[0].to_dict()
    assert row["manual_truth_source_bucket"] == "canonical_chart_reviewed"
    assert row["manual_truth_review_state"] == "reviewed"
    assert row["heuristic_evidence_source_kind"] == "manual_only"
    assert row["heuristic_evidence_quality"] == "missing"
    assert row["heuristic_barrier_main_label"] == "correct_wait"
    assert row["manual_vs_barrier_match"] == "match"
    assert row["manual_vs_wait_family_match"] == "partial_match"
    assert row["overall_alignment_grade"] == "partial_match"
    assert row["miss_type"] == ""
    assert row["correction_worthiness_class"] == "not_correction_worthy"
    assert row["canonical_promotion_readiness"] == "ready"
    assert row["canonical_promotion_recommendation"] == "promote_to_canonical"
    assert summary["heuristic_matched_rows"] == 1
    assert summary["match_reason_counts"]["matched"] == 1


def test_manual_vs_heuristic_comparison_marks_unknown_when_no_nearby_heuristic_snapshot() -> None:
    annotations = pd.DataFrame(
        [
            {
                "episode_id": "nas_episode_001",
                "symbol": "NAS100",
                "timeframe": "M1",
                "anchor_side": "SELL",
                "anchor_time": "2026-04-06T10:00:00+09:00",
                "anchor_price": 100.0,
                "ideal_entry_time": "2026-04-06T10:02:00+09:00",
                "ideal_entry_price": 99.8,
                "ideal_exit_time": "2026-04-06T10:30:00+09:00",
                "ideal_exit_price": 98.2,
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_confidence": "high",
                "annotation_source": "chart_annotated",
            }
        ]
    )
    heuristic = pd.DataFrame(
        [
            {
                "time": "2026-04-06T14:30:00+09:00",
                "signal_bar_ts": "",
                "symbol": "NAS100",
                "action": "",
                "observe_action": "",
                "observe_side": "",
                "observe_reason": "",
                "blocked_by": "",
                "core_reason": "",
                "entry_wait_decision": "",
                "barrier_candidate_recommended_family": "",
                "barrier_candidate_supporting_label": "",
                "barrier_action_hint_confidence": "",
                "barrier_action_hint_reason_summary": "",
                "forecast_decision_hint": "",
                "forecast_state25_scene_family": "",
                "belief_candidate_recommended_family": "",
                "belief_action_hint_reason_summary": "",
                "heuristic_time": pd.Timestamp("2026-04-06 14:30:00"),
            }
        ]
    )

    report, summary = build_manual_vs_heuristic_comparison_report(
        annotations,
        heuristic,
        max_gap_minutes=15,
        created_at="2026-04-06T12:00:00+09:00",
        review_owner="test",
    )

    row = report.iloc[0].to_dict()
    assert row["manual_vs_barrier_match"] == "unknown"
    assert row["manual_vs_wait_family_match"] == "unknown"
    assert row["overall_alignment_grade"] == "unknown"
    assert row["miss_type"] == "insufficient_heuristic_evidence"
    assert row["primary_correction_target"] == "insufficient_owner_coverage"
    assert row["rule_change_readiness"] == "insufficient_evidence"
    assert row["freeze_worthiness_class"] == "freeze_worthy"
    assert summary["heuristic_matched_rows"] == 0
    assert summary["match_reason_counts"]["heuristic_gap_exceeds_limit"] == 1


def test_manual_vs_heuristic_comparison_treats_blank_heuristic_fields_as_unknown_not_mismatch() -> None:
    annotations = pd.DataFrame(
        [
            {
                "episode_id": "xau_episode_001",
                "symbol": "XAUUSD",
                "timeframe": "M1",
                "anchor_side": "SELL",
                "anchor_time": "2026-04-06T10:00:00+09:00",
                "anchor_price": 100.0,
                "ideal_entry_time": "2026-04-06T10:04:00+09:00",
                "ideal_entry_price": 100.4,
                "ideal_exit_time": "2026-04-06T10:40:00+09:00",
                "ideal_exit_price": 99.1,
                "manual_wait_teacher_label": "good_wait_protective_exit",
                "manual_wait_teacher_confidence": "medium",
                "annotation_source": "chart_annotated",
            }
        ]
    )
    heuristic = pd.DataFrame(
        [
            {
                "time": "2026-04-06T10:02:00+09:00",
                "signal_bar_ts": "",
                "symbol": "XAUUSD",
                "action": "",
                "observe_action": "",
                "observe_side": "",
                "observe_reason": "",
                "blocked_by": "",
                "core_reason": "",
                "entry_wait_decision": "",
                "barrier_candidate_recommended_family": float("nan"),
                "barrier_candidate_supporting_label": float("nan"),
                "barrier_action_hint_confidence": float("nan"),
                "barrier_action_hint_reason_summary": float("nan"),
                "forecast_decision_hint": "",
                "forecast_state25_scene_family": "",
                "belief_candidate_recommended_family": "",
                "belief_action_hint_reason_summary": "",
                "heuristic_time": pd.Timestamp("2026-04-06 10:02:00"),
            }
        ]
    )

    report, summary = build_manual_vs_heuristic_comparison_report(
        annotations,
        heuristic,
        max_gap_minutes=30,
        created_at="2026-04-06T12:00:00+09:00",
        review_owner="test",
    )

    row = report.iloc[0].to_dict()
    assert row["manual_vs_barrier_match"] == "unknown"
    assert row["manual_vs_wait_family_match"] == "unknown"
    assert row["overall_alignment_grade"] == "unknown"
    assert row["miss_type"] == "insufficient_heuristic_evidence"
    assert row["heuristic_evidence_source_kind"] == "manual_only"
    assert summary["heuristic_matched_rows"] == 1
    assert summary["match_reason_counts"]["matched"] == 1


def test_manual_vs_heuristic_comparison_uses_global_detail_fallback_when_csv_snapshot_is_blank() -> None:
    annotations = pd.DataFrame(
        [
            {
                "episode_id": "nas_episode_fallback_001",
                "symbol": "NAS100",
                "timeframe": "M1",
                "anchor_side": "BUY",
                "anchor_time": "2026-04-03T15:20:00+09:00",
                "anchor_price": 100.0,
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "medium",
                "annotation_source": "chart_annotated",
            }
        ]
    )
    heuristic = pd.DataFrame(
        [
            {
                "time": "2026-04-03T12:15:00+09:00",
                "signal_bar_ts": 1775196900.0,
                "symbol": "NAS100",
                "action": "",
                "observe_action": "",
                "observe_side": "",
                "observe_reason": "",
                "blocked_by": "",
                "core_reason": "",
                "entry_wait_decision": "",
                "barrier_candidate_recommended_family": "",
                "barrier_candidate_supporting_label": "",
                "barrier_action_hint_confidence": "",
                "barrier_action_hint_reason_summary": "",
                "forecast_decision_hint": "",
                "forecast_state25_scene_family": "",
                "belief_candidate_recommended_family": "",
                "belief_action_hint_reason_summary": "",
                "heuristic_source_file": "entry_decisions.legacy_20260404_000006.csv",
                "heuristic_source_kind": "legacy",
                "heuristic_time": pd.Timestamp("2026-04-03 15:15:00"),
            }
        ]
    )
    fallback = pd.DataFrame(
        [
            {
                "episode_id": "nas_episode_fallback_001",
                "heuristic_source_file": "entry_decisions.legacy_20260404_000006.csv",
                "global_detail_source_file": "entry_decisions.detail.rotate_20260403_123318_780225.jsonl",
                "global_detail_source_kind": "rotate_detail",
                "global_detail_row_found": 1,
                "global_detail_observe_reason": "outer_band_reversal_support_required_observe",
                "global_detail_blocked_by": "outer_band_guard",
                "global_detail_entry_wait_decision": "wait_soft_helper_block",
                "global_detail_core_reason": "core_shadow_observe_wait",
                "global_detail_recoverability_grade": "medium",
            }
        ]
    )

    report, summary = build_manual_vs_heuristic_comparison_report(
        annotations,
        heuristic,
        global_detail_fallback_frame=fallback,
        max_gap_minutes=30,
        created_at="2026-04-06T12:00:00+09:00",
        review_owner="test",
    )

    row = report.iloc[0].to_dict()
    assert row["heuristic_reconstruction_mode"] == "global_detail_fallback"
    assert row["heuristic_reconstruction_source_file"] == "entry_decisions.detail.rotate_20260403_123318_780225.jsonl"
    assert row["heuristic_barrier_main_label"] == "correct_wait"
    assert row["heuristic_wait_family"] == "timing_improvement"
    assert row["heuristic_evidence_source_kind"] == "global_detail_fallback"
    assert row["heuristic_evidence_recoverability_grade"] == "medium"
    assert row["manual_vs_barrier_match"] == "match"
    assert summary["global_detail_fallback_used_rows"] == 1


def test_manual_vs_heuristic_comparison_reclassifies_lower_rebound_probe_skip_as_timing_improvement() -> None:
    annotations = pd.DataFrame(
        [
            {
                "episode_id": "nas_episode_probe_001",
                "symbol": "NAS100",
                "timeframe": "M1",
                "anchor_side": "BUY",
                "anchor_time": "2026-04-03T11:02:00+09:00",
                "anchor_price": 100.0,
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "medium",
                "annotation_source": "chart_annotated",
            }
        ]
    )
    heuristic = pd.DataFrame(
        [
            {
                "time": "2026-04-03T11:01:00+09:00",
                "signal_bar_ts": "",
                "symbol": "NAS100",
                "action": "",
                "observe_action": "",
                "observe_side": "",
                "observe_reason": "",
                "blocked_by": "",
                "core_reason": "",
                "entry_wait_decision": "",
                "barrier_candidate_recommended_family": "",
                "barrier_candidate_supporting_label": "",
                "barrier_action_hint_confidence": "",
                "barrier_action_hint_reason_summary": "",
                "forecast_decision_hint": "",
                "forecast_state25_scene_family": "",
                "belief_candidate_recommended_family": "",
                "belief_action_hint_reason_summary": "",
                "heuristic_source_file": "entry_decisions.legacy_20260404_000006.csv",
                "heuristic_source_kind": "legacy",
                "heuristic_time": pd.Timestamp("2026-04-03 11:01:00"),
            }
        ]
    )
    fallback = pd.DataFrame(
        [
            {
                "episode_id": "nas_episode_probe_001",
                "heuristic_source_file": "entry_decisions.legacy_20260404_000006.csv",
                "global_detail_source_file": "entry_decisions.detail.rotate_20260403_104850_636043.jsonl",
                "global_detail_source_kind": "rotate_detail",
                "global_detail_row_found": 1,
                "global_detail_observe_reason": "lower_rebound_probe_observe",
                "global_detail_blocked_by": "range_lower_buy_requires_lower_edge",
                "global_detail_entry_wait_decision": "skip",
                "global_detail_core_reason": "energy_soft_block",
                "global_detail_recoverability_grade": "high",
            }
        ]
    )

    report, summary = build_manual_vs_heuristic_comparison_report(
        annotations,
        heuristic,
        global_detail_fallback_frame=fallback,
        max_gap_minutes=30,
        created_at="2026-04-06T12:00:00+09:00",
        review_owner="test",
    )

    row = report.iloc[0].to_dict()
    assert row["heuristic_reconstruction_mode"] == "global_detail_fallback"
    assert row["heuristic_barrier_main_label"] == "correct_wait"
    assert row["heuristic_wait_family"] == "timing_improvement"
    assert row["manual_vs_barrier_match"] == "match"
    assert row["heuristic_evidence_quality"] == "rich"
    assert summary["global_detail_fallback_used_rows"] == 1


def test_manual_vs_heuristic_comparison_keeps_current_rich_seed_out_of_canonical_without_review() -> None:
    annotations = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::BTCUSD::2026-04-06T18:30:00",
                "symbol": "BTCUSD",
                "timeframe": "M1",
                "anchor_side": "SELL",
                "anchor_time": "2026-04-06T18:30:00+09:00",
                "anchor_price": 0.0,
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_confidence": "low",
                "manual_teacher_confidence": "low",
                "annotation_source": "assistant_current_rich_seed",
                "review_status": "needs_manual_recheck",
            }
        ]
    )
    heuristic = pd.DataFrame(
        [
            {
                "time": "2026-04-06T18:31:00+09:00",
                "signal_bar_ts": "",
                "symbol": "BTCUSD",
                "action": "",
                "observe_action": "SELL",
                "observe_side": "SELL",
                "observe_reason": "outer_band_reversal_support_required_observe",
                "blocked_by": "",
                "core_reason": "helper_wait",
                "entry_wait_decision": "wait_soft_helper_block",
                "barrier_candidate_recommended_family": "relief_watch",
                "barrier_candidate_supporting_label": "correct_wait",
                "barrier_action_hint_confidence": "medium",
                "barrier_action_hint_reason_summary": "helper wait remains valid",
                "forecast_decision_hint": "",
                "forecast_state25_scene_family": "",
                "belief_candidate_recommended_family": "",
                "belief_action_hint_reason_summary": "",
                "heuristic_source_file": "entry_decisions.csv",
                "heuristic_source_kind": "current",
                "heuristic_time": pd.Timestamp("2026-04-06 18:31:00"),
            }
        ]
    )

    report, _ = build_manual_vs_heuristic_comparison_report(
        annotations,
        heuristic,
        max_gap_minutes=30,
        created_at="2026-04-06T20:00:00+09:00",
        review_owner="test",
    )

    row = report.iloc[0].to_dict()
    assert row["manual_truth_source_bucket"] == "current_rich_draft"
    assert row["manual_truth_review_state"] == "needs_manual_recheck"
    assert row["current_rich_overlap_flag"] == "yes"
    assert row["current_rich_proxy_support"] == "mixed"
    assert row["rule_change_readiness"] == "needs_manual_recheck"
    assert row["mismatch_disposition"] == "collect_current_rich_truth"
    assert row["canonical_promotion_readiness"] == "review_needed"
    assert row["canonical_promotion_recommendation"] == "keep_in_current_rich_draft"
