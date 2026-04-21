from zoneinfo import ZoneInfo

from backend.services.improvement_detector_feedback_runtime import (
    build_detector_feedback_entry,
    build_detector_feedback_scope_key,
)
from backend.services.trade_feedback_runtime import (
    PROMOTION_POLICY_TARGET_REGISTRY_KEYS,
    build_manual_trade_proposal_snapshot,
)
from tests.unit.test_trade_feedback_runtime import _sample_closed_frame


KST = ZoneInfo("Asia/Seoul")


def _db3_issue_ref() -> dict[str, object]:
    summary_ko = "BTCUSD upper_reject_mixed_confirm 구조 복합 불일치 관찰"
    return {
        "feedback_ref": "D1",
        "feedback_key": "detfb_db3_binding",
        "feedback_scope_key": build_detector_feedback_scope_key(
            detector_key="candle_weight_detector",
            symbol="BTCUSD",
            summary_ko=summary_ko,
        ),
        "detector_key": "candle_weight_detector",
        "symbol": "BTCUSD",
        "summary_ko": summary_ko,
        "registry_key": "misread:composite_structure_mismatch",
        "registry_label_ko": "구조 복합 불일치",
        "registry_binding_mode": "derived",
        "evidence_registry_keys": [
            "misread:box_relative_position",
            "misread:upper_wick_ratio",
            "misread:recent_3bar_direction",
            "misread:composite_structure_mismatch",
        ],
        "target_registry_keys": [
            "state25_weight:upper_wick_weight",
            "state25_weight:reversal_risk_weight",
        ],
        "hindsight_status": "confirmed_misread",
        "hindsight_status_ko": "사후 확정 오판",
        "misread_confidence": 0.82,
    }


def _db3_feedback_entries(issue_ref: dict[str, object]) -> list[dict[str, object]]:
    timestamps = [
        "2026-04-10T09:10:00+09:00",
        "2026-04-10T09:20:00+09:00",
        "2026-04-11T10:10:00+09:00",
        "2026-04-12T11:10:00+09:00",
        "2026-04-12T11:20:00+09:00",
    ]
    verdicts = ["confirmed", "missed", "confirmed", "missed", "confirmed"]
    return [
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict=verdict,
            user_id=1001,
            username="ops",
            now_ts=ts,
        )
        for verdict, ts in zip(verdicts, timestamps, strict=True)
    ]


def test_db3_feedback_promotion_rows_attach_direct_binding_fields() -> None:
    issue_ref = _db3_issue_ref()
    payload = build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T12:30:00+09:00",
        detector_feedback_entries=_db3_feedback_entries(issue_ref),
        detector_latest_issue_refs=[issue_ref],
    )

    row = payload["feedback_promotion_rows"][0]
    assert row["registry_key"] == "promotion:hindsight_status"
    assert row["registry_binding_mode"] == "derived"
    assert row["registry_binding_ready"] is True
    assert set(row["evidence_registry_keys"]) == set(issue_ref["evidence_registry_keys"])
    assert set(row["target_registry_keys"]) == set(PROMOTION_POLICY_TARGET_REGISTRY_KEYS)
    assert set(row["downstream_target_registry_keys"]) == set(issue_ref["target_registry_keys"])
    assert row["detector_registry_key"] == issue_ref["registry_key"]
    assert row["detector_registry_label_ko"] == issue_ref["registry_label_ko"]


def test_db3_feedback_binding_summary_flows_into_problem_patterns_and_envelope() -> None:
    issue_ref = _db3_issue_ref()
    payload = build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T12:40:00+09:00",
        detector_feedback_entries=_db3_feedback_entries(issue_ref),
        detector_latest_issue_refs=[issue_ref],
    )

    binding_summary = payload["feedback_registry_binding_summary"]
    assert binding_summary["feedback_registry_keys"] == ["promotion:hindsight_status"]
    assert set(binding_summary["feedback_evidence_registry_keys"]) == set(issue_ref["evidence_registry_keys"])
    assert set(binding_summary["feedback_target_registry_keys"]) == set(PROMOTION_POLICY_TARGET_REGISTRY_KEYS)
    assert set(binding_summary["feedback_downstream_target_registry_keys"]) == set(issue_ref["target_registry_keys"])
    assert binding_summary["feedback_registry_binding_ready_count"] == 1

    top_issue = payload["surfaced_problem_patterns"][0]
    assert top_issue["feedback_priority_registry_key"] == "promotion:hindsight_status"
    assert top_issue["feedback_priority_registry_label_ko"] == "사후 hindsight 상태"
    assert top_issue["feedback_priority_binding_mode"] == "derived"
    assert set(top_issue["feedback_priority_evidence_registry_keys"]) == set(issue_ref["evidence_registry_keys"])
    assert set(top_issue["feedback_priority_target_registry_keys"]) == set(PROMOTION_POLICY_TARGET_REGISTRY_KEYS)

    evidence_snapshot = payload["proposal_envelope"]["evidence_snapshot"]
    assert evidence_snapshot["feedback_registry_keys"] == ["promotion:hindsight_status"]
    assert set(evidence_snapshot["feedback_target_registry_keys"]) == set(PROMOTION_POLICY_TARGET_REGISTRY_KEYS)
