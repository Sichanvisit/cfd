import json

import backend.trading.chart_flow_baseline_compare as compare_module
from backend.trading.engine.core.models import ObserveConfirmSnapshot


def _sample_runtime_row():
    return {
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "my_position_count": 0,
        "observe_confirm_input_contract_v2": "observe_confirm_input_contract_v2",
        "position_vector_v2": {},
        "position_snapshot_v2": {
            "vector": {},
            "zones": {"box_zone": "LOWER", "bb20_zone": "LOWER_EDGE", "bb44_zone": "LOWER"},
            "interpretation": {"primary_label": "LOWER_BIAS", "secondary_context_label": "LOWER_CONTEXT"},
            "energy": {},
        },
        "response_raw_snapshot_v1": {},
        "state_vector_v2": {"metadata": {"source_regime": "RANGE"}},
        "evidence_vector_v1": {},
        "belief_state_v1": {},
        "barrier_state_v1": {},
        "transition_forecast_v1": {},
        "trade_management_forecast_v1": {},
        "forecast_gap_metrics_v1": {},
    }


def _fake_observe_snapshot(*, baseline: bool):
    buy_support = 0.18 if baseline else 0.28
    sell_support = 0.06 if baseline else 0.08
    return ObserveConfirmSnapshot(
        state="OBSERVE",
        action="WAIT",
        side="BUY",
        confidence=0.22 if baseline else 0.31,
        reason="lower_rebound_probe_observe",
        metadata={
            "edge_pair_law_v1": {
                "contract_version": "edge_pair_law_v1",
                "context_label": "LOWER_REBOUND",
                "candidate_buy": buy_support,
                "candidate_sell": sell_support,
                "pair_gap": 0.12 if baseline else 0.18,
                "winner_side": "BUY",
                "winner_archetype": "LOWER_REBOUND",
                "winner_clear": True,
                "active_branch_side": "BUY",
                "active_branch_archetype": "LOWER_REBOUND",
                "opposing_branch_side": "SELL",
                "opposing_branch_archetype": "UPPER_REJECT",
            },
            "semantic_readiness_bridge_v1": {
                "contract_version": "semantic_readiness_bridge_v1",
                "source": "unit_test",
                "legacy_energy_snapshot_dependency": False,
                "base": {},
                "components": {},
                "final": {
                    "buy_support": buy_support,
                    "sell_support": sell_support,
                },
            },
            "symbol_probe_temperament_v1": {
                "scene_id": "btc_lower_buy_conservative_probe",
            },
            "blocked_guard": "",
            "blocked_reason": "",
        },
    )


def _patch_route(monkeypatch):
    def _fake_route(*args, **kwargs):
        _ = args, kwargs
        policy = getattr(compare_module.observe_confirm_router, "_SYMBOL_OVERRIDE_POLICY_V1", {})
        disabled = (
            (((policy.get("symbols") or {}).get("BTCUSD") or {}).get("router") or {})
            .get("probe", {})
            .get("lower_rebound", {})
            .get("enabled", True)
            is False
        )
        return _fake_observe_snapshot(baseline=disabled)

    monkeypatch.setattr(compare_module.observe_confirm_router, "route_observe_confirm", _fake_route)


def test_generate_and_write_chart_flow_baseline_compare_reports_writes_compare_outputs(tmp_path, monkeypatch):
    _patch_route(monkeypatch)
    monkeypatch.setenv("CHART_FLOW_BASELINE_COMPARE_MODE", "ALWAYS")
    monkeypatch.setenv("CHART_FLOW_COMPARE_OVERRIDE_DISTRIBUTION_PATH", str(tmp_path / "compare_override.json"))
    monkeypatch.setenv("CHART_FLOW_BASELINE_DISTRIBUTION_PATH", str(tmp_path / "baseline_only.json"))
    monkeypatch.setenv("CHART_FLOW_COMPARE_OVERRIDE_HISTORY_PATH", str(tmp_path / "compare_override_history.json"))
    monkeypatch.setenv("CHART_FLOW_COMPARE_BASELINE_HISTORY_PATH", str(tmp_path / "baseline_history.json"))
    monkeypatch.setenv("CHART_FLOW_BASELINE_COMPARE_STATE_PATH", str(tmp_path / "compare_state.json"))

    runtime_status_detail = {
        "latest_signal_by_symbol": {
            "BTCUSD": _sample_runtime_row(),
        }
    }

    result = compare_module.generate_and_write_chart_flow_baseline_compare_reports(
        runtime_status_detail=runtime_status_detail,
        now_ts=1_000,
        window_value=16,
    )

    assert result["ran"] is True
    assert result["compare_override_report"]["baseline_mode"] == "comparison_override"
    assert result["baseline_report"]["baseline_mode"] == "baseline_only"
    assert result["compare_override_distribution_path"].exists() is True
    assert result["baseline_distribution_path"].exists() is True
    persisted_state = json.loads(result["state_path"].read_text(encoding="utf-8"))
    assert persisted_state["last_run_ts"] == 1_000


def test_generate_and_write_chart_flow_baseline_compare_reports_respects_sampled_interval(tmp_path, monkeypatch):
    _patch_route(monkeypatch)
    monkeypatch.setenv("CHART_FLOW_BASELINE_COMPARE_MODE", "SAMPLED")
    monkeypatch.setenv("CHART_FLOW_BASELINE_COMPARE_INTERVAL_MINUTES", "15")
    monkeypatch.setenv("CHART_FLOW_COMPARE_OVERRIDE_DISTRIBUTION_PATH", str(tmp_path / "compare_override.json"))
    monkeypatch.setenv("CHART_FLOW_BASELINE_DISTRIBUTION_PATH", str(tmp_path / "baseline_only.json"))
    monkeypatch.setenv("CHART_FLOW_COMPARE_OVERRIDE_HISTORY_PATH", str(tmp_path / "compare_override_history.json"))
    monkeypatch.setenv("CHART_FLOW_COMPARE_BASELINE_HISTORY_PATH", str(tmp_path / "baseline_history.json"))
    monkeypatch.setenv("CHART_FLOW_BASELINE_COMPARE_STATE_PATH", str(tmp_path / "compare_state.json"))

    runtime_status_detail = {
        "latest_signal_by_symbol": {
            "BTCUSD": _sample_runtime_row(),
        }
    }

    first = compare_module.generate_and_write_chart_flow_baseline_compare_reports(
        runtime_status_detail=runtime_status_detail,
        now_ts=1_000,
        window_value=16,
    )
    second = compare_module.generate_and_write_chart_flow_baseline_compare_reports(
        runtime_status_detail=runtime_status_detail,
        now_ts=1_060,
        window_value=16,
    )

    assert first["ran"] is True
    assert second["ran"] is False
    assert second["reason"] == "interval_not_due"
    assert second["compare_override_report"]["baseline_mode"] == "comparison_override"


def test_generate_and_write_chart_flow_baseline_compare_reports_skips_when_mode_off(tmp_path, monkeypatch):
    _patch_route(monkeypatch)
    monkeypatch.setenv("CHART_FLOW_BASELINE_COMPARE_MODE", "OFF")
    monkeypatch.setenv("CHART_FLOW_COMPARE_OVERRIDE_DISTRIBUTION_PATH", str(tmp_path / "compare_override.json"))
    monkeypatch.setenv("CHART_FLOW_BASELINE_DISTRIBUTION_PATH", str(tmp_path / "baseline_only.json"))
    monkeypatch.setenv("CHART_FLOW_BASELINE_COMPARE_STATE_PATH", str(tmp_path / "compare_state.json"))

    result = compare_module.generate_and_write_chart_flow_baseline_compare_reports(
        runtime_status_detail={"latest_signal_by_symbol": {"BTCUSD": _sample_runtime_row()}},
        now_ts=1_000,
    )

    assert result["active"] is False
    assert result["ran"] is False
    assert result["reason"] == "mode_off"
    assert result["compare_override_distribution_path"].exists() is False
    assert result["baseline_distribution_path"].exists() is False
