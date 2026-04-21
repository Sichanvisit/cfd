from pathlib import Path

import pandas as pd

from backend.services.breakout_barrier_drag_calibrator import (
    build_breakout_barrier_drag_calibrator,
)


def test_breakout_barrier_drag_calibrator_summarizes_historical_and_live_rows(tmp_path: Path) -> None:
    historical = pd.DataFrame(
        [
            {
                "episode_id": "hist_1",
                "symbol": "BTCUSD",
                "action_target": "ENTER_NOW",
                "overlay_target": "WATCH_BREAKOUT",
                "historical_alignment_result": "demoted_but_supportive",
                "conflict_level": "barrier_drag",
                "action_demotion_rule": "watch_breakout_barrier_drag",
                "barrier_total": 0.58,
                "runtime_breakout_confidence": 0.14,
                "confirm_score": 0.16,
                "continuation_score": 0.18,
            },
            {
                "episode_id": "hist_2",
                "symbol": "BTCUSD",
                "action_target": "ENTER_NOW",
                "overlay_target": "WATCH_BREAKOUT",
                "historical_alignment_result": "demoted_but_supportive",
                "conflict_level": "barrier_drag",
                "action_demotion_rule": "watch_breakout_barrier_drag",
                "barrier_total": 0.63,
                "runtime_breakout_confidence": 0.19,
                "confirm_score": 0.20,
                "continuation_score": 0.21,
            },
        ]
    )
    live = pd.DataFrame(
        [
            {
                "detail_row_key": "row-1",
                "symbol": "BTCUSD",
                "overlay_target": "WATCH_BREAKOUT",
                "conflict_level": "barrier_drag",
                "action_demotion_rule": "watch_breakout_barrier_drag",
                "barrier_total": 0.61,
                "breakout_confidence": 0.15,
                "confirm_score": 0.14,
                "continuation_score": 0.17,
            },
            {
                "detail_row_key": "row-2",
                "symbol": "NAS100",
                "overlay_target": "WATCH_BREAKOUT",
                "conflict_level": "barrier_drag",
                "action_demotion_rule": "watch_breakout_barrier_drag",
                "barrier_total": 0.89,
                "breakout_confidence": 0.15,
                "confirm_score": 0.14,
                "continuation_score": 0.17,
            },
        ]
    )

    historical_path = tmp_path / "historical.csv"
    runtime_path = tmp_path / "runtime.csv"
    historical.to_csv(historical_path, index=False, encoding="utf-8-sig")
    live.to_csv(runtime_path, index=False, encoding="utf-8-sig")

    frame, summary = build_breakout_barrier_drag_calibrator(historical_path, runtime_path)

    assert len(frame) == 4
    assert summary["historical_barrier_drag_count"] == 2
    assert summary["historical_supportive_barrier_count"] == 2
    assert summary["live_barrier_drag_count"] == 2
    assert summary["live_soft_probe_window_count"] == 1
    assert summary["recommended_next_action"] == "allow_soft_probe_for_moderate_barrier_drag"
    assert frame["soft_probe_window_hit"].astype(bool).sum() == 3
