import pandas as pd

from backend.services.teacher_pattern_asset_calibration import (
    build_teacher_pattern_asset_calibration_report,
)


def _row(**overrides):
    row = {
        "symbol": "BTCUSD",
        "teacher_pattern_id": 12,
        "teacher_pattern_group": "C",
        "teacher_pattern_secondary_id": 23,
        "teacher_entry_bias": "breakout",
        "teacher_wait_bias": "short_wait",
        "teacher_exit_bias": "hold_runner",
        "teacher_label_confidence": 0.82,
        "entry_atr_ratio": 1.4,
        "regime_volatility_ratio": 0.7,
        "micro_body_size_pct_20": 0.18,
        "micro_doji_ratio_20": 0.11,
        "micro_range_compression_ratio_20": 0.72,
        "micro_volume_burst_ratio_20": 2.9,
        "micro_volume_burst_decay_20": 0.28,
    }
    row.update(overrides)
    return row


def test_teacher_pattern_asset_calibration_report_builds_per_symbol_summaries():
    frame = pd.DataFrame(
        [
            _row(symbol="BTCUSD", teacher_pattern_id=12, teacher_pattern_group="C", entry_atr_ratio=1.6),
            _row(symbol="BTCUSD", teacher_pattern_id=23, teacher_pattern_group="A", teacher_pattern_secondary_id=12, teacher_label_confidence=0.65, micro_range_compression_ratio_20=0.81),
            _row(symbol="XAUUSD", teacher_pattern_id=14, teacher_pattern_group="A", teacher_pattern_secondary_id=0, teacher_entry_bias="breakout", teacher_wait_bias="short_wait", teacher_exit_bias="range_take", entry_atr_ratio=0.9),
            _row(symbol="NAS100", teacher_pattern_id=9, teacher_pattern_group="E", teacher_pattern_secondary_id=0, teacher_entry_bias="early", teacher_wait_bias="hold", teacher_exit_bias="hold_runner", entry_atr_ratio=1.2),
        ]
    )

    report = build_teacher_pattern_asset_calibration_report(frame, min_rows_per_symbol=1)

    assert report["labeled_rows"] == 4
    assert report["symbols_present"] == ["BTCUSD", "XAUUSD", "NAS100"]
    assert report["overall_watchlist_pairs"]["12-23"] == 2
    assert report["symbol_reports"]["BTCUSD"]["rows"] == 2
    assert report["symbol_reports"]["BTCUSD"]["entry_atr_ratio_summary"]["median"] == 1.5
    assert report["symbol_reports"]["BTCUSD"]["watchlist_pairs"]["12-23"] == 2
    assert report["symbol_reports"]["XAUUSD"]["primary_patterns"][14]["count"] == 1


def test_teacher_pattern_asset_calibration_report_warns_on_missing_and_skewed_symbols():
    frame = pd.DataFrame(
        [
            _row(symbol="BTCUSD", teacher_pattern_id=1, teacher_pattern_group="A", teacher_pattern_secondary_id=0, teacher_entry_bias="avoid", teacher_wait_bias="wait", teacher_exit_bias="range_take"),
            _row(symbol="BTCUSD", teacher_pattern_id=14, teacher_pattern_group="A", teacher_pattern_secondary_id=0, teacher_entry_bias="breakout", teacher_wait_bias="short_wait", teacher_exit_bias="range_take"),
        ]
    )

    report = build_teacher_pattern_asset_calibration_report(frame, min_rows_per_symbol=3)

    assert "missing_symbol_seed:XAUUSD" in report["warnings"]
    assert "missing_symbol_seed:NAS100" in report["warnings"]
    assert "insufficient_symbol_seed:BTCUSD" in report["warnings"]
    assert "group_skew:BTCUSD:A" in report["warnings"]
    assert report["symbol_reports"]["XAUUSD"]["warnings"] == ["no_labeled_rows"]


def test_teacher_pattern_asset_calibration_report_flags_flat_atr_and_zero_micro_payload():
    frame = pd.DataFrame(
        [
            _row(
                symbol="BTCUSD",
                teacher_pattern_id=1,
                teacher_pattern_group="A",
                teacher_pattern_secondary_id=0,
                entry_atr_ratio=1.0,
                micro_body_size_pct_20=0.0,
                micro_doji_ratio_20=0.0,
                micro_range_compression_ratio_20=0.0,
                micro_volume_burst_ratio_20=0.0,
                micro_volume_burst_decay_20=0.0,
            ),
            _row(
                symbol="BTCUSD",
                teacher_pattern_id=14,
                teacher_pattern_group="A",
                teacher_pattern_secondary_id=0,
                entry_atr_ratio=1.0,
                micro_body_size_pct_20=0.0,
                micro_doji_ratio_20=0.0,
                micro_range_compression_ratio_20=0.0,
                micro_volume_burst_ratio_20=0.0,
                micro_volume_burst_decay_20=0.0,
            ),
        ]
    )

    report = build_teacher_pattern_asset_calibration_report(frame, min_rows_per_symbol=1)

    assert "entry_atr_ratio_flat:BTCUSD" in report["warnings"]
    assert "micro_payload_zero:BTCUSD" in report["warnings"]
    assert "entry_atr_ratio_flat" in report["symbol_reports"]["BTCUSD"]["warnings"]
    assert "micro_payload_zero" in report["symbol_reports"]["BTCUSD"]["warnings"]
