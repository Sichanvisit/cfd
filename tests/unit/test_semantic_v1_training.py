import json
from pathlib import Path

import pandas as pd

from ml.semantic_v1.evaluate import build_train_config, train_semantic_model


def _make_dataset(*, target_column: str, margin_column: str) -> pd.DataFrame:
    rows = []
    symbols = ["BTCUSD", "XAUUSD", "NAS100"]
    regimes = ["range", "trend"]
    setups = ["range_lower_reversal_buy", "upper_reject_sell"]
    liquidities = ["high", "medium", "low"]

    for idx in range(36):
        split_bucket = "train" if idx < 24 else "validation" if idx < 30 else "test"
        target = 1 if idx % 2 == 0 else 0
        positive_bias = 0.8 if target == 1 else 0.2
        negative_bias = 0.2 if target == 1 else 0.8
        rows.append(
            {
                "decision_row_key": f"rk{idx}",
                "runtime_snapshot_key": f"snap{idx}",
                "trade_link_key": f"trade{idx}",
                "replay_row_key": f"rk{idx}",
                "time": f"2026-03-20T09:{idx:02d}:00+09:00",
                "signal_bar_ts": 1773936000 + (idx * 60),
                "signal_timeframe": "M1",
                "symbol": symbols[idx % len(symbols)],
                "setup_id": setups[idx % len(setups)],
                "setup_side": "BUY" if target == 1 else "SELL",
                "entry_stage": "aggressive" if target == 1 else "confirm",
                "preflight_regime": regimes[idx % len(regimes)],
                "preflight_liquidity": liquidities[idx % len(liquidities)],
                "position_x_box": positive_bias,
                "position_x_bb20": positive_bias * 0.9,
                "position_alignment_label": "aligned" if target == 1 else "conflicted",
                "position_bias_label": "buy_bias" if target == 1 else "sell_bias",
                "position_conflict_kind": "none" if target == 1 else "opposed",
                "response_mid_reclaim_up": positive_bias,
                "response_upper_reject_down": negative_bias,
                "state_alignment_gain": positive_bias,
                "state_range_reversal_gain": positive_bias * 0.7,
                "state_noise_damp": negative_bias * 0.3,
                "evidence_buy_total": positive_bias,
                "evidence_sell_total": negative_bias,
                "forecast_position_primary_label": "lower_buy_zone" if target == 1 else "upper_sell_zone",
                "forecast_position_secondary_context_label": "range_reversal" if target == 1 else "upper_reject",
                "forecast_position_conflict_score": 0.1 if target == 1 else 0.7,
                "forecast_middle_neutrality": 0.2 if target == 1 else 0.6,
                "forecast_management_horizon_bars": 6,
                "forecast_signal_timeframe": "M1",
                "signal_age_sec": float(idx % 5),
                "bar_age_sec": float(idx % 5),
                "decision_latency_ms": 100 + idx,
                "order_submit_latency_ms": 30 + (idx % 7),
                "missing_feature_count": 0 if idx % 4 else 2,
                "data_completeness_ratio": 1.0 if idx % 4 else 0.9,
                "used_fallback_count": 0 if idx % 3 else 1,
                "compatibility_mode": "" if idx % 6 else "hybrid",
                "detail_blob_bytes": 100 + idx,
                "snapshot_payload_bytes": 70 + idx,
                "row_payload_bytes": 50 + idx,
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_unknown_count": 0,
                "label_positive_count": 4 if target == 1 else 1,
                "label_negative_count": 1 if target == 1 else 4,
                "label_is_ambiguous": 0,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": 0,
                "transition_positive_count": 3 if target == 1 else 1,
                "transition_negative_count": 1 if target == 1 else 3,
                "transition_unknown_count": 0,
                "management_positive_count": 2 if target == 1 else 1,
                "management_negative_count": 1 if target == 1 else 2,
                "management_unknown_count": 0,
                "event_ts": 1773936000 + (idx * 60),
                "time_split_bucket": split_bucket,
                "symbol_holdout_bucket": "holdout" if idx % 11 == 0 else "train",
                "regime_holdout_bucket": "holdout" if idx % 13 == 0 else "train",
                "is_symbol_holdout": 1 if idx % 11 == 0 else 0,
                "is_regime_holdout": 1 if idx % 13 == 0 else 0,
                target_column: target,
                margin_column: 2.0 if target == 1 else -2.0,
            }
        )
    return pd.DataFrame(rows)


def test_train_semantic_models_write_model_bundles_and_metrics(tmp_path):
    dataset_specs = [
        ("timing", "target_timing_now_vs_wait", "target_timing_margin"),
        ("entry_quality", "target_entry_quality", "target_entry_quality_margin"),
        ("exit_management", "target_exit_management", "target_exit_management_margin"),
    ]

    output_dir = tmp_path / "models" / "semantic_v1"
    metrics_path = output_dir / "metrics.json"

    for dataset_key, target_column, margin_column in dataset_specs:
        dataset_path = tmp_path / f"{dataset_key}.parquet"
        _make_dataset(target_column=target_column, margin_column=margin_column).to_parquet(dataset_path, index=False)

        config = build_train_config(dataset_key, dataset_path=dataset_path, output_dir=output_dir)
        summary = train_semantic_model(config)

        assert Path(summary["model_path"]).exists()
        assert Path(summary["model_summary_path"]).exists()
        assert Path(summary["metrics_path"]).exists()
        assert summary["metrics"]["dataset_key"] == dataset_key
        assert "auc" in summary["metrics"]
        assert "calibration_error" in summary["metrics"]
        assert "symbol_auc" in summary["metrics"]
        assert "regime_auc" in summary["metrics"]
        assert "setup_auc" in summary["metrics"]
        assert "top_k_precision" in summary["metrics"]
        assert "expected_value_proxy" in summary["metrics"]
        assert "fallback_vs_clean" in summary["metrics"]
        assert "split_health" in summary["metrics"]
        assert summary["metrics"]["split_health"]["overall_status"] in {"healthy", "warning", "fail"}
        assert "bucket_coverage" in summary["metrics"]["split_health"]
        assert "holdout_health" in summary["metrics"]["split_health"]
        assert summary["metrics"]["calibration_method"] in {"identity", "platt_logistic"}

    metrics_payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics_payload["metrics_version"] == "semantic_tabular_metrics_v1"
    assert "timing_metrics" in metrics_payload
    assert "entry_quality_metrics" in metrics_payload
    assert "exit_management_metrics" in metrics_payload


def test_train_semantic_model_handles_single_class_validation_split(tmp_path):
    output_dir = tmp_path / "models" / "semantic_v1"
    dataset_path = tmp_path / "exit_management_single_class.parquet"

    frame = _make_dataset(
        target_column="target_exit_management",
        margin_column="target_exit_management_margin",
    )
    frame.loc[frame["time_split_bucket"].isin(["train", "validation"]), "target_exit_management"] = 1
    frame.loc[frame["time_split_bucket"] == "test", "target_exit_management"] = [1, 0, 1, 0, 1, 0]
    frame.to_parquet(dataset_path, index=False)

    config = build_train_config("exit_management", dataset_path=dataset_path, output_dir=output_dir)
    summary = train_semantic_model(config)

    assert Path(summary["model_path"]).exists()
    assert summary["metrics"]["dataset_key"] == "exit_management"
    assert summary["metrics"]["train_class_balance"] == {"1": 24}
    assert summary["metrics"]["validation_class_balance"] == {"1": 6}
    assert summary["metrics"]["test_class_balance"] == {"1": 3, "0": 3}
    assert summary["metrics"]["split_health_status"] == "fail"
    assert summary["metrics"]["split_health_promotion_blocked"] is True
    assert any(
        str(issue).startswith("validation:")
        for issue in summary["metrics"]["split_health"]["blocking_issues"]
    )


def test_train_semantic_model_drops_all_missing_features_and_records_them(tmp_path):
    output_dir = tmp_path / "models" / "semantic_v1"
    dataset_path = tmp_path / "entry_quality_missing_features.parquet"

    frame = _make_dataset(
        target_column="target_entry_quality",
        margin_column="target_entry_quality_margin",
    )
    frame["forecast_management_horizon_bars"] = pd.NA
    frame["signal_age_sec"] = pd.NA
    frame["decision_latency_ms"] = pd.NA
    frame.to_parquet(dataset_path, index=False)

    summary_path = dataset_path.with_suffix(".parquet.summary.json")
    summary_path.write_text(
        json.dumps(
            {
                "source_generation": "legacy",
                "feature_tier_policy": {
                    "semantic_input_pack": "enabled",
                    "trace_quality_pack": "observed_only",
                },
                "dropped_feature_columns": ["signal_age_sec"],
                "dropped_feature_reasons": {"signal_age_sec": "legacy_trace_quality_pack_all_missing"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    config = build_train_config("entry_quality", dataset_path=dataset_path, output_dir=output_dir)
    summary = train_semantic_model(config)

    assert "forecast_management_horizon_bars" in summary["metrics"]["training_dropped_feature_columns"]
    assert "signal_age_sec" in summary["metrics"]["training_dropped_feature_columns"]
    assert "decision_latency_ms" in summary["metrics"]["training_dropped_feature_columns"]
    assert "forecast_management_horizon_bars" not in summary["metrics"]["feature_columns"]
    assert summary["metrics"]["dataset_source_generation"] == "legacy"
    assert summary["metrics"]["dataset_feature_tier_policy"]["trace_quality_pack"] == "observed_only"
    assert summary["metrics"]["dataset_feature_tier_summary"]["trace_quality_pack"]["mode"] == "observed_only"
    assert "signal_age_sec" in summary["metrics"]["dataset_observed_only_dropped_feature_columns"]


def test_train_semantic_model_handles_builder_dropped_fallback_columns(tmp_path):
    output_dir = tmp_path / "models" / "semantic_v1"
    dataset_path = tmp_path / "timing_builder_dropped_cols.parquet"

    frame = _make_dataset(
        target_column="target_timing_now_vs_wait",
        margin_column="target_timing_margin",
    ).drop(columns=["used_fallback_count", "missing_feature_count", "compatibility_mode"])
    frame.to_parquet(dataset_path, index=False)

    config = build_train_config("timing", dataset_path=dataset_path, output_dir=output_dir)
    summary = train_semantic_model(config)

    assert summary["metrics"]["rows"] > 0
    assert summary["metrics"]["fallback_vs_clean"]["fallback_heavy"]["rows"] == 0
    assert summary["metrics"]["fallback_vs_clean"]["clean"]["rows"] == summary["metrics"]["rows"]
