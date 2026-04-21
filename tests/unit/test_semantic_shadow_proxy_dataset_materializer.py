from pathlib import Path
import json

import pandas as pd

from backend.services.semantic_shadow_proxy_dataset_materializer import build_semantic_shadow_proxy_datasets


def _json_text(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def test_build_semantic_shadow_proxy_datasets_materializes_matched_feature_rows(tmp_path: Path):
    corpus_path = tmp_path / "semantic_shadow_training_corpus_latest.json"
    adapter_path = tmp_path / "semantic_shadow_training_bridge_adapter_latest.csv"
    archive_path = tmp_path / "entry_decisions.parquet"
    rebalanced_path = tmp_path / "shadow_rebalanced_training_corpus_latest.csv"

    corpus_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "corpus_source_id": "current_bridge",
                        "row_key": "bridge_row_key_1",
                        "bridge_quality_status": "full_outcome_bridge",
                        "entry_wait_quality_label": "avoided_loss_by_wait",
                        "state25_runtime_hint_v1": {
                            "scene_family": "reversal",
                            "wait_bias_hint": "wait",
                        },
                        "forecast_runtime_summary_v1": {
                            "decision_hint": "BALANCED",
                        },
                        "economic_target_summary": {
                            "learning_total_label": "positive",
                            "learning_total_score": 0.8,
                            "loss_quality_label": "non_loss",
                            "signed_exit_score": 3.5,
                            "profit": 2.0,
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    pd.DataFrame(
        [
            {
                "bridge_adapter_row_id": "bridge_adapter::0001",
                "bridge_row_key": "bridge_row_key_1",
                "bridge_decision_time": "2026-04-07T00:00:00",
                "archive_source_file": str(archive_path),
                "archive_replay_row_key": "replay_row_key_1",
                "match_status": "matched",
            }
        ]
    ).to_csv(adapter_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {
                "bridge_adapter_row_id": "bridge_adapter::0001",
                "effective_target_action_class": "wait_more",
                "effective_target_action_variant": "wait_small_value",
                "manual_target_action_class": "wait_more",
                "mapped_target_action_class": "exit_protect",
                "sample_weight": 2.5,
                "rebalance_bucket": "retarget_priority",
            }
        ]
    ).to_csv(rebalanced_path, index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "time": "2026-04-07T00:00:00",
                "signal_timeframe": "M1",
                "signal_bar_ts": 1775526000,
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "blocked_by": "",
                "decision_row_key": "decision_1",
                "runtime_snapshot_key": "runtime_1",
                "trade_link_key": "trade_1",
                "replay_row_key": "replay_row_key_1",
                "entry_stage": "probe",
                "setup_id": "setup_1",
                "setup_side": "BUY",
                "preflight_regime": "trend",
                "preflight_liquidity": "normal",
                "position_snapshot_v2": _json_text(
                    {
                        "vector": {"x_box": 0.1},
                        "interpretation": {"alignment_label": "aligned"},
                        "energy": {"lower_position_force": 0.2},
                    }
                ),
                "response_vector_v2": _json_text({"lower_hold_up": 0.3}),
                "state_vector_v2": _json_text({"alignment_gain": 0.4}),
                "evidence_vector_v1": _json_text({"buy_total_evidence": 0.5}),
                "belief_state_v1": "{}",
                "barrier_state_v1": "{}",
                "forecast_features_v1": _json_text({"position_primary_label": "balanced"}),
            }
        ]
    ).to_parquet(archive_path, index=False)

    datasets, summary, feature_rows = build_semantic_shadow_proxy_datasets(
        corpus_path=corpus_path,
        adapter_path=adapter_path,
        rebalanced_corpus_path=rebalanced_path,
        use_rebalanced_targets=True,
    )

    assert summary["matched_feature_row_count"] == 1
    assert summary["use_rebalanced_targets"] is True
    assert len(feature_rows) == 1
    assert len(datasets["timing"]) == 1
    timing_row = datasets["timing"].iloc[0]
    assert timing_row["target_timing_now_vs_wait"] == 0
    assert timing_row["target_entry_quality"] == 0
    assert timing_row["target_exit_management"] == 0
    assert timing_row["coarse_action_target_class"] == "wait_more"
    assert timing_row["sample_weight"] == 2.5
    assert timing_row["baseline_action"] == "BUY"
    assert timing_row["symbol"] == "BTCUSD"


def test_build_semantic_shadow_proxy_datasets_uses_rebalanced_targets_by_default(tmp_path: Path):
    corpus_path = tmp_path / "semantic_shadow_training_corpus_latest.json"
    adapter_path = tmp_path / "semantic_shadow_training_bridge_adapter_latest.csv"
    archive_path = tmp_path / "entry_decisions.parquet"
    rebalanced_path = tmp_path / "shadow_rebalanced_training_corpus_latest.csv"

    corpus_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "corpus_source_id": "current_bridge",
                        "row_key": "bridge_row_key_1",
                        "bridge_quality_status": "full_outcome_bridge",
                        "entry_wait_quality_label": "bad_wait_missed_move",
                        "state25_runtime_hint_v1": {"scene_family": "reversal", "wait_bias_hint": "wait"},
                        "forecast_runtime_summary_v1": {"decision_hint": "BALANCED"},
                        "economic_target_summary": {
                            "learning_total_label": "negative",
                            "learning_total_score": -0.6,
                            "loss_quality_label": "loss",
                            "signed_exit_score": -2.0,
                            "profit": 0.0,
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    pd.DataFrame(
        [
            {
                "bridge_adapter_row_id": "bridge_adapter::0001",
                "bridge_row_key": "bridge_row_key_1",
                "bridge_decision_time": "2026-04-07T00:00:00",
                "archive_source_file": str(archive_path),
                "archive_replay_row_key": "replay_row_key_1",
                "match_status": "matched",
            }
        ]
    ).to_csv(adapter_path, index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "bridge_adapter_row_id": "bridge_adapter::0001",
                "effective_target_action_class": "wait_more",
                "effective_target_action_variant": "wait_better_entry",
                "mapped_target_action_class": "enter_now",
                "sample_weight": 3.0,
                "rebalance_bucket": "manual_truth_anchor",
            }
        ]
    ).to_csv(rebalanced_path, index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "time": "2026-04-07T00:00:00",
                "signal_timeframe": "M1",
                "signal_bar_ts": 1775526000,
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "blocked_by": "",
                "decision_row_key": "decision_1",
                "runtime_snapshot_key": "runtime_1",
                "trade_link_key": "trade_1",
                "replay_row_key": "replay_row_key_1",
                "entry_stage": "probe",
                "setup_id": "setup_1",
                "setup_side": "BUY",
                "preflight_regime": "trend",
                "preflight_liquidity": "normal",
                "position_snapshot_v2": _json_text({"vector": {"x_box": 0.1}}),
                "response_vector_v2": _json_text({"lower_hold_up": 0.3}),
                "state_vector_v2": _json_text({"alignment_gain": 0.4}),
                "evidence_vector_v1": _json_text({"buy_total_evidence": 0.5}),
                "belief_state_v1": "{}",
                "barrier_state_v1": "{}",
                "forecast_features_v1": _json_text({"position_primary_label": "balanced"}),
            }
        ]
    ).to_parquet(archive_path, index=False)

    datasets, summary, _feature_rows = build_semantic_shadow_proxy_datasets(
        corpus_path=corpus_path,
        adapter_path=adapter_path,
        rebalanced_corpus_path=rebalanced_path,
    )

    assert summary["use_rebalanced_targets"] is True
    timing_row = datasets["timing"].iloc[0]
    assert timing_row["coarse_action_target_class"] == "wait_more"
    assert timing_row["target_timing_now_vs_wait"] == 0
    assert timing_row["target_entry_quality"] == 1
    assert timing_row["coarse_action_target_variant"] == "wait_better_entry"
    assert timing_row["sample_weight"] == 3.0


def test_build_semantic_shadow_proxy_datasets_skips_excluded_rebalanced_rows(tmp_path: Path):
    corpus_path = tmp_path / "semantic_shadow_training_corpus_latest.json"
    adapter_path = tmp_path / "semantic_shadow_training_bridge_adapter_latest.csv"
    archive_path = tmp_path / "entry_decisions.parquet"
    rebalanced_path = tmp_path / "shadow_rebalanced_training_corpus_latest.csv"

    corpus_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "corpus_source_id": "current_bridge",
                        "row_key": "bridge_row_key_1",
                        "bridge_quality_status": "full_outcome_bridge",
                        "entry_wait_quality_label": "neutral_wait",
                        "state25_runtime_hint_v1": {"scene_family": "reversal", "wait_bias_hint": "wait"},
                        "forecast_runtime_summary_v1": {"decision_hint": "BALANCED"},
                        "economic_target_summary": {"learning_total_label": "neutral", "signed_exit_score": 0.0, "profit": 0.0},
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "bridge_adapter_row_id": "bridge_adapter::0001",
                "bridge_row_key": "bridge_row_key_1",
                "bridge_decision_time": "2026-04-07T00:00:00",
                "archive_source_file": str(archive_path),
                "archive_replay_row_key": "replay_row_key_1",
                "match_status": "matched",
            }
        ]
    ).to_csv(adapter_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {
                "bridge_adapter_row_id": "bridge_adapter::0001",
                "effective_target_action_class": "wait_more",
                "effective_target_action_variant": "wait_small_value",
                "sample_weight": 1.5,
                "rebalance_bucket": "separate_freeze_family",
                "exclude_from_preview_train": True,
            }
        ]
    ).to_csv(rebalanced_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {
                "time": "2026-04-07T00:00:00",
                "signal_timeframe": "M1",
                "signal_bar_ts": 1775526000,
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "blocked_by": "",
                "decision_row_key": "decision_1",
                "runtime_snapshot_key": "runtime_1",
                "trade_link_key": "trade_1",
                "replay_row_key": "replay_row_key_1",
                "entry_stage": "probe",
                "setup_id": "setup_1",
                "setup_side": "BUY",
                "preflight_regime": "trend",
                "preflight_liquidity": "normal",
                "position_snapshot_v2": _json_text({"vector": {"x_box": 0.1}}),
                "response_vector_v2": _json_text({"lower_hold_up": 0.3}),
                "state_vector_v2": _json_text({"alignment_gain": 0.4}),
                "evidence_vector_v1": _json_text({"buy_total_evidence": 0.5}),
                "belief_state_v1": "{}",
                "barrier_state_v1": "{}",
                "forecast_features_v1": _json_text({"position_primary_label": "balanced"}),
            }
        ]
    ).to_parquet(archive_path, index=False)

    datasets, summary, feature_rows = build_semantic_shadow_proxy_datasets(
        corpus_path=corpus_path,
        adapter_path=adapter_path,
        rebalanced_corpus_path=rebalanced_path,
    )

    assert summary["matched_feature_row_count"] == 0
    assert feature_rows.empty
    assert datasets["timing"].empty
