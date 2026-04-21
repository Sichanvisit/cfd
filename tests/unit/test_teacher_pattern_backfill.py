import pandas as pd

from backend.services.teacher_pattern_backfill import (
    BACKFILL_LABEL_REVIEW_STATUS,
    BACKFILL_LABEL_SOURCE,
    RELABEL_LABEL_SOURCE,
    apply_teacher_pattern_backfill,
    build_teacher_pattern_backfill_plan,
)
from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df


def _row(**overrides):
    row = {column: "" for column in TRADE_COLUMNS}
    row.update(
        {
            "ticket": "1",
            "symbol": "BTCUSD",
            "direction": "BUY",
            "entry_setup_id": "breakout_prepare_buy",
            "entry_session_name": "LONDON",
            "micro_breakout_readiness_state": "COILED_BREAKOUT",
            "micro_reversal_risk_state": "LOW_RISK",
            "micro_participation_state": "ACTIVE_PARTICIPATION",
            "micro_gap_context_state": "NO_GAP_CONTEXT",
            "micro_range_compression_ratio_20": 0.82,
            "micro_volume_burst_ratio_20": 2.1,
            "micro_volume_burst_decay_20": 0.18,
            "micro_same_color_run_current": 2,
            "micro_same_color_run_max_20": 3,
            "micro_doji_ratio_20": 0.24,
            "micro_swing_high_retest_count_20": 2,
            "micro_swing_low_retest_count_20": 2,
            "teacher_pattern_id": 0,
            "teacher_pattern_name": "",
            "teacher_pattern_secondary_id": 0,
            "teacher_pattern_secondary_name": "",
            "teacher_label_source": "",
            "teacher_label_review_status": "",
        }
    )
    row.update(overrides)
    return row


def test_teacher_pattern_backfill_plan_reports_recent_window_candidates():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _row(ticket="1", teacher_pattern_id=4, teacher_pattern_name="kept"),
                _row(ticket="2"),
                _row(ticket="3"),
            ],
            columns=TRADE_COLUMNS,
        )
    )

    report = build_teacher_pattern_backfill_plan(frame, recent_limit=2)

    assert report["total_rows"] == 3
    assert report["scoped_rows"] == 2
    assert report["already_labeled_rows"] == 0
    assert report["predicted_rows"] == 2
    assert 12 in report["predicted_distribution"]


def test_teacher_pattern_backfill_apply_preserves_existing_rows_and_sets_backfill_provenance():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _row(ticket="1", teacher_pattern_id=5, teacher_pattern_name="existing", teacher_label_source="runtime", teacher_label_review_status="reviewed"),
                _row(ticket="2"),
            ],
            columns=TRADE_COLUMNS,
        )
    )

    updated, report = apply_teacher_pattern_backfill(frame, recent_limit=10, overwrite_existing=False)

    first = updated.iloc[0]
    second = updated.iloc[1]
    assert int(pd.to_numeric(first["teacher_pattern_id"], errors="coerce") or 0) == 5
    assert first["teacher_label_source"] == "runtime"
    assert int(pd.to_numeric(second["teacher_pattern_id"], errors="coerce") or 0) == 12
    assert second["teacher_label_source"] == BACKFILL_LABEL_SOURCE
    assert second["teacher_label_review_status"] == BACKFILL_LABEL_REVIEW_STATUS
    assert report["updated_rows"] == 1
    assert report["skipped_labeled_rows"] == 1


def test_teacher_pattern_backfill_apply_only_touches_tail_window():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _row(ticket="1"),
                _row(ticket="2"),
                _row(ticket="3"),
            ],
            columns=TRADE_COLUMNS,
        )
    )

    updated, report = apply_teacher_pattern_backfill(frame, recent_limit=1)

    assert int(pd.to_numeric(updated.iloc[0]["teacher_pattern_id"], errors="coerce") or 0) == 0
    assert int(pd.to_numeric(updated.iloc[1]["teacher_pattern_id"], errors="coerce") or 0) == 0
    assert int(pd.to_numeric(updated.iloc[2]["teacher_pattern_id"], errors="coerce") or 0) == 12
    assert report["updated_rows"] == 1


def test_teacher_pattern_backfill_overwrite_existing_marks_tuned_relabel_provenance():
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                    _row(
                        ticket="1",
                        direction="BUY",
                        entry_setup_id="range_lower_reversal_buy",
                        entry_session_name="",
                        micro_breakout_readiness_state="",
                        micro_participation_state="THIN_PARTICIPATION",
                        micro_reversal_risk_state="HIGH_RISK",
                        micro_doji_ratio_20=0.0,
                        micro_same_color_run_current=1,
                        micro_same_color_run_max_20=1,
                        micro_range_compression_ratio_20=0.0,
                        micro_volume_burst_ratio_20=0.84,
                        micro_volume_burst_decay_20=0.0,
                        micro_swing_high_retest_count_20=0,
                        micro_swing_low_retest_count_20=0,
                        teacher_pattern_id=1,
                        teacher_pattern_name="old",
                    teacher_label_source="rule_v2_backfill",
                    teacher_label_review_status="backfilled_unreviewed",
                ),
            ],
            columns=TRADE_COLUMNS,
        )
    )

    updated, report = apply_teacher_pattern_backfill(frame, recent_limit=10, overwrite_existing=True)

    row = updated.iloc[0]
    assert int(pd.to_numeric(row["teacher_pattern_id"], errors="coerce") or 0) == 5
    assert row["teacher_label_source"] == RELABEL_LABEL_SOURCE
    assert report["relabeled_rows"] == 1
