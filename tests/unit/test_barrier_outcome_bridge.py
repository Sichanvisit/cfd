import json
from datetime import datetime

from backend.services.barrier_outcome_bridge import (
    _build_correct_wait_casebook_v1,
    _build_timing_edge_absent_casebook_v1,
    _soft_relief_watch_label_candidate,
    _wait_outcome_surface_v1,
    build_barrier_outcome_bridge_report,
    build_barrier_outcome_bridge_rows,
    render_barrier_outcome_bridge_markdown,
)
from backend.services.barrier_state25_runtime_bridge import build_barrier_state25_runtime_bridge_v1


def _base_row(*, ts: int, action: str, outcome: str, blocked: bool, barrier_value: float) -> dict:
    row = {
        "symbol": "BTCUSD",
        "time": ts,
        "signal_bar_ts": ts,
        "outcome": outcome,
        "direction": action,
        "action": action,
        "setup_side": action,
        "my_position_count": 0 if blocked else 1,
        "entry_setup_id": "range_lower_reversal_buy" if action == "BUY" else "range_upper_reversal_sell",
        "entry_wait_state": "CENTER",
        "entry_wait_decision": "wait_lock" if blocked else "enter_ready",
        "observe_reason": "barrier_guard" if blocked else "",
        "blocked_by": "barrier_guard" if blocked else "",
        "entry_fill_price": 100.0,
        "expected_adverse_depth": 1.0,
        "transition_forecast_v1": {
            "p_buy_confirm": 0.82 if action == "BUY" else 0.18,
            "p_sell_confirm": 0.18 if action == "BUY" else 0.82,
            "p_false_break": 0.14,
            "p_continuation_success": 0.68,
            "metadata": {"mapper_version": "transition_mapper_v1", "side_separation": 0.44},
        },
        "trade_management_forecast_v1": {
            "p_continue_favor": 0.71,
            "p_fail_now": 0.16,
            "metadata": {"mapper_version": "management_mapper_v1"},
        },
        "forecast_gap_metrics_v1": {
            "wait_confirm_gap": 0.18,
            "hold_exit_gap": 0.14,
            "same_side_flip_gap": 0.09,
            "belief_barrier_tension_gap": 0.08,
        },
        "belief_state_v1": {
            "buy_belief": 0.74 if action == "BUY" else 0.18,
            "sell_belief": 0.74 if action == "SELL" else 0.18,
            "buy_persistence": 0.46 if action == "BUY" else 0.12,
            "sell_persistence": 0.46 if action == "SELL" else 0.12,
            "belief_spread": 0.56,
            "flip_readiness": 0.18,
            "belief_instability": 0.18,
            "dominant_side": action,
            "dominant_mode": "continuation",
            "buy_streak": 3 if action == "BUY" else 0,
            "sell_streak": 3 if action == "SELL" else 0,
            "transition_age": 3,
        },
        "evidence_vector_v1": {
            "buy_total_evidence": 0.66 if action == "BUY" else 0.19,
            "sell_total_evidence": 0.66 if action == "SELL" else 0.19,
            "buy_continuation_evidence": 0.46 if action == "BUY" else 0.08,
            "sell_continuation_evidence": 0.46 if action == "SELL" else 0.08,
            "buy_reversal_evidence": 0.14,
            "sell_reversal_evidence": 0.14,
        },
        "barrier_state_v1": {
            "buy_barrier": barrier_value if action == "BUY" else 0.18,
            "sell_barrier": barrier_value if action == "SELL" else 0.18,
            "conflict_barrier": 0.22,
            "middle_chop_barrier": 0.11,
            "direction_policy_barrier": 0.18,
            "liquidity_barrier": 0.28,
            "metadata": {
                "edge_turn_relief_score": 0.26 if not blocked else 0.12,
                "breakout_fade_barrier_score": 0.33,
                "execution_friction_barrier_score": 0.29,
                "event_risk_barrier_score": 0.21,
                "barrier_reasons": {
                    ("buy_barrier" if action == "BUY" else "sell_barrier"): "direction_barrier",
                },
                "policy_side_barriers": {
                    "buy_policy": "allow" if action == "BUY" else "restrict",
                    "sell_policy": "allow" if action == "SELL" else "restrict",
                },
                "edge_turn_relief_v1": {
                    "buy_relief": 0.30 if (action == "BUY" and not blocked) else 0.08,
                    "sell_relief": 0.30 if (action == "SELL" and not blocked) else 0.08,
                },
            },
        },
    }
    row["barrier_state25_runtime_bridge_v1"] = build_barrier_state25_runtime_bridge_v1(row)
    return row


def _avoided_loss_future_bars() -> list[dict]:
    prices = [
        (1060, 100.00, 100.12, 99.45, 99.58),
        (1120, 99.58, 99.86, 99.08, 99.22),
        (1180, 99.22, 99.42, 98.96, 99.10),
        (1240, 99.10, 99.38, 98.92, 99.05),
        (1300, 99.05, 99.40, 98.90, 99.24),
        (1360, 99.24, 99.44, 99.00, 99.18),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def _correct_wait_future_bars() -> list[dict]:
    prices = [
        (2060, 100.00, 100.03, 99.58, 99.70),
        (2120, 99.70, 99.78, 99.35, 99.42),
        (2180, 99.42, 99.68, 99.38, 99.60),
        (2240, 99.60, 99.94, 99.54, 99.88),
        (2300, 99.88, 100.12, 99.80, 100.06),
        (2360, 100.06, 100.28, 100.00, 100.24),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def _relief_failure_future_bars() -> list[dict]:
    prices = [
        (4060, 100.00, 100.05, 99.66, 99.74),
        (4120, 99.74, 99.88, 99.22, 99.30),
        (4180, 99.30, 99.52, 98.98, 99.10),
        (4240, 99.10, 99.36, 98.94, 99.06),
        (4300, 99.06, 99.34, 98.90, 99.00),
        (4360, 99.00, 99.28, 98.88, 98.96),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def _missed_profit_recovery_future_bars() -> list[dict]:
    prices = [
        (11060, 100.00, 100.22, 99.72, 100.10),
        (11120, 100.10, 100.48, 99.66, 100.30),
        (11180, 100.30, 100.76, 99.64, 100.58),
        (11240, 100.58, 100.88, 99.62, 100.80),
        (11300, 100.80, 100.92, 99.60, 100.84),
        (11360, 100.84, 100.95, 99.60, 100.90),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def _correct_wait_recovery_future_bars() -> list[dict]:
    prices = [
        (12060, 100.00, 100.05, 99.62, 99.70),
        (12120, 99.70, 99.78, 99.55, 99.74),
        (12180, 99.74, 99.92, 99.68, 99.86),
        (12240, 99.86, 100.02, 99.82, 99.96),
        (12300, 99.96, 100.12, 99.92, 100.06),
        (12360, 100.06, 100.20, 100.02, 100.14),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def _relief_success_recovery_future_bars() -> list[dict]:
    prices = [
        (13060, 100.00, 100.22, 99.72, 100.10),
        (13120, 100.10, 100.34, 99.68, 100.18),
        (13180, 100.18, 100.44, 99.66, 100.24),
        (13240, 100.24, 100.56, 99.70, 100.36),
        (13300, 100.36, 100.60, 99.72, 100.44),
        (13360, 100.44, 100.58, 99.74, 100.40),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def _relief_failure_gap_recovery_future_bars() -> list[dict]:
    prices = [
        (14060, 100.00, 100.87, 98.80, 99.10),
        (14120, 99.10, 99.40, 97.60, 97.90),
        (14180, 97.90, 98.20, 97.39, 97.60),
        (14240, 97.60, 98.10, 97.50, 97.90),
        (14300, 97.90, 98.00, 97.70, 97.85),
        (14360, 97.85, 97.95, 97.80, 97.88),
    ]
    return [{"symbol": "BTCUSD", "time": ts, "open": op, "high": hi, "low": lo, "close": cl} for ts, op, hi, lo, cl in prices]


def _shifted_future_bars(bars: list[dict], *, delta: int) -> list[dict]:
    shifted: list[dict] = []
    for row in bars:
        copied = dict(row)
        copied["time"] = int(copied["time"]) + int(delta)
        shifted.append(copied)
    return shifted


def test_barrier_outcome_bridge_rows_label_avoided_loss():
    anchor = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[anchor],
        future_bar_rows=_avoided_loss_future_bars(),
    )

    assert len(rows) == 1
    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_anchor_context"] == "wait_block"
    assert outcome["barrier_outcome_label"] == "avoided_loss"
    assert outcome["barrier_label_confidence"] in {"high", "medium"}
    assert outcome["actual_engine_action_family"] == "wait_or_block"
    assert outcome["barrier_recommended_family"] == "block_bias"
    assert outcome["recommended_action_family"] == "wait_or_block"
    assert outcome["drift_status"] == "aligned"
    assert outcome["drift_pair_key"] == "wait_or_block->wait_or_block"
    assert outcome["counterfactual_outcome_family"] == "aligned_wait_gain"
    assert outcome["counterfactual_cost_delta_r"] > 0.0
    assert "wait_or_block|block_bias|aligned_wait_gain|avoided_loss|positive" in outcome["counterfactual_reason_summary"]


def test_barrier_outcome_bridge_rows_reconstruct_bridge_from_json_string_barrier_state():
    anchor = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
    anchor.pop("barrier_state25_runtime_bridge_v1", None)
    anchor["barrier_state_v1"] = json.dumps(anchor["barrier_state_v1"], ensure_ascii=False)

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[anchor],
        future_bar_rows=_avoided_loss_future_bars(),
    )

    assert len(rows) == 1
    bridge = rows[0]["barrier_state25_runtime_bridge_v1"]
    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert bridge["barrier_runtime_summary_v1"]["available"] is True
    assert outcome["skip_reason"] == ""
    assert outcome["barrier_outcome_label"] == "avoided_loss"


def test_barrier_outcome_bridge_rows_promote_partial_coverage_to_weak_usable():
    anchor = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[anchor],
        future_bar_rows=_avoided_loss_future_bars()[:4],
    )

    assert len(rows) == 1
    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == "avoided_loss"
    assert outcome["future_bar_count"] == 4
    assert outcome["future_bar_coverage_ratio"] < 0.70
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["bridge_quality_status"] == "usable"


def test_barrier_outcome_bridge_rows_label_correct_wait():
    anchor = _base_row(ts=2000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.52)
    relief = _base_row(ts=2120, action="BUY", outcome="entered", blocked=False, barrier_value=0.24)
    relief["entry_fill_price"] = 99.40

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[anchor, relief],
        future_bar_rows=_correct_wait_future_bars(),
    )

    anchor_row = next(row for row in rows if int(row["time"]) == 2000)
    outcome = anchor_row["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == "correct_wait"
    assert outcome["BetterEntryGain_6"] >= 0.35
    assert outcome["LaterContinuation_F_6"] >= 0.60


def test_barrier_outcome_bridge_rows_label_relief_failure():
    relief = _base_row(ts=4000, action="BUY", outcome="entered", blocked=False, barrier_value=0.24)

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[relief],
        future_bar_rows=_relief_failure_future_bars(),
    )

    assert len(rows) == 1
    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_anchor_context"] == "relief_release"
    assert outcome["barrier_outcome_label"] == "relief_failure"


def test_barrier_outcome_bridge_report_summarizes_label_counts():
    avoided = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
    relief = _base_row(ts=4000, action="BUY", outcome="entered", blocked=False, barrier_value=0.24)

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[avoided, relief],
        future_bar_rows=(_avoided_loss_future_bars() + _relief_failure_future_bars()),
    )

    assert report["summary"]["raw_bridge_candidate_count"] == 2
    assert report["summary"]["bridged_row_count"] == 2
    assert report["summary"]["strict_rows"] == 2
    assert report["summary"]["usable_rows"] == 0
    assert report["summary"]["skip_rows"] == 0
    assert report["coverage"]["label_counts"]["avoided_loss"] >= 1
    assert report["coverage"]["label_counts"]["relief_failure"] >= 1
    assert report["coverage"]["coverage_bucket_counts"]["strict"] == 2
    assert report["coverage"]["dashboard"]["total_anchor_rows"] == 2
    assert report["coverage"]["dashboard"]["strict_share"] == 1.0
    assert report["coverage"]["usage_policy_v1"]["compare_gate_usage"] == "strict_only"
    assert report["summary"]["counterfactual_cost_delta_r_mean"] != 0.0
    assert report["counterfactual_audit"]["actual_engine_action_family_counts"]["wait_or_block"] >= 1
    assert report["counterfactual_audit"]["actual_engine_action_family_counts"]["enter"] >= 1
    assert report["counterfactual_audit"]["barrier_recommended_family_counts"]["block_bias"] >= 1
    assert report["counterfactual_audit"]["counterfactual_outcome_family_counts"]["aligned_wait_gain"] >= 1


def test_barrier_outcome_bridge_report_tracks_drift_audit_by_scene_and_barrier_family():
    aligned_wait = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
    mismatch_enter = _base_row(ts=3000, action="BUY", outcome="entered", blocked=False, barrier_value=0.72)

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[aligned_wait, mismatch_enter],
        future_bar_rows=(_avoided_loss_future_bars() + _relief_failure_future_bars()),
    )

    drift = report["drift_audit"]
    assert drift["aligned_rows"] >= 1
    assert drift["mismatch_rows"] == 1
    assert drift["mismatch_rate"] > 0.0
    assert drift["normalized_actual_vs_target_action_counts"]["wait_or_block->wait_or_block"] >= 1
    assert drift["mismatch_action_pair_counts"]["enter->wait_or_block"] == 1
    assert drift["top_mismatch_action_pairs"][0]["key"] == "enter->wait_or_block"
    assert drift["top_symbol_mismatch"][0]["key"] == "BTCUSD"
    assert drift["top_symbol_mismatch"][0]["count"] == 1
    assert drift["top_scene_family_mismatch"]
    assert drift["top_barrier_family_mismatch"]
    assert drift["top_repeated_mismatch_cases"]


def test_barrier_outcome_bridge_report_tracks_skip_reasons_in_dashboard():
    blocked = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[blocked],
        future_bar_rows=[],
    )

    assert report["summary"]["strict_rows"] == 0
    assert report["summary"]["skip_rows"] == 1
    assert report["coverage"]["coverage_bucket_counts"]["skip"] == 1
    assert report["coverage"]["skip_reason_counts"]["insufficient_future_bars"] == 1
    top_skip = report["coverage"]["dashboard"]["top_skip_reasons"]
    assert top_skip[0]["key"] == "insufficient_future_bars"
    assert top_skip[0]["count"] == 1


def test_barrier_outcome_bridge_report_builds_bias_baseline_for_strict_and_usable_rows():
    strict_row = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
    usable_row = _base_row(ts=2000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
    future_bars = _avoided_loss_future_bars() + _shifted_future_bars(_avoided_loss_future_bars()[:4], delta=1000)

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[strict_row, usable_row],
        future_bar_rows=future_bars,
    )

    bias = report["bias_baseline_v1"]
    label_distribution = bias["label_distribution"]
    assert bias["contract_version"] == "barrier_bias_baseline_v1"
    assert label_distribution["strict"]["counts"]["avoided_loss"] == 1
    assert label_distribution["usable"]["counts"]["avoided_loss"] == 1
    assert label_distribution["combined"]["total_rows"] == 2
    assert label_distribution["by_symbol"]["BTCUSD"]["combined"]["counts"]["avoided_loss"] == 2
    combined_cost = bias["cost_balance"]["combined"]
    assert combined_cost["loss_avoided_r"]["row_count"] == 2
    assert combined_cost["loss_avoided_r"]["mean"] > 0.0
    drift_baseline = bias["drift_baseline"]
    assert drift_baseline["top_normalized_action_pairs"]
    assert drift_baseline["top_normalized_action_pairs"][0]["key"] == "wait_or_block->wait_or_block"


def test_barrier_outcome_bridge_markdown_includes_bias_baseline_section():
    strict_row = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
    usable_row = _base_row(ts=2000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
    future_bars = _avoided_loss_future_bars() + _shifted_future_bars(_avoided_loss_future_bars()[:4], delta=1000)

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[strict_row, usable_row],
        future_bar_rows=future_bars,
    )
    markdown = render_barrier_outcome_bridge_markdown(report)

    assert "## Bias Baseline" in markdown
    assert "## Bias Recovery" in markdown
    assert "## Wait Outcome Family" in markdown
    assert "## Correct-Wait Casebook" in markdown
    assert "## Timing-Edge-Absent Casebook" in markdown
    assert "### Strict Label Distribution" in markdown
    assert "### Combined Cost Balance" in markdown


def test_wait_outcome_surface_v1_maps_wait_clusters_to_family_and_subtype():
    missed_profit_surface = _wait_outcome_surface_v1(
        barrier_outcome_label="missed_profit",
        barrier_label_confidence="weak_usable",
        coverage_bucket="usable",
        weak_candidate_reason="soft_missed_profit_bridge_recovery",
        anchor_context="wait_block",
        blocking_reason="timing_edge_absent",
        counterfactual_cost_delta_r=-0.44,
        better_entry_gain_6=0.0,
        later_continuation_f_6=0.16,
        loss_avoided_r=1.02,
        profit_missed_r=1.33,
        wait_value_r=0.12,
        release_f_6=0.0,
        release_a_6=0.0,
    )
    assert missed_profit_surface["wait_outcome_family"] == "failed_wait"
    assert missed_profit_surface["wait_outcome_subtype"] == "wait_but_missed_move"
    assert missed_profit_surface["wait_outcome_usage_bucket"] == "usable"

    zero_edge_surface = _wait_outcome_surface_v1(
        barrier_outcome_label="",
        barrier_label_confidence="low_skip",
        coverage_bucket="skip",
        weak_candidate_reason="",
        anchor_context="wait_block",
        blocking_reason="timing_edge_absent",
        counterfactual_cost_delta_r=0.0,
        better_entry_gain_6=0.0,
        later_continuation_f_6=0.0,
        loss_avoided_r=0.88,
        profit_missed_r=0.41,
        wait_value_r=0.0,
        release_f_6=0.0,
        release_a_6=0.0,
    )
    assert zero_edge_surface["wait_outcome_family"] == "failed_wait"
    assert zero_edge_surface["wait_outcome_subtype"] == "wait_without_timing_edge"
    assert zero_edge_surface["wait_outcome_usage_bucket"] == "diagnostic"

    small_value_surface = _wait_outcome_surface_v1(
        barrier_outcome_label="avoided_loss",
        barrier_label_confidence="high",
        coverage_bucket="strict",
        weak_candidate_reason="",
        anchor_context="wait_block",
        blocking_reason="timing_edge_absent",
        counterfactual_cost_delta_r=1.0,
        better_entry_gain_6=0.0,
        later_continuation_f_6=0.21,
        loss_avoided_r=1.0,
        profit_missed_r=0.21,
        wait_value_r=0.21,
        release_f_6=0.0,
        release_a_6=0.0,
    )
    assert small_value_surface["wait_outcome_family"] == "neutral_wait"
    assert small_value_surface["wait_outcome_subtype"] == "small_value_wait"
    assert small_value_surface["wait_outcome_usage_bucket"] == "diagnostic"

    correct_wait_surface = _wait_outcome_surface_v1(
        barrier_outcome_label="correct_wait",
        barrier_label_confidence="high",
        coverage_bucket="strict",
        weak_candidate_reason="",
        anchor_context="wait_block",
        blocking_reason="resolved_correct_wait",
        counterfactual_cost_delta_r=0.62,
        better_entry_gain_6=0.40,
        later_continuation_f_6=0.64,
        loss_avoided_r=0.28,
        profit_missed_r=0.12,
        wait_value_r=0.58,
        release_f_6=0.0,
        release_a_6=0.0,
    )
    assert correct_wait_surface["wait_outcome_family"] == "timing_improvement"
    assert correct_wait_surface["wait_outcome_subtype"] == "correct_wait_strict"
    assert correct_wait_surface["wait_outcome_usage_bucket"] == "strict"


def test_barrier_outcome_bridge_report_builds_wait_family_distribution():
    missed_profit_row = _base_row(ts=11000, action="BUY", outcome="wait", blocked=True, barrier_value=0.48)
    correct_wait_anchor = _base_row(ts=12000, action="BUY", outcome="wait", blocked=True, barrier_value=0.44)
    correct_wait_relief = _base_row(ts=12120, action="BUY", outcome="entered", blocked=False, barrier_value=0.18)
    correct_wait_relief["entry_fill_price"] = 99.75

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[missed_profit_row, correct_wait_anchor, correct_wait_relief],
        future_bar_rows=(_missed_profit_recovery_future_bars() + _correct_wait_recovery_future_bars()),
    )

    wait_family = report["wait_family_v1"]
    assert wait_family["contract_version"] == "wait_outcome_v1"
    assert wait_family["family_distribution"]["counts"]["failed_wait"] >= 1
    assert wait_family["family_distribution"]["counts"]["timing_improvement"] >= 1
    assert wait_family["subtype_distribution"]["counts"]["wait_but_missed_move"] >= 1
    assert wait_family["subtype_distribution"]["counts"]["correct_wait_strict"] >= 1
    assert wait_family["by_barrier_label"]["missed_profit"]["counts"]["failed_wait"] >= 1
    assert wait_family["by_barrier_label"]["correct_wait"]["counts"]["timing_improvement"] >= 1


def test_barrier_outcome_bridge_report_splits_pre_context_from_semantic_coverage():
    pre_context_row = {
        "symbol": "BTCUSD",
        "time": 900,
        "signal_bar_ts": 900,
        "action": "BUY",
        "outcome": "skipped",
        "blocked_by": "max_positions_reached",
        "barrier_state_v1": {},
    }
    strict_row = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[pre_context_row, strict_row],
        future_bar_rows=_avoided_loss_future_bars(),
    )

    summary = report["summary"]
    dashboard = report["coverage"]["dashboard"]
    assert summary["pre_context_skip_rows"] == 1
    assert summary["semantic_anchor_rows"] == 1
    assert summary["semantic_skip_rows"] == 0
    assert dashboard["pre_context_skip_rows"] == 1
    assert dashboard["semantic_anchor_rows"] == 1
    assert dashboard["strict_share_ex_pre_context"] == 1.0
    assert dashboard["usable_share_ex_pre_context"] == 0.0
    assert dashboard["semantic_skip_share_ex_pre_context"] == 0.0


def test_barrier_outcome_bridge_report_readiness_gate_flags_coverage_blockers():
    blocked = _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
    runtime_status = {"updated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "loop_count": 1216}

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[blocked],
        future_bar_rows=_avoided_loss_future_bars(),
        runtime_status=runtime_status,
    )

    readiness = report["readiness_gate"]
    assert readiness["ready"] is False
    assert readiness["stage"] == "blocked_coverage"
    assert readiness["checks"]["runtime_heartbeat_ready"] is True
    assert "semantic_anchor_rows_below_threshold" in readiness["blockers"]
    assert "strict_rows_below_threshold" in readiness["blockers"]


def test_barrier_outcome_bridge_report_readiness_gate_marks_ready_after_coverage_closes():
    anchors = [
        _base_row(ts=1000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
        for _ in range(200)
    ]
    runtime_status = {"updated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "loop_count": 1216}

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=anchors,
        future_bar_rows=_avoided_loss_future_bars(),
        runtime_status=runtime_status,
    )

    readiness = report["readiness_gate"]
    assert readiness["ready"] is True
    assert readiness["stage"] == "ready_for_next_owner"
    assert readiness["checks"]["covered_share_ready"] is True
    assert readiness["checks"]["strict_rows_ready"] is True
    assert readiness["checks"]["runtime_heartbeat_ready"] is True
    assert readiness["blockers"] == []


def test_barrier_outcome_bridge_rows_classify_stale_future_bar_dataset_separately():
    row = _base_row(ts=5000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.72)
    row["signal_bar_ts"] = 5000
    row["entry_fill_price"] = ""
    row["open_price"] = ""
    row["entry_request_price"] = ""
    row["close_price"] = ""
    row["expected_adverse_depth"] = ""
    row["forecast_expected_adverse_depth"] = ""
    row.pop("barrier_state25_runtime_bridge_v1", None)

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=_avoided_loss_future_bars(),
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["skip_reason"] == "future_bar_dataset_stale"
    assert outcome["barrier_outcome_reason"] == "future_bar_dataset_stale"
    assert outcome["future_bar_count"] == 0
    assert outcome["anchor_price"] == 0.0


def test_barrier_outcome_bridge_rows_split_light_block_observe_only_taxonomy():
    row = _base_row(ts=5000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.28)
    row["blocked_by"] = ""
    row["observe_reason"] = ""
    row["barrier_state25_runtime_bridge_v1"] = build_barrier_state25_runtime_bridge_v1(row)
    future_bars = [
        {"symbol": "BTCUSD", "time": 5060, "open": 100.00, "high": 100.08, "low": 99.70, "close": 99.78},
        {"symbol": "BTCUSD", "time": 5120, "open": 99.78, "high": 99.92, "low": 99.42, "close": 99.56},
        {"symbol": "BTCUSD", "time": 5180, "open": 99.56, "high": 99.68, "low": 99.20, "close": 99.34},
        {"symbol": "BTCUSD", "time": 5240, "open": 99.34, "high": 99.46, "low": 99.20, "close": 99.28},
        {"symbol": "BTCUSD", "time": 5300, "open": 99.28, "high": 99.40, "low": 99.18, "close": 99.24},
        {"symbol": "BTCUSD", "time": 5360, "open": 99.24, "high": 99.30, "low": 99.16, "close": 99.22},
    ]

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=future_bars,
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == ""
    assert outcome["barrier_label_confidence"] == "low_skip"
    assert outcome["skip_reason"] == "light_block_loss_avoided_bias"
    assert outcome["barrier_recommended_family"] == "observe_only"
    assert outcome["barrier_blocked_flag"] is False
    assert outcome["normalized_recommended_detail_family_v2"] == "block_bias_soft"
    assert outcome["normalized_recommended_action_family_v2"] == "wait_or_block"
    assert outcome["drift_status_v2"] == "aligned"


def test_barrier_outcome_bridge_rows_promote_wait_bias_loss_dominance_to_weak_usable():
    row = _base_row(ts=6000, action="BUY", outcome="wait", blocked=True, barrier_value=0.48)
    row["barrier_state25_runtime_bridge_v1"] = build_barrier_state25_runtime_bridge_v1(row)
    future_bars = [
        {"symbol": "BTCUSD", "time": 6060, "open": 100.00, "high": 100.55, "low": 98.60, "close": 99.00},
        {"symbol": "BTCUSD", "time": 6120, "open": 99.00, "high": 99.40, "low": 97.80, "close": 98.20},
        {"symbol": "BTCUSD", "time": 6180, "open": 98.20, "high": 98.90, "low": 96.70, "close": 97.10},
        {"symbol": "BTCUSD", "time": 6240, "open": 97.10, "high": 97.60, "low": 96.30, "close": 96.70},
        {"symbol": "BTCUSD", "time": 6300, "open": 96.70, "high": 97.30, "low": 96.10, "close": 96.90},
        {"symbol": "BTCUSD", "time": 6360, "open": 96.90, "high": 100.85, "low": 96.70, "close": 100.40},
    ]

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=future_bars,
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == "avoided_loss"
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["coverage_bucket"] == "usable"
    assert outcome["weak_candidate_used"] is True
    assert outcome["weak_candidate_reason"] == "soft_cost_balance_loss_bias"
    assert outcome["barrier_recommended_family"] == "wait_bias"
    assert outcome["skip_reason"] == ""


def test_barrier_outcome_bridge_rows_promote_effective_wait_block_without_blocked_flag():
    row = _base_row(ts=6500, action="BUY", outcome="wait", blocked=False, barrier_value=0.37)
    row["outcome"] = "wait"
    row["blocked_by"] = ""
    row["observe_reason"] = ""
    row["barrier_state25_runtime_bridge_v1"] = build_barrier_state25_runtime_bridge_v1(row)
    future_bars = [
        {"symbol": "BTCUSD", "time": 6560, "open": 100.00, "high": 100.20, "low": 98.70, "close": 99.10},
        {"symbol": "BTCUSD", "time": 6620, "open": 99.10, "high": 99.20, "low": 97.90, "close": 98.20},
        {"symbol": "BTCUSD", "time": 6680, "open": 98.20, "high": 98.50, "low": 97.10, "close": 97.40},
        {"symbol": "BTCUSD", "time": 6740, "open": 97.40, "high": 97.70, "low": 96.80, "close": 97.00},
        {"symbol": "BTCUSD", "time": 6800, "open": 97.00, "high": 97.30, "low": 96.70, "close": 96.95},
        {"symbol": "BTCUSD", "time": 6860, "open": 96.95, "high": 97.10, "low": 96.80, "close": 96.90},
    ]

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=future_bars,
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == "avoided_loss"
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["coverage_bucket"] == "usable"
    assert outcome["effective_wait_block"] is True
    assert outcome["barrier_blocked_flag"] is False
    assert outcome["weak_candidate_used"] is True
    assert outcome["weak_candidate_reason"] == "soft_cost_balance_loss_bias"
    assert outcome["barrier_recommended_family"] == "wait_bias"
    assert outcome["skip_reason"] == ""


def test_barrier_outcome_bridge_rows_promote_light_block_loss_dominance_to_weak_usable():
    row = _base_row(ts=7000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.26)
    row["blocked_by"] = ""
    row["observe_reason"] = ""
    row["barrier_state25_runtime_bridge_v1"] = build_barrier_state25_runtime_bridge_v1(row)
    future_bars = [
        {"symbol": "BTCUSD", "time": 7060, "open": 100.00, "high": 100.20, "low": 98.90, "close": 99.20},
        {"symbol": "BTCUSD", "time": 7120, "open": 99.20, "high": 99.30, "low": 98.20, "close": 98.40},
        {"symbol": "BTCUSD", "time": 7180, "open": 98.40, "high": 98.70, "low": 97.20, "close": 97.50},
        {"symbol": "BTCUSD", "time": 7240, "open": 97.50, "high": 97.80, "low": 96.90, "close": 97.10},
        {"symbol": "BTCUSD", "time": 7300, "open": 97.10, "high": 97.50, "low": 96.70, "close": 97.00},
        {"symbol": "BTCUSD", "time": 7360, "open": 97.00, "high": 97.20, "low": 96.80, "close": 96.95},
    ]

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=future_bars,
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == "avoided_loss"
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["coverage_bucket"] == "usable"
    assert outcome["weak_candidate_used"] is True
    assert outcome["weak_candidate_reason"] == "soft_light_block_loss_bias"
    assert outcome["barrier_recommended_family"] == "observe_only"
    assert outcome["blocking_bias"] == "LIGHT_BLOCK"
    assert outcome["skip_reason"] == ""


def test_barrier_outcome_bridge_rows_split_wait_bias_unresolved_taxonomy_when_not_promoted():
    row = _base_row(ts=6600, action="BUY", outcome="wait", blocked=False, barrier_value=0.37)
    row["outcome"] = "wait"
    row["blocked_by"] = ""
    row["observe_reason"] = ""
    row["barrier_state25_runtime_bridge_v1"] = build_barrier_state25_runtime_bridge_v1(row)
    future_bars = [
        {"symbol": "BTCUSD", "time": 6660, "open": 100.00, "high": 100.18, "low": 99.42, "close": 99.70},
        {"symbol": "BTCUSD", "time": 6720, "open": 99.70, "high": 100.24, "low": 99.20, "close": 99.55},
        {"symbol": "BTCUSD", "time": 6780, "open": 99.55, "high": 100.30, "low": 99.10, "close": 99.44},
        {"symbol": "BTCUSD", "time": 6840, "open": 99.44, "high": 99.82, "low": 99.05, "close": 99.30},
        {"symbol": "BTCUSD", "time": 6900, "open": 99.30, "high": 99.62, "low": 99.08, "close": 99.22},
        {"symbol": "BTCUSD", "time": 6960, "open": 99.22, "high": 99.50, "low": 99.12, "close": 99.18},
    ]

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=future_bars,
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == ""
    assert outcome["barrier_label_confidence"] == "low_skip"
    assert outcome["effective_wait_block"] is True
    assert outcome["skip_reason"] == "wait_bias_loss_avoided_unresolved"


def test_barrier_outcome_bridge_rows_promote_relief_watch_loss_bias_to_weak_usable():
    row = _base_row(ts=9000, action="BUY", outcome="skipped", blocked=False, barrier_value=0.25)
    row["outcome"] = "skipped"
    row["blocked_by"] = ""
    row["observe_reason"] = ""
    row["barrier_state25_runtime_bridge_v1"] = build_barrier_state25_runtime_bridge_v1(row)
    future_bars = [
        {"symbol": "BTCUSD", "time": 9060, "open": 100.00, "high": 100.10, "low": 98.80, "close": 99.00},
        {"symbol": "BTCUSD", "time": 9120, "open": 99.00, "high": 99.10, "low": 97.80, "close": 98.10},
        {"symbol": "BTCUSD", "time": 9180, "open": 98.10, "high": 98.20, "low": 97.10, "close": 97.30},
        {"symbol": "BTCUSD", "time": 9240, "open": 97.30, "high": 97.50, "low": 96.90, "close": 97.10},
        {"symbol": "BTCUSD", "time": 9300, "open": 97.10, "high": 97.20, "low": 96.90, "close": 97.00},
        {"symbol": "BTCUSD", "time": 9360, "open": 97.00, "high": 97.08, "low": 96.88, "close": 96.95},
    ]

    bridge = build_barrier_state25_runtime_bridge_v1(row)
    bridge["barrier_runtime_summary_v1"]["anchor_context"] = "wait_block"
    bridge["barrier_runtime_summary_v1"]["blocking_bias"] = "RELIEF_READY"
    bridge["barrier_runtime_summary_v1"]["barrier_blocked_flag"] = False
    bridge["barrier_runtime_summary_v1"]["relief_score"] = 0.21
    bridge["barrier_action_hint_v1"]["recommended_family"] = "relief_watch"
    bridge["barrier_action_hint_v1"]["enabled"] = True
    bridge["barrier_action_hint_v1"]["hint_mode"] = "log_only"
    row["barrier_state25_runtime_bridge_v1"] = bridge

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=future_bars,
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == "avoided_loss"
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["coverage_bucket"] == "usable"
    assert outcome["weak_candidate_used"] is True
    assert outcome["weak_candidate_reason"] == "soft_relief_watch_loss_bias"
    assert outcome["barrier_recommended_family"] == "relief_watch"
    assert outcome["skip_reason"] == ""


def test_soft_relief_watch_label_candidate_accepts_small_profit_missed_tail():
    label, reason = _soft_relief_watch_label_candidate(
        anchor_context="wait_block",
        barrier_recommended_family="relief_watch",
        blocking_bias="RELIEF_READY",
        coverage_ratio=1.0,
        dominant_cost_family="loss_avoided",
        cost_balance_margin_r=5.297615,
        loss_avoided_r=5.510858,
        profit_missed_r=0.213243,
        wait_value_r=0.0,
    )

    assert label == "avoided_loss"
    assert reason == "soft_relief_watch_loss_bias"


def test_barrier_outcome_bridge_rows_promote_relief_release_loss_bias_to_weak_usable():
    row = _base_row(ts=10000, action="BUY", outcome="entered", blocked=False, barrier_value=0.25)
    bridge = build_barrier_state25_runtime_bridge_v1(row)
    bridge["barrier_runtime_summary_v1"]["anchor_context"] = "relief_release"
    bridge["barrier_runtime_summary_v1"]["blocking_bias"] = "LIGHT_BLOCK"
    bridge["barrier_runtime_summary_v1"]["barrier_blocked_flag"] = False
    bridge["barrier_action_hint_v1"]["recommended_family"] = "observe_only"
    bridge["barrier_action_hint_v1"]["enabled"] = False
    bridge["barrier_action_hint_v1"]["hint_mode"] = "observe_only"
    row["barrier_state25_runtime_bridge_v1"] = bridge
    future_bars = [
        {"symbol": "BTCUSD", "time": 10060, "open": 100.00, "high": 100.45, "low": 98.40, "close": 99.20},
        {"symbol": "BTCUSD", "time": 10120, "open": 99.20, "high": 99.55, "low": 97.80, "close": 98.10},
        {"symbol": "BTCUSD", "time": 10180, "open": 98.10, "high": 98.40, "low": 96.90, "close": 97.20},
        {"symbol": "BTCUSD", "time": 10240, "open": 97.20, "high": 97.45, "low": 96.80, "close": 97.00},
        {"symbol": "BTCUSD", "time": 10300, "open": 97.00, "high": 97.20, "low": 96.85, "close": 96.95},
        {"symbol": "BTCUSD", "time": 10360, "open": 96.95, "high": 97.05, "low": 96.90, "close": 96.98},
    ]

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=future_bars,
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == "relief_failure"
    assert outcome["barrier_label_confidence"] in {"weak_usable", "medium"}
    assert outcome["coverage_bucket"] in {"usable", "strict"}
    assert outcome["barrier_anchor_context"] == "relief_release"
    assert outcome["skip_reason"] == ""


def test_barrier_outcome_bridge_rows_split_light_block_profit_skip_taxonomy():
    row = _base_row(ts=8000, action="BUY", outcome="skipped", blocked=True, barrier_value=0.24)
    row["blocked_by"] = ""
    row["observe_reason"] = ""
    row["barrier_state25_runtime_bridge_v1"] = build_barrier_state25_runtime_bridge_v1(row)
    future_bars = [
        {"symbol": "BTCUSD", "time": 8060, "open": 100.00, "high": 101.90, "low": 99.80, "close": 101.50},
        {"symbol": "BTCUSD", "time": 8120, "open": 101.50, "high": 103.20, "low": 101.20, "close": 103.00},
        {"symbol": "BTCUSD", "time": 8180, "open": 103.00, "high": 104.70, "low": 102.90, "close": 104.40},
        {"symbol": "BTCUSD", "time": 8240, "open": 104.40, "high": 104.90, "low": 104.10, "close": 104.70},
        {"symbol": "BTCUSD", "time": 8300, "open": 104.70, "high": 104.80, "low": 104.40, "close": 104.55},
        {"symbol": "BTCUSD", "time": 8360, "open": 104.55, "high": 104.66, "low": 104.20, "close": 104.50},
    ]

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=future_bars,
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["barrier_outcome_label"] == "missed_profit"
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["coverage_bucket"] == "usable"
    assert outcome["weak_candidate_used"] is True
    assert outcome["weak_candidate_reason"] == "soft_light_block_profit_bias"
    assert outcome["barrier_recommended_family"] == "observe_only"
    assert outcome["blocking_bias"] == "LIGHT_BLOCK"
    assert outcome["skip_reason"] == ""


def test_barrier_outcome_bridge_rows_recover_missed_profit_with_bias_recovery_surface():
    row = _base_row(ts=11000, action="BUY", outcome="wait", blocked=True, barrier_value=0.48)

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=_missed_profit_recovery_future_bars(),
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    bias_recovery = outcome["bias_recovery_v1"]
    assert bias_recovery["missed_profit_weak_candidate"] is True
    assert outcome["barrier_outcome_label"] == "missed_profit"
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["weak_candidate_reason"] in {
        "soft_missed_profit_bridge_recovery",
        "soft_missed_profit_weak_recovery",
        "soft_missed_profit_strict_recovery",
    }


def test_barrier_outcome_bridge_rows_recover_correct_wait_timing_candidate():
    anchor = _base_row(ts=12000, action="BUY", outcome="wait", blocked=True, barrier_value=0.44)
    relief = _base_row(ts=12120, action="BUY", outcome="entered", blocked=False, barrier_value=0.18)
    relief["entry_fill_price"] = 99.75

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[anchor, relief],
        future_bar_rows=_correct_wait_recovery_future_bars(),
    )

    anchor_row = next(row for row in rows if int(row["time"]) == 12000)
    outcome = anchor_row["barrier_outcome_bridge_v1"]
    bias_recovery = outcome["bias_recovery_v1"]
    assert bias_recovery["correct_wait_timing_candidate"] is True
    assert outcome["barrier_outcome_label"] == "correct_wait"
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["weak_candidate_reason"] in {
        "soft_correct_wait_bridge_recovery",
        "soft_correct_wait_timing_recovery",
    }


def test_barrier_outcome_bridge_rows_recover_relief_success_candidate():
    row = _base_row(ts=13000, action="BUY", outcome="entered", blocked=False, barrier_value=0.24)
    bridge = build_barrier_state25_runtime_bridge_v1(row)
    bridge["barrier_runtime_summary_v1"]["anchor_context"] = "relief_release"
    bridge["barrier_runtime_summary_v1"]["blocking_bias"] = "RELIEF_READY"
    bridge["barrier_runtime_summary_v1"]["barrier_blocked_flag"] = False
    bridge["barrier_action_hint_v1"]["recommended_family"] = "relief_release_bias"
    bridge["barrier_action_hint_v1"]["enabled"] = True
    bridge["barrier_action_hint_v1"]["hint_mode"] = "log_only"
    row["barrier_state25_runtime_bridge_v1"] = bridge

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=_relief_success_recovery_future_bars(),
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    bias_recovery = outcome["bias_recovery_v1"]
    assert bias_recovery["relief_success_weak_candidate"] is True
    assert outcome["barrier_outcome_label"] == "relief_success"
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["weak_candidate_reason"] in {
        "soft_relief_success_bridge_recovery",
        "soft_relief_success_recovery",
    }


def test_barrier_outcome_bridge_rows_recover_relief_failure_from_large_release_gap():
    row = _base_row(ts=14000, action="BUY", outcome="entered", blocked=False, barrier_value=0.24)
    bridge = build_barrier_state25_runtime_bridge_v1(row)
    bridge["barrier_runtime_summary_v1"]["anchor_context"] = "relief_release"
    bridge["barrier_runtime_summary_v1"]["blocking_bias"] = "WAIT_BLOCK"
    bridge["barrier_runtime_summary_v1"]["barrier_blocked_flag"] = False
    bridge["barrier_action_hint_v1"]["recommended_family"] = "wait_bias"
    bridge["barrier_action_hint_v1"]["enabled"] = True
    bridge["barrier_action_hint_v1"]["hint_mode"] = "log_only"
    row["barrier_state25_runtime_bridge_v1"] = bridge

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=_relief_failure_gap_recovery_future_bars(),
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    bias_recovery = outcome["bias_recovery_v1"]
    assert bias_recovery["relief_failure_weak_candidate"] is True
    assert outcome["barrier_outcome_label"] == "relief_failure"
    assert outcome["barrier_label_confidence"] == "weak_usable"
    assert outcome["weak_candidate_reason"] in {
        "soft_relief_failure_recovery",
    }


def test_barrier_outcome_bridge_report_builds_bias_recovery_counts():
    missed_profit_row = _base_row(ts=11000, action="BUY", outcome="wait", blocked=True, barrier_value=0.48)
    correct_wait_anchor = _base_row(ts=12000, action="BUY", outcome="wait", blocked=True, barrier_value=0.44)
    correct_wait_relief = _base_row(ts=12120, action="BUY", outcome="entered", blocked=False, barrier_value=0.18)
    correct_wait_relief["entry_fill_price"] = 99.75
    relief_row = _base_row(ts=13000, action="BUY", outcome="entered", blocked=False, barrier_value=0.24)
    relief_bridge = build_barrier_state25_runtime_bridge_v1(relief_row)
    relief_bridge["barrier_runtime_summary_v1"]["anchor_context"] = "relief_release"
    relief_bridge["barrier_runtime_summary_v1"]["blocking_bias"] = "RELIEF_READY"
    relief_bridge["barrier_runtime_summary_v1"]["barrier_blocked_flag"] = False
    relief_bridge["barrier_action_hint_v1"]["recommended_family"] = "relief_release_bias"
    relief_bridge["barrier_action_hint_v1"]["enabled"] = True
    relief_bridge["barrier_action_hint_v1"]["hint_mode"] = "log_only"
    relief_row["barrier_state25_runtime_bridge_v1"] = relief_bridge

    future_bars = (
        _missed_profit_recovery_future_bars()
        + _correct_wait_recovery_future_bars()
        + _relief_success_recovery_future_bars()
    )
    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[missed_profit_row, correct_wait_anchor, correct_wait_relief, relief_row],
        future_bar_rows=future_bars,
    )

    bias_recovery = report["bias_recovery_v1"]
    assert bias_recovery["candidate_counts"]["missed_profit_weak_candidate"] >= 1
    assert bias_recovery["candidate_counts"]["correct_wait_timing_candidate"] >= 1
    assert bias_recovery["candidate_counts"]["relief_success_weak_candidate"] >= 1
    assert bias_recovery["top_activated_recovery_reasons"]
    drift_baseline = report["bias_baseline_v1"]["drift_baseline"]
    assert "top_normalized_action_pairs_v2" in drift_baseline


def test_barrier_outcome_bridge_report_builds_correct_wait_diagnostic_surface():
    unresolved_wait = _base_row(ts=15000, action="BUY", outcome="wait", blocked=True, barrier_value=0.44)
    future_bars = [
        {"symbol": "BTCUSD", "time": 15060, "open": 100.00, "high": 100.28, "low": 98.70, "close": 99.40},
        {"symbol": "BTCUSD", "time": 15120, "open": 99.40, "high": 99.55, "low": 98.20, "close": 98.60},
        {"symbol": "BTCUSD", "time": 15180, "open": 98.60, "high": 98.90, "low": 97.80, "close": 98.10},
        {"symbol": "BTCUSD", "time": 15240, "open": 98.10, "high": 98.60, "low": 97.90, "close": 98.25},
        {"symbol": "BTCUSD", "time": 15300, "open": 98.25, "high": 98.55, "low": 98.00, "close": 98.30},
        {"symbol": "BTCUSD", "time": 15360, "open": 98.30, "high": 98.48, "low": 98.14, "close": 98.22},
    ]

    report = build_barrier_outcome_bridge_report(
        entry_decision_rows=[unresolved_wait],
        future_bar_rows=future_bars,
    )

    diagnostic = report["correct_wait_diagnostic_v1"]
    assert diagnostic["scope_rows"] == 1
    assert diagnostic["effective_wait_block_rows"] == 1
    assert diagnostic["labeled_correct_wait_rows"] == 0
    assert diagnostic["top_blocking_reasons"]
    assert diagnostic["top_blocking_reasons"][0]["key"] in {
        "timing_edge_absent",
        "loss_avoided_dominates",
        "continuation_support_absent",
    }


def test_build_correct_wait_casebook_v1_groups_loss_avoided_dominates_patterns():
    rows = [
        {
            "symbol": "BTCUSD",
            "time": "2026-04-04T18:00:00+09:00",
            "barrier_state25_runtime_bridge_v1": {
                "barrier_runtime_summary_v1": {
                    "top_component": "sell_barrier",
                    "blocking_bias": "WAIT_BLOCK",
                },
                "barrier_input_trace_v1": {
                    "state25_label": "갭필링 진행장",
                },
            },
            "barrier_outcome_bridge_v1": {
                "barrier_primary_component": "sell_barrier",
                "blocking_bias": "WAIT_BLOCK",
                "barrier_recommended_family": "wait_bias",
                "actual_engine_action_family": "wait_or_block",
                "normalized_recommended_action_family_v2": "wait_or_block",
                "barrier_outcome_label": "avoided_loss",
                "barrier_label_confidence": "weak_usable",
                "drift_pair_key_v2": "wait_or_block->wait_or_block",
                "counterfactual_cost_delta_r": 1.42,
                "correct_wait_diagnostic_v1": {
                    "blocking_reason": "loss_avoided_dominates",
                    "effective_wait_block": True,
                    "wait_value_support": True,
                    "continuation_support": True,
                    "loss_avoided_r": 2.611,
                    "profit_missed_r": 0.748,
                    "wait_value_r": 0.655,
                    "better_entry_gain_6": 0.126,
                    "later_continuation_f_6": 0.529,
                },
            },
        },
        {
            "symbol": "BTCUSD",
            "time": "2026-04-04T18:15:00+09:00",
            "barrier_state25_runtime_bridge_v1": {
                "barrier_runtime_summary_v1": {
                    "top_component": "sell_barrier",
                    "blocking_bias": "WAIT_BLOCK",
                },
                "barrier_input_trace_v1": {
                    "state25_label": "갭필링 진행장",
                },
            },
            "barrier_outcome_bridge_v1": {
                "barrier_primary_component": "sell_barrier",
                "blocking_bias": "WAIT_BLOCK",
                "barrier_recommended_family": "wait_bias",
                "actual_engine_action_family": "wait_or_block",
                "normalized_recommended_action_family_v2": "wait_or_block",
                "barrier_outcome_label": "avoided_loss",
                "barrier_label_confidence": "weak_usable",
                "drift_pair_key_v2": "wait_or_block->wait_or_block",
                "counterfactual_cost_delta_r": 1.38,
                "correct_wait_diagnostic_v1": {
                    "blocking_reason": "loss_avoided_dominates",
                    "effective_wait_block": True,
                    "wait_value_support": True,
                    "continuation_support": True,
                    "loss_avoided_r": 2.611,
                    "profit_missed_r": 0.748,
                    "wait_value_r": 0.655,
                    "better_entry_gain_6": 0.126,
                    "later_continuation_f_6": 0.529,
                },
            },
        },
        {
            "symbol": "BTCUSD",
            "time": "2026-04-04T18:30:00+09:00",
            "barrier_state25_runtime_bridge_v1": {
                "barrier_runtime_summary_v1": {
                    "top_component": "liquidity_barrier",
                    "blocking_bias": "WAIT_BLOCK",
                },
                "barrier_input_trace_v1": {
                    "state25_label": "쉬운 루즈장",
                },
            },
            "barrier_outcome_bridge_v1": {
                "barrier_primary_component": "liquidity_barrier",
                "blocking_bias": "WAIT_BLOCK",
                "barrier_recommended_family": "wait_bias",
                "actual_engine_action_family": "wait_or_block",
                "normalized_recommended_action_family_v2": "wait_or_block",
                "barrier_outcome_label": "avoided_loss",
                "barrier_label_confidence": "weak_usable",
                "drift_pair_key_v2": "wait_or_block->wait_or_block",
                "counterfactual_cost_delta_r": 0.92,
                "correct_wait_diagnostic_v1": {
                    "blocking_reason": "loss_avoided_dominates",
                    "effective_wait_block": True,
                    "wait_value_support": True,
                    "continuation_support": True,
                    "loss_avoided_r": 1.490,
                    "profit_missed_r": 0.794,
                    "wait_value_r": 0.533,
                    "better_entry_gain_6": 0.0,
                    "later_continuation_f_6": 0.533,
                },
            },
        },
    ]

    casebook = _build_correct_wait_casebook_v1(rows)

    assert casebook["contract_version"] == "correct_wait_casebook_v1"
    assert casebook["loss_avoided_dominates_rows"] == 3
    assert casebook["unique_signatures"] == 2
    assert casebook["top_signatures"]
    assert casebook["top_signatures"][0]["count"] == 2
    assert casebook["representative_samples"]
    assert casebook["mean_loss_wait_margin_r"] > 0.0


def test_build_timing_edge_absent_casebook_v1_groups_repeated_patterns():
    rows = [
        {
            "symbol": "BTCUSD",
            "time": "2026-04-04T19:00:00+09:00",
            "barrier_state25_runtime_bridge_v1": {
                "barrier_runtime_summary_v1": {
                    "top_component": "sell_barrier",
                    "blocking_bias": "WAIT_BLOCK",
                },
                "barrier_input_trace_v1": {
                    "state25_label": "gap_trend_scene",
                },
            },
            "barrier_outcome_bridge_v1": {
                "barrier_primary_component": "sell_barrier",
                "blocking_bias": "WAIT_BLOCK",
                "barrier_recommended_family": "wait_bias",
                "actual_engine_action_family": "wait_or_block",
                "normalized_recommended_action_family_v2": "wait_or_block",
                "barrier_outcome_label": "",
                "barrier_label_confidence": "low_skip",
                "drift_pair_key_v2": "wait_or_block->wait_or_block",
                "counterfactual_cost_delta_r": 0.0,
                "correct_wait_diagnostic_v1": {
                    "blocking_reason": "timing_edge_absent",
                    "effective_wait_block": True,
                    "wait_value_support": False,
                    "continuation_support": False,
                    "loss_avoided_r": 0.88,
                    "profit_missed_r": 0.41,
                    "wait_value_r": 0.0,
                    "better_entry_gain_6": 0.0,
                    "later_continuation_f_6": 0.0,
                },
            },
        },
        {
            "symbol": "BTCUSD",
            "time": "2026-04-04T19:15:00+09:00",
            "barrier_state25_runtime_bridge_v1": {
                "barrier_runtime_summary_v1": {
                    "top_component": "sell_barrier",
                    "blocking_bias": "WAIT_BLOCK",
                },
                "barrier_input_trace_v1": {
                    "state25_label": "gap_trend_scene",
                },
            },
            "barrier_outcome_bridge_v1": {
                "barrier_primary_component": "sell_barrier",
                "blocking_bias": "WAIT_BLOCK",
                "barrier_recommended_family": "wait_bias",
                "actual_engine_action_family": "wait_or_block",
                "normalized_recommended_action_family_v2": "wait_or_block",
                "barrier_outcome_label": "",
                "barrier_label_confidence": "low_skip",
                "drift_pair_key_v2": "wait_or_block->wait_or_block",
                "counterfactual_cost_delta_r": 0.0,
                "correct_wait_diagnostic_v1": {
                    "blocking_reason": "timing_edge_absent",
                    "effective_wait_block": True,
                    "wait_value_support": False,
                    "continuation_support": False,
                    "loss_avoided_r": 0.88,
                    "profit_missed_r": 0.41,
                    "wait_value_r": 0.0,
                    "better_entry_gain_6": 0.0,
                    "later_continuation_f_6": 0.0,
                },
            },
        },
        {
            "symbol": "BTCUSD",
            "time": "2026-04-04T19:30:00+09:00",
            "barrier_state25_runtime_bridge_v1": {
                "barrier_runtime_summary_v1": {
                    "top_component": "middle_chop_barrier",
                    "blocking_bias": "HARD_BLOCK",
                },
                "barrier_input_trace_v1": {
                    "state25_label": "range_reversal_scene",
                },
            },
            "barrier_outcome_bridge_v1": {
                "barrier_primary_component": "middle_chop_barrier",
                "blocking_bias": "HARD_BLOCK",
                "barrier_recommended_family": "block_bias",
                "actual_engine_action_family": "wait_or_block",
                "normalized_recommended_action_family_v2": "wait_or_block",
                "barrier_outcome_label": "missed_profit",
                "barrier_label_confidence": "weak_usable",
                "drift_pair_key_v2": "wait_or_block->wait_or_block",
                "counterfactual_cost_delta_r": 0.0,
                "weak_candidate_reason": "soft_missed_profit_weak_recovery",
                "correct_wait_diagnostic_v1": {
                    "blocking_reason": "timing_edge_absent",
                    "effective_wait_block": True,
                    "wait_value_support": False,
                    "continuation_support": False,
                    "loss_avoided_r": 1.02,
                    "profit_missed_r": 1.33,
                    "wait_value_r": 0.12,
                    "better_entry_gain_6": 0.0,
                    "later_continuation_f_6": 0.16,
                },
            },
        },
        {
            "symbol": "BTCUSD",
            "time": "2026-04-04T19:45:00+09:00",
            "barrier_state25_runtime_bridge_v1": {
                "barrier_runtime_summary_v1": {
                    "top_component": "middle_chop_barrier",
                    "blocking_bias": "HARD_BLOCK",
                },
                "barrier_input_trace_v1": {
                    "state25_label": "gap_trend_scene",
                },
            },
            "barrier_outcome_bridge_v1": {
                "barrier_primary_component": "middle_chop_barrier",
                "blocking_bias": "HARD_BLOCK",
                "barrier_recommended_family": "block_bias",
                "actual_engine_action_family": "wait_or_block",
                "normalized_recommended_action_family_v2": "wait_or_block",
                "barrier_outcome_label": "avoided_loss",
                "barrier_label_confidence": "high",
                "drift_pair_key_v2": "wait_or_block->wait_or_block",
                "counterfactual_cost_delta_r": 1.0,
                "correct_wait_diagnostic_v1": {
                    "blocking_reason": "timing_edge_absent",
                    "effective_wait_block": True,
                    "wait_value_support": False,
                    "continuation_support": False,
                    "loss_avoided_r": 1.0,
                    "profit_missed_r": 0.21,
                    "wait_value_r": 0.21,
                    "better_entry_gain_6": 0.0,
                    "later_continuation_f_6": 0.21,
                },
            },
        },
    ]

    casebook = _build_timing_edge_absent_casebook_v1(rows)
    assert casebook["contract_version"] == "timing_edge_absent_casebook_v1"
    assert casebook["timing_edge_absent_rows"] == 4
    assert casebook["unique_signatures"] == 3
    assert casebook["zero_entry_gain_rows"] == 4
    assert casebook["top_signatures"]
    assert casebook["top_signatures"][0]["count"] == 2
    assert casebook["mean_better_entry_gain_6"] == 0.0
    assert casebook["subtype_counts"]["zero_entry_gain_no_continuation"] == 2
    assert casebook["subtype_counts"]["missed_profit_leaning"] == 1
    assert casebook["subtype_counts"]["small_continuation_avoided_loss"] == 1
    assert casebook["top_subtypes"][0]["key"] == "zero_entry_gain_no_continuation"
    assert casebook["subtype_profiles"]["missed_profit_leaning"]["top_labels"][0]["key"] == "missed_profit"
    assert casebook["subtype_profiles"]["small_continuation_avoided_loss"]["top_labels"][0]["key"] == "avoided_loss"


def test_barrier_outcome_bridge_rows_use_barrier_state_missing_taxonomy():
    row = {
        "symbol": "BTCUSD",
        "time": 1000,
        "signal_bar_ts": 1000,
        "action": "BUY",
        "outcome": "skipped",
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {
                "available": False,
                "reason_summary": "barrier_missing",
            }
        },
    }

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=[],
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["skip_reason"] == "barrier_state_missing"
    assert outcome["barrier_outcome_reason"] == "barrier_state_missing"


def test_barrier_outcome_bridge_rows_separate_pre_context_skip_from_barrier_missing():
    row = {
        "symbol": "BTCUSD",
        "time": 1000,
        "signal_bar_ts": 1000,
        "action": "BUY",
        "outcome": "skipped",
        "blocked_by": "max_positions_reached",
        "barrier_state_v1": {},
    }

    rows = build_barrier_outcome_bridge_rows(
        entry_decision_rows=[row],
        future_bar_rows=[],
    )

    outcome = rows[0]["barrier_outcome_bridge_v1"]
    assert outcome["skip_reason"] == "pre_context_skip:max_positions_reached"
    assert outcome["barrier_outcome_reason"] == "pre_context_skip:max_positions_reached"
    assert outcome["barrier_trace_stage"] == "pre_context_skip"
    assert outcome["barrier_trace_reason"] == "max_positions_reached"
