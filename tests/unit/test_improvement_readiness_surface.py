from __future__ import annotations

import csv
from pathlib import Path

from backend.services.improvement_readiness_surface import (
    build_improvement_readiness_surface,
    build_pnl_readiness_digest_lines,
)


def _write_closed_trade_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_readiness_surface_builds_pa8_pa9_reverse_and_cost_summary(tmp_path: Path) -> None:
    closed_trade_csv = tmp_path / "trade_closed_history.csv"
    _write_closed_trade_csv(
        closed_trade_csv,
        [
            {
                "symbol": "BTCUSD",
                "gross_pnl": 12.0,
                "cost_total": 2.0,
                "net_pnl_after_cost": 10.0,
            },
            {
                "symbol": "XAUUSD",
                "gross_pnl": -5.0,
                "cost_total": 1.0,
                "net_pnl_after_cost": -6.0,
            },
        ],
    )

    payload = build_improvement_readiness_surface(
        phase="RUNNING",
        degraded_components=[],
        pa8_payload={
            "summary": {
                "active_symbol_count": 2,
                "live_observation_ready_count": 1,
                "recommended_next_action": "wait_for_more_live_rows",
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "live_observation_ready": True,
                    "observed_window_row_count": 30,
                    "active_trigger_count": 0,
                    "closeout_state": "READY_FOR_CLOSEOUT_REVIEW",
                    "first_window_status": "READY",
                    "recommended_next_action": "review_pa8_closeout_candidate",
                },
                {
                    "symbol": "XAUUSD",
                    "live_observation_ready": False,
                    "observed_window_row_count": 12,
                    "active_trigger_count": 1,
                    "closeout_state": "HOLD_CLOSEOUT_PENDING_LIVE_WINDOW",
                    "first_window_status": "PENDING",
                    "recommended_next_action": "wait_for_more_live_rows",
                },
            ],
        },
        pa9_handoff_payload={
            "summary": {
                "handoff_state": "HOLD_PENDING_PA8_LIVE_WINDOW",
                "recommended_next_action": "wait_for_pa8_closeout",
                "prepared_symbol_count": 1,
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "handoff_review_candidate": True,
                    "live_observation_ready": True,
                    "observed_window_row_count": 30,
                    "sample_floor": 30,
                    "active_trigger_count": 0,
                    "closeout_state": "READY_FOR_CLOSEOUT_REVIEW",
                }
            ],
        },
        pa9_review_payload={
            "summary": {
                "review_state": "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW",
                "recommended_next_action": "review_prepared_pa9_action_baseline_handoff_packet",
            }
        },
        pa9_apply_payload={
            "summary": {
                "apply_state": "HOLD_PENDING_REVIEW_APPROVAL",
                "recommended_next_action": "wait_for_review_approval",
            }
        },
        runtime_status_payload={
            "runtime_recycle": {
                "last_open_positions_count": 1,
            }
        },
        runtime_status_detail_payload={
            "pending_reverse_by_symbol": {
                "BTCUSD": {
                    "action": "BUY",
                    "score": 188.0,
                    "reasons": ["opposite_score_spike", "volatility_spike"],
                    "expires_in_sec": 14,
                }
            },
            "order_block_by_symbol": {
                "XAUUSD": {
                    "reason": "cooldown_active",
                    "remaining_sec": 9,
                }
            },
        },
        closed_trade_csv_path=closed_trade_csv,
        output_json_path=tmp_path / "improvement_readiness_surface_latest.json",
        output_markdown_path=tmp_path / "improvement_readiness_surface_latest.md",
        now_ts="2026-04-12T10:00:00+09:00",
    )

    summary = payload["summary"]
    assert summary["pa8_closeout_readiness_status"] == "PENDING_EVIDENCE"
    assert summary["pa8_closeout_focus_status"] == "READY_FOR_REVIEW"
    assert summary["pa8_focus_symbol_count"] == 1
    assert summary["pa8_primary_focus_symbol"] == "BTCUSD"
    assert summary["pa9_handoff_readiness_status"] == "READY_FOR_REVIEW"
    assert summary["reverse_readiness_status"] == "PENDING_EVIDENCE"
    assert summary["historical_cost_confidence_level"] == "MEDIUM"
    assert payload["pa8_closeout_surface"]["ready_symbol_count"] == 1
    assert payload["pa8_closeout_focus_surface"]["watchlist_symbol_count"] == 1
    assert payload["pa9_handoff_surface"]["ready_for_review_symbol_count"] == 1
    assert payload["reverse_surface"]["pending_symbol_count"] == 1
    assert payload["reverse_surface"]["blocked_symbol_count"] == 1
    assert payload["historical_cost_surface"]["recent_safe_trade_count"] == 2
    assert (tmp_path / "improvement_readiness_surface_latest.json").exists()
    assert (tmp_path / "improvement_readiness_surface_latest.md").exists()


def test_readiness_surface_marks_reverse_ready_for_apply_when_flat(tmp_path: Path) -> None:
    payload = build_improvement_readiness_surface(
        phase="RUNNING",
        degraded_components=[],
        runtime_status_payload={
            "runtime_recycle": {
                "last_open_positions_count": 0,
            }
        },
        runtime_status_detail_payload={
            "pending_reverse_by_symbol": {
                "BTCUSD": {
                    "action": "SELL",
                    "score": 201.0,
                    "reasons": ["plus_to_minus", "opposite_score_spike"],
                    "expires_in_sec": 18,
                }
            }
        },
        now_ts="2026-04-12T10:05:00+09:00",
    )

    assert payload["reverse_surface"]["readiness_status"] == "READY_FOR_APPLY"
    assert payload["summary"]["reverse_readiness_status"] == "READY_FOR_APPLY"
    assert payload["reverse_surface"]["ready_symbol_count"] == 1


def _legacy_test_readiness_digest_lines_render_operational_summary() -> None:
    lines = build_pnl_readiness_digest_lines(
        {
            "pa8_closeout_surface": {
                "readiness_status": "PENDING_EVIDENCE",
                "ready_symbol_count": 1,
                "active_symbol_count": 3,
            },
            "pa9_handoff_surface": {
                "readiness_status": "READY_FOR_REVIEW",
                "ready_for_review_symbol_count": 1,
                "ready_for_apply_symbol_count": 0,
            },
            "reverse_surface": {
                "readiness_status": "BLOCKED",
                "pending_symbol_count": 0,
                "blocked_symbol_count": 1,
                "ready_symbol_count": 0,
            },
            "historical_cost_surface": {
                "confidence_level": "LOW",
                "recent_safe_trade_count": 4,
                "recent_trade_count": 9,
            },
        }
    )

    joined = "\n".join(lines)
    assert "━━ 시스템 상태 ━━" in joined
    assert "PA8 closeout: PENDING_EVIDENCE (준비 1 / 활성 3)" in joined
    assert "PA9 handoff: READY_FOR_REVIEW (review 1 / apply 0)" in joined
    assert "reverse readiness: BLOCKED (pending 0 / blocked 1 / ready 0)" in joined
    assert "historical cost: LOW (최근 4 / 9건 안전)" in joined
