from __future__ import annotations

from zoneinfo import ZoneInfo

import backend.services.trade_feedback_runtime as runtime_module
from tests.unit.test_trade_feedback_runtime import _sample_closed_frame


KST = ZoneInfo("Asia/Seoul")


def test_proposal_snapshot_surfaces_directional_continuation_candidates(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_module,
        "build_semantic_baseline_no_action_cluster_candidates",
        lambda: [
            {
                "candidate_key": "NAS100 | upper_break_fail_confirm | energy_soft_block | execution_soft_blocked",
                "symbol": "NAS100",
                "cluster_count": 15,
                "cluster_share": 0.18,
                "cluster_symbol_share": 0.94,
                "priority_score": 71.0,
                "misread_confidence": 0.77,
                "summary_ko": "NAS100 상승 지속 누락 가능성 관찰",
                "why_now_ko": "계속 올라가는 장면이 blocked로만 반복됩니다.",
                "recommended_action_ko": "관찰을 누적합니다.",
                "evidence_lines_ko": ["- 추세 힌트: 계속 올라갈 가능성 누락 관찰"],
                "cluster_pattern_code": "continuation_gap",
                "registry_key": "misread:directional_up_continuation_conflict",
                "extra_evidence_registry_keys": ["misread:directional_up_continuation_conflict"],
            },
            {
                "candidate_key": "BTCUSD | outer_band_reversal_support_required_observe | outer_band_guard | probe_not_promoted",
                "symbol": "BTCUSD",
                "cluster_count": 40,
                "cluster_share": 0.48,
                "cluster_symbol_share": 0.60,
                "priority_score": 66.0,
                "misread_confidence": 0.71,
                "summary_ko": "BTCUSD baseline no-action observe cluster 관찰",
                "why_now_ko": "generic cluster",
                "recommended_action_ko": "generic review",
                "evidence_lines_ko": [],
                "cluster_pattern_code": "generic_observe_cluster",
                "observe_reason": "outer_band_reversal_support_required_observe",
                "blocked_by": "outer_band_guard",
                "action_none_reason": "probe_not_promoted",
                "registry_key": "misread:semantic_baseline_no_action_cluster",
            },
        ],
    )
    monkeypatch.setattr(
        runtime_module,
        "build_directional_continuation_learning_candidates",
        lambda **kwargs: [
            {
                "symbol": "XAUUSD",
                "continuation_direction": "DOWN",
                "summary_ko": "XAUUSD 하락 지속 누락 가능성 관찰",
                "why_now_ko": "반등처럼 읽었지만 실제로는 계속 내려가는 장면이 반복됐습니다.",
                "recommended_action_ko": "자동 관찰을 누적합니다.",
                "repeat_count": 4,
                "global_share": 0.44,
                "priority_score": 78.0,
                "registry_key": "misread:directional_down_continuation_conflict",
                "extra_evidence_registry_keys": ["misread:directional_down_continuation_conflict"],
                "source_kind": "wrong_side_conflict_harvest",
                "source_labels_ko": ["wrong-side conflict", "market-family observe"],
                "primary_failure_label": "wrong_side_buy_pressure",
                "context_failure_label": "false_up_pressure_in_downtrend",
                "continuation_failure_label": "missed_down_continuation",
                "pattern_label_ko": "하락 지속 누락",
                "dominant_observe_reason": "upper_reject_confirm",
            }
        ],
    )
    monkeypatch.setattr(
        runtime_module,
        "build_semantic_baseline_no_action_gate_review_candidates",
        lambda: [],
    )

    payload = runtime_module.build_manual_trade_proposal_snapshot(
        _sample_closed_frame(),
        recent_trade_limit=50,
        timezone=KST,
        now_ts="2026-04-14T15:00:00+09:00",
    )

    assert payload["directional_continuation_candidate_count"] == 1
    assert payload["semantic_cluster_candidate_count"] == 1
    assert any(
        "continuation 방향 학습 후보:" in str(line)
        for line in payload["report_lines_ko"]
    )
    assert any(
        "XAUUSD 하락 지속 누락 가능성 관찰" in str(line)
        for line in payload["report_lines_ko"]
    )
    assert any(
        "원천: wrong-side conflict / market-family observe" in str(line)
        for line in payload["report_lines_ko"]
    )
    assert "continuation 1건" in payload["inbox_summary_ko"]
