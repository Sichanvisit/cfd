from zoneinfo import ZoneInfo

import pandas as pd

import backend.services.improvement_log_only_detector as detector_module


KST = ZoneInfo("Asia/Seoul")


def test_detector_snapshot_surfaces_semantic_baseline_no_action_cluster(monkeypatch) -> None:
    monkeypatch.setattr(
        detector_module,
        "build_semantic_baseline_no_action_cluster_candidates",
        lambda: [
            {
                "candidate_key": "BTCUSD | outer_band_reversal_support_required_observe | energy_soft_block | execution_soft_blocked",
                "symbol": "BTCUSD",
                "observe_reason": "outer_band_reversal_support_required_observe",
                "blocked_by": "energy_soft_block",
                "action_none_reason": "execution_soft_blocked",
                "cluster_count": 12,
                "cluster_share": 0.5,
                "summary_ko": "BTCUSD semantic observe cluster",
                "why_now_ko": "cluster repeated",
                "recommended_action_ko": "observe via detector loop",
                "evidence_lines_ko": ["- cluster_count: 12"],
                "registry_key": "misread:semantic_baseline_no_action_cluster",
                "primary_registry_key_override": "misread:semantic_baseline_no_action_cluster",
                "extra_evidence_registry_keys": ["misread:semantic_baseline_no_action_cluster"],
                "result_type": "result_unresolved",
                "explanation_type": "explanation_gap",
                "misread_confidence": 0.72,
                "priority_score": 63.0,
            }
        ],
    )

    payload = detector_module.build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        runtime_status_detail_payload={},
        readiness_surface_payload={},
        scene_disagreement_payload={},
        scene_bias_preview_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-13T18:40:00+09:00",
    )

    row = payload["scene_aware_detector"]["surfaced_rows"][0]
    assert row["semantic_cluster_key"].startswith("BTCUSD |")
    assert row["registry_key"] == "misread:semantic_baseline_no_action_cluster"
    assert "misread:semantic_baseline_no_action_cluster" in row["evidence_registry_keys"]
    assert payload["feedback_issue_refs"][0]["registry_key"] == "misread:semantic_baseline_no_action_cluster"
