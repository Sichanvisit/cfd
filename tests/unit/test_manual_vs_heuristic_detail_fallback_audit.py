import json
from pathlib import Path

from backend.services.manual_vs_heuristic_detail_fallback_audit import (
    build_manual_vs_heuristic_detail_fallback_audit,
)


def test_detail_fallback_audit_marks_high_recoverability_when_semantic_payload_exists(tmp_path) -> None:
    trades_dir = tmp_path / "trades"
    trades_dir.mkdir()
    detail_path = trades_dir / "entry_decisions.legacy_foo.detail.jsonl"
    payload = {
        "time": "2026-04-03T15:21:00+09:00",
        "symbol": "NAS100",
        "decision_row_key": "row-1",
        "core_reason": "core_shadow_observe_wait",
        "observe_reason": "lower_rebound_probe_observe",
        "blocked_by": "",
        "entry_wait_decision": "wait_soft_helper_block",
        "entry_enter_value": 0.31,
        "entry_wait_value": 0.52,
        "barrier_state_v1": json.dumps({"buy_barrier": 0.2, "sell_barrier": 0.3}),
        "belief_state_v1": json.dumps({"buy_belief": 0.4, "sell_belief": 0.2}),
        "forecast_assist_v1": json.dumps({"decision_hint": "OBSERVE_FAVOR"}),
        "forecast_effective_policy_v1": json.dumps({"layer": "Forecast"}),
        "observe_confirm_v2": json.dumps({"state": "OBSERVE", "action": "WAIT"}),
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "v1",
                "row_key": "row-1",
                "payload": payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    matched_cases = [
        {
            "episode_id": "nas_episode_001",
            "symbol": "NAS100",
            "anchor_time": "2026-04-03T15:20:00+09:00",
            "manual_wait_teacher_label": "good_wait_better_entry",
            "heuristic_source_file": "entry_decisions.legacy_foo.csv",
        }
    ]

    frame, summary = build_manual_vs_heuristic_detail_fallback_audit(
        matched_cases,
        trades_dir=trades_dir,
        max_gap_minutes=10,
    )

    assert len(frame) == 1
    row = frame.iloc[0].to_dict()
    assert row["detail_row_found"] == 1
    assert row["detail_barrier_state_present"] == 1
    assert row["detail_observe_confirm_present"] == 1
    assert row["detail_recoverability_grade"] == "high"
    assert summary["detail_row_found_count"] == 1
    assert summary["recoverability_grade_counts"]["high"] == 1


def test_detail_fallback_audit_prefers_signal_bar_ts_over_record_time(tmp_path) -> None:
    trades_dir = tmp_path / "trades"
    trades_dir.mkdir()
    detail_path = trades_dir / "entry_decisions.legacy_bar.detail.jsonl"
    payload = {
        "time": "2026-04-03T23:53:24+09:00",
        "signal_bar_ts": 1775187600.0,
        "symbol": "NAS100",
        "decision_row_key": "row-2",
        "core_reason": "core_shadow_observe_wait",
        "observe_reason": "lower_rebound_probe_observe",
        "blocked_by": "",
        "entry_wait_decision": "wait_soft_helper_block",
        "barrier_state_v1": json.dumps({"buy_barrier": 0.2}),
        "belief_state_v1": json.dumps({"buy_belief": 0.4}),
        "forecast_effective_policy_v1": json.dumps({"layer": "Forecast"}),
        "observe_confirm_v2": json.dumps({"state": "OBSERVE", "action": "WAIT"}),
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "v1",
                "row_key": "row-2",
                "payload": payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    matched_cases = [
        {
            "episode_id": "nas_episode_002",
            "symbol": "NAS100",
            "anchor_time": "2026-04-03T12:40:00+09:00",
            "manual_wait_teacher_label": "good_wait_better_entry",
            "heuristic_source_file": "entry_decisions.legacy_bar.csv",
        }
    ]

    frame, summary = build_manual_vs_heuristic_detail_fallback_audit(
        matched_cases,
        trades_dir=trades_dir,
        max_gap_minutes=10,
    )

    assert len(frame) == 1
    row = frame.iloc[0].to_dict()
    assert row["detail_row_found"] == 1
    assert row["detail_match_gap_minutes"] == 0.0
    assert row["detail_recoverability_grade"] == "high"
    assert summary["detail_row_found_count"] == 1
