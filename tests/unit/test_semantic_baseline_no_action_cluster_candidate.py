from backend.services.semantic_baseline_no_action_cluster_candidate import (
    SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY,
    SEMANTIC_CONTINUATION_GAP_PRIMARY_REGISTRY_KEY,
    build_semantic_baseline_no_action_cluster_candidates,
)


def test_semantic_cluster_candidate_builds_dominant_clusters() -> None:
    rows = build_semantic_baseline_no_action_cluster_candidates(
        sample_audit_payload={
            "summary": {
                "baseline_no_action_count": 40,
                "cluster_counts": {
                    "BTCUSD | outer_band_reversal_support_required_observe | energy_soft_block | execution_soft_blocked": 21,
                    "BTCUSD | outer_band_reversal_support_required_observe | outer_band_guard | probe_not_promoted": 15,
                },
                "semantic_shadow_trace_quality_counts": {
                    "unavailable": 40,
                },
            }
        }
    )

    assert len(rows) == 2
    top = rows[0]
    assert top["registry_key"] == SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY
    assert top["symbol"] == "BTCUSD"
    assert top["cluster_count"] == 21
    assert top["cluster_share"] > 0.5
    assert top["misread_confidence"] > 0.0


def test_semantic_cluster_candidate_uses_symbol_local_share_for_continuation_gap() -> None:
    rows = build_semantic_baseline_no_action_cluster_candidates(
        sample_audit_payload={
            "summary": {
                "baseline_no_action_count": 82,
                "symbol_counts": {
                    "BTCUSD": 66,
                    "NAS100": 16,
                },
                "cluster_counts": {
                    "BTCUSD | outer_band_reversal_support_required_observe | outer_band_guard | probe_not_promoted": 40,
                    "NAS100 | upper_break_fail_confirm | energy_soft_block | execution_soft_blocked": 15,
                },
                "semantic_shadow_trace_quality_counts": {
                    "unavailable": 82,
                },
            }
        }
    )

    nas_rows = [row for row in rows if row["symbol"] == "NAS100"]
    assert len(nas_rows) == 1
    nas_row = nas_rows[0]
    assert nas_row["registry_key"] == SEMANTIC_CONTINUATION_GAP_PRIMARY_REGISTRY_KEY
    assert nas_row["cluster_symbol_share"] > 0.90
    assert "상승 지속 누락 가능성 관찰" in nas_row["summary_ko"]
    assert any("계속 올라갈 가능성" in line for line in nas_row["evidence_lines_ko"])
