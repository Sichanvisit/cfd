from pathlib import Path
import json

import pandas as pd

from backend.services.semantic_shadow_training_bridge_adapter import (
    build_semantic_shadow_training_bridge_adapter,
)


def test_training_bridge_adapter_matches_by_normalized_key_and_nearest_time(tmp_path: Path):
    archive_root = tmp_path / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "replay_row_key": "replay_dataset_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1775290500.0|action=|setup_id=|ticket=0|decision_time=1775279835.0|observe_reason=middle_sr_anchor_required_observe|probe_state=BLOCKED|blocked_by=middle_sr_anchor_guard|action_none_reason=observe_state_wait",
                "decision_row_key": "decision_a",
                "time": "2026-04-04T14:17:15",
                "signal_bar_ts": 1775290500,
                "symbol": "BTCUSD",
            }
        ]
    ).to_parquet(archive_root / "entry_decisions.parquet", index=False)

    bridge_path = tmp_path / "bridge.json"
    bridge_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "row_key": "replay_dataset_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1775290500.0|action=|setup_id=|ticket=0|decision_time=2026-04-04T14:17:15|observe_reason=middle_sr_anchor_required_observe|probe_state=BLOCKED|blocked_by=middle_sr_anchor_guard|action_none_reason=observe_state_wait",
                        "signal_bar_ts": 1775290500,
                        "symbol": "BTCUSD",
                        "bridge_quality_status": "partial_outcome_bridge",
                        "entry_wait_quality_label": "insufficient_evidence",
                        "economic_target_summary": {
                            "learning_total_label": "positive",
                            "learning_total_score": 0.4,
                            "loss_quality_label": "non_loss",
                            "signed_exit_score": 90.0,
                        },
                        "outcome_label_compact_summary_v1": {
                            "transition_label_status": "INSUFFICIENT_FUTURE_BARS",
                            "management_label_status": "INSUFFICIENT_FUTURE_BARS",
                        },
                        "state25_runtime_hint_v1": {
                            "scene_family": "pattern_1",
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

    frame, summary = build_semantic_shadow_training_bridge_adapter(
        forecast_outcome_bridge_path=bridge_path,
        archive_root=archive_root,
        max_gap_seconds=180.0,
    )

    row = frame.iloc[0]
    assert row["match_status"] == "matched"
    assert row["match_strategy"] == "normalized_key_nearest_time"
    assert row["candidate_count_for_key"] == 1
    assert float(row["match_gap_seconds"]) == 0.0
    assert summary["exact_match_count"] == 0
    assert summary["normalized_nearest_time_match_count"] == 1
    assert summary["matched_row_count"] == 1
    assert summary["training_bridge_ready"] is True


def test_training_bridge_adapter_marks_gap_exceeds_limit_when_nearest_time_is_too_far(tmp_path: Path):
    archive_root = tmp_path / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "replay_row_key": "replay_dataset_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1775290500.0|action=|setup_id=|ticket=0|decision_time=1775280300.0|observe_reason=middle_sr_anchor_required_observe|probe_state=BLOCKED|blocked_by=middle_sr_anchor_guard|action_none_reason=observe_state_wait",
                "decision_row_key": "decision_b",
                "time": "2026-04-04T14:25:00",
                "signal_bar_ts": 1775290500,
                "symbol": "BTCUSD",
            }
        ]
    ).to_parquet(archive_root / "entry_decisions.parquet", index=False)

    bridge_path = tmp_path / "bridge.json"
    bridge_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "row_key": "replay_dataset_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1775290500.0|action=|setup_id=|ticket=0|decision_time=2026-04-04T14:17:15|observe_reason=middle_sr_anchor_required_observe|probe_state=BLOCKED|blocked_by=middle_sr_anchor_guard|action_none_reason=observe_state_wait",
                        "signal_bar_ts": 1775290500,
                        "symbol": "BTCUSD",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    frame, summary = build_semantic_shadow_training_bridge_adapter(
        forecast_outcome_bridge_path=bridge_path,
        archive_root=archive_root,
        max_gap_seconds=180.0,
    )

    row = frame.iloc[0]
    assert row["match_status"] == "gap_exceeds_limit"
    assert row["match_strategy"] == "normalized_key_nearest_time"
    assert float(row["match_gap_seconds"]) > 180.0
    assert summary["matched_row_count"] == 0
    assert summary["gap_exceeds_limit_count"] == 1
    assert summary["training_bridge_ready"] is False
