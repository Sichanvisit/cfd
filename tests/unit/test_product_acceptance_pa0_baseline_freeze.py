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
        "check_stage": "PROBE",
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
