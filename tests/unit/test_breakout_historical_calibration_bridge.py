import json
from pathlib import Path

import pandas as pd

from backend.services.breakout_historical_calibration_bridge import (
    build_breakout_historical_calibration_bridge,
)


def _write_replay_dataset(path: Path) -> None:
    rows = [
        {
            "row_type": "replay_dataset_row_v1",
            "decision_row": {
                "time": "2026-04-03T15:19:58",
                "symbol": "NAS100",
                "action": "BUY",
                "micro_breakout_readiness_state": "",
                "micro_swing_high_retest_count_20": 1,
                "response_vector_v2": json.dumps(
                    {
                        "upper_break_up": 0.44,
                        "lower_break_down": 0.03,
                        "mid_reclaim_up": 0.18,
                        "mid_lose_down": 0.02,
                    },
                    ensure_ascii=False,
                ),
                "transition_forecast_v1": json.dumps(
                    {
                        "p_buy_confirm": 0.26,
                        "p_sell_confirm": 0.03,
                        "p_false_break": 0.18,
                        "p_continuation_success": 0.31,
                        "metadata": {"dominant_side": "BUY"},
                    },
                    ensure_ascii=False,
                ),
                "trade_management_forecast_v1": json.dumps(
                    {
                        "p_continue_favor": 0.28,
                        "p_fail_now": 0.12,
                        "metadata": {"continue_fail_gap": 0.16},
                    },
                    ensure_ascii=False,
                ),
                "forecast_gap_metrics_v1": json.dumps(
                    {
                        "wait_confirm_gap": 0.01,
                        "hold_exit_gap": 0.02,
                    },
                    ensure_ascii=False,
                ),
                "belief_state_v1": json.dumps(
                    {
                        "dominant_side": "BUY",
                        "dominant_mode": "continuation",
                        "buy_belief": 0.3,
                        "buy_persistence": 0.4,
                        "sell_belief": 0.1,
                        "sell_persistence": 0.1,
                        "belief_spread": 0.2,
                        "flip_readiness": 0.12,
                        "belief_instability": 0.2,
                        "transition_age": 1,
                    },
                    ensure_ascii=False,
                ),
                "barrier_state_v1": json.dumps(
                    {
                        "buy_barrier": 0.22,
                        "sell_barrier": 0.18,
                        "conflict_barrier": 0.0,
                        "middle_chop_barrier": 0.12,
                        "direction_policy_barrier": 0.0,
                        "liquidity_barrier": 0.09,
                    },
                    ensure_ascii=False,
                ),
                "entry_decision_result_v1": json.dumps(
                    {
                        "selected_setup": {"setup_id": "breakout_buy", "side": "BUY"},
                    },
                    ensure_ascii=False,
                ),
            },
        },
        {
            "row_type": "replay_dataset_row_v1",
            "decision_row": {
                "time": "2026-04-03T15:29:58",
                "symbol": "NAS100",
                "action": "BUY",
                "micro_breakout_readiness_state": "",
                "micro_swing_high_retest_count_20": 1,
                "response_vector_v2": json.dumps(
                    {
                        "upper_break_up": 0.40,
                        "lower_break_down": 0.03,
                        "mid_reclaim_up": 0.15,
                        "mid_lose_down": 0.02,
                    },
                    ensure_ascii=False,
                ),
                "transition_forecast_v1": json.dumps(
                    {
                        "p_buy_confirm": 0.20,
                        "p_sell_confirm": 0.22,
                        "p_false_break": 0.19,
                        "p_continuation_success": 0.30,
                        "metadata": {"dominant_side": "SELL"},
                    },
                    ensure_ascii=False,
                ),
                "trade_management_forecast_v1": json.dumps(
                    {
                        "p_continue_favor": 0.24,
                        "p_fail_now": 0.15,
                        "metadata": {"continue_fail_gap": 0.09},
                    },
                    ensure_ascii=False,
                ),
                "forecast_gap_metrics_v1": json.dumps(
                    {
                        "wait_confirm_gap": -0.01,
                        "hold_exit_gap": 0.01,
                    },
                    ensure_ascii=False,
                ),
                "belief_state_v1": json.dumps(
                    {
                        "dominant_side": "BUY",
                        "dominant_mode": "continuation",
                        "buy_belief": 0.25,
                        "buy_persistence": 0.34,
                        "sell_belief": 0.12,
                        "sell_persistence": 0.12,
                        "belief_spread": 0.13,
                        "flip_readiness": 0.1,
                        "belief_instability": 0.24,
                        "transition_age": 1,
                    },
                    ensure_ascii=False,
                ),
                "barrier_state_v1": json.dumps(
                    {
                        "buy_barrier": 0.20,
                        "sell_barrier": 0.19,
                        "conflict_barrier": 0.0,
                        "middle_chop_barrier": 0.11,
                        "direction_policy_barrier": 0.0,
                        "liquidity_barrier": 0.08,
                    },
                    ensure_ascii=False,
                ),
                "entry_decision_result_v1": json.dumps(
                    {
                        "selected_setup": {"setup_id": "breakout_buy", "side": "BUY"},
                    },
                    ensure_ascii=False,
                ),
            },
        },
    ]
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_breakout_historical_calibration_bridge_uses_matched_replay_rows(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay_dataset.jsonl"
    _write_replay_dataset(replay_path)

    alignment = pd.DataFrame(
        [
            {
                "episode_id": "episode_1",
                "symbol": "NAS100",
                "match_status": "matched",
                "matched_decision_time": "2026-04-03T15:19:58",
                "replay_dataset_path": str(replay_path),
                "action_target": "ENTER_NOW",
                "continuation_target": "CONTINUE_AFTER_BREAK",
                "time_gap_sec": 2.0,
            },
            {
                "episode_id": "episode_2",
                "symbol": "NAS100",
                "match_status": "matched",
                "matched_decision_time": "2026-04-03T15:29:58",
                "replay_dataset_path": str(replay_path),
                "action_target": "ENTER_NOW",
                "continuation_target": "PULLBACK_THEN_CONTINUE",
                "time_gap_sec": 1.0,
            },
        ]
    )
    alignment_path = tmp_path / "alignment.csv"
    alignment.to_csv(alignment_path, index=False, encoding="utf-8-sig")

    seed = pd.DataFrame(
        [
            {
                "episode_id": "episode_1",
                "seed_status": "promoted_canonical",
                "seed_grade": "strict",
                "promote_to_training": True,
            },
            {
                "episode_id": "episode_2",
                "seed_status": "promoted_canonical",
                "seed_grade": "strict",
                "promote_to_training": True,
            },
        ]
    )
    seed_path = tmp_path / "seed.csv"
    seed.to_csv(seed_path, index=False, encoding="utf-8-sig")

    frame, summary = build_breakout_historical_calibration_bridge(alignment_path, seed_path)

    assert len(frame) == 2
    assert summary["matched_row_count"] == 2
    assert summary["gold_seed_row_count"] == 2
    assert summary["bridge_row_count"] == 2
    assert summary["overlay_enter_now_count"] == 1
    assert summary["overlay_probe_count"] == 1
    assert "aligned_enter_now" in summary["historical_alignment_result_counts"]
    assert "demoted_but_supportive" in summary["historical_alignment_result_counts"]
    assert summary["recommended_next_action"] == "compare_historical_enter_now_with_live_candidate_bridge"
    assert set(frame["overlay_target"]) == {"ENTER_NOW", "PROBE_BREAKOUT"}
