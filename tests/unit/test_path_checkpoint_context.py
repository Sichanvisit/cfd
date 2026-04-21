import json
from pathlib import Path

import pandas as pd

from backend.services.path_checkpoint_context import (
    PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS,
    append_checkpoint_context_row,
    build_checkpoint_context,
    build_checkpoint_context_snapshot,
    build_exit_position_state,
    build_flat_position_state,
    record_checkpoint_context,
)


def test_build_checkpoint_context_for_entry_row_defaults_flat_state() -> None:
    payload = build_checkpoint_context(
        symbol="BTCUSD",
        runtime_row={
            "time": "2026-04-10T13:05:00+09:00",
            "symbol": "BTCUSD",
            "leg_id": "BTCUSD_UP_20260410T130500_L0001",
            "leg_direction": "UP",
            "checkpoint_id": "BTCUSD_UP_20260410T130500_L0001_CP001",
            "checkpoint_type": "INITIAL_PUSH",
            "checkpoint_index_in_leg": 1,
            "checkpoint_transition_reason": "leg_start_checkpoint_opened",
            "observe_action": "WAIT",
            "observe_side": "BUY",
        },
        symbol_state={"leg_row_count": 1, "rows_since_checkpoint_start": 1},
        position_state=build_flat_position_state(),
        source="entry_runtime",
    )

    row = payload["row"]
    assert row["surface_name"] == "follow_through_surface"
    assert row["position_side"] == "FLAT"
    assert row["position_size_fraction"] == 0.0
    assert row["unrealized_pnl_state"] == "FLAT"
    assert row["runtime_scene_gate_label"] == "none"
    assert row["runtime_scene_confidence_band"] == "low"
    assert row["runtime_scene_action_bias_strength"] == "none"
    assert row["runtime_scene_maturity"] == "provisional"
    assert row["runtime_scene_source"] == "schema_only"
    assert row["runtime_scene_modifier_json"] == "{}"
    assert row["runtime_scene_transition_bars"] == 0
    assert row["runtime_scene_gate_block_level"] == "none"
    assert row["runtime_scene_coarse_family"] == "UNRESOLVED"
    assert row["runtime_scene_fine_label"] == "unresolved"
    assert row["runtime_scene_transition_from"] == "unresolved"
    assert row["runtime_scene_transition_speed"] == "unknown"
    assert row["runtime_scene_family_alignment"] == "unknown"
    assert row["hindsight_scene_fine_label"] == "unresolved"
    assert row["hindsight_scene_quality_tier"] == "unresolved"
    assert row["scene_candidate_available"] is False
    assert row["scene_candidate_binding_mode"] == "disabled"
    assert row["scene_candidate_selected_label"] == "unresolved"
    assert row["scene_candidate_reason"] == "scene_candidate_bridge_unavailable"


def test_build_checkpoint_context_preserves_explicit_scene_overrides() -> None:
    payload = build_checkpoint_context(
        symbol="BTCUSD",
        runtime_row={
            "time": "2026-04-10T13:05:00+09:00",
            "symbol": "BTCUSD",
            "leg_id": "BTCUSD_UP_20260410T130500_L0001",
            "leg_direction": "UP",
            "checkpoint_id": "BTCUSD_UP_20260410T130500_L0001_CP001",
            "checkpoint_type": "INITIAL_PUSH",
            "checkpoint_index_in_leg": 1,
            "checkpoint_transition_reason": "leg_start_checkpoint_opened",
            "runtime_scene_coarse_family": "ENTRY_INITIATION",
            "runtime_scene_fine_label": "breakout",
            "runtime_scene_confidence_band": "high",
            "runtime_scene_action_bias_strength": "medium",
            "runtime_scene_maturity": "probable",
            "runtime_scene_source": "heuristic_v1",
        },
        symbol_state={"leg_row_count": 1, "rows_since_checkpoint_start": 1},
        position_state=build_flat_position_state(),
        source="entry_runtime",
    )

    row = payload["row"]
    assert row["runtime_scene_coarse_family"] == "ENTRY_INITIATION"
    assert row["runtime_scene_fine_label"] == "breakout"
    assert row["runtime_scene_confidence_band"] == "high"
    assert row["runtime_scene_action_bias_strength"] == "medium"
    assert row["runtime_scene_maturity"] == "probable"
    assert row["runtime_scene_source"] == "heuristic_v1"


def test_build_checkpoint_context_for_exit_row_marks_runner_secured_profit() -> None:
    payload = build_checkpoint_context(
        symbol="XAUUSD",
        runtime_row={
            "time": "2026-04-10T13:06:00+09:00",
            "symbol": "XAUUSD",
            "leg_id": "XAUUSD_UP_20260410T130500_L0001",
            "leg_direction": "UP",
            "checkpoint_id": "XAUUSD_UP_20260410T130500_L0001_CP004",
            "checkpoint_type": "RUNNER_CHECK",
            "checkpoint_index_in_leg": 4,
            "checkpoint_transition_reason": "checkpoint_progression::LATE_TREND_CHECK_to_RUNNER_CHECK",
            "blocked_by": "",
        },
        symbol_state={"leg_row_count": 19, "rows_since_checkpoint_start": 4},
        position_state=build_exit_position_state(
            direction="BUY",
            ticket=123,
            current_lot=0.1,
            entry_lot=0.2,
            entry_price=2312.4,
            profit=12.5,
            peak_profit=18.2,
            partial_done=True,
            be_moved=True,
        ),
        source="exit_manage",
    )

    row = payload["row"]
    assert row["surface_name"] == "continuation_hold_surface"
    assert row["position_side"] == "BUY"
    assert row["runner_secured"] is True
    assert row["unrealized_pnl_state"] == "OPEN_PROFIT"
    assert row["position_size_fraction"] == 0.5
    assert float(row["giveback_from_peak"]) > 0.0
    assert float(row["giveback_ratio"]) > 0.0
    assert row["checkpoint_rule_family_hint"] == "runner_secured_continuation"


def test_append_checkpoint_context_row_writes_csv_and_detail_jsonl(tmp_path: Path) -> None:
    csv_path = tmp_path / "checkpoint_rows.csv"
    detail_path = tmp_path / "checkpoint_rows.detail.jsonl"
    payload = build_checkpoint_context(
        symbol="NAS100",
        runtime_row={
            "time": "2026-04-10T13:07:00+09:00",
            "symbol": "NAS100",
            "leg_id": "NAS100_UP_20260410T130500_L0001",
            "leg_direction": "UP",
            "checkpoint_id": "NAS100_UP_20260410T130500_L0001_CP002",
            "checkpoint_type": "FIRST_PULLBACK_CHECK",
            "checkpoint_index_in_leg": 2,
            "checkpoint_transition_reason": "checkpoint_progression::INITIAL_PUSH_to_FIRST_PULLBACK_CHECK",
        },
        symbol_state={"leg_row_count": 3, "rows_since_checkpoint_start": 2},
        position_state=build_flat_position_state(),
        source="entry_runtime",
    )

    result = append_checkpoint_context_row(payload["row"], payload["detail"], csv_path=csv_path, detail_path=detail_path)

    assert result["appended"] is True
    frame = pd.read_csv(csv_path, encoding="utf-8-sig")
    assert len(frame) == 1
    assert frame.iloc[0]["checkpoint_type"] == "FIRST_PULLBACK_CHECK"
    for column in PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS:
        assert column in frame.columns
    detail_lines = detail_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(detail_lines) == 1
    assert json.loads(detail_lines[0])["row"]["symbol"] == "NAS100"


def test_build_checkpoint_context_snapshot_summarizes_sources_and_surfaces() -> None:
    runtime_status = {"updated_at": "2026-04-10T13:08:00+09:00"}
    frame = pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T13:05:00+09:00",
                "symbol": "BTCUSD",
                "source": "entry_runtime",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "runner_secured": False,
                "unrealized_pnl_state": "FLAT",
                "checkpoint_id": "BTC_CP001",
            },
            {
                "generated_at": "2026-04-10T13:06:00+09:00",
                "symbol": "XAUUSD",
                "source": "exit_manage",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "runner_secured": True,
                "unrealized_pnl_state": "OPEN_PROFIT",
                "checkpoint_id": "XAU_CP004",
            },
        ]
    )

    snapshot, summary = build_checkpoint_context_snapshot(runtime_status, frame, recent_limit=20)

    assert set(snapshot["symbol"]) == {"BTCUSD", "NAS100", "XAUUSD"}
    assert summary["runner_secured_count"] == 1
    assert summary["surface_counts"]["follow_through_surface"] >= 1
    assert summary["checkpoint_type_counts"]["RUNNER_CHECK"] >= 1


def test_record_checkpoint_context_updates_runtime_latest_row(tmp_path: Path) -> None:
    class _Runtime:
        def __init__(self):
            self.latest_signal_by_symbol = {"BTCUSD": {"symbol": "BTCUSD"}}

    runtime = _Runtime()
    payload = record_checkpoint_context(
        runtime=runtime,
        symbol="BTCUSD",
        runtime_row={
            "time": "2026-04-10T13:09:00+09:00",
            "symbol": "BTCUSD",
            "leg_id": "BTCUSD_UP_20260410T130900_L0001",
            "leg_direction": "UP",
            "checkpoint_id": "BTCUSD_UP_20260410T130900_L0001_CP001",
            "checkpoint_type": "INITIAL_PUSH",
            "checkpoint_index_in_leg": 1,
            "checkpoint_transition_reason": "leg_start_checkpoint_opened",
        },
        symbol_state={"leg_row_count": 1, "rows_since_checkpoint_start": 1},
        position_state=build_flat_position_state(),
        source="entry_runtime",
        csv_path=tmp_path / "checkpoint_rows.csv",
        detail_path=tmp_path / "checkpoint_rows.detail.jsonl",
        scene_bridge_active_state_path=tmp_path / "missing_active_candidate_state.json",
        scene_bridge_latest_run_path=tmp_path / "missing_latest_candidate_run.json",
    )

    assert payload["row"]["checkpoint_type"] == "INITIAL_PUSH"
    runtime_row = runtime.latest_signal_by_symbol["BTCUSD"]
    assert runtime_row["checkpoint_surface_name"] == "follow_through_surface"
    assert runtime_row["checkpoint_bars_since_last_checkpoint"] == 0
    assert float(runtime_row["checkpoint_runtime_continuation_odds"]) > 0.0
    assert runtime_row["checkpoint_runtime_scene_gate_label"] == "none"
    assert runtime_row["checkpoint_runtime_scene_confidence_band"] == "low"
    assert runtime_row["checkpoint_runtime_scene_action_bias_strength"] == "none"
    assert runtime_row["checkpoint_runtime_scene_maturity"] == "provisional"
    assert runtime_row["checkpoint_scene_candidate_available"] is False
    assert runtime_row["checkpoint_scene_candidate_binding_mode"] == "disabled"
    assert runtime_row["checkpoint_scene_candidate_selected_label"] == "unresolved"


def test_record_checkpoint_context_keeps_healthy_runner_unresolved_after_rebalance(tmp_path: Path) -> None:
    class _Runtime:
        def __init__(self):
            self.latest_signal_by_symbol = {"BTCUSD": {"symbol": "BTCUSD"}}

    runtime = _Runtime()
    payload = record_checkpoint_context(
        runtime=runtime,
        symbol="BTCUSD",
        runtime_row={
            "time": "2026-04-10T13:14:00+09:00",
            "symbol": "BTCUSD",
            "leg_id": "BTCUSD_UP_20260410T131400_L0001",
            "leg_direction": "UP",
            "checkpoint_id": "BTCUSD_UP_20260410T131400_L0001_CP009",
            "checkpoint_type": "RUNNER_CHECK",
            "checkpoint_index_in_leg": 9,
            "checkpoint_transition_reason": "checkpoint_progression::LATE_TREND_CHECK_to_RUNNER_CHECK",
            "blocked_by": "allow_long_blocked",
        },
        symbol_state={"leg_row_count": 13, "rows_since_checkpoint_start": 3},
        position_state=build_exit_position_state(
            direction="BUY",
            ticket=987,
            current_lot=0.10,
            entry_lot=0.20,
            entry_price=71234.0,
            profit=18.2,
            peak_profit=26.0,
            partial_done=True,
            be_moved=True,
        ),
        source="exit_manage_runner",
        csv_path=tmp_path / "checkpoint_rows.csv",
        detail_path=tmp_path / "checkpoint_rows.detail.jsonl",
        scene_bridge_active_state_path=tmp_path / "missing_active_candidate_state.json",
        scene_bridge_latest_run_path=tmp_path / "missing_latest_candidate_run.json",
    )

    row = payload["row"]
    assert row["runtime_scene_fine_label"] == "unresolved"
    assert row["runtime_scene_coarse_family"] == "UNRESOLVED"
    assert row["runtime_scene_family_alignment"] == "unknown"
    runtime_row = runtime.latest_signal_by_symbol["BTCUSD"]
    assert runtime_row["checkpoint_runtime_scene_fine_label"] == "unresolved"
    assert runtime_row["checkpoint_runtime_scene_source"] == "schema_only"


def test_record_checkpoint_context_can_skip_analysis_refresh_in_hot_path(tmp_path: Path) -> None:
    class _Runtime:
        def __init__(self):
            self.latest_signal_by_symbol = {"NAS100": {"symbol": "NAS100"}}

    runtime = _Runtime()
    payload = record_checkpoint_context(
        runtime=runtime,
        symbol="NAS100",
        runtime_row={
            "time": "2026-04-10T13:15:00+09:00",
            "symbol": "NAS100",
            "leg_id": "NAS100_UP_20260410T131500_L0001",
            "leg_direction": "UP",
            "checkpoint_id": "NAS100_UP_20260410T131500_L0001_CP001",
            "checkpoint_type": "INITIAL_PUSH",
            "checkpoint_index_in_leg": 1,
            "checkpoint_transition_reason": "leg_start_checkpoint_opened",
        },
        symbol_state={"leg_row_count": 1, "rows_since_checkpoint_start": 1},
        position_state=build_flat_position_state(),
        source="entry_runtime",
        csv_path=tmp_path / "checkpoint_rows.csv",
        detail_path=tmp_path / "checkpoint_rows.detail.jsonl",
        refresh_analysis=False,
    )

    assert payload["analysis_refresh"]["summary"]["trigger_state"] == "SKIP_REFRESH_DISABLED"


def test_append_checkpoint_context_row_migrates_existing_csv_schema(tmp_path: Path) -> None:
    csv_path = tmp_path / "checkpoint_rows.csv"
    detail_path = tmp_path / "checkpoint_rows.detail.jsonl"
    csv_path.write_text(
        "\n".join(
            [
                "generated_at,source,symbol,surface_name,leg_id,leg_direction,checkpoint_id,checkpoint_type,checkpoint_index_in_leg,checkpoint_transition_reason,bars_since_leg_start,bars_since_last_push,bars_since_last_checkpoint,position_side,position_size_fraction,avg_entry_price,realized_pnl_state,unrealized_pnl_state,runner_secured,mfe_since_entry,mae_since_entry,current_profit,ticket,action,outcome,blocked_by,observe_action,observe_side,decision_row_key,runtime_snapshot_key,trade_link_key",
                "2026-04-10T13:05:00+09:00,bootstrap_runtime,BTCUSD,follow_through_surface,BTC_L1,UP,BTC_L1_CP001,INITIAL_PUSH,1,leg_start_checkpoint_opened,0,0,0,FLAT,0.0,0.0,NONE,FLAT,False,0.0,0.0,0.0,0,,,forecast_guard,WAIT,BUY,,runtime_signal_row_v1|symbol=BTCUSD,",
            ]
        ),
        encoding="utf-8-sig",
    )
    payload = build_checkpoint_context(
        symbol="BTCUSD",
        runtime_row={
            "time": "2026-04-10T13:12:00+09:00",
            "symbol": "BTCUSD",
            "leg_id": "BTCUSD_UP_20260410T131200_L0001",
            "leg_direction": "UP",
            "checkpoint_id": "BTCUSD_UP_20260410T131200_L0001_CP002",
            "checkpoint_type": "RECLAIM_CHECK",
            "checkpoint_index_in_leg": 2,
            "checkpoint_transition_reason": "checkpoint_progression::INITIAL_PUSH_to_RECLAIM_CHECK",
            "observe_action": "BUY",
            "observe_side": "BUY",
        },
        symbol_state={"leg_row_count": 4, "rows_since_checkpoint_start": 1},
        position_state=build_flat_position_state(),
        source="entry_runtime",
    )

    append_checkpoint_context_row(payload["row"], payload["detail"], csv_path=csv_path, detail_path=detail_path)

    frame = pd.read_csv(csv_path, encoding="utf-8-sig")
    assert "runtime_continuation_odds" in frame.columns
    assert "runtime_score_reason" in frame.columns
    assert "giveback_from_peak" in frame.columns
    assert "checkpoint_rule_family_hint" in frame.columns
    assert "runtime_scene_coarse_family" in frame.columns
    assert "runtime_scene_maturity" in frame.columns
    assert "runtime_scene_gate_block_level" in frame.columns
    assert len(frame) == 2
