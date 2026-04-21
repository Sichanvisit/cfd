import json
from pathlib import Path

import pandas as pd

from backend.services.teacher_pattern_detail_micro_backfill import (
    DETAIL_BACKFILL_LABEL_REVIEW_STATUS,
    DETAIL_BACKFILL_LABEL_SOURCE,
    apply_teacher_pattern_detail_micro_backfill,
    build_teacher_pattern_detail_micro_backfill_plan,
)
from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df


def _row(**overrides):
    row = {column: "" for column in TRADE_COLUMNS}
    row.update(
        {
            "ticket": "1",
            "symbol": "BTCUSD",
            "direction": "BUY",
            "decision_row_key": "decision-1",
            "runtime_snapshot_key": "runtime-1",
            "trade_link_key": "trade-1",
            "entry_setup_id": "",
            "entry_session_name": "",
            "entry_atr_ratio": 1.0,
            "micro_breakout_readiness_state": "",
            "micro_reversal_risk_state": "",
            "micro_participation_state": "",
            "micro_gap_context_state": "",
            "micro_body_size_pct_20": 0.0,
            "micro_doji_ratio_20": 0.0,
            "micro_same_color_run_current": 0,
            "micro_same_color_run_max_20": 0,
            "micro_range_compression_ratio_20": 0.0,
            "micro_volume_burst_ratio_20": 0.0,
            "micro_volume_burst_decay_20": 0.0,
            "micro_gap_fill_progress": 0.0,
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


def _write_detail_file(path: Path, *, key: str = "decision-1", action: str = "BUY", setup_id: str = "breakout_prepare_buy"):
    payload = {
        "decision_row_key": key,
        "runtime_snapshot_key": "runtime-1",
        "trade_link_key": "trade-1",
        "action": action,
        "entry_setup_id": setup_id,
        "entry_session_name": "LONDON",
        "entry_atr_ratio": 1.42,
        "prediction_bundle": json.dumps({"p_continuation_success": 0.61, "p_false_break": 0.12}),
        "state_raw_snapshot_v1": json.dumps(
            {
                "s_body_size_pct_20": 0.14,
                "s_doji_ratio_20": 0.22,
                "s_same_color_run_current": 2,
                "s_same_color_run_max_20": 3,
                "s_range_compression_ratio_20": 0.82,
                "s_volume_burst_ratio_20": 2.15,
                "s_volume_burst_decay_20": 0.18,
                "s_gap_fill_progress": 0.47,
                "s_upper_wick_ratio_20": 0.18,
                "s_lower_wick_ratio_20": 0.12,
                "s_bull_ratio_20": 0.68,
                "s_bear_ratio_20": 0.22,
                "s_tick_volume_ratio": 1.9,
                "s_real_volume_ratio": 1.7,
            }
        ),
        "response_raw_snapshot_v1": json.dumps(
            {
                "pattern_double_top": 0.0,
                "pattern_double_bottom": 0.0,
                "sr_resistance_touch": 0.0,
                "sr_support_touch": 0.0,
                "micro_indecision": 0.0,
            }
        ),
    }
    record = {
        "record_type": "entry_decision_detail",
        "schema_version": "v1",
        "row_key": key,
        "payload": payload,
    }
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8-sig")


def test_teacher_pattern_detail_micro_backfill_plan_reports_matches(tmp_path: Path):
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    _write_detail_file(detail_path)
    frame = normalize_trade_df(pd.DataFrame([_row()], columns=TRADE_COLUMNS))

    report = build_teacher_pattern_detail_micro_backfill_plan(
        frame,
        detail_paths=[detail_path],
        recent_limit=100,
    )

    assert report["target_rows"] == 1
    assert report["matched_rows"] == 1
    assert report["micro_enriched_rows"] == 1
    assert len(report["preview_samples"]) == 1


def test_teacher_pattern_detail_micro_backfill_apply_enriches_micro_fields_and_labels_unlabeled_row(tmp_path: Path):
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    _write_detail_file(detail_path)
    frame = normalize_trade_df(pd.DataFrame([_row()], columns=TRADE_COLUMNS))

    updated, report = apply_teacher_pattern_detail_micro_backfill(
        frame,
        detail_paths=[detail_path],
        recent_limit=100,
    )

    row = updated.iloc[0]
    assert float(row["micro_body_size_pct_20"]) == 0.14
    assert float(row["micro_volume_burst_ratio_20"]) == 2.15
    assert str(row["micro_breakout_readiness_state"]) == "COILED_BREAKOUT"
    assert float(row["entry_atr_ratio"]) == 1.42
    assert int(pd.to_numeric(row["teacher_pattern_id"], errors="coerce") or 0) > 0
    assert row["teacher_label_source"] == DETAIL_BACKFILL_LABEL_SOURCE
    assert row["teacher_label_review_status"] == DETAIL_BACKFILL_LABEL_REVIEW_STATUS
    assert report["micro_enriched_rows"] == 1
    assert report["teacher_labeled_rows"] == 1
    assert report["atr_enriched_rows"] == 1


def test_teacher_pattern_detail_micro_backfill_preserves_existing_teacher_source_when_only_micro_is_enriched(tmp_path: Path):
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    _write_detail_file(detail_path, setup_id="range_outer_band_reversal_sell", action="SELL")
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _row(
                    direction="SELL",
                    teacher_pattern_id=5,
                    teacher_pattern_name="existing",
                    teacher_label_source="runtime",
                    teacher_label_review_status="reviewed",
                )
            ],
            columns=TRADE_COLUMNS,
        )
    )

    updated, report = apply_teacher_pattern_detail_micro_backfill(
        frame,
        detail_paths=[detail_path],
        recent_limit=100,
    )

    row = updated.iloc[0]
    assert int(pd.to_numeric(row["teacher_pattern_id"], errors="coerce") or 0) == 5
    assert row["teacher_label_source"] == "runtime"
    assert row["teacher_label_review_status"] == "reviewed"
    assert float(row["micro_body_size_pct_20"]) == 0.14
    assert report["micro_enriched_rows"] == 1
    assert report["teacher_labeled_rows"] == 0


def test_teacher_pattern_detail_micro_backfill_uses_regime_volatility_ratio_as_atr_proxy_when_direct_atr_missing(tmp_path: Path):
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    _write_detail_file(detail_path)
    raw = json.loads(detail_path.read_text(encoding="utf-8-sig").strip())
    raw["payload"].pop("entry_atr_ratio", None)
    detail_path.write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8-sig")
    frame = normalize_trade_df(
        pd.DataFrame(
            [
                _row(
                    entry_atr_ratio=1.0,
                    regime_volatility_ratio=1.37,
                )
            ],
            columns=TRADE_COLUMNS,
        )
    )

    updated, report = apply_teacher_pattern_detail_micro_backfill(
        frame,
        detail_paths=[detail_path],
        recent_limit=100,
    )

    row = updated.iloc[0]
    assert float(row["entry_atr_ratio"]) == 1.37
    assert report["atr_enriched_rows"] == 1
