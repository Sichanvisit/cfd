from pathlib import Path
import json

from backend.services.semantic_shadow_training_corpus import build_semantic_shadow_training_corpus


def test_build_semantic_shadow_training_corpus_supports_current_only_sources(tmp_path: Path):
    current_bridge_path = tmp_path / "forecast_state25_outcome_bridge_latest.json"
    current_bridge_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "symbol": "BTCUSD",
                        "signal_bar_ts": 1775526000,
                        "row_key": "shadow_row_key_1",
                        "bridge_quality_status": "full_outcome_bridge",
                        "entry_wait_quality_label": "neutral_wait",
                        "economic_target_summary": {
                            "learning_total_label": "positive",
                            "learning_total_score": 0.75,
                            "loss_quality_label": "non_loss",
                            "signed_exit_score": 5.0,
                            "profit": 2.5,
                        },
                        "outcome_label_compact_summary_v1": {
                            "transition_label_status": "READY",
                            "management_label_status": "READY",
                        },
                        "state25_runtime_hint_v1": {
                            "scene_family": "trend_pullback",
                            "wait_bias_hint": "wait",
                        },
                        "forecast_runtime_summary_v1": {
                            "decision_hint": "BALANCED",
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    frame, summary, rows = build_semantic_shadow_training_corpus(
        current_bridge_path=current_bridge_path,
        legacy_entry_paths=(),
        legacy_output_dir=tmp_path / "legacy_reports",
    )

    assert len(frame) == 1
    assert len(rows) == 1
    row = frame.iloc[0]
    assert row["symbol"] == "BTCUSD"
    assert row["bridge_quality_status"] == "full_outcome_bridge"
    assert row["learning_total_label"] == "positive"
    assert summary["row_count"] == 1
    assert summary["source_count"] == 1
    assert summary["bridge_quality_status_counts"]["full_outcome_bridge"] == 1
