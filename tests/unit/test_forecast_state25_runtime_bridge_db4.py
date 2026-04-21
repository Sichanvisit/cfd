from backend.services.forecast_state25_runtime_bridge import (
    build_forecast_runtime_summary_v1,
    build_forecast_state25_runtime_bridge_v1,
    build_state25_runtime_hint_v1,
    build_entry_wait_exit_bridge_v1,
)
from tests.unit.test_forecast_state25_runtime_bridge import _runtime_bridge_row


def test_db4_forecast_runtime_summary_attaches_direct_binding_fields() -> None:
    payload = build_forecast_runtime_summary_v1(_runtime_bridge_row())

    assert payload["registry_key"] == "forecast:decision_hint"
    assert payload["registry_binding_mode"] == "derived"
    assert payload["registry_binding_ready"] is True
    assert "forecast:confirm_side" in payload["target_registry_keys"]
    assert "forecast:decision_hint" in payload["target_registry_keys"]
    assert any("확정 우세 방향" in line for line in payload["registry_report_lines_ko"])
    assert any("가짜 돌파 경계 점수" in line for line in payload["registry_report_lines_ko"])


def test_db4_entry_wait_exit_bridge_and_top_level_report_use_registry_labels() -> None:
    row = _runtime_bridge_row()
    scene = build_state25_runtime_hint_v1(row)
    forecast = build_forecast_runtime_summary_v1(row)
    bridge = build_entry_wait_exit_bridge_v1(scene, forecast)

    assert bridge["registry_key"] == "forecast:prefer_entry_now"
    assert bridge["registry_binding_mode"] == "derived"
    assert bridge["registry_binding_ready"] is True
    assert set(bridge["target_registry_keys"]) == {
        "forecast:prefer_entry_now",
        "forecast:prefer_wait_now",
        "forecast:prefer_hold_if_entered",
        "forecast:prefer_fast_cut_if_entered",
    }
    assert any("지금 진입 선호" in line for line in bridge["registry_report_lines_ko"])

    runtime_bridge = build_forecast_state25_runtime_bridge_v1(row)
    assert runtime_bridge["registry_key"] == "forecast:decision_hint"
    assert runtime_bridge["registry_binding_ready"] is True
    assert len(runtime_bridge["target_registry_keys"]) == 15
    assert runtime_bridge["forecast_registry_report_lines_ko"][0] == "forecast 보조 판단:"
    assert any("확정 우세 방향" in line for line in runtime_bridge["forecast_registry_report_lines_ko"])
    assert any("지금 대기 선호" in line for line in runtime_bridge["forecast_registry_report_lines_ko"])
