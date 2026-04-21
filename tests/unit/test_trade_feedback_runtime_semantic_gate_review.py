from zoneinfo import ZoneInfo

import backend.services.trade_feedback_runtime as trade_feedback_module


KST = ZoneInfo("Asia/Seoul")


def test_manual_proposal_snapshot_surfaces_semantic_gate_review_candidates(monkeypatch) -> None:
    monkeypatch.setattr(
        trade_feedback_module,
        "build_semantic_baseline_no_action_cluster_candidates",
        lambda: [],
    )
    monkeypatch.setattr(
        trade_feedback_module,
        "build_semantic_baseline_no_action_gate_review_candidates",
        lambda: [
            {
                "candidate_code": "review_energy_soft_block_gate",
                "candidate_label_ko": "energy soft block gate 검토",
                "symbol_scope": "BTCUSD",
                "dimension": "blocked_by",
                "dimension_value": "energy_soft_block",
                "gate_count": 28,
                "gate_share": 0.48,
                "summary_ko": "BTCUSD semantic gate review 후보",
                "why_now_ko": "energy soft block가 반복됩니다.",
                "recommended_action_ko": "soft block gate를 review backlog로 먼저 올립니다.",
                "evidence_lines_ko": ["- gate_count: 28"],
                "registry_key": "misread:semantic_gate_review_candidate",
                "primary_registry_key_override": "misread:semantic_gate_review_candidate",
                "extra_evidence_registry_keys": [
                    "misread:semantic_gate_review_candidate",
                    "misread:semantic_blocked_by",
                ],
                "result_type": "result_unresolved",
                "explanation_type": "explanation_gap",
                "misread_confidence": 0.76,
                "priority_score": 72.0,
            }
        ],
    )

    payload = trade_feedback_module.build_manual_trade_proposal_snapshot(
        None,
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T18:55:00+09:00",
    )

    assert payload["semantic_gate_review_candidate_count"] == 1
    assert payload["proposal_envelope"]["readiness_status"] == "READY_FOR_REVIEW"
    assert payload["semantic_gate_review_candidates"][0]["registry_key"] == "misread:semantic_gate_review_candidate"
    assert any("semantic gate review" in line for line in payload["report_lines_ko"])
