import pandas as pd

from backend.services.manual_wait_teacher_seed_enrichment import (
    apply_manual_wait_teacher_seed_enrichment,
    build_manual_wait_teacher_seed_enrichment_plan,
)


def test_manual_wait_teacher_seed_enrichment_matches_episode_and_backfills_wait_fields() -> None:
    closed_history = pd.DataFrame(
        [
            {
                "ticket": 101,
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-04-04 10:00:00",
                "close_time": "2026-04-04 10:50:00",
                "status": "CLOSED",
            }
        ]
    )
    annotations = pd.DataFrame(
        [
            {
                "annotation_id": "btc_box_001",
                "episode_id": "btc_box_episode_001",
                "symbol": "BTCUSD",
                "timeframe": "M15",
                "anchor_side": "BUY",
                "box_regime_scope": "recent_range_box",
                "anchor_time": "2026-04-04T09:45:00+09:00",
                "anchor_price": 100.0,
                "ideal_entry_time": "2026-04-04T10:00:00+09:00",
                "ideal_entry_price": 99.4,
                "ideal_exit_time": "2026-04-04T10:50:00+09:00",
                "ideal_exit_price": 101.2,
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "high",
                "wait_outcome_reason_summary": "better_entry_plus_continuation",
                "annotation_note": "Manual BTC box sample.",
            }
        ]
    )

    updated, report = apply_manual_wait_teacher_seed_enrichment(
        closed_history,
        annotations=annotations,
    )

    assert report["matched_trade_rows"] == 1
    assert report["matched_annotations"] == 1
    assert report["updated_rows"] == 1
    row = updated.iloc[0].to_dict()
    assert row["manual_wait_teacher_episode_id"] == "btc_box_episode_001"
    assert row["manual_wait_teacher_label"] == "good_wait_better_entry"
    assert row["manual_wait_teacher_family"] == "timing_improvement"
    assert row["manual_wait_teacher_anchor_time"] == "2026-04-04T09:45:00+09:00"
    assert row["manual_wait_teacher_entry_time"] == "2026-04-04T10:00:00+09:00"
    assert row["manual_wait_teacher_exit_time"] == "2026-04-04T10:50:00+09:00"
    assert row["manual_wait_teacher_reason"] == "better_entry_plus_continuation"


def test_manual_wait_teacher_seed_enrichment_skips_existing_rows_without_overwrite() -> None:
    closed_history = pd.DataFrame(
        [
            {
                "ticket": 101,
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-04-04 10:00:00",
                "close_time": "2026-04-04 10:50:00",
                "status": "CLOSED",
                "manual_wait_teacher_label": "bad_wait_no_timing_edge",
                "manual_wait_teacher_episode_id": "existing_episode",
            }
        ]
    )
    annotations = pd.DataFrame(
        [
            {
                "annotation_id": "btc_box_001",
                "episode_id": "btc_box_episode_001",
                "symbol": "BTCUSD",
                "timeframe": "M15",
                "anchor_side": "BUY",
                "anchor_time": "2026-04-04T09:45:00+09:00",
                "anchor_price": 100.0,
                "ideal_entry_time": "2026-04-04T10:00:00+09:00",
                "ideal_entry_price": 99.4,
                "ideal_exit_time": "2026-04-04T10:50:00+09:00",
                "ideal_exit_price": 101.2,
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "high",
            }
        ]
    )

    updated, report = apply_manual_wait_teacher_seed_enrichment(
        closed_history,
        annotations=annotations,
        overwrite_existing=False,
    )

    assert report["skipped_existing_rows"] == 1
    assert report["updated_rows"] == 0
    row = updated.iloc[0].to_dict()
    assert row["manual_wait_teacher_label"] == "bad_wait_no_timing_edge"
    assert row["manual_wait_teacher_episode_id"] == "existing_episode"


def test_manual_wait_teacher_seed_enrichment_plan_reports_time_gap_miss() -> None:
    closed_history = pd.DataFrame(
        [
            {
                "ticket": 101,
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-04-04 10:00:00",
                "close_time": "2026-04-04 10:50:00",
                "status": "CLOSED",
            }
        ]
    )
    annotations = pd.DataFrame(
        [
            {
                "annotation_id": "btc_box_far",
                "episode_id": "btc_box_far",
                "symbol": "BTCUSD",
                "timeframe": "M15",
                "anchor_side": "BUY",
                "anchor_time": "2026-04-05T09:45:00+09:00",
                "anchor_price": 100.0,
                "ideal_entry_time": "2026-04-05T10:00:00+09:00",
                "ideal_entry_price": 99.4,
                "ideal_exit_time": "2026-04-05T10:50:00+09:00",
                "ideal_exit_price": 101.2,
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "high",
            }
        ]
    )

    report = build_manual_wait_teacher_seed_enrichment_plan(
        closed_history,
        annotations=annotations,
        max_entry_time_gap_minutes=120,
    )

    assert report["matched_annotations"] == 0
    assert report["unmatched_annotations"] == 1
    assert report["matched_trade_rows"] == 0
    assert report["match_reason_counts"]["time_gap_exceeds_limit"] == 1
