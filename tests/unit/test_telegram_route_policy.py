from pathlib import Path

from backend.services import telegram_route_policy


def _set_base_routes(monkeypatch) -> None:
    monkeypatch.setattr(telegram_route_policy.Config, "TG_CHAT_ID", "7210042241", raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_CHECK_CHAT_ID", "-1003971710112", raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_CHECK_TOPIC_ID", 4, raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_REPORT_CHAT_ID", "-1003971710112", raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_REPORT_TOPIC_ID", 2, raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_PNL_FORUM_CHAT_ID", "-1003749911122", raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_PNL_TOPIC_15M_ID", 32, raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_PNL_TOPIC_1H_ID", 30, raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_PNL_TOPIC_4H_ID", 3, raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_PNL_TOPIC_1D_ID", 5, raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_PNL_TOPIC_1W_ID", 7, raising=False)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_PNL_TOPIC_1M_ID", 9, raising=False)


def test_build_route_baseline_matches_current_three_lane_policy(monkeypatch) -> None:
    _set_base_routes(monkeypatch)

    baseline = telegram_route_policy.build_telegram_route_baseline()

    assert baseline.runtime_dm.role_ko == "실시간 실행 DM"
    assert baseline.runtime_dm.chat_id == "7210042241"
    assert baseline.runtime_dm.topic_id is None
    assert baseline.check_topic.chat_id == "-1003971710112"
    assert baseline.check_topic.topic_id == "4"
    assert baseline.report_topic.chat_id == "-1003971710112"
    assert baseline.report_topic.topic_id == "2"
    assert baseline.pnl_topics["15M"].chat_id == "-1003749911122"
    assert baseline.pnl_topics["15M"].topic_id == "32"
    assert baseline.issues == []


def test_route_baseline_flags_check_report_topic_conflict(monkeypatch) -> None:
    _set_base_routes(monkeypatch)
    monkeypatch.setattr(telegram_route_policy.Config, "TG_REPORT_TOPIC_ID", 4, raising=False)

    baseline = telegram_route_policy.build_telegram_route_baseline()

    codes = {issue.code for issue in baseline.issues}
    assert "check_report_topic_conflict" in codes


def test_resolve_route_destination_uses_central_policy(monkeypatch) -> None:
    _set_base_routes(monkeypatch)

    runtime_chat, runtime_thread = telegram_route_policy.resolve_telegram_route_destination(route="runtime")
    check_chat, check_thread = telegram_route_policy.resolve_telegram_route_destination(route="check")
    report_chat, report_thread = telegram_route_policy.resolve_telegram_route_destination(route="report")
    pnl_chat, pnl_thread = telegram_route_policy.resolve_telegram_route_destination(route="pnl", window_code="1H")

    assert runtime_chat == "7210042241"
    assert runtime_thread is None
    assert check_chat == "-1003971710112"
    assert check_thread == "4"
    assert report_chat == "-1003971710112"
    assert report_thread == "2"
    assert pnl_chat == "-1003749911122"
    assert pnl_thread == "30"


def test_write_route_baseline_snapshot_creates_json_and_markdown(tmp_path: Path, monkeypatch) -> None:
    _set_base_routes(monkeypatch)
    json_path = tmp_path / "telegram_route_baseline_latest.json"
    markdown_path = tmp_path / "telegram_route_baseline_latest.md"

    result = telegram_route_policy.write_telegram_route_baseline_snapshot(
        json_path=json_path,
        markdown_path=markdown_path,
    )

    assert result["contract_version"] == telegram_route_policy.TELEGRAM_ROUTE_POLICY_CONTRACT_VERSION
    assert json_path.exists()
    assert markdown_path.exists()
    assert "실시간 실행 DM" in markdown_path.read_text(encoding="utf-8")
