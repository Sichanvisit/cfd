from backend.services.semantic_baseline_no_action_gate_review_candidate import (
    SEMANTIC_BASELINE_NO_ACTION_GATE_REVIEW_PRIMARY_REGISTRY_KEY,
    build_semantic_baseline_no_action_gate_review_candidates,
)


def test_semantic_gate_review_candidate_builds_gate_backlog_rows() -> None:
    rows = build_semantic_baseline_no_action_gate_review_candidates(
        sample_audit_payload={
            "summary": {
                "baseline_no_action_count": 40,
                "symbol_counts": {"BTCUSD": 38, "NAS100": 2},
                "blocked_by_counts": {
                    "energy_soft_block": 22,
                    "outer_band_guard": 16,
                },
                "action_none_reason_counts": {
                    "execution_soft_blocked": 22,
                    "probe_not_promoted": 16,
                },
                "semantic_shadow_trace_quality_counts": {
                    "unavailable": 40,
                },
                "dominant_cluster": "BTCUSD | outer_band_reversal_support_required_observe | energy_soft_block | execution_soft_blocked",
                "dominant_cluster_count": 22,
            }
        }
    )

    assert len(rows) >= 3
    top = rows[0]
    assert top["registry_key"] == SEMANTIC_BASELINE_NO_ACTION_GATE_REVIEW_PRIMARY_REGISTRY_KEY
    assert top["symbol_scope"] == "BTCUSD"
    assert top["gate_count"] >= 22
    assert top["gate_share"] >= 0.4
    assert top["priority_score"] > 0.0
