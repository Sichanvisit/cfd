from __future__ import annotations

from pathlib import Path

from backend.services.checkpoint_improvement_p5_observation_runtime import (
    build_checkpoint_improvement_p5_observation_runtime,
)


def _board(
    *,
    first_symbol_status: str = "WATCHLIST",
    first_symbol_symbol: str = "BTCUSD",
    first_symbol_stage: str = "closeout_watchlist",
    rows: int = 12,
    sample_floor: int = 30,
    active_trigger_count: int = 1,
    pa7_status: str = "CLEAR",
    pa7_group_count: int = 0,
) -> dict[str, object]:
    return {
        "summary": {
            "generated_at": "2026-04-13T04:10:00+09:00",
            "blocking_reason": "pa8_live_window_pending",
            "next_required_action": "wait_for_new_pa8_candidate_rows_or_market_reopen",
            "pa8_closeout_review_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
            "pa8_closeout_apply_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
            "pa9_handoff_readiness_status": "PENDING_EVIDENCE",
        },
        "readiness_state": {
            "first_symbol_closeout_handoff_surface": {
                "observation_status": first_symbol_status,
                "primary_symbol": first_symbol_symbol,
                "observation_stage": first_symbol_stage,
                "reason_ko": "첫 번째 closeout 후보를 집중 관찰합니다.",
                "recommended_next_action": "monitor_first_symbol_closeout_focus_and_wait_for_review_ready",
                "observed_window_row_count": rows,
                "sample_floor": sample_floor,
                "active_trigger_count": active_trigger_count,
                "focus_progress_ratio": rows / sample_floor if sample_floor else 0.0,
                "handoff_review_candidate": False,
                "handoff_apply_candidate": False,
            },
            "pa7_narrow_review_surface": {
                "status": pa7_status,
                "group_count": pa7_group_count,
                "mixed_wait_boundary_group_count": 1 if pa7_status == "REVIEW_NEEDED" else 0,
                "mixed_review_group_count": 0,
                "primary_group_key": "BTCUSD::mixed",
                "primary_symbol": "BTCUSD",
                "primary_review_disposition": "mixed_wait_boundary_review" if pa7_status == "REVIEW_NEEDED" else "",
                "reason_ko": "남아 있는 WAIT 경계 혼합 review를 다시 봐야 합니다." if pa7_status == "REVIEW_NEEDED" else "",
                "recommended_next_action": "review_remaining_mixed_wait_boundary_groups_before_first_closeout" if pa7_status == "REVIEW_NEEDED" else "continue_first_symbol_closeout_observation",
            },
        },
    }


def test_p5_observation_runtime_sends_check_and_report_on_first_symbol_escalation(tmp_path: Path) -> None:
    deliveries: list[tuple[str, str]] = []

    def _send_sync(message: str, *, route: str, parse_mode=None):
        deliveries.append((route, message))
        return {"ok": True, "result": {"message_id": len(deliveries), "chat": {"id": 1}}}

    json_path = tmp_path / "p5.json"
    markdown_path = tmp_path / "p5.md"

    build_checkpoint_improvement_p5_observation_runtime(
        master_board_payload=_board(first_symbol_status="WATCHLIST"),
        snapshot_json_path=json_path,
        snapshot_markdown_path=markdown_path,
        now_ts="2026-04-13T04:10:00+09:00",
        notify=True,
        send_sync=_send_sync,
    )
    deliveries.clear()

    payload = build_checkpoint_improvement_p5_observation_runtime(
        master_board_payload=_board(
            first_symbol_status="CONCENTRATED",
            first_symbol_stage="closeout_concentrated",
            rows=25,
            sample_floor=30,
            active_trigger_count=0,
        ),
        snapshot_json_path=json_path,
        snapshot_markdown_path=markdown_path,
        now_ts="2026-04-13T04:11:00+09:00",
        notify=True,
        send_sync=_send_sync,
    )

    assert payload["summary"]["trigger_state"] == "FIRST_SYMBOL_SURFACED"
    assert payload["summary"]["check_sent"] is True
    assert payload["summary"]["report_sent"] is True
    assert [route for route, _ in deliveries] == ["check", "report"]
    assert "CONCENTRATED" in deliveries[0][1]


def test_p5_observation_runtime_surfaces_pa7_narrow_review_needed(tmp_path: Path) -> None:
    deliveries: list[tuple[str, str]] = []

    def _send_sync(message: str, *, route: str, parse_mode=None):
        deliveries.append((route, message))
        return {"ok": True, "result": {"message_id": len(deliveries), "chat": {"id": 1}}}

    payload = build_checkpoint_improvement_p5_observation_runtime(
        master_board_payload=_board(pa7_status="REVIEW_NEEDED", pa7_group_count=2),
        snapshot_json_path=tmp_path / "p5.json",
        snapshot_markdown_path=tmp_path / "p5.md",
        now_ts="2026-04-13T04:12:00+09:00",
        notify=True,
        send_sync=_send_sync,
    )

    assert payload["summary"]["trigger_state"] == "PA7_NARROW_REVIEW_SURFACED"
    assert payload["pa7_narrow_review_event"]["current_status"] == "REVIEW_NEEDED"
    assert [route for route, _ in deliveries] == ["check", "report"]


def test_p5_observation_runtime_skips_notify_when_no_board_payload(tmp_path: Path) -> None:
    deliveries: list[tuple[str, str]] = []

    def _send_sync(message: str, *, route: str, parse_mode=None):
        deliveries.append((route, message))
        return {"ok": True}

    payload = build_checkpoint_improvement_p5_observation_runtime(
        master_board_payload={},
        snapshot_json_path=tmp_path / "p5.json",
        snapshot_markdown_path=tmp_path / "p5.md",
        now_ts="2026-04-13T04:12:00+09:00",
        notify=True,
        send_sync=_send_sync,
    )

    assert payload["summary"]["trigger_state"] == "MASTER_BOARD_MISSING"
    assert deliveries == []
