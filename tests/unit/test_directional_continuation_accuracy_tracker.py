from datetime import datetime

import backend.services.directional_continuation_accuracy_tracker as tracker


def _row(*, symbol: str, now_ts: float, price: float, direction: str, candidate_key: str) -> dict:
    return {
        "symbol": str(symbol),
        "time": float(now_ts),
        "timestamp": datetime.fromtimestamp(float(now_ts)).astimezone().isoformat(),
        "current_close": float(price),
        "directional_continuation_overlay_enabled": True,
        "directional_continuation_overlay_direction": str(direction),
        "directional_continuation_overlay_candidate_key": str(candidate_key),
        "directional_continuation_overlay_source_kind": "semantic_baseline_no_action_cluster",
        "directional_continuation_overlay_score": 0.91,
        "consumer_check_side": "SELL" if str(direction).upper() == "UP" else "BUY",
    }


def test_directional_continuation_accuracy_tracker_resolves_primary_horizon_up_correctly(
    monkeypatch,
    tmp_path,
):
    base_ts = 1_700_000_000.0
    state_path = tmp_path / "tracker_state.json"

    monkeypatch.setattr(tracker.time, "time", lambda: base_ts)
    first = tracker.update_directional_continuation_accuracy_tracker(
        {
            "NAS100": _row(
                symbol="NAS100",
                now_ts=base_ts,
                price=100.0,
                direction="UP",
                candidate_key="candidate-nas-up",
            )
        },
        state_path=state_path,
        shadow_auto_dir=tmp_path,
    )

    assert first["summary"]["pending_observation_count"] == 3
    assert first["summary"]["resolved_observation_count"] == 0

    monkeypatch.setattr(tracker.time, "time", lambda: base_ts + (21 * 60))
    second = tracker.update_directional_continuation_accuracy_tracker(
        {
            "NAS100": _row(
                symbol="NAS100",
                now_ts=base_ts + (21 * 60),
                price=102.5,
                direction="UP",
                candidate_key="candidate-nas-up",
            )
        },
        state_path=state_path,
        shadow_auto_dir=tmp_path,
    )

    summary = second["symbol_direction_primary_summary"]["NAS100|UP"]
    assert second["summary"]["primary_horizon_bars"] == 20
    assert summary["sample_count"] == 1
    assert summary["measured_count"] == 1
    assert summary["correct_count"] == 1
    assert summary["correct_rate"] == 1.0
    assert summary["last_evaluation_state"] == "CORRECT"
    assert (tmp_path / "directional_continuation_accuracy_tracker_latest.json").exists()
    assert (tmp_path / "directional_continuation_accuracy_tracker_latest.md").exists()


def test_directional_continuation_accuracy_flat_fields_reflect_primary_summary() -> None:
    report = {
        "symbol_direction_primary_summary": {
            "BTCUSD|DOWN": {
                "sample_count": 4,
                "measured_count": 3,
                "correct_rate": 0.6667,
                "false_alarm_rate": 0.3333,
                "unresolved_rate": 0.25,
                "last_evaluation_state": "CORRECT",
                "last_candidate_key": "candidate-btc-down",
            }
        }
    }

    fields = tracker.build_directional_continuation_accuracy_flat_fields_v1(
        report,
        symbol="BTCUSD",
        direction="DOWN",
    )

    assert fields["directional_continuation_accuracy_horizon_bars"] == 20
    assert fields["directional_continuation_accuracy_sample_count"] == 4
    assert fields["directional_continuation_accuracy_measured_count"] == 3
    assert fields["directional_continuation_accuracy_correct_rate"] == 0.6667
    assert fields["directional_continuation_accuracy_false_alarm_rate"] == 0.3333
    assert fields["directional_continuation_accuracy_last_state"] == "CORRECT"
