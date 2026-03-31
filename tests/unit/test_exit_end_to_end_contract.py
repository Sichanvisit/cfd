import csv
import json

import pytest

from backend.app.trading_application import TradingApplication
from backend.domain.decision_models import WaitState
from backend.services.exit_manage_context_contract import (
    build_exit_manage_context_v1,
    compact_exit_manage_context_v1,
)
from backend.services.exit_wait_state_input_contract import (
    build_exit_wait_state_input_v1,
    compact_exit_wait_state_input_v1,
)
from backend.services.exit_wait_state_surface_contract import (
    build_exit_wait_state_surface_v1,
    compact_exit_wait_state_surface_v1,
)
from backend.services.exit_wait_taxonomy_contract import (
    build_exit_wait_taxonomy_v1,
    compact_exit_wait_taxonomy_v1,
)
from backend.services.storage_compaction import compact_runtime_signal_row


class _DummyBroker:
    pass


class _DummyNotifier:
    def send(self, message):
        return None

    def shutdown(self):
        return None


class _DummyObservability:
    def incr(self, name, amount=1):
        return None

    def event(self, name, level="info", payload=None):
        return None


def _dump_csv_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _write_trade_history_log(path, rows):
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _dump_csv_value(value) for key, value in row.items()})


def _exit_scene_fixtures():
    return {
        "confirm_wait": {
            "time": "2026-03-29T21:00:00+09:00",
            "close_time": "2026-03-29 21:00:00",
            "open_time": "2026-03-29 20:28:00",
            "symbol": "XAUUSD",
            "status": "OPEN",
            "trade_ctx": {
                "entry_setup_id": "range_upper_reversal_sell",
                "management_profile_id": "reversal_profile",
                "invalidation_id": "upper_break_reclaim",
                "exit_profile": "hold_then_trail",
                "direction": "SELL",
            },
            "stage_inputs": {
                "regime_now": "RANGE",
                "regime_at_entry": "RANGE",
                "current_box_state": "UPPER",
                "current_bb_state": "UPPER_EDGE",
                "entry_direction": "SELL",
                "profit": 0.41,
                "peak_profit": 0.66,
                "duration_sec": 240.0,
            },
            "context_inputs": {
                "chosen_stage": "protect",
                "policy_stage": "short",
                "exec_profile": "adaptive",
                "confirm_needed": 4,
                "exit_signal_score": 152,
                "score_gap": 21,
                "adverse_risk": True,
                "tf_confirm": True,
                "route_txt": "e5-confirm",
            },
            "wait_state": {
                "state": "REVERSAL_CONFIRM",
                "hard_wait": True,
                "reason": "opposite_signal_unconfirmed",
                "matched_rule": "reversal_confirm",
                "score": 0.21,
                "penalty": 0.0,
            },
            "utility_result": {
                "winner": "wait_exit",
                "decision_reason": "wait_exit_reversal_confirm",
                "wait_selected": True,
                "wait_decision": "wait_exit_reversal_confirm",
            },
            "expected": {
                "state_family": "confirm_hold",
                "decision_family": "wait_exit",
                "bridge_status": "aligned_confirm_wait",
                "base_state": "REVERSAL_CONFIRM",
                "rewrite_applied": False,
                "recovery_policy_id": "reversal_profile",
            },
        },
        "recovery_wait": {
            "time": "2026-03-29T21:01:00+09:00",
            "close_time": "2026-03-29 21:01:00",
            "open_time": "2026-03-29 20:04:00",
            "symbol": "BTCUSD",
            "status": "CLOSED",
            "trade_ctx": {
                "entry_setup_id": "range_lower_reversal_buy",
                "management_profile_id": "support_hold_profile",
                "invalidation_id": "lower_support_fail",
                "exit_profile": "neutral",
                "direction": "BUY",
            },
            "stage_inputs": {
                "regime_now": "RANGE",
                "regime_at_entry": "RANGE",
                "current_box_state": "LOWER",
                "current_bb_state": "LOWER_EDGE",
                "entry_direction": "BUY",
                "profit": -0.18,
                "peak_profit": 0.0,
                "duration_sec": 120.0,
            },
            "context_inputs": {
                "chosen_stage": "protect",
                "policy_stage": "short",
                "exec_profile": "neutral",
                "confirm_needed": 2,
                "exit_signal_score": 94,
                "score_gap": 8,
                "adverse_risk": False,
                "tf_confirm": True,
                "route_txt": "e5-recovery",
            },
            "wait_state": {
                "state": "RECOVERY_BE",
                "hard_wait": False,
                "reason": "recovery_to_breakeven",
                "matched_rule": "recovery_be",
                "score": 0.18,
                "penalty": 0.18,
            },
            "utility_result": {
                "winner": "wait_be",
                "decision_reason": "wait_be_recovery",
                "wait_selected": True,
                "wait_decision": "wait_be_recovery",
            },
            "expected": {
                "state_family": "recovery_hold",
                "decision_family": "recovery_wait",
                "bridge_status": "aligned_recovery_wait",
                "base_state": "RECOVERY_BE",
                "rewrite_applied": False,
                "recovery_policy_id": "range_lower_reversal_buy_btc_balanced",
            },
        },
        "reverse_now": {
            "time": "2026-03-29T21:02:00+09:00",
            "close_time": "2026-03-29 21:02:00",
            "open_time": "2026-03-29 20:17:00",
            "symbol": "NAS100",
            "status": "CLOSED",
            "trade_ctx": {
                "entry_setup_id": "breakout_retest_sell",
                "management_profile_id": "breakout_hold_profile",
                "invalidation_id": "breakout_failure",
                "exit_profile": "hold_then_trail",
                "direction": "SELL",
            },
            "stage_inputs": {
                "regime_now": "RANGE",
                "regime_at_entry": "TREND",
                "current_box_state": "UPPER",
                "current_bb_state": "UPPER_EDGE",
                "entry_direction": "SELL",
                "profit": -0.24,
                "peak_profit": 0.0,
                "duration_sec": 85.0,
            },
            "context_inputs": {
                "chosen_stage": "protect",
                "policy_stage": "short",
                "exec_profile": "adaptive",
                "confirm_needed": 2,
                "exit_signal_score": 144,
                "score_gap": 28,
                "adverse_risk": True,
                "tf_confirm": True,
                "route_txt": "e5-reverse",
            },
            "wait_state": {
                "state": "REVERSE_READY",
                "hard_wait": False,
                "reason": "reverse_ready_after_confirm",
                "matched_rule": "reverse_ready",
                "score": 0.28,
                "penalty": 0.24,
            },
            "utility_result": {
                "winner": "reverse_now",
                "decision_reason": "reverse_now_best",
                "wait_selected": False,
                "wait_decision": "",
            },
            "expected": {
                "state_family": "reverse_ready",
                "decision_family": "reverse_now",
                "bridge_status": "aligned_reverse",
                "base_state": "REVERSE_READY",
                "rewrite_applied": False,
                "recovery_policy_id": "breakout_hold_profile",
            },
        },
        "exit_pressure": {
            "time": "2026-03-29T21:03:00+09:00",
            "close_time": "2026-03-29 21:03:00",
            "open_time": "2026-03-29 20:45:00",
            "symbol": "US30",
            "status": "CLOSED",
            "trade_ctx": {
                "entry_setup_id": "trend_pullback_buy",
                "management_profile_id": "trend_hold_profile",
                "invalidation_id": "trend_break_fail",
                "exit_profile": "tight_protect",
                "direction": "BUY",
            },
            "stage_inputs": {
                "regime_now": "TREND",
                "regime_at_entry": "TREND",
                "current_box_state": "MIDDLE",
                "current_bb_state": "MID",
                "entry_direction": "BUY",
                "profit": -0.62,
                "peak_profit": 0.0,
                "duration_sec": 64.0,
            },
            "context_inputs": {
                "chosen_stage": "lock",
                "policy_stage": "short",
                "exec_profile": "tight",
                "confirm_needed": 1,
                "exit_signal_score": 118,
                "score_gap": 32,
                "adverse_risk": True,
                "tf_confirm": False,
                "route_txt": "e5-cut",
            },
            "wait_state": {
                "state": "CUT_IMMEDIATE",
                "hard_wait": False,
                "reason": "adverse_loss_expand",
                "matched_rule": "cut_immediate",
                "score": 0.62,
                "penalty": 0.62,
            },
            "utility_result": {
                "winner": "cut_now",
                "decision_reason": "cut_now_best",
                "wait_selected": False,
                "wait_decision": "",
            },
            "expected": {
                "state_family": "exit_pressure",
                "decision_family": "exit_now",
                "bridge_status": "aligned_exit_pressure",
                "base_state": "CUT_IMMEDIATE",
                "rewrite_applied": False,
                "recovery_policy_id": "trend_pullback",
            },
        },
    }


def _evaluate_exit_scene(scene_name: str):
    scene = dict(_exit_scene_fixtures()[scene_name])
    context_inputs = dict(scene["context_inputs"])
    route_txt = str(context_inputs.pop("route_txt", "") or "")

    exit_manage_context_v1 = build_exit_manage_context_v1(
        symbol=str(scene["symbol"]),
        trade_ctx=dict(scene["trade_ctx"]),
        stage_inputs=dict(scene["stage_inputs"]),
        chosen_stage=str(context_inputs["chosen_stage"]),
        policy_stage=str(context_inputs["policy_stage"]),
        exec_profile=str(context_inputs["exec_profile"]),
        confirm_needed=int(context_inputs["confirm_needed"]),
        exit_signal_score=int(context_inputs["exit_signal_score"]),
        score_gap=int(context_inputs["score_gap"]),
        adverse_risk=bool(context_inputs["adverse_risk"]),
        tf_confirm=bool(context_inputs["tf_confirm"]),
        detail={"route_txt": route_txt},
    )
    compact_exit_context_v1 = compact_exit_manage_context_v1(exit_manage_context_v1)
    exit_wait_state_input_v1 = build_exit_wait_state_input_v1(
        symbol=str(scene["symbol"]),
        trade_ctx=dict(scene["trade_ctx"]),
        stage_inputs=dict(scene["stage_inputs"]),
        adverse_risk=bool(context_inputs["adverse_risk"]),
        tf_confirm=bool(context_inputs["tf_confirm"]),
        chosen_stage=str(context_inputs["chosen_stage"]),
        policy_stage=str(context_inputs["policy_stage"]),
        confirm_needed=int(context_inputs["confirm_needed"]),
        exit_signal_score=int(context_inputs["exit_signal_score"]),
        score_gap=int(context_inputs["score_gap"]),
        detail={
            "route_txt": route_txt,
            "exit_manage_context_v1": dict(exit_manage_context_v1),
        },
    )
    compact_exit_wait_state_input = compact_exit_wait_state_input_v1(exit_wait_state_input_v1)

    wait_state_cfg = dict(scene["wait_state"])
    state_policy = {
        "contract_version": "exit_wait_state_policy_v1",
        "state": str(wait_state_cfg["state"]),
        "reason": str(wait_state_cfg["reason"]),
        "hard_wait": bool(wait_state_cfg["hard_wait"]),
        "matched_rule": str(wait_state_cfg["matched_rule"]),
    }
    state_rewrite = {
        "contract_version": "exit_wait_state_rewrite_v1",
        "state": str(wait_state_cfg["state"]),
        "reason": str(wait_state_cfg["reason"]),
        "hard_wait": bool(wait_state_cfg["hard_wait"]),
        "base_state": str(wait_state_cfg["state"]),
        "base_reason": str(wait_state_cfg["reason"]),
        "base_hard_wait": bool(wait_state_cfg["hard_wait"]),
        "base_matched_rule": str(wait_state_cfg["matched_rule"]),
        "rewrite_applied": False,
        "rewrite_rule": "",
    }
    exit_wait_state_surface_v1 = compact_exit_wait_state_surface_v1(
        build_exit_wait_state_surface_v1(
            exit_wait_state_input_v1=exit_wait_state_input_v1,
            exit_wait_state_policy_v1=state_policy,
            exit_wait_state_rewrite_v1=state_rewrite,
            score=float(wait_state_cfg["score"]),
            penalty=float(wait_state_cfg["penalty"]),
            conflict=0.0,
            noise=0.0,
        )
    )
    wait_state = WaitState(
        phase="exit",
        state=str(wait_state_cfg["state"]),
        hard_wait=bool(wait_state_cfg["hard_wait"]),
        reason=str(wait_state_cfg["reason"]),
        score=float(wait_state_cfg["score"]),
        penalty=float(wait_state_cfg["penalty"]),
        metadata={
            "exit_manage_context_v1": dict(compact_exit_context_v1),
            "exit_wait_state_input_v1": dict(compact_exit_wait_state_input),
            "exit_wait_state_rewrite_v1": dict(state_rewrite),
            "exit_wait_state_surface_v1": dict(exit_wait_state_surface_v1),
        },
    )
    utility_result = dict(scene["utility_result"])
    exit_wait_taxonomy_v1 = compact_exit_wait_taxonomy_v1(
        build_exit_wait_taxonomy_v1(
            wait_state=wait_state,
            utility_result=utility_result,
        )
    )

    runtime_row = {
        "time": str(scene["time"]),
        "symbol": str(scene["symbol"]),
        "status": str(scene["status"]),
        "decision_winner": str(utility_result.get("winner", "") or ""),
        "decision_reason": str(utility_result.get("decision_reason", "") or ""),
        "exit_wait_state": str(wait_state.state or ""),
        "exit_wait_selected": int(1 if utility_result.get("wait_selected") else 0),
        "exit_wait_decision": str(utility_result.get("wait_decision", "") or ""),
        "exit_wait_state_family": str(
            ((exit_wait_taxonomy_v1.get("state", {}) or {}).get("state_family", "")) or ""
        ),
        "exit_wait_hold_class": str(
            ((exit_wait_taxonomy_v1.get("state", {}) or {}).get("hold_class", "")) or ""
        ),
        "exit_wait_decision_family": str(
            ((exit_wait_taxonomy_v1.get("decision", {}) or {}).get("decision_family", "")) or ""
        ),
        "exit_wait_bridge_status": str(
            ((exit_wait_taxonomy_v1.get("bridge", {}) or {}).get("bridge_status", "")) or ""
        ),
        "exit_manage_context_v1": dict(compact_exit_context_v1),
        "exit_wait_state_v1": {
            "phase": "exit",
            "state": str(wait_state.state or ""),
            "hard_wait": bool(wait_state.hard_wait),
            "score": float(wait_state.score or 0.0),
            "penalty": float(wait_state.penalty or 0.0),
            "reason": str(wait_state.reason or ""),
            "metadata": dict(wait_state.metadata or {}),
        },
        "exit_wait_taxonomy_v1": dict(exit_wait_taxonomy_v1),
        "exit_utility_v1": {
            **dict(utility_result),
            "utility_exit_now": 0.0,
            "utility_hold": 0.0,
            "utility_reverse": 0.0,
            "utility_wait_exit": 0.0,
            "u_cut_now": 0.0,
            "u_wait_be": 0.0,
            "u_wait_tp1": 0.0,
            "u_reverse": 0.0,
        },
    }
    trade_row = {
        "close_time": str(scene["close_time"]),
        "open_time": str(scene["open_time"]),
        "symbol": str(scene["symbol"]),
        "status": str(scene["status"]),
        "exit_wait_state": str(wait_state.state or ""),
        "exit_wait_selected": int(1 if utility_result.get("wait_selected") else 0),
        "exit_wait_decision": str(utility_result.get("wait_decision", "") or ""),
        "decision_winner": str(utility_result.get("winner", "") or ""),
        "decision_reason": str(utility_result.get("decision_reason", "") or ""),
        "exit_wait_state_family": str(
            ((exit_wait_taxonomy_v1.get("state", {}) or {}).get("state_family", "")) or ""
        ),
        "exit_wait_hold_class": str(
            ((exit_wait_taxonomy_v1.get("state", {}) or {}).get("hold_class", "")) or ""
        ),
        "exit_wait_decision_family": str(
            ((exit_wait_taxonomy_v1.get("decision", {}) or {}).get("decision_family", "")) or ""
        ),
        "exit_wait_bridge_status": str(
            ((exit_wait_taxonomy_v1.get("bridge", {}) or {}).get("bridge_status", "")) or ""
        ),
    }
    compact = compact_runtime_signal_row(runtime_row)
    return {
        "scene": scene,
        "wait_state": wait_state,
        "runtime_row": runtime_row,
        "trade_row": trade_row,
        "compact": compact,
    }


@pytest.mark.parametrize(
    (
        "scene_name",
        "expected_state",
        "expected_winner",
        "expected_state_family",
        "expected_decision_family",
        "expected_bridge_status",
    ),
    [
        ("confirm_wait", "REVERSAL_CONFIRM", "wait_exit", "confirm_hold", "wait_exit", "aligned_confirm_wait"),
        ("recovery_wait", "RECOVERY_BE", "wait_be", "recovery_hold", "recovery_wait", "aligned_recovery_wait"),
        ("reverse_now", "REVERSE_READY", "reverse_now", "reverse_ready", "reverse_now", "aligned_reverse"),
        ("exit_pressure", "CUT_IMMEDIATE", "cut_now", "exit_pressure", "exit_now", "aligned_exit_pressure"),
    ],
)
def test_exit_end_to_end_contract_keeps_exit_surface_semantics_in_runtime_row(
    scene_name,
    expected_state,
    expected_winner,
    expected_state_family,
    expected_decision_family,
    expected_bridge_status,
):
    evaluated = _evaluate_exit_scene(scene_name)
    compact = evaluated["compact"]
    runtime_row = evaluated["runtime_row"]
    expected = evaluated["scene"]["expected"]

    assert runtime_row["exit_wait_state"] == expected_state
    assert runtime_row["decision_winner"] == expected_winner
    assert runtime_row["exit_wait_state_family"] == expected_state_family
    assert runtime_row["exit_wait_decision_family"] == expected_decision_family
    assert runtime_row["exit_wait_bridge_status"] == expected_bridge_status

    assert compact["exit_wait_state_surface_v1"]["state"]["state"] == expected_state
    assert compact["exit_wait_state_surface_v1"]["state"]["base_state"] == expected["base_state"]
    assert compact["exit_wait_base_state"] == expected["base_state"]
    assert compact["exit_wait_rewrite_applied"] is expected["rewrite_applied"]
    assert compact["exit_wait_recovery_policy_id"] == expected["recovery_policy_id"]
    assert compact["exit_wait_taxonomy_v1"]["state"]["state_family"] == expected_state_family
    assert compact["exit_wait_taxonomy_v1"]["decision"]["winner"] == expected_winner
    assert compact["exit_wait_state_family"] == expected_state_family
    assert compact["exit_wait_decision_family"] == expected_decision_family
    assert compact["exit_wait_bridge_status"] == expected_bridge_status
    assert compact["exit_manage_context_v1"]["identity"]["symbol"] == evaluated["scene"]["symbol"]


def test_exit_end_to_end_contract_recent_summary_matches_trade_rows(monkeypatch, tmp_path):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.runtime_status_path = tmp_path / "runtime_status.json"
    app.runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    app.semantic_rollout_manifest_path = tmp_path / "semantic_live_rollout_latest.json"
    app.entry_decision_log_path = tmp_path / "missing_entry_decisions.csv"
    app.trade_history_csv_path = tmp_path / "trade_history.csv"

    scene_names = ["confirm_wait", "recovery_wait", "reverse_now", "exit_pressure"]
    evaluated = [_evaluate_exit_scene(name) for name in scene_names]
    trade_rows = [entry["trade_row"] for entry in evaluated]
    runtime_rows = {str(entry["runtime_row"]["symbol"]): dict(entry["runtime_row"]) for entry in evaluated}

    _write_trade_history_log(app.trade_history_csv_path, trade_rows)
    app.latest_signal_by_symbol = runtime_rows

    app._write_runtime_status(
        loop_count=1,
        symbols=["BTCUSD", "NAS100", "US30", "XAUUSD"],
        entry_threshold=45,
        exit_threshold=35,
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))

    window = detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]
    state_summary = window["exit_state_semantic_summary"]
    decision_summary = window["exit_decision_summary"]
    bridge_summary = window["exit_state_decision_bridge_summary"]

    assert window["row_count"] == 4
    assert window["status_counts"]["OPEN"] == 1
    assert window["status_counts"]["CLOSED"] == 3

    assert state_summary["row_count"] == 4
    assert state_summary["state_family_counts"]["confirm_hold"] == 1
    assert state_summary["state_family_counts"]["recovery_hold"] == 1
    assert state_summary["state_family_counts"]["reverse_ready"] == 1
    assert state_summary["state_family_counts"]["exit_pressure"] == 1

    assert decision_summary["decision_row_count"] == 4
    assert decision_summary["decision_family_counts"]["wait_exit"] == 1
    assert decision_summary["decision_family_counts"]["recovery_wait"] == 1
    assert decision_summary["decision_family_counts"]["reverse_now"] == 1
    assert decision_summary["decision_family_counts"]["exit_now"] == 1
    assert decision_summary["winner_counts"]["wait_exit"] == 1
    assert decision_summary["winner_counts"]["wait_be"] == 1
    assert decision_summary["winner_counts"]["reverse_now"] == 1
    assert decision_summary["winner_counts"]["cut_now"] == 1
    assert decision_summary["wait_selected_rows"] == 2
    assert decision_summary["wait_selected_rate"] == 0.5

    assert bridge_summary["bridge_row_count"] == 4
    assert bridge_summary["bridge_status_counts"]["aligned_confirm_wait"] == 1
    assert bridge_summary["bridge_status_counts"]["aligned_recovery_wait"] == 1
    assert bridge_summary["bridge_status_counts"]["aligned_reverse"] == 1
    assert bridge_summary["bridge_status_counts"]["aligned_exit_pressure"] == 1
    assert bridge_summary["state_to_decision_counts"]["confirm_hold->wait_exit"] == 1
    assert bridge_summary["state_to_decision_counts"]["recovery_hold->recovery_wait"] == 1
    assert bridge_summary["state_to_decision_counts"]["reverse_ready->reverse_now"] == 1
    assert bridge_summary["state_to_decision_counts"]["exit_pressure->exit_now"] == 1

    assert window["symbol_summary"]["XAUUSD"]["rows"] == 1
    assert window["symbol_summary"]["BTCUSD"]["rows"] == 1
    assert window["symbol_summary"]["NAS100"]["rows"] == 1
    assert window["symbol_summary"]["US30"]["rows"] == 1
    assert (
        window["symbol_summary"]["NAS100"]["exit_state_decision_bridge_summary"]["bridge_status_counts"][
            "aligned_reverse"
        ]
        == 1
    )

    assert slim["recent_exit_summary_window"] == "last_200"
    assert slim["recent_exit_state_semantic_summary"]["state_family_counts"]["confirm_hold"] == 1
    assert slim["recent_exit_decision_summary"]["decision_family_counts"]["exit_now"] == 1
    assert (
        slim["recent_exit_state_decision_bridge_summary"]["bridge_status_counts"]["aligned_recovery_wait"]
        == 1
    )

    slim_xau = slim["latest_signal_by_symbol"]["XAUUSD"]
    slim_us30 = slim["latest_signal_by_symbol"]["US30"]
    assert slim_xau["exit_wait_state_family"] == "confirm_hold"
    assert slim_xau["exit_wait_decision_family"] == "wait_exit"
    assert slim_xau["exit_wait_bridge_status"] == "aligned_confirm_wait"
    assert slim_xau["exit_wait_base_state"] == "REVERSAL_CONFIRM"
    assert slim_us30["exit_wait_state_family"] == "exit_pressure"
    assert slim_us30["exit_wait_decision_family"] == "exit_now"
    assert slim_us30["exit_wait_bridge_status"] == "aligned_exit_pressure"
    assert slim_us30["exit_wait_base_state"] == "CUT_IMMEDIATE"
