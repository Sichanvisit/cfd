import pandas as pd

from backend.services.manual_current_rich_promotion_gate import (
    build_manual_current_rich_promotion_gate,
)


def test_manual_current_rich_promotion_gate_respects_followup_review_and_detail() -> None:
    draft = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::BTCUSD::2026-04-06T18:30:00",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-06T18:30:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_teacher_confidence": "medium",
                "review_status": "accepted_coarse",
            },
            {
                "episode_id": "manual_seed::XAUUSD::2026-04-06T20:00:00",
                "symbol": "XAUUSD",
                "anchor_time": "2026-04-06T20:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_teacher_confidence": "high",
                "review_status": "accepted_coarse",
                "ideal_entry_time": "2026-04-06T20:05:00+09:00",
                "ideal_exit_time": "2026-04-06T20:20:00+09:00",
            },
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "queue_id": "current_rich::BTCUSD::2026-04-06T18:30:00",
                "capture_priority": "high",
                "row_count": 220,
                "unique_signal_minutes": 4,
            },
            {
                "queue_id": "current_rich::XAUUSD::2026-04-06T20:00:00",
                "capture_priority": "high",
                "row_count": 220,
                "unique_signal_minutes": 4,
            },
        ]
    )
    review_results = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::BTCUSD::2026-04-06T18:30:00",
                "review_decision": "keep_wait_bias",
                "canonical_action": "do_not_promote_failed_wait_seed",
            }
        ]
    )
    review_trace_entries = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::BTCUSD::2026-04-06T18:30:00",
                "promotion_reviewer": "codex",
                "promotion_reviewed_at": "2026-04-07T12:00:00+09:00",
                "promotion_decision_reason": "assistant_review_reject",
                "promotion_blocking_reason": "followup_review_rejected",
                "promotion_followup_needed": "keep_as_control_only",
                "canonical_decision": "do_not_promote_failed_wait_seed",
            }
        ]
    )

    gate, summary = build_manual_current_rich_promotion_gate(
        draft,
        queue=queue,
        review_results=review_results,
        review_trace_entries=review_trace_entries,
    )

    assert len(gate) == 2
    assert gate.iloc[0]["promotion_readiness"] == "ready"
    assert gate.iloc[0]["canonical_promotion_recommendation"] == "promote_to_canonical"
    assert gate.iloc[0]["review_priority_tier"] == "ready_high"
    assert gate.iloc[0]["promotion_followup_needed"] == "promotion_signoff"
    rejected = gate[gate["symbol"] == "BTCUSD"].iloc[0]
    assert rejected["promotion_readiness"] == "do_not_promote"
    assert rejected["review_priority_tier"] == "control_only"
    assert rejected["promotion_decision_reason"] == "assistant_review_reject"
    assert rejected["promotion_blocking_reason"] == "followup_review_rejected"
    assert rejected["promotion_reviewer"] == "codex"
    assert summary["ready_for_canonical_count"] == 1
    assert summary["review_priority_tier_counts"]["control_only"] == 1
