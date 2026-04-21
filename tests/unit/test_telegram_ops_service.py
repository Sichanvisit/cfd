from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd

from backend.services.telegram_ops_service import (
    TelegramOpsService,
    build_check_card_text,
    build_check_candidate_from_row,
    resolve_completed_window,
)
from backend.services.telegram_pnl_digest_formatter import build_telegram_pnl_digest_message


KST = ZoneInfo("Asia/Seoul")


def test_resolve_completed_window_for_15m_and_1m_month():
    now = datetime(2026, 4, 11, 15, 7, 30, tzinfo=KST)
    start_15m, end_15m, bucket_15m = resolve_completed_window("15m", now)
    assert start_15m == datetime(2026, 4, 11, 14, 45, tzinfo=KST)
    assert end_15m == datetime(2026, 4, 11, 15, 0, tzinfo=KST)
    assert bucket_15m == end_15m.isoformat()

    start_1m, end_1m, bucket_1m = resolve_completed_window("1M", now)
    assert start_1m == datetime(2026, 3, 1, 0, 0, tzinfo=KST)
    assert end_1m == datetime(2026, 4, 1, 0, 0, tzinfo=KST)
    assert bucket_1m == end_1m.isoformat()


def test_build_pnl_digest_message_uses_operational_summary_layout():
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 14:50:00",
                "profit": 10.0,
                "gross_pnl": 12.0,
                "cost_total": 2.0,
                "net_pnl_after_cost": 10.0,
                "lot": 0.10,
                "entry_reason": "reclaim",
                "exit_reason": "target",
            },
            {
                "symbol": "XAUUSD",
                "close_time": "2026-04-11 14:59:00",
                "profit": -3.0,
                "gross_pnl": -2.0,
                "cost_total": 1.0,
                "net_pnl_after_cost": -3.0,
                "lot": 0.20,
                "entry_reason": "probe",
                "exit_reason": "cut",
            },
            {
                "symbol": "NAS100",
                "close_time": "2026-04-11 15:02:00",
                "profit": 50.0,
                "gross_pnl": 50.0,
                "cost_total": 0.0,
                "net_pnl_after_cost": 50.0,
                "lot": 0.30,
                "entry_reason": "late",
                "exit_reason": "runner",
            },
        ]
    )
    start = datetime(2026, 4, 11, 14, 45, tzinfo=KST)
    end = datetime(2026, 4, 11, 15, 0, tzinfo=KST)

    message = build_telegram_pnl_digest_message(
        "15m",
        frame,
        start=start,
        end=end,
        current_balance=1000.0,
        timezone=KST,
    )

    assert "[손익 요약 | 15분]" in message
    assert "순손익 합계: +7.00 USD" in message
    assert "총손익(비용 전): +10.00 USD" in message
    assert "총 비용: 3.00 USD" in message
    assert "진입 횟수(마감 기준): 2회" in message
    assert "총 진입 랏: 0.30 lot" in message
    assert "승/패: 1 / 1 (승률 50.0%)" in message
    assert "구간 시작 잔고(추정): 943.00 USD" in message
    assert "구간 종료 잔고(추정): 950.00 USD" in message
    assert "진입 사유 TOP 5:" in message
    assert "리클레임 진입" in message
    assert "탐색 진입" in message
    assert "청산 사유 TOP 5:" in message
    assert "목표가 도달 청산" in message
    assert "위험 차단 청산" in message
    assert "NAS100" not in message


def test_build_pnl_digest_message_falls_back_to_profit_when_recent_net_columns_are_zero():
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 13:10:00",
                "profit": 12.0,
                "gross_pnl": 12.0,
                "cost_total": 0.0,
                "net_pnl_after_cost": 12.0,
                "lot": 0.10,
                "entry_reason": "reclaim",
                "exit_reason": "target",
                "ticket": "old-1",
            },
            {
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 14:50:00",
                "profit": 10.0,
                "gross_pnl": 0.0,
                "cost_total": 0.0,
                "net_pnl_after_cost": 0.0,
                "lot": 0.10,
                "entry_reason": "reclaim",
                "exit_reason": "target",
                "ticket": "recent-1",
            },
            {
                "symbol": "XAUUSD",
                "close_time": "2026-04-11 14:59:00",
                "profit": -3.0,
                "gross_pnl": 0.0,
                "cost_total": 0.0,
                "net_pnl_after_cost": 0.0,
                "lot": 0.20,
                "entry_reason": "probe",
                "exit_reason": "cut",
                "ticket": "recent-2",
            },
        ]
    )
    start = datetime(2026, 4, 11, 14, 45, tzinfo=KST)
    end = datetime(2026, 4, 11, 15, 0, tzinfo=KST)

    message = build_telegram_pnl_digest_message(
        "15m",
        frame,
        start=start,
        end=end,
        current_balance=1000.0,
        timezone=KST,
    )

    assert "순손익 합계: +7.00 USD" in message
    assert "총손익(비용 전): +7.00 USD" in message
    assert "총 비용: 0.00 USD" in message
    assert "진입 횟수(마감 기준): 2회" in message
    assert "총 진입 랏: 0.30 lot" in message
    assert "승/패: 1 / 1 (승률 50.0%)" in message


def test_build_pnl_digest_message_shows_balance_pending_when_snapshot_missing():
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 14:50:00",
                "net_pnl_after_cost": 10.0,
                "cost_total": 2.0,
                "lot": 0.10,
                "entry_reason": "flat_reclaim_reentry_ready",
                "exit_reason": "runner",
            }
        ]
    )
    start = datetime(2026, 4, 11, 14, 45, tzinfo=KST)
    end = datetime(2026, 4, 11, 15, 0, tzinfo=KST)

    message = build_telegram_pnl_digest_message("15m", frame, start=start, end=end, timezone=KST)

    assert "잔고 변화: 계좌 잔고 스냅샷이 아직 연결되지 않아 계산을 보류했습니다." in message
    assert "플랫 상태에서 리클레임 재진입 준비 (플랫, 리클레임, 재진입, 준비)" in message


def test_build_pnl_digest_message_uses_separate_entry_and_exit_reason_explanations():
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 14:50:00",
                "net_pnl_after_cost": 5.0,
                "cost_total": 1.0,
                "lot": 0.10,
                "entry_reason": "flat_reclaim_reentry_ready",
                "exit_reason": "protective_loss_exit",
            }
        ]
    )
    start = datetime(2026, 4, 11, 14, 45, tzinfo=KST)
    end = datetime(2026, 4, 11, 15, 0, tzinfo=KST)

    message = build_telegram_pnl_digest_message("15m", frame, start=start, end=end, timezone=KST)

    assert "플랫 상태에서 리클레임 재진입 준비 (플랫, 리클레임, 재진입, 준비)" in message
    assert "손실 보호 목적 청산 (보호, 손실, 청산)" in message


def test_build_pnl_digest_message_appends_daily_readiness_summary_lines():
    frame = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 14:50:00",
                "net_pnl_after_cost": 5.0,
                "cost_total": 1.0,
                "lot": 0.10,
                "entry_reason": "reclaim",
                "exit_reason": "target",
            }
        ]
    )
    start = datetime(2026, 4, 11, 0, 0, tzinfo=KST)
    end = datetime(2026, 4, 12, 0, 0, tzinfo=KST)

    message = build_telegram_pnl_digest_message(
        "1D",
        frame,
        start=start,
        end=end,
        timezone=KST,
        system_status_lines=[
            "━━ 시스템 상태 ━━",
            "PA8 closeout: PENDING_EVIDENCE (준비 0 / 활성 3)",
            "PA9 handoff: PENDING_EVIDENCE (review 0 / apply 0)",
        ],
    )

    assert "━━ 시스템 상태 ━━" in message
    assert "PA8 closeout: PENDING_EVIDENCE (준비 0 / 활성 3)" in message
    assert "PA9 handoff: PENDING_EVIDENCE (review 0 / apply 0)" in message


def test_build_check_candidate_from_row_for_entry_and_exit():
    entry_candidate = build_check_candidate_from_row(
        {
            "generated_at": "2026-04-11T15:10:00+09:00",
            "symbol": "BTCUSD",
            "checkpoint_id": "btc_cp_1",
            "checkpoint_type": "RECLAIM_CHECK",
            "position_side": "FLAT",
            "observe_side": "BUY",
            "runtime_scene_fine_label": "breakout_retest",
            "management_action_label": "REBUY",
            "management_action_confidence": 0.81,
            "management_action_reason": "flat_reclaim_reentry_ready",
        }
    )
    assert entry_candidate is not None
    assert entry_candidate["kind"] == "ENTRY"
    assert entry_candidate["recommended_action"] == "ENTER"
    assert entry_candidate["action_strength"] == "HIGH"

    exit_candidate = build_check_candidate_from_row(
        {
            "generated_at": "2026-04-11T15:10:00+09:00",
            "symbol": "XAUUSD",
            "checkpoint_id": "xau_cp_2",
            "checkpoint_type": "RUNNER_CHECK",
            "position_side": "SELL",
            "observe_side": "SELL",
            "runtime_scene_fine_label": "trend_exhaustion",
            "management_action_label": "FULL_EXIT",
            "management_action_confidence": 0.74,
            "management_action_reason": "open_loss_thesis_break",
            "unrealized_pnl_state": "OPEN_LOSS",
        }
    )
    assert exit_candidate is not None
    assert exit_candidate["kind"] == "EXIT"
    assert exit_candidate["recommended_action"] == "EXIT"
    assert exit_candidate["action_strength"] == "MEDIUM"


def test_build_check_card_text_explains_confidence_and_scope_in_korean():
    card = build_check_candidate_from_row(
        {
            "generated_at": "2026-04-11T15:10:00+09:00",
            "symbol": "BTCUSD",
            "checkpoint_id": "btc_cp_1",
            "checkpoint_type": "RECLAIM_CHECK",
            "position_side": "FLAT",
            "observe_side": "BUY",
            "runtime_scene_fine_label": "breakout_retest",
            "management_action_label": "REBUY",
            "management_action_confidence": 0.81,
            "management_action_reason": "flat_reclaim_reentry_ready",
        }
    )

    message = build_check_card_text(card or {})

    assert "권장 조치:" in message
    assert "판단 강도: 높음 (confidence 0.81)" in message
    assert "범위: 이번 checkpoint 1건 기준" in message


def test_telegram_ops_service_delegates_tgbridge_callback(monkeypatch, tmp_path):
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )
    handled_callbacks: list[dict[str, object]] = []

    fake_runtime = SimpleNamespace(
        telegram_update_poller=SimpleNamespace(
            handle_callback_query=lambda callback_query: (
                handled_callbacks.append(dict(callback_query))
                or {"summary": {"handled": True}}
            )
        )
    )
    monkeypatch.setattr(service, "_ensure_checkpoint_improvement_runtime", lambda: fake_runtime)

    result = service._handle_callback_query(
        {
            "id": "cbq-bridge",
            "data": "tgbridge:approve:1:approval-1",
            "from": {"id": 1001, "username": "ops_user"},
        }
    )

    assert result is True
    assert handled_callbacks[0]["data"] == "tgbridge:approve:1:approval-1"


def test_telegram_ops_service_does_not_scan_live_check_cards_when_disabled(tmp_path):
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )
    service.live_check_approvals_enabled = False
    service.checkpoint_rows_path.write_text(
        "generated_at,symbol,checkpoint_id,checkpoint_type,position_side,observe_side,management_action_label,management_action_confidence\n"
        "2026-04-11T15:10:00+09:00,BTCUSD,btc_cp_1,RECLAIM_CHECK,FLAT,BUY,REBUY,0.91\n",
        encoding="utf-8-sig",
    )

    service._scan_checkpoint_cards()

    assert service.state.get("check_cards", {}) == {}


def test_store_latest_detect_issue_refs_preserves_last_non_empty_refs_on_empty_detect(tmp_path):
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )

    service._store_latest_detect_issue_refs(
        {
            "generated_at": "2026-04-13T18:51:00+09:00",
            "proposal_envelope": {
                "proposal_id": "prop_detect_non_empty",
                "summary_ko": "detector 관찰 6건",
                "readiness_status": "READY_FOR_REVIEW",
            },
            "surfaced_detector_count": 6,
            "feedback_issue_refs": [{"ref": "D1"}, {"ref": "D2"}],
        }
    )

    service._store_latest_detect_issue_refs(
        {
            "generated_at": "2026-04-13T18:51:30+09:00",
            "proposal_envelope": {
                "proposal_id": "prop_detect_empty",
                "summary_ko": "surface 없음",
                "readiness_status": "PENDING_EVIDENCE",
            },
            "surfaced_detector_count": 0,
            "feedback_issue_refs": [],
        }
    )

    latest_refs = dict(service.state.get("latest_detect_issue_refs") or {})
    latest_result = dict(service.state.get("latest_detect_result") or {})

    assert latest_refs.get("proposal_id") == "prop_detect_non_empty"
    assert latest_refs.get("items") == [{"ref": "D1"}, {"ref": "D2"}]
    assert latest_result.get("proposal_id") == "prop_detect_empty"
    assert latest_result.get("feedback_issue_ref_count") == 0
    assert latest_result.get("surfaced_detector_count") == 0


def test_store_latest_detect_issue_refs_allows_initial_empty_detect_state(tmp_path):
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )

    service._store_latest_detect_issue_refs(
        {
            "generated_at": "2026-04-13T18:55:00+09:00",
            "proposal_envelope": {
                "proposal_id": "prop_detect_empty_first",
                "summary_ko": "surface 없음",
                "readiness_status": "PENDING_EVIDENCE",
            },
            "surfaced_detector_count": 0,
            "feedback_issue_refs": [],
        }
    )

    assert service.state.get("latest_detect_issue_refs") == {
        "generated_at": "2026-04-13T18:55:00+09:00",
        "proposal_id": "prop_detect_empty_first",
        "items": [],
    }
    assert service.state.get("latest_detect_result", {}).get("summary_ko") == "surface 없음"


def test_telegram_ops_service_rejects_tgops_callback_when_live_execution_approval_disabled(
    monkeypatch,
    tmp_path,
):
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )
    service.live_check_approvals_enabled = False
    seen_answers: list[dict[str, object]] = []
    monkeypatch.setattr(
        "backend.services.telegram_ops_service.notifier.answer_callback_query",
        lambda callback_query_id, text="", show_alert=False: (
            seen_answers.append(
                {
                    "callback_query_id": callback_query_id,
                    "text": text,
                    "show_alert": show_alert,
                }
            )
            or True
        ),
    )

    result = service._handle_callback_query(
        {
            "id": "cbq-live-disabled",
            "data": "tgops:approve:test-card-1",
            "from": {"id": 1001, "username": "ops_user"},
        }
    )

    assert result is False
    assert seen_answers == [
        {
            "callback_query_id": "cbq-live-disabled",
            "text": "실시간 진입/청산 승인 경로는 비활성 상태입니다.",
            "show_alert": True,
        }
    ]
