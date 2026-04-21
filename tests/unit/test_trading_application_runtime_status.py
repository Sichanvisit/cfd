import csv
import json
import time

import backend.app.trading_application as trading_application_module
from backend.app.trading_application import (
    TradingApplication,
    _reset_runtime_signal_downstream_derived_fields,
    _runtime_signal_wiring_audit_artifact_write_allowed,
)


class _DummyBroker:
    def __init__(self, positions=None, rates_by_timeframe=None):
        self._positions = list(positions or [])
        self._rates_by_timeframe = dict(rates_by_timeframe or {})

    def positions_get(self, symbol: str = "", ticket: int | None = None):
        rows = list(self._positions)
        if ticket is not None:
            rows = [row for row in rows if int(getattr(row, "ticket", 0) or 0) == int(ticket)]
        if symbol:
            rows = [row for row in rows if str(getattr(row, "symbol", "") or "").upper() == str(symbol).upper()]
        return rows

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start_pos: int, count: int):
        return list(self._rates_by_timeframe.get(int(timeframe), []))


class _DummyPosition:
    def __init__(self, *, ticket: int, symbol: str, magic: int):
        self.ticket = int(ticket)
        self.symbol = str(symbol)
        self.magic = int(magic)


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


def _build_rates(*, start: float, step: float, count: int = 120):
    rows = []
    price = float(start)
    for index in range(count):
        open_price = price
        close_price = price + step
        rows.append(
            {
                "time": 1_700_000_000 + (index * 60),
                "open": float(open_price),
                "high": float(max(open_price, close_price) + 0.4),
                "low": float(min(open_price, close_price) - 0.4),
                "close": float(close_price),
            }
        )
        price = close_price
    return rows


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
            writer.writerow(row)


def test_reset_runtime_signal_downstream_derived_fields_strips_stale_flow_chain_fields():
    rows = {
        "NAS100": {
            "symbol": "NAS100",
            "signal_bar_ts": 1773817800,
            "my_position_count": 1,
            "consumer_check_side": "SELL",
            "directional_continuation_overlay_direction": "UP",
            "common_state_slot_core_v1": "BEAR_CONTINUATION_INITIATION",
            "flow_structure_gate_v1": "INELIGIBLE",
            "flow_support_state_v1": "FLOW_OPPOSED",
            "state_strength_profile_v1": {"contract_version": "state_strength_profile_contract_v1"},
            "state_strength_dominant_side_v1": "BEAR",
            "few_candle_structure_bias_v1": "REVERSAL_FAVOR",
            "breakout_hold_quality_v1": "FAILED",
            "body_drive_state_v1": "COUNTER_DRIVE",
            "runtime_readonly_surface_v1": {"contract_version": "runtime_readonly_surface_v1"},
            "consumer_veto_tier_v1": "REVERSAL_OVERRIDE",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "local_continuation_discount_v1": 0.3,
            "would_override_caution_v1": True,
            "state_slot_bridge_state_v1": "READY",
            "bridge_source_slot_v1": "BULL_RECOVERY_ACCEPTANCE",
            "entry_bias_v1": "MEDIUM",
            "hold_bias_v1": "HIGH",
            "add_bias_v1": "LOW",
            "reduce_bias_v1": "HIGH",
            "exit_bias_v1": "MEDIUM",
            "state_slot_execution_bridge_reason_summary_v1": "stale bridge",
            "state_slot_lifecycle_policy_state_v1": "READY",
            "state_slot_execution_policy_source_v1": "BRIDGE_BIAS",
            "entry_policy_v1": "SELECTIVE_ENTRY",
            "hold_policy_v1": "STRONG_HOLD",
            "add_policy_v1": "PROBE_ADD_ONLY",
            "reduce_policy_v1": "REDUCE_STRONG",
            "exit_policy_v1": "EXIT_PREP",
            "state_slot_lifecycle_policy_reason_summary_v1": "stale lifecycle",
            "lifecycle_policy_alignment_state_v1": "ALIGNED",
            "entry_delay_conflict_flag_v1": True,
            "hold_support_alignment_v1": "SUPPORTED",
            "reduce_exit_pressure_alignment_v1": "SUPPORTED",
            "execution_policy_shadow_error_type_v1": "ALIGNED",
            "execution_policy_shadow_reason_summary_v1": "stale shadow audit",
            "bounded_candidate_feedback_loop_action_v1": "ROLLBACK_CANDIDATE",
            "flow_shadow_axes_summary_v1": "지속 10% / 진입 5% / 반전 90%",
        }
    }

    cleaned = _reset_runtime_signal_downstream_derived_fields(rows)
    row = cleaned["NAS100"]

    assert row["symbol"] == "NAS100"
    assert row["signal_bar_ts"] == 1773817800
    assert row["my_position_count"] == 1
    assert row["consumer_check_side"] == "SELL"
    assert row["directional_continuation_overlay_direction"] == "UP"
    assert "common_state_slot_core_v1" not in row
    assert "flow_structure_gate_v1" not in row
    assert "flow_support_state_v1" not in row
    assert "state_strength_profile_v1" not in row
    assert "state_strength_dominant_side_v1" not in row
    assert "few_candle_structure_bias_v1" not in row
    assert "breakout_hold_quality_v1" not in row
    assert "body_drive_state_v1" not in row
    assert "runtime_readonly_surface_v1" not in row
    assert "consumer_veto_tier_v1" not in row
    assert "dominance_shadow_dominant_side_v1" not in row
    assert "local_continuation_discount_v1" not in row
    assert "would_override_caution_v1" not in row
    assert "state_slot_bridge_state_v1" not in row
    assert "bridge_source_slot_v1" not in row
    assert "entry_bias_v1" not in row
    assert "hold_bias_v1" not in row
    assert "add_bias_v1" not in row
    assert "reduce_bias_v1" not in row
    assert "exit_bias_v1" not in row
    assert "state_slot_execution_bridge_reason_summary_v1" not in row
    assert "state_slot_lifecycle_policy_state_v1" not in row
    assert "state_slot_execution_policy_source_v1" not in row
    assert "entry_policy_v1" not in row
    assert "hold_policy_v1" not in row
    assert "add_policy_v1" not in row
    assert "reduce_policy_v1" not in row
    assert "exit_policy_v1" not in row
    assert "state_slot_lifecycle_policy_reason_summary_v1" not in row
    assert "lifecycle_policy_alignment_state_v1" not in row
    assert "entry_delay_conflict_flag_v1" not in row
    assert "hold_support_alignment_v1" not in row
    assert "reduce_exit_pressure_alignment_v1" not in row
    assert "execution_policy_shadow_error_type_v1" not in row
    assert "execution_policy_shadow_reason_summary_v1" not in row
    assert "bounded_candidate_feedback_loop_action_v1" not in row
    assert "flow_shadow_axes_summary_v1" not in row


def test_runtime_status_wiring_audit_uses_final_flow_shadow_rows(monkeypatch, tmp_path):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        TradingApplication,
        "_enrich_runtime_signal_rows_with_state_context",
        lambda self, rows: {str(symbol): dict(row or {}) for symbol, row in dict(rows or {}).items()},
    )

    audit_calls = []
    sync_calls = []

    def fake_attach_flow_shadow_display_surface_fields(rows):
        enriched = {}
        for symbol, row in dict(rows or {}).items():
            payload = dict(row or {})
            payload.update(
                {
                    "flow_shadow_chart_event_ownership_v1": "SHADOW_DISPLAY",
                    "flow_shadow_chart_event_emit_v1": True,
                    "flow_shadow_chart_event_final_kind_v1": "BUY_WATCH",
                    "flow_shadow_chart_event_emit_reason_v1": "final_shadow_event",
                }
            )
            enriched[str(symbol)] = payload
        return enriched

    def fake_generate_runtime_signal_wiring_audit(rows, **kwargs):
        snapshot = {
            str(symbol): dict(row or {})
            for symbol, row in dict(rows or {}).items()
            if isinstance(row, dict)
        }
        audit_calls.append({"rows": snapshot, "kwargs": dict(kwargs)})
        has_final_flow_shadow = bool(
            snapshot.get("NAS100", {}).get("flow_shadow_chart_event_final_kind_v1")
        )
        if has_final_flow_shadow:
            assert sync_calls
            assert sync_calls[-1]["NAS100"]["flow_shadow_chart_event_final_kind_v1"] == "BUY_WATCH"
        return {
            "summary": {
                "symbol_count": len(snapshot),
                "overlay_present_count": 0,
                "execution_diff_surface_count": 0,
                "accuracy_surface_count": 0,
                "flow_sync_match_count": 1 if has_final_flow_shadow else 0,
            },
            "artifact_paths": {},
        }

    monkeypatch.setattr(
        trading_application_module,
        "attach_flow_shadow_display_surface_fields_v1",
        fake_attach_flow_shadow_display_surface_fields,
    )
    monkeypatch.setattr(
        trading_application_module,
        "generate_and_write_runtime_signal_wiring_audit",
        fake_generate_runtime_signal_wiring_audit,
    )

    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.runtime_status_path = tmp_path / "runtime_status.json"
    app.runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    app.semantic_rollout_manifest_path = tmp_path / "semantic_live_rollout_latest.json"
    app.entry_decision_log_path = tmp_path / "missing_entry_decisions.csv"
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"
    app.latest_signal_by_symbol = {
        "NAS100": {
            "symbol": "NAS100",
            "observe_confirm_v2": {
                "action": "WAIT",
                "side": "BUY",
                "reason": "fallback_watch_start",
            },
        }
    }
    app.runtime_flow_history_sync_hook = lambda rows: sync_calls.append(
        {
            str(symbol): dict(row or {})
            for symbol, row in dict(rows or {}).items()
            if isinstance(row, dict)
        }
    )

    app._write_runtime_status(
        1,
        {"NAS100": "NAS100"},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert len(audit_calls) >= 2
    assert audit_calls[0]["kwargs"].get("write_artifacts") is False
    assert "flow_shadow_chart_event_final_kind_v1" not in audit_calls[0]["rows"]["NAS100"]
    assert sync_calls
    assert audit_calls[-1]["kwargs"].get("write_artifacts", True) is True
    assert audit_calls[-1]["rows"]["NAS100"]["flow_shadow_chart_event_final_kind_v1"] == "BUY_WATCH"
    assert detail["runtime_signal_wiring_audit_summary_v1"]["flow_sync_match_count"] == 1


def test_runtime_signal_wiring_audit_artifact_write_waits_for_all_symbols():
    rows = {
        "NAS100": {"symbol": "NAS100"},
        "XAUUSD": {"symbol": "XAUUSD"},
    }

    assert not _runtime_signal_wiring_audit_artifact_write_allowed(
        rows,
        {"NAS100": "NAS100", "XAUUSD": "XAUUSD", "BTCUSD": "BTCUSD"},
    )
    assert _runtime_signal_wiring_audit_artifact_write_allowed(
        {
            **rows,
            "BTCUSD": {"symbol": "BTCUSD"},
        },
        {"NAS100": "NAS100", "XAUUSD": "XAUUSD", "BTCUSD": "BTCUSD"},
    )
    assert _runtime_signal_wiring_audit_artifact_write_allowed(rows, {})


def test_runtime_status_exports_state25_candidate_runtime_blocks(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"
    app.state25_active_candidate_state_path = tmp_path / "active_candidate_state.json"
    app.state25_active_candidate_state_path.write_text(
        json.dumps(
            {
                "active_candidate_id": "candidate_99",
                "active_policy_source": "state25_candidate",
                "current_rollout_phase": "log_only",
                "current_binding_mode": "log_only",
                "activated_at": "2026-04-03T17:40:00+09:00",
                "last_event": "promote_log_only",
                "desired_runtime_patch": {
                    "apply_now": True,
                    "state25_execution_bind_mode": "log_only",
                    "state25_execution_symbol_allowlist": ["BTCUSD", "NAS100"],
                    "state25_execution_entry_stage_allowlist": ["READY", "PROBE"],
                    "state25_threshold_log_only_enabled": True,
                    "state25_threshold_log_only_max_adjustment_abs": 6,
                    "state25_size_log_only_enabled": True,
                    "state25_size_log_only_min_multiplier": 0.85,
                    "state25_size_log_only_max_multiplier": 1.15,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    app.refresh_state25_candidate_runtime_state()

    app._write_runtime_status(
        7,
        {},
        45,
        70,
        adverse_loss_usd=120.0,
        reverse_signal_threshold=28,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))

    assert slim["state25_candidate_runtime_v1"]["state_source_status"] == "loaded"
    assert slim["state25_candidate_runtime_v1"]["active_candidate_id"] == "candidate_99"
    assert slim["state25_candidate_runtime_v1"]["current_rollout_phase"] == "log_only"
    assert slim["state25_candidate_threshold_surface_v1"]["enabled"] is True
    assert slim["state25_candidate_threshold_surface_v1"]["mode"] == "log_only"
    assert slim["state25_candidate_threshold_surface_v1"]["max_adjustment_abs"] == 6
    assert slim["state25_candidate_size_surface_v1"]["enabled"] is True
    assert slim["state25_candidate_size_surface_v1"]["candidate_log_only_min_multiplier"] == 0.85
    assert detail["state25_candidate_runtime_v1"]["desired_runtime_patch"]["apply_now"] is True


def test_runtime_status_exports_state_strength_s0_stability_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert "state_strength_s0_stability_summary_v1" in detail
    assert "state_strength_s0_stability_artifact_paths" in detail
    assert detail["state_strength_s0_stability_summary_v1"]["dependency_count"] == 6


def test_runtime_status_exports_state_polarity_d0_stability_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert "state_polarity_d0_stability_summary_v1" in detail
    assert "state_polarity_d0_stability_artifact_paths" in detail
    assert detail["state_polarity_d0_stability_summary_v1"]["dependency_count"] == 7


def test_runtime_status_exports_state_polarity_slot_vocabulary_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["state_polarity_slot_vocabulary_contract_v1"]["contract_version"] == (
        "state_polarity_slot_vocabulary_contract_v1"
    )
    assert "state_polarity_slot_vocabulary_summary_v1" in detail
    assert "state_polarity_slot_vocabulary_artifact_paths" in detail


def test_runtime_status_exports_rejection_split_rule_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["rejection_split_rule_contract_v1"]["contract_version"] == "rejection_split_rule_contract_v1"
    assert "rejection_split_rule_summary_v1" in detail
    assert "rejection_split_rule_artifact_paths" in detail


def test_runtime_status_exports_continuation_stage_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["continuation_stage_contract_v1"]["contract_version"] == "continuation_stage_contract_v1"
    assert "continuation_stage_summary_v1" in detail
    assert "continuation_stage_artifact_paths" in detail


def test_runtime_status_exports_location_context_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["location_context_contract_v1"]["contract_version"] == "location_context_contract_v1"
    assert "location_context_summary_v1" in detail
    assert "location_context_artifact_paths" in detail


def test_runtime_status_exports_tempo_profile_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["tempo_profile_contract_v1"]["contract_version"] == "tempo_profile_contract_v1"
    assert "tempo_profile_summary_v1" in detail
    assert "tempo_profile_artifact_paths" in detail


def test_runtime_status_exports_ambiguity_modifier_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["ambiguity_modifier_contract_v1"]["contract_version"] == "ambiguity_modifier_contract_v1"
    assert "ambiguity_modifier_summary_v1" in detail
    assert "ambiguity_modifier_artifact_paths" in detail


def test_runtime_status_exports_xau_readonly_surface_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["xau_readonly_surface_contract_v1"]["contract_version"] == "xau_readonly_surface_contract_v1"
    assert "xau_readonly_surface_summary_v1" in detail
    assert "xau_readonly_surface_artifact_paths" in detail


def test_runtime_status_exports_xau_decomposition_validation_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["xau_decomposition_validation_contract_v1"]["contract_version"] == (
        "xau_decomposition_validation_contract_v1"
    )
    assert "xau_decomposition_validation_summary_v1" in detail
    assert "xau_decomposition_validation_artifact_paths" in detail


def test_runtime_status_exports_xau_refined_gate_timebox_audit_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["xau_refined_gate_timebox_audit_contract_v1"]["contract_version"] == (
        "xau_refined_gate_timebox_audit_contract_v1"
    )
    assert "xau_refined_gate_timebox_audit_summary_v1" in detail
    assert "xau_refined_gate_timebox_audit_artifact_paths" in detail


def test_runtime_status_exports_state_flow_f0_chain_alignment_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["state_flow_f0_chain_alignment_contract_v1"]["contract_version"] == (
        "state_flow_f0_chain_alignment_contract_v1"
    )
    assert "state_flow_f0_chain_alignment_summary_v1" in detail
    assert "state_flow_f0_chain_alignment_artifact_paths" in detail


def test_runtime_status_exports_flow_structure_gate_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["flow_structure_gate_contract_v1"]["contract_version"] == "flow_structure_gate_contract_v1"
    assert "flow_structure_gate_summary_v1" in detail
    assert "flow_structure_gate_artifact_paths" in detail


def test_runtime_status_exports_aggregate_directional_flow_metrics_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["aggregate_directional_flow_metrics_contract_v1"]["contract_version"] == (
        "aggregate_directional_flow_metrics_contract_v1"
    )
    assert "aggregate_directional_flow_metrics_summary_v1" in detail
    assert "aggregate_directional_flow_metrics_artifact_paths" in detail


def test_runtime_status_exports_retained_window_flow_calibration_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["retained_window_flow_calibration_contract_v1"]["contract_version"] == (
        "retained_window_flow_calibration_contract_v1"
    )
    assert "retained_window_flow_calibration_summary_v1" in detail
    assert "retained_window_flow_calibration_artifact_paths" in detail


def test_runtime_status_exports_flow_threshold_provisional_band_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["flow_threshold_provisional_band_contract_v1"]["contract_version"] == (
        "flow_threshold_provisional_band_contract_v1"
    )
    assert "flow_threshold_provisional_band_summary_v1" in detail
    assert "flow_threshold_provisional_band_artifact_paths" in detail


def test_runtime_status_exports_exact_pilot_match_bonus_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["exact_pilot_match_bonus_contract_v1"]["contract_version"] == (
        "exact_pilot_match_bonus_contract_v1"
    )
    assert "exact_pilot_match_bonus_summary_v1" in detail
    assert "exact_pilot_match_bonus_artifact_paths" in detail


def test_runtime_status_exports_flow_support_state_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["flow_support_state_contract_v1"]["contract_version"] == (
        "flow_support_state_contract_v1"
    )
    assert "flow_support_state_summary_v1" in detail
    assert "flow_support_state_artifact_paths" in detail


def test_runtime_status_exports_flow_chain_shadow_comparison_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["flow_chain_shadow_comparison_contract_v1"]["contract_version"] == (
        "flow_chain_shadow_comparison_contract_v1"
    )
    assert "flow_chain_shadow_comparison_summary_v1" in detail
    assert "flow_chain_shadow_comparison_artifact_paths" in detail


def test_runtime_status_exports_flow_candidate_improvement_review_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["flow_candidate_improvement_review_contract_v1"]["contract_version"] == (
        "flow_candidate_improvement_review_contract_v1"
    )
    assert "flow_candidate_improvement_review_summary_v1" in detail
    assert "flow_candidate_improvement_review_artifact_paths" in detail


def test_runtime_status_exports_nas_btc_hard_opposed_truth_audit_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["nas_btc_hard_opposed_truth_audit_contract_v1"]["contract_version"] == (
        "nas_btc_hard_opposed_truth_audit_contract_v1"
    )
    assert "nas_btc_hard_opposed_truth_audit_summary_v1" in detail
    assert "nas_btc_hard_opposed_truth_audit_artifact_paths" in detail


def test_runtime_status_exports_bounded_calibration_candidate_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["bounded_calibration_candidate_contract_v1"]["contract_version"] == (
        "bounded_calibration_candidate_contract_v1"
    )
    assert "bounded_calibration_candidate_summary_v1" in detail
    assert "bounded_calibration_candidate_artifact_paths" in detail
    assert "row_primary_candidate_graduation_state_count_summary" in detail["bounded_calibration_candidate_summary_v1"]
    assert detail["bounded_candidate_shadow_apply_contract_v1"]["contract_version"] == (
        "bounded_candidate_shadow_apply_contract_v1"
    )
    assert "bounded_candidate_shadow_apply_summary_v1" in detail
    assert "bounded_candidate_shadow_apply_artifact_paths" in detail
    assert detail["bounded_candidate_evaluation_dashboard_contract_v1"]["contract_version"] == (
        "bounded_candidate_evaluation_dashboard_contract_v1"
    )
    assert "bounded_candidate_evaluation_dashboard_summary_v1" in detail
    assert "bounded_candidate_evaluation_dashboard_artifact_paths" in detail
    assert detail["bounded_candidate_lifecycle_feedback_loop_contract_v1"]["contract_version"] == (
        "bounded_candidate_lifecycle_feedback_loop_contract_v1"
    )
    assert "bounded_candidate_lifecycle_feedback_loop_summary_v1" in detail
    assert "bounded_candidate_lifecycle_feedback_loop_artifact_paths" in detail
    assert detail["bounded_candidate_patch_memory_loop_contract_v1"]["contract_version"] == (
        "bounded_candidate_patch_memory_loop_contract_v1"
    )
    assert "bounded_candidate_patch_memory_loop_summary_v1" in detail
    assert "bounded_candidate_patch_memory_loop_artifact_paths" in detail


def test_runtime_status_exports_nas_btc_pilot_and_validation_contracts(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["nas_pilot_mapping_contract_v1"]["contract_version"] == "nas_pilot_mapping_contract_v1"
    assert detail["btc_pilot_mapping_contract_v1"]["contract_version"] == "btc_pilot_mapping_contract_v1"
    assert detail["nas_readonly_surface_contract_v1"]["contract_version"] == "nas_readonly_surface_contract_v1"
    assert detail["btc_readonly_surface_contract_v1"]["contract_version"] == "btc_readonly_surface_contract_v1"
    assert detail["nas_decomposition_validation_contract_v1"]["contract_version"] == (
        "nas_decomposition_validation_contract_v1"
    )
    assert detail["btc_decomposition_validation_contract_v1"]["contract_version"] == (
        "btc_decomposition_validation_contract_v1"
    )
    assert "nas_pilot_mapping_summary_v1" in detail
    assert "btc_pilot_mapping_summary_v1" in detail
    assert "nas_readonly_surface_summary_v1" in detail
    assert "btc_readonly_surface_summary_v1" in detail
    assert "nas_decomposition_validation_summary_v1" in detail
    assert "btc_decomposition_validation_summary_v1" in detail


def test_runtime_status_exports_state_slot_commonization_judge_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["state_slot_commonization_judge_contract_v1"]["contract_version"] == (
        "state_slot_commonization_judge_contract_v1"
    )
    assert "state_slot_commonization_judge_summary_v1" in detail
    assert "state_slot_commonization_judge_artifact_paths" in detail


def test_runtime_status_exports_state_slot_execution_interface_bridge_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["state_slot_execution_interface_bridge_contract_v1"]["contract_version"] == (
        "state_slot_execution_interface_bridge_contract_v1"
    )
    assert "state_slot_execution_interface_bridge_summary_v1" in detail
    assert "state_slot_execution_interface_bridge_artifact_paths" in detail


def test_runtime_status_exports_state_slot_symbol_extension_surface_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["state_slot_symbol_extension_surface_contract_v1"]["contract_version"] == (
        "state_slot_symbol_extension_surface_contract_v1"
    )
    assert "state_slot_symbol_extension_surface_summary_v1" in detail
    assert "state_slot_symbol_extension_surface_artifact_paths" in detail


def test_runtime_status_exports_state_slot_position_lifecycle_policy_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["state_slot_position_lifecycle_policy_contract_v1"]["contract_version"] == (
        "state_slot_position_lifecycle_policy_contract_v1"
    )
    assert "state_slot_position_lifecycle_policy_summary_v1" in detail
    assert "state_slot_position_lifecycle_policy_artifact_paths" in detail


def test_runtime_status_exports_execution_policy_shadow_audit_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["execution_policy_shadow_audit_contract_v1"]["contract_version"] == (
        "execution_policy_shadow_audit_contract_v1"
    )
    assert "execution_policy_shadow_audit_summary_v1" in detail
    assert "execution_policy_shadow_audit_artifact_paths" in detail


def test_runtime_status_exports_bounded_lifecycle_canary_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["bounded_lifecycle_canary_contract_v1"]["contract_version"] == (
        "bounded_lifecycle_canary_contract_v1"
    )
    assert "bounded_lifecycle_canary_summary_v1" in detail
    assert "bounded_lifecycle_canary_artifact_paths" in detail


def test_runtime_status_exports_xau_pilot_mapping_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["xau_pilot_mapping_contract_v1"]["contract_version"] == "xau_pilot_mapping_contract_v1"
    assert "xau_pilot_mapping_summary_v1" in detail
    assert "xau_pilot_mapping_artifact_paths" in detail


def test_runtime_status_exports_state_strength_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["state_strength_profile_contract_v1"]["contract_version"] == "state_strength_profile_contract_v1"
    assert "state_strength_summary_v1" in detail
    assert "state_strength_artifact_paths" in detail


def test_runtime_status_exports_local_structure_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["local_structure_profile_contract_v1"]["contract_version"] == "local_structure_profile_contract_v1"
    assert "local_structure_summary_v1" in detail
    assert "local_structure_artifact_paths" in detail


def test_runtime_status_exports_runtime_readonly_surface_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["runtime_readonly_surface_contract_v1"]["contract_version"] == "runtime_readonly_surface_contract_v1"
    assert "runtime_readonly_surface_summary_v1" in detail
    assert "runtime_readonly_surface_artifact_paths" in detail


def test_runtime_status_exports_state_structure_dominance_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["state_structure_dominance_contract_v1"]["contract_version"] == "state_structure_dominance_contract_v1"
    assert "state_structure_dominance_summary_v1" in detail
    assert "state_structure_dominance_artifact_paths" in detail


def test_runtime_status_exports_dominance_validation_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["dominance_validation_contract_v1"]["contract_version"] == "dominance_validation_contract_v1"
    assert "dominance_validation_summary_v1" in detail
    assert "dominance_validation_artifact_paths" in detail


def test_runtime_status_exports_dominance_accuracy_shadow_contract_and_summaries(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["dominance_accuracy_shadow_contract_v1"]["contract_version"] == "dominance_accuracy_shadow_contract_v1"
    assert "dominance_accuracy_summary_v1" in detail
    assert "dominance_candidate_shadow_report_v1" in detail
    assert "dominance_accuracy_shadow_artifact_paths" in detail


def test_runtime_status_exports_symbol_specific_state_strength_calibration_contract_and_summary(
    monkeypatch, tmp_path
):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert (
        detail["symbol_specific_state_strength_calibration_contract_v1"]["contract_version"]
        == "symbol_specific_state_strength_calibration_contract_v1"
    )
    assert "symbol_specific_state_strength_calibration_summary_v1" in detail
    assert "symbol_specific_state_strength_calibration_artifact_paths" in detail


def test_runtime_row_context_export_includes_state25_context_bridge(monkeypatch, tmp_path):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        "backend.app.trading_application.build_context_state_v12",
        lambda **kwargs: {
            "htf_alignment_state": "AGAINST_HTF",
            "htf_against_severity": "HIGH",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_confidence": "MEDIUM",
            "previous_box_is_consolidation": True,
            "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
            "late_chase_risk_state": "NONE",
            "trend_1h_age_seconds": 60,
            "trend_4h_age_seconds": 60,
            "trend_1d_age_seconds": 60,
            "previous_box_age_seconds": 60,
        },
    )
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.state25_candidate_runtime_state = {
        "state25_teacher_weight_overrides": {
            "reversal_risk_weight": 1.0,
        }
    }

    enriched = app._enrich_runtime_signal_row_with_state_context(
        "BTCUSD",
        {
            "symbol": "BTCUSD",
            "consumer_check_side": "SELL",
            "effective_entry_threshold": 40.0,
            "final_score": 42.0,
        },
    )

    assert enriched["state25_candidate_context_bridge_v1"]["contract_version"] == "state25_candidate_context_bridge_v1"
    assert enriched["state25_context_bridge_stage"] == "BC6_THRESHOLD_LOG_ONLY"
    assert enriched["state25_context_bridge_weight_effective_count"] >= 1
    assert enriched["state25_context_bridge_threshold_requested_points"] > 0.0
    assert enriched["state25_context_bridge_threshold_effective_points"] > 0.0
    assert enriched["state25_context_bridge_threshold_direction"] == "HARDEN"
    assert enriched["state25_context_bridge_threshold_changed_decision"] is True


def test_runtime_status_state25_candidate_runtime_missing_file_falls_back(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"
    app.state25_active_candidate_state_path = tmp_path / "missing_active_candidate_state.json"
    app.refresh_state25_candidate_runtime_state()

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))

    assert slim["state25_candidate_runtime_v1"]["state_source_status"] == "missing_fallback"
    assert slim["state25_candidate_runtime_v1"]["active_policy_source"] == "current_baseline"
    assert slim["state25_candidate_threshold_surface_v1"]["enabled"] is False


def test_runtime_status_preserves_trace_quality_fields(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "trade_history.csv"
    btc_wait_bias_bundle = {
        "contract_version": "entry_wait_bias_bundle_v1",
        "active_release_sources": ["belief"],
        "active_wait_lock_sources": ["state"],
        "release_bias_count": 1,
        "wait_lock_bias_count": 1,
        "threshold_adjustment": {
            "base_soft_threshold": 45.0,
            "base_hard_threshold": 70.0,
            "effective_soft_threshold": 38.25,
            "effective_hard_threshold": 77.0,
            "combined_soft_multiplier": 0.85,
            "combined_hard_multiplier": 1.1,
        },
    }
    btc_wait_state_policy_input = {
        "contract_version": "entry_wait_state_policy_input_v1",
        "identity": {"symbol": "BTCUSD", "required_side": "BUY"},
        "helper_hints": {
            "wait_vs_enter_hint": "prefer_wait",
            "soft_block_active": True,
            "soft_block_reason": "energy_soft_block",
            "soft_block_strength": 0.66,
            "policy_hard_block_active": True,
            "policy_suppressed": False,
        },
        "special_scenes": {
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "probe_active": True,
            "probe_ready_for_entry": False,
            "xau_second_support_probe_relief": False,
            "btc_lower_strong_score_soft_wait_candidate": True,
        },
        "thresholds": {
            "base_soft_threshold": 45.0,
            "base_hard_threshold": 70.0,
            "effective_soft_threshold": 38.25,
            "effective_hard_threshold": 77.0,
        },
        "bias_bundle": {
            "active_release_sources": ["belief"],
            "active_wait_lock_sources": ["state"],
            "release_bias_count": 1,
            "wait_lock_bias_count": 1,
        },
    }
    btc_wait_context = {
        "contract_version": "entry_wait_context_v1",
        "identity": {"symbol": "BTCUSD", "action": "BUY"},
        "reasons": {
            "blocked_by": "energy_soft_block",
            "observe_reason": "lower_rebound_probe_observe",
            "action_none_reason": "execution_soft_blocked",
        },
        "observe_probe": {
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "probe_active": True,
            "probe_ready_for_entry": False,
            "xau_second_support_probe_relief": False,
        },
        "bias": {"bundle": dict(btc_wait_bias_bundle)},
        "policy": {
            "state": "HELPER_SOFT_BLOCK",
            "reason": "soft_block_preferred_wait",
            "hard_wait": True,
            "entry_wait_state_policy_input_v1": dict(btc_wait_state_policy_input),
        },
    }
    xau_wait_bias_bundle = {
        "contract_version": "entry_wait_bias_bundle_v1",
        "active_release_sources": ["probe"],
        "active_wait_lock_sources": [],
        "release_bias_count": 1,
        "wait_lock_bias_count": 0,
        "threshold_adjustment": {
            "base_soft_threshold": 45.0,
            "base_hard_threshold": 70.0,
            "effective_soft_threshold": 45.0,
            "effective_hard_threshold": 70.0,
            "combined_soft_multiplier": 1.0,
            "combined_hard_multiplier": 1.0,
        },
    }
    xau_wait_state_policy_input = {
        "contract_version": "entry_wait_state_policy_input_v1",
        "identity": {"symbol": "XAUUSD", "required_side": "BUY"},
        "helper_hints": {
            "wait_vs_enter_hint": "",
            "soft_block_active": False,
            "soft_block_reason": "",
            "soft_block_strength": 0.0,
            "policy_hard_block_active": False,
            "policy_suppressed": False,
        },
        "special_scenes": {
            "probe_scene_id": "xau_second_support_buy_probe",
            "probe_active": True,
            "probe_ready_for_entry": True,
            "xau_second_support_probe_relief": True,
            "btc_lower_strong_score_soft_wait_candidate": False,
        },
        "thresholds": {
            "base_soft_threshold": 45.0,
            "base_hard_threshold": 70.0,
            "effective_soft_threshold": 45.0,
            "effective_hard_threshold": 70.0,
        },
        "bias_bundle": {
            "active_release_sources": ["probe"],
            "active_wait_lock_sources": [],
            "release_bias_count": 1,
            "wait_lock_bias_count": 0,
        },
    }
    xau_wait_context = {
        "contract_version": "entry_wait_context_v1",
        "identity": {"symbol": "XAUUSD", "action": "BUY"},
        "reasons": {
            "blocked_by": "",
            "observe_reason": "lower_rebound_probe_observe",
            "action_none_reason": "",
        },
        "observe_probe": {
            "probe_scene_id": "xau_second_support_buy_probe",
            "probe_active": True,
            "probe_ready_for_entry": True,
            "xau_second_support_probe_relief": True,
        },
        "bias": {"bundle": dict(xau_wait_bias_bundle)},
        "policy": {
            "state": "PROBE_CANDIDATE",
            "reason": "xau_second_support_probe_wait",
            "hard_wait": False,
            "entry_wait_state_policy_input_v1": dict(xau_wait_state_policy_input),
        },
    }
    _write_entry_decision_log(
        app.entry_decision_log_path,
        [
            {
                "time": "2026-03-27T19:00:00+09:00",
                "symbol": "BTCUSD",
                "blocked_by": "energy_soft_block",
                "action_none_reason": "execution_soft_blocked",
                "consumer_check_stage": "BLOCKED",
                "consumer_check_entry_ready": "False",
                "consumer_check_display_ready": "True",
                "entry_wait_state": "HELPER_SOFT_BLOCK",
                "entry_wait_hard": "True",
                "entry_wait_reason": "soft_block_preferred_wait",
                "entry_wait_selected": "True",
                "entry_wait_decision": "wait_soft_helper_block",
                "entry_wait_context_v1": json.dumps(btc_wait_context),
                "entry_wait_bias_bundle_v1": json.dumps(btc_wait_bias_bundle),
                "entry_wait_state_policy_input_v1": json.dumps(btc_wait_state_policy_input),
                "entry_wait_energy_usage_trace_v1": json.dumps(
                    {
                        "contract_version": "consumer_energy_usage_trace_v1",
                        "usage_source": "recorded",
                        "usage_mode": "wait_state_branch_applied",
                        "branch_records": [
                            {"branch": "helper_soft_block_state"},
                            {"branch": "helper_soft_block_hard_wait"},
                        ],
                    }
                ),
                "entry_wait_decision_energy_usage_trace_v1": json.dumps(
                    {
                        "contract_version": "consumer_energy_usage_trace_v1",
                        "usage_source": "recorded",
                        "usage_mode": "wait_decision_branch_applied",
                        "branch_records": [
                            {"branch": "action_readiness_utility"},
                            {"branch": "wait_soft_helper_block_decision"},
                        ],
                    }
                ),
            },
            {
                "time": "2026-03-27T19:01:00+09:00",
                "symbol": "NAS100",
                "blocked_by": "forecast_guard",
                "action_none_reason": "",
                "consumer_check_stage": "READY",
                "consumer_check_entry_ready": "True",
                "consumer_check_display_ready": "True",
                "entry_wait_state": "NONE",
                "entry_wait_hard": "False",
                "entry_wait_reason": "",
                "entry_wait_selected": "False",
                "entry_wait_decision": "skip",
                "entry_wait_energy_usage_trace_v1": json.dumps(
                    {
                        "contract_version": "consumer_energy_usage_trace_v1",
                        "usage_source": "recorded",
                        "usage_mode": "wait_state_branch_applied",
                        "branch_records": [
                            {"branch": "helper_wait_bias_state"},
                        ],
                    }
                ),
            },
            {
                "time": "2026-03-27T19:02:00+09:00",
                "symbol": "XAUUSD",
                "blocked_by": "",
                "action_none_reason": "",
                "consumer_check_stage": "PROBE",
                "consumer_check_entry_ready": "False",
                "consumer_check_display_ready": "True",
                "entry_wait_state": "PROBE_CANDIDATE",
                "entry_wait_hard": "False",
                "entry_wait_reason": "xau_second_support_probe_wait",
                "entry_wait_selected": "True",
                "entry_wait_decision": "wait_soft_probe_candidate",
                "entry_wait_context_v1": json.dumps(xau_wait_context),
                "entry_wait_bias_bundle_v1": json.dumps(xau_wait_bias_bundle),
                "entry_wait_state_policy_input_v1": json.dumps(xau_wait_state_policy_input),
            },
            {
                "time": "2026-03-27T19:03:00+09:00",
                "symbol": "BTCUSD",
                "blocked_by": "",
                "action_none_reason": "",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_entry_ready": "False",
                "consumer_check_display_ready": "True",
                "entry_wait_state": "CENTER",
                "entry_wait_hard": "False",
                "entry_wait_reason": "center_wait",
                "entry_wait_selected": "False",
                "entry_wait_decision": "skip",
            },
        ],
    )
    _write_entry_decision_log(
        app.trade_history_csv_path,
        [
            {
                "close_time": "2026-03-27 19:10:00",
                "open_time": "2026-03-27 18:50:00",
                "symbol": "BTCUSD",
                "status": "OPEN",
                "exit_wait_state": "REVERSAL_CONFIRM",
                "exit_wait_selected": "1",
                "exit_wait_decision": "wait_exit_reversal_confirm",
                "decision_winner": "wait_exit",
                "decision_reason": "wait_exit_reversal_confirm",
                "exit_wait_state_family": "confirm_hold",
                "exit_wait_hold_class": "hard_hold",
                "exit_wait_decision_family": "wait_exit",
                "exit_wait_bridge_status": "aligned_confirm_wait",
            },
            {
                "close_time": "2026-03-27 19:11:00",
                "open_time": "2026-03-27 18:40:00",
                "symbol": "XAUUSD",
                "status": "CLOSED",
                "exit_wait_state": "RECOVERY_BE",
                "exit_wait_selected": "1",
                "exit_wait_decision": "wait_be_recovery",
                "decision_winner": "wait_be",
                "decision_reason": "wait_be_recovery",
                "exit_wait_state_family": "recovery_hold",
                "exit_wait_hold_class": "soft_hold",
                "exit_wait_decision_family": "recovery_wait",
                "exit_wait_bridge_status": "aligned_recovery_wait",
            },
            {
                "close_time": "2026-03-27 19:12:00",
                "open_time": "2026-03-27 18:30:00",
                "symbol": "NAS100",
                "status": "CLOSED",
                "exit_wait_state": "REVERSE_READY",
                "exit_wait_selected": "0",
                "exit_wait_decision": "",
                "decision_winner": "reverse_now",
                "decision_reason": "reverse_now_best",
                "exit_wait_state_family": "reverse_ready",
                "exit_wait_hold_class": "soft_hold",
                "exit_wait_decision_family": "reverse_now",
                "exit_wait_bridge_status": "aligned_reverse",
            },
        ],
    )
    app.latest_signal_by_symbol = {
        "BTCUSD": {
            "symbol": "BTCUSD",
            "action": "BUY",
            "next_action_hint": "BUY",
            "signal_bar_ts": 1773817800,
            "runtime_snapshot_generated_ts": 1773817812.5,
            "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1773817800|hint=BUY",
            "signal_age_sec": 12.5,
            "bar_age_sec": 12.5,
            "decision_latency_ms": 0,
            "missing_feature_count": 2,
            "data_completeness_ratio": 0.8,
            "used_fallback_count": 1,
            "compatibility_mode": "hybrid",
            "snapshot_payload_bytes": 321,
            "position_snapshot_v2": {
                "zones": {"box_zone": "LOWER"},
                "interpretation": {"primary_label": "LOWER_BIAS"},
                "energy": {"lower_position_force": 0.71},
                "vector": {"x_box": 0.12},
            },
            "response_vector_v2": {"lower_hold_up": 0.84},
            "observe_confirm_v2": {
                "action": "WAIT",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
            },
            "forecast_assist_v1": {"active": True, "decision_hint": "confirm_bias", "confirm_fake_gap": 0.21},
            "entry_default_side_gate_v1": {"contract_version": "entry_default_side_gate_v1", "gate_passed": True},
            "entry_probe_plan_v1": {
                "contract_version": "entry_probe_plan_v1",
                "active": True,
                "ready_for_entry": True,
                "reason": "probe_ready",
                "symbol_scene_relief": "xau_second_support_buy_probe",
                "symbol_probe_temperament_v1": {
                    "entry_style_hint": "aggressive_second_support",
                    "promotion_bias": "aggressive_second_support",
                    "source_map_id": "shared_symbol_temperament_map_v1",
                    "note": "xau_second_support_buy_more_aggressive",
                },
                "pair_gap": 0.28,
            },
            "edge_pair_law_v1": {"contract_version": "edge_pair_law_v1", "context_label": "LOWER_EDGE", "winner_side": "BUY"},
            "probe_candidate_v1": {
                "contract_version": "probe_candidate_v1",
                "active": True,
                "ready_for_entry": True,
                "probe_direction": "BUY",
                "candidate_support": 0.91,
                "pair_gap": 0.28,
                "intended_action": "BUY",
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_second_support_buy_probe",
                    "promotion_bias": "aggressive_second_support",
                    "source_map_id": "shared_symbol_temperament_map_v1",
                    "note": "xau_second_support_buy_more_aggressive",
                },
            },
            "entry_wait_context_v1": dict(btc_wait_context),
            "entry_wait_bias_bundle_v1": dict(btc_wait_bias_bundle),
            "entry_wait_state_policy_input_v1": dict(btc_wait_state_policy_input),
            "entry_wait_state": "HELPER_SOFT_BLOCK",
            "entry_wait_hard": 1,
            "entry_wait_reason": "soft_block_preferred_wait",
            "entry_wait_selected": 1,
            "entry_wait_decision": "wait_soft_helper_block",
            "entry_decision_context_v1": {
                "symbol": "BTCUSD",
                "phase": "entry",
                "market_mode": "RANGE",
                "box_state": "LOWER",
                "bb_state": "LOWER_EDGE",
                "metadata": {
                    "core_reason": "core_shadow_probe_action",
                    "forecast_assist_v1": {"active": True, "decision_hint": "confirm_bias", "confirm_fake_gap": 0.21},
                    "entry_probe_plan_v1": {"active": True, "ready_for_entry": True},
                },
            },
            "entry_decision_result_v1": {
                "phase": "entry",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "wait",
                "blocked_by": "probe_barrier_blocked",
                "selected_setup": {"setup_id": "range_lower_reversal_buy", "side": "BUY"},
            },
            "semantic_shadow_available": 1,
            "semantic_shadow_reason": "available",
            "semantic_shadow_activation_state": "active",
            "semantic_shadow_activation_reason": "available",
            "semantic_live_threshold_applied": 0,
            "semantic_live_threshold_state": "fallback_blocked",
            "semantic_live_threshold_reason": "compatibility_mode_blocked",
        }
    }

    app._write_runtime_status(
        loop_count=1,
        symbols=["BTCUSD"],
        entry_threshold=45,
        exit_threshold=35,
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))

    assert slim["detail_payload_path"] == "runtime_status.detail.json"
    assert slim["semantic_live_config"]["contract_version"] == "semantic_live_rollout_v1"
    assert "symbol_allowlist" in slim["semantic_live_config"]
    assert "entry_stage_allowlist" in slim["semantic_live_config"]
    assert slim["semantic_live_config"]["shadow_runtime_state"] == "inactive"
    assert slim["semantic_live_config"]["shadow_runtime_reason"] == "runtime_unavailable"
    assert slim["semantic_shadow_runtime_checked_at"]
    assert slim["semantic_shadow_runtime_model_dir"] == str(app.semantic_model_dir)
    assert slim["semantic_shadow_runtime_load_error"] == ""
    assert "semantic_rollout_state" in slim
    assert app.semantic_rollout_manifest_path.exists()
    assert slim["recent_summary_window"] == "last_200"
    assert slim["recent_stage_counts"]["READY"] == 1
    assert slim["recent_stage_counts"]["PROBE"] == 1
    assert slim["recent_stage_counts"]["OBSERVE"] == 1
    assert slim["recent_stage_counts"]["BLOCKED"] == 1
    assert slim["recent_wrong_ready_count"] == 1
    assert slim["recent_blocked_reason_counts"]["energy_soft_block"] == 1
    assert slim["recent_blocked_reason_counts"]["forecast_guard"] == 1
    assert slim["recent_symbol_summary"]["BTCUSD"]["rows"] == 2
    assert slim["recent_runtime_summary"]["windows"]["last_50"]["row_count"] == 4
    assert slim["recent_exit_summary_window"] == "last_200"
    assert slim["recent_exit_status_counts"]["CLOSED"] == 2
    assert slim["recent_exit_status_counts"]["OPEN"] == 1
    assert slim["recent_exit_state_semantic_summary"]["state_family_counts"]["confirm_hold"] == 1
    assert slim["recent_exit_state_semantic_summary"]["state_family_counts"]["recovery_hold"] == 1
    assert slim["recent_exit_decision_summary"]["decision_family_counts"]["wait_exit"] == 1
    assert slim["recent_exit_decision_summary"]["decision_family_counts"]["recovery_wait"] == 1
    assert slim["recent_exit_decision_summary"]["decision_family_counts"]["reverse_now"] == 1
    assert (
        slim["recent_exit_state_decision_bridge_summary"]["bridge_status_counts"]["aligned_confirm_wait"]
        == 1
    )
    assert slim["recent_exit_symbol_summary"]["BTCUSD"]["rows"] == 1
    assert "recent_runtime_diagnostics" not in slim
    assert "recent_exit_runtime_diagnostics" not in slim
    assert "semantic_shadow_runtime_diagnostics" not in slim
    slim_row = slim["latest_signal_by_symbol"]["BTCUSD"]
    assert slim_row["runtime_snapshot_key"].startswith("runtime_signal_row_v1|symbol=BTCUSD")
    assert slim_row["timestamp"]
    assert slim_row["observe_action"] == "WAIT"
    assert slim_row["observe_side"] == "BUY"
    assert slim_row["observe_reason"] == "lower_rebound_probe_observe"
    assert slim_row["signal_age_sec"] == 12.5
    assert slim_row["bar_age_sec"] == 12.5
    assert slim_row["decision_latency_ms"] == 0
    assert slim_row["missing_feature_count"] == 2
    assert slim_row["data_completeness_ratio"] == 0.8
    assert slim_row["used_fallback_count"] == 1
    assert slim_row["compatibility_mode"] == "hybrid"
    assert slim_row["snapshot_payload_bytes"] == 321
    assert slim_row["position_snapshot_v2"]["vector"]["x_box"] == 0.12
    assert slim_row["response_vector_v2"]["lower_hold_up"] == 0.84
    assert slim_row["forecast_assist_v1"]["decision_hint"] == "confirm_bias"
    assert slim_row["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert slim_row["edge_pair_law_v1"]["winner_side"] == "BUY"
    assert slim_row["probe_candidate_v1"]["intended_action"] == "BUY"
    assert slim_row["probe_candidate_active"] is True
    assert slim_row["probe_direction"] == "BUY"
    assert slim_row["probe_scene_id"] == "xau_second_support_buy_probe"
    assert slim_row["probe_candidate_support"] == 0.91
    assert slim_row["probe_pair_gap"] == 0.28
    assert slim_row["probe_plan_active"] is True
    assert slim_row["probe_plan_ready"] is True
    assert slim_row["probe_plan_reason"] == "probe_ready"
    assert slim_row["probe_plan_scene"] == "xau_second_support_buy_probe"
    assert slim_row["probe_promotion_bias"] == "aggressive_second_support"
    assert slim_row["probe_temperament_source"] == "shared_symbol_temperament_map_v1"
    assert slim_row["probe_entry_style"] == "aggressive_second_support"
    assert slim_row["probe_temperament_note"] == "xau_second_support_buy_more_aggressive"
    assert slim_row["quick_trace_state"] == "PROBE_READY"
    assert slim_row["quick_trace_reason"] == "probe_ready"
    assert slim_row["wait_policy_state"] == "HELPER_SOFT_BLOCK"
    assert slim_row["wait_policy_reason"] == "soft_block_preferred_wait"
    assert slim_row["wait_probe_scene_id"] == "btc_lower_buy_conservative_probe"
    assert slim_row["wait_probe_ready_for_entry"] is False
    assert slim_row["wait_bias_release_sources"] == ["belief"]
    assert slim_row["wait_bias_wait_lock_sources"] == ["state"]
    assert slim_row["wait_required_side"] == "BUY"
    assert slim_row["entry_wait_state"] == "HELPER_SOFT_BLOCK"
    assert slim_row["entry_wait_hard"] == 1
    assert slim_row["entry_wait_decision"] == "wait_soft_helper_block"
    assert slim_row["wait_threshold_shift_summary"]["soft_threshold_shift"] == -6.75
    assert slim_row["entry_wait_context_v1"]["policy"]["state"] == "HELPER_SOFT_BLOCK"
    assert slim_row["entry_wait_bias_bundle_v1"]["active_release_sources"] == ["belief"]
    assert slim_row["entry_wait_state_policy_input_v1"]["special_scenes"]["probe_scene_id"] == "btc_lower_buy_conservative_probe"
    assert slim_row["legacy_raw_score_v1"]["contract_version"] == "legacy_raw_score_surface_v1"
    assert slim_row["position_energy_surface_v1"]["position"]["primary_label"] == "LOWER_BIAS"
    assert slim_row["position_energy_surface_v1"]["observe"]["reason"] == "lower_rebound_probe_observe"
    assert slim_row["position_energy_surface_v1"]["readiness"]["wait_policy_state"] == "HELPER_SOFT_BLOCK"
    assert slim_row["position_energy_surface_v1"]["summary"]["decision_state"] == "BLOCKED"
    assert slim_row["semantic_shadow_available"] == 1
    assert slim_row["semantic_shadow_reason"] == "available"
    assert slim_row["semantic_shadow_activation_state"] == "active"
    assert slim_row["semantic_shadow_activation_reason"] == "available"
    assert slim_row["semantic_live_threshold_applied"] == 0
    assert slim_row["semantic_live_threshold_state"] == "fallback_blocked"
    assert slim_row["semantic_live_threshold_reason"] == "compatibility_mode_blocked"
    assert slim_row["entry_decision_context_v1"]["metadata"]["core_reason"] == "core_shadow_probe_action"
    assert slim_row["entry_decision_result_v1"]["selected_setup"]["setup_id"] == "range_lower_reversal_buy"

    detail_row = detail["latest_signal_by_symbol"]["BTCUSD"]
    assert detail_row["runtime_snapshot_key"] == slim_row["runtime_snapshot_key"]
    assert detail_row["snapshot_payload_bytes"] == 321
    assert detail_row["position_snapshot_v2"]["vector"]["x_box"] == 0.12
    assert detail_row["legacy_raw_score_v1"]["contract_version"] == "legacy_raw_score_surface_v1"
    assert detail_row["position_energy_surface_v1"]["summary"]["decision_state"] == "BLOCKED"
    assert detail_row["position_energy_surface_v1"]["summary"]["state_reason"] == "probe_barrier_blocked"
    assert detail_row["semantic_shadow_activation_state"] == "active"
    assert detail_row["semantic_live_threshold_reason"] == "compatibility_mode_blocked"
    assert detail["recent_runtime_diagnostics"]["source_path"] == str(app.entry_decision_log_path)
    assert detail["recent_exit_runtime_diagnostics"]["source_path"] == str(app.trade_history_csv_path)
    assert detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["row_count"] == 3
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["exit_state_semantic_summary"][
            "state_family_counts"
        ]["reverse_ready"]
        == 1
    )
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["exit_decision_summary"][
            "winner_counts"
        ]["wait_be"]
        == 1
    )
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["exit_state_decision_bridge_summary"][
            "state_to_decision_counts"
        ]["confirm_hold->wait_exit"]
        == 1
    )
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["XAUUSD"][
            "exit_decision_summary"
        ]["decision_family_counts"]["recovery_wait"]
        == 1
    )
    assert detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wrong_ready_count"] == 1
    assert detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"]["rows"] == 2
    wait_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_energy_trace_summary"]
    assert wait_summary["entry_wait_state_trace"]["trace_present_rows"] == 2
    assert wait_summary["entry_wait_state_trace"]["trace_branch_rows"] == 2
    assert wait_summary["entry_wait_state_trace"]["branch_counts"]["helper_soft_block_state"] == 1
    assert wait_summary["entry_wait_state_trace"]["branch_counts"]["helper_wait_bias_state"] == 1
    assert wait_summary["entry_wait_decision_trace"]["trace_present_rows"] == 1
    assert wait_summary["entry_wait_decision_trace"]["branch_counts"]["wait_soft_helper_block_decision"] == 1
    wait_bias_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_bias_bundle_summary"]
    assert wait_bias_summary["active_release_source_counts"]["belief"] == 1
    assert wait_bias_summary["active_release_source_counts"]["probe"] == 1
    assert wait_bias_summary["active_wait_lock_source_counts"]["state"] == 1
    wait_policy_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_state_policy_surface_summary"]
    assert wait_policy_summary["policy_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_policy_summary["policy_state_counts"]["PROBE_CANDIDATE"] == 1
    assert wait_policy_summary["policy_reason_counts"]["soft_block_preferred_wait"] == 1
    assert wait_policy_summary["policy_reason_counts"]["xau_second_support_probe_wait"] == 1
    assert wait_policy_summary["required_side_counts"]["BUY"] == 2
    assert wait_policy_summary["policy_hard_block_active_rows"] == 1
    assert wait_policy_summary["helper_soft_block_rows"] == 1
    assert wait_policy_summary["helper_wait_hint_rows"] == 1
    wait_scene_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_special_scene_summary"]
    assert wait_scene_summary["probe_scene_counts"]["btc_lower_buy_conservative_probe"] == 1
    assert wait_scene_summary["probe_scene_counts"]["xau_second_support_buy_probe"] == 1
    assert wait_scene_summary["xau_second_support_probe_relief_rows"] == 1
    assert wait_scene_summary["btc_lower_strong_score_soft_wait_candidate_rows"] == 1
    assert wait_scene_summary["probe_ready_for_entry_rows"] == 1
    wait_threshold_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_threshold_shift_summary"]
    assert wait_threshold_summary["soft_threshold_shift_avg"] == -3.375
    assert wait_threshold_summary["hard_threshold_shift_avg"] == 3.5
    assert wait_threshold_summary["soft_threshold_shift_down_rows"] == 1
    assert wait_threshold_summary["hard_threshold_shift_up_rows"] == 1
    wait_state_semantic_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_state_semantic_summary"]
    assert wait_state_semantic_summary["row_count"] == 4
    assert wait_state_semantic_summary["wait_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_state_semantic_summary["wait_state_counts"]["PROBE_CANDIDATE"] == 1
    assert wait_state_semantic_summary["wait_state_counts"]["CENTER"] == 1
    assert wait_state_semantic_summary["wait_state_counts"]["NONE"] == 1
    assert wait_state_semantic_summary["hard_wait_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_state_semantic_summary["hard_wait_true_rows"] == 1
    assert wait_state_semantic_summary["wait_reason_counts"]["soft_block_preferred_wait"] == 1
    wait_decision_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_decision_summary"]
    assert wait_decision_summary["decision_row_count"] == 4
    assert wait_decision_summary["wait_decision_counts"]["skip"] == 2
    assert wait_decision_summary["wait_decision_counts"]["wait_soft_helper_block"] == 1
    assert wait_decision_summary["wait_decision_counts"]["wait_soft_probe_candidate"] == 1
    assert wait_decision_summary["wait_selected_rows"] == 2
    assert wait_decision_summary["wait_skipped_rows"] == 2
    assert wait_decision_summary["wait_selected_rate"] == 0.5
    wait_bridge_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_state_decision_bridge_summary"]
    assert wait_bridge_summary["bridge_row_count"] == 4
    assert wait_bridge_summary["state_to_decision_counts"]["HELPER_SOFT_BLOCK->wait_soft_helper_block"] == 1
    assert wait_bridge_summary["state_to_decision_counts"]["PROBE_CANDIDATE->wait_soft_probe_candidate"] == 1
    assert wait_bridge_summary["selected_by_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_bridge_summary["selected_by_state_counts"]["PROBE_CANDIDATE"] == 1
    assert wait_bridge_summary["hard_wait_selected_rows"] == 1
    assert wait_bridge_summary["soft_wait_selected_rows"] == 1
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_energy_trace_summary"
        ]["entry_wait_decision_trace"]["trace_branch_rows"]
        == 1
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_special_scene_summary"
        ]["btc_lower_strong_score_soft_wait_candidate_rows"]
        == 1
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_state_semantic_summary"
        ]["wait_state_counts"]["CENTER"]
        == 1
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_decision_summary"
        ]["wait_selected_rows"]
        == 1
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_state_decision_bridge_summary"
        ]["selected_by_state_counts"]["HELPER_SOFT_BLOCK"]
        == 1
    )
    assert (
        slim["recent_runtime_summary"]["windows"]["last_200"]["wait_energy_trace_summary"][
            "entry_wait_state_trace"
        ]["trace_branch_rows"]
        == 2
    )
    assert slim["runtime_recycle_health_v1"]["contract_version"] == "runtime_recycle_health_v1"
    assert slim["runtime_recycle_health_v1"]["live_symbol_count"] == 1
    assert slim["runtime_recycle_drift_v1"]["contract_version"] == "runtime_recycle_drift_v1"
    assert slim["runtime_recycle_drift_v1"]["recent_row_count"] == 4
    assert slim["recent_wait_bias_bundle_summary"]["active_release_source_counts"]["belief"] == 1
    assert slim["recent_wait_special_scene_summary"]["probe_scene_counts"]["xau_second_support_buy_probe"] == 1
    assert slim["recent_wait_threshold_shift_summary"]["soft_threshold_shift_avg"] == -3.375
    assert slim["recent_wait_state_semantic_summary"]["wait_state_counts"]["NONE"] == 1
    assert slim["recent_wait_decision_summary"]["wait_selected_rate"] == 0.5
    assert (
        slim["recent_wait_state_decision_bridge_summary"]["state_to_decision_counts"][
            "CENTER->skip"
        ]
        == 1
    )
    assert detail["semantic_shadow_runtime_checked_at"]
    assert detail["semantic_shadow_runtime_diagnostics"]["reason"] == "runtime_unavailable"
    assert detail["semantic_shadow_runtime_diagnostics"]["model_dir"] == str(app.semantic_model_dir)
    assert detail["semantic_shadow_runtime_diagnostics"]["raw"]["checked_at"]
    assert detail["runtime_recycle_health_v1"]["signal_stale_sec"] == 900
    assert detail["runtime_recycle_drift_v1"]["required_signal_count"] == 2


def test_runtime_status_promotes_probe_candidate_from_observe_metadata(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"
    app.latest_signal_by_symbol = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "signal_bar_ts": 1773817800,
            "runtime_snapshot_generated_ts": 1773817812.5,
            "observe_confirm_v2": {
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "metadata": {
                    "blocked_reason": "outer_band_buy_reversal_support_required",
                    "blocked_guard": "outer_band_guard",
                    "probe_candidate_v1": {
                        "active": True,
                        "probe_direction": "BUY",
                        "candidate_support": 0.87,
                        "pair_gap": 0.18,
                        "symbol_probe_temperament_v1": {
                            "scene_id": "xau_second_support_buy_probe",
                            "promotion_bias": "aggressive_second_support",
                            "source_map_id": "shared_symbol_temperament_map_v1",
                            "note": "xau_second_support_buy_more_aggressive",
                        },
                    },
                    "edge_pair_law_v1": {
                        "context_label": "LOWER_EDGE",
                        "winner_side": "BUY",
                    },
                },
            },
        }
    }

    app._write_runtime_status(
        loop_count=1,
        symbols=["XAUUSD"],
        entry_threshold=45,
        exit_threshold=35,
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    slim_row = slim["latest_signal_by_symbol"]["XAUUSD"]
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert slim_row["blocked_by"] == "outer_band_guard"
    assert slim_row["probe_candidate_active"] is True
    assert slim_row["probe_direction"] == "BUY"
    assert slim_row["probe_scene_id"] == "xau_second_support_buy_probe"
    assert slim_row["probe_candidate_support"] == 0.87
    assert slim_row["probe_pair_gap"] == 0.18
    assert slim_row["probe_promotion_bias"] == "aggressive_second_support"
    assert slim_row["probe_temperament_source"] == "shared_symbol_temperament_map_v1"
    assert slim_row["probe_temperament_note"] == "xau_second_support_buy_more_aggressive"
    assert slim_row["quick_trace_state"] == "PROBE_CANDIDATE_BLOCKED"
    assert slim_row["quick_trace_reason"] == "outer_band_guard"
    assert slim_row["probe_candidate_v1"]["probe_direction"] == "BUY"
    assert slim_row["edge_pair_law_v1"]["winner_side"] == "BUY"
    assert slim["recent_runtime_summary"]["available"] is False
    assert slim["recent_runtime_summary"]["reason"] == "source_missing"
    assert slim["recent_exit_runtime_summary"]["available"] is False
    assert slim["recent_exit_runtime_summary"]["reason"] == "source_missing"
    assert slim["recent_stage_counts"] == {}
    assert slim["recent_wrong_ready_count"] == 0
    assert slim["recent_exit_status_counts"] == {}
    assert detail["recent_runtime_diagnostics"]["reason"] == "source_missing"
    assert detail["recent_exit_runtime_diagnostics"]["reason"] == "source_missing"
    assert detail["recent_runtime_diagnostics"]["windows"]["last_50"]["row_count"] == 0
    assert detail["recent_exit_runtime_diagnostics"]["windows"]["last_50"]["row_count"] == 0
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_energy_trace_summary"][
            "entry_wait_state_trace"
        ]["trace_branch_rows"]
        == 0
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_bias_bundle_summary"][
            "active_release_source_counts"
        ]
        == {}
    )
    assert detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_state_semantic_summary"]["row_count"] == 0
    assert detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_decision_summary"]["wait_selected_rate"] == 0.0
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_state_decision_bridge_summary"][
            "state_to_decision_counts"
        ]
        == {}
    )
    assert detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_threshold_shift_summary"][
        "soft_threshold_shift_avg"
    ] == 0.0
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_50"]["exit_state_semantic_summary"][
            "state_family_counts"
        ]
        == {}
    )
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_50"]["exit_decision_summary"][
            "winner_counts"
        ]
        == {}
    )


def test_runtime_status_normalizes_stale_position_counts_from_live_broker(monkeypatch, tmp_path):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    from backend.core.config import Config

    app = TradingApplication(
        broker=_DummyBroker(
            positions=[
                _DummyPosition(ticket=101, symbol="NAS100", magic=Config.MAGIC_NUMBER),
            ]
        ),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.runtime_status_path = tmp_path / "runtime_status.json"
    app.runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    app.semantic_rollout_manifest_path = tmp_path / "semantic_live_rollout_latest.json"
    app.entry_decision_log_path = tmp_path / "missing_entry_decisions.csv"
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"
    app.latest_signal_by_symbol = {
        "BTCUSD": {
            "symbol": "BTCUSD",
            "my_position_count": 1,
            "buy_score": 100,
            "sell_score": 10,
        },
        "NAS100": {
            "symbol": "NAS100",
            "my_position_count": 0,
            "buy_score": 80,
            "sell_score": 5,
        },
    }
    app.runtime_recycle_state["last_open_positions_count"] = 9
    app.runtime_recycle_state["last_owned_open_positions_count"] = 4

    app._write_runtime_status(
        loop_count=2,
        symbols=["BTCUSD", "NAS100"],
        entry_threshold=45,
        exit_threshold=70,
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))

    assert slim["latest_signal_by_symbol"]["BTCUSD"]["my_position_count"] == 0
    assert slim["latest_signal_by_symbol"]["NAS100"]["my_position_count"] == 1
    assert detail["runtime_recycle"]["last_open_positions_count"] == 1
    assert detail["runtime_recycle"]["last_owned_open_positions_count"] == 1


def test_runtime_status_exports_pending_reverse_by_symbol(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"
    now_ts = time.time()
    app.pending_reverse_by_symbol = {
        "BTCUSD": {
            "action": "BUY",
            "score": 189.0,
            "reasons": ["opposite_score_spike", "volatility_spike"],
            "created_at": now_ts - 3.0,
            "expires_at": now_ts + 12.0,
        }
    }

    app._write_runtime_status(
        loop_count=3,
        symbols=["BTCUSD"],
        entry_threshold=45,
        exit_threshold=70,
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    slim_pending = slim["pending_reverse_by_symbol"]["BTCUSD"]
    detail_pending = detail["pending_reverse_by_symbol"]["BTCUSD"]

    assert slim_pending["action"] == "BUY"
    assert slim_pending["reason_count"] == 2
    assert slim_pending["score"] == 189.0
    assert slim_pending["age_sec"] >= 0
    assert slim_pending["expires_in_sec"] > 0
    assert detail_pending["reasons"] == ["opposite_score_spike", "volatility_spike"]


def test_runtime_status_exports_state_first_context_fields(monkeypatch, tmp_path):
    from backend.core.trade_constants import TIMEFRAME_D1, TIMEFRAME_H1, TIMEFRAME_H4, TIMEFRAME_M15

    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    broker = _DummyBroker(
        rates_by_timeframe={
            TIMEFRAME_M15: _build_rates(start=100.0, step=-1.0),
            TIMEFRAME_H1: _build_rates(start=150.0, step=1.5),
            TIMEFRAME_H4: _build_rates(start=200.0, step=1.7),
            TIMEFRAME_D1: _build_rates(start=250.0, step=1.8),
        }
    )
    app = TradingApplication(
        broker=broker,
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.runtime_status_path = tmp_path / "runtime_status.json"
    app.runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    app.semantic_rollout_manifest_path = tmp_path / "semantic_live_rollout_latest.json"
    app.entry_decision_log_path = tmp_path / "missing_entry_decisions.csv"
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"
    app.latest_signal_by_symbol = {
        "NAS100": {
            "symbol": "NAS100",
            "consumer_check_side": "SELL",
            "current_price": 101.5,
            "same_color_run_current": 6,
        }
    }

    app._write_runtime_status(
        2,
        {"NAS100": "NAS100"},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    slim_row = dict(slim["latest_signal_by_symbol"]["NAS100"])
    detail_row = dict(detail["latest_signal_by_symbol"]["NAS100"])

    assert slim_row["trend_15m_direction"] == "DOWNTREND"
    assert slim_row["trend_1h_direction"] == "UPTREND"
    assert slim_row["htf_alignment_state"] == "AGAINST_HTF"
    assert slim_row["previous_box_break_state"] in {
        "BREAKOUT_HELD",
        "BREAKOUT_FAILED",
        "BREAKDOWN_HELD",
        "INSIDE",
        "REJECTED",
    }
    assert "context_conflict_state" in slim_row
    assert "context_conflict_flags" in slim_row
    assert "late_chase_risk_state" in slim_row
    assert detail_row["context_state_version"] == "context_state_v1_2"
    assert detail_row["previous_box_context_version"] == "previous_box_context_v1"


def test_runtime_row_context_export_includes_directional_continuation_overlay(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        "backend.app.trading_application.build_context_state_v12",
        lambda **kwargs: {
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "NONE",
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_directional_continuation_chart_overlay_state",
        lambda symbol, runtime_row, continuation_candidates=None: {
            "contract_version": "directional_continuation_chart_overlay_v1",
            "symbol": symbol,
            "overlay_enabled": True,
            "overlay_direction": "DOWN",
            "overlay_side": "SELL",
            "overlay_event_kind_hint": "SELL_WATCH",
            "overlay_score": 0.77,
            "overlay_selection_state": "DOWN_SELECTED",
            "overlay_candidate_key": "candidate-xau-down",
            "overlay_source_kind": "market_family_entry_audit",
            "overlay_reason_match": True,
        },
    )
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    enriched = app._enrich_runtime_signal_row_with_state_context(
        "XAUUSD",
        {
            "symbol": "XAUUSD",
            "observe_reason": "upper_reject_probe_observe",
        },
        continuation_candidates=[],
    )

    assert enriched["directional_continuation_overlay_v1"]["overlay_event_kind_hint"] == "SELL_WATCH"
    assert enriched["directional_continuation_overlay_enabled"] is True
    assert enriched["directional_continuation_overlay_direction"] == "DOWN"
    assert enriched["directional_continuation_overlay_selection_state"] == "DOWN_SELECTED"


def test_build_chart_painter_runtime_row_keeps_existing_execution_fields_and_adds_overlay(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        "backend.app.trading_application.build_context_state_v12",
        lambda **kwargs: {
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_directional_continuation_chart_overlay_state",
        lambda symbol, runtime_row, continuation_candidates=None: {
            "contract_version": "directional_continuation_chart_overlay_v1",
            "symbol": symbol,
            "overlay_enabled": True,
            "overlay_direction": "UP",
            "overlay_side": "BUY",
            "overlay_event_kind_hint": "BUY_WATCH",
            "overlay_score": 0.91,
            "overlay_selection_state": "UP_SELECTED",
            "overlay_candidate_key": "candidate-xau-up",
            "overlay_source_kind": "wrong_side_conflict_harvest",
            "overlay_reason_match": False,
        },
    )
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    row = app.build_chart_painter_runtime_row(
        "XAUUSD",
        {
            "symbol": "XAUUSD",
            "consumer_check_side": "SELL",
            "consumer_check_stage": "BLOCKED",
            "consumer_check_reason": "upper_break_fail_confirm",
            "execution_diff_original_action_side": "SELL",
            "execution_diff_final_action_side": "SKIP",
            "execution_action_diff_v1": {
                "original_action_side": "SELL",
                "final_action_side": "SKIP",
            },
        },
        continuation_candidates=[],
    )

    assert row["directional_continuation_overlay_v1"]["overlay_event_kind_hint"] == "BUY_WATCH"
    assert row["directional_continuation_overlay_enabled"] is True
    assert row["directional_continuation_overlay_direction"] == "UP"
    assert row["execution_diff_original_action_side"] == "SELL"
    assert row["execution_diff_final_action_side"] == "SKIP"
    assert row["execution_action_diff_v1"]["original_action_side"] == "SELL"


def test_build_entry_runtime_signal_row_keeps_existing_execution_fields_and_adds_overlay(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        "backend.app.trading_application.build_context_state_v12",
        lambda **kwargs: {
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_directional_continuation_chart_overlay_state",
        lambda symbol, runtime_row, continuation_candidates=None: {
            "contract_version": "directional_continuation_chart_overlay_v1",
            "symbol": symbol,
            "overlay_enabled": True,
            "overlay_direction": "UP",
            "overlay_side": "BUY",
            "overlay_event_kind_hint": "BUY_WATCH",
            "overlay_score": 0.87,
            "overlay_selection_state": "UP_SELECTED",
            "overlay_candidate_key": "candidate-nas-up",
            "overlay_source_kind": "wrong_side_conflict_harvest",
            "overlay_reason_match": False,
        },
    )
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    row = app.build_entry_runtime_signal_row(
        "NAS100",
        {
            "symbol": "NAS100",
            "consumer_check_side": "SELL",
            "consumer_check_stage": "READY",
            "consumer_check_reason": "upper_break_fail_confirm",
            "execution_diff_original_action_side": "SELL",
            "execution_diff_final_action_side": "SELL",
            "execution_action_diff_v1": {
                "original_action_side": "SELL",
                "final_action_side": "SELL",
            },
        },
        continuation_candidates=[],
    )

    assert row["directional_continuation_overlay_v1"]["overlay_event_kind_hint"] == "BUY_WATCH"
    assert row["directional_continuation_overlay_enabled"] is True
    assert row["directional_continuation_overlay_direction"] == "UP"
    assert row["execution_diff_original_action_side"] == "SELL"
    assert row["execution_diff_final_action_side"] == "SELL"
    assert row["execution_action_diff_v1"]["original_action_side"] == "SELL"


def test_build_entry_runtime_signal_row_builds_candidates_when_cache_missing(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        "backend.app.trading_application.build_context_state_v12",
        lambda **kwargs: {
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_HTF",
        },
    )
    candidate_payload = [
        {
            "symbol": "XAUUSD",
            "continuation_direction": "DOWN",
            "candidate_key": "candidate-xau-down",
        }
    ]
    monkeypatch.setattr(
        "backend.app.trading_application.build_directional_continuation_learning_candidates",
        lambda: list(candidate_payload),
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_directional_continuation_chart_overlay_state",
        lambda symbol, runtime_row, continuation_candidates=None, previous_overlay_state=None: {
            "contract_version": "directional_continuation_chart_overlay_v1",
            "symbol": symbol,
            "overlay_enabled": bool(continuation_candidates),
            "overlay_direction": "DOWN",
            "overlay_side": "SELL",
            "overlay_event_kind_hint": "SELL_WATCH",
            "overlay_score": 0.74,
            "overlay_selection_state": "DOWN_SELECTED",
            "overlay_candidate_key": "candidate-xau-down",
            "overlay_source_kind": "market_family_entry_audit",
            "overlay_reason_match": True,
        },
    )
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    row = app.build_entry_runtime_signal_row(
        "XAUUSD",
        {
            "symbol": "XAUUSD",
            "observe_reason": "upper_reject_probe_observe",
        },
    )

    assert row["directional_continuation_overlay_direction"] == "DOWN"
    assert row["directional_continuation_overlay_event_kind_hint"] == "SELL_WATCH"
    assert app.directional_continuation_candidates_cache_v1 == candidate_payload


def test_build_entry_runtime_signal_row_attaches_accuracy_and_normalizes_nested_execution_diff(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        "backend.app.trading_application.build_context_state_v12",
        lambda **kwargs: {
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "NONE",
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_directional_continuation_chart_overlay_state",
        lambda symbol, runtime_row, continuation_candidates=None: {
            "contract_version": "directional_continuation_chart_overlay_v1",
            "symbol": symbol,
            "overlay_enabled": True,
            "overlay_direction": "UP",
            "overlay_side": "BUY",
            "overlay_event_kind_hint": "BUY_WATCH",
            "overlay_score": 0.82,
            "overlay_selection_state": "UP_SELECTED",
            "overlay_candidate_key": "candidate-btc-up",
            "overlay_source_kind": "market_family_entry_audit",
            "overlay_reason_match": True,
        },
    )
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.directional_continuation_accuracy_report_v1 = {
        "symbol_direction_primary_summary": {
            "BTCUSD|UP": {
                "sample_count": 6,
                "measured_count": 5,
                "correct_rate": 0.8,
                "false_alarm_rate": 0.2,
                "unresolved_rate": 0.1667,
                "last_evaluation_state": "CORRECT",
                "last_candidate_key": "candidate-btc-up",
            }
        }
    }

    row = app.build_entry_runtime_signal_row(
        "BTCUSD",
        {
            "symbol": "BTCUSD",
            "execution_action_diff_v1": {
                "original_action_side": "SELL",
                "guarded_action_side": "SKIP",
                "promoted_action_side": "BUY",
                "final_action_side": "BUY",
                "action_changed": True,
                "guard_applied": True,
                "promotion_active": True,
                "action_change_reason_keys": ["active_action_conflict_guard"],
                "guard_reason_summary": "wrong_side_conflict_pressure",
                "promotion_reason": "directional_continuation_overlay_promotion",
                "promotion_suppressed_reason": "",
            },
        },
        continuation_candidates=[],
    )

    assert row["directional_continuation_accuracy_horizon_bars"] == 20
    assert row["directional_continuation_accuracy_sample_count"] == 6
    assert row["directional_continuation_accuracy_correct_rate"] == 0.8
    assert row["execution_diff_original_action_side"] == "SELL"
    assert row["execution_diff_guarded_action_side"] == "SKIP"
    assert row["execution_diff_promoted_action_side"] == "BUY"
    assert row["execution_diff_final_action_side"] == "BUY"
    assert row["execution_diff_changed"] is True
    assert row["execution_diff_guard_applied"] is True
    assert row["execution_diff_promotion_active"] is True
    assert row["execution_diff_reason_keys"] == ["active_action_conflict_guard"]
    assert row["execution_diff_guard_reason_summary"] == "wrong_side_conflict_pressure"
    assert row["execution_diff_promotion_reason"] == "directional_continuation_overlay_promotion"
    assert row["execution_diff_promotion_suppressed_reason"] == ""


def test_build_entry_runtime_signal_row_hydrates_execution_diff_from_latest_trace(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        "backend.app.trading_application.build_context_state_v12",
        lambda **kwargs: {
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "NONE",
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_directional_continuation_chart_overlay_state",
        lambda symbol, runtime_row, continuation_candidates=None: {
            "contract_version": "directional_continuation_chart_overlay_v1",
            "symbol": symbol,
            "overlay_enabled": True,
            "overlay_direction": "UP",
            "overlay_side": "BUY",
            "overlay_event_kind_hint": "BUY_WATCH",
            "overlay_score": 0.72,
            "overlay_selection_state": "UP_SELECTED",
            "overlay_candidate_key": "candidate-btc-up",
            "overlay_source_kind": "market_family_entry_audit",
            "overlay_reason_match": True,
        },
    )
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.ai_entry_traces = [
        {
            "symbol": "BTCUSD",
            "execution_action_diff_v1": {
                "original_action_side": "SELL",
                "guarded_action_side": "SKIP",
                "promoted_action_side": "BUY",
                "final_action_side": "BUY",
                "action_changed": True,
                "guard_applied": True,
                "promotion_active": True,
                "action_change_reason_keys": ["active_action_conflict_guard"],
                "guard_reason_summary": "wrong_side_conflict_pressure",
                "promotion_reason": "directional_continuation_overlay_promotion",
                "promotion_suppressed_reason": "",
            }
        }
    ]

    row = app.build_entry_runtime_signal_row(
        "BTCUSD",
        {
            "symbol": "BTCUSD",
            "observe_reason": "upper_break_fail_confirm",
        },
        continuation_candidates=[],
    )

    assert row["execution_diff_original_action_side"] == "SELL"
    assert row["execution_diff_guarded_action_side"] == "SKIP"
    assert row["execution_diff_promoted_action_side"] == "BUY"
    assert row["execution_diff_final_action_side"] == "BUY"
    assert row["execution_diff_changed"] is True
    assert row["execution_diff_guard_applied"] is True
    assert row["execution_diff_promotion_active"] is True
    assert row["execution_diff_reason_keys"] == ["active_action_conflict_guard"]
    assert row["execution_diff_guard_reason_summary"] == "wrong_side_conflict_pressure"
    assert row["execution_diff_promotion_reason"] == "directional_continuation_overlay_promotion"
    assert row["execution_diff_promotion_suppressed_reason"] == ""


def test_build_entry_runtime_signal_row_clears_stale_chart_event_hint_when_overlay_disabled(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        "backend.app.trading_application.build_context_state_v12",
        lambda **kwargs: {"context_conflict_state": "NONE"},
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_state25_candidate_context_bridge_v1",
        lambda row: {"contract_version": "state25_candidate_context_bridge_v1"},
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_state25_candidate_context_bridge_flat_fields_v1",
        lambda payload: {},
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_directional_continuation_chart_overlay_state",
        lambda symbol, row, continuation_candidates=None, previous_overlay_state=None: {
            "contract_version": "directional_continuation_chart_overlay_v1",
            "overlay_enabled": False,
            "overlay_direction": "",
            "overlay_side": "",
            "overlay_event_kind_hint": "",
            "overlay_score": 0.0,
            "overlay_selection_state": "LOW_ALIGNMENT",
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_directional_continuation_chart_overlay_flat_fields_v1",
        lambda payload: {
            "directional_continuation_overlay_enabled": False,
            "directional_continuation_overlay_direction": "",
            "directional_continuation_overlay_event_kind_hint": "",
            "directional_continuation_overlay_selection_state": "LOW_ALIGNMENT",
            "directional_continuation_overlay_score": 0.0,
        },
    )

    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    row = app.build_entry_runtime_signal_row(
        "XAUUSD",
        {
            "symbol": "XAUUSD",
            "chart_event_kind_hint": "BUY_WATCH",
            "chart_event_reason_hint": "stale_hint",
        },
        continuation_candidates=[],
    )

    assert row["directional_continuation_overlay_enabled"] is False
    assert row["chart_event_kind_hint"] == ""
    assert row["chart_event_reason_hint"] == ""


def test_append_ai_entry_trace_keeps_execution_diff_fields(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    app._append_ai_entry_trace(
        {
            "symbol": "BTCUSD",
            "action": "BUY",
            "final_score": 321.0,
            "threshold": 0.55,
            "execution_diff_original_action_side": "SELL",
            "execution_diff_guarded_action_side": "SKIP",
            "execution_diff_promoted_action_side": "BUY",
            "execution_diff_final_action_side": "BUY",
            "execution_diff_changed": True,
            "execution_diff_guard_applied": True,
            "execution_diff_promotion_active": True,
            "execution_diff_reason_keys": [
                "active_action_conflict_guard",
                "directional_continuation_overlay_multitf_promotion",
            ],
            "execution_diff_guard_reason_summary": "wrong_side_conflict_pressure",
            "execution_diff_promotion_reason": "directional_continuation_overlay_multitf_promotion",
            "execution_diff_promotion_suppressed_reason": "",
        }
    )

    row = app.ai_entry_traces[-1]
    assert row["execution_diff_original_action_side"] == "SELL"
    assert row["execution_diff_guarded_action_side"] == "SKIP"
    assert row["execution_diff_promoted_action_side"] == "BUY"
    assert row["execution_diff_final_action_side"] == "BUY"
    assert row["execution_diff_changed"] is True
    assert row["execution_diff_guard_applied"] is True
    assert row["execution_diff_promotion_active"] is True
    assert row["execution_diff_reason_keys"] == [
        "active_action_conflict_guard",
        "directional_continuation_overlay_multitf_promotion",
    ]
    assert row["execution_diff_guard_reason_summary"] == "wrong_side_conflict_pressure"
    assert row["execution_diff_promotion_reason"] == "directional_continuation_overlay_multitf_promotion"
    assert row["execution_diff_promotion_suppressed_reason"] == ""


def test_write_runtime_status_includes_runtime_signal_wiring_audit_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr(
        "backend.app.trading_application.update_directional_continuation_accuracy_tracker",
        lambda rows: {
            "summary": {
                "primary_horizon_bars": 20,
                "primary_measured_count": 3,
                "primary_correct_rate": 0.6667,
            },
            "artifact_paths": {"json_path": str(tmp_path / "accuracy.json")},
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.generate_and_write_runtime_signal_wiring_audit",
        lambda latest_signal_by_symbol, **kwargs: {
            "summary": {
                "symbol_count": 1,
                "overlay_present_count": 1,
                "execution_diff_surface_count": 1,
                "accuracy_surface_count": 1,
                "flow_sync_match_count": 1,
            },
            "artifact_paths": {"json_path": str(tmp_path / "wiring.json")},
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.generate_and_write_ca2_r0_stability_audit",
        lambda runtime_signal_wiring_audit, **kwargs: {
            "summary": {
                "status": "READY",
                "symbol_count": 1,
                "execution_diff_surface_count": 1,
                "flow_sync_match_count": 1,
                "primary_measured_count": 3,
            },
            "artifact_paths": {"json_path": str(tmp_path / "r0.json")},
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_runtime_row_session_bucket_surface_v1",
        lambda row: {
            "contract_version": "session_bucket_helper_v1",
            "session_bucket": "EU",
            "timestamp_source": "timestamp",
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_session_bucket_contract_v1",
        lambda: {
            "contract_version": "session_bucket_helper_v1",
            "timezone": "Asia/Seoul",
            "uses_dst_adjustment": False,
            "transition_buckets_enabled": False,
            "buckets": [],
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_session_direction_annotation_contract_v1",
        lambda: {
            "contract_version": "session_direction_annotation_contract_v1",
            "status": "READY",
            "session_bias_expansion_status": "HOLD",
            "fields": [],
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_should_have_done_contract_v1",
        lambda: {
            "contract_version": "should_have_done_contract_v1",
            "status": "READY",
            "fields": [],
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_canonical_surface_contract_v1",
        lambda: {
            "contract_version": "canonical_surface_contract_v1",
            "status": "READY",
            "priority_rule_v1": "phase>continuation>direction",
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.generate_and_write_ca2_session_split_audit",
        lambda **kwargs: {
            "summary": {
                "status": "READY",
                "correct_rate_by_session": {"ASIA": 0.61, "US": 0.78},
                "measured_count_by_session": {"ASIA": 22, "US": 24},
                "guard_helpful_rate_by_session": {"ASIA": None, "US": None},
                "promotion_win_rate_by_session": {"ASIA": None, "US": None},
                "session_difference_significance": {
                    "status": "SIGNIFICANT",
                    "pair": "ASIA|US",
                    "max_gap_pct_points": 17.0,
                },
            },
            "artifact_paths": {"json_path": str(tmp_path / "r1.json")},
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.generate_and_write_should_have_done_candidate_summary",
        lambda **kwargs: {
            "summary": {
                "status": "READY",
                "candidate_count": 2,
                "candidate_source_count_summary": {"AUTO_SURFACE_EXECUTION_MISMATCH": 1},
            },
            "artifact_paths": {"json_path": str(tmp_path / "r3.json")},
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.attach_canonical_surface_fields_v1",
        lambda rows: {
            "BTCUSD": {
                **dict(rows.get("BTCUSD") or {}),
                "canonical_runtime_surface_name_v1": "BUY_WATCH",
                "canonical_execution_surface_name_v1": "BUY_EXECUTION",
                "canonical_direction_annotation_v1": "UP",
                "canonical_continuation_annotation_v1": "CONTINUING",
                "canonical_phase_v1": "CONTINUATION",
                "canonical_runtime_execution_alignment_v1": "MATCH",
            }
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.generate_and_write_canonical_surface_summary_v1",
        lambda latest_signal_by_symbol, **kwargs: {
            "summary": {
                "status": "READY",
                "symbol_count": 1,
                "runtime_surface_count_summary": {"BUY_WATCH": 1},
                "execution_surface_count_summary": {"BUY_EXECUTION": 1},
                "alignment_count_summary": {"MATCH": 1},
            },
            "artifact_paths": {"json_path": str(tmp_path / "r4.json")},
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_session_aware_annotation_accuracy_contract_v1",
        lambda: {
            "contract_version": "session_aware_annotation_accuracy_contract_v1",
            "status": "READY",
            "fields": [],
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.generate_and_write_session_aware_annotation_accuracy_v1",
        lambda **kwargs: {
            "summary": {
                "status": "HOLD",
                "direction_accuracy_by_session": {"EU": 0.41, "US": 0.64},
                "phase_accuracy_data_status": "INSUFFICIENT_LABELED_ANNOTATIONS",
                "annotation_candidate_count_by_session": {"EU": 1, "US": 1},
                "runtime_execution_divergence_count_by_session": {"US": 1},
            },
            "artifact_paths": {"json_path": str(tmp_path / "r5.json")},
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.build_session_bias_shadow_contract_v1",
        lambda: {
            "contract_version": "session_bias_shadow_contract_v1",
            "status": "READY",
            "mode": "shadow_only",
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.attach_session_bias_shadow_fields_v1",
        lambda rows, **kwargs: {
            "BTCUSD": {
                **dict(rows.get("BTCUSD") or {}),
                "session_bias_candidate_state_v1": "READY",
                "session_bias_effect_v1": "RAISE_CONTINUATION_CONFIDENCE",
                "session_bias_confidence_v1": "HIGH",
                "would_change_surface_v1": True,
                "would_change_execution_v1": True,
                "would_change_state25_v1": False,
            }
        },
    )
    monkeypatch.setattr(
        "backend.app.trading_application.generate_and_write_session_bias_shadow_report_v1",
        lambda latest_signal_by_symbol, **kwargs: {
            "summary": {
                "status": "READY",
                "mode": "shadow_only",
                "symbol_count": 1,
                "candidate_state_count_summary": {"READY": 1},
                "effect_count_summary": {"RAISE_CONTINUATION_CONFIDENCE": 1},
                "execution_change_allowed": False,
                "state25_change_allowed": False,
            },
            "artifact_paths": {"json_path": str(tmp_path / "r6a.json")},
        },
    )
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.runtime_status_path = tmp_path / "runtime_status.json"
    app.runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    app.semantic_rollout_manifest_path = tmp_path / "semantic_live_rollout_latest.json"
    app.entry_decision_log_path = tmp_path / "entry_decision_log.csv"
    app.trade_history_csv_path = tmp_path / "trade_history.csv"
    app.latest_signal_by_symbol = {
        "BTCUSD": {
            "symbol": "BTCUSD",
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_enabled": True,
            "execution_action_diff_v1": {
                "original_action_side": "SELL",
                "final_action_side": "BUY",
            },
        }
    }

    app._write_runtime_status(
        1,
        {"BTCUSD": "BTCUSD"},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["runtime_signal_wiring_audit_summary_v1"]["symbol_count"] == 1
    assert detail["runtime_signal_wiring_audit_summary_v1"]["execution_diff_surface_count"] == 1
    assert detail["runtime_signal_wiring_audit_artifact_paths"]["json_path"].endswith("wiring.json")
    assert detail["session_bucket_contract_v1"]["contract_version"] == "session_bucket_helper_v1"
    assert detail["session_direction_annotation_contract_v1"]["contract_version"] == "session_direction_annotation_contract_v1"
    assert detail["session_direction_annotation_contract_v1"]["session_bias_expansion_status"] == "HOLD"
    assert detail["should_have_done_contract_v1"]["contract_version"] == "should_have_done_contract_v1"
    assert detail["canonical_surface_contract_v1"]["contract_version"] == "canonical_surface_contract_v1"
    assert detail["session_aware_annotation_accuracy_contract_v1"]["contract_version"] == "session_aware_annotation_accuracy_contract_v1"
    assert detail["ca2_r0_stability_summary_v1"]["status"] == "READY"
    assert detail["ca2_r0_stability_artifact_paths"]["json_path"].endswith("r0.json")
    assert detail["ca2_session_split_summary_v1"]["status"] == "READY"
    assert detail["ca2_session_split_summary_v1"]["session_difference_significance"]["status"] == "SIGNIFICANT"
    assert detail["ca2_session_split_artifact_paths"]["json_path"].endswith("r1.json")
    assert detail["should_have_done_summary_v1"]["status"] == "READY"
    assert detail["should_have_done_summary_v1"]["candidate_count"] == 2
    assert detail["should_have_done_artifact_paths"]["json_path"].endswith("r3.json")
    assert detail["canonical_surface_summary_v1"]["status"] == "READY"
    assert detail["canonical_surface_summary_v1"]["runtime_surface_count_summary"]["BUY_WATCH"] == 1
    assert detail["canonical_surface_artifact_paths"]["json_path"].endswith("r4.json")
    assert detail["session_aware_annotation_accuracy_summary_v1"]["status"] == "HOLD"
    assert detail["session_aware_annotation_accuracy_summary_v1"]["phase_accuracy_data_status"] == "INSUFFICIENT_LABELED_ANNOTATIONS"
    assert detail["session_aware_annotation_accuracy_artifact_paths"]["json_path"].endswith("r5.json")
    assert detail["session_bias_shadow_contract_v1"]["contract_version"] == "session_bias_shadow_contract_v1"
    assert detail["session_bias_shadow_contract_v1"]["execution_change_allowed"] is False
    assert detail["session_bias_shadow_summary_v1"]["status"] == "READY"
    assert detail["session_bias_shadow_summary_v1"]["mode"] == "shadow_only"
    assert detail["session_bias_shadow_artifact_paths"]["json_path"].endswith("r6a.json")
    assert detail["latest_signal_by_symbol"]["BTCUSD"]["session_bucket_v1"] == "EU"
    assert detail["latest_signal_by_symbol"]["BTCUSD"]["session_bucket_timestamp_source_v1"] == "timestamp"
    assert detail["latest_signal_by_symbol"]["BTCUSD"]["canonical_runtime_surface_name_v1"] == "BUY_WATCH"
    assert detail["latest_signal_by_symbol"]["BTCUSD"]["canonical_runtime_execution_alignment_v1"] == "MATCH"
    assert detail["latest_signal_by_symbol"]["BTCUSD"]["session_bias_effect_v1"] == "RAISE_CONTINUATION_CONFIDENCE"
    assert detail["latest_signal_by_symbol"]["BTCUSD"]["would_change_execution_v1"] is True


def test_attach_directional_continuation_accuracy_surface_fields(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    rows = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_enabled": True,
        }
    }
    report = {
        "symbol_direction_primary_summary": {
            "XAUUSD|UP": {
                "sample_count": 5,
                "measured_count": 4,
                "correct_rate": 0.75,
                "false_alarm_rate": 0.25,
                "unresolved_rate": 0.2,
                "last_evaluation_state": "CORRECT",
                "last_candidate_key": "candidate-xau-up",
            }
        }
    }

    enriched = app._attach_directional_continuation_accuracy_surface_fields(rows, report)
    row = enriched["XAUUSD"]

    assert row["directional_continuation_accuracy_horizon_bars"] == 20
    assert row["directional_continuation_accuracy_sample_count"] == 5
    assert row["directional_continuation_accuracy_measured_count"] == 4
    assert row["directional_continuation_accuracy_correct_rate"] == 0.75
    assert row["directional_continuation_accuracy_false_alarm_rate"] == 0.25
    assert row["directional_continuation_accuracy_last_state"] == "CORRECT"


def test_runtime_status_exports_flow_shadow_display_surface_contract_and_summary(monkeypatch, tmp_path):
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
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"

    app._write_runtime_status(
        1,
        {},
        45,
        70,
        policy_snapshot={"entry_threshold": 45, "exit_threshold": 70},
    )

    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert detail["flow_shadow_display_surface_contract_v1"]["contract_version"] == (
        "flow_shadow_display_surface_contract_v1"
    )
    assert "flow_shadow_display_surface_summary_v1" in detail
    assert "flow_shadow_display_surface_artifact_paths" in detail
