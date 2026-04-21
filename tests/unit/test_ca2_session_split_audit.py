import json

from backend.services.ca2_session_split_audit import (
    build_ca2_session_split_audit,
    generate_and_write_ca2_session_split_audit,
)


def _resolved_rows(timestamp: str, *, correct: int, incorrect: int, horizon: int = 20):
    rows = []
    for _ in range(int(correct)):
        rows.append(
            {
                "observed_at": timestamp,
                "evaluated_at": timestamp,
                "horizon_bars": horizon,
                "evaluation_state": "CORRECT",
            }
        )
    for _ in range(int(incorrect)):
        rows.append(
            {
                "observed_at": timestamp,
                "evaluated_at": timestamp,
                "horizon_bars": horizon,
                "evaluation_state": "INCORRECT",
            }
        )
    return rows


def test_build_ca2_session_split_audit_reports_significant_session_gap():
    report = build_ca2_session_split_audit(
        accuracy_state_payload={
            "resolved_observations": [
                *_resolved_rows("2026-04-15T08:00:00+09:00", correct=18, incorrect=2),
                *_resolved_rows("2026-04-15T01:00:00+09:00", correct=10, incorrect=10),
            ]
        },
        entry_payload_rows=[],
        ai_entry_traces=[],
    )

    summary = report["summary"]
    assert summary["status"] == "READY"
    assert summary["measured_count_by_session"]["ASIA"] == 20
    assert summary["measured_count_by_session"]["US"] == 20
    assert summary["correct_rate_by_session"]["ASIA"] == 0.9
    assert summary["correct_rate_by_session"]["US"] == 0.5
    assert summary["session_difference_significance"]["status"] == "SIGNIFICANT"
    assert summary["session_difference_significance"]["pair"] == "ASIA|US"


def test_build_ca2_session_split_audit_holds_when_samples_are_insufficient():
    report = build_ca2_session_split_audit(
        accuracy_state_payload={
            "resolved_observations": [
                *_resolved_rows("2026-04-15T16:00:00+09:00", correct=5, incorrect=3),
                *_resolved_rows("2026-04-15T22:00:00+09:00", correct=6, incorrect=2),
            ]
        },
        entry_payload_rows=[],
        ai_entry_traces=[],
    )

    summary = report["summary"]
    assert summary["status"] == "HOLD"
    assert "session_samples_present_but_insufficient" in summary["status_reasons"]
    assert summary["session_difference_significance"]["status"] == "INSUFFICIENT_SAMPLE"


def test_build_ca2_session_split_audit_splits_guard_and_promotion_traces_by_session():
    report = build_ca2_session_split_audit(
        accuracy_state_payload={
            "resolved_observations": _resolved_rows(
                "2026-04-15T08:00:00+09:00",
                correct=1,
                incorrect=0,
            )
        },
        entry_payload_rows=[
            {
                "time": "2026-04-15T08:10:00+09:00",
                "active_action_conflict_guard_applied": True,
            },
            {
                "time": "2026-04-15T22:10:00+09:00",
                "active_action_conflict_guard_applied": False,
            },
        ],
        ai_entry_traces=[
            {
                "time": "2026-04-15T22:20:00+09:00",
                "execution_diff_promotion_active": True,
            },
            {
                "time": "2026-04-15T08:20:00+09:00",
                "execution_diff_promotion_active": False,
            },
        ],
    )

    assert report["guard_trace_by_session"]["ASIA"]["guard_applied_count"] == 1
    assert report["guard_trace_by_session"]["EU_US_OVERLAP"]["guard_applied_count"] == 0
    assert report["promotion_trace_by_session"]["EU_US_OVERLAP"]["promotion_active_count"] == 1
    assert report["promotion_trace_by_session"]["ASIA"]["promotion_active_count"] == 0
    assert report["summary"]["guard_helpful_rate_by_session"]["ASIA"] is None
    assert report["summary"]["promotion_win_rate_by_session"]["EU_US_OVERLAP"] is None


def test_generate_and_write_ca2_session_split_audit_writes_artifacts(tmp_path):
    accuracy_state_path = tmp_path / "directional_continuation_accuracy_tracker_state.json"
    accuracy_state_path.write_text(
        json.dumps(
            {
                "resolved_observations": [
                    *_resolved_rows("2026-04-15T08:00:00+09:00", correct=10, incorrect=10),
                    *_resolved_rows("2026-04-15T01:00:00+09:00", correct=15, incorrect=5),
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    entry_detail_path = tmp_path / "entry_decisions.detail.jsonl"
    entry_detail_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "payload": {
                            "time": "2026-04-15T08:10:00+09:00",
                            "active_action_conflict_guard_applied": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "payload": {
                            "time": "2026-04-15T22:10:00+09:00",
                            "active_action_conflict_guard_applied": False,
                        }
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = generate_and_write_ca2_session_split_audit(
        ai_entry_traces=[
            {
                "time": "2026-04-15T22:20:00+09:00",
                "execution_diff_promotion_active": True,
            }
        ],
        accuracy_state_path=accuracy_state_path,
        entry_decision_detail_path=entry_detail_path,
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "ca2_session_split_audit_latest.json"
    md_path = tmp_path / "ca2_session_split_audit_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
