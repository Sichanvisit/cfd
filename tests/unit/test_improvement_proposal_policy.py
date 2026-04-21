from __future__ import annotations

import pytest

from backend.services.improvement_proposal_policy import (
    build_improvement_proposal_envelope,
    ensure_improvement_proposal_envelope,
    validate_improvement_proposal_envelope,
)


def test_build_improvement_proposal_envelope_sets_required_fields() -> None:
    envelope = build_improvement_proposal_envelope(
        proposal_type="CANARY_CLOSEOUT_REVIEW",
        scope_key="BTCUSD:pa8:closeout",
        trace_id="trace-pa8-btc",
        summary_ko="BTCUSD closeout readiness가 거의 찼습니다.",
        why_now_ko="live window가 closeout review 직전 상태입니다.",
        recommended_action_ko="closeout review를 열고 bounded scope만 검토합니다.",
        confidence_level="MEDIUM",
    )

    assert envelope["proposal_id"].startswith("prop_canary_closeout_review_btcusd_pa8_closeout_")
    assert envelope["proposal_type"] == "CANARY_CLOSEOUT_REVIEW"
    assert envelope["scope_key"] == "BTCUSD:pa8:closeout"
    assert envelope["trace_id"] == "trace-pa8-btc"
    assert envelope["proposal_stage"] == "REPORT_READY"
    assert envelope["readiness_status"] == "READY_FOR_REVIEW"


def test_ensure_improvement_proposal_envelope_builds_from_legacy_candidate_fields() -> None:
    candidate = {
        "review_type": "STATE25_WEIGHT_PATCH_REVIEW",
        "scope_key": "STATE25_WEIGHT_PATCH::BTCUSD::READY::upper_wick_weight",
        "proposal_summary_ko": "윗꼬리 비중 조정 제안",
        "evidence_summary_ko": "상방 추진력 장면에서 하단 해석이 과도했습니다.",
        "scope_note_ko": "symbol=BTCUSD | entry_stage=READY | binding_mode=log_only",
        "recommended_action_note": "bounded log-only 조정으로 먼저 확인합니다.",
    }

    envelope = ensure_improvement_proposal_envelope(
        candidate,
        trace_id="trace-state25-btc",
    )

    assert envelope["proposal_type"] == "STATE25_WEIGHT_PATCH_REVIEW"
    assert envelope["scope_key"] == candidate["scope_key"]
    assert envelope["trace_id"] == "trace-state25-btc"
    assert envelope["summary_ko"] == "윗꼬리 비중 조정 제안"
    assert envelope["why_now_ko"] == "상방 추진력 장면에서 하단 해석이 과도했습니다."
    assert envelope["recommended_action_ko"] == "bounded log-only 조정으로 먼저 확인합니다."
    assert envelope["scope_note_ko"] == candidate["scope_note_ko"]


def test_validate_improvement_proposal_envelope_rejects_missing_required_fields() -> None:
    with pytest.raises(ValueError, match="missing_proposal_envelope_fields"):
        validate_improvement_proposal_envelope({"proposal_type": "CANARY_CLOSEOUT_REVIEW"})
