import pandas as pd

from backend.services.teacher_pattern_full_labeling_qa import build_teacher_pattern_full_labeling_qa_report


def _row(**overrides):
    row = {
        "symbol": "BTCUSD",
        "teacher_pattern_id": 12,
        "teacher_pattern_secondary_id": 23,
        "teacher_pattern_group": "C",
        "teacher_entry_bias": "breakout",
        "teacher_wait_bias": "short_wait",
        "teacher_exit_bias": "hold_runner",
        "teacher_label_confidence": 0.82,
        "teacher_label_source": "rule_v2_backfill",
        "teacher_label_review_status": "backfilled_unreviewed",
        "teacher_lookback_bars": 20,
        "teacher_label_version": "state25_v2",
    }
    row.update(overrides)
    return row


def test_full_labeling_qa_report_marks_shortfall_and_missing_patterns():
    frame = pd.DataFrame(
        [
            _row(symbol="BTCUSD", teacher_pattern_id=1, teacher_pattern_secondary_id=0, teacher_pattern_group="A"),
            _row(symbol="XAUUSD", teacher_pattern_id=14, teacher_pattern_secondary_id=0, teacher_pattern_group="A"),
            _row(symbol="NAS100", teacher_pattern_id=9, teacher_pattern_secondary_id=0, teacher_pattern_group="E"),
        ]
    )

    report = build_teacher_pattern_full_labeling_qa_report(frame, min_labeled_rows=10)

    assert report["full_qa_readiness"]["full_qa_ready"] is False
    assert report["full_qa_readiness"]["shortfall_rows"] == 7
    assert 12 in report["pattern_coverage"]["missing_primary_ids"]
    assert "full_qa_seed_shortfall" in report["warnings"]
    assert "missing_primary_patterns_present" in report["warnings"]


def test_full_labeling_qa_report_tracks_pair_concentration_and_group_skew():
    frame = pd.DataFrame(
        [_row(symbol="BTCUSD", teacher_pattern_id=12, teacher_pattern_secondary_id=23, teacher_pattern_group="C") for _ in range(7)]
        + [_row(symbol="XAUUSD", teacher_pattern_id=12, teacher_pattern_secondary_id=23, teacher_pattern_group="C")]
        + [_row(symbol="NAS100", teacher_pattern_id=5, teacher_pattern_secondary_id=10, teacher_pattern_group="D")]
    )

    report = build_teacher_pattern_full_labeling_qa_report(
        frame,
        min_labeled_rows=5,
        group_skew_threshold=0.70,
        pair_ratio_limit=0.50,
    )

    assert report["full_qa_readiness"]["full_qa_ready"] is True
    assert report["confusion_proxy_summary"]["watchlist_pairs"]["12-23"]["count"] == 8
    assert report["confusion_proxy_summary"]["pair_concentration_warnings"][0]["pair"] == "12-23"
    assert "overall_group_skew:C" in report["warnings"]
    assert "symbol_group_skew:BTCUSD:C" in report["warnings"]


def test_full_labeling_qa_report_breaks_down_symbol_primary_patterns():
    frame = pd.DataFrame(
        [
            _row(symbol="BTCUSD", teacher_pattern_id=1, teacher_pattern_secondary_id=0, teacher_pattern_group="A"),
            _row(symbol="BTCUSD", teacher_pattern_id=1, teacher_pattern_secondary_id=0, teacher_pattern_group="A"),
            _row(symbol="XAUUSD", teacher_pattern_id=14, teacher_pattern_secondary_id=0, teacher_pattern_group="A"),
            _row(symbol="NAS100", teacher_pattern_id=5, teacher_pattern_secondary_id=10, teacher_pattern_group="D"),
        ]
    )

    report = build_teacher_pattern_full_labeling_qa_report(frame, min_labeled_rows=4)

    assert report["symbol_reports"]["BTCUSD"]["rows"] == 2
    assert report["symbol_reports"]["BTCUSD"]["primary_patterns_top"]["1"]["count"] == 2
    assert report["symbol_reports"]["XAUUSD"]["primary_patterns_top"]["14"]["count"] == 1
    assert report["group_distribution"]["A"]["count"] == 3
