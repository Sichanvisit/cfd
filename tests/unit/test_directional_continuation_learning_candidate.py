import json

from backend.services.directional_continuation_learning_candidate import (
    DIRECTIONAL_CONTINUATION_DOWN_REGISTRY_KEY,
    DIRECTIONAL_CONTINUATION_UP_REGISTRY_KEY,
    build_directional_continuation_learning_candidates,
)


def test_directional_continuation_learning_candidates_merge_semantic_up_and_wrong_side_down() -> None:
    rows = build_directional_continuation_learning_candidates(
        semantic_cluster_candidates=[
            {
                "candidate_key": "NAS100 | upper_break_fail_confirm | energy_soft_block | execution_soft_blocked",
                "symbol": "NAS100",
                "cluster_count": 15,
                "cluster_share": 0.18,
                "cluster_symbol_share": 0.94,
                "priority_score": 71.0,
                "misread_confidence": 0.77,
                "summary_ko": "NAS100 상승 지속 누락 가능성 관찰",
                "why_now_ko": "계속 올라가는 장면이 blocked로만 반복됐습니다.",
                "recommended_action_ko": "관찰을 누적하고 승격합니다.",
                "evidence_lines_ko": ["- 추세 힌트: 계속 올라갈 가능성 누락 관찰"],
                "cluster_pattern_code": "continuation_gap",
                "registry_key": DIRECTIONAL_CONTINUATION_UP_REGISTRY_KEY,
                "extra_evidence_registry_keys": [DIRECTIONAL_CONTINUATION_UP_REGISTRY_KEY],
            }
        ],
        wrong_side_conflict_payload={
            "rows": [
                {
                    "symbol": "XAUUSD",
                    "primary_failure_label": "wrong_side_buy_pressure",
                    "continuation_failure_label": "missed_down_continuation",
                    "context_failure_label": "false_up_pressure_in_downtrend",
                    "bridge_surface_family": "follow_through_surface",
                    "bridge_surface_state": "continuation_follow",
                    "bias_gap": 0.81,
                },
                {
                    "symbol": "XAUUSD",
                    "primary_failure_label": "wrong_side_buy_pressure",
                    "continuation_failure_label": "missed_down_continuation",
                    "context_failure_label": "false_up_pressure_in_downtrend",
                    "bridge_surface_family": "follow_through_surface",
                    "bridge_surface_state": "continuation_follow",
                    "bias_gap": 0.76,
                },
            ]
        },
        market_family_entry_payload={"summary": {}},
    )

    assert len(rows) == 2
    up_row = next(row for row in rows if row["continuation_direction"] == "UP")
    down_row = next(row for row in rows if row["continuation_direction"] == "DOWN")

    assert up_row["registry_key"] == DIRECTIONAL_CONTINUATION_UP_REGISTRY_KEY
    assert up_row["source_kind"] == "semantic_baseline_no_action_cluster"
    assert down_row["registry_key"] == DIRECTIONAL_CONTINUATION_DOWN_REGISTRY_KEY
    assert down_row["source_kind"] == "wrong_side_conflict_harvest"
    assert down_row["repeat_count"] == 2
    assert down_row["symbol_share"] == 1.0
    assert down_row["context_failure_label"] == "false_up_pressure_in_downtrend"


def test_directional_continuation_learning_candidates_add_market_family_down_signal() -> None:
    rows = build_directional_continuation_learning_candidates(
        semantic_cluster_candidates=[],
        wrong_side_conflict_payload={"rows": []},
        market_family_entry_payload={
            "summary": {
                "symbol_row_counts": json.dumps({"XAUUSD": 80, "BTCUSD": 80}),
                "symbol_observe_reason_counts": json.dumps(
                    {
                        "XAUUSD": {
                            "upper_reject_confirm": 9,
                            "upper_edge_observe": 11,
                        },
                        "BTCUSD": {
                            "upper_break_fail_confirm": 28,
                        },
                    }
                ),
            }
        },
    )

    assert len(rows) == 2
    xau_row = next(row for row in rows if row["symbol"] == "XAUUSD")
    btc_row = next(row for row in rows if row["symbol"] == "BTCUSD")

    assert xau_row["continuation_direction"] == "DOWN"
    assert xau_row["registry_key"] == DIRECTIONAL_CONTINUATION_DOWN_REGISTRY_KEY
    assert "market-family observe" in xau_row["source_labels_ko"]
    assert xau_row["dominant_observe_reason"] in {"upper_reject_confirm", "upper_edge_observe"}

    assert btc_row["continuation_direction"] == "UP"
    assert btc_row["registry_key"] == DIRECTIONAL_CONTINUATION_UP_REGISTRY_KEY
