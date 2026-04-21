from pathlib import Path

import pandas as pd

from backend.services.shadow_signal_activation_bridge import build_shadow_signal_activation_bridge


def test_build_shadow_signal_activation_bridge_reports_model_bundle_missing(tmp_path: Path):
    compare_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_a",
                "manual_label": "bad_wait_missed_move",
                "semantic_shadow_available": 0,
                "semantic_shadow_activation_state": "inactive",
                "shadow_reason": "model_dir_missing",
                "semantic_shadow_compare_label": "unavailable",
            }
        ]
    )
    candidates_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_a",
                "family_key": "fam_a",
                "candidate_kind": "truth_collection_probe",
                "bridge_status": "await_more_truth",
            }
        ]
    )

    bridge, summary = build_shadow_signal_activation_bridge(
        compare_df,
        shadow_candidates=candidates_df,
        model_dir=tmp_path / "missing_models",
    )

    assert len(bridge) == 1
    row = bridge.iloc[0]
    assert row["activation_bridge_status"] == "model_bundle_missing"
    assert row["recommended_next_action"] == "build_or_link_semantic_shadow_models"
    assert summary["available_bundle_count"] == 0


def test_build_shadow_signal_activation_bridge_reports_shadow_available_when_bundle_and_rows_exist(tmp_path: Path):
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    for file_name in ["timing_model.joblib", "entry_quality_model.joblib", "exit_management_model.joblib"]:
        (model_dir / file_name).write_text("placeholder", encoding="utf-8")

    compare_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_b",
                "manual_label": "good_wait_better_entry",
                "semantic_shadow_available": 1,
                "semantic_shadow_activation_state": "active",
                "shadow_reason": "shadow_ready",
                "semantic_shadow_compare_label": "semantic_later_block",
            }
        ]
    )
    candidates_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_b",
                "family_key": "fam_b",
                "candidate_kind": "shadow_patch_candidate",
                "bridge_status": "shadow_ready",
            }
        ]
    )

    bridge, summary = build_shadow_signal_activation_bridge(compare_df, shadow_candidates=candidates_df, model_dir=model_dir)

    row = bridge.iloc[0]
    assert row["activation_bridge_status"] == "shadow_available"
    assert row["recommended_next_action"] == "proceed_to_shadow_evaluation"
    assert summary["available_bundle_count"] == 3


def test_build_shadow_signal_activation_bridge_reports_precedence_blocked_when_family_rows_exist_but_are_claimed_by_another_candidate(
    tmp_path: Path,
):
    compare_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::higher_priority",
                "manual_family": "failed_wait",
                "manual_label": "bad_wait_missed_move",
                "semantic_shadow_available": 0,
                "semantic_shadow_activation_state": "inactive",
                "shadow_reason": "semantic_runtime_unavailable",
                "semantic_shadow_compare_label": "unavailable",
            }
        ]
    )
    candidates_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::freeze_monitor_failed_wait",
                "family_key": "fam_failed_wait_freeze",
                "manual_wait_teacher_family": "failed_wait",
                "candidate_kind": "freeze_monitor",
                "bridge_status": "freeze_track_only",
            }
        ]
    )

    bridge, _summary = build_shadow_signal_activation_bridge(
        compare_df,
        shadow_candidates=candidates_df,
        model_dir=tmp_path / "missing_models",
    )

    row = bridge.iloc[0]
    assert row["observed_overlap_rows"] == 0
    assert row["family_overlap_rows"] == 1
    assert bool(row["candidate_precedence_blocked"]) is True
    assert row["activation_bridge_status"] == "candidate_precedence_blocked"
    assert row["recommended_next_action"] == "keep_higher_priority_candidate_mapping"


def test_build_shadow_signal_activation_bridge_reports_preview_bundle_ready_when_active_dir_is_missing(tmp_path: Path):
    active_model_dir = tmp_path / "active_missing_models"
    preview_dir = tmp_path / "semantic_v1_preview_bridge_proxy"
    preview_dir.mkdir(parents=True, exist_ok=True)
    for file_name in ["timing_model.joblib", "entry_quality_model.joblib", "exit_management_model.joblib"]:
        (preview_dir / file_name).write_text("placeholder", encoding="utf-8")

    compare_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_preview",
                "manual_label": "good_wait_better_entry",
                "semantic_shadow_available": 0,
                "semantic_shadow_activation_state": "inactive",
                "shadow_reason": "model_dir_missing",
                "semantic_shadow_compare_label": "unavailable",
            }
        ]
    )
    candidates_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_preview",
                "family_key": "fam_preview",
                "candidate_kind": "shadow_patch_candidate",
                "bridge_status": "shadow_ready",
            }
        ]
    )

    bridge, summary = build_shadow_signal_activation_bridge(
        compare_df,
        shadow_candidates=candidates_df,
        model_dir=active_model_dir,
    )

    row = bridge.iloc[0]
    assert bool(row["preview_bundle_ready"]) is True
    assert int(row["preview_bundle_dir_count"]) >= 1
    assert row["effective_runtime_stage"] == "preview_only"
    assert row["activation_bridge_status"] == "preview_bundle_ready"
    assert row["recommended_next_action"] == "continue_preview_shadow_evaluation_until_bounded_ready"
    assert summary["preview_bundle_ready"] is True
