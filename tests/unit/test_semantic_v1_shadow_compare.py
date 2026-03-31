import json
from pathlib import Path

import pandas as pd

import ml.semantic_v1.shadow_compare as shadow_compare_module
from ml.semantic_v1.shadow_compare import (
    _resolve_default_compare_replay_source,
    _resolve_replay_source_inventory,
    build_shadow_compare_report,
    write_shadow_compare_report,
)


def test_build_shadow_compare_report_summarizes_row_level_differences():
    entry_df = pd.DataFrame(
        [
            {
                "time": "2026-03-20T09:00:00+09:00",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "entered",
                "blocked_by": "",
                "setup_id": "range_lower_reversal_buy",
                "preflight_regime": "range",
                "decision_row_key": "rk1",
                "replay_row_key": "rk1",
                "semantic_shadow_available": 1,
                "semantic_shadow_trace_quality": "clean",
                "semantic_shadow_timing_probability": 0.72,
                "semantic_shadow_entry_quality_probability": 0.64,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_compare_label": "agree_enter",
                "semantic_shadow_reason": "timing=0.720, entry_quality=0.640",
            },
            {
                "time": "2026-03-20T09:01:00+09:00",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "skipped",
                "blocked_by": "entry_wait",
                "setup_id": "range_lower_reversal_buy",
                "preflight_regime": "range",
                "decision_row_key": "rk2",
                "replay_row_key": "rk2",
                "semantic_shadow_available": 1,
                "semantic_shadow_trace_quality": "degraded",
                "semantic_shadow_timing_probability": 0.77,
                "semantic_shadow_entry_quality_probability": 0.67,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_compare_label": "semantic_earlier_enter",
                "semantic_shadow_reason": "timing=0.770, entry_quality=0.670",
            },
            {
                "time": "2026-03-20T09:02:00+09:00",
                "symbol": "XAUUSD",
                "action": "BUY",
                "outcome": "entered",
                "blocked_by": "",
                "setup_id": "range_lower_reversal_buy",
                "preflight_regime": "range",
                "decision_row_key": "rk3",
                "replay_row_key": "rk3",
                "semantic_shadow_available": 1,
                "semantic_shadow_trace_quality": "fallback_heavy",
                "semantic_shadow_timing_probability": 0.42,
                "semantic_shadow_entry_quality_probability": 0.39,
                "semantic_shadow_should_enter": 0,
                "semantic_shadow_compare_label": "semantic_later_block",
                "semantic_shadow_reason": "timing=0.420, entry_quality=0.390",
            },
        ]
    )

    replay_df = pd.DataFrame(
        [
            {
                "join_key": "rk1",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 3,
                "label_negative_count": 1,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition_positive_count": 3,
                "transition_negative_count": 1,
                "transition_unknown_count": 0,
                "management_positive_count": 2,
                "management_negative_count": 1,
                "management_unknown_count": 0,
            },
            {
                "join_key": "rk2",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 2,
                "label_negative_count": 1,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition_positive_count": 2,
                "transition_negative_count": 1,
                "transition_unknown_count": 0,
                "management_positive_count": 1,
                "management_negative_count": 0,
                "management_unknown_count": 0,
            },
            {
                "join_key": "rk3",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 1,
                "label_negative_count": 3,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition_positive_count": 1,
                "transition_negative_count": 3,
                "transition_unknown_count": 0,
                "management_positive_count": 0,
                "management_negative_count": 2,
                "management_unknown_count": 0,
            },
        ]
    )

    report = build_shadow_compare_report(entry_df, replay_label_frame=replay_df)

    assert report["summary"]["rows_total"] == 3
    assert report["summary"]["shadow_available_rows"] == 3
    assert report["summary"]["matched_replay_rows"] == 3
    assert report["summary"]["missing_replay_join_rows"] == 0
    assert report["summary"]["baseline_entered_rows"] == 2
    assert report["summary"]["semantic_enter_rows"] == 2
    assert report["summary"]["scorable_shadow_rows"] == 3
    assert report["summary"]["unscorable_shadow_rows"] == 0
    assert report["summary"]["semantic_earlier_enter_rows"] == 1
    assert report["summary"]["semantic_later_block_rows"] == 1
    assert report["compare_label_counts"]["semantic_earlier_enter"] == 1
    assert report["scorable_exclusion_reason_counts"]["scorable"] == 3
    assert report["transition_label_status_counts"]["VALID"] == 3
    assert report["by_symbol"]["BTCUSD"]["semantic_enter_rows"] == 2
    assert report["by_symbol"]["BTCUSD"]["scorable_shadow_rows"] == 2
    assert report["by_regime"]["range"]["rows"] == 3
    assert report["candidate_threshold_table"]


def test_build_shadow_compare_report_surfaces_unscorable_reason_taxonomy():
    entry_df = pd.DataFrame(
        [
            {
                "time": "2026-03-20T09:00:00+09:00",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "skipped",
                "blocked_by": "entry_wait",
                "setup_id": "range_lower_reversal_buy",
                "preflight_regime": "range",
                "decision_row_key": "rk1",
                "replay_row_key": "rk1",
                "semantic_shadow_available": 1,
                "semantic_shadow_trace_quality": "fallback_heavy",
                "semantic_shadow_timing_probability": 0.72,
                "semantic_shadow_entry_quality_probability": 0.64,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_compare_label": "semantic_earlier_enter",
                "semantic_shadow_reason": "timing=0.720, entry_quality=0.640",
            },
            {
                "time": "2026-03-20T09:01:00+09:00",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "skipped",
                "blocked_by": "entry_wait",
                "setup_id": "range_lower_reversal_buy",
                "preflight_regime": "range",
                "decision_row_key": "rk2",
                "replay_row_key": "rk2",
                "semantic_shadow_available": 1,
                "semantic_shadow_trace_quality": "fallback_heavy",
                "semantic_shadow_timing_probability": 0.72,
                "semantic_shadow_entry_quality_probability": 0.64,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_compare_label": "semantic_earlier_enter",
                "semantic_shadow_reason": "timing=0.720, entry_quality=0.640",
            },
            {
                "time": "2026-03-20T09:02:00+09:00",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "skipped",
                "blocked_by": "entry_wait",
                "setup_id": "range_lower_reversal_buy",
                "preflight_regime": "range",
                "decision_row_key": "rk3",
                "replay_row_key": "rk3",
                "semantic_shadow_available": 1,
                "semantic_shadow_trace_quality": "fallback_heavy",
                "semantic_shadow_timing_probability": 0.72,
                "semantic_shadow_entry_quality_probability": 0.64,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_compare_label": "semantic_earlier_enter",
                "semantic_shadow_reason": "timing=0.720, entry_quality=0.640",
            },
            {
                "time": "2026-03-20T09:03:00+09:00",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "skipped",
                "blocked_by": "entry_wait",
                "setup_id": "range_lower_reversal_buy",
                "preflight_regime": "range",
                "decision_row_key": "rk_missing",
                "replay_row_key": "rk_missing",
                "semantic_shadow_available": 1,
                "semantic_shadow_trace_quality": "fallback_heavy",
                "semantic_shadow_timing_probability": 0.72,
                "semantic_shadow_entry_quality_probability": 0.64,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_compare_label": "semantic_earlier_enter",
                "semantic_shadow_reason": "timing=0.720, entry_quality=0.640",
            },
        ]
    )

    replay_df = pd.DataFrame(
        [
            {
                "join_key": "rk1",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 0,
                "label_negative_count": 0,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition_positive_count": 0,
                "transition_negative_count": 0,
                "transition_unknown_count": 0,
                "management_positive_count": 0,
                "management_negative_count": 0,
                "management_unknown_count": 0,
            },
            {
                "join_key": "rk2",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "label_positive_count": 2,
                "label_negative_count": 1,
                "label_unknown_count": 0,
                "label_is_ambiguous": True,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": False,
                "transition_positive_count": 2,
                "transition_negative_count": 1,
                "transition_unknown_count": 0,
                "management_positive_count": 0,
                "management_negative_count": 0,
                "management_unknown_count": 0,
            },
            {
                "join_key": "rk3",
                "transition_label_status": "PENDING",
                "management_label_status": "VALID",
                "label_positive_count": 2,
                "label_negative_count": 1,
                "label_unknown_count": 0,
                "label_is_ambiguous": False,
                "label_source_descriptor": "closed_trade+future_bars",
                "is_censored": True,
                "transition_positive_count": 2,
                "transition_negative_count": 1,
                "transition_unknown_count": 0,
                "management_positive_count": 0,
                "management_negative_count": 0,
                "management_unknown_count": 0,
            },
        ]
    )

    report = build_shadow_compare_report(entry_df, replay_label_frame=replay_df)

    assert report["summary"]["shadow_available_rows"] == 4
    assert report["summary"]["matched_replay_rows"] == 3
    assert report["summary"]["missing_replay_join_rows"] == 1
    assert report["summary"]["scorable_shadow_rows"] == 0
    assert report["summary"]["unscorable_shadow_rows"] == 4
    assert report["scorable_exclusion_reason_counts"]["missing_replay_join"] == 1
    assert report["scorable_exclusion_reason_counts"]["transition_status_not_valid"] == 1
    assert report["scorable_exclusion_reason_counts"]["label_ambiguous"] == 1
    assert report["scorable_exclusion_reason_counts"]["no_transition_counts"] == 1
    assert report["transition_label_status_counts"]["VALID"] == 2
    assert report["transition_label_status_counts"]["PENDING"] == 1
    assert report["transition_label_status_counts"]["UNKNOWN"] == 1


def test_resolve_replay_source_inventory_excludes_non_production_by_default(tmp_path):
    (tmp_path / "replay_dataset_rows_20260322_174852.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "replay_dataset_rows_r2_audit.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "replay_dataset_rows_tail300.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "replay_dataset_rows_legacy.jsonl").write_text("{}", encoding="utf-8")

    inventory = _resolve_replay_source_inventory(tmp_path, explicit_source=False)

    assert inventory["selection_mode"] == "default_production_only"
    assert inventory["selected_file_count"] == 1
    assert inventory["excluded_file_count"] == 3
    assert [item.name for item in inventory["selected_paths"]] == ["replay_dataset_rows_20260322_174852.jsonl"]
    assert inventory["excluded_source_class_counts"]["audit_test_source"] == 2
    assert inventory["excluded_source_class_counts"]["legacy_snapshot_source"] == 1


def test_resolve_replay_source_inventory_allows_explicit_directory_override(tmp_path):
    (tmp_path / "replay_dataset_rows_20260322_174852.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "replay_dataset_rows_r2_audit.jsonl").write_text("{}", encoding="utf-8")

    inventory = _resolve_replay_source_inventory(tmp_path, explicit_source=True)

    assert inventory["selection_mode"] == "explicit_directory_override"
    assert inventory["selected_file_count"] == 2
    assert inventory["excluded_file_count"] == 0
    assert inventory["selected_source_class_counts"]["production_compare_source"] == 1
    assert inventory["selected_source_class_counts"]["audit_test_source"] == 1


def test_default_write_shadow_compare_report_aligns_to_selected_replay_coverage(tmp_path, monkeypatch):
    replay_dir = tmp_path / "replay_intermediate"
    replay_dir.mkdir()
    entry_path = tmp_path / "entry_decisions.csv"
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    entry_df = pd.DataFrame(
        [
            {
                "time": "2026-03-20T09:00:00",
                "symbol": "BTCUSD",
                "outcome": "skipped",
                "decision_row_key": "rk_prod",
                "replay_row_key": "rk_prod",
                "semantic_shadow_available": 1,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_compare_label": "semantic_earlier_enter",
                "semantic_shadow_trace_quality": "fallback_heavy",
            },
            {
                "time": "2026-03-26T09:00:00",
                "symbol": "BTCUSD",
                "outcome": "skipped",
                "decision_row_key": "rk_audit",
                "replay_row_key": "rk_audit",
                "semantic_shadow_available": 1,
                "semantic_shadow_should_enter": 1,
                "semantic_shadow_compare_label": "semantic_earlier_enter",
                "semantic_shadow_trace_quality": "fallback_heavy",
            },
        ]
    )
    entry_df.to_csv(entry_path, index=False, encoding="utf-8-sig")

    production_row = {
        "decision_row_key": "rk_prod",
        "replay_row_key": "rk_prod",
        "transition_label_status": "VALID",
        "label_positive_count": 1,
        "label_negative_count": 0,
        "label_unknown_count": 0,
        "label_is_ambiguous": False,
        "is_censored": False,
        "transition_positive_count": 1,
        "transition_negative_count": 0,
        "transition_unknown_count": 0,
        "decision_row": {"time": "2026-03-20T09:00:00"},
    }
    audit_row = {
        "decision_row_key": "rk_audit",
        "replay_row_key": "rk_audit",
        "transition_label_status": "VALID",
        "label_positive_count": 1,
        "label_negative_count": 0,
        "label_unknown_count": 0,
        "label_is_ambiguous": False,
        "is_censored": False,
        "transition_positive_count": 1,
        "transition_negative_count": 0,
        "transition_unknown_count": 0,
        "decision_row": {"time": "2026-03-26T09:00:00"},
    }
    (replay_dir / "replay_dataset_rows_20260320.jsonl").write_text(
        json.dumps(production_row) + "\n",
        encoding="utf-8",
    )
    (replay_dir / "replay_dataset_rows_r2_audit.jsonl").write_text(
        json.dumps(audit_row) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(shadow_compare_module, "DEFAULT_ENTRY_DECISIONS_PATH", entry_path)
    monkeypatch.setattr(shadow_compare_module, "DEFAULT_REPLAY_SOURCE", replay_dir)

    paths = write_shadow_compare_report(output_dir=output_dir)
    report = json.loads(Path(paths["json_path"]).read_text(encoding="utf-8"))

    assert report["summary"]["rows_total"] == 1
    assert report["summary"]["matched_replay_rows"] == 1
    assert report["source_scope"]["selection_mode"] == "default_production_only"
    assert report["source_scope"]["selected_file_count"] == 1
    assert report["source_scope"]["excluded_file_count"] == 1
    assert report["source_scope"]["aligned_entry_rows"] == 1
    assert report["source_scope"]["dropped_entry_rows"] == 1
    assert report["source_scope"]["replay_first_time"] == "2026-03-20T09:00:00"
    assert report["source_scope"]["replay_last_time"] == "2026-03-20T09:00:00"


def test_resolve_default_compare_replay_source_prefers_dedicated_live_directory(tmp_path, monkeypatch):
    dedicated_dir = tmp_path / "replay_intermediate_compare_live"
    fallback_dir = tmp_path / "replay_intermediate"
    dedicated_dir.mkdir()
    fallback_dir.mkdir()
    (fallback_dir / "replay_dataset_rows_20260322.jsonl").write_text("{}", encoding="utf-8")
    (dedicated_dir / "replay_dataset_rows_20260326.jsonl").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(shadow_compare_module, "DEFAULT_PRODUCTION_COMPARE_REPLAY_SOURCE", dedicated_dir)
    monkeypatch.setattr(shadow_compare_module, "DEFAULT_REPLAY_SOURCE", fallback_dir)

    assert _resolve_default_compare_replay_source() == dedicated_dir


def test_resolve_default_compare_replay_source_falls_back_when_dedicated_missing(tmp_path, monkeypatch):
    fallback_dir = tmp_path / "replay_intermediate"
    fallback_dir.mkdir()
    (fallback_dir / "replay_dataset_rows_20260322.jsonl").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        shadow_compare_module,
        "DEFAULT_PRODUCTION_COMPARE_REPLAY_SOURCE",
        tmp_path / "missing_compare_live",
    )
    monkeypatch.setattr(shadow_compare_module, "DEFAULT_REPLAY_SOURCE", fallback_dir)

    assert _resolve_default_compare_replay_source() == fallback_dir
