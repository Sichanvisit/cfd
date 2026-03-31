import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_semantic_v1_preview_audit.py"
spec = importlib.util.spec_from_file_location("run_semantic_v1_preview_audit", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_metrics_payload() -> dict:
    base_metrics = {
        "accuracy": 0.63,
        "auc": 0.61,
        "feature_columns": ["signal_strength", "signal_direction"],
        "split_health_status": "healthy",
        "validation_class_balance": {"1": 40, "0": 35},
        "dataset_source_generation": "legacy",
        "dataset_feature_tier_policy": {
            "semantic_input_pack": "enabled",
            "trace_quality_pack": "observed_only",
        },
        "dataset_feature_tier_summary": {
            "trace_quality_pack": {
                "mode": "observed_only",
                "candidate_count": 6,
                "retained_count": 2,
                "dropped_count": 4,
                "observed_only_dropped_count": 4,
            }
        },
        "dataset_observed_only_dropped_feature_columns": [
            "signal_age_sec",
            "probe_scene_id",
            "probe_pair_gap",
        ],
        "dataset_dropped_feature_columns": ["signal_age_sec"],
        "training_dropped_feature_columns": ["probe_scene_id"],
    }
    return {
        "timing_metrics": dict(base_metrics),
        "entry_quality_metrics": {**base_metrics, "auc": 0.59, "split_health_status": "warning"},
        "exit_management_metrics": {**base_metrics, "auc": 0.82, "split_health_status": "warning"},
    }


def _make_build_manifest(tmp_path: Path) -> Path:
    feature_path = tmp_path / "feature.parquet"
    replay_path = tmp_path / "replay.jsonl"
    pd.DataFrame(
        [
            {"decision_row_key": "rk1", "replay_row_key": "rk1"},
            {"decision_row_key": "rk2", "replay_row_key": "rk2"},
            {"decision_row_key": "rk3", "replay_row_key": "rk3"},
        ]
    ).to_parquet(feature_path, index=False)
    replay_path.write_text(
        "\n".join(
            [
                json.dumps({"decision_row_key": "rk1", "replay_row_key": "rk1"}),
                json.dumps({"decision_row_key": "rk2", "replay_row_key": "rk2"}),
                json.dumps({"decision_row_key": "rk3", "replay_row_key": "rk3"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "build_manifest.json"
    _write_json(
        manifest_path,
        {
            "joined_rows": 3,
            "feature_files": [str(feature_path)],
            "replay_files": [str(replay_path)],
        },
    )
    return manifest_path


def test_build_preview_audit_surfaces_feature_tier_and_shadow_compare(tmp_path):
    metrics_path = tmp_path / "metrics.json"
    manifest_path = _make_build_manifest(tmp_path)
    shadow_path = tmp_path / "semantic_shadow_compare_report.json"
    _write_json(metrics_path, _make_metrics_payload())
    _write_json(
        shadow_path,
        {
            "summary": {
                "rows_total": 120,
                "shadow_available_rows": 90,
                "baseline_entered_rows": 30,
                "semantic_enter_rows": 28,
                "scorable_shadow_rows": 64,
                "semantic_precision": 0.62,
                "semantic_false_positive_rate": 0.18,
            },
            "compare_label_counts": {"agree_enter": 18, "semantic_earlier_enter": 7},
            "trace_quality_counts": {"clean": 75, "degraded": 15},
            "candidate_threshold_table": [
                {
                    "timing_threshold": 0.55,
                    "entry_quality_threshold": 0.55,
                    "candidate_score": 0.51,
                    "precision": 0.64,
                    "false_positive_rate": 0.18,
                    "earlier_count": 7,
                    "later_block_count": 3,
                }
            ],
        },
    )

    report = module.build_preview_audit(
        metrics_path=metrics_path,
        build_manifest_path=manifest_path,
        shadow_compare_path=shadow_path,
    )

    assert report["report_version"] == "semantic_preview_audit_v2"
    assert report["join_coverage"]["coverage_ratio"] == 1.0
    assert report["targets"]["timing"]["feature_tier"]["source_generation"] == "legacy"
    assert report["targets"]["timing"]["feature_tier"]["observed_only_dropped_feature_count"] == 3
    assert report["shadow_compare"]["status"] == "healthy"
    assert report["shadow_compare"]["compare_label_counts"]["semantic_earlier_enter"] == 7
    assert report["promotion_gate"]["shadow_compare_ready"] is True
    assert report["promotion_gate"]["shadow_compare_status"] == "healthy"


def test_build_preview_audit_blocks_when_shadow_compare_report_is_missing(tmp_path):
    metrics_path = tmp_path / "metrics.json"
    manifest_path = _make_build_manifest(tmp_path)
    _write_json(metrics_path, _make_metrics_payload())

    report = module.build_preview_audit(
        metrics_path=metrics_path,
        build_manifest_path=manifest_path,
        shadow_compare_path=None,
    )

    assert report["shadow_compare"]["status"] == "missing"
    assert "shadow_compare_report_missing" in report["promotion_gate"]["blocking_issues"]
    assert report["promotion_gate"]["shadow_compare_ready"] is False
