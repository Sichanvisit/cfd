from __future__ import annotations

from pathlib import Path

from backend.services.checkpoint_improvement_first_symbol_focus_runtime import (
    build_checkpoint_improvement_first_symbol_focus_runtime,
)


def _board(*, status: str = "WATCHLIST", rows: int = 10, floor: int = 50) -> dict[str, object]:
    return {
        "summary": {
            "blocking_reason": "pa8_live_window_pending",
            "next_required_action": "keep_closeout_watchlist_on_btcusd",
        },
        "readiness_state": {
            "first_symbol_closeout_handoff_surface": {
                "observation_status": status,
                "primary_symbol": "BTCUSD",
                "observation_stage": "PA8_CLOSEOUT",
                "focus_progress_ratio": rows / floor if floor else 0.0,
                "observed_window_row_count": rows,
                "sample_floor": floor,
                "active_trigger_count": 1,
                "recommended_next_action": "keep_closeout_watchlist_on_btcusd",
                "reason_ko": "첫 번째 closeout 후보를 계속 관찰합니다.",
            }
        },
    }


def test_first_symbol_focus_runtime_tracks_progress_delta(tmp_path: Path) -> None:
    json_path = tmp_path / "focus.json"
    md_path = tmp_path / "focus.md"

    build_checkpoint_improvement_first_symbol_focus_runtime(
        master_board_payload=_board(rows=10, floor=50),
        now_ts="2026-04-13T05:00:00+09:00",
        output_json_path=json_path,
        output_markdown_path=md_path,
    )
    payload = build_checkpoint_improvement_first_symbol_focus_runtime(
        master_board_payload=_board(rows=25, floor=50),
        now_ts="2026-04-13T05:01:00+09:00",
        output_json_path=json_path,
        output_markdown_path=md_path,
    )

    assert payload["summary"]["progress_pct"] == 50.0
    assert payload["summary"]["progress_delta_pct"] == 30.0
    assert payload["summary"]["progress_bucket"] == "FIFTY"


def test_first_symbol_focus_runtime_marks_status_change(tmp_path: Path) -> None:
    json_path = tmp_path / "focus.json"
    md_path = tmp_path / "focus.md"

    build_checkpoint_improvement_first_symbol_focus_runtime(
        master_board_payload=_board(status="WATCHLIST", rows=25, floor=50),
        now_ts="2026-04-13T05:00:00+09:00",
        output_json_path=json_path,
        output_markdown_path=md_path,
    )
    payload = build_checkpoint_improvement_first_symbol_focus_runtime(
        master_board_payload=_board(status="CONCENTRATED", rows=41, floor=50),
        now_ts="2026-04-13T05:01:00+09:00",
        output_json_path=json_path,
        output_markdown_path=md_path,
    )

    assert payload["summary"]["trigger_state"] == "FIRST_SYMBOL_STATUS_CHANGED"
    assert payload["summary"]["status"] == "CONCENTRATED"
