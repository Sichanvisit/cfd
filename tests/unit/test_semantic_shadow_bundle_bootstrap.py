from pathlib import Path
import json

import pandas as pd

from backend.services.semantic_shadow_bundle_bootstrap import (
    build_semantic_shadow_bundle_bootstrap,
)


def test_semantic_shadow_bundle_bootstrap_reports_active_bundle_ready(tmp_path: Path):
    model_dir = tmp_path / "models" / "semantic_v1"
    model_dir.mkdir(parents=True, exist_ok=True)
    for file_name in [
        "timing_model.joblib",
        "entry_quality_model.joblib",
        "exit_management_model.joblib",
        "metrics.json",
    ]:
        (model_dir / file_name).write_text("placeholder", encoding="utf-8")

    frame, summary = build_semantic_shadow_bundle_bootstrap(
        model_dir=model_dir,
        models_root=tmp_path / "models",
        semantic_dataset_dir=tmp_path / "datasets",
        feature_source=tmp_path / "feature_source",
        feature_fallback_source=tmp_path / "feature_fallback_source",
        replay_source=tmp_path / "replay_source",
        archive_root=tmp_path / "archive",
        trades_root=tmp_path / "trades",
        forecast_outcome_bridge_path=tmp_path / "bridge.json",
    )

    row = frame.iloc[0]
    assert bool(row["active_bundle_ready"]) is True
    assert row["bootstrap_status"] == "active_bundle_ready"
    assert row["recommended_next_action"] == "shadow_runtime_can_activate"
    assert summary["active_bundle_ready"] is True


def test_semantic_shadow_bundle_bootstrap_reports_bridge_adapter_required_when_archive_and_bridge_exist_without_key_overlap(
    tmp_path: Path,
):
    archive_root = tmp_path / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "replay_row_key": "archive_key_only",
                "decision_row_key": "decision_a",
                "entry_wait_decision": "wait_probe",
                "belief_state_v1": "{}",
                "barrier_state_v1": "{}",
                "forecast_effective_policy_v1": "{}",
            }
        ]
    ).to_parquet(archive_root / "entry_decisions.parquet", index=False)

    bridge_path = tmp_path / "forecast_bridge.json"
    bridge_path.write_text(
        json.dumps({"rows": [{"row_key": "bridge_key_only"}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    frame, summary = build_semantic_shadow_bundle_bootstrap(
        model_dir=tmp_path / "models" / "semantic_v1",
        models_root=tmp_path / "models",
        semantic_dataset_dir=tmp_path / "datasets",
        feature_source=tmp_path / "feature_source",
        feature_fallback_source=tmp_path / "feature_fallback_source",
        replay_source=tmp_path / "replay_source",
        archive_root=archive_root,
        trades_root=tmp_path / "trades",
        forecast_outcome_bridge_path=bridge_path,
        training_bridge_path=tmp_path / "semantic_shadow_training_bridge_adapter_latest.json",
    )

    row = frame.iloc[0]
    assert row["archive_entry_decision_parquet_count"] == 1
    assert bool(row["forecast_outcome_bridge_exists"]) is True
    assert row["forecast_bridge_archive_key_match_count"] == 0
    assert row["bootstrap_status"] == "bridge_adapter_required"
    assert row["recommended_next_action"] == "build_bridge_adapter_for_semantic_training"
    assert "forecast_bridge_archive_join_keys_missing" in summary["blocking_issues"]


def test_semantic_shadow_bundle_bootstrap_reports_training_bridge_ready_when_adapter_exists(tmp_path: Path):
    training_bridge_path = tmp_path / "semantic_shadow_training_bridge_adapter_latest.json"
    training_bridge_path.write_text(
        json.dumps(
            {
                "summary": {
                    "bridge_row_count": 10,
                    "matched_row_count": 8,
                    "match_rate": 0.8,
                    "training_bridge_ready": True,
                },
                "rows": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    frame, summary = build_semantic_shadow_bundle_bootstrap(
        model_dir=tmp_path / "models" / "semantic_v1",
        models_root=tmp_path / "models",
        semantic_dataset_dir=tmp_path / "datasets",
        feature_source=tmp_path / "feature_source",
        feature_fallback_source=tmp_path / "feature_fallback_source",
        replay_source=tmp_path / "replay_source",
        archive_root=tmp_path / "archive",
        trades_root=tmp_path / "trades",
        forecast_outcome_bridge_path=tmp_path / "bridge.json",
        training_bridge_path=training_bridge_path,
    )

    row = frame.iloc[0]
    assert bool(row["training_bridge_exists"]) is True
    assert row["training_bridge_row_count"] == 10
    assert row["training_bridge_matched_row_count"] == 8
    assert float(row["training_bridge_match_rate"]) == 0.8
    assert bool(row["training_bridge_ready"]) is True
    assert row["bootstrap_status"] == "training_bridge_ready"
    assert row["recommended_next_action"] == "train_semantic_bundle_from_bridge_adapter"
    assert summary["training_bridge_ready"] is True
