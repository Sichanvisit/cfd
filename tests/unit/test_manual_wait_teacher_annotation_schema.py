import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    MANUAL_WAIT_TEACHER_ANNOTATION_COLUMNS,
    MANUAL_WAIT_TEACHER_LABEL_VERSION,
    manual_wait_teacher_defaults,
    normalize_manual_wait_teacher_annotation_df,
)


def test_manual_wait_teacher_defaults_good_wait_better_entry() -> None:
    defaults = manual_wait_teacher_defaults("good_wait_better_entry")

    assert defaults["manual_wait_teacher_polarity"] == "good"
    assert defaults["manual_wait_teacher_family"] == "timing_improvement"
    assert defaults["manual_wait_teacher_subtype"] == "better_entry_after_wait"
    assert defaults["manual_wait_teacher_usage_bucket"] == "usable"


def test_manual_wait_teacher_defaults_bad_wait_no_timing_edge() -> None:
    defaults = manual_wait_teacher_defaults("bad_wait_no_timing_edge")

    assert defaults["manual_wait_teacher_polarity"] == "bad"
    assert defaults["manual_wait_teacher_family"] == "failed_wait"
    assert defaults["manual_wait_teacher_subtype"] == "wait_without_timing_edge"
    assert defaults["manual_wait_teacher_usage_bucket"] == "diagnostic"


def test_normalize_manual_wait_teacher_annotation_df_supports_legacy_alias_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "annotation_id": "btc_box_001",
                "symbol": "BTCUSD",
                "timeframe": "M15",
                "side": "BUY",
                "box_regime_scope": "recent_range_box",
                "anchor_time": "2026-04-04T10:00:00+09:00",
                "annotated_entry_time": "2026-04-04T10:15:00+09:00",
                "annotated_exit_time": "2026-04-04T11:20:00+09:00",
                "manual_wait_teacher_label": "GOOD_WAIT_BETTER_ENTRY",
                "manual_wait_teacher_confidence": "HIGH",
                "anchor_price": "100.5",
                "annotated_entry_price": "99.8",
                "annotated_exit_price": "101.3",
                "revisit_flag": "1",
            }
        ]
    )

    normalized = normalize_manual_wait_teacher_annotation_df(frame)
    row = normalized.iloc[0].to_dict()

    assert list(normalized.columns) == MANUAL_WAIT_TEACHER_ANNOTATION_COLUMNS
    assert row["annotation_id"] == "btc_box_001"
    assert row["episode_id"] == "btc_box_001"
    assert row["anchor_side"] == "BUY"
    assert row["ideal_entry_time"] == "2026-04-04T10:15:00+09:00"
    assert row["ideal_exit_time"] == "2026-04-04T11:20:00+09:00"
    assert row["manual_wait_teacher_label"] == "good_wait_better_entry"
    assert row["manual_wait_teacher_confidence"] == "high"
    assert row["manual_wait_teacher_polarity"] == "good"
    assert row["manual_wait_teacher_family"] == "timing_improvement"
    assert row["manual_wait_teacher_subtype"] == "better_entry_after_wait"
    assert row["manual_wait_teacher_usage_bucket"] == "usable"
    assert row["annotation_source"] == "chart_annotated"
    assert row["review_status"] == "pending"
    assert row["manual_teacher_confidence"] == "high"
    assert row["label_version"] == MANUAL_WAIT_TEACHER_LABEL_VERSION
    assert row["anchor_price"] == 100.5
    assert row["ideal_entry_price"] == 99.8
    assert row["ideal_exit_price"] == 101.3
    assert row["revisit_flag"] == 1


def test_normalize_manual_wait_teacher_annotation_df_preserves_episode_fields() -> None:
    frame = pd.DataFrame(
        [
            {
                "annotation_id": "",
                "episode_id": "btc_box_episode_002",
                "symbol": "BTCUSD",
                "timeframe": "M15",
                "anchor_side": "sell",
                "scene_id": "btc_range_box_20260404",
                "chart_context": "recent_box_upper_reject",
                "box_regime_scope": "recent_range_box",
                "anchor_time": "2026-04-04T12:30:00+09:00",
                "anchor_price": "102.4",
                "ideal_entry_time": "2026-04-04T12:45:00+09:00",
                "ideal_entry_price": "102.1",
                "manual_entry_teacher_label": "GOOD_ENTRY_AFTER_WAIT",
                "manual_entry_teacher_confidence": "Medium",
                "manual_wait_teacher_label": "good_wait_reversal_escape",
                "manual_wait_teacher_confidence": "medium",
                "ideal_exit_time": "2026-04-04T13:05:00+09:00",
                "ideal_exit_price": "101.3",
                "manual_exit_teacher_label": "GOOD_EXIT_REVERSAL_ESCAPE",
                "manual_exit_teacher_confidence": "HIGH",
                "annotation_author": "bhs33",
                "annotation_created_at": "2026-04-06T09:10:00+09:00",
                "manual_teacher_confidence": "",
            }
        ]
    )

    normalized = normalize_manual_wait_teacher_annotation_df(frame)
    row = normalized.iloc[0].to_dict()

    assert row["annotation_id"] == "btc_box_episode_002"
    assert row["episode_id"] == "btc_box_episode_002"
    assert row["anchor_side"] == "SELL"
    assert row["manual_entry_teacher_label"] == "good_entry_after_wait"
    assert row["manual_entry_teacher_confidence"] == "medium"
    assert row["manual_exit_teacher_label"] == "good_exit_reversal_escape"
    assert row["manual_exit_teacher_confidence"] == "high"
    assert row["manual_teacher_confidence"] == "medium"
