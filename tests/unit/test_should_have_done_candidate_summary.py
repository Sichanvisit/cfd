import json

from backend.services.should_have_done_candidate_summary import (
    build_should_have_done_candidate_summary,
    generate_and_write_should_have_done_candidate_summary,
)


def test_build_should_have_done_candidate_summary_collects_surface_and_promotion_candidates():
    report = build_should_have_done_candidate_summary(
        latest_signal_by_symbol={
            "BTCUSD": {
                "symbol": "BTCUSD",
                "timestamp": "2026-04-15T22:10:00+09:00",
                "directional_continuation_overlay_direction": "UP",
                "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_score": 0.74,
                "directional_continuation_overlay_selection_state": "UP_SELECTED",
                "execution_diff_final_action_side": "SELL",
            }
        },
        ai_entry_traces=[
            {
                "symbol": "XAUUSD",
                "time": "2026-04-15T23:10:00+09:00",
                "execution_diff_promoted_action_side": "SELL",
                "execution_diff_final_action_side": "BUY",
                "execution_diff_promotion_suppressed_reason": "probe_not_promoted",
            }
        ],
    )

    summary = report["summary"]
    assert summary["status"] == "READY"
    assert summary["candidate_count"] == 2
    assert summary["candidate_source_count_summary"]["AUTO_SURFACE_EXECUTION_MISMATCH"] == 1
    assert summary["candidate_source_count_summary"]["AUTO_PROMOTION_REVIEW"] == 1
    rows = report["recent_candidate_rows"]
    assert any(row["expected_direction"] == "UP" for row in rows)
    assert any(row["expected_direction"] == "DOWN" for row in rows)


def test_generate_and_write_should_have_done_candidate_summary_writes_artifacts(tmp_path):
    report = generate_and_write_should_have_done_candidate_summary(
        latest_signal_by_symbol={
            "NAS100": {
                "symbol": "NAS100",
                "time": "2026-04-15T15:30:00+09:00",
                "directional_continuation_overlay_direction": "DOWN",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_score": 0.51,
                "execution_diff_final_action_side": "BUY",
            }
        },
        ai_entry_traces=[],
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "should_have_done_candidate_summary_latest.json"
    md_path = tmp_path / "should_have_done_candidate_summary_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
