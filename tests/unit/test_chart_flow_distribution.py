import json

from backend.trading.chart_flow_distribution import (
    build_chart_flow_distribution_report,
    generate_and_write_chart_flow_distribution_report,
)


def test_build_chart_flow_distribution_report_counts_event_families_and_deviation():
    history_by_symbol = {
        "XAUUSD": [
            {"ts": 100, "event_kind": "BUY_WAIT", "box_state": "LOWER", "score": 0.20, "level": 4},
            {"ts": 110, "event_kind": "BUY_PROBE", "box_state": "LOWER_EDGE", "score": 0.32, "level": 6},
            {"ts": 120, "event_kind": "WAIT", "box_state": "MIDDLE", "score": 0.10, "level": 2},
        ],
        "BTCUSD": [
            {"ts": 100, "event_kind": "SELL_WAIT", "box_state": "UPPER", "score": 0.22, "level": 4},
            {"ts": 110, "event_kind": "SELL_READY", "box_state": "UPPER_EDGE", "score": 0.55, "level": 8},
            {"ts": 120, "event_kind": "WAIT", "box_state": "MIDDLE", "score": 0.11, "level": 2},
        ],
    }

    report = build_chart_flow_distribution_report(history_by_symbol, window_mode="candles", window_value=16)

    assert report["contract_version"] == "chart_flow_distribution_v1"
    assert report["global_summary"]["presence"]["total_events"] == 6
    assert report["symbols"]["XAUUSD"]["event_counts"]["BUY_WAIT"] == 1
    assert report["symbols"]["XAUUSD"]["event_counts"]["BUY_PROBE"] == 1
    assert report["symbols"]["BTCUSD"]["event_counts"]["SELL_READY"] == 1
    assert report["symbols"]["XAUUSD"]["presence"]["buy_presence_ratio"] == 2 / 3
    assert report["symbols"]["BTCUSD"]["presence"]["sell_presence_ratio"] == 2 / 3
    assert report["symbols"]["XAUUSD"]["deviation"]["buy_deviation"] > 0.0
    assert report["symbols"]["BTCUSD"]["deviation"]["sell_deviation"] > 0.0


def test_build_chart_flow_distribution_report_tracks_zone_and_strength_breakdown():
    history_by_symbol = {
        "NAS100": [
            {
                "ts": 100,
                "event_kind": "BUY_PROBE",
                "box_state": "MIDDLE",
                "bb_state": "MID",
                "score": 0.28,
                "level": 5,
                "blocked_by": "forecast_guard",
                "action_none_reason": "probe_not_promoted",
                "probe_scene_id": "nas_clean_confirm_probe",
            },
            {
                "ts": 110,
                "event_kind": "BUY_READY",
                "box_state": "LOWER",
                "bb_state": "LOWER_EDGE",
                "score": 0.52,
                "level": 8,
                "probe_scene_id": "nas_clean_confirm_probe",
            },
        ]
    }

    report = build_chart_flow_distribution_report(history_by_symbol, window_mode="candles", window_value=16)
    summary = report["symbols"]["NAS100"]

    assert summary["zone_counts"]["MIDDLE"]["BUY_PROBE"] == 1
    assert summary["zone_counts"]["LOWER"]["BUY_READY"] == 1
    assert summary["strength_level_counts"]["5"] == 1
    assert summary["strength_level_counts"]["8"] == 1
    assert summary["event_kind_by_strength_level"]["5"]["BUY_PROBE"] == 1
    assert summary["blocked_by_counts"]["forecast_guard"] == 1
    assert summary["action_none_reason_counts"]["probe_not_promoted"] == 1
    assert summary["probe_scene_counts"]["nas_clean_confirm_probe"] == 2


def test_build_chart_flow_distribution_report_flags_flat_exit_anomaly():
    history_by_symbol = {
        "BTCUSD": [
            {
                "ts": 100,
                "event_kind": "EXIT_NOW",
                "reason": "adverse_loss_expand",
                "my_position_count": 0,
                "score": 0.30,
                "level": 5,
            }
        ]
    }

    report = build_chart_flow_distribution_report(history_by_symbol, window_mode="candles", window_value=16)

    assert report["anomalies"]["flat_exit_count"] == 1
    assert report["anomalies"]["flat_exit_symbols"][0]["symbol"] == "BTCUSD"
    assert report["symbols"]["BTCUSD"]["flat_exit_reasons"]["adverse_loss_expand"] == 1


def test_generate_and_write_chart_flow_distribution_report_reads_history_files(tmp_path):
    save_dir = tmp_path / "history"
    save_dir.mkdir()
    (save_dir / "XAUUSD_flow_history.json").write_text(
        json.dumps(
            {
                "version": 1,
                "symbol": "XAUUSD",
                "events": [
                    {
                        "ts": 100,
                        "event_kind": "BUY_WAIT",
                        "box_state": "LOWER",
                        "score": 0.20,
                        "level": 4,
                    }
                ],
            }
        ),
        encoding="ascii",
    )
    output_path = tmp_path / "chart_flow_distribution_latest.json"

    report, written = generate_and_write_chart_flow_distribution_report(
        save_dir=save_dir,
        output_path=output_path,
        window_mode="candles",
        window_value=16,
    )

    assert written == output_path.resolve()
    assert output_path.exists() is True
    assert report["symbols"]["XAUUSD"]["event_counts"]["BUY_WAIT"] == 1
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted["symbols"]["XAUUSD"]["presence"]["buy_presence_ratio"] == 1.0
