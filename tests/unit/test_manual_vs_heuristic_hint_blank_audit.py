import pandas as pd

from backend.services.manual_vs_heuristic_hint_blank_audit import (
    build_manual_vs_heuristic_hint_blank_audit,
)


def test_hint_blank_audit_classifies_missing_source_schema_fields(tmp_path) -> None:
    comparison = pd.DataFrame(
        [
            {
                "episode_id": "btc_episode_001",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-02T15:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "heuristic_source_file": "entry_decisions.legacy_20260402_232858.csv",
                "heuristic_source_kind": "legacy",
                "heuristic_match_gap_minutes": 5,
                "heuristic_barrier_main_label": "",
                "heuristic_wait_family": "",
                "heuristic_forecast_family": "",
                "heuristic_belief_family": "",
                "heuristic_barrier_reason_summary": "",
                "review_comment": "nearest entry_decisions heuristic snapshot; match_reason=matched; gap_minutes=5.0",
            }
        ]
    )
    trades_dir = tmp_path / "trades"
    trades_dir.mkdir()
    pd.DataFrame(
        [
            {
                "time": "2026-04-02T00:00:00",
                "symbol": "BTCUSD",
            }
        ]
    ).to_csv(trades_dir / "entry_decisions.legacy_20260402_232858.csv", index=False, encoding="utf-8-sig")

    matched, summary = build_manual_vs_heuristic_hint_blank_audit(comparison, trades_dir=trades_dir)

    assert len(matched) == 1
    assert summary["matched_case_count"] == 1
    assert summary["barrier_root_cause_counts"]["source_schema_missing_barrier_fields"] == 1
    assert summary["wait_root_cause_counts"]["wait_derivation_blocked_by_missing_barrier_fields"] == 1
    assert summary["forecast_root_cause_counts"]["source_schema_missing_forecast_field"] == 1
    assert summary["belief_root_cause_counts"]["source_schema_missing_belief_field"] == 1
