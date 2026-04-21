import json

from backend.services.manual_vs_heuristic_global_detail_fallback_audit import (
    build_manual_vs_heuristic_global_detail_fallback_audit,
    discover_detail_paths,
)


def test_global_detail_fallback_audit_recovers_from_non_paired_detail_file(tmp_path) -> None:
    trades_dir = tmp_path / "trades"
    trades_dir.mkdir()

    paired_detail = trades_dir / "entry_decisions.legacy_paired.detail.jsonl"
    paired_detail.write_text("", encoding="utf-8")

    other_detail = trades_dir / "entry_decisions.legacy_other.detail.jsonl"
    payload = {
        "time": "2026-04-03T23:53:24+09:00",
        "signal_bar_ts": 1775196900.0,
        "symbol": "NAS100",
        "decision_row_key": "row-3",
        "core_reason": "core_shadow_observe_wait",
        "observe_reason": "lower_rebound_probe_observe",
        "blocked_by": "",
        "entry_wait_decision": "wait_soft_helper_block",
        "barrier_state_v1": json.dumps({"buy_barrier": 0.2}),
        "belief_state_v1": json.dumps({"buy_belief": 0.4}),
        "forecast_effective_policy_v1": json.dumps({"layer": "Forecast"}),
        "observe_confirm_v2": json.dumps({"state": "OBSERVE", "action": "WAIT"}),
    }
    other_detail.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "v1",
                "row_key": "row-3",
                "payload": payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    matched_cases = [
        {
            "episode_id": "nas_episode_003",
            "symbol": "NAS100",
            "anchor_time": "2026-04-03T15:15:00+09:00",
            "manual_wait_teacher_label": "good_wait_better_entry",
            "heuristic_source_file": "entry_decisions.legacy_paired.csv",
        }
    ]

    frame, summary = build_manual_vs_heuristic_global_detail_fallback_audit(
        matched_cases,
        trades_dir=trades_dir,
        max_gap_minutes=10,
    )

    assert len(frame) == 1
    row = frame.iloc[0].to_dict()
    assert row["global_detail_row_found"] == 1
    assert row["global_detail_source_file"] == "entry_decisions.legacy_other.detail.jsonl"
    assert row["global_detail_recoverability_grade"] == "high"
    assert summary["global_detail_row_found_count"] == 1
    assert summary["recoverability_grade_counts"]["high"] == 1


def test_discover_detail_paths_includes_rotate_archives(tmp_path) -> None:
    trades_dir = tmp_path / "trades"
    trades_dir.mkdir()
    (trades_dir / "entry_decisions.detail.jsonl").write_text("", encoding="utf-8")
    (trades_dir / "entry_decisions.detail.rotate_20260402_210954_772382.jsonl").write_text("", encoding="utf-8")
    (trades_dir / "entry_decisions.legacy_20260404_000006.detail.jsonl").write_text("", encoding="utf-8")

    names = [path.name for path in discover_detail_paths(trades_dir)]

    assert "entry_decisions.detail.jsonl" in names
    assert "entry_decisions.detail.rotate_20260402_210954_772382.jsonl" in names
    assert "entry_decisions.legacy_20260404_000006.detail.jsonl" in names


def test_global_detail_fallback_uses_archive_scan_prefilter(tmp_path) -> None:
    trades_dir = tmp_path / "trades"
    trades_dir.mkdir()
    wanted = trades_dir / "entry_decisions.detail.rotate_20260403_123318_780225.jsonl"
    unwanted = trades_dir / "entry_decisions.detail.rotate_20260406_193456_518810.jsonl"
    payload = {
        "time": "2026-04-03T12:15:00+09:00",
        "signal_bar_ts": 1775196900.0,
        "symbol": "NAS100",
        "decision_row_key": "row-4",
        "barrier_state_v1": json.dumps({"buy_barrier": 0.2}),
        "belief_state_v1": json.dumps({"buy_belief": 0.4}),
        "forecast_effective_policy_v1": json.dumps({"layer": "Forecast"}),
        "observe_confirm_v2": json.dumps({"state": "OBSERVE", "action": "WAIT"}),
        "entry_wait_decision": "wait",
    }
    wanted.write_text(json.dumps({"payload": payload}) + "\n", encoding="utf-8")
    unwanted.write_text(json.dumps({"payload": payload}) + "\n", encoding="utf-8")

    scan_path = tmp_path / "archive_scan.csv"
    scan_path.write_text(
        "archive_file,archive_kind,archive_format,row_count,time_min,time_max,signal_bar_min,signal_bar_max,barrier_field_present,barrier_value_rows,belief_field_present,belief_value_rows,forecast_field_present,forecast_value_rows,wait_field_present,wait_value_rows\n"
        "entry_decisions.detail.rotate_20260403_123318_780225.jsonl,rotate_detail,detail_jsonl,1,2026-04-03T12:15:00,2026-04-03T12:15:00,2026-04-03T15:15:00,2026-04-03T15:15:00,1,1,1,1,1,1,1,1\n"
        "entry_decisions.detail.rotate_20260406_193456_518810.jsonl,rotate_detail,detail_jsonl,1,2026-04-06T19:00:00,2026-04-06T19:00:00,2026-04-06T19:00:00,2026-04-06T19:00:00,1,1,1,1,1,1,1,1\n",
        encoding="utf-8-sig",
    )

    matched_cases = [
        {
            "episode_id": "nas_episode_004",
            "symbol": "NAS100",
            "anchor_time": "2026-04-03T15:15:00+09:00",
            "manual_wait_teacher_label": "good_wait_better_entry",
            "heuristic_source_file": "entry_decisions.legacy_any.csv",
        }
    ]

    frame, summary = build_manual_vs_heuristic_global_detail_fallback_audit(
        matched_cases,
        trades_dir=trades_dir,
        archive_scan_path=scan_path,
        max_gap_minutes=10,
    )

    assert len(frame) == 1
    row = frame.iloc[0].to_dict()
    assert row["global_detail_source_file"] == wanted.name
    assert summary["global_detail_files_scanned"] == 1
