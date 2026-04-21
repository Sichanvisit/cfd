import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "product_acceptance_pa0_baseline_freeze.py"
spec = importlib.util.spec_from_file_location("product_acceptance_pa0_baseline_freeze", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_build_pa0_baseline_report_builds_tri_symbol_and_seed_queues(tmp_path):
    entry_path = tmp_path / "entry_decisions.csv"
    runtime_path = tmp_path / "runtime_status.json"
    chart_flow_path = tmp_path / "chart_flow_distribution_latest.json"
    closed_history_path = tmp_path / "trade_closed_history.csv"

    entry_fieldnames = [
        "time",
        "symbol",
        "action",
        "observe_reason",
        "blocked_by",
        "action_none_reason",
        "probe_scene_id",
        "box_state",
        "bb_state",
        "entry_score_raw",
        "consumer_check_state_v1",
    ]
    _write_csv(
        entry_path,
        entry_fieldnames,
        [
            {
                "time": "2026-03-31T10:00:00",
                "symbol": "BTCUSD",
                "action": "",
                "observe_reason": "lower_rebound_probe_observe",
                "blocked_by": "forecast_guard",
                "action_none_reason": "probe_not_promoted",
                "probe_scene_id": "btc_lower_buy_conservative_probe",
                "box_state": "LOWER",
                "bb_state": "BREAKDOWN",
                "entry_score_raw": "72",
                "consumer_check_state_v1": json.dumps(
                    {
                        "contract_version": "consumer_check_state_v1",
                        "check_candidate": True,
                        "check_display_ready": False,
                        "entry_ready": False,
                        "check_side": "BUY",
                        "check_stage": "BLOCKED",
                        "display_score": 0.0,
                        "display_repeat_count": 0,
                        "display_strength_level": 0,
                        "display_importance_tier": "medium",
                    }
                ),
            },
            {
                "time": "2026-03-31T10:01:00",
                "symbol": "NAS100",
                "action": "",
                "observe_reason": "conflict_box_upper_bb20_lower_upper_dominant_observe",
                "blocked_by": "middle_sr_anchor_guard",
                "action_none_reason": "observe_state_wait",
                "probe_scene_id": "",
                "box_state": "MIDDLE",
                "bb_state": "MID",
                "entry_score_raw": "48",
                "consumer_check_state_v1": json.dumps(
                    {
                        "contract_version": "consumer_check_state_v1",
                        "check_candidate": True,
                        "check_display_ready": True,
                        "entry_ready": False,
                        "check_side": "SELL",
                        "check_stage": "OBSERVE",
                        "display_score": 0.84,
                        "display_repeat_count": 2,
                        "display_strength_level": 5,
                    }
                ),
            },
            {
                "time": "2026-03-31T10:02:00",
                "symbol": "XAUUSD",
                "action": "BUY",
                "observe_reason": "lower_rebound_confirm",
                "blocked_by": "",
                "action_none_reason": "",
                "probe_scene_id": "",
                "box_state": "LOWER",
                "bb_state": "LOWER_EDGE",
                "entry_score_raw": "91",
                "consumer_check_state_v1": json.dumps(
                    {
                        "contract_version": "consumer_check_state_v1",
                        "check_candidate": True,
                        "check_display_ready": True,
                        "entry_ready": True,
                        "check_side": "BUY",
                        "check_stage": "READY",
                        "display_score": 0.95,
                        "display_repeat_count": 3,
                        "display_strength_level": 8,
                        "display_importance_tier": "high",
                    }
                ),
            },
            {
                "time": "2026-03-31T10:03:00",
                "symbol": "XAUUSD",
                "action": "",
                "observe_reason": "middle_sr_anchor_required_observe",
                "blocked_by": "middle_sr_anchor_guard",
                "action_none_reason": "observe_state_wait",
                "probe_scene_id": "",
                "box_state": "MIDDLE",
                "bb_state": "MID",
                "entry_score_raw": "44",
                "consumer_check_state_v1": json.dumps(
                    {
                        "contract_version": "consumer_check_state_v1",
                        "check_candidate": True,
                        "check_display_ready": False,
                        "entry_ready": False,
                        "check_side": "BUY",
                        "check_stage": "BLOCKED",
                        "display_score": 0.0,
                        "display_repeat_count": 0,
                        "display_strength_level": 0,
                    }
                ),
            },
            {
                "time": "2026-03-31T10:04:00",
                "symbol": "BTCUSD",
                "action": "",
                "observe_reason": "middle_sr_anchor_required_observe",
                "blocked_by": "middle_sr_anchor_guard",
                "action_none_reason": "observe_state_wait",
                "probe_scene_id": "",
                "box_state": "MIDDLE",
                "bb_state": "MID",
                "entry_score_raw": "41",
                "consumer_check_state_v1": json.dumps(
                    {
                        "contract_version": "consumer_check_state_v1",
                        "check_candidate": True,
                        "check_display_ready": True,
                        "entry_ready": False,
                        "check_side": "BUY",
                        "check_stage": "OBSERVE",
                        "display_score": 0.82,
                        "display_repeat_count": 2,
                        "display_strength_level": 5,
                    }
                ),
            },
        ],
    )

    _write_json(
        runtime_path,
        {
            "updated_at": "2026-03-31T14:36:47+09:00",
            "entry_threshold": 45,
            "exit_threshold": 150,
            "semantic_live_config": {"mode": "threshold_only"},
            "policy_snapshot": {
                "symbol_applied_vs_default": {
                    "BTCUSD": {
                        "entry_threshold_applied": 45,
                        "entry_threshold_delta": 0,
                        "exit_threshold_applied": 55,
                        "exit_threshold_delta": 0,
                        "policy_scope": "GLOBAL",
                        "sample_count": 0,
                    },
                    "NAS100": {
                        "entry_threshold_applied": 40,
                        "entry_threshold_delta": 0,
                        "exit_threshold_applied": 60,
                        "exit_threshold_delta": 0,
                        "policy_scope": "GLOBAL",
                        "sample_count": 0,
                    },
                    "XAUUSD": {
                        "entry_threshold_applied": 45,
                        "entry_threshold_delta": 0,
                        "exit_threshold_applied": 58,
                        "exit_threshold_delta": 0,
                        "policy_scope": "GLOBAL",
                        "sample_count": 0,
                    },
                }
            },
        },
    )
    _write_json(
        chart_flow_path,
        {
            "contract_version": "chart_flow_distribution_v1",
            "generated_at": "2026-03-31T14:36:43+09:00",
            "symbols": {
                "BTCUSD": {
                    "window_event_count": 16,
                    "event_counts": {"BUY_WAIT": 8, "SELL_WAIT": 5, "WAIT": 3},
                    "presence": {"buy_presence_ratio": 0.5, "sell_presence_ratio": 0.3125},
                },
                "NAS100": {
                    "window_event_count": 16,
                    "event_counts": {"BUY_WAIT": 2, "SELL_WAIT": 11, "BUY_PROBE": 1, "WAIT": 2},
                    "presence": {"buy_presence_ratio": 0.1875, "sell_presence_ratio": 0.6875},
                },
                "XAUUSD": {
                    "window_event_count": 16,
                    "event_counts": {"BUY_WAIT": 8, "SELL_WAIT": 1, "WAIT": 7},
                    "presence": {"buy_presence_ratio": 0.5, "sell_presence_ratio": 0.0625},
                },
            },
        },
    )

    closed_fieldnames = [
        "ticket",
        "symbol",
        "direction",
        "open_time",
        "close_time",
        "entry_reason",
        "exit_reason",
        "net_pnl_after_cost",
        "giveback_usd",
        "peak_profit_at_exit",
        "post_exit_mfe",
        "post_exit_mae",
        "wait_quality_label",
        "loss_quality_label",
        "exit_policy_profile",
        "status",
    ]
    _write_csv(
        closed_history_path,
        closed_fieldnames,
        [
            {
                "ticket": "1",
                "symbol": "XAUUSD",
                "direction": "BUY",
                "open_time": "2026-03-31 09:00:00",
                "close_time": "2026-03-31 09:15:00",
                "entry_reason": "range_lower_reversal_buy",
                "exit_reason": "protect_exit",
                "net_pnl_after_cost": "1.4",
                "giveback_usd": "0.1",
                "peak_profit_at_exit": "1.8",
                "post_exit_mfe": "0.1",
                "post_exit_mae": "0.0",
                "wait_quality_label": "no_wait",
                "loss_quality_label": "non_loss",
                "exit_policy_profile": "conservative",
                "status": "closed",
            },
            {
                "ticket": "2",
                "symbol": "BTCUSD",
                "direction": "SELL",
                "open_time": "2026-03-31 09:20:00",
                "close_time": "2026-03-31 09:35:00",
                "entry_reason": "upper_reject_sell",
                "exit_reason": "late_cut",
                "net_pnl_after_cost": "-0.8",
                "giveback_usd": "1.2",
                "peak_profit_at_exit": "0.5",
                "post_exit_mfe": "1.4",
                "post_exit_mae": "0.2",
                "wait_quality_label": "bad_wait",
                "loss_quality_label": "bad_loss",
                "exit_policy_profile": "neutral",
                "status": "closed",
            },
            {
                "ticket": "3",
                "symbol": "NAS100",
                "direction": "BUY",
                "open_time": "2026-03-31 09:40:00",
                "close_time": "2026-03-31 09:50:00",
                "entry_reason": "clean_confirm_buy",
                "exit_reason": "protect_exit",
                "net_pnl_after_cost": "0.1",
                "giveback_usd": "0.9",
                "peak_profit_at_exit": "1.0",
                "post_exit_mfe": "0.8",
                "post_exit_mae": "0.1",
                "wait_quality_label": "bad_wait",
                "loss_quality_label": "neutral_loss",
                "exit_policy_profile": "neutral",
                "status": "closed",
            },
        ],
    )

    report = module.build_product_acceptance_pa0_baseline_report(
        entry_decisions_path=entry_path,
        runtime_status_path=runtime_path,
        chart_flow_distribution_path=chart_flow_path,
        closed_history_path=closed_history_path,
        recent_rows_per_symbol=10,
        recent_closed_trades_per_symbol=10,
        now=datetime.fromisoformat("2026-03-31T15:00:00"),
    )

    summary = report["baseline_summary"]
    seed_queue = report["casebook_seed_queue"]
    tri_symbol = {row["symbol"]: row for row in report["tri_symbol_baseline_summary"]}

    assert report["report_version"] == module.REPORT_VERSION
    assert summary["tri_symbol_count"] == 3
    assert summary["recent_entry_row_count"] == 5
    assert summary["recent_closed_trade_count"] == 3
    assert summary["must_show_missing_count"] >= 1
    assert summary["must_hide_leakage_count"] >= 1
    assert summary["must_enter_candidate_count"] >= 1
    assert summary["must_block_candidate_count"] >= 1
    assert summary["divergence_seed_count"] >= 1
    assert summary["must_hold_candidate_count"] >= 1
    assert summary["must_release_candidate_count"] >= 1
    assert summary["good_exit_candidate_count"] >= 1
    assert summary["bad_exit_candidate_count"] >= 1
    assert tri_symbol["BTCUSD"]["chart_window_event_count"] == 16
    assert tri_symbol["XAUUSD"]["entry_ready_count"] == 1
    assert seed_queue["must_show_missing"][0]["symbol"] == "BTCUSD"
    assert seed_queue["must_hide_leakage"][0]["symbol"] == "NAS100"
    assert seed_queue["must_enter_candidates"][0]["symbol"] == "XAUUSD"
    assert seed_queue["bad_exit_candidates"][0]["symbol"] == "BTCUSD"


def test_write_pa0_baseline_report_writes_json_csv_and_markdown(tmp_path):
    entry_path = tmp_path / "entry_decisions.csv"
    runtime_path = tmp_path / "runtime_status.json"
    chart_flow_path = tmp_path / "chart_flow_distribution_latest.json"
    closed_history_path = tmp_path / "trade_closed_history.csv"
    output_dir = tmp_path / "analysis"

    _write_csv(
        entry_path,
        ["time", "symbol", "action", "observe_reason", "blocked_by", "action_none_reason", "probe_scene_id", "box_state", "bb_state", "entry_score_raw", "consumer_check_state_v1"],
        [
            {
                "time": "2026-03-31T10:02:00",
                "symbol": "XAUUSD",
                "action": "BUY",
                "observe_reason": "lower_rebound_confirm",
                "blocked_by": "",
                "action_none_reason": "",
                "probe_scene_id": "",
                "box_state": "LOWER",
                "bb_state": "LOWER_EDGE",
                "entry_score_raw": "91",
                "consumer_check_state_v1": json.dumps(
                    {
                        "contract_version": "consumer_check_state_v1",
                        "check_candidate": True,
                        "check_display_ready": True,
                        "entry_ready": True,
                        "check_side": "BUY",
                        "check_stage": "READY",
                        "display_score": 0.95,
                        "display_repeat_count": 3,
                        "display_strength_level": 8,
                    }
                ),
            }
        ],
    )
    _write_json(
        runtime_path,
        {
            "updated_at": "2026-03-31T14:36:47+09:00",
            "entry_threshold": 45,
            "exit_threshold": 150,
            "semantic_live_config": {"mode": "threshold_only"},
            "policy_snapshot": {"symbol_applied_vs_default": {}},
        },
    )
    _write_json(
        chart_flow_path,
        {"symbols": {"XAUUSD": {"window_event_count": 16, "event_counts": {"BUY_WAIT": 8}, "presence": {"buy_presence_ratio": 0.5}}}},
    )
    _write_csv(
        closed_history_path,
        ["ticket", "symbol", "direction", "open_time", "close_time", "entry_reason", "exit_reason", "net_pnl_after_cost", "giveback_usd", "peak_profit_at_exit", "post_exit_mfe", "post_exit_mae", "wait_quality_label", "loss_quality_label", "exit_policy_profile", "status"],
        [
            {
                "ticket": "1",
                "symbol": "XAUUSD",
                "direction": "BUY",
                "open_time": "2026-03-31 09:00:00",
                "close_time": "2026-03-31 09:15:00",
                "entry_reason": "range_lower_reversal_buy",
                "exit_reason": "protect_exit",
                "net_pnl_after_cost": "1.4",
                "giveback_usd": "0.1",
                "peak_profit_at_exit": "1.8",
                "post_exit_mfe": "0.1",
                "post_exit_mae": "0.0",
                "wait_quality_label": "no_wait",
                "loss_quality_label": "non_loss",
                "exit_policy_profile": "conservative",
                "status": "closed",
            }
        ],
    )

    result = module.write_product_acceptance_pa0_baseline_report(
        output_dir=output_dir,
        entry_decisions_path=entry_path,
        runtime_status_path=runtime_path,
        chart_flow_distribution_path=chart_flow_path,
        closed_history_path=closed_history_path,
        recent_rows_per_symbol=10,
        recent_closed_trades_per_symbol=10,
        now=datetime.fromisoformat("2026-03-31T15:00:00"),
    )

    json_path = Path(result["latest_json_path"])
    csv_path = Path(result["latest_csv_path"])
    md_path = Path(result["latest_markdown_path"])

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")
    csv_text = csv_path.read_text(encoding="utf-8-sig")

    assert payload["baseline_summary"]["good_exit_candidate_count"] == 1
    assert "Product Acceptance PA0 Baseline Freeze" in markdown
    assert "tri_symbol_baseline" in csv_text


def test_pa0_baseline_skips_acceptable_wait_check_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-03-31T15:38:59",
        "action": "",
        "observe_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "MID",
        "decision_row_key": "row-1",
    }
    rows_without_relief = {
        "BTCUSD": [dict(base_row)],
        "NAS100": [],
        "XAUUSD": [],
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "probe_guard_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_without_relief)) == 1
    assert len(module._build_must_hide_leakage_candidates(rows_without_relief)) == 1
    assert len(module._build_must_block_candidates(rows_without_relief)) == 1

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_nas_outer_band_probe_guard_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-03-31T21:26:51",
        "action": "",
        "observe_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "outer_band_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "nas_clean_confirm_probe",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "outer_band_guard",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-nas-outer-band-guard-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "probe_guard_wait_as_wait_checks",
            }
        ],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_outer_band_probe_guard_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-04-01T13:48:48",
        "action": "",
        "observe_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "outer_band_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "xau_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "outer_band_guard",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-outer-band-guard-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "probe_guard_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_outer_band_probe_guard_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-03-31T21:48:30",
        "action": "",
        "observe_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "outer_band_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "blocked_display_reason": "outer_band_guard",
        "entry_ready": False,
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "decision_row_key": "row-btc-outer-band-guard-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "probe_guard_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_lower_probe_guard_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T00:00:12",
        "action": "",
        "observe_reason": "lower_rebound_probe_observe",
        "blocked_by": "forecast_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "blocked_display_reason": "forecast_guard",
        "entry_ready": False,
        "box_state": "LOWER",
        "bb_state": "MID",
        "decision_row_key": "row-btc-lower-probe-guard-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_lower_probe_guard_wait_as_wait_checks",
            },
            {
                **base_row,
                "time": "2026-04-01T00:00:46",
                "blocked_by": "barrier_guard",
                "blocked_display_reason": "barrier_guard",
                "decision_row_key": "row-btc-lower-probe-guard-wait-2",
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_lower_probe_guard_wait_as_wait_checks",
            },
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_upper_reject_wait_check_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-03-31T16:58:50",
        "action": "",
        "observe_reason": "upper_reject_mixed_confirm",
        "blocked_by": "barrier_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 6,
        "display_importance_tier": "medium",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_reject_mixed_guard_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_reject_confirm_forecast_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T01:41:06",
        "action": "",
        "observe_reason": "upper_reject_confirm",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "forecast_guard",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "BREAKOUT",
        "decision_row_key": "row-btc-upper-confirm-forecast-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_reject_confirm_forecast_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_break_fail_confirm_forecast_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T01:45:56",
        "action": "",
        "observe_reason": "upper_break_fail_confirm",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "forecast_guard",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "BREAKOUT",
        "decision_row_key": "row-btc-upper-break-fail-forecast-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_break_fail_confirm_forecast_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_break_fail_confirm_entry_gate_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T14:44:25",
        "action": "SELL",
        "observe_reason": "upper_break_fail_confirm",
        "blocked_by": "clustered_entry_price_zone",
        "action_none_reason": "",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 6,
        "display_importance_tier": "high",
        "blocked_display_reason": "clustered_entry_price_zone",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-upper-break-fail-entry-gate-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_nas_upper_break_fail_confirm_entry_gate_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-04-01T15:59:19",
        "action": "SELL",
        "observe_reason": "upper_break_fail_confirm",
        "blocked_by": "clustered_entry_price_zone",
        "action_none_reason": "",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "clustered_entry_price_zone",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "BREAKOUT",
        "decision_row_key": "row-nas-upper-break-fail-entry-gate-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "nas_upper_break_fail_confirm_entry_gate_wait_as_wait_checks",
            }
        ],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_break_fail_confirm_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T14:53:24",
        "action": "",
        "observe_reason": "upper_break_fail_confirm",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "high",
        "blocked_display_reason": "energy_soft_block",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-upper-break-fail-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_break_fail_confirm_energy_soft_block_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_reject_probe_forecast_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T01:40:49",
        "action": "",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "forecast_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "btc_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.86,
        "display_repeat_count": 2,
        "display_strength_level": 6,
        "display_importance_tier": "",
        "blocked_display_reason": "forecast_guard",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-upper-probe-forecast-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_reject_probe_forecast_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_reject_probe_preflight_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T01:49:24",
        "action": "",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "preflight_action_blocked",
        "action_none_reason": "preflight_blocked",
        "probe_scene_id": "btc_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.65,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "preflight_action_blocked",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-upper-probe-preflight-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_reject_probe_preflight_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_reject_confirm_preflight_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T01:44:55",
        "action": "",
        "observe_reason": "upper_reject_confirm",
        "blocked_by": "preflight_action_blocked",
        "action_none_reason": "preflight_blocked",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "preflight_action_blocked",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "BREAKOUT",
        "decision_row_key": "row-btc-upper-confirm-preflight-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_reject_confirm_preflight_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_reject_probe_promotion_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T14:14:28",
        "action": "",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "probe_promotion_gate",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "btc_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.86,
        "display_repeat_count": 2,
        "display_strength_level": 7,
        "display_importance_tier": "",
        "blocked_display_reason": "probe_promotion_gate",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-upper-probe-promotion-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_reject_probe_promotion_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_reject_confirm_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T13:59:51",
        "action": "",
        "observe_reason": "upper_reject_confirm",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "energy_soft_block",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-upper-confirm-energy-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_reject_confirm_energy_soft_block_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_reject_probe_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T14:18:07",
        "action": "",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "btc_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "energy_soft_block",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-upper-probe-energy-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_reject_probe_energy_soft_block_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_upper_reject_mixed_forecast_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-03-31T23:24:40",
        "action": "",
        "observe_reason": "upper_reject_mixed_confirm",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "blocked_display_reason": "forecast_guard",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-mixed-forecast-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_reject_mixed_guard_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_upper_reject_confirm_forecast_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-04-01T01:43:59",
        "action": "",
        "observe_reason": "upper_reject_confirm",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "high",
        "blocked_display_reason": "forecast_guard",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-confirm-forecast-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_reject_confirm_forecast_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_middle_anchor_guard_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-03-31T21:48:05",
        "action": "",
        "observe_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "middle_sr_anchor_guard",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "MID",
        "decision_row_key": "row-xau-middle-anchor-guard-wait-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_middle_anchor_guard_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_upper_reject_confirm_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-03-31T23:10:54",
        "action": "",
        "observe_reason": "upper_reject_confirm",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "high",
        "blocked_display_reason": "energy_soft_block",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-upper-reject-confirm-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_reject_confirm_energy_soft_block_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_upper_reject_mixed_confirm_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-04-01T00:32:56",
        "action": "",
        "observe_reason": "upper_reject_mixed_confirm",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "blocked_display_reason": "energy_soft_block",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UNKNOWN",
        "decision_row_key": "row-xau-upper-reject-mixed-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_upper_reject_mixed_confirm_entry_gate_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-04-01T16:11:50",
        "action": "SELL",
        "observe_reason": "upper_reject_mixed_confirm",
        "blocked_by": "clustered_entry_price_zone",
        "action_none_reason": "",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "blocked_display_reason": "clustered_entry_price_zone",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-upper-mixed-entry-gate-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_reject_mixed_confirm_entry_gate_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_outer_band_probe_entry_gate_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-04-01T17:16:31",
        "action": "SELL",
        "observe_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "clustered_entry_price_zone",
        "action_none_reason": "",
        "probe_scene_id": "xau_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 2,
        "display_strength_level": 4,
        "display_importance_tier": "",
        "blocked_display_reason": "clustered_entry_price_zone",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-outer-band-entry-gate-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_outer_band_probe_entry_gate_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0
    assert len(module._build_must_enter_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_nas_upper_reject_mixed_confirm_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-04-01T15:53:33",
        "action": "",
        "observe_reason": "upper_reject_mixed_confirm",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "energy_soft_block",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "BREAKOUT",
        "decision_row_key": "row-nas-upper-mixed-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "nas_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks",
            }
        ],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_upper_break_fail_confirm_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-03-31T22:55:21",
        "action": "",
        "observe_reason": "upper_break_fail_confirm",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "high",
        "blocked_display_reason": "energy_soft_block",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "BREAKOUT",
        "decision_row_key": "row-xau-upper-break-fail-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_break_fail_confirm_energy_soft_block_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_nas_upper_break_fail_confirm_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-04-01T01:24:29",
        "action": "",
        "observe_reason": "upper_break_fail_confirm",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "energy_soft_block",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-nas-upper-break-fail-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "nas_upper_break_fail_confirm_energy_soft_block_as_wait_checks",
            }
        ],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_upper_reject_mixed_confirm_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T15:56:46",
        "action": "",
        "observe_reason": "upper_reject_mixed_confirm",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 1,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "blocked_display_reason": "energy_soft_block",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-upper-mixed-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_probe_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-03-31T17:14:38",
        "action": "",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "xau_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_reject_probe_energy_soft_block_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_probe_forecast_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-03-31T23:33:28",
        "action": "",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "forecast_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "xau_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 6,
        "display_importance_tier": "",
        "blocked_display_reason": "forecast_guard",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-forecast-probe-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_reject_probe_forecast_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_upper_reject_probe_promotion_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-04-01T00:59:53",
        "action": "",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "probe_promotion_gate",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "xau_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 6,
        "display_importance_tier": "medium",
        "blocked_display_reason": "probe_promotion_gate",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-xau-promotion-probe-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_upper_reject_probe_promotion_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_middle_anchor_probe_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-03-31T20:07:25",
        "action": "",
        "observe_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "xau_second_support_buy_probe",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "LOWER_EDGE",
        "decision_row_key": "row-xau-middle-anchor-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_middle_anchor_probe_energy_soft_block_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_lower_probe_guard_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-04-01T14:04:02",
        "action": "",
        "observe_reason": "lower_rebound_probe_observe",
        "blocked_by": "forecast_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "xau_second_support_buy_probe",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.86,
        "display_repeat_count": 2,
        "display_strength_level": 7,
        "display_importance_tier": "medium",
        "blocked_display_reason": "forecast_guard",
        "entry_ready": False,
        "box_state": "LOWER",
        "bb_state": "UNKNOWN",
        "decision_row_key": "row-xau-lower-forecast-probe-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_lower_probe_guard_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_middle_anchor_probe_guard_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-04-01T14:59:07",
        "action": "",
        "observe_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "xau_second_support_buy_probe",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "blocked_display_reason": "middle_sr_anchor_guard",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "MID",
        "decision_row_key": "row-xau-middle-anchor-probe-guard-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "probe_guard_wait_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_xau_outer_band_probe_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-03-31T22:38:26",
        "action": "",
        "observe_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "xau_upper_sell_probe",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.75,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UNKNOWN",
        "decision_row_key": "row-xau-outer-band-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "xau_outer_band_probe_energy_soft_block_as_wait_checks",
            }
        ],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_probe_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-03-31T17:52:17",
        "action": "",
        "observe_reason": "lower_rebound_probe_observe",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.91,
        "display_repeat_count": 3,
        "display_strength_level": 6,
        "display_importance_tier": "high",
        "entry_ready": False,
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "decision_row_key": "row-btc-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_lower_rebound_probe_energy_soft_block_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_lower_probe_promotion_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-03-31T20:11:43",
        "action": "",
        "observe_reason": "lower_rebound_probe_observe",
        "blocked_by": "probe_promotion_gate",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.91,
        "display_repeat_count": 3,
        "display_strength_level": 6,
        "display_importance_tier": "high",
        "entry_ready": False,
        "box_state": "BELOW",
        "bb_state": "LOWER_EDGE",
        "decision_row_key": "row-btc-lower-probe-promotion-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_lower_probe_promotion_wait_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_nas_upper_reject_probe_forecast_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-03-31T20:42:33",
        "action": "",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "forecast_guard",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "nas_clean_confirm_probe",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.86,
        "display_repeat_count": 2,
        "display_strength_level": 6,
        "display_importance_tier": "",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-nas-upper-reject-probe-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "nas_upper_reject_probe_forecast_wait_as_wait_checks",
            }
        ],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_nas_upper_reject_probe_promotion_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-03-31T20:30:42",
        "action": "",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "probe_promotion_gate",
        "action_none_reason": "probe_not_promoted",
        "probe_scene_id": "nas_clean_confirm_probe",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "SELL",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 6,
        "display_importance_tier": "",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-nas-upper-reject-probe-promotion-1",
    }
    rows_with_relief = {
        "BTCUSD": [],
        "NAS100": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "nas_upper_reject_probe_promotion_wait_as_wait_checks",
            }
        ],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_btc_structural_probe_energy_soft_block_wait_relief_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-03-31T19:16:28",
        "action": "",
        "observe_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "energy_soft_block",
        "action_none_reason": "execution_soft_blocked",
        "probe_scene_id": "btc_lower_buy_conservative_probe",
        "check_candidate": True,
        "check_stage": "BLOCKED",
        "check_side": "BUY",
        "display_ready": True,
        "display_score": 0.82,
        "display_repeat_count": 2,
        "display_strength_level": 5,
        "display_importance_tier": "medium",
        "entry_ready": False,
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "decision_row_key": "row-btc-structural-energy-1",
    }
    rows_with_relief = {
        "BTCUSD": [
            {
                **base_row,
                "chart_event_kind_hint": "WAIT",
                "chart_display_mode": "wait_check_repeat",
                "chart_display_reason": "btc_structural_probe_energy_soft_block_as_wait_checks",
            }
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows_with_relief)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows_with_relief)) == 0
    assert len(module._build_must_block_candidates(rows_with_relief)) == 0


def test_pa0_baseline_skips_hidden_nas_sell_outer_band_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-03-31T18:04:14",
        "action": "",
        "observe_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "outer_band_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "",
        "modifier_primary_reason": "sell_outer_band_wait_hide_without_probe",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UNKNOWN",
        "decision_row_key": "row-nas-sell-outer-band-hidden-1",
    }
    rows = {
        "BTCUSD": [],
        "NAS100": [base_row],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_pa0_baseline_skips_hidden_balanced_conflict_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-04-01T18:07:22",
        "action": "",
        "observe_reason": "conflict_box_upper_bb20_lower_lower_dominant_observe",
        "blocked_by": "",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": False,
        "check_stage": "",
        "check_side": "",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "",
        "modifier_primary_reason": "",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "UNKNOWN",
        "decision_row_key": "row-nas-balanced-conflict-hidden-1",
    }
    rows = {
        "BTCUSD": [],
        "NAS100": [base_row],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_pa0_baseline_skips_hidden_nas_sell_middle_anchor_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-03-31T19:03:52",
        "action": "",
        "observe_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "",
        "modifier_primary_reason": "nas_sell_middle_anchor_wait_hide_without_probe",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "MID",
        "decision_row_key": "row-nas-sell-middle-anchor-hidden-1",
    }
    rows = {
        "BTCUSD": [],
        "NAS100": [base_row],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_pa0_baseline_skips_hidden_btc_sell_middle_anchor_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T00:25:02",
        "action": "",
        "observe_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "",
        "modifier_primary_reason": "btc_sell_middle_anchor_wait_hide_without_probe",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-sell-middle-anchor-hidden-1",
    }
    rows = {
        "BTCUSD": [base_row],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_pa0_baseline_skips_hidden_btc_structural_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-04-01T00:23:14",
        "action": "",
        "observe_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "BUY",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "",
        "modifier_primary_reason": "structural_wait_hide_without_probe",
        "entry_ready": False,
        "box_state": "MIDDLE",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-btc-structural-hidden-1",
    }
    rows = {
        "BTCUSD": [base_row],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_pa0_baseline_skips_hidden_nas_upper_reject_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-03-31T20:16:06",
        "action": "",
        "observe_reason": "upper_reject_confirm",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "",
        "modifier_primary_reason": "nas_upper_reject_wait_hide_without_probe",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "decision_row_key": "row-nas-upper-reject-hidden-1",
    }
    rows = {
        "BTCUSD": [],
        "NAS100": [base_row],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_pa0_baseline_skips_hidden_nas_upper_break_fail_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-03-31T21:09:16",
        "action": "",
        "observe_reason": "upper_break_fail_confirm",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "SELL",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "",
        "modifier_primary_reason": "nas_upper_break_fail_wait_hide_without_probe",
        "entry_ready": False,
        "box_state": "ABOVE",
        "bb_state": "BREAKOUT",
        "decision_row_key": "row-nas-upper-break-fail-hidden-1",
    }
    rows = {
        "BTCUSD": [],
        "NAS100": [base_row],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_pa0_baseline_skips_hidden_nas_upper_reclaim_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "NAS100",
        "time": "2026-03-31T19:00:48",
        "action": "",
        "observe_reason": "upper_reclaim_strength_confirm",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "BUY",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "",
        "modifier_primary_reason": "nas_upper_reclaim_wait_hide_without_probe",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UNKNOWN",
        "decision_row_key": "row-nas-upper-reclaim-hidden-1",
    }
    rows = {
        "BTCUSD": [],
        "NAS100": [base_row],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_pa0_baseline_skips_hidden_xau_upper_reclaim_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "XAUUSD",
        "time": "2026-04-01T16:36:21",
        "action": "",
        "observe_reason": "upper_reclaim_strength_confirm",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "OBSERVE",
        "check_side": "BUY",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "",
        "modifier_primary_reason": "xau_upper_reclaim_wait_hide_without_probe",
        "entry_ready": False,
        "box_state": "UPPER",
        "bb_state": "UNKNOWN",
        "decision_row_key": "row-xau-upper-reclaim-hidden-1",
    }
    rows = {
        "BTCUSD": [],
        "NAS100": [],
        "XAUUSD": [base_row],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_pa0_baseline_skips_hidden_btc_lower_rebound_forecast_wait_without_probe_from_problem_seed_queues():
    base_row = {
        "symbol": "BTCUSD",
        "time": "2026-03-31T18:35:16",
        "action": "",
        "observe_reason": "lower_rebound_confirm",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "",
        "check_candidate": True,
        "check_stage": "PROBE",
        "check_side": "BUY",
        "display_ready": False,
        "display_score": 0.0,
        "display_repeat_count": 0,
        "display_strength_level": 0,
        "display_importance_tier": "high",
        "modifier_primary_reason": "btc_lower_rebound_forecast_wait_hide_without_probe",
        "entry_ready": False,
        "box_state": "LOWER",
        "bb_state": "BREAKDOWN",
        "decision_row_key": "row-btc-lower-rebound-forecast-hidden-1",
    }
    rows = {
        "BTCUSD": [base_row],
        "NAS100": [],
        "XAUUSD": [],
    }

    assert len(module._build_must_show_missing_candidates(rows)) == 0
    assert len(module._build_must_hide_leakage_candidates(rows)) == 0
    assert len(module._build_must_block_candidates(rows)) == 0


def test_resolve_closed_history_path_prefers_runtime_data_trades_path(tmp_path):
    preferred = tmp_path / "data" / "trades" / "trade_closed_history.csv"
    legacy = tmp_path / "trade_closed_history.csv"
    preferred.parent.mkdir(parents=True, exist_ok=True)
    preferred.write_text("ticket\n1\n", encoding="utf-8")
    legacy.write_text("ticket\n2\n", encoding="utf-8")

    resolved = module._resolve_closed_history_path(
        preferred_path=preferred,
        legacy_fallback_path=legacy,
    )

    assert resolved == preferred


def test_resolve_closed_history_path_falls_back_to_legacy_root_file(tmp_path):
    preferred = tmp_path / "data" / "trades" / "trade_closed_history.csv"
    legacy = tmp_path / "trade_closed_history.csv"
    legacy.write_text("ticket\n2\n", encoding="utf-8")

    resolved = module._resolve_closed_history_path(
        preferred_path=preferred,
        legacy_fallback_path=legacy,
    )

    assert resolved == legacy


def test_pa0_baseline_ignores_tiny_peak_defensive_losses_for_must_release_and_bad_exit():
    rows = {
        "BTCUSD": [
            {
                "ticket": "1",
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-04-01 10:00:00",
                "close_time": "2026-04-01 10:05:00",
                "entry_reason": "",
                "exit_reason": "Protect Exit | hard_guard=adverse",
                "net_pnl_after_cost": -0.9,
                "giveback_usd": 1.2,
                "peak_profit_at_exit": 0.02,
                "post_exit_mfe": 0.0,
                "post_exit_mae": 0.0,
                "wait_quality_label": "no_wait",
                "loss_quality_label": "neutral_loss",
                "exit_policy_profile": "conservative",
                "status": "CLOSED",
            },
            {
                "ticket": "2",
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-04-01 11:00:00",
                "close_time": "2026-04-01 11:05:00",
                "entry_reason": "",
                "exit_reason": "Protect Exit | hard_guard=adverse",
                "net_pnl_after_cost": -0.9,
                "giveback_usd": 1.2,
                "peak_profit_at_exit": 0.80,
                "post_exit_mfe": 0.0,
                "post_exit_mae": 0.0,
                "wait_quality_label": "no_wait",
                "loss_quality_label": "neutral_loss",
                "exit_policy_profile": "conservative",
                "status": "CLOSED",
            },
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    must_release = module._build_must_release_candidates(rows)
    bad_exit = module._build_bad_exit_candidates(rows)

    assert [row["ticket"] for row in must_release] == ["2"]
    assert [row["ticket"] for row in bad_exit] == ["2"]


def test_pa0_baseline_excludes_no_green_bad_loss_from_must_release_but_keeps_meaningful_giveback():
    rows = {
        "XAUUSD": [
            {
                "ticket": "1",
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-04-01 12:00:00",
                "close_time": "2026-04-01 12:02:00",
                "entry_reason": "",
                "exit_reason": "Exit Context, TopDown 30M: bullish (+30점)",
                "net_pnl_after_cost": -2.4,
                "giveback_usd": 0.0,
                "peak_profit_at_exit": 0.0,
                "post_exit_mfe": 0.0,
                "post_exit_mae": 0.0,
                "wait_quality_label": "no_wait",
                "loss_quality_label": "bad_loss",
                "exit_policy_profile": "conservative",
                "status": "CLOSED",
            },
            {
                "ticket": "2",
                "symbol": "XAUUSD",
                "direction": "SELL",
                "open_time": "2026-04-01 12:10:00",
                "close_time": "2026-04-01 12:15:00",
                "entry_reason": "",
                "exit_reason": "Exit Context, TopDown 30M: bullish (+30점)",
                "net_pnl_after_cost": 0.0,
                "giveback_usd": 1.1,
                "peak_profit_at_exit": 2.4,
                "post_exit_mfe": 0.0,
                "post_exit_mae": 0.0,
                "wait_quality_label": "no_wait",
                "loss_quality_label": "non_loss",
                "exit_policy_profile": "conservative",
                "status": "CLOSED",
            },
        ],
        "BTCUSD": [],
        "NAS100": [],
    }

    must_release = module._build_must_release_candidates(rows)
    bad_exit = module._build_bad_exit_candidates(rows)

    assert [row["ticket"] for row in must_release] == ["2"]
    assert [row["ticket"] for row in bad_exit] == ["2"]


def test_pa0_baseline_excludes_weak_peak_adverse_protect_and_stop_from_bad_exit():
    rows = {
        "BTCUSD": [
            {
                "ticket": "1",
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-04-01 13:00:00",
                "close_time": "2026-04-01 13:02:00",
                "entry_reason": "",
                "exit_reason": "Protect Exit | hard_guard=adverse",
                "net_pnl_after_cost": 0.0,
                "giveback_usd": 0.84,
                "peak_profit_at_exit": 0.04,
                "post_exit_mfe": 0.0,
                "post_exit_mae": 0.0,
                "wait_quality_label": "no_wait",
                "loss_quality_label": "bad_loss",
                "exit_policy_profile": "conservative",
                "status": "CLOSED",
            },
            {
                "ticket": "2",
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-04-01 13:10:00",
                "close_time": "2026-04-01 13:14:00",
                "entry_reason": "",
                "exit_reason": "Adverse Stop | hard_guard=adverse | adverse_wait=timeout(18s)",
                "net_pnl_after_cost": 0.0,
                "giveback_usd": 0.97,
                "peak_profit_at_exit": -0.47,
                "post_exit_mfe": 0.0,
                "post_exit_mae": 0.0,
                "wait_quality_label": "unnecessary_wait",
                "loss_quality_label": "bad_loss",
                "exit_policy_profile": "conservative",
                "status": "CLOSED",
            },
            {
                "ticket": "3",
                "symbol": "BTCUSD",
                "direction": "BUY",
                "open_time": "2026-04-01 13:20:00",
                "close_time": "2026-04-01 13:28:00",
                "entry_reason": "",
                "exit_reason": "Protect Exit | hard_guard=adverse",
                "net_pnl_after_cost": 0.0,
                "giveback_usd": 1.12,
                "peak_profit_at_exit": 1.84,
                "post_exit_mfe": 0.0,
                "post_exit_mae": 0.0,
                "wait_quality_label": "no_wait",
                "loss_quality_label": "bad_loss",
                "exit_policy_profile": "conservative",
                "status": "CLOSED",
            },
        ],
        "NAS100": [],
        "XAUUSD": [],
    }

    bad_exit = module._build_bad_exit_candidates(rows)

    assert [row["ticket"] for row in bad_exit] == ["3"]


def test_pa0_baseline_excludes_exit_now_best_no_wait_exit_context_from_bad_exit():
    rows = {
        "NAS100": [
            {
                "ticket": "1",
                "symbol": "NAS100",
                "direction": "SELL",
                "open_time": "2026-03-24 16:17:21",
                "close_time": "2026-03-24 16:20:07",
                "entry_reason": "[AUTO] sell",
                "exit_reason": "Exit Context, Structure: H1 bull stack (+80점) | Flow: BB20 breakout up (+150점)",
                "net_pnl_after_cost": 0.0,
                "giveback_usd": 1.04,
                "peak_profit_at_exit": 2.34,
                "post_exit_mfe": 0.0,
                "post_exit_mae": 0.0,
                "wait_quality_label": "no_wait",
                "loss_quality_label": "non_loss",
                "exit_policy_profile": "conservative",
                "decision_reason": "exit_now_best",
                "status": "CLOSED",
            },
            {
                "ticket": "2",
                "symbol": "NAS100",
                "direction": "SELL",
                "open_time": "2026-03-24 16:17:21",
                "close_time": "2026-03-24 16:20:07",
                "entry_reason": "[AUTO] sell",
                "exit_reason": "Exit Context, Structure: H1 bull stack (+80점) | Flow: BB20 breakout up (+150점)",
                "net_pnl_after_cost": 0.0,
                "giveback_usd": 1.04,
                "peak_profit_at_exit": 2.34,
                "post_exit_mfe": 0.64,
                "post_exit_mae": 0.0,
                "wait_quality_label": "no_wait",
                "loss_quality_label": "non_loss",
                "exit_policy_profile": "conservative",
                "decision_reason": "exit_now_best",
                "status": "CLOSED",
            },
        ],
        "BTCUSD": [],
        "XAUUSD": [],
    }

    bad_exit = module._build_bad_exit_candidates(rows)

    assert [row["ticket"] for row in bad_exit] == ["2"]


def test_pa0_baseline_normalizes_closed_trade_decision_fields_for_bad_exit_narrowing():
    normalized = module._normalize_closed_trade_row(
        {
            "ticket": "1",
            "symbol": "NAS100",
            "direction": "SELL",
            "open_time": "2026-03-24 16:17:21",
            "close_time": "2026-03-24 16:20:07",
            "entry_reason": "[AUTO] sell",
            "exit_reason": "Exit Context, Structure: H1 bull stack (+80점)",
            "net_pnl_after_cost": 0.0,
            "giveback_usd": 1.04,
            "peak_profit_at_exit": 2.34,
            "post_exit_mfe": 0.0,
            "post_exit_mae": 0.0,
            "wait_quality_label": "no_wait",
            "loss_quality_label": "non_loss",
            "exit_policy_profile": "conservative",
            "exit_wait_state": "NONE",
            "exit_wait_decision": "",
            "decision_reason": "exit_now_best",
            "utility_exit_now": 1.216372,
            "u_wait_be": 0.28176,
            "u_wait_tp1": -999.0,
            "status": "CLOSED",
        }
    )

    assert normalized["decision_reason"] == "exit_now_best"
    assert normalized["exit_wait_state"] == "NONE"
    assert normalized["utility_exit_now"] == 1.216372
    assert module._supports_bad_exit_non_loss_seed(normalized) is False
