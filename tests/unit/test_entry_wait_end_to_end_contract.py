import csv
import json
from copy import deepcopy

import pytest

from backend.app.trading_application import TradingApplication
from backend.services.storage_compaction import (
    build_entry_decision_hot_payload,
    compact_runtime_signal_row,
)
from backend.services.wait_engine import WaitEngine


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


def _write_entry_decision_log(path, rows):
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


def _wait_scene_fixtures():
    return {
        "helper_soft_block_wait": {
            "time": "2026-03-29T18:00:00+09:00",
            "symbol": "XAUUSD",
            "row": {
                "symbol": "XAUUSD",
                "action": "",
                "blocked_by": "core_not_passed",
                "box_state": "LOWER",
                "bb_state": "LOWER_EDGE",
                "wait_score": 0.0,
                "wait_conflict": 0.0,
                "wait_noise": 0.0,
                "wait_penalty": 0.0,
                "consumer_energy_action_readiness": 0.24,
                "consumer_energy_wait_vs_enter_hint": "prefer_wait",
                "consumer_energy_soft_block_active": True,
                "consumer_energy_soft_block_reason": "forecast_wait_bias",
                "consumer_energy_soft_block_strength": 0.81,
            },
            "blocked_reason": "core_not_passed",
            "raw_entry_score": 64.0,
            "effective_threshold": 63.0,
            "core_score": 0.22,
            "expected_state": "HELPER_SOFT_BLOCK",
            "expected_decision": "wait_soft_helper_block",
            "expected_selected": True,
        },
        "policy_suppressed_wait": {
            "time": "2026-03-29T18:01:00+09:00",
            "symbol": "BTCUSD",
            "row": {
                "symbol": "BTCUSD",
                "action": "",
                "blocked_by": "layer_mode_confirm_suppressed",
                "box_state": "LOWER",
                "bb_state": "LOWER_EDGE",
                "consumer_layer_mode_suppressed": True,
                "consumer_policy_block_layer": "Barrier",
                "consumer_policy_block_effect": "confirm_to_observe_suppression",
                "wait_score": 8.0,
                "wait_conflict": 0.0,
                "wait_noise": 0.0,
                "wait_penalty": 0.0,
            },
            "blocked_reason": "layer_mode_confirm_suppressed",
            "raw_entry_score": 70.0,
            "effective_threshold": 45.0,
            "core_score": 0.40,
            "expected_state": "POLICY_SUPPRESSED",
            "expected_decision": "wait_policy_suppressed",
            "expected_selected": True,
        },
        "center_skip": {
            "time": "2026-03-29T18:02:00+09:00",
            "symbol": "XAUUSD",
            "row": {
                "symbol": "XAUUSD",
                "action": "BUY",
                "blocked_by": "setup_rejected",
                "box_state": "MIDDLE",
                "bb_state": "LOWER_EDGE",
                "wait_score": 30.0,
                "wait_conflict": 0.0,
                "wait_noise": 0.0,
                "wait_penalty": 0.0,
            },
            "blocked_reason": "",
            "raw_entry_score": 66.0,
            "effective_threshold": 45.0,
            "core_score": 0.60,
            "expected_state": "CENTER",
            "expected_decision": "skip",
            "expected_selected": False,
        },
        "none_skip": {
            "time": "2026-03-29T18:03:00+09:00",
            "symbol": "NAS100",
            "row": {
                "symbol": "NAS100",
                "action": "SELL",
                "blocked_by": "dynamic_threshold_not_met",
                "box_state": "UPPER",
                "bb_state": "UPPER_EDGE",
                "wait_score": 0.0,
                "wait_conflict": 0.0,
                "wait_noise": 0.0,
                "wait_penalty": 0.0,
            },
            "blocked_reason": "dynamic_threshold_not_met",
            "raw_entry_score": 61.0,
            "effective_threshold": 68.0,
            "core_score": 0.60,
            "expected_state": "NONE",
            "expected_decision": "skip",
            "expected_selected": False,
        },
        "xau_probe_active_skip": {
            "time": "2026-03-29T18:04:00+09:00",
            "symbol": "XAUUSD",
            "row": {
                "symbol": "XAUUSD",
                "action": "BUY",
                "blocked_by": "outer_band_buy_reversal_support_required",
                "box_state": "LOWER",
                "bb_state": "MID",
                "wait_score": 34.0,
                "wait_conflict": 0.0,
                "wait_noise": 12.0,
                "wait_penalty": 0.0,
                "observe_confirm_v2": {
                    "state": "OBSERVE",
                    "action": "BUY",
                    "side": "BUY",
                    "reason": "lower_rebound_probe_observe",
                    "metadata": {
                        "xau_second_support_probe_relief": True,
                    },
                },
                "probe_candidate_v1": {
                    "active": True,
                    "probe_direction": "BUY",
                    "candidate_support": 0.87,
                    "near_confirm": True,
                    "pair_gap": 0.18,
                    "trigger_branch": "lower_rebound",
                    "symbol_probe_temperament_v1": {
                        "scene_id": "xau_second_support_buy_probe",
                        "promotion_bias": "aggressive_second_support",
                        "entry_style_hint": "second_support_probe",
                        "source_map_id": "shared_symbol_temperament_map_v1",
                        "note": "xau_second_support_buy_more_aggressive",
                    },
                },
            },
            "blocked_reason": "setup_rejected",
            "raw_entry_score": 132.0,
            "effective_threshold": 45.0,
            "core_score": 0.58,
            "expected_state": "ACTIVE",
            "expected_decision": "skip",
            "expected_selected": False,
            "expected_probe_scene_id": "xau_second_support_buy_probe",
        },
    }


def _evaluate_wait_scene(scene_name: str):
    scene = deepcopy(_wait_scene_fixtures()[scene_name])
    row_input = dict(scene["row"])
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol=str(scene["symbol"]),
        row=row_input,
        blocked_reason=str(scene["blocked_reason"]),
        raw_entry_score=float(scene["raw_entry_score"]),
        effective_threshold=float(scene["effective_threshold"]),
        core_score=float(scene["core_score"]),
    )
    wait_state = decision["wait_state"]
    wait_metadata = dict(wait_state.metadata or {})
    persisted_row = {
        "time": str(scene["time"]),
        "symbol": str(scene["symbol"]),
        "action": str(row_input.get("action", "") or ""),
        "blocked_by": str(row_input.get("blocked_by", "") or ""),
        "action_none_reason": str(row_input.get("action_none_reason", "") or ""),
        "observe_reason": str(wait_metadata.get("observe_reason", "") or ""),
        "entry_wait_state": str(wait_state.state or ""),
        "entry_wait_hard": int(1 if bool(wait_state.hard_wait) else 0),
        "entry_wait_reason": str(wait_state.reason or ""),
        "entry_wait_selected": int(1 if bool(decision.get("selected", False)) else 0),
        "entry_wait_decision": str(decision.get("decision", "skip") or "skip"),
        "entry_enter_value": float(decision.get("enter_value", 0.0) or 0.0),
        "entry_wait_value": float(decision.get("wait_value", 0.0) or 0.0),
        "entry_wait_context_v1": deepcopy(wait_metadata.get("entry_wait_context_v1", {}) or {}),
        "entry_wait_bias_bundle_v1": deepcopy(wait_metadata.get("entry_wait_bias_bundle_v1", {}) or {}),
        "entry_wait_state_policy_input_v1": deepcopy(
            wait_metadata.get("entry_wait_state_policy_input_v1", {}) or {}
        ),
        "entry_wait_energy_usage_trace_v1": deepcopy(
            decision.get("entry_wait_energy_usage_trace_v1", {}) or {}
        ),
        "entry_wait_decision_energy_usage_trace_v1": deepcopy(
            decision.get("entry_wait_decision_energy_usage_trace_v1", {}) or {}
        ),
    }
    for trace_key in ("observe_confirm_v2", "probe_candidate_v1", "entry_probe_plan_v1", "edge_pair_law_v1"):
        if trace_key in row_input:
            persisted_row[trace_key] = deepcopy(row_input[trace_key])
    compact_row = compact_runtime_signal_row(persisted_row)
    hot_payload = build_entry_decision_hot_payload(
        persisted_row,
        detail_row_key=f"wait-e2e-{scene_name}",
    )
    return {
        "scene": scene,
        "decision": decision,
        "row": persisted_row,
        "compact": compact_row,
        "hot": hot_payload,
    }


@pytest.mark.parametrize(
    ("scene_name", "expected_state", "expected_decision", "expected_selected"),
    [
        ("helper_soft_block_wait", "HELPER_SOFT_BLOCK", "wait_soft_helper_block", True),
        ("policy_suppressed_wait", "POLICY_SUPPRESSED", "wait_policy_suppressed", True),
        ("center_skip", "CENTER", "skip", False),
        ("none_skip", "NONE", "skip", False),
        ("xau_probe_active_skip", "ACTIVE", "skip", False),
    ],
)
def test_entry_wait_end_to_end_contract_keeps_state_and_decision_across_runtime_surfaces(
    scene_name,
    expected_state,
    expected_decision,
    expected_selected,
):
    evaluated = _evaluate_wait_scene(scene_name)
    decision = evaluated["decision"]
    row = evaluated["row"]
    compact = evaluated["compact"]
    hot = evaluated["hot"]

    assert decision["wait_state"].state == expected_state
    assert decision["decision"] == expected_decision
    assert decision["selected"] is expected_selected

    assert row["entry_wait_state"] == expected_state
    assert row["entry_wait_decision"] == expected_decision
    assert bool(row["entry_wait_selected"]) is expected_selected
    assert row["entry_wait_context_v1"]["policy"]["state"] == expected_state

    assert compact["entry_wait_state"] == expected_state
    assert compact["entry_wait_decision"] == expected_decision
    assert bool(compact["entry_wait_selected"]) is expected_selected
    assert compact["wait_policy_state"] == expected_state
    assert compact["entry_wait_context_v1"]["policy"]["state"] == expected_state

    hot_context = json.loads(str(hot["entry_wait_context_v1"]))
    hot_bundle = json.loads(str(hot["entry_wait_bias_bundle_v1"]))
    hot_policy_input = json.loads(str(hot["entry_wait_state_policy_input_v1"]))
    assert hot_context["policy"]["state"] == expected_state
    assert hot_bundle["contract_version"] == "entry_wait_bias_bundle_v1"
    assert hot_policy_input["contract_version"] == "entry_wait_state_policy_input_v1"


def test_entry_wait_end_to_end_contract_keeps_special_probe_scene_in_row_and_runtime_surface():
    evaluated = _evaluate_wait_scene("xau_probe_active_skip")
    row = evaluated["row"]
    compact = evaluated["compact"]
    hot = evaluated["hot"]

    assert row["entry_wait_state"] == "ACTIVE"
    assert row["entry_wait_decision"] == "skip"
    assert row["entry_wait_context_v1"]["observe_probe"]["probe_scene_id"] == "xau_second_support_buy_probe"
    assert (
        row["entry_wait_state_policy_input_v1"]["special_scenes"]["probe_scene_id"]
        == "xau_second_support_buy_probe"
    )

    assert compact["wait_probe_scene_id"] == "xau_second_support_buy_probe"
    assert compact["wait_policy_state"] == "ACTIVE"
    assert compact["probe_scene_id"] == "xau_second_support_buy_probe"
    assert compact["quick_trace_state"] == "PROBE_CANDIDATE_BLOCKED"

    hot_context = json.loads(str(hot["entry_wait_context_v1"]))
    hot_policy_input = json.loads(str(hot["entry_wait_state_policy_input_v1"]))
    assert hot_context["observe_probe"]["probe_scene_id"] == "xau_second_support_buy_probe"
    assert hot_policy_input["special_scenes"]["probe_scene_id"] == "xau_second_support_buy_probe"


def test_entry_wait_end_to_end_contract_recent_summary_matches_scene_rows(monkeypatch, tmp_path):
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
    app.entry_decision_log_path = tmp_path / "entry_decisions.csv"

    scene_names = [
        "helper_soft_block_wait",
        "policy_suppressed_wait",
        "center_skip",
        "none_skip",
        "xau_probe_active_skip",
    ]
    evaluated = [_evaluate_wait_scene(name) for name in scene_names]
    rows = [entry["row"] for entry in evaluated]

    _write_entry_decision_log(app.entry_decision_log_path, rows)

    latest_signal_by_symbol = {}
    for entry in evaluated:
        row = entry["row"]
        latest_signal_by_symbol[str(row["symbol"])] = dict(row)
    app.latest_signal_by_symbol = latest_signal_by_symbol

    app._write_runtime_status(
        loop_count=1,
        symbols=["BTCUSD", "NAS100", "XAUUSD"],
        entry_threshold=45,
        exit_threshold=35,
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))

    window = detail["recent_runtime_diagnostics"]["windows"]["last_200"]
    wait_state_summary = window["wait_state_semantic_summary"]
    wait_decision_summary = window["wait_decision_summary"]
    wait_bridge_summary = window["wait_state_decision_bridge_summary"]
    xau_symbol_summary = window["symbol_summary"]["XAUUSD"]

    assert wait_state_summary["row_count"] == 5
    assert wait_state_summary["wait_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_state_summary["wait_state_counts"]["POLICY_SUPPRESSED"] == 1
    assert wait_state_summary["wait_state_counts"]["CENTER"] == 1
    assert wait_state_summary["wait_state_counts"]["NONE"] == 1
    assert wait_state_summary["wait_state_counts"]["ACTIVE"] == 1
    assert wait_state_summary["hard_wait_true_rows"] == 2
    assert wait_state_summary["hard_wait_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_state_summary["hard_wait_state_counts"]["POLICY_SUPPRESSED"] == 1

    assert wait_decision_summary["decision_row_count"] == 5
    assert wait_decision_summary["wait_decision_counts"]["wait_soft_helper_block"] == 1
    assert wait_decision_summary["wait_decision_counts"]["wait_policy_suppressed"] == 1
    assert wait_decision_summary["wait_decision_counts"]["skip"] == 3
    assert wait_decision_summary["wait_selected_rows"] == 2
    assert wait_decision_summary["wait_skipped_rows"] == 3
    assert wait_decision_summary["wait_selected_rate"] == 0.4

    assert wait_bridge_summary["state_to_decision_counts"]["HELPER_SOFT_BLOCK->wait_soft_helper_block"] == 1
    assert wait_bridge_summary["state_to_decision_counts"]["POLICY_SUPPRESSED->wait_policy_suppressed"] == 1
    assert wait_bridge_summary["state_to_decision_counts"]["ACTIVE->skip"] == 1
    assert wait_bridge_summary["state_to_decision_counts"]["CENTER->skip"] == 1
    assert wait_bridge_summary["state_to_decision_counts"]["NONE->skip"] == 1
    assert wait_bridge_summary["selected_by_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_bridge_summary["selected_by_state_counts"]["POLICY_SUPPRESSED"] == 1
    assert wait_bridge_summary["hard_wait_selected_rows"] == 2
    assert wait_bridge_summary["soft_wait_selected_rows"] == 0

    assert xau_symbol_summary["rows"] == 3
    assert xau_symbol_summary["wait_state_semantic_summary"]["wait_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert xau_symbol_summary["wait_state_semantic_summary"]["wait_state_counts"]["CENTER"] == 1
    assert xau_symbol_summary["wait_state_semantic_summary"]["wait_state_counts"]["ACTIVE"] == 1
    assert xau_symbol_summary["wait_decision_summary"]["wait_selected_rows"] == 1
    assert xau_symbol_summary["wait_state_decision_bridge_summary"]["state_to_decision_counts"]["ACTIVE->skip"] == 1

    assert slim["recent_wait_state_semantic_summary"]["wait_state_counts"]["POLICY_SUPPRESSED"] == 1
    assert slim["recent_wait_decision_summary"]["wait_selected_rate"] == 0.4
    assert (
        slim["recent_wait_state_decision_bridge_summary"]["state_to_decision_counts"][
            "HELPER_SOFT_BLOCK->wait_soft_helper_block"
        ]
        == 1
    )
