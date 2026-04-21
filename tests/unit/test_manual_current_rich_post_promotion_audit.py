import pandas as pd

from backend.services.manual_current_rich_post_promotion_audit import (
    build_manual_current_rich_post_promotion_audit,
)


def test_post_promotion_audit_builds_due_row_from_promoted_trace() -> None:
    trace_entries = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::NAS100::2026-04-07T03:00:00",
                "promotion_reviewer": "codex",
                "promotion_reviewed_at": "2026-04-01T10:00:00+09:00",
                "promotion_decision_reason": "review_complete_and_promote",
                "canonical_decision": "promote_to_canonical",
            }
        ]
    )
    canonical = pd.DataFrame(
        [
            {
                "annotation_id": "ann_001",
                "episode_id": "manual_seed::NAS100::2026-04-07T03:00:00",
                "scene_id": "scene_01",
                "manual_wait_teacher_family": "timing_improvement",
            }
        ]
    )
    comparison = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::NAS100::2026-04-07T03:00:00",
                "scene_id": "scene_01",
                "manual_vs_barrier_match": "match",
                "evidence_gap_minutes": 2,
                "manual_wait_teacher_family": "timing_improvement",
                "heuristic_wait_family": "timing_improvement",
            }
        ]
    )
    audit_entries = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::NAS100::2026-04-07T03:00:00",
                "audit_result": "keep_canonical",
                "audit_reason": "still_consistent_after_review",
                "audit_reviewer": "codex",
                "audit_executed_at": "2026-04-05T11:00:00+09:00",
                "keep_canonical": "true",
                "needs_relabel": "false",
                "needs_note_update": "false",
                "demote_from_canonical": "false",
            }
        ]
    )

    audit, summary = build_manual_current_rich_post_promotion_audit(
        trace_entries,
        canonical,
        comparison,
        audit_entries=audit_entries,
        now="2026-04-07T12:00:00+09:00",
    )

    assert len(audit) == 1
    row = audit.iloc[0]
    assert row["canonical_row_id"] == "ann_001"
    assert row["audit_status"] == "audit_executed"
    assert row["heuristic_match_after_promotion"] == "match"
    assert row["family_consistency_after_promotion"] == "aligned"
    assert row["scene_consistency_after_promotion"] == "aligned"
    assert row["audit_result"] == "keep_canonical"
    assert summary["row_count"] == 1
    assert summary["due_count"] == 0
    assert summary["completed_count"] == 1
    assert summary["scheduled_count"] == 0


def test_post_promotion_audit_empty_when_no_promoted_trace_rows() -> None:
    trace_entries = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::BTCUSD::2026-04-07T03:30:00",
                "canonical_decision": "hold_review_needed",
            }
        ]
    )

    audit, summary = build_manual_current_rich_post_promotion_audit(
        trace_entries,
        pd.DataFrame(),
        pd.DataFrame(),
        now="2026-04-07T12:00:00+09:00",
    )

    assert audit.empty
    assert summary["row_count"] == 0


def test_post_promotion_audit_handles_default_now_for_aware_promotion_time() -> None:
    trace_entries = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::BTCUSD::2026-04-07T03:00:00",
                "promotion_reviewer": "codex",
                "promotion_reviewed_at": "2026-04-07T13:30:00+09:00",
                "promotion_decision_reason": "review_complete_and_promote",
                "canonical_decision": "promote_to_canonical",
            }
        ]
    )
    canonical = pd.DataFrame(
        [
            {
                "annotation_id": "ann_btc_001",
                "episode_id": "manual_seed::BTCUSD::2026-04-07T03:00:00",
                "scene_id": "btc_scene_01",
                "manual_wait_teacher_family": "timing_improvement",
            }
        ]
    )
    comparison = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::BTCUSD::2026-04-07T03:00:00",
                "scene_id": "btc_scene_01",
                "manual_vs_barrier_match": "match",
                "evidence_gap_minutes": 1,
                "manual_wait_teacher_family": "timing_improvement",
                "heuristic_wait_family": "timing_improvement",
            }
        ]
    )

    audit, summary = build_manual_current_rich_post_promotion_audit(
        trace_entries,
        canonical,
        comparison,
    )

    assert len(audit) == 1
    assert summary["row_count"] == 1
    assert "next_due_episode_ids" in summary
