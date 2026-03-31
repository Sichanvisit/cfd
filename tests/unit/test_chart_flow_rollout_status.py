import json

from backend.trading.chart_flow_distribution import (
    build_chart_flow_distribution_report,
    write_chart_flow_distribution_report,
)
from backend.trading.chart_flow_rollout_status import (
    build_chart_flow_rollout_status,
    generate_and_write_chart_flow_rollout_status,
)


def _event(ts, kind, *, box_state="", bb_state="", level=0, score=0.0, reason="", my_position_count=None):
    payload = {
        "ts": int(ts),
        "event_kind": str(kind),
        "box_state": str(box_state),
        "bb_state": str(bb_state),
        "level": int(level) if level else 0,
        "score": float(score),
        "reason": str(reason or kind.lower()),
    }
    if my_position_count is not None:
        payload["my_position_count"] = my_position_count
    return payload


def test_build_chart_flow_rollout_status_advances_when_stage_gates_are_satisfied():
    history_by_symbol = {
        "XAUUSD": [
            _event(100, "BUY_WAIT", box_state="LOWER", bb_state="LOWER_EDGE", level=4, score=0.24),
            _event(110, "SELL_WAIT", box_state="UPPER", bb_state="UPPER_EDGE", level=5, score=0.28),
            _event(120, "WAIT", box_state="MIDDLE", bb_state="MID", level=2, score=0.10),
            _event(130, "BUY_PROBE", box_state="LOWER", bb_state="LOWER_EDGE", level=6, score=0.34),
        ],
        "BTCUSD": [
            _event(100, "BUY_WAIT", box_state="LOWER", bb_state="LOWER_EDGE", level=4, score=0.22),
            _event(110, "SELL_WAIT", box_state="UPPER", bb_state="UPPER_EDGE", level=5, score=0.27),
            _event(120, "WAIT", box_state="MIDDLE", bb_state="MID", level=2, score=0.09),
            _event(130, "SELL_PROBE", box_state="UPPER", bb_state="UPPER_EDGE", level=6, score=0.33),
        ],
        "NAS100": [
            _event(100, "BUY_WAIT", box_state="LOWER", bb_state="LOWER_EDGE", level=4, score=0.23),
            _event(110, "SELL_WAIT", box_state="UPPER", bb_state="UPPER_EDGE", level=5, score=0.26),
            _event(120, "WAIT", box_state="MIDDLE", bb_state="MID", level=2, score=0.10),
            _event(130, "BUY_READY", box_state="LOWER", bb_state="LOWER_EDGE", level=8, score=0.55),
        ],
    }
    override_report = build_chart_flow_distribution_report(
        history_by_symbol,
        window_mode="candles",
        window_value=16,
        baseline_mode="override_on",
    )
    baseline_report = build_chart_flow_distribution_report(
        history_by_symbol,
        window_mode="candles",
        window_value=16,
        baseline_mode="baseline_only",
    )

    status = build_chart_flow_rollout_status(
        override_report,
        baseline_distribution_report=baseline_report,
        runtime_status={"updated_at": "2026-03-25T14:30:00+09:00", "symbols": ["XAUUSD", "BTCUSD", "NAS100"]},
        runtime_status_detail={"loop": {"ok": True}},
        history_by_symbol=history_by_symbol,
    )

    assert status["contract_version"] == "chart_flow_rollout_status_v1"
    assert status["stages"]["stage_a_semantic_baseline"]["status"] == "advance"
    assert status["stages"]["stage_b_common_threshold"]["status"] == "advance"
    assert status["stages"]["stage_c_strength_rollout"]["status"] == "advance"
    assert status["stages"]["stage_d_override_restore"]["status"] == "advance"
    assert status["stages"]["stage_e_micro_calibration"]["status"] == "advance"
    assert status["comparison"]["available"] is True
    assert status["inputs"]["history_schema_summary"]["symbols_with_zone"] == 3
    assert status["inputs"]["history_schema_summary"]["symbols_with_level"] == 3
    assert status["decision"]["phase6_complete"] is True
    assert status["decision"]["recommended_action"] == "advance"


def test_build_chart_flow_rollout_status_stops_on_flat_exit_anomaly():
    history_by_symbol = {
        "BTCUSD": [
            _event(
                100,
                "EXIT_NOW",
                level=5,
                score=0.31,
                reason="adverse_loss_expand",
                my_position_count=0,
            )
        ]
    }
    report = build_chart_flow_distribution_report(
        history_by_symbol,
        window_mode="candles",
        window_value=16,
        baseline_mode="override_on",
    )

    status = build_chart_flow_rollout_status(report, history_by_symbol=history_by_symbol)

    assert status["stages"]["stage_a_semantic_baseline"]["status"] == "stop"
    assert status["decision"]["overall_status"] == "stop"
    assert status["decision"]["recommended_action"] == "stop"


def test_generate_and_write_chart_flow_rollout_status_reads_baseline_report_when_configured(tmp_path, monkeypatch):
    history_payload = {
        "XAUUSD": [
            _event(100, "BUY_WAIT", box_state="LOWER", bb_state="LOWER_EDGE", level=4, score=0.24),
            _event(110, "WAIT", box_state="MIDDLE", bb_state="MID", level=2, score=0.10),
            _event(120, "SELL_WAIT", box_state="UPPER", bb_state="UPPER_EDGE", level=5, score=0.26),
            _event(130, "BUY_READY", box_state="LOWER", bb_state="LOWER_EDGE", level=8, score=0.52),
        ]
    }
    override_report = build_chart_flow_distribution_report(
        history_payload,
        window_mode="candles",
        window_value=16,
        baseline_mode="override_on",
    )
    baseline_report = build_chart_flow_distribution_report(
        history_payload,
        window_mode="candles",
        window_value=16,
        baseline_mode="baseline_only",
    )
    override_path = tmp_path / "override_distribution.json"
    baseline_path = tmp_path / "baseline_distribution.json"
    write_chart_flow_distribution_report(override_report, output_path=override_path)
    write_chart_flow_distribution_report(baseline_report, output_path=baseline_path)

    history_dir = tmp_path / "history"
    history_dir.mkdir()
    (history_dir / "XAUUSD_flow_history.json").write_text(
        json.dumps({"version": 1, "symbol": "XAUUSD", "events": history_payload["XAUUSD"]}),
        encoding="ascii",
    )
    runtime_status_path = tmp_path / "runtime_status.json"
    runtime_status_path.write_text(
        json.dumps({"updated_at": "2026-03-25T14:31:00+09:00", "symbols": ["XAUUSD"]}),
        encoding="utf-8",
    )
    runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    runtime_status_detail_path.write_text(json.dumps({"loop": {"ok": True}}), encoding="utf-8")
    output_path = tmp_path / "chart_flow_rollout_status_latest.json"
    monkeypatch.setenv("CHART_FLOW_BASELINE_DISTRIBUTION_PATH", str(baseline_path))

    status, written = generate_and_write_chart_flow_rollout_status(
        distribution_path=override_path,
        save_dir=history_dir,
        runtime_status_path=runtime_status_path,
        runtime_status_detail_path=runtime_status_detail_path,
        output_path=output_path,
    )

    assert written == output_path.resolve()
    assert output_path.exists() is True
    assert status["inputs"]["baseline_distribution_report"]["available"] is True
    assert status["comparison"]["available"] is True
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted["contract_version"] == "chart_flow_rollout_status_v1"
    assert persisted["decision"]["decision_log_latest"]["next_stage"]


def test_build_chart_flow_rollout_status_prefers_comparison_override_report_for_stage_d():
    live_history = {
        "BTCUSD": [
            _event(100, "BUY_WAIT", box_state="LOWER", bb_state="LOWER_EDGE", level=4, score=0.22),
            _event(110, "WAIT", box_state="MIDDLE", bb_state="MID", level=2, score=0.09),
            _event(120, "SELL_WAIT", box_state="UPPER", bb_state="UPPER_EDGE", level=5, score=0.27),
        ]
    }
    comparison_history = {
        "BTCUSD": [
            _event(100, "BUY_WAIT", box_state="LOWER", bb_state="LOWER_EDGE", level=4, score=0.22),
            _event(110, "BUY_PROBE", box_state="LOWER", bb_state="LOWER_EDGE", level=6, score=0.36),
            _event(120, "WAIT", box_state="MIDDLE", bb_state="MID", level=2, score=0.09),
        ]
    }
    live_report = build_chart_flow_distribution_report(
        live_history,
        window_mode="candles",
        window_value=16,
        baseline_mode="override_on",
    )
    comparison_override_report = build_chart_flow_distribution_report(
        comparison_history,
        window_mode="candles",
        window_value=16,
        baseline_mode="comparison_override",
    )
    baseline_report = build_chart_flow_distribution_report(
        comparison_history,
        window_mode="candles",
        window_value=16,
        baseline_mode="baseline_only",
    )

    status = build_chart_flow_rollout_status(
        live_report,
        comparison_override_distribution_report=comparison_override_report,
        baseline_distribution_report=baseline_report,
        history_by_symbol=live_history,
    )

    assert status["inputs"]["comparison_override_distribution_report"]["available"] is True
    assert status["inputs"]["comparison_override_distribution_report"]["baseline_mode"] == "comparison_override"
    assert status["stages"]["stage_d_override_restore"]["status"] == "advance"
