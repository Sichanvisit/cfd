from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd

from backend.core.config import Config
from backend.services.improvement_detector_feedback_runtime import build_detector_feedback_entry
from backend.services.telegram_ops_service import TelegramOpsService, resolve_completed_window


KST = ZoneInfo("Asia/Seoul")


def _closed_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "trade_link_key": "t1",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 09:10:00",
                "profit": -3.0,
                "gross_pnl": -2.4,
                "cost_total": 0.6,
                "net_pnl_after_cost": -3.0,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.8,
            },
            {
                "trade_link_key": "t2",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 09:30:00",
                "profit": -2.0,
                "gross_pnl": -1.4,
                "cost_total": 0.6,
                "net_pnl_after_cost": -2.0,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.7,
            },
            {
                "trade_link_key": "t3",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 10:00:00",
                "profit": -1.5,
                "gross_pnl": -0.9,
                "cost_total": 0.6,
                "net_pnl_after_cost": -1.5,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.9,
            },
            {
                "trade_link_key": "t4",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 11:00:00",
                "profit": 0.5,
                "gross_pnl": 1.1,
                "cost_total": 0.6,
                "net_pnl_after_cost": 0.5,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "runner",
                "peak_profit_at_exit": 1.8,
            },
            {
                "trade_link_key": "t5",
                "symbol": "BTCUSD",
                "close_time": "2026-04-11 11:30:00",
                "profit": -1.0,
                "gross_pnl": -0.4,
                "cost_total": 0.6,
                "net_pnl_after_cost": -1.0,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.6,
            },
            {
                "trade_link_key": "t6",
                "symbol": "XAUUSD",
                "close_time": "2026-04-11 14:00:00",
                "profit": 4.0,
                "gross_pnl": 4.5,
                "cost_total": 0.5,
                "net_pnl_after_cost": 4.0,
                "lot": 0.02,
                "entry_reason": "reclaim",
                "exit_reason": "target",
                "peak_profit_at_exit": 5.0,
            },
        ]
    )


def test_telegram_ops_service_handles_propose_command_and_sends_report_and_inbox(
    monkeypatch,
    tmp_path,
):
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )
    monkeypatch.setattr(Config, "TG_ALLOWED_USER_IDS", (1001,))
    sent_report: list[str] = []
    sent_check: list[str] = []
    sent_reply: list[dict[str, object]] = []

    monkeypatch.setattr(
        "backend.services.telegram_ops_service.notifier.send_report_telegram",
        lambda message, parse_mode=None: sent_report.append(message) or True,
    )
    monkeypatch.setattr(
        "backend.services.telegram_ops_service.notifier.send_check_telegram",
        lambda message, parse_mode=None: sent_check.append(message) or True,
    )
    monkeypatch.setattr(
        "backend.services.telegram_ops_service.notifier.send_telegram_sync",
        lambda message, **kwargs: sent_reply.append({"message": message, **kwargs}) or {"result": {"message_id": 1}},
    )

    result = service._handle_message_command(
        {
            "text": "/propose 50",
            "from": {"id": 1001, "username": "ops_user"},
            "chat": {"id": "chat-check"},
            "message_thread_id": 4,
        },
        trade_logger=SimpleNamespace(read_closed_df=_closed_frame),
    )

    assert result is True
    assert "surface" in sent_reply[0]["message"]
    assert len(sent_report) == 1
    assert len(sent_check) == 1


def test_telegram_ops_service_propose_surfaces_feedback_aware_priority(
    monkeypatch,
    tmp_path,
):
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )
    monkeypatch.setattr(Config, "TG_ALLOWED_USER_IDS", (1001,))
    sent_report: list[str] = []
    sent_check: list[str] = []
    sent_reply: list[dict[str, object]] = []

    issue_ref = {
        "feedback_ref": "D1",
        "feedback_key": "detfb_feedback_aware",
        "detector_key": "candle_weight_detector",
        "symbol": "BTCUSD",
        "summary_ko": "BTCUSD upper_reject_mixed_confirm candle overweight",
    }
    service.state["detect_feedback_history"] = [
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="confirmed",
            user_id=1001,
            username="ops",
            now_ts="2026-04-12T02:10:00+09:00",
        ),
        build_detector_feedback_entry(
            issue_ref=issue_ref,
            verdict="missed",
            user_id=1001,
            username="ops",
            now_ts="2026-04-12T02:20:00+09:00",
        ),
    ]
    service.state["latest_detect_issue_refs"] = {
        "generated_at": "2026-04-12T02:20:00+09:00",
        "proposal_id": "detector-proposal-1",
        "items": [issue_ref],
    }

    monkeypatch.setattr(
        "backend.services.telegram_ops_service.notifier.send_report_telegram",
        lambda message, parse_mode=None: sent_report.append(message) or True,
    )
    monkeypatch.setattr(
        "backend.services.telegram_ops_service.notifier.send_check_telegram",
        lambda message, parse_mode=None: sent_check.append(message) or True,
    )
    monkeypatch.setattr(
        "backend.services.telegram_ops_service.notifier.send_telegram_sync",
        lambda message, **kwargs: sent_reply.append({"message": message, **kwargs}) or {"result": {"message_id": 1}},
    )

    result = service._handle_message_command(
        {
            "text": "/propose 50",
            "from": {"id": 1001, "username": "ops_user"},
            "chat": {"id": "chat-check"},
            "message_thread_id": 4,
        },
        trade_logger=SimpleNamespace(read_closed_df=_closed_frame),
    )

    assert result is True
    assert "feedback-aware" in sent_report[0]
    assert "feedback-aware" in sent_check[0]
    assert "feedback-aware" in sent_reply[0]["message"]


def test_telegram_ops_service_appends_daily_lesson_lines_to_1d_pnl(monkeypatch, tmp_path):
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )
    service.state["pnl_last_sent"] = {}
    sent_pnl: list[dict[str, object]] = []

    monkeypatch.setattr(
        "backend.services.telegram_ops_service.notifier.send_pnl_telegram",
        lambda window_code, message, parse_mode=None: sent_pnl.append({"window_code": window_code, "message": message}) or True,
    )
    monkeypatch.setattr(service, "_resolve_current_account_balance", lambda trade_logger: 1000.0)

    fixed_now = datetime(2026, 4, 12, 1, 5, tzinfo=KST)
    monkeypatch.setattr(
        "backend.services.telegram_ops_service.resolve_completed_window",
        lambda window_code: resolve_completed_window(window_code, fixed_now),
    )

    service._emit_due_pnl(SimpleNamespace(read_closed_df=_closed_frame))

    daily_message = next(item["message"] for item in sent_pnl if item["window_code"] == "1D")
    assert "MFE" in daily_message
