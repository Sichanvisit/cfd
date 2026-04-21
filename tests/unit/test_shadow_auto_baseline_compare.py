from pathlib import Path

import pandas as pd

from backend.services.shadow_auto_baseline_compare import (
    build_shadow_auto_baseline_compare,
    load_entry_decision_history,
)


def test_build_shadow_auto_baseline_compare_uses_manual_reference_and_candidate_mapping():
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-07T03:00:14",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "wait",
                "entry_wait_decision": "wait_soft_helper_block",
                "semantic_shadow_available": 1,
                "semantic_shadow_compare_label": "semantic_earlier_enter",
                "semantic_shadow_action_hint": "BUY",
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_activation_state": "active",
                "semantic_shadow_reason": "shadow_probe",
            }
        ]
    )
    comparison = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::BTCUSD::2026-04-07T03:00:00",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-07T03:00:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_family": "failed_wait",
                "overall_alignment_grade": "mismatch",
            }
        ]
    )
    shadow_candidates = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_failed_wait",
                "manual_wait_teacher_family": "failed_wait",
                "bridge_status": "await_more_truth",
                "patch_version": "shadow_patch::fam_failed_wait::v0",
            }
        ]
    )

    compare_df, summary = build_shadow_auto_baseline_compare(
        entry_decisions,
        comparison=comparison,
        shadow_candidates=shadow_candidates,
        max_rows=50,
        manual_match_threshold_minutes=30.0,
    )

    assert len(compare_df) == 1
    assert summary["manual_reference_rows"] == 1
    row = compare_df.iloc[0]
    assert row["manual_family"] == "failed_wait"
    assert row["baseline_match"] == "mismatch"
    assert row["shadow_match"] == "potential_improvement"
    assert row["match_improvement"] == "improved"
    assert row["shadow_candidate_id"] == "shadow_candidate::fam_failed_wait"


def test_load_entry_decision_history_combines_current_and_legacy(tmp_path: Path):
    trades_dir = tmp_path / "data" / "trades"
    trades_dir.mkdir(parents=True, exist_ok=True)
    (trades_dir / "entry_decisions.csv").write_text(
        "time,symbol,action,outcome,entry_wait_decision\n2026-04-07T00:00:00,BTCUSD,,wait,wait_soft_helper_block\n",
        encoding="utf-8",
    )
    (trades_dir / "entry_decisions.legacy_20260402_000000.csv").write_text(
        "time,symbol,action,outcome,entry_wait_decision\n2026-04-02T21:46:00,BTCUSD,BUY,entered,\n",
        encoding="utf-8",
    )

    combined = load_entry_decision_history(trades_dir, include_legacy=True)

    assert len(combined) == 2
    assert set(combined["decision_source_kind"].tolist()) == {"current", "legacy"}


def test_build_shadow_auto_baseline_compare_maps_freeze_monitor_candidates_by_exact_family():
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-07T04:00:00",
                "symbol": "NAS100",
                "action": "",
                "outcome": "wait",
                "entry_wait_decision": "wait_probe",
                "semantic_shadow_available": 0,
                "semantic_shadow_activation_state": "inactive",
                "semantic_shadow_compare_label": "unavailable",
            }
        ]
    )
    comparison = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::NAS100::2026-04-07T04:00:00",
                "symbol": "NAS100",
                "anchor_time": "2026-04-07T04:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_family": "timing_improvement",
                "overall_alignment_grade": "freeze",
            }
        ]
    )
    shadow_candidates = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::timing_improvement_freeze_monitor",
                "manual_wait_teacher_family": "timing_improvement",
                "candidate_kind": "freeze_monitor",
                "bridge_status": "freeze_track_only",
                "patch_version": "shadow_patch::timing_improvement_freeze_monitor::v0",
            }
        ]
    )

    compare_df, _summary = build_shadow_auto_baseline_compare(
        entry_decisions,
        comparison=comparison,
        shadow_candidates=shadow_candidates,
        max_rows=50,
        manual_match_threshold_minutes=30.0,
    )

    assert len(compare_df) == 1
    row = compare_df.iloc[0]
    assert row["manual_family"] == "timing_improvement"
    assert row["shadow_candidate_id"] == "shadow_candidate::timing_improvement_freeze_monitor"
