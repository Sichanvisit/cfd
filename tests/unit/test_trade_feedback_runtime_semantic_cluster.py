from zoneinfo import ZoneInfo

import backend.services.trade_feedback_runtime as trade_feedback_module


KST = ZoneInfo("Asia/Seoul")


def test_manual_proposal_snapshot_surfaces_semantic_cluster_candidates(monkeypatch) -> None:
    monkeypatch.setattr(
        trade_feedback_module,
        "build_semantic_baseline_no_action_cluster_candidates",
        lambda: [
            {
                "candidate_key": "BTCUSD | outer_band_reversal_support_required_observe | energy_soft_block | execution_soft_blocked",
                "symbol": "BTCUSD",
                "observe_reason": "outer_band_reversal_support_required_observe",
                "blocked_by": "energy_soft_block",
                "action_none_reason": "execution_soft_blocked",
                "cluster_count": 18,
                "cluster_share": 0.5,
                "summary_ko": "BTCUSD semantic observe cluster",
                "why_now_ko": "cluster repeated",
                "recommended_action_ko": "promote through detector and proposal review",
                "evidence_lines_ko": ["- cluster_count: 18"],
                "registry_key": "misread:semantic_baseline_no_action_cluster",
                "primary_registry_key_override": "misread:semantic_baseline_no_action_cluster",
                "extra_evidence_registry_keys": ["misread:semantic_baseline_no_action_cluster"],
                "result_type": "result_unresolved",
                "explanation_type": "explanation_gap",
                "misread_confidence": 0.78,
                "priority_score": 70.0,
            }
        ],
    )

    payload = trade_feedback_module.build_manual_trade_proposal_snapshot(
        None,
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T18:45:00+09:00",
    )

    assert payload["semantic_cluster_candidate_count"] == 1
    assert payload["proposal_envelope"]["readiness_status"] == "READY_FOR_REVIEW"
    assert payload["semantic_cluster_candidates"][0]["registry_key"] == "misread:semantic_baseline_no_action_cluster"
    assert any("semantic observe cluster" in line for line in payload["report_lines_ko"])
