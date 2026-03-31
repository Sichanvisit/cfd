import csv
import json
from pathlib import Path

from backend.trading.engine.offline.replay_dataset_builder import (
    _resolve_default_future_bar_path,
    build_replay_dataset_row,
    resolve_replay_dataset_row_key,
    write_replay_dataset_batch,
)


def test_resolve_replay_dataset_row_key_prefers_signal_bar_ts():
    decision_row = {
        "ticket": 7001,
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 1773149400,
        "symbol": "NAS100",
        "action": "BUY",
        "setup_id": "range_lower_reversal_buy",
    }

    row_key = resolve_replay_dataset_row_key(decision_row)

    assert row_key == (
        "replay_dataset_row_v1"
        "|symbol=NAS100"
        "|anchor_field=signal_bar_ts"
        "|anchor_value=1773149400.0"
        "|action=BUY"
        "|setup_id=range_lower_reversal_buy"
        "|ticket=7001"
    )


def test_resolve_replay_dataset_row_key_prefers_existing_explicit_key():
    decision_row = {
        "symbol": "BTCUSD",
        "time": "2026-03-21T17:32:10",
        "signal_bar_ts": 1774092600,
        "action": "",
        "setup_id": "",
        "outcome": "wait",
        "decision_row_key": (
            "replay_dataset_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1774092600.0|"
            "action=|setup_id=|ticket=0|decision_time=2026-03-21T17:32:10|observe_reason=lower_rebound_probe_observe"
        ),
    }

    assert resolve_replay_dataset_row_key(decision_row) == decision_row["decision_row_key"]


def test_build_replay_dataset_row_bundles_decision_semantic_forecast_and_labels():
    decision_row = {
        "ticket": 7001,
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 100.0,
        "signal_timeframe": "15M",
        "symbol": "NAS100",
        "action": "BUY",
        "setup_id": "range_lower_reversal_buy",
        "setup_side": "BUY",
        "position_snapshot_v2": '{"interpretation":{"primary_label":"ALIGNED_LOWER_WEAK"}}',
        "response_raw_snapshot_v1": '{"bb20_lower_hold":1.0}',
        "response_vector_v2": '{"lower_hold_up":1.0}',
        "state_raw_snapshot_v1": '{"market_mode":"RANGE"}',
        "state_vector_v2": '{"range_reversal_gain":1.18}',
        "evidence_vector_v1": '{"buy_total_evidence":0.84}',
        "belief_state_v1": '{"buy_belief":0.51}',
        "barrier_state_v1": '{"buy_barrier":0.12}',
        "observe_confirm_v1": '{"state":"LOWER_REBOUND_CONFIRM","action":"BUY"}',
        "layer_mode_policy_v1": '{"contract_version":"layer_mode_policy_v1","layer_modes":[{"layer":"Position","mode":"enforce"}],"effective_influences":[],"suppressed_reasons":[],"confidence_adjustments":[],"hard_blocks":[],"mode_decision_trace":{"trace_version":"layer_mode_mode_decision_trace_v1","layers":[]}}',
        "layer_mode_logging_replay_v1": '{"contract_version":"layer_mode_logging_replay_v1","configured_modes":[{"layer":"Position","mode":"enforce"}],"raw_result_fields":[{"layer":"Position","fields":["position_snapshot_v2"]}],"effective_result_fields":[{"layer":"Position","fields":["position_snapshot_effective_v1"]}],"applied_adjustments":[],"block_suppress_reasons":{"policy_suppressed_reasons":[],"policy_hard_blocks":[],"consumer_block_reason":"","consumer_block_kind":"","consumer_block_source_layer":""},"final_consumer_action":{"consumer_effective_action":"BUY","consumer_guard_result":"PASS"}}',
        "forecast_features_v1": '{"position_primary_label":"ALIGNED_LOWER_WEAK"}',
        "transition_forecast_v1": '{"p_buy_confirm":0.72}',
        "trade_management_forecast_v1": '{"p_continue_favor":0.61}',
        "forecast_gap_metrics_v1": '{"transition_side_separation":0.22,"management_continue_fail_gap":0.19}',
    }
    future_bars = [
        {"time": 101, "open": 100.0, "high": 101.2, "low": 99.9, "close": 101.0},
        {"time": 102, "open": 101.0, "high": 101.6, "low": 100.8, "close": 101.5},
        {"time": 103, "open": 101.5, "high": 102.0, "low": 101.2, "close": 101.8},
        {"time": 104, "open": 101.8, "high": 102.1, "low": 101.6, "close": 101.9},
    ]
    closed_rows = [
        {
            "ticket": 7001,
            "symbol": "NAS100",
            "direction": "BUY",
            "open_ts": 101,
            "open_price": 100.0,
            "close_ts": 104,
            "close_price": 101.8,
            "profit": 0.25,
            "exit_reason": "Recovery TP1",
            "status": "CLOSED",
        },
    ]

    row = build_replay_dataset_row(
        decision_row,
        future_bars=future_bars,
        closed_trade_rows=closed_rows,
    )

    assert row["row_type"] == "replay_dataset_row_v1"
    assert row["dataset_builder_contract"] == "dataset_builder_bridge_v1"
    assert row["row_key"] == resolve_replay_dataset_row_key(decision_row)
    assert row["decision_row_key"] == row["row_key"]
    assert row["runtime_snapshot_key"] == ""
    assert row["trade_link_key"] == ""
    assert row["replay_row_key"] == row["row_key"]
    assert row["transition_label_status"] == "VALID"
    assert row["management_label_status"] == "VALID"
    assert row["label_positive_count"] == 5
    assert row["label_negative_count"] == 6
    assert row["label_unknown_count"] == 0
    assert row["label_is_ambiguous"] is False
    assert row["is_censored"] is False
    assert row["label_quality_summary_v1"]["row_key"] == row["row_key"]
    assert row["label_quality_summary_v1"]["transition"]["positive_count"] == 2
    assert row["row_identity"]["anchor_time_field"] == "signal_bar_ts"
    assert row["row_identity"]["ticket"] == 7001
    assert row["decision_row"]["transition_forecast_v1"] == '{"p_buy_confirm":0.72}'
    assert row["semantic_snapshots"]["position_snapshot_v2"]["interpretation"]["primary_label"] == "ALIGNED_LOWER_WEAK"
    assert row["semantic_snapshots"]["observe_confirm_v1"]["state"] == "LOWER_REBOUND_CONFIRM"
    assert row["semantic_snapshots"]["layer_mode_policy_v1"]["layer_modes"][0]["mode"] == "enforce"
    assert row["semantic_snapshots"]["layer_mode_logging_replay_v1"]["final_consumer_action"]["consumer_effective_action"] == "BUY"
    assert row["forecast_snapshots"]["transition_forecast_v1"]["p_buy_confirm"] == 0.72
    assert row["forecast_snapshots"]["forecast_gap_metrics_v1"]["transition_side_separation"] == 0.22
    assert row["forecast_branch_evaluation_v1"]["contract_version"] == "forecast_branch_evaluation_v1"
    assert row["forecast_branch_evaluation_v1"]["transition_forecast_vs_outcome"]["evaluations"]["p_buy_confirm"]["hit"] is True
    assert row["outcome_labels_v1"]["transition"]["label_status"] == "VALID"
    assert row["outcome_labels_v1"]["trade_management"]["label_status"] == "VALID"


def test_write_replay_dataset_batch_writes_jsonl_and_validation_report(tmp_path):
    entry_path = tmp_path / "entry_decisions.csv"
    entry_path.write_text(
        "ticket,time,signal_bar_ts,signal_timeframe,symbol,action,outcome,setup_id,setup_side,position_snapshot_v2,response_raw_snapshot_v1,response_vector_v2,state_raw_snapshot_v1,state_vector_v2,evidence_vector_v1,belief_state_v1,barrier_state_v1,observe_confirm_v1,forecast_features_v1,transition_forecast_v1,trade_management_forecast_v1,forecast_gap_metrics_v1\n"
        '7001,2026-03-10T19:00:00,100,15M,NAS100,BUY,entered,range_lower_reversal_buy,BUY,"{""interpretation"":{""primary_label"":""ALIGNED_LOWER_WEAK""}}","{""bb20_lower_hold"":1.0}","{""lower_hold_up"":1.0}","{""market_mode"":""RANGE""}","{""range_reversal_gain"":1.18}","{""buy_total_evidence"":0.84}","{""buy_belief"":0.51}","{""buy_barrier"":0.12}","{""state"":""LOWER_REBOUND_CONFIRM"",""action"":""BUY""}","{""position_primary_label"":""ALIGNED_LOWER_WEAK""}","{""p_buy_confirm"":0.72}","{""p_continue_favor"":0.61}","{""transition_side_separation"":0.22}"\n',
        encoding="utf-8",
    )
    closed_path = tmp_path / "trade_closed_history.csv"
    closed_path.write_text(
        "ticket,symbol,direction,open_ts,open_price,close_ts,close_price,profit,exit_reason,status\n"
        "7001,NAS100,BUY,101,100.0,104,101.8,0.25,Recovery TP1,CLOSED\n",
        encoding="utf-8",
    )
    future_path = tmp_path / "future_bars.csv"
    future_path.write_text(
        "symbol,time,open,high,low,close\n"
        "NAS100,101,100.0,101.2,99.9,101.0\n"
        "NAS100,102,101.0,101.6,100.8,101.5\n"
        "NAS100,103,101.5,102.0,101.2,101.8\n"
        "NAS100,104,101.8,102.1,101.6,101.9\n",
        encoding="utf-8",
    )

    summary = write_replay_dataset_batch(
        entry_decision_path=entry_path,
        closed_trade_path=closed_path,
        future_bar_path=future_path,
        output_dir=tmp_path / "replay",
        analysis_dir=tmp_path / "analysis",
        entered_only=True,
    )

    dataset_path = tmp_path / "replay" / Path(summary["dataset_path"]).name
    report_path = Path(summary["validation_report_path"])
    manifest_path = Path(summary["label_quality_manifest_path"])
    key_manifest_path = Path(summary["key_integrity_manifest_path"])
    build_manifest_path = Path(summary["replay_build_manifest_path"])

    assert summary["rows_written"] == 1
    assert dataset_path.exists()
    assert report_path.exists()
    assert manifest_path.exists()
    assert key_manifest_path.exists()
    assert build_manifest_path.exists()
    lines = dataset_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["row_type"] == "replay_dataset_row_v1"
    assert row["forecast_branch_evaluation_v1"]["contract_version"] == "forecast_branch_evaluation_v1"
    assert row["outcome_labels_v1"]["transition"]["label_status"] == "VALID"
    assert row["label_quality_summary_v1"]["management"]["positive_labels"] == [
        "continue_favor_label",
        "reach_tp1_label",
        "opposite_edge_reach_label",
    ]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["report_type"] == "outcome_label_validation_report_v1"
    assert report["transition"]["rows_total"] == 1
    assert report["forecast_branch_performance_v1"]["transition_forecast_vs_outcome"]["p_buy_confirm"]["hit_count"] == 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["manifest_type"] == "replay_label_quality_manifest_v1"
    assert manifest["rows_total"] == 1
    assert manifest["transition_status_counts"] == {"VALID": 1}
    assert manifest["management_status_counts"] == {"VALID": 1}
    key_manifest = json.loads(key_manifest_path.read_text(encoding="utf-8"))
    assert key_manifest["manifest_type"] == "replay_dataset_key_integrity_manifest_v1"
    assert key_manifest["rows_total"] == 1
    assert key_manifest["missing_key_rows"]["decision_row_key"] == 0
    build_manifest = json.loads(build_manifest_path.read_text(encoding="utf-8"))
    assert build_manifest["manifest_type"] == "replay_dataset_build_manifest_v1"
    assert build_manifest["export_kind"] == "replay_intermediate"
    assert "forecast_features_v1" in build_manifest["selected_forecast_snapshot_fields"]
    assert build_manifest["missing_forecast_snapshot_fields"] == []
    assert build_manifest["key_integrity_manifest_path"] == str(key_manifest_path)


def test_write_replay_dataset_batch_merges_detail_sidecar_when_hot_csv_is_slim(tmp_path):
    entry_path = tmp_path / "entry_decisions.csv"
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    hot_row = {
        "ticket": 7001,
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 100,
        "signal_timeframe": "15M",
        "symbol": "NAS100",
        "action": "BUY",
        "outcome": "entered",
        "setup_id": "range_lower_reversal_buy",
        "setup_side": "BUY",
        "position_snapshot_v2": '{"interpretation":{"primary_label":"ALIGNED_LOWER_WEAK"}}',
        "response_vector_v2": '{"lower_hold_up":1.0}',
        "state_vector_v2": '{"range_reversal_gain":1.18}',
        "evidence_vector_v1": '{"buy_total_evidence":0.84}',
        "belief_state_v1": '{"buy_belief":0.51}',
        "barrier_state_v1": '{"buy_barrier":0.12}',
        "observe_confirm_v1": '{"state":"LOWER_REBOUND_CONFIRM","action":"BUY"}',
        "transition_forecast_v1": '{"p_buy_confirm":0.72,"metadata":{"mapper_version":"transition_forecast_v1_fc10"}}',
        "trade_management_forecast_v1": '{"p_continue_favor":0.61,"metadata":{"mapper_version":"trade_management_forecast_v1_fc5"}}',
        "forecast_gap_metrics_v1": '{"transition_side_separation":0.22}',
        "detail_schema_version": "entry_decision_detail_v1",
    }
    hot_row["detail_row_key"] = resolve_replay_dataset_row_key(hot_row)
    with entry_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(hot_row.keys()))
        writer.writeheader()
        writer.writerow(hot_row)
    detail_payload = {
        "ticket": 7001,
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 100,
        "signal_timeframe": "15M",
        "symbol": "NAS100",
        "action": "BUY",
        "outcome": "entered",
        "setup_id": "range_lower_reversal_buy",
        "setup_side": "BUY",
        "position_snapshot_v2": '{"interpretation":{"primary_label":"ALIGNED_LOWER_WEAK"}}',
        "response_raw_snapshot_v1": '{"bb20_lower_hold":1.0}',
        "response_vector_v2": '{"lower_hold_up":1.0}',
        "state_raw_snapshot_v1": '{"market_mode":"RANGE"}',
        "state_vector_v2": '{"range_reversal_gain":1.18}',
        "evidence_vector_v1": '{"buy_total_evidence":0.84}',
        "belief_state_v1": '{"buy_belief":0.51}',
        "barrier_state_v1": '{"buy_barrier":0.12}',
        "observe_confirm_v1": '{"state":"LOWER_REBOUND_CONFIRM","action":"BUY"}',
        "layer_mode_policy_v1": '{"contract_version":"layer_mode_policy_v1","layer_modes":[{"layer":"Position","mode":"enforce"}]}',
        "layer_mode_logging_replay_v1": '{"contract_version":"layer_mode_logging_replay_v1","final_consumer_action":{"consumer_effective_action":"BUY"}}',
        "forecast_features_v1": '{"position_primary_label":"ALIGNED_LOWER_WEAK"}',
        "transition_forecast_v1": '{"p_buy_confirm":0.72}',
        "trade_management_forecast_v1": '{"p_continue_favor":0.61}',
        "forecast_gap_metrics_v1": '{"transition_side_separation":0.22}',
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "entry_decision_detail_v1",
                "row_key": hot_row["detail_row_key"],
                "payload": detail_payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    closed_path = tmp_path / "trade_closed_history.csv"
    closed_path.write_text(
        "ticket,symbol,direction,open_ts,open_price,close_ts,close_price,profit,exit_reason,status\n"
        "7001,NAS100,BUY,101,100.0,104,101.8,0.25,Recovery TP1,CLOSED\n",
        encoding="utf-8",
    )
    future_path = tmp_path / "future_bars.csv"
    future_path.write_text(
        "symbol,time,open,high,low,close\n"
        "NAS100,101,100.0,101.2,99.9,101.0\n"
        "NAS100,102,101.0,101.6,100.8,101.5\n"
        "NAS100,103,101.5,102.0,101.2,101.8\n"
        "NAS100,104,101.8,102.1,101.6,101.9\n",
        encoding="utf-8",
    )

    summary = write_replay_dataset_batch(
        entry_decision_path=entry_path,
        closed_trade_path=closed_path,
        future_bar_path=future_path,
        output_dir=tmp_path / "replay",
        analysis_dir=tmp_path / "analysis",
        entered_only=True,
    )

    dataset_path = tmp_path / "replay" / Path(summary["dataset_path"]).name
    row = json.loads(dataset_path.read_text(encoding="utf-8").strip())
    assert row["semantic_snapshots"]["response_raw_snapshot_v1"]["bb20_lower_hold"] == 1.0
    assert row["semantic_snapshots"]["layer_mode_policy_v1"]["contract_version"] == "layer_mode_policy_v1"
    assert row["semantic_snapshots"]["layer_mode_logging_replay_v1"]["final_consumer_action"]["consumer_effective_action"] == "BUY"


def test_write_replay_dataset_batch_uses_decision_row_key_fallback_for_detail_sidecar_join(tmp_path):
    entry_path = tmp_path / "entry_decisions.csv"
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    hot_row = {
        "ticket": 7001,
        "time": "2026-03-10T19:00:00",
        "signal_bar_ts": 100,
        "signal_timeframe": "15M",
        "symbol": "NAS100",
        "action": "BUY",
        "outcome": "entered",
        "setup_id": "range_lower_reversal_buy",
        "setup_side": "BUY",
        "decision_row_key": "decision-row-key-v1",
        "replay_row_key": "replay-row-key-v1",
        "position_snapshot_v2": '{"interpretation":{"primary_label":"ALIGNED_LOWER_WEAK"}}',
        "response_vector_v2": '{"lower_hold_up":1.0}',
        "state_vector_v2": '{"range_reversal_gain":1.18}',
        "evidence_vector_v1": '{"buy_total_evidence":0.84}',
        "belief_state_v1": '{"buy_belief":0.51}',
        "barrier_state_v1": '{"buy_barrier":0.12}',
        "observe_confirm_v1": '{"state":"LOWER_REBOUND_CONFIRM","action":"BUY"}',
        "transition_forecast_v1": '{"p_buy_confirm":0.72}',
        "trade_management_forecast_v1": '{"p_continue_favor":0.61}',
        "forecast_gap_metrics_v1": '{"transition_side_separation":0.22}',
        "detail_schema_version": "entry_decision_detail_v1",
    }
    with entry_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(hot_row.keys()))
        writer.writeheader()
        writer.writerow(hot_row)
    detail_payload = {
        "response_raw_snapshot_v1": '{"bb20_lower_hold":1.0}',
        "layer_mode_policy_v1": '{"contract_version":"layer_mode_policy_v1","layer_modes":[{"layer":"Position","mode":"enforce"}]}',
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "entry_decision_detail_v1",
                "row_key": "decision-row-key-v1",
                "payload": detail_payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    closed_path = tmp_path / "trade_closed_history.csv"
    closed_path.write_text(
        "ticket,symbol,direction,open_ts,open_price,close_ts,close_price,profit,exit_reason,status\n"
        "7001,NAS100,BUY,101,100.0,104,101.8,0.25,Recovery TP1,CLOSED\n",
        encoding="utf-8",
    )
    future_path = tmp_path / "future_bars.csv"
    future_path.write_text(
        "symbol,time,open,high,low,close\n"
        "NAS100,101,100.0,101.2,99.9,101.0\n"
        "NAS100,102,101.0,101.6,100.8,101.5\n"
        "NAS100,103,101.5,102.0,101.2,101.8\n"
        "NAS100,104,101.8,102.1,101.6,101.9\n",
        encoding="utf-8",
    )

    summary = write_replay_dataset_batch(
        entry_decision_path=entry_path,
        closed_trade_path=closed_path,
        future_bar_path=future_path,
        output_dir=tmp_path / "replay",
        analysis_dir=tmp_path / "analysis",
        entered_only=True,
        emit_validation_report=False,
    )

    dataset_path = tmp_path / "replay" / Path(summary["dataset_path"]).name
    row = json.loads(dataset_path.read_text(encoding="utf-8").strip())
    assert row["semantic_snapshots"]["response_raw_snapshot_v1"]["bb20_lower_hold"] == 1.0
    assert row["decision_row"]["detail_row_key"] == "decision-row-key-v1"


def test_resolve_default_future_bar_path_matches_entry_companion(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    market_bars_dir = project_root / "data" / "market_bars"
    market_bars_dir.mkdir(parents=True, exist_ok=True)
    entry_path = project_root / "data" / "trades" / "entry_decisions.tail_3000.csv"
    entry_path.parent.mkdir(parents=True, exist_ok=True)
    entry_path.write_text("time,symbol\n", encoding="utf-8")
    expected = market_bars_dir / "future_bars_tail_3000_m15.csv"
    expected.write_text("symbol,time,open,high,low,close\n", encoding="utf-8")
    monkeypatch.setattr(
        "backend.trading.engine.offline.replay_dataset_builder._project_root",
        lambda: project_root,
    )

    resolved = _resolve_default_future_bar_path(entry_path)

    assert resolved == expected.resolve()


def test_write_replay_dataset_batch_auto_resolves_future_bar_companion(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    trades_dir = project_root / "data" / "trades"
    market_bars_dir = project_root / "data" / "market_bars"
    trades_dir.mkdir(parents=True, exist_ok=True)
    market_bars_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.trading.engine.offline.replay_dataset_builder._project_root",
        lambda: project_root,
    )

    entry_path = trades_dir / "entry_decisions.tail_3000.csv"
    entry_path.write_text(
        "ticket,time,signal_bar_ts,signal_timeframe,symbol,action,outcome,setup_id,setup_side,position_snapshot_v2,response_raw_snapshot_v1,response_vector_v2,state_raw_snapshot_v1,state_vector_v2,evidence_vector_v1,belief_state_v1,barrier_state_v1,observe_confirm_v1,forecast_features_v1,transition_forecast_v1,trade_management_forecast_v1,forecast_gap_metrics_v1\n"
        '7001,2026-03-10T19:00:00,100,15M,NAS100,BUY,entered,range_lower_reversal_buy,BUY,"{""interpretation"":{""primary_label"":""ALIGNED_LOWER_WEAK""}}","{""bb20_lower_hold"":1.0}","{""lower_hold_up"":1.0}","{""market_mode"":""RANGE""}","{""range_reversal_gain"":1.18}","{""buy_total_evidence"":0.84}","{""buy_belief"":0.51}","{""buy_barrier"":0.12}","{""state"":""LOWER_REBOUND_CONFIRM"",""action"":""BUY""}","{""position_primary_label"":""ALIGNED_LOWER_WEAK""}","{""p_buy_confirm"":0.72}","{""p_continue_favor"":0.61}","{""transition_side_separation"":0.22}"\n',
        encoding="utf-8",
    )
    closed_path = trades_dir / "trade_closed_history.csv"
    closed_path.write_text(
        "ticket,symbol,direction,open_ts,open_price,close_ts,close_price,profit,exit_reason,status\n"
        "7001,NAS100,BUY,101,100.0,104,101.8,0.25,Recovery TP1,CLOSED\n",
        encoding="utf-8",
    )
    expected_future_path = market_bars_dir / "future_bars_tail_3000_m15.csv"
    expected_future_path.write_text(
        "symbol,time,open,high,low,close\n"
        "NAS100,101,100.0,101.2,99.9,101.0\n"
        "NAS100,102,101.0,101.6,100.8,101.5\n"
        "NAS100,103,101.5,102.0,101.2,101.8\n"
        "NAS100,104,101.8,102.1,101.6,101.9\n",
        encoding="utf-8",
    )

    summary = write_replay_dataset_batch(
        entry_decision_path=entry_path,
        closed_trade_path=closed_path,
        output_dir=project_root / "data" / "datasets" / "replay_intermediate",
        analysis_dir=project_root / "data" / "analysis",
        entered_only=True,
        emit_validation_report=False,
    )

    assert Path(summary["future_bar_path"]) == expected_future_path.resolve()
    assert summary["future_bar_resolution"] == "auto_companion"
    build_manifest = json.loads(Path(summary["replay_build_manifest_path"]).read_text(encoding="utf-8"))
    assert build_manifest["future_bar_resolution"] == "auto_companion"
    assert build_manifest["future_bar_path"] == str(expected_future_path.resolve())
