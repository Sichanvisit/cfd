from __future__ import annotations

from backend.services.improvement_detector_feedback_runtime import (
    DETECTOR_FEEDBACK_CONFIRMED,
    DETECTOR_FEEDBACK_MISSED,
    DETECTOR_FEEDBACK_OVERSENSITIVE,
    DETECTOR_NARROWING_KEEP,
    DETECTOR_NARROWING_SUPPRESS,
    build_detector_confusion_snapshot,
    build_detector_feedback_entry,
    build_detector_feedback_narrowing_index,
    build_detector_feedback_scope_key,
    build_detector_feedback_snapshot,
    evaluate_detector_feedback_narrowing,
    detector_feedback_verdict_label_ko,
    find_detect_issue_ref,
    normalize_detector_feedback_verdict,
)


def test_find_detect_issue_ref_supports_display_ref_and_key() -> None:
    latest_issue_refs = [
        {
            "feedback_ref": "D1",
            "feedback_key": "detfb_a",
            "detector_key": "scene_aware",
            "symbol": "BTCUSD",
            "summary_ko": "BTCUSD scene trace 누락 반복 감지",
        }
    ]

    assert find_detect_issue_ref(latest_issue_refs, "D1")["feedback_key"] == "detfb_a"
    assert find_detect_issue_ref(latest_issue_refs, "1")["feedback_key"] == "detfb_a"
    assert find_detect_issue_ref(latest_issue_refs, "detfb_a")["feedback_ref"] == "D1"


def test_detector_feedback_runtime_builds_snapshot_counts() -> None:
    issue_ref = {
        "feedback_ref": "D1",
        "feedback_key": "detfb_a",
        "detector_key": "scene_aware",
        "symbol": "BTCUSD",
        "summary_ko": "BTCUSD scene trace 누락 반복 감지",
    }
    issue_ref_2 = {
        "feedback_ref": "D2",
        "feedback_key": "detfb_b",
        "detector_key": "reverse_pattern",
        "symbol": "XAUUSD",
        "summary_ko": "XAUUSD missed reverse / shock 패턴 관찰",
    }
    entry_1 = build_detector_feedback_entry(
        issue_ref=issue_ref,
        verdict="맞았음",
        user_id=1001,
        username="@ops_user",
        proposal_id="proposal-1",
        now_ts="2026-04-12T22:00:00+09:00",
    )
    entry_2 = build_detector_feedback_entry(
        issue_ref=issue_ref_2,
        verdict="놓쳤음",
        user_id=1001,
        username="@ops_user",
        proposal_id="proposal-1",
        now_ts="2026-04-12T22:01:00+09:00",
    )

    snapshot = build_detector_feedback_snapshot(
        [entry_1, entry_2],
        [issue_ref, issue_ref_2],
        now_ts="2026-04-12T22:02:00+09:00",
    )

    assert normalize_detector_feedback_verdict("맞았음") == DETECTOR_FEEDBACK_CONFIRMED
    assert detector_feedback_verdict_label_ko("missed") == "놓쳤음"
    assert snapshot["feedback_entry_count"] == 2
    assert snapshot["counts_by_verdict"][DETECTOR_FEEDBACK_CONFIRMED] == 1
    assert snapshot["counts_by_verdict"][DETECTOR_FEEDBACK_MISSED] == 1
    assert snapshot["counts_by_detector"]["scene_aware"][DETECTOR_FEEDBACK_CONFIRMED] == 1
    assert snapshot["counts_by_detector"]["reverse_pattern"][DETECTOR_FEEDBACK_MISSED] == 1
    assert snapshot["latest_issue_feedback"][0]["feedback_scope_key"]


def test_detector_feedback_confusion_snapshot_and_narrowing_rules() -> None:
    issue_ref = {
        "feedback_ref": "D1",
        "feedback_key": "detfb_a",
        "feedback_scope_key": build_detector_feedback_scope_key(
            detector_key="scene_aware",
            symbol="BTCUSD",
            summary_ko="BTCUSD scene trace 누락 반복 감지",
        ),
        "detector_key": "scene_aware",
        "symbol": "BTCUSD",
        "summary_ko": "BTCUSD scene trace 누락 반복 감지",
    }
    oversensitive_1 = build_detector_feedback_entry(
        issue_ref=issue_ref,
        verdict="oversensitive",
        user_id=1001,
        username="@ops_user",
        proposal_id="proposal-1",
        now_ts="2026-04-12T22:00:00+09:00",
    )
    oversensitive_2 = build_detector_feedback_entry(
        issue_ref=issue_ref,
        verdict="oversensitive",
        user_id=1001,
        username="@ops_user",
        proposal_id="proposal-1",
        now_ts="2026-04-12T22:01:00+09:00",
    )

    confusion = build_detector_confusion_snapshot(
        [oversensitive_1, oversensitive_2],
        [issue_ref],
        now_ts="2026-04-12T22:02:00+09:00",
    )
    index = build_detector_feedback_narrowing_index([oversensitive_1, oversensitive_2])
    profile = index[issue_ref["feedback_scope_key"]]

    assert confusion["verdict_totals"][DETECTOR_FEEDBACK_OVERSENSITIVE] == 2
    assert confusion["scope_rows"][0]["narrowing_decision"] == DETECTOR_NARROWING_SUPPRESS
    assert evaluate_detector_feedback_narrowing(profile) == DETECTOR_NARROWING_SUPPRESS

    confirmed_entry = build_detector_feedback_entry(
        issue_ref=issue_ref,
        verdict="confirmed",
        user_id=1001,
        username="@ops_user",
        proposal_id="proposal-2",
        now_ts="2026-04-12T22:03:00+09:00",
    )
    promote_index = build_detector_feedback_narrowing_index([confirmed_entry])
    promote_profile = promote_index[issue_ref["feedback_scope_key"]]
    assert evaluate_detector_feedback_narrowing(promote_profile) == DETECTOR_NARROWING_KEEP
