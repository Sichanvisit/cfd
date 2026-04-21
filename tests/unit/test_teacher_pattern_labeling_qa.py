import pandas as pd

from backend.services.teacher_pattern_labeling_qa import build_teacher_pattern_labeling_qa_report


def _base_row(**overrides):
    row = {
        "ticket": "1",
        "symbol": "BTCUSD",
        "teacher_pattern_id": 12,
        "teacher_pattern_secondary_id": 23,
        "teacher_pattern_group": "C",
        "teacher_entry_bias": "breakout",
        "teacher_wait_bias": "short_wait",
        "teacher_exit_bias": "hold_runner",
        "teacher_label_confidence": 0.82,
        "teacher_lookback_bars": 20,
        "teacher_label_source": "rule_v2_draft",
        "teacher_label_version": "state25_v2",
        "teacher_label_review_status": "unreviewed",
    }
    row.update(overrides)
    return row


def test_teacher_pattern_labeling_qa_report_builds_watchlist_distribution():
    frame = pd.DataFrame(
        [
            _base_row(ticket="1", symbol="BTCUSD", teacher_pattern_id=12, teacher_pattern_secondary_id=23, teacher_pattern_group="C"),
            _base_row(ticket="2", symbol="XAUUSD", teacher_pattern_id=5, teacher_pattern_secondary_id=10, teacher_pattern_group="D", teacher_entry_bias="fade", teacher_exit_bias="range_take"),
            _base_row(ticket="3", symbol="NAS100", teacher_pattern_id=16, teacher_pattern_secondary_id=2, teacher_pattern_group="D", teacher_entry_bias="fade", teacher_exit_bias="fast_cut"),
            _base_row(ticket="4", symbol="BTCUSD", teacher_pattern_id=4, teacher_pattern_secondary_id=0, teacher_pattern_group="B", teacher_entry_bias="confirm", teacher_wait_bias="hold", teacher_exit_bias="trail", teacher_label_confidence=0.91),
        ]
    )

    report = build_teacher_pattern_labeling_qa_report(frame, rare_threshold=0.05, review_fraction=0.25)

    assert report["gate_status"] == "PASS_WITH_WARNINGS"
    assert report["total_rows"] == 4
    assert report["labeled_rows"] == 4
    assert report["watchlist_pairs"]["12-23"]["count"] == 1
    assert report["watchlist_pairs"]["5-10"]["count"] == 1
    assert report["watchlist_pairs"]["2-16"]["count"] == 1
    assert report["distribution"]["primary_patterns"][12]["count"] == 1
    assert report["distribution"]["entry_bias"]["fade"]["count"] == 2
    assert report["low_confidence_review"]["target_count"] == 1


def test_teacher_pattern_labeling_qa_report_flags_rare_watch_patterns():
    rows = [_base_row(ticket=str(index), teacher_pattern_id=4, teacher_pattern_secondary_id=0, teacher_pattern_group="B", teacher_label_confidence=0.80 + (index * 0.01)) for index in range(1, 10)]
    rows.append(
        _base_row(
            ticket="99",
            teacher_pattern_id=17,
            teacher_pattern_secondary_id=0,
            teacher_pattern_group="C",
            teacher_entry_bias="breakout",
            teacher_wait_bias="tight_wait",
            teacher_exit_bias="fast_cut",
            teacher_label_confidence=0.31,
        )
    )
    frame = pd.DataFrame(rows)

    report = build_teacher_pattern_labeling_qa_report(frame, rare_threshold=0.15, review_fraction=0.20)

    rare_ids = {item["pattern_id"] for item in report["rare_pattern_warnings"]}
    assert 17 in rare_ids
    assert report["low_confidence_review"]["target_count"] == 2
    assert report["warnings"].count("rare_pattern_watch_triggered") == 1


def test_teacher_pattern_labeling_qa_report_fails_on_missing_provenance():
    frame = pd.DataFrame(
        [
            _base_row(
                ticket="1",
                teacher_pattern_id=21,
                teacher_pattern_secondary_id=0,
                teacher_pattern_group="D",
                teacher_label_source="",
                teacher_lookback_bars=19,
            )
        ]
    )

    report = build_teacher_pattern_labeling_qa_report(frame)

    assert report["gate_status"] == "FAIL"
    assert "missing_label_source" in report["failures"]
    assert "invalid_teacher_lookback" in report["failures"]
    assert report["provenance"]["missing_source_count"] == 1
    assert report["provenance"]["invalid_lookback_count"] == 1
