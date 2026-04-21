from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from backend.core.config import Config
from backend.services.telegram_ops_service import TelegramOpsService


def _closed_frame() -> pd.DataFrame:
    rows = []
    for index in range(5):
        rows.append(
            {
                "trade_link_key": f"bad-{index}",
                "symbol": "BTCUSD",
                "close_time": f"2026-04-12 0{index}:10:00",
                "profit": -2.0,
                "gross_pnl": -1.4,
                "cost_total": 0.6,
                "net_pnl_after_cost": -2.0,
                "lot": 0.01,
                "entry_reason": "upper_reject_mixed_confirm",
                "exit_reason": "cut",
                "peak_profit_at_exit": 0.8,
            }
        )
    return pd.DataFrame(rows)


def test_telegram_ops_service_handles_detect_command_and_includes_feedback_refs(
    monkeypatch,
    tmp_path,
) -> None:
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )
    monkeypatch.setattr(Config, "TG_ALLOWED_USER_IDS", (1001,))
    sent_report: list[str] = []
    sent_check: list[str] = []
    sent_reply: list[dict[str, object]] = []

    runtime_status_path = tmp_path / "runtime_status.json"
    runtime_status_path.write_text(
        """
        {
          "semantic_rollout_state": {
            "recent": [
              {"domain":"entry","symbol":"BTCUSD","mode":"log_only","trace_quality_state":"unavailable","fallback_reason":"baseline_no_action","reason":"mode=log_only, trace=unavailable"},
              {"domain":"entry","symbol":"BTCUSD","mode":"log_only","trace_quality_state":"unavailable","fallback_reason":"baseline_no_action","reason":"mode=log_only, trace=unavailable"},
              {"domain":"entry","symbol":"BTCUSD","mode":"log_only","trace_quality_state":"unavailable","fallback_reason":"baseline_no_action","reason":"mode=log_only, trace=unavailable"}
            ]
          },
          "pending_reverse_by_symbol": {
            "BTCUSD": {
              "action": "BUY",
              "reasons": ["opposite_score_spike","volatility_spike","plus_to_minus_protect"],
              "reason_count": 3,
              "age_sec": 12,
              "expires_in_sec": 8
            }
          }
        }
        """.strip(),
        encoding="utf-8",
    )
    readiness_surface_path = tmp_path / "improvement_readiness_surface_latest.json"
    readiness_surface_path.write_text(
        '{"reverse_surface":{"readiness_status":"BLOCKED","blocking_reason":"system_phase_degraded"}}',
        encoding="utf-8",
    )
    scene_disagreement_path = tmp_path / "checkpoint_scene_disagreement_audit_latest.json"
    scene_disagreement_path.write_text(
        """
        {
          "summary": {
            "recommended_next_action": "keep_scene_candidate_log_only_and_patch_overpull_labels_before_sa6",
            "label_pull_profiles": [
              {
                "candidate_selected_label": "trend_exhaustion",
                "row_count": 4,
                "runtime_unresolved_share": 1.0,
                "hindsight_resolved_share": 0.1,
                "expected_action_alignment_rate": 0.99,
                "watch_state": "overpull_watch",
                "top_slices": [
                  {
                    "symbol": "BTCUSD",
                    "surface_name": "continuation_hold_surface",
                    "checkpoint_type": "RUNNER_CHECK",
                    "count": 4
                  }
                ]
              }
            ]
          }
        }
        """.strip(),
        encoding="utf-8",
    )
    scene_bias_preview_path = tmp_path / "checkpoint_trend_exhaustion_scene_bias_preview_latest.json"
    scene_bias_preview_path.write_text(
        """
        {
          "summary": {
            "preview_changed_row_count": 1,
            "improved_row_count": 1,
            "worsened_row_count": 0,
            "recommended_next_action": "keep_trend_exhaustion_scene_bias_preview_only",
            "top_changed_slices": [
              {
                "symbol": "BTCUSD",
                "checkpoint_type": "RUNNER_CHECK",
                "preview_action_label": "PARTIAL_THEN_HOLD",
                "count": 1
              }
            ]
          }
        }
        """.strip(),
        encoding="utf-8",
    )

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
    monkeypatch.setattr(
        "backend.services.improvement_log_only_detector.default_runtime_status_json_path",
        lambda: runtime_status_path,
    )
    monkeypatch.setattr(
        "backend.services.improvement_log_only_detector.default_improvement_readiness_surface_json_path",
        lambda: readiness_surface_path,
    )
    monkeypatch.setattr(
        "backend.services.improvement_log_only_detector.default_scene_disagreement_json_path",
        lambda: scene_disagreement_path,
    )
    monkeypatch.setattr(
        "backend.services.improvement_log_only_detector.default_scene_bias_preview_json_path",
        lambda: scene_bias_preview_path,
    )

    result = service._handle_message_command(
        {
            "text": "/detect 50",
            "from": {"id": 1001, "username": "ops_user"},
            "chat": {"id": "chat-check"},
            "message_thread_id": 4,
        },
        trade_logger=SimpleNamespace(read_closed_df=_closed_frame),
    )

    assert result is True
    assert "[log-only detector" in sent_report[0]
    assert "[detector" in sent_check[0]
    assert "surface detector" in sent_reply[0]["message"]
    assert "D1:" in sent_reply[0]["message"]
    assert "latest_detect_issue_refs" in service.state
    assert service.state["latest_detect_issue_refs"]["items"][0]["feedback_ref"] == "D1"


def test_telegram_ops_service_records_detect_feedback_from_latest_refs(
    monkeypatch,
    tmp_path,
) -> None:
    service = TelegramOpsService(
        state_path=tmp_path / "telegram_ops_state.json",
        checkpoint_rows_path=tmp_path / "checkpoint_rows.csv",
    )
    monkeypatch.setattr(Config, "TG_ALLOWED_USER_IDS", (1001,))
    sent_check: list[str] = []
    sent_reply: list[dict[str, object]] = []

    service.state["latest_detect_issue_refs"] = {
        "generated_at": "2026-04-12T22:10:00+09:00",
        "proposal_id": "proposal-detect-1",
        "items": [
            {
                "feedback_ref": "D1",
                "feedback_key": "detfb_scene_btc_1",
                "detector_key": "scene_aware",
                "symbol": "BTCUSD",
                "summary_ko": "BTCUSD scene trace 누락 반복 감지",
            }
        ],
    }

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
            "text": "/detect_feedback D1 맞았음 메모",
            "from": {"id": 1001, "username": "ops_user"},
            "chat": {"id": "chat-check"},
            "message_thread_id": 4,
        },
        trade_logger=SimpleNamespace(read_closed_df=_closed_frame),
    )

    assert result is True
    assert "[detector 피드백]" in sent_check[0]
    assert "맞았음" in sent_check[0]
    assert "detector 피드백을 기록했습니다." in sent_reply[0]["message"]
    assert len(service.state["detect_feedback_history"]) == 1
