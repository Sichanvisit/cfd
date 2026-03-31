import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "export_entry_decisions_ml.py"
spec = importlib.util.spec_from_file_location("export_entry_decisions_ml", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_export_entry_decisions_ml_writes_semantic_compact_outputs(tmp_path):
    source = tmp_path / "entry_decisions.csv"
    output = tmp_path / "ml_exports" / "forecast" / "entry_semantic.parquet"
    manifest_root = tmp_path / "manifests"

    rows = [
        {
            "time": "2026-03-18T10:00:00+09:00",
            "signal_timeframe": "M1",
            "symbol": "BTCUSD",
            "action": "BUY",
            "outcome": "entered",
            "setup_id": "range_lower_reversal_buy",
            "decision_row_key": "decision_row_v1|symbol=BTCUSD|anchor=1",
            "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1773817800|hint=BUY",
            "trade_link_key": "trade_link_v1|ticket=10|symbol=BTCUSD|direction=BUY|open_ts=1773817812",
            "replay_row_key": "decision_row_v1|symbol=BTCUSD|anchor=1",
            "observe_reason": "lower_rebound_probe_observe",
            "action_none_reason": "probe_not_promoted",
            "probe_candidate_active": 1,
            "probe_direction": "BUY",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "probe_candidate_support": 0.42,
            "probe_pair_gap": 0.19,
            "probe_plan_active": 1,
            "probe_plan_ready": 0,
            "probe_plan_reason": "probe_forecast_not_ready",
            "probe_plan_scene": "btc_lower_buy_conservative_probe",
            "probe_promotion_bias": "conservative_hold_first",
            "probe_temperament_source": "shared_symbol_temperament_map_v1",
            "probe_entry_style": "conservative_lower_probe",
            "probe_temperament_note": "btc_lower_buy_less_frequent_hold_longer",
            "edge_execution_scene_id": "btc_lower_hold_bias",
            "quick_trace_state": "PROBE_WAIT",
            "quick_trace_reason": "probe_forecast_not_ready",
            "semantic_shadow_available": 1,
            "semantic_shadow_reason": "timing=0.985, entry_quality=0.932, exit_management=0.010, trace=fallback_heavy",
            "semantic_shadow_activation_state": "active",
            "semantic_shadow_activation_reason": "available",
            "semantic_live_threshold_applied": 0,
            "semantic_live_threshold_state": "fallback_blocked",
            "semantic_live_threshold_reason": "baseline_no_action",
            "signal_age_sec": 12.5,
            "bar_age_sec": 12.5,
            "decision_latency_ms": 150,
            "order_submit_latency_ms": 40,
            "missing_feature_count": 2,
            "data_completeness_ratio": 0.8,
            "used_fallback_count": 1,
            "compatibility_mode": "hybrid",
            "detail_blob_bytes": 4096,
            "snapshot_payload_bytes": 1024,
            "row_payload_bytes": 768,
            "position_snapshot_v2": json.dumps(
                {
                    "vector": {
                        "x_box": 0.11,
                        "x_bb20": 0.22,
                        "x_bb44": 0.33,
                        "x_ma20": 0.44,
                        "x_ma60": 0.55,
                        "x_sr": 0.66,
                        "x_trendline": 0.77,
                    },
                    "interpretation": {
                        "pos_composite": 1.23,
                        "alignment_label": "aligned",
                        "bias_label": "buy_bias",
                        "conflict_kind": "none",
                    },
                    "energy": {
                        "lower_position_force": 0.81,
                        "upper_position_force": 0.19,
                        "middle_neutrality": 0.25,
                        "position_conflict_score": 0.12,
                    },
                }
            ),
            "response_vector_v2": json.dumps(
                {
                    "lower_break_down": 0.15,
                    "lower_hold_up": 0.85,
                    "mid_lose_down": 0.21,
                    "mid_reclaim_up": 0.79,
                    "upper_break_up": 0.42,
                    "upper_reject_down": 0.58,
                }
            ),
            "state_vector_v2": json.dumps(
                {
                    "alignment_gain": 0.91,
                    "breakout_continuation_gain": 0.61,
                    "trend_pullback_gain": 0.51,
                    "range_reversal_gain": 0.41,
                    "conflict_damp": 0.31,
                    "noise_damp": 0.21,
                    "liquidity_penalty": 0.11,
                    "volatility_penalty": 0.09,
                    "countertrend_penalty": 0.07,
                }
            ),
            "evidence_vector_v1": json.dumps(
                {
                    "buy_total_evidence": 0.88,
                    "buy_continuation_evidence": 0.62,
                    "buy_reversal_evidence": 0.26,
                    "sell_total_evidence": 0.12,
                    "sell_continuation_evidence": 0.07,
                    "sell_reversal_evidence": 0.05,
                }
            ),
            "forecast_features_v1": json.dumps(
                {
                    "position_primary_label": "lower_buy_zone",
                    "position_secondary_context_label": "range_reversal",
                    "position_conflict_score": 0.17,
                    "middle_neutrality": 0.29,
                    "metadata": {
                        "management_horizon_bars": 8,
                        "signal_timeframe": "M1",
                    },
                }
            ),
        },
        {
            "time": "2026-03-18T10:01:00+09:00",
            "signal_timeframe": "M1",
            "symbol": "XAUUSD",
            "action": "WAIT",
            "outcome": "wait",
            "setup_id": "",
            "position_snapshot_v2": json.dumps(
                {
                    "vector": {
                        "x_box": -0.15,
                    }
                }
            ),
        },
    ]
    pd.DataFrame(rows).to_csv(source, index=False, encoding="utf-8-sig")

    summary = module.export_entry_decisions_ml(
        source_path=source,
        output_path=output,
        batch_rows=1,
        symbols=[],
        entered_only=False,
        limit=None,
        compression="zstd",
        manifest_root=manifest_root,
        export_kind="forecast",
    )

    assert output.exists()
    exported = pq.read_table(output).to_pandas()
    assert list(exported.columns) == module.OUTPUT_COLUMNS
    assert "position_snapshot_v2" not in exported.columns
    assert "response_vector_v2" not in exported.columns
    assert "state_vector_v2" not in exported.columns
    assert "evidence_vector_v1" not in exported.columns
    assert "forecast_features_v1" not in exported.columns

    row = exported.iloc[0]
    assert row["position_x_box"] == pytest.approx(0.11)
    assert row["position_x_bb20"] == pytest.approx(0.22)
    assert row["position_pos_composite"] == pytest.approx(1.23)
    assert row["position_alignment_label"] == "aligned"
    assert row["decision_row_key"] == "decision_row_v1|symbol=BTCUSD|anchor=1"
    assert row["runtime_snapshot_key"].startswith("runtime_signal_row_v1|symbol=BTCUSD")
    assert row["trade_link_key"].startswith("trade_link_v1|ticket=10")
    assert row["replay_row_key"] == "decision_row_v1|symbol=BTCUSD|anchor=1"
    assert row["signal_age_sec"] == pytest.approx(12.5)
    assert row["bar_age_sec"] == pytest.approx(12.5)
    assert row["decision_latency_ms"] == 150
    assert row["order_submit_latency_ms"] == 40
    assert row["missing_feature_count"] == 2
    assert row["data_completeness_ratio"] == pytest.approx(0.8)
    assert row["used_fallback_count"] == 1
    assert row["compatibility_mode"] == "hybrid"
    assert row["detail_blob_bytes"] == 4096
    assert row["snapshot_payload_bytes"] == 1024
    assert row["row_payload_bytes"] == 768
    assert row["observe_reason"] == "lower_rebound_probe_observe"
    assert row["action_none_reason"] == "probe_not_promoted"
    assert row["probe_candidate_active"] == 1
    assert row["probe_scene_id"] == "btc_lower_buy_conservative_probe"
    assert row["probe_plan_reason"] == "probe_forecast_not_ready"
    assert row["quick_trace_state"] == "PROBE_WAIT"
    assert row["semantic_shadow_activation_state"] == "active"
    assert row["semantic_live_threshold_state"] == "fallback_blocked"
    assert row["response_mid_reclaim_up"] == pytest.approx(0.79)
    assert row["state_alignment_gain"] == pytest.approx(0.91)
    assert row["evidence_buy_total"] == pytest.approx(0.88)
    assert row["forecast_position_primary_label"] == "lower_buy_zone"
    assert row["forecast_management_horizon_bars"] == 8
    assert row["forecast_signal_timeframe"] == "M1"

    summary_path = Path(summary["summary_path"])
    missingness_path = Path(summary["missingness_report_path"])
    key_integrity_path = Path(summary["key_integrity_report_path"])
    assert summary_path.exists()
    assert missingness_path.exists()
    assert key_integrity_path.exists()
    assert summary["raw_nested_payload_included"] is False
    assert summary["export_kind"] == "forecast"
    assert summary["columns_written"] == len(module.OUTPUT_COLUMNS)

    manifest_files = list((manifest_root / "export").glob("entry_decisions_ml_export_forecast_*.json"))
    assert len(manifest_files) == 1
    manifest = json.loads(manifest_files[0].read_text(encoding="utf-8"))
    assert manifest["schema_version"] == module.EXPORT_SCHEMA_VERSION
    assert manifest["semantic_feature_contract_version"] == "semantic_feature_contract_v1"
    assert manifest["semantic_target_contract_version"] == "semantic_target_contract_v1"
    assert manifest["semantic_input_pack_keys"] == [
        "position_pack",
        "response_pack",
        "state_pack",
        "evidence_pack",
        "forecast_summary_pack",
    ]
    assert manifest["support_pack_keys"] == ["trace_quality_pack"]
    assert manifest["selected_columns"] == module.OUTPUT_COLUMNS
    assert "signal_bar_ts" in manifest["missing_columns"]
    assert "entry_score_raw" in manifest["missing_columns"]
    assert manifest["raw_nested_payload_included"] is False
    assert manifest["row_count"] == 2

    missingness = json.loads(missingness_path.read_text(encoding="utf-8"))
    assert missingness["report_version"] == module.MISSINGNESS_REPORT_VERSION
    assert missingness["semantic_feature_contract_version"] == "semantic_feature_contract_v1"
    assert missingness["overall"]["rows"] == 2
    assert missingness["missing_columns"] == manifest["missing_columns"]
    assert missingness["by_symbol"]["XAUUSD"]["missing_rows"]["response_mid_reclaim_up"] == 1
    assert missingness["by_setup_id"]["__missing_setup_id__"]["rows"] == 1

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_payload["missing_columns"] == manifest["missing_columns"]
    key_integrity = json.loads(key_integrity_path.read_text(encoding="utf-8"))
    assert key_integrity["report_version"] == module.KEY_INTEGRITY_REPORT_VERSION
    assert key_integrity["missing_key_rows"]["decision_row_key"] == 0
    assert key_integrity["missing_key_rows"]["runtime_snapshot_key"] == 0
    assert key_integrity["decision_replay_mismatch_rows"] == 0


def test_build_output_path_uses_export_kind_subdirectory(tmp_path):
    source = tmp_path / "entry_decisions.csv"
    output_dir = tmp_path / "ml_exports"

    built = module._build_output_path(
        source=source,
        output_dir=output_dir,
        explicit_output="",
        export_kind="replay",
    )

    assert built.parent == output_dir / "replay"
    assert built.suffix == ".parquet"


def test_export_entry_decisions_ml_derives_identity_keys_when_absent(tmp_path):
    source = tmp_path / "entry_decisions_legacy.csv"
    output = tmp_path / "ml_exports" / "replay" / "entry_semantic_replay.parquet"
    manifest_root = tmp_path / "manifests"

    rows = [
        {
            "time": "2026-03-16T18:55:45",
            "signal_timeframe": "M15",
            "signal_bar_ts": 1773665100,
            "symbol": "XAUUSD",
            "action": "BUY",
            "setup_id": "range_lower_reversal_buy",
            "outcome": "entered",
            "position_snapshot_v2": json.dumps({"vector": {"x_box": 0.25}}),
        },
        {
            "time": "2026-03-16T18:55:46",
            "signal_timeframe": "M15",
            "signal_bar_ts": 1773665100,
            "symbol": "BTCUSD",
            "action": "",
            "setup_id": "",
            "outcome": "wait",
            "position_snapshot_v2": json.dumps({"vector": {"x_box": -0.15}}),
        },
    ]
    pd.DataFrame(rows).to_csv(source, index=False, encoding="utf-8-sig")

    summary = module.export_entry_decisions_ml(
        source_path=source,
        output_path=output,
        batch_rows=50,
        symbols=[],
        entered_only=False,
        limit=None,
        compression="zstd",
        manifest_root=manifest_root,
        export_kind="replay",
    )

    exported = pq.read_table(output).to_pandas()
    assert len(exported) == 2
    first_row = exported.iloc[0]
    second_row = exported.iloc[1]

    assert first_row["decision_row_key"] == (
        "replay_dataset_row_v1|symbol=XAUUSD|anchor_field=signal_bar_ts|anchor_value=1773665100|"
        "action=BUY|setup_id=range_lower_reversal_buy|ticket=0"
    )
    assert first_row["replay_row_key"] == first_row["decision_row_key"]
    assert first_row["runtime_snapshot_key"].startswith(
        "runtime_signal_row_v1|symbol=XAUUSD|anchor_field=signal_bar_ts|anchor_value=1773665100"
    )
    assert second_row["decision_row_key"].startswith(
        "replay_dataset_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1773665100|"
        "action=|setup_id=|ticket=0"
    )
    assert "|decision_time=2026-03-16T18:55:46" in second_row["decision_row_key"]
    assert second_row["replay_row_key"] == second_row["decision_row_key"]
    assert second_row["runtime_snapshot_key"].startswith(
        "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1773665100"
    )
    assert "observe_reason" not in second_row["runtime_snapshot_key"]
    assert "blocked_by" not in second_row["runtime_snapshot_key"]
    assert summary["rows_written"] == 2
    assert summary["export_kind"] == "replay"
    assert "missing_columns" in summary
    key_integrity = json.loads(Path(summary["key_integrity_report_path"]).read_text(encoding="utf-8"))
    assert key_integrity["missing_key_rows"]["trade_link_key"] == 2
    assert key_integrity["missing_key_rows"]["decision_row_key"] == 0
    assert key_integrity["missing_key_rows"]["runtime_snapshot_key"] == 0


def test_transform_chunk_preserves_derived_keys_for_nonzero_chunk_index():
    chunk = pd.DataFrame(
        [
            {
                "time": "2026-03-10T20:52:43",
                "symbol": "BTCUSD",
                "action": "",
                "setup_id": "",
                "outcome": "skipped",
            },
            {
                "time": "2026-03-10T20:52:45",
                "symbol": "NAS100",
                "action": "",
                "setup_id": "",
                "outcome": "skipped",
            },
        ],
        index=[5000, 5001],
    )

    transformed = module._transform_chunk(chunk)

    assert len(transformed) == 2
    assert transformed.loc[0, "decision_row_key"].startswith(
        "replay_dataset_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=2026-03-10T20:52:43"
    )
    assert transformed.loc[1, "decision_row_key"].startswith(
        "replay_dataset_row_v1|symbol=NAS100|anchor_field=time|anchor_value=2026-03-10T20:52:45"
    )
    assert transformed["replay_row_key"].fillna("").astype(str).str.strip().ne("").all()
