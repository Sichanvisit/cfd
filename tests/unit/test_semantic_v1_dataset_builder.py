import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


DATASET_BUILDER_PATH = Path(__file__).resolve().parents[2] / "ml" / "semantic_v1" / "dataset_builder.py"
builder_spec = importlib.util.spec_from_file_location("semantic_v1_dataset_builder", DATASET_BUILDER_PATH)
builder_module = importlib.util.module_from_spec(builder_spec)
assert builder_spec is not None and builder_spec.loader is not None
sys.modules[builder_spec.name] = builder_module
builder_spec.loader.exec_module(builder_module)


def test_build_semantic_v1_datasets_writes_three_datasets_and_manifest(tmp_path):
    feature_dir = tmp_path / "ml_exports" / "replay"
    replay_dir = tmp_path / "replay_intermediate"
    output_dir = tmp_path / "semantic_v1"
    manifest_root = tmp_path / "manifests"
    feature_dir.mkdir(parents=True)
    replay_dir.mkdir(parents=True)

    features = pd.DataFrame(
        [
            {
                "time": "2026-03-20T09:00:00+09:00",
                "signal_bar_ts": 1773936000,
                "signal_timeframe": "M1",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "range_lower_reversal_buy",
                "setup_side": "BUY",
                "entry_stage": "aggressive",
                "preflight_regime": "range",
                "preflight_liquidity": "high",
                "decision_row_key": "rk1",
                "runtime_snapshot_key": "snap1",
                "trade_link_key": "trade1",
                "replay_row_key": "rk1",
                "position_x_box": 0.1,
                "response_mid_reclaim_up": 0.7,
                "state_alignment_gain": 0.6,
                "evidence_buy_total": 0.8,
                "forecast_position_primary_label": "lower_buy_zone",
                "signal_age_sec": 3.0,
                "bar_age_sec": 3.0,
                "decision_latency_ms": 120,
                "order_submit_latency_ms": 40,
                "missing_feature_count": 0,
                "data_completeness_ratio": 1.0,
                "used_fallback_count": 0,
                "compatibility_mode": "",
                "detail_blob_bytes": 100,
                "snapshot_payload_bytes": 80,
                "row_payload_bytes": 60,
            },
            {
                "time": "2026-03-20T09:01:00+09:00",
                "signal_bar_ts": 1773936060,
                "signal_timeframe": "M1",
                "symbol": "XAUUSD",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "range_lower_reversal_buy",
                "setup_side": "BUY",
                "entry_stage": "base",
                "preflight_regime": "range",
                "preflight_liquidity": "medium",
                "decision_row_key": "rk2",
                "runtime_snapshot_key": "snap2",
                "trade_link_key": "trade2",
                "replay_row_key": "rk2",
                "position_x_box": -0.2,
                "response_mid_reclaim_up": 0.4,
                "state_alignment_gain": 0.2,
                "evidence_buy_total": 0.3,
                "forecast_position_primary_label": "lower_buy_zone",
                "signal_age_sec": 5.0,
                "bar_age_sec": 5.0,
                "decision_latency_ms": 180,
                "order_submit_latency_ms": 55,
                "missing_feature_count": 1,
                "data_completeness_ratio": 0.95,
                "used_fallback_count": 1,
                "compatibility_mode": "hybrid",
                "detail_blob_bytes": 90,
                "snapshot_payload_bytes": 75,
                "row_payload_bytes": 58,
            },
            {
                "time": "2026-03-20T09:02:00+09:00",
                "signal_bar_ts": 1773936120,
                "signal_timeframe": "M1",
                "symbol": "NAS100",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "upper_reject_sell",
                "setup_side": "SELL",
                "entry_stage": "confirm",
                "preflight_regime": "trend",
                "preflight_liquidity": "high",
                "decision_row_key": "rk3",
                "runtime_snapshot_key": "snap3",
                "trade_link_key": "trade3",
                "replay_row_key": "rk3",
                "position_x_box": 0.5,
                "response_mid_reclaim_up": 0.1,
                "state_alignment_gain": 0.1,
                "evidence_buy_total": 0.1,
                "forecast_position_primary_label": "upper_sell_zone",
                "signal_age_sec": 8.0,
                "bar_age_sec": 8.0,
                "decision_latency_ms": 200,
                "order_submit_latency_ms": 70,
                "missing_feature_count": 0,
                "data_completeness_ratio": 0.98,
                "used_fallback_count": 0,
                "compatibility_mode": "",
                "detail_blob_bytes": 95,
                "snapshot_payload_bytes": 82,
                "row_payload_bytes": 61,
            },
            {
                "time": "2026-03-20T09:03:00+09:00",
                "signal_bar_ts": 1773936180,
                "signal_timeframe": "M1",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "range_lower_reversal_buy",
                "setup_side": "BUY",
                "entry_stage": "base",
                "preflight_regime": "range",
                "preflight_liquidity": "low",
                "decision_row_key": "rk4",
                "runtime_snapshot_key": "snap4",
                "trade_link_key": "trade4",
                "replay_row_key": "rk4",
                "position_x_box": 0.0,
                "response_mid_reclaim_up": 0.5,
                "state_alignment_gain": 0.5,
                "evidence_buy_total": 0.5,
                "forecast_position_primary_label": "middle_neutral",
                "signal_age_sec": 10.0,
                "bar_age_sec": 10.0,
                "decision_latency_ms": 210,
                "order_submit_latency_ms": 65,
                "missing_feature_count": 2,
                "data_completeness_ratio": 0.88,
                "used_fallback_count": 1,
                "compatibility_mode": "",
                "detail_blob_bytes": 99,
                "snapshot_payload_bytes": 84,
                "row_payload_bytes": 62,
            },
        ]
    )
    feature_path = feature_dir / "semantic_replay.parquet"
    features.to_parquet(feature_path, index=False)

    replay_rows = [
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "rk1",
            "decision_row_key": "rk1",
            "runtime_snapshot_key": "snap1",
            "trade_link_key": "trade1",
            "replay_row_key": "rk1",
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 3,
            "label_negative_count": 2,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "rk1",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 3,
                "label_negative_count": 2,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 2, "negative_count": 0, "unknown_count": 0},
                "management": {"positive_count": 1, "negative_count": 2, "unknown_count": 0},
            },
        },
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "rk2",
            "decision_row_key": "rk2",
            "runtime_snapshot_key": "snap2",
            "trade_link_key": "trade2",
            "replay_row_key": "rk2",
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 4,
            "label_negative_count": 3,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "rk2",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 4,
                "label_negative_count": 3,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 0, "negative_count": 2, "unknown_count": 0},
                "management": {"positive_count": 4, "negative_count": 1, "unknown_count": 0},
            },
        },
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "rk3",
            "decision_row_key": "rk3",
            "runtime_snapshot_key": "snap3",
            "trade_link_key": "trade3",
            "replay_row_key": "rk3",
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 1,
            "label_negative_count": 7,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "rk3",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 1,
                "label_negative_count": 7,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 1, "negative_count": 3, "unknown_count": 0},
                "management": {"positive_count": 0, "negative_count": 4, "unknown_count": 0},
            },
        },
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "rk4",
            "decision_row_key": "rk4",
            "runtime_snapshot_key": "snap4",
            "trade_link_key": "trade4",
            "replay_row_key": "rk4",
            "transition_label_status": "AMBIGUOUS",
            "management_label_status": "VALID",
            "label_unknown_count": 1,
            "label_positive_count": 1,
            "label_negative_count": 1,
            "label_is_ambiguous": True,
            "label_source_descriptor": "future_bars_only",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "rk4",
                "transition_label_status": "AMBIGUOUS",
                "management_label_status": "VALID",
                "label_positive_count": 1,
                "label_negative_count": 1,
                "label_unknown_count": 1,
                "label_is_ambiguous": True,
                "label_source_descriptor": "future_bars_only",
                "is_censored": False,
                "transition": {"positive_count": 1, "negative_count": 1, "unknown_count": 1},
                "management": {"positive_count": 1, "negative_count": 0, "unknown_count": 0},
            },
        },
    ]
    replay_path = replay_dir / "replay_rows.jsonl"
    replay_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in replay_rows) + "\n", encoding="utf-8")

    summary = builder_module.build_semantic_v1_datasets(
        feature_source=feature_dir,
        replay_source=replay_dir,
        output_dir=output_dir,
        manifest_root=manifest_root,
    )

    timing_path = output_dir / "timing_dataset.parquet"
    entry_path = output_dir / "entry_quality_dataset.parquet"
    exit_path = output_dir / "exit_management_dataset.parquet"
    assert timing_path.exists()
    assert entry_path.exists()
    assert exit_path.exists()
    assert Path(summary["manifest_path"]).exists()
    join_health_path = Path(summary["join_health_report_path"])
    assert join_health_path.exists()

    timing_df = pd.read_parquet(timing_path)
    entry_df = pd.read_parquet(entry_path)
    exit_df = pd.read_parquet(exit_path)

    assert len(timing_df) == 3
    assert len(entry_df) == 3
    assert len(exit_df) == 3
    assert "decision_row_key" in timing_df.columns
    assert "runtime_snapshot_key" in timing_df.columns
    assert "trade_link_key" in timing_df.columns
    assert "replay_row_key" in timing_df.columns
    assert "target_timing_now_vs_wait" in timing_df.columns
    assert "target_entry_quality" in entry_df.columns
    assert "target_exit_management" in exit_df.columns
    assert set(timing_df["time_split_bucket"].unique()) <= {"train", "validation", "test"}
    assert set(timing_df["symbol_holdout_bucket"].unique()) <= {"train", "holdout"}
    assert set(timing_df["regime_holdout_bucket"].unique()) <= {"train", "holdout"}

    timing_targets = dict(zip(timing_df["decision_row_key"], timing_df["target_timing_now_vs_wait"]))
    entry_targets = dict(zip(entry_df["decision_row_key"], entry_df["target_entry_quality"]))
    exit_targets = dict(zip(exit_df["decision_row_key"], exit_df["target_exit_management"]))
    assert timing_targets == {"rk1": 1, "rk2": 0, "rk3": 0}
    assert entry_targets == {"rk1": 1, "rk2": 1, "rk3": 0}
    assert exit_targets == {"rk1": 0, "rk2": 1, "rk3": 0}
    join_health = json.loads(join_health_path.read_text(encoding="utf-8"))
    assert join_health["report_version"] == builder_module.DATASET_JOIN_HEALTH_VERSION
    assert join_health["joined_rows"] == 4
    assert join_health["feature_only_join_keys_count"] == 0
    assert join_health["label_only_join_keys_count"] == 0
    assert join_health["joined_key_mismatch_rows"]["runtime_snapshot_key"] == 0

    timing_missingness = json.loads((timing_path.with_suffix(".parquet.missingness.json")).read_text(encoding="utf-8"))
    assert timing_missingness["report_version"] == builder_module.DATASET_MISSINGNESS_VERSION
    assert timing_missingness["overall"]["rows"] == 3
    assert "missing_columns" in timing_missingness


def test_build_semantic_v1_datasets_drops_all_missing_legacy_trace_features_and_records_them(tmp_path):
    feature_dir = tmp_path / "ml_exports" / "replay"
    replay_dir = tmp_path / "replay_intermediate_legacy"
    output_dir = tmp_path / "semantic_v1"
    manifest_root = tmp_path / "manifests"
    feature_dir.mkdir(parents=True)
    replay_dir.mkdir(parents=True)

    features = pd.DataFrame(
        [
            {
                "time": "2026-03-20T09:00:00+09:00",
                "signal_bar_ts": 1773936000,
                "signal_timeframe": "M1",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "range_lower_reversal_buy",
                "setup_side": "BUY",
                "entry_stage": "aggressive",
                "preflight_regime": "range",
                "preflight_liquidity": "high",
                "decision_row_key": "legacy-rk1",
                "runtime_snapshot_key": "legacy-snap1",
                "trade_link_key": "legacy-trade1",
                "replay_row_key": "legacy-rk1",
                "position_x_box": 0.1,
                "response_mid_reclaim_up": 0.7,
                "state_alignment_gain": 0.6,
                "evidence_buy_total": 0.8,
                "forecast_position_primary_label": "lower_buy_zone",
            },
            {
                "time": "2026-03-20T09:01:00+09:00",
                "signal_bar_ts": 1773936060,
                "signal_timeframe": "M1",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "upper_reject_sell",
                "setup_side": "SELL",
                "entry_stage": "confirm",
                "preflight_regime": "range",
                "preflight_liquidity": "medium",
                "decision_row_key": "legacy-rk2",
                "runtime_snapshot_key": "legacy-snap2",
                "trade_link_key": "legacy-trade2",
                "replay_row_key": "legacy-rk2",
                "position_x_box": -0.2,
                "response_mid_reclaim_up": 0.2,
                "state_alignment_gain": 0.3,
                "evidence_buy_total": 0.2,
                "forecast_position_primary_label": "upper_sell_zone",
            },
        ]
    )
    feature_path = feature_dir / "entry_decisions.legacy_sample.replay.parquet"
    features.to_parquet(feature_path, index=False)

    replay_rows = [
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "legacy-rk1",
            "decision_row_key": "legacy-rk1",
            "runtime_snapshot_key": "legacy-snap1",
            "trade_link_key": "legacy-trade1",
            "replay_row_key": "legacy-rk1",
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 3,
            "label_negative_count": 1,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "legacy-rk1",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 3,
                "label_negative_count": 1,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 3, "negative_count": 1, "unknown_count": 0},
                "management": {"positive_count": 1, "negative_count": 0, "unknown_count": 0},
            },
        },
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "legacy-rk2",
            "decision_row_key": "legacy-rk2",
            "runtime_snapshot_key": "legacy-snap2",
            "trade_link_key": "legacy-trade2",
            "replay_row_key": "legacy-rk2",
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 1,
            "label_negative_count": 3,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "legacy-rk2",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 1,
                "label_negative_count": 3,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 1, "negative_count": 3, "unknown_count": 0},
                "management": {"positive_count": 0, "negative_count": 1, "unknown_count": 0},
            },
        },
    ]
    (replay_dir / "replay_rows.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in replay_rows) + "\n",
        encoding="utf-8",
    )

    result = builder_module.build_semantic_v1_datasets(
        feature_source=feature_dir,
        replay_source=replay_dir,
        output_dir=output_dir,
        manifest_root=manifest_root,
    )

    summary = json.loads((output_dir / "entry_quality_dataset.parquet.summary.json").read_text(encoding="utf-8"))
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    dataset_df = pd.read_parquet(output_dir / "entry_quality_dataset.parquet")

    assert summary["source_generation"] == builder_module.SOURCE_GENERATION_LEGACY
    assert summary["feature_tier_policy"]["trace_quality_pack"] == "observed_only"
    assert summary["feature_tier_summary"]["trace_quality_pack"]["mode"] == "observed_only"
    assert "signal_age_sec" in summary["observed_only_dropped_feature_columns"]
    assert "missing_columns" in summary
    assert "signal_age_sec" in summary["dropped_feature_columns"]
    assert "forecast_management_horizon_bars" in summary["dropped_feature_columns"]
    assert "signal_age_sec" not in dataset_df.columns
    assert "forecast_management_horizon_bars" not in dataset_df.columns
    assert manifest["source_generation"] == builder_module.SOURCE_GENERATION_LEGACY
    assert "missing_columns" in manifest["datasets"]["entry_quality"]
    assert "signal_age_sec" in manifest["datasets"]["entry_quality"]["dropped_feature_columns"]
    assert "signal_age_sec" in manifest["datasets"]["entry_quality"]["observed_only_dropped_feature_columns"]


def test_build_semantic_v1_datasets_treats_mixed_trace_quality_as_observed_only(tmp_path):
    feature_dir = tmp_path / "ml_exports" / "replay"
    replay_dir = tmp_path / "replay_intermediate_modern"
    output_dir = tmp_path / "semantic_v1"
    manifest_root = tmp_path / "manifests"
    feature_dir.mkdir(parents=True)
    replay_dir.mkdir(parents=True)

    legacy_features = pd.DataFrame(
        [
            {
                "time": "2026-03-20T09:00:00+09:00",
                "signal_bar_ts": 1773936000,
                "signal_timeframe": "M1",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "range_lower_reversal_buy",
                "setup_side": "BUY",
                "entry_stage": "aggressive",
                "preflight_regime": "range",
                "preflight_liquidity": "high",
                "decision_row_key": "mixed-rk1",
                "runtime_snapshot_key": "mixed-snap1",
                "trade_link_key": "mixed-trade1",
                "replay_row_key": "mixed-rk1",
                "position_x_box": 0.1,
                "response_mid_reclaim_up": 0.7,
                "state_alignment_gain": 0.6,
                "evidence_buy_total": 0.8,
                "forecast_position_primary_label": "lower_buy_zone",
            }
        ]
    )
    modern_features = pd.DataFrame(
        [
            {
                "time": "2026-03-20T09:01:00+09:00",
                "signal_bar_ts": 1773936060,
                "signal_timeframe": "M1",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "upper_reject_sell",
                "setup_side": "SELL",
                "entry_stage": "confirm",
                "preflight_regime": "range",
                "preflight_liquidity": "medium",
                "decision_row_key": "mixed-rk2",
                "runtime_snapshot_key": "mixed-snap2",
                "trade_link_key": "mixed-trade2",
                "replay_row_key": "mixed-rk2",
                "position_x_box": -0.2,
                "response_mid_reclaim_up": 0.2,
                "state_alignment_gain": 0.3,
                "evidence_buy_total": 0.2,
                "forecast_position_primary_label": "upper_sell_zone",
            }
        ]
    )
    legacy_features.to_parquet(feature_dir / "entry_decisions.legacy_sample.replay.parquet", index=False)
    modern_features.to_parquet(feature_dir / "entry_decisions.modern_sample.replay.parquet", index=False)

    replay_rows = [
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "mixed-rk1",
            "decision_row_key": "mixed-rk1",
            "runtime_snapshot_key": "mixed-snap1",
            "trade_link_key": "mixed-trade1",
            "replay_row_key": "mixed-rk1",
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 3,
            "label_negative_count": 1,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "mixed-rk1",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 3,
                "label_negative_count": 1,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 3, "negative_count": 1, "unknown_count": 0},
                "management": {"positive_count": 1, "negative_count": 0, "unknown_count": 0},
            },
        },
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "mixed-rk2",
            "decision_row_key": "mixed-rk2",
            "runtime_snapshot_key": "mixed-snap2",
            "trade_link_key": "mixed-trade2",
            "replay_row_key": "mixed-rk2",
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 1,
            "label_negative_count": 3,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "mixed-rk2",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 1,
                "label_negative_count": 3,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 1, "negative_count": 3, "unknown_count": 0},
                "management": {"positive_count": 0, "negative_count": 1, "unknown_count": 0},
            },
        },
    ]
    (replay_dir / "replay_rows.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in replay_rows) + "\n",
        encoding="utf-8",
    )

    result = builder_module.build_semantic_v1_datasets(
        feature_source=feature_dir,
        replay_source=replay_dir,
        output_dir=output_dir,
        manifest_root=manifest_root,
    )

    summary = json.loads((output_dir / "timing_dataset.parquet.summary.json").read_text(encoding="utf-8"))
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

    assert summary["source_generation"] == builder_module.SOURCE_GENERATION_MIXED
    assert summary["feature_tier_policy"]["trace_quality_pack"] == "observed_only"
    assert summary["feature_tier_summary"]["trace_quality_pack"]["mode"] == "observed_only"
    assert "signal_age_sec" in summary["observed_only_dropped_feature_columns"]
    assert manifest["datasets"]["timing"]["feature_tier_summary"]["trace_quality_pack"]["mode"] == "observed_only"


def test_timing_target_uses_quality_as_tie_breaker_only_when_fallback_agrees():
    negative_tie_row = {
        "transition_same_side_positive_count": 1,
        "transition_adverse_positive_count": 1,
        "transition_positive_count": 2,
        "transition_negative_count": 3,
        "transition_quality_score": -0.0012,
    }
    assert builder_module._resolve_timing_target_reason(negative_tie_row) == "tie_break_negative"
    assert builder_module._resolve_timing_target(negative_tie_row) == 0
    assert builder_module._resolve_timing_margin(negative_tie_row) == -0.0012

    ambiguous_tie_row = {
        "transition_same_side_positive_count": 1,
        "transition_adverse_positive_count": 1,
        "transition_positive_count": 2,
        "transition_negative_count": 3,
        "transition_quality_score": -0.0001,
    }
    assert builder_module._resolve_timing_target_reason(ambiguous_tie_row) == "ambiguous_tie"
    assert builder_module._resolve_timing_target(ambiguous_tie_row) is None
    assert builder_module._resolve_timing_margin(ambiguous_tie_row) == -0.0001
    assert (
        builder_module._resolve_semantic_target(
            {
                **ambiguous_tie_row,
                "semantic_target_source": 1,
            },
            dataset_key="timing",
            positive=2,
            negative=3,
            status="VALID",
            is_ambiguous=False,
            is_censored=False,
        )
        is None
    )

    positive_count_row = {
        "transition_same_side_positive_count": 2,
        "transition_adverse_positive_count": 0,
        "transition_positive_count": 2,
        "transition_negative_count": 3,
        "transition_quality_score": 0.0035,
    }
    assert builder_module._resolve_timing_target_reason(positive_count_row) == "count_positive"
    assert builder_module._resolve_timing_target(positive_count_row) == 1
    assert builder_module._resolve_timing_margin(positive_count_row) == 2.0035

    conflicting_positive_row = {
        "transition_same_side_positive_count": 2,
        "transition_adverse_positive_count": 1,
        "transition_positive_count": 1,
        "transition_negative_count": 3,
        "transition_quality_score": -0.002,
    }
    assert builder_module._resolve_timing_target_reason(conflicting_positive_row) == "count_positive_conflict_veto"
    assert builder_module._resolve_timing_target(conflicting_positive_row) is None
    assert (
        builder_module._resolve_semantic_target(
            {
                **conflicting_positive_row,
                "semantic_target_source": 1,
            },
            dataset_key="timing",
            positive=1,
            negative=3,
            status="VALID",
            is_ambiguous=False,
            is_censored=False,
        )
        is None
    )

    conflicting_negative_row = {
        "transition_same_side_positive_count": 1,
        "transition_adverse_positive_count": 2,
        "transition_positive_count": 3,
        "transition_negative_count": 1,
        "transition_quality_score": 0.002,
    }
    assert builder_module._resolve_timing_target_reason(conflicting_negative_row) == "count_negative_conflict_veto"
    assert builder_module._resolve_timing_target(conflicting_negative_row) is None
    assert (
        builder_module._resolve_semantic_target(
            {
                **conflicting_negative_row,
                "semantic_target_source": 1,
            },
            dataset_key="timing",
            positive=3,
            negative=1,
            status="VALID",
            is_ambiguous=False,
            is_censored=False,
        )
        is None
    )


def test_entry_quality_target_requires_support_and_drops_ambiguous_quality_only_rows():
    positive_row = {
        "transition_same_side_positive_count": 2,
        "transition_adverse_positive_count": 0,
        "transition_quality_score": 0.0035,
    }
    assert builder_module._resolve_entry_quality_target_reason(positive_row) == "support_positive"
    assert builder_module._resolve_entry_quality_target(positive_row) == 1
    assert builder_module._resolve_entry_quality_margin(positive_row) == 2.0035

    negative_row = {
        "transition_same_side_positive_count": 0,
        "transition_adverse_positive_count": 1,
        "transition_quality_score": -0.0001,
    }
    assert builder_module._resolve_entry_quality_target_reason(negative_row) == "support_negative"
    assert builder_module._resolve_entry_quality_target(negative_row) == 0
    assert builder_module._resolve_entry_quality_margin(negative_row) == -1.0001

    ambiguous_quality_only_row = {
        "transition_same_side_positive_count": 0,
        "transition_adverse_positive_count": 0,
        "transition_quality_score": 0.002268,
    }
    assert builder_module._resolve_entry_quality_target_reason(ambiguous_quality_only_row) == "ambiguous"
    assert builder_module._resolve_entry_quality_target(ambiguous_quality_only_row) is None
    assert builder_module._resolve_entry_quality_margin(ambiguous_quality_only_row) == 0.002268
    assert (
        builder_module._resolve_semantic_target(
            {
                **ambiguous_quality_only_row,
                "semantic_target_source": 1,
            },
            dataset_key="entry_quality",
            positive=3,
            negative=1,
            status="VALID",
            is_ambiguous=False,
            is_censored=False,
        )
        is None
    )

    trend_row_below_strict_threshold = {
        "preflight_regime": "TREND",
        "transition_same_side_positive_count": 2,
        "transition_adverse_positive_count": 0,
        "transition_quality_score": 0.0075,
    }
    assert builder_module._resolve_entry_quality_target_reason(trend_row_below_strict_threshold) == "support_positive_quality_short"
    assert builder_module._resolve_entry_quality_target(trend_row_below_strict_threshold) is None

    trend_row_above_strict_threshold = {
        "preflight_regime": "TREND",
        "transition_same_side_positive_count": 2,
        "transition_adverse_positive_count": 0,
        "transition_quality_score": 0.0095,
    }
    assert builder_module._resolve_entry_quality_target_reason(trend_row_above_strict_threshold) == "support_positive"
    assert builder_module._resolve_entry_quality_target(trend_row_above_strict_threshold) == 1

    fallback_heavy_positive_row = {
        "transition_same_side_positive_count": 2,
        "transition_adverse_positive_count": 0,
        "transition_quality_score": 0.0042,
        "compatibility_mode": "hybrid",
    }
    assert builder_module._resolve_entry_quality_target_reason(fallback_heavy_positive_row) == "support_positive_fallback_veto"
    assert builder_module._resolve_entry_quality_target(fallback_heavy_positive_row) is None
    assert (
        builder_module._resolve_semantic_target(
            {
                **fallback_heavy_positive_row,
                "semantic_target_source": 1,
            },
            dataset_key="entry_quality",
            positive=3,
            negative=1,
            status="VALID",
            is_ambiguous=False,
            is_censored=False,
        )
        is None
    )

    hold_conflict_positive_row = {
        "transition_same_side_positive_count": 2,
        "transition_adverse_positive_count": 0,
        "transition_quality_score": 0.0042,
        "management_hold_favor_positive_count": 2,
        "management_exit_favor_positive_count": 0,
    }
    assert builder_module._resolve_entry_quality_target_reason(hold_conflict_positive_row) == "support_positive_hold_conflict_veto"
    assert builder_module._resolve_entry_quality_target(hold_conflict_positive_row) is None

    hold_conflict_negative_quality_only_row = {
        "transition_same_side_positive_count": 0,
        "transition_adverse_positive_count": 0,
        "transition_quality_score": -0.0012,
        "management_hold_favor_positive_count": 2,
        "management_exit_favor_positive_count": 0,
    }
    assert builder_module._resolve_entry_quality_target_reason(hold_conflict_negative_quality_only_row) == "quality_negative_hold_conflict_veto"
    assert builder_module._resolve_entry_quality_target(hold_conflict_negative_quality_only_row) is None

    na_guard_positive_row = {
        "transition_same_side_positive_count": 2,
        "transition_adverse_positive_count": 0,
        "transition_quality_score": 0.0035,
        "used_fallback_count": pd.NA,
        "missing_feature_count": pd.NA,
        "management_hold_favor_positive_count": pd.NA,
        "management_exit_favor_positive_count": pd.NA,
    }
    assert builder_module._resolve_entry_quality_target_reason(na_guard_positive_row) == "support_positive"
    assert builder_module._resolve_entry_quality_target(na_guard_positive_row) == 1


def test_build_semantic_v1_datasets_preserves_duplicate_join_keys_by_occurrence(tmp_path):
    feature_dir = tmp_path / "ml_exports" / "replay"
    replay_dir = tmp_path / "replay_intermediate"
    output_dir = tmp_path / "semantic_v1"
    manifest_root = tmp_path / "manifests"
    feature_dir.mkdir(parents=True)
    replay_dir.mkdir(parents=True)

    features = pd.DataFrame(
        [
            {
                "time": "2026-03-20T09:00:00+09:00",
                "signal_bar_ts": 1773936000,
                "signal_timeframe": "M1",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "range_lower_reversal_buy",
                "setup_side": "BUY",
                "entry_stage": "aggressive",
                "preflight_regime": "range",
                "preflight_liquidity": "high",
                "decision_row_key": "dup-rk",
                "runtime_snapshot_key": "snap-a",
                "trade_link_key": "trade-a",
                "replay_row_key": "dup-rk",
                "position_x_box": 0.1,
                "response_mid_reclaim_up": 0.7,
                "state_alignment_gain": 0.6,
                "evidence_buy_total": 0.8,
                "forecast_position_primary_label": "lower_buy_zone",
                "signal_age_sec": 3.0,
                "bar_age_sec": 3.0,
                "decision_latency_ms": 120,
                "order_submit_latency_ms": 40,
                "missing_feature_count": 0,
                "data_completeness_ratio": 1.0,
                "used_fallback_count": 0,
                "compatibility_mode": "",
                "detail_blob_bytes": 100,
                "snapshot_payload_bytes": 80,
                "row_payload_bytes": 60,
            },
            {
                "time": "2026-03-20T09:00:10+09:00",
                "signal_bar_ts": 1773936000,
                "signal_timeframe": "M1",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "range_lower_reversal_buy",
                "setup_side": "BUY",
                "entry_stage": "aggressive",
                "preflight_regime": "range",
                "preflight_liquidity": "high",
                "decision_row_key": "dup-rk",
                "runtime_snapshot_key": "snap-b",
                "trade_link_key": "trade-b",
                "replay_row_key": "dup-rk",
                "position_x_box": 0.2,
                "response_mid_reclaim_up": 0.8,
                "state_alignment_gain": 0.7,
                "evidence_buy_total": 0.9,
                "forecast_position_primary_label": "lower_buy_zone",
                "signal_age_sec": 4.0,
                "bar_age_sec": 4.0,
                "decision_latency_ms": 140,
                "order_submit_latency_ms": 45,
                "missing_feature_count": 0,
                "data_completeness_ratio": 1.0,
                "used_fallback_count": 0,
                "compatibility_mode": "",
                "detail_blob_bytes": 110,
                "snapshot_payload_bytes": 85,
                "row_payload_bytes": 65,
            },
        ]
    )
    features.to_parquet(feature_dir / "semantic_replay.parquet", index=False)

    replay_rows = [
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "dup-rk",
            "decision_row_key": "dup-rk",
            "runtime_snapshot_key": "snap-a",
            "trade_link_key": "trade-a",
            "replay_row_key": "dup-rk",
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 3,
            "label_negative_count": 1,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "dup-rk",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 3,
                "label_negative_count": 1,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 2, "negative_count": 0, "unknown_count": 0},
                "management": {"positive_count": 2, "negative_count": 1, "unknown_count": 0},
            },
        },
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "dup-rk",
            "decision_row_key": "dup-rk",
            "runtime_snapshot_key": "snap-b",
            "trade_link_key": "trade-b",
            "replay_row_key": "dup-rk",
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 1,
            "label_negative_count": 4,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "dup-rk",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 1,
                "label_negative_count": 4,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 0, "negative_count": 2, "unknown_count": 0},
                "management": {"positive_count": 0, "negative_count": 3, "unknown_count": 0},
            },
        },
    ]
    (replay_dir / "replay_rows.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in replay_rows) + "\n",
        encoding="utf-8",
    )

    summary = builder_module.build_semantic_v1_datasets(
        feature_source=feature_dir,
        replay_source=replay_dir,
        output_dir=output_dir,
        manifest_root=manifest_root,
    )

    timing_df = pd.read_parquet(output_dir / "timing_dataset.parquet")
    assert summary["joined_rows"] == 2
    assert len(timing_df) == 2
    assert set(timing_df["runtime_snapshot_key"]) == {"snap-a", "snap-b"}


def test_build_semantic_v1_datasets_prefers_outcome_semantics_for_targets(tmp_path):
    feature_dir = tmp_path / "ml_exports" / "replay"
    replay_dir = tmp_path / "replay_intermediate"
    output_dir = tmp_path / "semantic_v1"
    manifest_root = tmp_path / "manifests"
    feature_dir.mkdir(parents=True)
    replay_dir.mkdir(parents=True)

    features = pd.DataFrame(
        [
            {
                "time": "2026-03-20T10:00:00+09:00",
                "signal_bar_ts": 1773939600,
                "signal_timeframe": "M15",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "range_lower_reversal_buy",
                "setup_side": "BUY",
                "entry_stage": "aggressive",
                "preflight_regime": "range",
                "preflight_liquidity": "high",
                "decision_row_key": "sem-rk1",
                "runtime_snapshot_key": "sem-snap1",
                "trade_link_key": "sem-trade1",
                "replay_row_key": "sem-rk1",
                "position_x_box": 0.1,
                "response_mid_reclaim_up": 0.9,
                "state_alignment_gain": 0.8,
                "evidence_buy_total": 0.8,
                "forecast_position_primary_label": "lower_buy_zone",
                "signal_age_sec": 2.0,
                "bar_age_sec": 2.0,
                "decision_latency_ms": 100,
                "order_submit_latency_ms": 25,
                "missing_feature_count": 0,
                "data_completeness_ratio": 1.0,
                "used_fallback_count": 0,
                "compatibility_mode": "",
                "detail_blob_bytes": 80,
                "snapshot_payload_bytes": 70,
                "row_payload_bytes": 55,
            },
            {
                "time": "2026-03-20T10:15:00+09:00",
                "signal_bar_ts": 1773940500,
                "signal_timeframe": "M15",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "upper_reject_sell",
                "setup_side": "SELL",
                "entry_stage": "confirm",
                "preflight_regime": "trend",
                "preflight_liquidity": "high",
                "decision_row_key": "sem-rk2",
                "runtime_snapshot_key": "sem-snap2",
                "trade_link_key": "sem-trade2",
                "replay_row_key": "sem-rk2",
                "position_x_box": 0.7,
                "response_mid_reclaim_up": 0.2,
                "state_alignment_gain": 0.2,
                "evidence_buy_total": 0.1,
                "forecast_position_primary_label": "upper_sell_zone",
                "signal_age_sec": 6.0,
                "bar_age_sec": 6.0,
                "decision_latency_ms": 150,
                "order_submit_latency_ms": 40,
                "missing_feature_count": 0,
                "data_completeness_ratio": 1.0,
                "used_fallback_count": 0,
                "compatibility_mode": "",
                "detail_blob_bytes": 82,
                "snapshot_payload_bytes": 72,
                "row_payload_bytes": 56,
            },
        ]
    )
    features.to_parquet(feature_dir / "semantic_replay.parquet", index=False)

    replay_rows = [
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "sem-rk1",
            "decision_row_key": "sem-rk1",
            "runtime_snapshot_key": "sem-snap1",
            "trade_link_key": "sem-trade1",
            "replay_row_key": "sem-rk1",
            "decision_row": {"symbol": "BTCUSD", "setup_side": "BUY", "action": "BUY"},
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 1,
            "label_negative_count": 4,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "sem-rk1",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 1,
                "label_negative_count": 4,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 0, "negative_count": 4, "unknown_count": 0},
                "management": {"positive_count": 0, "negative_count": 2, "unknown_count": 0},
            },
            "outcome_labels_v1": {
                "transition": {
                    "label_status": "VALID",
                    "metadata": {
                        "position_context": {"direction": "BUY"},
                        "label_polarities": {
                            "buy_confirm_success_label": "POSITIVE",
                            "sell_confirm_success_label": "NEGATIVE",
                            "false_break_label": "NEGATIVE",
                            "reversal_success_label": "NEGATIVE",
                            "continuation_success_label": "POSITIVE",
                        },
                        "path_metrics": {
                            "bullish_move_ratio": 0.0007,
                            "bearish_move_ratio": 0.0001,
                        },
                    },
                },
                "trade_management": {
                    "label_status": "VALID",
                    "metadata": {
                        "label_polarities": {
                            "continue_favor_label": "POSITIVE",
                            "fail_now_label": "NEGATIVE",
                            "recover_after_pullback_label": "NEGATIVE",
                            "reach_tp1_label": "NEGATIVE",
                            "opposite_edge_reach_label": "NEGATIVE",
                            "better_reentry_if_cut_label": "NEGATIVE",
                        }
                    },
                },
            },
        },
        {
            "row_type": "replay_dataset_row_v1",
            "row_key": "sem-rk2",
            "decision_row_key": "sem-rk2",
            "runtime_snapshot_key": "sem-snap2",
            "trade_link_key": "sem-trade2",
            "replay_row_key": "sem-rk2",
            "decision_row": {"symbol": "XAUUSD", "setup_side": "SELL", "action": "SELL"},
            "transition_label_status": "VALID",
            "management_label_status": "VALID",
            "label_unknown_count": 0,
            "label_positive_count": 4,
            "label_negative_count": 1,
            "label_is_ambiguous": False,
            "label_source_descriptor": "closed_trade+future_bars",
            "is_censored": False,
            "label_quality_summary_v1": {
                "row_key": "sem-rk2",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 4,
                "label_negative_count": 1,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition": {"positive_count": 4, "negative_count": 1, "unknown_count": 0},
                "management": {"positive_count": 3, "negative_count": 0, "unknown_count": 0},
            },
            "outcome_labels_v1": {
                "transition": {
                    "label_status": "VALID",
                    "metadata": {
                        "position_context": {"direction": "SELL"},
                        "label_polarities": {
                            "buy_confirm_success_label": "POSITIVE",
                            "sell_confirm_success_label": "NEGATIVE",
                            "false_break_label": "POSITIVE",
                            "reversal_success_label": "NEGATIVE",
                            "continuation_success_label": "NEGATIVE",
                        },
                        "path_metrics": {
                            "bullish_move_ratio": 0.0006,
                            "bearish_move_ratio": 0.0001,
                        },
                    },
                },
                "trade_management": {
                    "label_status": "VALID",
                    "metadata": {
                        "label_polarities": {
                            "continue_favor_label": "NEGATIVE",
                            "fail_now_label": "POSITIVE",
                            "recover_after_pullback_label": "NEGATIVE",
                            "reach_tp1_label": "NEGATIVE",
                            "opposite_edge_reach_label": "NEGATIVE",
                            "better_reentry_if_cut_label": "NEGATIVE",
                        }
                    },
                },
            },
        },
    ]
    (replay_dir / "replay_rows.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in replay_rows) + "\n",
        encoding="utf-8",
    )

    builder_module.build_semantic_v1_datasets(
        feature_source=feature_dir,
        replay_source=replay_dir,
        output_dir=output_dir,
        manifest_root=manifest_root,
    )

    timing_df = pd.read_parquet(output_dir / "timing_dataset.parquet")
    entry_df = pd.read_parquet(output_dir / "entry_quality_dataset.parquet")
    exit_df = pd.read_parquet(output_dir / "exit_management_dataset.parquet")

    timing_targets = dict(zip(timing_df["decision_row_key"], timing_df["target_timing_now_vs_wait"]))
    entry_targets = dict(zip(entry_df["decision_row_key"], entry_df["target_entry_quality"]))
    exit_targets = dict(zip(exit_df["decision_row_key"], exit_df["target_exit_management"]))

    assert timing_targets == {"sem-rk1": 1, "sem-rk2": 0}
    assert entry_targets == {"sem-rk2": 0}
    assert exit_targets == {"sem-rk1": 0, "sem-rk2": 1}


def test_build_join_health_report_detects_orphans_and_runtime_key_mismatch(tmp_path):
    feature_df = pd.DataFrame(
        [
            {
                "join_key": "rk1",
                "join_ordinal": 0,
                "decision_row_key": "rk1",
                "runtime_snapshot_key": "snap-a",
                "trade_link_key": "trade-a",
                "replay_row_key": "rk1",
            },
            {
                "join_key": "rk_only_feature",
                "join_ordinal": 0,
                "decision_row_key": "rk_only_feature",
                "runtime_snapshot_key": "snap-only-feature",
                "trade_link_key": "",
                "replay_row_key": "rk_only_feature",
            },
        ]
    )
    label_df = pd.DataFrame(
        [
            {
                "join_key": "rk1",
                "join_ordinal": 0,
                "decision_row_key": "rk1",
                "runtime_snapshot_key": "snap-b",
                "trade_link_key": "trade-a",
                "replay_row_key": "rk1",
            },
            {
                "join_key": "rk_only_label",
                "join_ordinal": 0,
                "decision_row_key": "rk_only_label",
                "runtime_snapshot_key": "snap-only-label",
                "trade_link_key": "",
                "replay_row_key": "rk_only_label",
            },
        ]
    )
    joined_df = feature_df.merge(
        label_df,
        on=["join_key", "join_ordinal"],
        how="inner",
        suffixes=("", "_label"),
    )

    report = builder_module._build_join_health_report(
        feature_df=feature_df,
        label_df=label_df,
        joined_df=joined_df,
        feature_source=tmp_path / "features",
        replay_source=tmp_path / "replay",
    )

    assert report["feature_only_join_keys_count"] == 1
    assert report["label_only_join_keys_count"] == 1
    assert report["joined_rows"] == 1
    assert report["joined_key_mismatch_rows"]["runtime_snapshot_key"] == 1
